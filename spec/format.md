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
