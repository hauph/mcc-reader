import re
from typing import Any, Dict, List

from ..utils import timecode_to_microseconds

from ..models import (
    PEN_SIZE_MAP,
    PEN_OFFSET_MAP,
    TEXT_TAG_MAP,
    FONT_TAG_MAP,
    EDGE_TYPE_MAP,
    OPACITY_MAP,
    DISPLAY_EFFECT_MAP,
    DIRECTION_MAP,
    JUSTIFY_MAP,
    BORDER_TYPE_MAP,
    ANCHOR_MAP,
    WINDOW_STYLE_MAP,
)


def cea708_color_to_rgb(r: int, g: int, b: int) -> str:
    """
    Convert CEA-708 2-bit color values (0-3) to CSS hex color.

    CEA-708 uses 2 bits per channel (0-3 scale).
    Conversion to 8-bit (0-255): 0→0, 1→85, 2→170, 3→255

    Args:
        r: Red value (0-3)
        g: Green value (0-3)
        b: Blue value (0-3)

    Returns:
        CSS hex color string (e.g., "#FF0000")
    """
    # Scale 2-bit (0-3) to 8-bit (0-255)
    scale = {0: 0, 1: 85, 2: 170, 3: 255}
    r8 = scale.get(r, 0)
    g8 = scale.get(g, 0)
    b8 = scale.get(b, 0)
    return f"#{r8:02X}{g8:02X}{b8:02X}"


def cea708_opacity_to_css(opacity: int | str) -> Any:
    """
    Convert CEA-708 opacity value to CSS-friendly value.

    Supports both:
    - Integer values (0-3) from raw CEA-708 spec
    - String values from Caption Inspector (Solid, Flash, Translucent, Transparent)

    CEA-708 opacity values (2 bits):
        0 = Solid (fully opaque)
        1 = Flash (blinking)
        2 = Translucent (semi-transparent)
        3 = Transparent (invisible)

    Args:
        opacity: Opacity value (int 0-3) or string from Caption Inspector

    Returns:
        CSS-friendly opacity description string
    """
    # Handle integer input (original CEA-708 raw values)
    if isinstance(opacity, int):
        int_opacity_map = {
            0: "solid",
            1: "flash",
            2: "translucent",
            3: "transparent",
        }
        return int_opacity_map.get(opacity, "solid")

    # Handle string input (Caption Inspector format)
    return OPACITY_MAP.get(opacity.lower(), 1.0)


