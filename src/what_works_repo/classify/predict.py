import json
from pathlib import Path
from typing import cast

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import typer
from nacsos_data.util.academic.apis.scopus import ScopusAPI
from transformers import pipeline

from what_works_repo.batch import Batch
from what_works_repo.constants import PREDICTION_DIR, RAW_DATA
from what_works_repo.logging import logger
from what_works_repo.settings import settings


class TextPredictor:
    def __init__(self):
        self.included_ids = []
        return

    @property
    def prediction_dir(self):
        if settings.ml.train_model:
            # FIXME: should we have a new dir for each batch?
            # or should we be able to configure whether to do this?
            return PREDICTION_DIR / "prioritisation"
        else:
            model_names = [
                model.name.replace("/", "-") for model in settings.ml.pretrained_models
            ]
            return PREDICTION_DIR / "_".join(model_names)

    def save_predictions_file(
        self, df: pd.DataFrame, prediction_cols: list[str]
    ) -> None:
        for col in prediction_cols:
            df[col] = (df[col] * settings.ml.pred_multiplier).astype(
                settings.ml.pred_dtype
            )
        pq.write_to_dataset(
            pa.Table.from_pandas(df),
            root_path=self.prediction_dir,
            partition_cols=["batch_file"],
        )

    def predict_pretrained_model(
        self, texts: list[str], model_name: str, label_name: str
    ) -> list[float]:
        """
        Make predictions using pretrained models.

        Use model `model_name` to make predictions of label `label_name`
        for each text in `texts`.
        """
        classifier = pipeline("text-classification", model=model_name, top_k=None)
        results = cast(
            list[list[dict[str, float]]],
            classifier(texts, truncation=True, max_length=512),
        )
        logger.debug(f"First 2 results: {results[:2]}")
        logger.debug(f"Looking for label: {label_name}")
        scores = [
            next(r["score"] for r in doc if r["label"] == label_name) for doc in results
        ]
        logger.debug(f"Unique scores: {set(scores)}")
        return scores

    def predict_prioritisation_model(self, texts: list[str]) -> pd.DataFrame:
        # TODO Implement training and loading trained model
        raise NotImplementedError(
            "Training a new model not yet implemented. Cannot load model."
        )

    def predict(self, texts: list[str]) -> pd.DataFrame:
        if settings.ml.train_model:
            pred_df = self.predict_prioritisation_model(texts)
        else:
            if not settings.ml.pretrained_models:
                raise ValueError(
                    "Training mode is off but no pretrained models supplied"
                )
            pred_df = pd.DataFrame({"text": texts})
            pred_mask = pred_df["text"].str.contains(r"\w", na=False)
            for model in settings.ml.pretrained_models:
                logger.info(f"Making predictions with {model.name}")
                if pred_mask.sum() == 0:
                    logger.warning("No valid texts")
                    break
                y_pred = self.predict_pretrained_model(
                    texts=pred_df.loc[pred_mask, "text"].tolist(),
                    model_name=model.name,
                    label_name=model.label,
                )
                pred_df.loc[pred_mask, model.label] = y_pred
                if settings.ml.triage_predictions:
                    pred_mask &= pred_df[model.label] > model.threshold

        return pred_df

    def process_batches(
        self, skip_ids: list[str], batch_dir: Path = Path(RAW_DATA)
    ) -> None:
        logger.info("Processing batches")
        for jsonl_file in sorted(batch_dir.glob("*.jsonl")):
            records = []
            with jsonl_file.open() as f:
                partition_dir = self.prediction_dir / f"batch_file={jsonl_file.name}"
                sentinel = partition_dir / "_SUCCESS"
                if sentinel.exists():
                    logger.info(
                        f"Skipping {jsonl_file.name}, predictions already exist"
                    )
                    continue
                records = [
                    data
                    for line in f
                    if (data := ScopusAPI.translate_record(json.loads(line)))
                    and data.scopus_id not in skip_ids
                ]
                texts = [(row.title or "") + " " + (row.text or "") for row in records]
                logger.info(f"Predicting {len(records)} records from {jsonl_file}")
                pred_df = self.predict(texts)
                pred_df["batch_file"] = jsonl_file.name
                self.save_predictions_file(
                    pred_df, [model.label for model in settings.ml.pretrained_models]
                )
                sentinel.touch()


def main(batch_number: int):
    """Train a model for a batch"""
    batch = Batch(batch_number)
    logger.info(f"Running prediction for batch {batch.number}")
    predictor = TextPredictor()
    predictor.process_batches(skip_ids=[])


if __name__ == "__main__":
    typer.run(main)
