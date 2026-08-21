import os

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource


class NacsosSettings(BaseModel):
    project_id: str
    import_id: str
    inclusion_key: str
    comment_key: str | None = None
    deet_check_users: list[str] = Field(
        default_factory=list,
        description=(
            "User Ids of humans who check DEET predicted positives."
            " Leave empty to skip verification of positives."
        ),
    )
    deet_user_id: str
    deet_username: str


class TransformerModel(BaseModel):
    name: str
    label: str
    threshold: float


class MLSettings(BaseModel):
    train_model: bool
    pretrained_models: list[TransformerModel]


class Settings(BaseSettings):
    """Settings for the what works repo."""

    model_config = SettingsConfigDict(env_file="config/.env", extra="ignore")

    ts01_username: str = Field(default_factory=lambda: os.getenv("USER", ""))

    nacsos: NacsosSettings
    ml: MLSettings
    sample_size: int = 20000

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file="config/snakemake.yaml"),
        )


settings = Settings()
