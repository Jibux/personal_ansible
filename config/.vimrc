" All system-wide defaults are set in $VIMRUNTIME/archlinux.vim (usually just
" /usr/share/vim/vimfiles/archlinux.vim) and sourced by the call to :runtime
" you can find below.  If you wish to change any of those settings, you should
" do it in this file (/etc/vimrc), since archlinux.vim will be overwritten
" everytime an upgrade of the vim packages is performed.  It is recommended to
" make changes after sourcing archlinux.vim since it alters the value of the
" 'compatible' option.

" This line should not be removed as it ensures that various options are
" properly set to work with the Vim-related packages.
" runtime! archlinux.vim
" runtime! vimrc_example.vim

" If you prefer the old-style vim functionality, add 'runtime! vimrc_example.vim'
" Or better yet, read /usr/share/vim/vim72/vimrc_example.vim or the vim manual
" and configure vim to your own liking!

set nocompatible
set autoread
set title
"set t_Co=256 "set the 256 colors mode

" Silence
set visualbell
set t_vb=

" Before plugins are loaded
let g:ale_lint_on_text_changed = 0
let g:ale_lint_on_insert_leave = 1
let g:ale_linter_aliases = {'yml': ['yaml']}
let g:ale_linters = {'yml': ['yamllint']}

let g:instant_markdown_port = 1206
let g:instant_markdown_browser = "firefox --new-window"
" Start preview :InstantMarkdownPreview - stop with :InstantMarkdownStop.
let g:instant_markdown_autostart = 0

call plug#begin('~/.vim/plugged')

Plug 'ntpeters/vim-better-whitespace'
Plug 'glench/vim-jinja2-syntax'
" Use + and _
Plug 'terryma/vim-expand-region'
Plug 'dense-analysis/ale'
Plug 'scrooloose/nerdtree'
Plug 'hashivim/vim-terraform'
Plug 'dhruvasagar/vim-table-mode'
Plug 'vim-airline/vim-airline'
Plug 'vim-airline/vim-airline-themes'
" For installation, see https://github.com/suan/vim-instant-markdown. Use
" nodejs
Plug 'suan/vim-instant-markdown', {'for': 'markdown'}
Plug 'rust-lang/rust.vim'
Plug 'google/vim-jsonnet'
Plug 'tpope/vim-commentary'
Plug 'tpope/vim-fugitive'
Plug 'tpope/vim-rhubarb'
" makes sure that you have the latest binary
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'

" :PlugInstall to install plugins
" :PlugUpdate to update
" :PlugClean to remove unused
" :PlugUpgrade to upgrade vim-plug
call plug#end()

let g:airline_theme='solarized'
" let g:airline#extensions#tabline#enabled = 1
" let g:airline_powerline_fonts = 1

"colorscheme camo

" If using a dark background within the editing area and syntax highlighting
" turn on this option as well
"set background=dark

" Uncomment the following to have Vim jump to the last position when
" reopening a file
if has("autocmd")
	au BufReadPost * if line("'\"") > 1 && line("'\"") <= line("$") | exe "normal! g'\"" | endif
endif

" Uncomment the following to have Vim load indentation rules and plugins
" according to the detected filetype.
if has("autocmd")
	filetype plugin indent on
endif

syntax on

set backspace=indent,eol,start

"let loaded_minibufexplorer = 0

"let g:miniBufExplMapWindowNavVim = 1
"let g:miniBufExplMapWindowNavArrows = 1
"let g:miniBufExplMapCTabSwitchBufs = 1
"let g:miniBufExplModSelTarget = 1

" The following are commented out as they cause vim to behave a lot
" differently from regular Vi. They are highly recommended though.
"set showcmd		" Show (partial) command in status line.a

" Smart search
set showmatch		" Show matching brackets.
set ignorecase		" Do case insensitive matching
set smartcase		" Do smart case matching
set incsearch		" Incremental search
set hlsearch
highlight Search cterm=NONE ctermfg=Black ctermbg=yellow

"set autowrite		" Automatically save before commands like :next and :make
"set hidden         " Hide buffers when they are abandoned
set mouse=a		" Enable mouse usage (all modes)
set number
set shortmess=at
set wildignore=*.o,*.obj,*.bak,*.exe

set nostartofline
set sessionoptions+=buffers,curdir

