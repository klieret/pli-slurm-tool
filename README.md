# pli-slurm-tool

Script to monitor PLI partitions of the Princeton clusters

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
