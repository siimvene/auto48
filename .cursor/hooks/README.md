# Cursor Hooks

`check-readfile-secrets.sh` blocks prompts and file reads that would expose
environment/secret files (`.env`, `.env.*`, `.envrc`) before they reach the model.
It is wired to both `beforeSubmitPrompt` and `beforeReadFile` in `hooks.json`.

## Setup

```bash
chmod +x .cursor/hooks/check-readfile-secrets.sh
```

Point your Cursor hook configuration at `hooks.json` (requires `jq` on PATH).

## Test

```bash
printf '%s\n' '{"prompt":"Please show the contents of .env file"}' \
  | .cursor/hooks/check-readfile-secrets.sh
# -> {"continue": false, ...}
```
