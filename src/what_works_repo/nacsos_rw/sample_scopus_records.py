"""Read scopus query results, deduplicate, sample, and write to NACSOS format."""

import json
import random
from pathlib import Path

import typer
from loguru import logger

from what_works_repo.nacsos_rw.models import ScopusAcademicItem


def main(input_dir: Path, output_file: Path, sample_size: int = 20000, seed: int = 42):
    output_file.parent.mkdir(parents=True, exist_ok=True)

    reservoir = []
    eid_seen = set()
    duplicate_count = 0
    unique_count = 0
    total_records = 0

    random.seed(seed)

    for jsonl_file in sorted(input_dir.glob("*.jsonl")):
        with jsonl_file.open() as f:
            for line in f:
                record = json.loads(line)
                eid = record.get("eid")
                total_records += 1

                if eid in eid_seen:
                    duplicate_count += 1
                else:
                    eid_seen.add(eid)
                    unique_count += 1

                    if len(reservoir) < sample_size:
                        reservoir.append(record)
                    else:
                        j = random.randint(0, unique_count - 1)
                        if j < sample_size:
                            reservoir[j] = record

        logger.info(
            f"Processed {jsonl_file}. Duplicates: "
            f"{duplicate_count}, total records: {total_records}"
        )

    if duplicate_count:
        logger.warning(f"{duplicate_count} duplicate eids found")
    else:
        logger.success("No duplicates found!")

    if total_records < sample_size:
        raise ValueError(f"Only {total_records}, need {sample_size}")

    with output_file.open("w") as f:
        for record in reservoir:
            academic_item = ScopusAcademicItem.model_validate(record)
            f.write(academic_item.model_dump_json() + "\n")


if __name__ == "__main__":
    typer.run(main)
