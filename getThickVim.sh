#! /bin/bash
# Get a slimmed-down version of my .vimrc for use on a Datto. Limited since we
# don't have git, and it's probably not a good idea to install it.

mkdir -p ~/.vim/bundle
mkdir -p ~/.vim/colors

git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim

wget -O "$HOME/.vimrc" "https://raw.githubusercontent.com/bjd2385/Linux-Configuration-Files/master/datto/.thickVimrc"
wget -O "$HOME/.vim/colors/badwolf.vim" "https://raw.githubusercontent.com/sjl/badwolf/master/colors/badwolf.vim"
