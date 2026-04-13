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

---

## ❌ 事故记录

**日期：** 2026-03-30
**事故人：** 小剪
**严重程度：** 🔴 高 — 用户草稿数据永久丢失

---

### 事故 1：overwrite=True 导致用户草稿被覆盖

**背景：** 使用 `JyProject(project_name="xxx", overwrite=True)` 加载已有草稿时，`overwrite=True` 会强制用空白模板替换已有项目。

**经过：**
1. 测试技能3功能时，想要在"嘉政_精剪版"草稿上添加测试内容
2. 代码使用了 `overwrite=True`，导致草稿被空白模板替换
3. 原草稿的 70 个片段（5视频+65字幕）全部丢失

**教训：**
- `overwrite=True` = 创建/覆盖，应仅用于新建草稿
- 加载已有草稿时必须用 `overwrite=False`
- **绝对不能在用户数据上使用 overwrite=True**

**修复代码（正确用法）：**
```python
# ✅ 正确：加载已有草稿（不覆盖）
project = JyProject(project_name="嘉政_精剪版", overwrite=False)

# ❌ 错误：会覆盖已有草稿
project = JyProject(project_name="嘉政_精剪版", overwrite=True)
```

**未来防护措施：**
1. 在测试脚本中加入草稿是否存在的前置检查
2. 如草稿已存在，强制要求用户确认才可继续
3. 重要草稿操作前先备份 `draft_content.json`

**备份脚本参考：**
```python
import shutil, os
draft_path = "/path/to/draft"
backup_path = f"{draft_path}_backup_20260330"
shutil.copytree(draft_path, backup_path)
print(f"已备份到: {backup_path}")
```

---

### 事故 2：API 参数不熟悉导致测试脚本多处报错

**日期：** 2026-03-30

**问题列表：**
| API | 错误 | 正确用法 |
|-----|------|---------|
| `JyProject()` | 用 `draft_name=` | 用 `project_name=` |
| `add_text_simple()` | 用 `clip_settings=` | 需查看具体参数 |
| `add_styled_text()` | 方法可能不存在 | 需确认 |
| `add_transition_simple()` | 参数 `start_time` 不支持 | 需查看签名 |
| 关键帧 | `project.segments` 不存在 | 需从 track 获取 |

**改进方向：**
- 写测试前先完整阅读 `jy_wrapper.py` 和各 Mixin 的实际接口
- 草稿操作前打印/检查 API 返回值，确认对象属性

---

### 事故 3：save() 追加模式只合并轨道，不合并素材

**文件：** `scripts/jy_wrapper.py` — `save()` 方法

**问题：** 使用 `overwrite=False` 加载草稿后添加BGM，保存时轨道合并了但素材没有合并。`materials.audios` 在保存后为空，导致BGM在剪映中看不到。

**原因：** `save()` 的追加模式合并逻辑只处理了 `tracks`，完全遗漏了 `materials` 的合并。`new_dc = existing_dc` 直接用旧数据覆盖了包含新素材的 `new_dc`。

**修复：** 在 tracks 合并之后，增加 materials 的合并逻辑：
```python
# 合并素材：追加新的素材（避免覆盖已有）
for mat_type in ["audios", "videos", "images", "texts", ...]:
    existing_mats = existing_dc.get("materials", {}).get(mat_type, [])
    new_mats = new_dc.get("materials", {}).get(mat_type, [])
    existing_ids = {m.get("id") for m in existing_mats}
    for m in new_mats:
        if m.get("id") not in existing_ids:
            existing_mats.append(m)
```

---

### 事故 4：直接修改 draft_content.json 无法影响剪映实际读取

**日期：** 2026-03-30

**问题：** 多次尝试修改 `draft_content.json` 后，剪映打开草稿时内容没有变化，或者出现奇怪的状态。

**根本原因：** 剪映 macOS 版实际读取的是 `draft_info.json`（而非 `draft_content.json`）。`script.save()` 写入的是 `draft_content.json`，而剪映读取的是 `draft_info.json`。两个文件必须保持同步。

**教训：**
- `draft_content.json` = pyJianYingDraft 库内部读写用的文件
- `draft_info.json` = 剪映 macOS 实际读取的权威文件
- **所有修改必须通过 `save()` 触发同步**，或者手动同步两个文件
- `save()` 里的 `_sync_draft_info_from_dc()` 就是负责这个同步的

---

### 事故 5：误改 AudioMaterial type 导致波形消失

**文件：** `scripts/vendor/pyJianYingDraft/local_materials.py`

**问题：** 把 `AudioMaterial.export_json()` 中的 `type` 从 `"extract_music"` 改为 `"audio"`，导致本地音频在剪映中虽然能播放，但时间轴上完全看不见波形，无法选中操作。

