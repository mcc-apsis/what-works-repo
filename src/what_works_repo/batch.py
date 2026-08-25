"""Define batch resources and layout."""

from dataclasses import dataclass
from pathlib import Path

from what_works_repo.constants import BATCH_DIR, DEET_DIR


@dataclass(frozen=True)
class Batch:
    """Filesystem layout for a single processing batch.

    One source of truth for where a batch's resources live, shared by the
    Snakefile and the standalone scripts.
    """

    number: int

    # --- directories -------------------------------------------------------
    @property
    def dir(self) -> Path:
        return BATCH_DIR / f"batch_{self.number}"

    @property
    def deet_dir(self) -> Path:
        return DEET_DIR / f"batch_{self.number}"

    # --- data / control files ---------------------------------------------
    @property
    def items(self) -> Path:
        return self.dir / "items.jsonl"

    @property
    def annotations(self) -> Path:
        return self.dir / "annotations.csv"

    @property
    def imported(self) -> Path:
        return self.dir / "imported.txt"

    @property
    def scope_ids(self) -> Path:
        return self.dir / "assignment_scope_ids.json"

    @property
    def model(self) -> Path:
        return self.dir / "model.txt"

    @property
    def deet_config(self) -> Path:
        return self.deet_dir / "project.yaml"

    @property
    def deet_annotation_config(self) -> Path:
        return self.dir / "deet_annotation_config.json"

    @property
    def deet_annotations(self) -> Path:
        return self.dir / "deet_annotations.csv"

    @property
    def deet_resolution_scope(self) -> Path:
        return self.dir / "deet_resolution_scope_id.txt"

    @property
    def deet_resolved_annotations(self) -> Path:
        return self.dir / "resolved_deet_annotations.csv"

    @property
    def stopping_decision(self) -> Path:
        return self.dir / "stopping_decision.txt"

    # --- navigation -------------------------------------------------------
    @classmethod
    def current(cls) -> "Batch":
        """The latest batch that has an items file (0 if none exist yet)."""
        return cls(len(list(BATCH_DIR.glob("batch_*/items.jsonl"))))

    @property
    def next(self) -> "Batch":
        return Batch(self.number + 1)
