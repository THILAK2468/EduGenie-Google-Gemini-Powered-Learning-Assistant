// EduGenie frontend logic — no build step, vanilla JS.
// Talks directly to the FastAPI endpoints defined in main.py.

const API_BASE = ""; // same origin as this page; change if backend is hosted elsewhere
const USER_ID = "demo-user"; // placeholder until real auth/user system exists

let currentMode = "auto";
const modeSelectEl = document.getElementById("mode-select");
if (modeSelectEl) {
  modeSelectEl.addEventListener("change", (e) => {
    currentMode = e.target.value;
  });
}

const cardEl = document.getElementById("card");
const tabs = document.querySelectorAll(".tab");

// ---------------------------------------------------------------
// Module definitions: how to render the form, and how to call the API
// ---------------------------------------------------------------
const MODULES = {
  qa: {
    title: "Ask a question",
    hint: "Quick direct answers powered by Gemini cloud with local fallback.",
    fields: [{ name: "query_text", label: "Your question", type: "input" }],
    async call(values) {
      const params = new URLSearchParams({
        user_id: USER_ID,
        query_text: values.query_text,
        mode: currentMode,
      });
      const res = await fetch(`${API_BASE}/qa?${params}`);
      return res;
    },
  },
  explain: {
    title: "Explain a concept",
    hint: "Plain-terms concept explanations powered by Gemini cloud with local fallback.",
    fields: [{ name: "topic", label: "Topic to explain", type: "input" }],
    async call(values) {
      const res = await fetch(`${API_BASE}/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, topic: values.topic, mode: currentMode }),
      });
      return res;
    },
  },
  quiz: {
    title: "Generate a quiz",
    hint: "5 multiple-choice questions on any topic.",
    fields: [{ name: "topic", label: "Quiz topic", type: "input" }],
    async call(values) {
      const res = await fetch(`${API_BASE}/quiz`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, topic: values.topic, mode: currentMode }),
      });
      return res;
    },
  },
  summarize: {
    title: "Summarize a passage",
    hint: "Paste any educational text — get a 3-sentence summary.",
    fields: [{ name: "text", label: "Text to summarize", type: "textarea" }],
    async call(values) {
      const res = await fetch(`${API_BASE}/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: USER_ID, text: values.text, mode: currentMode }),
      });
      return res;
    },
  },
  learn: {
    title: "Plan a learning roadmap",
    hint: "A beginner-to-advanced path for any subject.",
    fields: [{ name: "subject", label: "Subject", type: "input" }],
    async call(values) {
      const params = new URLSearchParams({
        user_id: USER_ID,
        subject: values.subject,
        mode: currentMode,
      });
      const res = await fetch(`${API_BASE}/learn/recommendations?${params}`);
      return res;
    },
  },
};

let activeModule = "qa";

// ---------------------------------------------------------------
// Render the form for the active module
// ---------------------------------------------------------------
function renderCard() {
  const mod = MODULES[activeModule];

  const fieldsHtml = mod.fields
    .map((f) => {
      const tag =
        f.type === "textarea"
          ? `<textarea id="field-${f.name}" rows="5" placeholder="Paste text here..."></textarea>`
          : `<input id="field-${f.name}" type="text" placeholder="Type here..." />`;
      return `<div class="field"><label for="field-${f.name}">${f.label}</label>${tag}</div>`;
    })
    .join("");

  cardEl.innerHTML = `
    <h2 class="card__title">${mod.title}</h2>
    <p class="card__hint">${mod.hint}</p>
    <form id="module-form">
      ${fieldsHtml}
      <button type="submit" class="submit-btn">Submit</button>
    </form>
    <div class="response hidden" id="response-area"></div>
  `;

  document.getElementById("module-form").addEventListener("submit", handleSubmit);
}

