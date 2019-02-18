#! /bin/bash
# Get a "thicker" version of the thin .vimrc with indents; requires/installs
# git to acquire Vundle and install indentation guides.

apt update
apt install git -y

mkdir -p ~/.vim/bundle
mkdir ~/.vim/colors

git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim

wget -O "$HOME/.vimrc" "https://raw.githubusercontent.com/bjd2385/datto/master/.thickVimrc"
wget -O "$HOME/.vim/colors/badwolf.vim" "https://raw.githubusercontent.com/sjl/badwolf/master/colors/badwolf.vim"

vim +PluginInstall +qall
