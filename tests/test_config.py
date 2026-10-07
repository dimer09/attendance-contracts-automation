import pytest

from bpa.config import ConfigError, RulesConfig, RuleSetting, load_settings
from bpa.models import Severity


def test_default_severities():
    config = RulesConfig()
    assert config.setting_for("R3").severity == Severity.WARNING
    for code in ("R1", "R2", "R4", "R5"):
        assert config.setting_for(code).severity == Severity.BLOCKING


def test_override_wins_over_default():
    config = RulesConfig(settings={"R3": RuleSetting(enabled=False)})

    assert config.setting_for("R3").enabled is False
    assert config.setting_for("R1").enabled is True  


def test_unknown_rule_code_gets_a_safe_default():
    setting = RulesConfig().setting_for("R99")
    assert setting.enabled is True
    assert setting.severity == Severity.BLOCKING

def test_settings_are_read_from_environment():
    settings = load_settings({"BPA_API_URL": " http://api.test ", "BPA_API_KEY": "secret"})

    assert settings.api_base_url == "http://api.test"  
    assert settings.api_key == "secret"


def test_all_missing_variables_are_listed():
    with pytest.raises(ConfigError) as error:
        load_settings({})

    assert "BPA_API_URL" in str(error.value)
    assert "BPA_API_KEY" in str(error.value)


def test_blank_value_counts_as_missing():
    with pytest.raises(ConfigError) as error:
        load_settings({"BPA_API_URL": "http://api.test", "BPA_API_KEY": "   "})

    assert "BPA_API_KEY" in str(error.value)
    assert "BPA_API_URL" not in str(error.value)


def test_api_key_is_hidden_from_repr():
    settings = load_settings({"BPA_API_URL": "http://api.test", "BPA_API_KEY": "super-secret"})

    assert "super-secret" not in repr(settings)
    assert "http://api.test" in repr(settings)