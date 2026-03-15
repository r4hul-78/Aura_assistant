import os
import sys
import asyncio
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from aura.core.memory import MemoryManager  # pyre-ignore[21]
from aura.modules.nlp.spacy_nlp import SpacyNLPModule  # pyre-ignore[21]
from aura.core.events import EventBus  # pyre-ignore[21]

async def test_logic():
    print("--- Testing MemoryManager & ActionHandler ---")
    mem = MemoryManager("test_memory.json")
    mem.set_user_name("Rahul")
    mem.clear_tasks()
    
    print("\n--- Testing SpacyNLPModule + ActionHandler Intents ---")
    nlp = SpacyNLPModule()
    
    bus = EventBus()
    initialized = await nlp.initialize(bus)
    if not initialized:
        print("Failed to init NLP.")
        return

    # Override memory & action handler for isolation and clean slate
    nlp.memory = mem
    # Clear reminders for test
    nlp.action_handler.clear_reminders()

    test_phrases = [
        "Hello",
        "Open calc",
        "Set an alarm for 12:00 AM",
        "What do I have to do?",
        "Remind me to call the doctor",
        "What are my tasks?",
        "Save task debug the application code",
        "read my tasks"
    ]
    
    for phrase in test_phrases:
        print(f"\nUser: {phrase}")
        doc = nlp.nlp(phrase)
        response = nlp.action_handler.process_input(phrase, doc)
        print(f"Aura: {response}")

    print("\nAllowing threads/actions a moment...")
    time.sleep(2)

if __name__ == "__main__":
    asyncio.run(test_logic())
