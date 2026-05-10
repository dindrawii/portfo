(function () {
  "use strict";

  var models = window.OPENROUTER_FREE_MODELS || [];

  // --------------------------------------------------
  // DOM references
  // --------------------------------------------------
  var promptInput   = document.getElementById("mb-prompt-input");
  var submitBtn     = document.getElementById("mb-submit-btn");
  var gameIntro     = document.getElementById("game-intro");
  var gameLoading   = document.getElementById("game-loading");
  var gameResponses = document.getElementById("game-responses");
  var textA         = document.getElementById("mb-text-a");
  var textB         = document.getElementById("mb-text-b");
  var errorA        = document.getElementById("mb-error-a");
  var errorB        = document.getElementById("mb-error-b");
  var voting        = document.getElementById("mb-voting");
  var voteA         = document.getElementById("mb-vote-a");
  var voteB         = document.getElementById("mb-vote-b");
  var voteTie       = document.getElementById("mb-vote-tie");
  var resultDiv     = document.getElementById("mb-result");
  var revealDiv     = document.getElementById("mb-reveal");
  var scoreDiv      = document.getElementById("mb-score");
  var newRoundBtn   = document.getElementById("mb-new-round-btn");
  var globalError   = document.getElementById("mb-global-error");

  // --------------------------------------------------
  // Session score (persisted in localStorage)
  // --------------------------------------------------
  var STORAGE_KEY = "model_battle_score";

  function buildEmptyScore() {
    var s = { ties: 0, rounds: 0 };
    models.forEach(function (m) { s[m.id] = 0; });
    return s;
  }

  function loadScore() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        var parsed = JSON.parse(raw);
        // Ensure all model IDs exist in the loaded score
        var s = buildEmptyScore();
        Object.keys(s).forEach(function (k) {
          if (typeof parsed[k] === "number") s[k] = parsed[k];
        });
        s.ties  = typeof parsed.ties  === "number" ? parsed.ties  : 0;
        s.rounds = typeof parsed.rounds === "number" ? parsed.rounds : 0;
        return s;
      }
    } catch (_) {}
    return buildEmptyScore();
  }

  function saveScore(s) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); } catch (_) {}
  }

  var score = loadScore();
  var lastVote = null;
  var currentData = null;

  // --------------------------------------------------
  // Helpers
  // --------------------------------------------------
  function show(el)  { el.style.display = ""; }
  function hide(el)  { el.style.display = "none"; }

  function escapeHtml(str) {
    var d = document.createElement("div");
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
  }

  function showGlobalError(msg) {
    globalError.textContent = msg;
    show(globalError);
  }

  function hideGlobalError() {
    hide(globalError);
  }

  function showLoading() {
    submitBtn.disabled = true;
    hide(gameIntro);
    hide(gameResponses);
    hide(resultDiv);
    hide(globalError);
    show(gameLoading);
  }

  function hideLoading() {
    submitBtn.disabled = false;
    hide(gameLoading);
  }

  // --------------------------------------------------
  // Render response cards with anonymous labels
  // --------------------------------------------------
  function renderResponses(data) {
    if (data.response_a !== null && data.response_a !== undefined) {
      textA.textContent = data.response_a;
      hide(errorA);
      show(textA);
    } else {
      errorA.textContent = data.model_a_error || "An unknown error occurred.";
      hide(textA);
      show(errorA);
    }

    if (data.response_b !== null && data.response_b !== undefined) {
      textB.textContent = data.response_b;
      hide(errorB);
      show(textB);
    } else {
      errorB.textContent = data.model_b_error || "An unknown error occurred.";
      hide(textB);
      show(errorB);
    }

    currentData = data;
    lastVote = null;
    voteA.disabled = false;
    voteB.disabled = false;
    voteTie.disabled = false;

    show(gameResponses);
    show(voting);
    hide(resultDiv);
    hideLoading();
  }

  // --------------------------------------------------
  // Reveal model names after vote
  // --------------------------------------------------
  function revealModels() {
    var mA = currentData.model_a;
    var mB = currentData.model_b;
    var winnerText = "It's a tie!";
    if (lastVote === "a") winnerText = mA.name + " wins this round!";
    else if (lastVote === "b") winnerText = mB.name + " wins this round!";

    var html = "";
    html += '<div class="mb-reveal-title">Models Revealed</div>';
    html += '<div class="mb-reveal-cards">';

    // Card A
    html += '<div class="mb-reveal-card' + (lastVote === "a" ? " mb-winner" : "") + '">';
    html +=   '<div class="mb-reveal-name">' + escapeHtml(mA.name) + '</div>';
    html +=   '<div class="mb-reveal-cat">' + escapeHtml(mA.category) + '</div>';
    html +=   '<div class="mb-reveal-id">' + escapeHtml(mA.id) + '</div>';
    if (lastVote === "a") html += '<div class="mb-reveal-badge">YOUR PICK</div>';
    html += '</div>';

    // Card B
    html += '<div class="mb-reveal-card' + (lastVote === "b" ? " mb-winner" : "") + '">';
    html +=   '<div class="mb-reveal-name">' + escapeHtml(mB.name) + '</div>';
    html +=   '<div class="mb-reveal-cat">' + escapeHtml(mB.category) + '</div>';
    html +=   '<div class="mb-reveal-id">' + escapeHtml(mB.id) + '</div>';
    if (lastVote === "b") html += '<div class="mb-reveal-badge">YOUR PICK</div>';
    html += '</div>';

    html += '</div>';
    html += '<div class="mb-round-winner">' + winnerText + '</div>';

    revealDiv.innerHTML = html;
    updateScoreDisplay();
    show(resultDiv);
  }

  // --------------------------------------------------
  // Score display
  // --------------------------------------------------
  function updateScoreDisplay() {
    var html = '<div class="mb-score-title">Session Score</div>';
    html += '<div class="mb-score-grid">';

    var entries = [];
    models.forEach(function (m) {
      entries.push({ id: m.id, name: m.name, wins: score[m.id] || 0 });
    });
    entries.sort(function (a, b) { return b.wins - a.wins; });

    entries.forEach(function (e) {
      var pct = score.rounds > 0 ? Math.round((e.wins / score.rounds) * 100) : 0;
      html += '<div class="mb-score-row">';
      html +=   '<span class="mb-score-name">' + escapeHtml(e.name) + '</span>';
      html +=   '<span class="mb-score-bar-wrap"><span class="mb-score-bar" style="width:' + pct + '%"></span></span>';
      html +=   '<span class="mb-score-num">' + e.wins + ' win' + (e.wins !== 1 ? 's' : '') + '</span>';
      html += '</div>';
    });

    html += '</div>';
    html += '<div class="mb-score-meta">Ties: ' + (score.ties || 0) + ' &nbsp;|&nbsp; Rounds: ' + (score.rounds || 0) + '</div>';

    scoreDiv.innerHTML = html;
  }

  // --------------------------------------------------
  // New round: return to intro, keep score
  // --------------------------------------------------
  function startNewRound() {
    currentData = null;
    lastVote = null;
    hide(gameResponses);
    hide(resultDiv);
    hide(globalError);
    promptInput.value = "";
    show(gameIntro);
    updateScoreDisplay();
  }

  // --------------------------------------------------
  // Event listeners
  // --------------------------------------------------
  submitBtn.addEventListener("click", function () {
    var prompt = promptInput.value.trim();
    if (!prompt) {
      showGlobalError("Please enter a prompt before submitting.");
      return;
    }
    hideGlobalError();
    showLoading();

    fetch("/api/model-battle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: prompt })
    })
    .then(function (resp) {
      return resp.json().then(function (data) {
        return { status: resp.status, data: data };
      });
    })
    .then(function (result) {
      hideLoading();

      if (!result.data.ok) {
        showGlobalError(result.data.error || "Something went wrong. Please try again.");
        return;
      }

      renderResponses(result.data);
    })
    .catch(function (_) {
      hideLoading();
      showGlobalError("Network error. Please check your connection and try again.");
    });
  });

  voteA.addEventListener("click", function () {
    lastVote = "a";
    voteA.disabled = true;
    voteB.disabled = true;
    voteTie.disabled = true;
    score[currentData.model_a.id]++;
    score.rounds++;
    saveScore(score);
    revealModels();
  });

  voteB.addEventListener("click", function () {
    lastVote = "b";
    voteA.disabled = true;
    voteB.disabled = true;
    voteTie.disabled = true;
    score[currentData.model_b.id]++;
    score.rounds++;
    saveScore(score);
    revealModels();
  });

  voteTie.addEventListener("click", function () {
    lastVote = "tie";
    voteA.disabled = true;
    voteB.disabled = true;
    voteTie.disabled = true;
    score.ties++;
    score.rounds++;
    saveScore(score);
    revealModels();
  });

  newRoundBtn.addEventListener("click", startNewRound);

  promptInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && e.ctrlKey) {
      e.preventDefault();
      submitBtn.click();
    }
  });

  // --------------------------------------------------
  // Init
  // --------------------------------------------------
  hide(gameLoading);
  hide(gameResponses);
  hide(resultDiv);
  if (!models.length) {
    showGlobalError("Model list failed to load. Refresh the page and try again.");
    submitBtn.disabled = true;
    return;
  }
  updateScoreDisplay();
})();
