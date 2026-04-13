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

## v1.2.1 - 2026-03-29（字幕样式参数控制修复）

**开发者**：小剪 & 薛龙龙

### 🔧 核心问题：字幕样式参数不生效

**症状**：`add_text_simple()` 传入 `font_size`、`transform_y` 参数后，剪映里字幕的字号、位置没有任何变化。

**根因分析**：通过大量调试发现——

剪映读取的字幕样式来自 **两个文件**：
- `draft_content.json` — 主要时间线数据
- `draft_info.json` — **剪映实际读取的元数据**（！这个发现来之不易）

控制字幕样式的关键字段：
| 作用 | 字段路径 |
|------|---------|
| **字号** | `materials[].content.styles[0].size` |
| **缩放** | `tracks[].segments[].clip.scale.x / .y` |
| **Y位置** | `tracks[].segments[].clip.transform.y` |

**重要经验**：
- `add_text_simple()` 的 `allowed_keys` 会过滤掉 `font_size`、`transform_y`，导致参数无法透传到 TextSegment
- `pyJianYingDraft` 生成的 TextSegment 默认 `size=5.0`，`scale=1.0`，`transform.y=-0.8`
- 字幕的 Y位置换算：`display_y = transform_y × canvas_height`
  - 例如：Y=-1740，canvas=3840 → `transform_y = -1740/3840 = -0.4531`
- **剪映实际读 `draft_info.json`，不是 `draft_content.json`**

### ⚠️ 字幕样式设置注意事项

1. **字体大小**：设置 `materials[].content.styles[0].size`，非 `font_size` 字段
2. **缩放**：设置 `tracks[].segments[].clip.scale.x/y`（默认1.0）
3. **Y位置**：设置 `tracks[].segments[].clip.transform.y`
4. **必须写两个文件**：`draft_info.json` 和 `draft_content.json` 都要更新
5. **字号+缩放配合**：例如字号5 + 缩放3x = 视觉字号15

### 📐 Y位置参考换算

**经验总结**：字幕Y位置应根据视频高度自动计算，公式为：
```
y = -canvas_height / 4   # 字幕放在画面下方1/4处
transform_y = y / canvas_height = -0.25
```

| 视频高度 | Y位置（像素） | transform_y |
|---------|------------|-----------|
| 1280 | -320 | -0.25 |
| 1920 | -480 | -0.25 |
| 3840 (4K) | -960 | -0.25 |

> ⚠️ 之前错误地用 Y=-1740 作为默认值（这是4K视频的值），导致其他分辨率字幕位置错误。**正确做法是不指定Y，由系统按公式自动计算。**

---

## 🔜 待解决问题

1. **版本兼容性问题**：当前 hardcode 了 `app_version: 5.9.0`，如果用户剪映版本不同可能有问题。
2. **Python 3.14 编译问题**：`uv sync` 会因 pydantic-core 不支持 Python 3.14 而失败，需先用 `uv pip install pydantic-core` 或使用 Docker。
3. **template.tmp 格式**：目前是空文件，可能需要是正确的 protobuf 格式才能完整工作。
4. **字幕样式 API**：当前需要后置脚本修改 JSON，下一版本应在内核直接支持。

---

## v1.2.2 - 2026-03-30（BGM 添加流程完善）

**开发者**：小剪 & 薛龙龙

### 🔧 修复的问题

#### 问题 1：save() 只合并轨道不合并素材

**症状**：用 `overwrite=False` 加载草稿后添加 BGM，保存后轨道里能看到片段，但 `materials.audios` 为空，剪映里播放没有声音。

**根因**：`jy_wrapper.py` 的 `save()` 在追加模式下只合并了 `tracks`，完全遗漏了 `materials` 的合并。`new_dc = existing_dc` 直接用旧数据覆盖了包含新素材的 `new_dc`。

**修复文件**：`scripts/jy_wrapper.py` — `save()` 方法

```python
# 在 tracks 合并之后，增加 materials 的合并
for mat_type in ["audios", "videos", "images", "texts", " stickers", "effects", "filters"]:
    existing_mats = existing_dc.get("materials", {}).get(mat_type, [])
    new_mats = new_dc.get("materials", {}).get(mat_type, [])
    existing_ids = {m.get("id") for m in existing_mats}
    for m in new_mats:
        if m.get("id") not in existing_ids:
            existing_mats.append(m)
```

