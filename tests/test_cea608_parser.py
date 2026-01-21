import pytest
from MCCReader.parsers.cea608_parser import (
    parse_608_text_with_positions,
    parse_608_text_segments,
    parse_608_layout,
    parse_608_file,
)


class TestParse608TextSegments:
    """Tests for parse_608_text_segments function - style tracking."""

    def test_single_style_returns_style_not_segments(self):
        """Should return style dict and None segments for single-style text."""
        content = '{FG-Blue} "Hello world"'
        text, style, segments = parse_608_text_segments(content)
        assert text == "Hello world"
        assert style == {"color": "blue"}
        assert segments is None

    def test_multiple_styles_returns_segments(self):
        """Should return None style and segments list for multi-style text."""
        content = '{FG-Red} "Red text" {FG-Green} "Green text"'
        text, style, segments = parse_608_text_segments(content)
        assert text == "Red textGreen text"
        assert style is None
        assert len(segments) == 2
        assert segments[0]["text"] == "Red text"
        assert segments[0]["style"]["color"] == "red"
        assert segments[1]["text"] == "Green text"
        assert segments[1]["style"]["color"] == "green"

    def test_no_style_returns_none(self):
        """Should return None for both style and segments when no style codes present."""
        content = '"Plain text"'
        text, style, segments = parse_608_text_segments(content)
        assert text == "Plain text"
        # When there's no style, both style and segments are None
        assert style is None
        assert segments is None

    def test_italic_white_style(self):
        """Should parse italic white as combined style."""
        content = '{FG-Italic-White} "Styled"'
        _, style, _ = parse_608_text_segments(content)
        assert style["font-style"] == "italic"
        assert style["color"] == "white"

    def test_background_color(self):
        """Should parse background color."""
        content = '{BG-Blue} "Text with bg"'
        _, style, _ = parse_608_text_segments(content)
        assert style["background-color"] == "blue"

    def test_underline_style(self):
        """Should parse underline flag."""
        content = '{UL} "Underlined text"'
        _, style, _ = parse_608_text_segments(content)
        assert style["text-decoration"] == "underline"

    def test_pac_color(self):
        """Should parse PAC color codes."""
        content = '{R14:Yellow} "Yellow text"'
        _, style, _ = parse_608_text_segments(content)
        assert style["color"] == "yellow"

    def test_mixed_styled_and_unstyled(self):
        """Should handle transition from styled to unstyled text."""
        # When style changes to nothing, text continues with previous style
        content = '{FG-Blue} "Blue" "More text"'
        text, style, segments = parse_608_text_segments(content)
        # Both segments have same style, so should be single style
        assert text == "BlueMore text"
        assert style == {"color": "blue"}
        assert segments is None

    def test_style_change_creates_segments(self):
        """Should create segments when style changes mid-caption."""
        content = '{FG-White} "White " {FG-Yellow} "Yellow"'
        _, style, segments = parse_608_text_segments(content)
        assert style is None
        assert len(segments) == 2
        assert segments[0]["style"]["color"] == "white"
        assert segments[1]["style"]["color"] == "yellow"

    def test_empty_content(self):
        """Should handle empty content."""
        text, style, segments = parse_608_text_segments("")
        assert text == ""
        assert style is None
        assert segments is None


class TestParse608TextWithPositions:
    """Tests for parse_608_text_with_positions function."""

    def test_single_line_text(self):
        """Should parse single line of text."""
        content = '{R14:C8} "Hello world"'
        text, lines = parse_608_text_with_positions(content)
        assert text == "Hello world"
        assert len(lines) == 1
        assert lines[0]["row"] == 14
        assert lines[0]["column"] == 8

    def test_two_row_text(self):
        """Should parse text across two rows with line break."""
        content = '{R14:C8} "Line one" {R15:C4} "Line two"'
        text, lines = parse_608_text_with_positions(content)
        assert text == "Line one\nLine two"
        assert len(lines) == 2
        assert lines[0]["row"] == 14
        assert lines[1]["row"] == 15

    def test_same_row_concatenation(self):
        """Should concatenate text on same row."""
        content = '{R14:C8} "Hello" {R14:C14} "world"'
        text, lines = parse_608_text_with_positions(content)
        assert "Hello" in text
        assert "world" in text
        assert len(lines) == 1

    def test_empty_content(self):
        """Should handle empty content."""
        content = ""
        text, lines = parse_608_text_with_positions(content)
        assert text == ""
        assert lines == []

    def test_rows_sorted_by_number(self):
        """Should sort lines by row number."""
        content = '{R15:C0} "Bottom" {R14:C0} "Top"'
        text, lines = parse_608_text_with_positions(content)
        assert lines[0]["row"] == 14
        assert lines[1]["row"] == 15
        assert text == "Top\nBottom"

    def test_unclosed_quote_at_end(self):
        """Should extract text from unclosed quotes at end of content (truncated files)."""
        content = '{R15:C4} {TO2} {TO2} "[bacround chter]'
        text, lines = parse_608_text_with_positions(content)
        assert text == "[bacround chter]"
        assert len(lines) == 1
        assert lines[0]["text"] == "[bacround chter]"

    def test_mixed_closed_and_unclosed_quotes(self):
        """Should handle both closed quotes and unclosed quote at end."""
        content = '{R14:C0} "First line" {R15:C0} "Second line'
        text, lines = parse_608_text_with_positions(content)
        assert "First line" in text
        assert "Second line" in text
        assert len(lines) == 2


