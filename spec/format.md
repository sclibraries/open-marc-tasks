# Open MARC task format v0.1

## Task object

A task is a UTF-8 JSON object. `format_version`, `name`, `description`, and
`steps` are required; `normalize_typography` is optional.

| Property | Type | Meaning |
|---|---|---|
| `format_version` | string | The literal value `"0.1"`. |
| `name` | string | A human-readable task name. |
| `description` | string | A human-readable description. |
| `steps` | array | Commands to apply in order to each record. |
| `normalize_typography` | boolean | Whether to apply MarcEdit's observed typography normalization to every record before task steps. Defaults to `false`. |

The JSON Schema for this object is `task.schema.json`. Unknown task properties,
commands, and command settings are errors. A task file is data and is never
evaluated or imported.

## Runner

`load_task(path)` reads and validates a task, raising `TaskError` when the file
cannot be read, its JSON is malformed, or its contents do not match this
version of the format. A step error identifies its one-based step number.

`run_task(task, records)` consumes an iterable of pymarc records once, applies
each step in order to each record in place, and yields records in their input
order. Records are Unicode; MARC-8 conversion and file input/output are outside
this version.

## Record handling

Before running task steps, `run_task` replaces each backslash data-field
indicator with a blank on every input record, including records no step changes.
Backslashes in subfield values are unchanged.

When `normalize_typography` is `true`, `run_task` also normalizes control-field
data and data-field subfield values on every record before running task steps,
including records no step changes. It maps `“` and `”` to `"`, `‘` and `’` to
`'`, `—` and `–` to `-`, and `…` to `...`. A no-break space (U+00A0) is unchanged.
No other characters are normalized by this option. Its default is `false` so
tasks that omit it do not change record text.

## Command: `delete_field`

A step has the form:

```json
{"command": "delete_field", "tag": "029"}
```

`tag` is exactly three characters, each an ASCII digit or uppercase `X`. The
command removes every matching control or data field and preserves the order of
all remaining fields. A trailing `X` or run of `X` characters matches any digit
in those positions; for example, `9XX` matches tags from `900` through `999`.

MarcEdit 7.6 does not treat an `X` before a later digit as a wildcard: its
`0X9` delete task reports tag `09` and deletes no fields. To match that observed
behavior, a pattern with an `X` followed by a digit is valid task data but
matches no fields. An exact tag such as `009` can delete a control field.

