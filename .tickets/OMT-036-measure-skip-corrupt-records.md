Title: Measure the rest of a task when MarcEdit corrupts some records

Status: In-Progress
Size: S
Tier: small — private-measurement tooling only
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-036

Why:
- MarcEdit writes invalid UTF-8 for some records (HTML entities decoded to a
  Latin-1 byte; its smart-character step breaking U+2212 MINUS SIGN into
  `E2 88 27`). Since OMT-034 such a task is reported as `error (MarcEdit output
  unreadable)` and none of its other records are compared, hiding 11 tasks on
  two samples. Owner OK 2026-11-20 to compare the rest.

Scope (`tools/measure.py` and its spec paragraph):
- When the MarcEdit output reads with the same number of records as ours but
  some come back unreadable (pymarc yields `None` in that position), compare
  every other record by position.
- If they all match: report `match except MarcEdit-unreadable records: <record
  numbers>`; if any differ: `differs` as usual. A read that fails outright, or a
  record count that doesn't line up, stays `error (MarcEdit output unreadable)`.
- Count the new outcome separately (not as a match) in the summary line:
  `N of M task files match MarcEdit (K match except MarcEdit-unreadable
  records, D differ, E error, U not translated)`.

Out of scope:
- Engine, importer, conformance runner.

Likely files:
- tools/measure.py, spec/format.md (measure paragraph)

Acceptance tests:
- Small tier: no new tests. The orchestrator's private run shows the outcome
  on the raw sample (record 92) and sample 221 (record 89).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
