import pytest
from MCCReader.parsers.cea708_parser import (
    cea708_color_to_rgb,
    cea708_opacity_to_css,
    parse_708_text_with_positions,
    parse_708_layout,
    parse_708_file,
    decode_p16_character,
    extract_text_with_p16,
)


class TestDecodeP16Character:
    """Tests for decode_p16_character function (single hex value to Unicode)."""

    def test_decode_arabic_alef(self):
        """Should decode Arabic letter Alef (U+0627)."""
        result = decode_p16_character("0627")
        assert result == "ا"

    def test_decode_arabic_ba(self):
        """Should decode Arabic letter Ba (U+0628)."""
        result = decode_p16_character("0628")
        assert result == "ب"

    def test_decode_chinese_character(self):
        """Should decode Chinese character (U+4E2D)."""
        result = decode_p16_character("4E2D")
        assert result == "中"

    def test_decode_persian_kaf(self):
        """Should decode Persian Kaf (U+06A9)."""
        result = decode_p16_character("06A9")
        assert result == "ک"

    def test_decode_japanese_hiragana(self):
        """Should decode Japanese Hiragana (U+3042)."""
        result = decode_p16_character("3042")
        assert result == "あ"

    def test_decode_korean(self):
        """Should decode Korean Hangul (U+D55C)."""
        result = decode_p16_character("D55C")
        assert result == "한"

    def test_decode_ascii(self):
        """Should decode ASCII character (U+0041 = A)."""
        result = decode_p16_character("0041")
        assert result == "A"

    def test_invalid_hex_returns_empty(self):
        """Should return empty string for invalid hex."""
        result = decode_p16_character("ZZZZ")
        assert result == ""

    def test_empty_string_returns_empty(self):
        """Should return empty string for empty input."""
        result = decode_p16_character("")
        assert result == ""


class TestExtractTextWithP16:
    """Tests for extract_text_with_p16 function - handles P16 outside quotes."""

    def test_extract_p16_outside_quotes(self):
        """Should extract P16 sequences that appear outside of quoted text."""
        # This is how Caption Inspector outputs Farsi/Arabic text
        content = '"-" {P16:0x06A9} {P16:0x0647} " " {P16:0x06A9}'
        result = extract_text_with_p16(content)
        # "-" + ک (0x06A9) + ه (0x0647) + " " (space) + ک (0x06A9)
        assert result == "-که ک"

    def test_extract_farsi_text(self):
        """Should properly extract Farsi text from mixed content."""
        # Real example from S6.708 file
        content = '"-2020." {SPL:R1-C0} "-" {P16:0x06A9} {P16:0x0647} " " {P16:0x06A9} {P16:0x0634} {P16:0x0634} " " {P16:0x0627} {P16:0x0633} {P16:0x062A} "."'
        result = extract_text_with_p16(content)
        # -2020. -که کشش است.
        assert "2020" in result
        assert "که" in result  # Farsi word
        assert "است" in result  # Farsi word for "is"

    def test_extract_only_quoted_text(self):
        """Should work with just quoted text (no P16)."""
        content = '"Hello" " " "World"'
        result = extract_text_with_p16(content)
        assert result == "Hello World"

    def test_extract_only_p16(self):
        """Should work with only P16 sequences."""
        content = "{P16:0x0041}{P16:0x0042}{P16:0x0043}"  # ABC
        result = extract_text_with_p16(content)
        assert result == "ABC"

    def test_extract_empty_content(self):
        """Should handle empty content."""
        result = extract_text_with_p16("")
        assert result == ""

    def test_extract_persian_kaf(self):
        """Should decode Persian Kaf (ک) correctly."""
        content = "{P16:0x06A9}"  # Persian Kaf
        result = extract_text_with_p16(content)
        assert result == "ک"

    def test_extract_with_control_codes_ignored(self):
        """Should ignore control codes like ETX, NUL."""
        content = '"{P16:0x0645}" {ETX} {NUL} "text"'
        result = extract_text_with_p16(content)
        # The {P16:...} inside quotes won't be decoded by extract_text_with_p16
        # but outer P16 sequences would be
        assert "text" in result


