#!/bin/bash


set -euo pipefail


fail()
{
	echo "ERROR: ${1:-Something wrong happened}"
	exit 1
}


setup_ansible_vault_password()
{
	local file_path="$HOME/.personal_ansible_vault_password"
	local vault_pass

	[ -f "$file_path" ] && echo "Vault password file already present" && return 0

	read -rs -p "Personal ansible vault password: " vault_pass ; echo
	echo "$vault_pass" > "$file_path"
	chmod 400 "$file_path"
	return 0
}


trap fail ERR

setup_ansible_vault_password

SCRIPT_ROOT_PATH="$(dirname "$(realpath "$0")")"
VENV_DIR="$SCRIPT_ROOT_PATH/.venv"

echo "SCRIPT_ROOT_PATH: $SCRIPT_ROOT_PATH"
echo "VENV_DIR: $VENV_DIR"

if ! command -v curl >/dev/null; then
	sudo apt update && sudo apt install curl
fi

if command -v brew >/dev/null; then
	brew update
elif [ ! -d /home/linuxbrew ]; then
	/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if command -v uv >/dev/null; then
	uv self update
else
	curl -LsSf https://astral.sh/uv/install.sh | sh
	export PATH=$PATH:$HOME/.local/bin
fi

if command -v ruff >/dev/null; then
	uv tool upgrade ruff
else
	uv tool install ruff
fi

if [ -d "$VENV_DIR" ]; then
	sudo rm -rf "$VENV_DIR"
fi

uv venv --directory "$SCRIPT_ROOT_PATH"
uv pip install -r "$SCRIPT_ROOT_PATH/requirements.txt"

(export bin_path=$HOME/.local/bin && curl -sfL https://direnv.net/install.sh | bash)
direnv allow "$SCRIPT_ROOT_PATH"

export PATH=$PATH:$HOME/.local/bin

ansible-galaxy install -r requirements.yml --force

