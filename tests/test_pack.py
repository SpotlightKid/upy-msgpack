#!/usr/bin/env python

import struct
import sys
from collections import OrderedDict
from io import BytesIO

import pytest
from pytest import raises, xfail

from msgpack import unpackb, Unpacker
from upymsgpack.pack import Packer, packb


def check(data, use_list=False):
    re = unpackb(packb(data), use_list=use_list, strict_map_key=False)
    assert re == data


@pytest.mark.parametrize(
    "obj",
    [
        0,
        1,
        127,
        128,
        255,
        256,
        65535,
        65536,
        4294967295,
        4294967296,
        -1,
        -32,
        -33,
        -128,
        -129,
        -32768,
        -32769,
        -4294967296,
        -4294967297,
        1.0,
        b"",
        b"a",
        b"a" * 31,
        b"a" * 32,
        None,
        True,
        False,
        (),
        ((),),
        ((), None),
        {None: 0},
        (1 << 23),
    ],
)
def test_pack(obj):
    check(obj)


@pytest.mark.parametrize("s", ["", "abcd", ["defgh"], "Русский текст"])
def test_pack_unicode(s):
    re = unpackb(packb(s), use_list=1, raw=False)
    assert re == s
    packer = Packer()
    data = packer.pack(s)
    re = Unpacker(BytesIO(data), raw=False, use_list=1).unpack()
    assert re == s


@pytest.mark.parametrize("bites", [b"", b"abcd", (b"defgh",)])
def test_pack_bytes(bites):
    check(bites)


@pytest.mark.parametrize(
    "ba", [bytearray(b""), bytearray(b"abcd"), (bytearray(b"defgh"),)]
)
def test_pack_bytearray(ba):
    check(ba)


@pytest.mark.skipif(
    sys.version_info < (3, 0), reason="Python 2 passes invalid surrogates"
)
def test_ignore_unicode_errors():
    re = unpackb(
        packb(b"abc\xeddef", use_bin_type=False), raw=False, unicode_errors="ignore"
    )
    assert re == "abcdef"


def test_strict_unicode_unpack():
    packed = packb(b"abc\xeddef", use_bin_type=False)
    with pytest.raises(UnicodeDecodeError):
        unpackb(packed, raw=False, use_list=1)


def test_ignore_errors_pack():
    re = unpackb(
        packb("abc\uDC80\uDCFFdef", use_bin_type=True, unicode_errors="ignore"),
        raw=False,
        use_list=1,
    )
    assert re == "abcdef"


def test_decode_binary():
    re = unpackb(packb(b"abc"), use_list=1)
    assert re == b"abc"


def test_pack_float():
    assert packb(1.0, use_f32=True) == b"\xca" + struct.pack(str(">f"), 1.0)
    assert packb(1.0, use_f32=False) == b"\xcb" + struct.pack(str(">d"), 1.0)


def test_odict():
    seq = [(b"one", 1), (b"two", 2), (b"three", 3), (b"four", 4)]
    od = OrderedDict(seq)
    assert unpackb(packb(od), use_list=1) == dict(seq)

    def pair_hook(seq):
        return list(seq)

    assert unpackb(packb(od), object_pairs_hook=pair_hook, use_list=1) == seq