class TestParse608Layout:
    """Tests for parse_608_layout function."""

    def test_extract_row_and_column(self):
        """Should extract row and column from position code."""
        content = '{R14:C8} "Hello"'
        layout = parse_608_layout(content)
        assert layout["row"] == 14
        assert layout["column"] == 8

    def test_vertical_percent_calculation(self):
        """Should calculate vertical percentage (row/14 * 100)."""
        content = '{R7:C0} "Middle"'
        layout = parse_608_layout(content)
        assert layout["vertical_percent"] == 50.0  # 7/14 * 100

    def test_horizontal_percent_calculation(self):
        """Should calculate horizontal percentage (col/31 * 100)."""
        content = '{R0:C15} "Center-ish"'
        layout = parse_608_layout(content)
        # 15/31 * 100 ≈ 48.39
        assert layout["horizontal_percent"] == pytest.approx(48.39, rel=0.01)

    def test_tab_offset_extraction(self):
        """Should extract tab offset."""
        content = '{R14:C8} {TO3} "Hello"'
        layout = parse_608_layout(content)
        assert layout["tab_offset"] == 3

    def test_paint_on_mode(self):
        """Should detect paint-on mode from {RDC}."""
        content = '{RDC} {R14:C8} "Hello"'
        layout = parse_608_layout(content)
        assert layout["mode"] == "paint-on"

    def test_pop_on_mode(self):
        """Should detect pop-on mode from {RCL}."""
        content = '{RCL} {R14:C8} "Hello"'
        layout = parse_608_layout(content)
        assert layout["mode"] == "pop-on"

    def test_roll_up_mode(self):
        """Should detect roll-up mode from {RU2}, {RU3}, or {RU4}."""
        for code in ["{RU2}", "{RU3}", "{RU4}"]:
            content = f'{code} {{R14:C8}} "Hello"'
            layout = parse_608_layout(content)
            assert layout["mode"] == "roll-up"

    def test_no_position_returns_empty(self):
        """Should return empty dict when no position codes present."""
        content = '"Just text"'
        layout = parse_608_layout(content)
        assert "row" not in layout
        assert "column" not in layout


class TestParse608File:
    """Tests for parse_608_file function."""

    def test_parse_sample_file(self, tmp_path):
        """Should parse a simple .608 file."""
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:00:01:00 - {RCL} {R14:C8} "Hello world"
00:00:02:00 - {EOC}
00:00:03:00 - {RCL} {R14:C4} "Second caption"
00:00:04:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 2
        assert captions[0]["text"] == "Hello world"
        assert captions[1]["text"] == "Second caption"

    def test_parse_with_style(self, tmp_path):
        """Should preserve style information."""
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:00:01:00 - {RCL} {R14:C8} {FG-Italic-White} "Styled text"
00:00:02:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        assert captions[0]["style"]["font-style"] == "italic"
        assert captions[0]["style"]["color"] == "white"

    def test_parse_multiline_caption(self, tmp_path):
        """Should handle captions with multiple rows."""
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:00:01:00 - {RCL} {R14:C8} "Line one" {R15:C4} "Line two"
00:00:02:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        assert "Line one" in captions[0]["text"]
        assert "Line two" in captions[0]["text"]
        assert "\n" in captions[0]["text"]

    def test_timecode_conversion(self, tmp_path):
        """Should convert timecodes to microseconds.

        For pop-on captions (RCL), the caption is NOT visible until EOC.
        So start time should be at EOC, not when loading begins.
        """
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:00:01:00 - {RCL} {R14:C8} "Hello"
00:00:02:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        # Pop-on caption displays at EOC (02:00), not when loaded (01:00)
        assert captions[0]["start"] == pytest.approx(2_000_000, rel=0.01)
        # End time is None when unknown (no subsequent EOC/EDM)
        assert captions[0]["end"] is None

    def test_layout_information(self, tmp_path):
        """Should include layout information."""
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:00:01:00 - {RCL} {R14:C8} {TO2} "Hello"
00:00:02:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        assert captions[0]["layout"]["row"] == 14
        assert captions[0]["layout"]["column"] == 8
        assert captions[0]["layout"]["tab_offset"] == 2
        assert captions[0]["layout"]["mode"] == "pop-on"

    def test_empty_file(self, tmp_path):
        """Should handle file with only header."""
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        assert captions == []

    def test_preserves_timecode_strings(self, tmp_path):
        """Should preserve original timecode strings.

        For pop-on captions, start_timecode is when caption becomes visible (EOC).
        """
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:01:30:12 - {RCL} {R14:C8} "Hello"
00:01:32:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        # Pop-on caption's start time is at EOC when it becomes visible
        assert captions[0]["start_timecode"] == "00:01:32:00"
        # End time is None when unknown (no subsequent EOC/EDM)
        assert captions[0]["end_timecode"] is None

    def test_parse_with_multiple_styles_creates_segments(self, tmp_path):
        """Should create segments when caption has multiple styles."""
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:00:01:00 - {RCL} {R14:C8} {FG-Blue} "Blue text" {FG-White} "White text"
00:00:02:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        assert captions[0]["style"] is None  # None when segments present
        assert captions[0]["segments"] is not None
        assert len(captions[0]["segments"]) == 2
        assert captions[0]["segments"][0]["text"] == "Blue text"
        assert captions[0]["segments"][0]["style"]["color"] == "blue"
        assert captions[0]["segments"][1]["text"] == "White text"
        assert captions[0]["segments"][1]["style"]["color"] == "white"

    def test_parse_with_single_style_no_segments(self, tmp_path):
        """Should not create segments for single-style caption."""
        file_content = """Decoded Line 21 / CEA-608 for Asset: test - Channel: 1
00:00:01:00 - {RCL} {R14:C8} {FG-Blue} "All blue text"
00:00:02:00 - {EOC}
"""
        test_file = tmp_path / "test.608"
        test_file.write_text(file_content)

        captions = parse_608_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        assert captions[0]["style"] == {"color": "blue"}
        assert captions[0].get("segments") is None
