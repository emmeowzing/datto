#! /usr/bin/env python3.5
# -*- coding: utf-8 -*-

"""
Simple script to present included volumes/mountpoints and space data in a nice
format.

Brandon Doyle. <bdoyle@datto.com>. Last updated: November 13, 2018.

Type checked with Mypy v0.641. Variable type annotations are not supported in
Python versions <3.6, so there are 2 cases in this script where I've favored
generality.
"""

from typing import List, Generator, Dict, Optional, Any, Iterable
from subprocess import Popen, PIPE
from contextlib import contextmanager

import re
import argparse
import os


newlines = re.compile(r'\n+')

agentMountpoint = '/home/agents/'
infoPath = lambda uuid, snap: agentMountpoint + uuid + '/.zfs/snapshot/' \
                                + snap + '/' + uuid + '.agentInfo'


class InvalidArrayFormat(SyntaxError):
    """
    Raised when the input "compressed" JSON format is invalid.
    """


class UnsupportedOSError(ValueError):
    """
    Raised when this script is ran on an unsupported OS.
    """


class InvalidAgentNumberError(ValueError):
    """
    Raised when there are no agents on the appliance.
    """


class ConvertJSON:
    """
    Parse/convert PHP serialized JSON to Python dictionaries.

    Pasting this code here for an all-in-one, so we don't have to install a
    library for this script to work.
    """

    # Match these 'tokens'
    integer = r'^i:[0-9]+;?'
    double  = r'^d:[0-9]+\.?([0-9]*)?;?' # type introduced in IBU >500?
    string  = r'^s:[0-9]+:\"[^\"]*\";?'
    array   = r'^a:[0-9]+:{'
    boolean = r'^b:[01];?'
    endArr  = r'^}'

    lexer = re.compile('({}|{}|{}|{}|{}|{})'.format(integer, double, string,
                                                 array, endArr, boolean))

    # `:' between parentheses will break unpacking if we just `.split(':')`
    colonStringSplit = re.compile(r'(?<=s):|:(?=")')

    def __init__(self, key: Optional[str] =None) -> None:
        """
        Optionally set self.key value. If `key` is set in `self.decode`,
        however, this value is overwritten.
        """
        self.key = key

    def decode(self, key: Optional[str] =None) -> Dict:
        """
        Map serialized JSON -> Dict.
        """
        if key:
            self.key = key
        else:
            if not self.key:
                raise ValueError(
                    'ERROR: `decode` expected key value, received {}'\
                        .format(type(key))
                )

        if not os.path.isfile(self.key):
            raise FileNotFoundError('File {} does not exist'.format(key))

        with open(self.key, 'r') as keykeyData:
            keyData = keykeyData.readline().rstrip()

        def nestLevel(currentList: Optional[List] =None) -> List:
            """
            Allow the traversal of all nested levels.
            """
            nonlocal keyData

            if currentList is None:
                currentList = []

            while keyData:
                # Can't wait till assignment expressions!
                result = re.search(self.lexer, keyData)

                if not result:
                    # Show what it's stuck on so we can debug it
                    raise InvalidArrayFormat(keyData)

                start, end = result.span()
                substring = keyData[:end]
                keyData = keyData[end:]

                if substring.endswith(';'):
                    substring = substring[:-1]

                # Parse. Everything comes in 2's
                if substring.startswith('a'):
                    currentList.append(nestLevel([]))
                elif substring.startswith('i'):
                    _, value = substring.split(':')
                    currentList.append(int(value))
                elif substring.startswith('d'):
                    _, value = substring.split(':')
                    currentList.append(float(value))
                elif substring.startswith('s'):
                    _, _, value = re.split(self.colonStringSplit, substring)
                    value = value[1:len(value) - 1]
                    currentList.append(value)
                elif substring.startswith('b'):
                    _, value = substring.split(':')
                    currentList.append(bool(value))
                elif substring.startswith('}'):
                    return currentList
            return currentList

        def convert(multiLevelArray: List) -> Dict:
            """
            Convert our multi-level list to a dictionary of dictionaries ...
            """
            length = len(multiLevelArray)
            currentDict = {}

            for i, j in zip(range(0, length - 1, 2), range(1, length, 2)):
                key, val = multiLevelArray[i], multiLevelArray[j]
                if type(val) is list:
                    currentDict[key] = convert(val)
                else:
                    currentDict[key] = val

            return currentDict

        return convert(nestLevel()[0])

    @staticmethod
    def find(nestedDicts: Dict, key: Any) -> Any:
        """
        Return the first occurrence of value associated with `key`. O(n) for `n`
        items in the flattened data.

        (Iterable b => b -> a) so we can map over partial applications.
        """

        def traverse(nested: Dict) -> Any:
            nonlocal key
            for ky, value in list(nested.items()):
                if ky == key:
                    return value
                if type(value) is dict:
                    res = traverse(value)
                    if res:
                        return res

        return traverse(nestedDicts)

    @staticmethod
    def findAll(nestedDicts: Dict, key: Any, rvrsLookup: bool =False) -> List:
        """
        Return all occurrences of values associated with `key`, if any. Again,
        O(n). If `rvrsLookup`, searches by value and returns the associated \
        keys. (Essentially a reverse lookup.)
        """
        occurrences = []

        def traverse(nested: Dict) -> None:
            nonlocal key, occurrences
            for ky, value in list(nested.items()):
                if rvrsLookup:
                    if value == key:
                        occurrences.append(ky)
                else:
                    if ky == key:
                        occurrences.append(value)
                if type(value) is dict:
                    traverse(value)

        traverse(nestedDicts)
        return occurrences

    def __enter__(self) -> Dict:
        return self.decode()

    def __exit__(self, *args) -> Any:
        pass


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
        stdout = re.split(newlines, stdout.decode())[:-1]

    yield stdout