class TestCea708ColorToRgb:
    """Tests for cea708_color_to_rgb function."""

    def test_black_color(self):
        """Should convert R0G0B0 to black (#000000)."""
        result = cea708_color_to_rgb(0, 0, 0)
        assert result == "#000000"

    def test_white_color(self):
        """Should convert R3G3B3 to white (#FFFFFF)."""
        result = cea708_color_to_rgb(3, 3, 3)
        assert result == "#FFFFFF"

    def test_red_color(self):
        """Should convert R3G0B0 to red (#FF0000)."""
        result = cea708_color_to_rgb(3, 0, 0)
        assert result == "#FF0000"

    def test_green_color(self):
        """Should convert R0G3B0 to green (#00FF00)."""
        result = cea708_color_to_rgb(0, 3, 0)
        assert result == "#00FF00"

    def test_blue_color(self):
        """Should convert R0G0B3 to blue (#0000FF)."""
        result = cea708_color_to_rgb(0, 0, 3)
        assert result == "#0000FF"

    def test_mid_gray_color(self):
        """Should convert R2G2B2 to mid-gray (#AAAAAA)."""
        result = cea708_color_to_rgb(2, 2, 2)
        assert result == "#AAAAAA"

    def test_custom_color(self):
        """Should convert R1G2B3 to custom color (#55AAFF)."""
        result = cea708_color_to_rgb(1, 2, 3)
        assert result == "#55AAFF"


class TestCea708OpacityToCss:
    """Tests for cea708_opacity_to_css function."""

    def test_solid_opacity(self):
        """Should return 'solid' for opacity 0."""
        assert cea708_opacity_to_css(0) == "solid"

    def test_flash_opacity(self):
        """Should return 'flash' for opacity 1."""
        assert cea708_opacity_to_css(1) == "flash"

    def test_translucent_opacity(self):
        """Should return 'translucent' for opacity 2."""
        assert cea708_opacity_to_css(2) == "translucent"

    def test_transparent_opacity(self):
        """Should return 'transparent' for opacity 3."""
        assert cea708_opacity_to_css(3) == "transparent"

    def test_invalid_opacity_defaults_to_solid(self):
        """Should default to 'solid' for invalid opacity values."""
        assert cea708_opacity_to_css(5) == "solid"
        assert cea708_opacity_to_css(-1) == "solid"


class TestParse708TextWithPositions:
    """Tests for parse_708_text_with_positions function."""

    def test_single_position_text(self):
        """Should parse text at single position."""
        content = '{SPL:R0-C10} "Hello world"'
        text, lines = parse_708_text_with_positions(content)
        assert text == "Hello world"
        assert len(lines) == 1
        assert lines[0]["row"] == 0
        assert lines[0]["column"] == 10

    def test_two_position_text(self):
        """Should parse text at two positions with line break."""
        content = '{SPL:R1-C12} "Line two" {SPL:R0-C16} "Line one"'
        text, lines = parse_708_text_with_positions(content)
        # Should be sorted by row (0 first, then 1)
        assert "Line one" in text
        assert "Line two" in text
        assert "\n" in text
        assert len(lines) == 2
        assert lines[0]["row"] == 0  # Sorted
        assert lines[1]["row"] == 1

    def test_empty_content(self):
        """Should handle empty content."""
        content = ""
        text, lines = parse_708_text_with_positions(content)
        assert text == ""
        assert lines == []

    def test_rows_sorted_ascending(self):
        """Should sort lines by row number ascending."""
        content = '{SPL:R2-C0} "Third" {SPL:R0-C0} "First" {SPL:R1-C0} "Second"'
        text, lines = parse_708_text_with_positions(content)
        assert lines[0]["row"] == 0
        assert lines[1]["row"] == 1
        assert lines[2]["row"] == 2
        assert text == "First\nSecond\nThird"

    def test_unclosed_quote_at_end(self):
        """Should extract text from unclosed quotes at end of content (truncated files)."""
        content = '{SPL:R0-C10} "[background chatter]'
        text, lines = parse_708_text_with_positions(content)
        assert text == "[background chatter]"
        assert len(lines) == 1
        assert lines[0]["text"] == "[background chatter]"

    def test_mixed_closed_and_unclosed_quotes(self):
        """Should handle both closed quotes and unclosed quote at end."""
        content = '{SPL:R0-C0} "First line" {SPL:R1-C0} "Second line'
        text, lines = parse_708_text_with_positions(content)
        assert "First line" in text
        assert "Second line" in text
        assert len(lines) == 2


