import numpy as np
import pyarrow.compute as pc
import pyarrow.dataset as ds
import typer

from what_works_repo.batch import Batch
from what_works_repo.classify.predict import TextPredictor
from what_works_repo.logging import logger
from what_works_repo.settings import settings


def main(batch_number: int):

    batch = Batch(batch_number)
    predictor = TextPredictor(batch=batch)

    dataset = ds.dataset(
        predictor.prediction_dir, format="parquet", partitioning="hive"
    )

    mult = settings.ml.pred_multiplier
    for thresh in np.arange(10) * 0.1:
        logger.info(f"\n -------------With threshold: {thresh}\n")
        models = []
        filt = None
        for model in settings.ml.pretrained_models:
            models.append(model.label)
            logger.info(models)
            cond = pc.field(model.label) >= int(thresh * mult)
            filt = cond if filt is None else (filt & cond)
            n_kept = dataset.count_rows(filter=filt)
            logger.info(f"Matching filter: {n_kept}")
        logger.info("\n")


if __name__ == "__main__":
    typer.run(main)
