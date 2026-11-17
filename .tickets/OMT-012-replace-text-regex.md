Title: Add regex mode to replace_text with a portable regex dialect

Status: In-Progress
Size: M
Tier: major — format contract: regex dialect and replacement syntax other implementations must follow
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-012

Why:
- 142 of the 288 `REPLACE` lines in the Smith and UMass task files are regular
  expressions over the field text form (OMT-011), for example
  `(=008.{25}).{1}(.+)` → `$1o$2` and `(=001  )(\w{1,3})(.+)` → `$1$3`. This
  ticket builds regex mode in the library; importing those lines is OMT-013.
  Split twice by plan checks (OMT-011 01-verify; OMT-012 01-verify findings 1–10).

Observed with real MarcEdit 7.6 (orchestrator probes 2026-11-17, synthetic records):
- matching runs on each field's text form separately; `^` matches each field line;
  a pattern spanning two fields never matches; `.+` stops at the end of the field;
- alternation takes the first alternative that succeeds (`(a|ab)` on `ab` → group `a`);
  greedy quantifiers backtrack as in Python (`(.+)(.+)` on `abc` → `ab|c`;
  `(\w{1,3})(.+)` on `ab12` → `ab1|2`, on `ab` → `a|b`);
- replacement: a reference to a group that exists but didn't participate inserts
  nothing; a reference to a group that doesn't exist (`$9` with one group) stays
  literal text; `$0`, `$+` and `$01` have .NET meanings (whole match, last group, group 1);
- MarcEdit's regex sees UTF-8 records as single bytes: `\w` matched the first byte of
  `é` and the replacement split the character. Same with and without `-utf8`.
- patterns that can match empty text (`x*`, `a*|b`) gave no useful result.

Design (the spec records it):
- **Setting**: `replace_text` gains `regex` (boolean, default `false`). Plain mode
  is unchanged: `find` and `replace` are literal text.
- **Characters**: regex mode works on Unicode code points of the field text form.
  Deliberate difference from MarcEdit (orchestrator's call, documented in the
  spec like the `{dollar}` difference): MarcEdit's byte-level matching can split
  multi-byte characters; v0.1 never does. Results differ only where a pattern
  steps over non-ASCII text; the real task patterns work on ASCII fields.
- **Dialect**, enforced by `load_task` through our own small parser (no
  `sre_parse`): literal characters (any code point except those below);
  escapes `\. \/ \? \$ \\ \( \) \[ \] \+ \* \{ \} \| \^ \-`; `.` (any code point
  except LF); classes `[...]` with literal characters, escapes and ranges, and a
  leading `^` for negation; `\d \w \s` with ASCII meaning (`[0-9]`,
  `[A-Za-z0-9_]`, `[ \t\n\r\f\v]`), also inside classes; groups `(...)`;
  alternation `|`; greedy quantifiers `* + ? {n} {n,} {n,m}` (n ≤ m); anchors
  `^` (line start) and `$` (line end only, not before a final newline). Rejected
  at load with `TaskError` and the step number: anything else (lookaround,
  `(?…)` groups and inline flags, lazy or possessive quantifiers, `{,n}`,
  backreferences, `\b` and other escapes, class operations like `[a-z-[aeiou]]`
  or `[a&&b]`), malformed patterns (`[`, `(`, `a{3,1}`), and **any pattern that
  can match empty text**. Escaped or in-class parentheses are not groups. Once
  valid, the implementation may compile an equivalent Python pattern (with
  `re.ASCII`, `$` translated to `\Z`).
- **Matching**: leftmost, first-alternative, greedy with backtracking,
  non-overlapping, left to right, every match in the line.
- **Replacement** in regex mode: `$1`–`$9` insert that group (empty if it didn't
  participate; literal text if the pattern has fewer groups, as MarcEdit does);
  every other character, including `\` and a `$` not followed by a digit 1–9, is
  literal. `$` followed by two digits, `$0`, `$+`, `$&`, `$$`, `${`, `` $` ``,
  `$'` and `$_` are rejected at load (ambiguous or .NET-only). Substitute with
  a callback, once: captured text containing `$2` or backslashes is inserted as is.

Scope:
- Regex mode in `commands/replace_text.py`; `open_marc_tasks/regex_dialect.py`
  (validator and translation); spec and schema; `ARCHITECTURE.md` status.
- Conformance cases under `conformance/replace_text/` (synthetic records, ASCII
  in the matched text; `expected.mrc` only from `tools/marcedit_reference.py
  regenerate`; each case's `marcedit-task.txt` is the MarcEdit REPLACE line):
  008 position edit with a group (`(=008.{25}).{1}(.+)` → `$1o$2`); 001 prefix
  drop with `\w{1,3}` on two different 001 values; a multi-group URL rewrite in
  856 $u; `(a|ab)` and `(.+)(.+)` capture splits; per-line `^` on a repeated
  field; a replacement ending in `\` (`$1\`); an unmatched optional group; a
  reference to a nonexistent group (`$9`).
- No importer changes (OMT-013).

Out of scope:
- REPLACE import and conditions (OMT-013), SUBFIELD_EDIT `0|2`, REPLACE `0|1`.

Likely files:
- open_marc_tasks/commands/replace_text.py, open_marc_tasks/regex_dialect.py
- spec/format.md, spec/task.schema.json, ARCHITECTURE.md
- conformance/replace_text/<case>/…
- tests/test_task_loading.py (extend parametrized tests)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host, so regex matching, capture splits and replacement match MarcEdit.
- The loading parametrize separates shape errors (loader and schema reject:
  non-boolean `regex`) from dialect errors (loader rejects with the step number;
  schema only checks a string): `(?=a)`, `(?i)a`, `a+?`, `a++`, `(?>a)`, `a{,3}`,
  `(a)\1`, `\bx`, `[a-z-[aeiou]]`, `[a&&b]`, `[`, `(`, `a{3,1}`, `x*`, `a*|b`,
  and replacements `$12`, `$0`, `$&`, `${1}`. Existing rows keep requiring both.
- The same parametrize accepts `\(\?i\)`, `\\b`, `[+?]` and `[(]x` as valid
  regex patterns (escaped and in-class metacharacters are literal).
- A parametrized test of semantics the conformance cases can't show without
  non-ASCII data: `\d` doesn't match `٣`, `\w` doesn't match `é`, `\s` doesn't
  match a no-break space, `.` matches `é` and a supplementary character as one
  character, and `$` doesn't match before a trailing newline.
- In plain mode, `find` `a.b(` and `replace` `$1` are literal.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.

Plan:
1. Spec: regex mode, dialect, replacement, the byte-level difference.
2. regex_dialect validator and translation; regex mode with a replacement callback.
3. Conformance cases via regenerate; extend tests; ARCHITECTURE.md; gates.

Plan check (2026-11-17, OMT-012 01-verify, BLOCKING) answered:
- 1, 6 (character classes, characters, anchors): characterized; MarcEdit is
  byte-level; v0.1 works on code points with ASCII classes and documents the difference.
- 2, 3 (replacement syntax): characterized; rules above; ambiguous or .NET-only forms rejected at load.
- 4, 5 (mnemonic guard vs `{n}`, bare Leader conditions): importer work, moved to OMT-013.
- 7 (empty matches): patterns that can match empty text are rejected.
- 8 (alternation, greedy splits): characterized; conformance cases pin them.
- 9 (validator rejections): listed above and in the acceptance tests.
- 10: counts confirmed (syntactic coverage only).

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
