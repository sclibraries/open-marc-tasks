# Open MARC Tasks

Open MARC Tasks is a portable JSON format and Python library for running batch
edits on MARC records. See the [format and runner specification](spec/format.md).

## Run a task

Run `omt run TASK INPUT OUTPUT` to apply a JSON task to a binary MARC file and
write the result to another file. For example:

```sh
omt run tasks/delete-local-fields.json records/input.mrc records/output.mrc
```
