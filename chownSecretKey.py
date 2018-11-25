#! /usr/bin/env python3.5
# -*- coding: utf-8 -*-

"""
Change the owner of root file to secret key.
"""

import os

subDirectory = '/datto/array1/.recv/'


class Color:
    """
    `xterm` colors for coloring fonts written to stdout.
    """
    def __init__(self, color: str, string: str ='') -> None:
        self.color = color
        self.string = string

    ## Colors

    @classmethod
    def red(cls: Type['Color']) -> 'Color':
        return cls('\033[31;1m')

    @classmethod
    def blue(cls: Type['Color']) -> 'Color':
        return cls('\033[34m')

    @classmethod
    def yellow(cls: Type['Color']) -> 'Color':
        return cls('\033[33m')

    ## Effects

    @classmethod
    def bold(cls: Type['Color']) -> 'Color':
        return cls('\033[1m')

    def __enter__(self) -> None:
        print(self.color + self.string, end='', sep='')

    def __exit__(self, *args: Any) -> Any:
        print('\033[0m', end='', sep='')


def getFile() -> str:
    """
    Determine if a file input by the user is valid or not.
    """
    while True:
        ...


def main() -> None:
    """
    Change owner.
    """


if __name__ == '__main__':
    main()