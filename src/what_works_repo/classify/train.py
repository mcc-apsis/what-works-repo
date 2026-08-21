import typer

from what_works_repo.batch import Batch
from what_works_repo.settings import settings


def main(batch_number: int):
    """Train a model for a batch"""
    batch = Batch(batch_number)
    if settings.ml.train_model:
        # TODO Implement training
        raise NotImplementedError("Training a new model not yet implemented")
    else:
        batch.model.write_text("Model complete")


if __name__ == "__main__":
    typer.run(main)
