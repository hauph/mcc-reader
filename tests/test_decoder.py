import pytest
import os
import subprocess
from unittest.mock import patch, MagicMock

from MCCReader.decoder import decode_mcc_file, parse_caption_files
from MCCReader.constants import CEA608_FORMAT, CEA708_FORMAT

OUTPUT_DIR = "samples/output"


class TestParseCaptioneFiles:
    """Tests for parse_caption_files function using pre-generated output files."""

    def test_parse_existing_output_directory(self):
        """Should parse the existing OUTPUT_DIR directory."""

        result = parse_caption_files(OUTPUT_DIR)

        assert "captions" in result
        assert "metadata" in result
        assert CEA608_FORMAT in result["captions"]
        assert CEA708_FORMAT in result["captions"]

    def test_parse_extracts_cea608_captions(self):
        """Should extract CEA-608 captions from .608 files."""

        result = parse_caption_files(OUTPUT_DIR)

        # Should have c1 channel from NightOfTheLivingDead-C1.608
        assert "c1" in result["captions"][CEA608_FORMAT]
        captions = result["captions"][CEA608_FORMAT]["c1"]
        assert len(captions) > 0
        # Each caption should have required fields
        assert "text" in captions[0]
        assert "start" in captions[0]

    def test_parse_extracts_cea708_captions(self):
        """Should extract CEA-708 captions from .708 files."""

        result = parse_caption_files(OUTPUT_DIR)

        # Should have s1 service from NightOfTheLivingDead-S1.708
        assert "s1" in result["captions"][CEA708_FORMAT]
        captions = result["captions"][CEA708_FORMAT]["s1"]
        assert len(captions) > 0
        assert "text" in captions[0]
        assert "start" in captions[0]

    def test_parse_extracts_metadata_from_ccd(self):
        """Should extract frame rate and drop frame from .ccd file."""

        result = parse_caption_files(OUTPUT_DIR)

        # The sample has 30DF (30 drop frame) = 29.97fps
        assert result["metadata"]["fps"] == pytest.approx(29.97, rel=0.01)
        assert result["metadata"]["drop_frame"] is True

    def test_parse_empty_directory(self, tmp_path):
        """Should return empty captions for directory with no caption files."""
        result = parse_caption_files(str(tmp_path))

        assert result["captions"][CEA608_FORMAT] == {}
        assert result["captions"][CEA708_FORMAT] == {}


class TestDecodeMccFileValidation:
    """Tests for decode_mcc_file input validation."""

    def test_file_not_found_raises_error(self):
        """Should raise FileNotFoundError for non-existent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            decode_mcc_file("nonexistent.mcc")

        assert "MCC file not found" in str(exc_info.value)

    def test_wrong_extension_raises_error(self, tmp_path):
        """Should raise ValueError for non-.mcc file."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")

        with pytest.raises(ValueError) as exc_info:
            decode_mcc_file(str(txt_file))

        assert ".mcc extension" in str(exc_info.value)

    def test_empty_file_raises_error(self, tmp_path):
        """Should raise ValueError for empty .mcc file."""
        empty_mcc = tmp_path / "empty.mcc"
        empty_mcc.write_text("")

        with pytest.raises(ValueError) as exc_info:
            decode_mcc_file(str(empty_mcc))

        assert "no content" in str(exc_info.value)

    def test_wrong_header_raises_error(self, tmp_path):
        """Should raise ValueError for .mcc file with wrong header."""
        bad_mcc = tmp_path / "bad.mcc"
        bad_mcc.write_text("Wrong header content")

        with pytest.raises(ValueError) as exc_info:
            decode_mcc_file(str(bad_mcc))

        assert "no proper header" in str(exc_info.value)

    def test_valid_header_sample_file(self):
        """Should not raise error for valid MCC file header check."""
        # Just verify the sample file passes header validation
        # (Will fail at subprocess if caption-inspector not installed)
        mcc_path = "samples/NightOfTheLivingDead.mcc"

        # Read and verify header manually
        with open(mcc_path, "r", encoding="utf-8-sig") as f:
            content = f.read()

        assert content.startswith("File Format=MacCaption_MCC")


class TestDecodeMccFileMocked:
    """Tests for decode_mcc_file with mocked subprocess."""

    @patch("MCCReader.decoder.subprocess.run")
    @patch("MCCReader.decoder.parse_caption_files")
    @patch("MCCReader.decoder.parse_debug_file")
    def test_calls_caption_inspector(self, mock_debug, mock_parse, mock_run, tmp_path):
        """Should call caption-inspector with correct arguments."""
        # Setup mocks
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        mock_parse.return_value = {
            "captions": {CEA608_FORMAT: {}, CEA708_FORMAT: {}},
            "metadata": {"fps": 29.97, "drop_frame": True, "source_dir": str(tmp_path)},
        }
        mock_debug.return_value = []

        # Create valid MCC file
        mcc_file = tmp_path / "test.mcc"
        mcc_file.write_text("File Format=MacCaption_MCC V1.0\n\n00:00:00:00\tdata")
        output_dir = str(tmp_path / "output")
        os.makedirs(output_dir, exist_ok=True)

        decode_mcc_file(str(mcc_file), output_dir=output_dir)

        # Verify caption-inspector was called
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "caption-inspector"
        assert "-o" in call_args
        assert str(mcc_file) in call_args

    @patch("MCCReader.decoder.subprocess.run")
    def test_handles_caption_inspector_failure(self, mock_run, tmp_path):
        """Should raise RuntimeError when caption-inspector fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error message")

        mcc_file = tmp_path / "test.mcc"
        mcc_file.write_text("File Format=MacCaption_MCC V1.0\n\n00:00:00:00\tdata")

        with pytest.raises(RuntimeError) as exc_info:
            decode_mcc_file(str(mcc_file))

        assert "Caption Inspector failed" in str(exc_info.value)

    @patch("MCCReader.decoder.subprocess.run")
    def test_handles_caption_inspector_not_found(self, mock_run, tmp_path):
        """Should raise RuntimeError when caption-inspector not installed."""
        mock_run.side_effect = FileNotFoundError()

        mcc_file = tmp_path / "test.mcc"
        mcc_file.write_text("File Format=MacCaption_MCC V1.0\n\n00:00:00:00\tdata")

        with pytest.raises(RuntimeError) as exc_info:
            decode_mcc_file(str(mcc_file))

        assert "not found" in str(exc_info.value)

    @patch("MCCReader.decoder.subprocess.run")
    def test_handles_timeout(self, mock_run, tmp_path):
        """Should raise RuntimeError on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="caption-inspector", timeout=300
        )

        mcc_file = tmp_path / "test.mcc"
        mcc_file.write_text("File Format=MacCaption_MCC V1.0\n\n00:00:00:00\tdata")

        with pytest.raises(RuntimeError) as exc_info:
            decode_mcc_file(str(mcc_file))

        assert "timed out" in str(exc_info.value)