---

#### 问题 2：draft_info.json vs draft_content.json 混淆

**症状**：多次修改 `draft_content.json` 后剪映内容没有变化，或者出现奇怪的数据状态。

**根因**：剪映 macOS 实际读取的是 `draft_info.json`（权威文件），而 `script.save()` 写入的是 `draft_content.json`。两个文件必须保持同步，修改才生效。

**经验**：
- `draft_content.json` = pyJianYingDraft 库内部读写用的文件
- `draft_info.json` = 剪映 macOS 实际读取的权威文件
- **所有修改必须通过 `save()` 触发同步**，或者手动同步两个文件

---

#### 问题 3：AudioMaterial type 误改导致波形消失

**症状**：把 `AudioMaterial.export_json()` 中的 `type` 从 `"extract_music"` 改为 `"audio"` 后，本地音频在剪映中虽然能播放，但时间轴上完全看不见波形，无法选中操作。

**根因**：`"extract_music"` 是本地文件导入剪映后的正确类型，不是错误。随意修改 type 导致剪映无法正确渲染波形轨道。

**经验**：
- `type=extract_music` ✅ 本地导入的音乐素材（正确）
- `type=audio` ❌ 会导致波形不可见
- `type=none` ❌ 素材未正确识别

---

#### 问题 4：直接编辑草稿 JSON 导致数据损坏

**症状**：多次直接用 Python 修改 `draft_info.json` 的内容（如删除片段），导致草稿轨道数据出现孤立的片段引用（material_id 在素材列表中找不到），草稿最终损坏。

**根因**：没有完整追踪素材引用关系就手动删除，导致片段引用了不存在的素材。

**经验**：
- 永远不要手动拼接 JSON 中的片段引用关系
- 删除片段的正确做法：通过 JyProject 对象操作，然后用 `save()` 统一写入
- 至少要在内存中完整追踪引用关系后再批量写入

---

#### 问题 5：shutil.copytree 复制草稿后文件变空

**症状**：用 `shutil.copytree` 或 Finder 复制草稿时，目标目录下的 `draft_content.json` 变成 0 字节。

**根因**：macOS 的 Finder / rsync 可能用 `_` 扩展属性文件来存储元数据，直接复制会丢失这些属性，导致文件损坏。

**经验**：
```python
# Python shutil.copytree 通常更可靠
import shutil
shutil.copytree(src, dst)

# 或用 macOS 原生 ditto
import subprocess
subprocess.run(['ditto', src, dst])
```

---

### ✅ 成功验证的功能

#### 2. 读取草稿时间线结构

```python
from scripts.cloud_manager import CloudManager

cm = CloudManager()
# cm.assets 是 dict：{音乐ID: {name, url, duration_s, type, source_db, ...}}

# 搜索示例
results = [v for k, v in cm.assets.items() if '舒缓' in v.get('name', '')]
for r in results[:10]:
    print(f'{r["name"]} ({r["duration_s"]}s)')
```

**可用搜索关键词**：舒缓、钢琴、爵士、励志、VLOG、轻快、安静、唯美、治愈

---

### ⚠️ 添加 BGM 的已知限制

**手动授权不可避免**：通过 API 添加的云端音乐，剪映首次打开时会显示"暂无权限"，需要用户在草稿里点一次允许访问。这是剪映的权限机制，无法通过 API 绕过。

**解决方案**：用户只需在剪映里点一次"允许"，之后该草稿就能正常用 API 继续编辑了。

---

### 📋 v1.2.2 操作检查清单

- [x] 加载已有草稿（overwrite=False）
- [x] 添加视频到 VideoTrack
- [x] 获取视频时长
- [x] 从云素材库添加 BGM
- [x] 设置 BGM 音量
- [x] 保存草稿（自动同步两个 JSON）
- [ ] 剪映中手动允许访问云素材（一次性）

---

## v1.2.3 - 2026-03-30（画中画 + 缩放关键帧）

