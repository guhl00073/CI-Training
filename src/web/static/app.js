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
let savedInitialBal = localStorage.getItem("ci_audio_balance");
let audioBalance = savedInitialBal !== null ? parseFloat(savedInitialBal) : 0.0;
if (isNaN(audioBalance)) audioBalance = 0.0;

let savedInitialVol = localStorage.getItem("ci_audio_volume");
let audioVolume = savedInitialVol !== null ? parseFloat(savedInitialVol) : 1.0;
if (isNaN(audioVolume)) audioVolume = 1.0;

let savedInitialNoiseVol = localStorage.getItem("ci_noise_volume");
let noiseVolume = savedInitialNoiseVol !== null ? parseFloat(savedInitialNoiseVol) : 0.4;
if (isNaN(noiseVolume)) noiseVolume = 0.4;

const ipaCache = {};

function getIPASimple(word) {
  if (!word) return "";
  const clean = String(word).trim();
  const norm = clean.toLowerCase();
  if (ipaCache[norm]) return ipaCache[norm];

  // Client-side instant IPA heuristic
  let quickIPA = `[${norm}]`;
  const dict = {
    "pass": "[pas]", "bass": "[bas]", "tasse": "['tasə]", "dasse": "['dasə]",
    "haus": "[haʊ̯s]", "maus": "[maʊ̯s]", "kamm": "[kam]", "komm": "[kɔm]",
    "bus": "[bʊs]", "dach": "[dax]", "fisch": "[fɪʃ]", "brot": "[bʁoːt]",
    "strand": "[ʃtʁant]", "herbst": "[hɛʁpst]", "katze": "['katsə]", "mond": "[moːnt]",
    "zug": "[tsuːk]", "buch": "[buːx]", "schiff": "[ʃɪf]", "sonne": "['zɔnə]",
    "tisch": "[tɪʃ]", "bett": "[bɛt]", "hund": "[hʊnt]"
  };
  if (dict[norm]) {
    quickIPA = dict[norm];
  } else if (norm.startsWith("sch")) {
    quickIPA = `[${norm.replace('sch', 'ʃ')}]`;
  } else if (norm.startsWith("ch")) {
    quickIPA = `[${norm.replace('ch', 'ç')}]`;
  } else if (norm.includes("z")) {
    quickIPA = `[${norm.replace(/z/g, 't͡s')}]`;
  }
  ipaCache[norm] = quickIPA;

  // Asynchronously query authoritative phonetic IPA from backend
  fetch(`/api/ipa?word=${encodeURIComponent(clean)}`)
    .then(r => r.json())
    .then(data => {
      if (data && data.ipa && data.ipa !== "[-]") {
        ipaCache[norm] = data.ipa;
        document.querySelectorAll(".option-card, .card").forEach(card => {
          const wEl = card.querySelector(".card-word");
          const ipaEl = card.querySelector(".card-ipa");
          if (wEl && ipaEl && wEl.textContent.trim().toLowerCase() === norm) {
            ipaEl.textContent = data.ipa;
            if (data.hint) {
              ipaEl.title = `${data.place}: ${data.hint}`;
            }
          }
        });
      }
    })
    .catch(() => {});

  return quickIPA;
}
let savedInitialRate = localStorage.getItem("ci_audio_rate");
let audioRate = savedInitialRate !== null ? parseFloat(savedInitialRate) : 1.0;
if (isNaN(audioRate)) audioRate = 1.0;
let maskNoise = false;
let ambientNoise = false;
let ambientVolume = 0.4;
let selectedAmbientType = "noise";

let selectedVoice = "Anna";
let selectedMPCategory = "ALL";
let selectedESCategory = "ALL";
let selectedNumCategory = "ALL";
let selectedSentCategory = "ALL";
let selectedFreqFilter = "none";
let currentEditorView = "minimal_pairs";
let autoStart = false;
let autoMic = true;
let adaptiveSNR = false;
let mpDelayReveal = localStorage.getItem("ci_mp_delay_reveal") === "true";
let mpAudioFinished = true;
let mpRevealTimer = null;
let sentDelayReveal = localStorage.getItem("ci_sent_delay_reveal") === "true";
let sentAudioFinished = true;
let sentRevealTimer = null;
let correctStreak = 0;
let autostartSuccessDelay = parseFloat(localStorage.getItem("ci_autostart_success_delay") || "1.8");
let autostartErrorDelay = parseFloat(localStorage.getItem("ci_autostart_error_delay") || "5.0");

function announceA11y(text) {
  const el = document.getElementById("a11yAnnouncer");
  if (el) {
    el.textContent = "";
    setTimeout(() => { el.textContent = text; }, 50);
  }
}

function handleAdaptiveSNR(isCorrect) {
  if (!adaptiveSNR || !maskNoise) {
    correctStreak = 0;
    return;
  }
  if (isCorrect) {
    correctStreak++;
    if (correctStreak >= 3) {
      noiseVolume = Math.min(0.85, Math.round((noiseVolume + 0.05) * 100) / 100);
      correctStreak = 0;
      updateNoiseVolumeUI(noiseVolume);
      syncNoiseConfig();
      showToast(`🎯 Adaptive SNR: Störschall auf ${Math.round(noiseVolume * 100)}% erhöht!`, "info");
    }
  } else {
    correctStreak = 0;
    noiseVolume = Math.max(0.10, Math.round((noiseVolume - 0.05) * 100) / 100);
    updateNoiseVolumeUI(noiseVolume);
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
  initCollapsibleSections();
  initCanvasVisualizer();
  initTabs();
  initEditor();
  await initProfileManagement();
  if (!exercises.minimal_pairs || exercises.minimal_pairs.length === 0) {
    await loadExercises(window.currentLanguage || "de");
  }
  initSpeechRecognition();
  initHelpModal();
  initExitButton();
  initKeyboardShortcuts();
  initAutostartStopButtons();
  initOLSA();
  initAudiogram();
  initVocoderControls();
  initCalibrationWizard();
  updateStats();
  syncNoiseConfig();
});

const SNR_VOLUMES = {
  easy: 0.28,       // +10 dB SNR (Sprache 10dB lauter als Lärm)
  medium: 0.52,     // +5 dB SNR (Sprache 5dB lauter als Lärm)
  hard: 0.80,       // 0 dB SNR (Sprache und Lärm gleich laut)
  very_hard: 1.05   // -5 dB SNR (Lärm lauter als Sprache)
};

let isNoiseManuallyStopped = false;

async function syncNoiseConfig() {
  const currentTab = document.querySelector(".tab-btn.active")?.dataset.tab;
  const isNoiseTab = currentTab === "noise";
  const noiseType = document.getElementById("noiseTypeSelect")?.value || "restaurant";
  const level = document.getElementById("noiseLevelSelect")?.value || "medium";
  const noiseVol = SNR_VOLUMES[level] || 0.52;

  try {
    await fetch("/api/noise/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mask_noise: maskNoise,
        ambient_noise: isNoiseTab ? !isNoiseManuallyStopped : ambientNoise,
        ambient_type: noiseType,
        balance: audioBalance,
        noise_volume: noiseVolume,
        ambient_volume: noiseVol
      })
    });
  } catch (e) {
    console.error("Fehler beim Synchronisieren der Rauscheinstellungen:", e);
  }
}

window.currentLanguage = "de";

async function loadVoices(lang = (window.currentLanguage || "de")) {
  const voiceSelect = document.getElementById("voiceSelect");
  if (!voiceSelect) return;
  try {
    const res = await fetch(`/api/voices?lang=${lang}`);
    const voices = await res.json();
    if (Array.isArray(voices) && voices.length > 0) {
      const curVal = selectedVoice || voiceSelect.value || (lang === "en" ? "Edge-EN-Ava" : "Anna");
      voiceSelect.innerHTML = "";

      const sysGroup = document.createElement("optgroup");
      sysGroup.label = lang === "en" ? "💻 English System Voices" : "💻 System-Stimmen (Auf diesem Computer)";

      const edgeGroup = document.createElement("optgroup");
      edgeGroup.label = lang === "en" ? "🌐 Microsoft Azure Neural (US/UK Studio)" : "🌐 Microsoft Azure Neural (Online Studio)";

      const googleGroup = document.createElement("optgroup");
      googleGroup.label = "🌐 Google Cloud (Online KI)";

      let foundMatch = false;
      voices.forEach(v => {
        const opt = document.createElement("option");
        opt.value = v.id;
        opt.textContent = v.name;
        if (v.id === curVal || v.name === curVal) {
          opt.selected = true;
          foundMatch = true;
        }
        if (v.source === "edge") {
          edgeGroup.appendChild(opt);
        } else if (v.source === "google") {
          googleGroup.appendChild(opt);
        } else {
          sysGroup.appendChild(opt);
        }
      });

      if (sysGroup.children.length > 0) voiceSelect.appendChild(sysGroup);
      if (edgeGroup.children.length > 0) voiceSelect.appendChild(edgeGroup);
      if (googleGroup.children.length > 0) voiceSelect.appendChild(googleGroup);

      if (foundMatch) {
        voiceSelect.value = curVal;
      } else if (voiceSelect.options.length > 0) {
        voiceSelect.selectedIndex = 0;
        selectedVoice = voiceSelect.value;
      }
    }
  } catch (err) {
    console.warn("Voices fetch error:", err);
  }
}

window.loadVoices = loadVoices;

async function setLanguage(lang) {
  window.currentLanguage = lang;
  const btnDE = document.getElementById("langBtnDE");
  const btnEN = document.getElementById("langBtnEN");
  if (btnDE) btnDE.classList.toggle("active", lang === "de");
  if (btnEN) btnEN.classList.toggle("active", lang === "en");

  if (activeProfile) {
    activeProfile.exercise_lang = lang;
    if (lang === "en") {
      selectedVoice = activeProfile.voice_en || "Edge-EN-Ava";
    } else {
      selectedVoice = activeProfile.voice || "Anna";
    }
  }

  await loadVoices(lang);
  await loadExercises(lang);
  debouncedSaveActiveProfileAudio();
}

window.setLanguage = setLanguage;

// Load Exercises from API
async function loadExercises(lang = (window.currentLanguage || "de")) {
  try {
    const res = await fetch(`/api/exercises?lang=${lang}`);
    exercises = await res.json();
    populateMPCategorySelect();
    populateESCategorySelect();
    populateMSCategorySelect();
    populateNumCategorySelect();
    populateSentCategorySelect();
    updateCategoryDatalist();
    nextMPItem();
    nextESItem();
    nextMSItem();
    nextNumItem();
    nextSentItem();
    nextNoiseItem();
    nextMemoryItem();
    renderEditorList();
    updateEditorCounts();
    setStatus(`System bereit. ${lang === 'en' ? 'Englische' : 'Deutsche'} Datensätze geladen.`);
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
  if (volSlider) {
    volSlider.value = audioVolume;
    if (volVal) volVal.textContent = `${Math.round(audioVolume * 100)}%`;
    volSlider.addEventListener("input", (e) => {
      audioVolume = parseFloat(e.target.value);
      if (isNaN(audioVolume)) audioVolume = 1.0;
      localStorage.setItem("ci_audio_volume", audioVolume.toString());
      if (volVal) volVal.textContent = `${Math.round(audioVolume * 100)}%`;
      debouncedSaveActiveProfileAudio();
    });
  }

  const rateSlider = document.getElementById("rateSlider");
  const rateVal = document.getElementById("rateVal");
  if (rateSlider) {
    rateSlider.value = audioRate;
    if (rateVal) rateVal.textContent = `${audioRate.toFixed(1)}x`;
    rateSlider.addEventListener("input", (e) => {
      audioRate = parseFloat(e.target.value);
      if (isNaN(audioRate)) audioRate = 1.0;
      localStorage.setItem("ci_audio_rate", audioRate.toString());
      if (rateVal) rateVal.textContent = `${audioRate.toFixed(1)}x`;
      debouncedSaveActiveProfileAudio();
    });
  }

  const voiceSelect = document.getElementById("voiceSelect");
  if (voiceSelect) {
    selectedVoice = voiceSelect.value || (window.currentLanguage === "en" ? "Edge-EN-Ava" : "Anna");
    voiceSelect.addEventListener("change", (e) => {
      selectedVoice = e.target.value;
      if (activeProfile) {
        if (window.currentLanguage === "en") {
          activeProfile.voice_en = selectedVoice;
        } else {
          activeProfile.voice = selectedVoice;
        }
      }
      setStatus(`Stimme gewechselt: ${selectedVoice}`);
      debouncedSaveActiveProfileAudio();
    });

    loadVoices(window.currentLanguage || "de");
  }

  const testVoiceBtn = document.getElementById("testVoiceBtn");
  if (testVoiceBtn) {
    testVoiceBtn.addEventListener("click", () => {
      const v = selectedVoice || document.getElementById("voiceSelect")?.value || "Anna";
      const sampleText = "Das ist eine Probeaufnahme für dein Cochlea-Implantat Hörtraining mit optimaler Sprachdynamik.";
      playTTS(sampleText, "Stimmprobe", { voice: v });
      showToast(`🔊 Stimmprobe für „${v}“ wird abgespielt...`, "info");
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
      debouncedSaveActiveProfileAudio();
    });
  }

  let syncNoiseTimer = null;
  function debouncedSyncNoiseConfig(delay = 120) {
    clearTimeout(syncNoiseTimer);
    syncNoiseTimer = setTimeout(() => {
      syncNoiseConfig();
    }, delay);
  }

  const maskVolSlider = document.getElementById("maskVolSlider");
  const maskVolVal = document.getElementById("maskVolVal");
  const noiseVolSlider = document.getElementById("noiseVolSlider");
  const noiseVolVal = document.getElementById("noiseVolVal");

  function updateNoiseVolumeUI(vol) {
    noiseVolume = vol;
    if (isNaN(noiseVolume)) noiseVolume = 0.4;
    localStorage.setItem("ci_noise_volume", noiseVolume.toString());
    const volPct = `${Math.round(noiseVolume * 100)}%`;
    if (maskVolVal) maskVolVal.textContent = volPct;
    if (noiseVolVal) noiseVolVal.textContent = volPct;
    if (maskVolSlider) maskVolSlider.value = noiseVolume;
    if (noiseVolSlider) noiseVolSlider.value = noiseVolume;
  }

  updateNoiseVolumeUI(noiseVolume);

  if (maskVolSlider) {
    maskVolSlider.addEventListener("input", (e) => {
      updateNoiseVolumeUI(parseFloat(e.target.value));
      debouncedSyncNoiseConfig(120);
      debouncedSaveActiveProfileAudio();
    });
  }

  if (noiseVolSlider) {
    noiseVolSlider.addEventListener("input", (e) => {
      updateNoiseVolumeUI(parseFloat(e.target.value));
      debouncedSyncNoiseConfig(120);
      debouncedSaveActiveProfileAudio();
    });
  }

  const segBtns = document.querySelectorAll(".segmented-control .seg-btn[data-bal]");
  
  // Set initial UI state from current audioBalance
  segBtns.forEach(btn => {
    const bBal = parseFloat(btn.dataset.bal);
    btn.classList.toggle("active", bBal === audioBalance);
  });
  const balVal = document.getElementById("balVal");
  if (balVal) {
    if (audioBalance === -1.0) balVal.textContent = "Nur Links (CI)";
    else if (audioBalance === 1.0) balVal.textContent = "Nur Rechts (CI)";
    else balVal.textContent = "Beide Ohren";
  }

  segBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      segBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      audioBalance = parseFloat(btn.dataset.bal);
      if (isNaN(audioBalance)) audioBalance = 0.0;
      localStorage.setItem("ci_audio_balance", audioBalance.toString());

      if (balVal) {
        if (audioBalance === -1.0) balVal.textContent = "Nur Links (CI)";
        else if (audioBalance === 1.0) balVal.textContent = "Nur Rechts (CI)";
        else balVal.textContent = "Beide Ohren";
      }

      syncNoiseConfig();
      debouncedSaveActiveProfileAudio();
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
      debouncedSaveActiveProfileAudio();
    });
  }

  const autostartSuccessSlider = document.getElementById("autostartSuccessSlider");
  const autostartSuccessVal = document.getElementById("autostartSuccessVal");
  if (autostartSuccessSlider) {
    autostartSuccessSlider.addEventListener("input", (e) => {
      if (autostartSuccessVal) autostartSuccessVal.textContent = `${parseFloat(e.target.value).toFixed(1)}s`;
      debouncedSaveActiveProfileAudio();
    });
  }

  const autostartErrorSlider = document.getElementById("autostartErrorSlider");
  const autostartErrorVal = document.getElementById("autostartErrorVal");
  if (autostartErrorSlider) {
    autostartErrorSlider.addEventListener("input", (e) => {
      if (autostartErrorVal) autostartErrorVal.textContent = `${parseFloat(e.target.value).toFixed(1)}s`;
      debouncedSaveActiveProfileAudio();
    });
  }

  autoStart = localStorage.getItem("ci_autostart") === "true";
  autoMic = localStorage.getItem("ci_automic") !== "false";
  adaptiveSNR = localStorage.getItem("ci_adaptive_snr") === "true";

  const autoStartToggle = document.getElementById("autoStartToggle");
  if (autoStartToggle) {
    autoStartToggle.addEventListener("change", (e) => setAutoStart(e.target.checked));
  }
  const autoMicToggle = document.getElementById("autoMicToggle");
  if (autoMicToggle) {
    autoMicToggle.addEventListener("change", (e) => {
      setAutoMic(e.target.checked);
      debouncedSaveActiveProfileAudio();
    });
  }

  const adaptiveSNRToggle = document.getElementById("adaptiveSNRToggle");
  const adaptiveSNRVal = document.getElementById("adaptiveSNRVal");
  if (adaptiveSNRToggle) {
    adaptiveSNRToggle.addEventListener("change", (e) => {
      adaptiveSNR = e.target.checked;
      correctStreak = 0;
      localStorage.setItem("ci_adaptive_snr", adaptiveSNR ? "true" : "false");
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
      debouncedSaveActiveProfileAudio();
    });
  }

  // Autostart Duration Sliders
  const successSlider = document.getElementById("autostartSuccessSlider");
  const successVal = document.getElementById("autostartSuccessVal");
  if (successSlider && successVal) {
    successSlider.value = autostartSuccessDelay;
    successVal.textContent = `${autostartSuccessDelay.toFixed(1)}s`;
    successSlider.addEventListener("input", (e) => {
      autostartSuccessDelay = parseFloat(e.target.value);
      successVal.textContent = `${autostartSuccessDelay.toFixed(1)}s`;
      localStorage.setItem("ci_autostart_success_delay", autostartSuccessDelay.toString());
    });
  }

  const errorSlider = document.getElementById("autostartErrorSlider");
  const errorVal = document.getElementById("autostartErrorVal");
  if (errorSlider && errorVal) {
    errorSlider.value = autostartErrorDelay;
    errorVal.textContent = `${autostartErrorDelay.toFixed(1)}s`;
    errorSlider.addEventListener("input", (e) => {
      autostartErrorDelay = parseFloat(e.target.value);
      errorVal.textContent = `${autostartErrorDelay.toFixed(1)}s`;
      localStorage.setItem("ci_autostart_error_delay", autostartErrorDelay.toString());
    });
  }

  document.querySelectorAll(".auto-start-check").forEach(chk => {
    chk.addEventListener("change", (e) => setAutoStart(e.target.checked));
  });
  document.querySelectorAll(".auto-mic-check").forEach(chk => {
    chk.addEventListener("change", (e) => setAutoMic(e.target.checked));
  });

  const delayCheck = document.getElementById("mpDelayRevealCheck");
  if (delayCheck) {
    delayCheck.checked = mpDelayReveal;
    delayCheck.addEventListener("change", (e) => {
      mpDelayReveal = e.target.checked;
      localStorage.setItem("ci_mp_delay_reveal", mpDelayReveal ? "true" : "false");
      if (mpDelayReveal) {
        if (!mpAttempted) hideMPCards();
      } else {
        revealMPCards();
      }
    });
  }

  const sentDelayCheck = document.getElementById("sentDelayRevealCheck");
  if (sentDelayCheck) {
    sentDelayCheck.checked = sentDelayReveal;
    sentDelayCheck.addEventListener("change", (e) => {
      sentDelayReveal = e.target.checked;
      localStorage.setItem("ci_sent_delay_reveal", sentDelayReveal ? "true" : "false");
      if (sentDelayReveal && sentMode === "mc") {
        if (!sentAttempted) hideSentCards();
      } else {
        revealSentCards();
      }
    });
  }

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

  const adaptiveSNRToggle = document.getElementById("adaptiveSNRToggle");
  const adaptiveSNRVal = document.getElementById("adaptiveSNRVal");
  if (adaptiveSNRToggle) adaptiveSNRToggle.checked = adaptiveSNR;
  if (adaptiveSNRVal) adaptiveSNRVal.textContent = adaptiveSNR ? "Ein" : "Aus";

  if (autoStart) {
    document.body.classList.add("autostart-enabled");
  } else {
    document.body.classList.remove("autostart-enabled");
  }

  document.querySelectorAll(".btn-stop-autostart, .autostart-only-btn").forEach(btn => {
    btn.disabled = !autoStart;
    btn.title = autoStart 
      ? "Autostart pausieren / Audio anhalten (Taste X)" 
      : "Autostart ist nicht aktiv (Pause inaktiv)";
  });

  document.querySelectorAll(".auto-start-check").forEach(chk => {
    chk.checked = autoStart;
  });
  document.querySelectorAll(".auto-mic-check").forEach(chk => {
    chk.checked = autoMic;
  });
}

function setAutoStart(val) {
  autoStart = val;
  localStorage.setItem("ci_autostart", autoStart ? "true" : "false");
  updateAutoStartUI();
  debouncedSaveActiveProfileAudio();
}

function setAutoMic(val) {
  autoMic = val;
  localStorage.setItem("ci_automic", autoMic ? "true" : "false");
  updateAutoStartUI();
  debouncedSaveActiveProfileAudio();
}

const TAB_NAMES = {
  mp: { name: "Minimalpaare", icon: "🎭" },
  es: { name: "Freiburger Einsilber (DIN 45621)", icon: "🔤" },
  ms: { name: "Mehrsilber & Komposita", icon: "📚" },
  num: { name: "Zahlen & Uhrzeiten", icon: "🔢" },
  sent: { name: "Satzverständnis", icon: "💬" },
  olsa: { name: "OLSA (SRT)", icon: "🎯" },
  audiogram: { name: "DIN-Audiogramm", icon: "📈" },
  noise: { name: "Störschall-Training", icon: "🌊" },
  memory: { name: "Auditiv. Gedächtnis", icon: "🧠" },
  weakness: { name: "Schwachstellen", icon: "🎯" },
  stats: { name: "Statistik & Heatmap", icon: "📊" },
  editor: { name: "Übungs-Editor", icon: "✏️" }
};

function updateActiveTabBadges(tabId) {
  const meta = TAB_NAMES[tabId] || { name: tabId, icon: "🎯" };
  const badge = document.getElementById("activeTabSummaryBadge");
  const dialogSummary = document.getElementById("mainDialogTitleSummary");
  if (badge) {
    badge.textContent = `${meta.icon} ${meta.name}`;
  }
  if (dialogSummary) {
    dialogSummary.textContent = `🎯 Trainingsbereich: ${meta.name}`;
  }
}

function initCollapsibleSections() {
  const sectionIds = ["controlPanelDetails", "visualizerDetails", "navTabsDetails", "mainDialogDetails"];
  sectionIds.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const savedState = localStorage.getItem("ci_collapsible_" + id);
    if (savedState !== null) {
      el.open = (savedState === "true");
    }
    el.addEventListener("toggle", () => {
      localStorage.setItem("ci_collapsible_" + id, el.open ? "true" : "false");
    });
  });
}

function switchTab(tabId) {
  cancelAutoAdvance();
  const tabs = document.querySelectorAll(".tab-btn");
  const contents = document.querySelectorAll(".tab-content");
  tabs.forEach(t => t.classList.remove("active"));
  contents.forEach(c => c.classList.remove("active"));

  const targetTab = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
  const targetContent = document.getElementById(`tab-${tabId}`);
  if (targetTab) targetTab.classList.add("active");
  if (targetContent) targetContent.classList.add("active");

  updateActiveTabBadges(tabId);

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

      updateActiveTabBadges(btn.dataset.tab);

      if (btn.dataset.tab !== "noise" && !maskNoise) {
        stopNoiseAudio();
      }

      if (btn.dataset.tab === "weakness") loadWeaknessExercises();
      if (btn.dataset.tab === "stats") updateStats();
      if (btn.dataset.tab === "editor") renderEditorList();
      if (btn.dataset.tab === "olsa") {
        if (olsaHistory && olsaHistory.length > 0) drawOLSAStaircase(olsaHistory, olsaReversals);
      }
      if (btn.dataset.tab === "audiogram") {
        renderAudiogramPlot();
      }
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

  document.getElementById("msPlayBtn")?.addEventListener("click", playMSAudio);
  document.getElementById("msCheckBtn")?.addEventListener("click", checkMSAnswer);
  document.getElementById("msNextBtn")?.addEventListener("click", () => nextMSItem(true));
  document.getElementById("msInput")?.addEventListener("keypress", (e) => { if (e.key === "Enter") checkMSAnswer(); });

  const esModeSel = document.getElementById("esModeSelect");
  const esListSel = document.getElementById("esTestListSelect");
  const esListContainer = document.getElementById("esListSelectorContainer");

  if (esModeSel) {
    esModeSel.addEventListener("change", (e) => {
      esMode = e.target.value;
      const catContainer = document.getElementById("esCategoryContainer");
      if (esMode === "test_list") {
        if (catContainer) catContainer.style.display = "none";
        if (esListContainer) esListContainer.style.display = "inline-flex";
        startFreiburgerTestList(parseInt(esListSel ? esListSel.value : 1));
      } else {
        if (catContainer) catContainer.style.display = "inline-flex";
        if (esListContainer) esListContainer.style.display = "none";
        const banner = document.getElementById("esTestProgressBanner");
        if (banner) banner.style.display = "none";
        const resCard = document.getElementById("esTestResultCard");
        if (resCard) resCard.classList.add("hidden");
        nextESItem(false);
      }
      setPlayBtnState("esPlayBtn", false, "Wiederholen");
    });
  }

  if (esListSel) {
    esListSel.addEventListener("change", (e) => {
      startFreiburgerTestList(parseInt(e.target.value));
      setPlayBtnState("esPlayBtn", false, "Wiederholen");
    });
  }

  document.getElementById("esTestRestartBtn")?.addEventListener("click", () => {
    startFreiburgerTestList(currentTestListNum);
    setPlayBtnState("esPlayBtn", false, "Wiederholen");
  });

  document.getElementById("esTestNextListBtn")?.addEventListener("click", () => {
    const totalLists = freiburgerTestLists ? Object.keys(freiburgerTestLists).length : 20;
    const nextListNum = (currentTestListNum % totalLists) + 1;
    if (esListSel) esListSel.value = nextListNum.toString();
    startFreiburgerTestList(nextListNum);
    setPlayBtnState("esPlayBtn", false, "Wiederholen");
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
  document.getElementById("memorySpanSelect")?.addEventListener("change", () => nextMemoryItem(false));

  const mpCatSelect = document.getElementById("mpCategorySelect");
  if (mpCatSelect) {
    mpCatSelect.addEventListener("change", (e) => {
      selectedMPCategory = e.target.value;
      nextMPItem(false);
    });
  }

  const esCatSelect = document.getElementById("esCategorySelect");
  if (esCatSelect) {
    esCatSelect.addEventListener("change", (e) => {
      selectedESCategory = e.target.value;
      nextESItem(false);
    });
  }

  const msCatSelect = document.getElementById("msCategorySelect");
  if (msCatSelect) {
    msCatSelect.addEventListener("change", (e) => {
      selectedMSCategory = e.target.value;
      nextMSItem(false);
    });
  }

  const numCatSelect = document.getElementById("numCategorySelect");
  if (numCatSelect) {
    numCatSelect.addEventListener("change", (e) => {
      selectedNumCategory = e.target.value;
      nextNumItem(false);
    });
  }

  const sentCatSelect = document.getElementById("sentCategorySelect");
  if (sentCatSelect) {
    sentCatSelect.addEventListener("change", (e) => {
      selectedSentCategory = e.target.value;
      nextSentItem(false);
    });
  }

  document.getElementById("noiseLevelSelect")?.addEventListener("change", () => {
    isNoiseManuallyStopped = false;
    syncNoiseConfig();
    setPlayBtnState("noisePlayBtn", false, "Wiederholen");
  });

  document.getElementById("noiseTypeSelect")?.addEventListener("change", () => {
    isNoiseManuallyStopped = false;
    syncNoiseConfig();
    setPlayBtnState("noisePlayBtn", false, "Wiederholen");
  });

  document.getElementById("mpAddCustomBtn")?.addEventListener("click", () => openEditorForType("minimal_pairs"));
  document.getElementById("esAddCustomBtn")?.addEventListener("click", () => openEditorForType("monosyllables"));
  document.getElementById("numAddCustomBtn")?.addEventListener("click", () => openEditorForType("numbers"));
  document.getElementById("sentAddCustomBtn")?.addEventListener("click", () => openEditorForType("sentences"));

  document.getElementById("refreshStatsBtn")?.addEventListener("click", updateStats);
  const resetStatsBtn = document.getElementById("resetStatsBtn");
  if (resetStatsBtn) {
    resetStatsBtn.addEventListener("click", async () => {
      if (confirm("Möchtest du die gesamte Trainings-Statistik wirklich zurücksetzen?")) {
        await resetStats();
      }
    });
  }
  initTrainingLogsListeners();
}

// Dynamic Button State Helper (Start -> Wiederholen)
function setPlayBtnState(btnId, hasPlayed, repeatText = "Wiederholen") {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  if (hasPlayed) {
    btn.innerHTML = `<span class="icon">🔄</span> ${repeatText}`;
    btn.setAttribute("title", `${repeatText} (Leertaste oder P)`);
  } else {
    btn.innerHTML = `<span class="icon">▶</span> Start`;
    btn.setAttribute("title", `Audio abspielen / Start (Leertaste oder P)`);
  }
}

// Estimate speech duration based on text length, syllable count and audio rate
function estimateSpeechDurationMs(text, rate = 1.0) {
  if (!text) return 1000;
  const str = String(text).trim();
  const wordCount = str.split(/\s+/).length;
  const vowelMatches = str.match(/[aeiouyäöüáéíóú]+/gi);
  const approxSyllables = vowelMatches ? vowelMatches.length : Math.max(1, Math.round(str.length / 3));
  
  const syllableTime = approxSyllables * 280;
  const wordTime = wordCount * 220;
  const ms = (Math.max(syllableTime, wordTime) + 550) / (rate || 1.0);
  return Math.max(900, Math.min(8000, Math.round(ms)));
}

// Play Audio via API & Trigger Visualizer Wave
async function playTTS(text, labelName = "Audio", options = {}) {
  if (!text) return;
  const statusMsg = maskNoise && audioBalance !== 0.0 ? `▶ Spiele ${labelName}... (Vertäubung aktiv)` : `▶ Spiele ${labelName}...`;
  setStatus(statusMsg);

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
    vocoder_enabled: vocoderEnabled,
    vocoder_profile: document.getElementById("vocoderProfileSelect")?.value || "ab_16",
    vocoder_carrier: "sine",
    wait: options.wait !== undefined ? options.wait : false
  };

  try {
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data && data.file) {
      visualizeAudioFile(`/api/audio/${data.file}`).catch(() => {});
    } else {
      triggerWaveform(2.0);
    }
  } catch (e) {
    setStatus("Fehler bei Audio-Synthese.");
  }
}

