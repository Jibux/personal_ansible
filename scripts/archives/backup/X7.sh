#!/bin/bash


ROOT_PATH="$(dirname "$(realpath "$0")")"

"$ROOT_PATH/backup.sh" -vfc "$ROOT_PATH/X7/"

