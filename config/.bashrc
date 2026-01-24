#
# ~/.bashrc
#

# shellcheck disable=SC1000-SC9999

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

# don't put duplicate lines or lines starting with space in the history.
# See bash(1) for more options
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=200000
HISTFILESIZE=200000
HISTTIMEFORMAT="%d/%m/%y %T "

# check the window size after each command and, if necessary,
# update the values of LINES and COLUMNS.
shopt -s checkwinsize

# If set, the pattern "**" used in a pathname expansion context will
# match all files and zero or more directories and subdirectories.
#shopt -s globstar

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set variable identifying the chroot you work in (used in the prompt below)
if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
	debian_chroot=$(cat /etc/debian_chroot)
fi

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
	xterm-*color) color_prompt=yes;;
	screen-*color) color_prompt=yes;;
	tmux-*color) color_prompt=yes;;
	rxvt*) color_prompt=yes;;
esac

# uncomment for a colored prompt, if the terminal has the capability; turned
# off by default to not distract the user: the focus in a terminal window
# should be on the output of commands, not on the prompt
# force_color_prompt=yes

if [ -n "$force_color_prompt" ]; then
	if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
		# We have color support; assume it's compliant with Ecma-48
		# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
		# a case would tend to support setf rather than setaf.)
		color_prompt=yes
	else
		color_prompt=
	fi
fi

######### ######## ######
# Color # # Text # # bg #
######### ######## ######
# Black		30		40
# Red		31		41
# Green		32		42
# Orange	33		43
# Blue		34		44
# Magenta	35		45
# Cyan		36		46
# White		37		47

###########
# Effects #
###########
# 01 Bold
# 04 Underline
# 05 Blinking
# 07 Highlight

# \u user
# \h hostname
# \w current directory
# \$ user status ($ or #).

# If this is an xterm set the title to user@host:dir
WINDOW_TITLE=""
case "$TERM" in
xterm*|rxvt*)
	WINDOW_TITLE="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]"
	;;
*)
	;;
esac


if [ -z "$PS_SYMBOL" ]; then
	if [ "$EUID" == "0" ] ; then
		PS_SYMBOL='#'
		COLOR_USER=${COLOR_USER:-'\[\033[01;31m\]'} # red
	else
		PS_SYMBOL='$'
		COLOR_USER=${COLOR_USER:-'\[\033[01;32m\]'} # green
	fi
fi

## Uncomment to disable git info
#POWERLINE_GIT=0

# Colors
COLOR_RESET='\[\033[m\]'
COLOR_CWD=${COLOR_CWD:-'\[\033[0;34m\]'} # blue
COLOR_GIT=${COLOR_GIT:-'\[\033[0;36m\]'} # cyan
COLOR_SUCCESS=${COLOR_SUCCESS:-'\[\033[0;32m\]'} # green
COLOR_FAILURE=${COLOR_FAILURE:-'\[\033[0;31m\]'} # red

# Symbols
SYMBOL_GIT_BRANCH=${SYMBOL_GIT_BRANCH:-⑂}
SYMBOL_GIT_MODIFIED=${SYMBOL_GIT_MODIFIED:-*}
SYMBOL_GIT_PUSH=${SYMBOL_GIT_PUSH:-↑}
SYMBOL_GIT_PULL=${SYMBOL_GIT_PULL:-↓}

