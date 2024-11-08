import argparse
import os

from .pli_cp import ResourceChecker, ResourceCheckerAdmin


def pli_pc_check_quota():
    """
    Checks the resource usage quota for the current user on pli-pc partition.
    This function initializes a ResourceChecker object with the current user's
    environment, a specified partition, quota limit, and rolling window period.
    It then generates a usage report and prints the message.
    """
    rc = ResourceChecker(
        user=os.environ["USER"],
        partition="pli-c",  # TODO: Change to pli-pc when online
        quota=500,  # To be finalized
        rolling_window=30 * 24 * 60,  # 30 days
    )
    _, message = rc.usage_report(verbose=True)
    print(message)


def pli_pc_monitor_admin():
    """
    Monitors the resource usage quota for all users on pli-pc partition.
    Intended for admin use only. Should be run periodically to check the current job queue.
    """
    rc = ResourceCheckerAdmin(
        partition="pli-c",  # TODO: Change to pli-pc when online
        quota=500,  # To be finalized
        monitor_window=30,  # run the checker every 30 mins
        user_rolling_window=30 * 24 * 60,  # 30 days
    )
    rc.usage_monitor()


def main():
    parser = argparse.ArgumentParser(description="PLI Slurm Tool")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("cp-quota-check", help="Check quota")
    subparsers.add_parser("cp-quota-check-admin", help="Admin quota check")
    args = parser.parse_args()

    if args.command == "cp-quota-check":
        pli_pc_check_quota()
    elif args.command == "cp-quota-check-admin":
        pli_pc_monitor_admin()
    else:
        print("No command provided. Use -h for help.")


if __name__ == "__main__":
    main()
