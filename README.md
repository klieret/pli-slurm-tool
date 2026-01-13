# pli-slurm-tool

Script to monitor PLI partitions of the Princeton clusters

Pypi: https://pypi.org/project/pli-slurm-tool/

## Usage

Install the pipx package in your environment: e.g. `pip install pipx`.

```bash
# User-level quota checking for PLI-CP QoS
pipx run pli-slurm-tool cp-quota-check
```

## Admin usage

* Admin-level quota management for PLI-CP QoS `pipx run pli-slurm-tool cp-monitor-admin` (to be executed every ~30 mins)
* Admin-level usage stats for PLI-CP QoS `pipx run pli-slurm-tool cp-quota-report-admin`

Please add gmail username and app password to your system environment variables to enable email notifications to users:

```bash
export EmailUsername=XXX
export Password=XXX
```

## WandB Dashboard

The `wandb-dashboard` command logs daily SLURM metrics to Weights & Biases for visualization and tracking.

### Installation

Install with the `wandb` optional dependency:

```bash
pip install pli-slurm-tool[wandb]
```

### Environment Variables

The following environment variables configure the WandB dashboard. These can be set directly or in a `.env` file in the current directory:

| Variable | Required | Description |
|----------|----------|-------------|
| `WANDB_API_KEY` | Yes | Your WandB API key |
| `WANDB_PROJECT` | No | Project name (default: `pli-slurm-dashboard`) |
| `WANDB_ENTITY` | No | WandB team/entity name |

Example `.env` file:

```bash
WANDB_API_KEY=your-api-key-here
WANDB_PROJECT=pli-slurm-dashboard
WANDB_ENTITY=your-team-name
```

### Usage

Log yesterday's metrics (intended for daily cron job):

```bash
pli-slurm-tool wandb-dashboard
```

Rewrite history for the last N days (clears existing data and rebuilds):

```bash
pli-slurm-tool wandb-dashboard --rewrite-history-up-to-days 30
```

### Metrics Tracked

For each partition (pli-c, pli-lc, pli, pli-p):
- GPU hours (total)
- Job count
- Median wait time (hours)
- Long wait percentage (jobs with wait > 6h)

Metrics are also split by job size:
- Small jobs: ≤50 GPU hours
- Large jobs: >50 GPU hours

## Development setup

```bash
pip install pre-commit
pre-commit install
pip install --editable .
```

In order to release a new version

1. Increment version in `src/plislurmtool/__init__.py` and push it as a commit
2. Use the github UI to create a new release (use tag `v<VERSION>`, e.g., `v1.0.0`)

Alternatively, here are the manual steps

1. Increment version as above
2. Add tag `git tag v1.0.0`
3. Push `git push && git push origin v1.0.0`
4. `rm -r dist/** && python -m build`
5. `pipx run twine check dist/**`
6. `pipx run twine upload dist/**`

Ask Kilian for API key
