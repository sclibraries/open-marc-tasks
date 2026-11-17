Title: Add the field text form and plain replace_text (MarcEdit plain REPLACE)

Status: In-Progress
Size: M
Tier: major — format contract: defines the field text form other implementations must follow
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-011

Why:
- `REPLACE` is the largest remaining blocker (288 lines in the Smith and UMass
  task files): 140 plain, 30 regex, 112 regex with a Leader condition, 6 with
  option `0|1`. Plain REPLACE is how catalogers retag (`=945  ` → `=949  `),
  change indicators (`=852  0\` → `=852  8\`), add or remove an 856 $u proxy
  prefix, and reorder subfields. Regex mode is OMT-012 (split after the plan
  check: it needs its own rules for the regex dialect and replacement syntax).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic
records; each becomes a conformance case in this ticket):
- plain `0|0` replaces every occurrence and is case-sensitive (`ab ab AB` with
  find `ab`, replace `X` → `X X AB`);
- a retagged field stays in its position (945 → 249 was not re-sorted);
- an indicator edit through the text form works (`=852  0\` → `=852  8\`).

Design (the spec records it):
- **Text form of a field**, one line: `=` + tag (three ASCII digits) + two
  spaces + body. Data field body: indicator 1, indicator 2 (a blank shown as
  `\`), then each subfield as `$` + code + value. Control field (tag 001–009)
  body: the data with each blank shown as `\`. A literal `$` in a value is
  written `{dollar}`. Characterize how MarcEdit writes a literal `\`, `{`, `}`
  and the text `{dollar}` itself, and specify the escapes and the decoding
  order so nothing is decoded twice. The Leader line is not part of replace_text.
- **Character mnemonics** such as `{eacute}` are deferred (design allows them;
  staged later). A REPLACE line whose find or replace contains any `{name}`
  other than the characterized escapes is not translated, with its location.
- **`replace_text` step, plain mode**: settings `find` (non-empty string) and
  `replace` (string); optional `when` (existing conditions). For each record
  where `when` holds, for each field in order: render the text form, replace
  every non-overlapping occurrence left to right (case-sensitive, literal text),
  and if the text changed, parse it back into a field in the same position.
- **Parsing a result back**: tag must be three ASCII digits; 001–009 become
  control fields (body = data, `\` → blank); others become data fields and need
  two indicator characters followed by zero or more `$`+code+value subfields,
  where a code is one lowercase ASCII letter or digit. Characterize with
  MarcEdit and specify: retagging data → control and control → data; empty
  control data; a data field whose last subfield was removed; empty subfield
  values; repeated subfields (order kept); trailing spaces. Results the spec
  calls invalid raise an error.
- **Errors at run time name the record number and step number.** `run_task` and
  the CLI may change minimally to pass that context; the CLI's existing output
  for success and its other errors stays the same.
- Replacement sees the record after the existing record handling (backslash
  indicators, and typography when `normalize_typography` is true); tasks without
  that option keep curly quotes, dashes and no-break spaces unchanged.

Scope:
- `open_marc_tasks/text_form.py` (render, parse) and
  `open_marc_tasks/commands/replace_text.py`; table entry in `task.py`; minimal
  error-context plumbing in `task.py` and `cli.py`; spec and schema.
- Importer: `REPLACE<TAB>find<TAB>replace<TAB>0<TAB><TAB>0<TAB>False` → plain
  `replace_text`. Everything else (regex options, any condition, `True` flag,
  the six-column `0|1` form, unsupported mnemonics) stays not translated with a
  reason. `0|1` is deferred: don't investigate it here.
- Conformance cases under `conformance/replace_text/`, synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`: multiple
  occurrences and case; retag in place; indicator change; 856 proxy prefix add
  and remove; subfield reorder; a value with a literal `$`; whatever retag and
  empty-result cases MarcEdit accepts (cross-type retag, removing the last
  subfield) — invalid ones become loader/runtime error tests instead.
- `ARCHITECTURE.md` status lines for the text form and replace_text.

Out of scope:
- Regex mode and REPLACE conditions (OMT-012), `0|1`, character mnemonics,
  SUBFIELD_EDIT regex, the Leader line.

Likely files:
- open_marc_tasks/text_form.py, open_marc_tasks/commands/replace_text.py
- open_marc_tasks/task.py, open_marc_tasks/cli.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/replace_text/<case>/…
- tests/test_text_form.py, tests/test_task_loading.py, tests/test_marcedit_import.py, tests/test_cli.py (extend parametrized tests)

Acceptance tests:
- Every `replace_text` case passes the conformance suite and
  `tests/test_reference.py` on the host, so plain replacement, retag in place,
  indicator edits, proxy prefixes, reorder and `{dollar}` match MarcEdit.
- One parametrized round-trip test: render then parse returns an identical
  field for a control field with blanks, a data field with blank indicators, a
  value with `$`, a value containing the literal text `{dollar}`, a literal
  backslash, and unmatched braces — including when a different part of the same
  field is replaced — so the text form is lossless.
- One parametrized test of invalid results (tag not three digits, data field
  without indicators, bad subfield code, and whichever of the empty or
  cross-type results the spec calls invalid) raises an error whose message
  names record 2 and step 2 for a failure there, through `run_task` and through
  `omt run` (one `omt:` line, output not written).
- The invalid-task parametrize gains an empty `find` and a non-string `replace`,
  rejected by loader and schema.
- A default task (no `normalize_typography`) replacing unrelated text leaves a
  curly quote, an em dash and a no-break space unchanged.
- The importer parametrize gains the plain form (translated) and, not
  translated: a regex form, a conditional form, the `0|1` form, and a
  `{eacute}` mnemonic.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Plan:
1. Characterize escapes, empty and cross-type results with the reference runner.
2. Spec: text form, plain replace_text, error context.
3. text_form, replace_text, error plumbing; importer mapping.
4. Conformance cases via regenerate; extend tests; ARCHITECTURE.md; gates.

Plan check (2026-11-17, OMT-011 01-verify, BLOCKING) answered:
- 1 (worktree missing): wrong for this flow; the runner creates it and copies MarcEdit at build time.
- 2, 6, 10, 11, 12, 13 (bare Leader conditions, replacement syntax, Unicode classes, `$n`
  edge cases, zero-length matches, malformed patterns): all regex-mode; moved to OMT-012.
- 3, 5, 8, 9, 14, 16: added above (error context, mnemonic deferral fail-closed,
  escapes and decoding order, result grammar, normalization interplay,
  ARCHITECTURE.md; the measurement is the orchestrator's).
- 4: no dialect rows in this ticket, so loader and schema rows stay symmetric.
- 7: probe evidence summarized above; each behavior becomes a conformance case.
- 15: `0|1` deferred and removed from scope.
- 17: counts confirmed; "covers" means syntactic coverage only.
- More than five real findings, so the ticket was split (regex → OMT-012).

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
