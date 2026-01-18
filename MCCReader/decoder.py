"""
Decode MCC (MacCaption) files using Caption Inspector.
"""

import glob
import os
import re
import subprocess

from typing import Any, Dict


from .constants import (
    CEA608_FORMAT,
    CEA708_FORMAT,
    TEMP_OUTPUT_DIR,
)

from .parsers.ccd_parser import parse_ccd_metadata
from .parsers.cea608_parser import parse_608_file
from .parsers.cea708_parser import parse_708_file
from .parsers.dbg_parser import parse_debug_file


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

    if not mcc_file_path.lower().endswith(".mcc"):
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
