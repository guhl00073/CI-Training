// CI-Hörtrainer Modern Web Application Engine

let exercises = { minimal_pairs: [], monosyllables: [], numbers: [], sentences: [] };

let currentMP = null;
let currentMPTargetIndex = 0;
let currentMPTargetWord = "";
let currentMPWords = [];

let currentES = null;
let currentESTargetWord = "";

let currentNum = null;
let currentNumTargetWord = "";

let currentSent = null;
let currentSentTargetIndex = 0;
let currentSentTargetWord = "";
let currentSentWords = [];

// Attempt tracking - module level so check functions can read them
let mpAttempted = false;
let esAttempted = false;
let numAttempted = false;
let sentAttempted = false;

let isPlaying = false;
let audioBalance = 0.0;
let audioVolume = 1.0;
let noiseVolume = 0.4;

function getIPASimple(word) {
  if (!word) return "";
  const norm = String(word).toLowerCase().trim();
  const dict = {
    "pass": "[pas]", "bass": "[bas]", "tasse": "['tasə]", "dasse": "['dasə]",
    "haus": "[haʊ̯s]", "maus": "[maʊ̯s]", "kamm": "[kam]", "komm": "[kɔm]",
    "bus": "[bʊs]", "dach": "[dax]", "fisch": "[fɪʃ]", "brot": "[bʁoːt]",
    "strand": "[ʃtʁant]", "herbst": "[hɛʁpst]", "katze": "['katsə]", "mond": "[moːnt]",
    "zug": "[tsuːk]", "buch": "[buːx]", "schiff": "[ʃɪf]", "sonne": "['zɔnə]",
    "tisch": "[tɪʃ]", "bett": "[bɛt]", "hund": "[hʊnt]"
  };
  if (dict[norm]) return dict[norm];
  if (norm.startsWith("sch")) return `[${norm.replace('sch', 'ʃ')}]`;
  if (norm.startsWith("ch")) return `[${norm.replace('ch', 'ç')}]`;
  return `[${norm.replace('z', 'ts')}]`;
}
let audioRate = 1.0;
let maskNoise = false;
let ambientNoise = false;
let ambientVolume = 0.4;
let selectedAmbientType = "noise";

let selectedVoice = "Anna";
let selectedMPCategory = "ALL";
let selectedFreqFilter = "none";
let currentEditorView = "minimal_pairs";
let autoStart = false;
let autoMic = true;
let adaptiveSNR = false;
let correctStreak = 0;

function announceA11y(text) {
  const el = document.getElementById("a11yAnnouncer");
  if (el) {
    el.textContent = "";
    setTimeout(() => { el.textContent = text; }, 50);
  }
}

function handleAdaptiveSNR(isCorrect) {
  if (!adaptiveSNR || !maskNoise) return;
  if (isCorrect) {
    correctStreak++;
    if (correctStreak >= 3) {
      noiseVolume = Math.min(0.85, Math.round((noiseVolume + 0.05) * 100) / 100);
      correctStreak = 0;
      const slider = document.getElementById("maskVolSlider");
      const badge = document.getElementById("maskVolVal");
      if (slider) slider.value = noiseVolume;
      if (badge) badge.textContent = `${Math.round(noiseVolume * 100)}%`;
      syncNoiseConfig();
      showToast(`🎯 Adaptive SNR: Störschall auf ${Math.round(noiseVolume * 100)}% erhöht!`, "info");
    }
  } else {
    correctStreak = 0;
    noiseVolume = Math.max(0.10, Math.round((noiseVolume - 0.05) * 100) / 100);
    const slider = document.getElementById("maskVolSlider");
    const badge = document.getElementById("maskVolVal");
    if (slider) slider.value = noiseVolume;
    if (badge) badge.textContent = `${Math.round(noiseVolume * 100)}%`;
    syncNoiseConfig();
    showToast(`🎯 Adaptive SNR: Störschall auf ${Math.round(noiseVolume * 100)}% gesenkt.`, "info");
  }
}

function calculateLevel(xp) {
  if (xp <= 500) return 1;
  if (xp <= 2000) return 2;
  if (xp <= 5000) return 3;
  return 4 + Math.floor((xp - 5000) / 3000);
}

let userXP = parseInt(localStorage.getItem("ci_user_xp") || "0", 10);
let userLevel = calculateLevel(userXP);

// Initialize App
document.addEventListener("DOMContentLoaded", async () => {
  initAudioControls();
  initCanvasVisualizer();
  initTabs();
  initEditor();
  await loadExercises();
  initSpeechRecognition();
  initHelpModal();
  initKeyboardShortcuts();
  updateStats();
  syncNoiseConfig();
});

async function syncNoiseConfig() {
  try {
    await fetch("/api/noise/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mask_noise: maskNoise,
        ambient_noise: ambientNoise,
        balance: audioBalance,
        noise_volume: noiseVolume,
        ambient_volume: ambientVolume
      })
    });
  } catch (e) {
    console.error("Fehler beim Synchronisieren der Rauscheinstellungen:", e);
  }
}

// Load Exercises from API
async function loadExercises() {
  try {
    const res = await fetch("/api/exercises");
    exercises = await res.json();
    nextMPItem();
    nextESItem();
    nextNumItem();
    nextSentItem();
    nextNoiseItem();
    nextMemoryItem();
    renderEditorList();
    updateEditorCounts();
    setStatus("System bereit. Datensätze geladen.");
  } catch (e) {
    setStatus("Fehler beim Laden der Datensätze.");
  }
}

// Audio Control Listeners
function initAudioControls() {
  const ctrlDetails = document.getElementById("controlPanelDetails");
  if (ctrlDetails) {
    const savedState = localStorage.getItem("ci_ctrl_open");
    if (savedState !== null) {
      ctrlDetails.open = (savedState === "true");
    }
    ctrlDetails.addEventListener("toggle", () => {
      localStorage.setItem("ci_ctrl_open", ctrlDetails.open ? "true" : "false");
    });
  }

  const volSlider = document.getElementById("volSlider");
  const volVal = document.getElementById("volVal");
  volSlider.addEventListener("input", (e) => {
    audioVolume = parseFloat(e.target.value);
    volVal.textContent = `${Math.round(audioVolume * 100)}%`;
  });

  const rateSlider = document.getElementById("rateSlider");
  const rateVal = document.getElementById("rateVal");
  rateSlider.addEventListener("input", (e) => {
    audioRate = parseFloat(e.target.value);
    rateVal.textContent = `${audioRate.toFixed(1)}x`;
  });

  const voiceSelect = document.getElementById("voiceSelect");
  if (voiceSelect) {
    selectedVoice = voiceSelect.value;
    voiceSelect.addEventListener("change", (e) => {
      selectedVoice = e.target.value;
      setStatus(`Stimme gewechselt: ${selectedVoice}`);
    });
  }

  const maskToggle = document.getElementById("maskToggle");
  const maskVal = document.getElementById("maskVal");
  if (maskToggle) {
    maskNoise = maskToggle.checked;
    maskVal.textContent = maskNoise ? "Ja" : "Nein";
    maskToggle.addEventListener("change", (e) => {
      maskNoise = e.target.checked;
      maskVal.textContent = maskNoise ? "Ja" : "Nein";
      syncNoiseConfig();
    });
  }

  const maskVolSlider = document.getElementById("maskVolSlider");
  const maskVolVal = document.getElementById("maskVolVal");
  if (maskVolSlider) {
    maskVolSlider.addEventListener("input", (e) => {
      noiseVolume = parseFloat(e.target.value);
      if (maskVolVal) maskVolVal.textContent = `${Math.round(noiseVolume * 100)}%`;
      syncNoiseConfig();
    });
  }

  const segBtns = document.querySelectorAll(".segmented-control .seg-btn[data-bal]");
  segBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      segBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      audioBalance = parseFloat(btn.dataset.bal);
      if (isNaN(audioBalance)) audioBalance = 0.0;

      const balVal = document.getElementById("balVal");
      if (audioBalance === -1.0) balVal.textContent = "Nur Links (CI)";
      else if (audioBalance === 1.0) balVal.textContent = "Nur Rechts (CI)";
      else balVal.textContent = "Beide Ohren";

      syncNoiseConfig();
    });
  });

  const freqFilterSelect = document.getElementById("freqFilterSelect");
  const freqFilterBadge = document.getElementById("freqFilterBadge");
  if (freqFilterSelect) {
    selectedFreqFilter = freqFilterSelect.value;
    freqFilterSelect.addEventListener("change", (e) => {
      selectedFreqFilter = e.target.value;
      const labels = {
        "none": "Normal",
        "high_boost": "Hochton +6dB",
        "highpass": "Hochpass 1000Hz",
        "lowpass": "Tiefpass 3000Hz"
      };
      if (freqFilterBadge) freqFilterBadge.textContent = labels[selectedFreqFilter] || "Normal";
      setStatus(`Audio-Filter: ${labels[selectedFreqFilter] || selectedFreqFilter}`);
    });
  }

  autoStart = localStorage.getItem("ci_autostart") === "true";
  autoMic = localStorage.getItem("ci_automic") !== "false";

  const autoStartToggle = document.getElementById("autoStartToggle");
  if (autoStartToggle) {
    autoStartToggle.addEventListener("change", (e) => setAutoStart(e.target.checked));
  }
  const autoMicToggle = document.getElementById("autoMicToggle");
  if (autoMicToggle) {
    autoMicToggle.addEventListener("change", (e) => setAutoMic(e.target.checked));
  }

  const adaptiveSNRToggle = document.getElementById("adaptiveSNRToggle");
  const adaptiveSNRVal = document.getElementById("adaptiveSNRVal");
  if (adaptiveSNRToggle) {
    adaptiveSNRToggle.addEventListener("change", (e) => {
      adaptiveSNR = e.target.checked;
      if (adaptiveSNRVal) adaptiveSNRVal.textContent = adaptiveSNR ? "Ein" : "Aus";
      if (adaptiveSNR && !maskNoise) {
        const maskToggle = document.getElementById("maskToggle");
        if (maskToggle) {
          maskToggle.checked = true;
          maskNoise = true;
          const maskVal = document.getElementById("maskVal");
          if (maskVal) maskVal.textContent = "Ja";
          syncNoiseConfig();
        }
      }
      showToast(adaptiveSNR ? "🎯 Adaptive SNR aktiviert (Dynamischer Störschall)" : "Adaptive SNR deaktiviert", "info");
    });
  }

  document.querySelectorAll(".auto-start-check").forEach(chk => {
    chk.addEventListener("change", (e) => setAutoStart(e.target.checked));
  });
  updateAutoStartUI();
}

function updateAutoStartUI() {
  const autoStartToggle = document.getElementById("autoStartToggle");
  const autoStartVal = document.getElementById("autoStartVal");
  if (autoStartToggle) autoStartToggle.checked = autoStart;
  if (autoStartVal) autoStartVal.textContent = autoStart ? "Ja" : "Nein";

  const autoMicToggle = document.getElementById("autoMicToggle");
  const autoMicVal = document.getElementById("autoMicVal");
  if (autoMicToggle) autoMicToggle.checked = autoMic;
  if (autoMicVal) autoMicVal.textContent = autoMic ? "Ja" : "Nein";

  document.querySelectorAll(".auto-start-check").forEach(chk => {
    chk.checked = autoStart;
  });
}

