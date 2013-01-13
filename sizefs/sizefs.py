#!/usr/bin/env python
"""
SizeFS
===========

A mock Filesystem that exists in memory only. Returns files of a size as
specified by the filename

For example, reading a file named 128Mb+1 will return a file of 128 Megabytes
plus 1 byte, reading a file named 128Mb-1 will return a file of 128 Megabytes
minus 1 byte

>>> sfs = SizeFS()
>>> print len(sfs.open('1B').read())
1
>>> print len(sfs.open('2B').read())
2
>>> print len(sfs.open('1KB').read())
1024
>>> print len(sfs.open('128KB').read())
131072

The folder structure can also be used to determine the content of the files

>>> print sfs.open('zeros/5B').read(5)
00000

>>> print sfs.open('ones/128KB').read(5)
11111

File content can also be random

>>> print len(sfs.open('random/128KB').read())
131072
>>> print len(sfs.open('random/128KB-1').read())
131071
>>> print len(sfs.open('random/128KB+1').read())
131073

"""

__author__ = 'mm'

import datetime
import re
import stat
from fs.path import iteratepath, pathsplit, normpath
from fs.base import FS, synchronize
from fs.errors import ResourceNotFoundError, ResourceInvalidError
from contents import Filler

FILE_REGEX = re.compile("(?P<size>[0-9]*)(?P<si>[TGMK])*"
                        "(?P<unit>[bB]?)(?P<operator>[\+|\-]?)"
                        "(?P<shift>\d*)")
ONE_K = 1024


def __get_shift__(match):
    """
    Parses the shift part of a filename e.g. +128, -110
    """
    shift = 0
    keys = match.groupdict().keys()
    if "operator" in keys and "shift" in keys:
        operator = match.group('operator')
        shift_str = match.group('shift')
        if operator != '' and shift_str != '':
            shift = int(shift_str)
            if operator == "-":
                shift = -shift
    return shift


def __get_size__(filename):
    """
    Parses the filename to get the size of a file
    e.g. 128Mb+12, 110Mb-10b
    """
    match = FILE_REGEX.search(filename)
    if match:
        size_str = match.group('size')
        si_unit = match.group('si')
        unit = match.group('unit')
        shift = __get_shift__(match)
        div = 1
        if unit == 'b':
            div = 8
        elif unit == 'B' or not unit:
            div = 1
        else:
            raise ValueError
        if not si_unit:
            mul = 1
        elif si_unit == 'K':
            mul = ONE_K
        elif si_unit == 'M':
            mul = pow(ONE_K, 2)
        elif si_unit == 'G':
            mul = pow(ONE_K, 3)
        elif si_unit == 'T':
            mul = pow(ONE_K, 4)
        else:
            raise ValueError
        size = int(size_str)
        size_in_bytes = (size * mul / div) + shift
        return size_in_bytes
    else:
        return 0

class SizeFile(object):
    """
    A mock file object that returns a specified number of bytes
    """

    def __init__(self, path, size, filler=Filler(pattern="0")):
        self.closed = False
        self.length = size
        self.pos = 0
        self.filler = filler
        self.path = path

    def close(self):
        """ close the file to prevent further reading """
        self.closed = True

    def read(self, size=None):
        """ read size from the file, or if size is None read to end """
        if self.pos >= self.length or self.closed:
            return ''
        if size is None:
            toread = self.length - self.pos
            if toread > 0:
                return self.filler.fill(toread)
            else:
                return ''
        else:
            if size + self.pos >= self.length:
                toread = self.length - self.pos
                self.pos = self.length
                return self.filler.fill(toread)
            else:
                toread = size
                self.pos = self.pos + size
                return self.filler.fill(toread)

    def seek(self, offset):
        """ seek the position by a distance of 'offset' bytes
        """
        self.pos = self.pos + offset

    def tell(self):
        """ return how much of the file is left to read """
        return self.pos


class DirEntry(object):  # pylint: disable=R0902
    """
    A directory entry. Can be a file or folder.
    """

    def __init__(self, dir_type, name, contents=None,
                 filler=Filler(pattern="0")):

        assert dir_type in ("dir", "file"), "Type must be dir or file!"

        self.type = dir_type
        self.name = name

        if contents is None and dir_type == "dir":
            contents = {}

        self.filler = filler
        self.contents = contents
        self.mem_file = None
        self.created_time = datetime.datetime.now()
        self.modified_time = self.created_time
        self.accessed_time = self.created_time

        if self.type == 'file':
            self.mem_file = SizeFile(name, __get_size__(name), filler=filler)

    def desc_contents(self):
        """ describes the contents of this DirEntry """
        if self.isfile():
            return "<file %s>" % self.name
        elif self.isdir():
            return "<dir %s>" % "".join(
                "%s: %s" % (k, v.desc_contents())
                    for k, v in self.contents.iteritems())

    def isdir(self):
        """ is this DirEntry a directory """
        return self.type == "dir"

    def isfile(self):
        """ is this DirEntry a file """
        return self.type == "file"

    def __str__(self):
        return "%s: %s" % (self.name, self.desc_contents())

