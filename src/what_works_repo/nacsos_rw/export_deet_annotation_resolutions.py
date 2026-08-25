import asyncio
from pathlib import Path

import pandas as pd
import typer
from nacsos_data.db import get_engine_async
from nacsos_data.db.crud.annotations import read_assignment_counts_for_scope
from nacsos_data.models.nql import AssignmentFilter
from nacsos_data.util.annotations.export import prepare_export_table

from what_works_repo.constants import DEET_SCOPE_SENTINEL
from what_works_repo.settings import settings


async def export(resolution_scope_id: str, output_path: Path):
    db_engine = get_engine_async("config/.env")

    counts = await read_assignment_counts_for_scope(
        assignment_scope_id=resolution_scope_id, db_engine=db_engine
    )
    if counts.num_open > 0 or counts.num_partial > 0:
        raise ValueError(
            f"Resolution scope has incomplete assignments: "
            f"{counts.num_open} open, {counts.num_partial} partial"
        )

    async with db_engine.session() as session:
        rows = await prepare_export_table(
            session=session,
            nql_filter=AssignmentFilter(mode=2, scopes=[resolution_scope_id]),
            bot_annotation_metadata_ids=None,
            assignment_scope_ids=[resolution_scope_id],
            user_ids=None,
            project_id=settings.nacsos.project_id,
            # labels=list(labels_dict.values()),
            ignore_hierarchy=True,
            ignore_repeat=True,
        )
        df = pd.DataFrame(rows)

    df[["item_id", "title", "text", "incl"]].rename(
        columns={
            "item_id": "document_id",
            "title": "name",
            "text": "abstract",
        }
    ).to_csv(output_path, index=False)


def main(deet_resolutions_scope: Path, output_path: Path):
    """
    Retrieve and human resolutions of deet annotations.

    Write results to a csv.
    """
    resolution_scope_id = deet_resolutions_scope.read_text().strip()
    if resolution_scope_id == DEET_SCOPE_SENTINEL:
        output_path.write_text("document_id,name,abstract,incl\n")
        return

    asyncio.run(
        export(
            resolution_scope_id=resolution_scope_id,
            output_path=output_path,
        )
    )


if __name__ == "__main__":
    typer.run(main)