function setAutoStart(val) {
  autoStart = val;
  localStorage.setItem("ci_autostart", autoStart ? "true" : "false");
  updateAutoStartUI();
}

function setAutoMic(val) {
  autoMic = val;
  localStorage.setItem("ci_automic", autoMic ? "true" : "false");
  updateAutoStartUI();
}

function switchTab(tabId) {
  const tabs = document.querySelectorAll(".tab-btn");
  const contents = document.querySelectorAll(".tab-content");
  tabs.forEach(t => t.classList.remove("active"));
  contents.forEach(c => c.classList.remove("active"));

  const targetTab = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  const targetContent = document.getElementById(`tab-${tabId}`);
  if (targetTab) targetTab.classList.add("active");
  if (targetContent) targetContent.classList.add("active");

  if (tabId === "weakness") loadWeaknessExercises();
  if (tabId === "stats") updateStats();
  if (tabId === "editor") renderEditorList();
}

// Initialize Tabs
function initTabs() {
  const tabs = document.querySelectorAll(".tab-btn");
  const contents = document.querySelectorAll(".tab-content");

  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      contents.forEach(c => c.classList.remove("active"));

      btn.classList.add("active");
      const targetId = `tab-${btn.dataset.tab}`;
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add("active");
      }

      if (btn.dataset.tab !== "noise" && !maskNoise) {
        stopNoiseAudio();
      }

      if (btn.dataset.tab === "weakness") loadWeaknessExercises();
      if (btn.dataset.tab === "stats") updateStats();
      if (btn.dataset.tab === "editor") renderEditorList();
      if (btn.dataset.tab === "sent") {
        if (!currentSent) {
          nextSentItem();
        } else {
          renderSentCards();
        }
      }
      if (btn.dataset.tab === "memory") {
        if (!targetMemoryWords || targetMemoryWords.length === 0) {
          nextMemoryItem();
        } else {
          renderMemoryUI();
        }
      }
    });
  });

  // Action Buttons Setup
  document.getElementById("mpPlayBtn").addEventListener("click", playMPAudio);
  document.getElementById("mpNextBtn").addEventListener("click", () => nextMPItem(true));

  document.getElementById("esPlayBtn").addEventListener("click", playESAudio);
  document.getElementById("esCheckBtn").addEventListener("click", checkESAnswer);
  document.getElementById("esNextBtn").addEventListener("click", () => nextESItem(true));
  document.getElementById("esInput").addEventListener("keypress", (e) => { if (e.key === "Enter") checkESAnswer(); });

  const esModeSel = document.getElementById("esModeSelect");
  const esListSel = document.getElementById("esTestListSelect");
  const esListContainer = document.getElementById("esListSelectorContainer");

  if (esModeSel) {
    esModeSel.addEventListener("change", (e) => {
      esMode = e.target.value;
      if (esMode === "test_list") {
        if (esListContainer) esListContainer.style.display = "flex";
        startFreiburgerTestList(parseInt(esListSel ? esListSel.value : 1));
      } else {
        if (esListContainer) esListContainer.style.display = "none";
        const banner = document.getElementById("esTestProgressBanner");
        if (banner) banner.style.display = "none";
        const resCard = document.getElementById("esTestResultCard");
        if (resCard) resCard.classList.add("hidden");
        nextESItem(true);
      }
    });
  }

  if (esListSel) {
    esListSel.addEventListener("change", (e) => {
      startFreiburgerTestList(parseInt(e.target.value));
    });
  }

  document.getElementById("esTestRestartBtn")?.addEventListener("click", () => {
    startFreiburgerTestList(currentTestListNum);
  });

  document.getElementById("esTestNextListBtn")?.addEventListener("click", () => {
    const nextNum = currentTestListNum + 1;
    if (esListSel) esListSel.value = nextNum.toString();
    startFreiburgerTestList(nextNum);
  });

  document.getElementById("numPlayBtn").addEventListener("click", playNumAudio);
  document.getElementById("numCheckBtn").addEventListener("click", checkNumAnswer);
  document.getElementById("numNextBtn").addEventListener("click", () => nextNumItem(true));
  document.getElementById("numInput").addEventListener("keypress", (e) => { if (e.key === "Enter") checkNumAnswer(); });

  document.getElementById("sentPlayBtn").addEventListener("click", playSentAudio);
  document.getElementById("sentNextBtn").addEventListener("click", () => nextSentItem(true));
  document.getElementById("sentModeMCBtn")?.addEventListener("click", () => setSentMode("mc"));
  document.getElementById("sentModeFullBtn")?.addEventListener("click", () => setSentMode("full"));
  document.getElementById("sentFullSubmitBtn")?.addEventListener("click", checkSentFullAnswer);
  document.getElementById("sentFullInput")?.addEventListener("keypress", (e) => { if (e.key === "Enter") checkSentFullAnswer(); });

  // Schwachstellen-Training Buttons
  document.getElementById("weaknessQuickBtn")?.addEventListener("click", () => switchTab("weakness"));
  document.getElementById("refreshWeaknessBtn")?.addEventListener("click", loadWeaknessExercises);
  document.getElementById("weaknessPlayBtn")?.addEventListener("click", playWeaknessAudio);
  document.getElementById("weaknessNextBtn")?.addEventListener("click", () => nextWeaknessItem(true));

  // Störschall Buttons
  document.getElementById("noisePlayBtn")?.addEventListener("click", playNoiseAudio);
  document.getElementById("noiseStopBtn")?.addEventListener("click", stopNoiseAudio);
  document.getElementById("noiseCheckBtn")?.addEventListener("click", checkNoiseAnswer);
  document.getElementById("noiseNextBtn")?.addEventListener("click", () => nextNoiseItem(true));
  document.getElementById("noiseInput")?.addEventListener("keypress", (e) => { if (e.key === "Enter") checkNoiseAnswer(); });

  // Auditives Gedächtnis Buttons
  document.getElementById("memoryPlayBtn")?.addEventListener("click", playMemoryAudio);
  document.getElementById("memoryCheckBtn")?.addEventListener("click", checkMemoryAnswer);
  document.getElementById("memoryNextBtn")?.addEventListener("click", () => nextMemoryItem(true));
  document.getElementById("memoryResetBtn")?.addEventListener("click", resetMemorySelection);
  document.getElementById("memorySpanSelect")?.addEventListener("change", () => nextMemoryItem(true));

  const mpCatSelect = document.getElementById("mpCategorySelect");
  if (mpCatSelect) {
    mpCatSelect.addEventListener("change", (e) => {
      selectedMPCategory = e.target.value;
      nextMPItem(true);
    });
  }

  document.getElementById("refreshStatsBtn").addEventListener("click", updateStats);
  const resetStatsBtn = document.getElementById("resetStatsBtn");
  if (resetStatsBtn) {
    resetStatsBtn.addEventListener("click", async () => {
      if (confirm("Möchtest du die gesamte Trainings-Statistik wirklich zurücksetzen?")) {
        await resetStats();
      }
    });
  }
}

// Play Audio via API & Trigger Visualizer Wave
async function playTTS(text, labelName = "Audio", options = {}) {
  if (!text) return;
  const statusMsg = maskNoise && audioBalance !== 0.0 ? `▶ Spiele ${labelName}... (Vertäubung aktiv)` : `▶ Spiele ${labelName}...`;
  setStatus(statusMsg);
  triggerWaveform(2.5);

  const payload = {
    text: text,
    rate: options.rate !== undefined ? options.rate : audioRate,
    balance: options.balance !== undefined ? options.balance : audioBalance,
    volume: options.volume !== undefined ? options.volume : audioVolume,
    voice: options.voice !== undefined ? options.voice : selectedVoice,
    mask_noise: options.mask_noise !== undefined ? options.mask_noise : maskNoise,
    noise_volume: options.noise_volume !== undefined ? options.noise_volume : noiseVolume,
    ambient_noise: options.ambient_noise !== undefined ? options.ambient_noise : false,
    ambient_type: options.ambient_type !== undefined ? options.ambient_type : "noise",
    ambient_volume: options.ambient_volume !== undefined ? options.ambient_volume : 0.3,
    freq_filter: options.freq_filter !== undefined ? options.freq_filter : selectedFreqFilter,
    wait: options.wait !== undefined ? options.wait : false
  };

  try {
    await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    setStatus("Fehler bei Audio-Synthese.");
  }
}

// Gamification XP Add
function addXP(amount) {
  userXP += amount;
  userLevel = calculateLevel(userXP);
  localStorage.setItem("ci_user_xp", userXP);
  const badge = document.getElementById("userLevelBadge");
  if (badge) {
    badge.textContent = `⭐ Level ${userLevel} | ${userXP} XP`;
  }
}

// Minimalpaare Tab Logic
function nextMPItem(userTriggered = false) {
  if (!exercises.minimal_pairs || exercises.minimal_pairs.length === 0) return;

  let pool = exercises.minimal_pairs;
  if (selectedMPCategory === "RHYMES") {
    pool = exercises.minimal_pairs.filter(item => item.options || (item.category && item.category.includes("Reim")));
    if (pool.length === 0) pool = exercises.minimal_pairs;
  } else if (selectedMPCategory !== "ALL") {
    pool = exercises.minimal_pairs.filter(item => item.category === selectedMPCategory || (item.category && item.category.includes(selectedMPCategory)));
    if (pool.length === 0) pool = exercises.minimal_pairs;
  }

  currentMP = pool[Math.floor(Math.random() * pool.length)];

  if (currentMP.options && currentMP.options.length > 0) {
    currentMPWords = [...currentMP.options];
  } else {
    currentMPWords = [currentMP.word_a, currentMP.word_b];
  }

  currentMPTargetIndex = Math.floor(Math.random() * currentMPWords.length);
  currentMPTargetWord = currentMPWords[currentMPTargetIndex];
  mpAttempted = false;

  document.getElementById("mpCategory").textContent = `Fokus: ${currentMP.category}`;
  const mpSrcEl = document.getElementById("mpSource");
  if (mpSrcEl) mpSrcEl.textContent = currentMP.source ? `🏛 Quelle: ${currentMP.source}` : "🏛 Marburger Minimalpaar-Katalog";
  document.getElementById("mpHint").textContent = `Hinweis: ${currentMP.hint}`;

  const cardsContainer = document.querySelector("#tab-mp .cards-grid");
  cardsContainer.innerHTML = "";

  currentMPWords.forEach((word, idx) => {
    const card = document.createElement("div");
    card.className = "option-card";
    card.id = `card_${idx}`;
    card.innerHTML = `
      <div class="card-top-bar">
        <span class="card-label">OPTION ${String.fromCharCode(65 + idx)}</span>
        <button class="card-audio-btn" title="Dieses Wort vorlesen">🔊</button>
      </div>
      <span class="card-word">${word}</span>
      <span class="card-ipa">${getIPASimple(word)}</span>
    `;
    const audioBtn = card.querySelector(".card-audio-btn");
    if (audioBtn) {
      audioBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        playTTS(word, `Option ${String.fromCharCode(65 + idx)}`);
      });
    }
    card.addEventListener("click", () => checkMPAnswer(idx));
    cardsContainer.appendChild(card);
  });

  const feedback = document.getElementById("mpFeedback");
  feedback.className = "feedback-banner hidden";
  setStatus(`Bereit für Übung (${currentMP.category}).`);

  if (userTriggered && autoStart) {
    playMPAudio();
  }
}

