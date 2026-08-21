import typer

from what_works_repo.batch import Batch
from what_works_repo.logging import logger


def main(batch_n: int):
    batch = Batch(batch_n)
    logger.info(batch)
    batch.stopping_decision.write_text(f"{0.1}")
    pass


if __name__ == "__main__":
    typer.run(main)
