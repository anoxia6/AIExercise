from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class CameraProfile:
    name: str
    v4l2_controls: Mapping[str, str] = field(default_factory=dict)
    opencv_props: Mapping[int, float] = field(default_factory=dict)


class RGAHelper:
    def __init__(self):
        self.backend_name = "opencv"
        self._backend = None
        self._load_backend()

    def _load_backend(self):
        candidates = ("rga_ctypes", "rga", "librga", "im2d")
        for module_name in candidates:
            try:
                module = __import__(module_name)
            except Exception:
                continue

            backend = getattr(module, "RGA", None)
            if callable(backend):
                try:
                    backend = backend()
                except Exception:
                    backend = module
            else:
                backend = module

            if any(hasattr(backend, name) for name in ("resize", "imresize", "cvtColor", "cvt_color")):
                self._backend = backend
                self.backend_name = module_name
                print(f"[INFO] RGA backend active: {module_name}")
                return

        print("[INFO] RGA backend unavailable, using OpenCV fallback.")

    def available(self) -> bool:
        return self._backend is not None

    def resize(self, img, dsize, interpolation=cv2.INTER_LINEAR):
        if img is None:
            return None

        if tuple(dsize) == (img.shape[1], img.shape[0]):
            return img

        backend = self._backend
        if backend is not None:
            for method_name in ("resize", "imresize", "Resize"):
                fn = getattr(backend, method_name, None)
                if not callable(fn):
                    continue
                for args in ((img, dsize), (img, dsize[0], dsize[1]), (img, dsize[1], dsize[0])):
                    try:
                        result = fn(*args)
                        if result is not None:
                            return np.asarray(result)
                    except Exception:
                        continue

        return cv2.resize(img, dsize, interpolation=interpolation)

    def cvtColor(self, img, code):
        if img is None:
            return None

        backend = self._backend
        if backend is not None:
            for method_name in ("cvtColor", "cvt_color"):
                fn = getattr(backend, method_name, None)
                if not callable(fn):
                    continue
                for args in ((img, code), (img,)):
                    try:
                        result = fn(*args)
                        if result is not None:
                            return np.asarray(result)
                    except Exception:
                        continue

        return cv2.cvtColor(img, code)


rga_helper = RGAHelper()


PROFILE_PRESETS = {
    "balanced": CameraProfile(
        name="balanced",
        v4l2_controls={
            "exposure_auto": "3",
            "white_balance_temperature_auto": "1",
            "brightness": "128",
            "contrast": "32",
            "saturation": "64",
            "sharpness": "4",
        },
        opencv_props={
            cv2.CAP_PROP_BUFFERSIZE: 1,
        },
    ),
    "indoor": CameraProfile(
        name="indoor",
        v4l2_controls={
            "exposure_auto": "1",
            "exposure_absolute": "60",
            "gain": "8",
            "white_balance_temperature_auto": "0",
            "white_balance_temperature": "4300",
            "brightness": "132",
            "contrast": "36",
            "saturation": "70",
            "sharpness": "5",
        },
        opencv_props={
            cv2.CAP_PROP_BUFFERSIZE: 1,
        },
    ),
    "outdoor": CameraProfile(
        name="outdoor",
        v4l2_controls={
            "exposure_auto": "1",
            "exposure_absolute": "30",
            "gain": "0",
            "white_balance_temperature_auto": "0",
            "white_balance_temperature": "5200",
            "brightness": "120",
            "contrast": "30",
            "saturation": "60",
            "sharpness": "4",
        },
        opencv_props={
            cv2.CAP_PROP_BUFFERSIZE: 1,
        },
    ),
    "night": CameraProfile(
        name="night",
        v4l2_controls={
            "exposure_auto": "1",
            "exposure_absolute": "150",
            "gain": "16",
            "white_balance_temperature_auto": "0",
            "white_balance_temperature": "4000",
            "brightness": "140",
            "contrast": "40",
            "saturation": "72",
            "sharpness": "6",
        },
        opencv_props={
            cv2.CAP_PROP_BUFFERSIZE: 1,
        },
    ),
}


def resolve_camera_source(raw_value: Optional[str] = None):
    value = raw_value if raw_value is not None else os.getenv("PRIMECIALLO_CAMERA_SOURCE", "21")
    value = str(value).strip()
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


def resolve_camera_device(source) -> Optional[str]:
    if isinstance(source, int):
        return f"/dev/video{source}"
    if isinstance(source, str) and source.startswith("/dev/video"):
        return source
    return None


def open_video_capture(source):
    prefer_v4l2 = os.name == "posix" and hasattr(cv2, "CAP_V4L2") and (
        isinstance(source, int) or (isinstance(source, str) and source.startswith("/dev/video"))
    )
    if prefer_v4l2:
        return cv2.VideoCapture(source, cv2.CAP_V4L2)
    return cv2.VideoCapture(source)


class CameraISPTuner:
    def __init__(self, profile_name: str = "balanced", device: Optional[str] = None):
        self.profile_name = profile_name if profile_name in PROFILE_PRESETS else "balanced"
        self.profile = PROFILE_PRESETS[self.profile_name]
        self.device = device

    @classmethod
    def from_env(cls, device: Optional[str] = None):
        return cls(profile_name=os.getenv("PRIMECIALLO_ISP_PROFILE", "balanced"), device=device)

    def _list_v4l2_controls(self):
        if not self.device:
            return set()

        v4l2_ctl = shutil.which("v4l2-ctl")
        if not v4l2_ctl:
            return set()

        proc = subprocess.run(
            [v4l2_ctl, "-d", self.device, "--list-ctrls"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return set()

        controls = set()
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("User Controls") or line.startswith("Camera Controls"):
                continue
            controls.add(line.split()[0])
        return controls

    def _apply_v4l2_controls(self):
        if not self.device:
            return False

        v4l2_ctl = shutil.which("v4l2-ctl")
        if not v4l2_ctl:
            return False

        supported = self._list_v4l2_controls()
        kv_pairs = []
        for name, value in self.profile.v4l2_controls.items():
            if not supported or name in supported:
                kv_pairs.append(f"{name}={value}")

        if not kv_pairs:
            return False

        proc = subprocess.run(
            [v4l2_ctl, "-d", self.device, "-c", ",".join(kv_pairs)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return False

        print(f"[INFO] Applied V4L2 ISP profile '{self.profile_name}' on {self.device}")
        return True

    def _apply_opencv_props(self, cap):
        applied = False
        for prop_id, value in self.profile.opencv_props.items():
            try:
                applied = cap.set(prop_id, value) or applied
            except Exception:
                continue
        return applied

    def apply(self, cap):
        if cap is None:
            return False
        self._apply_opencv_props(cap)
        return self._apply_v4l2_controls()
