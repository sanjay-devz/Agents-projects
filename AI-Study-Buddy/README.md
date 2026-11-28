# StudyMate – AI Study Buddy (Streamlit prototype)

A minimal, hack‑athon‑ready demo that lets a student paste course material, get a concise explanation with an example, answer five AI‑generated multiple‑choice questions, and receive a score with feedback.

## Features (demo‑oriented)
- Pure **Streamlit** UI – no separate backend or database.
- All AI calls happen on the server side using a single model (OpenAI, Gemini, etc.).
- The model is forced to return **JSON**; the app validates that the response contains exactly five questions with four options each.
- Session state keeps the answer key hidden until the quiz is submitted.
- Graceful handling when no API key is configured.

## Project structure
```
StudyMate/
├─ app.py               # Streamlit app (the whole workflow)
├─ requirements.txt     # Python dependencies
├─ .env.example         # Template for credentials
├─ .gitignore           # Ignores env, venv, caches, etc.
└─ README.md            # (this file)
```

## 1️⃣ Add your API key
1. Copy the example file:
   ```bash
   cp .env.example .env
   ```
2. Open **`.env`** in a text editor and replace the placeholder values:
   ```dotenv
   AI_API_KEY=YOUR_API_KEY_HERE          # OpenAI, Gemini, etc.
   # For OpenAI use the default URL below, otherwise change it.
   AI_API_URL=https://api.openai.com/v1/chat/completions
   GENERATION_MODEL=gpt-4o-mini          # or gemini-1.5-pro, etc.
   ```
   - **OpenAI** example: keep the URL as shown and set `GENERATION_MODEL` to `gpt-4o-mini` (or any model you have access to).
   - **Gemini** example: replace `AI_API_URL` with something like:
     ```
     AI_API_URL=https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent
     GENERATION_MODEL=gemini-1.5-pro
     ```
   - Make sure the model name in `GENERATION_MODEL` matches the one in the URL.
3. Save the file. **Never commit `.env`** – it is listed in `.gitignore`.

## 2️⃣ Install dependencies
```bash
# From the project root (StudyMate)
python3 -m venv .venv          # create a virtual environment
source .venv/bin/activate      # Linux / macOS
# .venv\Scripts\activate   # Windows PowerShell
pip install -r requirements.txt
```
The install pulls:
- `streamlit` – UI framework
- `httpx` – async‑ready HTTP client for the LLM
- `python-dotenv` – loads the `.env` file

## 3️⃣ Run the app locally
```bash
streamlit run app.py
```
A browser window will open at `http://localhost:8501`. You’ll see the **StudyMate** title and the input form.

## 4️⃣ Demo workflow (what to show the judges)
1. **Enter a subject and topic** – e.g., *Subject: Physics*, *Topic: Newton's Laws*.
2. **Paste concise course notes** (a short paragraph is enough). The notes are the only knowledge source.
3. Click **“Start study session.”**
   - The app calls the LLM, which returns a JSON with an explanation, an example, and five MCQs.
4. **Explanation & example** appear above the quiz – read them quickly.
5. **Answer the five questions** using the radio buttons.
6. Click **“Submit answers.”**
   - The app scores the quiz, shows the numeric score, the correct answer for any wrong question, and a short explanation of the gap.
7. Optionally click **“Start a new session”** to repeat with different material.

## 5️⃣ Error handling you might see
- **Missing API key** – a red warning tells you to add `AI_API_KEY` to `.env`.
- **HTTP error / rate‑limit** – a Streamlit error box displays the cause (e.g., `401 Unauthorized`).
- **Invalid LLM response** – the app validates the JSON; if the model returns malformed data you’ll see a friendly error (e.g., “LLM returned a number of questions other than five”).

## 6️⃣ Extending the prototype (optional for later phases)
- Swap the OpenAI endpoint for Gemini or Anthropic by editing `AI_API_URL` and `GENERATION_MODEL`.
- Add a simple cache (e.g., `st.cache_data`) for the LLM call if you want faster repeats during a demo.
- Replace the hard‑coded schema with a Pydantic model for stricter validation.

---

### TL;DR commands
```bash
# 1️⃣ copy env template and fill it
cp .env.example .env   # edit .env as described above

# 2️⃣ create & activate venv, install deps
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3️⃣ run the Streamlit demo
streamlit run app.py
```
Now you can drive the full StudyMate workflow for the judges.
