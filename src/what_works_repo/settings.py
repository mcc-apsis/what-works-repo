import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource


class Settings(BaseSettings):
    """Settings for the what works repo."""

    model_config = SettingsConfigDict(env_file="config/.env", extra="ignore")

    ts01_username: str = Field(default_factory=lambda: os.getenv("USER", ""))

    nacsos__project_id: str = ""
    nacsos__import_id: str = ""
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
