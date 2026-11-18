from typing import Any, Dict

from pymarc import Record

from ..task import TaskError, _required, _unknown_settings
from ..text_form import render_field


_UNDEFINED_WINDOWS_1252 = {0x81, 0x8D, 0x8F, 0x90, 0x9D}
_WINDOWS_1252 = bytes(range(256)).decode("cp1252", errors="replace")
_WINDOWS_1252 = "".join(
    chr(byte) if byte in _UNDEFINED_WINDOWS_1252 else character
    for byte, character in enumerate(_WINDOWS_1252)
)


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command", "scope"}, number)
    scope = _required(step, "scope", number)
    if scope not in ("all", "0xx"):
        raise TaskError("step {} setting scope must be 'all' or '0xx'".format(number))


def _sort_key(field) -> str:
    field_text = render_field(field).encode("utf-8")
    return "".join(_WINDOWS_1252[byte] for byte in field_text)


def run(record: Record, step: Dict[str, Any]) -> None:
    if step["scope"] == "all":
        record.fields.sort(key=_sort_key)
        return

    zero_xx = [field for field in record.fields if field.tag.startswith("0")]
    other_fields = [field for field in record.fields if not field.tag.startswith("0")]
    zero_xx.sort(key=_sort_key)
    record.fields[:] = zero_xx + other_fields
