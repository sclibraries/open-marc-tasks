Title: Characterize MarcEdit RDAHELPER 336/337/338 generation (black-box spec only)

Status: In-Progress
Size: M
Tier: normal — specification and conformance cases only; no engine code
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-037

Why:
- `RDAHELPER<TAB>1|1|0|0|0|0|0|0|0|0|0|0|0|0|0|0|language of cataloging|0` is the
  only untranslated line in the four Smith "CORE Instance" tasks. Flags 1 and 2
  switch on 336 and 337/338 generation; every other flag is off (flag 17 is the
  literal placeholder `language of cataloging`). Owner decision 2026-11-20:
  implement only this form, clean-room.
- **Clean-room rule:** the behavior is specified only from MarcEdit's inputs
  and outputs. Do not read, search for, or use decompiled or disassembled
  MarcEdit code, and do not copy MarcEdit text other than field values it
  writes into records. Say in the handoff that you followed this.

Scope:
- Probe MarcEdit 7.6 (reference runner; synthetic records only; `RDAHELPER`
  needs no config files for flags 1 and 2 — confirm) with a grid wide enough to
  pin the rules, and write them in `spec/format.md` as a new section for a
  future step `add_content_types` (no settings): which 336, 337 and 338 fields
  are added, with which subfields and indicators, for each input that matters
  (Leader/06, Leader/07, 007 presence and positions, 008 form of item, any
  other field MarcEdit consults); what happens when 33X fields already exist
  (kept, replaced, skipped); where new fields are placed; repeated fields; and
  records MarcEdit leaves unchanged.
- Name every input the probes show MarcEdit consults; if a rule can't be pinned
  down within the round, write it as an open question rather than guess.
- Conformance cases under `conformance/add_content_types/` (synthetic records,
  `marcedit-task.txt` = the real RDAHELPER line, `expected.mrc` only from
  `tools/marcedit_reference.py regenerate`, `task.json` with the future step),
  covering each rule in the spec. They will fail until OMT-038 implements the
  step, so mark them so the suite skips them with a reason that names OMT-038
  (the only skip this ticket may add), and say so in the handoff.

Out of scope:
- Any engine or importer code; other RDAHELPER flags; the EDS flag set.

Likely files:
- spec/format.md, conformance/add_content_types/<case>/…
- tests/test_conformance.py (only the skip for these cases)

Acceptance tests:
- The spec section states every rule with the probe evidence (input → output)
  in a compact table, plus open questions.
- `tests/test_reference.py` on the host regenerates nothing different for the
  new cases (expected outputs are MarcEdit's), not skipped.
- The Python 3.9 gate passes with only the documented skips.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
