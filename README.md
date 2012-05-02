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