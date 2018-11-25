#! /usr/bin/env python3.5
# -*- coding: utf-8 -*-

r"""
    Restore keys from /home/configBackup/.zfs/snapshot/* to allow a user to
    remove data themselves.

    Works by building a reverse-list - present available agents from those keys
    listed at the aforementioned location.
"""

from typing import Generator, List
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from contextlib import contextmanager

configBackupSnaps = '/home/configBackup/.zfs/snapshot/'


@contextmanager
def getIO(command: str) -> Generator[List[str], None, None]:
    """
    Get results from terminal commands as lists of lines of text.
    """
    with Popen(command, shell=True, stdout=PIPE, stderr=PIPE) as proc:
        stdout, stderr = proc.communicate()

    if stderr:
        raise ValueError('Command exited with errors: {}'.format(stderr))

    if stdout:
        # For some reason, `shell=True` likes to yield an empty string.
        print(stdout)
        stdout = re.split(newlines, stdout.decode())[:-1]

    yield stdout


class StepArrow:
    """
    Print a nice 'progress' arrow at the top of the screen.
    """
    _arrow = '{} -> '

    def __init__(self, labels: List[str]) -> None:
        self.labels = labels
        self.steps = steps
        self.arrows = (_arrow * self.steps).format(*self.labels)

    def __str__(self) -> str:
        # FIXME
        ...

    @property
    def state(self) -> int:
        self._state =


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

    # Compare requested agents against valid agents, as I've done in my
    # basicVolumeInfo script.
    with getIO('zfs list -Ho name | grep -oP "(?<=(agents\/))[^\s]+"') as agents:
        if not agents:
            raise InvalidAgentNumberError('No agents found: {}'.format(agents))
        else:
            if not args.agent:
                # List agents by UUID, ask the user for input.
                while True:
                    print(*agents, sep='\n', end='\n\n')
                    uuid = input('Agent: ')
                    if uuid in agents:
                        break
                    else:
                        print('\n** ERROR: Please make a valid selection, '
                              'received {}\n'.format(uuid))
                allSnaps = getInfo([uuid])
                uuids = [uuid]
            else:
                for id in args.agent:
                    if id not in agents:
                        print('\n** ERROR: Please make a valid selection\n')
                        break
                allSnaps = getInfo(list(args.agent))
                uuids = list(args.agent)


if __name__ == '__main__':
    main()