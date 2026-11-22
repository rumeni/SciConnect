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

# Fail closed on hardening configurations that kill detached SSH-session
# processes. Ubuntu's default is KillUserProcesses=no; a nondefault "yes"
# requires a separately rehearsed systemd-managed deployment worker.
check_logind_policy() {
  command -v systemd-analyze >/dev/null || {
    echo "Cannot inspect systemd-logind KillUserProcesses policy" >&2; return 1;
  }
  local policy
  policy="$(systemd-analyze cat-config systemd/logind.conf | awk -F= '
    /^[[:space:]]*KillUserProcesses[[:space:]]*=/ {
      x=$2; sub(/#.*/, "", x); gsub(/[[:space:]]/, "", x); value=x
    }
    END {print value}
  ')" || return 1
  [[ -z "$policy" || "$policy" == no ]] || {
    echo "KillUserProcesses=$policy: unsafe to detach from SSH; refuse release" >&2
    return 1
  }
}

# A new poll must never report UNKNOWN if the worker completed between two
# filesystem/process observations. Confirm both status and final sentinel.
report_finished() {
  [[ -f "$folder/exit-code" ]] || return 1
  local code
  code="$(cat "$folder/exit-code")"
  if [[ "$code" == "0" ]] &&
     grep -Fx "RELEASE_OK $sha" "$folder/release.log" >/dev/null; then
    echo "RELEASE_OK $sha $attempt"
  else
    echo "RELEASE_FAILED $sha $attempt"
  fi
}

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
    check_logind_policy || exit 1
    mkdir -p "$attempts"
    chmod 700 "$attempts"
    # Reap short-lived registry auth left behind by an old SIGKILL/reboot.
    # Never remove credentials for a live worker or a recently starting one.
    for stale_auth in "$attempts"/*/docker-auth; do
      [[ -d "$stale_auth" ]] || continue
      [[ -n "$(find "$stale_auth" -maxdepth 0 -mmin +1440 -print)" ]] || continue
      stale_folder="${stale_auth%/docker-auth}"
      if [[ -f "$stale_folder/worker.pid" ]] &&
         kill -0 "$(cat "$stale_folder/worker.pid")" 2>/dev/null; then
        continue
      fi
      rm -rf -- "$stale_auth"
    done
    # mkdir is atomic: a rerun of the same GitHub attempt cannot start twice.
    mkdir "$folder" || { echo "Attempt ID already exists: $attempt" >&2; exit 1; }
    chmod 700 "$folder"
    auth_dir="$folder/docker-auth"
    mkdir -m 700 "$auth_dir"
    # A temporary DOCKER_CONFIG must not hide a per-user installed Compose
    # CLI plugin. It must NOT copy the user's permanent registry credentials.
    if [[ -d "$HOME/.docker/cli-plugins" ]]; then
      ln -s "$HOME/.docker/cli-plugins" "$auth_dir/cli-plugins"
    fi
    DOCKER_CONFIG="$auth_dir" docker compose version >/dev/null || {
      echo "Docker Compose unavailable with temporary DOCKER_CONFIG" >&2
      exit 1
    }
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
    # This deployment deliberately uses the local Docker daemon, not a
    # context stored in the user's (unshared) ~/.docker/config.json.
    export DOCKER_CONTEXT=default
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
    if report_finished; then
      :
    elif [[ -f "$folder/worker.pid" ]] &&
         kill -0 "$(cat "$folder/worker.pid")" 2>/dev/null; then
      echo "RELEASE_RUNNING $sha $attempt"
    elif report_finished; then
      # The worker may have atomically written exit-code between the
      # first check and its process exit; never false-alarm UNKNOWN.
      :
    else
      echo "RELEASE_UNKNOWN $sha $attempt"
    fi
    ;;
  *)
    echo "Usage: remote_session.sh start|status|worker SHA ATTEMPT ..." >&2
    exit 2
    ;;
esac
