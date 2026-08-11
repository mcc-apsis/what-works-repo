"""Create a deet subproject from a batch."""

import os
from contextlib import chdir
from pathlib import Path

import typer
import yaml
from deet.data_models.documents import ContextType
from deet.data_models.enums import EvaluationStrategyName
from deet.data_models.project import DeetProject
from deet.extractors.llm_data_extractor import DataExtractionConfig, LLMProvider
from deet.processors.converter_register import SupportedImportFormat


def main(annotation_path: Path, config_target: Path):
    deet_project_dir = config_target.parent
    relative_annotation_path = Path(os.path.relpath(annotation_path, deet_project_dir))

    with chdir(deet_project_dir):
        project = DeetProject(
            name="asdf",
            gold_standard_data_format=SupportedImportFormat.GENERIC_CSV,
            gold_standard_data_path=relative_annotation_path,
            pdf_dir=None,
            evaluation_strategy=EvaluationStrategyName.DEV_VAL_TEST,
        )
        project.setup()

        config = DataExtractionConfig(
            default_context_type=ContextType.ABSTRACT_ONLY,
            provider=LLMProvider.OLLAMA,
            model="smollm:360m",
        )
        project.config_path.write_text(
            yaml.safe_dump(config.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )


if __name__ == "__main__":
    typer.run(main)
