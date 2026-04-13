#!/usr/bin/env python3
"""
测试技能3：丰富的剪辑功能
草稿：龙龙演讲AI精剪版
测试内容：字幕/文字、转场、特效、关键帧、TTS、BGM等

⚠️ 安全须知：
- 使用 overwrite=False 加载已有草稿，保护原数据
- 测试前已自动备份草稿
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from scripts.jy_wrapper import JyProject
from pyJianYingDraft import KeyframeProperty as KP, ClipSettings, TextStyle, TextBorder, TrackType, Timerange
import pyJianYingDraft as draft

DRAFT_NAME = "龙龙演讲AI精剪版"

print("=" * 60)
print("技能3功能测试 — 丰富的剪辑功能")
print("=" * 60)

# 打开草稿（使用 overwrite=False 保护原数据）
print(f"\n[1] 加载草稿: {DRAFT_NAME}")
project = JyProject(project_name=DRAFT_NAME, overwrite=False)
print(f"    ✅ 草稿加载成功")

# 获取草稿时长，用于计算测试位置
total_dur = project.get_track_duration("VideoTrack") if hasattr(project, 'get_track_duration') else 0
total_sec = total_dur / 1_000_000 if total_dur else 0
print(f"    草稿时长: {total_sec:.1f}秒")

# ============================================================
# 测试1：添加普通字幕文字（动画打字机效果）
# ============================================================
print(f"\n[2] 测试普通字幕文字 + 打字机动画")
try:
    test_start = total_sec + 5  # 放在现有内容之后
    seg = project.add_text_simple(
        text="【AI测试字幕-龙龙演讲】",
        start_time=f"{test_start}s",
        duration="4s",
        track_name="Subtitles",
        anim_in="打字机_I",
        style=TextStyle(size=5.0),
        border=TextBorder(color=(0.0, 0.0, 0.0), alpha=1.0, width=40.0),
        clip_settings=ClipSettings(transform_y=-0.8)
    )
    print(f"    ✅ 字幕添加成功 (start={test_start}s, anim=打字机)")
except Exception as e:
    print(f"    ❌ 字幕添加失败: {e}")

# ============================================================
# 测试2：添加转场（叠化/交叉溶解）
# ============================================================
print(f"\n[3] 测试添加转场（叠化）")
try:
    # 获取视频轨道
    video_track = project.script.tracks.get("VideoTrack")
    if video_track and video_track.segments:
        last_seg = video_track.segments[-1]
        trans = project.add_transition_simple(
            transition_name="叠化",
            video_segment=last_seg,
            duration="1s"
        )
        if trans:
            print(f"    ✅ 转场添加成功: 叠化 1s")
        else:
            print(f"    ⚠️ 转场未找到（可能名称不匹配）")
    else:
        print(f"    ⚠️ 找不到视频轨道或片段")
except Exception as e:
    print(f"    ❌ 转场添加失败: {e}")

# ============================================================
# 测试3：TTS语音旁白
# ============================================================
print(f"\n[4] 测试TTS语音旁白")
try:
    tts_start = total_sec + 10
    seg = project.add_tts_intelligent(
        "欢迎观看龙龙演讲AI精剪版，这是一条AI自动生成的语音旁白测试。",
        speaker="zh_male_huoli",
        start_time=f"{tts_start}s",
        track_name="AudioTrack",
    )
    print(f"    ✅ TTS添加成功 (speaker=zh_male_huoli)")
except Exception as e:
    print(f"    ❌ TTS添加失败: {e}")

# ============================================================
# 测试4：TTS+字幕同步
# ============================================================
print(f"\n[5] 测试TTS+字幕同步")
try:
    narrated_start = total_sec + 20
    result = project.add_narrated_subtitles(
        "这是自动旁白与字幕对齐的测试内容，AI会同步生成语音和对应字幕。",
        speaker="zh_female_xiaopengyou",
        start_time=f"{narrated_start}s",
        track_name="Subtitles",
    )
    print(f"    ✅ TTS+字幕同步添加成功")
except Exception as e:
    print(f"    ❌ TTS+字幕同步添加失败: {e}")

# ============================================================
# 测试5：添加BGM（云端音乐）
# ============================================================
print(f"\n[6] 测试添加BGM（云端音乐）")
try:
    bgm_start = total_sec
    bgm_seg = project.add_cloud_music(
        query="励志",
        start_time=f"{bgm_start}s",
        duration="10s",
        track_name="BGM_Track"
    )
    if bgm_seg:
        bgm_seg.volume = 0.6
        print(f"    ✅ BGM添加成功，音量=0.6")
    else:
        print(f"    ⚠️ BGM未找到或下载失败")
except Exception as e:
    print(f"    ❌ BGM添加失败: {e}")

# ============================================================
# 测试6：添加特效（先搜索再应用）
# ============================================================
print(f"\n[7] 测试添加视频特效")
try:
    # 先搜索特效ID
    import subprocess
    result = subprocess.run(
        ["python3", "scripts/asset_search.py", "故障", "-c", "video_scene_effects"],
        capture_output=True, text=True,
        cwd="/Users/long/.openclaw/skills/trae-jianying-skill/.trae/skills/jianying-editor"
    )
    eff_output = result.stdout.strip()
    print(f"    搜索结果: {eff_output}")

    effect_start = total_sec + 30
    eff_seg = project.add_effect_simple(
        effect_name="故障_II",
        start_time=f"{effect_start}s",
        duration="2s",
        track_name="EffectTrack"
    )
    if eff_seg:
        print(f"    ✅ 特效添加成功")
    else:
        print(f"    ⚠️ 特效添加返回None（可能需要正确ID）")
except Exception as e:
    print(f"    ❌ 特效添加失败: {e}")

# ============================================================
# 测试7：关键帧动画
# ============================================================
print(f"\n[8] 测试关键帧动画（缩放）")
try:
    # 找到第一个视频片段添加关键帧
    video_track = project.script.tracks.get("VideoTrack")
    if video_track and video_track.segments:
        seg = video_track.segments[0]
        t_start = int(seg.target_timerange.start)
        t_mid = t_start + int(seg.target_timerange.duration / 2)
        t_end = t_start + int(seg.target_timerange.duration)

        # 缩放关键帧：从小到大
        seg.add_keyframe(KP.uniform_scale, t_start, 1.0)
        seg.add_keyframe(KP.uniform_scale, t_mid, 1.3)
        seg.add_keyframe(KP.uniform_scale, t_end, 1.0)
        print(f"    ✅ 关键帧添加成功: 缩放 1.0→1.3→1.0")
    else:
        print(f"    ⚠️ 没有找到视频片段")
except Exception as e:
    print(f"    ❌ 关键帧添加失败: {e}")

# ============================================================
# 测试8：搜索可用的文字动画
# ============================================================
print(f"\n[9] 搜索可用文字动画")
try:
    import subprocess
    result = subprocess.run(
        ["python3", "scripts/asset_search.py", "打字机", "-c", "text_animations"],
        capture_output=True, text=True,
        cwd="/Users/long/.openclaw/skills/trae-jianying-skill/.trae/skills/jianying-editor"
    )
    print(f"    打字机搜索结果: {result.stdout.strip()[:200]}")
except Exception as e:
    print(f"    ⚠️ 搜索失败: {e}")

# ============================================================
# 保存草稿
# ============================================================
print(f"\n[10] 保存草稿")
try:
    project.save()
    print(f"    ✅ 草稿保存成功！")
    print(f"    请在剪映中打开「{DRAFT_NAME}」查看测试效果")
except Exception as e:
    print(f"    ❌ 草稿保存失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
