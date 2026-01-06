import re
from typing import Any, Dict, List

from ..utils import timecode_to_microseconds

# CEA-608 color mappings from Caption Inspector
# PAC colors (Preamble Address Code)
PAC_COLORS = {
    "white": "#FFFFFF",
    "green": "#00FF00",
    "blue": "#0000FF",
    "cyan": "#00FFFF",
    "red": "#FF0000",
    "yellow": "#FFFF00",
    "magenta": "#FF00FF",
    "black": "#000000",
    "italic white": "#FFFFFF",  # Special style + color combo
}

# Mid-row foreground styles (includes Italic White)
# Note: Black is technically only a background color in CEA-608 spec,
# but we support it as foreground for flexibility
MIDROW_FG_STYLES = {
    "white": "#FFFFFF",
    "green": "#00FF00",
    "blue": "#0000FF",
    "cyan": "#00FFFF",
    "red": "#FF0000",
    "yellow": "#FFFF00",
    "magenta": "#FF00FF",
    "black": "#000000",
    "italic white": "#FFFFFF",
}

# Mid-row background colors
MIDROW_BG_COLORS = {
    "white": "#FFFFFF",
    "green": "#00FF00",
    "blue": "#0000FF",
    "cyan": "#00FFFF",
    "red": "#FF0000",
    "yellow": "#FFFF00",
    "magenta": "#FF00FF",
    "black": "#000000",
}

# CEA-608 control code descriptions
CONTROL_CODES = {
    "RCL": "Resume Caption Loading",
    "BS": "Backspace",
    "AOF": "Alarm Off",
    "AON": "Alarm On",
    "DER": "Delete to End of Row",
    "RU2": "Roll Up Captions Two Rows",
    "RU3": "Roll Up Captions Three Rows",
    "RU4": "Roll Up Captions Four Rows",
    "FON": "Flash On",
    "RDC": "Resume Direct Captioning",
    "TR": "Text Restart",
    "RTD": "Resume Text Display",
    "EDM": "Erase Displayed Memory",
    "CR": "Carriage Return",
    "ENM": "Erase Non-Displayed Memory",
    "EOC": "End Of Caption",
}


def parse_608_style(content: str) -> Dict[str, Any]:
    """
    Extract style information from CEA-608 content.

    Caption Inspector formats:
    - Foreground/style: {FG-<style>:PT:UL} where style can be color or "Italic White"
    - Background: {BG-<color>:PT:UL}
    - PAC with color: {R<row>:<color>:UL}
    - PAC with cursor: {R<row>:C<col>:UL}

    IMPORTANT: Style codes only apply to text that comes AFTER them.
    A style code that appears after all text in a line does NOT apply to that text.

    Args:
        content: The content string containing style codes

    Returns:
        Dictionary with CSS-like styling rules
    """
    style = {}

    # Find the position of the first text segment (quoted text)
    # Style codes must appear BEFORE text to apply to it
    first_text_match = re.search(r'"[^"]*"', content)
    first_text_pos = first_text_match.start() if first_text_match else len(content)

    # Only look at content BEFORE the first text for style codes
    # that should apply to the text
    content_before_text = content[:first_text_pos]

    # Extract foreground color/style: {FG-Italic-White:PT:UL}, {FG-White}, etc.
    # Caption Inspector format from MidRowControlCode.__str__(): '{FG-' + self.style + ...
    fg_match = re.search(r"\{FG-([^}]+)\}", content_before_text)
    if fg_match:
        fg_content = fg_match.group(1)

        # Split by colon to separate style from flags
        parts = fg_content.split(":")
        fg_style = parts[0]
        fg_flags = ":".join(parts[1:]) if len(parts) > 1 else ""

        # Handle "Italic White" as a special combo (hyphenated in output)
        fg_style_normalized = fg_style.replace("-", " ").lower().strip()

        if fg_style_normalized == "italic white":
            style["font-style"] = "italic"
            style["color"] = "white"
        elif fg_style_normalized in MIDROW_FG_STYLES:
            style["color"] = fg_style_normalized
        else:
            # Try individual parts (e.g., "Italic-White" split)
            style_parts = fg_style.split("-")
            for part in style_parts:
                part_lower = part.lower().strip()
                if part_lower in MIDROW_FG_STYLES:
                    style["color"] = part_lower
                elif part_lower == "italic":
                    style["font-style"] = "italic"

        # Check flags (PT = Partially Transparent, UL = Underline)
        if "PT" in fg_flags:
            style["partially_transparent"] = True
        if "UL" in fg_flags:
            style["text-decoration"] = "underline"

    # Extract background color: {BG-<color>:PT:UL}
    # Caption Inspector format from MidRowControlCode.__str__(): '{BG-' + self.color + ...
    bg_match = re.search(r"\{BG-([^}:]+)(?::([^}]+))?\}", content_before_text)
    if bg_match:
        bg_color = bg_match.group(1).lower()
        bg_flags = bg_match.group(2) or ""

        if bg_color in MIDROW_BG_COLORS:
            style["background-color"] = bg_color

        if "PT" in bg_flags:
            style["background_partially_transparent"] = True
        if "UL" in bg_flags:
            style["text-decoration"] = "underline"

    # Extract standalone PAC color codes like {R4:Yellow} or {R4:Yellow:UL}
    # Caption Inspector format from PreambleAccessCode.__str__(): '{R' + row + ':' + color + ...
    # Only consider PAC codes that appear BEFORE the first text
    color_match = re.search(
        r"\{R\d+:([A-Za-z][A-Za-z ]+)(?::UL)?\}", content_before_text
    )
    if color_match and "color" not in style:
        color = color_match.group(1).lower()
        if color == "italic white":
            style["color"] = "white"
            style["font-style"] = "italic"
        elif color in PAC_COLORS:
            style["color"] = color

    # Check for underline in PAC format: {R<row>:<something>:UL}
    if re.search(r"\{R\d+:[^}]+:UL\}", content_before_text):
        style["text-decoration"] = "underline"

    # Check for standalone underline marker (only before text)
    if "{UL}" in content_before_text:
        style["text-decoration"] = "underline"

    return style


