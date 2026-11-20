Title: Extend the regex dialect for MarcEdit's ISBD rules (lazy quantifiers, punctuation escapes, \D, literal braces)

Status: Completed
Size: S
Tier: normal — widens the documented regex dialect; no command changes
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-032

Why:
- The next ticket imports MarcEdit's REMOVEISBD rule file (about 200 regex
  rules) as regex rules. 133 of them are rejected by the OMT-012 dialect today
  (orchestrator check 2026-11-19 against the owner's private rule file):
  lazy quantifiers (69, e.g. `(=020\s{2}\\{2}\$.+?)(\$q)\((.+)\)`), escaped
  punctuation `\:` (30), `\,` (14), `\;` (10), `\=` (2), `\D` (16, e.g.
  `(\sCo|\sLtd|\sInc|Dr|Sr|Jr|\s\D|\sed)$`), and one rule with a typo,
  `(=880\s{2]\\{2}\$6020\-\d{2}.+?)…`, which .NET reads as `\s` followed by the
  literal text `{2]`.

Design (the spec records it in the dialect section):
- Lazy quantifiers `*?`, `+?`, `??`, `{n}?`, `{n,}?`, `{n,m}?`: match as few as
  possible, with backtracking (as .NET and Python do). Possessive stays rejected.
- Any ASCII punctuation character may be escaped with `\` to mean itself
  (outside and inside classes). Escaped letters other than the defined classes
  stay rejected.
- `\D` matches any code point that `\d` doesn't (consistent with the dialect's
  ASCII `\d`); likewise add `\W` and `\S` for symmetry only if the code needs no
  extra branch for them, otherwise leave them out.
- A `{` that does not start a valid `{n}`, `{n,}` or `{n,m}` quantifier is a
  literal character, as in .NET (`\s{2]` is `\s` then the text `{2]`); an
  unmatched `}` stays a literal only where .NET treats it as one — characterize
  `a}` and `a{2` with MarcEdit and follow it.
- Characterize each new form with MarcEdit 7.6 through a `REPLACE` regex line
  (the existing replace_text conformance pattern) before writing the spec.

Scope:
- `open_marc_tasks/regex_dialect.py`, `spec/format.md` dialect section.
- Conformance cases under `conformance/replace_text/` (synthetic records,
  `expected.mrc` only from `tools/marcedit_reference.py regenerate`): a lazy
  quantifier whose greedy result would differ; escaped `\:` `\,` `\;` `\=`; `\D`;
  a literal `{2]`.

Out of scope:
- Any command, the importer, the rule files themselves.

Likely files:
- open_marc_tasks/regex_dialect.py, spec/format.md
- conformance/replace_text/<case>/…
- tests/test_task_loading.py (extend the dialect-invalid rows only if a
  currently-rejected row becomes valid and must change)

Acceptance tests:
- Every new conformance case passes the suite and `tests/test_reference.py` on
  the host (not skipped).
- The existing dialect-invalid parametrize still rejects possessive
  quantifiers, lookaround and an escaped letter such as `\q` (change rows that
  this ticket makes valid, and say which in the handoff).

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- On the host from the worktree: `python3 -m pytest -q tests/test_reference.py`, counts reported.
- The orchestrator checks that every rule in the private ISBD file compiles and
  reruns the measurement (must stay 81/100, 0 differing).

Handoff:
- Head b99abed, merged into main (owner OK 2026-11-20). Python 3.9 gate 242 passed, 1 skipped; host reference passed. All 209 private ISBD rules compile. Measure 81/100, 0 differ.

Review:
- Lazy quantifiers, punctuation escapes, \D, .NET literal braces/brackets; `a+?` and `a{,3}` rows removed as now valid. No fix round.
