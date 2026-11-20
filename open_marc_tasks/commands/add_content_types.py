from typing import Any, Dict, List, Optional, Tuple

from pymarc import Field, Record, Subfield

from .add_field import insert_fields
from ..task import _unknown_settings


CONTENT_TYPES = {
    "a": ("text", "txt"),
    "b": ("unspecified", "zzz"),
    "c": ("notated music", "ntm"),
    "d": ("tactile notated music", "tcn"),
    "e": ("cartographic image", "cri"),
    "f": ("cartographic image", "cri"),
    "g": ("two-dimensional moving image", "tdi"),
    "h": ("unspecified", "zzz"),
    "i": ("spoken word", "spw"),
    "j": ("performed music", "prm"),
    "k": ("still image", "sti"),
    "l": ("unspecified", "zzz"),
    "m": ("computer dataset", "cod"),
    "n": ("unspecified", "zzz"),
    "o": ("other", "xxx"),
    "p": ("other", "xxx"),
    "q": ("unspecified", "zzz"),
    "r": ("three-dimensional artifact", None),
    "s": ("unspecified", "zzz"),
    "t": ("text", "txt"),
    "w": ("unspecified", "zzz"),
    " ": ("unspecified", "zzz"),
}

MEDIA_CARRIERS = {
    "c": (
        ("computer", "c"),
        {
            "a": ("computer tape cartridge", "ca"),
            "b": ("computer chip cartridge", "cb"),
            "d": ("computer disc", "cd"),
            "e": ("computer disc cartridge", "ce"),
            "f": ("computer tape cassette", "cf"),
            "h": ("computer tape reel", "ch"),
            "k": ("computer card", "ck"),
            "r": ("online resource", "cr"),
        },
        ("other", "cz"),
    ),
    "g": (
        ("projected", "g"),
        {
            "c": ("filmstrip cartridge", "gc"),
            "d": ("filmslip", "gd"),
            "f": ("filmstrip", "gf"),
            "s": ("slide", "gs"),
            "t": ("overhead transparency", "gt"),
        },
        ("other", "mz"),
    ),
    "h": (
        ("microform", "h"),
        {
            "a": ("aperture card", "ha"),
            "b": ("microfilm cartridge", "hb"),
            "c": ("microfilm cassette", "hc"),
            "d": ("microfilm reel", "hd"),
            "e": ("microfiche", "he"),
            "f": ("microfiche cassette", "hf"),
            "g": ("microopaque", "hg"),
            "h": ("microfilm slip", "hh"),
            "j": ("microfilm roll", "hj"),
        },
        ("other", "hz"),
    ),
    "m": (
        ("motion picture", "g"),
        {
            "c": ("film cartridge", "mc"),
            "f": ("film cassette", "mf"),
            "o": ("film roll", "mo"),
            "r": ("film reel", "mr"),
        },
        ("other", "mz"),
    ),
    "s": (
        ("audio", "s"),
        {
            "b": ("audio belt", "sb"),
            "d": ("audio disc", "sd"),
            "e": ("audio cylinder", "se"),
            "g": ("audio cartridge", "sg"),
            "i": ("sound track reel", "si"),
            "q": ("audio roll", "sq"),
            "s": ("audiocassette", "ss"),
            "t": ("audiotape reel", "st"),
            "w": ("udio wire reel", "sw"),
        },
        ("other", "sz"),
    ),
    "v": (
        ("video", "v"),
        {
            "c": ("video cartridge", "vc"),
            "d": ("videodisc", "vd"),
            "f": ("videocassette", "vf"),
            "r": ("videotape reel", "vr"),
        },
        ("other", "vz"),
    ),
    "z": (("other", "x"), {}, ("unspecified", "zu")),
}


def validate(step: Dict[str, Any], number: int) -> None:
    _unknown_settings(step, {"command"}, number)


def _data_field(tag: str, value: str, code: Optional[str], source: str) -> Field:
    subfields = [Subfield("a", value)]
    if code is not None:
        subfields.append(Subfield("b", code))
    subfields.append(Subfield("2", source))
    return Field(tag=tag, indicators=[" ", " "], subfields=subfields)


def _content_field(record: Record) -> Optional[Field]:
    content = CONTENT_TYPES.get(record.leader[6])
    if content is None:
        return None
    return _data_field("336", content[0], content[1], "rdacontent")


def _media_carrier_fields(record: Record) -> Tuple[List[Field], List[Field]]:
    fields_007 = record.get_fields("007")
    if not fields_007:
        return (
            [_data_field("337", "unmediated", "n", "rdamedia")],
            [_data_field("338", "volume", "nc", "rdacarrier")],
        )
    if any(len(field.data) < 2 for field in fields_007):
        return [], []

    media_fields = []
    carrier_fields = []
    for field in fields_007:
        mapping = MEDIA_CARRIERS.get(field.data[0])
        if mapping is None:
            media = ("unmediated", "n")
            carrier = ("volume", "nc")
        else:
            media, carriers, fallback = mapping
            carrier = carriers.get(field.data[1], fallback)
        media_fields.append(_data_field("337", media[0], media[1], "rdamedia"))
        carrier_fields.append(_data_field("338", carrier[0], carrier[1], "rdacarrier"))
    return media_fields, carrier_fields


def run(record: Record, step: Dict[str, Any]) -> None:
    fields_by_tag: Dict[str, List[Field]] = {"336": [], "337": [], "338": []}

    if not record.get_fields("336"):
        content_field = _content_field(record)
        if content_field is not None:
            fields_by_tag["336"].append(content_field)

    if (
        record.leader[6] in CONTENT_TYPES
        and not record.get_fields("337")
        and not record.get_fields("338")
    ):
        media_fields, carrier_fields = _media_carrier_fields(record)
        fields_by_tag["337"].extend(media_fields)
        fields_by_tag["338"].extend(carrier_fields)

    for tag, fields in fields_by_tag.items():
        if fields:
            insert_fields(record, fields)
