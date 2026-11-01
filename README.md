# Zeus

A hands-free voice assistant: say the wake word, ask a question, hear the answer.

Speech is transcribed **locally** with [Whisper](https://github.com/openai/whisper)
(the `tiny` model listens for the wake word, the `base` model transcribes your prompt),
then sent to an OpenAI chat model. The reply is spoken with `say` on macOS or `pyttsx3`
elsewhere. Zeus keeps the last few exchanges, so follow-up questions work.

## Setup

```bash
python -m venv env && source env/bin/activate
pip install -r requirements.txt     # PyAudio needs portaudio (brew/apt install portaudio19-dev)
cp .env.example .env                 # then put your OpenAI key in .env
python main.py
```

Whisper also needs `ffmpeg` on your PATH.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | — (required) | Your OpenAI API key. Keep it in `.env`, never in code. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat model used for answers. |
| `ZEUS_WAKE_WORD` | `july` | Word that wakes the assistant. |
