security added:-
Security currently in the project
- Local AI processing: Study notes are sent to the local Ollama server using the gemma2:latest model; no cloud AI API or API key is used by default.

- No stored credentials: The app does not require an API key.

- Input limits: Subject, topic, and study material fields have character limits.

- AI response validation: The app checks that Gemma returns five questions, four options per question, and a valid answer index before using the quiz.

- Local session state: Quiz answers and results are kept in the Streamlit session; there is no project database.