function playMPAudio() {
  playTTS(currentMPTargetWord, "Minimalpaar");
}

async function checkMPAnswer(chosenIndex) {
  const chosenWord = currentMPWords[chosenIndex];
  const isCorrect = (chosenIndex === currentMPTargetIndex);

  const cards = document.querySelectorAll("#tab-mp .option-card");
  const feedback = document.getElementById("mpFeedback");

  cards.forEach((card, idx) => {
    card.className = "option-card";
    if (idx === chosenIndex) {
      card.classList.add(isCorrect ? "correct" : "incorrect");
    }
  });

  if (mpAttempted) {
    // Only update visual highlight, do not evaluate/log stats again for subsequent clicks
    return;
  }
  mpAttempted = true;

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: currentMPTargetWord,
      user_input: chosenWord,
      module: "Minimalpaare",
      category: currentMP.category
    })
  });
  const evalData = await res.json();

  let ipaHtml = "";
  if (evalData.ipa_target) {
    ipaHtml = `
      <div style="margin-top:0.6rem; padding:0.5rem 0.8rem; background:rgba(15,23,42,0.6); border-radius:8px; font-size:0.85rem; text-align:left;">
        <span style="color:#C084FC; font-weight:700;">🔤 IPA-Lautschrift:</span> ${evalData.ipa_target} 
        <span style="margin-left:0.8rem; color:#60A5FA; font-weight:700;">📍 Artikulationsort:</span> ${evalData.articulation_place} 
        <span style="display:block; font-size:0.8rem; color:var(--text-muted); margin-top:0.2rem;">💡 ${evalData.articulation_hint || ""}</span>
      </div>
    `;
  }

  if (isCorrect) {
    feedback.innerHTML = `<div>✓ Richtig! Es war '<strong>${currentMPTargetWord}</strong>'. (+20 XP)</div>${ipaHtml}`;
    feedback.className = "feedback-banner success";
    announceA11y(`Richtig! Es war ${currentMPTargetWord}. Plus 20 Punkte.`);
    addXP(20);
  } else {
    feedback.innerHTML = `<div>✗ Falsch. Gesprochen wurde '<strong>${currentMPTargetWord}</strong>' (du hast '${chosenWord}' gewählt).</div>${ipaHtml}`;
    feedback.className = "feedback-banner danger";
    announceA11y(`Falsch. Gesprochen wurde ${currentMPTargetWord}, du hast ${chosenWord} gewählt.`);
  }

  handleAdaptiveSNR(isCorrect);

  if (autoStart) {
    setTimeout(() => nextMPItem(true), 1800);
  }
}

// Einsilber Tab Logic (mit Freiburger Testlisten DIN 45621)
let esMode = "random"; // "random" or "test_list"
let freiburgerTestLists = null;
let currentTestListNum = 1;
let currentTestIndex = 0;
let currentTestWords = [];
let currentTestResults = [];

async function loadFreiburgerTestLists() {
  if (freiburgerTestLists) return freiburgerTestLists;
  try {
    const res = await fetch("/api/test_lists");
    freiburgerTestLists = await res.json();
    return freiburgerTestLists;
  } catch (e) {
    console.error("Fehler beim Laden der Freiburger Testlisten:", e);
    return {};
  }
}

async function startFreiburgerTestList(listNum = 1) {
  const lists = await loadFreiburgerTestLists();
  const listKey = `Liste ${listNum}`;
  const testData = lists[listKey];
  if (!testData || !testData.words || testData.words.length === 0) {
    showToast("Testliste konnte nicht geladen werden.", "danger");
    return;
  }

  currentTestListNum = listNum;
  currentTestIndex = 0;
  currentTestWords = testData.words;
  currentTestResults = [];

  const resCard = document.getElementById("esTestResultCard");
  if (resCard) resCard.classList.add("hidden");
  const banner = document.getElementById("esTestProgressBanner");
  if (banner) banner.style.display = "flex";

  updateESTestProgressUI();
  loadESTestItem(0);
}

function updateESTestProgressUI() {
  const progressText = document.getElementById("esTestProgressText");
  const scoreText = document.getElementById("esTestScoreText");
  if (progressText) {
    progressText.textContent = `Wort ${currentTestIndex + 1} von ${currentTestWords.length} (Freiburger Testliste ${currentTestListNum})`;
  }
  if (scoreText) {
    const correctCount = currentTestResults.filter(r => r.is_correct).length;
    scoreText.textContent = `Ergebnis: ${correctCount} / ${currentTestResults.length}`;
  }
}

function loadESTestItem(idx) {
  if (idx < 0 || idx >= currentTestWords.length) return;
  currentES = currentTestWords[idx];
  currentESTargetWord = currentES.word || "";
  esAttempted = false;

  document.getElementById("esCategory").textContent = `Freiburger Liste ${currentTestListNum} (${idx + 1}/20)`;
  document.getElementById("esInput").value = "";
  const feedback = document.getElementById("esFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus(`Wort ${idx + 1} von 20 (Freiburger Testliste ${currentTestListNum}).`);

  if (autoStart) {
    playESAudio();
  }
}

function nextESItem(userTriggered = false) {
  if (esMode === "test_list") {
    if (currentTestResults.length <= currentTestIndex) {
      currentTestResults.push({ target: currentESTargetWord, answer: "-", is_correct: false });
    }
    currentTestIndex++;
    if (currentTestIndex >= currentTestWords.length) {
      finishFreiburgerTestList();
      return;
    }
    updateESTestProgressUI();
    loadESTestItem(currentTestIndex);
    if (userTriggered && autoStart) playESAudio();
    return;
  }

  if (!exercises.monosyllables || exercises.monosyllables.length === 0) return;
  const validItems = exercises.monosyllables.filter(item => item.word && !item.word.startsWith("Wort_"));
  const pool = validItems.length > 0 ? validItems : exercises.monosyllables;

  currentES = pool[Math.floor(Math.random() * pool.length)];
  currentESTargetWord = currentES.word || currentES.target || "";
  esAttempted = false;  // reset module-level flag

  document.getElementById("esCategory").textContent = `Kategorie: ${currentES.category || "General"}`;
  document.getElementById("esInput").value = "";
  const feedback = document.getElementById("esFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus("Bereit für Einsilber-Übung.");

  if (userTriggered && autoStart) {
    playESAudio();
  }
}

async function playESAudio() {
  await playTTS(currentESTargetWord, "Einsilber");
  if (autoMic || autoStart) {
    startAutoMic("es");
  }
}

async function checkESAnswer() {
  if (esAttempted) return;
  esAttempted = true;

  const userInput = document.getElementById("esInput").value.trim();
  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: currentESTargetWord,
      user_input: userInput,
      module: "Einsilber",
      category: esMode === "test_list" ? `Freiburger Liste ${currentTestListNum}` : currentES.category
    })
  });
  const data = await res.json();
  const feedback = document.getElementById("esFeedback");

  let ipaHtml = "";
  if (data.ipa_target) {
    ipaHtml = `
      <div style="margin-top:0.6rem; padding:0.5rem 0.8rem; background:rgba(15,23,42,0.6); border-radius:8px; font-size:0.85rem; text-align:left;">
        <span style="color:#C084FC; font-weight:700;">🔤 IPA-Lautschrift:</span> ${data.ipa_target} 
        <span style="margin-left:0.8rem; color:#60A5FA; font-weight:700;">📍 Artikulationsort:</span> ${data.articulation_place} 
        <span style="display:block; font-size:0.8rem; color:var(--text-muted); margin-top:0.2rem;">💡 ${data.articulation_hint || ""}</span>
      </div>
    `;
  }

  feedback.innerHTML = `<div>${data.message}</div>${ipaHtml}`;
  feedback.className = `feedback-banner ${data.is_correct ? "success" : "danger"}`;
  if (data.is_correct) addXP(30);

  if (esMode === "test_list") {
    currentTestResults.push({
      target: currentESTargetWord,
      answer: userInput,
      is_correct: data.is_correct,
      score: data.score
    });
    updateESTestProgressUI();

    if (currentTestResults.length >= 20 || currentTestIndex >= currentTestWords.length - 1) {
      setTimeout(() => finishFreiburgerTestList(), 1500);
      return;
    }
  }

  if (autoStart) {
    setTimeout(() => nextESItem(true), 1800);
  }
}

async function finishFreiburgerTestList() {
  const total = currentTestWords.length || 20;
  const correct = currentTestResults.filter(r => r.is_correct).length;
  const percent = Math.round((correct / total) * 100);

  const card = document.getElementById("esTestResultCard");
  const scoreLarge = document.getElementById("esTestScoreLarge");
  const scoreDetails = document.getElementById("esTestScoreDetails");
  const breakdown = document.getElementById("esTestWordBreakdown");

  if (card && scoreLarge && scoreDetails && breakdown) {
    scoreLarge.textContent = `${percent}%`;
    scoreLarge.style.color = percent >= 80 ? "#10B981" : (percent >= 50 ? "#F59E0B" : "#EF4444");
    scoreDetails.textContent = `Ergebnis Freiburger Testliste ${currentTestListNum}: ${correct} von ${total} Wörtern richtig erkannt.`;

    let html = "<table style='width:100%; border-collapse:collapse; font-size:0.9rem;'>";
    html += "<tr style='border-bottom:1px solid rgba(255,255,255,0.1); text-align:left;'><th>#</th><th>Vorgabe</th><th>Eingabe</th><th>Ergebnis</th></tr>";
    currentTestResults.forEach((item, idx) => {
      const statusSymbol = item.is_correct ? "✅" : "❌";
      html += `<tr style='border-bottom:1px solid rgba(255,255,255,0.05);'>
        <td style='padding:0.3rem 0;'>${idx + 1}</td>
        <td><strong>${item.target}</strong></td>
        <td>${item.answer || "-"}</td>
        <td>${statusSymbol}</td>
      </tr>`;
    });
    html += "</table>";
    breakdown.innerHTML = html;

    card.classList.remove("hidden");
    const banner = document.getElementById("esTestProgressBanner");
    if (banner) banner.style.display = "none";
  }

  try {
    await fetch("/api/test_run/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        test_name: "Freiburger Einsilbertest (DIN 45621)",
        list_num: currentTestListNum,
        total_words: total,
        correct_words: correct,
        score_percent: percent
      })
    });
    showToast(`🏆 Testergebnis (${percent}%) in DB gespeichert.`, "success");
  } catch (e) {
    console.error("Fehler beim Speichern des Testergebnisses:", e);
  }
}

// Numbers Tab Logic
function nextNumItem(userTriggered = false) {
  if (!exercises.numbers || exercises.numbers.length === 0) return;
  currentNum = exercises.numbers[Math.floor(Math.random() * exercises.numbers.length)];
  currentNumTargetWord = currentNum.spoken;
  numAttempted = false;  // reset module-level flag

  document.getElementById("numCategory").textContent = `Kategorie: ${currentNum.type}`;
  document.getElementById("numInput").value = "";
  const feedback = document.getElementById("numFeedback");
  feedback.className = "feedback-banner hidden";
  setStatus("Bereit für Zahlenübung.");

  if (userTriggered && autoStart) {
    playNumAudio();
  }
}

async function playNumAudio() {
  await playTTS(currentNumTargetWord, "Zahl / Uhrzeit");
  if (autoMic || autoStart) {
    startAutoMic("num");
  }
}

