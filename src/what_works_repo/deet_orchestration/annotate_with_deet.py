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
    read_assignments_for_scope,
    upsert_annotations,
)
from nacsos_data.db.crud.items import read_any_item_by_item_id
from nacsos_data.models.annotations import AnnotationModel
from nacsos_data.models.items import AcademicItemModel

from what_works_repo.deet_orchestration.deet_annotator import DeetAnnotator
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


async def annotate(annotator: DeetAnnotator, scope_id: str) -> None:
    """Annotate assignments."""
    db_engine = get_engine_async("config/.env")
    async with db_engine.session() as session:
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
            deet_value = next(
                ann.output_data
                for ann in deet_annotations
                if ann.attribute.attribute_label == settings.nacsos.inclusion_key
            )
            deet_value = cast(bool, deet_value)

            existing = await read_annotations_for_assignment(
                assignment_id=assignment.assignment_id, session=session
            )
            existing_by_key = {a.key: a for a in existing}
            annotation = existing_by_key.get(settings.nacsos.inclusion_key)
            annotation_id = annotation.annotation_id if annotation else uuid.uuid4()

            await upsert_annotations(
                annotations=[
                    AnnotationModel(
                        annotation_id=annotation_id,
                        assignment_id=assignment.assignment_id,
                        user_id=assignment.user_id,
                        item_id=assignment.item_id,
                        annotation_scheme_id=scheme.annotation_scheme_id,
                        key=settings.nacsos.inclusion_key,
                        value_int=deet_value,
                    )
                ],
                assignment_id=assignment.assignment_id,
                db_engine=db_engine,  # engine, not session
            )


def main(
    exp_path: Path, deet_scope_file: Path, deet_project_config: Path, output_path: Path
):
    experiment = resolve_deet_experiment(exp_path, deet_project_config)
    annotator = DeetAnnotator(experiment=experiment)
    scope_id = deet_scope_file.read_text().strip()
    asyncio.run(annotate(annotator=annotator, scope_id=scope_id))
    output_path.write_text("asdf")


if __name__ == "__main__":
    typer.run(main)
