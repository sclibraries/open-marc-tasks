Title: Add the MarcEdit cleanup commands (smart characters, ISBD rules, HTML entities, blank lines)

Status: In-Progress
Size: M
Tier: normal — two new commands, one new decode command, importer and CLI option; owner decided the design
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-033

Why:
- The shared task "Edit Smart, HTML, ISBD" (called by 10 tasks) is
  `CLEANSMARTCHARACTERS<TAB>smartlist.txt`, `REPLACEHTMLENTITIES`,
  `REMOVEISBD<TAB>remove_isbd_punc.txt`, `REMOVEBLANKLINES`, `SORTBY<TAB>ALL…`.
  Owner decisions 2026-11-19: rule files are copied into the task inline;
  entities that decode to non-ASCII are written as correct UTF-8.

How MarcEdit 7.6 does it (orchestrator reading of the decompiled code, 2026-11-19;
characterize each point with MarcEdit before the spec and follow MarcEdit):
- Both rule commands work on the record's text lines (`=LDR  …`, `=245  10$a…`,
  the field text form) and read their file from `UserDataPath/configs/<name>`.
- CLEANSMARTCHARACTERS: the file is read as UTF-8 without BOM detection (a BOM
  stays in the first line); blank lines are skipped; a `#` line containing
  `regex` switches later pairs to regex; any line with a tab is a pair
  `find<TAB>replace` (first pair for a `find` wins); other lines are ignored.
  Every pair is applied to every line: literal pairs replace every occurrence,
  regex pairs replace every match. (MarcEdit applies pairs in hash order; this
  format applies them in file order — the same unless pairs overlap; say so.)
- REMOVEISBD: lines that are blank, start with `#`, or have no tab are skipped;
  others are `key<TAB>pattern<TAB>replacement`, grouped by key in file order.
  For each line MarcEdit takes the group whose key equals the line's first 4
  characters (`=245`, `=LDR`), else first 3, else first 2 (`=1`), and applies
  that group's rules in order, each a regex replace of every match. So a 245
  line gets only the `=245` rules, never the `=2` ones.
- REPLACEHTMLENTITIES: decodes hexadecimal (`&#x2019;`), decimal (`&#233;`) and
  named (`&amp;`) entities in three passes in that order. The command-line copy
  writes non-ASCII results as a raw Latin-1 byte (invalid UTF-8); this format
  writes the correct character (documented difference).
- REMOVEBLANKLINES removes blank lines inside MarcEdit's text file; binary
  records have none, so it changes nothing.

Design (the spec records it):
- **Step** `replace_characters`: `pairs` — list of `[find, replace]`, plus
  optional `regex_pairs` (same shape, OMT-012/032 dialect). Applied to the
  Leader line and every field line in the text form, pairs then regex pairs,
  each in order.
- **Step** `apply_rules`: `rules` — list of `[key, pattern, replacement]`
  (dialect-checked at load), selected per line by the 4/3/2-character key rule
  above, applied in order.
- **Step** `decode_entities`: no settings; the three passes above.
- Leader edits: a changed Leader line must still be `=LDR  ` plus 24
  characters, else a run-time error naming the record and step.
- Importer: `omt import SOURCE OUT_DIR --configs DIR` (and `import_marcedit`
  gains the folder). CLEANSMARTCHARACTERS and REMOVEISBD read `DIR/<name>` and
  become the steps above with the rules copied in; without the folder or file
  the line is not translated with a reason. REPLACEHTMLENTITIES →
  `decode_entities`. REMOVEBLANKLINES imports as nothing (as OMT-030 did for
  option 9). `tools/measure.py` passes its `--configs` to the importer.

Scope:
- `open_marc_tasks/commands/replace_characters.py`, `apply_rules.py`,
  `decode_entities.py`; `task.py` table; `text_form.py` only if the Leader line
  needs rendering there; importer; `cli.py`; `tools/measure.py`; spec, schema,
  `ARCHITECTURE.md`.
- Conformance cases (synthetic records and synthetic rule files in each case's
  `marcedit-configs/`; never the owner's private files): smart pairs including a
  `&#x2022;`-style key and a regex pair; ISBD rules showing the 4/3/2 key
  precedence and an `=LDR` rule; HTML entities (hex, decimal, named, an unknown
  name, `&amp;lt;`) with ASCII results only; REMOVEBLANKLINES.

Out of scope:
- RDAHELPER, other MarcEdit config files.

Likely files:
- open_marc_tasks/commands/{replace_characters,apply_rules,decode_entities}.py
- open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py, open_marc_tasks/cli.py, tools/measure.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/<command>/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py, tests/test_cli.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped).
- One decode case with a non-ASCII entity shows the documented difference: our
  output has the correct UTF-8 character (a unit-level check in the existing
  parametrized style, not a conformance case).
- Loader: a dialect-invalid `apply_rules` pattern and a Leader rule that makes
  the Leader the wrong length (run-time error naming record 2 and step 2 through
  `omt run`, extending the existing row set).
- Importer: each of the four lines with `--configs` (translated, passing
  `load_task`); CLEANSMARTCHARACTERS without `--configs` (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private measurement with `--library` and `--configs`.

Plan:
1. Characterize the four commands with MarcEdit (synthetic configs) and write the spec.
2. `replace_characters` and `apply_rules` (with the Leader line); conformance.
3. `decode_entities`; conformance and the non-ASCII check.
4. Importer, `--configs` on the CLI and in measure.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