function isAutoStartActive(tabName = "es") {
  const chk = document.getElementById(`${tabName}AutoStartCheck`);
  if (chk) return chk.checked;
  return autoStart || false;
}

function isAutoMicActive(tabName = "es") {
  const chk = document.getElementById(`${tabName}AutoMicCheck`);
  if (chk) return chk.checked;
  return autoMic || false;
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

// ─── Universal Category & Custom Entries Management ───────────────────────────
function isCustomEntry(item, modType = "") {
  if (!item) return false;
  const standardSources = [
    "Marburger Minimalpaar-Katalog",
    "Logopädischer Minimalpaar-Katalog",
    "Freiburger Einsilber-Test (DIN 45621)",
    "Freiburger Einsilber-Test",
    "Audiologischer Zahlen- & Uhrzeitentest",
    "Oldenburger Satztest (OLSA)",
    "DIN 45621"
  ];
  if (item.source && (item.source.includes("Eigenes") || item.source.includes("Benutzer") || item.source.includes("Eigene") || item.source.includes("Custom") || item.source.includes("Import"))) return true;
  if (item.source && !standardSources.some(s => item.source.includes(s))) return true;
  if (item.id && (String(item.id).startsWith("cu_") || String(item.id).startsWith("custom_") || String(item.id).includes("uuid"))) return true;
  return false;
}

const KNOWN_MP_CATEGORIES = {
  "P vs. B": "🎯 P vs. B (Plosiv stimmlos/stimmhaft)",
  "T vs. D": "🎯 T vs. D (Alveolar Plosiv)",
  "K vs. G": "🎯 K vs. G (Velar Plosiv)",
  "S vs. SCH": "🎯 S vs. SCH (Zischlaute)",
  "M vs. N": "🎯 M vs. N (Nasale)",
  "F vs. W": "🎯 F vs. W (Labiodentale Frikative)",
  "W vs. B": "🎯 W vs. B (Reibelaut vs. Verschlusslaut)",
  "F vs. S": "🎯 F vs. S (Zahn-/Lippen-Frikativ)",
  "S vs. Z": "🎯 S vs. Z (Frikativ vs. Affrikate /ts/)",
  "N vs. NG": "🎯 N vs. NG (Zungenspitzen- vs. Gaumen-Nasal)",
  "R vs. L": "🎯 R vs. L (Liquidae / Schwinglaute)",
  "R vs. H": "🎯 R vs. H (Guttural vs. Glottal)",
  "CH vs. SCH": "🎯 CH vs. SCH (Ich-Laut /ç/ vs. /ʃ/)",
  "CH vs. K": "🎯 CH vs. K (Ach-Laut /x/ vs. Plosiv K)",
  "Vokallänge": "🎯 Vokallänge (Kurz- vs. Langvokale)"
};

const KNOWN_ES_CATEGORIES = {
  "Einsilber": "🔤 Freiburger Einsilber (DIN 45621)",
  "Plosive": "⚡ Plosive (P/T/K/B/D/G)",
  "Frikative": "🌊 Frikative (F/S/SCH/CH/W)",
  "Nasale": "👃 Nasale (M/N)",
  "Nomen & Gegenstände": "📦 Nomen & Gegenstände",
  "Verben & Aktionen": "🏃 Verben & Aktionen",
  "Adjektive": "🎨 Adjektive",
  "Tiere & Natur": "🐾 Tiere & Natur",
  "Essen & Trinken": "🍎 Essen & Trinken",
  "Wohnen & Haushalt": "🏠 Wohnen & Haushalt"
};

const KNOWN_MS_CATEGORIES = {
  "Mehrsilber & Komposita": "📚 Mehrsilber & Komposita (Alle)",
  "2-silbig": "📚 2-silbige Wörter & Komposita (z. B. Haustür)",
  "3-silbig": "📚 3-silbige Wörter & Komposita (z. B. Wörterbuch)",
  "4-silbig": "📚 4-silbige Wörter & Komposita (z. B. Kindergarten)"
};

const KNOWN_NUM_CATEGORIES = {
  "Freiburger Zahlentest (DIN 45621)": "🏛 Freiburger Zahlentest (DIN 45621)",
  "Einfache Zahlen": "🔢 Einfache Zahlen (1-100)",
  "Große Zahlen": "💯 Große Zahlen (Hunderter/Tausender)",
  "Uhrzeiten": "⏰ Uhrzeiten & Zeitangaben",
  "Beträge": "💶 Beträge & Geldbeträge",
  "Telefonnummern & Codes": "📞 Telefonnummern & Codes",
  "Datum & Kalender": "📅 Datum & Kalender"
};

const KNOWN_SENT_CATEGORIES = {
  "Alltagssätze": "💬 Alltagssätze",
  "OLSA Satz-Matrix": "🎯 OLSA Satz-Matrix",
  "Fragen & Dialoge": "❓ Fragen & Dialoge",
  "Arbeit & Beruf": "💼 Arbeit & Beruf",
  "Einkaufen & Gastronomie": "🛒 Einkaufen & Gastronomie",
  "Reisen & Unterwegs": "🚆 Reisen & Unterwegs",
  "Medizin & Gesundheit": "🏥 Medizin & Gesundheit"
};

function populateMPCategorySelect() {
  const select = document.getElementById("mpCategorySelect");
  if (!select) return;

  const prevValue = selectedMPCategory || select.value || "ALL";

  // Gather unique categories from minimal_pairs
  const cats = new Set();
  let hasCustom = false;
  if (exercises && exercises.minimal_pairs) {
    exercises.minimal_pairs.forEach(item => {
      if (item.category && item.category.trim()) {
        cats.add(item.category.trim());
      }
      if (isCustomEntry(item, "minimal_pairs")) hasCustom = true;
    });
  }

  // Also include default known categories
  Object.keys(KNOWN_MP_CATEGORIES).forEach(k => cats.add(k));

  let html = `
    <option value="ALL">🌟 Alle Kategorien (Zufall)</option>
    ${hasCustom ? '<option value="MY_ENTRIES">⭐ Nur eigene Einträge</option>' : ''}
    <option value="RHYMES">🔥 Reim-Gruppen (Mehrfachauswahl)</option>
  `;

  const sortedCats = Array.from(cats).sort((a, b) => {
    const isKnownA = a in KNOWN_MP_CATEGORIES;
    const isKnownB = b in KNOWN_MP_CATEGORIES;
    if (isKnownA && !isKnownB) return -1;
    if (!isKnownA && isKnownB) return 1;
    return a.localeCompare(b);
  });

  sortedCats.forEach(cat => {
    const label = KNOWN_MP_CATEGORIES[cat] || `🎯 ${escapeHtml(cat)}`;
    html += `<option value="${escapeHtml(cat)}">${label}</option>`;
  });

  select.innerHTML = html;

  if (Array.from(select.options).some(opt => opt.value === prevValue)) {
    select.value = prevValue;
    selectedMPCategory = prevValue;
  } else {
    select.value = "ALL";
    selectedMPCategory = "ALL";
  }
}

function populateESCategorySelect() {
  const select = document.getElementById("esCategorySelect");
  if (!select) return;

  const prevValue = selectedESCategory || select.value || "ALL";

  const cats = new Set();
  let hasCustom = false;
  if (exercises && exercises.monosyllables) {
    exercises.monosyllables.forEach(item => {
      if ((!item.syllable_count || item.syllable_count === 1) && !item.category?.includes("silbig") && item.category !== "Mehrsilber & Komposita") {
        const c = item.category || "Einsilber";
        if (c && c.trim()) cats.add(c.trim());
        if (isCustomEntry(item, "monosyllables")) hasCustom = true;
      }
    });
  }
  cats.add("Einsilber");

  let html = `
    <option value="ALL">🌟 Alle Freiburger Einsilber (Zufall)</option>
    ${hasCustom ? '<option value="MY_ENTRIES">⭐ Nur eigene Einsilber</option>' : ''}
  `;

  const sortedCats = Array.from(cats).sort((a, b) => {
    if (a === "Einsilber") return -1;
    if (b === "Einsilber") return 1;
    return a.localeCompare(b);
  });

  sortedCats.forEach(cat => {
    const label = KNOWN_ES_CATEGORIES[cat] || `🔤 ${escapeHtml(cat)}`;
    html += `<option value="${escapeHtml(cat)}">${label}</option>`;
  });

  select.innerHTML = html;

  if (Array.from(select.options).some(opt => opt.value === prevValue)) {
    select.value = prevValue;
    selectedESCategory = prevValue;
  } else {
    select.value = "ALL";
    selectedESCategory = "ALL";
  }
}

function populateMSCategorySelect() {
  const select = document.getElementById("msCategorySelect");
  if (!select) return;

  const prevValue = selectedMSCategory || select.value || "ALL";

  const cats = new Set();
  let hasCustom = false;
  if (exercises && exercises.monosyllables) {
    exercises.monosyllables.forEach(item => {
      if ((item.syllable_count && item.syllable_count > 1) || (item.category && item.category.includes("silbig")) || item.category === "Mehrsilber & Komposita") {
        const c = item.category || `${item.syllable_count}-silbig`;
        if (c && c.trim()) cats.add(c.trim());
        if (isCustomEntry(item, "monosyllables")) hasCustom = true;
      }
    });
  }
  cats.add("2-silbig");
  cats.add("3-silbig");
  cats.add("4-silbig");

  let html = `
    <option value="ALL">🌟 Alle Mehrsilber (Zufall)</option>
    ${hasCustom ? '<option value="MY_ENTRIES">⭐ Nur eigene Einträge</option>' : ''}
  `;

  const sortedCats = Array.from(cats).sort();

  sortedCats.forEach(cat => {
    const label = KNOWN_MS_CATEGORIES[cat] || `📚 ${escapeHtml(cat)}`;
    html += `<option value="${escapeHtml(cat)}">${label}</option>`;
  });

  select.innerHTML = html;

  if (Array.from(select.options).some(opt => opt.value === prevValue)) {
    select.value = prevValue;
    selectedMSCategory = prevValue;
  } else {
    select.value = "ALL";
    selectedMSCategory = "ALL";
  }
}

function populateNumCategorySelect() {
  const select = document.getElementById("numCategorySelect");
  if (!select) return;

  const prevValue = selectedNumCategory || select.value || "ALL";

  const cats = new Set();
  let hasCustom = false;
  if (exercises && exercises.numbers) {
    exercises.numbers.forEach(item => {
      const c = item.category || item.type;
      if (c && c.trim()) cats.add(c.trim());
      if (isCustomEntry(item, "numbers")) hasCustom = true;
    });
  }
  Object.keys(KNOWN_NUM_CATEGORIES).forEach(k => {
    // Only add default categories if items exist or standard
    if (k === "Einfache Zahlen" || k === "Beträge" || k === "Uhrzeiten") cats.add(k);
  });

  let html = `
    <option value="ALL">🌟 Alle Kategorien (Zufall)</option>
    ${hasCustom ? '<option value="MY_ENTRIES">⭐ Nur eigene Einträge</option>' : ''}
  `;

  const sortedCats = Array.from(cats).sort((a, b) => {
    const isKnownA = a in KNOWN_NUM_CATEGORIES;
    const isKnownB = b in KNOWN_NUM_CATEGORIES;
    if (isKnownA && !isKnownB) return -1;
    if (!isKnownA && isKnownB) return 1;
    return a.localeCompare(b);
  });

  sortedCats.forEach(cat => {
    const label = KNOWN_NUM_CATEGORIES[cat] || `🔢 ${escapeHtml(cat)}`;
    html += `<option value="${escapeHtml(cat)}">${label}</option>`;
  });

  select.innerHTML = html;

  if (Array.from(select.options).some(opt => opt.value === prevValue)) {
    select.value = prevValue;
    selectedNumCategory = prevValue;
  } else {
    select.value = "ALL";
    selectedNumCategory = "ALL";
  }
}

function populateSentCategorySelect() {
  const select = document.getElementById("sentCategorySelect");
  if (!select) return;

  const prevValue = selectedSentCategory || select.value || "ALL";

  const cats = new Set();
  let hasCustom = false;
  if (exercises && exercises.sentences) {
    exercises.sentences.forEach(item => {
      const c = item.category;
      if (c && c.trim()) cats.add(c.trim());
      if (isCustomEntry(item, "sentences")) hasCustom = true;
    });
  }
  cats.add("Alltagssätze");
  cats.add("OLSA Satz-Matrix");

  let html = `
    <option value="ALL">🌟 Alle Kategorien (Zufall)</option>
    ${hasCustom ? '<option value="MY_ENTRIES">⭐ Nur eigene Einträge</option>' : ''}
  `;

  const sortedCats = Array.from(cats).sort((a, b) => {
    const isKnownA = a in KNOWN_SENT_CATEGORIES;
    const isKnownB = b in KNOWN_SENT_CATEGORIES;
    if (isKnownA && !isKnownB) return -1;
    if (!isKnownA && isKnownB) return 1;
    return a.localeCompare(b);
  });

  sortedCats.forEach(cat => {
    const label = KNOWN_SENT_CATEGORIES[cat] || `💬 ${escapeHtml(cat)}`;
    html += `<option value="${escapeHtml(cat)}">${label}</option>`;
  });

  select.innerHTML = html;

  if (Array.from(select.options).some(opt => opt.value === prevValue)) {
    select.value = prevValue;
    selectedSentCategory = prevValue;
  } else {
    select.value = "ALL";
    selectedSentCategory = "ALL";
  }
}

function updateCategoryDatalist(modType = null) {
  const catSelect = document.getElementById("addCategory");
  if (!catSelect) return;

  if (!modType) {
    modType = document.getElementById("addTypeSelect")?.value || "minimal_pairs";
  }

  // Für die Filterung brauchen wir den eigentlichen Basis-Typ
  let baseModType = modType;
  if (baseModType === "multisyllables") baseModType = "monosyllables";

  const items = (exercises && exercises[baseModType]) ? exercises[baseModType] : [];
  const cats = new Set();
  
  if (modType === "multisyllables") {
    // Nur Mehrsilber-Kategorien extrahieren
    items.forEach(item => {
      const c = item.category || item.type;
      if (c && c.trim() && (c.includes("silbig") || c.includes("Komposita") || c.includes("Mehrsilber"))) cats.add(c.trim());
    });
    // Fallback/Standard-Kategorien
    cats.add("2-silbig");
    cats.add("3-silbig");
    cats.add("4-silbig");
    cats.add("Mehrsilber & Komposita");
  } else {
    items.forEach(item => {
      const c = item.category || item.type;
      if (c && c.trim()) cats.add(c.trim());
    });

    if (modType === "minimal_pairs") {
      Object.keys(KNOWN_MP_CATEGORIES).forEach(k => cats.add(k));
    } else if (modType === "monosyllables") {
      Object.keys(KNOWN_ES_CATEGORIES).forEach(k => cats.add(k));
    } else if (modType === "numbers") {
      Object.keys(KNOWN_NUM_CATEGORIES).forEach(k => cats.add(k));
    } else if (modType === "sentences") {
      Object.keys(KNOWN_SENT_CATEGORIES).forEach(k => cats.add(k));
    }
  }

  try {
    const customCats = JSON.parse(localStorage.getItem('ci_custom_categories') || '{}');
    const myCats = customCats[baseModType] || [];
    myCats.forEach(c => cats.add(c));
  } catch(e) {}

  // Bei Mehrsilbern auch die Einsilber-Fallback-Kategorien entfernen, falls sie reingerutscht sind
  if (modType === "multisyllables") {
    Object.keys(KNOWN_ES_CATEGORIES).forEach(k => cats.delete(k));
  } else if (modType === "monosyllables") {
    cats.delete("2-silbig");
    cats.delete("3-silbig");
    cats.delete("4-silbig");
    cats.delete("Mehrsilber & Komposita");
  }

  catSelect.innerHTML = Array.from(cats).sort().map(cat => `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`).join("");
}

function openEditorForType(modType, initialCategory = "") {
  switchTab("editor");
  currentEditorView = modType;
  switchEditorSubView("form", true);

  const addTypeSelect = document.getElementById("addTypeSelect");
  if (addTypeSelect) {
    addTypeSelect.value = modType;
    const evt = new Event("change");
    addTypeSelect.dispatchEvent(evt);
  }

  if (initialCategory) {
    const catInput = document.getElementById("addCategory");
    if (catInput) catInput.value = initialCategory;
  }

  const catInput = document.getElementById("addCategory");
  if (catInput) {
    catInput.focus();
  }
}
window.openEditorForType = openEditorForType;

// ─── Auto-Advance System (Adaptive Timers, Progress Bar & Hover/Click Pause) ──
let activeAutoAdvanceTimer = null;
let activeAutoAdvanceInterval = null;
let activeAutoAdvanceCancelFn = null;

function cancelAutoAdvance() {
  if (activeAutoAdvanceTimer) {
    clearTimeout(activeAutoAdvanceTimer);
    activeAutoAdvanceTimer = null;
  }
  if (activeAutoAdvanceInterval) {
    clearInterval(activeAutoAdvanceInterval);
    activeAutoAdvanceInterval = null;
  }
  if (activeAutoAdvanceCancelFn) {
    activeAutoAdvanceCancelFn();
    activeAutoAdvanceCancelFn = null;
  }
  document.querySelectorAll(".autoadvance-bar-wrapper").forEach(el => el.remove());
}

async function stopAutostartAndAudio() {
  // 1. Cancel any active auto advance countdown timer
  cancelAutoAdvance();

  // 2. Stop microphone / speech recognition recording if active
  try {
    if (typeof stopRecording === "function") stopRecording();
    if (typeof stopLiveMic === "function") stopLiveMic();
    if (typeof resetAllMicButtons === "function") resetAllMicButtons();
  } catch (_e) {}

  // 3. Stop backend player audio & background noise
  try {
    fetch("/api/audio/stop", { method: "POST" }).catch(() => {});
    fetch("/api/noise/stop", { method: "POST" }).catch(() => {});
  } catch (_e) {}

  // 4. Cancel browser TTS if active
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }

  // 5. Visual indicator on feedback banner
  const currentTab = getActiveTab();
  const feedbackEl = document.getElementById(`${currentTab}Feedback`);
  if (feedbackEl) {
    feedbackEl.className = "feedback-banner info-banner";
    feedbackEl.innerHTML = `<span>⏸ <strong>Autostart pausiert</strong> (Audio &amp; Countdown angehalten). Drücke <em>Start (Leertaste)</em> oder <em>Nächste Übung (N)</em> zum Fortfahren.</span>`;
    feedbackEl.classList.remove("hidden");
  }
  setStatus("⏸ Autostart pausiert.");
}

function scheduleAutoAdvance(feedbackEl, nextCallback, isCorrect) {
  cancelAutoAdvance();
  if (!autoStart || !feedbackEl) return;

  const totalDuration = isCorrect ? Math.round(autostartSuccessDelay * 1000) : Math.round(autostartErrorDelay * 1000);
  const startTime = Date.now();

  const barWrapper = document.createElement("div");
  barWrapper.className = "autoadvance-bar-wrapper";
  barWrapper.title = "Klicken oder Leertaste drücken zum Pausieren";

  const initialSec = (totalDuration / 1000).toFixed(1);
  barWrapper.innerHTML = `
    <div class="autoadvance-info">
      <span class="autoadvance-label">Nächste Übung in ${initialSec}s...</span>
      <span class="autoadvance-pause-btn" role="button">⏸ Pause</span>
    </div>
    <div class="autoadvance-progress">
      <div class="autoadvance-progress-fill ${isCorrect ? 'fill-success' : 'fill-danger'}"></div>
    </div>
  `;

  feedbackEl.appendChild(barWrapper);

  const labelEl = barWrapper.querySelector(".autoadvance-label");
  const fillEl = barWrapper.querySelector(".autoadvance-progress-fill");
  const pauseBtn = barWrapper.querySelector(".autoadvance-pause-btn");

  let isPaused = false;

  const pauseAutoAdvance = () => {
    if (isPaused) return;
    isPaused = true;
    if (activeAutoAdvanceTimer) {
      clearTimeout(activeAutoAdvanceTimer);
      activeAutoAdvanceTimer = null;
    }
    if (activeAutoAdvanceInterval) {
      clearInterval(activeAutoAdvanceInterval);
      activeAutoAdvanceInterval = null;
    }
    if (labelEl) labelEl.textContent = "⏸ Pausiert – Zeit lassen zum Vergleichen";
    if (pauseBtn) pauseBtn.textContent = "▶ Jetzt weiter";
    if (fillEl) fillEl.style.opacity = "0.4";
  };

  barWrapper.addEventListener("click", (e) => {
    e.stopPropagation();
    if (isPaused) {
      cancelAutoAdvance();
      nextCallback();
    } else {
      pauseAutoAdvance();
    }
  });

  // Pause when hovering over feedback banner on incorrect answers
  feedbackEl.addEventListener("mouseenter", () => {
    if (!isCorrect) {
      pauseAutoAdvance();
    }
  }, { once: true });

  activeAutoAdvanceCancelFn = () => {
    isPaused = true;
    if (labelEl) labelEl.textContent = "⏸ Pausiert";
  };

  activeAutoAdvanceInterval = setInterval(() => {
    if (isPaused) return;
    const elapsed = Date.now() - startTime;
    const remaining = Math.max(0, totalDuration - elapsed);
    const progress = (remaining / totalDuration);

    if (fillEl) {
      fillEl.style.transform = `scaleX(${progress})`;
    }
    if (labelEl) {
      labelEl.textContent = `Nächste Übung in ${(remaining / 1000).toFixed(1)}s...`;
    }

    if (remaining <= 0) {
      clearInterval(activeAutoAdvanceInterval);
      activeAutoAdvanceInterval = null;
    }
  }, 40);

  activeAutoAdvanceTimer = setTimeout(() => {
    if (!isPaused) {
      cancelAutoAdvance();
      nextCallback();
    }
  }, totalDuration);
}

// Minimalpaare Tab Logic
function revealMPCards() {
  clearTimeout(mpRevealTimer);
  mpRevealTimer = null;
  mpAudioFinished = true;
  const cards = document.querySelectorAll("#tab-mp .option-card");
  cards.forEach(card => {
    card.classList.remove("obscured");
    card.classList.add("revealed");
  });
  const hint = document.getElementById("mpHint");
  if (hint && !mpAttempted) {
    hint.textContent = currentMP?.hint || "Höre das Wort aufmerksam an und klicke auf die richtige Karte.";
  }
}

function hideMPCards() {
  clearTimeout(mpRevealTimer);
  mpRevealTimer = null;
  mpAudioFinished = false;
  const cards = document.querySelectorAll("#tab-mp .option-card");
  cards.forEach(card => {
    card.classList.add("obscured");
    card.classList.remove("revealed");
  });
  const hint = document.getElementById("mpHint");
  if (hint && !mpAttempted) {
    hint.textContent = "🎧 Höre zuerst das Wort (Klicke 'Start' oder Leertaste)...";
  }
}

