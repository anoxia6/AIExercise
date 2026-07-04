from __future__ import annotations

import ctypes
import os
from ctypes.util import find_library

import numpy as np


class rga_buffer_t(ctypes.Structure):
    _fields_ = [
        ("vir_addr", ctypes.c_void_p),
        ("phy_addr", ctypes.c_void_p),
        ("fd", ctypes.c_int),
        ("handle", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("wstride", ctypes.c_int),
        ("hstride", ctypes.c_int),
        ("format", ctypes.c_int),
        ("color_space_mode", ctypes.c_int),
        ("global_alpha", ctypes.c_int),
        ("rd_mode", ctypes.c_int),
    ]


RK_FORMAT_RGBA_8888 = 0x0 << 8
RK_FORMAT_RGB_888 = 0x2 << 8
RK_FORMAT_BGR_888 = 0x7 << 8

IM_STATUS_SUCCESS = 1


class RGA:
    def __init__(self):
        self.librga = None
        self._imresize = None
        self._imcvtcolor = None
        self._load_library()

    def _candidate_library_names(self):
        names = []
        env_path = os.getenv("LIBRGA_PATH")
        if env_path:
            names.append(env_path)
        found = find_library("rga")
        if found:
            names.append(found)
        names.extend(
            [
                "librga.so",
                "librga.so.2",
                "librga.so.2.2.0",
                "/usr/lib/aarch64-linux-gnu/librga.so",
                "/usr/lib/liblibrga.so",
            ]
        )
        return names

    def _load_library(self):
        for name in self._candidate_library_names():
            try:
                self.librga = ctypes.CDLL(name)
                print(f"[RGA-CTYPES] loaded: {name}")
                break
            except OSError:
                continue

        if not self.librga:
            return

        for func_name, argtypes in (
            ("imresize_t", [rga_buffer_t, rga_buffer_t, ctypes.c_double, ctypes.c_double, ctypes.c_int, ctypes.c_int]),
            ("imresize", [rga_buffer_t, rga_buffer_t]),
        ):
            fn = getattr(self.librga, func_name, None)
            if fn is not None:
                self._imresize = fn
                self._imresize.argtypes = argtypes
                self._imresize.restype = ctypes.c_int
                break

        for func_name in ("imcvtcolor_t", "imcvtcolor"):
            fn = getattr(self.librga, func_name, None)
            if fn is not None:
                self._imcvtcolor = fn
                self._imcvtcolor.argtypes = [rga_buffer_t, rga_buffer_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
                self._imcvtcolor.restype = ctypes.c_int
                break

    def is_available(self):
        return self.librga is not None and self._imresize is not None

    def _make_buffer(self, img, format_enum):
        if not img.flags["C_CONTIGUOUS"]:
            img = np.ascontiguousarray(img)
        buf = rga_buffer_t()
        buf.vir_addr = img.ctypes.data
        buf.fd = -1
        buf.handle = 0
        buf.width = img.shape[1]
        buf.height = img.shape[0]
        buf.wstride = img.shape[1]
        buf.hstride = img.shape[0]
        buf.format = format_enum
        buf.color_space_mode = 0
        buf.global_alpha = 0
        buf.rd_mode = 0
        return buf, img

    def resize(self, src_img, dsize):
        if not self.is_available():
            raise RuntimeError("RGA is not available.")

        src_buf, src_img = self._make_buffer(src_img, RK_FORMAT_BGR_888)
        dst_img = np.zeros((dsize[1], dsize[0], 3), dtype=np.uint8)
        dst_buf, dst_img = self._make_buffer(dst_img, RK_FORMAT_BGR_888)

        if self._imresize.argtypes and len(self._imresize.argtypes) == 6:
            ret = self._imresize(src_buf, dst_buf, 0.0, 0.0, 1, 1)
        else:
            ret = self._imresize(src_buf, dst_buf)

        if ret != IM_STATUS_SUCCESS:
            raise RuntimeError(f"RGA resize failed: {ret}")
        return dst_img

    def cvtColor(self, src_img, code):
        if not self.is_available():
            raise RuntimeError("RGA is not available.")

        if code == 4:  # cv2.COLOR_BGR2RGB
            src_fmt = RK_FORMAT_BGR_888
            dst_fmt = RK_FORMAT_RGB_888
        else:
            raise NotImplementedError(f"Unsupported cvtColor code: {code}")

        if self._imcvtcolor is None:
            raise RuntimeError("RGA cvtColor is unavailable.")

        src_buf, src_img = self._make_buffer(src_img, src_fmt)
        dst_img = np.zeros_like(src_img)
        dst_buf, dst_img = self._make_buffer(dst_img, dst_fmt)
        ret = self._imcvtcolor(src_buf, dst_buf, src_fmt, dst_fmt, 0, 1)
        if ret != IM_STATUS_SUCCESS:
            raise RuntimeError(f"RGA cvtColor failed: {ret}")
        return dst_img
