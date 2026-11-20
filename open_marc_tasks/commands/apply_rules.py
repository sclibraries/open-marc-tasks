from typing import Any, Dict, List, Tuple

from ..regex_dialect import (
    RegexDialectError,
    compile_pattern,
    expand_replacement,
    validate_replacement,
)
from ..task import TaskError, _required, _unknown_settings
from ..text_form import transform_record_text


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "rules"}, number)
    rules = _required(step, "rules", number)
    if not isinstance(rules, list):
        raise TaskError("step {} setting rules must be an array".format(number))

    for rule in rules:
        if not isinstance(rule, list) or len(rule) != 3:
            raise TaskError(
                "step {} setting rules must contain [key, pattern, replacement] triples".format(
                    number
                )
            )
        key, pattern, replacement = rule
        if not isinstance(key, str) or len(key) not in (2, 3, 4) or not (
            key.startswith("=") and key[1:].isascii() and key[1:].isalnum()
        ):
            raise TaskError(
                "step {} setting rules key must be two to four ASCII characters starting with '='".format(
                    number
                )
            )
        if not isinstance(pattern, str) or not pattern:
            raise TaskError(
                "step {} setting rules pattern must be a non-empty string".format(
                    number
                )
            )
        if not isinstance(replacement, str):
            raise TaskError(
                "step {} setting rules replacement must be a string".format(number)
            )
        try:
            compile_pattern(pattern)
            validate_replacement(replacement)
        except RegexDialectError as error:
            raise TaskError("step {} {}".format(number, error)) from error


def _compiled_rules(rules: List[List[str]]) -> Dict[str, List[Tuple[Any, str]]]:
    grouped = {}
    for key, pattern, replacement in rules:
        grouped.setdefault(key, []).append((compile_pattern(pattern), replacement))
    return grouped


def run(record, step: Dict[str, Any]) -> None:
    grouped = _compiled_rules(step["rules"])

    def apply(line: str) -> str:
        for length in (4, 3, 2):
            rules = grouped.get(line[:length])
            if rules is not None:
                for pattern, replacement in rules:
                    line = pattern.sub(
                        lambda match: expand_replacement(match, replacement), line
                    )
                break
        return line

    transform_record_text(record, apply)
