import pytest
from src.parsers.ccd_parser import parse_ccd_metadata


class TestParseCcdMetadata:
    """Tests for parse_ccd_metadata function."""

    def test_no_ccd_file_returns_none(self, tmp_path):
        """Should return (None, None) when no .ccd file exists."""
        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))
        assert frame_rate is None
        assert drop_frame is None

    def test_parse_frame_rate_and_drop_frame(self, tmp_path):
        """Should parse frame rate and drop frame from .ccd file."""
        ccd_content = """File Format=Comcast CC Data File
Frame Rate=30
Drop Frame=True
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        # 30 fps with drop frame should convert to 29.97 (30000/1001)
        assert frame_rate == pytest.approx(30000 / 1001, rel=1e-6)
        assert drop_frame is True

    def test_non_drop_frame(self, tmp_path):
        """Should return exact frame rate when drop frame is False."""
        ccd_content = """Frame Rate=25
Drop Frame=
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate == 25.0
        assert drop_frame is False

    def test_drop_frame_24fps(self, tmp_path):
        """Should convert 24fps to 23.976 with drop frame."""
        ccd_content = """Frame Rate=24
Drop Frame=True
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate == pytest.approx(24000 / 1001, rel=1e-6)
        assert drop_frame is True

    def test_drop_frame_60fps(self, tmp_path):
        """Should convert 60fps to 59.94 with drop frame."""
        ccd_content = """Frame Rate=60
Drop Frame=True
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate == pytest.approx(60000 / 1001, rel=1e-6)
        assert drop_frame is True

    def test_non_ntsc_rate_with_drop_frame(self, tmp_path):
        """Should not convert non-NTSC rates even with drop frame."""
        ccd_content = """Frame Rate=25
Drop Frame=True
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        # 25fps is PAL, shouldn't be converted even with drop frame
        assert frame_rate == 25.0
        assert drop_frame is True

    def test_invalid_frame_rate(self, tmp_path):
        """Should handle invalid frame rate value gracefully."""
        ccd_content = """Frame Rate=invalid
Drop Frame=True
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate is None
        assert drop_frame is True

    def test_missing_frame_rate(self, tmp_path):
        """Should return None for frame rate if not present."""
        ccd_content = """Drop Frame=True
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate is None
        assert drop_frame is True

    def test_missing_drop_frame(self, tmp_path):
        """Should return None for drop frame if not present."""
        ccd_content = """Frame Rate=30
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate == 30.0
        assert drop_frame is None

    def test_frame_rate_with_decimal(self, tmp_path):
        """Should handle decimal frame rates."""
        ccd_content = """Frame Rate=29.97
Drop Frame=
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate == pytest.approx(29.97, rel=1e-6)
        assert drop_frame is False

    def test_drop_frame_false_string(self, tmp_path):
        """Should correctly parse 'False' string as False boolean."""
        ccd_content = """Frame Rate=30
Drop Frame=False
"""
        ccd_file = tmp_path / "test.ccd"
        ccd_file.write_text(ccd_content)

        frame_rate, drop_frame = parse_ccd_metadata(str(tmp_path))

        assert frame_rate == 30.0
        assert drop_frame is False
