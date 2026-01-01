#!/usr/bin/env python3
"""
Decode MCC (MacCaption) files using Caption Inspector.
"""

import glob
import os
import re
import subprocess
# import json
# import argparse
# import sys

from typing import Any, Dict, List, Tuple, Optional


from constants import (
    CEA608_FORMAT,
    CEA708_FORMAT,
    TEMP_OUTPUT_DIR,
    DEBUG_LEVELS,
)


def parse_ccd_metadata(output_dir: str) -> Tuple[Optional[float], Optional[bool]]:
    """
    Parse the .ccd file to extract Frame Rate and Drop Frame values.

    Args:
        output_dir: Directory containing the .ccd file

    Returns:
        Tuple of (frame_rate, drop_frame) or (None, None) if not found
    """
    ccd_files = glob.glob(os.path.join(output_dir, "*.ccd"))
    if not ccd_files:
        return None, None

    ccd_file = ccd_files[0]  # Use the first .ccd file found

    frame_rate = None
    drop_frame = None

    with open(ccd_file, "r") as f:
        for line in f:
            line = line.strip()

            # Look for Frame Rate line
            if line.startswith("Frame Rate="):
                try:
                    frame_rate = float(line.split("=")[1])
                except (ValueError, IndexError):
                    pass

            # Look for Drop Frame line
            elif line.startswith("Drop Frame="):
                value = line.split("=")[1].strip()
                drop_frame = bool(value)

            # Stop parsing once we have both values (they appear early in the file)
            if frame_rate is not None and drop_frame is not None:
                break

    # Adjust frame rate for drop frame (29.97 instead of 30, etc.)
    # Drop frame is only applicable to NTSC frame rates (multiples of 30000/1001)
    # The .ccd file reports nominal rates (24, 30, 60) but actual NTSC rates are
    # slightly slower (multiplied by 1000/1001)
    if drop_frame and frame_rate is not None:
        # Common NTSC nominal -> actual frame rate conversions
        ntsc_conversions = {
            24: 24000 / 1001,  # 23.976 - Film for NTSC
            30: 30000 / 1001,  # 29.97  - NTSC standard
            48: 48000 / 1001,  # 47.952 - High frame rate film for NTSC
            60: 60000 / 1001,  # 59.94  - NTSC high frame rate
            120: 120000 / 1001,  # 119.88 - NTSC very high frame rate
        }
        if frame_rate in ntsc_conversions:
            frame_rate = ntsc_conversions[frame_rate]
        # Note: PAL rates (25, 50) don't use drop frame timecode

    return frame_rate, drop_frame


