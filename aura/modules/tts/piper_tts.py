import os
import subprocess
import asyncio
import logging
from typing import Optional
from aura.core.module_base import BaseModule  # pyre-ignore[21]
from aura.core.events import EventBus, AuraEvent  # pyre-ignore[21]
from aura.core.audio_file_manager import AudioFileManager  # pyre-ignore[21]

logger = logging.getLogger(__name__)

class PiperTTSModule(BaseModule):
    """
    Offline Text-To-Speech generation using the fast, local piper-tts tool.
    Listens for text generation events asynchronously and outputs audio files.
    """

    def __init__(self, model_path: str, output_dir: str = "outputs", executable_path: str = "piper"):
        self.model_path = model_path
        self.output_dir = output_dir
        self.executable_path = executable_path
        self.bus: Optional[EventBus] = None
        # Injected externally; falls back to a local instance
        self.file_manager: Optional[AudioFileManager] = None

    @property
    def module_name(self) -> str:
        return "tts"

    async def initialize(self, bus: EventBus) -> bool:
        self.bus = bus
        # Ensure a file manager is available (create a local one if not injected)
        if self.file_manager is None:
            self.file_manager = AudioFileManager(output_dir=self.output_dir)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        try:
            subprocess.run([self.executable_path, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Piper TTS executable verified at: {self.executable_path}")
            
            # Subscribe to NLP's finalized response for speaking
            bus = self.bus
            if bus:
                bus.subscribe("nlp_response_ready", self.handle_text_ready)
            return True
        except FileNotFoundError:
            logger.error(f"Piper TTS executable '{self.executable_path}' is missing.")
            return False

    async def handle_text_ready(self, event: AuraEvent):
        text = event.payload.get("text", "")
        if not text:
            return

        fm = self.file_manager
        if fm is None:
            logger.error("AudioFileManager not initialized — cannot synthesize.")
            return

        # Generate a unique audio file path for this response
        output_filepath = fm.generate()
        
        cmd = [
            self.executable_path,
            "--model", self.model_path,
            "--output_file", output_filepath
        ]

        logger.debug(f"Piper TTS Synthesis Initiated for: '{text[:30]}...'")
        
        try:
            # We use asyncio.create_subprocess_exec to avoid blocking the EventBus
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Send text and wait for the process to finish
            await process.communicate(input=text.encode('utf-8'))
            
            if process.returncode == 0:
                logger.info(f"Synthesized speech successfully output to: {output_filepath}")
                # Emit an event notifying the system that audio is ready to be played/logged
                bus = self.bus
                if bus:
                    await bus.publish(AuraEvent(
                        type="audio_ready",
                        payload={"file_path": output_filepath},
                        source=self.module_name
                    ))
            else:
                logger.error(f"Piper core process returned failure code: {process.returncode}")
                
        except Exception as e:
            logger.error(f"System failure during async TTS synthesis: {e}")
