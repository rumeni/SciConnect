#!/usr/bin/env bash
# Operator-only app rollback. Database migrations are NEVER automatically undone.
set -Eeuo pipefail
umask 077
[[ "${CONFIRM_DB_COMPATIBLE:-}" == "yes" ]] || {
  echo "Set CONFIRM_DB_COMPATIBLE=yes only after checking migration compatibility" >&2
  exit 1
}
choice="${1:-}"
[[ "$choice" == "current" || "$choice" == "previous" ]] || {
  echo "Usage: CONFIRM_DB_COMPATIBLE=yes bash remote_rollback.sh current|previous" >&2
  exit 2
}
root="$HOME/SciConnect"
state="$root/release-state"
file="$state/$choice-release"
[[ -r "$file" ]] || { echo "No recorded $choice release" >&2; exit 1; }
exec 9>"$state/deploy.lock"
flock -n 9 || { echo "Another release or rollback is in progress" >&2; exit 1; }

read -r sha api_image frontend_image < "$file"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 2
digest_regex='^ghcr.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$'
[[ "$api_image" =~ $digest_regex && "$frontend_image" =~ $digest_regex ]] || exit 2
release="$root/releases/$sha"
[[ -f "$release/compose.prod.yaml" && -f "$release/compose.release.yaml" ]] || {
  echo "Old release bundle missing; cannot roll back" >&2; exit 1;
}

export SCICONNECT_API_IMAGE="$api_image" SCICONNECT_FRONTEND_IMAGE="$frontend_image"
compose=(docker compose -p sciconnect --project-directory "$release" \
  -f "$release/compose.prod.yaml" -f "$release/compose.release.yaml" \
  --env-file "$root/.env.production")
"${compose[@]}" config --quiet
# Pull only the selected, immutable application digests. Never pull mutable
# postgres/caddy tags as an accidental side effect of application rollback.
"${compose[@]}" pull api frontend
"${compose[@]}" up -d --no-build --pull never --wait --wait-timeout 180
# The app may boot but be unhealthy at its public HTTPS entrypoint.
# Promote rollback state only after public/API smoke and DB readiness.
domain="$(sed -n 's/^SITE_DOMAIN=//p' "$root/.env.production" | tail -n 1)"
domain="${domain%\"}"
domain="${domain#\"}"
[[ "$domain" =~ ^[a-zA-Z0-9.-]+$ ]] || exit 1
ready=false
for attempt in $(seq 1 12); do
  if curl --proto '=https' --tlsv1.2 -fsS --max-time 10 \
      "https://$domain/" >/dev/null 2>&1 &&
     curl --proto '=https' --tlsv1.2 -fsS --max-time 10 \
       "https://$domain/api/v1/health" >/dev/null 2>&1 &&
     curl --proto '=https' --tlsv1.2 -fsS --max-time 10 \
       "https://$domain/api/v1/catalog/institutions" >/dev/null 2>&1 &&
     "${compose[@]}" exec -T api python -c \
       'import json,urllib.request; body=json.load(urllib.request.urlopen("http://localhost:8000/api/v1/health/database",timeout=10)); assert body["database"]=="ok" and body["migration"]' \
       >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 5
done
[[ "$ready" == "true" ]] || { echo "Rollback smoke failed; release state unchanged" >&2; exit 1; }

if [[ "$choice" == "previous" ]]; then
  # Swap previous/current only after a healthy rollback. Retain the former
  # current SHA as a deliberate option for a later roll-forward.
  cp -- "$state/current-release" "$state/previous-release.new"
  cp -- "$file" "$state/current-release.new"
  mv -- "$state/current-release.new" "$state/current-release"
  mv -- "$state/previous-release.new" "$state/previous-release"
fi
echo "Operator rollback healthy and recorded: $sha"
