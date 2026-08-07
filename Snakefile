from what_works_repo.settings import settings


rule all:
    input:
        "data/processed/scopus/import_complete.txt",


rule fetch_scopus_query:
    output:
        directory("data/raw/scopus/"),
    shell:
        f'rsync -av --progress -e "ssh -o ProxyJump={settings.ts01_username}@ts01.pik-potsdam.de" {settings.ts01_username}@se164:/data/academic-api/data/results/4/responses/*.jsonl {output}/'


rule prepare_sample_records:
    input:
        "data/raw/scopus",
    output:
        f"data/processed/batches/scopus/batch_sample_{settings.sample_size}.jsonl",
    shell:
        "uv run python src/what_works_repo/imports/sample_scopus_records.py "
        "{input} "
        "data/processed/batches/scopus "
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
        f"data/processed/batches/scopus/batch_sample_{settings.sample_size}.jsonl",
    output:
        "data/processed/scopus/import_complete.txt",
    shell:
        "uv run nacsos import ACADEMIC "
        "--source {input} "
        f"--project-id {settings.nacsos__project_id} "
        "--config-file config/.env "
        f"--import-id {settings.nacsos__import_id} "
        "2>&1 | tee {output}"
