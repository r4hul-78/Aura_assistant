"""
AudioFileManager — Resource lifecycle manager for temporary TTS audio files.

Lifecycle stages:
  creation  → generate() produces a unique .wav path
  tracking  → path is added to an internal registry
  usage     → callers write/read the file (TTS + player)
  retention → files remain on disk until program exit
  cleanup   → atexit hook deletes all tracked files
"""

import os
import time
import atexit
import logging
from pathlib import Path
from typing import FrozenSet, Set

logger = logging.getLogger(__name__)


class AudioFileManager:
    """Manages creation, tracking, and cleanup of temporary audio files."""

    def __init__(self, output_dir: str = "outputs"):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        self._registry: Set[str] = set()
        self._counter: int = 0  # Monotonic counter for collision safety

        # Register cleanup to run when the interpreter exits
        atexit.register(self.cleanup)  # pyre-ignore[6]
        logger.info("AudioFileManager initialized — cleanup registered via atexit.")

    @property
    def registry(self) -> FrozenSet[str]:
        """Read-only view of all tracked file paths."""
        return frozenset(self._registry)

    def generate(self) -> str:
        """Create a unique .wav file path and register it for lifecycle tracking.

        Uses nanosecond timestamp + monotonic counter to guarantee uniqueness
        even under rapid consecutive calls.
        """
        self._counter += 1
        filename = f"aura_{time.time_ns()}_{self._counter}.wav"
        filepath = str(self._output_dir / filename)

        self._registry.add(filepath)
        logger.debug(f"Generated audio path: {filepath}")
        return filepath

    def cleanup(self) -> None:
        """Delete all tracked audio files. Errors are logged but never raised."""
        if not self._registry:
            return

        logger.info(f"AudioFileManager cleanup: removing {len(self._registry)} file(s).")
        for filepath in list(self._registry):
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.debug(f"Deleted: {filepath}")
            except OSError as e:
                # File may be locked by a player — log and continue
                logger.warning(f"Could not delete '{filepath}': {e}")
        self._registry.clear()