class TestParse708Layout:
    """Tests for parse_708_layout function."""

    def test_extract_popup_mode(self):
        """Should detect pop-up mode from DF tag."""
        content = "{DF0:PopUp-Cntrd:R1-C29:Anchor-UL-V65-H0:Pen-MonoSerif:Pr-0:VIS}"
        layout = parse_708_layout(content)
        assert layout["mode"] == "pop-on"

    def test_extract_rollup_mode(self):
        """Should detect roll-up mode from DF tag."""
        content = "{DF0:RollUp-Left:R2-C20:Anchor-UL-V65-H0}"
        layout = parse_708_layout(content)
        assert layout["mode"] == "roll-up"

    def test_extract_painton_mode(self):
        """Should detect paint-on mode from DF tag."""
        content = "{DF0:PaintOn-Left:R2-C20:Anchor-UL-V65-H0}"
        layout = parse_708_layout(content)
        assert layout["mode"] == "paint-on"

    def test_extract_center_alignment(self):
        """Should detect centered alignment."""
        content = "{DF0:PopUp-Cntrd:R1-C29:Anchor-UL-V65-H0}"
        layout = parse_708_layout(content)
        assert layout["text-align"] == "center"

    def test_extract_left_alignment(self):
        """Should detect left alignment."""
        content = "{DF0:PopUp-Left:R1-C29:Anchor-UL-V65-H0}"
        layout = parse_708_layout(content)
        assert layout["text-align"] == "left"

    def test_extract_window_size(self):
        """Should extract window rows and columns."""
        content = "{DF0:PopUp-Cntrd:R1-C29:Anchor-UL-V65-H0}"
        layout = parse_708_layout(content)
        assert layout["window_rows"] == 1
        assert layout["window_columns"] == 29

    def test_extract_anchor_position(self):
        """Should extract anchor point and position."""
        content = "{DF0:PopUp-Cntrd:R1-C29:Anchor-UL-V65-H0}"
        layout = parse_708_layout(content)
        assert layout["anchor"] == "UL"
        assert layout["vertical_percent"] == 65
        assert layout["horizontal_percent"] == 0

    def test_extract_priority(self):
        """Should extract priority value."""
        content = "{DF0:PopUp-Cntrd:R1-C29:Pr-5}"
        layout = parse_708_layout(content)
        assert layout["priority"] == 5

    def test_extract_visibility(self):
        """Should detect visible flag."""
        content = "{DF0:PopUp-Cntrd:R1-C29:VIS}"
        layout = parse_708_layout(content)
        assert layout["visible"] is True

    def test_extract_pen_location(self):
        """Should extract pen location from SPL tag."""
        content = '{SPL:R1-C12} "Hello"'
        layout = parse_708_layout(content)
        assert layout["row"] == 1
        assert layout["column"] == 12

    def test_extract_multiple_pen_positions(self):
        """Should extract multiple pen positions."""
        content = '{SPL:R1-C12} "Line 1" {SPL:R0-C16} "Line 0"'
        layout = parse_708_layout(content)
        assert len(layout["pen_positions"]) == 2
        assert layout["pen_positions"][0] == {"row": 1, "column": 12}
        assert layout["pen_positions"][1] == {"row": 0, "column": 16}

    def test_no_layout_returns_empty(self):
        """Should return empty dict when no layout codes present."""
        content = '"Just text"'
        layout = parse_708_layout(content)
        assert layout == {}