async function checkNumAnswer() {
  if (numAttempted) return;
  numAttempted = true;

  const userInput = document.getElementById("numInput").value.trim();
  const targetVal = currentNum.value.trim();

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: targetVal,
      spoken: currentNumTargetWord,
      user_input: userInput,
      module: "Zahlen",
      category: currentNum.type
    })
  });

  const data = await res.json();
  const feedback = document.getElementById("numFeedback");
  feedback.textContent = data.message;
  feedback.className = `feedback-banner ${data.is_correct ? "success" : "danger"}`;
  if (data.is_correct) addXP(25);

  if (autoStart) {
    setTimeout(() => nextNumItem(true), 1800);
  }
}

// Sentence Training Tab Logic
function renderSentCards() {
  if (!currentSent) return;

  let rawOpts = currentSent.options;
  if (typeof rawOpts === "string") {
    try { rawOpts = JSON.parse(rawOpts); } catch (e) { rawOpts = []; }
  }
  if (!Array.isArray(rawOpts)) {
    rawOpts = [];
  }

  // Extract all distinct words from sentence as candidates if explicit options are missing/fewer than 2
  const sentenceWords = (currentSent.sentence || "")
    .replace(/[.,!?;:()""'']/g, "")
    .split(/\s+/)
    .map(w => w.trim())
    .filter(w => w.length > 0);

  if (rawOpts.length < 2 && sentenceWords.length > 0) {
    rawOpts = Array.from(new Set(sentenceWords));
  }

  if (currentSent.target_word) {
    const cleanTarget = currentSent.target_word.toLowerCase().replace(/[.,!?;:]/g, "").trim();
    const hasTarget = rawOpts.some(w => w.toLowerCase().replace(/[.,!?;:]/g, "").trim() === cleanTarget);
    if (!hasTarget) rawOpts.unshift(currentSent.target_word);
  }

  currentSentWords = rawOpts;
  currentSentTargetWord = currentSent.target_word || (currentSentWords[0] || "");
  currentSentTargetIndex = currentSentWords.indexOf(currentSentTargetWord);

  const catEl = document.getElementById("sentCategory");
  if (catEl) catEl.textContent = `Kategorie: ${currentSent.category || "Alltagssätze"}`;

  // Replace target word in sentence display with blank line
  const maskedSentence = (currentSentTargetWord && currentSent.sentence)
    ? currentSent.sentence.replace(currentSentTargetWord, "_______")
    : (currentSent.sentence || "...");
  const dispEl = document.getElementById("sentDisplay");
  if (dispEl) dispEl.textContent = `"${maskedSentence}"`;

  const cardsContainer = document.getElementById("sentCardsGrid");
  if (!cardsContainer) return;
  cardsContainer.innerHTML = "";

  currentSentWords.forEach((word, idx) => {
    const card = document.createElement("div");
    card.className = "option-card";
    card.id = `sent_card_${idx}`;
    card.innerHTML = `
      <div class="card-top-bar">
        <span class="card-label">OPTION ${String.fromCharCode(65 + idx)}</span>
        <button class="card-audio-btn" title="Dieses Wort vorlesen">🔊</button>
      </div>
      <span class="card-word">${word}</span>
      <span class="card-ipa">${getIPASimple(word)}</span>
    `;
    const audioBtn = card.querySelector(".card-audio-btn");
    if (audioBtn) {
      audioBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        playTTS(word, `Option ${String.fromCharCode(65 + idx)}`);
      });
    }
    card.addEventListener("click", () => checkSentAnswer(idx));
    cardsContainer.appendChild(card);
  });
}

let sentMode = "mc"; // "mc" or "full"

function setSentMode(mode) {
  sentMode = mode;
  const mcBtn = document.getElementById("sentModeMCBtn");
  const fullBtn = document.getElementById("sentModeFullBtn");
  const cardsGrid = document.getElementById("sentCardsGrid");
  const fullContainer = document.getElementById("sentFullContainer");
  const contextBox = document.getElementById("sentContextBox");
  const hintText = document.getElementById("sentHintText");

  if (mcBtn) mcBtn.classList.toggle("active", mode === "mc");
  if (fullBtn) fullBtn.classList.toggle("active", mode === "full");

  if (mode === "full") {
    if (cardsGrid) cardsGrid.classList.add("hidden");
    if (fullContainer) fullContainer.classList.remove("hidden");
    if (hintText) hintText.textContent = "Höre den ganzen Satz und tippe den gesamten Satz ein (oder sprich nach).";
    if (contextBox) contextBox.style.display = "none";
  } else {
    if (cardsGrid) cardsGrid.classList.remove("hidden");
    if (fullContainer) fullContainer.classList.add("hidden");
    if (hintText) hintText.textContent = "Höre den ganzen Satz und wähle das herausgehörte Schlüsselwort.";
    if (contextBox) contextBox.style.display = "block";
  }
}

function nextSentItem(userTriggered = false) {
  if (!exercises.sentences || exercises.sentences.length === 0) return;
  currentSent = exercises.sentences[Math.floor(Math.random() * exercises.sentences.length)];
  sentAttempted = false;

  renderSentCards();

  const inp = document.getElementById("sentFullInput");
  if (inp) inp.value = "";

  const feedback = document.getElementById("sentFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus("Bereit für Satz-Übung.");

  if (userTriggered && autoStart) {
    playSentAudio();
  }
}

function playSentAudio() {
  if (!currentSent || !currentSent.sentence) return;
  playTTS(currentSent.sentence, "Ganzen Satz");
  if (sentMode === "full" && (autoMic || autoStart)) {
    startAutoMic("sentFull");
  }
}

async function checkSentAnswer(chosenIndex) {
  const chosenWord = currentSentWords[chosenIndex];
  const cleanChosen = String(chosenWord || "").toLowerCase().replace(/[.,!?;:]/g, "").trim();
  const cleanTarget = String(currentSentTargetWord || "").toLowerCase().replace(/[.,!?;:]/g, "").trim();
  const isCorrect = (cleanChosen === cleanTarget);

  const cards = document.querySelectorAll("#sentCardsGrid .option-card");
  const feedback = document.getElementById("sentFeedback");

  cards.forEach((card, idx) => {
    card.className = "option-card";
    if (idx === chosenIndex) {
      card.classList.add(isCorrect ? "correct" : "incorrect");
    }
  });

  // Reveal target word in sentence
  document.getElementById("sentDisplay").textContent = `"${currentSent.sentence}"`;

  if (sentAttempted) {
    return;
  }
  sentAttempted = true;

  if (isCorrect) {
    if (feedback) {
      feedback.textContent = `✓ Richtig! Es war '${currentSentTargetWord}'. (+35 XP)`;
      feedback.className = "feedback-banner success";
    }
    announceA11y(`Richtig! Es war ${currentSentTargetWord}. Plus 35 Punkte.`);
    addXP(35);
  } else {
    if (feedback) {
      feedback.textContent = `✗ Falsch. Gesprochen wurde '${currentSentTargetWord}' (du hast '${chosenWord}' gewählt).`;
      feedback.className = "feedback-banner danger";
    }
    announceA11y(`Falsch. Gesprochen wurde ${currentSentTargetWord}, du hast ${chosenWord} gewählt.`);
  }

  handleAdaptiveSNR(isCorrect);

  await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: currentSentTargetWord,
      user_input: chosenWord,
      module: "Satzverständnis",
      category: currentSent.category
    })
  });

  if (autoStart) {
    setTimeout(() => nextSentItem(true), 1800);
  }
}

async function checkSentFullAnswer() {
  if (sentAttempted) return;
  sentAttempted = true;

  const userInput = document.getElementById("sentFullInput")?.value.trim() || "";
  const target = currentSent ? currentSent.sentence : "";

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: target,
      user_input: userInput,
      module: "Sentences_Full",
      category: currentSent ? currentSent.category : "OLSA Ganzsatz"
    })
  });
  const data = await res.json();
  const feedback = document.getElementById("sentFeedback");

  if (feedback) {
    let wordSpansHtml = "";
    if (data.word_results) {
      wordSpansHtml = `<div style="margin-top:0.6rem; display:flex; flex-wrap:wrap; gap:0.4rem; justify-content:center;">` +
        data.word_results.map(w => {
          const bg = w.status === "correct" ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)";
          const border = w.status === "correct" ? "#10B981" : "#EF4444";
          return `<span style="background:${bg}; border:1px solid ${border}; padding:0.25rem 0.6rem; border-radius:6px; font-weight:700; color:white;">${escapeHtml(w.word)}</span>`;
        }).join("") + `</div>`;
    }

    feedback.innerHTML = `<div>${data.message} ${data.is_correct ? "(+50 XP)" : ""}</div>` +
      `<div style="font-size:0.85rem; color:var(--text-muted); margin-top:0.4rem;">Ziel: "${escapeHtml(target)}"</div>` +
      wordSpansHtml;

    feedback.className = `feedback-banner ${data.is_correct ? "success" : "danger"}`;
  }

  announceA11y(data.message);
  handleAdaptiveSNR(data.is_correct);

  if (data.is_correct) {
    addXP(50);
  }

  if (autoStart) {
    setTimeout(() => nextSentItem(true), 2400);
  }
}



// ─── Störschall-Training (Hören im Lärm) ──────────────────────────
let currentNoiseItem = null;
let currentNoiseTargetWord = "";
let noiseAttempted = false;

function nextNoiseItem(userTriggered = false) {
  if (!exercises.monosyllables || exercises.monosyllables.length === 0) return;
  const pool = exercises.monosyllables.filter(item => item.word && !item.word.startsWith("Wort_"));
  const list = pool.length > 0 ? pool : exercises.monosyllables;

  currentNoiseItem = list[Math.floor(Math.random() * list.length)];
  currentNoiseTargetWord = currentNoiseItem.word || currentNoiseItem.target || currentNoiseItem.target_word || "";
  noiseAttempted = false;

  const level = document.getElementById("noiseLevelSelect")?.value || "medium";
  const levelLabels = { easy: "Leicht (+10 dB)", medium: "Mittel (+5 dB)", hard: "Schwer (0 dB)" };
  
  const catEl = document.getElementById("noiseCategory");
  if (catEl) catEl.textContent = `Störschall: ${levelLabels[level] || "Mittel"}`;
  
  const inpEl = document.getElementById("noiseInput");
  if (inpEl) inpEl.value = "";
  
  const feedback = document.getElementById("noiseFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus("Bereit für Störschall-Übung.");

  if (userTriggered && autoStart) {
    playNoiseAudio();
  }
}

async function playNoiseAudio() {
  if (!currentNoiseTargetWord) {
    nextNoiseItem();
  }
  if (!currentNoiseTargetWord && exercises.monosyllables && exercises.monosyllables.length > 0) {
    currentNoiseItem = exercises.monosyllables[Math.floor(Math.random() * exercises.monosyllables.length)];
    currentNoiseTargetWord = currentNoiseItem.word || currentNoiseItem.target || "Baum";
  }
  if (!currentNoiseTargetWord) {
    currentNoiseTargetWord = "Baum";
  }

  const level = document.getElementById("noiseLevelSelect")?.value || "medium";
  const ambientType = document.getElementById("noiseTypeSelect")?.value || "restaurant";
  const vols = { easy: 0.3, medium: 0.55, hard: 0.85 };
  const nVol = vols[level] || 0.55;

  await playTTS(currentNoiseTargetWord, "Störschall-Wort", {
    ambient_noise: true,
    ambient_type: ambientType,
    ambient_volume: nVol,
    mask_noise: false
  });

  if (autoMic || autoStart) {
    startAutoMic("noise");
  }
}

async function stopNoiseAudio() {
  try {
    await fetch("/api/noise/stop", { method: "POST" });
    setStatus("Störschall gestoppt.");
  } catch (e) {}
}
window.stopNoiseAudio = stopNoiseAudio;

async function checkNoiseAnswer() {
  if (noiseAttempted) return;
  noiseAttempted = true;

  const userInput = document.getElementById("noiseInput")?.value.trim() || "";
  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: currentNoiseTargetWord,
      user_input: userInput,
      module: "Störschall",
      category: document.getElementById("noiseLevelSelect")?.value || "Mittel"
    })
  });
  const data = await res.json();
  const feedback = document.getElementById("noiseFeedback");
  if (feedback) {
    feedback.textContent = data.message;
    feedback.className = `feedback-banner ${data.is_correct ? "success" : "danger"}`;
  }
  if (data.is_correct) addXP(35);

  if (autoStart) {
    setTimeout(() => nextNoiseItem(true), 1800);
  }
}

