document.addEventListener('DOMContentLoaded', () => {
  const startForm = document.getElementById('start-form');
  const sessionFormSection = document.getElementById('session-form');
  const studyArea = document.getElementById('study-area');
  const quizArea = document.getElementById('quiz-area');
  const resultArea = document.getElementById('result-area');
  const explanationDiv = document.getElementById('explanation');
  const exampleDiv = document.getElementById('example');
  const startQuizBtn = document.getElementById('start-quiz-btn');
  const questionContainer = document.getElementById('question-container');
  const submitQuizBtn = document.getElementById('submit-quiz-btn');
  const scoreP = document.getElementById('score');
  const feedbackDiv = document.getElementById('feedback');
  const newSessionBtn = document.getElementById('new-session-btn');
  const formError = document.getElementById('form-error');
  const quizError = document.getElementById('quiz-error');

  let sessionId = null;
  let questions = [];

  function resetUI() {
    sessionFormSection.classList.remove('hidden');
    studyArea.classList.add('hidden');
    quizArea.classList.add('hidden');
    resultArea.classList.add('hidden');
    explanationDiv.textContent = '';
    exampleDiv.textContent = '';
    questionContainer.innerHTML = '';
    feedbackDiv.innerHTML = '';
    formError.textContent = '';
    quizError.textContent = '';
    submitQuizBtn.disabled = true;
  }

  function showError(elem, msg) {
    elem.textContent = msg;
    elem.style.display = 'block';
  }

  startForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    formError.textContent = '';
    const subject = e.target.subject.value.trim();
    const topic = e.target.topic.value.trim();
    const material = e.target.material.value.trim();
    if (!subject || !topic || !material) {
      showError(formError, 'All fields are required');
      return;
    }
    try {
      const resp = await fetch('/api/start_session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, topic, material }),
      });
      if (!resp.ok) throw new Error(`Server error ${resp.status}`);
      const data = await resp.json();
      sessionId = data.session_id;
      explanationDiv.textContent = data.explanation;
      exampleDiv.textContent = data.example;
      questions = data.questions;
      sessionFormSection.classList.add('hidden');
      studyArea.classList.remove('hidden');
    } catch (err) {
      showError(formError, err.message);
    }
  });

  startQuizBtn.addEventListener('click', () => {
    quizArea.classList.remove('hidden');
    renderQuestions();
  });

  function renderQuestions() {
    questionContainer.innerHTML = '';
    questions.forEach((q, idx) => {
      const div = document.createElement('div');
      div.className = 'question-block';
      const title = document.createElement('h4');
      title.textContent = `Question ${idx + 1} of ${questions.length}`;
      const prompt = document.createElement('p');
      prompt.textContent = q.question;
      const optionsDiv = document.createElement('div');
      q.options.forEach((opt, i) => {
        const label = document.createElement('label');
        label.className = 'option-label';
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = `q_${q.id}`;
        radio.value = i;
        radio.required = true;
        label.appendChild(radio);
        label.appendChild(document.createTextNode(' ' + opt));
        optionsDiv.appendChild(label);
        optionsDiv.appendChild(document.createElement('br'));
      });
      div.appendChild(title);
      div.appendChild(prompt);
      div.appendChild(optionsDiv);
      questionContainer.appendChild(div);
    });
    submitQuizBtn.disabled = false;
  }

  submitQuizBtn.addEventListener('click', async () => {
    quizError.textContent = '';
    const answers = [];
    for (const q of questions) {
      const radios = document.getElementsByName(`q_${q.id}`);
      let selected = null;
      radios.forEach(r => { if (r.checked) selected = parseInt(r.value); });
      if (selected === null) {
        showError(quizError, 'Please answer all questions');
        return;
      }
      answers.push({ question_id: q.id, selected_option: selected });
    }
    try {
      const resp = await fetch('/api/submit_answers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, answers }),
      });
      if (!resp.ok) throw new Error(`Server error ${resp.status}`);
      const data = await resp.json();
      scoreP.textContent = `Score: ${data.score}`;
      feedbackDiv.innerHTML = '';
      data.feedback.forEach((fb, idx) => {
        const div = document.createElement('div');
        div.className = 'feedback-item';
        const q = questions[idx];
        const status = fb.correct ? '✅ Correct' : `❌ Incorrect (Correct: ${q.options[fb.correct_option]})`;
        const expl = fb.explanation ? `<p>${fb.explanation}</p>` : '';
        div.innerHTML = `<strong>Q${idx + 1}:</strong> ${status}${expl}`;
        feedbackDiv.appendChild(div);
      });
      quizArea.classList.add('hidden');
      resultArea.classList.remove('hidden');
    } catch (err) {
      showError(quizError, err.message);
    }
  });

  newSessionBtn.addEventListener('click', resetUI);
  resetUI();
});
