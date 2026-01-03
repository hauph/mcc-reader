import re
from typing import Any, Dict, List

from utils import timecode_to_seconds


def parse_608_style(content: str) -> Dict[str, Any]:
    """
    Extract style information from CEA-608 content.

    Args:
        content: The content string containing style codes

    Returns:
        Dictionary with CSS-like styling rules
    """
    style = {}

    # Extract foreground color/style: {FG-Italic-White}, {R4:Yellow}, etc.
    fg_match = re.search(r"\{FG-([^}]+)\}", content)
    if fg_match:
        fg_parts = fg_match.group(1).split("-")
        for part in fg_parts:
            part_lower = part.lower()
            if part_lower in (
                "white",
                "green",
                "blue",
                "cyan",
                "red",
                "yellow",
                "magenta",
                "black",
            ):
                style["color"] = part_lower
            elif part_lower == "italic":
                style["font-style"] = "italic"
            elif part_lower == "underline":
                style["text-decoration"] = "underline"

    # Extract standalone color codes like {R4:Yellow}
    color_match = re.search(r"\{R\d+:(\w+)\}", content)
    if color_match and "color" not in style:
        color = color_match.group(1).lower()
        if color in (
            "white",
            "green",
            "blue",
            "cyan",
            "red",
            "yellow",
            "magenta",
            "black",
        ):
            style["color"] = color

    # Check for underline
    if "{UL}" in content or ":UL}" in content:
        style["text-decoration"] = "underline"

    return style


def parse_608_text_with_positions(content: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Parse CEA-608 content to extract text with line breaks based on row positions.

    When row position changes (e.g., {R14:C8} to {R15:C4}), insert a line break.

    Args:
        content: The content string containing position codes and text

    Returns:
        Tuple of (formatted_text_with_linebreaks, list_of_lines_with_positions)
    """
    lines = []
    current_row = None
    current_line_text = []
    current_line_col = None

    # Pattern to match position codes followed by optional text
    # This handles: {R14:C8} {TO3} "text" or {R15:C4} "text"
    # We need to find each text segment and its preceding row position

    # Split content into segments by finding row positions
    # Pattern: everything from {R##:C##} until the next {R##:C##} or end
    segments = re.split(r"(?=\{R\d+:C\d+)", content)

    for segment in segments:
        if not segment.strip():
            continue

        # Extract row/column from this segment
        row_match = re.search(r"\{R(\d+):C(\d+)", segment)
        # Extract text from this segment
        text_matches = re.findall(r'"([^"]*)"', segment)

        if row_match and text_matches:
            row = int(row_match.group(1))
            col = int(row_match.group(2))
            text = " ".join(text_matches).strip()

            if current_row is not None and row != current_row:
                # Row changed - save current line and start new one
                if current_line_text:
                    lines.append(
                        {
                            "row": current_row,
                            "column": current_line_col,
                            "text": " ".join(current_line_text),
                        }
                    )
                current_line_text = [text]
                current_line_col = col
            else:
                # Same row or first segment
                current_line_text.append(text)
                if current_line_col is None:
                    current_line_col = col

            current_row = row

        elif text_matches and current_row is not None:
            # Text without new position - append to current line
            current_line_text.append(" ".join(text_matches).strip())

    # Don't forget the last line
    if current_line_text:
        lines.append(
            {
                "row": current_row,
                "column": current_line_col,
                "text": " ".join(current_line_text),
            }
        )

    # Sort lines by row number (top to bottom)
    lines.sort(key=lambda x: x["row"])

    # Join lines with newline character
    formatted_text = "\n".join(line["text"] for line in lines)

    return formatted_text, lines


def parse_608_layout(content: str) -> Dict[str, Any]:
    """
    Extract layout/positioning information from CEA-608 content.

    Args:
        content: The content string containing position codes

    Returns:
        Layout object with positioning information
    """
    layout = {}

    # Extract row position: {R14:C8} or {R15:C0}
    row_col_matches = re.findall(r"\{R(\d+):C(\d+)", content)
    if row_col_matches:
        # Use the first position found (primary position)
        row, col = row_col_matches[0]
        layout["row"] = int(row)
        layout["column"] = int(col)

        # CEA-608 has 15 rows (0-14), convert to percentage
        # Row 0 is top, Row 14 is bottom
        layout["vertical_percent"] = (int(row) / 14) * 100

        # CEA-608 has 32 columns (0-31), convert to percentage
        layout["horizontal_percent"] = (int(col) / 31) * 100

    # Extract tab offset: {TO1}, {TO2}, {TO3}
    tab_match = re.search(r"\{TO(\d+)\}", content)
    if tab_match:
        layout["tab_offset"] = int(tab_match.group(1))

    # Determine caption mode from control codes
    if "{RDC}" in content:
        layout["mode"] = "paint-on"
    elif "{RCL}" in content:
        layout["mode"] = "pop-on"
    elif "{RU2}" in content or "{RU3}" in content or "{RU4}" in content:
        layout["mode"] = "roll-up"

    return layout


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
        List of caption cues with start time, end time, text, style, and layout.
    """
    captions = []

    with open(file_path, "r") as f:
        file_lines = f.readlines()

    # Skip the header line
    current_caption = None
    last_timecode = None

    for line in file_lines[1:]:  # Skip header
        line = line.strip()
        if not line:
            continue

        # Match timecode pattern: HH:MM:SS:FF or HH:MM:SS;FF
        tc_match = re.match(r"^(\d{2}:\d{2}:\d{2}[:;]\d{2})\s*-\s*(.*)$", line)
        if not tc_match:
            continue

        timecode = tc_match.group(1)
        content = tc_match.group(2)

        # Extract text with line breaks based on row positions
        text, text_lines = parse_608_text_with_positions(content)

        # Check for control codes that indicate caption display
        is_display_command = "{EOC}" in content or "{EDM}" in content

        if text:
            # Extract style and layout information
            style = parse_608_style(content)
            layout = parse_608_layout(content)

            # Add the individual lines with positions to layout
            if text_lines:
                layout["lines"] = text_lines

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
                "style": style if style else None,
                "layout": layout if layout else None,
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
