"""Typed configuration: configs/config.yaml for structure, .env for secrets/overrides.

YAML provides the committed values; environment variables and .env override them,
with `__` as the nesting separator and ML520_ as the prefix
(e.g. ML520_SERVING__PREDICTION_THRESHOLD=0.35).
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, SecretStr, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class DataConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The CSV is what upstream ships; the parquet is what we train on.
    csv_path: Path = Path("data") / "dataset.csv"
    parquet_path: Path = Path("data") / "dataset.parquet"


class TrainingConfig(BaseModel):
    """Contains hyperparameters and other potential flags"""

    model_config = ConfigDict(extra="forbid")

    n_estimators: int = 100
    max_depth: int = 8
    test_size: float = 0.2
    val_size: float = 0.2
    seed: int = 0

    # The probability above which we call a client a subscriber.
    # The metrics from the pipeline depend on it
    # If you want to achieve same performance in serving than in training,
    # serving.prediction_threshold - must match this value
    decision_threshold: float = 0.5


class ServingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_path: Path
    prediction_threshold: float = 0.5
    simulate_work_ms: int = 0


class LoggingConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = "INFO"
    debug_file: Path | None = Path("out/logs/app.log")


class SecurityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enable_api_key_check: bool = True

    # Using SecretStr gives us a bit more security by
    # forcing the caller to call .get_secret_value(), otherwise
    # printing it shows '**********'
    api_token: SecretStr | None = None

    @model_validator(mode="after")
    def _token_required_when_check_enabled(self) -> "SecurityConfig":
        # Fail at configuration load
        if self.enable_api_key_check and self.api_token is None:
            raise ValueError(
                "security.enable_api_key_check is true but security.api_token is unset: "
                "run `make secrets-init`, or turn the check off on purpose"
            )
        return self


class WithYamlSources(BaseSettings):
    """Intermediary class that sets the source priority."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            file_secret_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )


class TrainingSettings(WithYamlSources):
    """Everything the training entrypoint needs.

    Provided as the worked example. Note what is absent: no security section, so no
    code reachable from `inferapi train` can read the API token, however hard it
    tries. That is the whole reason there are two of these and not one.
    """

    model_config = SettingsConfigDict(
        yaml_file="configs/config.yaml",
        env_file=".env",
        env_nested_delimiter="__",
        # This means we can use ML520_<value> to set fields of this object
        env_prefix="ML520_",
        # NOTE(LAB): Since we are using the same config.yaml file
        #            for both Training and InferAPI, we must set this to "ignore".
        #            Note that nonetheless, each BaseModel (ex: logging),
        #            sets extra="forbid"
        extra="ignore",
    )

    data: DataConfig
    training: TrainingConfig
    logging: LoggingConfig


class InferApiSettings(WithYamlSources):
    model_config = SettingsConfigDict(
        yaml_file="configs/config.yaml",
        env_file=".env",
        env_nested_delimiter="__",
        # This means we can use ML520_<value> to set fields of this object
        env_prefix="ML520_",
        # NOTE(LAB): Set to "ignore", rather than "forbid": see above
        extra="ignore",
    )

    security: SecurityConfig
    serving: ServingConfig
    logging: LoggingConfig
