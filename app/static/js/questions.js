/**
 * RAG Tutor — Question Bank JavaScript
 * Handles question generation, flashcard flip, T/F checking, progress tracking, and sessionStorage persistence.
 */

const QUESTIONS_STORAGE_KEY = 'ragtutor_questions_state';
let questionsData = null;
let questionType = 'short_answer';
let answeredCount = 0;
let totalCount = 0;
let answeredIds = {};  // track which items have been answered

// ── Restore state on page load ───────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    const saved = sessionStorage.getItem(QUESTIONS_STORAGE_KEY);
    if (saved) {
        try {
            const state = JSON.parse(saved);
            questionsData = state.questionsData;
            questionType = state.questionType || 'short_answer';
            answeredIds = state.answeredIds || {};

            // Restore tab selection
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.type === questionType);
            });

            if (questionsData) {
                renderQuestions(questionsData, true);
            }
        } catch { sessionStorage.removeItem(QUESTIONS_STORAGE_KEY); }
    }
});

function saveState() {
    sessionStorage.setItem(QUESTIONS_STORAGE_KEY, JSON.stringify({
        questionsData, questionType, answeredIds
    }));
}

function selectQuestionType(btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    questionType = btn.dataset.type;
}

async function generateQuestions() {
    const count = document.getElementById('questions-count').value;
    const btn = document.getElementById('generate-questions-btn');

    document.getElementById('questions-empty').style.display = 'none';
    document.getElementById('questions-area').style.display = 'none';
    document.getElementById('questions-loading').style.display = 'flex';
    document.getElementById('progress-tracker').style.display = 'none';
    btn.disabled = true;
    btn.innerHTML = '<i class="ph ph-spinner"></i> Generating...';
    answeredCount = 0;
    answeredIds = {};

    try {
        const res = await fetch('/questions/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: questionType, count }),
        });

        const data = await res.json();
        if (data.error) { showQError(data.error); return; }

        const parsed = parseJSON(data.result);
        if (!parsed) { showQError('Failed to parse response. Please try again.'); return; }

        questionsData = parsed;
        renderQuestions(parsed, false);
        saveState();

    } catch (err) {
        showQError('Network error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-sparkle"></i> Generate';
        document.getElementById('questions-loading').style.display = 'none';
    }
}

