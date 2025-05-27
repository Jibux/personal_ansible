#!/bin/bash


# Clean local git branches which have no remote references

set -o errexit -o nounset


keeping_branch()
{
	echo "Keeping branch '$branch'"
}

handle_delete_error()
{
	local branch=$1
	local force=$2

	if [ "$force" == "no" ]; then
		ask_delete_branch "$branch" "yes"
	else
		keeping_branch "$branch"
	fi
}

ask_delete_branch()
{
	local branch=$1
	local force="${2:-no}"
	local git_opt="-d"
	local force_string=""
	local resp

	if [ "$force" == "yes" ]; then
		git_opt="-D"
		force_string=" (force)"
	fi

	read -r -n1 -p "Delete local branch '$branch'$force_string? (y/N) " resp
	echo

	if [ "$resp" == "y" ]; then
		if git branch $git_opt "$branch"; then
			echo "Local branch '$branch' deleted"
		else
			handle_delete_error "$branch" "$force"
		fi
	else
		keeping_branch "$branch"
	fi
}

process_branch()
{
	local branch=$1

	echo -n "Check remote reference of branch '$branch': "

	if git branch -r | grep -q -E "origin/$branch$"; then
		echo "PRESENT"
	else
		echo "ABSENT"
		ask_delete_branch "$branch"
	fi
}

git sw "$(git defbr)"
git pull

while IFS= read -u 3 -r br; do
	process_branch "$br"
done 3< <(git branch | awk '{print $NF}')

