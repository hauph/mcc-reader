from typing import List, Union
from decoder import decode_mcc_file

from lingua import LanguageDetectorBuilder

from constants import (
    CEA608_FORMAT,
    CEA708_FORMAT,
    CaptionFormat,
    DEBUG_LEVELS,
    DebugLevels,
)

# Build language detector once (supports common caption languages)
_language_detector = LanguageDetectorBuilder.from_all_languages().build()


class MCCReader:
    def __init__(self):
        self.tracks = None
        self.captions = None
        self.fps = None
        self.drop_frame = None
        self.languages = None
        self.formats = None
        self.result = None
        self.debug_metadata = None
        self._languages_to_tracks = {
            CEA608_FORMAT: {},
            CEA708_FORMAT: {},
        }
        self._tracks_to_languages = {
            CEA608_FORMAT: {},
            CEA708_FORMAT: {},
        }

    def read(self, file_path: str, output_dir: str = None):
        result = decode_mcc_file(file_path, output_dir=output_dir)
        self.result = result
        self.captions = result["captions"]
        self.debug_metadata = result["metadata"]["debug"]
        self.fps = result["metadata"]["fps"]
        self.drop_frame = result["metadata"].get("drop_frame", False)
        self.tracks = self._get_available_tracks()
        self.languages = self._detect_languages()
        self.formats = self._get_available_formats()

    def get_captions(self, format: CaptionFormat = None, language: str = None):
        """
        Get captions for a specific track or all captions.

        Args:
            format: The format of the captions to get.
            language: The language of the captions to get.

        Returns:
            The captions for the specified format and language or all captions.
        """
        self._raise_error_if_captions_is_none()

        if format is None:
            print("No format provided, returning all captions")
            return self.captions
        elif format is not None:
            all_formats = self.get_formats()
            if format not in all_formats:
                raise ValueError(f"Format {format} not found")

            if language is not None:
                track_from_language = self._languages_to_tracks.get(format).get(
                    language
                )
                if track_from_language is not None:
                    return self.captions.get(format).get(track_from_language[0])
                else:
                    raise ValueError(
                        f"No track found for language {language} in format {format}"
                    )
            else:
                tracks = self.get_tracks(format)
                if tracks is not None and len(tracks) > 0:
                    # To make it simpler, always return the first track
                    return self.captions.get(format).get(tracks[0])
                else:
                    print(f"No track found for format {format}, returning all tracks")
                    return self.captions.get(format)

    def get_tracks(self, format: CaptionFormat = None):
        """
        Get available caption tracks grouped by standard.

        Returns:
            Dictionary with cea608 and cea708 lists.
            Example: {"cea608": ["c1", "c3"], "cea708": ["s1", "s2"]}
        """
        if self.tracks is None:
            print("No tracks found, getting available tracks ...")
            self.tracks = self._get_available_tracks()

        if format is None:
            print("No format provided, returning all tracks")
            return self.tracks
        else:
            print(f"Returning tracks for format {format}")
            return self.tracks.get(format)

    def get_languages(self, format: CaptionFormat = None):
        """
        Get detected languages for each track.

        Returns:
            Dictionary mapping track names to detected language codes.
            Example: {
                "cea608": {"c1": "en", "c3": "es"},
                "cea708": {"s1": "en", "s2": "es", "s3": "fr"}
            }
        """
        if self.languages is None:
            print("No languages found, detecting languages ...")
            self.languages = self._detect_languages()

        if format is None:
            print("No format provided, returning all languages")
            return self.languages
        else:
            print(f"Returning languages for format {format}")
            return self.languages.get(format)

    def get_fps(self):
        return self.fps

    def get_drop_frame(self):
        return self.drop_frame

    def get_formats(self):
        if self.formats is None:
            print("No formats found, getting available formats ...")
            self.formats = self._get_available_formats()
        return self.formats

    def get_debug_metadata(self, level: Union[DebugLevels, List[DebugLevels]] = None):
        """
        Get debug metadata for a specific level or all levels.

        Args:
            level: The level of the debug metadata to get.

        Returns:
            The debug metadata for the specified level or all levels.
        """
        if level is None:
            return self.debug_metadata
        elif isinstance(level, str):
            if level not in DEBUG_LEVELS:
                raise ValueError(f"Invalid level: {level}")
            return [entry for entry in self.debug_metadata if entry["level"] == level]
        elif isinstance(level, list):
            invalid_levels = [lvl for lvl in level if lvl not in DEBUG_LEVELS]
            if invalid_levels:
                raise ValueError(f"Invalid level(s): {invalid_levels}")
            return [entry for entry in self.debug_metadata if entry["level"] in level]

    def get_original_result(self):
        return self.result

    @staticmethod
    def detect(content: str) -> bool:
        """Simple check to validate whether the given content is a proper MCC file by checking its header.

        Args:
            content: The content of the file to check.

        Returns:
            True if the content is a proper MCC file, False otherwise.
        """
        lines = content.splitlines()
        if lines[0].startswith("File Format=MacCaption_MCC"):
            return True
        else:
            return False

    def _get_available_formats(self):
        self._raise_error_if_captions_is_none()

        formats: List[CaptionFormat] = []
        for format_name in self.captions.keys():
            if format_name not in formats:
                formats.append(format_name)
        return formats

    def _detect_languages(self):
        """
        Detect languages for all caption tracks using lingua-language-detector.

        Returns:
            Dictionary with detected languages per track.
        """
        self._raise_error_if_captions_is_none()

        result = {
            CEA608_FORMAT: [],
            CEA708_FORMAT: [],
        }

        for format_name in self.get_formats():
            for track_name in self.get_tracks(format_name):
                captions = self.captions[format_name][track_name]
                full_text = ""
                for caption in captions:
                    text = caption.get("text", "")
                    if not text.strip():
                        continue
                    full_text += f" {text}"

                if not full_text.strip():
                    continue

                detected_language = _language_detector.detect_language_of(full_text)
                if detected_language is None:
                    continue

                lang = detected_language.iso_code_639_1.name.lower()
                if lang not in self._languages_to_tracks[format_name]:
                    self._languages_to_tracks[format_name][lang] = []
                self._languages_to_tracks[format_name][lang].append(track_name)
                self._tracks_to_languages[format_name][track_name] = lang

                if lang not in result[format_name]:
                    result[format_name].append(lang)

        return result

    def _get_available_tracks(self):
        """
        Extract available caption tracks grouped by standard (CEA-608 vs CEA-708).

        Returns:
            Dictionary with cea608 and cea708 lists containing available track identifiers.
            Example: {"cea608": ["c1", "c3"], "cea708": ["s1", "s2", "s3"]}
        """
        self._raise_error_if_captions_is_none()

        caption_tracks = self.get_captions()

        result = {}

        for format_name in caption_tracks.keys():
            result[format_name] = []
            for track_name in caption_tracks[format_name].keys():
                result[format_name].append(track_name)

        # Sort for consistent ordering
        for format_name in result.keys():
            result[format_name].sort()

        return result

    def _raise_error_if_captions_is_none(self):
        if self.captions is None:
            raise ValueError("No captions found, please read the file first")
