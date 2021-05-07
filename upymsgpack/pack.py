try:
    from micropython import const
except ImportError:
    const = lambda x: x

from struct import pack as spack


MAX_NINT5 = const(-(2 ** 5))
MAX_NINT8 = const(-(2 ** 8) // 2)
MAX_NINT16 = const(-(2 ** 16) // 2)
MAX_NINT32 = const(-(2 ** 32) // 2)
MAX_NINT64 = const(-(2 ** 64) // 2)
MAX_UINT7 = const(2 ** 7)
MAX_UINT8 = const(2 ** 8)
MAX_UINT16 = const(2 ** 16)
MAX_UINT32 = const(2 ** 32)
MAX_UINT64 = const(2 ** 64)


class Writer(list):
    def write(self, data):
        assert isinstance(data, bytes)
        self.append(data)

    def contents(self):
        return b"".join(self)


class Packer:
    def __init__(
        self, writer=None, use_bin_type=True, use_f32=False, unicode_errors="strict"
    ):
        self.use_f32 = use_f32
        self.use_bin_type = use_bin_type
        self.unicode_errors = unicode_errors
        self.writer = Writer() if writer is None else writer

    def pack(self, obj):
        self._pack(obj)
        return self.writer.contents()

    def _pack(self, obj):
        w = self.writer

        if obj is None:
            w.write(b"\xC0")
        elif isinstance(obj, bool):
            w.write(b"\xC3" if obj else b"\xC2")
        elif isinstance(obj, int):
            if obj > 0:
                if obj < MAX_UINT7:
                    w.write(bytes([obj]))
                elif obj < MAX_UINT8:
                    w.write(bytes([0xCC, obj]))
                elif obj < MAX_UINT16:
                    w.write(b"\xCD")
                    w.write(spack("!H", obj))
                elif obj < MAX_UINT32:
                    w.write(b"\xCE")
                    w.write(spack("!I", obj))
                elif obj < MAX_UINT64:
                    w.write(b"\xCF")
                    w.write(spack("!Q", obj))
                else:
                    raise ValueError("Integer value >= 2^64 too large.")
            else:
                if obj >= MAX_NINT5:
                    w.write(spack("b", obj))
                elif obj >= MAX_UINT8:
                    w.write(b"\xD0" + spack("!b", obj))
                elif obj >= MAX_NINT16:
                    w.write(b"\xD1" + spack("!h", obj))
                elif obj >= MAX_NINT32:
                    w.write(b"\xD2" + spack("!i", obj))
                elif obj >= MAX_NINT64:
                    w.write(b"\xD3" + spack("!q", obj))
                else:
                    raise ValueError("Integer value < -2^64/2 too small.")
        elif isinstance(obj, float):
            w.write(b"\xCA" if self.use_f32 else b"\xCB")
            w.write(spack("!f" if self.use_f32 else "!d", obj))
        elif isinstance(obj, (bytearray, bytes, str)):
            if isinstance(obj, (bytearray, bytes)) and self.use_bin_type:
                olen = len(obj)

                if olen < MAX_UINT8:
                    w.write(bytes([0xC4, olen]))
                elif olen < MAX_UINT16:
                    w.write(b"\xC5")
                    w.write(spack("!H", olen))
                elif olen < MAX_UINT32:
                    w.write(b"\xC6")
                    w.write(spack("!I", olen))
                else:
                    raise ValueError("Bytes object len >= 2^32 too big.")

                w.write(bytes(obj) if isinstance(obj, bytearray) else obj)
            else:
                if isinstance(obj, str):
                    obj = bytes(obj, encoding="utf-8", errors=self.unicode_errors)

                olen = len(obj)

                if olen < 32:
                    w.write(bytes([olen | 0xA0]))
                elif olen < MAX_UINT8:
                    w.write(bytes([0xD9, olen]))
                elif olen < MAX_UINT16:
                    w.write(b"\xDA")
                    w.write(spack("!H", olen))
                elif olen < MAX_UINT32:
                    w.write(b"\xDB")
                    w.write(spack("!I", olen))
                else:
                    raise ValueError("Bytes object len >= 2^32 too big.")

                w.write(obj)
        elif isinstance(obj, (tuple, list)):
            olen = len(obj)

            if olen < 16:
                w.write(bytes([olen | 0x90]))
            elif olen < MAX_UINT16:
                w.write(b"\xDC")
                w.write(spack("!H", olen))
            elif olen < MAX_UINT32:
                w.write(b"\xDD")
                w.write(spack("!H", olen))
            else:
                raise ValueError("Sequence object has too many (>= 2^32) elements.")

            for elem in obj:
                self._pack(elem)
        elif isinstance(obj, dict):
            olen = len(obj)

            if olen < 16:
                w.write(bytes([olen | 0x80]))
            elif olen < MAX_UINT16:
                w.write(b"\xDE")
                w.write(spack("!H", olen))
            elif olen < MAX_UINT32:
                w.write(b"\xDF")
                w.write(spack("!H", olen))
            else:
                raise ValueError("Dict object has too many (>= 2^32) elements.")

            for elem in obj:
                self._pack(elem)
                self._pack(obj[elem])
        else:
            raise TypeError("Cannot serialize instance of %s." % type(obj))


def packb(obj, **kw):
    """Serialize obj to msgpack format byte string."""
    return Packer(**kw).pack(obj)


def pack(fp, obj, **kw):
    """Serialize obj to msgpack format byte string and write it to file object."""
    return Packer(writer=fp, **kw).pack(obj)
