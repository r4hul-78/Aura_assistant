"""
InteractionModule — EventBus adapter for the InteractionEngine.

Subscribes to 'intent_response_ready' events from SpacyNLP,
runs them through the InteractionEngine for social polish,
then publishes the final 'nlp_response_ready' event for PiperTTS.
"""

import logging
from typing import Optional
from aura.core.module_base import BaseModule  # pyre-ignore[21]
from aura.core.events import EventBus, AuraEvent  # pyre-ignore[21]
from aura.core.memory import MemoryManager  # pyre-ignore[21]
from aura.core.interaction_engine import InteractionEngine  # pyre-ignore[21]

logger = logging.getLogger(__name__)


class InteractionModule(BaseModule):
    """
    Thin EventBus adapter that wires the InteractionEngine
    into the Aura event-driven pipeline.

    Pipeline position:
        SpacyNLP --[intent_response_ready]--> InteractionModule
        InteractionModule --[nlp_response_ready]--> PiperTTS
    """

    def __init__(
        self,
        memory_file: str = "memory.json",
        responses_path: str = "responses.json"
    ):
        self.bus: Optional[EventBus] = None
        self._memory_file = memory_file
        self._responses_path = responses_path
        self.engine: Optional[InteractionEngine] = None

    @property
    def module_name(self) -> str:
        return "interaction"

    async def initialize(self, bus: EventBus) -> bool:
        self.bus = bus

        try:
            # Create a dedicated MemoryManager instance for the engine
            memory = MemoryManager(self._memory_file)
            self.engine = InteractionEngine(memory, self._responses_path)

            # Subscribe to the renamed NLP output event
            bus.subscribe("intent_response_ready", self._handle_intent_response)

            logger.info("InteractionModule initialized — subscribed to 'intent_response_ready'.")

            # Speak the startup greeting via TTS
            engine = self.engine
            greeting = engine.get_startup_greeting() if engine else ""
            if greeting:
                logger.info(f"Startup greeting: '{greeting}'")
                await bus.publish(AuraEvent(
                    type="nlp_response_ready",
                    payload={"text": greeting},
                    source=self.module_name
                ))

            return True

        except Exception as e:
            logger.error(f"Failed to initialize InteractionModule: {e}")
            return False

    async def _handle_intent_response(self, event: AuraEvent) -> None:
        """
        Callback for 'intent_response_ready' events.
        Processes the raw intent response through the InteractionEngine
        and publishes the polished result as 'nlp_response_ready'.
        """
        intent_text = event.payload.get("text", "")
        raw_user_text = event.payload.get("raw_text", "")

        engine = self.engine
        if not engine:
            logger.error("InteractionEngine not initialized.")
            return

        # Run the text through the social polish engine
        final_response = engine.process(intent_text, raw_user_text)

        logger.info(f"Interaction Engine output: '{final_response}'")

        # Forward the polished response to TTS
        bus = self.bus
        if bus:
            await bus.publish(AuraEvent(
                type="nlp_response_ready",
                payload={"text": final_response},
                source=self.module_name
            ))
