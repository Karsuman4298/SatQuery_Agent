import pytest
from app.agent.registry import missing_inputs


def test_pair_specialists_require_both_observations():
    assert missing_inputs('change_detection', {'before': 'image'}) == ['after']
    assert missing_inputs('fusion', {'optical': 'image'}) == ['sar']
    assert missing_inputs('fusion', {'optical': 'a', 'sar': 'b'}) == []


def test_unknown_tools_are_never_allowed():
    with pytest.raises(ValueError):
        missing_inputs('invented_tool', {})
