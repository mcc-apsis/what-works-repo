import typer
from deet.ui.terminal.wizards import run_model_wizard

from what_works_repo.batch import Batch
from what_works_repo.configurations import NextBatchConfig


def main(batch_n: int):
    batch = Batch(batch_n)
    next_batch_config = run_model_wizard(NextBatchConfig)
    batch.next_batch_config_path.write_text(next_batch_config.model_dump_json(indent=2))


if __name__ == "__main__":
    typer.run(main)
