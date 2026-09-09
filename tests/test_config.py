"""Sample tests for config

Mainly here to have some tests...
"""

import pytest
from pydantic import ValidationError

from inferapi.config import SecurityConfig, TrainingSettings


def test_yaml_loads_into_typed_sections():
    settings = TrainingSettings()
    assert settings.data.parquet_path.suffix == ".parquet"
    assert settings.training.n_estimators == 100
    assert settings.logging.level == "INFO"


# NOTE(LAB): monkeypatch is noteworthy, more on this on later class
# Monkeypatch is a builtin fixture of pytest
def test_environment_overrides_yaml(monkeypatch):
    monkeypatch.setenv("ML520_TRAINING__MAX_DEPTH", "3")
    assert TrainingSettings().training.max_depth == 3


def test_api_key_check_without_a_token_is_refused():
    with pytest.raises(ValidationError):
        SecurityConfig(enable_api_key_check=True, api_token=None)
