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
from contextlib import AbstractContextManager

import re

configBackupSnaps = '/home/configBackup/.zfs/snapshot/'

newlines = re.compile(r'\n+')


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


def main() -> None:
    """
    Collect user input.
    """



if __name__ == '__main__':
    main()