`match` is an optional string. By default, a matching-tag field is deleted
when its rendered field text contains `match`. Matching is a case-sensitive
substring search over the entire field text line, including `=TAG  ` and the
body described in [Field text form](#field-text-form). For example,
`"match": "\\\\$a(OCoLC)"` matches a subfield prefix after blank indicators.
Without `match`, every field with a matching tag is deleted.

`match_regex` is an optional boolean that defaults to `false`. When true,
`match` is a regular expression in the dialect defined for `replace_text`; it
is searched against each whole field text line. `^` and `$` anchor the start
and exact end of that line. A regex that is invalid or can match empty text is
rejected when the task is loaded.

`delete_nonmatches` is an optional boolean that defaults to `false`. When true,
the command deletes matching-tag fields whose field text does not match
`match`, and keeps fields whose text does match. It requires `match`.

## Conditions

A command that supports conditions may have an optional `when` array. Each
item is a condition that must hold for the command to run; all items must hold.
An empty array imposes no condition. This version defines Leader membership
conditions:

```json
{"leader": 6, "in": ["a", "m", "t"]}
```

`leader` is a zero-based position from 0 through 23 in the record Leader. `in`
is a non-empty array of one-character strings. The condition holds when the
Leader character at that position equals any item in `in`. A command without
`when` runs without a condition check.

## Command: `add_field`

A data-field step has this form:

```json
{
  "command": "add_field",
  "tag": "506",
  "ind1": "1",
  "ind2": " ",
  "subfields": [["a", "Text"], ["5", "MU"]]
}
```

`tag` is three ASCII digits. For data fields, `ind1` and `ind2` are each one
character, and `subfields` is a non-empty array of `[code, value]` pairs. A
subfield code is one lowercase ASCII letter or digit; a value is a string.
For a control field (`00X`), use `data` (a string) instead of indicators and
subfields:

```json
{"command": "add_field", "tag": "006", "data": "m        "}
```

`if_tag_exists` controls duplicate handling and defaults to `"add"`:

| Value | Behavior | MarcEdit option |
|---|---|---|
| `"add"` | Always add the field. | 100 (default) |
| `"skip"` | Skip when any field with the same tag exists. | 101 |
| `"skip_if_identical"` | Skip only when an identical field exists; otherwise add it. | 108 |

An identical data field has the same tag, indicators, and ordered subfield
codes and values. An identical control field has the same tag and data.

With `"add"`, the new field is inserted before the first existing field
whose tag is equal to or greater than the new tag, or at the end if there is
no such field. Thus a new field precedes existing fields with the same tag,
and repeated additions of one tag appear in reverse step order.

With `"skip_if_identical"`, when the tag exists but no identical field does,
the new field is inserted after the last existing field with that tag and
before the first field with a greater tag. If the tag is absent, it is
inserted before the first field with a greater tag, or at the end if there is
none. `"skip"` only adds when the tag is absent, so it follows that same
absent-tag placement.

If any `when` condition is false for a record, the field is not added. For
example, the following requires both conditions to hold:

```json
{
  "command": "add_field",
  "tag": "655",
  "ind1": " ",
  "ind2": "7",
  "subfields": [["a", "Text."], ["2", "local"]],
  "when": [{"leader": 6, "in": ["a", "m", "t"]}, {"leader": 7, "in": ["m"]}]
}
```

## Command: `build_field`

`build_field` builds a field from a text-form template and source fields:

```json
{
  "command": "build_field",
  "field": "=035  9\\$a({003}){001}",
  "mode": "add"
}
```

`field` is a field text form as defined in [Field text form](#field-text-form),
with placeholders. After replacing placeholders with empty text, it must parse
as a field. `mode` is optional and defaults to `"add"`:

| Value | Behavior |
|---|---|
| `"add"` | Add the built field or fields. |
| `"add_if_missing"` | Add only when the record has no field with the template's tag. |
| `"replace"` | Replace every existing field with the template's tag in place. If the tag is absent, make no change. |

The optional `when` setting uses the Leader conditions defined above. All
conditions must hold for the step to run.

The supported placeholders are `{NNN}`, `{NNN$c}`, and `{NNN$c[x]}`, where
`NNN` is a three-digit tag and `c` is one lowercase ASCII letter or digit.
`{NNN}` inserts the first matching field's body in field text form: control
data with blanks shown as `\`, or a data field's two indicators and
`$`-subfields. Templates for control-field tags (`000`–`009`) may not contain
a whole-field placeholder for a data-field tag (`010`–`999`), because
data-field indicators and subfield delimiters are not valid control-field data.
`{NNN$c}` inserts the first `$c` value found among fields with
that tag. If the source field or subfield is missing, the placeholder becomes
empty. A text-form escape such as `{dollar}`, `{lcub}`, `{rcub}`, or `{bsol}`
is literal and is not a placeholder. Any other brace expression is invalid.

There may be at most one `{NNN$c[x]}` placeholder. It builds one output field
for each source field with tag `NNN` that contains subfield `c`, in source
order, using that source field's first `$c` value. If none contains `$c`, it
builds one field with that placeholder empty. `{x}` cannot be used with
`"add_if_missing"`. Other placeholders keep their normal first-value behavior
for each output field. `{x}` cannot be used with `"replace"`. All source
values are read before adding or replacing fields, including when a source tag
equals the template tag.

Substitution uses the source values' field text form, then the completed
template is parsed as a field. A value's `$`, braces, backslashes,
non-ASCII characters, and supplementary characters are substituted as text;
text-form escapes introduced by a source value are not expanded as
placeholders. `{lcub}001{rcub}{001}`, for example, inserts `{001}` followed by
the 001 value. Control-field blanks display as `\` in field text form, so a
control value `a b` inserted into a data subfield becomes `a\b`. A data
subfield value inserted into a control field retains its characters, with
template backslashes decoded as control-field blanks when the result is
parsed.

For `"add"` and `"add_if_missing"`, built fields use the `add_field` tag-order
placement: before the first field whose tag is equal to or greater than the
built field's tag. Multiple fields from `{x}` are inserted together in source
order. `"add_if_missing"` checks for any field with the template's tag before
building fields. A data field is added only when at least one subfield value
is non-empty; spaces count as content, and empty subfields are kept when
another subfield has content. A control field is added even when its data is
empty.

With `"replace"`, each existing field with the template's tag is replaced at
its current position by a separately built field. Repeated target fields are
all replaced, using the same source-placeholder rules above. A control field
is replaced even when its data is empty. A data-field result must have at
least one non-empty subfield value; otherwise the step raises a run-time error
that names the record and step. This prevents a task from silently dropping
the output when MarcEdit produces an empty file for an all-empty data-field
replace.

## Command: `copy_field`

`copy_field` copies every field with one exact source tag to another tag:

```json
{"command": "copy_field", "from_tag": "856", "to_tag": "857"}
```

`from_tag` and `to_tag` are three ASCII digits and must differ. A data field
cannot be copied to a control tag (`00X`), and a control field cannot be copied
to another control tag. A control field can be copied to a data tag. `move` is
an optional boolean that defaults to `false`; when true, the selected source
fields are removed after their copies are made. If no source field is selected,
the record is unchanged.

`if_contains` is an optional non-empty string. A source field is selected when
its complete rendered field text line contains this string as a case-sensitive
substring. The line includes `=TAG  ` and the field body described in
[Field text form](#field-text-form). Field-text escapes in the rendered text,
such as `{dollar}`, `{lcub}`, and `{rcub}`, are matched in their rendered form.

Data fields keep their indicators and ordered subfields when copied. Copies
from a data-field source are inserted in source order after existing fields
with the destination tag, and before the first field with a greater tag (or at
the end if there is none). For example, copying two 945 fields to 949 places
both copies after the 945 fields and before 950.

When copying a control field to a data tag, the result has blank indicators
and one `$a` subfield containing the source field's rendered body. Thus a
blank in `001` data is represented by `\` in the copied subfield value. These
copies use the `build_field` tag-order placement and precede existing fields
with the destination tag. For example, copying `001` to `035` places the new
035 before existing 035 fields.

The MarcEdit importer translates COPY lines with the default columns: empty
columns 6 and 8, and `false` in column 7. It supports empty matches and
non-empty matches on data-field sources. The field-text match escapes
`{dollar}`, `{lcub}`, and `{rcub}` are preserved. Other `{…}` mnemonics and
filtered control-field sources are reported as not translated: MarcEdit 7.6
did not produce a copy for the synthetic filtered control-field probes, so
their match behavior is not defined here. Control-to-control COPY lines are
not imported because MarcEdit's synthetic reference output encoded copied
values as data-like control fields and interleaved repeated copies with the old
target fields; these mappings are rejected when a task is loaded.

## Command: `edit_subfield`

A step edits subfields of data fields with one exact tag:

```json
{"command": "edit_subfield", "tag": "949", "code": "h", "action": "add", "value": "Online"}
```

`tag` is three ASCII digits. `code` is one lowercase ASCII letter or digit.
For each matching data field, the command applies the action to every matching
subfield. Repeated fields with the same tag are processed. If no field has the
tag, no change is made. The optional `when` setting uses the Leader conditions
defined above; all conditions must hold.

| `action` | Required settings | Behavior |
|---|---|---|
| `add` | `value` | Append a new subfield with `code` and `value` to every matching field, even if it already has that code. |
| `add_if_missing` | `value` | Append one new subfield only to matching fields that have no subfield with `code`. Existing values are unchanged. |
| `replace` | non-empty `find`, `replace` | Replace every literal, case-sensitive occurrence of `find` in every matching subfield value. `replace` may be empty, which removes the matched text. |
| `replace_first` | non-empty `find`, `replace` | Replace only the first literal, case-insensitive occurrence of `find` in each matching subfield value. `replace` may be empty. |
| `replace_regex` | non-empty `find`, `replace` | Apply every match of `find` in the matching subfield's code followed by value, using the regex dialect and replacement rules defined for `replace_text`. The first character of a non-empty result becomes the subfield code and the rest becomes its value. An empty result removes the subfield. A non-empty result with an invalid code raises a run-time error naming the record and step. |
| `append` | `value` | Append `value` to every matching subfield value. |
| `prepend` | `value` | Prepend `value` to every matching subfield value. |
| `clear` | none | Set every matching subfield value to the empty string, leaving the subfields in place. |

The observed MarcEdit 7.6 `SUBFIELD_EDIT` forms map as follows:

| Find | Replace | Flags | `edit_subfield` settings |
|---|---|---|---|
| empty | text | `102|0` | `action: "add"`, `value: replace` |
| literal text | text | `0|0` | `action: "replace"`, `find`, `replace` |
| `^e` | text | `0|0` | `action: "append"`, `value: replace` |
| `^b` | text | `0|0` | `action: "prepend"`, `value: replace` |
| empty | text | `101|0` | `action: "add_if_missing"`, `value: replace` |
| literal text | empty | `0|0` | `action: "replace"`, `find`, `replace: ""` |
| empty | empty | `0|0` | `action: "clear"` |
| literal text | text | `0|1` | `action: "replace_first"`, `find`, `replace` (case-insensitive) |
| regex | text | `0|2` | `action: "replace_regex"`, `find`, `replace` |

For `replace_regex`, `find` uses the portable regex dialect and replacement
rules defined for `replace_text`. Each matching subfield is treated as the
string formed by its code followed by its value. Matching and replacement use
Unicode code points, and every non-overlapping match is replaced from left to
right. The resulting first character must be a lowercase ASCII letter or
digit. An empty result removes the subfield, but a data field left with no
subfields is retained, matching MarcEdit 7.6.

## Command: `remove_subfield`

A step removes subfields with one exact tag and code:

```json
{"command": "remove_subfield", "tag": "856", "code": "z"}
```

`tag` is three ASCII digits and must identify a data field (`010` through
`999`). `code` is one lowercase ASCII letter or digit. The optional
`if_contains`, `remove_text`, and `remove_regex` settings are non-empty
strings and at most one can be present.

Without either setting, every matching subfield is removed. With
`if_contains`, each matching subfield whose value contains that case-sensitive
literal substring is removed. These whole-subfield forms apply to all matching
fields. A data field left with no subfields is deleted.

With `remove_text`, every case-sensitive occurrence of the literal text is
removed from each matching subfield value. The subfield remains even when its
value becomes empty. If no field or subfield matches, no change is made.

With `remove_regex`, the portable regex dialect defined for `replace_text` is
applied to each matching subfield's code followed by value. Every
non-overlapping match is removed from left to right. If the result is empty,
the subfield is removed; otherwise its first character becomes the code and
the rest becomes the value. A non-empty result with an invalid code raises a
run-time error naming the record and step. A data field left with no subfields
is deleted.

## Field text form

The `replace_text` command edits the text form of one field. It is one line:
`=` followed by a three-digit tag, two spaces, and the body. The Leader is not
part of this form.

For a control field (tag `001` through `009`), the body is its data. For a data
field, the body starts with indicator 1 and indicator 2, followed by each
subfield in order as `$`, its one-character code, and its value. A blank
indicator is written as `\`. In a control-field body, each blank is also
written as `\`.

The field text escapes are `{dollar}` for a literal dollar sign, `{lcub}` for
`{`, `{rcub}` for `}`, and `{bsol}` for a literal backslash in control-field
data. A literal backslash in a data-field subfield value is written as itself.
The special text `{dollar}` in a value is therefore written
`{lcub}dollar{rcub}`. Unmatched braces and unknown brace text are literal in
field values. The parser decodes recognized escapes once, from left to right;
it does not scan decoded characters again. This preserves literal escape-like
text such as `{dollar}`. MarcEdit 7.6 writes that literal text with the same
brace escapes but decodes it to `$` when it reparses a changed field; v0.1
uses one-pass decoding to preserve the original value.

On parsing a changed field text, the tag must be exactly three ASCII digits
and the line must start with `=` and the two-space separator. Tags `001`
through `009` produce control fields, whose body decodes `\` to a blank.
Other tags produce data fields and require two indicator characters. In those
two positions, `\` decodes to a blank. After the indicators, the body is zero
or more subfields, each beginning with `$` and followed by a lowercase ASCII
letter or digit code; its value runs up to the next `$` or the end of the
body. Values may be empty. An empty control-field body, a data field with no
subfields, repeated subfields, and trailing spaces are valid. Retagging
between control and data field forms is allowed. A parsed replacement stays
at the original field position.

## Command: `sort_fields`

A step has one of these forms:

```json
{"command": "sort_fields", "scope": "all"}
{"command": "sort_fields", "scope": "0xx"}
```

`scope` is required. With `all`, fields are stably sorted by their complete
[field text form](#field-text-form). With `0xx`, fields whose tags begin with
`0` are stably sorted by the same key and placed first; all other fields keep
their original relative order after them. The sort is stable, so equal keys
retain their input order. The reference cannot expose the tie order of exact
duplicate field text because those fields are identical; it preserves their
multiplicity.

To compare field text forms, encode the complete line as UTF-8, decode each
byte as Windows-1252, and compare the resulting strings by Unicode code point.
The Windows-1252 bytes `0x81`, `0x8D`, `0x8F`, `0x90`, and `0x9D`, which that
codec leaves undefined, map to Unicode code points U+0081, U+008D, U+008F,
U+0090, and U+009D respectively. This includes the `=TAG  ` prefix, indicators,
and field content. Thus `=650  10$aZ` sorts before `=650  \0$aA`, and control
fields participate in the same ordering: an empty `001` precedes `001` with
data `Z`, followed by tags `003` and `008`. The reference is MarcEdit's
command-line version running with invariant globalization; a Windows desktop
install might compare differently.

## Command: `replace_text`

A plain-mode step has this form:

```json
{"command": "replace_text", "find": "old", "replace": "new"}
```

`find` is a non-empty string; `replace` is a string and may be empty. The
optional `regex` setting is a boolean that defaults to `false`. With `regex:
false`, `find` and `replace` are literal text, including regex punctuation,
backslashes, and dollar signs. The optional `when` setting uses the Leader
conditions defined above.

For each record where all conditions hold, fields are visited in record order.
Each field is rendered in the field text form. Plain mode replaces every
non-overlapping literal occurrence of `find` from left to right. Matching is
case-sensitive. If the text changes, it is parsed back into a field at the
same position. An invalid result raises an error naming the one-based record
and step numbers.

With `regex: true`, `find` uses the following portable dialect:

- Matching uses Unicode code points in each field's text form separately.
  Each field is treated as one string, even when its content contains LF; `^`
  matches its start and `$` its exact end. Matching is case-sensitive.
  MarcEdit 7.6 processes UTF-8 regex text as bytes, so its results can differ
  when a pattern consumes non-ASCII text. This format never splits a Unicode
  character.
- Ordinary characters match themselves. The literal escapes are `\.`, `\/`,
  `\?`, `\$`, `\\`, `\(`, `\)`, `\[`, `\]`, `\+`, `\*`, `\{`, `\}`,
  `\|`, `\^`, and `\-`. The escapes `\d`, `\w`, and `\s` match ASCII
  `[0-9]`, `[A-Za-z0-9_]`, and `[ \t\n\r\f\v]`, respectively. A dot
  matches any code point except LF. `^` and `$` are anchors, parentheses
  create groups, `|` separates alternatives, and quantifiers have the forms
  below. `/` and `-` are literal outside character classes, whether escaped
  or not. An unescaped `]` or unmatched `}` is invalid.
- A character class uses square brackets, may begin with `^` to negate the
  class, and may contain literal characters, escaped characters, the three
  ASCII classes above, and character ranges such as `a-z`. Class subtraction
  and intersection are not supported. Parentheses inside a class are literal.
- Parentheses create capturing groups, numbered from left to right. `|`
  separates alternatives. Greedy `*`, `+`, `?`, `{n}`, `{n,}`, and `{n,m}`
  quantifiers are supported, where `n` and `m` are non-negative integers and
  `n` must not exceed `m`. `^` matches the start of the field text form and `$`
  matches only its exact end, not the position before a trailing newline.
- Matching is leftmost, uses the first alternative that can match, and uses
  greedy quantifiers with backtracking. Every non-overlapping match is
  replaced from left to right.
- The pattern must be valid and must not be able to match an empty string.
  Lookaround, non-capturing or inline-flag groups, lazy or possessive
  quantifiers, backreferences, unsupported escapes, malformed expressions,
  and class operations are rejected when the task is loaded. `TaskError`
  identifies the one-based step number.

Regex-mode replacements use `$1` through `$9` to insert the corresponding
capturing group. A group that did not participate inserts an empty string. A
reference to a group number not present in the pattern remains literal text.
All other characters, including backslashes and a dollar sign not followed by
`1` through `9`, are literal. `$0`, multi-digit group references, and the .NET
replacement forms `$$`, `$+`, `$&`, `${...}`, `` $` ``, `$'`, and `$_` are
rejected when the task is loaded. Captured text is inserted once and is not
interpreted again as replacement syntax. The resulting field text is parsed
under the field-text rules above, so literal syntax inserted by a replacement
is interpreted there; `{dollar}` encodes a dollar sign within a field value.

