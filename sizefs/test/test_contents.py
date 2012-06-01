__author__ = 'jjw'

from sizefs.contents import Filler
import re

def test_simple():
    filler = Filler(regenerate=False,pattern="0",max_random=128)
    contents = filler.fill(16)
    assert contents == "0000000000000000"

def test_repeat():
    filler = Filler(regenerate=False,pattern="ab",max_random=128)
    contents = filler.fill(16)
    assert contents == "abababababababab"

def test_star():
    filler = Filler(regenerate=True,pattern="a(bc)*d",max_random=128)
    contents = filler.fill(256)
    match = re.match("a(bc)*d",contents)
    assert not match is None

def test_plus():
    filler = Filler(regenerate=True,pattern="a(bc)+d",max_random=128)
    contents = filler.fill(256)
    match = re.match("a(bc)+d",contents)
    assert not match is None

def test_numbered_repeat():
    filler = Filler(regenerate=True,pattern="a(bc){5}d",max_random=128)
    contents = filler.fill(16)
    assert contents == "abcbcbcbcbcdabcb"

def test_choice():
    filler = Filler(regenerate=True,pattern="a[012345]{14}b",max_random=128)
    contents = filler.fill(256)
    match = re.match("a[012345]{14}b",contents)
    assert not match is None

def test_range():
    filler = Filler(regenerate=True,pattern="a[0-9,a-z,A-Z]{5}d",max_random=128)
    contents = filler.fill(256)
    match = re.match("a[0-9,a-z,A-Z]{5}d",contents)
    assert not match is None


