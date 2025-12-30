from decoder import decode_mcc_file

from lingua import LanguageDetectorBuilder

from constants import (
    CEA608_FORMAT,
    CEA708_FORMAT,
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
        self._languages_to_tracks = {
            CEA608_FORMAT: {},
            CEA708_FORMAT: {},
        }
        self._tracks_to_languages = {
            CEA608_FORMAT: {},
            CEA708_FORMAT: {},
        }

    def read(self, file_path: str):
        result = decode_mcc_file(file_path)
        self.captions = result["captions"]
        self.fps = result["metadata"]["fps"]
        self.drop_frame = result["metadata"].get("drop_frame", False)
        self.tracks = self._get_available_tracks()
        self.languages = self._detect_languages()

    def get_captions(self, format: str = None, language: str = None):
        """
        Get captions for a specific track or all captions.
        """
        if format is None:
            return self.captions
        elif format is not None:
            tracks = self.get_tracks(format)
            if language is not None:
                track_from_language = self._languages_to_tracks.get(format).get(
                    language
                )
                if track_from_language is not None:
                    return self.captions.get(format).get(track_from_language[0])
                else:
                    print(f"No track found for language {language} in format {format}")
            else:
                if tracks is not None and len(tracks) > 0:
                    return self.captions.get(format).get(tracks[0])
                else:
                    return self.captions.get(format)

    def get_tracks(self, format: str = None):
        """
        Get available caption tracks grouped by standard.

        Returns:
            Dictionary with cea608 and cea708 lists.
            Example: {"cea608": ["c1", "c3"], "cea708": ["s1", "s2"]}
        """
        if format is None:
            return self.tracks
        return self.tracks.get(format)

    def get_languages(self, format: str = None):
        """
        Get detected languages for each track.

        Uses language detection on caption text to determine the language.
        Requires the 'langdetect' package: pip install langdetect

        Returns:
            Dictionary mapping track names to detected language codes.
            Example: {
                "cea608": {"c1": "en", "c3": "es"},
                "cea708": {"s1": "en", "s2": "es", "s3": "fr"}
            }
        """
        if format is None:
            return self.languages
        return self.languages.get(format)

    def get_fps(self):
        return self.fps

    def get_drop_frame(self):
        return self.drop_frame

    def get_formats(self):
        formats = []
        for format_name in self.captions.keys():
            if format_name == CEA608_FORMAT and format_name not in formats:
                formats.append(format_name)
            elif format_name == CEA708_FORMAT and format_name not in formats:
                formats.append(format_name)
        return formats

    def _detect_languages(self):
        """
        Detect languages for all caption tracks using langdetect.

        Returns:
            Dictionary with detected languages per track.
        """
        result = {
            CEA608_FORMAT: [],
            CEA708_FORMAT: [],
        }

        for format_name in self.captions.keys():
            for track_name in self.captions[format_name].keys():
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
        # Handle both full result dict and just the captions sub-dict
        caption_tracks = self.captions

        result = {
            CEA608_FORMAT: [],
            CEA708_FORMAT: [],
        }

        for format_name in caption_tracks.keys():
            if format_name == CEA608_FORMAT:
                for track_name in caption_tracks[format_name].keys():
                    result[CEA608_FORMAT].append(track_name)
            elif format_name == CEA708_FORMAT:
                for track_name in caption_tracks[format_name].keys():
                    result[CEA708_FORMAT].append(track_name)

        # Sort for consistent ordering
        result[CEA608_FORMAT].sort()
        result[CEA708_FORMAT].sort()

        return result
