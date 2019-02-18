#! /bin/bash
# Get a slimmed-down version of my .vimrc for use on a Datto. Limited since we
# don't have git, and it's probably not a good idea to install it.

apt update
apt install git -y

mkdir -p ~/.vim/bundle
mkdir ~/.vim/colors

git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/Vundle.vim

wget -O "$HOME/.vimrc" "https://raw.githubusercontent.com/bjd2385/datto/master/.thickVimrc"
wget -O "$HOME/.vim/colors/badwolf.vim" "https://raw.githubusercontent.com/sjl/badwolf/master/colors/badwolf.vim"

vim +PluginInstall +qall
