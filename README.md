# pli-slurm-tool

Script to monitor PLI partitions of the Princeton clusters

## Install
1. Install pipx package in your environment: e.g. `pip install pipx`
2. Clone the repo and run `pipx install ./pli-slurm-tool`
3. `pli-slurm-tool` can be called everywhere.

## How to Use
* User-level quota checking for PLI-CP QoS: `pli-slum-tool cp-quota-check`
* Admin-level quota management for PLI-CP QoS `pli-slum-tool cp-monitor-admin` (to be executed every ~30 mins)
* Admin-level usage stats for PLI-CP QoS `pli-slum-tool cp-quota-report-admin`

## Development setup

```
pip install pre-commit
pre-commit install
pip install --editable .
```
