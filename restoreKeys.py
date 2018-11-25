#! /usr/bin/env python3.5
# -*- coding: utf-8 -*-

r"""
    Restore keys from /home/configBackup/.zfs/snapshot/* to allow a user to
    remove data themselves.

    Works by building a reverse-list - present available agents from those keys
    listed at the aforementioned location.
"""

from typing import List, Any, Type
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from subprocess import Popen, PIPE
from collections.abc import Iterator
from contextlib import AbstractContextManager
from abc import ABCMeta

import re

configBackupSnaps = '/home/configBackup/.zfs/snapshot/'

newlines = re.compile(r'\n+')


class Levenshtein(AbstractContextManager):
    """
    Compute the Levenshtein distance between two strings - we will be presenting
    the keys in order of similarity.
    """
    def __init__(self, s1: str, s2: str) -> None:
        self.s1 = s1
        self.s2 = s2
        self._l1 = len(s1)
        self._l2 = len(s2)
        self._mat = self._constructMat(self._l1, self._l2)

    @staticmethod
    def _constructMat(dim1: int, dim2: int) -> List[List[int]]:
        """
        Get a list of lists of zeros for updating; requires O((n + 1) * (m + 1))
        space.
        """
        mat = [[0] * dim2] * dim1

        for i in range(dim1 + 1):
            mat[i][0] = i

        for j in range(dim2 + 1):
            mat[0][j] = j

        return mat

    def dist(self) -> int:
        """
        Get the distance between the two strings.
        """

        if min(self._l1, self._l2) == 0:
            return max(self._l1, self._l2)

        # Examine each character, comparing to the other string on self._mat.
        for i, ch1 in enumerate(self.s1, start=1):
            for j, ch2 in enumerate(self.s2, start=1):
                cost = 1 if ch1 != ch2 else 0

                self._mat[i][j] = min(
                    self._mat[i - 1][j] + 1,
                    self._mat[i][j - 1] + 1,
                    self._mat[i - 1][j - 1] + cost,
                )

        distance = self._mat[self._l1][self._l2]

        return distance

    def __enter__(self) -> int:
        return self.dist()

    def __exit__(self, *args) -> None:
        pass


class getIO(AbstractContextManager):
    """
    Get results from terminal commands as lists of lines of text.
    """
    def __init__(self, command: str) -> None:
        self.command = command

    def __enter__(self) -> List[str]:
        with Popen(self.command, shell=True, stdout=PIPE, stderr=PIPE) as proc:
            _stdout, self.stderr = proc.communicate()

        if self.stderr:
            raise ValueError(
                'Command exited with errors: {}'.format(self.stderr)
            )

        if _stdout:
            self.stdout = re.split(newlines, _stdout.decode())

            # For some reason, `shell=True` likes to yield an empty string.
            if self.stdout[-1] == '':
                self.stdout = self.stdout[:-1]

        return self.stdout


class ProgressArrow(Iterator, AbstractContextManager):
    """
    Print a nice 'progress' arrow at the top of the screen.
    """
    _arrow = '{} -> '

    def __init__(self, labels: List[str]) -> None:
        self.labels = labels
        self.steps = len(labels)
        self.arrows = (self._arrow * self.steps).format(*self.labels)

    def __enter__(self) -> 'ProgressArrow':
        return self

    def __exit__(self, *args: Any) -> Any:
        pass

    def __str__(self) -> str:
        with self as instance:
            return instance.state

    def __iter__(self) -> 'ProgressArrow':
        return self

    def __next__(self) -> str:
        with self as instance:
            instance.state += 1
            if instance.state

    @property
    def state(self) -> int:
        """
        Define the arrow's current state.
        """
        self._state = 0

        return self._state

    @state.setter
    def state(self, state: int) -> None:
        """
        Set the current state.
        """
        if self.steps <= state or state < self.steps:
            raise IndexError()

    @state.getter
    def state(self) -> str:
        """
        Acquire/print the current state.
        """
        return self.arrows


class Color(AbstractContextManager):
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


def main() -> None:
    """
    Collect user input.
    """
    parser = ArgumentParser(
        description=__doc__,
        formatter_class=RawDescriptionHelpFormatter
    )

    parser.add_argument('-a', '--agent', action='append', type=str,
        help='Specify agent string to search for in configBackup.'
    )

    args = parser.parse_args()

    #


if __name__ == '__main__':
    main()