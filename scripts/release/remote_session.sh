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

# Consult RUNNING logind over D-Bus: disk configuration can differ from
# what the daemon loaded, and KillOnlyUsers may override the global policy.
# Unknown/unavailable settings fail closed; never guess the distro default.
check_logind_policy() {
  command -v busctl >/dev/null || {
    echo "busctl required to inspect running systemd-logind" >&2; return 1;
  }
  local manager="org.freedesktop.login1.Manager"
  local service="org.freedesktop.login1"
  local object="/org/freedesktop/login1"
  local kill_all only_users
  kill_all="$(busctl get-property "$service" "$object" "$manager" KillUserProcesses)" || {
    echo "Cannot read running logind KillUserProcesses" >&2; return 1;
  }
  [[ "$kill_all" == "b false" ]] || {
    echo "Unsafe running logind KillUserProcesses ($kill_all)" >&2; return 1;
  }
  only_users="$(busctl get-property "$service" "$object" "$manager" KillOnlyUsers)" || {
    echo "Cannot read running logind KillOnlyUsers" >&2; return 1;
  }
  [[ "$only_users" == as\ * ]] || {
    echo "Unexpected logind KillOnlyUsers property" >&2; return 1;
  }
  if [[ "$only_users" == *"\"$USER\""* ]]; then
    echo "KillOnlyUsers contains deploy user $USER; refuse SSH-detached release" >&2
    return 1
  fi
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
    # Docker on Linux can auto-discover an external pass/secretservice helper
    # even with an empty config. Such credentials survive rm -rf of auth_dir.
    # Require inline auth stored ONLY in the per-attempt config, otherwise
    # revoke the helper entry and fail closed before launching the worker.
    if ! python3 - "$auth_dir/config.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    config = json.load(stream)
assert not config.get("credsStore") and not config.get("credHelpers")
registry = config.get("auths", {}).get("ghcr.io", {})
assert isinstance(registry.get("auth"), str) and registry["auth"]
PY
    then
      DOCKER_CONFIG="$auth_dir" docker logout ghcr.io >/dev/null 2>&1 || true
      echo "Registry auth escaped isolated DOCKER_CONFIG or was not saved inline" >&2
      exit 1
    fi
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
