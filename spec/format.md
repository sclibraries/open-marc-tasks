# Open MARC task format v0.1

## Task object

A task is a UTF-8 JSON object with these required properties:

| Property | Type | Meaning |
|---|---|---|
| `format_version` | string | The literal value `"0.1"`. |
| `name` | string | A human-readable task name. |
| `description` | string | A human-readable description. |
| `steps` | array | Commands to apply in order to each record. |

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
