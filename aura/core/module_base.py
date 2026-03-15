from abc import ABC, abstractmethod
from .events import EventBus  # pyre-ignore[21]


class BaseModule(ABC):
    """
    Base abstraction interface for all Aura framework capabilities.
    Any new plugin (TTS, NLP, Vision, LLM) should inherit from this class.
    """

    @property
    @abstractmethod
    def module_name(self) -> str:
        """Return the unique identifier/name for this module."""
        ...  # pragma: no cover

    @abstractmethod
    async def initialize(self, bus: EventBus) -> bool:
        """
        Asynchronous initialization routines such as event subscription, memory allocation,
        loading models, or authenticating external API connections.
        return: True if successful, False otherwise.
        """
        ...  # pragma: no cover