function nextMPItem(userTriggered = false) {
  cancelAutoAdvance();
  if (!exercises.minimal_pairs || exercises.minimal_pairs.length === 0) return;

  let pool = exercises.minimal_pairs;
  if (selectedMPCategory === "MY_ENTRIES") {
    pool = exercises.minimal_pairs.filter(item => isCustomEntry(item, "minimal_pairs"));
    if (pool.length === 0) pool = exercises.minimal_pairs;
  } else if (selectedMPCategory === "RHYMES") {
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

  document.getElementById("mpCategory").textContent = currentMP.category || "Konsonanten";
  const mpSrcEl = document.getElementById("mpSource");
  if (mpSrcEl) mpSrcEl.textContent = currentMP.source ? `🏛 ${currentMP.source}` : "🏛 Marburger Minimalpaare";
  document.getElementById("mpHint").textContent = currentMP.hint || "Höre das Wort aufmerksam an und klicke auf die richtige Karte.";

  const cardsContainer = document.querySelector("#tab-mp .cards-grid");
  cardsContainer.innerHTML = "";

  currentMPWords.forEach((word, idx) => {
    const card = document.createElement("div");
    card.className = "option-card";
    if (mpDelayReveal) {
      card.classList.add("obscured");
    }
    card.id = `card_${idx}`;
    card.setAttribute("data-hotkey", `Taste: ${idx + 1}`);

    let wordTranslation = "";
    if (idx === 0 && currentMP.translation_a) {
      wordTranslation = currentMP.translation_a;
    } else if (idx === 1 && currentMP.translation_b) {
      wordTranslation = currentMP.translation_b;
    } else if (currentMP.translation_de) {
      const parts = currentMP.translation_de.split("/").map(s => s.trim());
      if (parts.length > idx) {
        wordTranslation = parts[idx];
      } else if (idx === 0) {
        wordTranslation = currentMP.translation_de;
      }
    }

    if (wordTranslation) {
      card.setAttribute("title", `${word} = „${wordTranslation}“ (Taste ${idx + 1})`);
    } else {
      card.setAttribute("title", `Option ${String.fromCharCode(65 + idx)} wählen (Taste ${idx + 1})`);
    }

    card.innerHTML = `
      <div class="card-top-bar">
        <span class="card-label">OPTION ${String.fromCharCode(65 + idx)}</span>
        <button class="card-audio-btn" title="Dieses Wort vorlesen (Shift+${idx + 1} / Shift+${String.fromCharCode(65 + idx)})" data-hotkey="Shift+${idx + 1}">🔊</button>
      </div>
      <span class="card-word">${word}</span>
      ${wordTranslation ? `<span class="card-translation" title="Deutsche Übersetzung: ${wordTranslation}">🇩🇪 ${wordTranslation}</span>` : ''}
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
  setPlayBtnState("mpPlayBtn", false, "Wiederholen");

  if (mpDelayReveal) {
    hideMPCards();
  } else {
    revealMPCards();
  }

  if (userTriggered) {
    playMPAudio();
  }
}

function playMPAudio() {
  setPlayBtnState("mpPlayBtn", true, "Wiederholen");
  playTTS(currentMPTargetWord, "Minimalpaar");

  if (mpDelayReveal && !mpAudioFinished && !mpAttempted) {
    const hint = document.getElementById("mpHint");
    if (hint) hint.textContent = "🔊 Höre aufmerksam zu... Karten werden gleich aufgedeckt.";
    const delay = estimateSpeechDurationMs(currentMPTargetWord, audioRate);
    clearTimeout(mpRevealTimer);
    mpRevealTimer = setTimeout(() => {
      revealMPCards();
    }, delay);
  }
}

async function checkMPAnswer(chosenIndex) {
  if (mpDelayReveal && !mpAudioFinished) {
    revealMPCards();
    return;
  }

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

  scheduleAutoAdvance(feedback, () => nextMPItem(true), isCorrect);
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

function loadESTestItem(idx, shouldPlay = false) {
  if (idx < 0 || idx >= currentTestWords.length) return;
  currentES = currentTestWords[idx];
  currentESTargetWord = currentES.word || "";
  esAttempted = false;

  const esCatEl = document.getElementById("esCategory");
  if (esCatEl) esCatEl.textContent = `Freiburger Liste ${currentTestListNum} (${idx + 1}/20)`;
  document.getElementById("esInput").value = "";
  const feedback = document.getElementById("esFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus(`Wort ${idx + 1} von 20 (Freiburger Testliste ${currentTestListNum}).`);

  if (shouldPlay) {
    playESAudio();
  } else {
    setPlayBtnState("esPlayBtn", false, "Wiederholen");
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
    const shouldPlay = userTriggered || isAutoStartActive("es");
    loadESTestItem(currentTestIndex, shouldPlay);
    return;
  }

  if (!exercises.monosyllables || exercises.monosyllables.length === 0) return;
  const validItems = exercises.monosyllables.filter(item => 
    item.word && !item.word.startsWith("Wort_") &&
    (!item.syllable_count || item.syllable_count === 1) &&
    !item.category?.includes("silbig") &&
    item.category !== "Mehrsilber & Komposita"
  );
  const basePool = validItems.length > 0 ? validItems : exercises.monosyllables;

  let pool = basePool;
  if (selectedESCategory === "MY_ENTRIES") {
    pool = basePool.filter(item => isCustomEntry(item, "monosyllables"));
    if (pool.length === 0) pool = basePool;
  } else if (selectedESCategory !== "ALL") {
    pool = basePool.filter(item => item.category === selectedESCategory || (item.category && item.category.includes(selectedESCategory)));
    if (pool.length === 0) pool = basePool;
  }

  currentES = pool[Math.floor(Math.random() * pool.length)];
  currentESTargetWord = currentES.word || currentES.target || "";
  esAttempted = false;  // reset module-level flag

  const esCatEl2 = document.getElementById("esCategory");
  if (esCatEl2) esCatEl2.textContent = currentES.category || "Einsilber";
  const esSrcEl = document.getElementById("esSource");
  if (esSrcEl) esSrcEl.textContent = currentES.source ? `🏛 ${currentES.source}` : "🏛 Freiburger Einsilber (DIN 45621)";
  document.getElementById("esInput").value = "";
  const feedback = document.getElementById("esFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus("Bereit für Freiburger Einsilber-Übung (DIN 45621).");
  setPlayBtnState("esPlayBtn", false, "Wiederholen");

  if (userTriggered) {
    playESAudio();
  }
}

async function playESAudio() {
  setPlayBtnState("esPlayBtn", true, "Wiederholen");
  playTTS(currentESTargetWord, "Einsilber");
  if (isAutoMicActive("es")) {
    const delay = estimateSpeechDurationMs(currentESTargetWord, audioRate);
    setTimeout(() => startAutoMic("es"), delay + 200);
  }
}

async function checkESAnswer() {
  if (esAttempted) return;

  const userInput = document.getElementById("esInput")?.value.trim() || "";
  if (!userInput) {
    const feedback = document.getElementById("esFeedback");
    if (feedback) {
      feedback.textContent = "⚠️ Bitte gib zuerst das gehörte Wort ein oder nutze das Mikrofon.";
      feedback.className = "feedback-banner danger";
    }
    document.getElementById("esInput")?.focus();
    return;
  }

  esAttempted = true;

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: currentESTargetWord,
      user_input: userInput,
      module: "Einsilber",
      category: esMode === "test_list" ? `Freiburger Liste ${currentTestListNum}` : (currentES.category || "Einsilber")
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

  let sylHtml = "";
  if (data.hyphenated_target && data.syllable_count_target > 1) {
    sylHtml = `
      <div style="margin-top:0.4rem; padding:0.35rem 0.6rem; background:rgba(30,58,138,0.3); border-radius:6px; font-size:0.82rem; display:inline-flex; align-items:center; gap:0.5rem;">
        <span style="color:#93C5FD; font-weight:700;">🎵 Silbenaufbau:</span>
        <span style="color:#F3F4F6; font-weight:600; letter-spacing:0.5px;">${escapeHtml(data.hyphenated_target)}</span>
        <span class="val-badge" style="font-size:0.75rem; background:rgba(59,130,246,0.2); color:#60A5FA;">${data.syllable_count_target} Silben</span>
      </div>
    `;
  }

  feedback.innerHTML = `<div>${data.message}</div>${sylHtml}${ipaHtml}`;
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

  scheduleAutoAdvance(feedback, () => nextESItem(true), data.is_correct);
}

// ─── Mehrsilber & Komposita Module Logic ─────────────────────────────────────
let currentMS = null;
let currentMSTargetWord = "";
let selectedMSCategory = "ALL";
let msAttempted = false;

function nextMSItem(userTriggered = false) {
  if (!exercises.monosyllables || exercises.monosyllables.length === 0) return;
  const msItems = exercises.monosyllables.filter(item => 
    item.word && !item.word.startsWith("Wort_") && (
      (item.syllable_count && item.syllable_count > 1) ||
      (item.category && (item.category.includes("silbig") || item.category.includes("Komposita") || item.category.includes("Mehrsilber")))
    )
  );
  const basePool = msItems.length > 0 ? msItems : exercises.monosyllables;

  let pool = basePool;
  if (selectedMSCategory === "MY_ENTRIES") {
    pool = basePool.filter(item => isCustomEntry(item, "monosyllables"));
    if (pool.length === 0) pool = basePool;
  } else if (selectedMSCategory === "2-silbig") {
    pool = basePool.filter(item => item.category === "2-silbig" || item.syllable_count === 2);
    if (pool.length === 0) pool = basePool;
  } else if (selectedMSCategory === "3-silbig") {
    pool = basePool.filter(item => item.category === "3-silbig" || item.syllable_count === 3);
    if (pool.length === 0) pool = basePool;
  } else if (selectedMSCategory === "4-silbig") {
    pool = basePool.filter(item => item.category === "4-silbig" || item.syllable_count === 4);
    if (pool.length === 0) pool = basePool;
  } else if (selectedMSCategory !== "ALL") {
    pool = basePool.filter(item => item.category === selectedMSCategory);
    if (pool.length === 0) pool = basePool;
  }

  currentMS = pool[Math.floor(Math.random() * pool.length)];
  currentMSTargetWord = currentMS.word || currentMS.target || "";
  msAttempted = false;

  const msCatEl = document.getElementById("msCategory");
  if (msCatEl) msCatEl.textContent = currentMS.category || `${currentMS.syllable_count || 2}-silbig`;
  const msSrcEl = document.getElementById("msSource");
  if (msSrcEl) msSrcEl.textContent = currentMS.source ? `🏛 ${currentMS.source}` : "🏛 Logopädischer Mehrsilber-Katalog";

  const inputEl = document.getElementById("msInput");
  if (inputEl) inputEl.value = "";
  const feedback = document.getElementById("msFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus("Bereit für Mehrsilber- & Komposita-Übung.");
  setPlayBtnState("msPlayBtn", false, "Wiederholen");

  if (userTriggered) {
    playMSAudio();
  }
}

async function playMSAudio() {
  setPlayBtnState("msPlayBtn", true, "Wiederholen");
  playTTS(currentMSTargetWord, "Mehrsilber");
  if (isAutoMicActive("ms")) {
    const delay = estimateSpeechDurationMs(currentMSTargetWord, audioRate);
    setTimeout(() => startAutoMic("ms"), delay + 200);
  }
}

async function checkMSAnswer() {
  if (msAttempted) return;

  const userInput = document.getElementById("msInput")?.value.trim() || "";
  if (!userInput) {
    const feedback = document.getElementById("msFeedback");
    if (feedback) {
      feedback.textContent = "⚠️ Bitte gib zuerst das gehörte Wort ein oder nutze das Mikrofon.";
      feedback.className = "feedback-banner danger";
    }
    document.getElementById("msInput")?.focus();
    return;
  }

  msAttempted = true;

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: currentMSTargetWord,
      user_input: userInput,
      module: "Mehrsilber",
      category: currentMS.category || "Mehrsilber & Komposita"
    })
  });
  const data = await res.json();
  const feedback = document.getElementById("msFeedback");

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

  let sylHtml = "";
  if (data.hyphenated_target) {
    sylHtml = `
      <div style="margin-top:0.4rem; padding:0.35rem 0.6rem; background:rgba(30,58,138,0.3); border-radius:6px; font-size:0.85rem; display:inline-flex; align-items:center; gap:0.5rem;">
        <span style="color:#93C5FD; font-weight:700;">🎵 Silbenaufbau:</span>
        <span style="color:#F3F4F6; font-weight:600; letter-spacing:0.5px;">${escapeHtml(data.hyphenated_target)}</span>
        <span class="val-badge" style="font-size:0.75rem; background:rgba(59,130,246,0.2); color:#60A5FA;">${data.syllable_count_target || 2} Silben</span>
      </div>
    `;
  }

  feedback.innerHTML = `<div>${data.message}</div>${sylHtml}${ipaHtml}`;
  feedback.className = `feedback-banner ${data.is_correct ? "success" : "danger"}`;
  if (data.is_correct) addXP(30);

  scheduleAutoAdvance(feedback, () => nextMSItem(true), data.is_correct);
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

  let pool = exercises.numbers;
  if (selectedNumCategory === "MY_ENTRIES") {
    pool = exercises.numbers.filter(item => isCustomEntry(item, "numbers"));
    if (pool.length === 0) pool = exercises.numbers;
  } else if (selectedNumCategory !== "ALL") {
    pool = exercises.numbers.filter(item => {
      const cat = item.category || item.type;
      return cat === selectedNumCategory || (cat && cat.includes(selectedNumCategory));
    });
    if (pool.length === 0) pool = exercises.numbers;
  }

  currentNum = pool[Math.floor(Math.random() * pool.length)];
  currentNumTargetWord = currentNum.spoken;
  numAttempted = false;  // reset module-level flag

  document.getElementById("numCategory").textContent = currentNum.type || currentNum.category || "Zahlen & Uhrzeiten";
  const numSrcEl = document.getElementById("numSource");
  if (numSrcEl) numSrcEl.textContent = currentNum.source ? `🏛 ${currentNum.source}` : "🏛 Zahlen & Uhrzeiten";
  document.getElementById("numInput").value = "";
  const feedback = document.getElementById("numFeedback");
  feedback.className = "feedback-banner hidden";
  setStatus("Bereit für Zahlenübung.");
  setPlayBtnState("numPlayBtn", false, "Wiederholen");

  if (userTriggered) {
    playNumAudio();
  }
}

async function playNumAudio() {
  setPlayBtnState("numPlayBtn", true, "Wiederholen");
  playTTS(currentNumTargetWord, "Zahl / Uhrzeit");
  if (isAutoMicActive("num")) {
    const delay = estimateSpeechDurationMs(currentNumTargetWord, audioRate);
    setTimeout(() => startAutoMic("num"), delay + 200);
  }
}

async function checkNumAnswer() {
  if (numAttempted) return;

  const userInput = document.getElementById("numInput")?.value.trim() || "";
  if (!userInput) {
    const feedback = document.getElementById("numFeedback");
    if (feedback) {
      feedback.textContent = "⚠️ Bitte gib zuerst die gehörte Zahl oder Uhrzeit ein.";
      feedback.className = "feedback-banner danger";
    }
    document.getElementById("numInput")?.focus();
    return;
  }

  numAttempted = true;

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

  scheduleAutoAdvance(feedback, () => nextNumItem(true), data.is_correct);
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
  if (catEl) {
    const cat = currentSent.category || "Alltagssätze";
    const src = currentSent.source || "";
    if (cat.includes("OLSA") || src.includes("OLSA")) {
      catEl.textContent = "🏛 OLSA Satz-Matrix";
    } else {
      catEl.textContent = `💬 ${cat}`;
    }
  }

  // Replace target word in sentence display with blank line
  const maskedSentence = (currentSentTargetWord && currentSent.sentence)
    ? currentSent.sentence.replace(currentSentTargetWord, "_______")
    : (currentSent.sentence || "...");
  const dispEl = document.getElementById("sentDisplay");
  if (dispEl) dispEl.textContent = `"${maskedSentence}"`;

  const cardsContainer = document.getElementById("sentCardsGrid");
  if (!cardsContainer) return;
  cardsContainer.innerHTML = "";

  const sentTrans = currentSent ? (currentSent.translation_de || "") : "";
  if (dispEl && sentTrans) {
    dispEl.setAttribute("title", `Übersetzung: „${sentTrans}“`);
  }

  currentSentWords.forEach((word, idx) => {
    const card = document.createElement("div");
    card.className = "option-card";
    if (sentDelayReveal && sentMode === "mc") {
      card.classList.add("obscured");
    }
    card.id = `sent_card_${idx}`;
    card.setAttribute("data-hotkey", `Taste: ${idx + 1}`);

    let wordTranslation = "";
    if (sentTrans && currentSentWords.length > 0 && sentTrans.includes("/")) {
      const parts = sentTrans.split("/").map(s => s.trim());
      if (parts.length > idx) wordTranslation = parts[idx];
    } else if (sentTrans && word.toLowerCase() === (currentSent.target_word || "").toLowerCase()) {
      wordTranslation = sentTrans;
    }

    if (wordTranslation) {
      card.setAttribute("title", `${word} = „${wordTranslation}“ (Taste ${idx + 1})`);
    } else {
      card.setAttribute("title", `Option ${String.fromCharCode(65 + idx)} wählen (Taste ${idx + 1})`);
    }

    card.innerHTML = `
      <div class="card-top-bar">
        <span class="card-label">OPTION ${String.fromCharCode(65 + idx)}</span>
        <button class="card-audio-btn" title="Dieses Wort vorlesen (Shift+${idx + 1} / Shift+${String.fromCharCode(65 + idx)})" data-hotkey="Shift+${idx + 1}">🔊</button>
      </div>
      <span class="card-word">${word}</span>
      ${wordTranslation ? `<span class="card-translation" title="Deutsche Übersetzung: ${wordTranslation}">🇩🇪 ${wordTranslation}</span>` : ''}
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

function revealSentCards() {
  clearTimeout(sentRevealTimer);
  sentRevealTimer = null;
  sentAudioFinished = true;
  const cards = document.querySelectorAll("#sentCardsGrid .option-card");
  cards.forEach(card => {
    card.classList.remove("obscured");
    card.classList.add("revealed");
  });
  const hint = document.getElementById("sentHintText");
  if (hint && !sentAttempted && sentMode === "mc") {
    hint.textContent = "Höre den ganzen Satz und wähle das herausgehörte Schlüsselwort.";
  }
}

function hideSentCards() {
  clearTimeout(sentRevealTimer);
  sentRevealTimer = null;
  sentAudioFinished = false;
  const cards = document.querySelectorAll("#sentCardsGrid .option-card");
  cards.forEach(card => {
    card.classList.add("obscured");
    card.classList.remove("revealed");
  });
  const hint = document.getElementById("sentHintText");
  if (hint && !sentAttempted && sentMode === "mc") {
    hint.textContent = "🎧 Höre zuerst den ganzen Satz (Klicke 'Start' oder Leertaste)...";
  }
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
    if (sentDelayReveal) {
      if (!sentAttempted) hideSentCards();
    } else {
      revealSentCards();
    }
  }

  const sentStopBtn = document.getElementById("sentStopBtn");
  if (sentStopBtn) {
    sentStopBtn.style.display = (mode === "mc") ? "" : "none";
  }

  // Clear feedback banner & inner HTML explicitly
  const feedback = document.getElementById("sentFeedback");
  if (feedback) {
    feedback.innerHTML = "";
    feedback.className = "feedback-banner hidden";
  }

  // Re-initialize lower exercise area, clear input and reset feedback
  nextSentItem(false);
}

function nextSentItem(userTriggered = false) {
  if (!exercises.sentences || exercises.sentences.length === 0) return;

  let pool = exercises.sentences;
  if (selectedSentCategory === "MY_ENTRIES") {
    pool = exercises.sentences.filter(item => isCustomEntry(item, "sentences"));
    if (pool.length === 0) pool = exercises.sentences;
  } else if (selectedSentCategory !== "ALL") {
    pool = exercises.sentences.filter(item => item.category === selectedSentCategory || (item.category && item.category.includes(selectedSentCategory)));
    if (pool.length === 0) pool = exercises.sentences;
  }

  currentSent = pool[Math.floor(Math.random() * pool.length)];
  sentAttempted = false;

  renderSentCards();

  if (sentDelayReveal && sentMode === "mc") {
    hideSentCards();
  } else {
    revealSentCards();
  }

  const inp = document.getElementById("sentFullInput");
  if (inp) inp.value = "";

  const feedback = document.getElementById("sentFeedback");
  if (feedback) {
    feedback.innerHTML = "";
    feedback.className = "feedback-banner hidden";
  }
  setStatus("Bereit für Satz-Übung.");
  setPlayBtnState("sentPlayBtn", false, "Satz wiederholen");

  if (userTriggered) {
    playSentAudio();
  }
}

async function playSentAudio() {
  if (!currentSent || !currentSent.sentence) return;
  setPlayBtnState("sentPlayBtn", true, "Satz wiederholen");
  playTTS(currentSent.sentence, "Ganzen Satz");
  if (sentMode === "full" && isAutoMicActive("sent")) {
    const delay = estimateSpeechDurationMs(currentSent.sentence, audioRate);
    setTimeout(() => startAutoMic("sentFull"), delay + 200);
  } else if (sentMode === "mc" && sentDelayReveal && !sentAudioFinished && !sentAttempted) {
    const hint = document.getElementById("sentHintText");
    if (hint) hint.textContent = "🔊 Höre aufmerksam zu... Schlüsselwörter werden gleich aufgedeckt.";
    const delay = estimateSpeechDurationMs(currentSent.sentence, audioRate);
    clearTimeout(sentRevealTimer);
    sentRevealTimer = setTimeout(() => {
      revealSentCards();
    }, delay);
  }
}

async function checkSentAnswer(chosenIndex) {
  if (sentDelayReveal && sentMode === "mc" && !sentAudioFinished) {
    revealSentCards();
    return;
  }

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
    nextSentItem(true);
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

  scheduleAutoAdvance(feedback, () => nextSentItem(true), isCorrect);
}

async function checkSentFullAnswer() {
  if (sentAttempted) return;

  if (!currentSent || !currentSent.sentence) {
    nextSentItem(true);
    return;
  }

  const userInput = document.getElementById("sentFullInput")?.value.trim() || "";
  if (!userInput) {
    const feedback = document.getElementById("sentFeedback");
    if (feedback) {
      feedback.textContent = "⚠️ Bitte tippe zuerst den gehörten Satz ein oder nutze das Mikrofon.";
      feedback.className = "feedback-banner danger";
    }
    document.getElementById("sentFullInput")?.focus();
    return;
  }

  sentAttempted = true;

  const target = currentSent.sentence;

  const res = await fetch("/api/evaluate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target: target,
      user_input: userInput,
      module: "Sentences_Full",
      category: currentSent.category || "OLSA Ganzsatz"
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

  scheduleAutoAdvance(feedback, () => nextSentItem(true), data.is_correct);
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
  setPlayBtnState("noisePlayBtn", false, "Wiederholen");

  if (userTriggered) {
    playNoiseAudio();
  }
}

async function playNoiseAudio() {
  setPlayBtnState("noisePlayBtn", true, "Wiederholen");
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

  isNoiseManuallyStopped = false;
  const level = document.getElementById("noiseLevelSelect")?.value || "medium";
  const ambientType = document.getElementById("noiseTypeSelect")?.value || "restaurant";
  const nVol = SNR_VOLUMES[level] || 0.52;

  playTTS(currentNoiseTargetWord, "Störschall-Wort", {
    ambient_noise: true,
    ambient_type: ambientType,
    ambient_volume: nVol,
    mask_noise: false
  });

  if (isAutoMicActive("noise")) {
    const delay = estimateSpeechDurationMs(currentNoiseTargetWord, audioRate);
    setTimeout(() => startAutoMic("noise"), delay + 200);
  }
}

async function stopNoiseAudio() {
  isNoiseManuallyStopped = true;
  try {
    await fetch("/api/noise/stop", { method: "POST" });
    setStatus("Störschall gestoppt.");
  } catch (e) {}
}
window.stopNoiseAudio = stopNoiseAudio;

async function checkNoiseAnswer() {
  if (noiseAttempted) return;

  const userInput = document.getElementById("noiseInput")?.value.trim() || "";
  if (!userInput) {
    const feedback = document.getElementById("noiseFeedback");
    if (feedback) {
      feedback.textContent = "⚠️ Bitte gib zuerst das im Störschall gehörte Wort ein.";
      feedback.className = "feedback-banner danger";
    }
    document.getElementById("noiseInput")?.focus();
    return;
  }

  noiseAttempted = true;

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

  scheduleAutoAdvance(feedback, () => nextNoiseItem(true), data.is_correct);
}

// ─── Auditives Gedächtnis (Merkspanne & Sequenz) ─────────────────
let targetMemoryWords = [];
let selectedMemoryWords = [];
let memoryAttempted = false;
let currentMemorySequenceId = 0;
let isMemoryUnlocked = false;
let isMemoryPlaying = false;

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
  isMemoryUnlocked = false;
  isMemoryPlaying = false;

  renderMemoryUI();
  const feedback = document.getElementById("memoryFeedback");
  if (feedback) feedback.className = "feedback-banner hidden";
  setStatus(`Bereit für Merkspannen-Übung (${targetMemoryWords.length} Wörter).`);
  setPlayBtnState("memoryPlayBtn", false, "Sequenz wiederholen");

  if (userTriggered) {
    playMemoryAudio();
  }
}

function renderMemoryUI() {
  const count = targetMemoryWords.length;
  const slotsContainer = document.getElementById("memorySelectedSlots");
  const poolContainer = document.getElementById("memoryPoolGrid");
  const checkBtn = document.getElementById("memoryCheckBtn");
  const resetBtn = document.getElementById("memoryResetBtn");

  if (checkBtn) checkBtn.disabled = !isMemoryUnlocked || selectedMemoryWords.length === 0;
  if (resetBtn) resetBtn.disabled = !isMemoryUnlocked || selectedMemoryWords.length === 0;

  if (slotsContainer) {
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
  }

  if (!poolContainer) return;

  if (!isMemoryUnlocked) {
    if (isMemoryPlaying) {
      poolContainer.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 1.6rem; text-align:center; background: rgba(30,41,59,0.45); border: 1px dashed rgba(96,165,250,0.4); border-radius: 14px;">
          <span style="font-size: 1.8rem; display:block; margin-bottom:0.4rem;">🎧</span>
          <span style="font-weight: 700; color: #93C5FD; font-size: 1.05rem;">Sequenz wird vorgelesen... Bitte aufmerksam zuhören!</span>
          <p style="font-size:0.85rem; color: var(--text-muted); margin:0.4rem 0 0 0;">Die Auswahlkarten werden automatisch freigeschaltet, sobald alle Wörter gesprochen wurden.</p>
        </div>
      `;
    } else {
      poolContainer.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 1.6rem; text-align:center; background: rgba(30,41,59,0.4); border: 1px dashed rgba(255,255,255,0.15); border-radius: 14px;">
          <span style="font-size: 1.8rem; display:block; margin-bottom:0.4rem;">🔒</span>
          <span style="font-weight: 700; color: var(--text-main); font-size: 1.05rem;">Wort-Karten gesperrt</span>
          <p style="font-size:0.85rem; color: var(--text-muted); margin:0.4rem 0 0 0;">Klicke oben auf <strong>▶ Start</strong>, um die Sequenz anzuhören und freizuschalten.</p>
        </div>
      `;
    }
    return;
  }

  const displayPool = [...targetMemoryWords].sort((a, b) => a.localeCompare(b));
  poolContainer.innerHTML = displayPool.map((word, idx) => {
    const isSelected = selectedMemoryWords.includes(word);
    return `
      <button class="option-card ${isSelected ? 'incorrect' : ''}" data-hotkey="Taste: ${idx + 1}" title="Wort wählen (Taste ${idx + 1})" style="padding: 1.1rem; text-align: center; justify-content: center; opacity: ${isSelected ? 0.35 : 1}; color: #FFFFFF !important;" ${isSelected ? 'disabled' : ''} onclick="selectMemoryWord('${escapeHtml(word)}')">
        <span class="card-word" style="font-size: 1.35rem; font-weight: 800; color: #FFFFFF !important; text-align: center; text-shadow: 0 2px 4px rgba(0,0,0,0.6);">${escapeHtml(word)}</span>
      </button>
    `;
  }).join("");
}

function selectMemoryWord(word) {
  if (!isMemoryUnlocked) return;
  if (selectedMemoryWords.length < targetMemoryWords.length && !selectedMemoryWords.includes(word)) {
    selectedMemoryWords.push(word);
    renderMemoryUI();
  }
}
window.selectMemoryWord = selectMemoryWord;

function resetMemorySelection() {
  if (!isMemoryUnlocked) return;
  selectedMemoryWords = [];
  renderMemoryUI();
}

async function playMemoryAudio() {
  setPlayBtnState("memoryPlayBtn", true, "Sequenz wiederholen");
  if (!targetMemoryWords || targetMemoryWords.length === 0) {
    nextMemoryItem(false);
  }
  const seqId = ++currentMemorySequenceId;
  isMemoryPlaying = true;
  isMemoryUnlocked = false;
  renderMemoryUI();

  setStatus(`▶ Spreche Sequenz (${targetMemoryWords.length} Wörter)...`);
  for (let i = 0; i < targetMemoryWords.length; i++) {
    if (seqId !== currentMemorySequenceId) return;
    setStatus(`▶ Wort ${i + 1} von ${targetMemoryWords.length} wird gesprochen...`);
    playTTS(targetMemoryWords[i], `Wort ${i + 1}`);
    if (seqId !== currentMemorySequenceId) return;
    const duration = estimateSpeechDurationMs(targetMemoryWords[i], audioRate);
    await new Promise(r => setTimeout(r, duration + 450));
  }
  if (seqId === currentMemorySequenceId) {
    isMemoryPlaying = false;
    isMemoryUnlocked = true;
    renderMemoryUI();
    setStatus("✅ Sequenz vollständig! Wähle nun die Wörter in der richtigen Reihenfolge.");
  }
}

async function checkMemoryAnswer() {
  if (!isMemoryUnlocked) return;
  if (selectedMemoryWords.length === 0) {
    const feedback = document.getElementById("memoryFeedback");
    if (feedback) {
      feedback.textContent = "⚠️ Bitte wähle zuerst mindestens ein Wort aus dem Wort-Pool aus.";
      feedback.className = "feedback-banner danger";
    }
    return;
  }

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

  scheduleAutoAdvance(feedback, () => nextMemoryItem(true), isCorrect);
}

// Exercise Editor Engine & Database CRUD
let editingItemId = null;
let editingItemType = null;
let editorSearchQuery = "";
let editorCategoryFilterValue = "";
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
  ["minimal_pairs", "monosyllables", "multisyllables", "numbers", "sentences"].forEach(key => {
    const el = document.getElementById(`fcount_${key}`);
    if (el) {
      let n = 0;
      if (key === "multisyllables") {
        n = (exercises["monosyllables"] || []).filter(item => (item.syllable_count && item.syllable_count > 1) || item.category === "Mehrsilber & Komposita" || (item.category && item.category.includes("silbig"))).length;
      } else if (key === "monosyllables") {
        n = (exercises["monosyllables"] || []).filter(item => (!item.syllable_count || item.syllable_count === 1) && !item.category?.includes("silbig") && item.category !== "Mehrsilber & Komposita").length;
      } else {
        n = (exercises[key] || []).length;
      }
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

function getItemSpokenText(item, type) {
  if (!item) return "";
  if (type === "minimal_pairs") {
    if (item.word_a && item.word_b) return `${item.word_a}, ${item.word_b}`;
    if (item.options && Array.isArray(item.options)) return item.options.join(", ");
    return "";
  } else if (type === "monosyllables") {
    return item.word || "";
  } else if (type === "numbers") {
    return item.spoken || item.value || "";
  } else if (type === "sentences") {
    return item.sentence || "";
  }
  return "";
}

function handlePlayClick(btn) {
  try {
    const item = JSON.parse(btn.dataset.item);
    const text = getItemSpokenText(item, currentEditorView);
    if (text) {
      playTTS(text, "Vorschau");
    } else {
      showToast("Kein gesprochener Text verfügbar.", "info");
    }
  } catch (e) {
    console.error("handlePlayClick error", e);
  }
}
window.handlePlayClick = handlePlayClick;

function convertNumberToSpokenGerman(raw) {
  if (!raw) return "";
  let str = String(raw).trim();

  // Uhrzeit: 14:30 oder 8:15 oder 14.30
  const timeMatch = str.match(/^([01]?[0-9]|2[0-3])[:.]([0-5][0-9])$/);
  if (timeMatch) {
    const h = parseInt(timeMatch[1], 10);
    const m = parseInt(timeMatch[2], 10);
    if (m === 0) return `${h} Uhr`;
    const mStr = m < 10 ? `0${m}` : `${m}`;
    return `${h} Uhr ${mStr}`;
  }

  // Währung mit Nachkommastellen: 12,50 € / 12.50€ / 12,50 Euro
  const currMatch = str.match(/^(\d+)[,.](\d{1,2})\s*(€|Euro|euro|EUR)?$/i);
  if (currMatch) {
    const eur = currMatch[1];
    const cent = currMatch[2];
    return `${eur} Euro ${cent}`;
  }

  // Währung glatt: 50 € / 50 Euro
  const currWhole = str.match(/^(\d+)\s*(€|Euro|euro|EUR)$/i);
  if (currWhole) {
    return `${currWhole[1]} Euro`;
  }

  return str;
}

function updateLiveIPABadges() {
  const wordA = document.getElementById("addWordA")?.value.trim();
  const wordB = document.getElementById("addWordB")?.value.trim();
  const esWord = document.getElementById("addESWord")?.value.trim();
  const sentTarget = document.getElementById("addSentTarget")?.value.trim();

  const ipaA = document.getElementById("ipaWordA");
  const ipaB = document.getElementById("ipaWordB");
  const ipaES = document.getElementById("ipaESWord");
  const ipaTarget = document.getElementById("ipaSentTarget");

  if (ipaA) ipaA.innerHTML = wordA ? `<span>IPA:</span> <code>${getIPASimple(wordA)}</code>` : "";
  if (ipaB) ipaB.innerHTML = wordB ? `<span>IPA:</span> <code>${getIPASimple(wordB)}</code>` : "";
  if (ipaES) ipaES.innerHTML = esWord ? `<span>IPA:</span> <code>${getIPASimple(esWord)}</code>` : "";
  if (ipaTarget) ipaTarget.innerHTML = sentTarget ? `<span>IPA:</span> <code>${getIPASimple(sentTarget)}</code>` : "";
}

function updateSentWordChips() {
  const container = document.getElementById("sentWordChipsContainer");
  if (!container) return;
  const sentence = document.getElementById("addSentText")?.value || "";
  const currentTarget = (document.getElementById("addSentTarget")?.value || "").trim().toLowerCase();

  const words = sentence
    .replace(/[.,!?;:()""'']/g, " ")
    .split(/\s+/)
    .map(w => w.trim())
    .filter(w => w.length > 0);

  const uniqueWords = Array.from(new Set(words));
  if (uniqueWords.length === 0) {
    container.innerHTML = `<span style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">(Tippe oben einen Satz ein...)</span>`;
    return;
  }

  container.innerHTML = uniqueWords.map(w => {
    const isSel = w.toLowerCase() === currentTarget;
    return `<button type="button" class="word-chip ${isSel ? 'selected' : ''}" onclick="selectSentChipTarget('${escapeHtml(w)}')">${escapeHtml(w)}</button>`;
  }).join("");
}

function selectSentChipTarget(word) {
  const targetInp = document.getElementById("addSentTarget");
  if (targetInp) {
    targetInp.value = word;
    updateLiveIPABadges();
    updateSentWordChips();
  }
}
window.selectSentChipTarget = selectSentChipTarget;

function suggestSentDistractors() {
  const target = (document.getElementById("addSentTarget")?.value || "").trim();
  const sentence = document.getElementById("addSentText")?.value || "";
  const optsInp = document.getElementById("addSentOptions");
  if (!optsInp) return;

  if (!target) {
    showToast("Bitte zuerst ein Zielwort festlegen!", "warning");
    return;
  }

  // Extract other words from sentence
  const sentenceWords = sentence
    .replace(/[.,!?;:()""'']/g, " ")
    .split(/\s+/)
    .map(w => w.trim())
    .filter(w => w.length > 2 && w.toLowerCase() !== target.toLowerCase());

  const candidates = Array.from(new Set(sentenceWords));
  const pool = (exercises.sentences || [])
    .map(s => s.target_word)
    .filter(w => w && w.toLowerCase() !== target.toLowerCase());

  const options = [target];
  while (options.length < 3 && candidates.length > 0) {
    const pick = candidates.shift();
    if (!options.includes(pick)) options.push(pick);
  }
  while (options.length < 3 && pool.length > 0) {
    const rnd = pool[Math.floor(Math.random() * pool.length)];
    if (!options.includes(rnd)) options.push(rnd);
  }
  if (options.length < 3) {
    options.push("Wort 2", "Wort 3");
  }

  optsInp.value = options.join(", ");
  showToast("🪄 Distraktoren vorgeschlagen!", "info");
}

function clearItemSpecificFormFields(modType) {
  if (modType === "minimal_pairs") {
    document.getElementById("addWordA").value = "";
    document.getElementById("addWordB").value = "";
    document.getElementById("addMPOptions").value = "";
    document.getElementById("addHint").value = "";
  } else if (modType === "monosyllables") {
    document.getElementById("addESWord").value = "";
  } else if (modType === "numbers") {
    document.getElementById("addNumVal").value = "";
    document.getElementById("addNumSpoken").value = "";
  } else if (modType === "sentences") {
    document.getElementById("addSentText").value = "";
    document.getElementById("addSentTarget").value = "";
    document.getElementById("addSentOptions").value = "";
  }
  updateLiveIPABadges();
  updateSentWordChips();
}

function focusFirstFormField(modType) {
  setTimeout(() => {
    if (modType === "minimal_pairs") document.getElementById("addWordA")?.focus();
    else if (modType === "monosyllables") document.getElementById("addESWord")?.focus();
    else if (modType === "numbers") document.getElementById("addNumVal")?.focus();
    else if (modType === "sentences") document.getElementById("addSentText")?.focus();
  }, 80);
}

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
  document.getElementById("formES").classList.toggle("hidden", val !== "monosyllables" && val !== "multisyllables");
  document.getElementById("formNum").classList.toggle("hidden", val !== "numbers");
  document.getElementById("formSent").classList.toggle("hidden", val !== "sentences");
  
  const esTitle = document.getElementById("formESTitle");
  if (esTitle) esTitle.textContent = val === "multisyllables" ? "📚 Mehrsilber-Felder" : "🔤 Einsilber-Felder";

  updateCategoryDatalist(val);
  updateLiveIPABadges();
  updateSentWordChips();
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
  if (titleEl) titleEl.textContent = `✏️ Übung bearbeiten`;

  const btnEl = document.getElementById("addItemBtn");
  if (btnEl) btnEl.textContent = "💾 Änderungen speichern";

  const addTypeSelect = document.getElementById("addTypeSelect");
  if (addTypeSelect) addTypeSelect.value = type;

  const formMP = document.getElementById("formMP");
  const formES = document.getElementById("formES");
  const formNum = document.getElementById("formNum");
  const formSent = document.getElementById("formSent");

  if (formMP) formMP.classList.toggle("hidden", type !== "minimal_pairs");
  if (formES) formES.classList.toggle("hidden", type !== "monosyllables" && type !== "multisyllables");
  if (formNum) formNum.classList.toggle("hidden", type !== "numbers");
  if (formSent) formSent.classList.toggle("hidden", type !== "sentences");

  const esTitle = document.getElementById("formESTitle");
  if (esTitle) esTitle.textContent = type === "multisyllables" ? "📚 Mehrsilber-Felder" : "🔤 Einsilber-Felder";

  const categoryInput = document.getElementById("addCategory");
  const sourceInput = document.getElementById("addSource");

  updateCategoryDatalist(type);

  if (categoryInput) {
    const val = item.category || item.type || "";
    // Falls die Kategorie noch nicht in den Optionen existiert, füge sie temporär hinzu, damit sie selektiert werden kann.
    if (val && !Array.from(categoryInput.options).some(opt => opt.value === val)) {
      const opt = document.createElement("option");
      opt.value = val;
      opt.text = val;
      categoryInput.add(opt);
    }
    categoryInput.value = val;
  }
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

  updateLiveIPABadges();
  updateSentWordChips();

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
      editorCurrentPage = 1;
      renderEditorList();
    });
  }

  const categoryFilterSelect = document.getElementById("editorCategoryFilter");
  if (categoryFilterSelect) {
    categoryFilterSelect.addEventListener("change", (e) => {
      editorCategoryFilterValue = e.target.value;
      editorCurrentPage = 1;
      renderEditorList();
    });
  }

  // Sort Dropdown
  const editorSortSelect = document.getElementById("editorSortSelect");
  if (editorSortSelect) {
    editorSortSelect.addEventListener("change", (e) => {
      editorSortMode = e.target.value;
      editorCurrentPage = 1;
      renderEditorList();
    });
  }

  const addTypeSelect = document.getElementById("addTypeSelect");

  function showTypeFields(val) {
    ["formMP", "formES", "formNum", "formSent"].forEach(id => {
      document.getElementById(id)?.classList.add("hidden");
    });
    const map = {
      minimal_pairs: "formMP",
      monosyllables: "formES",
      multisyllables: "formES",
      numbers: "formNum",
      sentences: "formSent",
    };
    const target = map[val];
    if (target) document.getElementById(target)?.classList.remove("hidden");
    
    const esTitle = document.getElementById("formESTitle");
    if (esTitle) esTitle.textContent = val === "multisyllables" ? "📚 Mehrsilber-Felder" : "🔤 Einsilber-Felder";

    updateCategoryDatalist(val);
  }

  if (addTypeSelect) {
    addTypeSelect.addEventListener("change", (e) => showTypeFields(e.target.value));
    showTypeFields(addTypeSelect.value);
  }

  // Live IPA input listeners
  document.getElementById("addWordA")?.addEventListener("input", updateLiveIPABadges);
  document.getElementById("addWordB")?.addEventListener("input", updateLiveIPABadges);
  document.getElementById("addESWord")?.addEventListener("input", updateLiveIPABadges);
  document.getElementById("addSentTarget")?.addEventListener("input", updateLiveIPABadges);

  // Numbers auto spoken text
  const addNumVal = document.getElementById("addNumVal");
  const addNumSpoken = document.getElementById("addNumSpoken");
  if (addNumVal && addNumSpoken) {
    let lastAutoVal = "";
    addNumVal.addEventListener("input", (e) => {
      const converted = convertNumberToSpokenGerman(e.target.value);
      if (!addNumSpoken.value || addNumSpoken.value === lastAutoVal) {
        addNumSpoken.value = converted;
        lastAutoVal = converted;
      }
    });
    document.getElementById("autoGenerateNumTextBtn")?.addEventListener("click", () => {
      addNumSpoken.value = convertNumberToSpokenGerman(addNumVal.value);
      showToast("🪄 Gesprochener Text generiert!", "info");
    });
  }

  // Sentence text input & chips
  document.getElementById("addSentText")?.addEventListener("input", () => {
    updateSentWordChips();
  });
  document.getElementById("suggestSentOptionsBtn")?.addEventListener("click", suggestSentDistractors);

  // Form Audio Previews
  document.getElementById("previewWordABtn")?.addEventListener("click", () => {
    const val = document.getElementById("addWordA")?.value.trim();
    if (val) playTTS(val, "Wort A");
  });
  document.getElementById("previewWordBBtn")?.addEventListener("click", () => {
    const val = document.getElementById("addWordB")?.value.trim();
    if (val) playTTS(val, "Wort B");
  });
  document.getElementById("previewMPOptsBtn")?.addEventListener("click", () => {
    const val = document.getElementById("addMPOptions")?.value.trim();
    if (val) playTTS(val, "Optionen");
  });
  document.getElementById("previewESWordBtn")?.addEventListener("click", () => {
    const val = document.getElementById("addESWord")?.value.trim();
    if (val) playTTS(val, "Einsilber");
  });
  document.getElementById("previewNumBtn")?.addEventListener("click", () => {
    const val = document.getElementById("addNumSpoken")?.value.trim() || document.getElementById("addNumVal")?.value.trim();
    if (val) playTTS(val, "Zahl");
  });
  document.getElementById("previewSentBtn")?.addEventListener("click", () => {
    const val = document.getElementById("addSentText")?.value.trim();
    if (val) playTTS(val, "Satz");
  });
  document.getElementById("previewTargetBtn")?.addEventListener("click", () => {
    const val = document.getElementById("addSentTarget")?.value.trim();
    if (val) playTTS(val, "Zielwort");
  });

  // Save Exercise
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

    } else if (modType === "monosyllables" || modType === "multisyllables") {
      const word = document.getElementById("addESWord").value.trim();
      if (!word) {
        showToast("Bitte Wort eingeben!", "warning");
        return;
      }
      newItem.word = word;
      newItem.difficulty = "Mittel";
      if (modType === "multisyllables" && !newItem.syllable_count) {
        newItem.syllable_count = 2; // Default for Mehrsilber
      }

    } else if (modType === "numbers") {
      const val = document.getElementById("addNumVal").value.trim();
      const spoken = document.getElementById("addNumSpoken").value.trim() || convertNumberToSpokenGerman(val);
      if (!val) {
        showToast("Bitte Wert für die Zahl/Uhrzeit eingeben!", "warning");
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
    let apiModType = modType;
    if (apiModType === "multisyllables") apiModType = "monosyllables";
    
    const res = await fetch("/api/exercises", {
      method: isEdit ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mod_type: apiModType, item: newItem })
    });

    const data = await res.json();
    editorFormDirty = false;

    const serialMode = document.getElementById("serialModeCheck")?.checked;
    await loadExercises();

    if (serialMode && !isEdit) {
      clearItemSpecificFormFields(modType);
      showToast("✅ Gespeichert! Nächste Übung eingeben...", "success");
      focusFirstFormField(modType);
    } else {
      showToast(data.message || (isEdit ? "✅ Eintrag aktualisiert!" : "✅ Eintrag gespeichert!"), "success");
      resetEditorForm();
      switchEditorSubView("list", true);
    }
  });

  const filterBtns = document.querySelectorAll(".filter-tab-btn");
  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentEditorView = btn.dataset.view;
      editorCategoryFilterValue = "";
      editorCurrentPage = 1;
      populateEditorCategoryFilter();
      renderEditorList();
    });
  });

  // Modal actions
  initCategoryManager();
  initExportImport();
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

