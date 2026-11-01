"""Zeus - a hands-free voice assistant.

Say the wake word (default: "july"), then speak your question. Zeus transcribes
it locally with Whisper, asks an OpenAI chat model, and reads the answer aloud.

Configuration comes from environment variables (or a local `.env` file):
    OPENAI_API_KEY   required - never commit this
    OPENAI_MODEL     optional - chat model to use (default: gpt-4o-mini)
    ZEUS_WAKE_WORD   optional - wake word (default: july)
"""

import os
import subprocess
import sys
import tempfile
import time
import warnings

import speech_recognition as sr
import whisper
from openai import OpenAI

try:  # optional: load a local .env file if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

WAKE_WORD = os.getenv("ZEUS_WAKE_WORD", "july").lower()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = (
    "You are Zeus, a helpful voice assistant. Answer in one to three short, "
    "conversational sentences because your reply will be spoken aloud."
)
MAX_HISTORY_TURNS = 6  # keep the last few exchanges so follow-up questions work

if not os.getenv("OPENAI_API_KEY"):
    sys.exit(
        "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key, "
        "or export it in your shell."
    )

client = OpenAI()  # reads OPENAI_API_KEY from the environment

warnings.filterwarnings("ignore", category=UserWarning, module="whisper.transcribe")
# The tiny model is fast enough to run on every utterance for wake-word spotting;
# the base model is more accurate for the actual prompt.
tiny_model = whisper.load_model("tiny")
base_model = whisper.load_model("base")

recognizer = sr.Recognizer()
source = sr.Microphone()
listening_for_wake_word = True
history = []

if sys.platform != "darwin":
    import pyttsx3

    engine = pyttsx3.init()


def speak(text):
    print(f"Zeus: {text}")
    if sys.platform == "darwin":
        # Pass the text as an argument (no shell) so nothing in the reply can be
        # interpreted as a command.
        subprocess.run(["say", text], check=False)
    else:
        engine.say(text)
        engine.runAndWait()


def transcribe(audio, model):
    """Write the captured audio to a temp WAV file and run Whisper on it."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio.get_wav_data())
        path = f.name
    try:
        return model.transcribe(path, fp16=False)["text"].strip()
    finally:
        os.remove(path)


def listen_for_wake_word(audio):
    global listening_for_wake_word
    text = transcribe(audio, tiny_model).lower()
    if WAKE_WORD in text:
        print("Wake word detected - speak your prompt.")
        speak("Listening")
        listening_for_wake_word = False


def ask_model(prompt_text):
    history.append({"role": "user", "content": prompt_text})
    del history[: -MAX_HISTORY_TURNS * 2]
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *history],
        max_completion_tokens=300,
    )
    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})
    return reply


def prompt_gpt(audio):
    global listening_for_wake_word
    try:
        prompt_text = transcribe(audio, base_model)
        if not prompt_text:
            speak("I didn't catch that. Please say the wake word and try again.")
            return
        print(f"You: {prompt_text}")
        speak(ask_model(prompt_text))
    except Exception as e:  # keep the assistant alive on network/API errors
        print("Prompt error:", e)
        speak("Sorry, something went wrong.")
    finally:
        listening_for_wake_word = True
        print(f"\nSay '{WAKE_WORD}' to wake me up.\n")


def callback(_recognizer, audio):
    if listening_for_wake_word:
        listen_for_wake_word(audio)
    else:
        prompt_gpt(audio)


def start_listening():
    with source as s:
        recognizer.adjust_for_ambient_noise(s, duration=2)
    print(f"\nSay '{WAKE_WORD}' to wake me up.\n")
    stop = recognizer.listen_in_background(source, callback)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop(wait_for_stop=False)
        print("\nGoodbye.")


if __name__ == "__main__":
    start_listening()
