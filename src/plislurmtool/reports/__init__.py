"""SLURM reporting and analysis tools."""

from .monthly_report import main as monthly_report_main
from .slurm_analyzer import SLURMAnalyzer

__all__ = ["SLURMAnalyzer", "monthly_report_main"]
