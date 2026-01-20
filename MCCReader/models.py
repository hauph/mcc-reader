from enum import Enum

CEA608_FORMAT = "cea608"
CEA708_FORMAT = "cea708"


class CaptionFormat(str, Enum):
    CEA608 = CEA608_FORMAT
    CEA708 = CEA708_FORMAT


TEMP_OUTPUT_DIR = "/tmp/caption_output"

UNKNOWN_DEBUG_LEVEL = "UNKNOWN_DEBUG_LEVEL"
VERBOSE = "VERBOSE"
INFO = "INFO"
WARN = "WARN"
ERROR = "ERROR"
FATAL = "FATAL"
ASSERT = "ASSERT"
DEBUG_LEVELS = [
    UNKNOWN_DEBUG_LEVEL,
    VERBOSE,
    INFO,
    WARN,
    ERROR,
    FATAL,
    ASSERT,
]


class DebugLevels(str, Enum):
    UNKNOWN_DEBUG_LEVEL = UNKNOWN_DEBUG_LEVEL
    VERBOSE = VERBOSE
    INFO = INFO
    WARN = WARN
    ERROR = ERROR
    FATAL = FATAL
    ASSERT = ASSERT


# =============================================================================
# # CEA-708 models from Caption Inspector
# =============================================================================


# Pen size mappings (from pen_size_trans_dict)
PEN_SIZE_MAP = {
    "small": "small",
    "standard": "medium",
    "large": "large",
}

# Pen offset mappings (from pen_offset_trans_dict)
PEN_OFFSET_MAP = {
    "subscript": "sub",
    "normal": "normal",
    "superscript": "super",
}

# Font tag mappings (from font_tag_trans_dict / predef_pen_style_dict)
FONT_TAG_MAP = {
    "default": None,
    "monospaced serif": "monospace, serif",
    "monoserif": "monospace, serif",
    "proportional serif": "serif",
    "proportserif": "serif",
    "propserif": "serif",
    "monospaced sanserif": "monospace, sans-serif",
    "monosanserif": "monospace, sans-serif",
    "monosans": "monospace, sans-serif",
    "proportional sanserif": "sans-serif",
    "proportionsanserif": "sans-serif",
    "propsans": "sans-serif",
    "propsanserif": "sans-serif",
    "casual": "cursive",
    "cursive": "cursive",
    "smallcaps": "small-caps",
}

# Opacity mappings (from opacity_trans_dict)
OPACITY_MAP = {
    "solid": 1.0,
    "flash": "flash",
    "translucent": 0.5,
    "transparent": 0.0,
}

# Anchor point mappings (from anchor_trans_dict)
ANCHOR_MAP = {
    "ul": "upper-left",
    "uc": "upper-center",
    "ur": "upper-right",
    "ml": "middle-left",
    "mc": "middle-center",
    "mr": "middle-right",
    "ll": "lower-left",
    "lc": "lower-center",
    "lr": "lower-right",
}

# Pre-defined window styles (from predef_win_style_dict)
WINDOW_STYLE_MAP = {
    "608-popup": "pop-on",
    "popup-transbg": "pop-on",
    "popup-centered": "pop-on",
    "608-rollup": "roll-up",
    "rollup-transbg": "roll-up",
    "rollup-centered": "roll-up",
    "tickertape": "ticker",
}

# Border type mappings (from border_type_trans_dict)
BORDER_TYPE_MAP = {
    "none": None,
    "raised": "raised",
    "depressed": "depressed",
    "uniform": "uniform",
    "shadow left": "shadow-left",
    "shadow right": "shadow-right",
}

# Direction mappings (from direction_trans_dict)
DIRECTION_MAP = {
    "ltor": "left-to-right",
    "rtol": "right-to-left",
    "ttob": "top-to-bottom",
    "btot": "bottom-to-top",
}

# Justify mappings (from justify_trans_dict)
JUSTIFY_MAP = {
    "l/t": "left",
    "r/b": "right",
    "cntr": "center",
    "full": "justify",
}

# Display effect mappings (from display_effect_trans_dict)
DISPLAY_EFFECT_MAP = {
    "snap": "snap",
    "fade": "fade",
    "wipe": "wipe",
    "mask": "mask",
}


# =============================================================================
# # CEA-608 models from Caption Inspector
# =============================================================================


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
