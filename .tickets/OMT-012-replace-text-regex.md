Title: Add regex mode to replace_text, with a portable regex dialect and REPLACE Leader conditions

Status: Ready
Size: M
Tier: major — format contract: regex dialect and replacement syntax other implementations must follow
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-012

Why:
- 142 of the 288 `REPLACE` lines in the Smith and UMass task files are regular
  expressions over the field text form (OMT-011): 30 unconditional and 112 with a
  Leader condition. Typical: `(=008.{25}).{1}(.+)` → `$1o$2` (set 008/23 to o),
  `(=001  )(\w{1,3})(.+)` → `$1$3` (drop an 001 prefix), 901 $a URL rewrites with
  several groups. Split from OMT-011 by its plan check (findings 2, 6, 10–13).

Design (the spec records it):
- **Setting**: `replace_text` gains `regex` (boolean, default `false`). With
  `regex: true`, `find` is a pattern in the dialect below and `replace` may use
  group references. Matching runs on each field's text form separately (observed
  2026-11-17: `^` matched each field line; a pattern spanning two fields never
  matched; `.+` stopped at the end of the field).
- **Dialect** (enforced by `load_task` with a small validator of our own; don't
  depend on `sre_parse`, which moved in Python 3.11+): literal characters,
  including non-ASCII literals such as `ǂ`; escapes `\. \/ \? \$ \\ \( \) \[ \] \+ \* \{ \} \| \^ \-`;
  `.`; classes `[...]` with ranges and `^` negation; `\d \w \s` with **ASCII**
  meaning (`[0-9]`, `[A-Za-z0-9_]`, ASCII whitespace); groups `(...)`;
  alternation `|`; greedy quantifiers `* + ? {n} {n,} {n,m}`; anchors `^ $` at
  field-line start and end. Anything else (lookaround, inline flags, lazy
  quantifiers, backreferences, named or non-capturing groups, `\b`, other
  escapes) is a `TaskError` at load with the step number, as is a malformed
  pattern such as `[` or `(`. Implementation may compile with Python `re` and
  `re.ASCII` once the pattern passes the validator.
- **Matching and replacement**: leftmost, greedy, non-overlapping, left to right,
  every match in the line. Characterize with MarcEdit how a pattern that can
  match empty text (for example `x*`) behaves, and specify exactly that; if
  MarcEdit and Python differ, implement MarcEdit's behavior explicitly rather
  than relying on the host engine.
- **Replacement syntax**: `$1`–`$9` insert that group (a group that didn't
  participate inserts nothing); a `$` followed by anything else is literal; a
  backslash is literal (the task files contain `$1\`). Apply replacements with a
  small callback; never pass replacement text to `re.sub` as a template.
  Characterize MarcEdit for `$1\`, `$12` and `$` at the end, and specify what
  you see; .NET constructs `$&`, `$$`, `${n}`, `` $` ``, `$'`, `$_` and
  references to groups 10+ are not part of the dialect: the importer reports
  them as not translated.
- **Leader conditions in REPLACE** are written without slashes
  (`=LDR.{8}[e,f,g,k].+`, `=LDR.{8}[a,c,d,i,j,m,o,p,r,t][c,m,s,i].+`). Extend the
  importer's Leader-condition parser to accept both the ADD form (`/…/`) and the
  bare form, mapping to the same `when` conditions; ADD's behavior must not change.

Scope:
- Regex mode in `commands/replace_text.py`; a dialect validator module; spec and
  schema; importer mapping for `REPLACE<TAB>find<TAB>replace<TAB>2<TAB><TAB>0<TAB>False`
  (regex) and `…<TAB>2<TAB><condition><TAB>2<TAB>False` (regex + Leader
  condition). Not translated, each with a reason: patterns outside the dialect,
  replacements with .NET-only constructs, non-Leader conditions, `True` flags,
  other options.
- Conformance cases under `conformance/replace_text/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): the 008
  position edit (books and maps via the two Leader conditions, plus a record that
  matches neither); an 001 prefix drop with `\w{1,3}`; a multi-group 901/856 URL
  rewrite; greedy `.+` splitting between two groups; per-line `^` anchor on a
  repeated field; a non-ASCII literal in the pattern; ASCII `\d` not matching a
  non-ASCII digit; the empty-match behavior; `$1\` trailing backslash; a group
  that didn't participate.

Out of scope:
- SUBFIELD_EDIT `0|2` regex (follow-up can reuse the dialect), REPLACE `0|1`,
  character mnemonics, the Leader line as a replace target.

Likely files:
- open_marc_tasks/commands/replace_text.py, open_marc_tasks/regex_dialect.py
- open_marc_tasks/marcedit_import.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/replace_text/<case>/…
- tests/test_task_loading.py, tests/test_marcedit_import.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host, so regex replacement, conditions, ASCII classes, empty matches and
  replacement syntax match MarcEdit.
- The loading parametrize distinguishes shape errors (rejected by loader and
  schema: non-boolean `regex`) from dialect errors (rejected by the loader with
  the step number; the schema only checks it's a string): lookahead `(?=`,
  inline flag `(?i)`, lazy `+?`, backreference `\1`, named group `(?P<x>`, `\b`,
  malformed `[` and `(`. Existing rows keep requiring both, unchanged.
- In plain mode (`regex` false or absent), a `find` such as `a.b(` and a
  `replace` such as `$1` are treated literally, so plain tasks don't change meaning.
- The importer parametrize gains: a regex line and a regex + bare Leader
  condition line (translated, with the right Leader positions); and not
  translated: a `$&` replacement, a lookahead pattern, a non-Leader condition.
  The existing ADD condition rows still pass, so ADD import is unchanged.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator reruns the private 100-task measurement after the check.

Plan:
1. Characterize empty matches and replacement edge cases with the reference runner.
2. Spec: regex mode, dialect, replacement syntax, condition forms.
3. Dialect validator; regex mode with a replacement callback; importer mapping.
4. Conformance cases via regenerate; extend tests; ARCHITECTURE.md; gates.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
