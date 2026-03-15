import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MemoryManager:
    """Handles long-term memory for Aura using a simple JSON file."""
    
    def __init__(self, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.memory: Dict[str, Any] = {
            "user_name": "Iraiva",  # Default user name
            "interaction_history": [],
            "tasks": []
        }
        self.load_memory()

    def load_memory(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.memory.update(data)
                # Ensure tasks list exists even for older memory files
                if "tasks" not in self.memory:
                    self.memory["tasks"] = []
                logger.info(f"Loaded memory from {self.memory_file}")
            except Exception as e:
                logger.error(f"Failed to load memory: {e}")
        else:
            self.save_memory()
            logger.info(f"Created new memory file at {self.memory_file}")

    def save_memory(self):
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")

    def get_user_name(self) -> str:
        return str(self.memory.get("user_name", "Boss"))

    def set_user_name(self, name: str):
        self.memory["user_name"] = name
        self.save_memory()

    def add_interaction(self, user_input: str, bot_response: str):
        history = self.memory.get("interaction_history", [])
        history.append({
            "user": user_input,
            "aura": bot_response
        })
        # Keep only the last 5 interactions
        if len(history) > 5:
            history = history[-5:]
        self.memory["interaction_history"] = history
        self.save_memory()

    def add_task(self, task_desc: str):
        tasks = self.memory.setdefault("tasks", [])
        tasks.append(task_desc)
        self.save_memory()

    def get_tasks(self) -> List[str]:
        return list(self.memory.get("tasks", []))

    def clear_tasks(self):
        self.memory["tasks"] = []
        self.save_memory()
