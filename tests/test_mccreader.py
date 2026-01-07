import pytest
from unittest.mock import patch

# MCCReader requires lingua-language-detector library - skip all tests if not installed
pytest.importorskip("lingua", reason="lingua-language-detector library not installed")

from MCCReader import MCCReader
from MCCReader.constants import CEA608_FORMAT, CEA708_FORMAT

SAMPLE_FILE_NAME = "NightOfTheLivingDead"


class TestMCCReaderDetect:
    """Tests for MCCReader.detect() static method using sample files."""

    def test_detect_valid_mcc_file(self):
        """Should return True for valid MCC file."""
        with open(f"samples/{SAMPLE_FILE_NAME}.mcc", "r", encoding="utf-8-sig") as f:
            content = f.read()

        assert MCCReader.detect(content) is True

    def test_detect_wrong_header_file(self):
        """Should return False for file with wrong header."""
        with open("samples/Wrong_header.mcc", "r", encoding="utf-8-sig") as f:
            content = f.read()

        assert MCCReader.detect(content) is False

    def test_detect_text_file(self):
        """Should return False for non-MCC file."""
        with open("samples/text.txt", "r") as f:
            content = f.read()

        assert MCCReader.detect(content) is False

    def test_detect_plain_string(self):
        """Should return False for plain string without MCC header."""
        content = "This is not an MCC file"
        assert MCCReader.detect(content) is False

    def test_detect_valid_header_string(self):
        """Should return True for string with valid MCC header."""
        content = "File Format=MacCaption_MCC V1.0\n\nUUID=test"
        assert MCCReader.detect(content) is True


class TestMCCReaderBeforeRead:
    """Tests for MCCReader methods called before read()."""

    def test_get_captions_before_read_raises_error(self):
        """Should raise ValueError when get_captions called before read."""
        reader = MCCReader()

        with pytest.raises(ValueError) as exc_info:
            reader.get_captions()

        assert "No captions found" in str(exc_info.value)
        assert "read the file first" in str(exc_info.value)

    def test_get_formats_before_read_raises_error(self):
        """Should raise ValueError when get_formats called before read."""
        reader = MCCReader()

        with pytest.raises(ValueError) as exc_info:
            reader.get_formats()

        assert "No captions found" in str(exc_info.value)

    def test_properties_are_none_before_read(self):
        """Should have None properties before read."""
        reader = MCCReader()

        assert reader.tracks is None
        assert reader.captions is None
        assert reader.fps is None
        assert reader.drop_frame is None
        assert reader.formats is None
        assert reader.result is None
        assert reader.debug_metadata is None


class TestMCCReaderReadOnlyProperties:
    """Tests for read-only property enforcement."""

    def test_cannot_set_tracks(self):
        """Should raise AttributeError when trying to set tracks."""
        reader = MCCReader()

        with pytest.raises(AttributeError):
            reader.tracks = {"test": "value"}

    def test_cannot_set_captions(self):
        """Should raise AttributeError when trying to set captions."""
        reader = MCCReader()

        with pytest.raises(AttributeError):
            reader.captions = {"test": "value"}

    def test_cannot_set_fps(self):
        """Should raise AttributeError when trying to set fps."""
        reader = MCCReader()

        with pytest.raises(AttributeError):
            reader.fps = 30.0

    def test_cannot_set_drop_frame(self):
        """Should raise AttributeError when trying to set drop_frame."""
        reader = MCCReader()

        with pytest.raises(AttributeError):
            reader.drop_frame = True