" Permits split proportions conservation
set noequalalways

" Indent
set autoindent
set smartindent
set softtabstop=8
set tabstop=8
set shiftwidth=8
set noexpandtab

autocmd Filetype python setlocal expandtab tabstop=4 shiftwidth=4 softtabstop=4

au! BufNewFile,BufReadPost *.{yaml,yml} set filetype=yaml "foldmethod=indent
autocmd FileType yaml setlocal softtabstop=2 tabstop=2 shiftwidth=2 expandtab
autocmd FileType markdown setlocal softtabstop=2 tabstop=2 shiftwidth=2 expandtab
autocmd Filetype markdown TableModeToggle
autocmd FileType jsonnet setlocal softtabstop=2 tabstop=2 shiftwidth=2 expandtab
autocmd FileType json setlocal softtabstop=2 tabstop=2 shiftwidth=2 expandtab
autocmd FileType jinja setlocal softtabstop=2 tabstop=2 shiftwidth=2 expandtab

" In visual, keep the indented bloc
vnoremap < <gv
vnoremap > >gv
" Use TAB
nnoremap <TAB> >>
vmap <TAB> >
nnoremap <S-TAB> <<
vmap <S-TAB> <

set diffopt=filler,iwhite,vertical

" Turbo mode
set ttyfast
set showcmd
"set noswapfile
" Increase mapping reactivity (The time in milliseconds that is waited for a key code or mapped key sequence to complete)
set timeout timeoutlen=3000 ttimeoutlen=100

" Go to the next/last line if right/left arrows are pressed in end/beginning of line
set whichwrap=<,>,[,]

" vim-airline already handles statusline
"set laststatus=2
"set statusline= " clear
"set statusline+=%-3.3n\ " nombre buffer
"set statusline+=%f\ " nom fichier
"set statusline+=%h%m%r%w " flags
"set statusline+=[%{strlen(&ft)?&ft:'none'}, " file type
"set statusline+=%{strlen(&fenc)?&fenc:&enc}, " encoding
"set statusline+=%{&fileformat}] " file format
"set statusline+=%{FugitiveStatusline()} " git status
"set statusline+=%#warningmsg# " Syntastic
""set statusline+=%{SyntasticStatuslineFlag()}
"set statusline+=%*
"set statusline+=%= " right alignment
"set statusline+=%-14.(%l,%c%V%)\ %<%P " offset

set cursorline
hi CursorLine cterm=bold ctermbg=NONE ctermfg=NONE guibg=NONE guifg=NONE
hi CursorLineNr cterm=bold ctermbg=NONE ctermfg=red guibg=NONE guifg=NONE
"hi CursorColumn cterm=NONE ctermbg=NONE ctermfg=NONE guibg=NONE guifg=NONE

hi Visual cterm=inverse ctermfg=NONE ctermbg=NONE guibg=NONE guifg=NONE

hi Pmenu cterm=bold ctermbg=black ctermfg=red guibg=NONE guifg=NONE
hi PmenuSel cterm=NONE ctermbg=grey ctermfg=black guibg=NONE guifg=NONE
hi PmenuSbar cterm=NONE ctermbg=yellow ctermfg=NONE guibg=NONE guifg=NONE

" TEST1 TEST2 -> doesn't work
syntax keyword Todo contained TEST1 TEST2

hi Todo cterm=NONE ctermbg=white ctermfg=black guibg=NONE guifg=NONE
"hi def link MyTodo Todo
hi MyTodo cterm=NONE ctermbg=blue ctermfg=black guibg=NONE guifg=NONE

" Avoid screen problem for (Meta) Left and (Meta) right
"if $TERM =~ 'screen'
"	nmap [1;5D B
"	nmap [1;5C W
"	inoremap <Esc>[1;5C <C-O>W
"	inoremap <Esc>[1;5D <C-O>B
"endif

" Map ctrl+s for saving
noremap <C-s> :update<CR>
vnoremap <C-s> <C-C>:update<CR>
inoremap <C-s> <C-O>:update<CR>

" Map ctrl+l for next
noremap <C-l> :n<CR>
vnoremap <C-l> <C-C>:n<CR>
inoremap <C-l> <C-O>:n<CR>