Replacement runs after the record handling above. In particular,
backslash-indicator conversion happens first, and typography is normalized
first only when `normalize_typography` is true. With its default `false`,
unrelated curly quotes, dashes, and no-break spaces are preserved. MarcEdit
7.6 also normalizes curly quotes, dashes, and ellipses during a plain REPLACE
with its default setting; v0.1 follows `normalize_typography` instead. A
no-break space is unchanged by either behavior.

## Record matching

`records_match(a, b)` compares records without changing either input. It
compares every field's tag, indicators, control-field data, subfield codes and
subfield values exactly, including whitespace, and compares fields in order.
It also compares Leader positions 05–09 and 17–19. It ignores field 005 and
Leader positions 00–04 and 12–16 (including the record length and base address).

## Conformance

Each `conformance/<command>/<case>/` directory contains `task.json`,
`input.mrc`, `expected.mrc`, and `marcedit-task.txt`. Regenerate expected
records with the local MarcEdit reference copy using
`python tools/marcedit_reference.py regenerate <case-dir>...`. All public
conformance data is synthetic and uses `example.edu` where a domain is needed.
If MarcEdit writes an empty output for a no-change task, use the input records
with backslash indicators blanked and typography normalized, matching MarcEdit's
written output.

## Importing MarcEdit tasks

