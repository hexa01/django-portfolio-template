#!/bin/sh
# Nightly backup of the database and the uploads (media/), keeping the last 7 of each. Run from the repo root by
# cron, e.g.:
#   15 3 * * * cd /path/to/project && ./deploy/backup.sh >> backups/backup.log 2>&1
# Copy backups/ off the server now and then: a backup on the same disk doesn't survive losing the server.
set -eu
mkdir -p backups
stamp=$(date +%Y-%m-%d)
# the db container already has POSTGRES_USER/DB, so .env is never parsed by the shell (its values may contain symbols)
docker compose -f docker-compose.server.yml exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' > "backups/db-$stamp.dump"
tar -czf "backups/media-$stamp.tar.gz" media
ls -1t backups/db-*.dump | tail -n +8 | xargs -r rm --
ls -1t backups/media-*.tar.gz | tail -n +8 | xargs -r rm --
echo "$(date -Is) backup ok: backups/db-$stamp.dump backups/media-$stamp.tar.gz"
