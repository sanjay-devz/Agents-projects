# Study Buddy

A Streamlit study helper that sends course notes to a **local Ollama model** and creates an explanation, an example, and a five-question multiple-choice quiz. The app does not use a cloud AI API or require an API key.

## Requirements

- Python 3.10 or newer
- Ollama installed and running locally
- A model downloaded in Ollama (the default is `gemma2:latest`)

Check installed models with:

```bash
ollama list
```

If needed, download the default model and start the Ollama server:

```bash
ollama pull gemma2:latest
ollama serve
```

If Ollama is already running as a background service, you do not need to run `ollama serve` again.

## Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local address printed by Streamlit (usually `http://localhost:8501`), enter a subject, topic, and notes, then generate the study guide. Answer all five questions and submit to see your score and explanations.

## Local configuration

The defaults connect to Ollama at `http://localhost:11434` and use `gemma2:latest`. Override them with environment variables if needed:

```dotenv
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=gemma2:latest
```

For a model already installed under another name, set `OLLAMA_MODEL` to the exact name shown by `ollama list`, such as `qwen3:4b`. `OLLAMA_CHAT_URL` can override the full chat endpoint if your local Ollama server uses a custom address. No API key is used or sent.

If the app cannot connect, start Ollama and confirm `ollama list` works. If the selected model is missing, pull it with `ollama pull <model-name>`.
