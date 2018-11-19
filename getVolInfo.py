#! /usr/bin/env python3.5
# -*- coding: utf-8 -*-

r"""
    Simple script to present included volumes/mountpoints and space data in a
    nice format.

    Possible to use/pipe output from this script as well; e.g.,

        $ ./getVolInfo.py --agent <some_agent> | grep -P "[^\s]+(?=-)"

    will highlight volumes.

    Type checked with Mypy v0.641. Variable type annotations are not supported
    in Python versions <3.6, so there's 1 case in this script where I've
    favored generality and ignored type.

        $ mypy --strict getVol.py

    Brandon Doyle <bdoyle@datto.com>.

    Last updated: November 19, 2018.
"""


from typing import (List, Generator, Dict, Optional, Any, Iterable,
                    Callable as Function, Type)
from subprocess import Popen, PIPE
from contextlib import contextmanager
from functools import wraps
from collections import OrderedDict
from datetime import datetime

import re
import argparse
import os


newlines = re.compile(r'\n+')

agentMountpoint = '/home/agents/'


def infoPath(uuid: str, snap: str) -> str:
    return agentMountpoint + uuid + '/.zfs/snapshot/' + snap + '/' + uuid \
           + '.agentInfo'


def time(epoch: int) -> str:
    """
    Convert Linux epoch time to a UTC string.
    """
    return datetime.utcfromtimestamp(epoch).strftime('%Y-%m-%d %H:%M')


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
                filtering by `els`.
                """
                if currentDepth == level:
                    if level == 0:
                        # Cover base-case filtering.
                        nonlocal res
                        res = rmElements(subDict, els=els, rev=rev)
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


# Filter volume info and select/reject those entries we don't need.

@rmElementsDec(['capacity', 'used'], rev=True, level=1)
@rmElementsDec(['BOOT', 'Recovery'], level=0)
def windows(info: Dict) -> Dict[str, Dict[str, int]]:
    """
    Extract information about Windows' volumes.
    """
    volumes = info['Volumes']  # type: Dict[str, Dict[str, int]]

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
    mounts = info['Volumes']  # type: Dict[str, Dict[str, int]]

    return mounts


def getInfo(uuid: List[str]) -> List[List[Dict[str, Dict[str, int]]]]:
    """
    Collect information about a UUID/agent and print it to the terminal.
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

    return allSnaps


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


class Color:
    """
    `xterm` colors for coloring fonts written to stdout.
    """
    def __init__(self, color: str) -> None:
        self.color = color

    @classmethod
    def red(cls: Type['Color']) -> 'Color':
        return cls('\033[31;1m')

    @classmethod
    def blue(cls: Type['Color']) -> 'Color':
        return cls('\033[34m')

    def __enter__(self) -> None:
        print(self.color, end='', sep='')

    def __exit__(self, *args: Any) -> Any:
        print('\033[0m', end='', sep='')


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


