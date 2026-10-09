# -*- coding: utf-8 -*-
"""数字人环境探测：不装重依赖也能先跑轻量档。

用法：
    python -m noedit_core.dh.validator              # 全量探测并打印
    python -m noedit_core.dh.validator --download liveportrait   # 下载模型权重（未实现，提示手动）
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys


def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def check_lightweight() -> str:
    if not _has_module("PIL"):
        return "missing Pillow"
    if not (_has_ffmpeg() or _has_module("imageio_ffmpeg")):
        return "missing ffmpeg (install ffmpeg / pip install imageio-ffmpeg)"
    return "ok"


def check_liveportrait() -> str:
    from .engines import liveportrait_engine
    return liveportrait_engine.LivePortraitEngine().check()


def check_sadtalker() -> str:
    from .engines import sadtalker_engine
    return sadtalker_engine.SadTalkerEngine().check()


def check_cloud() -> str:
    if not _has_module("requests"):
        return "missing requests"
    from .engines import cloud_engine
    if not cloud_engine.load_config():
        return "no config set (copy cloud_config.example.json -> cloud_config.json)"
    return "ok"


def check_all() -> dict:
    """返回 {engine: 'ok' | 'missing ...'}。至少 lightweight ok 即可开始。"""
    return {
        "lightweight": check_lightweight(),
        "liveportrait": check_liveportrait(),
        "sadtalker": check_sadtalker(),
        "cloud": check_cloud(),
    }


def _print_status():
    status = check_all()
    width = max(len(k) for k in status)
    for k, v in status.items():
        print("%-*s: %s" % (width, k, v))
    return status


def _download_hint(engine: str):
    print("模型权重请按 dh/README.md 手动下载：")
    if engine == "liveportrait":
        print("  https://github.com/KlingAIResearch/LivePortrait  →  pretrained weights")
    elif engine == "sadtalker":
        print("  https://github.com/OpenTalker/SadTalker  →  checkpoints（脚本 bash scripts/download_models.sh）")
    else:
        print("  未知引擎:", engine)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--download":
        _download_hint(argv[1] if len(argv) > 1 else "")
        return 0
    _print_status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