function populateEditorCategoryFilter() {
  const filterSelect = document.getElementById("editorCategoryFilter");
  if (!filterSelect) return;

  let rawList = [];
  if (currentEditorView === "multisyllables") {
    rawList = (exercises["monosyllables"] || []).filter(item => (item.syllable_count && item.syllable_count > 1) || item.category === "Mehrsilber & Komposita" || (item.category && item.category.includes("silbig")));
  } else if (currentEditorView === "monosyllables") {
    rawList = (exercises["monosyllables"] || []).filter(item => (!item.syllable_count || item.syllable_count === 1) && !item.category?.includes("silbig") && item.category !== "Mehrsilber & Komposita");
  } else {
    rawList = exercises[currentEditorView] || [];
  }
  const catCounts = {};
  rawList.forEach(item => {
    const cat = (item.category || item.type || "Allgemein").trim();
    catCounts[cat] = (catCounts[cat] || 0) + 1;
  });

  const hasCustom = rawList.some(item => isCustomEntry(item, currentEditorView));
  const customCount = rawList.filter(item => isCustomEntry(item, currentEditorView)).length;

  const sortedCats = Object.keys(catCounts).sort((a, b) => a.localeCompare(b));
  let html = `<option value="">🏷 Alle Kategorien (${rawList.length})</option>`;
  if (hasCustom) {
    const selected = (editorCategoryFilterValue === "MY_ENTRIES") ? "selected" : "";
    html += `<option value="MY_ENTRIES" ${selected}>⭐ Nur eigene Einträge (${customCount})</option>`;
  }
  sortedCats.forEach(cat => {
    const selected = (cat === editorCategoryFilterValue) ? "selected" : "";
    html += `<option value="${escapeHtml(cat)}" ${selected}>${escapeHtml(cat)} (${catCounts[cat]})</option>`;
  });

  filterSelect.innerHTML = html;
  if (editorCategoryFilterValue !== "MY_ENTRIES" && !sortedCats.includes(editorCategoryFilterValue)) {
    editorCategoryFilterValue = "";
  }
  filterSelect.value = editorCategoryFilterValue;
}

