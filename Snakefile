import os

from what_works_repo.settings import settings
from what_works_repo.constants import BATCH_DIR, DEET_DIR, STOPPING_CRITERIA_TRIGGERED


def get_next_batch_number():
    existing_batches = list(BATCH_DIR.glob("batch_*/items.jsonl"))
    return len(existing_batches) + 1


NEXT_BATCH = get_next_batch_number()
CURRENT_BATCH = NEXT_BATCH - 1

CURRENT_BATCH_DIR = BATCH_DIR / f"batch_{CURRENT_BATCH}"
CURRENT_BATCH_ITEMS = CURRENT_BATCH_DIR / "items.jsonl"
CURRENT_BATCH_ANNOTATIONS = CURRENT_BATCH_DIR / "annotations.csv"
CURRENT_BATCH_IMPORTED = CURRENT_BATCH_DIR / "imported.txt"
CURRENT_BATCH_MODEL = CURRENT_BATCH_DIR / "model.txt"  # TODO define model serialisation
CURRENT_BATCH_DEET_PROJECT_DIR = DEET_DIR / f"batch_{CURRENT_BATCH}"
CURRENT_BATCH_DEET_PROJECT_CONFIG = CURRENT_BATCH_DEET_PROJECT_DIR / "project.yaml"
CURRENT_BATCH_SCOPE_ID_FILE = CURRENT_BATCH_DIR / "assignment_scope_ids.json"
CURRENT_BATCH_DEET_FINALISED = CURRENT_BATCH_DEET_PROJECT_DIR / "finalised_run.txt"
CURRENT_BATCH_DEET_ASSIGNMENT_SCOPE = CURRENT_BATCH_DIR / "deet_assignment_scope_id.txt"
CURRENT_BATCH_DEET_RESOLVED_ANNOTATIONS = (
    CURRENT_BATCH_DIR / "resolved_deet_annotations.jsonl"
)

NEXT_BATCH_ITEMS = BATCH_DIR / f"batch_{NEXT_BATCH}" / "items.jsonl"


rule fetch_scopus_query:
    output:
        directory("data/raw/scopus/"),
    shell:
        f'rsync -av --progress -e "ssh -o ProxyJump={settings.ts01_username}@ts01.pik-potsdam.de" {settings.ts01_username}@se164:/data/academic-api/data/results/4/responses/*.jsonl {output}/'


rule prepare_sample_records:
    input:
        "data/raw/scopus",
    output:
        BATCH_DIR / "batch_1" / "items.jsonl",
    shell:
        "uv run python src/what_works_repo/nacsos_rw/sample_scopus_records.py "
        "{input} "
        f"{output} "
        f"--sample-size {settings.sample_size}"


rule setup_nacsos_project:
    """Validate that NACSOS project is configured"""
    output:
        "data/metadata/nacsos_project.txt",
    run:
        required = ["nacsos__project_id", "nacsos__import_id"]
        missing = [k for k in required if not hasattr(settings, k)]
        if missing:
            raise ValueError(f"Missing required config keys: {', '.join(missing)}")
        with open(output[0]) as f:
            f.write(f"Project ID: {settings.nacsos__project_id}\n")
            f.write(f"Import ID: {settings.nacsos__import_id}\n")


rule import_scopus_to_nacsos:
    input:
        CURRENT_BATCH_ITEMS,
    output:
        CURRENT_BATCH_IMPORTED,
    shell:
        # f"ssh -N -L 5433:localhost:5432 -L 19530:localhost:19530 {settings.ts01_username}@se164 -J {settings.ts01_username}@ts01 & "
        # "TUNNEL_PID=$! ; "
        # "trap 'kill $TUNNEL_PID' EXIT ; "
        "uv run nacsos import ACADEMIC "
        "--source {input} "
        f"--project-id {settings.nacsos.project_id} "
        "--config-file config/.env "
        f"--import-id {settings.nacsos.import_id} "
        "2>&1 | tee {output}.log && "
        "echo 'import successful' > {output}"


rule make_assignments:
    """Manual step: Create an assignment scope in NACSOS, write ID to output file."""
    input:
        CURRENT_BATCH_IMPORTED,
    output:
        CURRENT_BATCH_SCOPE_ID_FILE,
    run:
        import os

        if not os.path.exists(output[0]):
            raise FileNotFoundError(
                f"Create assignment scope in NACSOS, then write ID to {output[0]}"
            )


rule export_batch_annotations:
    """Check imported batch for completed annotations and write if complete, otherwise do nothing."""
    input:
        CURRENT_BATCH_SCOPE_ID_FILE,
    output:
        CURRENT_BATCH_ANNOTATIONS,
    shell:
        "uv run python src/what_works_repo/nacsos_rw/export_human_annotations.py "
        "{input} "
        "{output} "


rule create_deet_subproject:
    """Create a deet project that uses annotations as gold standard data"""
    input:
        CURRENT_BATCH_ANNOTATIONS,
    output:
        CURRENT_BATCH_DEET_PROJECT_CONFIG,
    shell:
        "uv run python src/what_works_repo/deet_orchestration/create_deet_subproject.py "
        "{input} "
        "{output} "


rule finalise_deet_run:
    """Manual step: User completes DEET work, writes preferred run ID."""
    input:
        CURRENT_BATCH_DEET_PROJECT_CONFIG,
    output:
        CURRENT_BATCH_DEET_FINALISED,
    run:
        if not os.path.exists(output[0]):
            raise FileNotFoundError(
                f"Complete DEET work and write run ID to {output[0]}"
            )


rule annotate_with_deet_and_assign_checks:
    """Use finalised deet config to annotate remaining batch documents. Assign predicted positives to human."""
    input:
        CURRENT_BATCH_DEET_FINALISED,
    output:
        CURRENT_BATCH_DEET_ASSIGNMENT_SCOPE,


rule export_batch_resolved_deet_annotations:
    """Make sure all deet predicted positives have been checked by a human, and export all annotations, preferring human decisions to deet."""
    input:
        CURRENT_BATCH_DEET_FINALISED,
    output:
        CURRENT_BATCH_DEET_RESOLVED_ANNOTATIONS,


rule check_stopping_criteria:
    """Check if stopping criteria is met."""
    input:
        CURRENT_BATCH_DEET_RESOLVED_ANNOTATIONS,
    output:
        STOPPING_CRITERIA_TRIGGERED,


rule train_prioritisation_model:
    """Combine human-only, and human+deet resolutions to train a model."""
    input:
        CURRENT_BATCH_ANNOTATIONS,
        CURRENT_BATCH_DEET_RESOLVED_ANNOTATIONS,
    output:
        CURRENT_BATCH_MODEL,


rule predict:
    """Use predicted model to make predictions for all remaining documents."""
    input:
        CURRENT_BATCH_MODEL,
    output:
        NEXT_BATCH_ITEMS,


rule all:
    input:
        STOPPING_CRITERIA_TRIGGERED,
