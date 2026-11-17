import json
from pathlib import Path

import jsonschema
import pytest
from pymarc import Field, Record, Subfield

from open_marc_tasks import TaskError, load_task, run_task


VALID_STEP = {"command": "delete_field", "tag": "999"}
INVALID_DOCUMENTS = [
    ("non-boolean normalize_typography", {"format_version": "0.1", "name": "x", "description": "x", "normalize_typography": "yes", "steps": [VALID_STEP]}, None),
    ("wrong version", {"format_version": "9.9", "name": "x", "description": "x", "steps": [VALID_STEP]}, None),
    ("missing command", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"tag": "999"}]}, "step 2"),
    ("unknown command", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "unknown"}]}, "step 2"),
    ("missing tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field"}]}, "step 2"),
    ("short tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "9X"}]}, "step 2"),
    ("trailing newline tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "999\n"}]}, "step 2"),
    ("lowercase tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "9xx"}]}, "step 2"),
    ("nondigit tag", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "abc"}]}, "step 2"),
    ("unknown setting", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "999", "case_sensitive": True}]}, "step 2"),
    ("delete_field non-string match", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "650", "match": 1}]}, "step 2"),
    ("delete_field non-boolean match_regex", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "delete_field", "tag": "650", "match": "x", "match_regex": "yes"}]}, "step 2"),
    ("step is not an object", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, "delete 999"]}, "step 2"),
    ("add missing subfields", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0"}]}, "step 2"),
    ("add bad indicator length", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": "  ", "ind2": "0", "subfields": [["a", "Topic"]]}]}, "step 2"),
    ("add bad subfield code", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["A", "Topic"]]}]}, "step 2"),
    ("add unknown if_tag_exists", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["a", "Topic"]], "if_tag_exists": "unknown"}]}, "step 2"),
    ("add Leader position 24", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["a", "Topic"]], "when": [{"leader": 24, "in": ["a"]}]}]}, "step 2"),
    ("add empty condition in", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "add_field", "tag": "650", "ind1": " ", "ind2": "0", "subfields": [["a", "Topic"]], "when": [{"leader": 7, "in": []}]}]}, "step 2"),
    ("edit_subfield bad code", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "edit_subfield", "tag": "650", "code": "A", "action": "add", "value": "Topic"}]}, "step 2"),
    ("edit_subfield unknown action", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "edit_subfield", "tag": "650", "code": "a", "action": "change", "value": "Topic"}]}, "step 2"),
    ("edit_subfield missing value", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "edit_subfield", "tag": "650", "code": "a", "action": "add"}]}, "step 2"),
    ("replace_text empty find", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "replace_text", "find": "", "replace": "x"}]}, "step 2"),
    ("replace_text non-string replace", {"format_version": "0.1", "name": "x", "description": "x", "steps": [VALID_STEP, {"command": "replace_text", "find": "x", "replace": 1}]}, "step 2"),
]


def task_document(steps=None, format_version="0.1"):
    return {
        "format_version": format_version,
        "name": "Synthetic delete-field task",
        "description": "Removes a synthetic local field.",
        "steps": steps if steps is not None else [{"command": "delete_field", "tag": "999"}],
    }


REGEX_INVALID_DOCUMENTS = [
    (
        "replace_text invalid regex pattern {}".format(pattern),
        task_document(
            [
                VALID_STEP,
                {"command": "replace_text", "find": pattern, "replace": "x", "regex": True},
            ]
        ),
        "step 2",
        True,
    )
    for pattern in (
        "(?=a)",
        "(?i)a",
        "a+?",
        "a++",
        "(?>a)",
        "a{,3}",
        r"(a)\1",
        r"\bx",
        "[a-z-[aeiou]]",
        "[a&&b]",
        "[",
        "(",
        "a{3,1}",
        "x*",
        "a*|b",
    )
]
REGEX_INVALID_DOCUMENTS.extend(
    (
        "replace_text invalid regex replacement {}".format(replacement),
        task_document(
            [
                VALID_STEP,
                {"command": "replace_text", "find": "(a)", "replace": replacement, "regex": True},
            ]
        ),
        "step 2",
        True,
    )
    for replacement in ("$12", "$0", "$&", "${1}")
)
REGEX_INVALID_DOCUMENTS.append(
    (
        "delete_field invalid regex pattern",
        task_document(
            [
                VALID_STEP,
                {"command": "delete_field", "tag": "650", "match": "(?=a)", "match_regex": True},
            ]
        ),
        "step 2",
        True,
    )
)
INVALID_TASK_CASES = [
    (name, document, step_number, False)
    for name, document, step_number in INVALID_DOCUMENTS
] + [
    (
        "replace_text non-boolean regex",
        task_document(
            [
                VALID_STEP,
                {"command": "replace_text", "find": "a", "replace": "b", "regex": "yes"},
            ]
        ),
        "step 2",
        False,
    )
] + REGEX_INVALID_DOCUMENTS


