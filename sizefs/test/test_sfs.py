__author__ = 'jjw'

from sizefs import SizeFS
import re

sfs = SizeFS()

def test_regex_dir():
    sfs.add_regex_dir("regex1","a(bcd)*e{4}")
    regex_file = sfs.open('regex1/128KB')
    regex_file_contents = regex_file.read()
    match = re.match("a(bcd)*e{4}",regex_file_contents)
    assert (len(regex_file_contents) == 131072 and not match is None)
