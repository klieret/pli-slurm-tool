# SLURM Monthly Reports

This module provides tools for generating monthly SLURM usage reports with ASCII tables.

## Usage

### Generate a fresh report (fetches new data)

```bash
# Using the main CLI
pli-slurm-tool monthly-report

# Or run the module directly
python -m plislurmtool.reports.monthly_report
```

### Using cached data

If you already have the JSON data files and want to skip fetching fresh data:

```bash
pli-slurm-tool monthly-report --use-cached-data
```

### Specify a custom data directory

By default, JSON files are saved to/read from the current working directory. You can specify a different location:

```bash
pli-slurm-tool monthly-report --data-dir /path/to/data/directory
```

## Data Files

The script fetches data from three SLURM partitions and saves them as JSON files:

- `sacct_pli_core.json` - Data from pli-c partition
- `sacct_pli_campus.json` - Data from pli partition  
- `sacct_pli_large_campus.json` - Data from pli-lc partition

## Report Contents

The monthly report includes:

1. **Total GPU Utilization by Partition** - Total GPU hours used in each partition
2. **Wait Times by Partition (Small Jobs)** - Jobs with ≤23 GPU hours
3. **Wait Times by Partition (Large Jobs)** - Jobs with >23 GPU hours
4. **Wait Times by Period** - Average wait times for last 7 and 30 days

## Requirements

The script requires:
- SLURM `sacct` command available (for fetching fresh data)
- Python packages: `pandas`, `tabulate`
- Access to SLURM accounting data for the partitions

## Data Collection

The script collects data from the last 90 days using the following command pattern:

```bash
sacct -S <start_date> --partition <partition_name> --allusers --json
```

## Example Output

```
======================================================================
                    SLURM MONTHLY REPORT
======================================================================
Report generated: 2025-11-17 10:30:00
Total jobs analyzed: 15432
======================================================================

Total GPU Utilization by Partition
==================================================
  pli-c     :    1234k hours
  pli-lc    :     567k hours
  pli       :     890k hours

Wait Times by Partition (Small Jobs, ≤23 GPU hours)
Partition    Avg. wait (h)    jobs with wait > 24h    Jobs
-----------  ---------------  ----------------------  ------
pli-c                    4.5                     123    5432
pli-lc                   8.2                     234    3210
pli                      6.7                     189    4567

Wait Times by Partition (Large Jobs, >23 GPU hours)
Partition    Avg. wait (h)    jobs with wait > 24h    Jobs
-----------  ---------------  ----------------------  ------
pli-c                   12.3                     456    1234
pli-lc                  18.5                     567     987
pli                     15.4                     432    1002

Wait Times by Period (All Jobs)
Period          Avg. wait (h)    jobs with wait > 24h    Jobs
--------------  ---------------  ----------------------  ------
Last 7 days               5.6                     234    3210
Last 30 days              7.8                     987    8765

======================================================================
```

