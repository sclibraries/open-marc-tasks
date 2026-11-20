Title: Make the measurement report per-task errors instead of crashing

Status: Completed
Size: S
Tier: small — private-measurement tooling only; no engine, format or importer change
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-034

Why:
- Since OMT-033 more tasks translate fully, and the measurement now stops at
  the first problem (orchestrator run 2026-11-20): a `TaskError` from running
  our task (e.g. `record 1 step 11: replace result has no non-empty subfields`,
  or an invalid subfield code inside a called task) ends the whole run, and so
  does MarcEdit output that pymarc can't read (`records_match` gets `None`).
  One task's problem must not hide the other 99 results.

Scope (`tools/measure.py` only, plus its spec paragraph):
- A `TaskError` while loading or running our task is reported for that task as
  `error (ours): <message on one line>` and the run continues.
- MarcEdit output that can't be read (any record pymarc returns as `None`, or a
  read exception) is reported as `error (MarcEdit output unreadable): <reason>`.
- Neither counts as a match. The final line adds the counts:
  `N of M task files match MarcEdit (D differ, E error, U not translated)`.

Out of scope:
- Changing what the engine does in those cases; the conformance runner.

Likely files:
- tools/measure.py, spec/format.md (measure paragraph)

Acceptance tests:
- Small tier: no new tests. The orchestrator's private run over the three
  samples completes and shows each outcome.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".

Handoff:
- Head ad15baf, merged into main (owner OK 2026-11-20). Python 3.9 gate 259 passed, 1 skipped. Measure 89/86/81 match, 0 differ; 2/5/10 errors, 9 not translated.

Review:
- Per-task error reporting as specified. No fix round.