class TestMCCReaderWithMockedDecoder:
    """Tests for MCCReader with mocked decode_mcc_file."""

    @pytest.fixture
    def mock_decode_result(self):
        """Create a mock decode result similar to real output."""
        return {
            "captions": {
                CEA608_FORMAT: {
                    "c1": [
                        {
                            "start": 7.3,
                            "end": 9.0,
                            "text": "Hello world",
                            "style": None,
                            "layout": None,
                        },
                        {
                            "start": 9.0,
                            "end": 11.0,
                            "text": "Second caption",
                            "style": None,
                            "layout": None,
                        },
                    ]
                },
                CEA708_FORMAT: {
                    "s1": [
                        {
                            "start": 7.3,
                            "end": 9.0,
                            "text": "Hello world",
                            "style": None,
                            "layout": None,
                        },
                    ]
                },
            },
            "metadata": {
                "fps": 29.97,
                "drop_frame": True,
                "debug": [
                    {
                        "level": "INFO",
                        "category": "DBG_GENERAL",
                        "source": "main.c:1",
                        "message": "Test",
                    }
                ],
            },
        }

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_read_populates_properties(self, mock_decode, mock_decode_result):
        """Should populate properties after read."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        assert reader.captions is not None
        assert reader.fps == 29.97
        assert reader.drop_frame is True
        assert reader.debug_metadata is not None

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_tracks_returns_available_tracks(self, mock_decode, mock_decode_result):
        """Should return available tracks after read."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        tracks = reader.get_tracks()

        assert CEA608_FORMAT in tracks
        assert CEA708_FORMAT in tracks
        assert "c1" in tracks[CEA608_FORMAT]
        assert "s1" in tracks[CEA708_FORMAT]

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_tracks_by_format(self, mock_decode, mock_decode_result):
        """Should return tracks for specific format."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        cea608_tracks = reader.get_tracks(CEA608_FORMAT)

        assert "c1" in cea608_tracks

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_formats_returns_available_formats(
        self, mock_decode, mock_decode_result
    ):
        """Should return available formats after read."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        formats = reader.get_formats()

        assert CEA608_FORMAT in formats
        assert CEA708_FORMAT in formats

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_captions_returns_all(self, mock_decode, mock_decode_result):
        """Should return all captions when no format specified."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        captions = reader.get_captions()

        assert CEA608_FORMAT in captions
        assert CEA708_FORMAT in captions

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_captions_by_format(self, mock_decode, mock_decode_result):
        """Should return captions for specific format."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        captions = reader.get_captions(format=CEA608_FORMAT)

        assert len(captions) == 2
        assert captions[0]["text"] == "Hello world"

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_captions_invalid_format_raises_error(
        self, mock_decode, mock_decode_result
    ):
        """Should raise ValueError for invalid format."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        with pytest.raises(ValueError) as exc_info:
            reader.get_captions(format="invalid_format")

        assert "not found" in str(exc_info.value)

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_fps_returns_fps(self, mock_decode, mock_decode_result):
        """Should return fps value."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        assert reader.get_fps() == 29.97

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_drop_frame_returns_value(self, mock_decode, mock_decode_result):
        """Should return drop_frame value."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        assert reader.get_drop_frame() is True

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_debug_metadata_returns_all(self, mock_decode, mock_decode_result):
        """Should return all debug metadata."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        debug = reader.get_debug_metadata()

        assert len(debug) == 1
        assert debug[0]["level"] == "INFO"

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_debug_metadata_by_level(self, mock_decode, mock_decode_result):
        """Should filter debug metadata by level."""
        mock_decode_result["metadata"]["debug"] = [
            {"level": "INFO", "category": "A", "source": "a.c:1", "message": "Info"},
            {"level": "WARN", "category": "B", "source": "b.c:1", "message": "Warning"},
            {"level": "ERROR", "category": "C", "source": "c.c:1", "message": "Error"},
        ]
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        info_debug = reader.get_debug_metadata(level="INFO")
        warn_debug = reader.get_debug_metadata(level="WARN")

        assert len(info_debug) == 1
        assert info_debug[0]["message"] == "Info"
        assert len(warn_debug) == 1
        assert warn_debug[0]["message"] == "Warning"

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_debug_metadata_invalid_level_raises_error(
        self, mock_decode, mock_decode_result
    ):
        """Should raise ValueError for invalid debug level."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        with pytest.raises(ValueError) as exc_info:
            reader.get_debug_metadata(level="INVALID")

        assert "Invalid level" in str(exc_info.value)

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_get_original_result(self, mock_decode, mock_decode_result):
        """Should return original decode result."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        result = reader.get_original_result()

        assert result == mock_decode_result

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_tracks_property_returns_same_as_get_tracks(
        self, mock_decode, mock_decode_result
    ):
        """Should have consistent tracks between property and method."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        assert reader.tracks == reader.get_tracks()

    @patch("MCCReader.MCCReader.decode_mcc_file")
    def test_formats_property_returns_same_as_get_formats(
        self, mock_decode, mock_decode_result
    ):
        """Should have consistent formats between property and method."""
        mock_decode.return_value = mock_decode_result

        reader = MCCReader()
        reader.read(f"samples/{SAMPLE_FILE_NAME}.mcc")

        assert reader.formats == reader.get_formats()
