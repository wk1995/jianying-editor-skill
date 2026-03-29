"""草稿文件夹管理器"""

import os
import shutil
import uuid
import hashlib
import platform as platform_module

from typing import List

from . import assets
from .script_file import ScriptFile

class DraftFolder:
    """管理一个文件夹及其内的一系列草稿"""

    folder_path: str
    """根路径"""

    def __init__(self, folder_path: str):
        """初始化草稿文件夹管理器

        Args:
            folder_path (`str`): 包含若干草稿的文件夹, 一般取剪映保存草稿的位置即可

        Raises:
            `FileNotFoundError`: 路径不存在
        """
        self.folder_path = folder_path

        if not os.path.exists(self.folder_path):
            raise FileNotFoundError(f"根文件夹 {self.folder_path} 不存在")

    def list_drafts(self) -> List[str]:
        """列出文件夹中所有草稿的名称

        注意: 本函数只是如实地列出子文件夹的名称, 并不检查它们是否符合草稿的格式
        """
        return [f for f in os.listdir(self.folder_path) if os.path.isdir(os.path.join(self.folder_path, f))]

    def has_draft(self, draft_name: str) -> bool:
        """检查文件夹中是否存在指定名称的草稿

        注意: 本函数只检查文件夹是否存在, 并不检查草稿是否符合剪映的格式

        Args:
            draft_name (`str`): 草稿名称, 即相应文件夹名称
        """
        return draft_name in self.list_drafts()

    def remove(self, draft_name: str) -> None:
        """删除指定名称的草稿

        Args:
            draft_name (`str`): 草稿名称, 即相应文件夹名称

        Raises:
            `FileNotFoundError`: 对应的草稿不存在
        """
        draft_path = os.path.join(self.folder_path, draft_name)
        if not os.path.exists(draft_path):
            raise FileNotFoundError(f"草稿文件夹 {draft_name} 不存在")

        shutil.rmtree(draft_path)

    def create_draft(self, draft_name: str, width: int, height: int, fps: int = 30, *,
                     maintrack_adsorb: bool = True,
                     allow_replace: bool = False) -> ScriptFile:
        """创建一个新草稿并开始编辑, 编辑完成后使用`ScriptFile.save()`保存即可

        Args:
            draft_name (`str`): 草稿名称, 即相应文件夹名称
            width (`int`): 视频宽度, 单位为像素
            height (`int`): 视频高度, 单位为像素
            fps (`int`, optional): 视频帧率. 默认为30.
            maintrack_adsorb (`bool`, optional): 是否启用主轨道吸附（主轨磁吸）. 默认启用.
            allow_replace (`bool`, optional): 是否允许覆盖与`draft_name`重名的草稿. 默认为否.

        Raises:
            `FileExistsError`: 已存在与`draft_name`重名的草稿, 但不允许覆盖.
        """
        draft_path = os.path.join(self.folder_path, draft_name)
        if os.path.exists(draft_path):
            if not allow_replace:
                raise FileExistsError(f"草稿文件夹 {draft_name} 已存在且不允许覆盖")
            shutil.rmtree(draft_path)

        # 创建草稿文件夹
        os.makedirs(draft_path)
        shutil.copy(assets.get_asset_path("DRAFT_META_TEMPLATE"), os.path.join(draft_path, "draft_meta_info.json"))

        # 创建 draft_info.json
        draft_info = _generate_draft_info(draft_name, width, height, fps)
        with open(os.path.join(draft_path, "draft_info.json"), "w", encoding="utf-8") as f:
            import json
            json.dump(draft_info, f, ensure_ascii=False, indent=4)

        # 创建 template.tmp (空 protobuf placeholder)
        with open(os.path.join(draft_path, "template.tmp"), "wb") as f:
            f.write(b"")

        # 创建 draft_settings
        with open(os.path.join(draft_path, "draft_settings"), "w", encoding="utf-8") as f:
            f.write("")

        # 创建草稿文件
        script_file = ScriptFile(width, height, fps, maintrack_adsorb)
        script_file.save_path = os.path.join(draft_path, "draft_content.json")

        return script_file

    def inspect_material(self, draft_name: str) -> None:
        """输出指定名称草稿中的贴纸素材元数据

        Args:
            draft_name (`str`): 草稿名称, 即相应文件夹名称

        Raises:
            `FileNotFoundError`: 对应的草稿不存在
        """
        draft_path = os.path.join(self.folder_path, draft_name)
        if not os.path.exists(draft_path):
            raise FileNotFoundError(f"草稿文件夹 {draft_name} 不存在")

        script_file = self.load_template(draft_name)
        script_file.inspect_material()

    def load_template(self, draft_name: str) -> ScriptFile:
        """在文件夹中打开一个草稿作为模板, 并在其上进行编辑

        Args:
            draft_name (`str`): 草稿名称, 即相应文件夹名称

        Returns:
            `ScriptFile`: 以模板模式打开的草稿对象

        Raises:
            `FileNotFoundError`: 对应的草稿不存在
        """
        draft_path = os.path.join(self.folder_path, draft_name)
        if not os.path.exists(draft_path):
            raise FileNotFoundError(f"草稿文件夹 {draft_name} 不存在")

        return ScriptFile.load_template(os.path.join(draft_path, "draft_content.json"))

    def duplicate_as_template(self, template_name: str, new_draft_name: str, allow_replace: bool = False) -> ScriptFile:
        """复制一份给定的草稿, 并在复制出的新草稿上进行编辑

        Args:
            template_name (`str`): 原草稿名称
            new_draft_name (`str`): 新草稿名称
            allow_replace (`bool`, optional): 是否允许覆盖与`new_draft_name`重名的草稿. 默认为否.

        Returns:
            `ScriptFile`: 以模板模式打开的**复制后的**草稿对象

        Raises:
            `FileNotFoundError`: 原始草稿不存在
            `FileExistsError`: 已存在与`new_draft_name`重名的草稿, 但不允许覆盖.
        """
        template_path = os.path.join(self.folder_path, template_name)
        new_draft_path = os.path.join(self.folder_path, new_draft_name)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"模板草稿 {template_name} 不存在")
        if os.path.exists(new_draft_path) and not allow_replace:
            raise FileExistsError(f"新草稿 {new_draft_name} 已存在且不允许覆盖")

        # 复制草稿文件夹
        shutil.copytree(template_path, new_draft_path, dirs_exist_ok=allow_replace)

        # 打开草稿
        return self.load_template(new_draft_name)