class SizeFS(FS):  # pylint: disable=R0902,R0904,R0921
    """
    A mock file system that returns files of specified sizes and content
    """
    def __init__(self, *args, **kwargs):
        super(SizeFS, self).__init__(*args, **kwargs)
        #thread_synchronize=_thread_synchronize_default)
        self.sizes = [1, 10, 100]
        self.si_units = ['K', 'M', 'G']
        self.units = ["B", "b"]
        files = ["%s%s%s" % (size, si, unit)
                 for size in self.sizes
                 for si in self.si_units
                 for unit in self.units]
        self.root = DirEntry('dir', 'root')

        self.zeros = DirEntry('dir', 'zeros', filler=Filler(pattern="0"))
        self.ones = DirEntry('dir', 'ones', filler=Filler(pattern="1"))
        self.random = DirEntry('dir', 'random', filler=Filler(regenerate=True,pattern="[a-z,A-Z,0-9]",max_random=128))
        self.common = DirEntry('dir', 'common')

        for filename in files:
            self.zeros.contents[filename] = DirEntry(
                'file', filename, filler=Filler(pattern="0"))
            self.ones.contents[filename] = DirEntry(
                'file', filename, filler=Filler(pattern="1"))
            self.random.contents[filename] = DirEntry(
                'file', filename, filler=Filler(regenerate=True,pattern="[a-z,A-Z,0-9]",max_random=128))

        self.root.contents['zeros'] = self.zeros
        self.root.contents['ones'] = self.ones
        self.root.contents['random'] = self.random
        self.root.contents['common'] = self.common

    def _get_dir_entry(self, dir_path):
        """
        Returns a DirEntry for a specified path 'dir_path'
        """
        dir_path = normpath(dir_path)
        current_dir = self.root
        for path_component in iteratepath(dir_path):
            if current_dir.contents is None:
                return None
            dir_entry = current_dir.contents.get(path_component, None)
            if dir_entry is None:
                return None
            current_dir = dir_entry
        return current_dir

    def isdir(self, path):
        path = normpath(path)
        if path in ('', '/'):
            return True
        dir_item = self._get_dir_entry(path)
        if dir_item is None:
            return False
        return dir_item.isdir()

    def add_regex_dir(self, name, regex, max_random=128, regenerate=True):
        dir = DirEntry('dir', name, filler=Filler(regenerate=regenerate,pattern=regex,max_random=max_random))
        self.root.contents[name] = dir

    @synchronize
    def isfile(self, path):
        path = normpath(path)
        if path in ('', '/'):
            return False
        dir_item = self._get_dir_entry(path)
        if dir_item is None:
            return False
        return dir_item.isfile()

    @synchronize
    def makedir(self, dirname, recursive=False, allow_recreate=False):
        raise NotImplementedError

    @synchronize
    def remove(self, path):
        raise NotImplementedError

    @synchronize
    def removedir(self, path, recursive=False, force=False):
        raise NotImplementedError

    @synchronize
    def rename(self, src, dst):
        raise NotImplementedError

    @synchronize
    def listdir(self, path="/", wildcard=None,  # pylint: disable=R0913
                full=False, absolute=False,
                dirs_only=False, files_only=False):
        dir_entry = self._get_dir_entry(path)
        if dir_entry is None:
            raise ResourceNotFoundError(path)
        if dir_entry.isfile():
            raise ResourceInvalidError(path, msg="not a directory: %(path)s")
        paths = dir_entry.contents.keys()
        for (i, _path) in enumerate(paths):
            if not isinstance(_path, unicode):
                paths[i] = unicode(_path)
        p_dirs = self._listdir_helper(path, paths, wildcard, full,
            absolute, dirs_only, files_only)
        return p_dirs

    @synchronize
    def getinfo(self, path):
        dir_entry = self._get_dir_entry(path)

        if dir_entry is None:
            raise ResourceNotFoundError(path)

        info = {}
        info['created_time'] = dir_entry.created_time
        info['modified_time'] = dir_entry.modified_time
        info['accessed_time'] = dir_entry.accessed_time

        if dir_entry.isdir():
            info['st_mode'] = 0755 | stat.S_IFDIR
        else:
            info['size'] = dir_entry.mem_file.length
            info['st_mode'] = 0666 | stat.S_IFREG

        return info

    @synchronize
    def open(self, path, mode="r", **kwargs):
        """

        """
        path = normpath(path)
        file_path, file_name = pathsplit(path)
        parent_dir_entry = self._get_dir_entry(file_path)

        if parent_dir_entry is None or not parent_dir_entry.isdir():
            raise ResourceNotFoundError(path)

        if 'r' in mode:

            if file_name in parent_dir_entry.contents:
                file_dir_entry = parent_dir_entry.contents[file_name]
                if file_dir_entry.isdir():
                    raise ResourceInvalidError(path)

                file_dir_entry.accessed_time = datetime.datetime.now()
                return file_dir_entry.mem_file
            else:
                size = __get_size__(file_name)
                mem_file = SizeFile(path, size, filler=parent_dir_entry.filler)
                return mem_file

        elif 'w' in mode or 'a' in mode:
            raise NotImplementedError

if __name__ == "__main__":
    import doctest
    doctest.testmod()
