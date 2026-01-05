from src.parsers.dbg_parser import parse_debug_file


class TestParseDebugFile:
    """Tests for parse_debug_file function."""

    def test_no_dbg_file_returns_empty(self, tmp_path):
        """Should return empty list when no .dbg file exists."""
        result = parse_debug_file(str(tmp_path))
        assert result == []

    def test_parse_info_level(self, tmp_path):
        """Should parse INFO level entries."""
        dbg_content = """INFO DBG_GENERAL [main.c:194] - Version: v0.0
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 1
        assert result[0]["level"] == "INFO"
        assert result[0]["category"] == "DBG_GENERAL"
        assert result[0]["source"] == "main.c:194"
        assert result[0]["message"] == "Version: v0.0"

    def test_parse_warn_level(self, tmp_path):
        """Should parse WARN level entries."""
        dbg_content = """WARN DBG_708_DEC [dtvcc_decode.c:628] - Skipping Unknown G2 Char: 0x03
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 1
        assert result[0]["level"] == "WARN"
        assert result[0]["category"] == "DBG_708_DEC"
        assert result[0]["source"] == "dtvcc_decode.c:628"
        assert result[0]["message"] == "Skipping Unknown G2 Char: 0x03"

    def test_parse_error_level(self, tmp_path):
        """Should parse ERROR level entries."""
        dbg_content = """ERROR DBG_FILE_IN [autodetect_file.c:100] - Failed to open file
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 1
        assert result[0]["level"] == "ERROR"

    def test_parse_fatal_level(self, tmp_path):
        """Should parse FATAL level entries."""
        dbg_content = """FATAL DBG_GENERAL [main.c:50] - Critical failure occurred
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 1
        assert result[0]["level"] == "FATAL"

    def test_parse_verbose_level(self, tmp_path):
        """Should parse VERBOSE level entries."""
        dbg_content = """VERBOSE DBG_608_DEC [line21_decode.c:100] - Processing frame data
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 1
        assert result[0]["level"] == "VERBOSE"

    def test_parse_multiple_entries(self, tmp_path):
        """Should parse multiple entries in order."""
        dbg_content = """INFO DBG_GENERAL [main.c:194] - Version: v0.0
WARN DBG_708_DEC [dtvcc_decode.c:628] - Warning message
ERROR DBG_FILE_IN [file.c:10] - Error message
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 3
        assert result[0]["level"] == "INFO"
        assert result[1]["level"] == "WARN"
        assert result[2]["level"] == "ERROR"

    def test_preserves_original_order(self, tmp_path):
        """Should preserve entries in original file order."""
        dbg_content = """WARN DBG_CCD_OUT [cc_data_output.c:1580] - First warning
INFO DBG_GENERAL [main.c:285] - Info message
WARN DBG_608_DEC [line21_decode.c:268] - Second warning
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 3
        assert result[0]["message"] == "First warning"
        assert result[1]["message"] == "Info message"
        assert result[2]["message"] == "Second warning"

    def test_skip_empty_lines(self, tmp_path):
        """Should skip empty lines."""
        dbg_content = """INFO DBG_GENERAL [main.c:1] - First

INFO DBG_GENERAL [main.c:2] - Second

"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 2

    def test_skip_malformed_lines(self, tmp_path):
        """Should skip lines that don't match the pattern."""
        dbg_content = """INFO DBG_GENERAL [main.c:194] - Valid entry
This is not a valid debug line
Another invalid line without proper format
WARN DBG_708_DEC [dtvcc_decode.c:628] - Another valid entry
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 2
        assert result[0]["level"] == "INFO"
        assert result[1]["level"] == "WARN"

    def test_message_with_special_characters(self, tmp_path):
        """Should handle messages with special characters."""
        dbg_content = """INFO DBG_FILE_IN [mcc_file.c:223] - Caption Window: 00:00:07;09 to 00:00:36;24
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 1
        assert "00:00:07;09" in result[0]["message"]
        assert "00:00:36;24" in result[0]["message"]

    def test_message_with_hex_values(self, tmp_path):
        """Should handle messages with hex values."""
        dbg_content = """WARN DBG_CCD_OUT [cc_data_output.c:1580] - {1} - Skipping Unknown G2 Char: 0x03 Srvc: 1
"""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text(dbg_content)

        result = parse_debug_file(str(tmp_path))

        assert len(result) == 1
        assert "0x03" in result[0]["message"]

    def test_empty_file(self, tmp_path):
        """Should return empty list for empty .dbg file."""
        dbg_file = tmp_path / "test.dbg"
        dbg_file.write_text("")

        result = parse_debug_file(str(tmp_path))

        assert result == []
