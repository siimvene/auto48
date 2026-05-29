#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"
prompt_text="$(printf '%s' "$payload" | jq -r '(.prompt // .text // .content // .user_prompt // empty)' | tr '[:upper:]' '[:lower:]')"
if ! command -v jq >/dev/null 2>&1; then
  echo '{"continue": false, "user_message": "Hook requires jq to parse file context."}'
  exit 0
fi

if [[ "$prompt_text" == *".env"*
  || "$prompt_text" == *"/.env/"*
  || "$prompt_text" == *".env."*
  || "$prompt_text" == *".envrc"* ]]; then
  echo '{"continue": false, "user_message": "Blocked: prompt appears to request environment file content."}'
  exit 0
fi

file_path="$(printf '%s' "$payload" | jq -r '
  [ .file_path, .path, .file, .uri, .filepath, .file_name, .fileName ]
  | map(select(type == "string"))
  | map(select(length > 0))
  | .[0]
' | tr '[:upper:]' '[:lower:]')"

if [ -z "$file_path" ] || [ "$file_path" = "null" ]; then
  file_path="$(printf '%s' "$payload" | jq -r '[.. | strings] | join(" ")' | tr '[:upper:]' '[:lower:]')"
fi

if [ -z "$file_path" ] || [ "$file_path" = "null" ]; then
  echo '{"continue": true}'
  exit 0
fi

if [ ! -f "$file_path" ]; then
  echo '{"continue": true}'
  exit 0
fi

file_name="$(basename "$file_path")"

if [[ "$file_path" == */.env \
  || "$file_path" == .env \
  || "$file_path" == .env.* \
  || "$file_name" == .env \
  || "$file_name" == .env.* \
  || "$file_name" == .envrc \
  || "$file_path" == */.envrc ]]; then
  echo '{"continue": false, "user_message": "Blocked: environment file access is not allowed."}'
  exit 0
fi

echo '{"continue": true}'