// ─── Auditives Gedächtnis (Merkspanne & Sequenz) ─────────────────
let targetMemoryWords = [];
let selectedMemoryWords = [];
let memoryAttempted = false;
let currentMemorySequenceId = 0;

function nextMemoryItem(userTriggered = false) {
  currentMemorySequenceId++;
  const count = parseInt(document.getElementById("memorySpanSelect")?.value || "4", 10);
  
  let pool = [];
  if (exercises.monosyllables && exercises.monosyllables.length > 0) {
    const validItems = exercises.monosyllables.filter(item => item.word && !item.word.startsWith("Wort_"));
    pool = validItems.length >= count ? validItems : exercises.monosyllables;
  }
  
  if (pool.length === 0) {
    const fallbackWords = ["Baum", "Haus", "Zug", "Brot", "Fisch", "Tisch", "Bett", "Hund", "Mund", "Buch"];
    pool = fallbackWords.map(w => ({ word: w }));
  }

  const shuffled = [...pool].sort(() => 0.5 - Math.random());
  targetMemoryWords = shuffled.slice(0, Math.min(count, shuffled.length)).map(i => i.word || i.target || i);
  selectedMemoryWords = [];
  memoryAttempted = false;

  renderMemoryUI();
  const feedback = document.getElementById("memoryFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus(`Bereit für Merkspannen-Übung (${targetMemoryWords.length} Wörter).`);

  if (userTriggered && autoStart) {
    playMemoryAudio();
  }
}

function renderMemoryUI() {
  const count = targetMemoryWords.length;
  const slotsContainer = document.getElementById("memorySelectedSlots");
  const poolContainer = document.getElementById("memoryPoolGrid");
  if (!slotsContainer || !poolContainer) return;

  slotsContainer.innerHTML = Array.from({ length: count }, (_, idx) => {
    const word = selectedMemoryWords[idx];
    if (word) {
      return `<div class="badge" style="background: rgba(59,130,246,0.25); border: 1px solid var(--primary); padding: 0.5rem 1rem; border-radius: 10px; font-weight: 700; font-size: 1rem; color: white;">
        ${idx + 1}. ${escapeHtml(word)}
      </div>`;
    } else {
      return `<div class="badge" style="background: rgba(255,255,255,0.04); border: 1px dashed var(--panel-border); padding: 0.5rem 1rem; border-radius: 10px; font-weight: 500; font-size: 0.95rem; color: var(--text-muted);">
        ${idx + 1}. ?
      </div>`;
    }
  }).join("");

  const displayPool = [...targetMemoryWords].sort((a, b) => a.localeCompare(b));
  poolContainer.innerHTML = displayPool.map(word => {
    const isSelected = selectedMemoryWords.includes(word);
    return `
      <button class="option-card ${isSelected ? 'incorrect' : ''}" style="padding: 1.1rem; text-align: center; justify-content: center; opacity: ${isSelected ? 0.35 : 1}; color: #FFFFFF !important;" ${isSelected ? 'disabled' : ''} onclick="selectMemoryWord('${escapeHtml(word)}')">
        <span class="card-word" style="font-size: 1.35rem; font-weight: 800; color: #FFFFFF !important; text-align: center; text-shadow: 0 2px 4px rgba(0,0,0,0.6);">${escapeHtml(word)}</span>
      </button>
    `;
  }).join("");
}

function selectMemoryWord(word) {
  if (selectedMemoryWords.length < targetMemoryWords.length && !selectedMemoryWords.includes(word)) {
    selectedMemoryWords.push(word);
    renderMemoryUI();
  }
}
window.selectMemoryWord = selectMemoryWord;

function resetMemorySelection() {
  selectedMemoryWords = [];
  renderMemoryUI();
}

async function playMemoryAudio() {
  if (!targetMemoryWords || targetMemoryWords.length === 0) {
    nextMemoryItem();
  }
  const seqId = ++currentMemorySequenceId;
  setStatus(`Spreche Sequenz von ${targetMemoryWords.length} Wörtern...`);
  for (let i = 0; i < targetMemoryWords.length; i++) {
    if (seqId !== currentMemorySequenceId) return;
    await playTTS(targetMemoryWords[i], `Wort ${i + 1}`, { wait: true });
    if (seqId !== currentMemorySequenceId) return;
    await new Promise(r => setTimeout(r, 650));
  }
  if (seqId === currentMemorySequenceId) {
    setStatus("Sequenz beendet. Wähle die Wörter in der richtigen Reihenfolge!");
  }
}

async function checkMemoryAnswer() {
  if (memoryAttempted) return;
  memoryAttempted = true;

  const targetSeq = targetMemoryWords.join(" ");
  const userSeq = selectedMemoryWords.join(" ");
  const isCorrect = (targetSeq.toLowerCase() === userSeq.toLowerCase());

  await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: targetSeq,
      user_input: userSeq,
      module: "Auditives Gedächtnis",
      category: `${targetMemoryWords.length} Wörter`
    })
  });

  const feedback = document.getElementById("memoryFeedback");
  if (feedback) {
    if (isCorrect) {
      feedback.textContent = `✓ Richtig! Exakte Sequenz: '${targetSeq}' (+45 XP)`;
      feedback.className = "feedback-banner success";
      addXP(45);
    } else {
      feedback.textContent = `✗ Falsch. Richtig war: '${targetSeq}' (Deine Wahl: '${userSeq || "Keine"}')`;
      feedback.className = "feedback-banner danger";
    }
  }

  if (autoStart) {
    setTimeout(() => nextMemoryItem(true), 2200);
  }
}

// Exercise Editor Engine & Database CRUD
let editingItemId = null;
let editingItemType = null;
let editorSearchQuery = "";
let editorSortMode = "az";     // 'az' | 'za' | 'cat'
let editorCurrentPage = 1;
const EDITOR_PAGE_SIZE = 10;
let editorFormDirty = false;

// ── Toast system ──────────────────────────────────────────────
function showToast(msg, type = "info", duration = 3000) {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const icons = { success: "✅", danger: "❌", info: "ℹ️", warning: "⚠️" };
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${msg}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add("fadeout");
    setTimeout(() => el.remove(), 380);
  }, duration);
}

// ── Update filter tab count badges ────────────────────────────
function updateEditorCounts() {
  ["minimal_pairs", "monosyllables", "numbers", "sentences"].forEach(key => {
    const el = document.getElementById(`fcount_${key}`);
    if (el) {
      const n = (exercises[key] || []).length;
      el.textContent = n > 0 ? `(${n})` : "";
    }
  });
}

function switchEditorSubView(viewName, force = false) {
  const listView = document.getElementById("editorListView");
  const formView = document.getElementById("editorFormView");
  const listBtn = document.getElementById("editorViewListBtn");
  const formBtn = document.getElementById("editorViewFormBtn");

  if (viewName === "list") {
    // Warn if form has unsaved changes
    if (!force && editorFormDirty) {
      if (!confirm("Du hast ungespeicherte Änderungen. Wirklich abbrechen?")) return;
    }
    editorFormDirty = false;
    if (listView) listView.classList.remove("hidden");
    if (formView) formView.classList.add("hidden");
    if (listBtn) listBtn.classList.add("active");
    if (formBtn) formBtn.classList.remove("active");
    renderEditorList();
  } else {
    if (listView) listView.classList.add("hidden");
    if (formView) formView.classList.remove("hidden");
    if (listBtn) listBtn.classList.remove("active");
    if (formBtn) formBtn.classList.add("active");
  }
}
window.switchEditorSubView = switchEditorSubView;

function resetEditorForm() {
  editingItemId = null;
  editingItemType = null;
  const titleEl = document.getElementById("formTitle");
  if (titleEl) titleEl.textContent = "➕ Neue Übung hinzufügen";
  const btnEl = document.getElementById("addItemBtn");
  if (btnEl) btnEl.textContent = "💾 Neue Übung in Datenbank speichern";

  const addTypeSelect = document.getElementById("addTypeSelect");
  if (addTypeSelect) addTypeSelect.value = currentEditorView || "minimal_pairs";

  document.getElementById("addCategory").value = "";
  document.getElementById("addSource").value = "";
  document.getElementById("addWordA").value = "";
  document.getElementById("addWordB").value = "";
  document.getElementById("addMPOptions").value = "";
  document.getElementById("addHint").value = "";
  document.getElementById("addESWord").value = "";
  document.getElementById("addNumVal").value = "";
  document.getElementById("addNumSpoken").value = "";
  document.getElementById("addSentText").value = "";
  document.getElementById("addSentTarget").value = "";
  document.getElementById("addSentOptions").value = "";

  const val = addTypeSelect ? addTypeSelect.value : "minimal_pairs";
  document.getElementById("formMP").classList.toggle("hidden", val !== "minimal_pairs");
  document.getElementById("formES").classList.toggle("hidden", val !== "monosyllables");
  document.getElementById("formNum").classList.toggle("hidden", val !== "numbers");
  document.getElementById("formSent").classList.toggle("hidden", val !== "sentences");
}

function openFormForNew() {
  resetEditorForm();
  switchEditorSubView("form");
}

