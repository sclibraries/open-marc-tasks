Title: Add the edit_subfield command for MarcEdit SUBFIELD_EDIT, with importer mapping

Status: In-Progress
Size: M
Tier: normal — new command behavior; no new dependencies
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-007

Why:
- `SUBFIELD_EDIT` is the biggest blocker in the Smith and UMass task files (393
  lines). Until it runs, most of those tasks can't be imported.

Scope:
- Characterize with real MarcEdit (reference runner) first. A line is
  `SUBFIELD_EDIT<TAB>tag<TAB>code<TAB>find<TAB>replace<TAB>A|B`. The forms in the
  task files, by count:
  1. empty find, text replace, `102|0` (187), for example 949 $h "Online";
  2. literal text find and replace, `0|0` (85);
  3. find `^e`, text replace, `0|0` (51): append, for example 949 $b + "-AC";
  4. find `^b`, text replace, `0|0` (26): prepend;
  5. literal text find and replace, `0|2` (22);
  6. empty find, text replace, `101|0` (14);
  7. rarer: text find with empty replace `0|0` (3), empty find and empty replace
     `0|0` (3), text find `0|1` (2).
  For each, observe what MarcEdit does with: the subfield present once, present
  twice, absent; the tag present twice; the find text occurring twice in a
  value; letter case differences. Write the observed rules in the spec.
- `edit_subfield` command with plain-English settings that express the observed
  behaviors (for example an `action` of `set`, `replace`, `append`, `prepend`,
  plus whatever forms 5–7 turn out to mean). Name things by behavior, not by
  MarcEdit's numbers; the spec table maps each MarcEdit form to its settings.
  Optional `when` conditions as in `add_field`.
- Importer: translate the characterized forms to `edit_subfield`; anything else
  stays not translated with a reason.
- Move each command's settings validator and runner into its own command
  module (`commands/<name>.py` exports `validate(step, number)` and
  `run(record, step)`); `task.py` keeps only the table and the generic checks,
  so it stays well under 300 lines as commands are added.
- Spec and schema sections; conformance cases under `conformance/edit_subfield/`,
  one per characterized form (several records per case are fine), each with
  `expected.mrc` from `tools/marcedit_reference.py regenerate` only.

Out of scope:
- Other commands, regex find (if MarcEdit treats any form as a regex, stop and
  record it in the handoff instead of building it), changes to existing
  command behavior.

Likely files:
- open_marc_tasks/commands/edit_subfield.py, delete_field.py, add_field.py
- open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json
- conformance/edit_subfield/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend the existing parametrized tests)

Acceptance tests:
- Every `edit_subfield` case passes the conformance suite and
  `tests/test_reference.py` on the host, so each characterized form matches MarcEdit.
- The existing parametrized importer test gains one row per characterized form
  (translated) and the parametrized not-translated test gains an
  uncharacterized form, so the importer can't guess.
- The existing invalid-task test gains `edit_subfield` rows (bad code, unknown
  action, missing required setting), rejected by both loader and schema.
- All existing tests pass unchanged, so moving validators into command modules
  breaks nothing.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
