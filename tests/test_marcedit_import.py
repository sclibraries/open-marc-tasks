import json
import zipfile

import pytest

from open_marc_tasks.cli import main
from open_marc_tasks.marcedit_import import import_marcedit
from open_marc_tasks.task import load_task


@pytest.mark.parametrize(
    "line,step",
    [
        (
            "DELETE\t245\t\t0\tFalse\tFalse\tFalse\tFalse\tFalse",
            {"command": "delete_field", "tag": "245"},
        ),
        (
            "DELETE\t9XX\t\t0\tFalse\tFalse\tFalse\tFalse\tFalse",
            {"command": "delete_field", "tag": "9XX"},
        ),
        (
            "ADD\t506\t1\\$aSynthetic text\t100\t",
            {
                "command": "add_field",
                "tag": "506",
                "ind1": "1",
                "ind2": " ",
                "subfields": [["a", "Synthetic text"]],
                "if_tag_exists": "add",
            },
        ),
        (
            "ADD\t650\t\\0$aSynthetic topic\t101\t",
            {
                "command": "add_field",
                "tag": "650",
                "ind1": " ",
                "ind2": "0",
                "subfields": [["a", "Synthetic topic"]],
                "if_tag_exists": "skip",
            },
        ),
        (
            "ADD\t650\t\\0$aSynthetic topic\t108\t",
            {
                "command": "add_field",
                "tag": "650",
                "ind1": " ",
                "ind2": "0",
                "subfields": [["a", "Synthetic topic"]],
                "if_tag_exists": "skip_if_identical",
            },
        ),
        (
            "ADD\t655\t\\7$aSynthetic genre\t106\t/=LDR.{8}[amt][m].+/",
            {
                "command": "add_field",
                "tag": "655",
                "ind1": " ",
                "ind2": "7",
                "subfields": [["a", "Synthetic genre"]],
                "if_tag_exists": "add",
                "when": [
                    {"leader": 6, "in": ["a", "m", "t"]},
                    {"leader": 7, "in": ["m"]},
                ],
            },
        ),
        (
            "ADD\t655\t\\7$aSynthetic genre\t106\t/=LDR.{9}s.+/",
            {
                "command": "add_field",
                "tag": "655",
                "ind1": " ",
                "ind2": "7",
                "subfields": [["a", "Synthetic genre"]],
                "if_tag_exists": "add",
                "when": [{"leader": 7, "in": ["s"]}],
            },
        ),
        (
            "ADD\t500\t\\\\$aCost {dollar} 5\t100\t",
            {
                "command": "add_field",
                "tag": "500",
                "ind1": " ",
                "ind2": " ",
                "subfields": [["a", "Cost $ 5"]],
                "if_tag_exists": "add",
            },
        ),
        (
            "ADD\t006\tm         \t100\t",
            {
                "command": "add_field",
                "tag": "006",
                "data": "m         ",
                "if_tag_exists": "add",
            },
        ),
        (
            "SUBFIELD_EDIT\t949\ta\t\tOnline\t102|0",
            {"command": "edit_subfield", "tag": "949", "code": "a", "action": "add", "value": "Online"},
        ),
        (
            "SUBFIELD_EDIT\t950\ta\tneedle\tREPL\t0|0",
            {"command": "edit_subfield", "tag": "950", "code": "a", "action": "replace", "find": "needle", "replace": "REPL"},
        ),
        (
            "SUBFIELD_EDIT\t951\ta\t^e\t-END\t0|0",
            {"command": "edit_subfield", "tag": "951", "code": "a", "action": "append", "value": "-END"},
        ),
        (
            "SUBFIELD_EDIT\t952\ta\t^b\tSTART-\t0|0",
            {"command": "edit_subfield", "tag": "952", "code": "a", "action": "prepend", "value": "START-"},
        ),
        (
            "SUBFIELD_EDIT\t956\th\t\tOnline\t101|0",
            {"command": "edit_subfield", "tag": "956", "code": "h", "action": "add_if_missing", "value": "Online"},
        ),
        (
            "SUBFIELD_EDIT\t957\ta\tneedle\t\t0|0",
            {"command": "edit_subfield", "tag": "957", "code": "a", "action": "replace", "find": "needle", "replace": ""},
        ),
        (
            "SUBFIELD_EDIT\t958\ta\t\t\t0|0",
            {"command": "edit_subfield", "tag": "958", "code": "a", "action": "clear"},
        ),
        (
            "SUBFIELD_EDIT\t959\ta\tneedle\tREPL\t0|1",
            {"command": "edit_subfield", "tag": "959", "code": "a", "action": "replace_first", "find": "needle", "replace": "REPL"},
        ),
    ],
)
def test_import_translates_supported_lines_into_valid_tasks(tmp_path, line, step):
    source = tmp_path / "Synthetic task.txt"
    source.write_text("#DESCRIPTION#\tSynthetic description\n" + line + "\n", encoding="utf-8")

    result = import_marcedit(source)

    assert result.not_translated == []
    assert len(result.tasks) == 1
    imported = result.tasks[0]
    assert imported.name == "Synthetic task"
    assert imported.document == {
        "format_version": "0.1",
        "name": "Synthetic task",
        "description": "Synthetic description",
        "steps": [step],
    }
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(imported.document), encoding="utf-8")
    assert load_task(task_path).steps == [step]


