/**
 * RAG Tutor — Quiz Generator JavaScript
 * Handles quiz generation, answer selection, scoring, and sessionStorage persistence.
 */

const QUIZ_STORAGE_KEY = 'ragtutor_quiz_state';
let quizData = null;
let userAnswers = {};
let quizSubmitted = false;

// ── Restore state on page load ───────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    const saved = sessionStorage.getItem(QUIZ_STORAGE_KEY);
    if (saved) {
        try {
            const state = JSON.parse(saved);
            quizData = state.quizData;
            userAnswers = state.userAnswers || {};
            quizSubmitted = state.quizSubmitted || false;

            if (quizData && quizData.questions && quizData.questions.length) {
                renderQuiz(quizData.questions);
                // Restore selected answers
                for (const [qid, option] of Object.entries(userAnswers)) {
                    const btn = document.querySelector(`[data-qid="${qid}"][data-option="${option}"]`);
                    if (btn) btn.classList.add('selected');
                }
                // Re-submit if was already graded
                if (quizSubmitted) {
                    submitQuiz(true);
                }
            }
        } catch { sessionStorage.removeItem(QUIZ_STORAGE_KEY); }
    }
});

function saveState() {
    sessionStorage.setItem(QUIZ_STORAGE_KEY, JSON.stringify({
        quizData, userAnswers, quizSubmitted
    }));
}

async function generateQuiz() {
    const topic = document.getElementById('quiz-topic').value.trim();
    const numQuestions = document.getElementById('quiz-count').value;
    const btn = document.getElementById('generate-quiz-btn');

    document.getElementById('quiz-empty').style.display = 'none';
    document.getElementById('quiz-area').style.display = 'none';
    document.getElementById('quiz-loading').style.display = 'flex';
    document.getElementById('quiz-result').style.display = 'none';
    btn.disabled = true;
    btn.innerHTML = '<i class="ph ph-spinner"></i> Generating...';

    try {
        const res = await fetch('/quiz/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, num_questions: numQuestions }),
        });

        const data = await res.json();

        if (data.error) {
            showQuizError(data.error);
            return;
        }

        const parsed = parseJSON(data.result);
        if (!parsed || !parsed.questions || !parsed.questions.length) {
            showQuizError('Failed to parse quiz data. Please try again.');
            return;
        }

        quizData = parsed;
        userAnswers = {};
        quizSubmitted = false;
        saveState();
        renderQuiz(parsed.questions);

    } catch (err) {
        showQuizError('Network error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-sparkle"></i> Generate Quiz';
        document.getElementById('quiz-loading').style.display = 'none';
    }
}

function renderQuiz(questions) {
    const container = document.getElementById('quiz-questions');
    container.innerHTML = '';

    questions.forEach((q, idx) => {
        const card = document.createElement('div');
        card.className = 'question-card glass-card';
        card.id = `q-${q.id}`;

        let optionsHTML = '';
        for (const [key, value] of Object.entries(q.options)) {
            optionsHTML += `
                <button class="option-btn" data-qid="${q.id}" data-option="${key}" onclick="selectOption(this)">
                    <span class="option-key">${key}</span>
                    <span class="option-text">${value}</span>
                </button>`;
        }

        card.innerHTML = `
            <div class="question-number">Question ${idx + 1} of ${questions.length}</div>
            <div class="question-text">${q.question}</div>
            <div class="options-grid">${optionsHTML}</div>
            <div class="question-feedback" id="feedback-${q.id}" style="display:none;"></div>
        `;
        container.appendChild(card);
    });

    document.getElementById('quiz-area').style.display = 'block';
    document.getElementById('quiz-actions').style.display = 'flex';
    document.getElementById('quiz-empty').style.display = 'none';
}

function selectOption(btn) {
    if (quizSubmitted) return;
    const qid = btn.dataset.qid;
    const option = btn.dataset.option;

    document.querySelectorAll(`[data-qid="${qid}"]`).forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    userAnswers[qid] = option;
    saveState();
}

function submitQuiz(isRestore = false) {
    if (!quizData) return;

    let correct = 0;
    const total = quizData.questions.length;

    quizData.questions.forEach(q => {
        const qid = String(q.id);
        const userAnswer = userAnswers[qid];
        const isCorrect = userAnswer === q.correct;
        if (isCorrect) correct++;

        document.querySelectorAll(`[data-qid="${qid}"]`).forEach(btn => {
            btn.disabled = true;
            if (btn.dataset.option === q.correct) btn.classList.add('correct');
            else if (btn.dataset.option === userAnswer && !isCorrect) btn.classList.add('incorrect');
        });

        const feedback = document.getElementById(`feedback-${qid}`);
        if (feedback) {
            feedback.style.display = 'block';
            feedback.className = `question-feedback ${isCorrect ? 'feedback-correct' : 'feedback-incorrect'}`;
            feedback.innerHTML = `
                <i class="ph ${isCorrect ? 'ph-check-circle' : 'ph-x-circle'}"></i>
                <span>${isCorrect ? 'Correct!' : 'Incorrect.'} ${q.explanation || ''}</span>
            `;
        }
    });

    const percent = Math.round((correct / total) * 100);
    document.getElementById('quiz-actions').style.display = 'none';
    document.getElementById('quiz-result').style.display = 'block';
    document.getElementById('result-score').textContent = `${correct} / ${total} (${percent}%)`;
    document.getElementById('result-bar').style.width = `${percent}%`;

    if (percent >= 80) document.getElementById('result-title').textContent = '🎉 Excellent!';
    else if (percent >= 50) document.getElementById('result-title').textContent = '👍 Good Job!';
    else document.getElementById('result-title').textContent = '📚 Keep Studying!';

    quizSubmitted = true;
    saveState();

    if (!isRestore) {
        document.getElementById('quiz-result').scrollIntoView({ behavior: 'smooth' });
    }
}

function resetQuiz() {
    quizData = null;
    userAnswers = {};
    quizSubmitted = false;
    sessionStorage.removeItem(QUIZ_STORAGE_KEY);
    document.getElementById('quiz-area').style.display = 'none';
    document.getElementById('quiz-result').style.display = 'none';
    document.getElementById('quiz-empty').style.display = 'flex';
    document.querySelector('#quiz-empty h3').textContent = 'Ready to test yourself?';
    document.querySelector('#quiz-empty p').textContent = 'Click "Generate Quiz" to create questions from your documents.';
}

function showQuizError(msg) {
    document.getElementById('quiz-loading').style.display = 'none';
    document.getElementById('quiz-empty').style.display = 'flex';
    document.querySelector('#quiz-empty h3').textContent = 'Oops!';
    document.querySelector('#quiz-empty p').textContent = msg;
}

function parseJSON(text) {
    try { return JSON.parse(text); } catch {
        const match = text.match(/\{[\s\S]*\}/);
        if (match) { try { return JSON.parse(match[0]); } catch { return null; } }
        return null;
    }
}
