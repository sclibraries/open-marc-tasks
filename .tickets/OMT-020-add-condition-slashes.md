Title: Import ADD Leader conditions written with doubled or tripled slashes

Status: In-Review
Size: S
Tier: normal — importer mapping only
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-020

Why:
- 33 `ADD` lines write their Leader condition as `//=LDR.{8}[amt][m].+//`
  (one as `///…///`) instead of `/…/`. That form is the only untranslated line
  in 8 UMass tasks (eds_cc_fcku, eds_cc_umbdramal, eds_cc_umeapb, eds_cc_umsecbn,
  folio_ac_jstorp, folio_jstorpurchased_ac, folio_umbfrp, folio_umnaacp).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic
records with Leader 06–07 `am`, `as`, `em`, `cm`): `/=LDR.{8}[amt][m].+/`,
`//=LDR.{8}[amt][m].+//` and `///=LDR.{8}[amt][m].+///` all added the field to
the `am` record only; `//=LDR.{8}[e,f][m,c].+//` added it to the `em` record only.

Scope:
- Importer: an ADD condition wrapped in the same number (1–3) of slashes on
  each side is read like the single-slash form (existing Leader-condition
  parsing). Unequal slashes, or more than three, stay not translated.
- `spec/format.md`: one sentence in the ADD import section.
- One conformance case under `conformance/add_field/` with a doubled-slash
  condition on records whose Leader matches and doesn't (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`;
  `marcedit-task.txt` is the doubled-slash ADD line).

Out of scope:
- The 7-column ADD form (`…/\t100\t`), field-text conditions (`/650.+Newspapers.+/`),
  a leading space before the indicators, other commands.

Likely files:
- open_marc_tasks/marcedit_import.py, spec/format.md
- conformance/add_field/<case>/…
- tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- The new conformance case passes the suite and `tests/test_reference.py` on the host (not skipped).
- The importer parametrize gains `//…//` and `///…///` (translated, same `when`
  as the single-slash form, passing `load_task`) and `//…/` (not translated).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