function renderEditorList() {
  updateEditorCounts();
  populateEditorCategoryFilter();

  const container = document.getElementById("editorExerciseList");
  const paginationContainer = document.getElementById("editorPagination");
  if (!container) return;

  let rawList = [];
  if (currentEditorView === "multisyllables") {
    rawList = (exercises["monosyllables"] || []).filter(item => (item.syllable_count && item.syllable_count > 1) || item.category === "Mehrsilber & Komposita" || (item.category && item.category.includes("silbig")));
  } else if (currentEditorView === "monosyllables") {
    rawList = (exercises["monosyllables"] || []).filter(item => (!item.syllable_count || item.syllable_count === 1) && !item.category?.includes("silbig") && item.category !== "Mehrsilber & Komposita");
  } else {
    rawList = exercises[currentEditorView] || [];
  }

  function getItemText(item, type) {
    if (type === "minimal_pairs") {
      return item.options ? item.options.join(", ") : `${item.word_a || ''} / ${item.word_b || ''}`;
    } else if (type === "monosyllables" || type === "multisyllables") {
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
    if (editorCategoryFilterValue === "MY_ENTRIES") {
      if (!isCustomEntry(item, currentEditorView)) return false;
    } else if (editorCategoryFilterValue) {
      const cat = (item.category || item.type || "Allgemein").trim();
      if (cat !== editorCategoryFilterValue) return false;
    }
    if (!editorSearchQuery) return true;
    const txt = getItemText(item, currentEditorView).toLowerCase();
    const cat = (item.category || item.type || "Allgemein").toLowerCase();
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
      const isCustom = isCustomEntry(item, currentEditorView);

      const itemJson = escapeHtml(JSON.stringify(item));

      return `
        <div class="exercise-item-card ${isCustom ? 'is-custom-entry' : ''}" data-id="${escapeHtml(item.id)}">
          <div class="item-info">
            <div class="item-main">
              ${escapeHtml(mainText)}
              ${isCustom ? `<span style="font-size:0.75rem; margin-left:0.4rem; color:#F59E0B;" title="Eigene Übung">⭐</span>` : ""}
            </div>
            <div class="item-meta" style="color: var(--text-muted); font-size: 0.82rem; margin-top: 0.35rem; display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
              <span style="opacity: 0.9;">🏷 ${escapeHtml(cat)}</span>
              ${hint ? `<span style="opacity: 0.5;">|</span><span style="opacity: 0.9;">💡 ${escapeHtml(hint)}</span>` : ""}
            </div>
          </div>
          <div class="item-actions">
            <button class="btn-icon-action play" data-item="${itemJson}" onclick="handlePlayClick(this)" title="Anhören">🔊</button>
            <button class="btn-icon-action edit" data-item="${itemJson}" onclick="handleEditClick(this)" title="Bearbeiten">✏️</button>
            <button class="btn-icon-action copy" data-item="${itemJson}" onclick="handleCopyClick(this)" title="Duplizieren">📑</button>
            <button class="btn-icon-action delete" onclick="deleteExerciseItem('${currentEditorView}', '${escapeHtml(item.id)}', this.closest('.exercise-item-card'))" title="Löschen" style="color: #F87171;">🗑️</button>
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
  try {
    const item = JSON.parse(btn.dataset.item);
    openFormForEdit(currentEditorView, item);
  } catch (e) {
    console.error("handleEditClick parse error:", e);
    showToast("Fehler beim Öffnen des Eintrags.", "danger");
  }
}
window.handleEditClick = handleEditClick;

function handleCopyClick(btn) {
  try {
    const item = JSON.parse(btn.dataset.item);
    duplicateExerciseItem(currentEditorView, item);
  } catch (e) {
    console.error("handleCopyClick parse error:", e);
    showToast("Fehler beim Kopieren des Eintrags.", "danger");
  }
}
window.handleCopyClick = handleCopyClick;

function duplicateExerciseItem(type, item) {
  const copy = { ...item };
  delete copy.id;
  openFormForEdit(type, copy);
  showToast("📋 Kopie erstellt – bitte bearbeiten und speichern.", "info");
}

async function deleteExerciseItem(type, id, cardEl) {
  const deleteBtn = cardEl ? cardEl.querySelector(".item-actions .delete") : null;
  if (deleteBtn && !deleteBtn.dataset.confirmed) {
    const orig = deleteBtn.innerHTML;
    deleteBtn.innerHTML = "⚠️ Sicher?";
    deleteBtn.style.cssText = "padding:0.3rem 0.6rem; font-size:0.8rem; color:#FBBF24; border-color:#FBBF24; cursor:pointer; font-weight:700;";
    deleteBtn.dataset.confirmed = "1";
    setTimeout(() => {
      if (deleteBtn.dataset.confirmed) {
        deleteBtn.innerHTML = orig;
        deleteBtn.style.cssText = "";
        delete deleteBtn.dataset.confirmed;
      }
    }, 3000);
    return;
  }
  if (deleteBtn) delete deleteBtn.dataset.confirmed;

  let apiModType = type;
  if (apiModType === "multisyllables") apiModType = "monosyllables";

  const res = await fetch("/api/exercises", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mod_type: apiModType, item_id: id })
  });

  if (!res.ok) {
    showToast("Fehler beim Löschen!", "danger");
    return;
  }
  showToast("🗑 Eintrag gelöscht.", "warning", 2500);
  await loadExercises();
}
window.deleteExerciseItem = deleteExerciseItem;

// ─── CATEGORY MANAGER MODAL ──────────────────────────────────────────────────
function getCustomCategories() {
  try { return JSON.parse(localStorage.getItem('ci_custom_categories')) || {}; }
  catch (e) { return {}; }
}
function saveCustomCategory(modType, catName) {
  let cc = getCustomCategories();
  if (!cc[modType]) cc[modType] = [];
  if (!cc[modType].includes(catName)) {
    cc[modType].push(catName);
    localStorage.setItem('ci_custom_categories', JSON.stringify(cc));
  }
}
function removeCustomCategory(modType, catName) {
  let cc = getCustomCategories();
  if (cc[modType]) {
    cc[modType] = cc[modType].filter(c => c !== catName);
    localStorage.setItem('ci_custom_categories', JSON.stringify(cc));
  }
}

function initCategoryManager() {
  const modal = document.getElementById("categoryManagerModal");
  const closeBtn = document.getElementById("closeCatModalBtn");
  const closeFooterBtn = document.getElementById("closeCatModalFooterBtn");
  const addCategoryBtn = document.getElementById("addCategoryBtn");
  const newCategoryInput = document.getElementById("newCategoryInput");

  function openModal() {
    if (!modal) return;
    renderCategoryManagerList();
    modal.classList.remove("hidden");
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.add("hidden");
  }

  window.openCategoryManager = openModal;
  window.closeCategoryManager = closeModal;

  if (addCategoryBtn && newCategoryInput) {
    addCategoryBtn.addEventListener("click", () => {
      const val = newCategoryInput.value.trim();
      if (!val) return;
      let baseModType = currentEditorView;
      if (baseModType === "multisyllables") baseModType = "monosyllables";
      saveCustomCategory(baseModType, val);
      newCategoryInput.value = "";
      renderCategoryManagerList();
      updateCategoryDatalist(currentEditorView);
      showToast(`Kategorie '${val}' hinzugefügt!`, "success");
    });
    newCategoryInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") addCategoryBtn.click();
    });
  }

  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (closeFooterBtn) closeFooterBtn.addEventListener("click", closeModal);
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeModal();
    });
  }
}

function renderCategoryManagerList() {
  const listContainer = document.getElementById("categoryManagerList");
  const titleEl = document.getElementById("catModalTitle");
  if (!listContainer) return;

  const modNames = {
    minimal_pairs: "🎭 Minimalpaare",
    monosyllables: "🔤 Einsilber",
    multisyllables: "📚 Mehrsilber",
    numbers: "🔢 Zahlen & Uhrzeiten",
    sentences: "💬 Satzverständnis"
  };
  if (titleEl) titleEl.textContent = `🏷️ Kategorien verwalten (${modNames[currentEditorView] || currentEditorView})`;

  let baseModType = currentEditorView;
  if (baseModType === "multisyllables") baseModType = "monosyllables";

  let rawList = [];
  if (currentEditorView === "multisyllables") {
    rawList = (exercises["monosyllables"] || []).filter(item => (item.syllable_count && item.syllable_count > 1) || item.category === "Mehrsilber & Komposita" || (item.category && item.category.includes("silbig")));
  } else if (currentEditorView === "monosyllables") {
    rawList = (exercises["monosyllables"] || []).filter(item => (!item.syllable_count || item.syllable_count === 1) && !item.category?.includes("silbig") && item.category !== "Mehrsilber & Komposita");
  } else {
    rawList = exercises[currentEditorView] || [];
  }
  
  const catMap = {};
  rawList.forEach(item => {
    const cat = (item.category || item.type || "Allgemein").trim();
    if (!catMap[cat]) catMap[cat] = { total: 0, custom: 0 };
    catMap[cat].total++;
    if (isCustomEntry(item, baseModType)) catMap[cat].custom++;
  });

  const customCats = getCustomCategories()[baseModType] || [];
  customCats.forEach(cat => {
    if (!catMap[cat]) catMap[cat] = { total: 0, custom: 0 };
  });

  const sortedCats = Object.keys(catMap).sort((a, b) => a.localeCompare(b));
  if (sortedCats.length === 0) {
    listContainer.innerHTML = `<div style="text-align:center; padding:1.5rem; color:var(--text-muted);">Keine Kategorien vorhanden.</div>`;
    return;
  }

  listContainer.innerHTML = sortedCats.map(cat => {
    const info = catMap[cat];
    const isPureCustom = info.custom === info.total;
    return `
      <div class="cat-manager-row">
        <div class="cat-manager-title">
          <span>🏷️ ${escapeHtml(cat)}</span>
          <span style="font-size:0.75rem; color:var(--text-muted);">(${info.total} Übungen${info.custom > 0 ? `, ${info.custom} eigene` : ''})</span>
        </div>
        <div class="cat-manager-actions">
          <button class="btn btn-secondary btn-sm" onclick="promptRenameCategory('${escapeHtml(cat)}')">✏️ Umbenennen</button>
          ${(info.custom > 0 || info.total === 0) ? `<button class="btn btn-danger btn-sm" onclick="promptDeleteCategory('${escapeHtml(cat)}', ${info.total === 0})">🗑️ Löschen</button>` : ''}
        </div>
      </div>
    `;
  }).join("");
}

async function promptRenameCategory(oldCat) {
  const newCat = prompt(`Kategorie '${oldCat}' umbenennen in:`, oldCat);
  if (!newCat || newCat.trim() === "" || newCat.trim() === oldCat) return;

  try {
    let baseModType = currentEditorView;
    if (baseModType === "multisyllables") baseModType = "monosyllables";

    let cc = getCustomCategories();
    if (cc[baseModType] && cc[baseModType].includes(oldCat)) {
      cc[baseModType] = cc[baseModType].map(c => c === oldCat ? newCat.trim() : c);
      localStorage.setItem('ci_custom_categories', JSON.stringify(cc));
    }

    const res = await fetch("/api/categories/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mod_type: baseModType,
        old_category: oldCat,
        new_category: newCat.trim()
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || "✅ Kategorie umbenannt!", "success");
      await loadExercises();
      renderCategoryManagerList();
      updateCategoryDatalist(currentEditorView);
    } else {
      showToast(data.message || "Fehler beim Umbenennen.", "danger");
    }
  } catch (e) {
    showToast("Netzwerkfehler beim Umbenennen.", "danger");
  }
}
window.promptRenameCategory = promptRenameCategory;

async function promptDeleteCategory(cat, isPureCustom) {
  const confirmMsg = isPureCustom
    ? `Möchtest du die Kategorie '${cat}' und alle darin enthaltenen eigenen Übungen wirklich löschen?`
    : `Möchtest du alle eigenen Übungen aus der Kategorie '${cat}' löschen? (Standard-Übungen bleiben erhalten)`;

  if (!confirm(confirmMsg)) return;

  try {
    const res = await fetch("/api/categories/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mod_type: currentEditorView,
        category: cat,
        only_custom: true
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || "🗑️ Kategorie gelöscht.", "warning");
      await loadExercises();
      renderCategoryManagerList();
    } else {
      showToast(data.message || "Fehler beim Löschen.", "danger");
    }
  } catch (e) {
    showToast("Netzwerkfehler beim Löschen.", "danger");
  }
}
window.promptDeleteCategory = promptDeleteCategory;

// ─── EXPORT & IMPORT ─────────────────────────────────────────────────────────
function initExportImport() {
  const fileInput = document.getElementById("importFileInput");
  const moreOptions = document.getElementById("editorMoreOptions");

  if (moreOptions) {
    moreOptions.addEventListener("change", (e) => {
      const action = e.target.value;
      if (action === "export") {
        exportExercisesAsJSON();
      } else if (action === "import" && fileInput) {
        fileInput.click();
      }
      e.target.value = ""; // reset dropdown
    });
  }

  const manageCatsBtn = document.getElementById("manageCategoriesBtn");
  if (manageCatsBtn) {
    manageCatsBtn.addEventListener("click", () => {
      if (window.openCategoryManager) window.openCategoryManager();
    });
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        importExercisesFromJSON(file);
        fileInput.value = "";
      }
    });
  }
}

function exportExercisesAsJSON() {
  const customExercises = {};
  let totalCustom = 0;

  for (const modType of ["minimal_pairs", "monosyllables", "numbers", "sentences"]) {
    const list = (exercises[modType] || []).filter(item => isCustomEntry(item, modType));
    customExercises[modType] = list;
    totalCustom += list.length;
  }

  if (totalCustom === 0) {
    showToast("ℹ️ Keine eigenen/individuellen Übungen zum Exportieren vorhanden.", "info", 3500);
    return;
  }

  const exportData = {
    version: "2.3",
    exported_at: new Date().toISOString(),
    description: "CI-Hörtrainer Benutzerdefinierte Übungen & Eigene Kategorien",
    custom_only: true,
    total_exercises: totalCustom,
    exercises: customExercises
  };

  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(exportData, null, 2));
  const downloadAnchor = document.createElement("a");
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `ci_eigene_kategorien_export_${new Date().toISOString().slice(0, 10)}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
  showToast(`📤 ${totalCustom} individuelle Übung(en) erfolgreich exportiert!`, "success");
}

function importExercisesFromJSON(file) {
  const reader = new FileReader();
  reader.onload = async (event) => {
    try {
      const json = JSON.parse(event.target.result);
      const exData = json.exercises || json;

      let totalImported = 0;
      let totalSkippedStandard = 0;

      for (const modType of ["minimal_pairs", "monosyllables", "numbers", "sentences"]) {
        const rawItems = exData[modType];
        if (!Array.isArray(rawItems) || rawItems.length === 0) continue;

        // Strictly filter to ONLY individual/custom entries (skip all standard catalog items)
        const customItems = rawItems.filter(item => {
          if (!item || typeof item !== "object") return false;
          const isStandard = !isCustomEntry(item, modType);
          if (isStandard) {
            totalSkippedStandard++;
            return false;
          }
          return true;
        });

        if (customItems.length > 0) {
          const res = await fetch("/api/exercises/bulk", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mod_type: modType, items: customItems })
          });
          if (res.ok) {
            const d = await res.json();
            totalImported += (d.count || customItems.length);
          }
        }
      }

      if (totalImported > 0) {
        const skippedNote = totalSkippedStandard > 0 ? ` (${totalSkippedStandard} Standard-Übungen wurden übersprungen)` : "";
        showToast(`📥 ${totalImported} individuelle Übung(en) erfolgreich importiert!${skippedNote}`, "success", 4000);
        await loadExercises();
        renderEditorList();
      } else {
        showToast("ℹ️ Keine individuellen/eigenen Übungen in der Datei gefunden. Standard-Kategorien werden nicht importiert.", "info", 4500);
      }
    } catch (err) {
      console.error("JSON Import Fehler:", err);
      showToast("Fehler beim Lesen der JSON-Datei! Bitte überprüfe das Dateiformat.", "danger");
    }
  };
  reader.readAsText(file);
}

let activeMicTab = "es";
let isVoiceRecordingActive = false;
let globalRec = null;
let persistentMicStream = null;

async function getOrInitMicStream() {
  if (persistentMicStream && persistentMicStream.active && persistentMicStream.getAudioTracks().some(t => t.readyState === "live")) {
    return persistentMicStream;
  }
  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      persistentMicStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: false,
          autoGainControl: true
        }
      });
      return persistentMicStream;
    }
  } catch (err) {
    console.warn("Could not get microphone stream for visualizer:", err);
  }
  return null;
}

function startVoiceInput(tabName = "es", isManual = true) {
  if (!isManual && !isAutoMicActive(tabName)) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    if (isManual) {
      showToast("🎙 Spracherkennung wird in diesem Browser leider nicht unterstützt (Empfehlung: Google Chrome, Edge oder Safari).", "warning");
    }
    return;
  }

  // Determine button and input element
  let micBtn = null;
  let inputEl = null;
  activeMicTab = tabName;

  if (tabName === "es") {
    micBtn = document.getElementById("esMicBtn");
    inputEl = document.getElementById("esInput");
  } else if (tabName === "ms") {
    micBtn = document.getElementById("msMicBtn");
    inputEl = document.getElementById("msInput");
  } else if (tabName === "num") {
    micBtn = document.getElementById("numMicBtn");
    inputEl = document.getElementById("numInput");
  } else if (tabName === "noise") {
    micBtn = document.getElementById("noiseMicBtn");
    inputEl = document.getElementById("noiseInput");
  } else if (tabName === "sentFull" || tabName === "sent") {
    micBtn = document.getElementById("sentFullMicBtn");
    inputEl = document.getElementById("sentFullInput");
  } else if (tabName === "weakness") {
    inputEl = document.getElementById("weaknessInput");
  }

  // If already recording and user clicks manually again -> stop
  if (isManual && isVoiceRecordingActive) {
    isVoiceRecordingActive = false;
    if (globalRec) {
      try { globalRec.abort(); } catch (e) {}
      globalRec = null;
    }
    resetMicButtons();
    setStatus("🎙 Mikrofon gestoppt.");
    return;
  }

  // For fresh or automated recording, clean up any previous instance first
  if (globalRec) {
    try { globalRec.abort(); } catch (e) {}
    globalRec = null;
  }
  isVoiceRecordingActive = false;

  isVoiceRecordingActive = true;
  if (maskNoise || ambientNoise) {
    fetch("/api/noise/stop", { method: "POST" }).catch(() => {});
  }
  if (micBtn) {
    micBtn.classList.add("recording");
    micBtn.innerHTML = "🔴 Höre zu...";
  }
  setStatus("🔴 Mikrofon aktiv: Bitte jetzt sprechen!");
  
  // Connect live mic stream to real-time audio spectrum
  getOrInitMicStream().then(stream => {
    if (stream && isVoiceRecordingActive) {
      startMicVisualizer(stream);
    } else {
      triggerWaveform(7.5);
    }
  }).catch(() => {
    triggerWaveform(7.5);
  });

  let silenceTimer = null;
  let maxListenTimer = null;
  let hasResult = false;

  // Max listening safety timeout (7.5s)
  maxListenTimer = setTimeout(() => {
    if (isVoiceRecordingActive && !hasResult) {
      isVoiceRecordingActive = false;
      if (globalRec) {
        try { globalRec.stop(); } catch (e) {}
        globalRec = null;
      }
      resetMicButtons();
      setStatus("Bereit.");
    }
  }, 7500);

  function createAndStartRec() {
    if (!isVoiceRecordingActive) return;

    if (globalRec) {
      try { globalRec.abort(); } catch (e) {}
      globalRec = null;
    }

    const rec = new SpeechRecognition();
    rec.lang = "de-DE";
    rec.continuous = false;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      if (micBtn && isVoiceRecordingActive) {
        micBtn.classList.add("recording");
        micBtn.innerHTML = "🔴 Höre zu...";
      }
    };

    rec.onresult = (e) => {
      let finalTranscript = "";
      let interimTranscript = "";

      for (let i = 0; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) {
          finalTranscript += (finalTranscript ? " " : "") + res[0].transcript.trim();
        } else {
          interimTranscript += (interimTranscript ? " " : "") + res[0].transcript.trim();
        }
      }

      const bestText = (finalTranscript || interimTranscript).trim();
      if (bestText && inputEl) {
        hasResult = true;
        inputEl.value = bestText;
        setStatus(`🔴 Gehört: '${bestText}'`);

        clearTimeout(silenceTimer);
        clearTimeout(maxListenTimer);
        silenceTimer = setTimeout(() => {
          isVoiceRecordingActive = false;
          try { rec.stop(); } catch (err) {}
          resetMicButtons();
          if (activeMicTab === "es") checkESAnswer();
          else if (activeMicTab === "ms") checkMSAnswer();
          else if (activeMicTab === "num") checkNumAnswer();
          else if (activeMicTab === "noise") checkNoiseAnswer();
          else if (activeMicTab === "sentFull" || activeMicTab === "sent") checkSentFullAnswer();
          else if (activeMicTab === "weakness" && currentWeaknessItem && currentWeaknessItem.mod_type !== "minimal_pairs" && currentWeaknessItem.mod_type !== "sentences") checkWeaknessAnswer(bestText);
        }, 900);
      }
    };

    rec.onerror = (e) => {
      console.log("Speech recognition status:", e.error);
      if (e.error === "not-allowed") {
        isVoiceRecordingActive = false;
        clearTimeout(silenceTimer);
        clearTimeout(maxListenTimer);
        resetMicButtons();
        showToast("🎙 Mikrofon-Zugriff nicht erlaubt. Bitte Berechtigung im Browser erteilen!", "danger");
      }
    };

    rec.onend = () => {
      if (isVoiceRecordingActive && !hasResult) {
        setTimeout(() => {
          if (isVoiceRecordingActive && !hasResult) {
            createAndStartRec();
          }
        }, 80);
      } else if (!isVoiceRecordingActive) {
        resetMicButtons();
      }
    };

    globalRec = rec;
    try {
      rec.start();
    } catch (err) {
      console.warn("Rec start notice:", err);
    }
  }

  createAndStartRec();
}

function resetMicButtons() {
  isVoiceRecordingActive = false;
  stopMicVisualizer();
  const btns = [
    document.getElementById("esMicBtn"),
    document.getElementById("msMicBtn"),
    document.getElementById("numMicBtn"),
    document.getElementById("noiseMicBtn"),
    document.getElementById("sentFullMicBtn")
  ];
  btns.forEach(btn => {
    if (btn) {
      btn.classList.remove("recording");
      btn.innerHTML = "🎙 Nachsprechen";
    }
  });
  initCanvasVisualizer();
  if (maskNoise || ambientNoise) {
    syncNoiseConfig();
  }
}

function startAutoMic(tabName = "es") {
  startVoiceInput(tabName, false);
}

// Browser Web Speech Recognition (Native German Speech-to-Text)
function initSpeechRecognition() {
  const esMicBtn = document.getElementById("esMicBtn");
  if (esMicBtn) {
    esMicBtn.addEventListener("click", (e) => {
      e.preventDefault();
      startVoiceInput("es", true);
    });
  }

  const msMicBtn = document.getElementById("msMicBtn");
  if (msMicBtn) {
    msMicBtn.addEventListener("click", (e) => {
      e.preventDefault();
      startVoiceInput("ms", true);
    });
  }

  const numMicBtn = document.getElementById("numMicBtn");
  if (numMicBtn) {
    numMicBtn.addEventListener("click", (e) => {
      e.preventDefault();
      startVoiceInput("num", true);
    });
  }

  const noiseMicBtn = document.getElementById("noiseMicBtn");
  if (noiseMicBtn) {
    noiseMicBtn.addEventListener("click", (e) => {
      e.preventDefault();
      startVoiceInput("noise", true);
    });
  }

  const sentFullMicBtn = document.getElementById("sentFullMicBtn");
  if (sentFullMicBtn) {
    sentFullMicBtn.addEventListener("click", (e) => {
      e.preventDefault();
      startVoiceInput("sentFull", true);
    });
  }
}

// ─── Real-Time Web Audio Visualizer (FFT Spectrum & Waveform) ────────────────
let audioCtx = null;
let analyserNode = null;
let visualizerAnimFrame = null;
let currentSourceNode = null;
let micMediaStream = null;
let micSourceNode = null;

function getAudioContext() {
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
      analyserNode = audioCtx.createAnalyser();
      analyserNode.fftSize = 256;
      analyserNode.smoothingTimeConstant = 0.8;
    }
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume();
  }
  return audioCtx;
}

// Canvas Waveform Visualizer - Idle State
function initCanvasVisualizer() {
  const canvas = document.getElementById("waveformCanvas");
  const statusEl = document.getElementById("visStatus");
  if (statusEl) {
    statusEl.textContent = "Bereit";
    statusEl.style.color = "var(--text-muted)";
  }
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.clearRect(0, 0, width, height);

  // Subtle center baseline with soft ambient gradient
  const midY = height / 2;
  const grad = ctx.createLinearGradient(0, 0, width, 0);
  grad.addColorStop(0, "rgba(59, 130, 246, 0.05)");
  grad.addColorStop(0.5, "rgba(59, 130, 246, 0.35)");
  grad.addColorStop(1, "rgba(59, 130, 246, 0.05)");

  ctx.beginPath();
  ctx.moveTo(0, midY);
  ctx.lineTo(width, midY);
  ctx.strokeStyle = grad;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

async function visualizeAudioFile(audioUrl) {
  return new Promise(async (resolve) => {
    try {
      const ctx = getAudioContext();
      if (!ctx || !analyserNode) {
        triggerWaveform(2.0);
        setTimeout(resolve, 2000);
        return;
      }

      if (currentSourceNode) {
        try { currentSourceNode.stop(); } catch (e) {}
        try { currentSourceNode.disconnect(); } catch (e) {}
        currentSourceNode = null;
      }

      const response = await fetch(audioUrl);
      const arrayBuffer = await response.arrayBuffer();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);

      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyserNode);

      // Silent gain node so the audio signal flows through analyser without speaker conflict
      const silentGain = ctx.createGain();
      silentGain.gain.value = 0.0;
      analyserNode.connect(silentGain);
      silentGain.connect(ctx.destination);

      currentSourceNode = source;

      const statusEl = document.getElementById("visStatus");
      if (statusEl) {
        statusEl.textContent = "🔊 Audio aktiv";
        statusEl.style.color = "var(--primary-light, #60A5FA)";
      }

      startRealtimeVisualizerLoop();

      let isDone = false;
      const finish = () => {
        if (!isDone) {
          isDone = true;
          if (currentSourceNode === source) {
            currentSourceNode = null;
            stopVisualizerLoop();
          }
          resolve();
        }
      };

      source.onended = finish;
      source.start(0);

      // Fallback timeout matching audio duration + 200ms
      setTimeout(finish, Math.round(audioBuffer.duration * 1000) + 200);
    } catch (err) {
      console.warn("Realtime visualizer notice:", err);
      triggerWaveform(2.0);
      setTimeout(resolve, 2000);
    }
  });
}

async function startMicVisualizer(stream) {
  try {
    const ctx = getAudioContext();
    if (!ctx || !analyserNode || !stream) return;

    if (micSourceNode) {
      try { micSourceNode.disconnect(); } catch (e) {}
      micSourceNode = null;
    }

    micSourceNode = ctx.createMediaStreamSource(stream);
    micSourceNode.connect(analyserNode);

    const statusEl = document.getElementById("visStatus");
    if (statusEl) {
      statusEl.textContent = "🎙 Mikrofon live";
      statusEl.style.color = "#F43F5E";
    }

    startRealtimeVisualizerLoop();
  } catch (err) {
    console.warn("Mic visualizer notice:", err);
  }
}

function stopMicVisualizer() {
  if (micSourceNode) {
    try { micSourceNode.disconnect(); } catch (e) {}
    micSourceNode = null;
  }
  stopVisualizerLoop();
}

function startRealtimeVisualizerLoop() {
  if (visualizerAnimFrame) {
    cancelAnimationFrame(visualizerAnimFrame);
  }

  const canvas = document.getElementById("waveformCanvas");
  if (!canvas || !analyserNode) return;
  const canvasCtx = canvas.getContext("2d");

  const bufferLength = analyserNode.frequencyBinCount;
  const freqData = new Uint8Array(bufferLength);
  const timeData = new Uint8Array(bufferLength);

  function renderFrame() {
    visualizerAnimFrame = requestAnimationFrame(renderFrame);

    analyserNode.getByteFrequencyData(freqData);
    analyserNode.getByteTimeDomainData(timeData);

    const width = canvas.width;
    const height = canvas.height;

    canvasCtx.clearRect(0, 0, width, height);

    const isMicActive = !!micSourceNode;

    // 1. Draw Real-Time FFT Frequency Spectrum Bars (Background)
    const barCount = 54;
    const barWidth = width / barCount;
    const step = Math.max(1, Math.floor(bufferLength / barCount));

    for (let i = 0; i < barCount; i++) {
      const val = freqData[i * step] || 0;
      const barHeight = (val / 255) * height * 0.92;

      if (barHeight > 1) {
        // Cyan-to-Purple for TTS, Vibrant Coral-to-Fuchsia for Microphone
        const hue = isMicActive ? (335 + (i / barCount) * 55) : (195 + (i / barCount) * 75);
        const grad = canvasCtx.createLinearGradient(0, height, 0, height - barHeight);
        grad.addColorStop(0, `hsla(${hue}, 90%, 55%, 0.2)`);
        grad.addColorStop(0.7, `hsla(${hue}, 95%, 65%, 0.6)`);
        grad.addColorStop(1, `hsla(${hue}, 100%, 75%, 0.95)`);

        canvasCtx.fillStyle = grad;
        canvasCtx.fillRect(i * barWidth + 1, height - barHeight, Math.max(1, barWidth - 2), barHeight);
      }
    }

    // 2. Draw Real-Time Time-Domain Waveform (Foreground Overlay)
    canvasCtx.beginPath();
    canvasCtx.lineWidth = 2.2;
    canvasCtx.strokeStyle = isMicActive ? "#FB7185" : "#38BDF8";
    canvasCtx.shadowBlur = 10;
    canvasCtx.shadowColor = isMicActive ? "#E11D48" : "#0284C7";

    const sliceWidth = width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = timeData[i] / 128.0;
      const y = (v * height) / 2;

      if (i === 0) {
        canvasCtx.moveTo(x, y);
      } else {
        canvasCtx.lineTo(x, y);
      }

      x += sliceWidth;
    }

    canvasCtx.stroke();
    canvasCtx.shadowBlur = 0;
  }

  renderFrame();
}

function stopVisualizerLoop() {
  if (visualizerAnimFrame) {
    cancelAnimationFrame(visualizerAnimFrame);
    visualizerAnimFrame = null;
  }
  initCanvasVisualizer();
}

// Fallback Synthetic Waveform Trigger
function triggerWaveform(durationSec = 2.5) {
  const canvas = document.getElementById("waveformCanvas");
  const statusEl = document.getElementById("visStatus");
  if (statusEl) {
    statusEl.textContent = "🔊 Audio aktiv";
    statusEl.style.color = "var(--primary-light, #60A5FA)";
  }
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
      const amp = Math.sin(x * 0.04 + elapsed * 12) * Math.cos(x * 0.015) * (canvas.height * 0.35) * (1 - elapsed / durationSec);
      if (x === 0) ctx.moveTo(x, cy + amp);
      else ctx.lineTo(x, cy + amp);
    }

    ctx.strokeStyle = "#3B82F6";
    ctx.lineWidth = 2;
    ctx.shadowBlur = 6;
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
    await loadTrainingLogs();
  } catch (e) {
    console.log("Error loading stats:", e);
  }
}

// ─── Training Logs Management ──────────────────────────────────────────────
async function loadTrainingLogs() {
  const tbody = document.getElementById("trainingLogsTbody");
  const countEl = document.getElementById("logsCountText");
  const modFilter = document.getElementById("logFilterModule")?.value || "";
  const statusFilter = document.getElementById("logFilterStatus")?.value || "";
  if (!tbody) return;

  try {
    const query = new URLSearchParams();
    query.set("limit", "100");
    if (modFilter) query.set("module", modFilter);
    if (statusFilter) query.set("status", statusFilter);

    const res = await fetch(`/api/logs?${query.toString()}`);
    const data = await res.json();
    renderTrainingLogs(data);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1rem; color:var(--text-muted);">Fehler beim Laden des Protokolls.</td></tr>`;
  }
}

function renderTrainingLogs(data) {
  const tbody = document.getElementById("trainingLogsTbody");
  const countEl = document.getElementById("logsCountText");
  if (!tbody) return;

  const logs = data.logs || [];
  if (countEl) countEl.textContent = `${logs.length} von ${data.total || logs.length} Einträgen angezeigt`;

  if (logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:var(--text-muted);">Keine Protokolleinträge gefunden.</td></tr>`;
    return;
  }

  tbody.innerHTML = logs.map(log => {
    let timeStr = "";
    try {
      const d = new Date(log.timestamp);
      timeStr = isNaN(d.getTime()) ? log.timestamp : d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      timeStr = log.timestamp || "";
    }

    const isCorrect = log.is_correct;
    const badgeStyle = isCorrect
      ? "background:rgba(16,185,129,0.15); color:#34D399; border:1px solid rgba(16,185,129,0.3);"
      : "background:rgba(239,68,68,0.15); color:#F87171; border:1px solid rgba(239,68,68,0.3);";

    return `
      <tr style="border-bottom:1px solid rgba(255,255,255,0.05);">
        <td style="padding:0.45rem 0.6rem; color:var(--text-muted); font-size:0.8rem; white-space:nowrap;">${escapeHtml(timeStr)}</td>
        <td style="padding:0.45rem 0.6rem; font-weight:600; color:#60A5FA;">${escapeHtml(log.module || '-')}</td>
        <td style="padding:0.45rem 0.6rem; color:var(--text-main);">${escapeHtml(log.category || '-')}</td>
        <td style="padding:0.45rem 0.6rem; font-weight:700; color:#FCD34D;">${escapeHtml(log.target_word || '-')}</td>
        <td style="padding:0.45rem 0.6rem; color:var(--text-muted);">${escapeHtml(log.user_answer || '-')}</td>
        <td style="padding:0.45rem 0.6rem; text-align:center;">
          <span style="display:inline-block; padding:0.2rem 0.5rem; border-radius:6px; font-size:0.75rem; font-weight:700; ${badgeStyle}">
            ${isCorrect ? '✅ Richtig' : '❌ Falsch'}
          </span>
        </td>
        <td style="padding:0.45rem 0.6rem; text-align:right;">
          <button class="btn-icon-action" onclick="deleteTrainingLogItem(${log.id})" title="Diesen Eintrag löschen" style="color:#EF4444; padding:0.2rem 0.4rem; font-size:0.85rem;">🗑️</button>
        </td>
      </tr>
    `;
  }).join("");
}

async function deleteTrainingLogItem(logId) {
  if (!confirm("Möchtest du diesen Eintrag aus dem Protokoll löschen?")) return;
  try {
    const res = await fetch("/api/logs/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: logId })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast("🗑 Eintrag aus Protokoll gelöscht.", "warning", 2000);
      await updateStats();
    } else {
      showToast(data.message || "Fehler beim Löschen.", "danger");
    }
  } catch (e) {
    showToast("Netzwerkfehler beim Löschen.", "danger");
  }
}
window.deleteTrainingLogItem = deleteTrainingLogItem;

