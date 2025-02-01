import argparse
import os
import json
import threading

from .pli_cp import ResourceChecker, ResourceCheckerAdmin


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


def pli_lc_monitor_admin(monitor_window: int, file_path:str):
    """
    Monitors the resource usage quota for a specific account on pli-lc partition.
    The quota is defined over a specific timeline. 
    Intended for admin use only. Should be run periodically to check the current job queue.
    """
    def _read_data():
        with threading.Lock():
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                return data
            except (IOError, json.JSONDecodeError) as e:
                print(f"Failed to read JSON file at {file_path}: {e}")
                raise
    
    if not os.path.exists(file_path):
        raise f"JSON file found at {file_path}."
    
    mapping_account2quota = _read_data()

    for account in mapping_account2quota["accounts"]:
        rc = ResourceCheckerAdmin(
            qos=account["qos"],
            quota=account["quota"],
            monitor_window=monitor_window,
            start_date = account["start_date"],
            account = account["account"]
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
    parent_parser.add_argument(
        "--path_to_mapping",
        type=str,
        default=30 * 24 * 60,  # 30 days
        help="Path to JSON file that contains mapping of quota/users in PLI-LC",
    )    

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("cp-quota-check", help="Check quota for PLI-CP QOS", parents=[parent_parser])
    subparsers.add_parser("cp-monitor-admin", help="Admin monitoring for PLI-CP QOS", parents=[parent_parser])
    subparsers.add_parser("cp-quota-report-admin", help="Admin quota for PLI-CP QOS", parents=[parent_parser])
    subparsers.add_parser("lc-monitor-admin", help="Admin quota for PLI-LC QOS", parents=[parent_parser])

    args = parser.parse_args()

    if args.command == "cp-quota-check":
        pli_pc_check_quota(args.quota, args.rolling_window)
    elif args.command == "cp-monitor-admin":
        pli_pc_monitor_admin(args.quota, args.monitor_window, args.rolling_window)
    elif args.command == "cp-quota-report-admin":
        pli_pc_monitor_admin_report(args.quota, args.monitor_window, args.rolling_window)
    elif args.command == "lc-monitor-admin":
        pli_lc_monitor_admin(args.monitor_window, args.path_to_mapping)
    else:
        print("No command provided. Use -h for help.")


if __name__ == "__main__":
    main()
