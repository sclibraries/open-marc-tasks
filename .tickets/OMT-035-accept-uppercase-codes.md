Title: Accept uppercase subfield codes in edited fields, as MarcEdit does

Status: In-Progress
Size: S
Tier: normal — relaxes a text-form check (owner decision 2026-11-20)
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-035

Why:
- A real source record has `=655  \7$Documentary films.$2lcgft` (subfield
  code `D`). When an edit rewrites that field, `parse_field` rejects the code
  and the whole task stops ("data field text has an invalid subfield code"); 8
  tasks fail on the raw sample. MarcEdit keeps the field as is. Owner decision
  2026-11-20: accept uppercase codes like MarcEdit, including where an edit
  creates one (OMT-022 observed MarcEdit writing code `X`; OMT-025 `$A`).

Scope:
- An uppercase ASCII letter is a valid subfield code when a field's text form
  is parsed back (`open_marc_tasks/text_form.py`) and in the regex result
  checks of `edit_subfield` and `remove_subfield`. Other characters stay
  invalid, with the same errors as now.
- Task settings that name a code (`code`, `add_field` subfields, …) stay
  lowercase letters and digits; the importer's checks stay as they are.
- `spec/format.md`: the text-form section and the two regex sections say so.

Out of scope:
- Codes other than uppercase letters; settings validation; the importer.

Likely files:
- open_marc_tasks/text_form.py, open_marc_tasks/commands/edit_subfield.py,
  open_marc_tasks/commands/remove_subfield.py, spec/format.md
- tests/test_cli.py (change the two existing invalid-result rows to a code that
  stays invalid), conformance/<command>/<case>/…

Acceptance tests:
- Conformance (synthetic records, `expected.mrc` only from
  `tools/marcedit_reference.py regenerate`): a field with a source code `D`
  that a `replace_text` edit changes elsewhere, and an `edit_subfield`
  `replace_regex` that produces code `X` (the OMT-022 probe `^.*$` → `X`).
  Both pass the suite and `tests/test_reference.py` on the host.
- The existing CLI rows "invalid subfield regex result" and "invalid edit_field
  result" still raise naming record 2 and step 2, using a result whose code is
  not a letter or digit (characterize with MarcEdit what it writes for such a
  code and say so in the handoff; don't follow it if it writes an invalid record).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the measurement; the raw sample's 8 record-32 errors should go.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
