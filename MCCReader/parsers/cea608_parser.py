import re
from typing import Any, Dict, List

from ..utils import timecode_to_microseconds

from ..models import MIDROW_FG_STYLES, MIDROW_BG_COLORS, PAC_COLORS, CONTROL_CODES


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


def parse_608_text_segments(
    content: str,
) -> tuple[str, Dict[str, Any] | None, List[Dict[str, Any]] | None]:
    """
    Parse CEA-608 content to extract text with style segments.

    Style commands (FG, BG, PAC with color) apply to subsequent text until changed.
    This function tracks style changes and associates each text segment
    with its applicable style.

    Args:
        content: The content string containing style and position codes

    Returns:
        Tuple of (full_text, style, segments):
        - full_text: Complete text with newlines
        - style: Single style dict if all text has same style, None if multiple styles
        - segments: List of {text, style} dicts if multiple styles, None if single style
    """
    # Find all style commands and their positions
    # FG (foreground): {FG-<color>} or {FG-<color>:PT:UL}
    fg_pattern = re.compile(r"\{FG-([^}]+)\}")
    # BG (background): {BG-<color>} or {BG-<color>:PT:UL}
    bg_pattern = re.compile(r"\{BG-([^}:]+)(?::([^}]+))?\}")
    # PAC with color: {R<row>:<color>} or {R<row>:<color>:UL}
    pac_color_pattern = re.compile(r"\{R(\d+):([A-Za-z][A-Za-z ]+)(?::UL)?\}")
    # PAC with position: {R<row>:C<col>} or {R<row>:C<col>:UL}
    pac_pos_pattern = re.compile(r"\{R(\d+):C(\d+)(?::UL)?\}")
    # Standalone underline
    ul_pattern = re.compile(r"\{UL\}")
    # Text pattern
    text_pattern = re.compile(r'"([^"]*)"')

    # Build list of (position, type, data) tuples
    events = []

    # Collect FG style commands
    for match in fg_pattern.finditer(content):
        events.append((match.start(), "fg", match.group(1)))

    # Collect BG style commands
    for match in bg_pattern.finditer(content):
        color = match.group(1)
        flags = match.group(2) or ""
        events.append((match.start(), "bg", (color, flags)))

    # Collect PAC with color
    for match in pac_color_pattern.finditer(content):
        row = int(match.group(1))
        color = match.group(2)
        has_ul = ":UL" in match.group(0)
        events.append((match.start(), "pac_color", (row, color, has_ul)))

    # Collect PAC with position
    for match in pac_pos_pattern.finditer(content):
        row = int(match.group(1))
        col = int(match.group(2))
        has_ul = ":UL" in match.group(0)
        events.append((match.start(), "pac_pos", (row, col, has_ul)))

    # Collect standalone underline
    for match in ul_pattern.finditer(content):
        events.append((match.start(), "ul", True))

    # Collect text segments
    for match in text_pattern.finditer(content):
        text = match.group(1)
        if text:  # Skip empty strings
            events.append((match.start(), "text", text))

    # Sort events by position
    events.sort(key=lambda x: x[0])

    # Process events sequentially, tracking current style and row
    current_style = {}
    current_row = 0
    segments = []

    for _, event_type, data in events:
        if event_type == "fg":
            fg_content = data
            # Split by colon to separate style from flags
            parts = fg_content.split(":")
            fg_style = parts[0]
            fg_flags = ":".join(parts[1:]) if len(parts) > 1 else ""

            # Handle "Italic White" as a special combo
            fg_style_normalized = fg_style.replace("-", " ").lower().strip()

            if fg_style_normalized == "italic white":
                current_style["font-style"] = "italic"
                current_style["color"] = "white"
            elif fg_style_normalized in MIDROW_FG_STYLES:
                current_style["color"] = fg_style_normalized
            else:
                # Try individual parts
                style_parts = fg_style.split("-")
                for part in style_parts:
                    part_lower = part.lower().strip()
                    if part_lower in MIDROW_FG_STYLES:
                        current_style["color"] = part_lower
                    elif part_lower == "italic":
                        current_style["font-style"] = "italic"

            if "PT" in fg_flags:
                current_style["partially_transparent"] = True
            if "UL" in fg_flags:
                current_style["text-decoration"] = "underline"

        elif event_type == "bg":
            color, flags = data
            bg_color = color.lower()
            if bg_color in MIDROW_BG_COLORS:
                current_style["background-color"] = bg_color

            if "PT" in flags:
                current_style["background_partially_transparent"] = True
            if "UL" in flags:
                current_style["text-decoration"] = "underline"

        elif event_type == "pac_color":
            row, color, has_ul = data
            current_row = row
            color_lower = color.lower()
            if color_lower == "italic white":
                current_style["color"] = "white"
                current_style["font-style"] = "italic"
            elif color_lower in PAC_COLORS:
                current_style["color"] = color_lower
            if has_ul:
                current_style["text-decoration"] = "underline"

        elif event_type == "pac_pos":
            row, col, has_ul = data
            current_row = row
            if has_ul:
                current_style["text-decoration"] = "underline"

        elif event_type == "ul":
            current_style["text-decoration"] = "underline"

        elif event_type == "text":
            text = data
            segments.append(
                {
                    "text": text,
                    "style": dict(current_style) if current_style else None,
                    "row": current_row,
                }
            )

    if not segments:
        return "", None, None

    # Sort segments by row
    segments.sort(key=lambda x: x["row"])

    # Build full text with newlines between different rows
    full_text_parts = []
    prev_row = None
    for seg in segments:
        if prev_row is not None and seg["row"] != prev_row:
            # Add newline when row changes
            if full_text_parts:
                full_text_parts[-1] = full_text_parts[-1] + "\n"
        full_text_parts.append(seg["text"])
        prev_row = seg["row"]

    full_text = "".join(full_text_parts)

    # Check if all segments have the same style
    styles = [seg["style"] for seg in segments]
    all_same_style = all(s == styles[0] for s in styles)

    if all_same_style:
        # Single style - return style at top level, no segments
        return full_text, styles[0], None
    else:
        # Multiple styles - build segments with text including newlines
        result_segments = []
        for i, seg in enumerate(segments):
            seg_text = seg["text"]
            # Add newline to text if row changes after this segment
            if i < len(segments) - 1 and segments[i + 1]["row"] != seg["row"]:
                seg_text += "\n"
            result_seg = {"text": seg_text}
            if seg["style"]:
                result_seg["style"] = seg["style"]
            result_segments.append(result_seg)

        return full_text, None, result_segments


