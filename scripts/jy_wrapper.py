"""
JianYing Editor Skill - High Level Wrapper (Mixin Based)
旨在解决路径依赖、API 复杂度及严格校验问题。
"""

import os
import sys
import uuid
from typing import Union, Optional

# 环境初始化
from utils.env_setup import setup_env
setup_env()

# 导入工具函数
from utils.constants import SYNONYMS
from utils.formatters import (
    resolve_enum_with_synonyms, format_srt_time, safe_tim, 
    get_duration_ffprobe_cached, get_default_drafts_root, get_all_drafts
)

# 导入基类与 Mixins
from core.project_base import JyProjectBase
from core.media_ops import MediaOpsMixin
from core.text_ops import TextOpsMixin
from core.vfx_ops import VfxOpsMixin
from core.mocking_ops import MockingOpsMixin

try:
    import pyJianYingDraft as draft
    from pyJianYingDraft import VideoSceneEffectType, TransitionType
except ImportError:
    draft = None

class JyProject(JyProjectBase, MediaOpsMixin, TextOpsMixin, VfxOpsMixin, MockingOpsMixin):
    """
    高层封装工程类。通过多重继承 Mixins 实现功能解耦。
    """
    def _resolve_enum(self, enum_cls, name: str):
        return resolve_enum_with_synonyms(enum_cls, name, SYNONYMS)

    def add_clip(self, media_path: str, source_start: Union[str, int], duration: Union[str, int], 
                 target_start: Union[str, int] = None, track_name: str = "VideoTrack", **kwargs):
        """高层剪辑接口：从媒体指定位置裁剪指定长度，并放入轨道。"""
        if target_start is None:
            target_start = self.get_track_duration(track_name)
        return self.add_media_safe(media_path, target_start, duration, track_name, source_start=source_start, **kwargs)

    def save(self):
        """保存并执行质检报告。"""
        import json as _json

        draft_path = os.path.join(self.root, self.name)
        draft_content_path = os.path.join(draft_path, "draft_content.json")
        draft_info_path = os.path.join(draft_path, "draft_info.json")

        # 1. 如果是追加模式，加载已有文件内容
        existing_dc = None
        existing_di = None
        if not self.overwrite and os.path.exists(draft_content_path) and os.path.exists(draft_info_path):
            with open(draft_content_path, "r", encoding="utf-8") as f:
                existing_dc = _json.load(f)
            with open(draft_info_path, "r", encoding="utf-8") as f:
                existing_di = _json.load(f)

        # 2. 触发质检（需要在保存前调用）
        self._patch_cloud_material_ids()
        self._force_activate_adjustments()

        # 3. 获取 script 保存后的完整 tracks
        self.script.save()
        with open(draft_content_path, "r", encoding="utf-8") as f:
            new_dc = _json.load(f)

        # 4. 如果是追加模式，合并轨道和素材
        if existing_dc is not None:
            # 按 (轨道名, 类型) 合并 tracks
            tracks_map = {}
            for t in existing_dc.get("tracks", []):
                key = (t.get("name", ""), t.get("type", ""))
                tracks_map[key] = t

            for t in new_dc.get("tracks", []):
                key = (t.get("name", ""), t.get("type", ""))
                if key in tracks_map:
                    # 合并片段
                    exist_segs = tracks_map[key].get("segments", [])
                    exist_ids = {s.get("id") for s in exist_segs}
                    for seg in t.get("segments", []):
                        if seg.get("id") not in exist_ids:
                            exist_segs.append(seg)
                    tracks_map[key]["segments"] = exist_segs
                    tracks_map[key]["clip_count"] = len(exist_segs)
                else:
                    existing_dc["tracks"].append(t)

            # 合并素材：追加新的素材（避免覆盖已有）
            for mat_type in ["audios", "videos", "images", "texts", " stickers", "effects", "filters"]:
                existing_mats = existing_dc.get("materials", {}).get(mat_type, [])
                new_mats = new_dc.get("materials", {}).get(mat_type, [])
                existing_ids = {m.get("id") for m in existing_mats}
                for m in new_mats:
                    if m.get("id") not in existing_ids:
                        existing_mats.append(m)

            new_dc = existing_dc

        # 5. 写回合并后的 draft_content
        with open(draft_content_path, "w", encoding="utf-8") as f:
            _json.dump(new_dc, f, ensure_ascii=False, indent=4)

        # 6. 同步到 draft_info
        self._sync_draft_info_from_dc(new_dc)

        # 7. 应用字幕样式
        self._apply_subtitle_styles()

        if os.path.exists(draft_path):
            os.utime(draft_path, None)
        print(f"✅ Project '{self.name}' saved and patched.")
        return {"status": "SUCCESS", "draft_path": draft_path}

    def set_subtitle_style(self, font_size: float = 5.0, scale: float = 1.0,
                          x: float = 0.0, y: float = None):
        """统一设置所有字幕的样式（字号、缩放、位置）

        所有位置参数均为像素值，方法内部自动换算为剪映坐标。

        Args:
            font_size: 字体大小，建议 5-20。字号越小字幕越细，注意与 scale 配合。
                      例如 font_size=5 + scale=3 的最终效果 ≈ font_size=15。
            scale: 缩放倍数，如 3.0 表示 300%。调大字幕放大，调小字幕缩小。
            x: X轴像素位置，默认 0 = 水平居中。
               竖屏 720x1280 通常设为 0 居中即可。
            y: Y轴像素位置（默认自动）。如果不传或传None，则自动设为 canvas_height / 4。
               即字幕放在画面下方1/4处（距顶部约3/4高度位置）。
               自动计算参考值：
                 - 竖屏 720x1280：y ≈ -320
                 - 竖屏 1080x1920：y ≈ -480
                 - 竖屏 2160x3840（4K）：y ≈ -960
               也可以手动覆盖，例如设为 -300 等微调值。

        Example:
            # 竖屏 2160x3840，字号5，缩放3x，自动Y位置
            project.set_subtitle_style(font_size=5.0, scale=3.0, x=0)
            project.save()

            # 手动指定Y位置
            project.set_subtitle_style(font_size=5.0, scale=3.0, x=0, y=-300)
            project.save()
        """
        # 像素 → 剪映坐标换算（transform = 像素Y / 画布高度）
        canvas_h = self.script.height
        # 如果 y 未指定，自动设为画面下方1/4位置
        if y is None:
            y = -canvas_h / 4
        transform_x = x / canvas_h
        transform_y = y / canvas_h
        
        self._pending_subtitle_style = {
            "font_size": font_size,
            "scale": scale,
            "transform_x": transform_x,
            "transform_y": transform_y,
        }

    def _apply_subtitle_styles(self):
        """将字幕样式应用到 draft_info.json 和 draft_content.json"""
        import json
        
        if not getattr(self, "_pending_subtitle_style", None):
            return
        
        style = self._pending_subtitle_style
        font_size = style["font_size"]
        scale = style["scale"]
        tx = style["transform_x"]
        ty = style["transform_y"]

        draft_path = os.path.join(self.root, self.name)
        draft_info_path = os.path.join(draft_path, "draft_info.json")
        draft_content_path = os.path.join(draft_path, "draft_content.json")

        if not os.path.exists(draft_info_path):
            return

        with open(draft_info_path, "r", encoding="utf-8") as f:
            draft_info = json.load(f)

        with open(draft_content_path, "r", encoding="utf-8") as f:
            draft_content = json.load(f)

        # --- 更新 draft_info.json ---
        # 1. 更新 materials 中的字幕字号
        for mat in draft_info.get("materials", {}).get("texts", []):
            try:
                c = json.loads(mat.get("content", "{}"))
                for s in c.get("styles", []):
                    s["size"] = font_size
                mat["content"] = json.dumps(c, ensure_ascii=False)
            except Exception:
                pass

        # 2. 更新 tracks 中字幕片段的缩放和位置
        for track in draft_info.get("tracks", []):
            if track.get("type") == "text":
                for seg in track.get("segments", []):
                    clip = seg.get("clip", {})
                    clip["scale"] = {"x": scale, "y": scale}
                    clip["transform"] = {"x": tx, "y": ty}

        # --- 更新 draft_content.json ---
        # 1. 更新 materials 中的字幕字号
        for mat in draft_content.get("materials", {}).get("texts", []):
            try:
                c = json.loads(mat.get("content", "{}"))
                for s in c.get("styles", []):
                    s["size"] = font_size
                mat["content"] = json.dumps(c, ensure_ascii=False)
            except Exception:
                pass

        # 2. 更新 tracks 中字幕片段的缩放和位置
        for track in draft_content.get("tracks", []):
            if track.get("type") == "text":
                for seg in track.get("segments", []):
                    clip = seg.get("clip", {})
                    clip["scale"] = {"x": scale, "y": scale}
                    clip["transform"] = {"x": tx, "y": ty}

        # 写回文件
        with open(draft_info_path, "w", encoding="utf-8") as f:
            json.dump(draft_info, f, ensure_ascii=False, indent=4)

        with open(draft_content_path, "w", encoding="utf-8") as f:
            json.dump(draft_content, f, ensure_ascii=False, indent=4)

        print(f"✅ 字幕样式已应用: 字号={font_size}, 缩放={scale}x, X={tx}, Y={ty}")

    def _sync_draft_info(self):
        """将 draft_content.json 的 materials 同步到 draft_info.json"""
        import json
        import uuid
        import hashlib
        import platform as platform_module

        draft_path = os.path.join(self.root, self.name)
        draft_info_path = os.path.join(draft_path, "draft_info.json")
        draft_content_path = os.path.join(draft_path, "draft_content.json")

        if not os.path.exists(draft_info_path) or not os.path.exists(draft_content_path):
            return

        with open(draft_info_path, "r", encoding="utf-8") as f:
            draft_info = json.load(f)

        with open(draft_content_path, "r", encoding="utf-8") as f:
            draft_content = json.load(f)

        # 从 draft_content 获取 materials
        content_materials = draft_content.get("materials", {})

        # 复制关键材料数组到 draft_info
        draft_info["materials"] = {
            "ai_translates": content_materials.get("ai_translates", []),
            "audio_balances": content_materials.get("audio_balances", []),
            "audio_effects": content_materials.get("audio_effects", []),
            "audio_fades": content_materials.get("audio_fades", []),
            "audio_track_indexes": content_materials.get("audio_track_indexes", []),
            "audios": content_materials.get("audios", []),
            "beats": content_materials.get("beats", []),
            "canvases": content_materials.get("canvases", []),
            "chromas": content_materials.get("chromas", []),
            "color_curves": content_materials.get("color_curves", []),
            "digital_humans": content_materials.get("digital_humans", []),
            "drafts": content_materials.get("drafts", []),
            "effects": content_materials.get("effects", []),
            "flowers": content_materials.get("flowers", []),
            "green_screens": content_materials.get("green_screens", []),
            "handwrites": content_materials.get("handwrites", []),
            "hsl": content_materials.get("hsl", []),
            "images": content_materials.get("images", []),
            "log_color_wheels": content_materials.get("log_color_wheels", []),
            "loudnesses": content_materials.get("loudnesses", []),
            "manual_deformations": content_materials.get("manual_deformations", []),
            "masks": content_materials.get("masks", []),
            "material_animations": content_materials.get("material_animations", []),
            "material_colors": content_materials.get("material_colors", []),
            "multi_language_refs": content_materials.get("multi_language_refs", []),
            "placeholders": content_materials.get("placeholders", []),
            "plugin_effects": content_materials.get("plugin_effects", []),
            "primary_color_wheels": content_materials.get("primary_color_wheels", []),
            "realtime_denoises": content_materials.get("realtime_denoises", []),
            "shapes": content_materials.get("shapes", []),
            "smart_crops": content_materials.get("smart_crops", []),
            "smart_relights": content_materials.get("smart_relights", []),
            "sound_channel_mappings": content_materials.get("sound_channel_mappings", []),
            "speeds": content_materials.get("speeds", []),
            "stickers": content_materials.get("stickers", []),
            "tail_leaders": content_materials.get("tail_leaders", []),
            "text_templates": content_materials.get("text_templates", []),
            "texts": content_materials.get("texts", []),
            "time_marks": content_materials.get("time_marks", []),
            "transitions": content_materials.get("transitions", []),
            "video_effects": content_materials.get("video_effects", []),
            "video_trackings": content_materials.get("video_trackings", []),
            "videos": content_materials.get("videos", []),
            "vocal_beautifys": content_materials.get("vocal_beautifys", []),
            "vocal_separations": content_materials.get("vocal_separations", []),
        }

        # 更新时长
        draft_info["duration"] = draft_content.get("duration", 0)

        # 更新 canvas_config（以 draft_content 为准）
        canvas = draft_content.get("canvas_config", {})
        draft_info["canvas_config"] = {
            "width": canvas.get("width", self.script.width),
            "height": canvas.get("height", self.script.height),
            "ratio": canvas.get("ratio", "original")
        }

        # 更新 tracks
        draft_info["tracks"] = draft_content.get("tracks", [])

        # 写回 draft_info.json
        with open(draft_info_path, "w", encoding="utf-8") as f:
            json.dump(draft_info, f, ensure_ascii=False, indent=4)

    def _sync_draft_info_from_dc(self, new_dc):
        """将 draft_content dict 的 materials 同步到 draft_info.json"""
        import json

        draft_path = os.path.join(self.root, self.name)
        draft_info_path = os.path.join(draft_path, "draft_info.json")

        if not os.path.exists(draft_info_path):
            return

        with open(draft_info_path, "r", encoding="utf-8") as f:
            draft_info = json.load(f)

        content_materials = new_dc.get("materials", {})

        # 复制关键材料数组到 draft_info
        draft_info["materials"] = {
            "ai_translates": content_materials.get("ai_translates", []),
            "audio_balances": content_materials.get("audio_balances", []),
            "audio_effects": content_materials.get("audio_effects", []),
            "audio_fades": content_materials.get("audio_fades", []),
            "audio_track_indexes": content_materials.get("audio_track_indexes", []),
            "audios": content_materials.get("audios", []),
            "beats": content_materials.get("beats", []),
            "canvases": content_materials.get("canvases", []),
            "chromas": content_materials.get("chromas", []),
            "color_curves": content_materials.get("color_curves", []),
            "digital_humans": content_materials.get("digital_humans", []),
            "drafts": content_materials.get("drafts", []),
            "effects": content_materials.get("effects", []),
            "flowers": content_materials.get("flowers", []),
            "green_screens": content_materials.get("green_screens", []),
            "handwrites": content_materials.get("handwrites", []),
            "hsl": content_materials.get("hsl", []),
            "images": content_materials.get("images", []),
            "log_color_wheels": content_materials.get("log_color_wheels", []),
            "loudnesses": content_materials.get("loudnesses", []),
            "manual_deformations": content_materials.get("manual_deformations", []),
            "masks": content_materials.get("masks", []),
            "material_animations": content_materials.get("material_animations", []),
            "material_colors": content_materials.get("material_colors", []),
            "multi_language_refs": content_materials.get("multi_language_refs", []),
            "placeholders": content_materials.get("placeholders", []),
            "plugin_effects": content_materials.get("plugin_effects", []),
            "primary_color_wheels": content_materials.get("primary_color_wheels", []),
            "realtime_denoises": content_materials.get("realtime_denoises", []),
            "shapes": content_materials.get("shapes", []),
            "smart_crops": content_materials.get("smart_crops", []),
            "smart_relights": content_materials.get("smart_relights", []),
            "sound_channel_mappings": content_materials.get("sound_channel_mappings", []),
            "speeds": content_materials.get("speeds", []),
            "stickers": content_materials.get("stickers", []),
            "tail_leaders": content_materials.get("tail_leaders", []),
            "text_templates": content_materials.get("text_templates", []),
            "texts": content_materials.get("texts", []),
            "time_marks": content_materials.get("time_marks", []),
            "transitions": content_materials.get("transitions", []),
            "video_effects": content_materials.get("video_effects", []),
            "video_trackings": content_materials.get("video_trackings", []),
            "videos": content_materials.get("videos", []),
            "vocal_beautifys": content_materials.get("vocal_beautifys", []),
            "vocal_separations": content_materials.get("vocal_separations", []),
        }

        # 更新时长
        draft_info["duration"] = new_dc.get("duration", 0)

        # 更新 canvas_config
        canvas = new_dc.get("canvas_config", {})
        draft_info["canvas_config"] = {
            "width": canvas.get("width", self.script.width),
            "height": canvas.get("height", self.script.height),
            "ratio": canvas.get("ratio", "original")
        }

        # 更新 tracks
        draft_info["tracks"] = new_dc.get("tracks", [])

        # 写回 draft_info.json
        with open(draft_info_path, "w", encoding="utf-8") as f:
            json.dump(draft_info, f, ensure_ascii=False, indent=4)

# 导出工具函数以便向下兼容
__all__ = ["JyProject", "get_default_drafts_root", "get_all_drafts", "safe_tim", "format_srt_time"]

if __name__ == "__main__":
    # 测试代码
    try:
        project = JyProject("Refactor_Test_Project", overwrite=True)
        print("🚀 Refactored JyProject initialized successfully.")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
