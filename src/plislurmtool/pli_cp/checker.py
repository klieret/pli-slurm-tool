import json
import os
import subprocess
from datetime import datetime, timedelta

import yagmail
from dotenv import load_dotenv

from .utils import cancel_job, email_hpgres_cap_canceling, email_hpgres_cap_warning, progress_bar

load_dotenv("local.env")


def date2int(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d-%H:%M:%S").timestamp()


class ResourceChecker:
    def __init__(self, user, qos, quota, rolling_window=30 * 34 * 60):
        self.user = user
        self.rolling_window = rolling_window
        self.qos = qos
        self.quota = quota
        self.yag = yagmail.SMTP(os.getenv("EmailUsername"), os.getenv("Password"))

        # If rolling reset days is set, start time is set to that many days ago
        # Otherwise, start time is set to the first day of the current month
        if self.rolling_window:
            self.start_time = (datetime.now() - timedelta(minutes=rolling_window)).strftime("%Y-%m-%d-%H:%M:%S")
        else:
            self.start_time = datetime.now().replace(day=1).strftime("%Y-%m-%d-00:00:00")

        self.end_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        self.usage = self.fetch_report()

    def fetch_report(self) -> list:
        if self.user == "ALL":
            command = f"sacct --allusers -S {self.start_time} -E {self.end_time} --qos={self.qos} --json"
        else:
            command = f"sacct -u {self.user} -S {self.start_time} -E {self.end_time} --qos={self.qos} --json"
        try:
            output = json.loads(subprocess.check_output(command, shell=True))
        except subprocess.CalledProcessError:
            error_message = f"Error while parsing sacct command {command}"
            raise Exception(error_message)
        return self.parse(output)

    def parse(self, data: dict) -> list:
        """
        Parse the sacct output to get the relevant information
        """

        records = []
        start_time_int = date2int(self.start_time)

        for job in data["jobs"]:
            n_gpus = self.get_n_gpus(job)
            record = {
                "n_gpus": n_gpus,
                "elapsed": job["time"]["elapsed"],
                "start_time": job["time"]["start"],
                "submission_time": job["time"]["submission"],
                "job_name": job["name"],
                "job_id": job["job_id"],
                "limit": job["time"]["limit"]["number"],
            }
            for key in ["qos", "account", "qos", "qos", "user", "allocation_nodes", "state"]:
                record[key] = job[key]

            if record["start_time"] >= start_time_int:
                records.append(record)

        records.sort(key=lambda x: x["start_time"])
        return records

    def get_n_gpus(self, job_data: dict) -> int:
        n_gpus = 0
        for allocation in job_data["tres"]["allocated"]:
            if allocation["type"] == "gres" and allocation["name"] == "gpu":
                n_gpus += int(allocation["count"])
        return n_gpus

    @property
    def active_jobs(self):
        job_ls = []
        for job in self.usage:
            if job["state"]["current"][0] in ["RUNNING", "PENDING"]:
                job_ls.append(job)
        return job_ls

    def get_gpu_hrs(self, start_timestamp: int, end_timestamp: int) -> float:
        return (
            sum(
                [
                    job["elapsed"] * job["n_gpus"]
                    for job in self.usage
                    if (job["start_time"] >= start_timestamp and job["start_time"] <= end_timestamp)
                ]
            )
            / 3600
        )

    def get_quota_forecast(self, total_quota: float, hrs=None) -> str:
        """
        Get the forecast of available quota for future hours
        """

        assert self.rolling_window, "Rolling quota must be enabled to get forecast"
        if hrs is None:
            hrs = [12, 24, 72, 168]

        ret = "Available Quota Forecast:\n"
        for hr_shifted in hrs:
            date_caps = date2int(self.start_time) + 3600 * hr_shifted
            shifted_usage = self.get_gpu_hrs(date_caps, date2int(self.end_time))
            shifted_quota = total_quota - shifted_usage
            ret += f"+{hr_shifted} hrs:  {shifted_quota:.2f} GPU hour\n"
        return ret

    def get_quota_yesterday(self):
        gpu_hours = self.get_gpu_hrs(
            datetime.strptime(self.start_time, "%Y-%m-%d-%H:%M:%S").timestamp(),
            (datetime.now() - timedelta(days=1)).timestamp(),
        )
        return self.quota - gpu_hours

    def usage_report(self, verbose=True):
        start_time = datetime.strptime(self.start_time, "%Y-%m-%d-%H:%M:%S").timestamp()
        end_time = datetime.strptime(self.end_time, "%Y-%m-%d-%H:%M:%S").timestamp()
        gpu_hours = self.get_gpu_hrs(start_time, end_time)

        remaining_hours = self.quota - gpu_hours
        if not verbose:
            return remaining_hours, None

        percentage_used = gpu_hours / self.quota
        pbar = progress_bar(percentage_used)
        report_strs = [
            "\n== PLI High Priority GPU Usage Report ==\n",
            f"User: {self.user}",
            f"qos: {self.qos}",
            f"Cycle Start:\t\t{self.start_time}",
            f"Cycle End:\t\t{self.end_time}",
            f"HP GPU hrs used:\t{gpu_hours:.2f} hours.",
            f"Remaining HP hrs:\t{remaining_hours:.2f} hours.\n",
            f"{pbar}",
        ]

        if percentage_used > 1:
            report_strs.append(
                f"\nWARNING: YOU HAVE EXCEEDED YOUR HP GPU QUOTA!\nJobs submitted to {self.qos} will be automatically CANCELLED."
            )
        if self.rolling_window:
            report_strs.append(
                f"\nQuota of high priority GPU hrs is calculateds over a rolling window of {self.rolling_window // (24*60)} days."
            )
            report_strs.append(self.get_quota_forecast(self.quota))
        else:
            report_strs.append("GPU quota will be reset at the beginning of the next month.")
        # print("\n".join(report_strs))
        return remaining_hours, "\n".join(report_strs)


class ResourceCheckerAdmin(ResourceChecker):
    def __init__(self, qos, quota, monitor_window=30, user_rolling_window=30 * 24 * 60):
        """
        Check the active jobs for all users in the qos recently (default 30 mins)
        """
        super().__init__("ALL", qos, quota, monitor_window)
        self.user_rolling_window = user_rolling_window
        # self.report_usage()

    def usage_monitor(self):
        active_users = set()
        for job in self.active_jobs:
            active_users.add(job["user"])

        if len(active_users) == 0:
            print("No active jobs found")
            return

        for user in list(active_users):
            user_checker = ResourceChecker(user, self.qos, self.quota, self.user_rolling_window)
            user_quota, _ = user_checker.usage_report(verbose=False)
            print(f"User: {user} | Remaining Quota: {user_quota:.2f} GPUhrs")

            if user_quota < 0:
                # If the user has exceeded the quota but still within the grace period
                if user_checker.get_quota_yesterday() >= 0:
                    # send warning email
                    _, user_report = user_checker.usage_report()
                    email_hpgres_cap_warning(user, user_report, user_checker.active_jobs, self.yag)

                # If the user has exceeded the quota and the grace period (1 day) is over
                else:
                    # send canceling email and cancel jobs
                    _, user_report = user_checker.usage_report()
                    email_hpgres_cap_canceling(user, user_report, user_checker.active_jobs, self.yag)
                    for job in user_checker.active_jobs:
                        cancel_job(job["job_id"])

    def fetch_all_users(self):
        command = "sacctmgr list account pli withassoc format=User --json"
        account_meta = json.loads(subprocess.check_output(command, shell=True))
        all_users = []
        for meta in account_meta["accounts"][0]["associations"]:
            if len(meta["user"]) > 0:
                all_users.append(meta["user"])

        return all_users

    def report_usage_stats(self):
        users = self.fetch_all_users()
        usage_ls = []

        for user in list(users):
            user_checker = ResourceChecker(user, self.qos, self.quota, self.user_rolling_window)
            user_quota, _ = user_checker.usage_report(verbose=False)

            used_quota = self.quota - user_quota
            if used_quota > 1e-5:
                usage_ls.append((user, used_quota))

        usage_ls.sort(key=lambda x: x[1], reverse=True)
        # print("== PLI High Priority GPU Usage Report ==\n")
        print(f"\n {'User':10} | Quota Used (cap@{self.quota:.2f})")
        print("======================================")
        for user, quota in usage_ls:
            message = "!Exceeded!" if quota < 0 else ""
            print(f" {user:10} | {quota:.3f} GPUhrs\t{message}")


if __name__ == "__main__":
    user_name = os.environ["USER"]
    user_name = "ALL"
    qos = "pli-cp"
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d-%H:%M:%S")
    end_date = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

    quota = 500
    # checker = ResourceChecker(user_name, qos, quota, rolling_window=30*24*60)
    # checker.usage_report(quota)

    admin_checker = ResourceCheckerAdmin(qos, quota, monitor_window=30, user_rolling_window=30 * 24 * 60)
    admin_checker.usage_monitor()
