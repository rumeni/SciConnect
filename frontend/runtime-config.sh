#!/bin/sh
# Write the runtime configuration the page reads before it boots.
#
# Runs from the nginx image's startup hook directory, so it happens on every
# container start: pointing the deployment at a different API is an environment
# change and a restart, not a rebuild.
set -e

api_url="${VITE_API_URL:-${API_URL:-}}"
config="/usr/share/nginx/html/config.js"

if [ -n "$api_url" ]; then
  # Trailing slashes would produce "//api/v1/..." once paths are appended.
  api_url="${api_url%/}"
  printf 'window.__SCICONNECT__ = { apiUrl: "%s" };\n' "$api_url" > "$config"
  echo "runtime-config: API set to $api_url"
else
  printf 'window.__SCICONNECT__ = {};\n' > "$config"
  echo "runtime-config: no VITE_API_URL set, the page will call its own origin's default"
fi
