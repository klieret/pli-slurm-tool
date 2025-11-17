from datetime import datetime

import pandas as pd
from pandas import DataFrame as DF


class SLURMAnalyzer:
    def parse(self, data: dict) -> DF:
        records = []
        for job in data["jobs"]:
            n_gpus = self._get_n_gpus(job)
            record = {
                "n_gpus": n_gpus,
                "elapsed": job["time"]["elapsed"],
                "start_time": job["time"]["start"],
                "submission_time": job["time"]["submission"],
                "job_name": job["name"],
                "limit": job["time"]["limit"]["number"],
            }
            for key in ["qos", "account", "partition", "qos", "user", "allocation_nodes"]:
                record[key] = job[key]
            records.append(record)
        df = pd.DataFrame.from_records(records)
        self._augment_df(df)
        return self._sanity_filter(df)

    @staticmethod
    def _get_n_gpus(job_data: dict) -> int:
        n_gpus = 0
        for allocation in job_data["tres"]["allocated"]:
            if allocation["type"] == "gres" and allocation["name"] == "gpu":
                n_gpus += int(allocation["count"])
        return n_gpus

    @staticmethod
    def _augment_df(df: DF) -> None:
        df["gpu_time"] = df["n_gpus"] * df["elapsed"]
        df["wait_time"] = df["start_time"] - df["submission_time"]
        for c in ["start_time", "submission_time"]:
            df[c] = pd.to_datetime(df[c], unit="s")
        df["wait_time_h"] = df["wait_time"] / 3600
        df["gpu_time_h"] = df["gpu_time"] / 3600
        df["submission_hour"] = df["submission_time"].dt.hour
        df["age_days"] = -(df.start_time - datetime.now()).dt.days
        df["elapsed_h"] = df["elapsed"] / 3600

    @staticmethod
    def _sanity_filter(df: DF) -> DF:
        def mask(df, name: str, query: str):
            n_before = len(df)
            df = df.query(query)
            n_after = len(df)
            n_filtered = n_before - n_after
            frac_filtered = n_filtered / n_before
            if n_before != n_after:
                print(f"Filtered {n_before - n_after} jobs ({100 * frac_filtered:.0f}%) with {name}")
            return df

        df = mask(df, "no gpus", "n_gpus > 0")
        df = mask(df, "< 10min run time", "elapsed > 600")
        return mask(df, "wait time > 1 month", "wait_time < 3600*24*31")
