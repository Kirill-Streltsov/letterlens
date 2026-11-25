#!/usr/bin/env bash
# Store the Mistral API key without showing it: hidden prompt -> check -> Keychain + GitHub secret.
set -euo pipefail
REPO=Kirill-Streltsov/letterlens

printf "Paste your Mistral API key (input is hidden), then press Enter: "
read -rs KEY
echo
if [ -z "$KEY" ]; then echo "No key entered."; exit 1; fi

HEADER=$(mktemp)
chmod 600 "$HEADER"
printf 'Authorization: Bearer %s\n' "$KEY" > "$HEADER"
STATUS=$(curl -s -o /dev/null -w '%{http_code}' -H @"$HEADER" https://api.mistral.ai/v1/models || true)
rm -f "$HEADER"
if [ "$STATUS" != "200" ]; then
  echo "Mistral did not accept this key (HTTP $STATUS). Check it and run this script again."
  exit 1
fi

security add-generic-password -U -a letterlens -s letterlens-mistral-api-key -w "$KEY"
printf '%s' "$KEY" | gh secret set MISTRAL_API_KEY --repo "$REPO"
unset KEY
echo "Done: the key works and is stored in your Keychain and as the GitHub secret MISTRAL_API_KEY."
echo "You can close this tab."
