Title: Apply MarcEdit's typography mapping in the reference runner's empty-output fill-in

Status: Ready
Size: S
Tier: small — developer tooling only; no library behavior changes
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-010

Why:
- When a task changes nothing, MarcEdit writes no file and
  `tools/marcedit_reference.py` fills in "the input with backslash indicators
  blanked" (OMT-008). But MarcEdit also always replaces curly quotes, dashes and
  ellipses when it writes (OMT-009, spec "Record handling"). On raw vendor
  records, three real JSTOR tasks that change nothing "differ" only because the
  fill-in skips that mapping.

Scope:
- `run_marcedit`: in the empty-output fill-in, also apply the typography mapping,
  reusing the library's helper (expose it the way `blank_backslash_indicators`
  is, if it isn't already reusable). MarcEdit applies it regardless of any task
  option, so the fill-in always applies it.
- `spec/format.md` "Conformance": update the sentence about empty output.

Out of scope:
- Library behavior, conformance fixtures (regenerate must leave them unchanged), measure.py.

Likely files:
- tools/marcedit_reference.py, spec/format.md, open_marc_tasks/task.py (only to expose the helper)

Acceptance tests:
- `regenerate` on all existing cases leaves `git diff -- conformance/` empty and
  `tests/test_reference.py` passes on the host, so existing answers are unaffected.
- A run (shown in the handoff, not committed) of a do-nothing task on a synthetic
  record with “curly” quotes and an em dash yields straight quotes and a hyphen.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
