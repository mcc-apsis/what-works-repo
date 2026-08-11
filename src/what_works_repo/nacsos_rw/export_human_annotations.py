"""Export human annotations, if complete."""

import asyncio
import json
import uuid
from pathlib import Path
from typing import cast

import pandas as pd
import typer
from nacsos_data.db import get_engine_async
from nacsos_data.db.crud.annotations import (
    read_assignments_for_scope,
)
from nacsos_data.db.crud.items import read_any_item_by_item_id
from nacsos_data.db.schemas import BotAnnotationMetaData
from nacsos_data.models.items import AcademicItemModel
from nacsos_data.util.annotations import read_bot_annotations
from sqlalchemy import select

from what_works_repo.settings import settings


def read_scopes(scope_path: Path) -> list[str]:
    scope_ids = []
    for item in json.loads(scope_path.read_text()):
        try:
            uuid.UUID(item)
        except ValueError as e:
            raise e
        scope_ids.append(item)
    if not scope_ids:
        raise ValueError("The list of scope IDs is empty")
    return scope_ids


async def export_assignments(assignment_scope_id: str) -> list[dict]:
    db_engine = get_engine_async("config/.env")

    async with db_engine.session() as session:
        # get assignments
        assignments = await read_assignments_for_scope(
            assignment_scope_id=assignment_scope_id, session=session
        )

        # Get bot metadata
        stmt = select(BotAnnotationMetaData).filter_by(
            assignment_scope_id=assignment_scope_id
        )
        bot_meta = (await session.execute(stmt)).scalars().one_or_none()
        if not bot_meta:
            raise ValueError("No resolved annotations for this scope.")

        resolved = await read_bot_annotations(
            session=session,
            bot_annotation_metadata_id=str(bot_meta.bot_annotation_metadata_id),
        )
        resolved_item_ids = {str(r.item_id) for r in resolved}

    for assignment in assignments:
        if str(assignment.item_id) not in resolved_item_ids:
            raise ValueError(f"Assignment {assignment.item_id} not resolved")

    annotations_to_export = []

    for resolved_anno in resolved:
        if resolved_anno.key == settings.nacsos.inclusion_key:
            item = await read_any_item_by_item_id(
                resolved_anno.item_id, "academic", db_engine
            )
            item = cast(AcademicItemModel, item)
            if not item:
                raise ValueError("Item not found")
            annotations_to_export.append(
                {
                    "document_id": str(item.item_id),
                    "name": item.title,
                    "abstract": item.text,
                    settings.nacsos.inclusion_key: resolved_anno.value_int,
                }
            )
    return annotations_to_export


async def gather_exports(scope_ids: list[str]) -> list[dict]:
    results = await asyncio.gather(
        *[export_assignments(scope_id) for scope_id in scope_ids]
    )
    return [row for rows in results for row in rows]


def main(scope_path: Path, output_path: Path):

    scope_ids = read_scopes(scope_path)
    all_rows = asyncio.run(gather_exports(scope_ids))

    pd.DataFrame(all_rows).to_csv(output_path, index=False)


if __name__ == "__main__":
    typer.run(main)
