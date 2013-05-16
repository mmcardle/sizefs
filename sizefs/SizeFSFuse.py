#!/usr/bin/env python

import logging

from collections import defaultdict
from errno import ENOENT, EPERM
from stat import S_IFDIR, S_IFLNK, S_IFREG
from sys import argv, exit
from time import time

import re
import os
import stat
from contents import Filler

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

if not hasattr(__builtins__, 'bytes'):
    bytes = str

FILE_REGEX = re.compile("^(?P<size>[0-9]+(\.[0-9])?)(?P<size_si>[TGMKB])"
                        "((?P<operator>[\+|\-])(?P<shift>\d+)(?P<shift_si>[TGMKB]))?$")

ONE_K = 1024

ENOATTR = 1009  # Python 2 does not provide ENOATTR in errno for some reason

class SizeFSFuse(LoggingMixIn, Operations):
    """
     Size Filesystem.

     Allows 1 level of folders to be created that have an xattr describing how files should be filled (regex).
     Each directory contains a list of commonly useful file sizes, however non-listed files of arbitrary size
     can be opened and read from. The size spec comes from the filename, e.g.

       open("/<folder>/1.1T-1")
    """

    def __init__(self):
        self.folders = {}
        self.files = {}
        self.data = defaultdict(bytes)
        self.fd = 0
        now = time()
        self.folders['/'] = dict(st_mode=(S_IFDIR | 0444), st_ctime=now,
                                 st_mtime=now, st_atime=now, st_nlink=2)

        # Create the default dirs (zeros, ones, common)
        self.mkdir('/zeros', (S_IFDIR | 0444))
        self.setxattr('/zeros', "pattern", "0", None)
        self.mkdir('/ones', (S_IFDIR | 0444))
        self.setxattr('/ones', "pattern", "1", None)
        self.mkdir('/alpha_num', (S_IFDIR | 0444))
        self.setxattr('/alpha_num', "pattern", "[a-z,A-Z,0-9]", None)


    def chmod(self, path, mode):
        """
         We'll return EPERM error to indicate that the user cannot change the permissions of files/folders
        """
        return FuseOSError(EPERM)

    def chown(self, path, uid, gid):
        """
         We'll return EPERM error to indicate that the user cannot change the ownership of files/folders
        """
        return FuseOSError(EPERM)

    def create(self, path, mode):
        """
         We'll return EPERM error to indicate that the user cannot create files
        """
        return FuseOSError(EPERM)

    def getattr(self, path, fh=None):
        """
         Getattr either returns an attribute dict for a folder from the self.folders map, or it returns a standard
         attribute dict for any valid files
        """
        (folder, filename) = os.path.split(path)

        # Does the folder exist?
        if not folder in self.folders:
            return FuseOSError(ENOENT)

        # Does the requested filename match our size spec?
        if not FILE_REGEX.match(filename):
            return FuseOSError(ENOENT)

        if path in self.folders:
            return self.folders[path]
        else:
            return dict(st_mode=(S_IFREG | 0444), st_nlink=1,
                        st_size=0, st_ctime=time(), st_mtime=time(),
                        st_atime=time())

    def getxattr(self, path, name, position=0):
        """
         Returns an extended attribute of a file/folder
         This is always an ENOATTR error for files, and the only thing that should ever really be used
         for folders is the pattern
        """
        attrs = self.folders[path].get('attrs', {})

        if name in attrs:
            return attrs[name]
        else:
            return FuseOSError(ENOATTR)

    def listxattr(self, path):
        """
         Return a list of all extended attribute names for a folder (always empty for files)
        """
        attrs = self.folders[path].get('attrs', {})
        return attrs.keys()

    def mkdir(self, path, mode):
        """
         Here we ignore the mode because we only allow 0444 directories to be created
        """
        self.folders[path] = dict(st_mode=(S_IFDIR | 0444), st_nlink=2,
                                  st_size=0, st_ctime=time(), st_mtime=time(),
                                  st_atime=time())

        # Set the default pattern for a folder to "0" so that all new folders default to filling files with zeros
        self.setxattr(path, "pattern", "0", None)
        self.folders['/']['st_nlink'] += 1

    def open(self, path, flags):
        """
         We check that a file conforms to a size spec and is from a requested folder
        """
        (folder, filename) = os.path.split(path)

        # Does the folder exist?
        if not folder in self.folders:
            return FuseOSError(ENOENT)

        # Does the requested filename match our size spec?
        if not FILE_REGEX.match(filename):
            return FuseOSError(ENOENT)

        ## Now do the right thing and open one of the file objects (add it to files)

        self.fd += 1
        return self.fd

    def read(self, path, size, offset, fh):
        """
         Returns content based on the pattern of the containing folder
        """
        return self.data[path][offset:offset + size]

    def readdir(self, path, fh):
        return ['.', '..'] + [x[1:] for x in self.files if x != '/']

    def readlink(self, path):
        return self.data[path]

    def removexattr(self, path, name):
        attrs = self.folders[path].get('attrs', {})

        if name in attrs:
            del attrs[name]
        else:
            return FuseOSError(ENOATTR)

    def rename(self, old, new):
        self.folders[new] = self.folders.pop(old)



    # FIX ME
    def rmdir(self, path):
        self.files.pop(path)
        self.files['/']['st_nlink'] -= 1

    def setxattr(self, path, name, value, options, position=0):
        # Ignore options
        if path in self.folders:
            attrs = self.folders[path].setdefault('attrs', {})
            attrs[name] = value
        else:
            return FuseOSError(EPERM)

    def statfs(self, path):
        return dict(f_bsize=512, f_blocks=4096, f_bavail=2048)

    def symlink(self, target, source):
        return FuseOSError(EPERM)

    def truncate(self, path, length, fh=None):
        return FuseOSError(EPERM)

    def unlink(self, path):
        if path in self.folders:
            self.folders.pop(path)
        else:
            return FuseOSError(EPERM)

    def utimens(self, path, times=None):
        pass

    def write(self, path, data, offset, fh):
        return FuseOSError(EPERM)


if __name__ == '__main__':
    if len(argv) != 2:
        print('usage: %s <mountpoint>' % argv[0])
        exit(1)

    logging.getLogger().setLevel(logging.DEBUG)
    fuse = FUSE(SizeFSFuse(), argv[1], foreground=True)