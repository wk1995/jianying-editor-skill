# 版本演进文档

> 记录 skill 的每一次修复和进化，为后来者提供经验参考。

---

## 📌 版本约定

- **基准版本**：上游 JianYing-Editor-Skill v1.5.0（2026-03-04）
- **分支版本**：以 v1.2.0 为起点，记录在 macOS 剪映 5.9.0 下的调试与修复
- **版本命名**：`{主版本}.{分支版本}.{修订号}`

---

## v1.2.0 - 2026-03-29（macOS 剪映 5.9+ 兼容性修复）

**开发者**：小剪 & 薛龙龙  
**测试环境**：macOS Darwin 25.1.0 + 剪映 5.9.0 + Python 3.14

### 🔧 修复的问题

#### 问题 1：macOS 草稿目录探测错误

**症状**：生成的项目路径错误，使用了 Windows fallback 路径 `C:/Users/Administrator/...`

**根因**：`get_default_drafts_root()` 只实现了 Windows 路径探测，macOS 用户无法获得正确的草稿目录。

**修复文件**：`scripts/utils/formatters.py`

```python
# 新增 macOS 路径支持
if home:
    candidates.extend([
        os.path.join(home, "Movies/JianyingPro/User Data/Projects/com.lveditor.draft"),
        os.path.join(home, "Movies/CapCut/User Data/Projects/com.lveditor.draft"),
    ])

# 根据系统选择 fallback
if sys.platform == "darwin":
    return fallback_macos
```

**经验**：跨平台路径处理必须一开始就考虑，不能依赖 Windows-only 的 fallback。

---

#### 问题 2：视频素材导入后不显示

**症状**：草稿创建成功，视频素材在 `draft_content.json` 中存在，但剪映中看不到素材。

**根因**：剪映 macOS 5.9.0 要求 `VideoMaterial.export_json()` 包含更多字段，原实现缺少：
- `has_audio` — 视频是否有音轨
- `source` — 素材来源标记（本地=0）
- `is_copyright` — 版权标记
- `extra_type_option` — 额外类型选项
- `matting` — 抠图设置
- `video_algorithm` — 视频算法参数
- `smart_motion` — 智能运动参数

**修复文件**：`scripts/vendor/pyJianYingDraft/local_materials.py`

```python
# 检测音频轨道
has_audio = False
try:
    info = pymediainfo.MediaInfo.parse(self.path)
    if len(info.audio_tracks) > 0:
        has_audio = True
except Exception:
    has_audio = True  # 保守假设有音频

# export_json 新增字段
{
    "has_audio": has_audio,
    "source": 0,  # 本地素材
    "is_copyright": False,
    "extra_type_option": 0,
    "matting": {"flag": 0, ...},
    "video_algorithm": {"algorithms": [], ...},
    "smart_motion": None,
    # ... 其他字段
}
```

**经验**：第三方库（如 pyJianYingDraft）与剪映版本的兼容性问题，只能通过对比正常草稿文件的 JSON 结构来发现差异。

---

#### 问题 3：草稿文件缺失

**症状**：创建的草稿只有 `draft_content.json` 和 `draft_meta_info.json`，缺少 `draft_info.json`，剪映无法识别项目。

**根因**：`DraftFolder.create_draft()` 只创建了 2 个文件，但剪映 macOS 5.9+ 需要至少 4 个文件：
- `draft_info.json` — 项目元数据（含分辨率、设备信息）
- `draft_content.json` — 时间线内容
- `draft_meta_info.json` — 草稿信息
- `template.tmp` — 模板二进制
- `draft_settings` — 设置文件

**修复文件**：`scripts/vendor/pyJianYingDraft/draft_folder.py`

```python
# 新增 _generate_draft_info() 函数
def _generate_draft_info(name, width, height, fps):
    """生成符合 macOS 5.9+ 的 draft_info.json"""
    return {
        "canvas_config": {"width": width, "height": height, "ratio": "original"},
        "fps": float(fps),
        "materials": { /* 完整空材料结构 */ },
        "platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",  # 硬编码为 5.9.0
            "os": "mac",
            # ... 设备信息
        },
        # ...
    }

# create_draft() 中新增
shutil.copy(draft_meta_template, draft_path + "/draft_meta_info.json")
draft_info = _generate_draft_info(draft_name, width, height, fps)
with open(draft_path + "/draft_info.json", "w") as f:
    json.dump(draft_info, f)
with open(draft_path + "/template.tmp", "wb") as f:
    f.write(b"")
with open(draft_path + "/draft_settings", "w") as f:
    f.write("")
```

**经验**：剪映草稿的文件结构在不同版本间可能变化，需要用正常草稿文件做基准对比。

---

#### 问题 4：materials 未同步

**症状**：`draft_info.json` 的 `materials` 数组为空，即使 `draft_content.json` 有素材数据。

**根因**：保存时只更新了 `draft_content.json`，没有同步更新 `draft_info.json`。

**修复文件**：`scripts/jy_wrapper.py`

```python
def save(self):
    self.script.save()
    self._sync_draft_info()  # 新增同步调用
    # ...

def _sync_draft_info(self):
    """将 draft_content 的 materials 同步到 draft_info"""
    # 读取两个文件
    # 复制 materials, tracks, duration, canvas_config
    # 写回 draft_info.json
```

**经验**：某些版本中 `draft_info.json` 和 `draft_content.json` 是双写结构，需要保持同步。

---

### 📊 调试方法论

1. **对比法**：手动在剪映中操作正常项目，保存后对比 JSON 文件结构差异。
2. **分段验证**：逐个功能测试（创建→导入→剪辑→字幕），尽早发现问题。
3. **文件追踪**：用 `stat` 记录修改时间，找到实际变化的文件。
4. **环境隔离**：测试时使用独立的测试项目名，避免污染真实项目。

---

### 🧪 测试验证清单

- [x] 空白项目创建（无素材）
- [x] 导入完整视频
- [x] `add_clip()` 精确剪辑（掐头去尾）
- [x] `add_text_simple()` 添加字幕
- [x] 草稿在剪映中正确显示所有素材
- [x] 剪辑后的时长与预期一致

---

## 📚 参考文献

- [上游 JianYing-Editor-Skill](https://github.com/luoluoluo22/jianying-editor-skill)
- [pyJianYingDraft 源码](https://github.com/Hommy-master/pyJianYingDraft)
- [剪映草稿格式讨论](https://github.com/Hommy-master/capcut-mate)

---

## 🔜 待解决问题

1. **版本兼容性问题**：当前 hardcode 了 `app_version: 5.9.0`，如果用户剪映版本不同可能有问题。
2. **Python 3.14 编译问题**：`uv sync` 会因 pydantic-core 不支持 Python 3.14 而失败，需先用 `uv pip install pydantic-core` 或使用 Docker。
3. **template.tmp 格式**：目前是空文件，可能需要是正确的 protobuf 格式才能完整工作。