function initTrainingLogsListeners() {
  document.getElementById("logFilterModule")?.addEventListener("change", loadTrainingLogs);
  document.getElementById("logFilterStatus")?.addEventListener("change", loadTrainingLogs);
  document.getElementById("refreshLogsBtn")?.addEventListener("click", loadTrainingLogs);
  document.getElementById("clearAllLogsBtn")?.addEventListener("click", async () => {
    if (confirm("Möchtest du wirklich das GESAMTE Übungsprotokoll und alle Statistiken leeren?")) {
      await resetStats();
    }
  });
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

// ── APP BEENDEN (EXIT) ───────────────────────────────────────────────────────

function initExitButton() {
  const exitBtn = document.getElementById("exitAppBtn");
  if (!exitBtn) return;
  exitBtn.addEventListener("click", handleAppExit);
}

async function handleAppExit() {
  const confirmed = confirm("Möchten Sie den CI-Hörtrainer wirklich beenden?");
  if (!confirmed) return;

  showToast("🛑 CI-Hörtrainer wird beendet...", "warning", 8000);
  setStatus("Server wird beendet...");

  try {
    await fetch("/api/shutdown", {
      method: "POST",
      headers: { "Content-Type": "application/json" }
    });
  } catch (e) {
    console.log("Server shutdown initiated");
  }

  // Zeige saubere Abschlussmeldung im Fenster
  document.body.innerHTML = `
    <div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: #0B0F19;
      color: #E2E8F0;
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      text-align: center;
      padding: 2rem;
    ">
      <div style="
        background: rgba(30, 41, 59, 0.85);
        border: 1px solid rgba(239, 68, 68, 0.4);
        border-radius: 20px;
        padding: 3rem 2.5rem;
        max-width: 520px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      ">
        <div style="font-size: 3.5rem; margin-bottom: 1.2rem; line-height: 1;">🛑</div>
        <h1 style="font-size: 1.8rem; margin-bottom: 0.8rem; font-weight: 800; color: #FFFFFF; font-family: 'Outfit', sans-serif;">CI-Hörtrainer beendet</h1>
        <p style="color: #94A3B8; font-size: 1rem; line-height: 1.6; margin-bottom: 1.5rem;">
          Das Hörtrainings-Programm und der lokale Server wurden ordnungsgemäß heruntergefahren.
        </p>
        <p style="color: #64748B; font-size: 0.88rem; border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 1.2rem; margin: 0;">
          Sie können diesen Browser-Tab bzw. dieses Fenster nun schließen.
        </p>
      </div>
    </div>
  `;

  setTimeout(() => {
    window.close();
  }, 400);
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
  cancelAutoAdvance();
  const tab = getActiveTab();
  if (tab === "mp") playMPAudio();
  else if (tab === "es") playESAudio();
  else if (tab === "ms") playMSAudio();
  else if (tab === "num") playNumAudio();
  else if (tab === "sent" || tab === "sentences") playSentAudio();
  else if (tab === "weakness") playWeaknessAudio();
  else if (tab === "noise") playNoiseAudio();
  else if (tab === "memory") playMemoryAudio();
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
  } else if (tab === "weakness") {
    const opts = document.querySelectorAll("#weaknessExerciseArea .option-card");
    if (opts && opts[index]) {
      opts[index].click();
    }
  } else if (tab === "memory") {
    const btns = document.querySelectorAll("#memoryPoolGrid .option-card:not([disabled])");
    if (btns && btns[index]) {
      btns[index].click();
    }
  }
}

function nextExerciseItem() {
  const tab = getActiveTab();
  if (tab === "mp") nextMPItem(true);
  else if (tab === "es") nextESItem(true);
  else if (tab === "ms") nextMSItem(true);
  else if (tab === "num") nextNumItem(true);
  else if (tab === "sent" || tab === "sentences") nextSentItem(true);
  else if (tab === "weakness") nextWeaknessItem(true);
  else if (tab === "noise") nextNoiseItem(true);
  else if (tab === "memory") nextMemoryItem(true);
  showToast("➔ Nächste Übung geladen", "info");
}

function triggerMicRecording() {
  const tab = getActiveTab();
  if (tab === "es") {
    const micBtn = document.getElementById("esMicBtn");
    if (micBtn) micBtn.click();
  } else if (tab === "ms") {
    const micBtn = document.getElementById("msMicBtn");
    if (micBtn) micBtn.click();
  } else if (tab === "num") {
    const micBtn = document.getElementById("numMicBtn");
    if (micBtn) micBtn.click();
  } else if (tab === "sent" || tab === "sentences") {
    const micBtn = document.getElementById("sentFullMicBtn");
    if (micBtn) micBtn.click();
  } else if (tab === "noise") {
    const micBtn = document.getElementById("noiseMicBtn");
    if (micBtn) micBtn.click();
  }
}

function submitActiveAnswer() {
  const tab = getActiveTab();
  if (tab === "es") {
    checkESAnswer();
  } else if (tab === "ms") {
    checkMSAnswer();
  } else if (tab === "num") {
    checkNumAnswer();
  } else if (tab === "sent" || tab === "sentences") {
    if (sentMode === "full") {
      checkSentFullAnswer();
    }
  } else if (tab === "noise") {
    checkNoiseAnswer();
  } else if (tab === "memory") {
    checkMemoryAnswer();
  } else if (tab === "weakness") {
    const weakInput = document.getElementById("weaknessInput");
    if (weakInput) checkWeaknessAnswer(weakInput.value);
  }
}

function playOptionAudio(idx) {
  const activeTab = getActiveTab();
  const activeSection = document.querySelector(`#tab-${activeTab}`) || document.querySelector(`.tab-content:not(.hidden)`);
  if (!activeSection) return false;

  const cards = activeSection.querySelectorAll(".option-card, .cards-grid .option-card");
  if (cards && cards[idx]) {
    const audioBtn = cards[idx].querySelector(".card-audio-btn");
    if (audioBtn) {
      audioBtn.click();
      return true;
    }
  }
  return false;
}
window.playOptionAudio = playOptionAudio;

// Cross-Platform OS Detection
const isMac = typeof navigator !== "undefined" && (navigator.platform?.toUpperCase().indexOf('MAC') >= 0 || navigator.userAgent?.includes('Mac'));
const isWindows = typeof navigator !== "undefined" && (navigator.platform?.toUpperCase().indexOf('WIN') >= 0 || navigator.userAgent?.includes('Win'));
const isLinux = typeof navigator !== "undefined" && (navigator.platform?.toUpperCase().indexOf('LINUX') >= 0 || navigator.userAgent?.includes('Linux'));

