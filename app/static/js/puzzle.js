/**
 * RAG Tutor — Puzzle Generator JavaScript
 * Handles puzzle generation, word scramble, fill-blank, timer, hints, and sessionStorage persistence.
 */

const PUZZLE_STORAGE_KEY = 'ragtutor_puzzle_state';
let puzzleData = null;
let puzzleType = 'fill_blank';
let timerInterval = null;
let timerSeconds = 0;
let puzzleChecked = false;
let scrambledWords = {};

// ── Restore state on page load ───────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    const saved = sessionStorage.getItem(PUZZLE_STORAGE_KEY);
    if (saved) {
        try {
            const state = JSON.parse(saved);
            puzzleData = state.puzzleData;
            puzzleType = state.puzzleType || 'fill_blank';
            timerSeconds = state.timerSeconds || 0;
            puzzleChecked = state.puzzleChecked || false;
            scrambledWords = state.scrambledWords || {};

            // Restore tab selection
            document.querySelectorAll('.tab-btn').forEach(b => {
                b.classList.toggle('active', b.dataset.type === puzzleType);
            });

            if (puzzleData && puzzleData.puzzles && puzzleData.puzzles.length) {
                renderPuzzle(puzzleData.puzzles, true);

                // Restore input values
                if (state.inputValues) {
                    for (const [id, val] of Object.entries(state.inputValues)) {
                        const input = document.getElementById(`answer-${id}`);
                        if (input) input.value = val;
                    }
                }

                // If was checked, re-check
                if (puzzleChecked) {
                    checkPuzzle(true);
                } else {
                    startTimer();
                }
            }
        } catch { sessionStorage.removeItem(PUZZLE_STORAGE_KEY); }
    }
});

function saveState() {
    const inputValues = {};
    if (puzzleData) {
        puzzleData.puzzles.forEach(p => {
            const input = document.getElementById(`answer-${p.id}`);
            if (input) inputValues[p.id] = input.value;
        });
    }
    sessionStorage.setItem(PUZZLE_STORAGE_KEY, JSON.stringify({
        puzzleData, puzzleType, timerSeconds, puzzleChecked, scrambledWords, inputValues
    }));
}

function selectPuzzleType(btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    puzzleType = btn.dataset.type;
}

async function generatePuzzle() {
    const count = document.getElementById('puzzle-count').value;
    const btn = document.getElementById('generate-puzzle-btn');

    document.getElementById('puzzle-empty').style.display = 'none';
    document.getElementById('puzzle-area').style.display = 'none';
    document.getElementById('puzzle-loading').style.display = 'flex';
    document.getElementById('puzzle-result').style.display = 'none';
    btn.disabled = true;
    btn.innerHTML = '<i class="ph ph-spinner"></i> Generating...';
    stopTimer();
    timerSeconds = 0;
    puzzleChecked = false;
    scrambledWords = {};

    try {
        const res = await fetch('/puzzle/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: puzzleType, count }),
        });

        const data = await res.json();
        if (data.error) { showPuzzleError(data.error); return; }

        const parsed = parseJSON(data.result);
        if (!parsed || !parsed.puzzles || !parsed.puzzles.length) {
            showPuzzleError('Failed to parse puzzle data. Please try again.');
            return;
        }

        puzzleData = parsed;
        renderPuzzle(parsed.puzzles, false);
        startTimer();
        saveState();

    } catch (err) {
        showPuzzleError('Network error. Please try again.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="ph ph-sparkle"></i> Generate Puzzle';
        document.getElementById('puzzle-loading').style.display = 'none';
    }
}

function renderPuzzle(puzzles, isRestore) {
    const container = document.getElementById('puzzle-items');
    container.innerHTML = '';

    if (puzzleType === 'scramble') {
        puzzles.forEach((p, idx) => {
            let scrambled;
            if (isRestore && scrambledWords[p.id]) {
                scrambled = scrambledWords[p.id];
            } else {
                scrambled = scrambleWord(p.word);
                scrambledWords[p.id] = scrambled;
            }
            const card = document.createElement('div');
            card.className = 'puzzle-card glass-card';
            card.id = `puzzle-${p.id}`;
            card.innerHTML = `
                <div class="puzzle-number">#${idx + 1}</div>
                <div class="scramble-word">${scrambled}</div>
                <div class="puzzle-hint-text"><i class="ph ph-lightbulb"></i> ${p.hint}</div>
                <input type="text" class="puzzle-input" id="answer-${p.id}" placeholder="Unscramble the word..." autocomplete="off" oninput="saveState()">
                <div class="puzzle-feedback" id="pfeedback-${p.id}" style="display:none;"></div>
            `;
            container.appendChild(card);
        });
    } else {
        puzzles.forEach((p, idx) => {
            const card = document.createElement('div');
            card.className = 'puzzle-card glass-card';
            card.id = `puzzle-${p.id}`;
            const sentenceHTML = p.sentence.replace('___', '<span class="blank-marker">___</span>');
            card.innerHTML = `
                <div class="puzzle-number">#${idx + 1}</div>
                <div class="puzzle-sentence">${sentenceHTML}</div>
                <input type="text" class="puzzle-input" id="answer-${p.id}" placeholder="Fill in the blank..." autocomplete="off" oninput="saveState()">
                <button class="btn-hint" onclick="showHint(${p.id})" title="Show hint"><i class="ph ph-lightbulb"></i> Hint</button>
                <div class="puzzle-hint-reveal" id="hint-${p.id}" style="display:none;"></div>
                <div class="puzzle-feedback" id="pfeedback-${p.id}" style="display:none;"></div>
            `;
            container.appendChild(card);
        });
    }

    document.getElementById('puzzle-area').style.display = 'block';
    document.getElementById('puzzle-actions').style.display = 'flex';
    document.getElementById('puzzle-timer').style.display = 'flex';
    document.getElementById('puzzle-empty').style.display = 'none';
}

