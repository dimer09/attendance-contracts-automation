import pytest

from bpa.config import ConfigError, RulesConfig, RuleSetting, load_settings, load_smtp_settings
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


SMTP_ENV = {
    "BPA_SMTP_HOST": "smtp.example.com",
    "BPA_MAIL_FROM": "bpa@example.com",
    "BPA_MAIL_TO": "manager@example.com",
}


def smtp_env(**overrides):
    return {**SMTP_ENV, **overrides}


def test_smtp_minimal_settings_use_safe_defaults():
    settings = load_smtp_settings(smtp_env())

    assert settings.host == "smtp.example.com"
    assert settings.security == "starttls"
    assert settings.port == 587
    assert settings.sender == "bpa@example.com"
    assert settings.recipients == ("manager@example.com",)
    assert settings.username is None and settings.password is None


def test_smtp_default_port_follows_the_security_mode():
    assert load_smtp_settings(smtp_env(BPA_SMTP_SECURITY="ssl")).port == 465
    assert load_smtp_settings(smtp_env(BPA_SMTP_SECURITY="ssl", BPA_SMTP_PORT="2465")).port == 2465


def test_smtp_recipients_are_split_and_cleaned():
    settings = load_smtp_settings(smtp_env(BPA_MAIL_TO=" a@example.com , b@example.com,"))

    assert settings.recipients == ("a@example.com", "b@example.com")


def test_smtp_missing_variables_are_listed():
    with pytest.raises(ConfigError) as error:
        load_smtp_settings({})

    for name in ("BPA_SMTP_HOST", "BPA_MAIL_FROM", "BPA_MAIL_TO"):
        assert name in str(error.value)


@pytest.mark.parametrize(
    "value",
    ["not-an-address", "a@b.com\nBcc: evil@x.com", "a@@b.com", "a b@c.com"],
)
def test_invalid_recipients_are_rejected(value):
    with pytest.raises(ConfigError, match="BPA_MAIL_TO"):
        load_smtp_settings(smtp_env(BPA_MAIL_TO=value))


def test_invalid_sender_is_rejected():
    with pytest.raises(ConfigError, match="BPA_MAIL_FROM"):
        load_smtp_settings(smtp_env(BPA_MAIL_FROM="bpa"))


@pytest.mark.parametrize("port", ["abc", "0", "70000"])
def test_invalid_port_is_rejected(port):
    with pytest.raises(ConfigError, match="BPA_SMTP_PORT"):
        load_smtp_settings(smtp_env(BPA_SMTP_PORT=port))


def test_unknown_security_mode_is_rejected():
    with pytest.raises(ConfigError, match="BPA_SMTP_SECURITY"):
        load_smtp_settings(smtp_env(BPA_SMTP_SECURITY="tls"))


@pytest.mark.parametrize(
    "extra, missing_name",
    [
        ({"BPA_SMTP_USER": "bpa-user"}, "BPA_SMTP_PASSWORD"),
        ({"BPA_SMTP_PASSWORD": "secret"}, "BPA_SMTP_USER"),
    ],
)
def test_half_credentials_are_rejected(extra, missing_name):
    with pytest.raises(ConfigError, match=missing_name):
        load_smtp_settings(smtp_env(**extra))


def test_credentials_are_loaded_together():
    settings = load_smtp_settings(smtp_env(BPA_SMTP_USER="bpa-user", BPA_SMTP_PASSWORD="secret"))

    assert settings.username == "bpa-user"
    assert settings.password == "secret"


def test_unencrypted_connection_is_refused_for_remote_hosts():
    with pytest.raises(ConfigError, match="local host"):
        load_smtp_settings(smtp_env(BPA_SMTP_SECURITY="none"))


def test_unencrypted_connection_is_allowed_on_localhost():
    settings = load_smtp_settings(smtp_env(BPA_SMTP_SECURITY="none", BPA_SMTP_HOST="127.0.0.1"))

    assert settings.security == "none"
    assert settings.port == 25


def test_smtp_password_is_hidden_from_repr():
    settings = load_smtp_settings(
        smtp_env(BPA_SMTP_USER="bpa-user", BPA_SMTP_PASSWORD="super-smtp-secret")
    )

    assert "super-smtp-secret" not in repr(settings)
    assert "smtp.example.com" in repr(settings)