function initKeyboardShortcuts() {
  // Adapt data-hotkey tooltips dynamically based on OS (e.g. Cmd on Mac vs Strg on Win/Linux)
  if (isMac) {
    document.querySelectorAll("[data-hotkey]").forEach(el => {
      let hk = el.getAttribute("data-hotkey");
      if (hk) {
        hk = hk.replace(/Alt\+/g, "⌥").replace(/Strg\+/g, "⌘").replace(/Ctrl\+/g, "⌘");
        el.setAttribute("data-hotkey", hk);
      }
    });
  }

  document.addEventListener("keydown", (e) => {
    const activeEl = document.activeElement;
    const isInput = activeEl && (activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA" || activeEl.isContentEditable);

    // Escape: Close Modals or exit input
    if (e.key === "Escape" || e.code === "Escape") {
      if (isInput) activeEl.blur();
      closeHelpModal();
      if (typeof closeProfileModal === "function") closeProfileModal();
      if (typeof closeCalibrationModal === "function") closeCalibrationModal();
      if (typeof closeCatModal === "function") closeCatModal();
      const cancelForm = document.getElementById("cancelFormBtn");
      if (cancelForm && !document.getElementById("editorFormView")?.classList.contains("hidden")) {
        cancelForm.click();
      }
      return;
    }

    // Extract digit 1..9 from e.code (Digit1..Digit9 / Numpad1..Numpad9) or e.key (for macOS Alt-character independence)
    let digit = null;
    if (e.code && e.code.startsWith("Digit")) {
      const d = parseInt(e.code.replace("Digit", ""), 10);
      if (d >= 1 && d <= 9) digit = d;
    } else if (e.code && e.code.startsWith("Numpad")) {
      const d = parseInt(e.code.replace("Numpad", ""), 10);
      if (d >= 1 && d <= 9) digit = d;
    } else if (e.key >= "1" && e.key <= "9") {
      digit = parseInt(e.key, 10);
    }

    const hasModifier = e.altKey || e.ctrlKey || e.metaKey;

    // 🌐 Tab Switching (Alt+1..9 on Win/Linux, Option/Cmd+1..9 on macOS, or Ctrl+1..9)
    if (hasModifier && digit !== null) {
      e.preventDefault();
      const tabKeys = ["mp", "es", "num", "sent", "noise", "memory", "weakness", "stats", "editor"];
      const targetTab = tabKeys[digit - 1];
      if (targetTab) switchTab(targetTab);
      return;
    }

    // 💾 Ctrl+S / Cmd+S -> Save in Editor (Works on Mac Cmd+S / Windows Ctrl+S / Linux Ctrl+S)
    if ((e.ctrlKey || e.metaKey) && (e.code === "KeyS" || e.key.toLowerCase() === "s")) {
      const tab = getActiveTab();
      if (tab === "editor") {
        e.preventDefault();
        const addBtn = document.getElementById("addItemBtn");
        if (addBtn) addBtn.click();
      }
      return;
    }

    // 📋 Alt+L / Option+L / Cmd+L -> Editor List View
    if (hasModifier && (e.code === "KeyL" || e.key.toLowerCase() === "l" || e.key === "@")) {
      const tab = getActiveTab();
      if (tab === "editor") {
        e.preventDefault();
        switchTab("editor");
        switchEditorView("list");
        return;
      }
    }

    // ➕ Alt+N / Option+N / Cmd+N -> Editor New Exercise
    if (hasModifier && (e.code === "KeyN" || e.key.toLowerCase() === "n" || e.key === "˜")) {
      const tab = getActiveTab();
      if (tab === "editor") {
        e.preventDefault();
        switchTab("editor");
        switchEditorView("form");
        return;
      }
    }

    // 🗑️ Alt+Delete / Alt+Backspace / Cmd+Backspace -> Reset Stats
    if (hasModifier && (e.key === "Delete" || e.key === "Backspace" || e.code === "Delete" || e.code === "Backspace")) {
      const tab = getActiveTab();
      if (tab === "stats") {
        e.preventDefault();
        resetStats();
      }
      return;
    }

    // While typing in an input/textarea, only Enter submits, do not intercept normal typing
    if (isInput) {
      if (e.key === "Enter" || e.code === "Enter" || e.code === "NumpadEnter") {
        submitActiveAnswer();
      }
      return;
    }

    const key = e.key ? e.key.toLowerCase() : "";

    // ❓ F1, H, ? -> Toggle Online Help (F1 is universal across Win/Linux/Mac)
    if (!hasModifier && (key === "h" || e.key === "?" || e.code === "F1" || e.key === "F1")) {
      e.preventDefault();
      toggleHelpModal();
      return;
    }

    // ✕ Q -> App Exit
    if (!hasModifier && (key === "q" || e.code === "KeyQ")) {
      e.preventDefault();
      handleAppExit();
      return;
    }

    // 👤 Alt+P / Option+P / U -> Open User Profile Modal
    if ((hasModifier && (e.code === "KeyP" || key === "p" || e.key === "π")) || (!hasModifier && (key === "u" || e.code === "KeyU"))) {
      e.preventDefault();
      openProfileModal();
      return;
    }

    // ▶ Space or P -> Audio Replay / Play (without modifiers)
    if (!hasModifier && (e.code === "Space" || e.code === "KeyP" || key === "p" || e.key === " ")) {
      e.preventDefault();
      replayCurrentAudio();
      return;
    }

    // 🔊 Shift+1..6 or Shift+A..F -> Read Option Card Aloud
    if (e.shiftKey && digit !== null && digit >= 1 && digit <= 6) {
      e.preventDefault();
      playOptionAudio(digit - 1);
      return;
    }

    if (e.shiftKey && e.code && e.code.startsWith("Key")) {
      const letterCode = e.code.replace("Key", "");
      const letterIdx = letterCode.charCodeAt(0) - 65; // A=0, B=1, C=2, D=3, E=4, F=5
      if (letterIdx >= 0 && letterIdx <= 5) {
        e.preventDefault();
        playOptionAudio(letterIdx);
        return;
      }
    }

    // 1..6 or A..F -> Option Selection on active exercise card
    if (!hasModifier && digit !== null && digit >= 1 && digit <= 6) {
      e.preventDefault();
      selectOptionByHotkey(digit - 1);
      return;
    }

    if (!hasModifier && !e.shiftKey && e.code && e.code.startsWith("Key")) {
      const letterCode = e.code.replace("Key", "");
      const letterIdx = letterCode.charCodeAt(0) - 65;
      if (letterIdx >= 0 && letterIdx <= 5 && !["n", "m", "w", "d", "x", "r", "l", "h", "q", "u", "p", "s"].includes(key)) {
        e.preventDefault();
        selectOptionByHotkey(letterIdx);
        return;
      }
    }

    // ↵ Enter / NumpadEnter -> Submit & Check
    if (e.key === "Enter" || e.code === "Enter" || e.code === "NumpadEnter") {
      e.preventDefault();
      submitActiveAnswer();
      return;
    }

    // ➔ N or ArrowRight -> Next Item
    if (!hasModifier && (key === "n" || e.code === "KeyN" || e.key === "ArrowRight" || e.code === "ArrowRight")) {
      e.preventDefault();
      nextExerciseItem();
      return;
    }

    // 🎙 M -> Microphone Recording
    if (!hasModifier && (key === "m" || e.code === "KeyM")) {
      e.preventDefault();
      triggerMicRecording();
      return;
    }

    // 🔘 W -> Sentence Word Focus Mode
    if (!hasModifier && (key === "w" || e.code === "KeyW")) {
      const tab = getActiveTab();
      if (tab === "sent" || tab === "sentences") {
        e.preventDefault();
        setSentMode("mc");
      }
      return;
    }

    // ✍️ D -> Sentence Full Dictation Mode
    if (!hasModifier && (key === "d" || e.code === "KeyD")) {
      const tab = getActiveTab();
      if (tab === "sent" || tab === "sentences") {
        e.preventDefault();
        setSentMode("full");
      }
      return;
    }

    // 🛑 X -> Stop Autostart / Noise / Audio in all modules
    if (!hasModifier && (key === "x" || e.code === "KeyX")) {
      e.preventDefault();
      stopAutostartAndAudio();
      return;
    }

    // 🔄 R -> Reset / Refresh
    if (!hasModifier && (key === "r" || e.code === "KeyR")) {
      const tab = getActiveTab();
      if (tab === "memory") {
        e.preventDefault();
        resetMemorySelection();
      } else if (tab === "weakness") {
        e.preventDefault();
        loadWeaknessExercises();
      } else if (tab === "stats") {
        e.preventDefault();
        updateStats();
      } else if (tab === "es") {
        const restartBtn = document.getElementById("esTestRestartBtn");
        if (restartBtn && !document.getElementById("esTestResultCard")?.classList.contains("hidden")) {
          e.preventDefault();
          restartBtn.click();
        }
      }
      return;
    }

    // 📋 L -> Next Test List (Freiburger DIN Test in ES)
    if (key === "l" || e.code === "KeyL") {
      const tab = getActiveTab();
      if (tab === "es") {
        const nextListBtn = document.getElementById("esTestNextListBtn");
        if (nextListBtn && !document.getElementById("esTestResultCard")?.classList.contains("hidden")) {
          e.preventDefault();
          nextListBtn.click();
        }
      }
      return;
    }
  });
}

function initAutostartStopButtons() {
  document.addEventListener("click", (e) => {
    const stopBtn = e.target.closest(".btn-stop-autostart, .stop-autostart-btn, #mpStopBtn, #esActionStopBtn, #esStopBtn, #msActionStopBtn, #msStopBtn, #numActionStopBtn, #numStopBtn, #sentStopBtn, #sentFullStopBtn, #weaknessStopBtn, #weaknessInputStopBtn, #noiseStopBtn, #noiseInputStopBtn, #memoryStopBtn");
    if (stopBtn && !stopBtn.disabled) {
      e.preventDefault();
      stopAutostartAndAudio();
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
  let targetWord = currentWeaknessItem.word_a || currentWeaknessItem.target_word || currentWeaknessItem.word || currentWeaknessItem.value || "";

  if (modType === "minimal_pairs") {
    const opts = currentWeaknessItem.options || [currentWeaknessItem.word_a, currentWeaknessItem.word_b];
    targetWord = currentWeaknessItem.word_a || opts[0];
    inputHtml = `<div class="cards-grid" style="margin-top:1rem;">` +
      opts.map((opt, idx) => `
        <div class="option-card" id="weakness_card_${idx}" data-hotkey="Taste: ${idx + 1}" title="Option ${idx + 1} wählen (Taste ${idx + 1})" onclick="checkWeaknessAnswer('${escapeHtml(opt)}')">
          <span class="card-word">${escapeHtml(opt)}</span>
        </div>
      `).join("") + `</div>`;
  } else if (modType === "sentences") {
    targetWord = currentWeaknessItem.target_word || "";
    const opts = currentWeaknessItem.options || [targetWord, "Wort 2", "Wort 3"];
    const rawSentence = currentWeaknessItem.sentence || "";
    const maskedSentence = (targetWord && rawSentence.includes(targetWord))
      ? rawSentence.replace(targetWord, "_______")
      : rawSentence;

    inputHtml = `
      <div style="background:rgba(15,23,42,0.6); padding:1rem; border-radius:12px; margin-bottom:1rem; text-align:left; border:1px solid var(--panel-border);">
        <span style="color:var(--text-muted);">Satzkontext:</span>
        <h4 id="weaknessSentenceDisplay" style="font-size:1.3rem; color:white; margin-top:0.3rem;">"${escapeHtml(maskedSentence)}"</h4>
      </div>
      <div class="cards-grid">` +
      opts.map((opt, idx) => `
        <div class="option-card" id="weakness_card_${idx}" data-hotkey="Taste: ${idx + 1}" title="Option ${idx + 1} wählen (Taste ${idx + 1})" onclick="checkWeaknessAnswer('${escapeHtml(opt)}')">
          <span class="card-word">${escapeHtml(opt)}</span>
        </div>
      `).join("") + `</div>`;
  } else {
    inputHtml = `
      <div class="input-section" style="display:flex; gap:0.5rem; align-items:center; margin-top:0.8rem;">
        <input type="text" id="weaknessInput" placeholder="Antwort eingeben..." class="custom-input" autocomplete="off" style="flex:1;">
        <button id="weaknessMicBtn" class="btn btn-mic" data-hotkey="Taste: M" title="Mit Mikrofon nachsprechen (Taste M)" onclick="startWeaknessMic()">🎙 Nachsprechen</button>
        <button id="weaknessInputStopBtn" class="btn btn-stop-autostart autostart-only-btn" data-hotkey="Taste: X" title="Autostart pausieren (Taste X)" onclick="stopAutostartAndAudio()">⏸ Pause</button>
        <button class="btn btn-success" data-hotkey="Enter" title="Eingabe prüfen (Taste Enter)" onclick="checkWeaknessAnswer(document.getElementById('weaknessInput').value)">Prüfen</button>
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

  const weaknessStopBtn = document.getElementById("weaknessStopBtn");
  if (weaknessStopBtn) {
    weaknessStopBtn.style.display = (modType === "minimal_pairs" || modType === "sentences") ? "" : "none";
  }

  setStatus(`Schwachstellen-Übung bereit (${currentWeaknessItem.category || ""}).`);
  setPlayBtnState("weaknessPlayBtn", false, "Wiederholen");

  if (userTriggered) {
    playWeaknessAudio();
  }
}

async function playWeaknessAudio() {
  if (!currentWeaknessItem) return;
  setPlayBtnState("weaknessPlayBtn", true, "Wiederholen");
  const speechText = currentWeaknessItem.sentence || currentWeaknessItem.word_a || currentWeaknessItem.word || currentWeaknessItem.target_word || currentWeaknessItem.spoken || currentWeaknessItem.value || "";
  playTTS(speechText, "Schwachstellen-Audio");
  if (isAutoMicActive("weakness")) {
    const delay = estimateSpeechDurationMs(speechText, audioRate);
    setTimeout(() => startAutoMic("weakness"), delay + 200);
  }
}

async function checkWeaknessAnswer(userVal) {
  const cleanUser = String(userVal || "").trim();
  if (!cleanUser) {
    const feedback = document.getElementById("weaknessFeedback");
    if (feedback) {
      feedback.textContent = "⚠️ Bitte gib zuerst ein Wort ein oder wähle eine Option.";
      feedback.className = "feedback-banner danger";
    }
    document.getElementById("weaknessInput")?.focus();
    return;
  }

  if (weaknessAttempted || !currentWeaknessItem) return;
  weaknessAttempted = true;

  const targetWord = currentWeaknessItem.word_a || currentWeaknessItem.target_word || currentWeaknessItem.word || currentWeaknessItem.value || "";
  const category = currentWeaknessItem.category || "Schwachstelle";

  // Reveal target word in sentence context if sentence exercise
  if (currentWeaknessItem.mod_type === "sentences" && currentWeaknessItem.sentence) {
    const dispEl = document.getElementById("weaknessSentenceDisplay");
    if (dispEl) dispEl.textContent = `"${currentWeaknessItem.sentence}"`;
  }

  // Highlight option cards if multiple choice
  const cleanTarget = String(targetWord || "").toLowerCase().trim();
  const isCorrect = (cleanUser.toLowerCase() === cleanTarget);

  const cards = document.querySelectorAll("#weaknessExerciseArea .option-card");
  cards.forEach(card => {
    const text = card.querySelector(".card-word")?.textContent.trim() || "";
    const cleanCardText = text.toLowerCase().trim();
    if (cleanCardText === cleanTarget) {
      card.classList.add("correct");
    } else if (cleanCardText === cleanUser && !isCorrect) {
      card.classList.add("incorrect");
    }
  });

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

  scheduleAutoAdvance(feedback, () => nextWeaknessItem(true), data.is_correct);
}
window.checkWeaknessAnswer = checkWeaknessAnswer;

// ══════════════════════════════════════════════════════════════════════════════
// 🎯 ADAPTIVER OLSA-SATZTEST (SRT-MESSUNG NACH BRAND & KOLLMEIER)
// ══════════════════════════════════════════════════════════════════════════════

let olsaMatrix = null;
let olsaSelectedWords = [null, null, null, null, null];
let olsaCurrentAudio = null;
let olsaHistory = [];
let olsaReversals = [];
let olsaActive = false;

function initOLSA() {
  const startBtn = document.getElementById("olsaStartTestBtn");
  const submitBtn = document.getElementById("olsaSubmitStepBtn");
  const playBtn = document.getElementById("olsaPlaySentenceBtn");
  const restartBtn = document.getElementById("olsaRestartBtn");

  if (startBtn) startBtn.addEventListener("click", startOLSATest);
  if (submitBtn) submitBtn.addEventListener("click", submitOLSAStep);
  if (playBtn) playBtn.addEventListener("click", playOLSASentence);
  if (restartBtn) restartBtn.addEventListener("click", startOLSATest);
}

async function startOLSATest() {
  const noiseType = document.getElementById("olsaNoiseTypeSelect")?.value || "olnoise";
  const startSNR = parseFloat(document.getElementById("olsaStartSNRSelect")?.value || "0.0");
  const activeArea = document.getElementById("olsaActiveArea");
  const resultCard = document.getElementById("olsaResultCard");

  if (resultCard) resultCard.classList.add("hidden");
  if (activeArea) activeArea.classList.remove("hidden");

  olsaSelectedWords = [null, null, null, null, null];
  olsaHistory = [];
  olsaReversals = [];
  olsaActive = true;

  try {
    const res = await fetch("/api/olsa/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        start_snr_db: startSNR,
        noise_type: noiseType,
        total_sentences: 20,
        voice: selectedVoice
      })
    });
    const data = await res.json();
    olsaMatrix = data.matrix;
    olsaCurrentAudio = data.audio_file;

    renderOLSAMatrix(olsaMatrix);
    updateOLSAUI(data.sentence_index, data.total_sentences, data.current_snr_db);
    drawOLSAStaircase(olsaHistory, olsaReversals);
  } catch (err) {
    showToast("Fehler beim Starten des OLSA-Tests: " + err.message, "danger");
  }
}

function renderOLSAMatrix(matrix) {
  const container = document.getElementById("olsaMatrixContainer");
  if (!container || !matrix) return;

  container.innerHTML = "";
  const cols = [
    { title: "1. Name", words: matrix.names },
    { title: "2. Verb", words: matrix.verbs },
    { title: "3. Zahl", words: matrix.numbers },
    { title: "4. Adjektiv", words: matrix.adjectives },
    { title: "5. Nomen", words: matrix.nouns }
  ];

  cols.forEach((col, colIdx) => {
    const colDiv = document.createElement("div");
    colDiv.className = "olsa-column";

    const header = document.createElement("div");
    header.className = "olsa-col-header";
    header.textContent = col.title;
    colDiv.appendChild(header);

    col.words.forEach(word => {
      const btn = document.createElement("button");
      btn.className = "olsa-word-btn";
      btn.textContent = word;
      btn.addEventListener("click", () => selectOLSAWord(colIdx, word, btn, colDiv));
      colDiv.appendChild(btn);
    });

    container.appendChild(colDiv);
  });
  updateOLSAPreview();
}

function selectOLSAWord(colIdx, word, btn, colDiv) {
  colDiv.querySelectorAll(".olsa-word-btn").forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
  olsaSelectedWords[colIdx] = word;
  updateOLSAPreview();
}

function updateOLSAPreview() {
  const preview = document.getElementById("olsaSelectedSentencePreview");
  const submitBtn = document.getElementById("olsaSubmitStepBtn");

  const filledCount = olsaSelectedWords.filter(w => w !== null).length;
  if (filledCount === 5) {
    if (preview) preview.textContent = olsaSelectedWords.join(" ");
    if (submitBtn) submitBtn.disabled = false;
  } else {
    const displayArr = olsaSelectedWords.map((w, idx) => w || `[${["Name", "Verb", "Zahl", "Adj.", "Nomen"][idx]}]`);
    if (preview) preview.textContent = displayArr.join(" ");
    if (submitBtn) submitBtn.disabled = true;
  }
}

function updateOLSAUI(sentIdx, totalSent, snrDb) {
  const countBadge = document.getElementById("olsaSentenceCountBadge");
  const snrBadge = document.getElementById("olsaCurrentSNRBadge");
  if (countBadge) countBadge.textContent = `Satz ${sentIdx} / ${totalSent}`;
  if (snrBadge) {
    const sign = snrDb > 0 ? "+" : "";
    let desc = "";
    if (Math.abs(snrDb) < 0.1) desc = " (Gleich laut)";
    else if (snrDb > 0) desc = " (Sprache lauter)";
    else desc = " (Rauschen lauter)";
    snrBadge.textContent = `SNR: ${sign}${snrDb.toFixed(1)} dB${desc}`;
  }
}

async function playOLSASentence() {
  if (!olsaCurrentAudio) return;
  try {
    await fetch("/api/olsa/play", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ audio_file: olsaCurrentAudio })
    });
  } catch (e) {
    const audio = new Audio(`/api/audio/${olsaCurrentAudio}`);
    audio.play().catch(err => console.log("Audio play err:", err));
  }
}

async function submitOLSAStep() {
  const submitBtn = document.getElementById("olsaSubmitStepBtn");
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch("/api/olsa/step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_words: olsaSelectedWords,
        voice: selectedVoice
      })
    });
    const data = await res.json();
    olsaHistory = data.history || [];
    olsaReversals = data.reversals || [];

    drawOLSAStaircase(olsaHistory, olsaReversals);

    if (data.finished) {
      olsaActive = false;
      showOLSAResults(data);
    } else {
      olsaCurrentAudio = data.audio_file;
      olsaSelectedWords = [null, null, null, null, null];
      document.querySelectorAll(".olsa-word-btn").forEach(b => b.classList.remove("selected"));
      updateOLSAPreview();
      updateOLSAUI(data.next_sentence_index, 20, data.next_snr_db);
    }
  } catch (err) {
    showToast("Fehler bei der OLSA-Schrittauswertung: " + err.message, "danger");
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

function showOLSAResults(data) {
  const activeArea = document.getElementById("olsaActiveArea");
  const resultCard = document.getElementById("olsaResultCard");
  const srtVal = document.getElementById("olsaResultSRT");
  const stdDevVal = document.getElementById("olsaResultStdDev");
  const ratingVal = document.getElementById("olsaResultRating");

  if (activeArea) activeArea.classList.add("hidden");
  if (resultCard) resultCard.classList.remove("hidden");

  const srt = data.srt_db;
  const sdev = data.std_dev;
  const sign = srt > 0 ? "+" : "";

  if (srtVal) srtVal.textContent = `${sign}${srt.toFixed(1)} dB`;
  if (stdDevVal) stdDevVal.textContent = `± ${sdev.toFixed(1)} dB`;

  let rating = "Hervorragend (Klinischer Spitzenwert)";
  let rColor = "#34D399";
  if (srt > 5.0) {
    rating = "Schwierigkeiten im Störlärm (Training empfohlen)";
    rColor = "#F87171";
  } else if (srt > 0.0) {
    rating = "Gutes Sprachverstehen im moderaten Lärm";
    rColor = "#F59E0B";
  } else if (srt > -4.0) {
    rating = "Sehr gutes Sprachverstehen im Störschall";
    rColor = "#60A5FA";
  }

  if (ratingVal) {
    ratingVal.textContent = rating;
    ratingVal.style.color = rColor;
  }

  addXP(100);
  showToast(`🎯 OLSA-Test abgeschlossen: SRT = ${sign}${srt.toFixed(1)} dB SNR`, "success");
}

function drawOLSAStaircase(history, reversals) {
  const canvas = document.getElementById("olsaStaircaseCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Background Grid
  ctx.fillStyle = "#0B132B";
  ctx.fillRect(0, 0, w, h);

  const padLeft = 50;
  const padRight = 30;
  const padTop = 25;
  const padBottom = 30;

  const minSNR = -15;
  const maxSNR = 15;
  const totalSent = 20;

  function toX(sentNum) {
    return padLeft + ((sentNum - 1) / (totalSent - 1)) * (w - padLeft - padRight);
  }
  function toY(snr) {
    return padTop + ((maxSNR - snr) / (maxSNR - minSNR)) * (h - padTop - padBottom);
  }

  // Horizontal Zero / Target Line (0 dB SNR)
  const zeroY = toY(0);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);

  [-10, -5, 0, 5, 10].forEach(snrLevel => {
    const y = toY(snrLevel);
    ctx.beginPath();
    ctx.moveTo(padLeft, y);
    ctx.lineTo(w - padRight, y);
    ctx.stroke();

    ctx.fillStyle = "rgba(148, 163, 184, 0.7)";
    ctx.font = "10px sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(`${snrLevel > 0 ? "+" : ""}${snrLevel} dB`, padLeft - 6, y + 3);
  });
  ctx.setLineDash([]);

  // Axes labels
  ctx.fillStyle = "#60A5FA";
  ctx.font = "bold 11px sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Satz-Nummer (1 .. 20)", w / 2, h - 8);

  if (!history || history.length === 0) return;

  // Plot Staircase Line
  ctx.beginPath();
  ctx.strokeStyle = "#3B82F6";
  ctx.lineWidth = 3;
  history.forEach((rec, idx) => {
    const x = toX(rec.sentence_num);
    const y = toY(rec.snr_db);
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Plot Points with color-coded score
  history.forEach(rec => {
    const x = toX(rec.sentence_num);
    const y = toY(rec.snr_db);

    ctx.beginPath();
    ctx.arc(x, y, 6, 0, 2 * Math.PI);
    // Color: Green if 4-5 words, Orange if 3 words, Red if 0-2 words
    if (rec.correct_words >= 4) ctx.fillStyle = "#10B981";
    else if (rec.correct_words === 3) ctx.fillStyle = "#F59E0B";
    else ctx.fillStyle = "#EF4444";

    ctx.fill();
    ctx.strokeStyle = "#FFFFFF";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Word score text inside/above dot
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "bold 9px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${rec.correct_words}/5`, x, y - 9);
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// 📈 FREIBURGER DIN-45621 SPRACHAUDIOMETRIE (MEHRPEGEL-KURVE)
// ══════════════════════════════════════════════════════════════════════════════

function initAudiogram() {
  const plotBtn = document.getElementById("plotAudiogramBtn");
  const saveBtn = document.getElementById("saveAudiogramCurveBtn");

  if (plotBtn) plotBtn.addEventListener("click", renderAudiogramPlot);
  if (saveBtn) saveBtn.addEventListener("click", saveAudiogramCurve);

  renderAudiogramPlot();
}

function renderAudiogramPlot() {
  const canvas = document.getElementById("audiogramCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  const score50 = Math.max(0, Math.min(100, parseFloat(document.getElementById("audioScore50")?.value || "45")));
  const score65 = Math.max(0, Math.min(100, parseFloat(document.getElementById("audioScore65")?.value || "75")));
  const score80 = Math.max(0, Math.min(100, parseFloat(document.getElementById("audioScore80")?.value || "90")));

  // Berechne Vmax und Diskriminationsverlust
  const vMax = Math.max(score50, score65, score80);
  const discLoss = Math.max(0, 100 - vMax);

  const vMaxEl = document.getElementById("audioVMaxVal");
  const discLossEl = document.getElementById("audioDiscLossVal");
  if (vMaxEl) vMaxEl.textContent = `${vMax} %`;
  if (discLossEl) discLossEl.textContent = `${discLoss} %`;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#0B132B";
  ctx.fillRect(0, 0, w, h);

  const padLeft = 60;
  const padRight = 30;
  const padTop = 30;
  const padBottom = 40;

  const minDb = 0;
  const maxDb = 100;

  function toX(db) {
    return padLeft + (db / maxDb) * (w - padLeft - padRight);
  }
  function toY(pct) {
    return padTop + ((100 - pct) / 100.0) * (h - padTop - padBottom);
  }

  // Grid lines
  ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
  ctx.lineWidth = 1;

  [0, 20, 40, 60, 80, 100].forEach(db => {
    const x = toX(db);
    ctx.beginPath(); ctx.moveTo(x, padTop); ctx.lineTo(x, h - padBottom); ctx.stroke();
    ctx.fillStyle = "#94A3B8"; ctx.font = "10px sans-serif"; ctx.textAlign = "center";
    ctx.fillText(`${db} dB`, x, h - padBottom + 14);
  });

  [0, 20, 40, 50, 60, 80, 100].forEach(pct => {
    const y = toY(pct);
    ctx.beginPath(); ctx.moveTo(padLeft, y); ctx.lineTo(w - padRight, y); ctx.stroke();
    ctx.fillStyle = "#94A3B8"; ctx.font = "10px sans-serif"; ctx.textAlign = "right";
    ctx.fillText(`${pct}%`, padLeft - 8, y + 3);
  });

  // Reference Normal Hearing Curve (DIN 45621 standard Einsilber reference)
  ctx.beginPath();
  ctx.strokeStyle = "rgba(96, 165, 250, 0.5)";
  ctx.lineWidth = 2.5;
  ctx.setLineDash([5, 5]);
  for (let db = 10; db <= 50; db += 1) {
    // Sigmoid Logistic Function centered around 30 dB SPL
    const normPct = 100.0 / (1.0 + Math.exp(-0.16 * (db - 30)));
    const x = toX(db);
    const y = toY(normPct);
    if (db === 10) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.setLineDash([]);

  // Patient's Curve (Measured Points at 50, 65, 80 dB)
  const patientPoints = [
    { db: 35, score: Math.max(0, score50 - 30) },
    { db: 50, score: score50 },
    { db: 65, score: score65 },
    { db: 80, score: score80 }
  ];

  ctx.beginPath();
  ctx.strokeStyle = "#34D399";
  ctx.lineWidth = 3.5;
  patientPoints.forEach((pt, i) => {
    const x = toX(pt.db);
    const y = toY(pt.score);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Dots
  patientPoints.slice(1).forEach(pt => {
    const x = toX(pt.db);
    const y = toY(pt.score);
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, 2 * Math.PI);
    ctx.fillStyle = "#34D399";
    ctx.fill();
    ctx.strokeStyle = "#FFFFFF";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = "#F8FAFC";
    ctx.font = "bold 11px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`${pt.score}%`, x, y - 10);
  });
}

async function saveAudiogramCurve() {
  const score50 = parseFloat(document.getElementById("audioScore50")?.value || "45");
  const score65 = parseFloat(document.getElementById("audioScore65")?.value || "75");
  const score80 = parseFloat(document.getElementById("audioScore80")?.value || "90");

  const vMax = Math.max(score50, score65, score80);
  const discLoss = Math.max(0, 100 - vMax);

  try {
    const res = await fetch("/api/freiburger/curve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        list_name: "Freiburger Mehrpegel-Test",
        test_data: [
          { db: 50, score: score50 },
          { db: 65, score: score65 },
          { db: 80, score: score80 }
        ],
        v_max: vMax,
        disc_loss: discLoss,
        notes: `Messung bei 50/65/80 dB SPL (Vmax: ${vMax}%)`
      })
    });
    const data = await res.json();
    showToast("📈 Audiogramm-Kurve erfolgreich in der Datenbank gespeichert!", "success");
    addXP(60);
  } catch (err) {
    showToast("Fehler beim Speichern: " + err.message, "danger");
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// 🎛️ CI-VOCODER SIMULATION CONTROLS
// ══════════════════════════════════════════════════════════════════════════════

let vocoderEnabled = false;

function initVocoderControls() {
  const toggle = document.getElementById("vocoderToggle");
  const valBadge = document.getElementById("vocoderVal");
  const optionsDiv = document.getElementById("vocoderOptions");
  const profileSelect = document.getElementById("vocoderProfileSelect");

  const updateVocoderBadge = () => {
    if (!toggle || !valBadge) return;
    vocoderEnabled = toggle.checked;
    if (!vocoderEnabled) {
      valBadge.textContent = "Aus";
      if (optionsDiv) optionsDiv.classList.add("hidden");
    } else {
      const pText = profileSelect?.options[profileSelect.selectedIndex]?.text?.split("(")[0]?.trim() || "Aktiv";
      valBadge.textContent = pText;
      if (optionsDiv) optionsDiv.classList.remove("hidden");
    }
  };

  if (toggle) {
    toggle.addEventListener("change", () => {
      updateVocoderBadge();
      if (vocoderEnabled) {
        const pName = profileSelect?.options[profileSelect.selectedIndex]?.text || "CI-Simulation";
        showToast(`🎛 CI-Vocoder aktiviert: ${pName} (Sinustöne)`, "info");
      }
      debouncedSaveActiveProfileAudio();
    });
  }

  if (profileSelect) {
    profileSelect.addEventListener("change", () => {
      updateVocoderBadge();
      if (vocoderEnabled) {
        const pName = profileSelect.options[profileSelect.selectedIndex]?.text;
        showToast(`🎛 CI-Profil: ${pName}`, "info");
      }
      debouncedSaveActiveProfileAudio();
    });
  }
}

// ══════════════════════════════════════════════════════════════════════════════
// 🔊 65 dB SPL KALIBRIERUNGS-ASSISTENT (DIN 45621)
// ══════════════════════════════════════════════════════════════════════════════

let isCalibPlaying = false;

function initCalibrationWizard() {
  const openBtn = document.getElementById("openCalibrationBtn");
  const openFromAudioBtn = document.getElementById("openCalibrationFromAudioBtn");
  const closeBtn = document.getElementById("closeCalibrationModalBtn");
  const closeFooterBtn = document.getElementById("closeCalibModalFooterBtn");
  const toggleAudioBtn = document.getElementById("toggleCalibAudioBtn");
  const confirmBtn = document.getElementById("confirmCalibrationBtn");
  const signalSelect = document.getElementById("calibSignalSelect");
  const modal = document.getElementById("calibrationModal");

  const openModal = () => {
    if (modal) modal.classList.remove("hidden");
    updateCalibrationUIStatus();
  };

  const closeModal = () => {
    stopCalibrationAudio();
    if (modal) modal.classList.add("hidden");
  };

  if (openBtn) openBtn.addEventListener("click", openModal);
  if (openFromAudioBtn) openFromAudioBtn.addEventListener("click", openModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (closeFooterBtn) closeFooterBtn.addEventListener("click", closeModal);

  if (toggleAudioBtn) {
    toggleAudioBtn.addEventListener("click", () => {
      if (isCalibPlaying) {
        stopCalibrationAudio();
      } else {
        startCalibrationAudio();
      }
    });
  }

  if (signalSelect) {
    signalSelect.addEventListener("change", () => {
      if (isCalibPlaying) {
        startCalibrationAudio();
      }
    });
  }

  if (confirmBtn) {
    confirmBtn.addEventListener("click", () => {
      const nowStr = new Date().toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
      localStorage.setItem("ci_calibrated_at", nowStr);
      updateCalibrationUIStatus();
      stopCalibrationAudio();
      showToast("✅ System erfolgreich auf 65 dB SPL kalibriert!", "success");
      setTimeout(closeModal, 600);
    });
  }

  updateCalibrationUIStatus();
}

function updateCalibrationUIStatus() {
  const lastCalib = localStorage.getItem("ci_calibrated_at");
  const statusBadge = document.getElementById("calibrationStatusBadge");
  const modalStatusText = document.getElementById("calibModalStatusText");

  if (lastCalib) {
    if (statusBadge) {
      statusBadge.innerHTML = `<span style="color:#10B981;">🟢</span> Kalibriert am ${lastCalib}`;
    }
    if (modalStatusText) {
      modalStatusText.innerHTML = `<span style="color:#10B981; font-weight:700;">🟢 Kalibriert:</span> Letzte Messung am ${lastCalib}`;
    }
  } else {
    if (statusBadge) {
      statusBadge.innerHTML = `<span>⚪</span> Nicht kalibriert (Standardpegel)`;
    }
    if (modalStatusText) {
      modalStatusText.textContent = "Noch nicht als kalibriert markiert.";
    }
  }
}

async function startCalibrationAudio() {
  const signalType = document.getElementById("calibSignalSelect")?.value || "speech_noise";
  const btn = document.getElementById("toggleCalibAudioBtn");

  try {
    const res = await fetch("/api/calibration/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        signal_type: signalType,
        volume: 0.6
      })
    });
    if (res.ok) {
      isCalibPlaying = true;
      if (btn) {
        btn.innerHTML = `<span>⏹</span> Signal stoppen`;
        btn.className = "btn btn-danger btn-sm";
      }
      setStatus("▶ Kalibriersignal aktiv (System-Audioausgabe)...");
    }
  } catch (e) {
    console.error("Fehler beim Starten des Kalibriersignals:", e);
    showToast("Fehler beim Starten des Kalibriersignals.", "danger");
  }
}

async function stopCalibrationAudio() {
  isCalibPlaying = false;
  const btn = document.getElementById("toggleCalibAudioBtn");
  if (btn) {
    btn.innerHTML = `<span>▶</span> Kalibriersignal starten`;
    btn.className = "btn btn-primary btn-sm";
  }
  try {
    await fetch("/api/calibration/stop", { method: "POST" });
    setStatus("Kalibriersignal beendet.");
  } catch (e) {}
}

// ─── MULTI-USER & CI-SPECIFIC PROFILES ─────────────────────────────────────
let activeProfile = null;
let allUserProfiles = [];

async function initProfileManagement() {
  const openBtn = document.getElementById("openProfileBtn");
  const closeBtn = document.getElementById("closeProfileModalBtn");
  const closeFooterBtn = document.getElementById("closeProfileModalFooterBtn");
  const modal = document.getElementById("profileModal");
  const addBtn = document.getElementById("addNewProfileBtn");
  const cancelBtn = document.getElementById("cancelProfileEditBtn");
  const saveBtn = document.getElementById("saveProfileBtn");
  const fittingSelect = document.getElementById("profileFormFitting");
  const dateInput = document.getElementById("profileFormFittingDate");
  const gainSlider = document.getElementById("profileFormGain");
  const rateSlider = document.getElementById("profileFormRate");
  const balSelect = document.getElementById("profileFormBalance");

  if (openBtn) {
    openBtn.addEventListener("click", () => openProfileModal());
  }
  if (closeBtn) {
    closeBtn.addEventListener("click", () => closeProfileModal());
  }
  if (closeFooterBtn) {
    closeFooterBtn.addEventListener("click", () => closeProfileModal());
  }
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeProfileModal();
    });
  }

  if (addBtn) {
    addBtn.addEventListener("click", () => openProfileEditForm(null));
  }
  if (cancelBtn) {
    cancelBtn.addEventListener("click", () => {
      document.getElementById("profileEditFormContainer")?.classList.add("hidden");
    });
  }
  if (saveBtn) {
    saveBtn.addEventListener("click", () => saveProfileForm());
  }

  if (dateInput) {
    dateInput.addEventListener("input", (e) => {
      const badge = document.getElementById("profileFormRehaBadge");
      if (badge) {
        const val = e.target.value;
        if (!val) {
          badge.textContent = "Reha-Woche 1";
          return;
        }
        try {
          const dt = new Date(val);
          const now = new Date();
          const diffDays = Math.floor((now - dt) / (1000 * 60 * 60 * 24));
          const w = diffDays < 0 ? 1 : Math.max(1, Math.floor(diffDays / 7) + 1);
          badge.textContent = `Reha-Woche ${w}`;
        } catch (err) {
          badge.textContent = "Reha-Woche 1";
        }
      }
    });
  }

  if (fittingSelect) {
    fittingSelect.addEventListener("change", (e) => {
      const f = e.target.value;
      if (balSelect) {
        if (f === "monoral_r") balSelect.value = "1.0";
        else if (f === "monoral_l") balSelect.value = "-1.0";
        else balSelect.value = "0.0";
      }
      const badge = document.getElementById("profileFormFittingBadge");
      if (badge) badge.textContent = getFittingShortLabel(f);
    });
  }

  if (gainSlider) {
    gainSlider.addEventListener("input", (e) => {
      const el = document.getElementById("profileFormGainVal");
      if (el) el.textContent = `${Math.round(parseFloat(e.target.value) * 100)}%`;
    });
  }

  if (rateSlider) {
    rateSlider.addEventListener("input", (e) => {
      const el = document.getElementById("profileFormRateVal");
      if (el) el.textContent = `${parseFloat(e.target.value).toFixed(1)}x`;
    });
  }

  // Initial load of active profile
  await loadActiveProfile();
}

async function loadActiveProfile() {
  try {
    const res = await fetch("/api/profiles/active");
    if (res.ok) {
      const prof = await res.json();
      if (prof && prof.id) {
        activeProfile = prof;
        await applyProfileToUI(prof);
      }
    }
  } catch (e) {
    console.error("Fehler beim Laden des aktiven Profils:", e);
  }
}

function getFittingLabel(type) {
  switch (type) {
    case "monoral_r": return "🦻 Monoral Rechts (CI)";
    case "monoral_l": return "🦻 Monoral Links (CI)";
    case "bimodal_r": return "🦻 Bimodal Rechts (CI R / HG L)";
    case "bimodal_l": return "🦻 Bimodal Links (CI L / HG R)";
    case "bimodal_hg": return "🦻 Bimodal (CI + HG)";
    case "ssd_r": return "🦻 SSD Rechts (CI R / Normal L)";
    case "ssd_l": return "🦻 SSD Links (CI L / Normal R)";
    case "ssd": return "🦻 SSD (Einseitig taub)";
    case "bilateral":
    default: return "🦻🦻 Bilateral CI";
  }
}

function getFittingShortLabel(type) {
  switch (type) {
    case "monoral_r": return "CI Rechts";
    case "monoral_l": return "CI Links";
    case "bimodal_r": return "Bimodal R";
    case "bimodal_l": return "Bimodal L";
    case "bimodal_hg": return "Bimodal";
    case "ssd_r": return "SSD Rechts";
    case "ssd_l": return "SSD Links";
    case "ssd": return "SSD";
    case "bilateral":
    default: return "Bilateral";
  }
}

async function applyProfileToUI(prof) {
  if (!prof) return;

  const headerName = document.getElementById("headerProfileName");
  const headerBadge = document.getElementById("headerProfileBadge");
  if (headerName) headerName.textContent = prof.name || "Profil";
  if (headerBadge) headerBadge.textContent = getFittingShortLabel(prof.fitting_type);

  const targetLang = prof.exercise_lang || "de";
  if (targetLang !== window.currentLanguage || !exercises.minimal_pairs || exercises.minimal_pairs.length === 0) {
    await setLanguage(targetLang);
  } else {
    const btnDE = document.getElementById("langBtnDE");
    const btnEN = document.getElementById("langBtnEN");
    if (btnDE) btnDE.classList.toggle("active", targetLang === "de");
    if (btnEN) btnEN.classList.toggle("active", targetLang === "en");
  }

  const curLang = window.currentLanguage || "de";
  if (curLang === "en" && prof.voice_en) {
    selectedVoice = prof.voice_en;
  } else if (prof.voice) {
    selectedVoice = prof.voice;
  }

  const voiceSelect = document.getElementById("voiceSelect");
  if (voiceSelect) {
    await loadVoices(curLang);
  }

  if (prof.audio_balance !== undefined && prof.audio_balance !== null && parseFloat(prof.audio_balance) !== 0.0) {
    audioBalance = parseFloat(prof.audio_balance);
  } else if (prof.fitting_type) {
    if (["monoral_l", "bimodal_l", "ssd_l"].includes(prof.fitting_type)) {
      audioBalance = -1.0;
    } else if (["monoral_r", "bimodal_r", "ssd_r"].includes(prof.fitting_type)) {
      audioBalance = 1.0;
    } else {
      audioBalance = parseFloat(prof.audio_balance || 0.0);
    }
  } else {
    audioBalance = parseFloat(prof.audio_balance || 0.0);
  }

  localStorage.setItem("ci_audio_balance", audioBalance.toString());

  const segBtns = document.querySelectorAll(".segmented-control .seg-btn[data-bal]");
  segBtns.forEach(btn => {
    const bBal = parseFloat(btn.dataset.bal);
    btn.classList.toggle("active", bBal === audioBalance);
  });

  const balVal = document.getElementById("balVal");
  if (balVal) {
    if (audioBalance === -1.0) balVal.textContent = "Nur Links (CI)";
    else if (audioBalance === 1.0) balVal.textContent = "Nur Rechts (CI)";
    else balVal.textContent = "Beide Ohren";
  }

  if (prof.master_gain !== undefined && prof.master_gain !== null) {
    audioVolume = parseFloat(prof.master_gain);
    if (isNaN(audioVolume)) audioVolume = 1.0;
    localStorage.setItem("ci_audio_volume", audioVolume.toString());
    const volSlider = document.getElementById("volSlider");
    const volVal = document.getElementById("volVal");
    if (volSlider) volSlider.value = audioVolume;
    if (volVal) volVal.textContent = `${Math.round(audioVolume * 100)}%`;
  }

  if (prof.speech_rate !== undefined && prof.speech_rate !== null) {
    audioRate = parseFloat(prof.speech_rate);
    if (isNaN(audioRate)) audioRate = 1.0;
    localStorage.setItem("ci_audio_rate", audioRate.toString());
    const rateSlider = document.getElementById("rateSlider");
    const rateVal = document.getElementById("rateVal");
    if (rateSlider) rateSlider.value = audioRate;
    if (rateVal) rateVal.textContent = `${audioRate.toFixed(1)}x`;
  }

  if (prof.mask_noise !== undefined) {
    maskNoise = Boolean(prof.mask_noise);
    const maskToggle = document.getElementById("maskToggle");
    const maskVal = document.getElementById("maskVal");
    if (maskToggle) maskToggle.checked = maskNoise;
    if (maskVal) maskVal.textContent = maskNoise ? "Ja" : "Nein";
  }

  if (prof.noise_volume !== undefined && prof.noise_volume !== null) {
    noiseVolume = parseFloat(prof.noise_volume);
    if (isNaN(noiseVolume)) noiseVolume = 0.4;
    localStorage.setItem("ci_noise_volume", noiseVolume.toString());
    const maskVolSlider = document.getElementById("maskVolSlider");
    const maskVolVal = document.getElementById("maskVolVal");
    const noiseVolSlider = document.getElementById("noiseVolSlider");
    const noiseVolVal = document.getElementById("noiseVolVal");
    const volPct = `${Math.round(noiseVolume * 100)}%`;
    if (maskVolSlider) maskVolSlider.value = noiseVolume;
    if (noiseVolSlider) noiseVolSlider.value = noiseVolume;
    if (maskVolVal) maskVolVal.textContent = volPct;
    if (noiseVolVal) noiseVolVal.textContent = volPct;
  }

  if (prof.freq_filter) {
    selectedFreqFilter = prof.freq_filter;
    const freqFilterSelect = document.getElementById("freqFilterSelect");
    const freqFilterBadge = document.getElementById("freqFilterBadge");
    if (freqFilterSelect) freqFilterSelect.value = selectedFreqFilter;
    const labels = {
      "none": "Normal",
      "high_boost": "Hochton +6dB",
      "highpass": "Hochpass 1000Hz",
      "lowpass": "Tiefpass 3000Hz"
    };
    if (freqFilterBadge) freqFilterBadge.textContent = labels[selectedFreqFilter] || "Normal";
  }

  if (prof.autostart_success_delay !== undefined) {
    const sSlider = document.getElementById("autostartSuccessSlider");
    const sVal = document.getElementById("autostartSuccessVal");
    if (sSlider) sSlider.value = prof.autostart_success_delay;
    if (sVal) sVal.textContent = `${parseFloat(prof.autostart_success_delay).toFixed(1)}s`;
  }

  if (prof.autostart_error_delay !== undefined) {
    const eSlider = document.getElementById("autostartErrorSlider");
    const eVal = document.getElementById("autostartErrorVal");
    if (eSlider) eSlider.value = prof.autostart_error_delay;
    if (eVal) eVal.textContent = `${parseFloat(prof.autostart_error_delay).toFixed(1)}s`;
  }

  if (prof.auto_mic !== undefined) {
    const autoMicToggle = document.getElementById("autoMicToggle");
    const autoMicVal = document.getElementById("autoMicVal");
    if (autoMicToggle) autoMicToggle.checked = Boolean(prof.auto_mic);
    if (autoMicVal) autoMicVal.textContent = prof.auto_mic ? "Ja" : "Nein";
    autoMic = Boolean(prof.auto_mic);
    localStorage.setItem("ci_automic", autoMic ? "true" : "false");
  }

  if (prof.auto_start !== undefined) {
    autoStart = Boolean(prof.auto_start);
    localStorage.setItem("ci_autostart", autoStart ? "true" : "false");
    updateAutoStartUI();
  }

  if (prof.adaptive_snr !== undefined) {
    adaptiveSNR = Boolean(prof.adaptive_snr);
    localStorage.setItem("ci_adaptive_snr", adaptiveSNR ? "true" : "false");
    const adaptiveSNRToggle = document.getElementById("adaptiveSNRToggle");
    const adaptiveSNRVal = document.getElementById("adaptiveSNRVal");
    if (adaptiveSNRToggle) adaptiveSNRToggle.checked = adaptiveSNR;
    if (adaptiveSNRVal) adaptiveSNRVal.textContent = adaptiveSNR ? "Ein" : "Aus";
  }

  if (prof.vocoder_enabled !== undefined) {
    vocoderEnabled = Boolean(prof.vocoder_enabled);
    const vocoderToggle = document.getElementById("vocoderToggle");
    const vocoderVal = document.getElementById("vocoderVal");
    if (vocoderToggle) vocoderToggle.checked = vocoderEnabled;
    if (vocoderVal) vocoderVal.textContent = vocoderEnabled ? "Ein" : "Aus";
  }

  if (prof.vocoder_profile) {
    const vocoderProfileSelect = document.getElementById("vocoderProfileSelect");
    if (vocoderProfileSelect) vocoderProfileSelect.value = prof.vocoder_profile;
  }

  syncNoiseConfig();
}

async function openProfileModal() {
  const modal = document.getElementById("profileModal");
  if (!modal) return;
  modal.classList.remove("hidden");
  document.getElementById("profileEditFormContainer")?.classList.add("hidden");
  await refreshProfileList();
}
window.openProfileModal = openProfileModal;

function closeProfileModal() {
  const modal = document.getElementById("profileModal");
  if (modal) modal.classList.add("hidden");
}
window.closeProfileModal = closeProfileModal;

async function refreshProfileList() {
  try {
    const res = await fetch("/api/profiles");
    if (res.ok) {
      allUserProfiles = await res.json();
      renderProfileList();
    }
  } catch (e) {
    console.error("Fehler beim Laden der Profile:", e);
  }
}

function renderProfileList() {
  const container = document.getElementById("profileListContainer");
  if (!container) return;

  if (!allUserProfiles || allUserProfiles.length === 0) {
    container.innerHTML = `<div style="text-align:center; padding:1.5rem; color:var(--text-muted);">Keine Profile gefunden.</div>`;
    return;
  }

  container.innerHTML = allUserProfiles.map(p => {
    const isActive = p.is_active;
    const fittingBadge = getFittingLabel(p.fitting_type);
    const dateFormatted = p.first_fitting_date ? p.first_fitting_date : "Nicht hinterlegt";
    const balLabel = p.audio_balance === -1 ? "Links" : p.audio_balance === 1 ? "Rechts" : "Zentriert";

    return `
      <div class="glass-card" style="padding:1rem 1.2rem; border-radius:14px; border:1px solid ${isActive ? 'rgba(59,130,246,0.6)' : 'var(--panel-border)'}; background:${isActive ? 'rgba(30,58,138,0.2)' : 'rgba(15,23,42,0.5)'}; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
        <div style="display:flex; flex-direction:column; gap:0.35rem; flex:1; min-width:240px;">
          <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
            <span style="font-size:1.1rem; font-weight:700; color:white;">${escapeHtml(p.name)}</span>
            <span class="cat-tag" style="background:rgba(59,130,246,0.2); color:#93C5FD; font-size:0.75rem;">${escapeHtml(fittingBadge)}</span>
            ${isActive ? '<span class="cat-tag" style="background:rgba(34,197,94,0.3); color:#4ADE80; font-weight:700; font-size:0.75rem;">🟢 Aktiv</span>' : ''}
          </div>
          <div style="font-size:0.82rem; color:var(--text-muted); display:flex; gap:1rem; flex-wrap:wrap;">
            <span>🔬 <strong>Implantat:</strong> ${escapeHtml(p.implant_model || "—")}</span>
            <span>🗓 <strong>Erstanpassung:</strong> ${escapeHtml(dateFormatted)}</span>
            <span>🎚 <strong>Audio:</strong> ${Math.round(p.master_gain * 100)}% Vol | ${p.speech_rate}x Rate | ${balLabel}</span>
          </div>
        </div>

        <div style="display:flex; align-items:center; gap:0.5rem;">
          ${!isActive ? `
            <button class="btn btn-primary btn-sm" onclick="switchActiveProfile('${p.id}')" style="padding:0.35rem 0.8rem; font-size:0.8rem;">
              Aktivieren
            </button>
          ` : ''}
          <button class="btn btn-secondary btn-sm" onclick="openProfileEditForm('${p.id}')" title="Profil bearbeiten" style="padding:0.35rem 0.75rem; font-size:0.8rem;">
            ✏️ Bearbeiten
          </button>
          ${allUserProfiles.length > 1 ? `
            <button class="btn btn-exit btn-sm" onclick="deleteUserProfile('${p.id}')" title="Profil löschen" style="padding:0.35rem 0.6rem; font-size:0.8rem;">
              🗑️
            </button>
          ` : `
            <button class="btn btn-secondary btn-sm" disabled title="Das letzte verbleibende Profil kann nicht gelöscht werden" style="padding:0.35rem 0.6rem; font-size:0.8rem; opacity:0.3; cursor:not-allowed;">
              🗑️
            </button>
          `}
        </div>
      </div>
    `;
  }).join("");
}

let saveProfileAudioTimer = null;
function debouncedSaveActiveProfileAudio(delay = 400) {
  if (!activeProfile || !activeProfile.id) return;
  clearTimeout(saveProfileAudioTimer);
  saveProfileAudioTimer = setTimeout(async () => {
    try {
      const autoMicEl = document.getElementById("autoMicToggle");
      const sSlider = document.getElementById("autostartSuccessSlider");
      const eSlider = document.getElementById("autostartErrorSlider");
      const fSelect = document.getElementById("freqFilterSelect");

      const payload = {
        audio_balance: audioBalance,
        master_gain: audioVolume,
        speech_rate: audioRate,
        mask_noise: maskNoise ? 1 : 0,
        noise_volume: noiseVolume,
        freq_filter: fSelect ? fSelect.value : selectedFreqFilter,
        autostart_success_delay: sSlider ? parseFloat(sSlider.value) : 1.8,
        autostart_error_delay: eSlider ? parseFloat(eSlider.value) : 5.0,
        auto_mic: autoMicEl ? (autoMicEl.checked ? 1 : 0) : 1,
        exercise_lang: window.currentLanguage || "de"
      };

      if (window.currentLanguage === "en") {
        payload.voice_en = selectedVoice;
      } else {
        payload.voice = selectedVoice;
      }

      await fetch(`/api/profiles/${encodeURIComponent(activeProfile.id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      Object.assign(activeProfile, payload);
    } catch (e) {
      console.error("Fehler beim automatischen Speichern der Profil-Audioeinstellungen:", e);
    }
  }, delay);
}

function openProfileEditForm(profileId) {
  const formCont = document.getElementById("profileEditFormContainer");
  const title = document.getElementById("profileFormTitle");
  const idInput = document.getElementById("profileFormId");
  const nameInput = document.getElementById("profileFormName");
  const fitSelect = document.getElementById("profileFormFitting");
  const impSelect = document.getElementById("profileFormImplant");
  const dateInput = document.getElementById("profileFormFittingDate");
  const fitBadge = document.getElementById("profileFormFittingBadge");
  const delBtn = document.getElementById("deleteProfileFormBtn");

  if (!formCont) return;
  formCont.classList.remove("hidden");

  if (delBtn) {
    if (profileId && allUserProfiles.length > 1) {
      delBtn.style.display = "inline-flex";
      delBtn.onclick = () => deleteUserProfile(profileId);
    } else {
      delBtn.style.display = "none";
    }
  }

  const langSelect = document.getElementById("profileFormLang");
  if (profileId) {
    const prof = allUserProfiles.find(p => p.id === profileId);
    if (prof) {
      if (title) title.textContent = `Profil bearbeiten: ${prof.name}`;
      if (idInput) idInput.value = prof.id;
      if (nameInput) nameInput.value = prof.name;
      if (fitSelect) fitSelect.value = prof.fitting_type || "bilateral";
      if (impSelect) impSelect.value = prof.implant_model || "Cochlear Nucleus 8";
      if (dateInput) dateInput.value = prof.first_fitting_date ? prof.first_fitting_date.slice(0, 10) : "";
      if (langSelect) langSelect.value = prof.exercise_lang || "de";
      if (fitBadge) fitBadge.textContent = getFittingShortLabel(prof.fitting_type);
      formCont.scrollIntoView({ behavior: "smooth" });
      return;
    }
  }

  // New Profile
  if (title) title.textContent = "Neues Profil anlegen";
  if (idInput) idInput.value = "";
  if (nameInput) nameInput.value = `Profil ${allUserProfiles.length + 1}`;
  if (fitSelect) fitSelect.value = "bilateral";
  if (impSelect) impSelect.value = "Cochlear Nucleus 8";
  if (langSelect) langSelect.value = window.currentLanguage || "de";
  const todayStr = new Date().toISOString().slice(0, 10);
  if (dateInput) dateInput.value = todayStr;
  if (fitBadge) fitBadge.textContent = "Bilateral";
  formCont.scrollIntoView({ behavior: "smooth" });
}

window.openProfileEditForm = openProfileEditForm;

async function saveProfileForm() {
  const id = document.getElementById("profileFormId")?.value.trim();
  const name = document.getElementById("profileFormName")?.value.trim() || "Profil";
  const fitting_type = document.getElementById("profileFormFitting")?.value || "bilateral";
  const implant_model = document.getElementById("profileFormImplant")?.value || "Cochlear Nucleus 8";
  const first_fitting_date = document.getElementById("profileFormFittingDate")?.value || "";
  const exercise_lang = document.getElementById("profileFormLang")?.value || "de";

  let derivedBalance = audioBalance;
  if (["monoral_l", "bimodal_l", "ssd_l"].includes(fitting_type)) {
    derivedBalance = -1.0;
  } else if (["monoral_r", "bimodal_r", "ssd_r"].includes(fitting_type)) {
    derivedBalance = 1.0;
  }
  audioBalance = derivedBalance;
  localStorage.setItem("ci_audio_balance", audioBalance.toString());

  const payload = {
    name,
    fitting_type,
    implant_model,
    first_fitting_date,
    exercise_lang,
    audio_balance: audioBalance
  };

  try {
    let res;
    if (id) {
      res = await fetch(`/api/profiles/${encodeURIComponent(id)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } else {
      res = await fetch("/api/profiles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...payload,
          master_gain: audioVolume,
          speech_rate: audioRate,
          voice: selectedVoice,
          mask_noise: maskNoise ? 1 : 0,
          noise_volume: noiseVolume
        })
      });
    }

    if (res.ok) {
      showToast("Profil erfolgreich gespeichert! ✅", "success");
      document.getElementById("profileEditFormContainer")?.classList.add("hidden");
      await refreshProfileList();
      await loadActiveProfile();
    } else {
      showToast("Fehler beim Speichern des Profils.", "danger");
    }
  } catch (e) {
    console.error("Fehler beim Speichern:", e);
    showToast("Netzwerkfehler beim Speichern.", "danger");
  }
}

async function switchActiveProfile(profileId) {
  try {
    const res = await fetch(`/api/profiles/${encodeURIComponent(profileId)}/activate`, {
      method: "POST"
    });
    if (res.ok) {
      showToast("Profil aktiviert! 🦻 Audio-Settings angewendet.", "success");
      await refreshProfileList();
      await loadActiveProfile();
    }
  } catch (e) {
    console.error("Fehler beim Aktivieren:", e);
    showToast("Fehler beim Profilwechsel.", "danger");
  }
}
window.switchActiveProfile = switchActiveProfile;

async function deleteUserProfile(profileId) {
  if (allUserProfiles.length <= 1) {
    showToast("Das letzte verbleibende Profil kann nicht gelöscht werden.", "warning");
    return;
  }

  const prof = allUserProfiles.find(p => p.id === profileId);
  const name = prof ? `"${prof.name}"` : "dieses Profil";

  if (!confirm(`Möchtest du das Hörprofil ${name} wirklich unwiderruflich löschen?`)) return;

  try {
    const res = await fetch(`/api/profiles/${encodeURIComponent(profileId)}`, {
      method: "DELETE"
    });
    if (res.ok) {
      showToast("Profil gelöscht. 🗑️", "success");
      document.getElementById("profileEditFormContainer")?.classList.add("hidden");
      await refreshProfileList();
      await loadActiveProfile();
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.error || "Löschen fehlgeschlagen.", "danger");
    }
  } catch (e) {
    console.error("Fehler beim Löschen:", e);
    showToast("Netzwerkfehler beim Löschen.", "danger");
  }
}
window.deleteUserProfile = deleteUserProfile;

// Screenshot auto-capture trigger on load
document.addEventListener("DOMContentLoaded", () => {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("capture") === "true") {
    setTimeout(() => { if (typeof window.captureDocsScreenshots === "function") window.captureDocsScreenshots(); }, 1800);
  }
});

