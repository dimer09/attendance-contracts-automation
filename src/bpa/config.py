from dataclasses import dataclass, field

from bpa.models import Severity


@dataclass(frozen=True)
class RuleSetting:
    enabled: bool = True
    severity: Severity = Severity.BLOCKING


DEFAULT_SETTINGS: dict[str, RuleSetting] = {
    "R1": RuleSetting(),
    "R2": RuleSetting(),
    "R5": RuleSetting(),
}


@dataclass(frozen=True)
class RulesConfig:
    settings: dict[str, RuleSetting] = field(default_factory=dict)

    def setting_for(self, rule_code: str) -> RuleSetting:
        if rule_code in self.settings:
            return self.settings[rule_code]
        return DEFAULT_SETTINGS.get(rule_code, RuleSetting())