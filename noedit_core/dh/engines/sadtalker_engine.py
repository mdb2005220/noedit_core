# -*- coding: utf-8 -*-
"""SadTalker 引擎封装（MIT，备选）。

要求：本地克隆 SadTalker 仓库 + 官方 checkpoints，设置环境变量
NOEDIT_DH_SADTALKER 指向仓库根目录。输入单张照片 + 音频，输出说话人脸视频。
"""
from __future__ import annotations

import glob
import os
import subprocess

from .base import Engine, EngineError


def _has(module: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:
        return False


def _repo_root() -> str:
    return os.environ.get("NOEDIT_DH_SADTALKER", "").strip()


class SadTalkerEngine(Engine):
    name = "sadtalker"

    def check(self) -> str:
        if not _has("torch"):
            return "missing torch"
        root = _repo_root()
        if not root or not os.path.isfile(os.path.join(root, "inference.py")):
            return "missing repo (set NOEDIT_DH_SADTALKER to SadTalker checkout)"
        if not glob.glob(os.path.join(root, "checkpoints", "*")):
            return "missing checkpoints (bash scripts/download_models.sh)"
        return "ok"

    def generate(self, image: str, audio: str, out_path: str, **kw) -> str:
        status = self.check()
        if status != "ok":
            raise EngineError("sadtalker 引擎不可用: %s" % status)
        root = _repo_root()
        out_dir = os.path.dirname(out_path) or "."
        cmd = [os.environ.get("PYTHON", "python"), "inference.py",
               "--driven_audio", audio,
               "--source_image", image,
               "--result_dir", out_dir,
               "--still", "--preprocess", "full",
               "--enhancer", "gfpgan"]
        env = dict(os.environ, PYTHONPATH=root)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=root, env=env)
        if r.returncode != 0:
            raise EngineError("SadTalker 推理失败: %s" % (r.stderr or r.stdout)[-400:])
        # result_dir 下的 mp4 找最新，改名到 out_path
        cand = [f for f in glob.glob(os.path.join(out_dir, "*.mp4"))
                if not f.endswith(out_path)]
        cand = [f for f in glob.glob(os.path.join(out_dir, "**", "*.mp4"), recursive=True)]
        if not cand:
            raise EngineError("SadTalker 未产出视频")
        latest = max(cand, key=os.path.getmtime)
        if os.path.abspath(latest) != os.path.abspath(out_path):
            os.replace(latest, out_path)
        return out_path


def register_self():
    from . import register as _reg
    _reg("sadtalker", SadTalkerEngine)


register_self()
