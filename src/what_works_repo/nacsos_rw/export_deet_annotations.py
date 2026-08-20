import asyncio
from pathlib import Path

import typer
from nacsos_data.db import get_engine_async
from nacsos_data.models.nql import AssignmentFilter
from nacsos_data.util.annotations.export import wide_export_table

from what_works_repo.constants import DEET_SCOPE_SENTINEL
from what_works_repo.settings import settings


async def export(
    deet_scope_id: str, resolution_scope_id: str | None, output_path: Path
):
    db_engine = get_engine_async("config/.env")

    scope_ids = [deet_scope_id] + ([resolution_scope_id] if resolution_scope_id else [])

    nql_filter = AssignmentFilter(mode=2, scopes=[deet_scope_id])

    base_cols, label_cols, df = await wide_export_table(
        db_engine=db_engine,
        nql_filter=nql_filter,
        scope_ids=scope_ids,
        project_id=settings.nacsos.project_id,
    )

    deet_col = f"{settings.nacsos.deet_username}|incl:1"
    human_cols = [
        c
        for c in label_cols
        if "|incl:1" in c and settings.nacsos.deet_username not in c
    ]

    df["incl"] = df[human_cols].any(axis=1)  # True if any human said include
    df["incl"] = df["incl"].where(df[human_cols].notna().any(axis=1), df[deet_col])

    df[["item_id", "title", "text", "incl"]].rename(
        columns={
            "item_id": "document_id",
            "title": "name",
            "text": "abstract",
        }
    ).to_csv(output_path, index=False)


def main(deet_assignment_scope: Path, deet_resolutions_scope: Path, output_path: Path):
    """
    Retrieve and resolve annotations made by deet.

    Wherever deet and a human resolver have coded the same document,
    prefer the human annotation.

    Write results to a csv.
    """
    deet_scope_id = deet_assignment_scope.read_text().strip()
    resolution_scope_id = deet_resolutions_scope.read_text().strip()
    if resolution_scope_id == DEET_SCOPE_SENTINEL:
        resolution_scope_id = None

    asyncio.run(
        export(
            deet_scope_id=deet_scope_id,
            resolution_scope_id=resolution_scope_id,
            output_path=output_path,
        )
    )


if __name__ == "__main__":
    typer.run(main)
