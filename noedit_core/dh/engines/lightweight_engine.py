# -*- coding: utf-8 -*-
"""轻量占位引擎：无深度学习依赖（ffmpeg + Pillow）。

对静态照片做缓慢呼吸缩放 + 亮度脉动，并与讲稿音频合并成 MP4。
效果不逼真，但能立即验证「照片 → 视频 → 页面元素 → 导出」全链路。
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile

from .base import Engine, EngineError


def _has(module: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:
        return False


def _ffmpeg_exe() -> str:
    """优先系统 ffmpeg；没有则用 imageio-ffmpeg 捆绑二进制；都没有返回空串。"""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return ""


def _ffprobe_seconds(audio: str, ffmpeg_exe: str) -> float:
    """用 ffmpeg 自带探测拿音频时长（兼容无独立 ffprobe 的捆绑版）。"""
    if not ffmpeg_exe:
        return 0.0
    try:
        out = subprocess.run(
            [ffmpeg_exe, "-hide_banner", "-i", audio],
            capture_output=True, text=True, timeout=30,
        )
        # 在 stderr 里找 "Duration: 00:00:12.34"
        import re
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out.stderr)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0


def _probe_audio_seconds(audio: str) -> float:
    """探音频时长：优先系统 ffprobe，退回 ffmpeg 解析。"""
    probe = shutil.which("ffprobe")
    if probe:
        try:
            out = subprocess.run(
                [probe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=nw=1:nk=1", audio],
                capture_output=True, text=True, timeout=30,
            )
            return float(out.stdout.strip())
        except Exception:
            pass
    return _ffprobe_seconds(audio, _ffmpeg_exe())


class LightweightEngine(Engine):
    name = "lightweight"

    def check(self) -> str:
        if not _has("PIL"):
            return "missing Pillow"
        if not _ffmpeg_exe():
            return "missing ffmpeg (install ffmpeg / pip install imageio-ffmpeg)"
        return "ok"

    def generate(self, image: str, audio: str, out_path: str, **kw) -> str:
        status = self.check()
        if status != "ok":
            raise EngineError("lightweight 引擎不可用: %s" % status)
        from PIL import Image, ImageEnhance

        ffmpeg = _ffmpeg_exe()
        fps = int(kw.get("fps", 15))
        duration = float(kw.get("duration", 0)) or _probe_audio_seconds(audio) or 4.0
        w = int(kw.get("width", 480))
        # 高按原图比例算，限制在 480~720
        base = Image.open(image).convert("RGB")
        h = max(480, min(720, int(base.height * w / base.width)))
        nframes = max(1, int(duration * fps))

        tmp = tempfile.mkdtemp(prefix="dh_light_")
        try:
            for i in range(nframes):
                t = i / fps
                # 呼吸缩放：1.00 ~ 1.03
                scale = 1.0 + 0.015 * (1.0 - math.cos(t * 2 * math.pi / max(duration, 0.1)))
                sw, sh = int(w * scale), int(h * scale)
                frame = base.resize((sw, sh), Image.LANCZOS)
                # 居中裁回目标尺寸
                frame = frame.crop(((sw - w) // 2, (sh - h) // 2,
                                    (sw - w) // 2 + w, (sh - h) // 2 + h))
                # 亮度脉动：0.97 ~ 1.03
                frame = ImageEnhance.Brightness(frame).enhance(
                    1.0 + 0.03 * math.sin(t * 2 * math.pi / max(duration, 0.1)))
                frame.save(os.path.join(tmp, "f%05d.png" % i))

            # 合成：视频流（帧序列）+ 原音频；时长以音频为准（-shortest）
            cmd = [ffmpeg, "-y",
                   "-framerate", str(fps), "-i", os.path.join(tmp, "f%05d.png"),
                   "-i", audio,
                   "-c:v", "libx264", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-shortest",
                   "-movflags", "+faststart", out_path]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if r.returncode != 0 or not os.path.exists(out_path):
                raise EngineError("ffmpeg 合成失败: %s" % r.stderr[-400:])
            return out_path
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def register_self():
    from . import register as _reg
    _reg("lightweight", LightweightEngine)


register_self()
