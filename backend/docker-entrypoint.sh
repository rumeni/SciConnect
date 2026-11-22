#!/bin/sh
# Bring the database up to date before the API starts, and optionally load the
# demo catalog. Seeding is skipped unless APP_SEED_ON_STARTUP is true, and the
# seed itself is a no-op once the catalog holds any data, so a restart against
# an existing volume changes nothing.
set -e

# Manual Compose starts still migrate by default. In digest-pinned releases
# the deploy workflow runs a one-off migration after verifying a DB backup.
case "${APP_RUN_MIGRATIONS:-true}" in
  true) alembic upgrade head ;;
  false) echo "Migrations handled by the approved release workflow" ;;
  *) echo "APP_RUN_MIGRATIONS must be true or false" >&2; exit 1 ;;
esac

if [ "${APP_SEED_ON_STARTUP:-false}" = "true" ]; then
  python -m app.seed
fi

exec "$@"
