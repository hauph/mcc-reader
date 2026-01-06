import re


def timecode_to_microseconds(
    timecode: str, fps: float = 24.0, drop_frame: bool = False
) -> int:
    """
    Convert timecode (HH:MM:SS:FF or HH:MM:SS;FF) to microseconds.

    Args:
        timecode: Timecode string in format HH:MM:SS:FF (non-drop) or HH:MM:SS;FF (drop frame)
        fps: Frames per second
        drop_frame: Whether to use drop frame calculation

    Returns:
        Time in microseconds
    """
    # Handle both : and ; separators
    # Note: ; separator typically indicates drop frame timecode
    parts = re.split(r"[:;]", timecode)
    if len(parts) != 4:
        return 0

    hours, minutes, seconds, frames = map(int, parts)

    # Check if fps is in the drop frame range (29.97 or 59.94)
    is_2997_fps = 29.9 < fps < 30.1
    is_5994_fps = 59.9 < fps < 60.1

    if drop_frame and (is_2997_fps or is_5994_fps):
        # Drop frame timecode calculation
        # For 29.97fps, 2 frame numbers are dropped every minute except every 10th minute
        # For 59.94fps, 4 frame numbers are dropped
        drop_frames = 2 if is_2997_fps else 4

        # Calculate total minutes
        total_minutes = hours * 60 + minutes

        # Calculate frames dropped (not on 10-minute marks)
        frames_dropped = drop_frames * (total_minutes - (total_minutes // 10))

        # Calculate total frames
        frame_rate_rounded = 30 if is_2997_fps else 60
        total_frames = (
            hours * 3600 * frame_rate_rounded
            + minutes * 60 * frame_rate_rounded
            + seconds * frame_rate_rounded
            + frames
            - frames_dropped
        )

        # Convert to seconds using actual frame rate (29.97 or 59.94)
        actual_fps = 30000 / 1001 if is_2997_fps else 60000 / 1001
        total_seconds = total_frames / actual_fps
    else:
        # Non-drop frame calculation
        total_seconds = hours * 3600 + minutes * 60 + seconds + (frames / fps)

    return int(total_seconds * 1_000_000)