// ─── Handbuch Screenshot-Generator ─────────────────────────────────────────
window.captureDocsScreenshots = async function() {
  if (typeof showToast === "function") showToast("📸 Erfasse Screenshots für das Handbuch...", "info");
  
  if (typeof html2canvas === "undefined") {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("html2canvas konnte nicht geladen werden."));
      document.head.appendChild(script);
    });
  }

  async function captureAndUpload(element, filename) {
    if (!element) return;
    const canvas = await html2canvas(element, {
      backgroundColor: "#0B0F19",
      scale: 1.5,
      logging: false,
      useCORS: true
    });
    const dataUrl = canvas.toDataURL("image/png");
    await fetch("/api/upload_image", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, data: dataUrl })
    });
  }

  try {
    if (typeof closeHelpModal === "function") closeHelpModal();
    await new Promise(r => setTimeout(r, 400));

    // 1. Navigation Bar
    const navEl = document.querySelector(".tab-nav");
    if (navEl) await captureAndUpload(navEl, "nav_bar.png");

    // 2. Audio Settings Panel
    const ctrlPanel = document.getElementById("controlPanelDetails");
    if (ctrlPanel) {
      ctrlPanel.open = true;
      await new Promise(r => setTimeout(r, 300));
      await captureAndUpload(ctrlPanel, "audio_settings.png");
      ctrlPanel.open = false;
    }

    // 3. Exercise Card
    const exCard = document.querySelector(".card-inner") || document.querySelector(".tab-panel.active");
    if (exCard) await captureAndUpload(exCard, "exercise_card.png");

    // 4. Profiles Modal
    if (typeof openProfileModal === "function") {
      openProfileModal();
      await new Promise(r => setTimeout(r, 400));
      const profModalContent = document.querySelector("#profileModal .modal-content");
      if (profModalContent) await captureAndUpload(profModalContent, "profiles.png");
      if (typeof closeProfileModal === "function") closeProfileModal();
      await new Promise(r => setTimeout(r, 300));
    }

    // 5. Full Dashboard
    const appEl = document.querySelector(".app-container") || document.body;
    if (appEl) await captureAndUpload(appEl, "dashboard.png");

    if (typeof showToast === "function") {
      showToast("✅ Alle Handbuch-Screenshots erfolgreich in docs/images/ aktualisiert!", "success");
    }
  } catch (err) {
    console.error("Screenshot capture error:", err);
    if (typeof showToast === "function") {
      showToast("Fehler beim Erfassen: " + err.message, "danger");
    }
  }
};

// Stop background noise immediately when the browser tab/window is closed or navigated away
window.addEventListener("beforeunload", () => {
  if (navigator.sendBeacon) {
    navigator.sendBeacon("/api/noise/stop");
  } else {
    fetch("/api/noise/stop", { method: "POST", keepalive: true }).catch(() => {});
  }
});

window.addEventListener("pagehide", () => {
  if (navigator.sendBeacon) {
    navigator.sendBeacon("/api/noise/stop");
  } else {
    fetch("/api/noise/stop", { method: "POST", keepalive: true }).catch(() => {});
  }
});


// ─── Therapeutenbericht (Logopädische & Audiologische Dokumentation) ──────
let cachedTherapistReportData = null;

async function openTherapistReportModal() {
  const modal = document.getElementById("therapistReportModal");
  if (modal) modal.classList.remove("hidden");
  await loadAndRenderTherapistReport();
}
window.openTherapistReportModal = openTherapistReportModal;

function closeTherapistReportModal() {
  const modal = document.getElementById("therapistReportModal");
  if (modal) modal.classList.add("hidden");
}
window.closeTherapistReportModal = closeTherapistReportModal;

async function loadAndRenderTherapistReport() {
  const container = document.getElementById("therapistReportContainer");
  if (!container) return;

  container.innerHTML = `<div style="text-align:center; padding: 2rem; color:var(--text-muted);"><span>⏳ Generiere Therapeutenbericht...</span></div>`;

  try {
    const res = await fetch("/api/reports/therapist");
    if (!res.ok) throw new Error("Fehler beim Abrufen des Berichts");
    const data = await res.json();
    cachedTherapistReportData = data;

    const profile = data.profile || {};
    const summary = data.summary || {};
    const categories = data.by_category || {};
    const testRuns = data.test_runs || [];
    const olsaRuns = data.olsa_runs || [];
    const weakCats = data.weak_categories || [];

    let html = `
      <div class="therapist-report-sheet">
        <!-- Report Header -->
        <div style="border-bottom: 2px solid #3B82F6; padding-bottom: 1rem; margin-bottom: 1.2rem; display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <h2 style="margin: 0; color: #1E293B; font-size: 1.4rem;">KLINISCHER THERAPEUTENBERICHT</h2>
            <p style="margin: 0.2rem 0 0 0; color: #64748B; font-size: 0.85rem;">Dokumentation des auditiven Hörtrainings & Sprachaudiometrie</p>
          </div>
          <div style="text-align: right; font-size: 0.8rem; color: #64748B;">
            <div>Erstellt am: <strong>${data.generated_at || new Date().toLocaleString("de-DE")}</strong></div>
          </div>
        </div>

        <!-- Patient Profile Box -->
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 1rem; margin-bottom: 1.2rem;">
          <h4 style="margin: 0 0 0.6rem 0; color: #1E293B; font-size: 0.95rem; border-bottom: 1px dashed #CBD5E1; padding-bottom: 0.4rem;">👤 Patient / CI-Versorgungsprofil</h4>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0.6rem; font-size: 0.85rem; color: #334155;">
            <div><strong>Name / Profil:</strong> ${profile.name || "Standard Profil"}</div>
            <div><strong>Versorgung:</strong> ${(profile.fitting_type || "Bilateral").toUpperCase()}</div>
            <div><strong>CI-Implantat:</strong> ${profile.implant_model || "Cochlear Nucleus 8"}</div>
            <div><strong>Erstanpassung (EA):</strong> ${profile.first_fitting_date || "Keine Angabe"}</div>
            <div><strong>Wort-Lautstärke:</strong> ${Math.round((profile.master_gain || 1.0) * 100)}%</div>
            <div><strong>Sprechtempo:</strong> ${(profile.speech_rate || 1.0).toFixed(1)}x</div>
          </div>
        </div>

        <!-- Summary KPIs -->
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.8rem; margin-bottom: 1.4rem;">
          <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 0.8rem; text-align: center;">
            <div style="font-size: 0.75rem; color: #1D4ED8; font-weight: 600; text-transform: uppercase;">Trefferquote</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #1E40AF;">${summary.accuracy || 0}%</div>
            <div style="font-size: 0.72rem; color: #3B82F6;">${summary.correct_attempts || 0} von ${summary.total_attempts || 0} richtig</div>
          </div>
          <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 0.8rem; text-align: center;">
            <div style="font-size: 0.75rem; color: #15803D; font-weight: 600; text-transform: uppercase;">Übungen Gesamt</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #166534;">${summary.total_attempts || 0}</div>
            <div style="font-size: 0.72rem; color: #22C55E;">${summary.active_days || 0} aktive Trainingstage</div>
          </div>
          <div style="background: #FAF5FF; border: 1px solid #E9D5FF; border-radius: 8px; padding: 0.8rem; text-align: center;">
            <div style="font-size: 0.75rem; color: #6B21A8; font-weight: 600; text-transform: uppercase;">Ø Score</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #581C87;">${summary.avg_score || 0}%</div>
            <div style="font-size: 0.72rem; color: #A855F7;">Gewichtete Bewertung</div>
          </div>
          <div style="background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 8px; padding: 0.8rem; text-align: center;">
            <div style="font-size: 0.75rem; color: #C2410C; font-weight: 600; text-transform: uppercase;">Trainingszeitraum</div>
            <div style="font-size: 0.82rem; font-weight: 700; color: #9A3412; margin-top: 0.4rem;">${(summary.first_attempt || "").split(" ")[0] || "-"}</div>
            <div style="font-size: 0.72rem; color: #EA580C;">bis ${(summary.last_attempt || "").split(" ")[0] || "-"}</div>
          </div>
        </div>

        <!-- Logopedic Focus / Recommendations -->
        <div style="background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 8px; padding: 1rem; margin-bottom: 1.4rem;">
          <h4 style="margin: 0 0 0.5rem 0; color: #92400E; font-size: 0.92rem; display: flex; align-items: center; gap: 0.4rem;">
            <span>🎯</span> Logopädischer Therapie-Fokus &amp; Laut-Analysen
          </h4>
          ${weakCats.length > 0 ? `
            <p style="margin: 0 0 0.5rem 0; font-size: 0.83rem; color: #78350F;">
              Aufgrund der aktuellen Trefferquoten wird eine gezielte logopädische Übung folgender Lautkontraste empfohlen:
            </p>
            <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
              ${weakCats.map(c => `<span style="background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.8rem; font-weight: 600;">⚠️ ${c}</span>`).join("")}
            </div>
          ` : `
            <p style="margin:0; font-size: 0.83rem; color: #78350F;">
              ✅ Sehr gute Unterscheidungsleistung über alle geübten Lautkategorien (> 60% Trefferquote). Es liegen aktuell keine akuten Schwachstellen vor.
            </p>
          `}
        </div>

        <!-- Category Accuracy Breakdown Table -->
        <div style="margin-bottom: 1.4rem;">
          <h4 style="margin: 0 0 0.6rem 0; color: #1E293B; font-size: 0.95rem;">📊 Leistung nach Laut- &amp; Übungskategorien</h4>
          <table style="width: 100%; border-collapse: collapse; font-size: 0.83rem; text-align: left;">
            <thead>
              <tr style="background: #F1F5F9; color: #475569; border-bottom: 2px solid #CBD5E1;">
                <th style="padding: 0.5rem 0.8rem;">Kategorie / Kontrast</th>
                <th style="padding: 0.5rem 0.8rem; text-align: center;">Übungen</th>
                <th style="padding: 0.5rem 0.8rem; text-align: center;">Richtig</th>
                <th style="padding: 0.5rem 0.8rem; text-align: right;">Trefferquote</th>
              </tr>
            </thead>
            <tbody>
              ${Object.keys(categories).length > 0 ? Object.entries(categories).map(([cat, item]) => {
                const acc = item.accuracy || 0;
                const statusColor = acc >= 75 ? "#16A34A" : (acc >= 50 ? "#D97706" : "#DC2626");
                return `
                  <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="padding: 0.45rem 0.8rem; font-weight: 600; color: #334155;">${cat}</td>
                    <td style="padding: 0.45rem 0.8rem; text-align: center; color: #64748B;">${item.count}</td>
                    <td style="padding: 0.45rem 0.8rem; text-align: center; color: #64748B;">${item.correct}</td>
                    <td style="padding: 0.45rem 0.8rem; text-align: right; font-weight: 700; color: ${statusColor};">${acc}%</td>
                  </tr>
                `;
              }).join("") : `<tr><td colspan="4" style="padding: 0.8rem; text-align: center; color: #94A3B8;">Noch keine Kategoriendaten vorhanden.</td></tr>`}
            </tbody>
          </table>
        </div>

        <!-- Speech Audiometry History -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem;">
          <div>
            <h4 style="margin: 0 0 0.5rem 0; color: #1E293B; font-size: 0.9rem;">🏛 Freiburger Sprachtests (DIN 45621)</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.78rem;">
              <thead>
                <tr style="background: #F1F5F9; color: #475569; border-bottom: 1px solid #CBD5E1;">
                  <th style="padding: 0.4rem;">Datum</th>
                  <th style="padding: 0.4rem;">Testliste</th>
                  <th style="padding: 0.4rem; text-align: right;">Ergebnis</th>
                </tr>
              </thead>
              <tbody>
                ${testRuns.length > 0 ? testRuns.slice(0, 5).map(r => `
                  <tr style="border-bottom: 1px solid #F1F5F9;">
                    <td style="padding: 0.35rem; color: #64748B;">${(r.timestamp || "").split(" ")[0]}</td>
                    <td style="padding: 0.35rem; font-weight: 600; color: #334155;">${r.list_name}</td>
                    <td style="padding: 0.35rem; text-align: right; font-weight: 700; color: #2563EB;">${r.correct_words}/${r.total_words} (${Math.round(r.score)}%)</td>
                  </tr>
                `).join("") : `<tr><td colspan="3" style="padding: 0.5rem; text-align: center; color: #94A3B8;">Keine Freiburger Testläufe.</td></tr>`}
              </tbody>
            </table>
          </div>

          <div>
            <h4 style="margin: 0 0 0.5rem 0; color: #1E293B; font-size: 0.9rem;">🎯 Adaptive OLSA SRT Testergebnisse</h4>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.78rem;">
              <thead>
                <tr style="background: #F1F5F9; color: #475569; border-bottom: 1px solid #CBD5E1;">
                  <th style="padding: 0.4rem;">Datum</th>
                  <th style="padding: 0.4rem;">Störschall</th>
                  <th style="padding: 0.4rem; text-align: right;">SRT (dB SNR)</th>
                </tr>
              </thead>
              <tbody>
                ${olsaRuns.length > 0 ? olsaRuns.slice(0, 5).map(r => `
                  <tr style="border-bottom: 1px solid #F1F5F9;">
                    <td style="padding: 0.35rem; color: #64748B;">${(r.timestamp || "").split(" ")[0]}</td>
                    <td style="padding: 0.35rem; color: #334155;">${r.noise_type || "OLSA Rauschen"}</td>
                    <td style="padding: 0.35rem; text-align: right; font-weight: 700; color: #059669;">${r.srt_db > 0 ? '+' : ''}${r.srt_db.toFixed(1)} dB</td>
                  </tr>
                `).join("") : `<tr><td colspan="3" style="padding: 0.5rem; text-align: center; color: #94A3B8;">Keine OLSA Durchläufe.</td></tr>`}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Footer Signature Line -->
        <div style="margin-top: 2rem; border-top: 1px solid #E2E8F0; padding-top: 1.5rem; display: flex; justify-content: space-between; font-size: 0.8rem; color: #64748B;">
          <div>Unterschrift Patient / Betreuer: _______________________</div>
          <div>Unterschrift Logopäde / Audiologe: _______________________</div>
        </div>
      </div>
    `;

    container.innerHTML = html;
  } catch (err) {
    console.error("Error loading therapist report:", err);
    container.innerHTML = `<div style="text-align:center; padding: 2rem; color:var(--danger);">⚠️ Fehler beim Laden des Therapeutenberichts: ${err.message}</div>`;
  }
}

function printTherapistReport() {
  window.print();
}
window.printTherapistReport = printTherapistReport;


// ─── System Logs ─────────────────────────────────────────────────────────────
async function fetchSystemLogs() {
  const container = document.getElementById("systemLogsContainer");
  if (!container) return;
  container.innerText = "Lade Logs...";
  try {
    const res = await fetch("/api/system_logs");
    const data = await res.json();
    if (data.error) {
      container.innerText = `Fehler: ${data.error}`;
    } else {
      container.innerText = data.logs || "Keine Logs vorhanden.";
      // Scroll to bottom
      container.scrollTop = container.scrollHeight;
    }
  } catch (err) {
    console.error("Error fetching logs:", err);
    container.innerText = `Fehler beim Laden der Logs: ${err.message}`;
  }
}

function openSystemLogsModal() {
  const modal = document.getElementById("systemLogsModal");
  if (modal) modal.classList.remove("hidden");
  fetchSystemLogs();
}
window.openSystemLogsModal = openSystemLogsModal;
window.fetchSystemLogs = fetchSystemLogs;

function closeSystemLogsModal() {
  const modal = document.getElementById("systemLogsModal");
  if (modal) modal.classList.add("hidden");
}
window.closeSystemLogsModal = closeSystemLogsModal;
