#!/bin/bash

progName=$0

function checkExistence {
	pathToTest=$1
	typeOf=$2

	if [ "$typeOf" -eq "0" ]
	then
		if [ ! -d "$pathToTest" ]
		then
			echo "$pathToTest is not a directory or doesn't exist"
			exit 2
		fi
	fi

	if [ "$typeOf" -eq "1" ]
	then
		if [ ! -f "$pathToTest" ]
		then
			echo "$pathToTest is not a valid file or doesn't exist"
			exit 2
		fi
	fi

	if [ "$typeOf" -eq "2" ]
	then
		if [ ! -e "$pathToTest" ]
		then
			echo "the path $pathToTest doesn't exist"
			exit 2
		fi
	fi
}

function helpBackup {
	echo "Coming soon..."
	exit 0
}

function usage {
	echo "Usage: $progName [-hvfcF] [-i include file] [-e [exclude file]] [backup folder]"
	echo "Try « $progName » --help, for more informations."
	exit 0
}

ROOT_PATH="$(dirname "$(realpath "$0")")"
logPath="$ROOT_PATH/logs"
backupLog="$logPath/backup.log"
errorLog="$logPath/error.log"

exclude=0
debug=0
conserveLastLog=0
ntfs=0
forceyes=0

includeFile="include.txt"
excludeFile="exclude.txt"

# Arguments testing
TEMP=$(getopt -n"$0" -o hvfcFi:e: -l help,verbose -- "$@")

if test $? != 0
then
	usage
fi

eval set -- "$TEMP"

while [ $# -gt 0 ]
do
	case "$1" in
		-h|--help) helpBackup;shift;;
		-v|--verbose) debug=1;shift;;
		-c) conserveLastLog=1;shift;;
		-f) forceyes=1;shift;;
		-F) exclude=1;shift;;
		-i) includeFile="$2"; shift 2;;
		-e) exclude=1;excludeFile="$2";shift 2;;
		--) shift;break;;
		*) exit 1;;
	esac
done


#echo "Remaining arguments:"
#for arg do echo '--> '"\`$arg'" ; done

# normaly, we got 2 arguments remaining
if test $# -ne 1
then
	usage
fi

backupFolder="$1"
backupParameters="$backupFolder""parameters"
checkExistence "$backupFolder" 0
checkExistence "$backupParameters" 1
prefixPathToSave=""

# import variables
# shellcheck disable=SC1090
source "$backupParameters"

includeFile="$backupFolder$includeFile"
excludeFile="$backupFolder$excludeFile"

if [ $debug -eq 1 ]
then
	# shellcheck disable=SC2154
	echo -e "path: $path"
	echo -e "backupFolder: $backupFolder"
	echo -e "includeFile: $includeFile"
	echo -e "excludeFile: $excludeFile\n\n"
fi

checkExistence "$path" 0
checkExistence "$includeFile" 1
checkExistence "$excludeFile" 1
mkdir -p "$logPath"
checkExistence "$logPath" 0

rsyncCommand=""
and=""
excludeParam=""
ntfsParam=""
syncParam="a"

if [ $exclude -eq 1 ]
then
	excludeParam=" --delete-excluded --exclude-from='$excludeFile'"
fi

if [ $ntfs -eq 1 ]
then
	ntfsParam=" --modify-window=1 --size-only"
	syncParam="rtD"
fi

echo "Will do:"

while read -r line
do
	pathToSave=$(echo "$line" | cut -d: -f1)
	pathToSave=$prefixPathToSave$pathToSave
	destinationPath=$(echo "$line" | cut -d: -f2)
	checkExistence "$pathToSave" 2
	cmd2=""
	if [ ! -d "$path$destinationPath" ]
	then
		cmd2="mkdir -p '$path$destinationPath' && "
	fi

	cmd=$cmd2"rsync -L$syncParam --progress --ignore-errors --delete$ntfsParam$excludeParam '$pathToSave' '$path$destinationPath'"
	echo "$cmd"
	rsyncCommand=$rsyncCommand$and$cmd
	rsyncCommand=$rsyncCommand" 2>>$errorLog 1>>$backupLog"
	and=" && "
done < "$includeFile"

if [ $debug -eq 1 ]
then
	echo -e "\n\n$rsyncCommand\n"
fi

if [ $forceyes -eq 0 ]
then
	echo "Continue? (y,n)"
	read -r response
else
	response="y"
fi

if [ "$response" != "y" ]
then
	echo "Abort"
	exit 0
fi


date=$(date)
msg="Backup begun --- $date ---\n"

if [ $conserveLastLog -eq 1 ]
then
	echo -e "$msg" >> "$backupLog"
	echo -e "$msg" >> "$errorLog"
else
	echo -e "$msg" > "$backupLog"
	echo -e "$msg" > "$errorLog"
fi

eval "$rsyncCommand"

date=$(date)
msg="\nBackup finished --- $date ---\n"
echo -e "$msg" >> "$backupLog"
echo -e "$msg" >> "$errorLog"

