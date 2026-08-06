import getpass
from builtins import input as user_input

default_user = getpass.getuser()
USERNAME = user_input(f"Username for ts01.pik-potsdam.de [{default_user}]: ") or default_user



rule fetch_scopus_query:
    output: 
        directory("data/raw/scopus/")
    shell:
        'rsync -av --progress -e "ssh -o ProxyJump={USERNAME}@ts01.pik-potsdam.de" {USERNAME}@se164:/data/academic-api/data/results/4/responses/*.jsonl {output}/'

rule sample_scopus_records:
    input:
        "data/raw/scopus"
    output:
        directory("data/processed/scopus")
    shell:
        "uv run python src/what-works-repo/imports/sample_scopus_records.py "
        "--input-dir {input} "
        "--output-dir {output} "
        "--sample-size 20000"

rule transform_scopus_to_nacsos:
    input:
        "data/processed/scopus/sample_20000.jsonl"
    output:
        "data/processed/scopus/sample_20000_nacsos.jsonl"
    shell:
        "uv run python src/what-works-repo/imports/process_scopus_to_nacsos.py "
        "{input} {output}"

configfile: "config/snakemake.yaml"

rule import_scopus_to_nacsos:
    input:
        "data/processed/scopus/sample_20000_nacsos.jsonl"
    output:
        "data/processed/scopus/import_complete.txt"
    shell:
        "uv run nacsos import ACADEMIC "
        "--source {input} "
        "--project-id {config[nacsos][project_id]} "
        "--config-file config/.env "
        "--import-id {config[nacsos][import_id]} "
        "2>&1 | tee {output}"
