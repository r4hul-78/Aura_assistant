"""
Tests for the InteractionEngine — standalone, no EventBus/spaCy/Vosk required.

Validates:
1. Time-aware greetings
2. Session tracking (rapid-fire shorthand)
3. Gratitude detection
4. Clarification prompts for empty input
5. Unknown app refusal
6. Response variety (no-repeat selection)
7. Fallback signal interception
"""

import os
import sys

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta  # noqa: E402
from aura.core.memory import MemoryManager  # pyre-ignore[21]
from aura.core.interaction_engine import InteractionEngine  # pyre-ignore[21]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COUNTS = {"passed": 0, "failed": 0}


def check(label: str, condition: bool, detail: str = ""):
    """Simple assertion with formatted output."""
    status = "PASS" if condition else "FAIL"
    if condition:
        _COUNTS["passed"] += 1
    else:
        _COUNTS["failed"] += 1
    extra = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{extra}")


# ---------------------------------------------------------------------------
# Test suite
# ---------------------------------------------------------------------------

def test_startup_greeting(engine: InteractionEngine):
    """Startup greeting should be time-aware and include the user name."""
    print("\n--- Test: Startup Greeting ---")

    greeting = engine.get_startup_greeting()
    check("Greeting is non-empty", bool(greeting), greeting)
    check("Greeting contains user name", "TestUser" in greeting, greeting)

    # Second call should return empty (already greeted)
    second = engine.get_startup_greeting()
    check("Second greeting is empty", second == "", repr(second))


def test_gratitude_detection(engine: InteractionEngine):
    """Gratitude phrases should trigger warm replies."""
    print("\n--- Test: Gratitude Detection ---")

    phrases = ["thanks", "Thank you so much", "I appreciate that", "thx"]
    for phrase in phrases:
        result = engine.process("some response", phrase)
        check(f"'{phrase}' triggers gratitude reply", bool(result), result)
        # Should NOT be the raw intent text
        check("  reply is not passthrough", result != "some response", result)


def test_clarification_on_empty_input(engine: InteractionEngine):
    """Empty or whitespace-only input should return a clarification prompt."""
    print("\n--- Test: Clarification Prompts ---")

    for raw in ["", "   ", None]:
        result = engine.process("anything", raw or "")
        check(f"Empty input '{repr(raw)}' → clarification", bool(result), result)


def test_unknown_app_signal(engine: InteractionEngine):
    """[UNKNOWN_APP] prefix should be intercepted and enhanced."""
    print("\n--- Test: Unknown App Refusal ---")

    result = engine.process("[UNKNOWN_APP]spotify", "open spotify")
    check("Contains 'spotify'", "spotify" in result.lower(), result)
    check("Does NOT contain prefix", "[UNKNOWN_APP]" not in result, result)


def test_fallback_signal(engine: InteractionEngine):
    """[FALLBACK] prefix should be intercepted and a varied fallback returned."""
    print("\n--- Test: Fallback Signal ---")

    result = engine.process("[FALLBACK]raw fallback text", "some gibberish")
    check("Is non-empty", bool(result), result)
    check("Does NOT contain prefix", "[FALLBACK]" not in result, result)


def test_response_variety(engine: InteractionEngine):
    """Repeated calls to _pick should yield variety."""
    print("\n--- Test: Response Variety ---")

    results = set()
    for _ in range(15):
        r = engine._pick("acknowledgments")
        results.add(r)

    check("At least 2 distinct acknowledgments from 15 picks", len(results) >= 2,
          f"got {len(results)} distinct: {results}")


def test_rapid_session_shorthand(engine: InteractionEngine):
    """After rapid interactions, responses should gain a shorthand prefix."""
    print("\n--- Test: Rapid Session Shorthand ---")

    # Simulate 3 rapid interactions by manipulating session state
    now = datetime.now()
    engine._session["last_interaction_time"] = now - timedelta(seconds=30)
    engine._session["interaction_count"] = 3

    result = engine.process("Opening calculator now.", "open calc")
    # The response MIGHT have a shorthand prefix if the engine considers it rapid
    # (interaction_count >= 2 and within 120s)
    check("Rapid session produces non-empty response", bool(result), result)
    print(f"    Response: '{result}'")


def test_normal_passthrough(engine: InteractionEngine):
    """Normal intent responses should pass through unchanged (first interaction)."""
    print("\n--- Test: Normal Passthrough ---")

    # Reset session to first interaction
    engine._session["last_interaction_time"] = None
    engine._session["interaction_count"] = 0

    intent = "Opening calculator now."
    result = engine.process(intent, "open calc")
    check("Response matches intent text", result == intent, result)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 55)
    print("   InteractionEngine Test Suite")
    print("=" * 55)

    # Set up isolated memory
    mem = MemoryManager("test_memory.json")
    mem.set_user_name("TestUser")

    # Create engine with the project's responses.json
    engine = InteractionEngine(mem, "responses.json")

    test_startup_greeting(engine)
    test_gratitude_detection(engine)
    test_clarification_on_empty_input(engine)
    test_unknown_app_signal(engine)
    test_fallback_signal(engine)
    test_response_variety(engine)
    test_rapid_session_shorthand(engine)
    test_normal_passthrough(engine)

    print("\n" + "=" * 55)
    print(f"   Results: {_COUNTS['passed']} passed, {_COUNTS['failed']} failed")
    print("=" * 55)

    if _COUNTS["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
