# what-works-repo

Active-learning screening pipeline: sample → import to NACSOS → human annotation
→ DEET auto-annotation → resolve → stopping criterion.

## Quick start
uv sync
uv run snakemake          # runs until a manual step is needed, then stops

## Layout
| Path            | What it holds                                            |
|-----------------|----------------------------------------------------------|
| `Snakefile`     | Pipeline definition (the entry point)                    |
| `src/`          | Python package (`what_works_repo`) — all real logic      |
| `config/`       | `.env` and run configuration                             |
| `profiles/`     | Snakemake command-line defaults (auto-loaded)            |
| `data/`         | Inputs & outputs — DVC-tracked, not in git (`data.dvc`)  |
| `deet_projects/`| Per-batch DEET extraction configs & runs                 |
| `docs/`         | mkdocs site (`mkdocs.yml`); see `docs/workflow.md`       |

## Manual steps
The workflow pauses and prints "MANUAL STEP REQUIRED" when it needs a human
(create scope, finalise DEET run, assign docs). Do the step, write the ID to the
named file, and re-run

## Deet project development

Change directory into the deet project

```bash
cd deet_projects/batch_X/
```

Run splits

```bash
deet experiments splits
```

Run experiment, referencing a prompt file and config from another batch

```bash
deet experiments evaluate --config-path ..\batch_1\gpt-luna.yaml --prompt-csv-path ..\batch_1\prompts\260902_prompt_definitions_v1.csv --run-name luna-test
```