**开发者**：小剪 & 薛龙龙

### 🔧 修复的问题

#### 问题 1：VideoTrack_2 轨道不存在导致画中画添加失败

**症状**：`add_media_safe` 报错 "NoneType has no attribute 'segments'"。

**根因**：`add_media_safe` 调用 `add_track(name)` 创建轨道，但创建的轨道不在 `script.tracks` 里。`get_track` 找不到轨道时返回 `None`，调用 `None.segments` 报错。

**经验**：
- 通过 `imported_tracks` 找轨道（已有草稿的轨道在 imported_tracks 里）
- 直接用 Python 操作 draft_info.json 来添加片段和轨道

---

#### 问题 2：duration 参数传字符串导致崩溃

**症状**：`ValueError: could not convert string to float: '106767000us'`

**根因**：`safe_tim()` 函数不认 "us" 后缀，只认 "s" / "ms" / "us" 的数字形式。`f'{video_dur}us'` 拼出了 "106767000us" 这样的错误字符串。

**经验**：
```python
# ✅ 正确：直接传整数（微秒）
p.add_media_safe(path, start_time=0, duration=106767000, track_name='VideoTrack_2')

# ❌ 错误
p.add_media_safe(path, start_time='0s', duration='106767000us', ...)
```

---

#### 问题 3：缩放关键帧 time_offset 用绝对时间

**症状**：只有第一张照片有缩放效果，第2-4张照片的关键帧没生效。

**根因**：`time_offset` 设置的是相对于整条时间线的绝对时间，但剪映要求是**相对于当前片段起点的相对时间**。第2张照片起点在5秒，关键帧设在10秒处（绝对），但片段只有5秒长，所以超出部分被忽略。

**正确格式**：
```python
{
  'property_type': 'KFTypeScaleX',   # 注意是"KFTypeScaleX"不是"UNIFORM_SCALE"
  'keyframe_list': [
    {'time_offset': 0,        'values': [1.0]},   # 片段起点 = 相对0
    {'time_offset': 5000000,  'values': [1.5]}   # 片段终点 = 5秒（微秒）
  ]
}
```

---

#### 问题 4：直接操作草稿 JSON 导致轨道重复

**症状**：多次用 `script.tracks[track_name] = track` 添加轨道，导致同一轨道出现多次。

**经验**：操作 draft_info.json 时要完整重建轨道列表，不要只追加。

---

### ✅ 成功验证的功能

#### 1. 读取草稿时间线结构

```python
import json

draft_dir = '/path/to/草稿'
with open(f'{draft_dir}/draft_info.json') as f:
    d = json.load(f)

for t in d.get('tracks', []):
    print(f'{t.get("name")} ({t.get("type")}): {len(t.get("segments", []))} 片段')
    for seg in t.get('segments', []):
        tr = seg.get('target_timerange', {})
        start = tr.get('start', 0) / 1000000
        dur = tr.get('duration', 0) / 1000000
        print(f'  {start:.2f}s - {start+dur:.2f}s')
```

---

#### 3. 修改画布比例

```python
import json

draft_dir = '/path/to/草稿'
with open(f'{draft_dir}/draft_info.json') as f:
    d = json.load(f)

# 9:16 竖屏
d['canvas_config'] = {
    'width': 1080,
    'height': 1920,
    'ratio': '9:16'
}

# 或 16:9 横屏
d['canvas_config'] = {
    'width': 1920,
    'height': 1080,
    'ratio': '16:9'
}

with open(f'{draft_dir}/draft_info.json', 'w') as f:
    json.dump(d, f, ensure_ascii=False, indent=4)
```

**⚠️ 注意**：修改画布比例后，现有片段可能变形，需重新调整。

---

### 📋 v1.2.3 操作检查清单

- [x] 加载已有草稿（overwrite=False）
- [x] 添加主视频到 VideoTrack
- [x] 获取视频时长（微秒）
- [x] 添加画中画照片到 VideoTrack_2
- [x] 多张照片分时段排列（每段5秒）
- [x] 添加缩放关键帧（1.0x → 1.5x）
- [x] 修改画布比例为 9:16

---