def rmElements(it: Dict, els: List) -> Dict:
    """
    Filter one container by another.
    """
    retIt = {}
    for el in it:
        if el not in els:
            retIt = {**retIt, el : it[el]}
    return retIt


def windows(info: Dict) -> Dict[str, int]:
    """
    Parse *.agentInfo data and extract information about Windows' volumes.
    """
    irrelevantVolumes = ['BOOT', 'Recovery']
    volumes = info['Volumes']

    print(volumes)


def linux(info: Dict) -> Dict[str, int]:
    """
    Parse *.agentInfo data and extract information about mountpoints and disks.
    """
    irrelevantMounts = ['<swap>']
    mounts = rmElements(info['Volumes'], irrelevantMounts)

    print(mounts)


def uniq(data: Iterable) -> Iterable:
    """
    Apply `set` builtin to the data and return as the same type.

        [a] -> [a] (∃!)

    I doubt this is the best general solution, but if you subtype Iterable,

    https://github.com/python/cpython/blob/master/Lib/typing.py#L1197
    https://github.com/python/cpython/blob/master/Lib/_collections_abc.py#L243

    it should work on all follow-up types listed starting at

    https://github.com/python/cpython/blob/master/Lib/_collections_abc.py#L277

    Dictionaries are special though since the same hash can't map to two values.
    """
    tp = type(data)

    if tp is dict:
        data = data.items() # type: ignore

    return tp(set(data)) # type: ignore


def main() -> None:
    """
    Get user input. Set up process.
    """
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument('-a', '--agent', type=str,
        help='Run the script on a particular agent/UUID'
    )

    args = parser.parse_args()

    # Just some basic control-flow to get an agent that actually exists.
    with getIO('zfs list -Ho name | grep -oP "(?<=(agents\/))[^\s]+"') as agents:
        if not agents:
            raise InvalidAgentNumberError()
        else:
            if not args.agent:
                # List agents by UUID, ask the user for input.
                while True:
                    print(*agents, sep='\n', end='\n\n')
                    uuid = input('Please select an agent: ').lower()
                    if uuid in agents:
                        break
                    else:
                        print('\n** ERROR: Please make a valid selection\n')
            else:
                uuid = args.agent
                if uuid not in agents:
                    print('\n** ERROR: Please make a valid selection\n')

    # Now that we have the agent, let's go print the information we need.
    for snap in os.listdir(agentMountpoint + uuid + '/.zfs/snapshot/'):
        path = infoPath(uuid, snap)
        if os.path.isfile(path):
            with ConvertJSON(path) as info:
                if 'type' in info:
                    # Linux
                    linux(info)
                elif info['os'].lower().startswith('windows'):
                    # Windows (is there a better validation?)
                    windows(info)
                else:
                    # Mac OS, other ?
                    raise UnsupportedOSError('Received {}'.format(info['os']))



if __name__ == '__main__':
    main()
