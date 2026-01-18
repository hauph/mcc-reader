# MCCReader

A Python library for reading and parsing MCC (MacCaption) closed caption files. Extracts CEA-608 and CEA-708 caption data using [Caption Inspector](https://github.com/Comcast/caption-inspector) with automatic language detection.

## Preface

Once, I worked on a project that required me to parse MCC files and get the caption data in a structured format. In the Python world, there is [Pycaption](https://github.com/pbs/pycaption), the famous library for parsing caption files. However, it does not support MCC files :disappointed:.

I struggeled to find a public or open-source library that did this (maybe I just didn't look hard enough). Therefore, I decided to vibe code this library, based on the amazing [Caption Inspector](https://github.com/Comcast/caption-inspector) by Comcast, to help me (and maybe others) parse MCC files.

## Features

- 📝 Parse MCC files into structured caption data. In order to achive this, I followed the script [cshim.py](https://github.com/Comcast/caption-inspector/blob/master/python/cshim.py) from Caption Inspector to understand how they decode the MCC files and return the output files. Furthermore, as inspired by Pycaption, I tried to produce as similar caption data as possible (with some differences):
  - `start`: Start time in microseconds.
  - `start_timecode`: Start time in timecode format.
  - `end`: End time in microseconds.
  - `end_timecode`: End time in timecode format.
  - `text`: Caption decoded text.
  - `style`: A dictionary with CSS-like styling rules (`None` if not present).
  - `layout`: A Layout object with the necessary positioning information (`None` if not present).
- 🎯 Support for both **CEA-608** (Line 21) and **CEA-708** (DTVCC) formats.
- 🌍 Automatic language detection using [lingua](https://github.com/pemistahl/lingua-py).
- ⏱️ Frame rate and drop frame detection from output file (.ccd).
- 🐛 Debug metadata extraction for troubleshooting from output file (.dbg).
- 🐳 Docker support with pre-built [Caption Inspector](https://github.com/Comcast/caption-inspector).

## Requirements

- Python 3.8+ (recommended: 3.11).

<!-- ## Installation -->

<!-- ### Using pip

```bash
pip install MCCReader
```-->

## Usage

### Basic Usage

```python
from MCCReader import MCCReader

reader = MCCReader()
reader.read("path/to/file.mcc")

# Get all captions
captions = reader.get_captions()

# Get captions by format
cea608_captions = reader.get_captions(format="cea608")
cea708_captions = reader.get_captions(format="cea708")

# Get captions by format and language
spanish_captions = reader.get_captions(format="cea608", language="es")
```

### Other Available Methods

```python
# Get available caption tracks
reader.get_tracks()              # All tracks: {"cea608": ["c1"], "cea708": ["s1"]}
reader.get_tracks("cea608")      # CEA-608 only: ["c1", "c3"]

# Get detected languages
reader.get_languages()           # {"cea608": {"c1": "en", "c3": "es"}, "cea708": {"s1": "en", "s2": "es", "s3": "fr"}}
reader.get_languages("cea608")   # {"c1": "en", "c3": "es"}

# Get available formats
reader.get_formats()             # ["cea608", "cea708"]

# Get metadata
reader.get_fps()                 # 29.97
reader.get_drop_frame()          # True/False

# Get debug information
reader.get_debug_metadata()                    # All debug entries
reader.get_debug_metadata(level="WARN")        # Filter by level
reader.get_debug_metadata(level=["WARN", "ERROR"]) # Filter by multiple levels
## List of all debug levels: 
## (captured from https://github.com/Comcast/caption-inspector/blob/master/python/cshim.py#L27C12-L27C112)
### DEBUG_LEVELS = [
###     UNKNOWN_DEBUG_LEVEL,
###     VERBOSE,
###     INFO,
###     WARN,
###     ERROR,
###     FATAL,
###     ASSERT,
### ]

# Get the original decoded result
reader.get_original_result()

# Validate MCC file content
MCCReader.detect(file_content)   # Returns True if valid MCC format
```

### Saving Output Files

Specify an output directory to keep the decoded caption files:

```python
reader.read("file.mcc", output_dir="./output")
```

This generates:

- `*.608` - [CEA-608 Decode File](https://comcast.github.io/caption-inspector/html/docs-page.html#section-7-2)
- `*.708` - [CEA-708 Decode File](https://comcast.github.io/caption-inspector/html/docs-page.html#section-7-3)  
- `*.ccd` - [Closed Caption Descriptor File](https://comcast.github.io/caption-inspector/html/docs-page.html#section-7-4)
- `*.dbg` - [Debug File](https://comcast.github.io/caption-inspector/html/docs-page.html#section-7-6)

If no output directory is specified, the output files will be saved temporarily in `/tmp/caption_output` and will be cleaned up after decoding is done.

## Caption Output Format

Captions are returned as a list of dictionaries:

```python
{
    "captions": {
        "cea608": {
            "c1": [
                {
                    "start": 7307300,
                    "start_timecode": "00:00:07:09",
                    "end": 9075730,
                    "end_timecode": "00:00:09:02",
                    "text": "Hello World\nMy Name is Hau",
                    "style": {"font-style": "italic", "color": "white"},
                    "layout": {
                        "row": 14,
                        "column": 8,
                        "vertical_percent": 100.0,
                        "horizontal_percent": 25.806451612903224,
                        "all_positions": [
                            {"row": 14, "column": 8},
                            {"row": 15, "column": 4},
                        ],
                        "tab_offset": 3,
                        "mode": "paint-on",
                        "control_codes": ["RDC"],
                        "lines": [
                            {"row": 14, "column": 8, "text": "Hello World"},
                            {"row": 15, "column": 4, "text": "My Name is Hau"},
                        ],
                    },
                },
                # ...
            ]
        },
        "cea708": {
            "s1": [
                {
                    "start": 7374030,
                    "start_timecode": "00:00:07:11",
                    "end": 9075730,
                    "end_timecode": "00:00:09:02",
                    "text": "Hello World\nMy Name is Hau",
                    "style": {"font-family": "monospace, serif"},
                    "layout": {
                        "window_id": 0,
                        "mode": "pop-on",
                        "window_style": "PopUp-Cntrd",
                        "text-align": "center",
                        "window_rows": 1,
                        "window_columns": 29,
                        "anchor": "UL",
                        "anchor_description": "upper-left",
                        "vertical_percent": 65,
                        "horizontal_percent": 0,
                        "priority": 0,
                        "visible": True,
                        "pen_positions": [
                            {"row": 1, "column": 12},
                            {"row": 0, "column": 16},
                        ],
                        "row": 1,
                        "column": 12,
                        "delete_windows": "11111111",
                        "lines": [
                            {"row": 0, "column": 16, "text": "Hello World"},
                            {
                                "row": 1,
                                "column": 12,
                                "text": "My Name is Hau",
                            },
                        ],
                    },
                },
                # ...
            ]
        }
    },
    "metadata": {
        "fps": 29.97,
        "drop_frame": True,
        "input_file": "path/to/file.mcc",
        "output_files": [
            "path/to/file.608",
            "path/to/file.708",
            "path/to/file.ccd",
            "path/to/file.dbg",
        ],
        "source_dir": "path",
        "debug": [
            {
                "level": "WARN",
                "category": "DBG_608_DEC",
                "source": "line21_decode.c:268",
                "message": "Ambiguous Line 21 Captioning Type on Channel 1: PopOn - 1; RollUp - 0; PaintOn - 1",
            },
            {
                "level": "INFO",
                "category": "DBG_GENERAL",
                "source": "main.c:285",
                "message": "Total Runtime: 0 seconds",
            },
            # ...
        ]
    }
}
```

## Development

- Build the Docker image which includes Caption Inspector and all dependencies:

```bash
docker build -t mcc-reader .
```

- Watch for file changes during development:

```bash
./dev.sh --watch
```

All development commands:

`./dev.sh`: Run [dev.py](./dev.py) once.
`./dev.sh --watch`: Watch mode: auto-reload on Python file changes (except [watch.py](./watch.py)).

- Run the example script inside the Docker container:

```bash
docker run -v $(pwd)/samples:/app/samples mcc-reader \
    python dev.py
```

- Run tests (recommended inside a [virtual environment](https://www.w3schools.com/django/django_create_virtual_environment.php)):

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Many Thanks

- [caption-inspector](https://github.com/Comcast/caption-inspector) by Comcast.
- [lingua](https://github.com/pemistahl/lingua-py) by pemistahl.
- [watchdog](https://github.com/gorakhargosh/watchdog) by gorakhargosh.

## Postface

I am not an expert in Closed Captioning (CEA-608, CEA-708 and other formats), so this library is not perfect and may not be the best way to parse MCC files. Therefore, I would appreciate any suggestions and improvements.
