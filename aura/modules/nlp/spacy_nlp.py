import spacy  # pyre-ignore[21]
import logging
from typing import Any, Optional
from aura.core.module_base import BaseModule  # pyre-ignore[21]
from aura.core.events import EventBus, AuraEvent  # pyre-ignore[21]
from aura.core.memory import MemoryManager  # pyre-ignore[21]
from aura.core.action_handler import ActionHandler  # pyre-ignore[21]

logger = logging.getLogger(__name__)

class SpacyNLPModule(BaseModule):
    """
    Natural Language Processing capability powered by spaCy.
    Handles entity extraction, tokenization, and linguistic analysis asynchronously.
    """

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self.nlp: Optional[Any] = None  # spacy.Language type, resolved at runtime
        self.bus: Optional[EventBus] = None
        self.memory = MemoryManager()
        self.action_handler = ActionHandler(self.memory)

    @property
    def module_name(self) -> str:
        return "nlp"

    async def initialize(self, bus: EventBus) -> bool:
        self.bus = bus
        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Successfully loaded spaCy NLP model: {self.model_name}")
            
            # Subscribe to whenever new text comes into the system from Vosk
            bus = self.bus
            if bus:
                bus.subscribe("user_input_received", self.handle_user_input)
            return True
            
        except OSError:
            logger.error(f"spaCy model '{self.model_name}' could not be located on disk.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading spaCy model: {e}")
            return False

    async def handle_user_input(self, event: AuraEvent):
        """Callback triggered when the orchestrator fires a 'user_input_received' event."""
        text = event.payload.get("text", "")
        if not text:
            return

        nlp = self.nlp
        if not nlp:
            logger.error("spaCy model is not initialized/loaded.")
            return

        doc = nlp(text)

        response_text = self.action_handler.process_input(text, doc)
        
        # Keep track of interaction via memory manager
        self.memory.add_interaction(text, response_text)

        logger.info(f"Action Handler determined response: '{response_text}'")

        # Publish the response back to the Event Bus for TTS
        bus = self.bus
        if bus:
            await bus.publish(AuraEvent(
                type="nlp_response_ready",
                payload={"text": response_text},
                source=self.module_name
            ))
