Title: Import MarcEdit DELETE and ADD lines into the open format, and measure how many tasks match MarcEdit

Status: Ready
Size: M
Tier: normal — new behavior (importer, CLI subcommand, dev tool); no new dependencies
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-005

Why:
- The point of the project is that a cataloger brings their MarcEdit tasks
  over. With `delete_field` and `add_field` built, the plain `DELETE` lines (384
  in the Smith and UMass task files) and all four `ADD` options (809 lines) can
  be converted now. Anything else must be listed, never dropped or guessed.
- Progress is measured as "how many of the 100 task files produce the same
  records as MarcEdit". That needs the importer and a measuring tool.

Scope:
- `open_marc_tasks/marcedit_import.py`:
  `import_marcedit(path: Path) -> ImportResult` where
  `ImportResult(tasks: List[ImportedTask], not_translated: List[NotTranslated])`,
  `ImportedTask(name: str, document: dict)` (a valid v0.1 task document) and
  `NotTranslated(source: str, line_number: int, text: str, reason: str)`.
  Accepts a MarcEdit tasks text file (tab-separated) or a `.task` zip (each
  `.txt` entry becomes its own task; `source` names the entry). Task `name`
  comes from the file or entry name; `description` from a `#DESCRIPTION#` line.
- Translations (anything else is a `NotTranslated` with a plain reason):
  - `DELETE<TAB>tag<TAB><TAB>0<TAB>False<TAB>False<TAB>False<TAB>False<TAB>False`
    (empty match column, default flags) → `delete_field`. Translate the tag as
    written, including `X` patterns.
  - `ADD<TAB>tag<TAB>field text<TAB>option<TAB>condition` with option 100, 101,
    108 → `add_field` with `if_tag_exists` `add`, `skip`, `skip_if_identical`;
    option 106 → `add` plus `when`, only when the condition is exactly a
    Leader-class regex of the forms in the task files:
    `/=LDR.{N}[letters].+/`, `/=LDR.{N}[letters][letters].+/` or
    `/=LDR.{N}x.+/` (single letter). In MarcEdit's text form the Leader line
    is `=LDR` plus two spaces plus the Leader, so `.{N}` after the literal
    `=LDR` covers those two spaces and Leader positions 0 to N − 3: the first
    bracket is Leader position N − 2 and a second bracket is N − 1
    (`.{8}[amt][m]` → 06 in a,m,t and 07 = m; `.{9}s` → 07 = s). Commas inside brackets are separators, not
    data (`[i,j]` means i or j). Any other condition form (for example `//…//`)
    is not translated.
  - Field text: `\` is a blank indicator, `$x` starts subfield x, `{dollar}` is a
    literal `$`. Text containing any other `{…}` mnemonic is not translated
    (character mnemonics come later). Control-field ADD (00X) → `data`.
  - Lines starting `#` other than `#DESCRIPTION#`, and blank lines, are ignored.
- CLI: `omt import SOURCE OUT_DIR` writes one `<name>.json` per task and prints
  one line per not-translated line (`source:line: reason`), then a summary
  (`N tasks, M lines not translated`). Exit 0 even with not-translated lines;
  exit 1 on an unreadable source. A task is written only when every line was
  translated; the summary names the tasks not written, so a partial task can't
  be run by mistake.
- `tools/measure.py` (dev only): `python tools/measure.py --records SAMPLE.mrc FOLDER...`
  For every MarcEdit task file in the folders: import it; if fully translated,
  run it through the library and through MarcEdit (reference runner) on the
  sample and compare with `records_match`. Prints per file
  `match | differs | not translated (k lines)` and a total
  (`X of Y task files match MarcEdit`). Reads folders and the sample from the
  given paths and writes nothing into the repository.
- Spec: a short "Importing MarcEdit tasks" section listing what v0 translates.
  README: `omt import` usage.

Out of scope:
- Other MarcEdit commands, `DELETE` with a match value or non-default flags,
  `TASK_LIST`, character mnemonics, any change to `delete_field` or `add_field`.

Likely files:
- open_marc_tasks/marcedit_import.py, open_marc_tasks/cli.py
- tools/measure.py
- spec/format.md, README.md
- tests/test_marcedit_import.py

Acceptance tests:
- One parametrized test over synthetic MarcEdit lines checks the translation of:
  a plain DELETE; a `9XX` DELETE; ADD options 100, 101, 108; ADD 106 with
  `/=LDR.{8}[amt][m].+/` (Leader 06 in a,m,t and 07 = m) and with
  `/=LDR.{9}s.+/` (Leader 07 = s); `{dollar}` in a value; a control-field ADD.
  Each produced document passes `load_task`, so the importer can't emit an
  invalid task.
- One parametrized test checks that each of these becomes `NotTranslated` with
  the right line number and the original text: DELETE with a match value, DELETE
  with a `True` flag, ADD 106 with `//=LDR.{8}[amt][m].+//`, ADD with an
  unknown option, a `{eacute}` mnemonic, a `TASK_LIST` line, an unknown verb.
  So nothing is dropped or guessed.
- A `.task` zip with two entries imports as two tasks; `omt import` writes only
  the fully translated one and reports the other's lines, so a partial task is
  never runnable by accident.
- `tools/measure.py` on a synthetic folder of two task files (one translatable,
  one not) and a synthetic sample prints the per-file lines and
  `1 of 2 task files match MarcEdit` on the host (MarcEdit through Docker).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`
  and the `tools/measure.py` run above; report both.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
