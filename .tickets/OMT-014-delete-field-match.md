Title: Let delete_field delete only fields whose text matches, and import MarcEdit DELETE with a match value

Status: In-Review
Size: S
Tier: normal — extends an existing command; reuses the field text form and regex dialect
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-014

Why:
- 110 `DELETE` lines in the Smith and UMass task files delete a field only when
  it contains a value, and they are the only blocker for 5 tasks. Examples:
  `655 | Electronic books` (50 lines), `035 | \\$a(OCoLC)`,
  `856 | 40$uhttps://www.jstor.org/stable`, `6XX | \6` (second indicator 6), and
  a regex form `856 | 40\$uhttps:\/\/www\.jstor\.org\/stable\/.+$` with column 4 `2`.
  The match text is MarcEdit's field text (OMT-011), so this reuses that form
  and the OMT-012 regex dialect.

Scope:
- Characterize with real MarcEdit first (reference runner): for
  `DELETE<TAB>tag<TAB>match<TAB>A<TAB>f1<TAB>f2<TAB>f3<TAB>f4<TAB>f5`, what the match
  is compared against (the field's text form after `=TAG  `, or the whole line,
  or the data only), whether plain matching is substring and case-sensitive,
  how `A=2` (regex) anchors (`^`, `$`) behave, and what `f2=True` means (14 lines:
  `0|False|True|…` and `2|False|True|…`). Also the X wildcard with a match
  (`6XX | \6`).
- `delete_field` gains optional `match` (string) and `match_regex` (boolean,
  default false; when true, `match` follows the OMT-012 dialect and is validated
  at load). If `f2=True` has a clear meaning, add one plain-English setting for
  it; if not, leave those lines not translated and say so.
- Importer: DELETE with a match value and the characterized flag combinations →
  `delete_field` with `match` (and `match_regex`); others stay not translated.
- Spec, schema, conformance cases under `conformance/delete_field/` (synthetic
  records, `expected.mrc` only from `tools/marcedit_reference.py regenerate`):
  plain value in a subfield (655 "Electronic books" with a non-matching 655 kept);
  indicator match with a wildcard tag (`6XX` with `\6`); subfield-prefix match
  (`035` `\\$a(OCoLC)`); a regex match with `$`; and the `f2=True` behavior if built.

Out of scope:
- Other DELETE flags beyond what's characterized, other commands.

Likely files:
- open_marc_tasks/commands/delete_field.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json
- conformance/delete_field/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host, so value, indicator, prefix and regex deletes match MarcEdit.
- The invalid-task parametrize gains a non-string `match`, a non-boolean
  `match_regex` (loader and schema), and a `match_regex: true` pattern outside
  the dialect (loader only, with the step number).
- The importer parametrize gains each characterized DELETE-with-match form
  (translated) and one uncharacterized flag combination (not translated).
- Existing delete_field cases pass unchanged.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