def parse_708_style(content: str) -> Dict[str, Any]:
    """
    Extract style information from CEA-708 content.

    Caption Inspector formats:
    - SPA (Set Pen Attributes): {SPA:Pen-[Size:<size>,Offset:<offset>]:TextTag-<tag>:FontTag-<tag>:EdgeType-<type>:UL:IT}
    - SPC (Set Pen Color): {SPC:FG-<opacity>-R<r>G<g>B<b>:BG-<opacity>-R<r>G<g>B<b>Edg-R<r>G<g>B<b>}
    - Standalone RGB: R<r>G<g>B<b>

    Args:
        content: The content string containing style codes

    Returns:
        Dictionary with CSS-like styling rules
    """
    style = {}

    # Parse SPC (Set Pen Color) command
    # Format: {SPC:FG-<opacity>-R<r>G<g>B<b>:BG-<opacity>-R<r>G<g>B<b>Edg-R<r>G<g>B<b>}
    spc_match = re.search(r"\{SPC:([^}]+)\}", content)
    if spc_match:
        spc_content = spc_match.group(1)

        # Foreground color and opacity: FG-<opacity>-R<r>G<g>B<b>
        fg_match = re.search(r"FG-(\w+)-R([0-3])G([0-3])B([0-3])", spc_content)
        if fg_match:
            opacity_str = fg_match.group(1)
            r = int(fg_match.group(2))
            g = int(fg_match.group(3))
            b = int(fg_match.group(4))
            style["color"] = cea708_color_to_rgb(r, g, b)
            style["color_raw"] = {"r": r, "g": g, "b": b}
            style["opacity"] = cea708_opacity_to_css(opacity_str)
            style["opacity_raw"] = opacity_str.lower()

        # Background color and opacity: BG-<opacity>-R<r>G<g>B<b>
        bg_match = re.search(r"BG-(\w+)-R([0-3])G([0-3])B([0-3])", spc_content)
        if bg_match:
            opacity_str = bg_match.group(1)
            r = int(bg_match.group(2))
            g = int(bg_match.group(3))
            b = int(bg_match.group(4))
            style["background-color"] = cea708_color_to_rgb(r, g, b)
            style["background_color_raw"] = {"r": r, "g": g, "b": b}
            style["background_opacity"] = cea708_opacity_to_css(opacity_str)
            style["background_opacity_raw"] = opacity_str.lower()

        # Edge color: Edg-R<r>G<g>B<b>
        edge_match = re.search(r"Edg-R([0-3])G([0-3])B([0-3])", spc_content)
        if edge_match:
            r = int(edge_match.group(1))
            g = int(edge_match.group(2))
            b = int(edge_match.group(3))
            style["edge_color"] = cea708_color_to_rgb(r, g, b)
            style["edge_color_raw"] = {"r": r, "g": g, "b": b}

    # Parse SPA (Set Pen Attributes) command
    # Format: {SPA:Pen-[Size:<size>,Offset:<offset>]:TextTag-<tag>:FontTag-<tag>:EdgeType-<type>:UL:IT}
    spa_match = re.search(r"\{SPA:([^}]+)\}", content)
    if spa_match:
        spa_content = spa_match.group(1)

        # Pen size: Size:<size>
        size_match = re.search(r"Size:(\w+)", spa_content)
        if size_match:
            size = size_match.group(1).lower()
            style["font-size"] = PEN_SIZE_MAP.get(size, size)

        # Pen offset: Offset:<offset>
        offset_match = re.search(r"Offset:(\w+)", spa_content)
        if offset_match:
            offset = offset_match.group(1).lower()
            if offset in PEN_OFFSET_MAP and PEN_OFFSET_MAP[offset] != "normal":
                style["vertical-align"] = PEN_OFFSET_MAP[offset]

        # Text tag: TextTag-<tag>
        text_tag_match = re.search(r"TextTag-([^:}]+)", spa_content)
        if text_tag_match:
            tag = text_tag_match.group(1).lower()
            if tag in TEXT_TAG_MAP:
                style["text_tag"] = TEXT_TAG_MAP[tag]
            else:
                style["text_tag"] = tag

        # Font tag: FontTag-<tag>
        font_tag_match = re.search(r"FontTag-([^:}]+)", spa_content)
        if font_tag_match:
            font = font_tag_match.group(1).lower()
            if font in FONT_TAG_MAP and FONT_TAG_MAP[font]:
                style["font-family"] = FONT_TAG_MAP[font]

        # Edge type: EdgeType-<type>
        edge_match = re.search(r"EdgeType-([^:}]+)", spa_content)
        if edge_match:
            edge = edge_match.group(1).lower()
            if edge in EDGE_TYPE_MAP and EDGE_TYPE_MAP[edge]:
                style["text-edge"] = EDGE_TYPE_MAP[edge]

        # Underline: :UL
        if ":UL" in spa_content or spa_content.endswith("UL"):
            style["text-decoration"] = "underline"

        # Italic: :IT
        if ":IT" in spa_content or spa_content.endswith("IT"):
            style["font-style"] = "italic"

        # Bold: :BL
        if ":BL" in spa_content or spa_content.endswith("BL"):
            style["font-weight"] = "bold"

    # Fallback: extract standalone RGB color (not in SPC command)
    if "color" not in style:
        # Look for RGB not preceded by FG-, BG-, or Edg-
        rgb_match = re.search(
            r"(?<!FG-)(?<!BG-)(?<!Edg-)R([0-3])G([0-3])B([0-3])", content
        )
        if rgb_match:
            r = int(rgb_match.group(1))
            g = int(rgb_match.group(2))
            b = int(rgb_match.group(3))
            style["color"] = cea708_color_to_rgb(r, g, b)
            style["color_raw"] = {"r": r, "g": g, "b": b}

    # Extract font from window definition pen style
    # Format: Pen-<style> in DF command or standalone Pen-<style>
    pen_match = re.search(r"(?:^|[:{])Pen-([A-Za-z]+)(?:[:-]|$|\})", content)
    if not pen_match:
        # Also try standalone format like "Pen-PropSans"
        pen_match = re.search(r"^Pen-([A-Za-z]+)$", content)
    if pen_match and "font-family" not in style:
        font = pen_match.group(1).lower()
        if font in FONT_TAG_MAP and FONT_TAG_MAP[font]:
            style["font-family"] = FONT_TAG_MAP[font]

    return style


