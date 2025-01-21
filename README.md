# pli-slurm-tool

Script to monitor PLI partitions of the Princeton clusters

## Usage

Install the pipx package in your environment: e.g. `pip install pipx`.

```bash
# User-level quota checking for PLI-CP QoS
pipx run pli-slurm-tool cp-quota-check`
```

## Admin usage

* Admin-level quota management for PLI-CP QoS `pipx run pli-slurm-tool cp-monitor-admin` (to be executed every ~30 mins)
* Admin-level usage stats for PLI-CP QoS `pipx run pli-slurm-tool cp-quota-report-admin`

Please add gmail username and app password to your system environment variables to enable email notifications to users:

```bash
export EmailUsername=XXX
export Password=XXX
```

## Development setup

```bash
pip install pre-commit
pre-commit install
pip install --editable .
```

In order to release a new version

1. Bump version (you cannot overwrite pypi versions)
2. Add tag `git tag v1.0.0`
3. Push `git push && git push origin v1.0.0`
4. `rm -r dist/** && python -m build`
5. `pipx run twine check dist/**`
6. `pipx run twine upload dist/**`

Ask Kilian for API key
