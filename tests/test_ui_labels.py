from campaign_assistant.ui.labels import format_tristate


def test_format_tristate_true():
    assert format_tristate(True) == "Yes"


def test_format_tristate_false():
    assert format_tristate(False) == "No"


def test_format_tristate_unknown():
    assert format_tristate(None) == "Unknown"