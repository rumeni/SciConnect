#!/bin/sh
# Bring the database up to date before the API starts, and optionally load the
# demo catalog. Seeding is skipped unless APP_SEED_ON_STARTUP is true, and the
# seed itself is a no-op once the catalog holds any data, so a restart against
# an existing volume changes nothing.
set -e

alembic upgrade head

if [ "${APP_SEED_ON_STARTUP:-false}" = "true" ]; then
  python -m app.seed
fi

exec "$@"
