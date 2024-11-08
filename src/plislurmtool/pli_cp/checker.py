import json
import os
import subprocess
from datetime import datetime, timedelta

from .utils import cancel_job, email_hpgres_cap_canceling, email_hpgres_cap_warning, progress_bar


def date2int(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d-%H:%M:%S").timestamp()


class ResourceChecker:
    def __init__(self, user, partition, quota, rolling_window=30 * 34 * 60):
        self.user = user
        self.rolling_window = rolling_window
        self.partition = partition
        self.quota = quota

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
            command = f"sacct --allusers -S {self.start_time} -E {self.end_time} --partition={self.partition} --json"
        else:
            command = (
                f"sacct -u {self.user} -S {self.start_time} -E {self.end_time} --partition={self.partition} --json"
            )
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
            for key in ["qos", "account", "partition", "qos", "user", "allocation_nodes", "state"]:
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
            "== PLI High Priority GPU Usage Report ==\n",
            f"User: {self.user}",
            f"Partition: {self.partition}",
            f"Cycle Start:\t\t{self.start_time}",
            f"Cycle End:\t\t{self.end_time}",
            f"HP GPU hrs used:\t{gpu_hours:.2f} hours.",
            f"Remaining HP hrs:\t{remaining_hours:.2f} hours.\n",
            f"{pbar}",
        ]

        if percentage_used > 1:
            report_strs.append(
                f"\nWARNING: YOU HAVE EXCEEDED YOUR HP GPU QUOTA!\nJobs submitted to {self.partition} will be automatically CANCELLED."
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
    def __init__(self, partition, quota, monitor_window=30, user_rolling_window=30 * 24 * 60):
        """
        Check the active jobs for all users in the partition recently (default 30 mins)
        """
        super().__init__("ALL", partition, quota, monitor_window)
        self.user_rolling_window = user_rolling_window

    def usage_monitor(self):
        active_users = set()
        for job in self.active_jobs:
            active_users.add(job["user"])

        for user in list(active_users):
            user_checker = ResourceChecker(user, self.partition, self.quota, self.user_rolling_window)
            user_quota, _ = user_checker.usage_report(verbose=False)
            print(f"User: {user} | Remaining Quota: {user_quota:.2f} GPUhrs")

            if user_quota < 0:
                # If the user has exceeded the quota but still within the grace period
                if user_checker.get_quota_yesterday() >= 0:
                    # send warning email
                    _, user_report = user_checker.usage_report()
                    email_hpgres_cap_warning(user, user_report, user_checker.active_jobs)

                # If the user has exceeded the quota and the grace period (1 day) is over
                else:
                    # send canceling email and cancel jobs
                    _, user_report = user_checker.usage_report()
                    email_hpgres_cap_canceling(user, user_report, user_checker.active_jobs)
                    for job in user_checker.active_jobs:
                        cancel_job(job["job_id"])


if __name__ == "__main__":
    user_name = os.environ["USER"]
    user_name = "ALL"
    partition = "pli-c"
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d-%H:%M:%S")
    end_date = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")

    quota = 500
    # checker = ResourceChecker(user_name, partition, quota, rolling_window=30*24*60)
    # checker.usage_report(quota)

    admin_checker = ResourceCheckerAdmin(partition, quota, monitor_window=30, user_rolling_window=30 * 24 * 60)
    admin_checker.usage_monitor()