## v1.2.4 - 2026-04-07（字体批量修改 + 单行部分文字样式修改）

**开发者**：小剪 & 薛龙龙
**测试环境**：macOS Darwin 25.1.0 + 剪映 5.9.0 + Python 3.14

### ✅ 新功能验证：批量修改所有字幕字体

#### 问题：字体设置不生效

**症状**：`add_text_simple()` 传入字体名称后，打开剪映所有字幕字体还是默认字体，不生效。

**根因**：
- 错误做法：直接传字符串 `font="新青年体"`，API 需要 `FontType` 枚举实例
- 正确做法：从 `FontType` 枚举中通过 `getattr` 获取字体对象传入
- 枚举名称转换：显示名称 `新青年体` → 枚举成员名 `新青年体`（无需转换，直接 getattr）

**正确代码示例**：
```python
from pyJianYingDraft.metadata.font_meta import FontType

# 获取字体枚举
FONT_NAME = "新青年体"
font_enum = getattr(FontType, FONT_NAME.replace(" ", "_"))

# 添加字幕
project.add_text_simple(
    line['text'],
    start_time=start_str,
    duration=dur_str,
    font=font_enum,  # 正确！这里需要枚举实例，不能传字符串
    font_size=5.0,
    track_name="Subtitle Track"
)

# 统一设置缩放和位置（内置方法，自动换算像素→相对坐标）
project.set_subtitle_style(
    font_size=5.0,
    scale=3.0,
    x=0.0,      # X坐标，像素
    y=-1700.0   # Y坐标，像素
)

project.save()
```

**经验**：
- 必须传入 `FontType` 枚举实例，不支持直接传字体名称字符串
- `jy_wrapper` 内置 `set_subtitle_style()` 方法已经支持像素坐标直接输入，内部自动换算成剪映要求的相对坐标
- 所有修改都在 `save()` 时自动同步到 `draft_info.json`，无需手动同步

---

### ✅ 新功能验证：单行内部分文字独立样式（修改字号/颜色）

#### 使用场景
需要给一行字幕中的**几个字**单独修改字号、颜色，实现高亮效果。

#### JSON 数据结构
剪映使用 `content.styles` 数组来存储多行样式，每个 `style` 有 `range` 字段指定覆盖的文字范围：
```json
{
  "text": "来找我咨询JY人",
  "styles": [
    {
      "fill": {"content": {"solid": {"color": [1, 1, 1]}}},
      "range": [0, 3],   // "来找我"
      "size": 5.0,
      // ... 其他属性
    },
    {
      "fill": {"content": {"solid": {"color": [1, 0, 0]}}},
      "range": [3, 5],   // "咨询" → 两个字
      "size": 9.0,       // 字号放大到 9
      "useLetterColor": true
    },
    {
      "fill": {"content": {"solid": {"color": [1, 1, 1]}}},
      "range": [5, 8],   // "JY人"
      "size": 5.0
    }
  ]
}
```

#### 关键规则：
1. `range` 是 `[start_index, end_index]`，**左闭右开**，按 UTF-16 字符索引计算
   - 中文一个字占一个索引，英文每个字母一个索引
   - 例如：`"来找我咨询JY人"` 长度是 8
   - "咨询"两个字在索引 `[3, 5]`

2. **颜色值**：
   - RGB 每个通道归一化到 `[0.0, 1.0]`
   - 例如：`#ff0000` 红色 → `[1.0, 0.0, 0.0]`
   - 例如：`#ffbe4b` 暖黄色 → `[1.0, 0.745, 0.294]`

