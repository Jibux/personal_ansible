#!/bin/bash


set -euo pipefail -o errtrace


date_prefix()
{
	date "+%Y-%m-%d %H:%M:%S"
}

dry_run_prefix()
{
	is_dry_run && printf " - DRY-RUN"
	return 0
}

err()
{
	echo "$(date_prefix)$(dry_run_prefix) - ERROR ${1:-}" >&2
}

log()
{
	echo "$(date_prefix)$(dry_run_prefix) - ${1:-}"
}

fail()
{
	err "${1:-Something wrong happened}"
	exit 2
}

is_dry_run()
{
	[ "$DRY_RUN" = "yes" ]
}

is_verbose()
{
	[ "$VERBOSE" = "yes" ]
}

sync()
{
	local src="$1"
	local dst="$2"

	[ -z "$src" ] && return 0
	[ -z "$dst" ] && return 0

	log "Sync '$src' to '$dst'"
	rclone sync "${RCLONE_OPTS[@]}" "$src/" "$dst/"
	log "Sync '$src' to '$dst' ended"
}

parse_backup_list()
{
	local line

	while read -r line || [ -n "$line" ]; do
		sync "${line%|*}" "${line#*|}"
	done < "$TMP_BACKUP_LIST"
}


SCRIPT_PATH=$0
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
SCRIPT_FULL_NAME="$(basename "$SCRIPT_PATH")"
SCRIPT_NAME="${SCRIPT_FULL_NAME%.*}"
LOG_PATH="$SCRIPT_DIR/$SCRIPT_NAME.log"
TMP_BACKUP_LIST=/tmp/.backup_list.txt
DRY_RUN=no
SHUTDOWN=no
VERBOSE=no
RCLONE_OPTS=()

trap 'fail "Something wrong happened line $LINENO"' ERR

exec &> "$LOG_PATH"

for i in "$@"; do
	case $i in
		--dry-run)
			DRY_RUN="yes"
			shift
			;;
		--shutdown)
			SHUTDOWN="yes"
			shift
			;;
		--verbose)
			VERBOSE="yes"
			shift
			;;
		-*)
			usage
			exit 1
			;;
	esac
done

[ "$SHUTDOWN" = "yes" ] && log "Will shutdown the NAS at the end of the execution"

is_verbose && RCLONE_OPTS=("--verbose")
is_dry_run && RCLONE_OPTS+=("--dry-run")

if [ "${#RCLONE_OPTS[@]}" -gt 0 ]; then
	rclone_log_options="with ${RCLONE_OPTS[*]} options"
else
	rclone_log_options="without any option"
fi

log "rclone will be launched $rclone_log_options"

[ -f "$TMP_BACKUP_LIST" ] || fail "'$TMP_BACKUP_LIST' file not found"

parse_backup_list

if [ "$SHUTDOWN" = "yes" ]; then
	log "Finished - shutting down..."
	is_dry_run || sudo shutdown --poweroff now
fi

