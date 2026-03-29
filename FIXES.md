# 修复记录 - macOS 剪映 5.9+ 兼容性

**修复日期：** 2026-03-29
**修复人：** 小剪 + 薛龙龙
**适用版本：** 剪映 macOS 5.9.0+

---

## 🔧 修复内容

### 1. macOS 草稿目录自动探测
**文件：** `scripts/utils/formatters.py`

**问题：** `get_default_drafts_root()` 只支持 Windows 路径，macOS 用户会使用错误的 fallback 路径。

**修复：** 添加 macOS 路径探测支持。
```python
# macOS 路径
if home:
    candidates.extend([
        os.path.join(home, "Movies/JianyingPro/User Data/Projects/com.lveditor.draft"),
        os.path.join(home, "Movies/CapCut/User Data/Projects/com.lveditor.draft"),
    ])
```

---

### 2. VideoMaterial 导出字段缺失
**文件：** `scripts/vendor/pyJianYingDraft/local_materials.py`

**问题：** `export_json()` 缺少剪映 macOS 5.9+ 需要的必填字段，导致素材添加后剪映无法识别。

**修复：** 添加完整字段，特别是：
- `has_audio: bool` — 自动检测视频是否有音轨
- `source: 0` — 本地素材标记
- `is_copyright: false`
- `extra_type_option: 0`
- `matting: {...}`
- `video_algorithm: {...}`
- `smart_motion: None`
- 等其他 macOS 5.9+ 必填字段

---

### 3. 草稿文件缺失
**文件：** `scripts/vendor/pyJianYingDraft/draft_folder.py`

**问题：** `create_draft()` 只创建 `draft_meta_info.json` 和 `draft_content.json`，但剪映 macOS 5.9+ 还需要 `draft_info.json`、`template.tmp`、`draft_settings`。

**修复：** 在 `create_draft()` 中新增：
- 生成完整的 `draft_info.json`（包含 canvas_config、设备信息、平台信息等）
- 创建空的 `template.tmp`
- 创建 `draft_settings`

同时新增 `_generate_draft_info()` 函数，生成符合 macOS 5.9.0 规范的 draft_info 结构。

---

### 4. materials 未同步到 draft_info.json
**文件：** `scripts/jy_wrapper.py`

**问题：** 保存时 `draft_content.json` 有素材数据，但 `draft_info.json` 的 `materials` 是空的，导致剪映读取失败。

**修复：** 在 `save()` 中新增 `_sync_draft_info()` 调用，在保存时将 `draft_content.json` 的完整 materials 数组同步到 `draft_info.json`，同时同步：
- `tracks` 轨道数据
- `duration` 时长
- `canvas_config` 分辨率

---

## 📋 迁移检查清单

在新机器上部署 skill 时，确保执行以下步骤：

### 1. 安装依赖
```bash
pip install --break-system-packages -r requirements.txt
```

**注意：** macOS 需要加 `--break-system-packages`（因为 Python 3.14+ 受 PEP 668 限制）。

### 2. 依赖列表
- `pymediainfo` — 视频元数据解析
- `uiautomation` — UI 自动化（Windows）
- `playwright` — 浏览器自动化
- `pynput` — 键盘鼠标控制
- `edge-tts` — 微软 TTS 配音
- `opencv-python` — 视频处理
- `numpy` — 数值计算
- `imageio` — 图像处理
- `psutil` — 系统工具
- `requests` — HTTP 请求
- `websockets` — WebSocket

### 3. 剪映路径（macOS）
确保剪映项目目录存在：
```bash
~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft
```

### 4. Python 版本
推荐 **Python 3.11+**，实测 **Python 3.14** 可用（需要 pydantic-core 预编译 wheel）。

---

## ✅ 测试验证

### 测试 1：创建空白项目
```python
from jy_wrapper import JyProject
project = JyProject("测试", overwrite=True)
project.save()
# 打开剪映应能看到"测试"项目
```

### 测试 2：导入视频+剪辑
```python
project = JyProject("剪辑测试", overwrite=True, width=2160, height=3840)
project.add_clip("/path/to/video.mp4", source_start="6s", duration="155s", target_start="0s")
project.save()
# 打开剪映，项目应有 155 秒视频轨道
```

### 测试 3：添加字幕
```python
project.add_text_simple("标题文字", start_time="0s", duration="5s", transform_y=-0.6)
project.save()
# 打开剪映，应看到字幕轨道
```

---

## 🐛 已知问题

1. **Python 3.14 编译问题：** 直接 `uv sync` 会失败（pydantic-core 不支持），需要先手动 `uv pip install pydantic-core` 或使用 Docker 部署。
2. **CRLF 行尾符：** 原始仓库使用 Windows CRLF，已在本次修复中统一为 LF。