def parse_708_text_segments(
    content: str,
) -> tuple[str, Dict[str, Any] | None, List[Dict[str, Any]] | None]:
    """
    Parse CEA-708 content to extract text with style segments.

    Style commands (SPC, SPA) apply to all subsequent text until changed.
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
    # Find all style commands and their positions in the content
    # Pattern matches {SPC:...} or {SPA:...}
    style_pattern = re.compile(r"\{(SPC|SPA):([^}]+)\}")

    # Find all quoted text and their positions
    text_pattern = re.compile(r'"([^"]*)"')

    # Find all SPL position markers
    spl_pattern = re.compile(r"\{SPL:R(\d+)-C(\d+)\}")

    # Build list of (position, type, data) tuples for sequential processing
    events = []

    # Collect style commands
    for match in style_pattern.finditer(content):
        cmd_type = match.group(1)  # SPC or SPA
        cmd_content = match.group(2)
        events.append((match.start(), "style", (cmd_type, cmd_content)))

    # Collect text segments
    for match in text_pattern.finditer(content):
        text = match.group(1)
        if text:  # Skip empty strings
            events.append((match.start(), "text", text))

    # Collect SPL position markers
    for match in spl_pattern.finditer(content):
        row = int(match.group(1))
        col = int(match.group(2))
        events.append((match.start(), "spl", (row, col)))

    # Sort events by position
    events.sort(key=lambda x: x[0])

    # Process events sequentially, tracking current style and row
    current_style = {}
    current_row = 0
    segments = []

    # Extract font from window definition (DF) as base style
    df_match = re.search(r"\{DF\d+:[^}]*Pen-([A-Za-z]+)", content)
    if df_match:
        font = df_match.group(1).lower()
        if font in FONT_TAG_MAP and FONT_TAG_MAP[font]:
            current_style["font-family"] = FONT_TAG_MAP[font]

    for _, event_type, data in events:
        if event_type == "style":
            cmd_type, cmd_content = data
            if cmd_type == "SPC":
                # Parse SPC command and update current style
                fg_match = re.search(r"FG-(\w+)-R([0-3])G([0-3])B([0-3])", cmd_content)
                if fg_match:
                    opacity_str = fg_match.group(1)
                    r = int(fg_match.group(2))
                    g = int(fg_match.group(3))
                    b = int(fg_match.group(4))
                    current_style["color"] = cea708_color_to_rgb(r, g, b)
                    current_style["color_raw"] = {"r": r, "g": g, "b": b}
                    current_style["opacity"] = cea708_opacity_to_css(opacity_str)
                    current_style["opacity_raw"] = opacity_str.lower()

                bg_match = re.search(r"BG-(\w+)-R([0-3])G([0-3])B([0-3])", cmd_content)
                if bg_match:
                    opacity_str = bg_match.group(1)
                    r = int(bg_match.group(2))
                    g = int(bg_match.group(3))
                    b = int(bg_match.group(4))
                    current_style["background-color"] = cea708_color_to_rgb(r, g, b)
                    current_style["background_color_raw"] = {"r": r, "g": g, "b": b}
                    current_style["background_opacity"] = cea708_opacity_to_css(
                        opacity_str
                    )
                    current_style["background_opacity_raw"] = opacity_str.lower()

                edge_match = re.search(r"Edg-R([0-3])G([0-3])B([0-3])", cmd_content)
                if edge_match:
                    r = int(edge_match.group(1))
                    g = int(edge_match.group(2))
                    b = int(edge_match.group(3))
                    current_style["edge_color"] = cea708_color_to_rgb(r, g, b)
                    current_style["edge_color_raw"] = {"r": r, "g": g, "b": b}

            elif cmd_type == "SPA":
                # Parse SPA command and update current style
                size_match = re.search(r"Size:(\w+)", cmd_content)
                if size_match:
                    size = size_match.group(1).lower()
                    current_style["font-size"] = PEN_SIZE_MAP.get(size, size)

                offset_match = re.search(r"Offset:(\w+)", cmd_content)
                if offset_match:
                    offset = offset_match.group(1).lower()
                    if offset in PEN_OFFSET_MAP and PEN_OFFSET_MAP[offset] != "normal":
                        current_style["vertical-align"] = PEN_OFFSET_MAP[offset]

                if ":UL" in cmd_content or cmd_content.endswith("UL"):
                    current_style["text-decoration"] = "underline"
                elif "text-decoration" in current_style:
                    del current_style["text-decoration"]

                if ":IT" in cmd_content or cmd_content.endswith("IT"):
                    current_style["font-style"] = "italic"
                elif "font-style" in current_style:
                    del current_style["font-style"]

                if ":BL" in cmd_content or cmd_content.endswith("BL"):
                    current_style["font-weight"] = "bold"
                elif "font-weight" in current_style:
                    del current_style["font-weight"]

        elif event_type == "spl":
            row, col = data
            current_row = row

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


def parse_708_text_with_positions(content: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Parse CEA-708 content to extract text with line breaks based on pen positions.

    Caption Inspector format: {SPL:R<row>-C<col>}
    When pen position row changes, insert a line break.

    Text can appear:
    - After {SPL:R#-C#} tags (explicit position)
    - Before any SPL tag (uses row from window definition or default row 0)

    Args:
        content: The content string containing position codes and text

    Returns:
        Tuple of (formatted_text_with_linebreaks, list_of_lines_with_positions)
    """
    lines = []

    # Default row for text that appears before any SPL position tag
    default_row = 0

    # Split content by SPL tags, keeping track of text before first SPL
    # Pattern to match {SPL:R#-C#} followed by text in quotes
    segments = re.split(r"(?=\{SPL:R\d+-C\d+\})", content)

    for i, segment in enumerate(segments):
        if not segment.strip():
            continue

        # Extract row/column from this segment
        spl_match = re.search(r"\{SPL:R(\d+)-C(\d+)\}", segment)
        # Extract text from this segment
        text_matches = re.findall(r'"([^"]*)"', segment)

        if text_matches:
            text = " ".join(text_matches).strip()
            if not text:
                continue

            if spl_match:
                # Text after SPL tag - use explicit position
                row = int(spl_match.group(1))
                col = int(spl_match.group(2))
            else:
                # Text before any SPL tag - use default position (row 0)
                # This handles cases like: {DF1:...} {SPC:...} "text" {SPL:R1-C0} "more text"
                row = default_row
                col = 0

            lines.append(
                {
                    "row": row,
                    "column": col,
                    "text": text,
                }
            )

    # Sort lines by row number (ascending: row 0 at top, higher rows below)
    lines.sort(key=lambda x: x["row"])

    # Join lines with newline character
    formatted_text = "\n".join(line["text"] for line in lines)

    return formatted_text, lines


