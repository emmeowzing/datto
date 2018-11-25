#! /bin/bash
# Get a slimmed-down version of my .vimrc for use on a Datto. Limited since we
# don't have git, and it's probably not a good idea to install it.

mkdir -p ~/.vim/colors

wget -O "$HOME/.vimrc" "https://raw.githubusercontent.com/bjd2385/Linux-Configuration-Files/master/datto/.vimrc"
wget -O "$HOME/.vim/colors/badwolf.vim" "https://raw.githubusercontent.com/sjl/badwolf/master/colors/badwolf.vim"