`omt import SOURCE OUT_DIR` imports a tab-separated MarcEdit task file or a
`.task` archive containing `.txt` task entries. It translates tag-only `DELETE`
lines with default settings and lines with a non-empty match when column A is
`0` (plain substring) or `2` (regex). DELETE matching uses the whole field text
line, including `=TAG  `. MarcEdit's second boolean flag (`f2`) maps to
`delete_nonmatches`; the other boolean flags must be `False`. Tag-only DELETE
lines translate only with A=`0` and all boolean flags `False`. Tag patterns
such as `9XX` are preserved. ADD options 100, 101, and 108 map to
`if_tag_exists` values `add`, `skip`, and `skip_if_identical`. Option 106 uses
`add` and supports only the
Leader conditions `/=LDR.{N}[letters].+/`,
`/=LDR.{N}[letters][letters].+/`, and `/=LDR.{N}x.+/`; commas in brackets
separate allowed characters. Conditions may have the same one, two, or three
slashes on both sides; other slash wrappers are not translated. ADD field text
supports blank indicators (`\`), subfield markers (`$a`), and the `{dollar}`
literal. Control-field ADD lines become `data` values. Descriptions come from
`#DESCRIPTION#` lines.

MarcEdit `SORTBY` lines with target `ALL` and a pair of `True`/`False` flags
map to `sort_fields` with scope `all`. Target `0XX` maps to scope `0xx` with
or without a pair of `True`/`False` flags. Other targets and unsupported flag
forms are reported as not translated.

The characterized `SUBFIELD_EDIT` forms map to `edit_subfield` as shown above,
including regex option `0|2`, which maps to `replace_regex`. Regex patterns and
replacement strings are validated with the `replace_text` dialect when the
task is loaded.

`SUBFIELD_REMOVE` lines have five tab-separated columns. Empty-value forms with
options `107|0` or `0|0` map to `remove_subfield` without a filter. With a
non-empty value, `107|0` maps to `if_contains`, and `0|0` maps to `remove_text`.
Regex option `0|2` with a non-empty value maps to `remove_regex` and is
validated with the `replace_text` regex dialect when the task is loaded. Other
regex options are not translated. The value mnemonics `{dollar}`, `{lcub}`,
and `{rcub}` become their literal characters for non-regex forms. **Difference
from MarcEdit.** An empty-value `9|0` line maps to
`remove_subfield` without a filter, intentionally clearing barcode, material
type, and holdings-prefix subfields before copies are built; MarcEdit 7.6 makes
no change because an empty option-9 value matches nothing. Option `9|…` with a
non-empty value is reported as not translated with the reason
`option 9 with a value is not supported`; other options, control-field tags,
and unsupported character mnemonics are also reported as not translated.

The plain `REPLACE` form with seven tab-separated columns, flags `0`, an empty
condition, flags `0`, and final flag `False` maps to `replace_text`. Other
plain REPLACE options and conditions, and find or replace text containing an
unsupported character mnemonic such as `{eacute}`, are reported as not
translated with their source and line number. Character mnemonics are not
field-text escapes.

Regex `REPLACE` lines with find flags `2`, an empty condition, replace flags
`0`, and final flag `False` map to `replace_text` with `regex: true`. They may
also use a bare Leader condition in one of the forms `=LDR.{N}[letters].+`,
`=LDR.{N}[letters][letters].+`, or `=LDR.{N}x.+`, mapped to the corresponding
zero-based Leader positions. Conditional lines use replace flags `2` in the
sixth column; the sixth column is `0` only when the condition is empty. Unlike
ADD option 106, REPLACE conditions have no slash delimiters. In regex find or
replace text, `{n}`, `{n,}`, and `{n,m}` are quantifiers, not character
mnemonics; any other `{name}` is unsupported.
Regex patterns and replacements that fail the task loader's `replace_text`
rules are reported as not translated with the loader's reason. Other REPLACE
flags, final flag `True`, `0|1`, and non-Leader conditions are not translated.

Unsupported lines are reported with their source and line number. A task is
written only when every line has been translated, so partial imports cannot be
run accidentally. Other MarcEdit commands, DELETE options outside the forms
above, character mnemonics, and other ADD condition forms are not translated.
