from typing import Dict, List
import glob
import os
import re
from ..constants import DEBUG_LEVELS


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
        r"^(" + "|".join(DEBUG_LEVELS) + r")\s+(\S+)\s+\[([^\]]+)\]\s+-\s+(.*)$"
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
