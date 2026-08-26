import typer

from what_works_repo.batch import Batch


def main(batch_number: int):
    """Train a model for a batch"""
    batch = Batch(batch_number)
    next_batch_config = batch.next_batch_config
    print(next_batch_config)
    if next_batch_config.use_pretrained_models:
        batch.model.write_text("Model complete")
    else:
        # TODO Implement training
        raise NotImplementedError("Training a new model not yet implemented")


if __name__ == "__main__":
    typer.run(main)
