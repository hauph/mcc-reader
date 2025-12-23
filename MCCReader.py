from decoder import decode_mcc_file

from langdetect import detect, DetectorFactory

# Make detection deterministic
DetectorFactory.seed = 0


class MCCReader:
    def __init__(self):
        self.tracks = None
        self.captions = None
        self.fps = None
        self.drop_frame = None
        self.languages = None

    def read(self, file_path: str):
        result = decode_mcc_file(file_path)
        self.captions = result["captions"]
        self.fps = result["metadata"]["fps"]
        self.drop_frame = result["metadata"].get("drop_frame", False)
        self.tracks = self._get_available_tracks()
        self.languages = self._detect_languages()

    def get_captions(self, track: str = None):
        """
        Get captions for a specific track or all captions.

        Args:
            track: Track identifier (e.g., "cea608_c1", "cea708_s1").
                   If None, returns all captions.
        """
        if track is None:
            return self.captions
        return self.captions.get(track)

    def get_tracks(self):
        """
        Get available caption tracks grouped by standard.

        Returns:
            Dictionary with cea608 and cea708 lists.
            Example: {"cea608": ["c1", "c3"], "cea708": ["s1", "s2"]}
        """
        return self.tracks

    def get_languages(self):
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
        return self.languages

    def _detect_languages(self):
        """
        Detect languages for all caption tracks using langdetect.

        Returns:
            Dictionary with detected languages per track.
        """
        result = {
            "cea608": {},
            "cea708": {},
        }

        for track_name, captions in self.captions.items():
            # Combine all caption text for better detection accuracy
            all_text = " ".join(
                caption.get("text", "") for caption in captions if caption.get("text")
            )

            if not all_text.strip():
                continue

            try:
                lang = detect(all_text)
            except Exception:
                lang = "unknown"

            # Categorize by track type
            if track_name.startswith("cea608_"):
                channel_id = track_name.replace("cea608_", "")
                result["cea608"][channel_id] = lang
            elif track_name.startswith("cea708_"):
                service_id = track_name.replace("cea708_", "")
                result["cea708"][service_id] = lang

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
            "cea608": [],
            "cea708": [],
        }

        for track_name in caption_tracks.keys():
            if track_name.startswith("cea608_"):
                # Extract channel identifier (e.g., "cea608_c1" -> "c1")
                channel_id = track_name.replace("cea608_", "")
                result["cea608"].append(channel_id)
            elif track_name.startswith("cea708_"):
                # Extract service identifier (e.g., "cea708_s1" -> "s1")
                service_id = track_name.replace("cea708_", "")
                result["cea708"].append(service_id)

        # Sort for consistent ordering
        result["cea608"].sort()
        result["cea708"].sort()

        return result
