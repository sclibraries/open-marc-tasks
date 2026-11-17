Title: Add copy_field and import MarcEdit COPY

Status: In-Progress
Size: S
Tier: normal — new command with plain settings; reuses existing placement, text form and match rules
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-018

Why:
- `COPY` has 68 lines in the Smith and UMass task files: 945 → 946–949 (one
  holdings field per college), 856 → 956 (copy or move before rebuilding),
  035 ↔ 935/999 moves, 001 → 035/950, and filtered copies (`856 → 857` only
  where the field has `$3JSTOR`; `035 → 935` only for `9\$a10.3998`).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic
records). Line form: `COPY<TAB>from<TAB>to<TAB>move<TAB>match<TAB><TAB>false<TAB>`;
columns 6 and 8 are always empty and column 7 always `false` in real files.
- `false`: every field with the from tag is copied to the to tag (indicators and
  subfields kept). The copies are inserted together, in source order, before the
  first field with an equal or greater tag (945 ×2 → two 949s after the 945s and
  before 950; 945 → 040 lands before 245; 001 → 035 lands before the existing 035s).
- `true`: the same, and the source fields are removed (move).
- A match value copies only fields whose text form contains it
  (`$3JSTOR` copied only the 856 that has it; `9\$a10.3998` and `9\` selected
  the 035 with first indicator 9).
- A control field copied to a data tag becomes a data field with blank
  indicators and `$a` holding the control field's text-form body, so a blank
  shows as `\` (001 `r1 x` → 035 `\\$ar1\x`), as in build_field.
- A record without the from tag is unchanged.

Design (the spec records it):
- **Step** `copy_field`: `from_tag`, `to_tag` (three digits, different), `move`
  (boolean, default `false`), optional `if_contains` (non-empty string matched
  against the field text form). Characterize with MarcEdit whether the match sees
  the whole `=TAG  …` line, as delete_field's `match` does (OMT-014), or only the
  part after it, and whether it is case-sensitive; reuse delete_field's matching
  code if the rule is the same.
- A data field copied to a control tag is rejected at load (no real lines).
- Reuse `insert_fields` (OMT-015) for placement; don't copy it.

Scope:
- `open_marc_tasks/commands/copy_field.py`, table entry in `task.py`; spec,
  schema, `ARCHITECTURE.md` status line.
- Importer: the real forms (`false`/`true`, empty or non-empty match, column 7
  `false`, columns 6 and 8 empty) → `copy_field`. Not translated, with a reason:
  any other column 6/7/8 value, a data-to-control copy, an unsupported `{…}`
  mnemonic in the match.
- Conformance cases under `conformance/copy_field/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): repeated
  source copied to a later tag and to an earlier tag; move; a filtered copy by a
  subfield value and by an indicator, with a case-mismatched value that doesn't
  match; 001 with a blank → 035 ahead of existing 035s; a record without the source.

Out of scope:
- Other COPY columns, other commands.

Likely files:
- open_marc_tasks/commands/copy_field.py, open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- open_marc_tasks/commands/delete_field.py (shared matching only, if reused)
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/copy_field/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped), so placement, move, filters and control-to-data copies match MarcEdit.
- Existing delete_field cases pass unchanged (if matching is shared).
- The invalid-task parametrize gains: a bad `to_tag`, `from_tag` equal to
  `to_tag`, a non-boolean `move`, an empty `if_contains` (loader and schema),
  and a data-to-control copy (loader, with the step number).
- The importer parametrize gains copy, move and filtered forms (translated,
  passing `load_task`) and a non-empty column 6, column 7 `true`, and a
  data-to-control copy (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
