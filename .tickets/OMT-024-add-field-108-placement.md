Title: Place skip_if_identical additions before the first greater tag (MarcEdit ADD option 108)

Status: Ready
Size: S
Tier: normal — changes where one add_field policy inserts a field
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-024

Why:
- `eds_cc_umsiam` differs from MarcEdit on two measurement samples since
  OMT-023 made it fully translatable. Its `ADD 710 … 108` runs on records whose
  tags are out of order (`… 710 653 653 856`). add_field puts the new 710 right
  after the existing 710; MarcEdit puts it before the 856. Ten other real
  `ADD … 108` lines (710, 336–338) can hit the same records.

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-18, synthetic records):
- Option 108, no identical field present: the new field is inserted before the
  first field (scanning from the start) whose tag is **strictly greater** than
  the new tag, or at the end if there is none. Where existing same-tag fields
  sit does not matter:
  - `001 245 710 653 653 856` + 710 → `001 245 710 653 653 710* 856`
  - `001 245 856 710` + 710 → `001 245 710* 856 710`
  - `001 500 245 710 300` + 710 → `001 500 245 710 300 710*`
  - `001 710 856 710 653` + 710 → `001 710 710* 856 710 653`
  - `001 245 650 650 700 650` + 650 → `001 245 650 650 650* 700 650`
  - `001 500 245 710 300` + 300 → `001 300* 500 245 710 300`
- Options 100, 106 and 101 already match add_field's current rule (before the
  first field whose tag is equal or greater) in every probed record; don't
  change them.

Scope:
- `open_marc_tasks/commands/add_field.py`: with `skip_if_identical` (when no
  identical field exists), insert before the first field whose tag is greater
  than the new tag, else at the end. This replaces the current "after the last
  same-tag field" branch; delete code it makes dead.
- `spec/format.md`: restate the `skip_if_identical` placement as that one rule
  (it covers the tag-absent case too).
- One conformance case `conformance/add_field/option-108-out-of-order/`
  (synthetic records, `expected.mrc` only from
  `tools/marcedit_reference.py regenerate`) with three records: `… 710 653 653
  856`, `… 245 856 710`, and `… 710 300` (no greater tag), adding a 710 with 108.

Out of scope:
- Options 100, 106, 101; copy_field and build_field placement; other commands.

Likely files:
- open_marc_tasks/commands/add_field.py, spec/format.md
- conformance/add_field/option-108-out-of-order/…

Acceptance tests:
- The new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped); it fails on the old placement, which is why it exists.
- The existing `conformance/add_field/option-108` and all other conformance
  cases pass unchanged. No new unit tests.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
