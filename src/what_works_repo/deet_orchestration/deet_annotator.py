"""
Create annotations from a deet config
"""

import csv
from pathlib import Path

from deet.data_models.base import Attribute, AttributeType, GoldStandardAnnotation
from deet.data_models.project import ExperimentArtefacts
from deet.extractors.llm_data_extractor import DataExtractionConfig, LLMDataExtractor


class DeetAnnotator:
    def __init__(self, experiment: ExperimentArtefacts) -> None:
        self.config = DataExtractionConfig.from_yaml(experiment.config_snapshot)
        self.extractor = LLMDataExtractor(config=self.config)
        self.parse_attributes(experiment.config_snapshot)

    def parse_attributes(self, prompt_path: Path) -> None:
        """Parse attributes from a prompt path"""
        with prompt_path.open(newline="", encoding="utf-8") as csv_file:
            self.attributes = [
                Attribute(
                    prompt=row["prompt"],
                    output_data_type=AttributeType(row["output_data_type"]),
                    attribute_id=int(row["attribute_id"]),
                    attribute_label=row["attribute_label"],
                )
                for row in csv.DictReader(csv_file)
                if row["output_data_type"] == "bool"
            ]

    def predict(self, text: str) -> list[GoldStandardAnnotation]:
        """Run extractor over text and return annotations."""
        result = self.extractor.extract_from_document(self.attributes, payload=text)
        return result.annotations
