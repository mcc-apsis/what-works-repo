import os

from snakemake.exceptions import WorkflowError

from what_works_repo.batch import Batch
from what_works_repo.logging import logger
from what_works_repo.settings import settings
from what_works_repo.constants import STOPPING_CRITERIA_TRIGGERED, RAW_DATA

batch = Batch.current()


def pipeline_target(wildcards):
    decision = checkpoints.decide_stopping.get().output[0]
    verdict = float(open(decision).read().strip())
    if verdict < 0.05:
        return str(decision)
    return str(batch.next.items)


rule all:
    input:
        pipeline_target,


def require_manual_step(output_path, instruction):
    if os.path.exists(output_path):
        return
    banner = "!" * 72
    logger.error(
        f"\n{banner}\n  MANUAL STEP REQUIRED\n{banner}\n"
        f"  {instruction}\n"
        f"  Write the result to:\n    {output_path}\n"
        f"  then re-run snakemake to continue.\n{banner}"
    )
    raise WorkflowError(f"Manual step required: {instruction}")


rule fetch_scopus_query:
    output:
        directory(RAW_DATA),
    shell:
        f'rsync -av --progress -e "ssh -o ProxyJump={settings.ts01_username}@ts01.pik-potsdam.de" {settings.ts01_username}@se164:/data/academic-api/data/results/4/responses/*.jsonl {output}/'


rule prepare_sample_records:
    input:
        RAW_DATA,
    output:
        Batch(1).items,
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
        batch.items,
    output:
        batch.imported,
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
        ancient(batch.imported),
    output:
        batch.scope_ids,
    run:
        require_manual_step(
            output[0], "Create assignment scope in NACSOS, and record its ID"
        )


rule export_batch_annotations:
    """Check imported batch for completed annotations and write if complete, otherwise do nothing."""
    input:
        batch.scope_ids,
    output:
        batch.annotations,
    shell:
        "uv run python src/what_works_repo/nacsos_rw/export_human_annotations.py "
        "{input} "
        "{output} "


rule create_deet_subproject:
    """Create a deet project that uses annotations as gold standard data"""
    input:
        batch.annotations,
    output:
        batch.deet_config,
    shell:
        "uv run python src/what_works_repo/deet_orchestration/create_deet_subproject.py "
        "{input} "
        "{output} "


rule finalise_deet_run:
    """Manual step: User completes DEET work, writes preferred run ID."""
    input:
        ancient(batch.deet_config),
    output:
        batch.deet_finalised,
    run:
        require_manual_step(
            output[0], f"Complete DEET work and write run ID to {output[0]}"
        )


rule assign_docs_deet:
    """In the NACSOS UI, assign the documents you want deet to annotate to deet."""
    input:
        ancient(batch.deet_finalised),
    output:
        batch.deet_assignment_scope,
    run:
        require_manual_step(
            output[0],
            f"Assign a batch of documents to deet, and write the scope ID to {output[0]}",
        )


rule annotate_with_deet_and_assign_checks:
    """Use finalised deet config to annotate remaining batch documents. Assign predicted positives to human."""
    input:
        batch.deet_finalised,
        batch.deet_assignment_scope,
        batch.deet_config,
    output:
        batch.deet_resolution_scope,
    shell:
        "uv run python src/what_works_repo/deet_orchestration/annotate_with_deet.py "
        "{input} "
        "{output} "


rule export_batch_resolved_deet_annotations:
    """Make sure all deet predicted positives have been checked by a human, and export all annotations, preferring human decisions to deet."""
    input:
        batch.deet_assignment_scope,
        batch.deet_resolution_scope,
    output:
        batch.deet_resolved_annotations,
    shell:
        "uv run python src/what_works_repo/nacsos_rw/export_deet_annotations.py "
        "{input} "
        "{output} "


checkpoint decide_stopping:
    input:
        batch.deet_resolved_annotations,
    output:
        batch.stopping_decision,
    shell:
        "uv run python src/what_works_repo/classify/stopping_criteria.py {batch.number} "


rule train_prioritisation_model:
    """Combine human-only, and human+deet resolutions to train a model."""
    input:
        batch.annotations,
        batch.deet_resolved_annotations,
    output:
        batch.model,
    shell:
        "uv run python src/what_works_repo/classify/train.py {batch.number}"


rule predict:
    """Use predicted model to make predictions for all remaining documents."""
    input:
        batch.model,
    output:
        batch.next.items,
    shell:
        "uv run python src/what_works_repo/classify/predict.py {batch.number}"
