import logging
import sys
import asyncio
from aura.core.assistant import AuraAssistant  # pyre-ignore[21]
from aura.modules.nlp.spacy_nlp import SpacyNLPModule  # pyre-ignore[21]
from aura.modules.tts.piper_tts import PiperTTSModule  # pyre-ignore[21]
from aura.modules.asr.vosk_asr import VoskASRModule  # pyre-ignore[21]
from aura.modules.audio.audio_player import AudioPlayerModule  # pyre-ignore[21]
from aura.core.events import AuraEvent  # pyre-ignore[21]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


async def async_main():
    print("=" * 55)
    print("   Aura — Modular AI Assistant (Event-Driven Mode)   ")
    print("=" * 55)
    print("Press Ctrl+C at any time to shut down.\n")

    # 1. Initialize the Core Framework Orchestrator
    aura = AuraAssistant()

    # 2. Register NLP Module
    nlp_module = SpacyNLPModule(model_name="en_core_web_sm")
    await aura.register_module(nlp_module)

    # 3. Register TTS Module
    tts_module = PiperTTSModule(
        model_path=r"piper\en_US-libritts_r-medium.onnx",
        executable_path=r"piper\piper.exe"
    )
    await aura.register_module(tts_module)

    # 4. Register Audio Player
    audio_player = AudioPlayerModule()
    await aura.register_module(audio_player)

    # 5. Register ASR (Speech-to-Text) Module.
    asr_module = VoskASRModule(
        model_path="vosk-model-small-en-in-0.4",
        enable_mic=True
    )
    await aura.register_module(asr_module)

    print("\n[Aura] All modules loaded. Listening for your voice...\n")

    # 6. Keep the event loop alive until Ctrl+C is pressed.
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n\n[Aura] Shutting down. Goodbye!")


if __name__ == "__main__":
    main()
