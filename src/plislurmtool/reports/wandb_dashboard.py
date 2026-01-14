#!/usr/bin/env python3
"""WandB Dashboard for SLURM Metrics"""

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

import wandb

from .slurm_analyzer import SLURMAnalyzer

PARTITIONS = ["pli-c", "pli-lc", "pli", "pli-p"]
DEFAULT_PROJECT = "pli-slurm-dashboard"


def get_wandb_config() -> dict:
    """Get WandB configuration from environment variables."""
    load_dotenv()

    if not os.environ.get("WANDB_API_KEY"):
        msg = (
            "WANDB_API_KEY environment variable is not set. "
            "Please set it directly or add it to a .env file in the current directory."
        )
        raise RuntimeError(msg)

    return {
        "project": os.environ.get("WANDB_PROJECT", DEFAULT_PROJECT),
        "entity": os.environ.get("WANDB_ENTITY"),
    }


def get_slurm_data(output_dir: Path, days: int = 1):
    """Fetch SLURM accounting data for the specified number of days."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    partitions = [
        ("pli-c", "sacct_pli_core.json"),
        ("pli-lc", "sacct_pli_large_campus.json"),
        ("pli", "sacct_pli_campus.json"),
        ("pli-p", "sacct_pli_p.json"),
    ]

    for partition, filename in partitions:
        print(f"Fetching data for {partition} (last {days} days)")
        result = subprocess.run(
            ["sacct", "-S", start_date, "--partition", partition, "--allusers", "--json"],
            capture_output=True,
            text=True,
            check=True,
        )
        (output_dir / filename).write_text(result.stdout)


def load_data(data_dir: Path) -> pd.DataFrame:
    """Load and parse SLURM data from JSON files."""
    analyzer = SLURMAnalyzer()
    files = ["sacct_pli_core.json", "sacct_pli_campus.json", "sacct_pli_large_campus.json", "sacct_pli_p.json"]

    dfs = []
    for filename in files:
        filepath = data_dir / filename
        if filepath.exists():
            dfs.append(analyzer.parse(json.loads(filepath.read_text())))

    if not dfs:
        msg = f"No SLURM data files found in {data_dir}"
        raise RuntimeError(msg)

    return pd.concat(dfs, ignore_index=True)


def compute_daily_metrics(df: pd.DataFrame, target_date: datetime) -> dict:
    """Compute metrics for jobs that started on a specific day."""
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    day_df = df[(df["start_time"] >= start_of_day) & (df["start_time"] < end_of_day)]

    metrics = {}

    for partition in PARTITIONS:
        partition_df = day_df[day_df["partition"] == partition]

        prefix = f"{partition}/"
        metrics[f"{prefix}gpu_hours"] = partition_df["gpu_time_h"].sum()
        metrics[f"{prefix}job_count"] = len(partition_df)
        metrics[f"{prefix}median_wait_h"] = partition_df["wait_time_h"].median() if len(partition_df) > 0 else 0

        long_wait_count = len(partition_df[partition_df["wait_time_h"] > 6])
        total_count = len(partition_df)
        metrics[f"{prefix}long_wait_pct"] = (long_wait_count / total_count * 100) if total_count > 0 else 0

        small_df = partition_df[partition_df["gpu_time_h"] <= 50]
        metrics[f"{prefix}small/job_count"] = len(small_df)
        metrics[f"{prefix}small/median_wait_h"] = small_df["wait_time_h"].median() if len(small_df) > 0 else 0
        small_long_wait = len(small_df[small_df["wait_time_h"] > 6])
        small_total = len(small_df)
        metrics[f"{prefix}small/long_wait_pct"] = (small_long_wait / small_total * 100) if small_total > 0 else 0

        large_df = partition_df[partition_df["gpu_time_h"] > 50]
        metrics[f"{prefix}large/job_count"] = len(large_df)
        metrics[f"{prefix}large/median_wait_h"] = large_df["wait_time_h"].median() if len(large_df) > 0 else 0
        large_long_wait = len(large_df[large_df["wait_time_h"] > 6])
        large_total = len(large_df)
        metrics[f"{prefix}large/long_wait_pct"] = (large_long_wait / large_total * 100) if large_total > 0 else 0

    metrics["total/gpu_hours"] = day_df["gpu_time_h"].sum()
    metrics["total/job_count"] = len(day_df)

    return metrics


def rewrite_history(days: int, data_dir: Path | None = None):
    """Clear WandB history and rebuild from N days of historical data."""
    config = get_wandb_config()

    print(f"Rewriting history for the last {days} days...")

    if data_dir:
        df = load_data(data_dir)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            get_slurm_data(tmp_path, days=days)
            df = load_data(tmp_path)

    run = wandb.init(
        **config,
        name="daily-metrics",
        id="slurm-daily-metrics",
        resume="allow",
    )

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    for step, day_offset in enumerate(range(days - 1, -1, -1)):
        target_date = today - timedelta(days=day_offset)
        print(f"Computing metrics for {target_date.strftime('%Y-%m-%d')}...")

        metrics = compute_daily_metrics(df, target_date)
        metrics["_timestamp"] = target_date.timestamp()
        wandb.log(metrics, step=step)

    run.finish()
    print(f"Successfully logged {days} days of historical data to WandB.")


def log_daily(data_dir: Path | None = None):
    """Log yesterday's metrics to WandB."""
    config = get_wandb_config()

    if data_dir:
        df = load_data(data_dir)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            get_slurm_data(tmp_path, days=2)
            df = load_data(tmp_path)

    yesterday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    print(f"Computing metrics for {yesterday.strftime('%Y-%m-%d')}...")

    metrics = compute_daily_metrics(df, yesterday)

    run = wandb.init(
        **config,
        name="daily-metrics",
        resume="allow",
        id="slurm-daily-metrics",
    )

    next_step = run.step + 1 if run.step else 0
    metrics["_timestamp"] = yesterday.timestamp()
    wandb.log(metrics, step=next_step)

    run.finish()

    print(f"Successfully logged metrics for {yesterday.strftime('%Y-%m-%d')} to WandB.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Log SLURM metrics to WandB dashboard")
    parser.add_argument(
        "--rewrite-history-up-to-days",
        type=int,
        metavar="N",
        help="Clear WandB history and rebuild from N days of historical data",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Use existing JSON files from this directory instead of fetching via sacct",
    )
    args = parser.parse_args()

    if args.rewrite_history_up_to_days:
        rewrite_history(args.rewrite_history_up_to_days, args.data_dir)
    else:
        log_daily(args.data_dir)


if __name__ == "__main__":
    main()