def parse_608_text_with_positions(content: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Parse CEA-608 content to extract text with line breaks based on row positions.

    When row position changes (e.g., {R14:C8} to {R15:C4}), insert a line break.
    Caption Inspector format from PreambleAccessCode.__str__(): '{R' + row + ':C' + col + ...

    Text can appear:
    - After {R##:C##} tags (explicit position)
    - Before any position tag (uses default row 0 or continues from previous)

    Args:
        content: The content string containing position codes and text

    Returns:
        Tuple of (formatted_text_with_linebreaks, list_of_lines_with_positions)
    """
    lines = []
    current_row = None
    current_line_text = []
    current_line_col = None

    # Default row for text that appears before any position marker
    default_row = 0

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

        if text_matches:
            text = " ".join(text_matches).strip()
            if not text:
                continue

            if row_match:
                # Text after position marker - use explicit position
                row = int(row_match.group(1))
                col = int(row_match.group(2))

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
                    # Same row or first segment with position
                    current_line_text.append(text)
                    if current_line_col is None:
                        current_line_col = col

                current_row = row
            else:
                # Text without position marker
                if current_row is not None:
                    # Continue from previous row
                    current_line_text.append(text)
                else:
                    # No previous row - use default row 0
                    current_row = default_row
                    current_line_col = 0
                    current_line_text.append(text)

    # Don't forget the last line
    if current_line_text and current_row is not None:
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


def _merge_caption_text(
    caption: Dict[str, Any],
    new_text: str,
    new_lines: List[Dict[str, Any]],
    new_style: Dict[str, Any] | None,
    new_segments: List[Dict[str, Any]] | None,
) -> None:
    """
    Merge new text into an existing caption buffer (for pop-on mode continuation).

    Text without explicit position markers should continue on the last row.
    Text with position markers starts on the specified row.

    Args:
        caption: The existing caption dict to merge into (modified in place)
        new_text: The new text to merge
        new_lines: Position information for the new text
        new_style: Style for the new text (if single style)
        new_segments: Segments for the new text (if multiple styles)
    """
    if not caption.get("layout"):
        caption["layout"] = {}

    existing_lines = caption["layout"].get("lines", [])

    # Find the last row in the existing caption
    last_row = 0
    if existing_lines:
        last_row = max(line["row"] for line in existing_lines)

    # Process new lines - if a line has row 0 and column 0, it likely means
    # no position was specified, so it should continue on the last row
    adjusted_lines = []
    for line in new_lines:
        if line["row"] == 0 and line["column"] == 0 and existing_lines:
            # No explicit position - continue on last row
            # Find if there's already text on the last row
            found_last_row = False
            for existing in existing_lines:
                if existing["row"] == last_row:
                    # Append to existing text on this row
                    existing["text"] += " " + line["text"]
                    found_last_row = True
                    break
            if not found_last_row:
                # Add to last row
                adjusted_lines.append(
                    {"row": last_row, "column": 0, "text": line["text"]}
                )
        else:
            # Explicit position specified
            adjusted_lines.append(line)

    # Add the adjusted lines to existing
    caption["layout"]["lines"] = existing_lines + adjusted_lines

    # Rebuild the text from all lines
    all_lines = caption["layout"]["lines"]
    # Sort by row
    all_lines.sort(key=lambda x: x["row"])
    caption["text"] = "\n".join(line["text"] for line in all_lines)

    # Handle style/segments merging
    # Get text that was added (for segment creation)
    added_text_parts = []
    for line in new_lines:
        if line["row"] == 0 and line["column"] == 0 and len(existing_lines) > 0:
            # This text was appended to existing row, find it
            for existing in existing_lines:
                if existing["row"] == last_row:
                    # The appended text (with leading space)
                    added_text_parts.append(line["text"])
                    break
        else:
            added_text_parts.append(line["text"])

    if new_segments:
        existing_segments = caption.get("segments", [])
        if existing_segments:
            caption["segments"] = existing_segments + new_segments
        else:
            # Convert from single style to segments
            if caption.get("style"):
                old_lines = [
                    line
                    for line in all_lines
                    if line not in adjusted_lines and line not in new_lines
                ]
                old_text = "\n".join(line["text"] for line in old_lines)
                if old_text:
                    caption["segments"] = [
                        {"text": old_text + "\n", "style": caption["style"]}
                    ] + new_segments
                else:
                    caption["segments"] = new_segments
            else:
                caption["segments"] = new_segments
            caption["style"] = None
    elif caption.get("segments"):
        # Caption already has segments - add new text as segment
        if new_style or added_text_parts:
            added_text = "\n".join(added_text_parts) if added_text_parts else new_text
            seg = {"text": " " + added_text}
            if new_style:
                seg["style"] = new_style
            caption["segments"].append(seg)
    elif caption.get("style") != new_style:
        # Styles are different - convert to segments
        # Get the original text before merging
        original_text = ""
        for line in existing_lines:
            if original_text:
                original_text += "\n"
            # Get text before the appended part
            if line["row"] == last_row and added_text_parts:
                # This line may have had text appended to it
                full_text = line["text"]
                for added in added_text_parts:
                    if full_text.endswith(" " + added):
                        full_text = full_text[: -(len(added) + 1)]
                        break
                original_text += full_text
            else:
                original_text += line["text"]

        # Build new text from new_lines
        new_text_combined = (
            "\n".join(added_text_parts) if added_text_parts else new_text
        )

        caption["segments"] = []
        if original_text:
            seg1 = {"text": original_text}
            if caption.get("style"):
                seg1["style"] = caption["style"]
            caption["segments"].append(seg1)
        if new_text_combined:
            seg2 = {"text": " " + new_text_combined}
            if new_style:
                seg2["style"] = new_style
            caption["segments"].append(seg2)
        caption["style"] = None


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

        # Handle EDM - erases displayed memory (but doesn't affect loading buffer)
        # Process EDM first, then continue to handle any text on the same line
        if is_edm:
            if displayed_caption and displayed_caption.get("text"):
                displayed_caption["end"] = current_time
                displayed_caption["end_timecode"] = timecode
                captions.append(displayed_caption)
                displayed_caption = None

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

        # Handle text content (can be on same line as EDM or other control codes)
        if text:
            # Extract style and layout information using segment-aware parsing
            _, style, segments = parse_608_text_segments(content)
            layout = parse_608_layout(content)

            if text_lines:
                layout["lines"] = text_lines

            caption_data = {
                "start": current_time,
                "start_timecode": timecode,
                "end": None,
                "end_timecode": None,
                "text": text,
                "style": style,  # None if segments are present
                "layout": layout if layout else None,
            }

            # Add segments only if multiple styles detected
            if segments:
                caption_data["segments"] = segments

            if is_pop_on:
                # Pop-on mode: start new loading buffer (will display at EOC)
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
                if loading_caption is not None:
                    # Continue loading in pop-on mode - merge text intelligently
                    _merge_caption_text(
                        loading_caption, text, text_lines, style, segments
                    )
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
