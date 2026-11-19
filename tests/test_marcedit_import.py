import json
import zipfile

import pytest

from open_marc_tasks.cli import main
from open_marc_tasks.marcedit_import import import_marcedit
from open_marc_tasks.task import load_task


GATHER_LOOP_REPLACE = "\t".join(
    [
        "REPLACE",
        r"(=856)([^\r\n]*?)(\$u[^\r\n]*)(.*)(=945[^\n\r]*)(.*)/m",
        r"=999$2$3$4$5$3$6",
        "2",
        "",
        "0",
        "False",
    ]
)
GATHER_LOOP_DELETE = "\t".join(
    ["DELETE", "999", "", "0", "False", "False", "False", "False", "False"]
)
GATHER_LOOP_WITH_DELETE = "\n".join(
    ["#STARTLOOP:r=0", GATHER_LOOP_REPLACE, "#ENDLOOP", GATHER_LOOP_DELETE]
)
GATHER_LOOP_WITHOUT_DELETE = "\n".join(
    ["#STARTLOOP:r=0", GATHER_LOOP_REPLACE, "#ENDLOOP"]
)
GATHER_LOOP_UNCORRECTED = "\n".join(
    [
        "#STARTLOOP:r=0",
        "\t".join(
            [
                "REPLACE",
                r"(=856)(.*)(\$u[^\r\n]*)(.*)(=945[^\n\r]*)(.*)/m",
                r"=999$2$3$4$5$3$6",
                "2",
                "",
                "0",
                "False",
            ]
        ),
        "#ENDLOOP",
        GATHER_LOOP_DELETE,
    ]
)


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
            "DELETE\t9xx\t\t0\tFalse\tFalse\tFalse\tFalse\tFalse",
            {"command": "delete_field", "tag": "9XX"},
        ),
        (
            "DELETE\t506\t\t0\tFalse\tFalse\tFalse\tFalse\tFalse\t",
            {"command": "delete_field", "tag": "506"},
        ),
        (
            "DELETE\t655\tElectronic books\t0\tFalse\tFalse\tFalse\tFalse\tFalse",
            {"command": "delete_field", "tag": "655", "match": "Electronic books"},
        ),
        (
            "DELETE\t856\t" r"^=856  40\$uhttps:\/\/example\.edu\/journal\/.+$" "\t2\tFalse\tFalse\tFalse\tFalse\tFalse",
            {"command": "delete_field", "tag": "856", "match": r"^=856  40\$uhttps:\/\/example\.edu\/journal\/.+$", "match_regex": True},
        ),
        (
            "DELETE\t655\tElectronic books\t0\tFalse\tTrue\tFalse\tFalse\tFalse",
            {"command": "delete_field", "tag": "655", "match": "Electronic books", "delete_nonmatches": True},
        ),
        (
            "DELETE\t856\t" r"^=856  40\$uhttps:\/\/example\.edu\/journal\/.+$" "\t2\tFalse\tTrue\tFalse\tFalse\tFalse",
            {"command": "delete_field", "tag": "856", "match": r"^=856  40\$uhttps:\/\/example\.edu\/journal\/.+$", "match_regex": True, "delete_nonmatches": True},
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
            "ADD\t877\t\\\\$mSynthetic image\t106\t/=LDR.{8}[km].+/\t100\t",
            {
                "command": "add_field",
                "tag": "877",
                "ind1": " ",
                "ind2": " ",
                "subfields": [["m", "Synthetic image"]],
                "if_tag_exists": "add",
                "when": [{"leader": 6, "in": ["k", "m"]}],
            },
        ),
        (
            "ADD\t337\t \\\\$aSynthetic computer$bc$2rdamedia\t100\t",
            {
                "command": "add_field",
                "tag": "337",
                "ind1": " ",
                "ind2": " ",
                "subfields": [["a", "Synthetic computer"], ["b", "c"], ["2", "rdamedia"]],
                "if_tag_exists": "add",
            },
        ),
        (
            "ADD\t655\t\\7$aSynthetic genre\t106\t//=LDR.{8}[amt][m].+//",
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
            "ADD\t655\t\\7$aSynthetic genre\t106\t///=LDR.{8}[amt][m].+///",
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
            "REPLACE\t(=008.{25}).{1}(.+)\t$1o$2\t2\t\t0\tFalse",
            {
                "command": "replace_text",
                "find": "(=008.{25}).{1}(.+)",
                "replace": "$1o$2",
                "regex": True,
            },
        ),
        (
            "REPLACE\tfind\treplace\t2\t=LDR.{8}[e,f,g,k].+\t2\tFalse",
            {
                "command": "replace_text",
                "find": "find",
                "replace": "replace",
                "regex": True,
                "when": [{"leader": 6, "in": ["e", "f", "g", "k"]}],
            },
        ),
        (
            "REPLACE\tfind\treplace\t2\t=LDR.{8}[a,c,d,i,j,m,o,p,r,t][c,m,s,i].+\t2\tFalse",
            {
                "command": "replace_text",
                "find": "find",
                "replace": "replace",
                "regex": True,
                "when": [
                    {"leader": 6, "in": ["a", "c", "d", "i", "j", "m", "o", "p", "r", "t"]},
                    {"leader": 7, "in": ["c", "m", "s", "i"]},
                ],
            },
        ),
        (
            "REPLACE\t\\w{1,3}\tx\t2\t\t0\tFalse",
            {
                "command": "replace_text",
                "find": r"\w{1,3}",
                "replace": "x",
                "regex": True,
            },
        ),
        (
            "EDITFIELD\t001\tocn\t0\t\t",
            {"command": "edit_field", "tag": "001", "find": "ocn", "replace": ""},
        ),
        (
            "EDITFIELD\t001\ton|ocn|ocm\t2\t\t",
            {"command": "edit_field", "tag": "001", "find": "on|ocn|ocm", "replace": "", "regex": True},
        ),
        (
            "INDICATOR\t024\t\\\t\t8",
            {"command": "set_indicators", "tag": "024", "if_starts_with": " ", "value": "8"},
        ),
        (
            "INDICATOR\t856\t\t\t40",
            {"command": "set_indicators", "tag": "856", "value": "40"},
        ),
        (
            "INDICATOR\t035\t\\\t\t9",
            {"command": "set_indicators", "tag": "035", "if_starts_with": " ", "value": "9"},
        ),
        (
            "TASK_LIST\tOCLC Records Clean up 001 and 035\ttasksfile-2024_06_04_122910785.txt",
            {
                "command": "call_task",
                "task": "OCLC Records Clean up 001 and 035.-tasksfile-2024_06_04_122910785.json",
            },
        ),
        (
            "TASK_LIST\tFOLIO|FOLIO All FC CORE\ttasksfile-1a705cbaa3d242eca9bbd78f44eb4bbf.txt",
            {
                "command": "call_task",
                "task": "FOLIO All FC CORE.-tasksfile-1a705cbaa3d242eca9bbd78f44eb4bbf.json",
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
        (
            "SUBFIELD_EDIT\t950\ta\tneed.*le\tX\t0|2",
            {"command": "edit_subfield", "tag": "950", "code": "a", "action": "replace_regex", "find": "need.*le", "replace": "X"},
        ),
        (
            "SUBFIELD_REMOVE\t856\tz\t\t107|0",
            {"command": "remove_subfield", "tag": "856", "code": "z"},
        ),
        (
            "SUBFIELD_REMOVE\t856\tz\t\t0|0",
            {"command": "remove_subfield", "tag": "856", "code": "z"},
        ),
        (
            "SUBFIELD_REMOVE\t945\tb\t\t9|0",
            {"command": "remove_subfield", "tag": "945", "code": "b", "duplicates": True},
        ),
        (
            "SUBFIELD_REMOVE\t856\tz\tOCoLC\t107|0",
            {"command": "remove_subfield", "tag": "856", "code": "z", "if_contains": "OCoLC"},
        ),
        (
            "SUBFIELD_REMOVE\t856\tz\t(OCoLC)\t0|0",
            {"command": "remove_subfield", "tag": "856", "code": "z", "remove_text": "(OCoLC)"},
        ),
        (
            "SUBFIELD_REMOVE\t856\tz\t{dollar}{lcub}{rcub}\t0|0",
            {"command": "remove_subfield", "tag": "856", "code": "z", "remove_text": "${}"},
        ),
        (
            "SUBFIELD_REMOVE\t856\tz\tOCoLC\t0|2",
            {"command": "remove_subfield", "tag": "856", "code": "z", "remove_regex": "OCoLC"},
        ),
        (
            "COPY\t856\t857\tfalse\t\t\tfalse\t",
            {"command": "copy_field", "from_tag": "856", "to_tag": "857"},
        ),
        (
            "COPY\t035\t935\ttrue\t\t\tfalse\t",
            {"command": "copy_field", "from_tag": "035", "to_tag": "935", "move": True},
        ),
        (
            "COPY\t856\t857\tfalse\t$3JSTOR\t\tfalse\t",
            {"command": "copy_field", "from_tag": "856", "to_tag": "857", "if_contains": "$3JSTOR"},
        ),
        (
            "COPY\t856\t857\tfalse\t{dollar}\t\tfalse\t",
            {"command": "copy_field", "from_tag": "856", "to_tag": "857", "if_contains": "{dollar}"},
        ),
        (
            "REPLACE\tbefore\tafter\t0\t\t0\tFalse",
            {"command": "replace_text", "find": "before", "replace": "after"},
        ),
        (
            "buildnewfield\t=035  9\\$a({003}){001}\tFalse\tFalse\tFalse\tTrue",
            {"command": "build_field", "field": "=035  9\\$a({003}){001}", "mode": "add"},
        ),
        (
            "buildnewfield\t=035  \\\\$a{001}\tFalse\tFalse\tTrue\tFalse",
            {"command": "build_field", "field": "=035  \\\\$a{001}", "mode": "add_if_missing"},
        ),
        (
            "buildnewfield\t=035  \\\\$a{001}\tFalse\tTrue\tFalse\tFalse",
            {"command": "build_field", "field": "=035  \\\\$a{001}", "mode": "replace"},
        ),
        (
            "buildnewfield\t=001  X{956$a}\tFalse\tTrue\tFalse\tFalse",
            {"command": "build_field", "field": "=001  X{956$a}", "mode": "replace"},
        ),
        (
            "SORTBY\tALL\tTrue\tTrue",
            {"command": "sort_fields", "scope": "all"},
        ),
        (
            "SORTBY\tALL\tTrue\tFalse",
            {"command": "sort_fields", "scope": "all"},
        ),
        (
            "SORTBY\tALL\tFalse\tTrue",
            {"command": "sort_fields", "scope": "all"},
        ),
        (
            "SORTBY\tALL\tFalse\tFalse",
            {"command": "sort_fields", "scope": "all"},
        ),
        (
            "SORTBY\t0XX",
            {"command": "sort_fields", "scope": "0xx"},
        ),
        (
            "SORTBY\t0XX\tTrue\tTrue",
            {"command": "sort_fields", "scope": "0xx"},
        ),
        (
            "SORTBY\t0XX\tTrue\tFalse",
            {"command": "sort_fields", "scope": "0xx"},
        ),
        (
            "SORTBY\t0XX\tFalse\tTrue",
            {"command": "sort_fields", "scope": "0xx"},
        ),
        (
            "SORTBY\t0XX\tFalse\tFalse",
            {"command": "sort_fields", "scope": "0xx"},
        ),
        (
            GATHER_LOOP_WITH_DELETE,
            {
                "command": "gather_subfields",
                "from_tag": "856",
                "code": "u",
                "to_tag": "945",
                "remove_source": True,
            },
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
    expected_steps = [step]
    if step["command"] == "gather_subfields":
        expected_steps.append({"command": "delete_field", "tag": "999"})
    assert imported.document == {
        "format_version": "0.1",
        "name": "Synthetic task",
        "description": "Synthetic description",
        "normalize_typography": True,
        "steps": expected_steps,
    }
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(imported.document), encoding="utf-8")
    if step["command"] == "call_task":
        (tmp_path / step["task"]).write_text(
            json.dumps(
                {
                    "format_version": "0.1",
                    "name": "Synthetic called task",
                    "description": "Allows validating the imported call step.",
                    "steps": [],
                }
            ),
            encoding="utf-8",
        )
    assert load_task(task_path).steps == expected_steps


@pytest.mark.parametrize(
    "line",
    [
        "buildnewfield\t=035  \\\\$a{001}\tTrue\tFalse\tFalse\tTrue",
        "buildnewfield\t=035  \\\\$a{001}\tFalse\tTrue\tTrue\tFalse",
        "buildnewfield\t=035  \\$a{eacute}\tFalse\tFalse\tFalse\tTrue",
        "buildnewfield\t=035  \\$a{001$a[x]}{002$a[x]}\tFalse\tFalse\tFalse\tTrue",
        "buildnewfield\t=901  \\\\$a{001$a[x]}\tFalse\tFalse\tTrue\tFalse",
        "buildnewfield\t=001  X{956}\tFalse\tTrue\tFalse\tFalse",
        "DELETE\t245\t$aSynthetic match\t0\tTrue\tFalse\tFalse\tFalse\tFalse",
        "DELETE\t245\t\t0\tTrue\tFalse\tFalse\tFalse\tFalse",
        "DELETE\t506\t\t0\tFalse\tFalse\tFalse\tFalse\tFalse\textra",
        "ADD\t655\t\\7$aSynthetic genre\t106\t=LDR.{8}g.+",
        "ADD\t655\t\\7$aSynthetic genre\t106\t/=LDR.{8}g.+",
        "ADD\t655\t\\7$aSynthetic genre\t106\t//=LDR.{8}[amt][m].+/",
        "ADD\t655\t\\7$aSynthetic genre\t106\t////=LDR.{8}g.+////",
        "ADD\t650\t\\0$aSynthetic topic\t999\t",
        "ADD\t877\t\\\\$mSynthetic image\t106\t/=LDR.{8}[km].+/\t101\t",
        "ADD\t650\t\\0$aCaf{eacute}\t100\t",
        "SUBFIELD_EDIT\t950\ta\tneed.*le\tX\t0|3",
        "SUBFIELD_REMOVE\t856\tz\tOCoLC\t9|0",
        "SUBFIELD_REMOVE\t856\tz\tOCoLC\t0|3",
        "SUBFIELD_REMOVE\t856\tz\tOCoLC\t3|1",
        "SUBFIELD_REMOVE\t001\ta\t\t107|0",
        "SUBFIELD_REMOVE\t856\tz\t{bsol}\t0|0",
        "SUBFIELD_REMOVE\t856\tz\t{eacute}\t0|0",
        "COPY\t856\t857\tfalse\t\tX\tfalse\t",
        "COPY\t856\t857\tfalse\t\t\ttrue\t",
        "COPY\t856\t857\tfalse\t\t\tfalse\tX",
        "COPY\t856\t857\tfalse\t{eacute}\t\tfalse\t",
        "COPY\t001\t035\tfalse\tabc\t\tfalse\t",
        "COPY\t001\t005\tfalse\t\t\tfalse\t",
        "COPY\t856\t001\tfalse\t\t\tfalse\t",
        "REPLACE\tbefore.*\tafter\t0|2\t\t0\tFalse",
        "REPLACE\tbefore\tafter\t0\t/=LDR.{6}a.+/\t0\tFalse",
        "REPLACE\tbefore\tafter\t0\t\t0\tTrue",
        "REPLACE\tbefore\tafter\t0|1\t\t",
        "REPLACE\tfind\t$&\t2\t\t0\tFalse",
        "REPLACE\t(?=a)a\treplacement\t2\t\t0\tFalse",
        "REPLACE\tfind{eacute}\treplacement\t2\t\t0\tFalse",
        "REPLACE\tfind\treplacement\t2\t=008.+\t0\tFalse",
        "REPLACE\tfind\treplacement\t2\t=LDR.{8}g.+\t0\tFalse",
        "REPLACE\t{eacute}\tafter\t0\t\t0\tFalse",
        "EDITFIELD\t001\tocn\t1\t\t",
        "EDITFIELD\t001\tocn\t0\treplacement\tnote",
        "INDICATOR\t856\t\tcondition\t40",
        "TASK_LIST\tSynthetic task list",
        "TASK_LIST\tFOLIO\tFOLIO UM Core\ttasksfile-2023_10_30_154434371.txt",
        "SORTBY\t1XX",
        "SORTBY\tALL",
        "SORTBY\tALL\tTrue",
        "SORTBY\t0XX\tTrue",
        "MYSTERY\tSynthetic unknown command",
        GATHER_LOOP_UNCORRECTED,
        GATHER_LOOP_WITHOUT_DELETE,
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
    if line.startswith("#STARTLOOP:"):
        assert item.line_number == 4
        assert item.text.startswith("REPLACE\t")
        if line == GATHER_LOOP_UNCORRECTED:
            assert item.reason == "unsupported MarcEdit loop"
        else:
            assert item.reason == "gather_subfields loop requires a later DELETE 999"
        return
    assert item.line_number == 3
    assert item.text == line
    if line.startswith("SUBFIELD_EDIT"):
        assert item.reason == "unsupported SUBFIELD_EDIT settings"
    elif line.startswith("SUBFIELD_REMOVE") and "\t9|" in line:
        assert item.reason == "option 9 with a value is not supported"
    elif line == "buildnewfield\t=001  X{956}\tFalse\tTrue\tFalse\tFalse":
        assert item.reason == "step 1 setting field cannot use a whole data-field placeholder for a control field"
    elif line.startswith("SORTBY\t1XX"):
        assert item.reason == "unsupported SORTBY target"
    elif line.startswith("SORTBY\t"):
        assert item.reason == "unsupported SORTBY settings"
    elif line.startswith("EDITFIELD\t"):
        assert item.reason == "unsupported EDITFIELD settings"
    elif line.startswith("INDICATOR\t"):
        assert item.reason == "INDICATOR condition is not supported"
    elif line.startswith("TASK_LIST\t"):
        assert item.reason == "malformed TASK_LIST line"
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
