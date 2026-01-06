import os
import glob
from typing import Tuple, Optional


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
                drop_frame = value.lower() == "true"

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