__git_info()
{
	[[ $POWERLINE_GIT = 0 ]] && return # disabled
	hash git 2>/dev/null || return # git not found
	local git_eng="env LANG=C git"   # force git output in English to make our work easier

	# get current branch name
	local ref

	ref=$($git_eng symbolic-ref --short HEAD 2>/dev/null)

	if [[ -n "$ref" ]]; then
		# prepend branch symbol
		ref=$SYMBOL_GIT_BRANCH$ref
	else
		# get tag name or short unique hash
		ref=$($git_eng describe --tags --always 2>/dev/null)
	fi

	[[ -n "$ref" ]] || return  # not a git repo

	local marks

	# scan first two lines of output from `git status`
	while IFS= read -r line; do
	if [[ $line =~ ^## ]]; then # header line
		[[ $line =~ ahead\ ([0-9]+) ]] && marks+=" $SYMBOL_GIT_PUSH${BASH_REMATCH[1]}"
		[[ $line =~ behind\ ([0-9]+) ]] && marks+=" $SYMBOL_GIT_PULL${BASH_REMATCH[1]}"
	else # branch is modified if output contains more lines after the header line
		marks="$SYMBOL_GIT_MODIFIED$marks"
		break
	fi
	done < <($git_eng status --porcelain --branch 2>/dev/null)  # note the space between the two <

	# print the git branch segment without a trailing newline
	printf " %s" "$ref$marks"
}

ps1_color()
{
	# Check the exit code of the previous command and display different
	# colors in the prompt accordingly.
	if [ $? -eq 0 ]; then
		local symbol="$COLOR_SUCCESS\n$PS_SYMBOL $COLOR_RESET"
	else
		local symbol="$COLOR_FAILURE\n$PS_SYMBOL $COLOR_RESET"
	fi

	local cwd="$COLOR_CWD\w$COLOR_RESET"
	cwd='${debian_chroot:+($debian_chroot)}'"$COLOR_USER"'\u\[\033[01;34m\]@\[\033[01;33m\]\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]'

	local git
	# Bash by default expands the content of PS1 unless promptvars is disabled.
	# We must use another layer of reference to prevent expanding any user
	# provided strings, which would cause security issues.
	# POC: https://github.com/njhartwell/pw3nage
	# Related fix in git-bash: https://github.com/git/git/blob/9d77b0405ce6b471cb5ce3a904368fc25e55643d/contrib/completion/git-prompt.sh#L324
	if shopt -q promptvars; then
		__powerline_git_info="$(__git_info)"
		git="$COLOR_GIT\${__powerline_git_info}$COLOR_RESET"
	else
		# promptvars is disabled. Avoid creating unnecessary env var.
		git="$COLOR_GIT$(__git_info)$COLOR_RESET"
	fi

	local format_date
	format_date="\[\033[00;90m\]$(date '+%H:%M:%S')$COLOR_RESET"

	local kube_ps=""
	if [[ -f /usr/bin/kubectl && $(type -t kube_ps1) == function ]]; then
		kube_ps=' $(kube_ps1)'
	fi
	local venv_prompt=""
	if [ -n "${VIRTUAL_ENV_PROMPT:-}" ]; then
		venv_prompt="$VIRTUAL_ENV_PROMPT"
	fi
	PS1L="$format_date $cwd$git$kube_ps"
	PS1R="$venv_prompt"
	if [ -n "$PS1R" ]; then
		# Use compensate variable if PS1R has some formating like colors
		compensate=0
		PS1_FINAL=$(printf "%*s\r%s" "$((COLUMNS+compensate))" "$PS1R" "$PS1L")
	else
		PS1_FINAL="$PS1L"
	fi
	PS1="$WINDOW_TITLE$PS1_FINAL$symbol"
}


alias_color=''
if [ "$color_prompt" = yes ]; then

	PROMPT_COMMAND="ps1_color${PROMPT_COMMAND:+; $PROMPT_COMMAND}"

	if [ -x /usr/bin/dircolors ]; then
		if test -r ~/.dircolors; then
			eval "$(dircolors -b ~/.dircolors)"
		else
			eval "$(dircolors -b)"
		fi

		alias_color='--color=auto'

		alias dir='dir --color=auto'
		alias grep='grep --color=auto'
		alias fgrep='fgrep --color=auto'
		alias egrep='egrep --color=auto'
		alias diff='diff --color=auto'
	fi
else
	#PS1='\u@\h:\w\$ '
	PS1="$WINDOW_TITLE"'${debian_chroot:+($debian_chroot)}\u@\h:\w'"$PS_SYMBOL "
fi

ruff_fmt()
{
	if [ $# -ne 1 ]; then
		echo "Please specify path to format"
		return 1
	fi
	ruff check --fix "$1" && ruff format "$1"
}

unset color_prompt force_color_prompt

PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND;}history -a"

export LS_OPTIONS="$alias_color -h --group-directories-first"
alias ls='ls $LS_OPTIONS'
alias ll='ls $LS_OPTIONS -lA'
alias llrt='ls $LS_OPTIONS -lArt'
alias la='ls $LS_OPTIONS -A'
alias lla='ls $LS_OPTIONS -al'
alias l='ls $LS_OPTIONS -l'
alias lrt='ls $LS_OPTIONS -lrt'
alias sl='ls'

alias ..='cd ..'
alias cd..='cd ..'

# Some more alias to avoid making mistakes:
alias rm='rm -i'
alias cp='cp -i'
alias mv='mv -i'

# SSH alias
alias sshr='ssh -l root'
alias scpr='scp -o "User=root"'

# Add an "alert" alias for long running commands.  Use like so:
#   sleep 10; alert
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'

# Git
alias git_lasthash_copy='lasthash=$(git lasthash)'

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.

if [ -f ~/.bash_aliases ]; then
	. ~/.bash_aliases
fi

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
	if [ -f /usr/share/bash-completion/bash_completion ]; then
		. /usr/share/bash-completion/bash_completion
	elif [ -f /etc/bash_completion ]; then
		. /etc/bash_completion
	fi
fi

# Dfreeze/unfreeze when tipping Ctrl+s and Ctrl+q
stty -ixon
#bind 'Control-s: '

[ -n "$DISPLAY" ] && xset b off

PATH=$PATH:~/bin:~/.local/bin:$HOME/.cargo/bin

[ -f "$HOME/bin/ssh_agent_custom.sh" ] && "$HOME/bin/ssh_agent_custom.sh"
[[ -z "$SSH_AGENT_PID" && -f "$HOME/.tmp/ssh_vars" ]] && . "$HOME/.tmp/ssh_vars"

if [ "$EUID" != "0" ]; then
	umask 077
else
	umask 022
fi

[ -f "$HOME/.bashrc.ansible" ] && . "$HOME/.bashrc.ansible" || true
[ -f "$HOME/.bashrc.local" ] && . "$HOME/.bashrc.local" || true

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" || true  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion" || true  # This loads nvm bash_completion

command -v direnv > /dev/null && eval "$(direnv hook bash)" || true

if [ -e /home/linuxbrew/.linuxbrew/bin/brew ]; then
# BEGIN ANSIBLE MANAGED BLOCK: linuxbrew
eval $(/home/linuxbrew/.linuxbrew/bin/brew shellenv)
# END ANSIBLE MANAGED BLOCK: linuxbrew
fi

if command -v fzf > /dev/null; then
	eval "$(fzf --bash)"
	# bind Ctrl+f to execute __fzf_history__
	bind -m emacs-standard -x '"\C-f": __fzf_history__'
	bind -m vi-command -x '"\C-f": __fzf_history__'
	bind -m vi-insert -x '"\C-f": __fzf_history__'
	# revert ctrl+r to original bash behavior
	bind '"\C-r": reverse-search-history'

	export FZF_DEFAULT_OPTS="
	  --no-height
	  --walker-skip .git,.venv,node_modules,.cache,.ruff_cache
	  --select-1 --exit-0
	"

	export FZF_CTRL_T_OPTS="
	  --preview 'bat -n --color=always {}'
	  --bind page-up:preview-page-up,page-down:preview-page-down
	"

	export FZF_CTRL_R_OPTS="
	  --bind 'ctrl-y:execute-silent(echo -n {2..} | xclip -sel clip)+abort'
	  --color header:italic
	  --header 'Press CTRL-Y to copy command into clipboard'
	"

	export FZF_ALT_C_OPTS="
	  --preview 'tree -C {} | head -200'
	"
fi

