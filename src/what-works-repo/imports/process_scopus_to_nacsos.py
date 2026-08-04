import json
from pathlib import Path

import typer
from nacsos_data.models.items.academic import AcademicAuthorModel, AcademicItemModel
from pydantic import field_validator, model_validator


class ScopusAcademicItem(AcademicItemModel):
    """AcademicItemModel subclass that deserializes from Scopus JSON."""

    @model_validator(mode="before")
    @classmethod
    def map_scopus_fields(cls, data):
        """Remap Scopus field names to AcademicItemModel field names."""
        if isinstance(data, dict):
            return {
                "scopus_id": data.get("eid"),
                "doi": data.get("prism:doi"),
                "title": data.get("dc:title"),
                "text": data.get("dc:description"),
                "publication_year": data.get("prism:coverDate"),
                "source": data.get("prism:publicationName"),
                "keywords": data.get("authkeywords"),
                "authors": data.get("author"),
            }
        return data

    @field_validator("publication_year", mode="before")
    @classmethod
    def parse_year(cls, v):
        if isinstance(v, str):
            return int(v[:4])
        return v

    @field_validator("keywords", mode="before")
    @classmethod
    def split_keywords(cls, v):
        if isinstance(v, str):
            return [k.strip() for k in v.split("|")] if v else None
        return v

    @field_validator("authors", mode="before")
    @classmethod
    def parse_authors(cls, v):
        if isinstance(v, list):
            return [
                AcademicAuthorModel(
                    name=f"{a.get('given-name', '')} {a.get('surname', '')}".strip()
                )
                for a in v
            ]
        return v


def main(input_file: Path, output_file: Path):
    """Read jsonl of scopus records and translate to"""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(input_file) as inf, open(output_file, "w") as outf:
        for line in inf:
            scopus_dict = json.loads(line)
            item = ScopusAcademicItem.model_validate(scopus_dict)
            outf.write(item.model_dump_json() + "\n")


if __name__ == "__main__":
    typer.run(main)
