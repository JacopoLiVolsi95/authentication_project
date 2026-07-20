#!/bin/bash

# Discover current directory
SOURCE="${BASH_SOURCE[0]}"
while [[ -h "$SOURCE" ]]; do # resolve $SOURCE until the file is no longer a symlink
	DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
	SOURCE="$(readlink "$SOURCE")"
	# if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
	[[ ${SOURCE} != /* ]] && SOURCE="$DIR/$SOURCE"
done
THIS_SCRIPT_DIR=$(dirname "$(realpath "${BASH_SOURCE[0]}")")

BACKUP_DIR="${THIS_SCRIPT_DIR}/db_backups"
mkdir -p "${BACKUP_DIR}"

# Generate a timestamp for the filename
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="${BACKUP_DIR}/auth_service_${TIMESTAMP}.sql.gz"

echo "[${TIMESTAMP}] Will backup databse into ${BACKUP_DIR}"

# Execute pg_dump inside Docker and compress the output
POSTGRES_CONTAINER_NAME="postgres"
docker exec -t "${POSTGRES_CONTAINER_NAME}" bash -c 'pg_dump -U "${POSTGRES_USER}" ${POSTGRES_DB}' | gzip > "${BACKUP_FILE}"
return_value=${?}
if [ ${return_value} -eq 0 ]; then
    echo "[${TIMESTAMP}] Backup successfully saved to ${BACKUP_FILE}"
else
    echo "[${TIMESTAMP}] ERROR: Database backup failed!" >&2
    exit 1
fi

# Delete backup archives older than 30 days
find "${BACKUP_DIR}" -type f -name "*.sql.gz" -mtime +30 -delete