function openFormForEdit(type, idOrItem) {
  let item = null;
  if (typeof idOrItem === "object" && idOrItem !== null) {
    item = idOrItem;
  } else {
    item = (exercises[type] || []).find(i => String(i.id).trim() === String(idOrItem).trim());
  }

  if (!item) {
    console.error("openFormForEdit: Item nicht gefunden", type, idOrItem);
    alert("Eintrag konnte nicht zum Bearbeiten geladen werden.");
    return;
  }

  editingItemId = item.id;
  editingItemType = type;

  const titleEl = document.getElementById("formTitle");
  if (titleEl) titleEl.textContent = `✏️ Übung bearbeiten (ID: ${item.id})`;

  const btnEl = document.getElementById("addItemBtn");
  if (btnEl) btnEl.textContent = "💾 Änderungen speichern";

  const addTypeSelect = document.getElementById("addTypeSelect");
  if (addTypeSelect) addTypeSelect.value = type;

  const formMP = document.getElementById("formMP");
  const formES = document.getElementById("formES");
  const formNum = document.getElementById("formNum");
  const formSent = document.getElementById("formSent");

  if (formMP) formMP.classList.toggle("hidden", type !== "minimal_pairs");
  if (formES) formES.classList.toggle("hidden", type !== "monosyllables");
  if (formNum) formNum.classList.toggle("hidden", type !== "numbers");
  if (formSent) formSent.classList.toggle("hidden", type !== "sentences");

  const categoryInput = document.getElementById("addCategory");
  const sourceInput = document.getElementById("addSource");

  if (categoryInput) categoryInput.value = item.category || item.type || "";
  if (sourceInput) sourceInput.value = item.source || "";

  if (type === "minimal_pairs") {
    const wordAEl = document.getElementById("addWordA");
    const wordBEl = document.getElementById("addWordB");
    const optsEl = document.getElementById("addMPOptions");
    const hintEl = document.getElementById("addHint");

    if (wordAEl) wordAEl.value = item.word_a || "";
    if (wordBEl) wordBEl.value = item.word_b || "";
    if (optsEl) optsEl.value = item.options ? item.options.join(", ") : "";
    if (hintEl) hintEl.value = item.hint || "";

  } else if (type === "monosyllables") {
    const wordEl = document.getElementById("addESWord");
    if (wordEl) wordEl.value = item.word || "";

  } else if (type === "numbers") {
    const numValEl = document.getElementById("addNumVal");
    const numSpokenEl = document.getElementById("addNumSpoken");
    if (numValEl) numValEl.value = item.value || "";
    if (numSpokenEl) numSpokenEl.value = item.spoken || "";

  } else if (type === "sentences") {
    const sentTextEl = document.getElementById("addSentText");
    const sentTargetEl = document.getElementById("addSentTarget");
    const sentOptsEl = document.getElementById("addSentOptions");

    if (sentTextEl) sentTextEl.value = item.sentence || "";
    if (sentTargetEl) sentTargetEl.value = item.target_word || "";
    if (sentOptsEl) sentOptsEl.value = item.options ? item.options.join(", ") : "";
  }

  switchEditorSubView("form");
  setTimeout(() => {
    const editorContainer = document.getElementById("editorFormView");
    if (editorContainer) editorContainer.scrollIntoView({ behavior: 'smooth' });
    if (categoryInput) categoryInput.focus();
  }, 100);
}
window.openFormForEdit = openFormForEdit;

function initEditor() {
  const listBtn = document.getElementById("editorViewListBtn");
  const formBtn = document.getElementById("editorViewFormBtn");
  const newBtn = document.getElementById("newExerciseBtn");
  const cancelFormBtn = document.getElementById("cancelFormBtn");
  const cancelItemBtn = document.getElementById("cancelItemBtn");
  const searchInput = document.getElementById("editorSearchInput");

  if (listBtn) listBtn.addEventListener("click", () => switchEditorSubView("list"));
  if (formBtn) formBtn.addEventListener("click", () => openFormForNew());
  if (newBtn) newBtn.addEventListener("click", () => openFormForNew());
  if (cancelFormBtn) cancelFormBtn.addEventListener("click", () => switchEditorSubView("list"));
  if (cancelItemBtn) cancelItemBtn.addEventListener("click", () => switchEditorSubView("list"));

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    const formView = document.getElementById("editorFormView");
    if (!formView || formView.classList.contains("hidden")) return;
    if (e.key === "Escape") {
      switchEditorSubView("list");
    } else if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      document.getElementById("addItemBtn")?.click();
    }
  });

  // Track form dirty state on any input change
  const editorFormView = document.getElementById("editorFormView");
  if (editorFormView) {
    editorFormView.addEventListener("input", () => { editorFormDirty = true; });
    editorFormView.addEventListener("change", () => { editorFormDirty = true; });
  }

  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      editorSearchQuery = e.target.value.toLowerCase().trim();
      editorCurrentPage = 1; // reset to page 1 on new search
      renderEditorList();
    });
  }

  // Sort buttons
  const sortBtns = document.querySelectorAll(".sort-btn");
  document.getElementById("sortAZ")?.addEventListener("click", () => {
    editorSortMode = "az"; editorCurrentPage = 1;
    sortBtns.forEach(b => b.classList.remove("active"));
    document.getElementById("sortAZ")?.classList.add("active");
    renderEditorList();
  });
  document.getElementById("sortZA")?.addEventListener("click", () => {
    editorSortMode = "za"; editorCurrentPage = 1;
    sortBtns.forEach(b => b.classList.remove("active"));
    document.getElementById("sortZA")?.classList.add("active");
    renderEditorList();
  });
  document.getElementById("sortCat")?.addEventListener("click", () => {
    editorSortMode = "cat"; editorCurrentPage = 1;
    sortBtns.forEach(b => b.classList.remove("active"));
    document.getElementById("sortCat")?.classList.add("active");
    renderEditorList();
  });

  const addTypeSelect = document.getElementById("addTypeSelect");

  function showTypeFields(val) {
    ["formMP", "formES", "formNum", "formSent"].forEach(id => {
      document.getElementById(id)?.classList.add("hidden");
    });
    const map = {
      minimal_pairs: "formMP",
      monosyllables: "formES",
      numbers: "formNum",
      sentences: "formSent",
    };
    const target = map[val];
    if (target) document.getElementById(target)?.classList.remove("hidden");
  }

  if (addTypeSelect) {
    addTypeSelect.addEventListener("change", (e) => showTypeFields(e.target.value));
    showTypeFields(addTypeSelect.value); // initialer Zustand
  }

  document.getElementById("addItemBtn").addEventListener("click", async () => {
    const modType = addTypeSelect.value;
    const category = document.getElementById("addCategory").value.trim() || "Allgemein";
    const sourceVal = document.getElementById("addSource").value.trim() || "Eigenes Übungsmaterial";
    let newItem = { category: category, source: sourceVal };

    if (editingItemId) {
      newItem.id = editingItemId;
    }

    if (modType === "minimal_pairs") {
      const wordA = document.getElementById("addWordA").value.trim();
      const wordB = document.getElementById("addWordB").value.trim();
      const mpOptsRaw = document.getElementById("addMPOptions").value.trim();
      const hint = document.getElementById("addHint").value.trim();

      if (mpOptsRaw) {
        const opts = mpOptsRaw.split(",").map(s => s.trim()).filter(Boolean);
        if (opts.length < 2) {
          showToast("Bitte mindestens 2 Optionen durch Komma getrennt eingeben!", "warning");
          return;
        }
        newItem.options = opts;
        newItem.hint = hint || `Reim-Gruppe (${opts.join(', ')})`;
      } else if (wordA && wordB) {
        newItem.word_a = wordA;
        newItem.word_b = wordB;
        newItem.hint = hint || `Unterscheidung ${wordA} vs ${wordB}`;
      } else {
        showToast("Bitte entweder Wort A & B ODER Mehrfachauswahl-Optionen eingeben!", "warning");
        return;
      }
      newItem.difficulty = "Mittel";

    } else if (modType === "monosyllables") {
      const word = document.getElementById("addESWord").value.trim();
      if (!word) {
        showToast("Bitte Einsilber-Wort eingeben!", "warning");
        return;
      }
      newItem.word = word;
      newItem.difficulty = "Mittel";

    } else if (modType === "numbers") {
      const val = document.getElementById("addNumVal").value.trim();
      const spoken = document.getElementById("addNumSpoken").value.trim();
      if (!val || !spoken) {
        showToast("Bitte Wert und gesprochenen Text eingeben!", "warning");
        return;
      }
      newItem.type = category;
      newItem.value = val;
      newItem.spoken = spoken;
      newItem.difficulty = "Mittel";

    } else if (modType === "sentences") {
      const sentText = document.getElementById("addSentText").value.trim();
      const target = document.getElementById("addSentTarget").value.trim();
      const opts = document.getElementById("addSentOptions").value.split(",").map(s => s.trim()).filter(Boolean);

      if (!sentText || !target) {
        showToast("Bitte Satz und Zielwort eingeben!", "warning");
        return;
      }
      newItem.sentence = sentText;
      newItem.target_word = target;
      newItem.options = opts.length ? opts : [target, "Wort 2", "Wort 3"];
      newItem.hint = "Achte auf das Schlüsselwort im Satz.";
    }

    const isEdit = !!editingItemId;
    const res = await fetch("/api/exercises", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mod_type: modType, item: newItem })
    });

    const data = await res.json();
    editorFormDirty = false;
    showToast(data.message || (isEdit ? "✅ Eintrag aktualisiert!" : "✅ Eintrag gespeichert!"), "success");
    resetEditorForm();
    await loadExercises();
    switchEditorSubView("list", true); // force=true → skip dirty-check
  });

  const filterBtns = document.querySelectorAll(".filter-tab-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentEditorView = btn.dataset.view;
      editorCurrentPage = 1; // reset page on tab switch
      renderEditorList();
    });
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function setEditorPage(p) {
  editorCurrentPage = p;
  renderEditorList();
  const listView = document.getElementById("editorListView");
  if (listView) listView.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
window.setEditorPage = setEditorPage;

function renderEditorList() {
  updateEditorCounts();

  const container = document.getElementById("editorExerciseList");
  const paginationContainer = document.getElementById("editorPagination");
  if (!container) return;

  const rawList = exercises[currentEditorView] || [];

  function getItemText(item, type) {
    if (type === "minimal_pairs") {
      return item.options ? item.options.join(", ") : `${item.word_a || ''} / ${item.word_b || ''}`;
    } else if (type === "monosyllables") {
      return item.word || "";
    } else if (type === "numbers") {
      return `${item.value || ''} (${item.spoken || ''})`;
    } else if (type === "sentences") {
      return item.sentence || "";
    }
    return "";
  }

  // Filter
  let filtered = rawList.filter(item => {
    if (!editorSearchQuery) return true;
    const txt = getItemText(item, currentEditorView).toLowerCase();
    const cat = (item.category || item.type || "").toLowerCase();
    const src = (item.source || "").toLowerCase();
    const hint = (item.hint || "").toLowerCase();
    return txt.includes(editorSearchQuery) || cat.includes(editorSearchQuery) || src.includes(editorSearchQuery) || hint.includes(editorSearchQuery);
  });

  // Sort
  filtered.sort((a, b) => {
    if (editorSortMode === "cat") {
      const catA = (a.category || a.type || "").toLowerCase();
      const catB = (b.category || b.type || "").toLowerCase();
      if (catA !== catB) return catA.localeCompare(catB);
    }
    const txtA = getItemText(a, currentEditorView).toLowerCase();
    const txtB = getItemText(b, currentEditorView).toLowerCase();
    return editorSortMode === "za" ? txtB.localeCompare(txtA) : txtA.localeCompare(txtB);
  });

  const totalItems = filtered.length;
  const totalPages = Math.ceil(totalItems / EDITOR_PAGE_SIZE) || 1;
  if (editorCurrentPage > totalPages) editorCurrentPage = totalPages;
  if (editorCurrentPage < 1) editorCurrentPage = 1;

  const startIdx = (editorCurrentPage - 1) * EDITOR_PAGE_SIZE;
  const pageItems = filtered.slice(startIdx, startIdx + EDITOR_PAGE_SIZE);

  if (pageItems.length === 0) {
    container.innerHTML = `<div style="text-align: center; padding: 2.5rem; color: var(--text-muted);">Keine Übungen in dieser Kategorie/Suche gefunden.</div>`;
  } else {
    container.innerHTML = pageItems.map(item => {
      const mainText = getItemText(item, currentEditorView);
      const cat = item.category || item.type || "Allgemein";
      const src = item.source ? `🏛 ${item.source}` : "";
      const hint = item.hint ? `💡 ${item.hint}` : "";

      const itemJson = escapeHtml(JSON.stringify(item));

      return `
        <div class="exercise-item-card" data-id="${escapeHtml(item.id)}">
          <div class="item-info">
            <div class="item-main">${escapeHtml(mainText)}</div>
            <div class="item-meta">
              <span class="cat-badge">${escapeHtml(cat)}</span>
              ${src ? `<span class="src-badge">${escapeHtml(src)}</span>` : ""}
              ${hint ? `<span class="hint-badge">${escapeHtml(hint)}</span>` : ""}
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-icon-action edit" data-item="${itemJson}" onclick="handleEditClick(this)" title="Bearbeiten">✏️</button>
            <button class="btn-icon-action copy" data-item="${itemJson}" onclick="handleCopyClick(this)" title="Duplizieren">📋</button>
            <button class="btn-icon-action delete" onclick="deleteExerciseItem('${currentEditorView}', '${escapeHtml(item.id)}', this.closest('.exercise-item-card'))" title="Löschen">🗑️</button>
          </div>
        </div>
      `;
    }).join("");
  }

  if (paginationContainer) {
    if (totalPages <= 1) {
      paginationContainer.innerHTML = `<span class="page-info">Gesamt: ${totalItems} Einträge</span>`;
    } else {
      let pageBtns = "";
      for (let p = 1; p <= totalPages; p++) {
        if (p === 1 || p === totalPages || (p >= editorCurrentPage - 2 && p <= editorCurrentPage + 2)) {
          pageBtns += `<button class="page-btn ${p === editorCurrentPage ? 'active' : ''}" onclick="setEditorPage(${p})">${p}</button>`;
        } else if (p === editorCurrentPage - 3 || p === editorCurrentPage + 3) {
          pageBtns += `<span class="page-info">...</span>`;
        }
      }

      paginationContainer.innerHTML = `
        <button class="page-btn" ${editorCurrentPage === 1 ? 'disabled' : ''} onclick="setEditorPage(${editorCurrentPage - 1})">◀ Zurück</button>
        ${pageBtns}
        <button class="page-btn" ${editorCurrentPage === totalPages ? 'disabled' : ''} onclick="setEditorPage(${editorCurrentPage + 1})">Weiter ▶</button>
        <span class="page-info">(${startIdx + 1}–${Math.min(startIdx + EDITOR_PAGE_SIZE, totalItems)} von ${totalItems})</span>
      `;
    }
  }
}
window.renderEditorList = renderEditorList;

function handleEditClick(btn) {
  const item = JSON.parse(btn.dataset.item);
  openFormForEdit(currentEditorView, item);
}
window.handleEditClick = handleEditClick;

function handleCopyClick(btn) {
  const item = JSON.parse(btn.dataset.item);
  duplicateExerciseItem(currentEditorView, item);
}
window.handleCopyClick = handleCopyClick;



function duplicateExerciseItem(type, item) {
  // Open form pre-filled with this item's data, but no ID → will create new
  const copy = { ...item };
  delete copy.id;
  openFormForEdit(type, copy);
  showToast("📋 Kopie erstellt – bitte bearbeiten und speichern.", "info");
}

async function deleteExerciseItem(type, id, cardEl) {
  // Inline two-step confirmation on the button
  const deleteBtn = cardEl ? cardEl.querySelector("button:last-child") : null;
  if (deleteBtn && !deleteBtn.dataset.confirmed) {
    const orig = deleteBtn.innerHTML;
    deleteBtn.innerHTML = "⚠️ Sicher?";
    deleteBtn.style.cssText = "padding:0.3rem 0.6rem; font-size:0.8rem; color:#FBBF24; border-color:#FBBF24; cursor:pointer; font-weight:700;";
    deleteBtn.dataset.confirmed = "1";
    // Reset after 3 seconds if not clicked again
    setTimeout(() => {
      if (deleteBtn.dataset.confirmed) {
        deleteBtn.innerHTML = orig;
        deleteBtn.style.cssText = "padding:0.3rem 0.6rem; font-size:0.8rem; color:#EF4444; border-color:#EF4444; cursor:pointer;";
        delete deleteBtn.dataset.confirmed;
      }
    }, 3000);
    return;
  }
  if (deleteBtn) delete deleteBtn.dataset.confirmed;

  const res = await fetch("/api/exercises", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mod_type: type, item_id: id })
  });

  if (!res.ok) {
    showToast("Fehler beim Löschen!", "danger");
    return;
  }
  showToast("🗑 Eintrag gelöscht.", "warning", 2500);
  await loadExercises();
}
window.deleteExerciseItem = deleteExerciseItem;