@pytest.fixture
def task_schema():
    schema_path = Path(__file__).resolve().parents[1] / "spec" / "task.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name,document,step_number,schema_valid", INVALID_TASK_CASES)
def test_invalid_tasks_are_rejected_by_loader_and_schema(
    tmp_path, task_schema, name, document, step_number, schema_valid
):
    task_path = tmp_path / (name.replace(" ", "-") + ".json")
    task_path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(TaskError) as error:
        load_task(task_path)
    if step_number:
        assert step_number in str(error.value)
    if name == "replace_text empty find":
        assert "setting find" in str(error.value)
    if name == "replace_text non-string replace":
        assert "setting replace" in str(error.value)
    if name == "replace_text non-boolean regex":
        assert "regex" in str(error.value)
    if name == "delete_field non-string match":
        assert "match" in str(error.value)
    if name == "delete_field non-boolean match_regex":
        assert "match_regex" in str(error.value)
    if name == "delete_field invalid regex pattern":
        assert "special groups are not supported" in str(error.value)
    if schema_valid:
        jsonschema.validate(document, task_schema)
    else:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(document, task_schema)


@pytest.mark.parametrize(
    "pattern", [r"\(\?i\)", r"\\b", "[+?]", "[(]x"]
)
def test_regex_dialect_accepts_escaped_and_in_class_metacharacters(
    tmp_path, task_schema, pattern
):
    document = task_document(
        [{"command": "replace_text", "find": pattern, "replace": "x", "regex": True}]
    )
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(document), encoding="utf-8")

    jsonschema.validate(document, task_schema)
    assert load_task(task_path).steps[0]["regex"] is True


@pytest.mark.parametrize(
    "tag,value,find,replacement,regex,expected",
    [
        ("245", "٣", r"^=245  10\$a\d$", "X", True, "٣"),
        ("245", "é", r"^=245  10\$a\w$", "X", True, "é"),
        ("245", " ", r"^=245  10\$a\s$", "X", True, " "),
        ("245", "é", r"^(=245  10\$a).$", "$1X", True, "X"),
        ("245", "𐐀", r"^(=245  10\$a).$", "$1X", True, "X"),
        ("245", "abc\n", r"^(=245  10\$a)(abc)$", "$1$2X", True, "abc\n"),
        ("001", "a.b(", "a.b(", "$1", False, "$1"),
    ],
)
def test_replace_text_uses_portable_regex_character_and_plain_literal_semantics(
    tmp_path, tag, value, find, replacement, regex, expected
):
    task_path = tmp_path / "task.json"
    task_path.write_text(
        json.dumps(
            task_document(
                [{"command": "replace_text", "find": find, "replace": replacement, "regex": regex}]
            )
        ),
        encoding="utf-8",
    )
    record = Record()
    if tag.startswith("00"):
        record.add_field(Field(tag=tag, data=value))
    else:
        record.add_field(
            Field(tag=tag, indicators=["1", "0"], subfields=[Subfield("a", value)])
        )

    result = list(run_task(load_task(task_path), [record]))

    if tag.startswith("00"):
        actual = result[0][tag].data
    else:
        actual = result[0][tag]["a"]
    assert actual == expected


@pytest.mark.parametrize("contents", ['{"format_version":', None])
def test_unreadable_or_malformed_task_raises_task_error(tmp_path, contents):
    task_path = tmp_path / "broken.json"
    if contents is not None:
        task_path.write_text(contents, encoding="utf-8")

    with pytest.raises(TaskError):
        load_task(task_path)


def test_run_task_consumes_generator_once_and_mutates_records_in_order(tmp_path):
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task_document()), encoding="utf-8")
    task = load_task(task_path)
    records = []
    for identifier in ("one", "two", "three"):
        record = Record()
        record.add_field(Field(tag="001", data=identifier))
        record.add_field(Field(tag="999", indicators=[" ", " "], subfields=[Subfield("a", "remove")]))
        record.add_field(Field(tag="245", indicators=["1", "0"], subfields=[Subfield("a", "Café archive")]))
        records.append(record)

    result = list(run_task(task, (record for record in records)))

    assert result == records
    assert [record["001"].data for record in result] == ["one", "two", "three"]
    assert all(record.get_fields("999") == [] for record in records)
    assert all(record["245"]["a"] == "Café archive" for record in records)


def test_replace_text_preserves_unrelated_typography_by_default(tmp_path):
    task_path = tmp_path / "task.json"
    task_path.write_text(
        json.dumps(
            task_document(
                [{"command": "replace_text", "find": "TOKEN", "replace": "Changed"}]
            )
        ),
        encoding="utf-8",
    )
    record = Record()
    record.add_field(
        Field(
            tag="245",
            indicators=["1", "0"],
            subfields=[Subfield("a", "“Quoted” — dash NBSP TOKEN")],
        )
    )

    result = list(run_task(load_task(task_path), [record]))

    assert result[0]["245"]["a"] == "“Quoted” — dash NBSP Changed"
