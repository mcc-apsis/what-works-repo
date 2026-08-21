from typing import cast
from pathlib import Path
import typer
from transformers import pipeline

from what_works_repo.batch import Batch
from what_works_repo.constants import RAW_DATA
from what_works_repo.settings import settings


class TextPredictor:
    def __init__(self):
        self.included_ids = []
        return

    def predict_pretrained_model(
        self, texts: list[str], model_name: str, label_name: str
    ) -> list[float]:
        """Use model `model_name` to make predictions of label `label_name` for each text in `texts`."""
        classifier = pipeline("text-classification", model=model_name, top_k=None)
        results = cast(
            list[list[dict[str, float]]],
            classifier(texts, truncation=True, max_length=512),
        )
        return [
            next(r["score"] for r in doc if r["label"] == label_name) for doc in results
        ]

    def predict_prioritisation_model(self, texts: list[str]):
        # TODO Implement training and loading trained model
        raise NotImplementedError(
            "Training a new model not yet implemented. Cannot load model."
        )

    def predict(self, texts: list[str]):
        if settings.ml.train_model:
            y_pred = self.predict_prioritisation_model(texts)
        else:
            if not settings.ml.pretrained_models:
                raise ValueError(
                    "Training mode is off but no pretrained models supplied"
                )
            for model in settings.ml.pretrained_models:
                y_pred = self.predict_pretrained_model(
                    texts=texts, model_name=model.name, label_name=model.label
                )

    def process_batches(self, batch_dir: Path = Path(RAW_DATA)) -> None:
        for 


def main(batch_number: int):
    """Train a model for a batch"""
    batch = Batch(batch_number)


if __name__ == "__main__":
    typer.run(main)