class TestParse708File:
    """Tests for parse_708_file function."""

    def test_parse_simple_file(self, tmp_path):
        """Should parse a simple .708 file."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:00:01:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:Pen-MonoSerif:Pr-0:VIS} {SPL:R0-C10} "Hello world"
00:00:02:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:Pen-MonoSerif:Pr-0:VIS} {SPL:R0-C10} "Second caption"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 2
        assert captions[0]["text"] == "Hello world"
        assert captions[1]["text"] == "Second caption"

    def test_parse_multiline_caption(self, tmp_path):
        """Should parse caption with multiple pen positions."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:00:01:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R1-C29:Anchor-UL-V65-H0:Pen-MonoSerif:Pr-0:VIS} {SPL:R1-C12} "Line two" {SPL:R0-C16} "Line one"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        assert "Line one" in captions[0]["text"]
        assert "Line two" in captions[0]["text"]
        assert "\n" in captions[0]["text"]

    def test_parse_with_style(self, tmp_path):
        """Should preserve style information."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:00:01:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0} {SPA:Pen-[Size:Standard]:IT} {SPL:R0-C10} "Italic text"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        assert captions[0]["style"]["font-style"] == "italic"

    def test_parse_with_layout(self, tmp_path):
        """Should preserve layout information."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:00:01:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R1-C29:Anchor-UL-V65-H0:Pen-MonoSerif:Pr-0:VIS} {SPL:R0-C10} "Hello"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert captions[0]["layout"]["mode"] == "pop-on"
        assert captions[0]["layout"]["text-align"] == "center"
        assert captions[0]["layout"]["anchor"] == "UL"

    def test_timecode_conversion(self, tmp_path):
        """Should convert timecodes to microseconds."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:00:01:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:VIS} {SPL:R0-C10} "Hello"
00:00:02:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:VIS} {SPL:R0-C10} "World"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert captions[0]["start"] == pytest.approx(1_000_000, rel=0.01)
        assert captions[0]["end"] == pytest.approx(2_000_000, rel=0.01)

    def test_preserves_timecode_strings(self, tmp_path):
        """Should preserve original timecode strings."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:01:30:12 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:VIS} {SPL:R0-C10} "Hello"
00:01:32:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:VIS} {SPL:R0-C10} "World"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert captions[0]["start_timecode"] == "00:01:30:12"
        assert captions[0]["end_timecode"] == "00:01:32:00"

    def test_empty_file(self, tmp_path):
        """Should handle file with only header."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert captions == []

    def test_last_caption_unknown_end_time(self, tmp_path):
        """Last caption should have None end time if no subsequent command."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:00:10:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:VIS} {SPL:R0-C10} "Last caption"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        # End time is None when unknown - consuming application decides
        assert captions[0]["end"] is None

    def test_parse_with_p16_characters(self, tmp_path):
        """Should decode P16 extended characters (e.g., Farsi) that appear OUTSIDE quotes."""
        # This is the actual format from Caption Inspector - P16 sequences are outside quotes
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 6
00:00:01:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:VIS} {SPL:R0-C10} "-" {P16:0x06A9} {P16:0x0647} " " {P16:0x06A9} {P16:0x0634} {P16:0x0634} "."
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        # Should contain Farsi characters: که کشش (keh kashesh)
        assert "که" in captions[0]["text"]
        assert "کشش" in captions[0]["text"]

    def test_parse_mixed_ascii_and_p16(self, tmp_path):
        """Should handle mixed ASCII and P16 content (P16 outside quotes)."""
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 1
00:00:01:00 - {DLW:11111111} {DF0:PopUp-Cntrd:R0-C20:Anchor-UL-V65-H0:VIS} {SPL:R0-C10} "Hello " {P16:0x4E16} {P16:0x754C} " World"
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        assert "Hello" in captions[0]["text"]
        assert "世界" in captions[0]["text"]  # Chinese "world" decoded
        assert "World" in captions[0]["text"]

    def test_parse_real_farsi_line(self, tmp_path):
        """Should parse real Farsi content from S6.708 format."""
        # Actual line from BigBuckBunny S6.708
        file_content = """Decoded DTVCC / CEA-708 for Asset: test - Service: 6
00:00:00:02 - {DLW:00000001} {DF0:PopUp-Cntrd:R1-C41:Anchor-UL-V65-H55:Pen-MonoSerif:Pr-0} {SPL:R0-C6} {SPC:FG-Solid-R2G2B2:BG-Solid-R0G0B0:Edg-R1G1B1} "-2020." {SPL:R1-C0} "-" {P16:0x06A9} {P16:0x0647} " " {P16:0x06A9} {P16:0x0634} {P16:0x0634} " " {P16:0x0627} {P16:0x0633} {P16:0x062A} "."
"""
        test_file = tmp_path / "test.708"
        test_file.write_text(file_content)

        captions = parse_708_file(str(test_file), fps=24.0, drop_frame=False)

        assert len(captions) == 1
        # Should contain: -2020. and Farsi text
        assert "2020" in captions[0]["text"]
        assert "است" in captions[0]["text"]  # Farsi word for "is"
