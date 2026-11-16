from typing import Any, Dict, List

from pymarc import Record


def conditions_match(record: Record, conditions: List[Dict[str, Any]]) -> bool:
    """Return whether every validated Leader condition holds for a record."""
    return all(record.leader[condition["leader"]] in condition["in"] for condition in conditions)
