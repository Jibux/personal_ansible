#!/bin/bash


set -euo pipefail -o errtrace


date_prefix()
{
	date "+%Y-%m-%d %H:%M:%S"
}

err()
{
	echo "$(date_prefix) - ERROR ${1:-}" >&2
}

log()
{
	echo "$(date_prefix) - ${1:-}"
}

fail()
{
	err "${1:-Something wrong happened}"
	exit 2
}

sync()
{
	local src="$SRC_ROOT/$1"
	local dst="$2"

	log "Sync '$src' to '$dst'"
	rclone sync -P "$src/" "$dst/"
	log "Sync '$src' to '$dst' ended"
}


SCRIPT_PATH=$0
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
SCRIPT_FULL_NAME="$(basename "$SCRIPT_PATH")"
SCRIPT_NAME="${SCRIPT_FULL_NAME%.*}"
LOG_PATH="$SCRIPT_DIR/$SCRIPT_NAME.log"

trap 'fail "Something wrong happened line $LINENO"' ERR

exec &> "$LOG_PATH"

SRC_ROOT=/volume1

sync "JIBUX-DATA/JBH/Informatique" "pcloud_encrypted:JBH/Informatique"
sync "JIBUX-MEDIA/Photos-Images" "pcloud_encrypted:Photos-Images"
sync "JIBUX-MEDIA/Videos" "pcloud_encrypted:Media/Videos"
sync "JIBUX-MEDIA/Music" "pcloud_encrypted:Media/Music"
sync "JIBUX-MEDIA/Installations - Logiciels" "pcloud_encrypted:Media/Installations - Logiciels"
sync "JIBUX-MEDIA/Films" "pcloud_encrypted:Media/Films"

log "Finished - shutting down..."

sudo shutdown --poweroff now