def parse_608_text_with_positions(content: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Parse CEA-608 content to extract text with line breaks based on row positions.

    When row position changes (e.g., {R14:C8} to {R15:C4}), insert a line break.
    Caption Inspector format from PreambleAccessCode.__str__(): '{R' + row + ':C' + col + ...

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

    # Split content into segments by finding row positions with column
    # Pattern: everything from {R##:C##} until the next {R##:C##} or end
    segments = re.split(r"(?=\{R\d+:C\d+)", content)

    for segment in segments:
        if not segment.strip():
            continue

        # Extract row/column from this segment (format: {R<row>:C<col>...})
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

    Caption Inspector formats:
    - PAC position: {R<row>:C<col>} or {R<row>:C<col>:UL}
    - Tab offset: {TO<1-3>}
    - Control codes: {RCL}, {RDC}, {RU2}, {RU3}, {RU4}, {EDM}, {EOC}, {CR}, etc.

    Args:
        content: The content string containing position codes

    Returns:
        Layout object with positioning information
    """
    layout = {}

    # Extract row position with cursor column: {R14:C8} or {R15:C0}
    # Caption Inspector format from PreambleAccessCode
    row_col_matches = re.findall(r"\{R(\d+):C(\d+)", content)
    if row_col_matches:
        # Use the first position found (primary position)
        row, col = row_col_matches[0]
        layout["row"] = int(row)
        layout["column"] = int(col)

        # CEA-608 has 15 rows (1-15 typically, but Caption Inspector uses 0-14)
        # Row 0/1 is top, Row 14/15 is bottom
        layout["vertical_percent"] = (int(row) / 14) * 100

        # CEA-608 has 32 columns (0-31), convert to percentage
        layout["horizontal_percent"] = (int(col) / 31) * 100

        # Store all positions for multi-line captions
        if len(row_col_matches) > 1:
            layout["all_positions"] = [
                {"row": int(r), "column": int(c)} for r, c in row_col_matches
            ]

    # Extract row position with color (PAC style mode): {R14:Yellow} or {R14:Italic White}
    row_color_match = re.search(r"\{R(\d+):([A-Za-z][A-Za-z ]+)(?::UL)?\}", content)
    if row_color_match and "row" not in layout:
        row = int(row_color_match.group(1))
        layout["row"] = row
        layout["vertical_percent"] = (row / 14) * 100

    # Extract tab offset: {TO1}, {TO2}, {TO3}
    # Caption Inspector format from TabControlCode.__str__(): '{TO' + str(self.tab_offset) + '}'
    tab_match = re.search(r"\{TO(\d+)\}", content)
    if tab_match:
        layout["tab_offset"] = int(tab_match.group(1))

    # Determine caption mode from control codes
    # Caption Inspector control codes from global_ctrl_name_trans_dict
    if "{RDC}" in content:
        layout["mode"] = "paint-on"  # Resume Direct Captioning
    elif "{RCL}" in content:
        layout["mode"] = "pop-on"  # Resume Caption Loading
    elif "{RU2}" in content:
        layout["mode"] = "roll-up"
        layout["roll_up_rows"] = 2
    elif "{RU3}" in content:
        layout["mode"] = "roll-up"
        layout["roll_up_rows"] = 3
    elif "{RU4}" in content:
        layout["mode"] = "roll-up"
        layout["roll_up_rows"] = 4

    # Extract other control codes present
    control_codes_found = []
    for code in CONTROL_CODES:
        if "{" + code + "}" in content:
            control_codes_found.append(code)
    if control_codes_found:
        layout["control_codes"] = control_codes_found

    return layout


def parse_608_file(
    file_path: str, fps: float = 24.0, drop_frame: bool = False
) -> List[Dict[str, Any]]:
    """
    Parse a CEA-608 decode file from Caption Inspector.

    File format (from Caption Inspector):
    - Header line with channel info
    - Lines with format: HH:MM:SS:FF - <content>
    - Content includes PAC codes, control codes, and text in quotes

    CEA-608 Caption Modes:
    - Paint-on (RDC): Text appears immediately as it's received
    - Pop-on (RCL): Text loads into buffer, displays on EOC command
    - Roll-up (RU2/RU3/RU4): Text scrolls up as new lines arrive

    Timing:
    - Paint-on captions: START when text received, END at EOC/EDM
    - Pop-on captions: START at EOC (when displayed), END at next EOC/EDM
    - EOC = End of Caption (swaps buffers, displays loaded caption)
    - EDM = Erase Displayed Memory (clears visible captions)

    Args:
        file_path: Path to the .608 file
        fps: Frames per second
        drop_frame: Whether to use drop frame calculation

    Returns:
        List of caption cues with start time, end time, text, style, and layout.
    """
    captions = []

    with open(file_path, "r", encoding="latin-1") as f:
        file_lines = f.readlines()

    # Track displayed caption (what's currently visible on screen)
    displayed_caption = None
    # Track loading caption (pop-on buffer being filled)
    loading_caption = None

    for line in file_lines[1:]:  # Skip header
        line = line.strip()
        if not line:
            continue

        # Match timecode pattern: HH:MM:SS:FF or HH:MM:SS;FF (drop frame)
        tc_match = re.match(r"^(\d{2}:\d{2}:\d{2}[:;]\d{2})\s*-\s*(.*)$", line)
        if not tc_match:
            continue

        timecode = tc_match.group(1)
        content = tc_match.group(2)
        current_time = timecode_to_microseconds(timecode, fps, drop_frame)

        # Extract text with line breaks based on row positions
        text, text_lines = parse_608_text_with_positions(content)

        # Check for control codes
        is_eoc = "{EOC}" in content  # End of Caption - displays pop-on
        is_edm = "{EDM}" in content  # Erase Displayed Memory
        is_pop_on = "{RCL}" in content  # Resume Caption Loading (pop-on mode)
        is_paint_on = "{RDC}" in content  # Resume Direct Captioning (paint-on mode)
        is_roll_up = "{RU2}" in content or "{RU3}" in content or "{RU4}" in content

        # Handle EOC - displays the loaded pop-on caption
        if is_eoc:
            # End the currently displayed caption
            if displayed_caption and displayed_caption.get("text"):
                displayed_caption["end"] = current_time
                displayed_caption["end_timecode"] = timecode
                captions.append(displayed_caption)
                displayed_caption = None

            # The loading caption becomes the displayed caption
            if loading_caption and loading_caption.get("text"):
                loading_caption["start"] = current_time
                loading_caption["start_timecode"] = timecode
                displayed_caption = loading_caption
                loading_caption = None

        # Handle EDM - erases displayed memory
        elif is_edm:
            if displayed_caption and displayed_caption.get("text"):
                displayed_caption["end"] = current_time
                displayed_caption["end_timecode"] = timecode
                captions.append(displayed_caption)
                displayed_caption = None

        # Handle text content
        elif text:
            # Extract style and layout information
            style = parse_608_style(content)
            layout = parse_608_layout(content)

            if text_lines:
                layout["lines"] = text_lines

            caption_data = {
                "start": current_time,
                "start_timecode": timecode,
                "end": None,
                "end_timecode": None,
                "text": text,
                "style": style if style else None,
                "layout": layout if layout else None,
            }

            if is_pop_on:
                # Pop-on mode: load into buffer (will display at EOC)
                loading_caption = caption_data
            elif is_paint_on or is_roll_up:
                # Paint-on/Roll-up mode: displays immediately
                # End any currently displayed caption first
                if displayed_caption and displayed_caption.get("text"):
                    displayed_caption["end"] = current_time
                    displayed_caption["end_timecode"] = timecode
                    captions.append(displayed_caption)

                displayed_caption = caption_data
            else:
                # No explicit mode - check if we're continuing a previous mode
                # Default to loading into buffer if no mode specified
                if loading_caption is not None:
                    # Continue loading (append to existing buffer)
                    loading_caption = caption_data
                elif displayed_caption is not None:
                    # Continue paint-on mode
                    displayed_caption["end"] = current_time
                    displayed_caption["end_timecode"] = timecode
                    captions.append(displayed_caption)
                    displayed_caption = caption_data
                else:
                    # First caption - assume paint-on
                    displayed_caption = caption_data

    # Add any remaining displayed caption
    # Note: end time is left as None if unknown - consuming application decides
    if displayed_caption and displayed_caption.get("text"):
        if displayed_caption not in captions:
            captions.append(displayed_caption)

    # Add any remaining loading caption (shouldn't normally happen - means EOC was missing)
    if loading_caption and loading_caption.get("text"):
        if loading_caption not in captions:
            captions.append(loading_caption)

    return captions
