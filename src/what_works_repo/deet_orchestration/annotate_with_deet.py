import asyncio
import uuid
from pathlib import Path
from typing import cast

import typer
from deet.data_models.project import DeetProject, ExperimentArtefacts
from nacsos_data.db import get_engine_async
from nacsos_data.db.crud.annotations import (
    read_annotation_scheme_for_scope,
    read_annotations_for_assignment,
    read_assignment_scope,
    read_assignments_for_scope,
    store_assignments,
    upsert_annotations,
    upsert_assignment_scope,
)
from nacsos_data.db.crud.items import read_any_item_by_item_id
from nacsos_data.models.annotations import (
    AnnotationModel,
    AssignmentModel,
    AssignmentScopeModel,
    AssignmentStatus,
)
from nacsos_data.models.items import AcademicItemModel

from what_works_repo.constants import DEET_SCOPE_SENTINEL
from what_works_repo.deet_orchestration.deet_annotator import DeetAnnotator
from what_works_repo.logging import logger
from what_works_repo.settings import settings


def resolve_deet_experiment(
    exp_path: Path, deet_project_config: Path
) -> ExperimentArtefacts:
    """Resolve a deet project and run id (stored in a text file) to an experiment."""
    run_id = exp_path.read_text().strip()
    project = DeetProject.load(project_dir=deet_project_config.parent)
    experiment = ExperimentArtefacts(base_dir=project.experiments_dir / run_id)
    if not experiment.is_complete:
        raise ValueError
    return experiment


async def annotate(
    annotator: DeetAnnotator, scope_id: str
) -> tuple[list[str], str, str]:
    """
    Annotate assignments with the DeetAnnotator.

    Return the list of documents that are predicted positives, and the id of the scheme.
    """
    logger.info("Annotating assignments with deet.")
    db_engine = get_engine_async("config/.env")
    predicted_positive_ids: list[str] = []
    async with db_engine.session() as session:
        scope = await read_assignment_scope(
            assignment_scope_id=scope_id, session=session
        )
        if not scope:
            raise ValueError(f"Scope {scope_id} does not exist!")
        assignments = await read_assignments_for_scope(
            assignment_scope_id=scope_id, session=session
        )
        if not assignments:
            raise ValueError(f"No scheme for assignment scope {scope_id}")
        scheme = await read_annotation_scheme_for_scope(
            assignment_scope_id=scope_id, session=session
        )
        if not scheme or not scheme.annotation_scheme_id:
            raise ValueError(f"No scheme for assignment scope {scope_id}")
        for assignment in assignments:
            if not assignment.assignment_id:
                raise ValueError("Assignment has no ID!")
            item = await read_any_item_by_item_id(
                assignment.item_id, "academic", db_engine
            )
            item = cast(AcademicItemModel, item)
            text = (item.title or "") + " " + (item.text or "")
            deet_annotations = annotator.predict(text)
            logger.info(deet_annotations)
            deet_value, reasoning = next(
                (ann.output_data, ann.reasoning)
                for ann in deet_annotations
                if ann.attribute.attribute_label == settings.nacsos.inclusion_key
            )
            deet_value = cast(bool, deet_value)
            logger.debug(deet_value)
            if deet_value:
                predicted_positive_ids.append(str(assignment.item_id))

            existing = await read_annotations_for_assignment(
                assignment_id=assignment.assignment_id, session=session
            )
            existing_by_key = {a.key: a for a in existing}
            annotation = existing_by_key.get(settings.nacsos.inclusion_key)
            annotation_id = (
                str(annotation.annotation_id) if annotation else str(uuid.uuid4())
            )
            annotations = [
                AnnotationModel(
                    annotation_id=annotation_id,
                    assignment_id=assignment.assignment_id,
                    user_id=assignment.user_id,
                    item_id=assignment.item_id,
                    annotation_scheme_id=scheme.annotation_scheme_id,
                    key=settings.nacsos.inclusion_key,
                    value_int=deet_value,
                )
            ]
            if settings.nacsos.comment_key and reasoning:
                annotation = existing_by_key.get(settings.nacsos.comment_key)
                annotation_id = (
                    str(annotation.annotation_id) if annotation else str(uuid.uuid4())
                )
                annotations.append(
                    AnnotationModel(
                        annotation_id=annotation_id,
                        assignment_id=assignment.assignment_id,
                        user_id=assignment.user_id,
                        item_id=assignment.item_id,
                        annotation_scheme_id=scheme.annotation_scheme_id,
                        key=settings.nacsos.comment_key,
                        value_str=reasoning,
                    )
                )
            upsert_res = await upsert_annotations(
                annotations,
                assignment_id=assignment.assignment_id,
                db_engine=db_engine,  # engine, not session
            )
            logger.debug(upsert_res)

        return predicted_positive_ids, str(scheme.annotation_scheme_id), scope.name


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


async def _main(annotator: DeetAnnotator, scope_id: str, output_path: Path) -> None:
    predicted_positive_ids, scheme_id, scope_name = await annotate(annotator, scope_id)
    new_scope_id = await assign_deet_verification_scope(
        predicted_positive_ids, scheme_id, scope_name
    )
    output_path.write_text(new_scope_id)


def main(
    exp_path: Path, deet_scope_file: Path, deet_project_config: Path, output_path: Path
):
    """
    Annotate documents with deet.

    Take documents assigned to deet in the scope specified in the scope file,
    and annotate them using deet, creating annotations in NACSOS.

    Create a new scope with assignments to human users if specified,
    with all predicted positives.
    """
    experiment = resolve_deet_experiment(exp_path, deet_project_config)
    annotator = DeetAnnotator(experiment=experiment)
    scope_id = deet_scope_file.read_text().strip()
    asyncio.run(_main(annotator=annotator, scope_id=scope_id, output_path=output_path))


if __name__ == "__main__":
    typer.run(main)