let activeMicTab = "es";

function startAutoMic(tabName = "es") {
  if (!autoMic && !autoStart) return;
  activeMicTab = tabName;

  setTimeout(() => {
    try {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) return;

      if (window.globalRec) {
        try { window.globalRec.stop(); } catch (e) { }
      }

      const rec = new SpeechRecognition();
      rec.lang = "de-DE";
      rec.continuous = true;
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      let finalTranscript = "";
      let silenceTimer = null;

      rec.onstart = () => {
        setStatus("🔴 Mikrofon hört zu... Bitte sprechen!");
        triggerWaveform(4.5);
      };

      rec.onresult = (e) => {
        let currentInterim = "";
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const res = e.results[i];
          const text = res[0].transcript.trim();
          if (res.isFinal) {
            finalTranscript += (finalTranscript ? " " : "") + text;
          } else {
            currentInterim = text;
          }
        }

        const bestText = (finalTranscript || currentInterim).trim();
        if (bestText) {
          setStatus(`🔴 Gehört: '${bestText}'`);

          // Update input field live while speaking
          if (activeMicTab === "es") {
            const inputEl = document.getElementById("esInput");
            if (inputEl) inputEl.value = bestText;
          } else if (activeMicTab === "num") {
            const inputEl = document.getElementById("numInput");
            if (inputEl) inputEl.value = bestText;
          } else if (activeMicTab === "noise") {
            const inputEl = document.getElementById("noiseInput");
            if (inputEl) inputEl.value = bestText;
          }

          // Wait 900ms after user stops speaking to allow full word completion (e.g. "lolle")
          clearTimeout(silenceTimer);
          silenceTimer = setTimeout(() => {
            try { rec.stop(); } catch (err) {}
            if (activeMicTab === "es") checkESAnswer();
            else if (activeMicTab === "num") checkNumAnswer();
            else if (activeMicTab === "noise") checkNoiseAnswer();
          }, 900);
        }
      };

      rec.onerror = (e) => {
        console.warn("Speech recognition notice:", e.error);
      };

      window.globalRec = rec;
      rec.start();
    } catch (e) {
      console.warn("Auto mic start notice:", e);
    }
  }, 750);
}

// Browser Web Speech Recognition (Native German Speech-to-Text)
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  const esMicBtn = document.getElementById("esMicBtn");
  if (esMicBtn) {
    esMicBtn.addEventListener("click", () => {
      startAutoMic("es");
    });
  }

  const numMicBtn = document.getElementById("numMicBtn");
  if (numMicBtn) {
    numMicBtn.addEventListener("click", () => {
      startAutoMic("num");
    });
  }

  const noiseMicBtn = document.getElementById("noiseMicBtn");
  if (noiseMicBtn) {
    noiseMicBtn.addEventListener("click", () => {
      startAutoMic("noise");
    });
  }
}

// Canvas Waveform Visualizer
function initCanvasVisualizer() {
  const canvas = document.getElementById("waveformCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function drawIdle() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.moveTo(0, canvas.height / 2);
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 2;
    ctx.stroke();
  }
  drawIdle();
}

function triggerWaveform(durationSec) {
  const canvas = document.getElementById("waveformCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const startTime = Date.now();

  function animate() {
    const elapsed = (Date.now() - startTime) / 1000;
    if (elapsed > durationSec) {
      initCanvasVisualizer();
      return;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();

    const cy = canvas.height / 2;
    for (let x = 0; x < canvas.width; x += 4) {
      const amp = Math.sin(x * 0.03 + elapsed * 10) * Math.cos(x * 0.01) * 16 * (1 - elapsed / durationSec);
      if (x === 0) ctx.moveTo(x, cy + amp);
      else ctx.lineTo(x, cy + amp);
    }

    ctx.strokeStyle = "#3B82F6";
    ctx.lineWidth = 3;
    ctx.shadowBlur = 10;
    ctx.shadowColor = "#3B82F6";
    ctx.stroke();
    ctx.shadowBlur = 0;

    requestAnimationFrame(animate);
  }
  animate();
}

// Stats Dashboard Update
async function updateStats() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();
    renderStatsData(data);
  } catch (e) {
    console.log("Error loading stats:", e);
  }
}

