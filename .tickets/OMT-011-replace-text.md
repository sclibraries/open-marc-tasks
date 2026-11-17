Title: Add replace_text (MarcEdit REPLACE) on a documented text form of each field, with a portable regex subset

Status: Ready
Size: M
Tier: major — format contract: defines the field text form and a regex dialect other implementations must follow
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-011

Why:
- `REPLACE` is the largest remaining blocker in the Smith and UMass task files
  (288 lines). Catalogers use it for things field commands can't express:
  retagging (`=945  ` → `=949  `), changing indicators (`=852  0\` →
  `=852  8\`), adding or removing a proxy prefix in 856 $u, reordering
  subfields, and fixed-position 008 edits (`(=008.{25}).{1}(.+)` → `$1o$2`).

Design (decided here; the spec records it):
- **Text form of a field** (one line, MarcEdit's "mnemonic" form): `=` + tag +
  two spaces + body. Data field body: indicator 1, indicator 2 (a blank shown
  as `\`), then each subfield as `$` + code + value. Control field body: the
  data with each blank shown as `\`. A literal `$` in a value is written
  `{dollar}`. The Leader line is not part of `replace_text`. Characterize with
  MarcEdit how it writes a literal `\`, `{` and `}` in data, and include those
  escapes in the spec; any other `{name}` character mnemonic is out of scope.
- **`replace_text` step**: settings `find` (non-empty string), `replace`
  (string), `regex` (boolean, default `false`), optional `when` (existing
  conditions). For each record where `when` holds, for each field in order:
  render its text form, replace, and if the text changed, parse the result back
  into a field in the same position (the tag may change; order is kept — observed
  with MarcEdit: a retagged 945 stays where it was). Plain mode replaces every
  occurrence, case-sensitive (observed). Regex mode works on one field line at a
  time: `^` and `$` match the start and end of the line, `.` never crosses into
  another field (observed: a pattern spanning two fields never matches).
- **Regex dialect** (spec section, so a Java implementation can match it):
  literal characters and escapes (`\.`, `\/`, `\?`, `\$`, `\\`, `\(`, `\)`,
  `\[`, `\]`, `\+`, `\*`), `.`, character classes `[...]` with ranges and
  negation, `\d` `\w` `\s` (ASCII meaning), groups `(...)`, alternation `|`,
  quantifiers `*` `+` `?` `{n}` `{n,}` `{n,m}`, anchors `^` `$`. Replacement
  text may use `$1`–`$9` for groups; any other `$` in a replacement is literal.
  Patterns using anything else (lookaround, inline flags, lazy quantifiers,
  backreferences, named groups) are rejected by `load_task`. This subset covers
  every REPLACE pattern in the 100 task files.
- **A result that doesn't parse back into a valid field** (for example a tag
  that isn't three characters, or a data field without indicators) is a
  `TaskError`-style runtime error naming the record and step, not a silently
  dropped field.

Scope:
- Characterize first with real MarcEdit (reference runner): the text-form
  escapes above; that a replacement producing a control-field tag on a data
  field (or the reverse) behaves as the spec says, or record what MarcEdit does;
  and what option `0|1` (6 lines, plain, no seventh column) means — probe case
  and occurrence differences. If `0|1` can't be pinned down, leave it not translated.
- `open_marc_tasks/commands/replace_text.py` and a text-form module
  (render/parse) usable by later commands; spec, schema; validator rejects
  patterns outside the dialect.
- Importer: `REPLACE<TAB>find<TAB>replace<TAB>A<TAB>condition<TAB>B<TAB>flag`
  with `0|0|False` → plain; `2|0|False` → regex; `2|2|False` with a Leader-class
  condition (the forms the ADD 106 mapping already handles) → regex + `when`.
  Anything else (other options, other conditions, `True` flags, patterns outside
  the dialect) is not translated with a reason.
- Conformance cases under `conformance/replace_text/`, synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`: plain
  multi-occurrence and case; retag in place; indicator change; 856 proxy prefix
  add and remove; regex with groups (the 008 position edit); regex anchors per
  line; regex with a Leader condition (true and false records); a literal `$`
  via `{dollar}`.

Out of scope:
- SUBFIELD_EDIT `0|2` (regex) — a follow-up can reuse this dialect.
- Replacing on the Leader line, `{name}` character mnemonics beyond those
  characterized above, other commands.

Likely files:
- open_marc_tasks/commands/replace_text.py, open_marc_tasks/text_form.py
- open_marc_tasks/regex_subset.py (or inside replace_text.py if small)
- open_marc_tasks/task.py (table entry only), open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json
- conformance/replace_text/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized
  tests); tests/test_text_form.py only for render/parse round-trips the
  conformance cases can't reach

Acceptance tests:
- Every `replace_text` case passes the conformance suite and
  `tests/test_reference.py` on the host, so plain, regex, retag, indicator,
  condition and escape behavior match MarcEdit.
- Rendering then parsing returns an identical field for a control field with
  blanks, a data field with blank indicators, and a value containing `$`, so the
  text form round-trips without loss.
- The invalid-task parametrize gains rows for an empty `find`, a non-boolean
  `regex`, and patterns using lookahead `(?=`, an inline flag `(?i)`, a lazy
  `+?` and a backreference `\1`; loader and schema both reject each (schema may
  reject only the shape; the loader rejects the dialect).
- A replacement that yields an unparseable field raises an error naming the
  record and step number.
- The importer parametrize gains one translated row per mapped REPLACE form and
  not-translated rows for an unknown option, a non-Leader condition and a
  pattern outside the dialect.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Plan:
1. Characterize the open questions with the reference runner.
2. Spec: text form, replace_text, regex dialect.
3. text_form render/parse; replace_text; dialect validation.
4. Importer mapping; conformance cases via regenerate; extend tests; gates.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
