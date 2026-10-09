# 数字人播报工作流（照片 + 讲稿音频 → dh 模块生成 → 落入工程 → 插入页面）

本文件给**要给 PPT 配虚拟讲师的 Agent** 用：何时用数字人、怎么选引擎、怎么避开许可红线、五步插入页面。模块总览 / 拆分卸载 / 许可对比见 [`noedit_core/dh/README.md`](../../../noedit_core/noedit_core/dh/README.md)。

## 核心约束

1. **`props.src` 只能写工程内 `assets/` 相对路径**（如 `assets/host.mp4`）。云端生成的视频 URL 必须先下载落 `assets/`，**不许直接写外链**。
2. **一页最多 1 个数字人**——数字人是带声视频，多个会互相抢声音。
3. **先问用户**：无人讲解场景才提数字人；现场有人演讲的场合不用。
4. **使用真人照片必须获得当事人授权**；虚拟形象用生图合成（提示词见下）也注意肖像权。
5. **许可红线**：**Wav2Lip 严禁商用**（LRS2 训练数据，官方 README 明说 research only）。商用走 LivePortrait / SadTalker（MIT）或付费云（Azure / 腾讯云）。

## 何时用数字人（判断表）

| 场景 | 建议 |
| --- | --- |
| 无人讲解的对外路演 / 产品页 | 封面或关键页 1 个数字人，其余页用 audio 配音 |
| 教学 / 慕课 | 讲解页配虚拟讲师 |
| 多语言批量出片 | 同一讲稿换音色，数字人批量生成 |
| 现场有人演讲 | **不用**（真人声与数字人声打架） |
| 内部快过一遍的草稿 | 用 audio 就够，别浪费数字人生成时间 |

## 引擎选择（先探测后使用）

```python
from noedit_core import api
api.dh_status()
# {'lightweight': 'ok', 'liveportrait': 'missing repo', 'sadtalker': 'missing repo', 'cloud': 'no config set'}
```

| 状态 | 用法 |
| --- | --- |
| liveportrait / sadtalker `ok` | `engine="auto"` 自动选效果最好的可用档 |
| 只有 lightweight `ok` | `engine="auto"` 也能跑（呼吸缩放 + 音画合并，朴素但链路完整） |
| cloud 配了 key | `engine="cloud"`（Azure / 腾讯云效果最好，付费） |
| 全红 | 老实回退 audio 模式，别硬塞不会说话的假人 |

## 五步标准动作

### 1. 准备照片

- **正脸、干净背景、光线均匀**；分辨率 ≥ 512×512；
- 用户提供了授权照片就用用户的；没有就**生图合成虚拟形象**：

```
professional portrait of a virtual presenter, front-facing, friendly expression,
plain dark blue background, soft studio lighting, corporate style,
business casual, high quality, no text, no watermark
```

### 2. 准备讲稿音频

按 [audio-workflow.md](audio-workflow.md) 的讲稿写法合成该页的口语化讲稿（90–150 字/页）。
数字人的口型/时长完全跟着音频走——**音频质量决定成片质量**。

### 3. 生成播报视频

```python
r = api.generate_digital_human(
    image=r"D:\pics\host.png",     # 正脸照
    audio=r"D:\tts\p1.wav",        # 该页讲稿
    engine="auto",                 # liveportrait → sadtalker → lightweight 自动降级
)
# -> {"video": "D:\\tts\\host_p1.mp4", "engine": "liveportrait"}
```

**失败处理**：指定引擎报"不可用"就换 `engine="auto"`；`auto` 都不行说明连 lightweight 的
Pillow/ffmpeg 都没装——先 `pip install Pillow imageio-ffmpeg`，还失败就回退 audio 模式。

### 4. 落入工程

```python
rec = api.import_asset(P, [r["video"]])["imported"][0]
```

### 5. 插入 digital_human 元素

```python
api.insert(P, {
    "type": "digital_human",
    "name": "页1-数字人",
    "x": 880, "y": 390, "w": 360, "h": 300,   # 右下角，不压正文
    "props": {
        "src": rec["relPath"],                 # assets/host_p1.mp4
        "poster": "",                          # 可选封面帧（没给就深色兜底图）
        "title": "虚拟讲解员",                   # 左下角名牌徽章文字
        "startAt": 0,                          # 进页第几秒开始播报
        "autoplay": True, "loop": False,
        "volume": 1.0,
    },
}, page_index=0)
```

## 导出与演示模式

- **HTML**：进视口后 `startAt` 秒自动开始播报，离视口暂停；名牌徽章显示名字。
- **PPTX**：`add_movie` 真嵌 MP4（放映可播可听），封面帧 + 名牌当海报。
- **PDF / PNG / SVG**：静态封面帧 + 名牌徽章。
- **UI 导出弹窗**：用户三选一——**纯 PPT**（`export(..., mediaMode="plain")` 剥掉音频与数字人）/
  **音频模式**（保留 audio）/ **数字人模式**（全保留）。**主动问用户要哪种**；
  现场放映场景默认建议纯 PPT。

```python
api.export(P, "pptx", out_dir=..., mediaMode="plain")   # 纯 PPT
api.export(P, "pptx", out_dir=...)                       # 默认 full（保留）
```

## 反面模式

- ❌ `props.src` 写外链 URL；
- ❌ 一页塞 2 个数字人；
- ❌ 用 Wav2Lip 做商用交付（License 明确禁止）；
- ❌ 没探测引擎就调 `engine="liveportrait"`（报 missing repo）；
- ❌ 现场演讲场合硬加数字人；
- ❌ 拿未授权真人照片做形象；
- ❌ 没问用户就全篇铺数字人（生成很慢，先确认再批量）；
- ❌ 忘了 `mediaMode="plain"`——用户要「安静放映」结果页面自己开始说话。

## 与 UI 的配合

数字人元素在画布上就是一段视频框 + 左下角名牌徽章；属性面板可上传播报视频、
改名牌文字 / 开始秒 / 音量。导出时若此前没记住过演示模式，会弹窗让你三选一。
