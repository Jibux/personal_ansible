#!/bin/bash


ROOT_PATH="$(dirname "$(realpath "$0")")"

"$ROOT_PATH/backup.sh" -vfFc "$ROOT_PATH/backup_nas_family/"
"$ROOT_PATH/backup.sh" -vfFc "$ROOT_PATH/backup_nas_agathe/"

