Title: Add build_field (fields built from other fields' data) and import MarcEdit buildnewfield

Status: Ready
Size: M
Tier: major — format contract: placeholder syntax and build modes other implementations must follow
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-015

Why:
- `buildnewfield` is the largest remaining blocker: 163 lines in the Smith and
  UMass task files. Catalogers use it to build 035s from 003/001
  (`=035  9\\$a({003}){001}`), proxy 856s from 956 or 857 URLs
  (`=856  40$uhttps://proxy…?url={956$u[x]}$y…`), 876/852 holdings fields, and
  new 001s (`=001  FCSAF{950$a}`).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic
records). Line form: `buildnewfield<TAB>template<TAB>f1<TAB>f2<TAB>f3<TAB>f4`;
f1 is always `False` in real files. Real files use three flag combinations:
- `False|False|False|True` (121 lines): always add. Placement follows add_field's
  MarcEdit order (before the first field with an equal or greater tag; a 001
  built this way lands before the existing 001, giving two).
- `False|False|True|False` (12 lines): add only when no field with the tag exists.
- `False|True|False|False` (30 lines): replace every existing field with the tag,
  in place, each with the same built field (two 950s both replaced); if the tag
  is absent, nothing happens. Works for control fields (001, 003).
- `True|False|False|False`: did nothing in probes; no real lines use it.
Template, as MarcEdit text form (OMT-011), with placeholders:
- `{TAG}`: a control field's data; for a data field, its text-form body
  (`{956}` → `40$uhttp://x$znote`), whose `$` codes become subfields of the new field.
- `{TAG$c}`: the first `$c` value in the first field with that tag.
- `{TAG$c[x]}`: one new field per field with that tag (source order, all before
  the next greater tag), each using that field's first `$c`; other placeholders
  in the same template take their usual first value. Real files have at most one
  `[x]` per template and use `[x]` only with "always add".
- A missing source gives empty text (`$h{050$a} {050$b}` → `$h `).
- A built data field whose subfields are all empty is not added
  (`$a{956$z}` on a record without 956 adds nothing; `$a$bQ` and `$aP` are added).
  With `[x]` and no source fields, one field is built from empty values and the
  same rule applies.
- Indicators are the characters before the first `$`: `\` is a blank, `9\` and
  `\` alone are accepted (a missing indicator is blank). Real files often have
  a third character (`=035  9\\$a…`, 48 lines). MarcEdit writes it into the
  record as an extra indicator byte; pymarc drops it when reading, so a
  MarcEdit-made `expected.mrc` reads as indicators `9` and blank.

Design (the spec records it):
- **Step** `build_field`: settings `field` (template string: `=TAG  ` + body in
  the text form, plus placeholders) and `mode`: `"add"` (default),
  `"add_if_missing"`, `"replace"`; optional `when` (existing conditions).
- **Placeholders**: exactly `{NNN}`, `{NNN$c}`, `{NNN$c[x]}` (three ASCII digits,
  code one lowercase ASCII letter or digit). Other `{…}` sequences that aren't
  text-form escapes are rejected at load with the step number. At most one
  `[x]` placeholder, and only with `mode` `"add"`; otherwise rejected at load.
- **Building**: substitute each placeholder with the source in text form
  (escaped as `render_field` escapes it, so a `$` in a source value stays a
  literal `$`), normalize the indicator part by the rule above, then parse with
  `parse_field`. Characterize with MarcEdit a source value containing `$`; if
  MarcEdit splits it into subfields, keep v0.1 lossless and document the
  difference in the spec, as with `{dollar}`.
- **Empty rule** as observed. Characterize and specify: an empty control-field
  result in `add` and `replace`; an all-empty data-field result in `replace`.
- **Deliberate difference**: v0.1 writes a valid two-indicator field and never
  the extra indicator byte. The spec says so.
- Reuse add_field's placement code; don't copy it.

Scope:
- `open_marc_tasks/commands/build_field.py`, table entry in `task.py`; spec and
  schema; `ARCHITECTURE.md` status line.
- Importer: the three real flag combinations → `build_field` with the matching
  `mode`. Not translated, with a reason: f1 `True`, any other combination, an
  unsupported `{…}` (mnemonics), more than one `[x]`, `[x]` outside "always add".
- Conformance cases under `conformance/build_field/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): 035 from
  `({003}){001}` with `9\\` indicators on two records, one without 003; `[x]`
  proxy 856 over two source 856s (one with two `$u`) and a record without the
  source; two placeholders with one missing (`$h{050$a} {050$b}`); whole-field
  `{956}`; `add_if_missing` with the tag present and absent; `replace` on a
  repeated data field and on 001; the all-empty skip.

Out of scope:
- f1, other flag combinations, Leader placeholders, character mnemonics, other commands.

Likely files:
- open_marc_tasks/commands/build_field.py, open_marc_tasks/commands/add_field.py (shared placement only)
- open_marc_tasks/task.py, open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/build_field/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host, so placement, modes, placeholders, `[x]`, the empty rule and the
  indicator rule match MarcEdit.
- The invalid-task parametrize gains: a missing or non-string `field`, an
  unknown `mode` (loader and schema); an unsupported `{eacute}`, two `[x]`
  placeholders, `[x]` with `replace`, and a template whose tag isn't three
  digits (loader, with the step number).
- The importer parametrize gains each of the three combinations (translated)
  and f1 `True`, `False|True|True|False`, a mnemonic and two `[x]` (not translated).
- Existing add_field cases pass unchanged (shared placement).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Plan:
1. Characterize the open points (`$` in a source value, empty control and replace results) with the reference runner.
2. Spec and schema: build_field, placeholders, modes, empty and indicator rules, differences.
3. build_field with shared placement; importer mapping.
4. Conformance cases via regenerate; extend tests; ARCHITECTURE.md; gates.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
