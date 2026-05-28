
from app.services.formula.formula_quality_filter import (
    QualityStatus,
    filter_formula_rules,
)


def _rule(
    id: int,
    sheet_id: int,
    formula_text: str,
    verification_score: float = 0.8,
    confidence: float = 0.9,
) -> dict[str, object]:
    return {
        "id": id,
        "sheet_id": sheet_id,
        "formula_text": formula_text,
        "formula_type": "column_arithmetic",
        "confidence": confidence,
        "verification_score": verification_score,
    }


def test_filter_rejects_rules_below_quality_threshold():
    rules = [
        _rule(1, 1, "col_C = col_A + col_B", verification_score=0.05),
        _rule(2, 1, "col_D = col_A - col_B", verification_score=0.85),
    ]
    passed, filtered, conflicts = filter_formula_rules(rules, quality_threshold=0.3)
    assert len(passed) == 1
    assert len(filtered) == 1
    assert len(conflicts) == 0
    assert passed[0]["id"] == 2
    assert passed[0]["quality_status"] == QualityStatus.PASSED
    assert filtered[0]["id"] == 1
    assert filtered[0]["quality_status"] == QualityStatus.FILTERED_LOW_SCORE


def test_filter_deduplicates_same_formula_in_same_sheet():
    rules = [
        _rule(1, 1, "col_C = col_A - col_B", confidence=0.9),
        _rule(2, 1, "col_C = col_A - col_B", confidence=0.6),
    ]
    passed, filtered, conflicts = filter_formula_rules(rules, quality_threshold=0.3)
    assert len(passed) == 1
    assert len(filtered) == 1
    assert passed[0]["id"] == 1  # 保留高 confidence
    assert filtered[0]["quality_status"] == QualityStatus.FILTERED_DUPLICATE


def test_filter_detects_same_target_different_formula_as_conflict():
    rules = [
        _rule(1, 1, "col_C = col_A - col_B", confidence=0.9),
        _rule(2, 1, "col_C = col_A + col_B", confidence=0.8),
    ]
    passed, filtered, conflicts = filter_formula_rules(rules, quality_threshold=0.3)
    assert len(passed) == 0
    assert len(filtered) == 0
    assert len(conflicts) == 2
    assert all(c["quality_status"] == QualityStatus.CONFLICT for c in conflicts)


def test_filter_allows_all_when_above_threshold_no_conflicts():
    rules = [
        _rule(1, 1, "col_C = col_A - col_B", verification_score=0.8),
        _rule(2, 2, "col_D = col_A + col_B", verification_score=0.9),
    ]
    passed, filtered, conflicts = filter_formula_rules(rules, quality_threshold=0.3)
    assert len(passed) == 2
    assert len(filtered) == 0
    assert len(conflicts) == 0


def test_filter_returns_empty_lists_for_empty_input():
    passed, filtered, conflicts = filter_formula_rules([], quality_threshold=0.3)
    assert passed == []
    assert filtered == []
    assert conflicts == []
