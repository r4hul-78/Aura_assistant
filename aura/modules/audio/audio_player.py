import asyncio
import logging
import subprocess
from aura.core.module_base import BaseModule  # pyre-ignore[21]
from aura.core.events import EventBus, AuraEvent  # pyre-ignore[21]
from typing import Optional

logger = logging.getLogger(__name__)


class AudioPlayerModule(BaseModule):
    """
    Subscribes to 'audio_ready' events and plays the .wav file using
    the Windows built-in media player (no extra dependencies needed).
    Falls back to playsound if available, then to a system beep.
    """

    def __init__(self):
        self.bus: Optional[EventBus] = None

    @property
    def module_name(self) -> str:
        return "audio_player"

    async def initialize(self, bus: EventBus) -> bool:
        self.bus = bus
        bus.subscribe("audio_ready", self.handle_audio_ready)
        logger.info("AudioPlayerModule ready — subscribed to audio_ready events.")
        return True

    async def handle_audio_ready(self, event: AuraEvent):
        """Plays the synthesized .wav file as soon as it's ready."""
        file_path = event.payload.get("file_path", "")
        if not file_path:
            return

        logger.info(f"Playing audio: {file_path}")

        # Run the blocking playback in a thread so the event loop stays free
        await asyncio.to_thread(self._play, file_path)  # pyre-ignore[6]

    @staticmethod
    def _play(file_path: str):
        """Blocking audio playback — called from a background thread."""
        try:
            # playsound (already installed)
            from playsound import playsound  # pyre-ignore[21]
            playsound(file_path)
            return
        except Exception:
            pass

        try:
            # Windows fallback: use the built-in Media Player via PowerShell
            subprocess.run(
                [
                    "powershell", "-c",
                    f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"
                ],
                check=True
            )
        except Exception as e:
            logger.error(f"Audio playback failed: {e}")