3. **完整修改流程（手动修改草稿）**：
```python
import json

# 1. 读取 draft_info.json
with open(draft_info_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 2. 找到对应字幕素材
for text_mat in data['materials']['texts']:
    if text_mat['id'] == target_material_id:
        content = json.loads(text_mat['content'])  # content 是 JSON 字符串
        text = content['text']
        original_style = content['styles'][0]
        
        # 3. 拆分多个 style 段
        new_styles = []
        # 前半段（未修改）
        before = original_style.copy()
        before['range'] = [0, 3]
        new_styles.append(before)
        # 中间修改段
        modified = original_style.copy()
        modified['range'] = [3, 5]
        modified['size'] = 9.0  # 修改字号
        modified['fill'] = {   # 修改颜色
            'alpha': 1.0,
            'content': {
                'render_type': 'solid',
                'solid': {
                    'alpha': 1.0,
                    'color': [1.0, 0.0, 0.0]
                }
            }
        }
        modified['useLetterColor'] = True
        new_styles.append(modified)
        # 后半段（未修改）
        after = original_style.copy()
        after['range'] = [5, len(text)]
        new_styles.append(after)
        
        # 4. 更新并写回
        content['styles'] = new_styles
        text_mat['content'] = json.dumps(content, ensure_ascii=False)
        break

# 5. 保存文件
with open(draft_info_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
```

---

### 📋 v1.2.4 操作检查清单

- [x] 批量修改所有字幕字体（新青年体、思源粗宋等）
- [x] 统一设置字幕缩放和位置（像素坐标输入，自动换算）
- [x] 单行字幕部分文字独立字号修改验证
- [x] 单行字幕部分文字独立颜色修改验证
- [x] 修改后剪映正确读取并显示，无数据损坏

---

## 📅 v1.3.0 字幕动画（2026-04-13）

### 重大发现：字幕动效的正确写入格式

**问题：** 想批量给字幕添加打字机/吸入等动效，但剪映不认。

**根因：** Jianying 有两个文件 `draft_content.json` 和 `draft_info.json`，实际读取的是 `draft_info.json`。

### 正确的字幕动效格式

给字幕添加动效需要同时修改 `draft_info.json` 的两处：

**1. 在 `materials.material_animations` 中添加动画条目：**
```json
{
  "id": "UUID格式的引用ID",
  "multi_language_current": "none",
  "type": "sticker_animation",
  "animations": [{
    "anim_adjust_params": null,
    "category_id": "ruchang",
    "category_name": "入场",
    "duration": 500000,
    "id": "动画类型ID",
    "material_type": "sticker",
    "name": "效果名称",
    "panel": "",
    "path": "/Users/long/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/{animation_id}/{path_hash}",
    "platform": "all",
    "request_id": "",
    "resource_id": "资源ID",
    "start": 0,
    "type": "in"
  }]
}
```

**2. 在对应字幕段落的 `extra_material_refs` 中添加引用：**
```json
{
  "segments": [{
    "id": "段落UUID",
    "material_id": "素材UUID",
    "extra_material_refs": ["UUID引用ID"],  // ← 添加这里
    "clip": { ... }
  }]
}
```

### 动画参数三要素（缺一不可）

| 参数 | 说明 | 示例 |
|------|------|------|
| `id` | 动画类型ID，决定效果种类 | `1644275` (打字机) |
| `resource_id` | 资源ID，Jianying下载时生成 | `6724920249654710791` |
| `path` | 本地缓存路径，包含hash | `.../effect/1644275/0dc90e490f15d6bac5fd1d778e501917` |

### 14种验证过的字幕动效参数

| 动效名称 | animation_id | resource_id | path_hash |
|---------|-------------|------------|-----------|
| 吸入 | `3576973` | `7120438380453696031` | `bd8a769d9a57b1ae916a88e35feece27` |
| 放大 | `1644264` | `6724919499042066958` | `e694f4c17470423f93efd621e99f7a45` |
| 打字机 | `1644275` | `6724920249654710791` | `0dc90e490f15d6bac5fd1d778e501917` |
| 水平翻转 | `1644340` | `7051512227353858590` | `70a0e248370c0701d52c0102808717ac` |
| 扭曲模糊 | `1722114` | `7089261793406620197` | `b604b7cd821a1ba28aabf217c9bfcf31` |
| 闪动 | `1644322` | `7035902226602136071` | `0ee8140d83447478b1011e2b1341ccd7` |
| 向上翻转 | `8945307` | `7194703971498332727` | `a52cc0d9590790f8408fa1daf79c05f3` |
| 复古打字机 | `17639720` | `7253888335163167291` | `190be08db8fb94ab4f6286a6cce7ecf1` |
| 缩小 | `1644263` | `6724921217721045515` | `598b8d652143c644edc95d67d67b37ee` |
| 日出 | `1644269` | `6779084126457696776` | `eba8d27e99beab7421ef4bf3c6628094` |
| 向右露出 | `5925714` | `7163514730525495839` | `15c385bc3346b485754622a112d54d00` |
| 向左露出 | `5925715` | `7163514612690719269` | `698227e23131cc83a920782ccb1f8fdb` |
| 收拢 | `1644261` | `6779879712261935619` | `a1dc7a08db7479c4499c405a0889919d` |
| 渐显 | `1644304` | `6724916044072227332` | `8aad5add2c87ca5154b841b00f890479` |

