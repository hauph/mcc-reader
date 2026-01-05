import pytest
from src.utils import timecode_to_seconds


class TestTimecodeToSeconds:
    """Tests for timecode_to_seconds function."""

    def test_zero_timecode(self):
        """Should return 0 for 00:00:00:00."""
        result = timecode_to_seconds("00:00:00:00", fps=24.0)
        assert result == 0.0

    def test_one_second(self):
        """Should return 1.0 for one second timecode."""
        result = timecode_to_seconds("00:00:01:00", fps=24.0)
        assert result == 1.0

    def test_one_minute(self):
        """Should return 60.0 for one minute timecode."""
        result = timecode_to_seconds("00:01:00:00", fps=24.0)
        assert result == 60.0

    def test_one_hour(self):
        """Should return 3600.0 for one hour timecode."""
        result = timecode_to_seconds("01:00:00:00", fps=24.0)
        assert result == 3600.0

    def test_frames_at_24fps(self):
        """Should correctly convert frames at 24fps."""
        # 12 frames at 24fps = 0.5 seconds
        result = timecode_to_seconds("00:00:00:12", fps=24.0)
        assert result == pytest.approx(0.5, rel=1e-6)

    def test_frames_at_30fps(self):
        """Should correctly convert frames at 30fps."""
        # 15 frames at 30fps = 0.5 seconds
        result = timecode_to_seconds("00:00:00:15", fps=30.0)
        assert result == pytest.approx(0.5, rel=1e-6)

    def test_frames_at_25fps(self):
        """Should correctly convert frames at 25fps (PAL)."""
        # 25 frames at 25fps = 1 second
        result = timecode_to_seconds("00:00:01:00", fps=25.0)
        assert result == 1.0

    def test_complex_timecode(self):
        """Should correctly convert complex timecode."""
        # 01:30:45:12 at 24fps = 1*3600 + 30*60 + 45 + 12/24 = 5445.5
        result = timecode_to_seconds("01:30:45:12", fps=24.0)
        assert result == pytest.approx(5445.5, rel=1e-6)

    def test_semicolon_separator(self):
        """Should handle semicolon separator (drop frame notation)."""
        result = timecode_to_seconds("00:00:01;00", fps=24.0)
        assert result == 1.0

    def test_invalid_timecode_returns_zero(self):
        """Should return 0.0 for invalid timecode format."""
        result = timecode_to_seconds("invalid", fps=24.0)
        assert result == 0.0

    def test_incomplete_timecode_returns_zero(self):
        """Should return 0.0 for incomplete timecode."""
        result = timecode_to_seconds("00:00:00", fps=24.0)
        assert result == 0.0

    def test_drop_frame_2997_basic(self):
        """Should calculate drop frame correctly at 29.97fps."""
        # At 29.97fps, frames are dropped at minute marks (except every 10th)
        # 00:01:00:00 in drop frame should account for dropped frames
        result = timecode_to_seconds("00:01:00:00", fps=29.97, drop_frame=True)
        # Non-drop would be 60.0, drop frame is slightly different
        assert result == pytest.approx(59.94, rel=0.01)

    def test_drop_frame_at_10_minute_mark(self):
        """Should not drop frames at 10-minute marks."""
        # At 10 minute marks, no additional frames are dropped
        result = timecode_to_seconds("00:10:00:00", fps=29.97, drop_frame=True)
        # 10 minutes = 600 seconds nominal
        # 9 minutes of drops (2 frames each) = 18 frames dropped
        assert result == pytest.approx(599.4, rel=0.01)

    def test_non_drop_frame_at_2997fps(self):
        """Should use simple calculation when drop_frame=False at 29.97fps."""
        result = timecode_to_seconds("00:00:01:00", fps=29.97, drop_frame=False)
        assert result == pytest.approx(1.0, rel=0.01)

    def test_drop_frame_5994fps(self):
        """Should handle 59.94fps drop frame (4 frames dropped per minute)."""
        result = timecode_to_seconds("00:01:00:00", fps=59.94, drop_frame=True)
        # Should account for 4 dropped frames at 59.94fps
        assert result == pytest.approx(59.94, rel=0.01)

    def test_drop_frame_disabled_at_24fps(self):
        """Should ignore drop_frame flag at non-NTSC frame rates."""
        # Drop frame only applies to 29.97 and 59.94fps
        result_df = timecode_to_seconds("00:01:00:00", fps=24.0, drop_frame=True)
        result_ndf = timecode_to_seconds("00:01:00:00", fps=24.0, drop_frame=False)
        assert result_df == result_ndf == 60.0

    def test_drop_frame_disabled_at_25fps(self):
        """Should ignore drop_frame flag at PAL frame rate."""
        result_df = timecode_to_seconds("00:01:00:00", fps=25.0, drop_frame=True)
        result_ndf = timecode_to_seconds("00:01:00:00", fps=25.0, drop_frame=False)
        assert result_df == result_ndf == 60.0

    def test_mixed_separator_types(self):
        """Should handle both : and ; in the same timecode."""
        # Real-world drop frame timecodes use ; before frames
        result = timecode_to_seconds("00:00:07;09", fps=29.97, drop_frame=True)
        assert result > 7.0  # Should be slightly more than 7 seconds

    def test_large_frame_number(self):
        """Should handle frame numbers up to fps-1."""
        # 23 frames at 24fps
        result = timecode_to_seconds("00:00:00:23", fps=24.0)
        assert result == pytest.approx(23 / 24, rel=1e-6)
