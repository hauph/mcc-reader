from enum import Enum


class CaptionFormat(str, Enum):
    CEA608 = "cea608"
    CEA708 = "cea708"


CEA608_FORMAT = CaptionFormat.CEA608.value
CEA708_FORMAT = CaptionFormat.CEA708.value

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