function scrambleWord(word) {
    const arr = word.toUpperCase().split('');
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    const scrambled = arr.join('');
    if (scrambled === word.toUpperCase() && word.length > 1) return arr.reverse().join('');
    return scrambled;
}

function showHint(id) {
    const puzzle = puzzleData.puzzles.find(p => p.id === id);
    if (!puzzle) return;
    const hintEl = document.getElementById(`hint-${id}`);
    if (hintEl) {
        hintEl.style.display = 'block';
        hintEl.innerHTML = `<i class="ph ph-info"></i> ${puzzle.hint || `Starts with "${puzzle.answer[0]}"`}`;
    }
}

function checkPuzzle(isRestore = false) {
    if (!puzzleData) return;
    stopTimer();

    let correct = 0;
    const total = puzzleData.puzzles.length;

    puzzleData.puzzles.forEach(p => {
        const input = document.getElementById(`answer-${p.id}`);
        const userAnswer = input.value.trim().toLowerCase();
        const correctAnswer = (p.word || p.answer).toLowerCase();
        const isCorrect = userAnswer === correctAnswer;
        if (isCorrect) correct++;

        input.disabled = true;
        input.classList.add(isCorrect ? 'input-correct' : 'input-incorrect');

        const feedback = document.getElementById(`pfeedback-${p.id}`);
        if (feedback) {
            feedback.style.display = 'block';
            feedback.className = `puzzle-feedback ${isCorrect ? 'feedback-correct' : 'feedback-incorrect'}`;
            feedback.innerHTML = `
                <i class="ph ${isCorrect ? 'ph-check-circle' : 'ph-x-circle'}"></i>
                <span>${isCorrect ? 'Correct!' : `Answer: ${p.word || p.answer}`}</span>
            `;
        }
    });

    const percent = Math.round((correct / total) * 100);
    document.getElementById('puzzle-actions').style.display = 'none';
    document.getElementById('puzzle-result').style.display = 'block';
    document.getElementById('puzzle-result-score').textContent = `${correct} / ${total} (${percent}%) — Time: ${formatTime(timerSeconds)}`;
    document.getElementById('puzzle-result-bar').style.width = `${percent}%`;

    if (percent >= 80) document.getElementById('puzzle-result-title').textContent = '🎉 Excellent!';
    else if (percent >= 50) document.getElementById('puzzle-result-title').textContent = '👍 Good Job!';
    else document.getElementById('puzzle-result-title').textContent = '📚 Keep Trying!';

    puzzleChecked = true;
    saveState();

    if (!isRestore) document.getElementById('puzzle-result').scrollIntoView({ behavior: 'smooth' });
}

function resetPuzzle() {
    puzzleData = null;
    puzzleChecked = false;
    scrambledWords = {};
    stopTimer();
    timerSeconds = 0;
    sessionStorage.removeItem(PUZZLE_STORAGE_KEY);
    document.getElementById('puzzle-area').style.display = 'none';
    document.getElementById('puzzle-result').style.display = 'none';
    document.getElementById('puzzle-timer').style.display = 'none';
    document.getElementById('puzzle-empty').style.display = 'flex';
    document.querySelector('#puzzle-empty h3').textContent = 'Ready for a challenge?';
    document.querySelector('#puzzle-empty p').textContent = 'Click "Generate Puzzle" to create word puzzles from your documents.';
}

function startTimer() {
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        timerSeconds++;
        updateTimerDisplay();
        // Save timer every 5 seconds to avoid excessive writes
        if (timerSeconds % 5 === 0) saveState();
    }, 1000);
}

function stopTimer() {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
}

function updateTimerDisplay() {
    document.getElementById('timer-display').textContent = formatTime(timerSeconds);
}

function formatTime(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

function showPuzzleError(msg) {
    document.getElementById('puzzle-loading').style.display = 'none';
    document.getElementById('puzzle-empty').style.display = 'flex';
    document.querySelector('#puzzle-empty h3').textContent = 'Oops!';
    document.querySelector('#puzzle-empty p').textContent = msg;
}

function parseJSON(text) {
    try { return JSON.parse(text); } catch {
        const match = text.match(/\{[\s\S]*\}/);
        if (match) { try { return JSON.parse(match[0]); } catch { return null; } }
        return null;
    }
}
