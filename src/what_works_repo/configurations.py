from typing import Annotated

from deet.ui.terminal.wizards import UI
from pydantic import BaseModel, Field


class DeetAnnotationConfig(BaseModel):
    deet_run: str = Field(...)
    check_positives: Annotated[
        bool,
        UI(
            help="Assign predicted [bold]includes[/bold] for human checking?",
            label="Check positives?",
        ),
    ] = Field(default=True, description="Check positives?")
    check_negatives: Annotated[
        bool,
        UI(
            help="Assign predicted [bold]excludes[/bold] for human checking",
        ),
    ] = Field(default=False, description="Check negatives")
    n_annotations: Annotated[
        int, UI(help="How many documents to assign to deet", placeholder="0")
    ] = Field(default=0, description="n deet annotations")


class NextBatchConfig(BaseModel):
    n_items: Annotated[
        int, UI(help="Define the number of of items that the next batch should contain")
    ] = Field(default=1000, description="Items in next batch")
    use_pretrained_models: Annotated[
        bool,
        UI(help="If True, use pretrained models specified in config/snakemake.yaml"),
    ] = Field(default=True, description="Use pretrained models")
    retrain_model: Annotated[bool, UI()] = Field(
        default=False, description="Retrain prioritisation model"
    )