def parse_708_layout(content: str) -> Dict[str, Any]:
    """
    Extract layout/positioning information from CEA-708 content.

    Caption Inspector formats:
    - Define Window: {DF<n>:<win_style>:R<rows>-C<cols>:Anchor-<anchor>-V<v>-H<h>:Pen-<pen_style>:Pr-<priority>:VIS:RL:CL:RP}
    - Set Pen Location: {SPL:R<row>-C<col>}
    - Set Window Attributes: {SWA:Fill-<opacity>-R<r>G<g>B<b>:Brdr-<type>-R<r>G<g>B<b>:PD-<dir>:SD-<dir>:JD-<dir>:<effect>-<speed>sec-<dir>:WW}
    - Window commands: {CLW:<bitmap>}, {DSW:<bitmap>}, {HDW:<bitmap>}, {TGW:<bitmap>}, {DLW:<bitmap>}

    Args:
        content: The content string containing position codes

    Returns:
        Layout object with positioning information
    """
    layout = {}

    # Extract window definition: {DF<n>:<content>}
    # Format: {DF0:608-PopUp:R1-C29:Anchor-UL-V65-H0:Pen-MonoSerif:Pr-0:VIS:RL:CL:RP}
    # Or simpler: {DF0:PopUp-Cntrd:R1-C29:...}
    df_match = re.search(r"\{DF(\d+):([^}]+)\}", content)
    if df_match:
        window_id = int(df_match.group(1))
        df_content = df_match.group(2)
        layout["window_id"] = window_id

        # Window style (first segment before colon)
        # Styles: 608-PopUp, PopUp-TransBG, PopUp-Centered, 608-RollUp, RollUp-TransBG, RollUp-Centered, TickerTape
        # Also simpler formats: PopUp-Cntrd, RollUp-Left, PaintOn-Left
        style_match = re.match(r"([^:]+)", df_content)
        if style_match:
            win_style = style_match.group(1).lower()
            if win_style in WINDOW_STYLE_MAP:
                layout["mode"] = WINDOW_STYLE_MAP[win_style]
            else:
                # Handle simpler format patterns
                if "popup" in win_style:
                    layout["mode"] = "pop-on"
                elif "rollup" in win_style:
                    layout["mode"] = "roll-up"
                elif "painton" in win_style:
                    layout["mode"] = "paint-on"
                elif "ticker" in win_style:
                    layout["mode"] = "ticker"
            layout["window_style"] = style_match.group(1)

            # Check for alignment in style name
            if "centered" in win_style or "cntrd" in win_style:
                layout["text-align"] = "center"
            elif "left" in win_style:
                layout["text-align"] = "left"
            elif "right" in win_style:
                layout["text-align"] = "right"
            # Check for transparent background
            if "transbg" in win_style:
                layout["transparent_background"] = True

        # Window size: R<rows>-C<cols>
        size_match = re.search(r":R(\d+)-C(\d+)", df_content)
        if size_match:
            layout["window_rows"] = int(size_match.group(1))
            layout["window_columns"] = int(size_match.group(2))

        # Anchor position: Anchor-<anchor>-V<vertical>-H<horizontal>
        anchor_match = re.search(r"Anchor-(\w+)-V(\d+)-H(\d+)", df_content)
        if anchor_match:
            anchor_point = anchor_match.group(1)
            vertical = int(anchor_match.group(2))
            horizontal = int(anchor_match.group(3))

            # Keep anchor as-is (UL, UC, UR, etc.) for compatibility
            layout["anchor"] = anchor_point
            # Also provide human-readable version
            if anchor_point.lower() in ANCHOR_MAP:
                layout["anchor_description"] = ANCHOR_MAP[anchor_point.lower()]
            layout["vertical_percent"] = vertical  # 0-100
            layout["horizontal_percent"] = horizontal  # 0-100

        # Priority: Pr-<priority>
        pr_match = re.search(r"Pr-(\d+)", df_content)
        if pr_match:
            layout["priority"] = int(pr_match.group(1))

        # Visibility: :VIS
        if ":VIS" in df_content:
            layout["visible"] = True

        # Row locked: :RL
        if ":RL" in df_content:
            layout["row_locked"] = True

        # Column locked: :CL
        if ":CL" in df_content:
            layout["column_locked"] = True

        # Relative positioning: :RP
        if ":RP" in df_content:
            layout["relative_position"] = True

    # Parse SWA (Set Window Attributes) command
    # Format: {SWA:Fill-<opacity>-R<r>G<g>B<b>:Brdr-<type>-R<r>G<g>B<b>:PD-<dir>:SD-<dir>:JD-<dir>:<effect>-<speed>sec-<dir>:WW}
    swa_match = re.search(r"\{SWA:([^}]+)\}", content)
    if swa_match:
        swa_content = swa_match.group(1)

        # Fill color: Fill-<opacity>-R<r>G<g>B<b>
        fill_match = re.search(r"Fill-(\w+)-R([0-3])G([0-3])B([0-3])", swa_content)
        if fill_match:
            r = int(fill_match.group(2))
            g = int(fill_match.group(3))
            b = int(fill_match.group(4))
            layout["fill_color"] = cea708_color_to_rgb(r, g, b)
            layout["fill_opacity"] = fill_match.group(1).lower()

        # Border: Brdr-<type>-R<r>G<g>B<b>
        border_match = re.search(r"Brdr-(\w+)-R([0-3])G([0-3])B([0-3])", swa_content)
        if border_match:
            border_type = border_match.group(1).lower()
            r = int(border_match.group(2))
            g = int(border_match.group(3))
            b = int(border_match.group(4))
            if border_type in BORDER_TYPE_MAP and BORDER_TYPE_MAP[border_type]:
                layout["border_type"] = BORDER_TYPE_MAP[border_type]
            layout["border_color"] = cea708_color_to_rgb(r, g, b)

        # Print direction: PD-<dir>
        pd_match = re.search(r"PD-(\w+)", swa_content)
        if pd_match:
            pd = pd_match.group(1).lower()
            if pd in DIRECTION_MAP:
                layout["print_direction"] = DIRECTION_MAP[pd]

        # Scroll direction: SD-<dir>
        sd_match = re.search(r"SD-(\w+)", swa_content)
        if sd_match:
            sd = sd_match.group(1).lower()
            if sd in DIRECTION_MAP:
                layout["scroll_direction"] = DIRECTION_MAP[sd]

        # Justify direction: JD-<dir>
        jd_match = re.search(r"JD-(\w+)", swa_content)
        if jd_match:
            jd = jd_match.group(1).lower()
            if jd in JUSTIFY_MAP:
                layout["text-align"] = JUSTIFY_MAP[jd]

        # Display effect: <effect>-<speed>sec-<dir>
        effect_match = re.search(
            r"(Snap|Fade|Wipe|Mask)-([0-9.]+)sec-(\w+)", swa_content
        )
        if effect_match:
            effect = effect_match.group(1).lower()
            speed = float(effect_match.group(2))
            direction = effect_match.group(3).lower()
            if effect in DISPLAY_EFFECT_MAP:
                layout["display_effect"] = DISPLAY_EFFECT_MAP[effect]
            layout["effect_speed"] = speed
            if direction in DIRECTION_MAP:
                layout["effect_direction"] = DIRECTION_MAP[direction]

        # Word wrap: :WW
        if ":WW" in swa_content:
            layout["word_wrap"] = True

    # Extract pen location: {SPL:R<row>-C<col>}
    spl_matches = re.findall(r"\{SPL:R(\d+)-C(\d+)\}", content)
    if spl_matches:
        # Store all pen locations (for multi-line captions)
        layout["pen_positions"] = [
            {"row": int(r), "column": int(c)} for r, c in spl_matches
        ]
        # Primary position is the first one
        layout["row"] = int(spl_matches[0][0])
        layout["column"] = int(spl_matches[0][1])

    # Extract window commands
    # Clear Windows: {CLW:<bitmap>}
    clw_match = re.search(r"\{CLW:(\d+)\}", content)
    if clw_match:
        layout["clear_windows"] = clw_match.group(1)

    # Display Windows: {DSW:<bitmap>}
    dsw_match = re.search(r"\{DSW:(\d+)\}", content)
    if dsw_match:
        layout["display_windows"] = dsw_match.group(1)

    # Hide Windows: {HDW:<bitmap>}
    hdw_match = re.search(r"\{HDW:(\d+)\}", content)
    if hdw_match:
        layout["hide_windows"] = hdw_match.group(1)

    # Toggle Windows: {TGW:<bitmap>}
    tgw_match = re.search(r"\{TGW:(\d+)\}", content)
    if tgw_match:
        layout["toggle_windows"] = tgw_match.group(1)

    # Delete Windows: {DLW:<bitmap>}
    dlw_match = re.search(r"\{DLW:(\d+)\}", content)
    if dlw_match:
        layout["delete_windows"] = dlw_match.group(1)

    return layout