def _generate_draft_info(name: str, width: int, height: int, fps: int) -> dict:
    """生成 draft_info.json 的基本结构（适配 macOS 剪映 5.9+）"""
    # 生成稳定的设备 ID
    raw_id = f"{platform_module.node()}-{os.getpid()}".encode()
    device_id = hashlib.md5(raw_id).hexdigest()[:32]
    mac_address = hashlib.md5(raw_id).hexdigest()[:12]
    hard_disk_id = hashlib.md5(raw_id).hexdigest()[:32]

    return {
        "canvas_config": {
            "height": height,
            "ratio": "original",
            "width": width
        },
        "color_space": 0,
        "config": {
            "adjust_max_index": 1,
            "attachment_info": [],
            "combination_max_index": 1,
            "export_range": None,
            "extract_audio_last_index": 1,
            "lyrics_recognition_id": "",
            "lyrics_sync": True,
            "lyrics_taskinfo": [],
            "maintrack_adsorb": True,
            "material_save_mode": 0,
            "multi_language_current": "none",
            "multi_language_list": [],
            "multi_language_main": "none",
            "multi_language_mode": "none",
            "original_sound_last_index": 1,
            "record_audio_last_index": 1,
            "sticker_max_index": 1,
            "subtitle_keywords_config": None,
            "subtitle_recognition_id": "",
            "subtitle_sync": True,
            "subtitle_taskinfo": [],
            "system_font_list": [],
            "video_mute": False,
            "zoom_info_params": None
        },
        "cover": None,
        "create_time": 0,
        "duration": 0,
        "extra_info": None,
        "fps": float(fps),
        "free_render_index_mode_on": False,
        "group_container": None,
        "id": str(uuid.uuid4()).upper(),
        "keyframe_graph_list": [],
        "keyframes": {
            "adjusts": [],
            "audios": [],
            "effects": [],
            "filters": [],
            "handwrites": [],
            "stickers": [],
            "texts": [],
            "videos": []
        },
        "last_modified_platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",
            "device_id": device_id,
            "hard_disk_id": hard_disk_id,
            "mac_address": mac_address,
            "os": "mac",
            "os_version": platform_module.mac_ver()[0] if platform_module.system() == "Darwin" else "0.0"
        },
        "materials": {
            "ai_translates": [],
            "audio_balances": [],
            "audio_effects": [],
            "audio_fades": [],
            "audio_track_indexes": [],
            "audios": [],
            "beats": [],
            "canvases": [],
            "chromas": [],
            "color_curves": [],
            "digital_humans": [],
            "drafts": [],
            "effects": [],
            "flowers": [],
            "green_screens": [],
            "handwrites": [],
            "hsl": [],
            "images": [],
            "log_color_wheels": [],
            "loudnesses": [],
            "manual_deformations": [],
            "masks": [],
            "material_animations": [],
            "material_colors": [],
            "multi_language_refs": [],
            "placeholders": [],
            "plugin_effects": [],
            "primary_color_wheels": [],
            "realtime_denoises": [],
            "shapes": [],
            "smart_crops": [],
            "smart_relights": [],
            "sound_channel_mappings": [],
            "speeds": [],
            "stickers": [],
            "tail_leaders": [],
            "text_templates": [],
            "texts": [],
            "time_marks": [],
            "transitions": [],
            "video_effects": [],
            "video_trackings": [],
            "videos": [],
            "vocal_beautifys": [],
            "vocal_separations": []
        },
        "mutable_config": None,
        "name": "",
        "new_version": "110.0.0",
        "platform": {
            "app_id": 3704,
            "app_source": "lv",
            "app_version": "5.9.0",
            "device_id": device_id,
            "hard_disk_id": hard_disk_id,
            "mac_address": mac_address,
            "os": "mac",
            "os_version": platform_module.mac_ver()[0] if platform_module.system() == "Darwin" else "0.0"
        },
        "relationships": [],
        "render_index_track_mode_on": False,
        "retouch_cover": None,
        "source": "default",
        "static_cover_image_path": "",
        "time_marks": None,
        "tracks": [],
        "update_time": 0,
        "version": 360000
    }
