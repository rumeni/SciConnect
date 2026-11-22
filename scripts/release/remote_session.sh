#!/usr/bin/env bash
# Operator-approved release session. Start detaches work from SSH, status
# reports a durable server-side result, worker owns isolated registry auth.
set -Eeuo pipefail
umask 077

mode="${1:-}"
sha="${2:-}"
attempt="${3:-}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid release SHA" >&2; exit 2; }
[[ "$attempt" =~ ^[0-9]{1,20}-[0-9]{1,6}$ ]] || {
  echo "Invalid unique GitHub attempt ID" >&2; exit 2;
}
root="$HOME/SciConnect"
release="$root/releases/$sha"
state="$root/release-state"
attempts="$state/deploy-attempts"
folder="$attempts/$attempt"
script="$release/scripts/release/remote_deploy.sh"

case "$mode" in
  start)
    [[ $# == 6 ]] || exit 2
    api_image="$4"
    frontend_image="$5"
    registry_user="$6"
    digest_regex='^ghcr.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$'
    [[ "$api_image" =~ $digest_regex && "$frontend_image" =~ $digest_regex ]] || exit 2
    [[ "$registry_user" =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
    [[ -f "$script" && -f "$release/compose.release.yaml" ]] || exit 1
    mkdir -p "$attempts"
    chmod 700 "$attempts"
    # mkdir is atomic: a rerun of the same GitHub attempt cannot start twice.
    mkdir "$folder" || { echo "Attempt ID already exists: $attempt" >&2; exit 1; }
    chmod 700 "$folder"
    auth_dir="$folder/docker-auth"
    mkdir -m 700 "$auth_dir"
    started=false
    trap 'if [[ "$started" != true ]]; then rm -rf -- "$auth_dir"; fi' EXIT
    # A short-lived read-only registry token reaches Docker ONLY via stdin;
    # never use ~/.docker/config.json on the production host.
    DOCKER_CONFIG="$auth_dir" docker login ghcr.io \
      --username "$registry_user" --password-stdin >/dev/null
    # Both stdout and stderr are server-side, with stdin disconnected. The
    # launched process and its lock survive runner cancellation or SSH loss.
    nohup setsid bash "$release/scripts/release/remote_session.sh" \
      worker "$sha" "$attempt" "$api_image" "$frontend_image" \
      >"$folder/release.log" 2>&1 </dev/null &
    worker_pid=$!
    printf '%s\n' "$worker_pid" > "$folder/worker.pid"
    started=true
    echo "RELEASE_STARTED $sha $attempt"
    ;;
  worker)
    [[ $# == 5 ]] || exit 2
    api_image="$4"
    frontend_image="$5"
    auth_dir="$folder/docker-auth"
    [[ -d "$auth_dir" && -f "$script" ]] || exit 1
    export DOCKER_CONFIG="$auth_dir"
    trap 'rm -rf -- "$auth_dir"' EXIT
    # We must record an exit code even when migrations or Compose fail.
    set +e
    bash "$script" "$sha" "$api_image" "$frontend_image"
    result=$?
    set -e
    printf '%s\n' "$result" > "$folder/exit-code.new"
    mv -f -- "$folder/exit-code.new" "$folder/exit-code"
    exit "$result"
    ;;
  status)
    [[ $# == 3 ]] || exit 2
    [[ -d "$folder" ]] || { echo "Unknown release attempt" >&2; exit 1; }
    if [[ -f "$folder/exit-code" ]]; then
      code="$(cat "$folder/exit-code")"
      if [[ "$code" == "0" ]] &&
         grep -Fx "RELEASE_OK $sha" "$folder/release.log" >/dev/null; then
        echo "RELEASE_OK $sha $attempt"
      else
        echo "RELEASE_FAILED $sha $attempt"
      fi
    elif [[ -f "$folder/worker.pid" ]] &&
         kill -0 "$(cat "$folder/worker.pid")" 2>/dev/null; then
      echo "RELEASE_RUNNING $sha $attempt"
    else
      echo "RELEASE_UNKNOWN $sha $attempt"
    fi
    ;;
  *)
    echo "Usage: remote_session.sh start|status|worker SHA ATTEMPT ..." >&2
    exit 2
    ;;
esac
