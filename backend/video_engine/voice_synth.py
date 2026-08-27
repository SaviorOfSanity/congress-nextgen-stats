"""
AI Voiceover Synthesis Engine for Congressional Scouting Videos
Uses Edge-TTS neural broadcast voices to generate synchronized narration audio.
"""
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
import edge_tts
import imageio_ffmpeg

from backend.config import DEFAULT_VOICE, CACHE_DIR

logger = logging.getLogger(__name__)

def get_audio_duration_seconds(audio_path: Path) -> float:
    """Probe audio file duration using imageio-ffmpeg binary."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        cmd = [ffmpeg_exe, "-i", str(audio_path)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        # Parse Duration: 00:00:05.32 from stderr
        for line in res.stderr.split("\n"):
            if "Duration:" in line:
                dur_str = line.split("Duration:")[1].split(",")[0].strip()
                h, m, s = dur_str.split(":")
                return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception as e:
        logger.warning(f"Could not probe audio duration with ffmpeg: {e}")
    # Default fallback estimate (approx 140 words per minute / 2.3 words per sec)
    return 6.0

async def _synthesize_all_segments(script: Dict[str, str], output_dir: Path, voice: str):
    tasks = []
    for seg_name, text in script.items():
        audio_file = output_dir / f"{seg_name}.mp3"
        comm = edge_tts.Communicate(text, voice, rate="+5%", pitch="+0Hz")
        tasks.append((seg_name, audio_file, comm.save(str(audio_file))))
    
    # Run all saves concurrently
    await asyncio.gather(*(t[2] for t in tasks))
    return [(t[0], t[1]) for t in tasks]

def synthesize_script_segments(
    script: Dict[str, str], 
    output_dir: Path, 
    voice: str = DEFAULT_VOICE
) -> List[Tuple[str, Path, float]]:
    """
    Generate audio for each script segment in parallel and calculate precise playback durations.
    Returns list of (segment_name, audio_path, duration_seconds).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        saved_items = asyncio.run(_synthesize_all_segments(script, output_dir, voice))
    except Exception as e:
        logger.error(f"Async TTS synthesis error: {e}")
        saved_items = [(seg_name, output_dir / f"{seg_name}.mp3") for seg_name in script.keys()]

    results = []
    for seg_name, audio_file in saved_items:
        dur = get_audio_duration_seconds(audio_file)
        results.append((seg_name, audio_file, max(4.0, dur + 0.4)))
        
    return results

def merge_audio_tracks(segments: List[Tuple[str, Path, float]], output_merged_path: Path) -> Path:
    """
    Concatenate all audio segments into a single cohesive voiceover track using ffmpeg.
    """
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    concat_list_file = output_merged_path.parent / "audio_concat_list.txt"
    
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for _, audio_path, _ in segments:
            # Escape path for ffmpeg concat file
            clean_path = str(audio_path).replace("\\", "/")
            f.write(f"file '{clean_path}'\n")
            
    cmd = [
        ffmpeg_exe, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(output_merged_path)
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return output_merged_path
