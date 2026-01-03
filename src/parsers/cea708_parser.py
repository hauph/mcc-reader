import re
from typing import Any, Dict, List

from utils import timecode_to_seconds


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


def cea708_opacity_to_css(opacity: int) -> str:
    """
    Convert CEA-708 opacity value to CSS opacity description.

    CEA-708 opacity values (2 bits):
        0 = Solid (fully opaque)
        1 = Flash (blinking)
        2 = Translucent (semi-transparent)
        3 = Transparent (invisible)

    Args:
        opacity: Opacity value (0-3)

    Returns:
        CSS-friendly opacity description
    """
    opacity_map = {
        0: "solid",  # 1.0
        1: "flash",  # blinking effect
        2: "translucent",  # ~0.5
        3: "transparent",  # 0.0
    }
    return opacity_map.get(opacity, "solid")


def parse_708_style(content: str) -> Dict[str, Any]:
    """
    Extract style information from CEA-708 content.

    CEA-708 color format: R#G#B# where # is 0-3 (2-bit per channel, 64 colors total)
    Example: R2G3B1 means Red=2, Green=3, Blue=1 on 0-3 scale

    CEA-708 font styles (per spec):
        0: Default, 1: MonoSerif, 2: PropSerif, 3: MonoSans,
        4: PropSans, 5: Casual, 6: Cursive, 7: SmallCaps

    Args:
        content: The content string containing style codes

    Returns:
        Dictionary with CSS-like styling rules
    """
    style = {}

    # Extract CEA-708 RGB color: R#G#B# format (e.g., R2G3B1, R0G0B0)
    # This can appear in foreground (FG) or background (BG) color specs
    rgb_match = re.search(r"R([0-3])G([0-3])B([0-3])", content)
    if rgb_match:
        r = int(rgb_match.group(1))
        g = int(rgb_match.group(2))
        b = int(rgb_match.group(3))
        style["color"] = cea708_color_to_rgb(r, g, b)
        style["color_raw"] = {"r": r, "g": g, "b": b}

    # Extract opacity if present (O# format where # is 0-3)
    opacity_match = re.search(r"(?:^|[:-])O([0-3])(?:[:-]|$)", content)
    if opacity_match:
        opacity = int(opacity_match.group(1))
        style["opacity"] = cea708_opacity_to_css(opacity)
        style["opacity_raw"] = opacity

    # Extract background color if present (BG-R#G#B#)
    bg_match = re.search(r"BG-?R([0-3])G([0-3])B([0-3])", content)
    if bg_match:
        r = int(bg_match.group(1))
        g = int(bg_match.group(2))
        b = int(bg_match.group(3))
        style["background-color"] = cea708_color_to_rgb(r, g, b)
        style["background_color_raw"] = {"r": r, "g": g, "b": b}

    # Extract pen attributes: {SPA:Pen-[Size:Standard,Offset:Normal]:TextTag-Dialog:FontTag-Default:EdgeType-None:IT}
    spa_match = re.search(r"\{SPA:([^}]+)\}", content)
    if spa_match:
        spa_content = spa_match.group(1)

        # Font size (CEA-708 defines: Small, Standard, Large)
        size_match = re.search(r"Size:(\w+)", spa_content)
        if size_match:
            size = size_match.group(1).lower()
            size_map = {"small": "small", "standard": "medium", "large": "large"}
            style["font-size"] = size_map.get(size, size)

        # Italic (IT at end)
        if ":IT" in spa_content or spa_content.endswith("IT"):
            style["font-style"] = "italic"

        # Underline (UL)
        if ":UL" in spa_content:
            style["text-decoration"] = "underline"

        # Bold (BL)
        if ":BL" in spa_content:
            style["font-weight"] = "bold"

        # Edge type (for text shadow/outline effects)
        # CEA-708 edge types: None, Raised, Depressed, Uniform, LeftDropShadow, RightDropShadow
        edge_match = re.search(r"EdgeType-(\w+)", spa_content)
        if edge_match:
            edge = edge_match.group(1).lower()
            if edge != "none":
                style["text-edge"] = edge

    # Extract font from window definition
    # CEA-708 defines 8 font styles (see docstring)
    font_match = re.search(r"Pen-(\w+)", content)
    if font_match:
        font = font_match.group(1)
        # Mapping CEA-708 font IDs to CSS font-family
        font_map = {
            "MonoSerif": "monospace, serif",  # ID 1
            "PropSerif": "serif",  # ID 2
            "MonoSans": "monospace, sans-serif",  # ID 3
            "PropSans": "sans-serif",  # ID 4
            "Casual": "cursive",  # ID 5
            "Cursive": "cursive",  # ID 6
            "SmallCaps": "small-caps",  # ID 7
        }
        if font in font_map:
            style["font-family"] = font_map[font]

    return style


