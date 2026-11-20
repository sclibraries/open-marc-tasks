import html
import re
from html.entities import html5
from typing import Any, Dict

from ..task import _unknown_settings
from ..text_form import transform_record_text


_HEX_ENTITY = re.compile(r"&#[xX][0-9A-Fa-f]+;")
_DECIMAL_ENTITY = re.compile(r"&#[0-9]+;")
_NAMED_ENTITY = re.compile(r"&[A-Za-z][A-Za-z0-9]*;")


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command"}, number)


def _decode(line: str) -> str:
    line = _HEX_ENTITY.sub(lambda match: html.unescape(match.group(0)), line)
    line = _DECIMAL_ENTITY.sub(lambda match: html.unescape(match.group(0)), line)
    return _NAMED_ENTITY.sub(
        lambda match: html5.get(match.group(0)[1:], match.group(0)), line
    )


def run(record, step: Dict[str, Any]) -> None:
    transform_record_text(record, _decode)
