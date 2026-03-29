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
        self.script.save()
        self._patch_cloud_material_ids()
        self._force_activate_adjustments()
        
        # 同步 materials 到 draft_info.json（剪映 macOS 5.9+ 需要）
        self._sync_draft_info()
        
        # 应用字幕样式设置（如果用户通过 set_subtitle_style 设定了样式）
        self._apply_subtitle_styles()
        
        draft_path = os.path.join(self.root, self.name)
        if os.path.exists(draft_path):
            os.utime(draft_path, None)
        print(f"✅ Project '{self.name}' saved and patched.")
        return {"status": "SUCCESS", "draft_path": draft_path}

    def set_subtitle_style(self, font_size: float = 5.0, scale: float = 1.0,
                          x: float = 0.0, y: float = -1600):
        """统一设置所有字幕的样式（字号、缩放、位置）

        所有位置参数均为像素值，方法内部自动换算为剪映坐标。

        Args:
            font_size: 字体大小，建议 5-20。字号越小字幕越细，注意与 scale 配合。
                      例如 font_size=5 + scale=3 的最终效果 ≈ font_size=15。
            scale: 缩放倍数，如 3.0 表示 300%。调大字幕放大，调小字幕缩小。
            x: X轴像素位置，默认 0 = 水平居中。
               竖屏 2160x3840 通常设为 0 居中即可。
            y: Y轴像素位置，默认 -1600（偏上）。
               竖屏 9:16 常见位置参考：
                 -1740 ~ -1600：字幕偏上（适合放演讲金句）
                 -1200 ~ -800：字幕居中偏上
                 0：垂直居中
               ⚠️ 注意：竖屏画布高度 = 3840，Y=-1740 约在画布偏上1/3处。

        Example:
            # 竖屏 2160x3840，字号5，缩放3x，字幕偏上
            project.set_subtitle_style(font_size=5.0, scale=3.0, x=0, y=-1740)
            project.save()

            # 如果字幕偏下，可以调整 y 值（如 y=-1500 或 y=-1200）
            # 配合 scale 参数：scale=2.5 + font_size=5.0 效果 ≈ scale=2x + font_size=8.0
        """
        # 像素 → 剪映坐标换算
        canvas_h = self.script.height
        transform_x = x / (canvas_h / 2)
        transform_y = y / (canvas_h / 2)
        
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

# 导出工具函数以便向下兼容
__all__ = ["JyProject", "get_default_drafts_root", "get_all_drafts", "safe_tim", "format_srt_time"]

if __name__ == "__main__":
    # 测试代码
    try:
        project = JyProject("Refactor_Test_Project", overwrite=True)
        print("🚀 Refactored JyProject initialized successfully.")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