**path格式：** `/Users/long/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/{animation_id}/{path_hash}`

### 自动添加字幕动效的Python代码

```python
import json
import uuid

def add_text_animation(draft_info_path, target_material_ids, animation_config):
    """
    给指定字幕添加动效
    
    animation_config = {
        "name": "打字机",
        "id": "1644275",
        "resource_id": "6724920249654710791",
        "path_hash": "0dc90e490f15d6bac5fd1d778e501917"
    }
    """
    with open(draft_info_path, 'r') as f:
        info = json.load(f)
    
    # 1. 创建动画条目
    anim_ref_id = str(uuid.uuid4()).upper()
    anim_entry = {
        "id": anim_ref_id,
        "multi_language_current": "none",
        "type": "sticker_animation",
        "animations": [{
            "anim_adjust_params": None,
            "category_id": "ruchang",
            "category_name": "入场",
            "duration": 500000,
            "id": animation_config["id"],
            "material_type": "sticker",
            "name": animation_config["name"],
            "panel": "",
            "path": f"/Users/long/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/{animation_config['id']}/{animation_config['path_hash']}",
            "platform": "all",
            "request_id": "",
            "resource_id": animation_config["resource_id"],
            "start": 0,
            "type": "in"
        }]
    }
    
    # 2. 添加到 material_animations
    info['materials'].setdefault('material_animations', []).append(anim_entry)
    
    # 3. 找到对应段落，添加引用
    for track in info.get('tracks', []):
        if track.get('type') == 'text':
            for seg in track.get('segments', []):
                if seg.get('material_id') in target_material_ids:
                    refs = seg.get('extra_material_refs', [])
                    refs.append(anim_ref_id)
                    seg['extra_material_refs'] = refs
    
    # 4. 保存
    with open(draft_info_path, 'w') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已添加 {animation_config['name']} 到 {len(target_material_ids)} 个字幕")
```

### 批量给所有字幕添加同一动效

```python
# 收集所有字幕的 material_id
all_text_ids = []
for track in info.get('tracks', []):
    if track.get('type') == 'text':
        for seg in track.get('segments', []):
            all_text_ids.append(seg.get('material_id'))

# 添加打字机效果
add_text_animation(draft_info_path, all_text_ids, {
    "name": "打字机",
    "id": "1644275",
    "resource_id": "6724920249654710791",
    "path_hash": "0dc90e490f15d6bac5fd1d778e501917"
})
```

### 不同字幕不同动效

```python
# 为不同字幕配置不同动效
subtitle_animation_map = [
    ("你发现没有", "水平翻转", "1644340", "7051512227353858590", "70a0e248370c0701d52c0102808717ac"),
    ("很多时候", "扭曲模糊", "1722114", "7089261793406620197", "b604b7cd821a1ba28aabf217c9bfcf31"),
    # ... 更多
]

for text, name, anim_id, res_id, path_hash in subtitle_animation_map:
    # 找到这个字幕的 material_id
    target_id = None
    for t in info.get('materials', {}).get('texts', []):
        if json.loads(t.get('content', '{}')).get('text') == text:
            target_id = t['id']
            break
    
    if target_id:
        add_text_animation(draft_info_path, [target_id], {
            "name": name, "id": anim_id, "resource_id": res_id, "path_hash": path_hash
        })
```

### 版本演进记录

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v1.3.0 | 2026-04-13 | **新增：** 字幕动效添加完整指南，14种动效参数，正确的三要素格式 |

