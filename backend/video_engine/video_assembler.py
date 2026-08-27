"""
Ultra-Fast Native Video Assembler and Encoder for Congressional NextGenStats
Renders broadcast scouting videos in seconds using optimized FFmpeg stream pipelines.
"""
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
import imageio_ffmpeg

from backend.config import VIDEOS_DIR, CARDS_DIR
from backend.models import CongressionalProfile
from backend.video_engine.graphics_generator import generate_all_slides
from backend.video_engine.commentator import generate_commentator_script
from backend.video_engine.voice_synth import synthesize_script_segments

logger = logging.getLogger(__name__)

def render_scouting_video(
    profile: CongressionalProfile,
    is_vertical: bool = True,
    fps: int = 30
) -> Path:
    """
    Render and export complete broadcast scouting video (.mp4) with synced AI voiceover.
    Uses direct FFmpeg stream muxing for blazing-fast multi-segment rendering.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    member_slug = profile.bio.full_name.lower().replace(" ", "_")
    orientation = "shorts" if is_vertical else "broadcast"
    work_dir = CARDS_DIR / f"{member_slug}_{orientation}"
    work_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Generate Visual Slides
    logger.info(f"Generating visual slides for {profile.bio.full_name} ({orientation})...")
    slide_paths = generate_all_slides(profile, is_vertical=is_vertical)
    slide_map = {p.stem: p for p in slide_paths}
    
    # 2. Generate Commentator Script
    logger.info("Generating commentator script...")
    script = generate_commentator_script(profile)
    
    # 3. Synthesize Audio per Segment
    logger.info("Synthesizing neural voiceover audio...")
    audio_segments = synthesize_script_segments(script, work_dir)
    
    # 4. Render Individual Segment Videos
    segment_mp4_paths: List[Path] = []
    logger.info("Rendering video segments with FFmpeg...")
    
    for idx, (seg_name, audio_path, duration) in enumerate(audio_segments):
        slide_path = slide_map.get(seg_name)
        if not slide_path or not slide_path.exists():
            continue
            
        seg_mp4 = work_dir / f"segment_{idx:02d}_{seg_name}.mp4"
        
        # FFmpeg command with explicit duration for instant completion
        cmd = [
            ffmpeg_exe, "-y",
            "-loop", "1",
            "-framerate", str(fps),
            "-i", str(slide_path),
            "-i", str(audio_path),
            "-t", f"{duration:.2f}",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(seg_mp4)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg segment error: {res.stderr}")
            raise RuntimeError(f"Failed rendering segment {seg_name}: {res.stderr}")
            
        segment_mp4_paths.append(seg_mp4)
        
    # 5. Concatenate Segments into Final MP4 Video
    final_video_path = VIDEOS_DIR / f"{member_slug}_{orientation}.mp4"
    concat_list_file = work_dir / "video_concat_list.txt"
    
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in segment_mp4_paths:
            clean_path = str(p.resolve()).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")
            
    logger.info("Muxing final video stream...")
    concat_cmd = [
        ffmpeg_exe, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(final_video_path)
    ]
    res = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        logger.error(f"FFmpeg concat error: {res.stderr}")
        raise RuntimeError(f"Failed concatenating segments: {res.stderr}")

    logger.info(f"Video successfully rendered to: {final_video_path}")
    return final_video_path
