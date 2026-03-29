# Changelog

## v1.2.0 - 2026-03-29（macOS 剪映 5.9+ 兼容性修复）

**开发者**：小剪 & 薛龙龙

### 🔧 核心修复

1. **macOS 草稿目录探测**（`formatters.py`）
   - 添加 `~/Movies/JianyingPro/` 和 `~/Movies/CapCut/` 路径支持
   - 根据系统类型自动选择正确的 fallback

2. **VideoMaterial 字段补全**（`local_materials.py`）
   - 添加 `has_audio` 自动检测（通过 pymediainfo 检测音轨）
   - 添加 `source=0`, `is_copyright=false`, `extra_type_option=0` 等 macOS 5.9+ 必填字段
   - 添加 `matting`, `video_algorithm`, `smart_motion` 等嵌套对象

3. **完整草稿文件生成**（`draft_folder.py`）
   - 新增 `_generate_draft_info()` 生成符合 macOS 5.9.0 规范的 `draft_info.json`
   - 创建 `template.tmp` 和 `draft_settings` 空文件

4. **materials 同步机制**（`jy_wrapper.py`）
   - 新增 `_sync_draft_info()` 在 save() 时同步 materials, tracks, duration, canvas_config 到 `draft_info.json`

### 📄 新增文档

- `EVOLUTION.md` — 版本演进详细记录，供后来者参考经验

### 🧪 测试验证

- ✅ 空白项目创建
- ✅ 导入完整视频
- ✅ add_clip() 精确剪辑（掐头去尾）
- ✅ add_text_simple() 添加字幕
- ✅ 草稿在剪映中正确显示所有素材

---

## v1.5.0 - 2026-03-04
- Security hardening:
  - sanitized draft project names and blocked path traversal/out-of-root delete.
  - restored TLS verification for SAMI TTS by default.
  - added cloud download URL/header/size guards.
- API/CLI standardization:
  - unified machine-readable `--json` output for key scripts.
  - added strict mode for validator (`--strict`).
  - centralized runtime config (`scripts/utils/config.py`).
- Quality engineering:
  - expanded unit tests for security guards.
  - added repo hygiene and data schema checks.
  - added CI lint/format/test/schema pipeline.
- Repo organization:
  - removed tracked runtime artifacts and cache binaries.
  - added compatibility wrappers and common logger utility.
