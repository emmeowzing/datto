" Slimmed down .vimrc
" Brandon Doyle
" September 8, 2018

filetype plugin indent on
syntax enable

set nocompatible
set tabstop=4       " set tabs to 4 spaces
set softtabstop=4   " number of spaces in tab when editing
set shiftwidth=4    " reindent ops
set expandtab       " convert tabs to spaces
set smarttab
set number          " line numbering
set showcmd         " show last command in bottom-right

set cursorline      " underline the line your cursor is on, so it's
                    " easier to go back after flipping between windows

set showmatch       " highlight matching [{()}]

set incsearch
set hlsearch        " search as you're typing

set colorcolumn=80  " vertical line for Python

set t_Co=256        " Allow 256 colors; without only supports 8

set backspace=indent,eol,start
set laststatus=2
set linebreak       " break at the word level instead of the character

" Remap keys
noremap ; l
noremap l k
noremap k j
noremap j h

colorscheme badwolf
