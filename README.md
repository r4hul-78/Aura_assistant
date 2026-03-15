# Aura

Aura is a modular AI assistant designed with an extensible architecture. It is built to support varying plug-and-play modules for Natural Language Processing (NLP), Text-to-Speech (TTS), and other generative or functional capabilities.

## Architecture Structure

- `aura/core/`: Foundational framework handling base definitions, common configuration, and module registration.
- `aura/modules/`: Individual plug-and-play capabilities (e.g., `nlp` using spaCy, `tts` using Piper, `asr` using Vosk).
- `tests/`: Isolated sandbox tests for verifying individual modules (e.g., NLP logic).
- `main.py`: Entry-point script wiring up the modules and testing the assistant interaction pipeline.

## Setup Instructions

1. **Set up a virtual environment**
   ```bash
   python -m venv .venv
   
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   source .venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install the spaCy Model**
   ```bash
   python -m spacy download en_core_web_sm
   ```

4. **Piper TTS Setup**
   Because TTS voice models are heavily large, they are not included in this repository.
   - Download the Piper executable and required ONNX models from the [Piper Repository](https://github.com/rhasspy/piper).
   - Create a `piper/` folder in the root directory and place `piper.exe` and your `.onnx` models there. 
   - Update the path in `main.py` if necessary.

5. **Vosk ASR Setup**
   Because offline transcription models are large, they are not included directly here.
   - Download a lightweight English model (e.g., `vosk-model-small-en-in-0.4`) from [Vosk Models](https://alphacephei.com/vosk/models).
   - Extract the folder into the project root directory.
   - Ensure the path matches `vosk-model-small-en-in-0.4` as referenced in `main.py`.

## Example Usage

Run the primary framework to begin the conversational loop. Ensure your microphone is accessible.

```bash
run.bat
```
Alternatively:
```bash
python main.py
```
