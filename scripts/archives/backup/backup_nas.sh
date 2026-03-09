#!/bin/bash


ROOT_PATH="$(dirname "$(realpath "$0")")"

"$ROOT_PATH/backup.sh" -vFf "$ROOT_PATH/backup_nas_data/"
"$ROOT_PATH/backup.sh" -vFfc "$ROOT_PATH/backup_nas_pictures/"
"$ROOT_PATH/backup.sh" -vFfc "$ROOT_PATH/backup_nas_media/"