def parse_708_text_with_positions(content: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Parse CEA-708 content to extract text with line breaks based on pen positions.

    When pen position row changes (e.g., {SPL:R1-C12} to {SPL:R0-C16}), insert a line break.

    Args:
        content: The content string containing position codes and text

    Returns:
        Tuple of (formatted_text_with_linebreaks, list_of_lines_with_positions)
    """
    lines = []

    # Pattern to match {SPL:R#-C#} followed by text in quotes
    # Example: {SPL:R1-C12} "I was thinking we" {SPL:R0-C16} "So, for Mom"
    segments = re.split(r"(?=\{SPL:R\d+-C\d+\})", content)

    for segment in segments:
        if not segment.strip():
            continue

        # Extract row/column from this segment
        spl_match = re.search(r"\{SPL:R(\d+)-C(\d+)\}", segment)
        # Extract text from this segment
        text_matches = re.findall(r'"([^"]*)"', segment)

        if spl_match and text_matches:
            row = int(spl_match.group(1))
            col = int(spl_match.group(2))
            text = " ".join(text_matches).strip()

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

    Args:
        content: The content string containing position codes

    Returns:
        Layout object with positioning information
    """
    layout = {}

    # Extract window definition: {DF0:PopUp-Cntrd:R1-C29:Anchor-UL-V65-H0:Pen-MonoSerif:Pr-0:VIS}
    df_match = re.search(r"\{DF\d+:([^}]+)\}", content)
    if df_match:
        df_content = df_match.group(1)

        # Window type (PopUp, RollUp, PaintOn)
        if "PopUp" in df_content:
            layout["mode"] = "pop-on"
        elif "RollUp" in df_content:
            layout["mode"] = "roll-up"
        elif "PaintOn" in df_content:
            layout["mode"] = "paint-on"

        # Alignment (Cntrd = centered, Left, Right)
        if "Cntrd" in df_content:
            layout["text-align"] = "center"
        elif "Left" in df_content:
            layout["text-align"] = "left"
        elif "Right" in df_content:
            layout["text-align"] = "right"

        # Window size: R1-C29 (rows and columns)
        size_match = re.search(r"R(\d+)-C(\d+)", df_content)
        if size_match:
            layout["window_rows"] = int(size_match.group(1))
            layout["window_columns"] = int(size_match.group(2))

        # Anchor position: Anchor-UL-V65-H0
        anchor_match = re.search(r"Anchor-(\w+)-V(\d+)-H(\d+)", df_content)
        if anchor_match:
            anchor_point = anchor_match.group(1)
            vertical = int(anchor_match.group(2))
            horizontal = int(anchor_match.group(3))

            layout["anchor"] = anchor_point  # UL, UC, UR, CL, C, CR, LL, LC, LR
            layout["vertical_percent"] = vertical  # 0-100
            layout["horizontal_percent"] = horizontal  # 0-100

        # Priority
        pr_match = re.search(r"Pr-(\d+)", df_content)
        if pr_match:
            layout["priority"] = int(pr_match.group(1))

        # Visibility
        if ":VIS" in df_content:
            layout["visible"] = True

    # Extract pen location: {SPL:R1-C12}
    spl_matches = re.findall(r"\{SPL:R(\d+)-C(\d+)\}", content)
    if spl_matches:
        # Store all pen locations (for multi-line captions)
        layout["pen_positions"] = [
            {"row": int(r), "column": int(c)} for r, c in spl_matches
        ]
        # Primary position is the first one
        layout["row"] = int(spl_matches[0][0])
        layout["column"] = int(spl_matches[0][1])

    return layout


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
        List of caption cues with start time, end time, text, style, and layout.
    """
    captions = []

    with open(file_path, "r") as f:
        file_lines = f.readlines()

    current_caption = None

    for line in file_lines:
        line = line.strip()
        if not line:
            continue

        # Match timecode pattern at start of line
        tc_match = re.match(r"^(\d{2}:\d{2}:\d{2}[:;]\d{2})\s*-\s*(.*)$", line)

        if tc_match:
            timecode = tc_match.group(1)
            content = tc_match.group(2)

            # Extract text with line breaks based on pen positions
            text, text_lines = parse_708_text_with_positions(content)

            # Check for display commands
            has_dlw = "{DLW:" in content  # Define Layer Window - indicates new caption

            if text and has_dlw:
                # Extract style and layout information
                style = parse_708_style(content)
                layout = parse_708_layout(content)

                # Add the individual lines with positions to layout
                if text_lines:
                    layout["lines"] = text_lines

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
                    "style": style if style else None,
                    "layout": layout if layout else None,
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
                    "style": None,
                    "layout": None,
                }

    # Add last caption
    if current_caption and current_caption.get("text"):
        if current_caption["end"] is None:
            current_caption["end"] = current_caption["start"] + 2.0
            current_caption["end_timecode"] = current_caption["start_timecode"]
        captions.append(current_caption)

    return captions
