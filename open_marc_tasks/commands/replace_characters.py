from typing import Any, Dict, List, Tuple

from ..regex_dialect import (
    RegexDialectError,
    compile_pattern,
    expand_replacement,
    validate_replacement,
)
from ..task import TaskError, _required, _unknown_settings
from ..text_form import transform_record_text


def _validate_pairs(pairs: Any, setting: str, number: int, regex: bool) -> None:
    if not isinstance(pairs, list):
        raise TaskError("step {} setting {} must be an array".format(number, setting))
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            raise TaskError(
                "step {} setting {} must contain [find, replace] pairs".format(
                    number, setting
                )
            )
        find, replacement = pair
        if not isinstance(find, str) or not find:
            raise TaskError(
                "step {} setting {} find must be a non-empty string".format(
                    number, setting
                )
            )
        if not isinstance(replacement, str):
            raise TaskError(
                "step {} setting {} replace must be a string".format(
                    number, setting
                )
            )
        if regex:
            try:
                compile_pattern(find)
                validate_replacement(replacement)
            except RegexDialectError as error:
                raise TaskError("step {} {}".format(number, error)) from error


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "pairs", "regex_pairs"}, number)
    _validate_pairs(_required(step, "pairs", number), "pairs", number, False)
    _validate_pairs(step.get("regex_pairs", []), "regex_pairs", number, True)


def _replacements(step: Dict[str, Any]) -> List[Tuple[Any, str]]:
    return [
        (compile_pattern(find), replacement)
        for find, replacement in step.get("regex_pairs", [])
    ]


def run(record, step: Dict[str, Any]) -> None:
    literal_pairs = step["pairs"]
    regex_pairs = _replacements(step)

    def replace(line: str) -> str:
        for find, replacement in literal_pairs:
            line = line.replace(find, replacement)
        for pattern, replacement in regex_pairs:
            line = pattern.sub(
                lambda match: expand_replacement(match, replacement), line
            )
        return line

    transform_record_text(record, replace)
