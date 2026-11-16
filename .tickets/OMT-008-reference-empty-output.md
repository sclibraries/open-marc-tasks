Title: Treat MarcEdit's empty "no changes" output as the input with backslash indicators blanked

Status: Ready
Size: S
Tier: small — developer tooling only; no library behavior changes
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-008

Why:
- When a task changes nothing, MarcEdit writes an empty output file, and
  `tools/marcedit_reference.py` uses the input unchanged as MarcEdit's result.
  But whenever MarcEdit does write records it blanks backslash indicators on
  every record (OMT-006, spec "Record handling"). So for input with backslash
  indicators, a task that changes nothing "differs" from MarcEdit only because
  of how the runner fills the gap: three real JSTOR tasks showed exactly this
  in the 2026-11-16 measurement.

Scope:
- `tools/marcedit_reference.py` `run_marcedit`: when MarcEdit's output is empty,
  write the input records with each data field's backslash indicators replaced
  by blanks (the same rule as the spec's "Record handling"; reuse the library's
  code for it rather than writing it twice).
- `spec/format.md` "Conformance": update the one sentence about empty output.

Out of scope:
- Library behavior, conformance fixtures (all synthetic inputs have no
  backslash indicators, so `regenerate` must leave them unchanged), measure.py.

Likely files:
- tools/marcedit_reference.py, spec/format.md
- open_marc_tasks/task.py only if the normalization needs to become a small public function to reuse

Acceptance tests:
- `regenerate` on all existing cases leaves `git diff -- conformance/` empty, and
  `tests/test_reference.py` passes on the host, so existing answers are unaffected.
- A run (shown in the handoff, not committed) of a do-nothing task on a synthetic
  record with backslash indicators yields output with blank indicators, so
  "no changes" compares like MarcEdit's written output.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