**教训：** `"extract_music"` 不是错误类型，而是**本地文件导入到剪映后生成的正确类型**。不要随意修改。正确的 type 决定剪映如何渲染该素材。

**正确理解：**
- `type=extract_music`：本地导入的音乐素材（正确✅）
- `type=audio`：另一种用途的类型
- `type=none`：未正确识别的素材（错误❌）

---

### 事故 6：直接编辑草稿 JSON 导致数据损坏

**日期：** 2026-03-30

**问题：** 多次直接用 Python 修改 `draft_info.json` 的内容（如删除片段），导致草稿轨道数据出现孤立的片段引用（material_id 在素材列表中找不到），草稿最终损坏到无法打开。

**教训：**
- 永远不要手动拼接 JSON 中的片段引用关系
- 删除片段的正确做法：通过 JyProject 对象操作，然后用 `save()` 统一写入
- 如果 JyProject 的 API 不支持直接删除，至少要在内存中完整追踪引用关系后再批量写入

---

### 事故 7：直接用 shutil.rmtree / copytree 操作剪映草稿导致文件丢失

**问题：** 用 `shutil.copytree` 复制草稿时，草稿目录下的文件有时变成 0 字节（如 `draft_content.json` 复制后变成空文件）。

**原因：** macOS 的 Finder / rsync 可能用 `_` 扩展属性文件来存储元数据，直接 copytree 会丢失这些属性。

**正确做法：**
```python
import shutil
shutil.copytree(src, dst)  # Python 的 copytree 通常更可靠
# 或用 ditto（macOS 原生命令）
import subprocess
subprocess.run(['ditto', src, dst])
```

---

## 📝 关键经验总结

### API 添加音频的正确流程

1. **选对添加方式：**
   - 云端音乐 → `add_cloud_music(query="关键词")`（下载到 cache 后添加）
   - 本地音频 → `add_audio_safe(local_path, ...)`
   - **不要**用 `add_cloud_media` 来添加音乐

2. **新建草稿 vs 已有草稿：**
   ```python
   # 新建（overwrite=True）
   p = JyProject(project_name="新草稿", overwrite=True)
   
   # 已有草稿（overwrite=False）— 不覆盖！
   p = JyProject(project_name="已有草稿", overwrite=False)
   ```

3. **保存后检查两个文件：**
   ```python
   # 验证 draft_info.json 里的 materials.audios 数量和 type
   with open(f'{draft_dir}/draft_info.json') as f:
       d = json.load(f)
   for a in d.get('materials', {}).get('audios', []):
       print(f'type={a.get("type")}, name={a.get("name")}')
   ```

4. **关于"需要链接素材"：**
   - 本地文件通过 API 添加后，**一定需要手动链接一次**
   - 云端音乐（预索引库）通过 API 添加后，**也可能需要一次手动授权**
   - 这是剪映的权限机制，无法通过 API 绕过
   - **解决方案**：用户只需在剪映里点一次"允许"，之后草稿就正常了

---

### 事故 8：API 参数含义搞反导致所有片段都显示视频开头

**日期：** 2026-04-08
**严重程度：** 🟡 中 — 浪费时间，但草稿可重新生成

**问题现象：**
生成剪映草稿后，时间线上片段排列顺序正确，但**所有片段内容都显示为视频开头**，每个片段只是时长不同，但内容都是开头重复拼接，看起来像是把开头剪成了长短不一的片段，完全不对。

**错误原因：**
混淆了 API 参数含义，误用错误方法和错误参数顺序：
- ❌ 错误：用 `add_media_safe`，将 `start_time` 参数当作原视频起始位置，但实际上 `start_time` 是目标时间线位置
- ❌ 错误：把 `source_start` 和 `target_start` 理解反了

**正确用法：**
必须使用 `add_clip` 方法，参数含义绝对不能搞反：
```python
project.add_clip(
    视频路径,
    source_start="原视频中从哪里切片段",  # ← 正确：表示在原视频中的起始位置
    duration="切多长时间",                # ← 需要截取的时长
    target_start="放到时间线哪个位置"     # ← 正确：表示在目标时间线的起始位置
)
```

**完整示例（正确）：**
```python
target_start = 0.0
for keep in keep_segments:
    project.add_clip(
        video_path,
        source_start=f"{keep['source_start']}s",
        duration=f"{keep['duration']}s",
        target_start=f"{target_start}s"
    )
    target_start += keep['duration']  # ← 必须递增，每个片段接着上一个放
```

**教训：**
1. 不要想当然猜测 API 参数含义，一定要先看函数签名再使用
2. 使用前打印函数签名确认：`print(inspect.signature(project.add_clip))`
3. 第一个片段 target_start 从 0 开始，每个片段之后 target_start += 片段时长，这样才不会重叠

**验证：**
生成后检查每个片段是否内容正确，而不只是检查顺序正确。


---