def parse_708_file(
    file_path: str, fps: float = 24.0, drop_frame: bool = False
) -> List[Dict[str, Any]]:
    """
    Parse a CEA-708 decode file from Caption Inspector.

    File format:
    - Header line with service info
    - Lines with format: HH:MM:SS:FF - <content>
    - Content includes window commands, pen attributes, colors, positions, and text in quotes

    Caption display is triggered by DSW (Display Windows) command.
    Caption clearing is triggered by DLW (Delete Windows) or CLW (Clear Windows) commands.

    Args:
        file_path: Path to the .708 file
        fps: Frames per second
        drop_frame: Whether to use drop frame calculation

    Returns:
        List of caption cues with start time, end time, text, style, and layout.
    """
    captions = []

    with open(file_path, "r", encoding="latin-1") as f:
        file_lines = f.readlines()

    current_caption = None

    for line in file_lines:
        line = line.strip()
        if not line:
            continue

        # Match timecode pattern at start of line
        # Format: HH:MM:SS:FF or HH:MM:SS;FF (drop frame)
        tc_match = re.match(r"^(\d{2}:\d{2}:\d{2}[:;]\d{2})\s*-\s*(.*)$", line)

        if tc_match:
            timecode = tc_match.group(1)
            content = tc_match.group(2)

            # Extract text with line breaks based on pen positions
            text, text_lines = parse_708_text_with_positions(content)

            # Check for display commands
            # DSW = Display Windows - shows captions
            # DLW = Delete Windows - removes captions
            # DF = Define Window - creates a window for captions
            has_dsw = "{DSW:" in content or re.search(r"\{DSW:\d+\}", content)
            has_dlw = "{DLW:" in content or re.search(r"\{DLW:\d+\}", content)
            has_clw = "{CLW:" in content or re.search(r"\{CLW:\d+\}", content)
            has_df = re.search(r"\{DF\d+:", content)  # Window definition

            # New caption: text with either DSW (display) or DF (window definition with text)
            if text and (has_dsw or has_df):
                # New caption being displayed
                # Extract style and layout information using segment-aware parsing
                _, style, segments = parse_708_text_segments(content)
                layout = parse_708_layout(content)

                # Add the individual lines with positions to layout
                if text_lines:
                    layout["lines"] = text_lines

                # End previous caption
                if current_caption and current_caption.get("text"):
                    current_caption["end"] = timecode_to_microseconds(
                        timecode, fps, drop_frame
                    )
                    current_caption["end_timecode"] = timecode
                    captions.append(current_caption)

                # Start new caption
                current_caption = {
                    "start": timecode_to_microseconds(timecode, fps, drop_frame),
                    "start_timecode": timecode,
                    "end": None,
                    "end_timecode": None,
                    "text": text,
                    "style": style,  # None if segments are present
                    "layout": layout if layout else None,
                }

                # Add segments only if multiple styles detected
                if segments:
                    current_caption["segments"] = segments

            elif (has_dlw or has_clw) and current_caption:
                # Caption being deleted/cleared - end the current caption
                current_caption["end"] = timecode_to_microseconds(
                    timecode, fps, drop_frame
                )
                current_caption["end_timecode"] = timecode
                captions.append(current_caption)
                current_caption = None

            elif text and not current_caption:
                # Text without DSW - might be continuation or first caption
                _, style, segments = parse_708_text_segments(content)
                layout = parse_708_layout(content)

                if text_lines:
                    layout["lines"] = text_lines

                current_caption = {
                    "start": timecode_to_microseconds(timecode, fps, drop_frame),
                    "start_timecode": timecode,
                    "end": None,
                    "end_timecode": None,
                    "text": text,
                    "style": style,  # None if segments are present
                    "layout": layout if layout else None,
                }

                # Add segments only if multiple styles detected
                if segments:
                    current_caption["segments"] = segments

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
                    "style": None,
                    "layout": None,
                }

    # Add last caption
    # Note: end time is left as None if unknown - consuming application decides
    if current_caption and current_caption.get("text"):
        captions.append(current_caption)

    return captions
