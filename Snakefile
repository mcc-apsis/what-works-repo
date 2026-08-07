from what_works_repo.settings import settings

rule all:
    input:
        "data/processed/scopus/import_complete.txt"

rule fetch_scopus_query:
    output: 
        directory("data/raw/scopus/")
    shell:
        f'rsync -av --progress -e "ssh -o ProxyJump={settings.ts01_username}@ts01.pik-potsdam.de" {settings.ts01_username}@se164:/data/academic-api/data/results/4/responses/*.jsonl {output}/'

rule sample_scopus_records:
    input:
        "data/raw/scopus"
    output:
        f"data/processed/scopus/sample_{settings.sample_size}.jsonl"
    shell:
        "uv run python src/what-works-repo/imports/sample_scopus_records.py "
        "--input-dir {input} "
        "--output-dir data/processed/scopus "
        f"--sample-size {settings.sample_size}"

rule transform_scopus_to_nacsos:
    input:
        f"data/processed/scopus/sample_{settings.sample_size}.jsonl"
    output:
        f"data/processed/scopus/sample_{settings.sample_size}_nacsos.jsonl"
    shell:
        "uv run python src/what-works-repo/imports/process_scopus_to_nacsos.py "
        "{input} {output}"

rule import_scopus_to_nacsos:
    input:
        f"data/processed/scopus/sample_{settings.sample_size}_nacsos.jsonl"
    output:
        "data/processed/scopus/import_complete.txt"
    shell:
        "uv run nacsos import ACADEMIC "
        "--source {input} "
        f"--project-id {settings.nacsos__project_id} "
        "--config-file config/.env "
        f"--import-id {settings.nacsos__import_id} "
        "2>&1 | tee {output}"
