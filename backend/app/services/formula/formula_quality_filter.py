"""Day 14 formula quality filter — deterministic post-inference cleansing."""

from __future__ import annotations


class QualityStatus:
    PASSED = "passed"
    FILTERED_LOW_SCORE = "filtered_low_score"
    FILTERED_DUPLICATE = "filtered_duplicate"
    CONFLICT = "conflict"


def _target_column(formula_text: str) -> str:
    """Extract the left-hand side (target column) from a formula like 'col_X = ...'."""
    if "=" not in formula_text:
        return formula_text
    return formula_text.split("=", 1)[0].strip()


def filter_formula_rules(
    rules: list[dict[str, object]],
    quality_threshold: float = 0.3,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Filter inferred formula rules for quality, duplicates, and conflicts.

    Returns three lists: (passed, filtered_out, conflicts).
    Each dict gains a ``quality_status`` key.
    """
    if not rules:
        return [], [], []

    tagged: list[dict[str, object]] = []
    filtered_out: list[dict[str, object]] = []

    # --- Pass 1: quality threshold ---
    for rule in rules:
        score = float(rule.get("verification_score", 0))
        if score < quality_threshold:
            tagged_rule = dict(rule)
            tagged_rule["quality_status"] = QualityStatus.FILTERED_LOW_SCORE
            filtered_out.append(tagged_rule)
        else:
            tagged_rule = dict(rule)
            tagged_rule["quality_status"] = QualityStatus.PASSED
            tagged.append(tagged_rule)

    # --- Pass 2: deduplicate within same sheet ---
    seen: dict[tuple[int, str], dict[str, object]] = {}
    deduped: list[dict[str, object]] = []
    for rule in tagged:
        key = (int(rule["sheet_id"]), str(rule["formula_text"]))
        if key in seen:
            existing = seen[key]
            if float(rule.get("confidence", 0)) > float(existing.get("confidence", 0)):
                existing["quality_status"] = QualityStatus.FILTERED_DUPLICATE
                filtered_out.append(existing)
                seen[key] = rule
                rule["quality_status"] = QualityStatus.PASSED
                deduped = [r for r in deduped if r is not existing] + [rule]
            else:
                rule["quality_status"] = QualityStatus.FILTERED_DUPLICATE
                filtered_out.append(rule)
        else:
            seen[key] = rule
            deduped.append(rule)

    # --- Pass 3: conflict detection ---
    target_map: dict[tuple[int, str], list[dict[str, object]]] = {}
    for rule in deduped:
        sheet_id = int(rule["sheet_id"])
        target = _target_column(str(rule["formula_text"]))
        target_map.setdefault((sheet_id, target), []).append(rule)

    passed: list[dict[str, object]] = []
    conflicts: list[dict[str, object]] = []
    for group in target_map.values():
        if len(group) > 1:
            for rule in group:
                rule["quality_status"] = QualityStatus.CONFLICT
                conflicts.append(rule)
        else:
            passed.extend(group)

    return passed, filtered_out, conflicts
