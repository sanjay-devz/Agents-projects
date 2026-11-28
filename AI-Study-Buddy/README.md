# StudyMate – AI Study Buddy

## Overview
StudyMate is a lightweight web application that helps students study campus courses.  A student provides a **subject**, a **topic**, and the **syllabus material** for that topic.  StudyMate then:

1. Generates a simple explanation with one concrete example based on the supplied material.
2. Generates **exactly five** multiple‑choice practice questions.
3. Lets the student answer the questions.
4. Scores the quiz and gives detailed feedback for any wrong answers.

The app is built with **plain HTML/CSS/JavaScript** for the frontend and **FastAPI** for the backend.  All AI calls are performed on the server so the API key never leaves the backend.

---

## Project Structure
```
StudyMate/
├─ api/                     # FastAPI backend (Vercel serverless functions)
│   ├─ __init__.py
│   ├─ app.py               # FastAPI entry point
│   ├─ models.py            # Pydantic request/response models
│   └─ ai.py                # Wrapper for the AI provider
├─ public/                  # Front‑end static files served by Vercel
│   ├─ index.html
│   ├─ styles.css
│   └─ script.js
├─ .gitignore
├─ .env.example            # Example environment variables
├─ requirements.txt
├─ vercel.json              # Vercel configuration
└─ README.md                # This file
```
---

## Prerequisites
* Python 3.10+ (tested with 3.11)
* A virtual environment tool (`venv` or `conda`)
* An AI model provider that offers a REST JSON API (e.g., OpenAI, Anthropic, Gemini).  You only need the **API key** and the **base URL**.

---

## Local Development
1. **Clone the repository** (once you have pushed it to GitHub).
   ```bash
   git clone <your‑repo‑url>
   cd StudyMate
   ```
2. **Create a virtual environment** and install dependencies.
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # on Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Copy the example environment file and add your credentials**.
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   ```
   AI_API_KEY=your‑api‑key
   AI_API_URL=https://api.your‑provider.com/v1/chat/completions
   ```
4. **Run the app locally**
   ```bash
   uvicorn api.app:app --reload
   ```
   The frontend is served from `public/`.  Open the browser at `http://localhost:8000/public/index.html`.

---

## Running the Tests (optional)
At the moment the project does not ship automated tests, but you can quickly check that the FastAPI app starts without syntax errors:
```bash
python -m py_compile $(git ls-files "*.py")
```
---

## Vercel Deployment
1. **Create a Vercel project** and connect it to the GitHub repository.
2. **Add the required environment variables** in the Vercel dashboard:
   * `AI_API_KEY`
   * `AI_API_URL`
3. **Deploy** – Vercel automatically detects the `vercel.json` configuration and builds the Python backend as serverless functions.  Static files under `public/` are served directly.
4. After deployment, the app will be reachable at `https://<your‑project>.vercel.app`.

### Vercel Compatibility Note
FastAPI works on Vercel’s Python runtime (currently 3.11).  The backend is placed in the `api/` directory; each `.py` file becomes a serverless function.  The `vercel.json` file maps all files under `api/` to the `python3.11` runtime.  No additional build steps are required.

---

## How the Backend Works
* **`/api/start_session`** – receives the subject, topic, and material, calls the AI model to generate an explanation, example, and five MCQs, stores the answer key in memory, and returns the data needed for the frontend.
* **`/api/submit_answers`** – receives the session ID and the student’s selected options, compares them to the stored answer key, computes a score and per‑question feedback, then returns this information.
* **`/api/health`** – simple health check used by Vercel and local scripts.

All AI calls request **structured JSON** from the model, and the server validates the response before sending anything to the client.  If the model returns malformed data the server responds with a clear error message.

---

## Contributing
* Fork the repository.
* Create a feature branch (`git checkout -b feature/awesome‑thing`).
* Open a Pull Request against `main`.
* Follow the coding style in the existing files – keep the code beginner‑friendly and well‑commented where the logic is non‑obvious.

---

## License
This project is provided under the MIT License – feel free to use, modify, and share.
