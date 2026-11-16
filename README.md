# Open MARC Tasks

Open MARC Tasks is a portable JSON format and Python library for running batch
edits on MARC records. See the [format and runner specification](spec/format.md).

## Run a task

Run `omt run TASK INPUT OUTPUT` to apply a JSON task to a binary MARC file and
write the result to another file. For example:

```sh
omt run tasks/delete-local-fields.json records/input.mrc records/output.mrc
```

## Import MarcEdit tasks

Import a tab-separated MarcEdit task file or a `.task` archive with:

```sh
omt import SOURCE OUT_DIR
```

The importer writes JSON for tasks it translates completely and reports
unsupported lines for review. See [the import subset](spec/format.md#importing-marcedit-tasks).

## Developer: reference runs

With a local MarcEdit copy in `reference/marcedit/`, regenerate expected
outputs with:

```sh
python tools/marcedit_reference.py regenerate conformance/delete_field/*
```

Check the committed answers against fresh MarcEdit runs with
`python3 -m pytest -q tests/test_reference.py`.