def timecode_to_seconds(
    timecode: str, fps: float = 24.0, drop_frame: bool = False
) -> float:
    """
    Convert timecode (HH:MM:SS:FF or HH:MM:SS;FF) to seconds.

    Args:
        timecode: Timecode string in format HH:MM:SS:FF (non-drop) or HH:MM:SS;FF (drop frame)
        fps: Frames per second
        drop_frame: Whether to use drop frame calculation

    Returns:
        Time in seconds
    """
    # Handle both : and ; separators
    # Note: ; separator typically indicates drop frame timecode
    parts = re.split(r"[:;]", timecode)
    if len(parts) != 4:
        return 0.0

    hours, minutes, seconds, frames = map(int, parts)

    # Check if fps is in the drop frame range (29.97 or 59.94)
    is_2997_fps = 29.9 < fps < 30.1
    is_5994_fps = 59.9 < fps < 60.1

    if drop_frame and (is_2997_fps or is_5994_fps):
        # Drop frame timecode calculation
        # For 29.97fps, 2 frame numbers are dropped every minute except every 10th minute
        # For 59.94fps, 4 frame numbers are dropped
        drop_frames = 2 if is_2997_fps else 4

        # Calculate total minutes
        total_minutes = hours * 60 + minutes

        # Calculate frames dropped (not on 10-minute marks)
        frames_dropped = drop_frames * (total_minutes - (total_minutes // 10))

        # Calculate total frames
        frame_rate_rounded = 30 if is_2997_fps else 60
        total_frames = (
            hours * 3600 * frame_rate_rounded
            + minutes * 60 * frame_rate_rounded
            + seconds * frame_rate_rounded
            + frames
            - frames_dropped
        )

        # Convert to seconds using actual frame rate (29.97 or 59.94)
        actual_fps = 30000 / 1001 if is_2997_fps else 60000 / 1001
        total_seconds = total_frames / actual_fps
    else:
        # Non-drop frame calculation
        total_seconds = hours * 3600 + minutes * 60 + seconds + (frames / fps)

    return total_seconds


def parse_608_file(
    file_path: str, fps: float = 24.0, drop_frame: bool = False
) -> List[Dict[str, Any]]:
    """
    Parse a CEA-608 decode file from Caption Inspector.

    Args:
        file_path: Path to the .608 file
        fps: Frames per second
        drop_frame: Whether to use drop frame calculation

    Returns:
        List of caption cues with start time, end time, and text.
    """
    captions = []

    with open(file_path, "r") as f:
        lines = f.readlines()

    # Skip the header line
    current_caption = None
    last_timecode = None

    for line in lines[1:]:  # Skip header
        line = line.strip()
        if not line:
            continue

        # Match timecode pattern: HH:MM:SS:FF or HH:MM:SS;FF
        tc_match = re.match(r"^(\d{2}:\d{2}:\d{2}[:;]\d{2})\s*-\s*(.*)$", line)
        if not tc_match:
            continue

        timecode = tc_match.group(1)
        content = tc_match.group(2)

        # Extract text in quotes
        text_matches = re.findall(r'"([^"]*)"', content)
        text = " ".join(text_matches).strip()

        # Check for control codes that indicate caption display
        is_display_command = "{EOC}" in content or "{EDM}" in content

        if text:
            # Start a new caption
            if current_caption and current_caption.get("text"):
                # Set end time for previous caption
                current_caption["end"] = timecode_to_seconds(timecode, fps, drop_frame)
                current_caption["end_timecode"] = timecode
                captions.append(current_caption)

            current_caption = {
                "start": timecode_to_seconds(timecode, fps, drop_frame),
                "start_timecode": timecode,
                "end": None,
                "end_timecode": None,
                "text": text,
            }
            last_timecode = timecode

        elif is_display_command and current_caption:
            # End of caption display
            current_caption["end"] = timecode_to_seconds(timecode, fps, drop_frame)
            current_caption["end_timecode"] = timecode
            captions.append(current_caption)
            current_caption = None

    # Add last caption if exists
    if current_caption and current_caption.get("text"):
        if last_timecode:
            current_caption["end"] = (
                current_caption["start"] + 2.0
            )  # Default 2 second duration
            current_caption["end_timecode"] = last_timecode
        captions.append(current_caption)

    return captions


def parse_708_file(
    file_path: str, fps: float = 24.0, drop_frame: bool = False
) -> List[Dict[str, Any]]:
    """
    Parse a CEA-708 decode file from Caption Inspector.

    Args:
        file_path: Path to the .708 file
        fps: Frames per second
        drop_frame: Whether to use drop frame calculation

    Returns:
        List of caption cues with start time, end time, and text.
    """
    captions = []

    with open(file_path, "r") as f:
        lines = f.readlines()

    current_caption = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Match timecode pattern at start of line
        tc_match = re.match(r"^(\d{2}:\d{2}:\d{2}[:;]\d{2})\s*-\s*(.*)$", line)

        if tc_match:
            timecode = tc_match.group(1)
            content = tc_match.group(2)

            # Extract text in quotes
            text_matches = re.findall(r'"([^"]*)"', content)
            text = " ".join(text_matches).strip()

            # Check for display commands
            has_dlw = "{DLW:" in content  # Define Layer Window - indicates new caption

            if text and has_dlw:
                # End previous caption
                if current_caption and current_caption.get("text"):
                    current_caption["end"] = timecode_to_seconds(
                        timecode, fps, drop_frame
                    )
                    current_caption["end_timecode"] = timecode
                    captions.append(current_caption)

                # Start new caption
                current_caption = {
                    "start": timecode_to_seconds(timecode, fps, drop_frame),
                    "start_timecode": timecode,
                    "end": None,
                    "end_timecode": None,
                    "text": text,
                }
        else:
            # Header line or line without timecode - check for text
            text_matches = re.findall(r'"([^"]*)"', line)
            if text_matches and not current_caption:
                # First caption (header line often contains first caption text)
                text = " ".join(text_matches).strip()
                current_caption = {
                    "start": 0.0,
                    "start_timecode": "00:00:00:00",
                    "end": None,
                    "end_timecode": None,
                    "text": text,
                }

    # Add last caption
    if current_caption and current_caption.get("text"):
        if current_caption["end"] is None:
            current_caption["end"] = current_caption["start"] + 2.0
            current_caption["end_timecode"] = current_caption["start_timecode"]
        captions.append(current_caption)

    return captions


def parse_caption_files(output_dir: str, fps: float = None) -> Dict[str, Any]:
    """
    Parse all caption files in the output directory and return a unified JSON structure
    similar to pycaption format.

    The function automatically extracts Frame Rate and Drop Frame values from the .ccd file
    if available, for more accurate timestamp calculation.

    Args:
        output_dir: Directory containing the caption files
        fps: Optional override for frames per second. If None, extracts from .ccd file.

    Returns:
        Dictionary with captions and metadata
    """
    # Extract frame rate and drop frame from .ccd file
    ccd_fps, drop_frame = parse_ccd_metadata(output_dir)

    # Use extracted values or defaults
    if fps is not None:
        # User provided fps override
        actual_fps = fps
        # Try to determine drop frame from ccd or timecode format
        actual_drop_frame = drop_frame if drop_frame is not None else False
    elif ccd_fps is not None:
        actual_fps = ccd_fps
        actual_drop_frame = drop_frame if drop_frame is not None else False
    else:
        # Fallback to defaults
        actual_fps = 24.0
        actual_drop_frame = False

    result = {
        "captions": {
            CEA608_FORMAT: {},
            CEA708_FORMAT: {},
        },
        "metadata": {
            "fps": actual_fps,
            "drop_frame": actual_drop_frame,
            "source_dir": output_dir,
        },
    }

    # Parse CEA-608 files (*.608)
    for f608 in sorted(glob.glob(os.path.join(output_dir, "*.608"))):
        filename = os.path.basename(f608)
        # Extract channel info from filename (e.g., "BigBuckBunny-C1.608" -> "cea608_c1")
        channel_match = re.search(r"-C(\d+)\.608$", filename)
        channel = f"c{channel_match.group(1)}" if channel_match else None

        captions = parse_608_file(f608, actual_fps, actual_drop_frame)
        if captions and channel:
            result["captions"][CEA608_FORMAT][channel] = captions

    # Parse CEA-708 files (*.708)
    for f708 in sorted(glob.glob(os.path.join(output_dir, "*.708"))):
        filename = os.path.basename(f708)
        # Extract service info from filename (e.g., "BigBuckBunny-S1.708" -> "cea708_s1")
        service_match = re.search(r"-S(\d+)\.708$", filename)
        service = f"s{service_match.group(1)}" if service_match else None

        captions = parse_708_file(f708, actual_fps, actual_drop_frame)
        if captions and service:
            result["captions"][CEA708_FORMAT][service] = captions

    return result


def parse_debug_file(output_dir: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Parse a debug file from Caption Inspector and extract all levels (UNKNOWN_DEBUG_LEVEL, VERBOSE, INFO, WARN, ERROR, FATAL, and ASSERT) in their original order.

    Args:
        output_dir: Directory containing the debug file

    Returns:
        List of dictionaries with 'category', 'source', and 'message' keys.
    """
    dbg_files = glob.glob(os.path.join(output_dir, "*.dbg"))
    if not dbg_files:
        return []

    debug_file = dbg_files[0]

    result: List[Dict[str, str]] = []

    # Pattern: LEVEL CATEGORY [source:line] - message
    # Example: WARN DBG_708_DEC [dtvcc_decode.c:342] - Mismatch in Packet length...
    pattern = re.compile(
        r"^(" + "|".join(DEBUG_LEVELS) + ")\s+(\S+)\s+\[([^\]]+)\]\s+-\s+(.*)$"
    )

    with open(debug_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            match = pattern.match(line)
            if match:
                level = match.group(1)
                category = match.group(2)
                source = match.group(3)
                message = match.group(4)

                entry = {
                    "level": level,
                    "category": category,
                    "source": source,
                    "message": message,
                }

                result.append(entry)

    return result


def decode_mcc_file(
    mcc_file_path: str,
    output_dir: str = None,
    fps: float = None,
) -> Dict[str, Any]:
    """
    Decode an MCC file using Caption Inspector and parse results to JSON.

    Args:
        - mcc_file_path: Path to the MCC file
        - output_dir: Optional output directory for decoded files. If None, uses "/tmp/caption_output". If "/tmp/caption_output", the output directory will be cleaned up after the function returns. If a custom directory is provided, it will not be cleaned up.
        - fps: Optional override for frames per second. If None, extracts from .ccd file.
    Returns:
        dict: Parsed caption data in pycaption-like format
    """
    if not os.path.exists(mcc_file_path):
        raise FileNotFoundError(f"MCC file not found: {mcc_file_path}")

    if not mcc_file_path.endswith(".mcc"):
        raise ValueError(f"MCC file must have .mcc extension: {mcc_file_path}")

    content = None
    try:
        # Try the best standard first (handles BOMs automatically)
        with open(mcc_file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback to Latin-1, which reads *any* byte without crashing
        with open(mcc_file_path, "r", encoding="latin-1") as f:
            content = f.read()

    if not content:
        raise ValueError(f"MCC file has no content: {mcc_file_path}")
    if not content.startswith("File Format=MacCaption_MCC"):
        raise ValueError(
            f'MCC file has no proper header "File Format=MacCaption_MCC": {mcc_file_path}'
        )

    # Default output directory
    if output_dir is None:
        output_dir = TEMP_OUTPUT_DIR

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Build Caption Inspector command
    cmd = [
        "caption-inspector",
        "-o",
        output_dir,
        mcc_file_path,
    ]

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            print(f"stderr: {result.stderr}")
            raise RuntimeError(
                f"Caption Inspector failed with code {result.returncode}: {result.stderr}"
            )

    except subprocess.TimeoutExpired:
        raise RuntimeError("Caption Inspector timed out after 300 seconds")
    except FileNotFoundError:
        raise RuntimeError("Caption Inspector not found. Is it installed?")

    # Parse the generated files into JSON format
    parsed_data = parse_caption_files(output_dir, fps)

    # Add file metadata
    output_files = glob.glob(os.path.join(output_dir, "*"))
    parsed_data["metadata"]["input_file"] = mcc_file_path
    parsed_data["metadata"]["output_files"] = output_files

    debug_data = parse_debug_file(output_dir)
    parsed_data["metadata"]["debug"] = debug_data

    if output_dir == TEMP_OUTPUT_DIR:
        # Clean up the temporary output directory
        import shutil

        shutil.rmtree(output_dir)

    return parsed_data


# def main():
#     parser = argparse.ArgumentParser(
#         description="Decode MCC files using Caption Inspector and output as JSON",
#         formatter_class=argparse.RawDescriptionHelpFormatter,
#         epilog="""
# Examples:
#     python MCCDecoder.py samples/BigBuckBunny_256x144-24fps.mcc
#     python MCCDecoder.py samples/BigBuckBunny_256x144-24fps.mcc -o samples/output
#     python MCCDecoder.py input.mcc -o /tmp/decoded --pretty --fps 29.97

# Output format (similar to pycaption):
#     {
#       "captions": {
#         "c1": [
#           {"start": 0.0, "end": 2.5, "text": "Hello world", ...}
#         ],
#         "s1": [...]
#       },
#       "metadata": {...}
#     }
#         """,
#     )
#     parser.add_argument("input_file", help="Path to the MCC file to decode")
#     parser.add_argument(
#         "-o", "--output", dest="output_dir", help="Output directory for decoded files"
#     )
#     parser.add_argument(
#         "--pretty", action="store_true", help="Pretty print JSON output"
#     )
#     parser.add_argument(
#         "--fps",
#         type=float,
#         default=None,
#         help="Override frames per second (auto-detected from .ccd file if not specified)",
#     )
#     parser.add_argument(
#         "--save-json", dest="save_json", help="Save JSON output to file"
#     )

#     args = parser.parse_args()

#     try:
#         print(f"Decoding MCC file: {args.input_file}")
#         result = decode_mcc_file(args.input_file, args.output_dir, args.fps)

#         # Print summary
#         print(f"\nFound {len(result['captions'])} caption tracks:")
#         for track, captions in result["captions"].items():
#             print(f"  - {track}: {len(captions)} captions")

#         # Print JSON result
#         json_output = json.dumps(result, indent=2 if args.pretty else None, default=str)
#         print(f"\n{json_output}")

#         # Save to file if requested
#         if args.save_json:
#             with open(args.save_json, "w") as f:
#                 f.write(json_output)
#             print(f"\nJSON saved to: {args.save_json}")

#         return 0

#     except FileNotFoundError as e:
#         print(f"Error: {e}", file=sys.stderr)
#         return 1
#     except RuntimeError as e:
#         print(f"Error: {e}", file=sys.stderr)
#         return 1
#     except Exception as e:
#         print(f"Unexpected error: {e}", file=sys.stderr)
#         return 1


# if __name__ == "__main__":
#     sys.exit(main())
