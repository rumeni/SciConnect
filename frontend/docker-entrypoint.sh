#!/bin/sh
# node_modules is a named volume, so it shadows whatever the image installed and
# survives rebuilds. Without this, adding a dependency to package.json leaves the
# container with the older tree and Vite fails to resolve the new import.
# npm install is idempotent, so this is a quick no-op once the tree is in step.
set -e

npm install --no-audit --no-fund

exec "$@"
