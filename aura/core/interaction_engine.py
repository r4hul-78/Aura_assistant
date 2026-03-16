"""
InteractionEngine — Pure-logic Social & Interaction Layer for Aura.

Sits between the NLP intent parser and TTS. Responsible for:
- Time-aware greetings
- Session state tracking (rapid-fire shorthand)
- Response variety via randomized selection
- Gratitude detection and warm replies
- Clarification prompts for empty/unclear input
- Graceful refusal for unmapped apps
- Personalization via user name from memory

No EventBus dependency — fully testable in isolation.
"""

import json
import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from .memory import MemoryManager  # pyre-ignore[21]

logger = logging.getLogger(__name__)

# Signal prefixes emitted by ActionHandler for the engine to intercept
_UNKNOWN_APP_PREFIX = "[UNKNOWN_APP]"
_FALLBACK_PREFIX = "[FALLBACK]"

# Keywords that indicate gratitude
_GRATITUDE_KEYWORDS = [
    "thanks", "thank you", "thank u", "thx",
    "appreciate", "grateful", "cheers", "glad"
]

# Rapid-session threshold in seconds (15 minutes)
_RAPID_SESSION_SECONDS = 900


class InteractionEngine:
    """
    Lightweight conversational polish engine.
    Enhances raw ActionHandler responses with social intelligence.
    """

    def __init__(
        self,
        memory: MemoryManager,
        responses_path: str = "responses.json"
    ):
        self.memory = memory
        self.responses: Dict[str, Any] = {}
        self._load_responses(responses_path)

        # Session state — ephemeral, not persisted to disk
        self._session: Dict[str, Any] = {
            "last_interaction_time": None,  # datetime of last interaction
            "interaction_count": 0,         # count in current burst
            "greeted": False                # whether startup greeting was given
        }

        # Track last picked index per category to avoid immediate repeats
        self._last_pick: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _load_responses(self, path: str) -> None:
        """Load the responses.json data file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.responses = json.load(f)
            logger.info(f"Loaded response variations from '{path}'")
        except FileNotFoundError:
            logger.warning(
                f"Response file '{path}' not found. "
                "Using empty response bank — Aura will pass through raw responses."
            )
        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON in '{path}': {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, intent_text: str, raw_user_text: str) -> str:
        """
        Main entry point. Takes the ActionHandler's response and the
        original user text, returns the final polished string for TTS.

        Args:
            intent_text:   The response string from ActionHandler.process_input()
            raw_user_text: The original transcribed user speech.

        Returns:
            The final response string to be spoken by Piper TTS.
        """
        now = datetime.now()

        # 1. Empty / unclear input → clarification prompt
        if not raw_user_text or not raw_user_text.strip():
            return self._pick("clarification_prompts")

        # 2. Gratitude detection (takes priority over intent response)
        if self._detect_gratitude(raw_user_text):
            reply = self._pick("gratitude_replies")
            user_name = self.memory.get_user_name()
            self._update_session(now)
            return reply.format(name=user_name)

        # 3. Intercept signal prefixes from ActionHandler
        if intent_text.startswith(_UNKNOWN_APP_PREFIX):
            app_name = intent_text.removeprefix(_UNKNOWN_APP_PREFIX)
            self._update_session(now)
            return self.enhance_app_refusal(app_name)

        if intent_text.startswith(_FALLBACK_PREFIX):
            self._update_session(now)
            return self._pick("fallback")

        # 4. Rapid-session shorthand — after several quick exchanges,
        #    prepend a shorthand cue so Aura sounds conversational.
        response = intent_text
        if self._is_rapid_session(now) and self._session["interaction_count"] >= 2:
            if not self._looks_like_greeting(intent_text):
                shorthand = self._pick("shorthand")
                response = f"{shorthand} {intent_text}"

        self._update_session(now)
        return response

    def get_startup_greeting(self) -> str:
        """
        Generate a time-aware greeting for when Aura first starts up.
        Only returns a greeting once per session.
        """
        if self._session["greeted"]:
            return ""

        self._session["greeted"] = True
        period = self._get_time_period()
        user_name = self.memory.get_user_name()

        # Try time-specific greetings first, then welcome_back
        time_greetings = self.responses.get("time_greetings", {})
        period_list = time_greetings.get(period, [])

        if period_list:
            greeting = random.choice(period_list)
        else:
            # Fallback if responses.json is missing
            greeting = f"Hello, {{name}}. How can I help you?"

        return greeting.format(name=user_name)

    def enhance_app_refusal(self, app_name: str) -> str:
        """Generate a polite refusal for an unmapped application."""
        templates = self.responses.get("unknown_app", [])
        if templates:
            template = random.choice(templates)
            return template.format(app=app_name)
        return f"I don't have {app_name} mapped yet. I can add it if you'd like."

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pick(self, category: str) -> str:
        """
        Pick a random response from the given category,
        avoiding the immediately previous selection.
        """
        options = self.responses.get(category, [])
        if not options:
            return ""

        if len(options) == 1:
            return options[0]

        last_idx = self._last_pick.get(category, -1)

        # Pick a different index than last time
        idx = random.randrange(len(options))
        attempts = 0
        while idx == last_idx and attempts < 5:
            idx = random.randrange(len(options))
            attempts += 1

        self._last_pick[category] = idx
        return options[idx]

    def _is_rapid_session(self, now: datetime) -> bool:
        """True if the last interaction was less than 2 minutes ago."""
        last = self._session["last_interaction_time"]
        if last is None:
            return False
        delta = (now - last).total_seconds()
        return delta < _RAPID_SESSION_SECONDS

    def _update_session(self, now: datetime) -> None:
        """Update session timing after each interaction."""
        if self._is_rapid_session(now):
            self._session["interaction_count"] += 1
        else:
            self._session["interaction_count"] = 1
        self._session["last_interaction_time"] = now

    @staticmethod
    def _detect_gratitude(text: str) -> bool:
        """Check if the user's text contains a gratitude expression."""
        lower = text.lower()
        return any(kw in lower for kw in _GRATITUDE_KEYWORDS)

    @staticmethod
    def _get_time_period() -> str:
        """Determine the current time-of-day period."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"

    @staticmethod
    def _looks_like_greeting(text: str) -> bool:
        """Quick heuristic check if a response is a greeting."""
        greeting_starts = [
            "hello", "hi ", "hi!", "hey", "greetings",
            "good morning", "good afternoon", "good evening",
            "welcome"
        ]
        lower = text.lower()
        return any(lower.startswith(g) for g in greeting_starts)
