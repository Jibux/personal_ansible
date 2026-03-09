#!/bin/bash


ROOT_PATH="$(dirname "$(realpath "$0")")"

"$ROOT_PATH/backup.sh" -vF "$ROOT_PATH/restore_from_nas_family/"

