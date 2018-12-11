#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Change the owner of send files to secret key on offsite servers.

Vin (Tony) Presciutti, Brandon Doyle. 12/10/2018.

Type-checked with Mypy v0.641.
"""

import os
import re
import sys

from subprocess import Popen, PIPE


if sys.version_info.major >= 3 and sys.version_info.minor >= 5:
    from typing import Any

subDirectory = '/datto/array1/.recv/'

newlines    = re.compile(r'\n+')
affirmative = re.compile(r'^[Yy]')
devID       = re.compile(r'(?<=-)[0-9]{4,6}(?=-)')


class Color:
    """
    `xterm` colors for coloring fonts written to stdout.
    """
    def __init__(self, color, string =''):
        # type: (str, str) -> None
        self.color = color    # type: str
        self.string = string  # type: str

    ## Colors

    @classmethod
    def red(cls):
        # type: () -> Color
        return cls('\033[31;1m')

    @classmethod
    def blue(cls):
        # type: () -> Color
        return cls('\033[34m')

    @classmethod
    def yellow(cls):
        # type: () -> Color
        return cls('\033[33m')

    @classmethod
    def green(cls):
        # type: () -> Color
        return cls('\033[32m')

    @classmethod
    def normal(cls):
        # type: () -> Color
        return cls('\033[0m')

    ## Effects

    @classmethod
    def bold(cls):
        # type: () -> Color
        return cls('\033[1m')

    def __enter__(self):
        # type: () -> None
        print(self.color + self.string, end='', sep='')

    def __exit__(self, *args):
        # type: (Any) -> Any
        print('\033[0m', end='', sep='')


def getFile():
    # type: () -> str
    """
    Get a valid file in /datto/array1/.recv/ from a user.
    """
    while True:
        with Color.blue():
            # Get the file name.
            print('Enter a file in {}: '.format(subDirectory), end='')
            with Color.normal():
                rootfile = input()

            # Verify it's accurate.
            if not os.path.isfile(subDirectory + rootfile):
                with Color.red(), Color.bold():
                    print('** Error: please enter a valid file in \'{}\'. '
                          'Received \'{}\''.format(subDirectory, rootfile))
                    continue
            if rootfile not in os.listdir(subDirectory):
                with Color.red(), Color.bold():
                    print('** ERROR: please enter a valid filename in \'{}\'. '
                          'Received \'{}\''.format(subDirectory, rootfile))
                    continue
            else:
                return rootfile


def getIO(command):
    # type: (str) -> Any
    """
    Get results from terminal commands as lists of lines of text.
    """
    with Popen(command, shell=True, stdout=PIPE, stderr=PIPE) as proc:
        stdout, stderr = proc.communicate()

    if stderr:
        raise ValueError('Command exited with errors: {}'.format(stderr))

    if stdout:
        stdout = re.split(newlines, stdout.decode())

        # For some reason, `shell=True` likes to yield an empty string.
        if stdout[-1] == '':
            stdout = stdout[:-1]

    return stdout


def chownSecretKey(rootfile):
    # type: (str) -> None
    """
    Change ownership to the SecretKey user.
    """

    # Get the devID from the file name that we're changing ownership of.
    rootDevID = re.findall(devID, rootfile)[0]

    # Now find the secretKey user from /etc/passwd with the devID.
    try:
        rootSecretKey = getIO(
            'awk -F "[:/]" \'{ if ($0 ~ /' + rootDevID + '/) { print $1; } }\' '
            '/etc/passwd'
        )[0]
    except IndexError:
        with Color.red():
            print('** ERROR: user with devID {} does not exist in /etc/passwd,'
                  ' exiting'.format(rootDevID))
            return

    while True:
        with Color.blue():
            print('This will change the ownership of \'{}\' to \'{}\'.'
                  ' Confirm? [Yy]: '.format(subDirectory + rootfile, 
                                            rootSecretKey), end='')

        chownConfirm = input()

        if re.match(affirmative, chownConfirm):
            break
        else:
            with Color.red(), Color.bold():
                print('** Exiting.')
            return

    # Chown the file to owner `rootSecretKey`.
    getIO('chown {} {}'.format(rootSecretKey + ':www-data', subDirectory + rootfile))

    # Success!
    with Color.green():
        print('\n\t** Success.\n')

    # Print the file so the user can confirm.
    print(getIO('ls -lash ' + subDirectory + rootfile)[0])


def main():
    # type: () -> None
    """
    Change owner.
    """
    rootFileName = getFile()      # type: str
    chownSecretKey(rootFileName)  # type: None


if __name__ == '__main__':
    main()