function renderStatsData(data) {
  const statTotal = document.getElementById("statTotal");
  if (statTotal) statTotal.textContent = data.total_attempts || 0;

  const statCorrect = document.getElementById("statCorrect");
  if (statCorrect) statCorrect.textContent = data.correct_attempts || 0;

  const statAccuracy = document.getElementById("statAccuracy");
  if (statAccuracy) statAccuracy.textContent = `${data.accuracy || 0}%`;

  // Render Phonem-Heatmap Grid dynamically
  const heatmapGrid = document.getElementById("phonemHeatmapGrid");
  if (heatmapGrid) {
    heatmapGrid.innerHTML = "";
    const catEntries = Object.entries(data.by_category || {});
    if (catEntries.length === 0) {
      heatmapGrid.innerHTML = "<p style='color:var(--text-muted); font-size:0.9rem; grid-column:1 / -1; padding:0.5rem;'>Noch keine Auswertungsdaten vorhanden. Absolviere erste Übungen!</p>";
    } else {
      for (const [cat, stats] of catEntries) {
        let color = "#EF4444";
        if (stats.accuracy >= 80) color = "#10B981";
        else if (stats.accuracy >= 60) color = "#F59E0B";

        const card = document.createElement("div");
        card.className = "metric-card";
        card.style.borderLeft = `4px solid ${color}`;
        card.innerHTML = `
          <strong>${cat}</strong>
          <span class="val-badge" style="background:${color}; color:white; margin-top:0.3rem;">${stats.accuracy}% (${stats.correct}/${stats.count})</span>
        `;
        heatmapGrid.appendChild(card);
      }
    }
  }

  // Render Module Stats List
  const list = document.getElementById("moduleStatsList");
  if (list) {
    list.innerHTML = "";
    const modEntries = Object.entries(data.by_module || {});
    if (modEntries.length === 0) {
      list.innerHTML = "<p style='color:var(--text-muted); font-size:0.9rem; padding:0.5rem;'>Keine Modul-Statistiken vorhanden.</p>";
    } else {
      for (const [mod, stats] of modEntries) {
        const item = document.createElement("div");
        item.className = "metric-card";
        item.style.marginTop = "0.8rem";
        item.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="font-size:1.1rem; color:#60A5FA;">${mod}</strong>
            <span class="badge" style="background:#1E293B;">${stats.accuracy}% Treffer (${stats.correct}/${stats.count})</span>
          </div>
        `;
        list.appendChild(item);
      }
    }
  }
}

async function resetStats() {
  try {
    const res = await fetch("/api/stats/reset", { method: "POST" });
    const data = await res.json();
    userXP = 0;
    userLevel = 1;
    addXP(0);
    renderStatsData(data.stats || { total_attempts: 0, correct_attempts: 0, accuracy: 0, avg_score: 0, by_module: {}, by_category: {} });
    setStatus("Statistik erfolgreich zurückgesetzt.");
  } catch (e) {
    console.error("Fehler beim Zurücksetzen der Statistik:", e);
  }
}

function setStatus(msg) {
  const el = document.getElementById("statusText");
  if (el) el.textContent = msg;
}

// ── ONLINE HILFE & KEYBOARD HOTKEYS ──────────────────────────────────────────

function initHelpModal() {
  const openBtn = document.getElementById("openHelpBtn");
  const closeBtn = document.getElementById("closeHelpModalBtn");
  const closeFooterBtn = document.getElementById("closeHelpModalFooterBtn");
  const helpModal = document.getElementById("helpModal");

  if (openBtn) openBtn.addEventListener("click", toggleHelpModal);
  if (closeBtn) closeBtn.addEventListener("click", closeHelpModal);
  if (closeFooterBtn) closeFooterBtn.addEventListener("click", closeHelpModal);
  if (helpModal) {
    helpModal.addEventListener("click", (e) => {
      if (e.target === helpModal) closeHelpModal();
    });
  }
}

function toggleHelpModal() {
  const helpModal = document.getElementById("helpModal");
  if (helpModal) {
    helpModal.classList.toggle("hidden");
  }
}

function closeHelpModal() {
  const helpModal = document.getElementById("helpModal");
  if (helpModal) {
    helpModal.classList.add("hidden");
  }
}

function getActiveTab() {
  const activeBtn = document.querySelector(".tab-btn.active");
  return activeBtn ? activeBtn.dataset.tab : "mp";
}

function replayCurrentAudio() {
  const tab = getActiveTab();
  if (tab === "mp") playMPAudio();
  else if (tab === "es") playESAudio();
  else if (tab === "num") playNumAudio();
  else if (tab === "sent" || tab === "sentences") playSentAudio();
  showToast("▶ Audio wird abgespielt", "info");
}

function selectOptionByHotkey(index) {
  const tab = getActiveTab();
  if (tab === "mp") {
    if (currentMPWords && currentMPWords[index]) {
      checkMPAnswer(index);
    }
  } else if (tab === "sent" || tab === "sentences") {
    const opts = document.querySelectorAll("#sentCardsGrid .option-card");
    if (opts && opts[index]) {
      opts[index].click();
    }
  }
}

function nextExerciseItem() {
  const tab = getActiveTab();
  if (tab === "mp") nextMPItem(true);
  else if (tab === "es") nextESItem(true);
  else if (tab === "num") nextNumItem(true);
  else if (tab === "sent" || tab === "sentences") nextSentItem(true);
  showToast("➔ Nächste Übung geladen", "info");
}

function triggerMicRecording() {
  const tab = getActiveTab();
  if (tab === "es") {
    const micBtn = document.getElementById("esMicBtn");
    if (micBtn) micBtn.click();
  } else if (tab === "num") {
    const micBtn = document.getElementById("numMicBtn");
    if (micBtn) micBtn.click();
  }
}

function initKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    const activeEl = document.activeElement;
    const isInput = activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.isContentEditable);

    if (e.key === "Escape") {
      if (isInput) activeEl.blur();
      closeHelpModal();
      return;
    }

    if (isInput) {
      return; // Do not trigger letter/number hotkeys when typing in input fields
    }

    const key = e.key.toLowerCase();

    // H or ? -> Toggle Online Help
    if (key === "h" || e.key === "?") {
      e.preventDefault();
      toggleHelpModal();
      return;
    }

    // Space or P -> Replay Audio
    if (e.code === "Space" || key === "p") {
      e.preventDefault();
      replayCurrentAudio();
      return;
    }

    // 1 -> Option A
    if (e.key === "1") {
      e.preventDefault();
      selectOptionByHotkey(0);
      return;
    }

    // 2 -> Option B
    if (e.key === "2") {
      e.preventDefault();
      selectOptionByHotkey(1);
      return;
    }

    // N or ArrowRight -> Next item
    if (key === "n" || e.key === "ArrowRight") {
      e.preventDefault();
      nextExerciseItem();
      return;
    }

    // M -> Mic Recording
    if (key === "m") {
      e.preventDefault();
      triggerMicRecording();
      return;
    }
  });
}

// ─── Schwachstellen-Training ──────────────────────────────────────
let weaknessExercises = [];
let currentWeaknessIndex = 0;
let currentWeaknessItem = null;
let weaknessAttempted = false;

async function loadWeaknessExercises() {
  const noticeEl = document.getElementById("weaknessNotice");
  if (noticeEl) noticeEl.innerHTML = `<span>🔍 Analysiere Ihre Übungshistorie & Schwachstellen...</span>`;

  try {
    const res = await fetch("/api/exercises/weaknesses");
    const data = await res.json();
    weaknessExercises = data.exercises || [];
    currentWeaknessIndex = 0;

    if (noticeEl) {
      if (data.weak_categories && data.weak_categories.length > 0) {
        noticeEl.innerHTML = `<span>🎯 <strong>${data.weak_categories.length} Schwachstelle(n) identifiziert:</strong> ${escapeHtml(data.weak_categories.join(", "))}. Gezielte Übungen geladen.</span>`;
        noticeEl.style.background = "rgba(239,68,68,0.15)";
        noticeEl.style.borderColor = "rgba(239,68,68,0.4)";
        noticeEl.style.color = "#FCA5A5";
      } else {
        noticeEl.innerHTML = `<span>🌟 Keine gravierenden Schwachstellen (< 60% Trefferquote) gefunden. Diagnose-Katalog mit ausgewogenen Übungen geladen.</span>`;
        noticeEl.style.background = "rgba(16,185,129,0.15)";
        noticeEl.style.borderColor = "rgba(16,185,129,0.4)";
        noticeEl.style.color = "#6EE7B7";
      }
    }

    nextWeaknessItem();
  } catch (e) {
    if (noticeEl) noticeEl.innerHTML = `<span>Fehler beim Laden des Schwachstellentrainings.</span>`;
  }
}

function nextWeaknessItem(userTriggered = false) {
  if (!weaknessExercises || weaknessExercises.length === 0) return;

  currentWeaknessItem = weaknessExercises[currentWeaknessIndex % weaknessExercises.length];
  currentWeaknessIndex++;
  weaknessAttempted = false;

  const area = document.getElementById("weaknessExerciseArea");
  const feedback = document.getElementById("weaknessFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";

  if (!area || !currentWeaknessItem) return;

  const rationale = currentWeaknessItem.rationale || "Gezieltes Hörtraining";
  const modType = currentWeaknessItem.mod_type || "minimal_pairs";

  let inputHtml = "";
  let targetWord = currentWeaknessItem.word || currentWeaknessItem.target_word || currentWeaknessItem.value || "";

  if (modType === "minimal_pairs") {
    const opts = currentWeaknessItem.options || [currentWeaknessItem.word_a, currentWeaknessItem.word_b];
    targetWord = currentWeaknessItem.word_a || opts[0];
    inputHtml = `<div class="cards-grid" style="margin-top:1rem;">` +
      opts.map((opt, idx) => `
        <div class="option-card" onclick="checkWeaknessAnswer('${escapeHtml(opt)}')">
          <span class="card-word">${escapeHtml(opt)}</span>
        </div>
      `).join("") + `</div>`;
  } else if (modType === "sentences") {
    targetWord = currentWeaknessItem.target_word || currentWeaknessItem.sentence;
    const opts = currentWeaknessItem.options || [targetWord, "Wort 2", "Wort 3"];
    inputHtml = `
      <div style="background:rgba(15,23,42,0.6); padding:1rem; border-radius:12px; margin-bottom:1rem; text-align:left; border:1px solid var(--panel-border);">
        <span style="color:var(--text-muted);">Satzkontext:</span>
        <h4 style="font-size:1.3rem; color:white; margin-top:0.3rem;">"${escapeHtml(currentWeaknessItem.sentence)}"</h4>
      </div>
      <div class="cards-grid">` +
      opts.map(opt => `
        <div class="option-card" onclick="checkWeaknessAnswer('${escapeHtml(opt)}')">
          <span class="card-word">${escapeHtml(opt)}</span>
        </div>
      `).join("") + `</div>`;
  } else {
    inputHtml = `
      <div class="input-wrapper" style="max-width:500px; margin:1rem auto 0 auto; display:flex; gap:0.5rem;">
        <input type="text" id="weaknessInput" placeholder="Antwort eingeben..." class="custom-input" style="flex:1;">
        <button class="btn btn-primary" onclick="checkWeaknessAnswer(document.getElementById('weaknessInput').value)">Prüfen</button>
      </div>
    `;
  }

  area.innerHTML = `
    <div style="background:rgba(30,41,59,0.5); padding:1.2rem; border-radius:14px; border:1px solid var(--panel-border);">
      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.8rem;">
        <span class="cat-tag" style="background:rgba(239,68,68,0.2); color:#FCA5A5; border-color:rgba(239,68,68,0.4);">
          ${escapeHtml(rationale)}
        </span>
        <span class="val-badge">${escapeHtml(currentWeaknessItem.category || "Schwachstelle")}</span>
      </div>
      ${inputHtml}
    </div>
  `;

  const inputEl = document.getElementById("weaknessInput");
  if (inputEl) {
    inputEl.addEventListener("keypress", (e) => {
      if (e.key === "Enter") checkWeaknessAnswer(inputEl.value);
    });
  }

  setStatus(`Schwachstellen-Übung bereit (${currentWeaknessItem.category || ""}).`);

  if (userTriggered && autoStart) {
    playWeaknessAudio();
  }
}

function playWeaknessAudio() {
  if (!currentWeaknessItem) return;
  const speechText = currentWeaknessItem.sentence || currentWeaknessItem.word_a || currentWeaknessItem.word || currentWeaknessItem.target_word || currentWeaknessItem.spoken || currentWeaknessItem.value || "";
  playTTS(speechText, "Schwachstellen-Audio");
}

async function checkWeaknessAnswer(userVal) {
  if (weaknessAttempted || !currentWeaknessItem) return;
  weaknessAttempted = true;

  const targetWord = currentWeaknessItem.word_a || currentWeaknessItem.target_word || currentWeaknessItem.word || currentWeaknessItem.value || "";
  const category = currentWeaknessItem.category || "Schwachstelle";

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: targetWord,
      user_input: userVal,
      module: "Schwachstellen",
      category: category
    })
  });
  const data = await res.json();
  const feedback = document.getElementById("weaknessFeedback");

  if (feedback) {
    feedback.textContent = data.message;
    feedback.className = `feedback-banner ${data.is_correct ? "success" : "danger"}`;
  }

  announceA11y(data.message);
  handleAdaptiveSNR(data.is_correct);

  if (data.is_correct) addXP(40);

  if (autoStart) {
    setTimeout(() => nextWeaknessItem(true), 1800);
  }
}
window.checkWeaknessAnswer = checkWeaknessAnswer;


