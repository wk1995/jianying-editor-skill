# JianYing Editor Skill - 完整使用手册

> **一句话：** 让 AI 帮你全自动在剪映里拼好时间轴，生成草稿，你只需要打开剪映继续微调，最后导出就行。

---

## 📋 目录

- [能做什么](#-能做什么)
- [不能做什么](#-不能做什么)
- [快速开始](#-快速开始)
  - [安装](#安装)
  - [第一个示例](#第一个示例)
- [核心功能用法](#-核心功能用法)
  - [视频剪辑](#视频剪辑)
  - [字幕添加](#字幕添加)
  - [字体设置](#字体设置)
  - [缩放与位置](#缩放与位置)
  - [单行部分文字样式修改](#单行部分文字样式修改)
  - [添加 BGM](#添加-bgm)
  - [关键帧动画](#关键帧动画)
  - [画中画](#画中画)
- [重要经验](#️-重要经验)
  - [两个文件：draft_info.json vs draft_content.json](#两个文件-draft_infojson-vs-draft_contentjson)
  - [overwrite=True 风险](#overwritetrue-风险)
  - [常见错误](#常见错误)
- [故障排查](#-故障排查)
- [版本演进](#-版本演进)

---

## 🎯 能做什么

| 功能 | 说明 |
|------|------|
| **素材导入** | 视频、音频、图片自动导入到时间轴 |
| **AI 配音** | 文案→语音，支持剪映原生音色和微软TTS |
| **字幕生成** | 根据配音自动对齐时间轴 |
| **批量字体修改** | 所有字幕一键改字体 |
| **单行部分样式** | 一行里几个字单独改字号/颜色（做高亮） |
| **自动配乐** | 本地/云端音乐自动添加 |
| **特效/转场/滤镜** | 按名字搜索，一键应用 |
| **网页动效转视频** | HTML/JS/Canvas → 剪映视频素材 |
| **录屏 + 智能变焦** | 录屏自动给鼠标位置加缩放+红圈 |
| **影视解说** | AI分析视频→生成解说脚本→合成视频 |
| **自动导出** | 剪完一键导出 MP4（支持 1080P/4K） |
| **关键帧动画** | 缩放/位移/透明度关键帧 |
| **复合片段** | 嵌套工程组合 |

---

## ❌ 不能做什么

- ❌ 不是剪映替代品，剪映负责最终渲染和预览
- ❌ 不能用剪映GPU实时特效（智能抠图、美颜等）
- ❌ 不能操作剪映全部UI按钮（一键成片这类AI功能）
- ❌ 自动导出只支持剪映 **5.9及以下版本**（新版本弹窗太多干扰自动化）
- ❌ 只支持桌面版剪映，不支持手机端

---

## 🚀 快速开始

### 安装

**Windows 用户一键安装：**
```powershell
irm is.gd/rpb65M | iex
```

**Trae IDE 手动安装：**
```bash
git clone https://github.com/luoluoluo22/jianying-editor-skill.git .trae/skills/jianying-editor
```

**安装 Python 依赖：**
```bash
cd .trae/skills/jianying-editor
pip install -r requirements.txt
playwright install chromium  # 网页转视频功能需要
```

**下载剪映：**
- [剪映专业版 5.9 (夸克网盘)](https://pan.quark.cn/s/81566e9c6e08)
- 下载后禁止自动更新

---

### 第一个示例

```python
import os
import sys

# 1. 环境初始化（必须放在脚本开头）
current_dir = os.path.dirname(os.path.abspath(__file__))
env_root = os.getenv("JY_SKILL_ROOT", "").strip()
# 自动探测 Skill 路径
skill_root = next((p for p in [
    env_root,
    os.path.join(current_dir, ".agent", "skills", "jianying-editor"),
    os.path.join(current_dir, ".trae", "skills", "jianying-editor"),
    os.path.join(current_dir, ".claude", "skills", "jianying-editor"),
    os.path.join(current_dir, "skills", "jianying-editor"),
    os.path.abspath(".agent/skills/jianying-editor"),
    os.path.abspath(".trae/skills/jianying-editor"),
    os.path.abspath(".claude/skills/jianying-editor"),
] if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py"))), None)

if not skill_root: raise ImportError("Could not find jianying-editor skill root.")
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject
from pyJianYingDraft.metadata.font_meta import FontType

if __name__ == "__main__":
    # 2. 创建项目（竖屏 2160x3840）
    # ⚠️  新建项目用 overwrite=True，加载已有项目用 overwrite=False
    project = JyProject("我的第一个项目", overwrite=True, width=2160, height=3840)
    
    # 3. 添加视频（从第0秒开始，切出前30秒）
    project.add_clip(
        "/path/to/your/video.mp4",
        source_start="0s",
        duration="30s",
        target_start="0s"
    )
    
    # 4. 添加字幕，设置字体为新青年体
    font = getattr(FontType, "新青年体")
    project.add_text_simple(
        "大家好，欢迎观看",
        start_time="0s",
        duration="3s",
        font=font,
        font_size=5.0
    )
    
    # 5. 统一设置字幕缩放和位置（像素直接输入，自动换算）
    project.set_subtitle_style(
        font_size=5.0,
        scale=3.0,      # 3倍放大
        x=0.0,          # X像素，0=水平居中
        y=-1700.0       # Y像素，-1700向下移
    )
    
    # 6. 保存（自动同步两个JSON文件）
    project.save()
```

> 📌 **脚本存放位置规范：** 禁止在 Skill 目录放业务脚本，请放在你的项目目录。这样 Skill 升级不会覆盖你的代码。

---

## 🔧 核心功能用法

### 视频剪辑

**精确剪辑（从原视频切一段放到时间轴）：**
```python
project.add_clip(
    "/path/to/video.mp4",    # 原视频路径
    source_start="1.3s",     # 从原视频哪里开始切
    duration="3.8s",         # 切多长
    target_start="0s",       # 放到时间轴哪里开始
    track_name="Video Track" # 轨道名称
)
```

**要点：**
- `source_start`: **原视频**的起始时间
- `target_start`: **时间线**的起始位置
- 多段剪辑要手动递增 `target_start` 避免重叠
```python
current_target = 0.0
for seg in keep_segments:
    project.add_clip(..., target_start=current_target, ...)
    current_target += seg['duration']
```

---

### 字幕添加

**添加简单字幕：**
```python
project.add_text_simple(
    "字幕文字",
    start_time="1.0s",  # 开始时间
    duration="2.5s",    # 持续时长
    font=font_enum,     # 字体（枚举实例）
    font_size=5.0,      # 基础字号
    track_name="Subtitle Track"
)
```

---

### 字体设置

**错误做法（不生效）：**
```python
# ❌ 直接传字符串不生效
project.add_text_simple(..., font="新青年体")
```

**正确做法：**
```python
# ✅ 必须从 FontType 获取枚举实例
from pyJianYingDraft.metadata.font_meta import FontType
FONT_NAME = "新青年体"
font_enum = getattr(FontType, FONT_NAME.replace(" ", "_"))

project.add_text_simple(..., font=font_enum)
```

**常见字体获取：**
```python
font_siyuan_cusong = getattr(FontType, "思源粗宋")  # 思源粗宋
font_xinqingnian = getattr(FontType, "新青年体")      # 新青年体
font_source_han_sans = getattr(FontType, "源ノ角ゴシック")  # 思源黑体（官方名）
```

---

### 缩放与位置

**使用内置方法（推荐，自动换算）：**
```python
# 用户给的是像素坐标，直接传进去就行
project.set_subtitle_style(
    font_size=5.0,   # 基础字号
    scale=3.0,       # 缩放倍数 → 3x 放大
    x=0.0,           # X位置（像素），0 = 水平居中
    y=-1700.0        # Y位置（像素），负数向下移动
)
```

**换算公式（内置方法已经帮你做了）：**
```
transform_y = y_pixel / canvas_height
transform_x = x_pixel / canvas_width
```

**示例：2160x3840 竖屏**
- Y=-1700像素 → transform_y = -1700 / 3840 ≈ -0.4427

---

### 单行部分文字样式修改

**场景：** 给一行字幕里几个字单独改字号/颜色做高亮。

**数据结构：**
```json
{
  "text": "来找我咨询JY人",
  "styles": [
    {
      "range": [0, 3],      // 文字范围：左闭右开，索引从0开始
      "size": 5.0,          // 字号
      "fill": {             // 颜色
        "content": {
          "solid": {
            "color": [1, 1, 1]  // RGB 归一化 [0-1]
          }
        }
      }
    },
    {
      "range": [3, 5],      // "咨询"两个字
      "size": 9.0,          // 字号放大到 9
      "fill": {
        "content": {
          "solid": {
            "color": [1, 0, 0]  // 红色 #ff0000
          }
        }
      },
      "useLetterColor": true
    }
  ]
}
```

**完整修改代码：**
```python
import json

# 读取草稿
draft_info_path = "/Users/long/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/项目名/draft_info.json"
with open(draft_info_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 找到第二行字幕素材
target_material_id = "..."  # 从 segments 找 material_id
for text_mat in data['materials']['texts']:
    if text_mat['id'] == target_material_id:
        content = json.loads(text_mat['content'])  # content 是 JSON 字符串
        text = content['text']
        original_style = content['styles'][0]
        
        # 拆分三段：前 + 修改 + 后
        new_styles = []
        
        # 前半段：0-3
        before = original_style.copy()
        before['range'] = [0, 3]
        new_styles.append(before)
        
        # 修改段：3-5（"咨询"）
        modified = original_style.copy()
        modified['range'] = [3, 5]
        modified['size'] = 9.0  # 字号9
        # 颜色：红色 #ff0000
        modified['fill'] = {
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
        
        # 后半段：5到结尾
        after = original_style.copy()
        after['range'] = [5, len(text)]
        new_styles.append(after)
        
        # 更新
        content['styles'] = new_styles
        text_mat['content'] = json.dumps(content, ensure_ascii=False)
        break

# 保存
with open(draft_info_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
```

**颜色转换速查表：**
| 十六进制 | RGB 归一化 |
|---------|-----------|
| #ffffff | [1, 1, 1] |
| #ff0000 | [1, 0, 0] |
| #00ff00 | [0, 1, 0] |
| #0000ff | [0, 0, 1] |
| #ffbe4b | [1, 0.745, 0.294] |

---

### 添加 BGM

**本地音频：**
```python
project.add_audio_safe("/path/to/music.mp3", start_time="0s")
```

**云端音乐：**
```python
# 搜索关键词找到音乐ID，然后添加
from scripts.cloud_manager import CloudManager
cm = CloudManager()
results = [v for k, v in cm.assets.items() if '舒缓' in v.get('name', '')]
project.add_cloud_music(results[0]['id'], start_time="0s")
```

**⚠️ 重要：**
- 云端音乐添加后，剪映第一次打开需要手动点"允许访问"
- 这是剪映权限机制，无法绕过，点一次就好了

---

### 关键帧动画

**示例：5秒内从 1.0x 放大到 1.5x**
```python
seg = text_segment  # 你的片段
seg.add_keyframe_scale(
    time_offset=0,           # 相对片段起点的时间（微秒）
    value=1.0
)
seg.add_keyframe_scale(
    time_offset=5000000,    # 5秒 = 5,000,000 微秒
    value=1.5
)
```

**要点：**
- `time_offset` 是相对于**片段起点**的时间，不是绝对时间
- 单位是微秒（1秒 = 1,000,000 微秒）

---

### 画中画

**添加到第二轨道：**
```python
project.add_clip(
    "/path/to/picture.png",
    source_start="0s",
    duration="5s",
    target_start="0s",
    track_name="Video Track 2"
)
```

---

## ⚠️ 重要经验

### 两个文件：`draft_info.json` vs `draft_content.json`

| 文件 | 作用 |
|------|------|
| `draft_content.json` | pyJianYingDraft 库内部读写使用 |
| `draft_info.json` | **剪映 macOS 实际读取的权威文件** ✅ |

**教训：**
- 修改后必须通过 `project.save()` 触发同步，保证两个文件一致
- 直接改 `draft_content.json` 剪映看不到变化

---

### `overwrite=True` 风险

| 用法 | 正确/错误 |
|-----|---------|
| **新建项目** | `overwrite=True` ✅ |
| **加载已有项目修改** | `overwrite=False` ✅ |
| **加载已有项目用 `overwrite=True`** | ❌ 会清空整个项目，数据丢失！ |

**备份重要草稿：**
```python
import shutil
draft_path = "/path/to/your/draft"
backup_path = f"{draft_path}_backup_20260407"
shutil.copytree(draft_path, backup_path)
print(f"已备份到: {backup_path}")
```

---

### 常见错误

| 症状 | 根因 | 修复 |
|------|------|------|
| 生成的项目剪映看不到 | 缺少 `draft_info.json` | 已在 v1.2.0 修复 |
| 视频素材导入后不显示 | 缺少 `has_audio` `source` 等必填字段 | 已在 v1.2.0 修复 |
| 添加了 BGM 但保存后看不到 | save() 只合并轨道没合并素材 | 已在 v1.2.2 修复 |
| 字体设置不生效 | 直接传字符串，API 需要枚举实例 | 用 `getattr(FontType, name)` 获取 ✅ |
| Y位置改了没变化 | 直接传像素，剪映要相对坐标 | 用 `set_subtitle_style()` 自动换算 ✅ |
| 音频能播放但看不到波形 | 把 `type` 从 `extract_music` 改成 `audio` | 改回 `extract_music` ✅ |
| 草稿损坏：片段引用了不存在的素材 | 手动删片段没处理引用关系 | 通过 JyProject API 操作，不要直接删 JSON |

---

## 🔍 故障排查

### 问题：看不到新生成的草稿
**解决：** 剪映不会实时刷新，重启剪映，或者点进一个旧草稿再退出来就行。

### 问题：自动导出失败
**解决：**
1. 确认你用的是剪映 **5.9 或更早版本**
2. 运行导出时不要动鼠标键盘
3. 检查路径是否正确

### 问题：所有片段都显示开头的内容
**根因：** `source_start` 和 `target_start` 搞反了
**修复：**
- `source_start` = 原视频从哪开始切
- `target_start` = 时间线放哪里
- 多段剪辑必须递增 `target_start`

---

## 🎬 字幕动效添加（v1.3.0 新增）

### 核心概念：三要素

给字幕添加动效需要三个参数**同时正确**：

| 参数 | 作用 | 示例 |
|------|------|------|
| `animation_id` | 决定效果种类 | `1644275` → 打字机 |
| `resource_id` | 资源文件标识 | `6724920249654710791` |
| `path` | 本地缓存路径（含hash） | `.../effect/1644275/0dc90e490f...` |

**任意一个不对，动效就不生效。**

---

### 操作对象：draft_info.json（不是 draft_content.json！）

Jianying 项目有两个文件：
- `draft_info.json` — **实际读取的主文件**
- `draft_content.json` — 辅助文件

**所有字幕和动效操作都只修改 `draft_info.json`。**

---

### 操作两处

**第1处：** `info['materials']['material_animations']` — 创建动画数据条目

```python
import uuid

anim_ref_id = str(uuid.uuid4()).upper()  # 引用ID

anim_entry = {
    "id": anim_ref_id,
    "multi_language_current": "none",
    "type": "sticker_animation",
    "animations": [{
        "anim_adjust_params": None,
        "category_id": "ruchang",
        "category_name": "入场",
        "duration": 500000,
        "id": "1644275",           # ← animation_id
        "material_type": "sticker",
        "name": "打字机",
        "panel": "",
        "path": "/Users/long/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/1644275/0dc90e490f15d6bac5fd1d778e501917",  # ← path（含hash）
        "platform": "all",
        "request_id": "",
        "resource_id": "6724920249654710791",  # ← resource_id
        "start": 0,
        "type": "in"
    }]
}

info['materials'].setdefault('material_animations', []).append(anim_entry)
```

**第2处：** `info['tracks'][text_track]['segments'][i]['extra_material_refs']` — 段落引用

```python
for track in info.get('tracks', []):
    if track.get('type') == 'text':
        for seg in track.get('segments', []):
            if seg.get('material_id') == target_material_id:
                # ⚠️ 用赋值，不是追加！否则 extra_material_refs 为空的字幕无法引用
                seg['extra_material_refs'] = [anim_ref_id]
                break
```

---

### 14种已验证的动效参数

| 动效 | animation_id | resource_id | path_hash |
|------|-------------|------------|-----------|
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

**path =** `/Users/long/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/{animation_id}/{path_hash}`

---

### 快速添加：所有字幕同一动效

```python
import json
import uuid

DRAFT_INFO = "/path/to/your/project/draft_info.json"
ANIMATION = {
    "name": "打字机",
    "id": "1644275",
    "resource_id": "6724920249654710791",
    "path_hash": "0dc90e490f15d6bac5fd1d778e501917"
}

with open(DRAFT_INFO, 'r') as f:
    info = json.load(f)

anim_ref_id = str(uuid.uuid4()).upper()

# 1. 添加动画数据
anim_entry = {
    "id": anim_ref_id,
    "multi_language_current": "none",
    "type": "sticker_animation",
    "animations": [{
        "anim_adjust_params": None, "category_id": "ruchang", "category_name": "入场",
        "duration": 500000, "id": ANIMATION["id"], "material_type": "sticker",
        "name": ANIMATION["name"], "panel": "", "platform": "all", "request_id": "",
        "resource_id": ANIMATION["resource_id"], "start": 0, "type": "in",
        "path": f"/Users/long/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/{ANIMATION['id']}/{ANIMATION['path_hash']}"
    }]
}
info['materials'].setdefault('material_animations', []).append(anim_entry)

# 2. 给所有字幕段落添加引用
for track in info.get('tracks', []):
    if track.get('type') == 'text':
        for seg in track.get('segments', []):
            # ⚠️ 用赋值，不是追加！
            seg['extra_material_refs'] = [anim_ref_id]

with open(DRAFT_INFO, 'w') as f:
    json.dump(info, f, ensure_ascii=False, indent=2)

print("✅ 已给所有字幕添加" + ANIMATION["name"])
```

---

### 注意事项

⚠️ **path_hash 不能硬编码**
path_hash 是Jianving本地缓存目录名，每台Mac、每次重装都不同。
如果要添加Jianying没有预加载的效果，需要用户先在Jianying中手动添加一次，
然后从 `draft_info.json` 提取正确的 path_hash。

⚠️ **优先使用 draft_info.json**
所有字幕、动画操作只针对 `draft_info.json`。

⚠️ **效果duration单位是微秒**
`500000` = 0.5秒，不是 `0.5`。

---

### 学习新动效的方法

1. 让用户在Jianying中手动给任意字幕添加目标动效
2. 保存后在 `draft_info.json` 的 `materials.material_animations` 中找到新条目
3. 提取 `id`、`resource_id`、`path` 三个字段
4. 用这三个字段即可批量添加



## 📅 版本演进

| 版本 | 日期 | 主要更新 |
|------|------|---------|
| v1.2.0 | 2026-03-29 | macOS 剪映 5.9+ 兼容性修复，解决草稿识别问题 |
| v1.2.1 | 2026-03-29 | 字幕样式参数修复，坐标换算说明 |
| v1.2.2 | 2026-03-30 | BGM 添加流程完善，解决保存后素材丢失问题 |
| v1.2.3 | 2026-03-30 | 画中画 + 缩放关键帧支持 |
| v1.2.4 | 2026-04-07 | **新增：** 批量字体修改，单行部分文字样式修改经验 |
| v1.3.0 | 2026-04-13 | **新增：** 字幕动效添加完整指南，14种动效参数，正确三要素格式 |

---

## 📝 最后一句话

> **脚本放在你的项目目录，Skill 目录只放工具**
> **加载已有项目永远用 `overwrite=False`**
> **重要项目操作前先备份**

Happy Cutting! 🎬
