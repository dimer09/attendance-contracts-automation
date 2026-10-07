from dataclasses import dataclass, field

from bpa.models import Severity

import os
import re
from collections.abc import Mapping


@dataclass(frozen=True)
class RuleSetting:
    enabled: bool = True
    severity: Severity = Severity.BLOCKING



DEFAULT_SETTINGS: dict[str, RuleSetting] = {
    "R1": RuleSetting(),
    "R2": RuleSetting(),
    "R3": RuleSetting(severity=Severity.WARNING),  
    "R4": RuleSetting(),
    "R5": RuleSetting(),
}


@dataclass(frozen=True)
class RulesConfig:
    settings: dict[str, RuleSetting] = field(default_factory=dict)

    def setting_for(self, rule_code: str) -> RuleSetting:
        if rule_code in self.settings:
            return self.settings[rule_code]
        return DEFAULT_SETTINGS.get(rule_code, RuleSetting())


class ConfigError(Exception):
    """Raised when the program is not configured correctly."""


@dataclass(frozen=True)
class Settings:


    api_base_url: str
    api_key: str = field(repr=False)


REQUIRED_VARIABLES = ("BPA_API_URL", "BPA_API_KEY")


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    if environ is None:
        environ = os.environ
    missing = [name for name in REQUIRED_VARIABLES if not environ.get(name, "").strip()]
    if missing:
        raise ConfigError(f"Missing environment variables: {', '.join(missing)}")
    return Settings(
        api_base_url=environ["BPA_API_URL"].strip(),
        api_key=environ["BPA_API_KEY"].strip(),
    )



EMAIL_PATTERN = re.compile(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+")
SMTP_SECURITY_MODES = ("starttls", "ssl", "none")
DEFAULT_SMTP_PORTS = {"starttls": 587, "ssl": 465, "none": 25}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class SmtpSettings:
 

    host: str
    port: int
    security: str 
    sender: str
    recipients: tuple[str, ...]
    username: str | None = None
    password: str | None = field(default=None, repr=False)


def _value(environ: Mapping[str, str], name: str) -> str:
    return environ.get(name, "").strip()


def _is_valid_email(address: str) -> bool:
    return EMAIL_PATTERN.fullmatch(address) is not None


def load_smtp_settings(environ: Mapping[str, str] | None = None) -> SmtpSettings:
    if environ is None:
        environ = os.environ

    required = ("BPA_SMTP_HOST", "BPA_MAIL_FROM", "BPA_MAIL_TO")
    missing = [name for name in required if not _value(environ, name)]
    if missing:
        raise ConfigError(f"Missing environment variables: {', '.join(missing)}")

    security = _value(environ, "BPA_SMTP_SECURITY").lower() or "starttls"
    if security not in SMTP_SECURITY_MODES:
        raise ConfigError(f"BPA_SMTP_SECURITY must be one of: {', '.join(SMTP_SECURITY_MODES)}")

    host = _value(environ, "BPA_SMTP_HOST")
    if security == "none" and host.lower() not in LOCAL_HOSTS:
       
        raise ConfigError("BPA_SMTP_SECURITY=none is only allowed for a local host")

    port_text = _value(environ, "BPA_SMTP_PORT")
    if port_text:
        if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            raise ConfigError("BPA_SMTP_PORT must be a number between 1 and 65535")
        port = int(port_text)
    else:
        port = DEFAULT_SMTP_PORTS[security]

    sender = _value(environ, "BPA_MAIL_FROM")
    if not _is_valid_email(sender):
        raise ConfigError("BPA_MAIL_FROM is not a valid email address")

    recipients = tuple(
        part.strip() for part in _value(environ, "BPA_MAIL_TO").split(",") if part.strip()
    )
    if not recipients or not all(_is_valid_email(address) for address in recipients):
        raise ConfigError("BPA_MAIL_TO must hold valid email addresses separated by commas")

    username = _value(environ, "BPA_SMTP_USER") or None
    password = _value(environ, "BPA_SMTP_PASSWORD") or None
    if (username is None) != (password is None):
        missing_name = "BPA_SMTP_PASSWORD" if password is None else "BPA_SMTP_USER"
        raise ConfigError(f"Missing environment variables: {missing_name}")

    return SmtpSettings(
        host=host,
        port=port,
        security=security,
        sender=sender,
        recipients=recipients,
        username=username,
        password=password,
    )