" Map ctrl+k for prev
noremap <C-k> :N<CR>
vnoremap <C-k> <C-C>:N<CR>
inoremap <C-k> <C-O>:N<CR>

" Map ctrl+q to quit all files
noremap <C-q> :qa<CR>
vnoremap <C-q> <C-C>:qa<CR>
inoremap <C-q> <C-O>:qa<CR>

" Map ctrl+? to quit current file
"noremap <C-?> :q<CR>

" Shortcut to save/restore sessions
nnoremap <F5> :mksession! ~/.vim/sessions/
nnoremap <F6> :so ~/.vim/sessions/

set pastetoggle=<F1>
"set clipboard=unnamedplus


" Copy/cut/past in visual mode using clipboard
vnoremap <C-c> "+y
vnoremap <C-x> "+d
inoremap <C-v> <C-c>"+pa
vnoremap <C-v> <C-c>"+p


" Tabs
" ctrl+page-up or ctrl+page-down
noremap [6^ :tabnext<CR>
noremap [5^ :tabprevious<CR>
noremap <C-t> :tabnew<CR>

" Launch fzf file selector
noremap <C-p> :FZF<CR>


" Source a global configuration file if available
if filereadable("/etc/vim/vimrc.local")
	source /etc/vim/vimrc.local
endif

" Syntastic
let g:syntastic_enable_signs=1
let g:syntastic_auto_loc_list=1


" Folding {{{
if has ('folding')
	set foldenable
	set foldmethod=marker
	set foldmarker={{{,}}}
	set foldcolumn=1
endif

" Automatically load and save the folds
" Edit: removed that because it saves other settings
"autocmd BufWinLeave * if expand("%") != "" | mkview | endif
"autocmd BufWinEnter * if expand("%") != "" | loadview | endif

" Fold Toggle
inoremap <F2> <C-O>za
nnoremap <F2> za
onoremap <F2> <C-C>za
vnoremap <F2> zf

hi FoldColumn cterm=NONE ctermbg=black ctermfg=green guibg=NONE guifg=NONE
hi Folded cterm=NONE ctermbg=black ctermfg=green guibg=NONE guifg=NONE

" Toggle foldcolumn with foldenable
function Foldtoggle()
	if &foldenable
		set nofoldenable
		set foldcolumn=0
	else
		set foldenable
		set foldcolumn=1
	endif
endfunction
" }}}

" Number and foldcolumn on/off
function CopyModeToggle()
	set nonumber!
	call Foldtoggle()
endfunction

noremap	<F3> :call CopyModeToggle() <CR>
nnoremap <C-LeftMouse> :call CopyModeToggle()<CR>

" NERDTree
noremap <F7> :NERDTreeToggle <CR>

syntax keyword SpellBad ERROR

autocmd BufNewFile,BufRead *.vue set syntax=html
autocmd BufNewFile,BufRead *.ts set syntax=javascript

let g:ctrlp_custom_ignore = {
	\ 'dir':  '\v[\/]\.(git|hg|svn)$',
	\ 'file': '\v\.(exe|so|dll|flac|mp3|m4a|jpg|jpeg|png|gif)$',
	\ 'link': 'some_bad_symbolic_links',
\}

" Color column
set colorcolumn=81
"call matchadd('ColorColumn', '\%81v', 100) "set column nr

" https://github.com/altercation/solarized/tree/master/vim-colors-solarized
"set t_Co=16
set background=dark " dark | light "
" When using a terminal without solarized theme
" let g:solarized_termcolors=256
colorscheme solarized


" Set transparent background to make it same color as terminal
hi Normal ctermbg=NONE

" Spell
if has("spell")
	if !filewritable($HOME."/.vim/spell")
		call mkdir($HOME."/.vim/spell", "p")
	endif
	set spellsuggest=10 "10 suggestions
	" We set the keys to manually activate the syntax's correction
	noremap <F10> :setlocal spell spelllang=fr <CR>
	noremap <F11> :setlocal spell spelllang=en <CR>
	noremap <F9> :setlocal nospell <CR>
	noremap [29~ z=
	hi clear SpellBad
	hi SpellBad cterm=underline ctermbg=NONE ctermfg=NONE guibg=NONE guifg=NONE
	hi SpellCap cterm=inverse,bold ctermbg=NONE ctermfg=NONE guibg=NONE guifg=NONE
endif

