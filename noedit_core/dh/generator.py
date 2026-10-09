# -*- coding: utf-8 -*-
"""生成入口：generate(image, audio, engine="auto") → 输出视频路径。

engine="auto" 按效果优先级探测：liveportrait → sadtalker → lightweight；
全部不可用则抛错并列出各引擎缺失项。
"""
from __future__ import annotations

import os
from typing import Optional

from .engines import auto_pick, get
from .engines.base import EngineError
from . import validator


def generate(image: str, audio: str, engine: str = "auto", out_dir: Optional[str] = None,
             out_name: Optional[str] = None, **kw) -> dict:
    """输入真人照片 + 讲稿音频，生成数字人播报视频。

    参数：
        image    : 真人正脸照片路径（png/jpg）
        audio    : 讲稿音频路径（wav/mp3）
        engine   : "auto" | "liveportrait" | "sadtalker" | "lightweight" | "cloud"
        out_dir  : 输出目录（默认与音频同目录）
        out_name : 输出文件名（默认 <照片名>_<音频名>.mp4）
        **kw     : 透传给引擎（lightweight 支持 fps/width/duration 等）

    返回：
        {"video": 输出绝对路径, "engine": 实际使用的引擎}
    """
    if not os.path.isfile(image):
        raise EngineError("照片不存在: %s" % image)
    if not os.path.isfile(audio):
        raise EngineError("音频不存在: %s" % audio)

    out_dir = out_dir or os.path.dirname(os.path.abspath(audio)) or "."
    os.makedirs(out_dir, exist_ok=True)
    if not out_name:
        stem_img = os.path.splitext(os.path.basename(image))[0]
        stem_aud = os.path.splitext(os.path.basename(audio))[0]
        out_name = ("%s_%s.mp4" % (stem_img[:24], stem_aud[:24])).replace(" ", "_")
    out_path = os.path.join(out_dir, out_name)

    if engine == "auto":
        status = validator.check_all()
        picked = auto_pick(lambda n: status.get(n, ""))
        if not picked:
            missing = "\n".join("  %-12s %s" % (k, v) for k, v in status.items())
            raise EngineError("没有可用的数字人引擎。各引擎状态：\n%s\n"
                              "最简单：pip install pillow 并安装 ffmpeg 后用 lightweight 引擎。" % missing)
        engine = picked
    else:
        status = validator.check_all()
        if status.get(engine) and status[engine] != "ok":
            raise EngineError("引擎 %s 不可用: %s" % (engine, status[engine]))

    eng = get(engine)
    result = eng.generate(image, audio, out_path, **kw)
    if not os.path.isfile(result):
        raise EngineError("引擎 %s 未产出文件" % engine)
    return {"video": os.path.abspath(result), "engine": engine}
