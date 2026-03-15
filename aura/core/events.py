import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Coroutine, Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class AuraEvent:
    """A standardized event payload passed between loosely coupled modules."""
    type: str                     # e.g., "user_input_received", "audio_ready"
    payload: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None  # Which module generated the event (e.g., "nlp")


class EventBus:
    """
    Central Asynchronous Message Broker.
    Allows modules to seamlessly publish and subscribe to specific event types
    without knowing about each other's existence.
    """
    def __init__(self):
        # A dictionary mapping event_type strings to a list of asynchronous callbacks
        self._subscribers: Dict[str, List[Callable[[AuraEvent], Coroutine[Any, Any, None]]]] = {}

    def subscribe(self, event_type: str, callback: Callable[[AuraEvent], Coroutine[Any, Any, None]]):
        """Register an async callback function to handle an event_type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        logger.debug(f"Subscribed to Event[{event_type}] with {callback.__name__}")

    async def publish(self, event: AuraEvent):
        """
        Asynchronously dispatch an event to all interested subscribers.
        We use asyncio.gather to allow multiple subscribers to handle the event concurrently.
        """
        if event.type in self._subscribers:
            callbacks = self._subscribers[event.type]
            logger.info(f"Bus routing Event[{event.type}] from [{event.source}] to {len(callbacks)} subscriber(s).")
            
            # Execute all subscriber coroutines concurrently
            tasks = [cb(event) for cb in callbacks]
            # Use return_exceptions so a failing module doesn't kill parallel execution
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result, cb in zip(results, callbacks):
                if isinstance(result, Exception):
                    logger.error(f"Error in EventBus subscriber {cb.__name__} for event '{event.type}': {result}")
        else:
            logger.debug(f"EventBus dropped Event[{event.type}] from [{event.source}] (No subscribers).")
