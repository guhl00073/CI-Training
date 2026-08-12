import tkinter as tk
from tkinter import ttk, messagebox
import random
import pathlib

import threading
from src.audio.tts_engine import TTSEngine
from src.audio.player import AudioPlayer
from src.audio.recorder import AudioRecorder
from src.evaluator.phonetic_matcher import PhoneticMatcher
from src.database.progress_db import ProgressDatabase
from src.stt.stt_engine import STTEngine

class CardButton(tk.Label):
    """
    High-contrast clickable Card widget for macOS/Linux/Windows.
    Bypasses macOS native button styling limitations.
    """
    def __init__(self, parent, text="", command=None, width=16, height=3, **kwargs):
        super().__init__(
            parent, text=text, font=("Helvetica", 22, "bold"),
            bg="#1E293B", fg="#FFFFFF", relief="ridge", bd=3,
            padx=30, pady=20, cursor="hand2", width=width, height=height, **kwargs
        )
        self.command = command
        self._bg_color = "#1E293B"
        self._is_enabled = True
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def set_card_text(self, text: str, bg: str = "#1E293B", enabled: bool = True):
        self._bg_color = bg
        self._is_enabled = enabled
        self.config(text=text, bg=bg, fg="#FFFFFF")

    def _on_click(self, event):
        if self._is_enabled and self.command:
            self.command()

    def _on_enter(self, event):
        if self._is_enabled:
            self.config(bg="#3B82F6")

    def _on_leave(self, event):
        if self._is_enabled:
            self.config(bg=self._bg_color)

class CIAudioTrainerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CI-Hörtrainer (Audiolog-Stil Hörtrainingsprogramm)")
        self.root.geometry("980x720")
        self.root.configure(bg="#0F172A")

        # Core Engines
        self.tts = TTSEngine()
        self.player = AudioPlayer()
        self.recorder = AudioRecorder()
        self.matcher = PhoneticMatcher()
        self.db = ProgressDatabase()
        self.stt = STTEngine()

        # Audio Settings State
        self.volume_var = tk.DoubleVar(value=0.9)
        self.balance_var = tk.DoubleVar(value=0.0) # -1.0 (Left), 0.0 (Both), 1.0 (Right)
        self.rate_var = tk.DoubleVar(value=1.0)
        self.autostart_var = tk.BooleanVar(value=False)

        # Datasets — aus SQLite-Datenbank (kein JSON-Direktzugriff mehr)
        _exercises = self.db.get_all_exercises()
        self.minimal_pairs = _exercises["minimal_pairs"]
        self.monosyllables = _exercises["monosyllables"]
        self.numbers       = _exercises["numbers"]

        # Current Exercise State
        self.current_item = None
        self.current_target_word = ""

        # Build GUI
        self._setup_styles()
        self._create_header()
        self._create_audio_controls()
        self._create_notebook()
        self._create_statusbar()


    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Colors
        BG_DARK = "#0F172A"
        BG_PANEL = "#1E293B"
        ACCENT_BLUE = "#3B82F6"
        ACCENT_GREEN = "#10B981"
        TEXT_LIGHT = "#F8FAFC"

        style.configure(".", background=BG_DARK, foreground=TEXT_LIGHT, font=("Helvetica", 11))
        style.configure("TFrame", background=BG_DARK)
        style.configure("Panel.TFrame", background=BG_PANEL, relief="flat")
        
        style.configure("TLabel", background=BG_DARK, foreground=TEXT_LIGHT, font=("Helvetica", 11))
        style.configure("Header.TLabel", font=("Helvetica", 20, "bold"), foreground="#60A5FA", background=BG_DARK)
        style.configure("SubHeader.TLabel", font=("Helvetica", 13, "bold"), foreground="#94A3B8", background=BG_DARK)
        style.configure("Panel.TLabel", background=BG_PANEL, foreground=TEXT_LIGHT, font=("Helvetica", 11, "bold"))

        # Buttons
        style.configure("Accent.TButton", font=("Helvetica", 12, "bold"), background=ACCENT_BLUE, foreground="#FFFFFF", borderwidth=0, padding=8)
        style.map("Accent.TButton", background=[("active", "#2563EB")])

        style.configure("Green.TButton", font=("Helvetica", 12, "bold"), background=ACCENT_GREEN, foreground="#FFFFFF", borderwidth=0, padding=8)
        style.map("Green.TButton", background=[("active", "#059669")])

        # Notebook / Tabs
        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_PANEL, foreground="#94A3B8", padding=[18, 10], font=("Helvetica", 12, "bold"))
        style.map("TNotebook.Tab", background=[("selected", ACCENT_BLUE)], foreground=[("selected", "#FFFFFF")])

    def _create_header(self):
        header_frame = ttk.Frame(self.root, padding="15 15 15 5")
        header_frame.pack(fill="x")

        lbl_title = ttk.Label(header_frame, text="👂 CI-Hörtrainer", style="Header.TLabel")
        lbl_title.pack(side="left")

        lbl_subtitle = ttk.Label(header_frame, text="Audio-phonetisches Hörtraining für Cochlea-Implantat Träger", style="SubHeader.TLabel")
        lbl_subtitle.pack(side="left", padx=15)

    def _create_audio_controls(self):
        ctrl_frame = ttk.Frame(self.root, style="Panel.TFrame", padding="15")
        ctrl_frame.pack(fill="x", padx=15, pady=10)

        # Volume
        ttk.Label(ctrl_frame, text="🔊 Lautstärke:", style="Panel.TLabel").grid(row=0, column=0, sticky="w", padx=5)
        scale_vol = ttk.Scale(ctrl_frame, from_=0.0, to=2.5, variable=self.volume_var, orient="horizontal", length=120)
        scale_vol.grid(row=0, column=1, padx=5)

        # Balance (Left / Both / Right)
        ttk.Label(ctrl_frame, text="🎧 Ohr-Kanal:", style="Panel.TLabel").grid(row=0, column=2, sticky="w", padx=(20, 5))
        btn_left = ttk.Button(ctrl_frame, text="Links (CI)", command=lambda: self.balance_var.set(-1.0), width=9)
        btn_left.grid(row=0, column=3, padx=2)
        btn_both = ttk.Button(ctrl_frame, text="Beide", command=lambda: self.balance_var.set(0.0), width=7)
        btn_both.grid(row=0, column=4, padx=2)
        btn_right = ttk.Button(ctrl_frame, text="Rechts (CI)", command=lambda: self.balance_var.set(1.0), width=9)
        btn_right.grid(row=0, column=5, padx=2)

        # Speed / Rate
        ttk.Label(ctrl_frame, text="⏱ Tempo:", style="Panel.TLabel").grid(row=0, column=6, sticky="w", padx=(20, 5))
        scale_rate = ttk.Scale(ctrl_frame, from_=0.6, to=1.4, variable=self.rate_var, orient="horizontal", length=110)
        scale_rate.grid(row=0, column=7, padx=5)

        # Autostart Checkbox
        chk_autostart = ttk.Checkbutton(ctrl_frame, text="⚡ Autostart", variable=self.autostart_var)
        chk_autostart.grid(row=0, column=8, padx=(15, 5))

    def _create_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=5)

        # Tab 1: Minimalpaare
        self.tab_mp = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_mp, text=" Minimalpaare ")
        self._build_minimal_pairs_tab()

        # Tab 2: Einsilber
        self.tab_es = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_es, text=" Einsilber-Training ")
        self._build_monosyllable_tab()

        # Tab 3: Zahlen
        self.tab_num = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_num, text=" Zahlenverständnis ")
        self._build_numbers_tab()

        # Tab 4: Statistik
        self.tab_stats = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_stats, text=" Statistik & Fortschritt ")
        self._build_stats_tab()

    # ---------------- Minimalpaare ----------------
    def _build_minimal_pairs_tab(self):
        lbl_info = ttk.Label(self.tab_mp, text="Höre das Wort und klicke auf die richtige Karte:", style="SubHeader.TLabel")
        lbl_info.pack(anchor="w", pady=5)

        self.mp_cat_label = ttk.Label(self.tab_mp, text="Kategorie: -", font=("Helvetica", 13, "bold"), foreground="#60A5FA")
        self.mp_cat_label.pack(anchor="w", pady=4)

        # Play audio button
        btn_play = ttk.Button(self.tab_mp, text="▶ Audio abspielen", style="Accent.TButton", command=self._play_mp_audio)
        btn_play.pack(pady=15)

        # Cards for Option A vs Option B
        cards_frame = ttk.Frame(self.tab_mp)
        cards_frame.pack(pady=15)

        self.btn_option_a = CardButton(
            cards_frame, text="Wort A", command=lambda: self._check_mp_answer(0)
        )
        self.btn_option_a.grid(row=0, column=0, padx=25)

        self.btn_option_b = CardButton(
            cards_frame, text="Wort B", command=lambda: self._check_mp_answer(1)
        )
        self.btn_option_b.grid(row=0, column=1, padx=25)

        # Feedback & Next
        self.mp_feedback_lbl = ttk.Label(self.tab_mp, text="", font=("Helvetica", 14, "bold"))
        self.mp_feedback_lbl.pack(pady=12)

        btn_next = ttk.Button(self.tab_mp, text="Nächste Übung ➔", command=lambda: self._next_mp_item(user_triggered=True))
        btn_next.pack(pady=5)

        self._next_mp_item(user_triggered=False)

    def _next_mp_item(self, user_triggered: bool = False):
        if not self.minimal_pairs:
            return
        self.current_mp_item = random.choice(self.minimal_pairs)
        self.mp_target_index = random.choice([0, 1])
        words = [self.current_mp_item["word_a"], self.current_mp_item["word_b"]]
        self.mp_target_word = words[self.mp_target_index]

        self.mp_cat_label.config(text=f"Kategorie: {self.current_mp_item['category']} | Hinweis: {self.current_mp_item['hint']}")
        self.btn_option_a.set_card_text(words[0], bg="#1E293B", enabled=True)
        self.btn_option_b.set_card_text(words[1], bg="#1E293B", enabled=True)
        self.mp_feedback_lbl.config(text="")
        self._set_status(f"Bereit für Minimalpaar-Übung.")

        if user_triggered and self.autostart_var.get():
            self._play_mp_audio()

    def _play_mp_audio(self):
        if hasattr(self, 'mp_target_word') and self.mp_target_word:
            bal_str = "Links" if self.balance_var.get() < -0.3 else ("Rechts" if self.balance_var.get() > 0.3 else "Beide")
            self._set_status(f"▶ Spiele Minimalpaar: '{self.mp_target_word}' (Tempo: {round(self.rate_var.get(), 1)}x, Ohr: {bal_str})")
            audio_path = self.tts.generate_audio(self.mp_target_word, rate=self.rate_var.get())
            self.player.play(audio_path, balance=self.balance_var.get(), volume=self.volume_var.get(), rate=self.rate_var.get())

    def _check_mp_answer(self, chosen_index: int):
        words = [self.current_mp_item["word_a"], self.current_mp_item["word_b"]]
        chosen_word = words[chosen_index]
        is_correct = (chosen_index == self.mp_target_index)

        if is_correct:
            self.mp_feedback_lbl.config(text=f"✓ Richtig! Es war '{self.mp_target_word}'.", foreground="#10B981")
            if chosen_index == 0:
                self.btn_option_a.set_card_text(words[0], bg="#10B981", enabled=False)
                self.btn_option_b.set_card_text(words[1], bg="#1E293B", enabled=False)
            else:
                self.btn_option_a.set_card_text(words[0], bg="#1E293B", enabled=False)
                self.btn_option_b.set_card_text(words[1], bg="#10B981", enabled=False)
        else:
            self.mp_feedback_lbl.config(text=f"✗ Falsch. Gehört wurde '{self.mp_target_word}' (du hast '{chosen_word}' gewählt).", foreground="#EF4444")
            if chosen_index == 0:
                self.btn_option_a.set_card_text(words[0], bg="#EF4444", enabled=False)
                self.btn_option_b.set_card_text(words[1], bg="#1E293B", enabled=False)
            else:
                self.btn_option_a.set_card_text(words[0], bg="#1E293B", enabled=False)
                self.btn_option_b.set_card_text(words[1], bg="#EF4444", enabled=False)

        self.db.log_attempt(
            module="Minimalpaare",
            category=self.current_mp_item["category"],
            target_word=self.mp_target_word,
            user_answer=chosen_word,
            is_correct=is_correct,
            score=100.0 if is_correct else 0.0
        )

    # ---------------- Einsilber ----------------
    def _build_monosyllable_tab(self):
        lbl_info = ttk.Label(self.tab_es, text="Höre das Einsilber-Wort und tippe es ein oder sprich es nach:", style="SubHeader.TLabel")
        lbl_info.pack(anchor="w", pady=5)

        btn_play = ttk.Button(self.tab_es, text="▶ Einsilber abspielen", style="Accent.TButton", command=self._play_es_audio)
        btn_play.pack(pady=15)

        input_frame = ttk.Frame(self.tab_es)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Eingabe / Gehörtes Wort:").grid(row=0, column=0, padx=8)
        
        self.entry_es = tk.Entry(
            input_frame, font=("Helvetica", 16, "bold"), width=16,
            bg="#1E293B", fg="#FFFFFF", insertbackground="#FFFFFF",
            relief="solid", bd=2, highlightthickness=2, highlightcolor="#3B82F6"
        )
        self.entry_es.grid(row=0, column=1, padx=8)
        self.entry_es.bind("<Return>", lambda e: self._check_es_answer())

        btn_check = ttk.Button(input_frame, text="Prüfen", style="Green.TButton", command=self._check_es_answer)
        btn_check.grid(row=0, column=2, padx=8)

        btn_mic = ttk.Button(input_frame, text="🎙 Nachsprechen", command=self._record_and_check_es)
        btn_mic.grid(row=0, column=3, padx=8)

        self.es_feedback_lbl = ttk.Label(self.tab_es, text="", font=("Helvetica", 13, "bold"), wraplength=750)
        self.es_feedback_lbl.pack(pady=15)

        btn_next = ttk.Button(self.tab_es, text="Nächster Einsilber ➔", command=lambda: self._next_es_item(user_triggered=True))
        btn_next.pack(pady=5)

        self._next_es_item(user_triggered=False)

    def _record_and_check_es(self):
        def _rec_thread():
            self._set_status("🔴 Mikrofon nimmt auf (3 Sekunden)... Bitte Wort jetzt sprechen!")
            wav_file = self.recorder.record_clip(duration_sec=3.0)
            
            self._set_status("⏳ Spracherkennung läuft...")
            recognized_text = self.stt.transcribe_wav(wav_file, language="de-DE")
            
            self.root.after(0, lambda: self._apply_voice_recognition_es(recognized_text))

        threading.Thread(target=_rec_thread, daemon=True).start()

    def _apply_voice_recognition_es(self, text: str):
        if text:
            self.entry_es.delete(0, tk.END)
            self.entry_es.insert(0, text)
            self._set_status(f"✓ Spracherkennung: '{text}'")
            self._check_es_answer()
        else:
            self.es_feedback_lbl.config(
                text="⚠️ Mikrofonaufnahme nicht erkannt. Bitte erneut versuchen oder tippen.",
                foreground="#F59E0B"
            )
            self._set_status("Spracheingabe nicht erkannt.")

    def _next_es_item(self, user_triggered: bool = False):
        if not self.monosyllables:
            return
        self.current_es_item = random.choice(self.monosyllables)
        self.es_target_word = self.current_es_item["word"]
        self.entry_es.delete(0, tk.END)
        self.es_feedback_lbl.config(text="")
        self._set_status("Bereit für Einsilber-Übung.")

        if user_triggered and self.autostart_var.get():
            self._play_es_audio()

    def _play_es_audio(self):
        if hasattr(self, 'es_target_word') and self.es_target_word:
            bal_str = "Links" if self.balance_var.get() < -0.3 else ("Rechts" if self.balance_var.get() > 0.3 else "Beide")
            self._set_status(f"▶ Spiele Einsilber: '{self.es_target_word}' (Tempo: {round(self.rate_var.get(), 1)}x, Ohr: {bal_str})")
            audio_path = self.tts.generate_audio(self.es_target_word, rate=self.rate_var.get())
            self.player.play(audio_path, balance=self.balance_var.get(), volume=self.volume_var.get(), rate=self.rate_var.get())

    def _check_es_answer(self):
        user_text = self.entry_es.get()
        eval_result = self.matcher.evaluate(self.es_target_word, user_text)

        color = "#10B981" if eval_result["is_correct"] else "#EF4444"
        self.es_feedback_lbl.config(text=eval_result["message"], foreground=color)

        self.db.log_attempt(
            module="Einsilber",
            category=self.current_es_item["category"],
            target_word=self.es_target_word,
            user_answer=user_text,
            is_correct=eval_result["is_correct"],
            score=eval_result["score"]
        )

    # ---------------- Zahlen ----------------
    def _build_numbers_tab(self):
        lbl_info = ttk.Label(self.tab_num, text="Höre die Zahl / Uhrzeit und gib sie ein oder sprich sie nach:", style="SubHeader.TLabel")
        lbl_info.pack(anchor="w", pady=5)

        btn_play = ttk.Button(self.tab_num, text="▶ Zahl abspielen", style="Accent.TButton", command=self._play_num_audio)
        btn_play.pack(pady=15)

        input_frame = ttk.Frame(self.tab_num)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Zahl / Betrag:").grid(row=0, column=0, padx=8)
        
        self.entry_num = tk.Entry(
            input_frame, font=("Helvetica", 16, "bold"), width=15,
            bg="#1E293B", fg="#FFFFFF", insertbackground="#FFFFFF",
            relief="solid", bd=2, highlightthickness=2, highlightcolor="#3B82F6"
        )
        self.entry_num.grid(row=0, column=1, padx=8)
        self.entry_num.bind("<Return>", lambda e: self._check_num_answer())

        btn_check = ttk.Button(input_frame, text="Prüfen", style="Green.TButton", command=self._check_num_answer)
        btn_check.grid(row=0, column=2, padx=8)

        btn_mic = ttk.Button(input_frame, text="🎙 Nachsprechen", command=self._record_and_check_num)
        btn_mic.grid(row=0, column=3, padx=8)

        self.num_feedback_lbl = ttk.Label(self.tab_num, text="", font=("Helvetica", 13, "bold"))
        self.num_feedback_lbl.pack(pady=15)

        btn_next = ttk.Button(self.tab_num, text="Nächste Zahl ➔", command=lambda: self._next_num_item(user_triggered=True))
        btn_next.pack(pady=5)

        self._next_num_item(user_triggered=False)

    def _record_and_check_num(self):
        def _rec_thread():
            self._set_status("🔴 Mikrofon nimmt auf (3 Sekunden)... Bitte Zahl sprechen!")
            wav_file = self.recorder.record_clip(duration_sec=3.0)
            
            self._set_status("⏳ Spracherkennung läuft...")
            recognized_text = self.stt.transcribe_wav(wav_file, language="de-DE")
            
            self.root.after(0, lambda: self._apply_voice_recognition_num(recognized_text))

        threading.Thread(target=_rec_thread, daemon=True).start()

    def _apply_voice_recognition_num(self, text: str):
        if text:
            self.entry_num.delete(0, tk.END)
            self.entry_num.insert(0, text)
            self._set_status(f"✓ Spracherkennung: '{text}'")
            self._check_num_answer()
        else:
            self.num_feedback_lbl.config(
                text="⚠️ Mikrofonaufnahme nicht erkannt. Bitte erneut versuchen oder tippen.",
                foreground="#F59E0B"
            )
            self._set_status("Spracheingabe nicht erkannt.")

    def _next_num_item(self, user_triggered: bool = False):
        if not self.numbers:
            return
        self.current_num_item = random.choice(self.numbers)
        self.num_target_word = self.current_num_item["spoken"]
        self.entry_num.delete(0, tk.END)
        self.num_feedback_lbl.config(text="")
        self._set_status("Bereit für Zahlenübung.")

        if user_triggered and self.autostart_var.get():
            self._play_num_audio()

    def _play_num_audio(self):
        if hasattr(self, 'num_target_word') and self.num_target_word:
            bal_str = "Links" if self.balance_var.get() < -0.3 else ("Rechts" if self.balance_var.get() > 0.3 else "Beide")
            self._set_status(f"▶ Spiele Zahl: '{self.num_target_word}' (Tempo: {round(self.rate_var.get(), 1)}x, Ohr: {bal_str})")
            audio_path = self.tts.generate_audio(self.num_target_word, rate=self.rate_var.get())
            self.player.play(audio_path, balance=self.balance_var.get(), volume=self.volume_var.get(), rate=self.rate_var.get())

    def _check_num_answer(self):
        user_val = self.entry_num.get().strip()
        target_val = self.current_num_item["value"].strip()
        spoken_val = self.current_num_item["spoken"]

        is_correct = (user_val.lower() == target_val.lower() or user_val.lower() == spoken_val.lower())
        
        if is_correct:
            self.num_feedback_lbl.config(text=f"✓ Richtig! ({spoken_val})", foreground="#10B981")
        else:
            self.num_feedback_lbl.config(text=f"✗ Falsch. Gesprochen wurde '{spoken_val}' ({target_val}).", foreground="#EF4444")

        self.db.log_attempt(
            module="Zahlen",
            category=self.current_num_item["type"],
            target_word=target_val,
            user_answer=user_val,
            is_correct=is_correct,
            score=100.0 if is_correct else 0.0
        )

    # ---------------- Statistik ----------------
    def _build_stats_tab(self):
        btn_frame = ttk.Frame(self.tab_stats)
        btn_frame.pack(anchor="w", pady=5)

        btn_refresh = ttk.Button(btn_frame, text="🔄 Statistik aktualisieren", command=self._refresh_stats)
        btn_refresh.pack(side="left", padx=5)

        btn_reset = ttk.Button(btn_frame, text="🗑️ Statistik zurücksetzen", command=self._reset_stats)
        btn_reset.pack(side="left", padx=5)

        self.stats_text = tk.Text(
            self.tab_stats, font=("Consolas", 12, "bold"), bg="#1E293B", fg="#F8FAFC",
            relief="flat", highlightthickness=0, width=70, height=20, padx=15, pady=15
        )
        self.stats_text.pack(fill="both", expand=True, pady=10)
        self._refresh_stats()

    def _reset_stats(self):
        if messagebox.askyesno("Statistik zurücksetzen", "Möchtest du die gesamte Trainings-Statistik wirklich löschen?"):
            self.db.reset_stats()
            self._refresh_stats()
            self._set_status("Statistik zurückgesetzt.")

    def _refresh_stats(self):
        stats = self.db.get_stats()
        self.stats_text.delete("1.0", tk.END)

        report = [
            "==================================================",
            "        CI-HÖRTRAINING FORTSCHRITTSBERICHT",
            "==================================================",
            f"Gesamtanzahl Übungen:     {stats['total_attempts']}",
            f"Erfolgreiche Übungen:     {stats['correct_attempts']}",
            f"Gesamterfolgsquote:       {stats['accuracy']} %",
            f"Durchschnittlicher Score: {stats['avg_score']} %",
            "--------------------------------------------------",
            "Übungsmodule im Detail:",
        ]

        for mod, d in stats["by_module"].items():
            report.append(f"  • {mod:<16}: {d['accuracy']}% Treffer ({d['correct']}/{d['count']} absolviert)")

        report.append("==================================================")
        self.stats_text.insert(tk.END, "\n".join(report))

    def _create_statusbar(self):
        status_frame = ttk.Frame(self.root, padding="5 10 15 10", style="Panel.TFrame")
        status_frame.pack(fill="x", side="bottom")

        self.status_lbl = ttk.Label(status_frame, text="System bereit | Audio-Synthese: Online/Native macOS Engine", style="Panel.TLabel")
        self.status_lbl.pack(side="left")

    def _set_status(self, text: str):
        if hasattr(self, 'status_lbl'):
            self.status_lbl.config(text=text)
