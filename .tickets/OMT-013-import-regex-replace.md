Title: Import MarcEdit regex REPLACE lines, including their Leader conditions

Status: In-Review
Size: S
Tier: normal — importer behavior; no format change
Milestone: M2 — Commands
Base: the local `main` commit that adds this ticket
Branch: codex/OMT-013

Why:
- The library runs regex `replace_text` (OMT-012), but the importer still
  reports all 142 regex REPLACE lines in the Smith and UMass task files as not
  translated. Three importer gaps were found by OMT-012's plan check
  (findings 2, 4, 5).

Scope:
- `marcedit_import.py`:
  - `REPLACE<TAB>find<TAB>replace<TAB>2<TAB><TAB>0<TAB>False` → `replace_text`
    with `regex: true`.
  - `REPLACE<TAB>find<TAB>replace<TAB>2<TAB>condition<TAB>2<TAB>False` →
    `regex: true` plus `when`, where the condition is a **bare** Leader-class
    regex (`=LDR.{8}[e,f,g,k].+`, `=LDR.{8}[a,c,d,i,j,m,o,p,r,t][c,m,s,i].+`),
    mapped exactly as ADD 106 maps its `/…/` form. Keep the delimiter rule per
    command: ADD needs `/…/`, REPLACE needs bare. Share only the inner parsing.
  - In regex mode, `{n}`, `{n,}` and `{n,m}` are quantifiers, not MarcEdit
    character mnemonics; any other `{name}` in a regex find or replace stays not
    translated (plain mode keeps its existing mnemonic rule).
  - A translated step must pass `load_task` (the OMT-012 dialect and replacement
    rules); if it doesn't, the line is not translated with the loader's reason.
    In particular the .NET-only replacement forms (`$0`, `$+`, `$&`, `$$`, `${`,
    `` $` ``, `$'`, `$_`, `$` + two digits) are not translated.
  - Everything else stays not translated (other options, `True` flags, `0|1`,
    non-Leader conditions).
- Spec "Importing MarcEdit tasks": list the new mappings.

Out of scope:
- Library behavior, SUBFIELD_EDIT `0|2`, REPLACE `0|1`.

Likely files:
- open_marc_tasks/marcedit_import.py, spec/format.md
- tests/test_marcedit_import.py (extend the parametrized tests)

Acceptance tests:
- The translated-lines parametrize gains: an unconditional regex REPLACE
  (`(=008.{25}).{1}(.+)` → `$1o$2`); a regex REPLACE with each of the two bare
  Leader conditions above, producing the right Leader positions; a pattern with
  `\w{1,3}` (quantifier braces are not mnemonics). Each document passes `load_task`.
- The not-translated parametrize gains: a `$&` replacement, a lookahead pattern,
  a `{eacute}` in a regex find, a non-Leader condition, and ADD with a bare
  condition, a half-delimited `/=LDR.{8}g.+` and a double-delimited
  `//=LDR.{8}g.+//` condition, so ADD import is unchanged.
- Existing importer rows still pass unchanged.

Verification:
- The Python 3.9 gate in AGENTS.md "Build and test".
- The orchestrator reruns the private 100-task measurement after the check.

Handoff:
- (orchestrator fills in after the check)

Review:
- (orchestrator fills in)
