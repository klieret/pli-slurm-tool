import argparse
import os
from pathlib import Path

from .pli_cp import ResourceChecker, ResourceCheckerAdmin
from .reports import monthly_report, wandb_dashboard


def pli_pc_check_quota(quota: int, rolling_window: int):
    """
    Checks the resource usage quota for the current user on pli-pc partition.
    This function initializes a ResourceChecker object with the current user's
    environment, a specified partition, quota limit, and rolling window period.
    It then generates a usage report and prints the message.
    """
    rc = ResourceChecker(
        user=os.environ["USER"],
        qos="pli-cp",
        quota=quota,  # To be finalized
        rolling_window=rolling_window,
    )
    _, message = rc.usage_report(verbose=True)
    print(message)


def pli_pc_monitor_admin(quota: int, monitor_window: int, rolling_window: int):
    """
    Monitors the resource usage quota for all users on pli-pc partition.
    Intended for admin use only. Should be run periodically to check the current job queue.
    """
    rc = ResourceCheckerAdmin(
        qos="pli-cp",
        quota=quota,  # To be finalized
        monitor_window=monitor_window,
        user_rolling_window=rolling_window,
    )
    rc.usage_monitor()


def pli_pc_monitor_admin_report(quota: int, monitor_window: int, rolling_window: int):
    """
    Monitors the resource usage quota for all users on pli-cp partition.
    """
    rc = ResourceCheckerAdmin(
        qos="pli-cp",  # TODO: Change to pli-pc when online
        quota=quota,  # To be finalized
        monitor_window=monitor_window,
        user_rolling_window=rolling_window,
    )
    rc.report_usage_stats()


def main():
    parser = argparse.ArgumentParser(description="PLI Slurm Tool")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--quota",
        type=int,
        default=500,  # To be finalized
        help="Quota limit",
    )
    parent_parser.add_argument(
        "--monitor_window",
        type=int,
        default=30,  # run the checker every 30 mins
        help="Monitor window in minutes",
    )
    parent_parser.add_argument(
        "--rolling_window",
        type=int,
        default=30 * 24 * 60,  # 30 days
        help="(User) rolling window in minutes",
    )

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("cp-quota-check", help="Check quota for PLI-CP QOS", parents=[parent_parser])
    subparsers.add_parser("cp-monitor-admin", help="Admin monitoring for PLI-CP QOS", parents=[parent_parser])
    subparsers.add_parser("cp-quota-report-admin", help="Admin quota for PLI-CP QOS", parents=[parent_parser])

    # Monthly report subcommand
    monthly_parser = subparsers.add_parser("monthly-report", help="Generate monthly SLURM usage report")
    monthly_parser.add_argument(
        "--use-cached-data", action="store_true", help="Use cached JSON files instead of fetching fresh data"
    )
    monthly_parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory for storing/reading JSON data files (default: current directory)",
    )

    # WandB dashboard subcommand
    wandb_parser = subparsers.add_parser(
        "wandb-dashboard", help="Log SLURM metrics to WandB dashboard (requires wandb optional dependency)"
    )
    wandb_parser.add_argument(
        "--rewrite-history-up-to-days",
        type=int,
        metavar="N",
        help="Clear WandB history and rebuild from N days of historical data",
    )
    wandb_parser.add_argument(
        "--data-dir",
        type=Path,
        help="Use existing JSON files from this directory instead of fetching via sacct",
    )

    args = parser.parse_args()

    if args.command == "cp-quota-check":
        pli_pc_check_quota(args.quota, args.rolling_window)
    elif args.command == "cp-monitor-admin":
        pli_pc_monitor_admin(args.quota, args.monitor_window, args.rolling_window)
    elif args.command == "cp-quota-report-admin":
        pli_pc_monitor_admin_report(args.quota, args.monitor_window, args.rolling_window)
    elif args.command == "monthly-report":
        # Pass through to monthly report module
        import sys

        sys.argv = ["monthly-report"]
        if args.use_cached_data:
            sys.argv.append("--use-cached-data")
        sys.argv.extend(["--data-dir", str(args.data_dir)])
        exit(monthly_report.main())
    elif args.command == "wandb-dashboard":
        if args.rewrite_history_up_to_days:
            wandb_dashboard.rewrite_history(args.rewrite_history_up_to_days, args.data_dir)
        else:
            wandb_dashboard.log_daily(args.data_dir)
    else:
        print("No command provided. Use -h for help.")


if __name__ == "__main__":
    main()
