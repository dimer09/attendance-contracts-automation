from bpa.config import RulesConfig, RuleSetting
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