function renderQuestions(data, isRestore) {
    const container = document.getElementById('questions-items');
    container.innerHTML = '';

    if (questionType === 'flashcard') {
        const cards = data.flashcards || [];
        totalCount = cards.length;
        cards.forEach((fc, idx) => {
            const card = document.createElement('div');
            card.className = 'flashcard-wrapper';
            card.innerHTML = `
                <div class="flashcard ${isRestore && answeredIds[fc.id] ? 'flipped' : ''}" id="fc-${fc.id}" onclick="flipCard(${fc.id})">
                    <div class="flashcard-inner">
                        <div class="flashcard-front">
                            <div class="fc-number">${idx + 1} / ${cards.length}</div>
                            <div class="fc-content">${fc.front}</div>
                            <div class="fc-hint"><i class="ph ph-cursor-click"></i> Click to reveal answer</div>
                        </div>
                        <div class="flashcard-back">
                            <div class="fc-number">${idx + 1} / ${cards.length}</div>
                            <div class="fc-label">Answer</div>
                            <div class="fc-content">${fc.back}</div>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
    } else if (questionType === 'true_false') {
        const questions = data.questions || [];
        totalCount = questions.length;
        questions.forEach((q, idx) => {
            const wasAnswered = isRestore && answeredIds[q.id];
            const card = document.createElement('div');
            card.className = 'tf-card glass-card';
            card.id = `tf-${q.id}`;
            card.innerHTML = `
                <div class="question-number">Question ${idx + 1} of ${questions.length}</div>
                <div class="question-text">${q.statement}</div>
                <div class="tf-buttons">
                    <button class="tf-btn tf-true ${wasAnswered ? 'tf-disabled' : ''}" onclick="answerTF(${q.id}, true, this)" ${wasAnswered ? 'disabled' : ''}>
                        <i class="ph ph-check-circle"></i> True
                    </button>
                    <button class="tf-btn tf-false ${wasAnswered ? 'tf-disabled' : ''}" onclick="answerTF(${q.id}, false, this)" ${wasAnswered ? 'disabled' : ''}>
                        <i class="ph ph-x-circle"></i> False
                    </button>
                </div>
                <div class="question-feedback" id="qfeedback-${q.id}" style="display:none;"></div>
            `;
            container.appendChild(card);

            // Restore answered state
            if (wasAnswered) {
                const userAnswer = answeredIds[q.id].answer;
                const isCorrect = userAnswer === q.answer;
                const targetBtn = userAnswer ? card.querySelector('.tf-true') : card.querySelector('.tf-false');
                if (targetBtn) targetBtn.classList.add(isCorrect ? 'tf-correct' : 'tf-wrong');
                const feedback = document.getElementById(`qfeedback-${q.id}`);
                if (feedback) {
                    feedback.style.display = 'block';
                    feedback.className = `question-feedback ${isCorrect ? 'feedback-correct' : 'feedback-incorrect'}`;
                    feedback.innerHTML = `<i class="ph ${isCorrect ? 'ph-check-circle' : 'ph-x-circle'}"></i><span>${isCorrect ? 'Correct!' : 'Incorrect.'} ${q.explanation || ''}</span>`;
                }
            }
        });
    } else {
        const questions = data.questions || [];
        totalCount = questions.length;
        questions.forEach((q, idx) => {
            const wasRevealed = isRestore && answeredIds[q.id];
            const card = document.createElement('div');
            card.className = 'sa-card glass-card';
            card.id = `sa-${q.id}`;
            card.innerHTML = `
                <div class="question-number">Question ${idx + 1} of ${questions.length}</div>
                <div class="question-text">${q.question}</div>
                <button class="btn-show-answer" onclick="toggleAnswer(${q.id}, this)" ${wasRevealed ? 'data-counted="true"' : ''}>
                    <i class="ph ph-eye${wasRevealed ? '-closed' : ''}"></i> ${wasRevealed ? 'Hide Answer' : 'Show Answer'}
                </button>
                <div class="sa-answer" id="sa-answer-${q.id}" style="display:${wasRevealed ? 'block' : 'none'};">
                    <div class="sa-answer-label"><i class="ph ph-check-circle"></i> Model Answer</div>
                    <div class="sa-answer-text">${q.answer}</div>
                </div>
            `;
            container.appendChild(card);
        });
    }

    // Restore answered count
    answeredCount = Object.keys(answeredIds).length;

    document.getElementById('questions-area').style.display = 'block';
    document.getElementById('progress-tracker').style.display = 'flex';
    document.getElementById('questions-empty').style.display = 'none';
    updateProgress();
}

function flipCard(id) {
    const card = document.getElementById(`fc-${id}`);
    if (card && !card.classList.contains('flipped')) {
        card.classList.add('flipped');
        if (!answeredIds[id]) {
            answeredIds[id] = true;
            answeredCount++;
            updateProgress();
            saveState();
        }
    }
}

function answerTF(id, userAnswer, btn) {
    if (answeredIds[id]) return;
    const q = questionsData.questions.find(q => q.id === id);
    if (!q) return;

    const isCorrect = userAnswer === q.answer;
    answeredIds[id] = { answer: userAnswer };
    answeredCount++;

    const card = document.getElementById(`tf-${id}`);
    card.querySelectorAll('.tf-btn').forEach(b => {
        b.disabled = true;
        b.classList.add('tf-disabled');
    });
    btn.classList.add(isCorrect ? 'tf-correct' : 'tf-wrong');

    const feedback = document.getElementById(`qfeedback-${id}`);
    if (feedback) {
        feedback.style.display = 'block';
        feedback.className = `question-feedback ${isCorrect ? 'feedback-correct' : 'feedback-incorrect'}`;
        feedback.innerHTML = `<i class="ph ${isCorrect ? 'ph-check-circle' : 'ph-x-circle'}"></i><span>${isCorrect ? 'Correct!' : 'Incorrect.'} ${q.explanation || ''}</span>`;
    }

    updateProgress();
    saveState();
}

function toggleAnswer(id, btn) {
    const answerEl = document.getElementById(`sa-answer-${id}`);
    if (answerEl.style.display === 'none') {
        answerEl.style.display = 'block';
        btn.innerHTML = '<i class="ph ph-eye-closed"></i> Hide Answer';
        if (!answeredIds[id]) {
            answeredIds[id] = true;
            answeredCount++;
            btn.dataset.counted = 'true';
            updateProgress();
            saveState();
        }
    } else {
        answerEl.style.display = 'none';
        btn.innerHTML = '<i class="ph ph-eye"></i> Show Answer';
    }
}

function updateProgress() {
    document.getElementById('progress-text').textContent = `${answeredCount} / ${totalCount}`;
    const pct = totalCount > 0 ? (answeredCount / totalCount) * 100 : 0;
    document.getElementById('progress-bar').style.width = `${pct}%`;
}

function showQError(msg) {
    document.getElementById('questions-loading').style.display = 'none';
    document.getElementById('questions-empty').style.display = 'flex';
    document.querySelector('#questions-empty h3').textContent = 'Oops!';
    document.querySelector('#questions-empty p').textContent = msg;
}

function parseJSON(text) {
    try { return JSON.parse(text); } catch {
        const match = text.match(/\{[\s\S]*\}/);
        if (match) { try { return JSON.parse(match[0]); } catch { return null; } }
        return null;
    }
}
