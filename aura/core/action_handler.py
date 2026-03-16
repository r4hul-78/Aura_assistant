import os
import json
import logging
import random
import threading
import subprocess
import time
from datetime import datetime, timedelta

try:
    from playsound import playsound  # pyre-ignore[21]
except ImportError:
    playsound = None

from .memory import MemoryManager  # pyre-ignore[21]

logger = logging.getLogger(__name__)

class ActionHandler:
    """
    Central controller that processes parsed intents from NLP and executes side-effects like:
    Greetings, Tasks, System Apps, Reminders, and Alarms.
    """

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.reminders_file = "reminders.json"
        
        # App mapping optimized for Windows OS
        self.app_map = {
            "browser": "start chrome" if os.name == 'nt' else "chrome",
            "chrome": "start chrome" if os.name == 'nt' else "chrome",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "calc": "calc.exe",
            "terminal": "start cmd" if os.name == 'nt' else "cmd",
            "cmd": "start cmd" if os.name == 'nt' else "cmd",
            "explorer": "explorer.exe",
            "files": "explorer.exe"
        }

        self.greetings_in = ["hello", "hi", "hey", "greetings", "good morning", "good evening", "good afternoon", "wake up"]
        self.greetings_out = [
            "Hello {name}, how can I help you today?",
            "Hi {name}! What's on your mind?",
            "Greetings, {name}. I'm ready for your commands.",
            "Hey {name}! How are you doing?",
            "I'm here, {name}. What do we need to do?",
            "Always a pleasure, {name}. What's the plan for today?"
        ]

        self._ensure_reminders_file()

    def process_input(self, text: str, doc) -> str:
        """Single source of truth for handling parsed intents."""
        lower_text = text.lower().strip()

        # 1. GREETING INTENT
        is_greeting = any(greet in lower_text for greet in self.greetings_in)
        if is_greeting and len(doc) <= 5:
            user_name = self.memory.get_user_name()
            return random.choice(self.greetings_out).format(name=user_name)

        # 2. OPEN APP INTENT
        if lower_text.startswith("open ") or lower_text.startswith("launch "):
            app_request = lower_text.replace("open ", "").replace("launch ", "").strip()
            return self.open_app(app_request)

        # 3. ALARM INTENT
        if "set alarm" in lower_text or "set an alarm" in lower_text:
            return self.handle_set_alarm(lower_text)

        # 4. READ REMINDERS/TASKS INTENT
        read_intents = ["what do i have to do", "read my tasks", "what are my tasks", "tell me my tasks", "read tasks", "check reminders", "what are my reminders"]
        if any(phrase in lower_text for phrase in read_intents):
            return self.check_reminders()

        # 5. SAVE REMINDER/TASK INTENT
        save_intents = ["remember to", "remind me to", "remember that", "remind me that", "new task", "save task", "task"]
        if any(phrase in lower_text for phrase in save_intents) or "remember" in lower_text or "remind" in lower_text:
            task_desc = self._extract_task_from_doc(doc, lower_text)
            if task_desc:
                self.save_reminder(task_desc)
                return f"Got it. I have saved '{task_desc}' to your reminders list."
            else:
                return "I understood you want to save a reminder, but I couldn't catch the details. Could you repeat?"

        # Fallback — prefixed so InteractionEngine can enhance it
        return "[FALLBACK]I heard you, but I'm not sure how to process that command yet."

    def _extract_task_from_doc(self, doc, lower_text: str) -> str:
        """Heuristic to extract the task description using spaCy's dependency parser."""
        tokens = [token.text for token in doc]
        
        prefixes_to_strip = ["remind me to ", "remind me that ", "remember to ", "remember that ", "new task ", "save task "]
        for prefix in prefixes_to_strip:
            if prefix in lower_text:
                extracted = lower_text.split(prefix, 1)[-1].strip()
                if extracted:
                    return extracted

        for token in doc:
            if token.lemma_ in ["remind", "remember", "save", "add"] and token.pos_ == "VERB":
                for child in token.children:
                    if child.dep_ in ["xcomp", "ccomp", "dobj"]:
                        return " ".join([t.text for t in child.subtree]).strip()
                        
        words = lower_text.split()
        if len(words) > 1 and words[0].lower() in ["remember", "remind", "save"]:
            return " ".join([w for i, w in enumerate(words) if i > 0]).strip()
            
        if len(tokens) > 2:
            return doc.text.strip()
            
        return ""

    # --- APP OPENER ---

    def open_app(self, app_name: str) -> str:
        """Attempts to open a system application optimized for Windows."""
        # Find exact or partial match
        cmd_to_run: str = ""
        for key, cmd in self.app_map.items():
            if key in app_name:
                cmd_to_run = cmd
                break
                
        if not cmd_to_run:
            # Signal the InteractionEngine that this app is unmapped
            return f"[UNKNOWN_APP]{app_name}"

        try:
            # Use shell=True to support 'start' command in Windows
            subprocess.Popen(cmd_to_run, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Launched application: {cmd_to_run}")
            return f"Opening {app_name} now."
        except Exception as e:
            logger.error(f"Failed to open application {app_name}: {e}")
            return f"I encountered an error while trying to open {app_name}."

    # --- REMINDERS LOGIC ---

    def _ensure_reminders_file(self):
        if not os.path.exists(self.reminders_file):
            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                json.dump({"reminders": []}, f)

    def save_reminder(self, task_desc: str):
        try:
            with open(self.reminders_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data.setdefault("reminders", []).append({
                "task": task_desc,
                "timestamp": datetime.now().isoformat()
            })
            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving reminder: {e}")

    def check_reminders(self) -> str:
        try:
            with open(self.reminders_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            reminders = data.get("reminders", [])
            
            if not reminders:
                return "You currently have no pending reminders."
            else:
                task_list = ", ".join([r["task"] for r in reminders])
                return f"You have {len(reminders)} reminders: {task_list}"
        except Exception as e:
            logger.error(f"Error reading reminders: {e}")
            return "I couldn't access your reminders list right now."

    def clear_reminders(self):
        with open(self.reminders_file, 'w', encoding='utf-8') as f:
            json.dump({"reminders": []}, f)

    # --- ALARMS LOGIC ---

    def handle_set_alarm(self, text: str) -> str:
        """Parse time string from text and spawn the alarm thread."""
        # Extremely basic heuristic to extract time string (e.g. 7 PM, 14:30)
        words = text.split()
        time_str = ""
        
        # Look for numbers or AM/PM
        for i, word in enumerate(words):
            if ":" in word or word.isdigit() or word.lower() in ["am", "pm"]:
                # Try to capture the phrase e.g. "7 pm" or "14:30"
                if i > 0 and words[i-1].isdigit() and word.lower() in ["am", "pm"]:  # pyre-ignore[28]
                    time_str = f"{words[i-1]} {word}"  # pyre-ignore[28]
                else:
                    time_str = word
                    if i + 1 < len(words) and words[i+1].lower() in ["am", "pm"]:  # pyre-ignore[28]
                        time_str += f" {words[i+1]}"  # pyre-ignore[28]
                break
                
        if not time_str:
            return "I couldn't understand the time for the alarm. Please specify a time like 7 PM."
            
        # Spawn thread
        t = threading.Thread(target=self._alarm_worker, args=(time_str,), daemon=True)
        t.start()
        return f"Alarm set for {time_str}."

    def _alarm_worker(self, time_str: str):
        """Background worker that continuously poll current time."""
        logger.info(f"Alarm thread started for target: {time_str}")
        
        target_time = None
        time_str = time_str.lower()
        
        try:
            # Try parsing different common formats
            today = datetime.now()
            if "am" in time_str or "pm" in time_str:
                if ":" in time_str:
                    parsed = datetime.strptime(time_str, "%I:%M %p")  # pyre-ignore[28]
                else:
                    parsed = datetime.strptime(time_str, "%I %p")  # pyre-ignore[28]
            else:
                if ":" in time_str:
                    parsed = datetime.strptime(time_str, "%H:%M")  # pyre-ignore[28]
                else:
                    parsed = datetime.strptime(time_str, "%H")  # pyre-ignore[28]
                    
            target_time = today.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
            
            # If the time has already passed today, set it for tomorrow
            if target_time < today:
                target_time += timedelta(days=1)
                
        except ValueError as e:
            logger.error(f"Failed to parse alarm time '{time_str}': {e}")
            return

        logger.info(f"Normalized target alarm time: {target_time}")

        # Poll loop
        while True:
            now = datetime.now()
            if now >= target_time:
                logger.info("ALARM TRIGGERED!")
                self._play_alarm_sound()
                break
            # Sleep to prevent high CPU usage
            time.sleep(10)

    def _play_alarm_sound(self):
        """Plays a local wav file."""
        sound_path = "alarm.wav"  # Ensure this exists or use system beep
        if playsound and os.path.exists(sound_path):
            try:
                playsound(sound_path)
            except Exception as e:
                logger.error(f"Failed to play sound: {e}")
        else:
            # Fallback beep
            if os.name == 'nt':
                import winsound
                winsound.Beep(1000, 2000)  # pyre-ignore[16]
            logger.info("BEEP BEEP BEEP ALARM!")
