Title: Add build_field (fields built from other fields' data) and import MarcEdit buildnewfield add forms

Status: In-Review
Size: M
Tier: major — format contract: placeholder syntax and build modes other implementations must follow
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-015

Why:
- `buildnewfield` is the largest remaining blocker: 163 lines in the Smith,
  UMass EDS CC and UMass FOLIO task files (standalone `.txt` files and `.task`
  archive members; the measure tool's folders). Catalogers build 035s from
  003/001 (`=035  9\$a({003}){001}`), proxy 856s from 956 or 857 URLs
  (`=856  40$uhttps://proxy…?url={956$u[x]}$y…`), 876/852 holdings fields.
  This ticket covers the two add forms (133 lines). Replace mode (30 lines,
  mostly new 001s) is OMT-016, split after the plan check.

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic
records; script and lines in `open-marc-tasks-coordination/runs/OMT-015/probes.md`).
Line form: `buildnewfield<TAB>template<TAB>f1<TAB>f2<TAB>f3<TAB>f4`; f1 is
always `False` in real files. Every real data-field template has exactly two
indicator characters.
- `False|False|False|True` (121 lines): always add. Placement is add_field's
  MarcEdit order (before the first field with an equal or greater tag; a 001
  built this way lands before the existing 001, giving two).
- `False|False|True|False` (12 lines): add only when no field with the tag exists.
- `False|True|False|False` (replace, OMT-016) and f1 `True` (did nothing; no real lines): not here.
Placeholders in the template (MarcEdit text form, OMT-011):
- `{TAG}`: the source field's text-form body: control data with blanks as `\`;
  for a data field, indicators plus `$`-subfields (`{956}` → `40$uhttp://x$znote`),
  whose `$` codes become subfields of the new field.
- `{TAG$c}`: the first `$c` in the first field with that tag that has `$c`
  (035 `$z` only, then 035 `$a(A)1` → `(A)1`).
- `{TAG$c[x]}`: one new field per field with that tag that has `$c`, in source
  order, each using that field's first `$c` (an 856 with two `$u` gives one field);
  other placeholders keep their first value. If no field has `$c`, one field is
  built with the placeholder empty. Real files have at most one `[x]`, only with
  always-add. Added fields go in source order before the first field with an
  equal or greater tag, also when the template's tag is the source's tag
  (`=035  \\$aX{035$a[x]}` reads the 035s before adding).
- A missing source gives empty text (`$h{050$a} {050$b}` → `$h `).
- Substitution is textual, then decoded once: a source `$`, `{x}`, accents and
  a supplementary character come through unchanged; `{lcub}001{rcub}{001}` gives
  `{001}abc123` (escapes are never expanded as placeholders). Because the text
  form shows control blanks as `\`, a 001 `a b` inserted into a subfield gives
  `a\b`, and a subfield `a\b` inserted into a control field gives `a b`.
- Empty results: a built data field whose subfields are all empty is not added
  (`$a{956$z}` without 956 adds nothing); a space-only value counts as data
  (`$a $b…`); `$aP`, `$a$bQ` are added with their empty subfields kept. A built
  control field with empty data is added (`=009  {950$a}` without 950 → empty 009).

Design (the spec records it):
- **Step** `build_field`: settings `field` (template: `=TAG  ` + body in the text
  form, with placeholders) and `mode`: `"add"` (default) or `"add_if_missing"`;
  optional `when` (existing conditions). OMT-016 adds `"replace"`.
- **Placeholders**: exactly `{NNN}`, `{NNN$c}`, `{NNN$c[x]}` (three ASCII digits;
  code one lowercase ASCII letter or digit), found in the template in one pass.
  Any other `{…}` that isn't a text-form escape is rejected at load with the step
  number, as is more than one `[x]`, `[x]` with `add_if_missing`, and a template
  that doesn't parse as a field when each placeholder is replaced by empty text.
- **Building**: read every source from the record before changing it; replace
  each placeholder with the source's text form as `render_field` writes it
  (subfield values as `render_field` escapes them); parse the result once with
  `parse_field`. `parse_field` stays as it is.
- Reuse add_field's placement code; don't copy it. One `[x]` expansion inserts
  its fields together, in source order (not by repeated single inserts, which
  reverse order).

Scope:
- `open_marc_tasks/commands/build_field.py`, table entry in `task.py`; spec and
  schema; `ARCHITECTURE.md` status line.
- Importer: the two add combinations → `build_field` (reusing command
  validation so every translated step passes `load_task`). Not translated, with
  source, line and reason: replace (`False|True|False|False`, OMT-016), f1
  `True`, any other combination, an unsupported `{…}` (mnemonics), more than one
  `[x]`, `[x]` with add-if-missing, a template that doesn't parse.
- Conformance cases under `conformance/build_field/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`):
  1. 035 from `({003}){001}` with `9\` indicators on two records, one without 003;
  2. `[x]` proxy 856 over two source 856s (one with two `$u`) plus a `{035$a}`
     placeholder used twice, and a record without 856;
  3. `[x]` where the first source field lacks the code, and a self-tag `[x]` (035 from 035);
  4. `$h{050$a} {050$b}` with 050 `$b` missing on one record;
  5. whole-field `{956}` and `{001}` with a blank into a subfield;
  6. a source with `$`, `{x}`, `é`, a supplementary character and `\`, into a
     subfield and into a control field; `{lcub}001{rcub}{001}`;
  7. `add_if_missing` with the tag present on one record and absent on another;
  8. the empty rules: all-empty data skipped, space-only kept, empty control added.

Out of scope:
- Replace mode (OMT-016), f1, other flag combinations, Leader placeholders,
  character mnemonics, other commands.

Likely files:
- open_marc_tasks/commands/build_field.py, open_marc_tasks/commands/add_field.py (shared placement only)
- open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/build_field/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped), so placement, modes, placeholders, `[x]`, text-form
  substitution and the empty rules match MarcEdit.
- Existing add_field cases (repeated add order, option 108) and `parse_field`
  tests pass unchanged.
- The invalid-task parametrize gains: a missing or non-string `field`, an unknown
  `mode` (loader and schema); `{eacute}`, two `[x]`, `[x]` with `add_if_missing`,
  a tag that isn't three digits, and a data template with a bad subfield code
  (loader, with the step number).
- The importer parametrize gains both add combinations (translated, and the
  result passes `load_task`) and, not translated: the replace form, f1 `True`,
  `False|True|True|False`, a mnemonic, two `[x]`, `[x]` with add-if-missing.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Plan:
1. Spec and schema: build_field, placeholders, add modes, substitution and empty rules.
2. build_field with shared placement; importer mapping.
3. Conformance cases via regenerate; extend tests; ARCHITECTURE.md; gates.

Plan check (2026-11-17, OMT-015 01-verify, BLOCKING) answered:
- 1 (third indicator character): right; the orchestrator's survey miscounted.
  The indicator rule is removed; templates use the normal text form.
- 2 (escape for the destination): MarcEdit substitutes text form and decodes
  once (probes above); the spec follows MarcEdit, and cases 5–6 pin it.
- 3, 4, 12 (dollar and empty open points): characterized; no divergence left;
  `$` and non-ASCII come through unchanged (case 6).
- 5 (worktree, reference copy): wrong for this flow; the runner creates the
  worktree and copies MarcEdit at build time.
- 6 (probe evidence): attached in the coordination run records.
- 7, 8, 9, 13: added (escape vs placeholder, `[x]` with ordinary placeholders and
  a first field lacking the code, source-order insertion and self-tag reads,
  load-time rejections and importer rows).
- 10, 11 (replace): replace has its own behaviors (an all-empty replace makes
  MarcEdit write no output for the whole file), so it moved to OMT-016.
- 14, 15: confirmed; census boundary named in Why; `parse_field` stays strict.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