// ---------------------------------------------------------------
// Handle form submit -> call API -> render response
// ---------------------------------------------------------------
async function handleSubmit(e) {
  e.preventDefault();
  const mod = MODULES[activeModule];
  const btn = e.target.querySelector(".submit-btn");
  const responseArea = document.getElementById("response-area");

  const values = {};
  mod.fields.forEach((f) => {
    values[f.name] = document.getElementById(`field-${f.name}`).value.trim();
  });

  // basic client-side check — mirrors the backend's own validation,
  // doesn't replace it (the backend still checks independently)
  if (Object.values(values).some((v) => !v)) {
    responseArea.classList.remove("hidden");
    responseArea.innerHTML = `<p class="response-text">Fill in the field above first.</p>`;
    return;
  }

  btn.disabled = true;
  btn.textContent = "Working...";
  responseArea.classList.remove("hidden");
  responseArea.innerHTML = `<p class="loading">Contacting the model...</p>`;

  try {
    const res = await mod.call(values);
    let data;
    try {
      data = await res.json();
    } catch {
      // Server didn't return JSON at all — likely an unhandled
      // exception (plain-text "Internal Server Error"). Show the
      // real HTTP status instead of a confusing parse error.
      throw new Error(`Server returned ${res.status} ${res.statusText} (no JSON body — check the backend terminal for the traceback)`);
    }
    if (!res.ok) {
      // Server DID return JSON, but it's an error payload (e.g. a
      // 400/422 validation error) — surface its actual message.
      throw new Error(data.detail ? JSON.stringify(data.detail) : `Server returned ${res.status}`);
    }
    renderResponse(responseArea, data);
  } catch (err) {
    responseArea.innerHTML = `<p class="response-text">Something went wrong reaching the server: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Submit";
  }
}

// ---------------------------------------------------------------
// Pull the actual answer text out of the response, regardless of
// which field name the backend used. QNA/Explanation/Quiz appear to
// use response_text consistently, but if Summarize/Roadmap's modules
// return the text under a different key, this catches it instead of
// silently showing "No response text."
// ---------------------------------------------------------------
function extractResponseText(data) {
  const candidates = [
    "response_text", "text", "result", "summary",
    "output_text", "output", "content", "answer",
  ];
  for (const key of candidates) {
    if (typeof data[key] === "string" && data[key].trim().length > 0) {
      return data[key];
    }
  }
  return null;
}

// ---------------------------------------------------------------
// Render the API response, including the model-source badge
// ---------------------------------------------------------------
function renderResponse(container, data) {
  // Temporary debug aid — open the browser console (F12) and check
  // this log if "No response text" shows up again despite a 200 OK.
  // It shows you the EXACT field names the backend actually sent.
  console.log(`[${activeModule}] raw response:`, data);

  if (data.blocked) {
    container.innerHTML = `
      <span class="badge badge--blocked">◉ blocked</span>
      <p class="response-text">This didn't look like an educational request (reason: ${data.reason}). Try rephrasing.</p>
    `;
    return;
  }

  let badgeHtml = "";
  if (data.model_used === "gemini") {
    badgeHtml = `<span class="badge badge--cloud">◉ cloud</span>`;
  } else if (data.model_used === "gemini-fallback") {
    badgeHtml = `<span class="badge badge--cloud" style="border: 1px dashed var(--ochre);">◉ cloud · fallback</span>`;
  } else if (data.model_used === "lamini") {
    badgeHtml = `<span class="badge badge--local">◉ local</span>`;
  } else if (data.model_used === "lamini-fallback") {
    badgeHtml = `<span class="badge badge--fallback">◉ local · fallback</span>`;
  } else if (data.model_used === "offline-fallback") {
    badgeHtml = `<span class="badge badge--blocked">◉ offline</span>`;
  } else if (data.model_used === "guardrail") {
    badgeHtml = `<span class="badge badge--blocked">◉ blocked</span>`;
  }

  const text = extractResponseText(data);

  // Quiz gets special structured rendering; everything else is plain text
  if (activeModule === "quiz" && text) {
    container.innerHTML = badgeHtml + renderQuiz(text);
    attachQuizHandlers(container);
  } else if (activeModule === "learn" && text) {
    container.innerHTML = badgeHtml + renderRoadmap(text);
  } else {
    container.innerHTML = `${badgeHtml}<p class="response-text">${escapeHtml(text || "No response text.")}</p>`;
  }
}

// ---------------------------------------------------------------
// Parse "Q: ... A) ... B) ... C) ... D) ... Correct: X" blocks
// ---------------------------------------------------------------
function renderQuiz(text) {
  const blocks = text.split(/\n(?=Q:)/).filter((b) => b.trim().startsWith("Q:"));
  if (blocks.length === 0) {
    return `<p class="response-text">${escapeHtml(text)}</p>`;
  }

  return blocks
    .map((block, qIndex) => {
      const qMatch = block.match(/Q:\s*(.+)/);
      const question = qMatch ? qMatch[1].trim() : "";
      const optionMatches = [...block.matchAll(/([A-D])\)\s*(.+)/g)];
      const correctMatch = block.match(/Correct:\s*([A-D])/);
      const correctLetter = correctMatch ? correctMatch[1] : null;

      const optionsHtml = optionMatches
        .map(([, letter, text]) => {
          return `<div class="quiz-option" data-question="${qIndex}" data-letter="${letter}" data-correct="${correctLetter}">${letter}) ${escapeHtml(text.trim())}</div>`;
        })
        .join("");

      return `
        <div class="quiz-question">
          <div class="quiz-question__text">${escapeHtml(question)}</div>
          <div class="quiz-question__options">${optionsHtml}</div>
        </div>
      `;
    })
    .join("");
}

// After quiz HTML is inserted into the page, attach click handlers so
// the correct answer only reveals once the student picks an option —
// not immediately on render.
function attachQuizHandlers(container) {
  container.querySelectorAll(".quiz-option").forEach((optionEl) => {
    optionEl.addEventListener("click", () => {
      const qIndex = optionEl.dataset.question;
      const correctLetter = optionEl.dataset.correct;
      const alreadyAnswered = container.querySelector(
        `.quiz-option[data-question="${qIndex}"].selected`
      );
      if (alreadyAnswered) return; // one selection per question

      // Mark this one as selected, and reveal the correct answer
      // among all options for this question.
      container
        .querySelectorAll(`.quiz-option[data-question="${qIndex}"]`)
        .forEach((el) => {
          el.classList.add("revealed");
          if (el.dataset.letter === correctLetter) el.classList.add("correct");
          if (el === optionEl && el.dataset.letter !== correctLetter) {
            el.classList.add("incorrect");
          }
        });
      optionEl.classList.add("selected");
    });
  });
}

// ---------------------------------------------------------------
// Parse "Beginner: / Intermediate: / Advanced:" sections with bullets
// ---------------------------------------------------------------
function renderRoadmap(text) {
  const tiers = ["Beginner", "Intermediate", "Advanced"];
  const sections = {};

  tiers.forEach((tier, i) => {
    const start = text.indexOf(`${tier}:`);
    if (start === -1) return;
    const nextTier = tiers[i + 1];
    const end = nextTier && text.indexOf(`${nextTier}:`) !== -1
      ? text.indexOf(`${nextTier}:`)
      : text.length;
    sections[tier] = text.slice(start + tier.length + 1, end);
  });

  if (Object.keys(sections).length === 0) {
    return `<p class="response-text">${escapeHtml(text)}</p>`;
  }

  return Object.entries(sections)
    .map(([tier, content]) => {
      const items = content
        .split(/\n/)
        .map((line) => line.replace(/^[\s*\-#]+/, "").replace(/\*\*/g, "").trim())
        .filter((line) => line.length > 0);

      const itemsHtml = items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");

      return `
        <div class="roadmap-tier">
          <h3>${tier}</h3>
          <ul>${itemsHtml}</ul>
        </div>
      `;
    })
    .join("");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    activeModule = tab.dataset.module;
    renderCard();
  });
});

renderCard();