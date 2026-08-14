from app.extraction.normalize import normalize


def test_normalizes_thousands() -> None:
    result = normalize("12,345", "$K")
    assert result.normalized_value == 12_345_000.0
    assert result.needs_review is False


def test_normalizes_percent() -> None:
    result = normalize("45", "%")
    assert result.normalized_value == 0.45
    assert result.needs_review is False


def test_normalizes_plain_number_with_no_unit() -> None:
    result = normalize("42", "")
    assert result.normalized_value == 42.0
    assert result.needs_review is False


def test_parenthesized_value_is_negative() -> None:
    result = normalize("(1,234)", "")
    assert result.normalized_value == -1234.0


def test_unparsable_value_needs_review() -> None:
    result = normalize("not a number", "$K")
    assert result.normalized_value is None
    assert result.needs_review is True
    assert result.reason


def test_unrecognized_unit_needs_review() -> None:
    result = normalize("100", "widgets")
    assert result.normalized_value is None
    assert result.needs_review is True
    assert "widgets" in result.reason
