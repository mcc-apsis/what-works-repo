import asyncio
import datetime
import uuid
from pathlib import Path

import pandas as pd
import typer
from deet.data_models.project import DeetProject, ExperimentArtefacts
from nacsos_data.db import get_engine_async
from nacsos_data.db.crud.annotations import (
    store_assignments,
    upsert_assignment_scope,
)
from nacsos_data.models.annotations import (
    AssignmentModel,
    AssignmentScopeModel,
    AssignmentStatus,
)

from what_works_repo.batch import Batch
from what_works_repo.constants import DEET_RUN_SKIP, DEET_SCOPE_SENTINEL
from what_works_repo.deet_orchestration.deet_annotation_configuration import (
    DeetAnnotationConfig,
)
from what_works_repo.deet_orchestration.deet_annotator import DeetAnnotator
from what_works_repo.logging import logger
from what_works_repo.settings import settings


def resolve_deet_experiment(
    run_id: str, deet_project_config: Path
) -> ExperimentArtefacts:
    """Resolve a deet project and run id (stored in a text file) to an experiment."""
    project = DeetProject.load(project_dir=deet_project_config.parent)
    experiment = ExperimentArtefacts(base_dir=project.experiments_dir / run_id)
    if not experiment.is_complete:
        raise ValueError
    return experiment


def annotate(annotator: DeetAnnotator, annotation_df: pd.DataFrame) -> pd.DataFrame:
    """
    Annotate documents in dataframe
    """
    incl_values = []
    reasoning_values = []

    for _, row in annotation_df.iterrows():
        text = (row["name"] or "") + " " + (row["abstract"] or "")
        deet_annotations = annotator.predict(text)

        deet_value, reasoning = next(
            (ann.output_data, ann.reasoning)
            for ann in deet_annotations
            if ann.attribute.attribute_label == settings.nacsos.inclusion_key
        )

        incl_values.append(bool(deet_value))
        reasoning_values.append(reasoning or "")

    annotation_df["incl"] = incl_values
    annotation_df["reasoning"] = reasoning_values

    return annotation_df


async def assign_deet_verification_scope(
    predicted_positive_ids: list[str], scheme_id: str, scope_name: str
) -> str:
    """
    Assign predicted positives to users defined in config.

    If either the list of users is empty, or there are no predicted positives,
    return a sentinel.

    Else, create a new assignment scope, and create assignments splitting
    predicted positives across users.
    """
    if not predicted_positive_ids or not settings.nacsos.deet_check_users:
        return DEET_SCOPE_SENTINEL
    db_engine = get_engine_async("config/.env")

    new_scope_id = uuid.uuid4()
    scope = AssignmentScopeModel(
        assignment_scope_id=new_scope_id,
        annotation_scheme_id=scheme_id,
        name=f"{scope_name}__human_resolution",
        description="Human review of deet-predicted positives",
    )
    await upsert_assignment_scope(scope, db_engine)

    new_assignments = [
        AssignmentModel(
            assignment_id=uuid.uuid4(),
            assignment_scope_id=new_scope_id,
            user_id=user_id,
            item_id=item_id,
            annotation_scheme_id=scheme_id,
            status=AssignmentStatus.OPEN,
        )
        for item_id in predicted_positive_ids
        for user_id in settings.nacsos.deet_check_users
    ]
    await store_assignments(
        db_engine=db_engine, assignments=new_assignments, use_commit=True
    )
    return str(new_scope_id)


async def get_items_to_annotate(
    annotation_config: DeetAnnotationConfig,
) -> pd.DataFrame:
    """From all unassigned documents, return a dataframe of documents.

    dataframe should have columns
     - document_id (scopus id),
     - name (title)
     - abstract (abstract)
    """
    from nacsos_data.db.schemas import AcademicItem, Assignment
    from sqlalchemy import exists, select

    db_engine = get_engine_async("config/.env")

    async with db_engine.session() as session:
        # Get academic items in project with no assignments
        stmt = (
            select(
                AcademicItem.scopus_id,
                AcademicItem.title,
                AcademicItem.text,
                AcademicItem.item_id,
            )
            .where(
                AcademicItem.project_id == settings.nacsos.project_id,
                ~exists(select(1).where(Assignment.item_id == AcademicItem.item_id)),
            )
            .limit(annotation_config.n_annotations)
        )
        rows = await session.execute(stmt)

        df = pd.DataFrame(rows, columns=["document_id", "name", "abstract", "item_id"])

    return df


def get_items_to_resolve(
    annotated_df: pd.DataFrame, annotation_config: DeetAnnotationConfig
) -> list[str]:
    """
    Given an annotated df, return the list of documents to resolve.

    Resolution configuration is set in `annotation_config`.
    """
    items_to_resolve = []
    if annotation_config.check_negatives:
        items_to_resolve.extend(annotated_df[~annotated_df["incl"]]["item_id"].tolist())
    if annotation_config.check_positives:
        items_to_resolve.extend(annotated_df[annotated_df["incl"]]["item_id"].tolist())
    return items_to_resolve


async def _main(
    annotator: DeetAnnotator, annotation_config: DeetAnnotationConfig, batch: Batch
) -> None:
    to_annotate = await get_items_to_annotate(annotation_config)
    logger.info(f"{len(to_annotate)} items to annotate.")
    annotated_df = annotate(annotator, to_annotate)
    annotated_df.to_csv(batch.deet_annotations, index=False)
    items_to_resolve = get_items_to_resolve(annotated_df, annotation_config)

    today = datetime.date.today()
    scope_name = f"{today.strftime('%Y_%m_%d')}_deet_batch_{batch.number}"

    new_scope_id = await assign_deet_verification_scope(
        items_to_resolve, settings.nacsos.scheme_id, scope_name
    )
    batch.deet_resolution_scope.write_text(new_scope_id)


def main(
    batch_number: int,
):
    """
    Annotate documents with deet.

    Take documents from items. Annotate with deet, using the configuration
    read from the overall deet project config, and the annotation config.

    Create a new scope with assignments to human users,
        as specified in annotation config.
    """
    batch = Batch(batch_number)
    annotation_config = DeetAnnotationConfig.model_validate_json(
        batch.deet_annotation_config.read_text()
    )
    if (
        annotation_config.deet_run == DEET_RUN_SKIP
        or annotation_config.n_annotations < 1
    ):
        batch.deet_annotation_config.write_text("document_id,name,abstract,incl\n")
        batch.deet_resolution_scope.write_text(DEET_SCOPE_SENTINEL)
        return

    experiment = resolve_deet_experiment(annotation_config.deet_run, batch.deet_config)
    annotator = DeetAnnotator(experiment=experiment)
    asyncio.run(
        _main(annotator=annotator, annotation_config=annotation_config, batch=batch)
    )


if __name__ == "__main__":
    typer.run(main)