## 🔧 v1.3.0 字幕动效相关修复（2026-04-13）

### 问题：批量添加字幕动效后剪映不生效

**症状：** 用Python修改了 `draft_content.json` 中的字幕段落动画，但剪映打开后没有任何动效。

**根因：** 错误地修改了 `draft_content.json`，而 Jianying 实际读取的是 `draft_info.json`。

**解决：** 必须在 `draft_info.json` 中两处同时修改：
1. `materials.material_animations` — 动画数据
2. `tracks[].segments[].extra_material_refs` — 段落对动画的引用

**教训：** Jianying 有两个文件保存草稿，实际读取的是 `draft_info.json`。所有字幕/动画相关操作都必须针对 `draft_info.json`。

---

### 问题：animation_id 对但动效不生效

**症状：** 使用了正确的 animation_id（如 `1644275` 打字机），但剪映显示不出效果。

**根因：** `path` 字段的 hash 值错误。path 格式为：
```
/Users/long/Library/Containers/com.lemon.lvpro/Data/Movies/JianyingPro/User Data/Cache/effect/{animation_id}/{path_hash}
```

`path_hash` 必须与本地缓存目录名一致，否则 Jianying 找不到资源文件。

**解决：** 手动在Jianying中添加一次效果，然后从 `draft_info.json` 中提取正确的 `path_hash`。

**教训：** animation_id 决定效果种类，path_hash 决定资源路径。两者都必须正确才能生效。

---

### 问题：path_hash 硬编码导致跨机器/重装后失效

**症状：** 在一台Mac上获取的path_hash，换到另一台Mac或者重装后完全不一样。

**根因：** path_hash 是Jianying下载效果资源时生成的本地缓存目录名，每次下载都不同。

**正确做法：** 
- path_hash 不能硬编码，必须从 `draft_info.json` 中读取
- 如果目标机器没有对应的缓存文件，效果会失效
- 最佳实践：让用户先在Jianying里下载/缓存需要的效果，再通过本Skill添加

---

### 问题：同一字幕添加多个动效引用导致重复

**症状：** 同一个字幕段落出现了两个 `extra_material_refs`，导致显示异常。

**原因：** 之前添加的引用没清除，又追加了新的。

**解决：** 添加动效前先检查是否已有引用，保留原有引用追加新引用：
```python
refs = seg.get('extra_material_refs', [])
refs.append(anim_ref_id)
seg['extra_material_refs'] = refs
```

如果要替换动效，先清空现有引用，再添加新引用。

---

### 问题：打字机效果名称不统一

**发现：** Jianying 中打字机效果有两种名称：
- `打字机` — animation_id `1644275`
- `打字机 I` — 同ID，但 name 字段不同

实际生效的是 animation_id，name 只是显示名。

**教训：** 靠 name 字段识别效果不可靠，必须用 animation_id。

---

### 正确的字幕动效debug步骤

1. 在Jianiang中手动添加目标动效到任意字幕，保存
2. 读取 `draft_info.json`
3. 在 `materials.material_animations` 中找到刚添加的条目
4. 提取 `id`, `resource_id`, `path` 三个字段
5. 用这三个字段批量添加到其他字幕

**验证方法：** 在Jianying中打开，确认效果有动画（不是静止的）。如果没动画，说明path_hash不对。


---

### 问题：添加字幕动效时，部分字幕没有生效（v1.3.0 bug）

**症状：** 用代码给所有字幕添加动效后，只有前面几个字幕有效果，后面的字幕没有。

**根因：** 代码使用了 `refs.append()` 来添加动画引用。当字幕的 `extra_material_refs` 字段为空列表时：
```python
# 错误代码
refs = seg.get('extra_material_refs', [])  # 如果为空，返回 []
refs.append(anim_ref_id)  # 只在列表末尾添加
seg['extra_material_refs'] = refs  # 但如果之前有无效引用，这里不会更新
```

实际上，部分字幕的 `extra_material_refs` 可能已经指向无效的动画条目（animations为空），但 `append` 不会替换这些无效引用。

**正确代码：**
```python
# 正确：用赋值替换，而不是追加
seg['extra_material_refs'] = [anim_ref_id]
```

**修复：** 
1. 先清理 `material_animations` 中无效的条目（animations为空的）
2. 对所有字幕段落，用赋值设置新的引用

```python
# 1. 清理无效的 material_animations
mat_anim = info['materials'].get('material_animations', [])
valid_mat_anim = [ma for ma in mat_anim if ma.get('animations') and len(ma['animations']) > 0]
info['materials']['material_animations'] = valid_mat_anim

# 2. 用赋值设置引用（不是追加）
for track in info.get('tracks', []):
    if track.get('type') == 'text':
        for seg in track.get('segments', []):
            seg['extra_material_refs'] = [anim_ref_id]  # 赋值，不是append
```

