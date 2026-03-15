import asyncio
import json
import logging
import pyaudio  # pyre-ignore[21]
from vosk import Model, KaldiRecognizer  # pyre-ignore[21]
from aura.core.module_base import BaseModule  # pyre-ignore[21]
from aura.core.events import EventBus, AuraEvent  # pyre-ignore[21]
from typing import Optional

logger = logging.getLogger(__name__)

class VoskASRModule(BaseModule):
    """
    Offline Speech-To-Text capability using Vosk API.
    Can be run in non-blocking event-driven mode.
    """

    def __init__(self, model_path: str = "model", sample_rate: int = 16000,
                 enable_mic: bool = False, device_index: Optional[int] = None):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.enable_mic = enable_mic
        self.device_index = device_index
        self.model = None
        self.bus: Optional[EventBus] = None
        self._listening = False
        self._thread: Optional[asyncio.Task] = None  # pyre-ignore[31]

        # Audio Stream Configuration
        self.chunk_size = 8000
        self.audio_format = pyaudio.paInt16
        self.channels = 1

    @property
    def module_name(self) -> str:
        return "asr"

    async def initialize(self, bus: EventBus) -> bool:
        self.bus = bus
        try:
            # Vosk Model Loading
            logger.info(f"Loading Vosk ASR model from '{self.model_path}'...")
            self.model = Model(self.model_path)

            if self.enable_mic:
                # Start the background listening task
                self._listening = True
                self._thread = asyncio.create_task(self._listen_loop())
                logger.info("Vosk ASR module initialized and microphone listening started.")
            else:
                logger.info("Vosk ASR module initialized. Microphone capture is currently disabled.")

            return True

        except Exception as e:
            logger.error(f"Failed to initialize Vosk ASR model at '{self.model_path}': {e}")
            return False

    async def _listen_loop(self):
        """Continuous background loop capturing audio chunks and running them through Vosk."""
        # Initialize PyAudio
        p = pyaudio.PyAudio()

        try:
            stream = p.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=self.device_index
            )

            recognizer = KaldiRecognizer(self.model, self.sample_rate)

            logger.info("Microphone stream opened. Awaiting speech...")

            while self._listening:
                # We use asyncio.to_thread to prevent PyAudio's blocking read from freezing the Event Bus
                data = await asyncio.to_thread(stream.read, self.chunk_size, exception_on_overflow=False)

                if recognizer.AcceptWaveform(data):
                    result_json = recognizer.Result()
                    result_dict = json.loads(result_json)
                    text = result_dict.get("text", "").strip()

                    if text:
                        logger.info(f"Vosk Recognized Speech: '{text}'")
                        bus = self.bus
                        if bus:
                            # Use asyncio.run_coroutine_threadsafe if we had the actual main loop,
                            # but for demonstration we can schedule it if the bus handles thread safety
                            # or emit an event to the bus.
                            asyncio.run_coroutine_threadsafe(
                                bus.publish(AuraEvent(type="user_input_received", payload={"text": text}, source=self.module_name)),
                                asyncio.get_event_loop()
                            )
                # Yield control back to the event loop so other modules can process their events
                await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"Error in Vosk listening loop: {e}")
        finally:
            self._listening = False
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
            p.terminate()
            logger.info("Microphone stream closed.")

    def stop_listening(self):
        """Safely terminate the listening loop."""
        self._listening = False