@pytest.mark.parametrize(
    "line",
    [
        "DELETE\t245\t$aSynthetic match\t0\tFalse\tFalse\tFalse\tFalse\tFalse",
        "DELETE\t245\t\t0\tTrue\tFalse\tFalse\tFalse\tFalse",
        "ADD\t655\t\\7$aSynthetic genre\t106\t//=LDR.{8}[amt][m].+//",
        "ADD\t650\t\\0$aSynthetic topic\t999\t",
        "ADD\t650\t\\0$aCaf{eacute}\t100\t",
        "SUBFIELD_EDIT\t950\ta\tneed.*le\tX\t0|2",
        "TASK_LIST\tSynthetic task list",
        "MYSTERY\tSynthetic unknown command",
    ],
)
def test_import_preserves_unsupported_lines_for_review(tmp_path, line):
    source = tmp_path / "Synthetic task.txt"
    source.write_text(
        "#DESCRIPTION#\tSynthetic description\n\n" + line + "\n",
        encoding="utf-8",
    )

    result = import_marcedit(source)

    assert len(result.not_translated) == 1
    item = result.not_translated[0]
    assert item.source == "Synthetic task.txt"
    assert item.line_number == 3
    assert item.text == line
    if line.startswith("SUBFIELD_EDIT"):
        assert item.reason == "SUBFIELD_EDIT regular expressions are not supported yet"
    else:
        assert item.reason and "\n" not in item.reason


def test_task_zip_import_writes_only_complete_tasks_and_reports_partial_lines(tmp_path, capsys):
    archive = tmp_path / "Synthetic tasks.task"
    complete_line = "ADD\t650\t\\0$aSynthetic topic\t100\t"
    unsupported_line = "MYSTERY\tSynthetic command"
    with zipfile.ZipFile(archive, "w") as task_zip:
        task_zip.writestr(
            "Complete.txt",
            "#DESCRIPTION#\tFully translated\n" + complete_line + "\n",
        )
        task_zip.writestr(
            "Partial.txt",
            "#DESCRIPTION#\tNeeds review\n\n" + unsupported_line + "\n",
        )

    imported = import_marcedit(archive)
    assert [task.name for task in imported.tasks] == ["Complete", "Partial"]
    assert [
        (item.source, item.line_number, item.text)
        for item in imported.not_translated
    ] == [("Partial.txt", 3, unsupported_line)]

    output_dir = tmp_path / "output"
    exit_code = main(["import", str(archive), str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == (
        "Partial.txt:3: unknown MarcEdit command\n"
        "2 tasks, 1 lines not translated; not written: Partial\n"
    )
    assert sorted(path.name for path in output_dir.iterdir()) == ["Complete.json"]
    assert load_task(output_dir / "Complete.json").name == "Complete"
