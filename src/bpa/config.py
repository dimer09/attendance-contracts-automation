from dataclasses import dataclass, field

from bpa.models import Severity

import os
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