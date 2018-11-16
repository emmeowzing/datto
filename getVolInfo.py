#! /usr/bin/env python3.5
# -*- coding: utf-8 -*-

r"""
    Simple script to present included volumes/mountpoints and space data in a
    nice format.

    Type checked with Mypy v0.641. Variable type annotations are not supported
    in Python versions <3.6, so there's 1 case in this script where I've
    favored generality and ignored type.

        $ mypy --strict getVol.py

    Brandon Doyle <bdoyle@datto.com>.

    Last updated: November 16, 2018.
"""

from typing import (List, Generator, Dict, Optional, Any, Iterable,
                    Callable as Function)
from subprocess import Popen, PIPE
from contextlib import contextmanager
from functools import wraps

import re
import argparse
import os


newlines = re.compile(r'\n+')

agentMountpoint = '/home/agents/'


def infoPath(uuid: str, snap: str) -> str:
    return agentMountpoint + uuid + '/.zfs/snapshot/' + snap + '/' + uuid \
           + '.agentInfo'


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
    double  = r'^d:[0-9]+\.?([0-9]*)?;?'  # type introduced in IBU >500 *Info's?
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
            # Overwrite.
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
        O(n). If `rvrsLookup`, searches by value and returns the associated
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

    def __exit__(self, *args: Any) -> Any:
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


def rmElements(it: Dict, els: List, rev: bool =False) -> Dict:
    """
    Filter one container by another. If `rev` is set to True, then the logic is
    reversed.
    """
    retIt = {}  # type: Dict

    if rev:
        for el in it:
            if el in els:
                retIt = {**retIt, el: it[el]}
    else:
        for el in it:
            if el not in els:
                retIt = {**retIt, el: it[el]}

    return retIt


def rmElementsDec(els: List, rev: bool =False, level: int =0) -> Function:
    """
    Apply `rmElements` to a function, the first argument being its return value.

    Level applies to depth at which to apply the filter. Could be generalized
    for true depth-independent/flattened filtering, without losing structure.
    """
    def _decor(fn: Function[..., Dict[str, int]]) -> Function[[Dict], Dict[str, int]]:
        @wraps(fn)
        def _fn(arg: Dict) -> Dict[str, int]:
            res = fn(arg)

            def traverse(subDict: Dict, currentDepth: int =0) -> Optional[Dict]:
                """
                Traverse nested dictionaries to the necessary level before
                filtering by `els`. Had an issue typing this, but apparently
                """
                if currentDepth == level:
                    if level == 0:
                        # Cover base-case filtering.
                        nonlocal res
                        res = rmElements(subDict, els=els, rev=rev)
                        # PEP 8 :/
                        return None
                    else:
                        return rmElements(subDict, els=els, rev=rev)
                else:
                    for key in subDict.keys():
                        if isinstance(subDict[key], dict):
                             subDict[key] = \
                                 traverse(subDict[key], currentDepth + 1)
                    else:
                        return None

            traverse(res)

            return res
        return _fn
    return _decor


@rmElementsDec(['capacity', 'used'], rev=True, level=1)
@rmElementsDec(['BOOT', 'Recovery'], level=0)
def windows(info: Dict) -> Dict[str, Dict[str, int]]:
    """
    Extract information about Windows' volumes.
    """
    volumes = info['Volumes']

    # As an annoying aside, it appears *Info keys associated with Windows use a
    # string type for `capacity` data and integers for `used`, whereas in Linux
    # *Info keys, integer type is used for both. :/
    for volume in volumes:
        volumes[volume]['capacity'] = int(volumes[volume]['capacity'])

    return volumes


@rmElementsDec(['capacity', 'used'], rev=True, level=1)
@rmElementsDec(['<swap>'], level=0)
def linux(info: Dict) -> Dict[str, Dict[str, int]]:
    """
    Extract information about mountpoints and disks.
    """
    mounts = info['Volumes']

    return mounts


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
    They're already unique, but support them anyway.

    Perhaps this type issue can be cleared up with a  type variable?
    """
    tp = type(data)

    if tp is dict:
        return data

    return tp(set(data))  # type: ignore


def getInfo(uuid: List[str]) -> List[List[Dict[str, Dict[str, int]]]]:
    """
    Collect information and print it to the terminal.
    """
    # Now that we have the agent, let's go print the information we need.
    allSnaps = []

    for id in uuid:
        snaps = []
        for snap in os.listdir(agentMountpoint + id + '/.zfs/snapshot/'):
            path = infoPath(id, snap)
            if os.path.isfile(path):
                with ConvertJSON(path) as info:
                    if 'type' in info:
                        # Linux (info[type] => 'linux')
                        snaps.append(linux(info))
                    elif info['os'].lower().startswith('windows'):
                        # Windows (is there a better validation?)
                        snaps.append(windows(info))
                    else:
                        # Mac OS, other ?
                        raise UnsupportedOSError(
                            'Received {}'.format(info['os'])
                        )
        allSnaps.append(snaps)

        print(snaps)

    return allSnaps


class PresentNiceColumns:
    """
    Present
    """
    def __init__(self, allSnaps: List[List[Dict[str, Dict[str, int]]]],
                       binary: bool =True) -> None:
        self.allSnaps = allSnaps
        self.binary = binary

    def render(self) -> None:
        """
        Additively build each line of output. This is generated every time
        instead of storing the result in memory.
        """
        for agent in self.allSnaps:
            for snap in agent:
                for volume in snap:
                    used = snap[volume]['used']
                    capacity = snap[volume]['capacity']
                    print(volume, self.scale(used, self.binary),
                          self.scale(capacity, self.binary), end='  ', sep=' ')
                else:
                    print()
        return None

    @staticmethod
    def scale(bts: int, binary: bool =True) -> str:
        """
        Format volume used/capacity values to the correct binary or metric
        magnitude (and hence prefix).
        """
        if bts < 0:
            raise ValueError('Expected value >=0, received {}'.format(bts))

        fixes = ['K', 'M', 'G', 'T', 'P', 'E', 'Z']

        if binary:
            fixes = [fix + 'i' for fix in fixes]
        else:
            fixes = [fix + 'B' for fix in fixes]

        value = ''

        for magnitude, prefix in zip(range(len(fixes)), fixes):
            print('{0:.2f} {1}'.format(bts / 2 ** magnitude, prefix))
            if 2 ** magnitude <= bts < 2 ** (magnitude + 1):
                value = '{0:.2f} {1}'.format(bts / 2 ** magnitude, prefix)
                break

        return value


def main() -> None:
    """
    Get user input. Set up process.
    """
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-a', '--agent', type=str, action='append',
        help='Run the script on particular agent(s)/UUID(s)'
    )

    parser.add_argument('-m', '--metric', type=bool, default='store_true',
        help='Present the columns in base-10 (HD/metric) magnitude rather '
             'than the default binary output.'
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
                allSnaps = getInfo([uuid])
            else:
                for id in args.agent:
                    if id not in agents:
                        print('\n** ERROR: Please make a valid selection\n')
                        break
                allSnaps = getInfo(list(args.agent))

    PresentNiceColumns(allSnaps).render()


if __name__ == '__main__':
    main()
