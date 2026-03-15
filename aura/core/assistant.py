import logging
from typing import Dict, Optional
from .module_base import BaseModule  # pyre-ignore[21]
from .events import EventBus  # pyre-ignore[21]

logger = logging.getLogger(__name__)


class AuraAssistant:
    """Core Event-Driven orchestrator for the Aura AI assistant."""

    def __init__(self):
        self.modules: Dict[str, BaseModule] = {}
        self.bus = EventBus()
        logger.info("Initializing Aura Core Event Broker...")

    async def register_module(self, module: BaseModule):
        """Register a new modular capability and allow it to subscribe to the EventBus."""
        try:
            success = await module.initialize(self.bus)
            if success:
                self.modules[module.module_name] = module
                logger.info(f"Successfully registered module: '{module.module_name}'")
            else:
                logger.error(f"Failed during initialization of module: '{module.module_name}'")
        except Exception as e:
            logger.error(f"Error registering module '{module.module_name}': {e}")

    def get_module(self, module_name: str) -> Optional[BaseModule]:
        """Retrieve an initialized module instance by its unique identifier."""
        return self.modules.get(module_name)
