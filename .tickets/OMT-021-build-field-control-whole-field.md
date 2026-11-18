Title: Reject a whole data-field placeholder in a control-field build_field template

Status: Completed
Size: S
Tier: normal — one load-time rejection and its importer reason
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-021

Why:
- `eds_cc_umeapb` has `buildnewfield =001  UMEAPB{956}` (replace). MarcEdit 7.6
  puts the whole 956 into the 001 and writes its raw subfield delimiter (0x1F)
  there: `UMEAPB40␟uhttps://…` (orchestrator measurement 2026-11-18). build_field
  writes a literal `$` instead, so the task differs. Both results are broken
  control data; the cataloger most likely meant `{956$u}`. Orchestrator's call
  (cautious default, importer never approximates): refuse the form so the line
  is reported for someone to fix.

Scope:
- `build_field`: a template whose tag is a control tag (`00X`) and that has a
  `{NNN}` placeholder with NNN ≥ 010 (a whole data field) is rejected at load
  with the step number. `{00X}` and `{NNN$c}` stay allowed.
- Importer: such a `buildnewfield` line is not translated, with that reason.
- `spec/format.md`: one sentence in the build_field section saying so and why.

Out of scope:
- Other build_field behavior, other commands.

Likely files:
- open_marc_tasks/commands/build_field.py, spec/format.md
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- The invalid-task parametrize gains `=001  X{956}` (loader, with the step number).
- The importer parametrize gains `buildnewfield\t=001  X{956}\tFalse\tTrue\tFalse\tFalse`
  (not translated) and keeps `=001  X{956$a}` translated.
- Existing build_field conformance cases pass unchanged.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- Head 4044863, merged into main (owner OK 2026-11-18). Python 3.9 gate 190 passed, 1 skipped. Measure 33 match / 0 differ on all three samples.

Review:
- Whole data-field placeholder in a control-field template rejected at load; eds_cc_umeapb now reported for a fix. No fix round.
