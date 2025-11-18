#!/usr/bin/env python3
"""Monthly SLURM Report Generator"""

import argparse
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import tabulate

from .slurm_analyzer import SLURMAnalyzer


def format_pct_change(current, previous):
    """Format percentage change as a string."""
    if previous == 0 or pd.isna(current) or pd.isna(previous):
        return ""
    pct = ((current - previous) / previous) * 100
    if not pd.isna(pct) and abs(pct) != float("inf"):
        sign = "+" if pct >= 0 else ""
        return f" ({sign}{pct:.0f}%)"
    return ""


def format_time_h_min(hours):
    """Format time in hours to human-readable format (e.g., '1h15', '3h10', '15min', '< 1min')."""
    if pd.isna(hours) or hours == 0:
        return "< 1min"

    total_minutes = hours * 60

    if total_minutes < 1:
        return "< 1min"

    h = int(hours)
    minutes = int(round((hours - h) * 60))

    # Handle rounding edge case where minutes round to 60
    if minutes == 60:
        h += 1
        minutes = 0

    if h > 0:
        if minutes > 0:
            return f"{h}h{minutes:02d}"
        else:
            return f"{h}h"
    else:
        return f"{minutes}min"


def get_slurm_data(output_dir: Path):
    """Fetch SLURM accounting data for the last 60 days."""
    start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

    partitions = [
        ("pli-c", "sacct_pli_core.json"),
        ("pli-lc", "sacct_pli_large_campus.json"),
        ("pli", "sacct_pli_campus.json"),
        ("pli-p", "sacct_pli_p.json"),
    ]

    for partition, filename in partitions:
        print("Fetching data for", partition)
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
        print("Loading data from", filename)
        filepath = data_dir / filename
        if filepath.exists():
            dfs.append(analyzer.parse(json.loads(filepath.read_text())))

    return pd.concat(dfs, ignore_index=True)


def wait_by_partition(df: pd.DataFrame, title: str = ""):
    """Generate a table showing wait times by partition with month-over-month comparison."""
    tab = []
    for partition in ["pli-c", "pli-lc", "pli", "pli-p"]:
        # Last 30 days
        current = df.query(f"partition == '{partition}' and age_days <= 30")
        current_median = current.wait_time_h.median() if len(current) > 0 else 0
        current_long_count = len(current.query("wait_time_h > 6"))
        current_total = len(current)
        current_long_pct = (current_long_count / current_total * 100) if current_total > 0 else 0

        # Previous 30 days (31-60 days ago)
        previous = df.query(f"partition == '{partition}' and age_days > 30 and age_days <= 60")
        previous_median = previous.wait_time_h.median() if len(previous) > 0 else 0
        previous_long_count = len(previous.query("wait_time_h > 6"))
        previous_total = len(previous)
        previous_long_pct = (previous_long_count / previous_total * 100) if previous_total > 0 else 0

        # Format with percentage changes
        tab.append(
            (
                partition,
                f"{format_time_h_min(current_median)}{format_pct_change(current_median, previous_median)}",
                f"{current_long_pct:.1f}%{format_pct_change(current_long_pct, previous_long_pct)}",
                f"{current_total:,}{format_pct_change(current_total, previous_total)}",
            )
        )

    if title:
        print(title)
    print(tabulate.tabulate(tab, headers=["Partition", "Median wait", "jobs with wait > 6h (%)", "Jobs"]))


def utilization_by_partition(df: pd.DataFrame):
    """Print total GPU utilization by partition with month-over-month comparison."""
    print("Total GPU Utilization by Partition (Last 30 Days)")
    tab = []
    for partition in ["pli-c", "pli-lc", "pli", "pli-p"]:
        # Last 30 days
        current = df.query(f"partition == '{partition}' and age_days <= 30")
        current_util = current["gpu_time_h"].sum()
        current_jobs = len(current)

        # Previous 30 days (31-60 days ago)
        previous = df.query(f"partition == '{partition}' and age_days > 30 and age_days <= 60")
        previous_util = previous["gpu_time_h"].sum()
        previous_jobs = len(previous)

        tab.append(
            (
                partition,
                f"{current_util / 1000:,.0f}k{format_pct_change(current_util, previous_util)}",
                f"{current_jobs:,}{format_pct_change(current_jobs, previous_jobs)}",
            )
        )

    print(tabulate.tabulate(tab, headers=["Partition", "GPU h", "Jobs"]))
    print()


def generate_report(df: pd.DataFrame):
    """Generate the complete monthly report with all tables."""
    print("\n" + "=" * 70)
    print(" " * 20 + "SLURM MONTHLY REPORT")
    print("=" * 70 + "\n")

    utilization_by_partition(df)
    wait_by_partition(df.query("gpu_time_h <= 50"), "Wait Times by Partition (Small Jobs, ≤50 GPU hours)")
    print()
    wait_by_partition(df.query("gpu_time_h > 50"), "Wait Times by Partition (Large Jobs, >50 GPU hours)")
    print("\n" + "=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate monthly SLURM usage reports with ASCII tables")
    parser.add_argument(
        "--use-cached-data", action="store_true", help="Use cached JSON files instead of fetching fresh data"
    )
    parser.add_argument(
        "--data-dir", type=Path, default=Path.cwd(), help="Directory for storing/reading JSON data files"
    )
    args = parser.parse_args()

    args.data_dir.mkdir(parents=True, exist_ok=True)

    if not args.use_cached_data:
        get_slurm_data(args.data_dir)

    df = load_data(args.data_dir)
    generate_report(df)


if __name__ == "__main__":
    main()