class PresentNiceColumns:
    """
    Present the information in straight columns; this is probably my least
    favorite part of this script :/ So ugly.
    """
    def __init__(self, allSnaps: List[List[Dict[str, Dict[str, int]]]],
                       binary: bool =True, noscale: bool =False,
                       smart: bool =False) -> None:
        self.allSnaps = allSnaps
        self.binary = binary
        self.fixes = ['B'] + [fix + ('i' if self.binary else 'B')
                      for fix in ['K', 'M', 'G', 'T', 'P', 'E', 'Z']]
        self.noscale = noscale
        self.smart = smart

    def render(self) -> None:
        """
        Print these agents' snapshots in nice visual columns.
        """
        for agent in self.allSnaps:
            # Type safe conversion/storage of the former dictionary.
            _agent = []  # type: List[Dict[str, Dict[str, str]]]

            # Get column widths for this agent prior to presentation.
            nCols = 4 * len(agent[0])
            colWidths = [0] * nCols

            for snap in agent:
                # Type checks because OrderedDict <: Dict.
                _snap = OrderedDict()  # type: Dict[str, Dict[str, str]]
                for volume in snap:
                    _used = snap[volume]['used']
                    _capacity = snap[volume]['capacity']
                    if self.noscale:
                        used = str(_used)
                        capacity = str(_capacity)
                    else:
                        used = self.scale(_used)
                        capacity = self.scale(_capacity)

                    # Build new ordered entry. Python 3.5's dictionaries don't
                    # maintain their order, so we must explicitly create an
                    # ordered dictionary for the convenience. (Uses an internal
                    # doubly-linked list data structure).
                    vol = volume + '-'
                    _snap[vol] = OrderedDict()
                    _snap[vol]['used'] = str(used)
                    _snap[vol]['capacity'] = str(capacity)
                    _snap[vol]['percent'] \
                        = '{0:.1f}%'.format(100 * _used / _capacity)

                _agent.append(_snap)

            for _snap in _agent:
                snapshot = self._flatten(_snap)
                for i, column in enumerate(snapshot):
                    width = len(column)
                    if colWidths[i] < width:
                        colWidths[i] = width

            # Now print these columns with proper widths to the terminal.
            for _snap in _agent:
                snapshot = self._flatten(_snap)
                for i, column in enumerate(snapshot):
                    if i % 4 == 0 and i != 0:
                        print(' ', end='')
                    if i % 4 == 0:
                        with Color.red():
                            print(self._extend(column, colWidths[i]), end=' ')
                    else:
                        print(self._extend(column, colWidths[i]), end=' ')
                else:
                    print()

    def scale(self, bts: int) -> str:
        """
        Format volume used/capacity values to the correct binary or metric
        magnitude (and hence prefix).
        """
        if bts < 0:
            raise ValueError('Expected value >=0, received {}'.format(bts))

        if self.binary:
            if bts == 0:
                return '0.00 Ki'

            for magnitude, prefix in zip(range(len(self.fixes)), self.fixes):
                if 2 ** (10 * magnitude) <= bts < 2 ** (10 * (magnitude + 1)):
                    bts /= 2 ** (10 * magnitude)
                    return '{0:.2f}{1}'.format(bts, prefix)
        else:
            if bts == 0:
                return '0.00 KB'

            for magnitude, prefix in zip(range(len(self.fixes)), self.fixes):
                if 10 ** (3 * magnitude) <= bts < 10 ** (3 * (magnitude + 1)):
                    bts /= (10 ** (3 * magnitude))
                    return '{0:.2f}{1}'.format(bts, prefix)

        raise ValueError('Bytes received too large, received {}'.format(bts))

    @staticmethod
    def _flatten(snap: Dict[str, Dict[str, str]]) -> List[str]:
        """
        Flatten nested dictionaries.
        """
        ret = []

        for volume in snap:
            ret.append(volume)
            for usage in snap[volume]:
                ret.append(snap[volume][usage])

        return ret

    @staticmethod
    def _extend(value: str, properWidth: int) -> str:
        """
        Extend a string to the proper width.
        """
        return (' ' * abs(len(value) - properWidth)) + value


def main() -> None:
    """
    Get user input. Set up process.
    """
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-a', '--agent', type=str, action='append',
        help='Run the script on particular agent(s)/UUID(s)'
    )

    # Cannot call both --metric and --noscale.
    group = parser.add_mutually_exclusive_group()

    group.add_argument('-m', '--metric', default=True, action='store_false',
        help='Present the columns in base-10 (HD/metric) magnitude rather '
             'than the default binary output.'
    )

    group.add_argument('-n', '--noscale', default=False, action='store_true',
        help='Do not scale byte counts (for later processing/plotting)'
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
                    uuid = input('Agent: ').lower()
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

    # allSnaps :: List[List[Dict[str, Dict[str, int]]]]

    PresentNiceColumns(allSnaps, binary=args.metric, noscale=args.noscale).render()


if __name__ == '__main__':
    main()
