# pli-slurm-tool

Script to monitor PLI partitions of the Princeton clusters

## Install

Install the pipx package in your environment: e.g. `pip install pipx`.

## How to Use

* User-level quota checking for PLI-CP QoS: `pipx run pli-slurm-tool cp-quota-check`
* Admin-level quota management for PLI-CP QoS `pipx run pli-slurm-tool cp-monitor-admin` (to be executed every ~30 mins)
* Admin-level usage stats for PLI-CP QoS `pipx run pli-slurm-tool cp-quota-report-admin`

## Admin usage
Please add gmail username and app password to your system environment variables to enable email notifications to users:
```
export EmailUsername=XXX
export Password=XXX
```

## Development setup

```
pip install pre-commit
pre-commit install
pip install --editable .
```
