import difflib
import re

class PhoneticMatcher:
    """
    Evaluator for comparing user's spoken or typed answer with target words.
    Uses Cologne Phonetics (Kölner Phonetik) for German phonetic sound matching
    and provides detailed audiological feedback for CI auditory training.
    """
    GERMAN_VOWELS = set("aeiouäöüyAEIOUÄÖÜY")

    @staticmethod
    def normalize(text: str) -> str:
        """Strips punctuation and normalizes string for comparison."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        return text

    @staticmethod
    def cologne_phonetics(word: str) -> str:
        """
        Calculates the Cologne Phonetics (Kölner Phonetik) code for a German word.
        Maps consonants to phonetic articulation categories (Postel 1969 algorithm).
        """
        if not word:
            return ""

        word = word.lower().strip()
        word = word.replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
        chars = [c for c in word if c.isalpha()]
        n = len(chars)
        if n == 0:
            return ""

        codes = []
        for i, c in enumerate(chars):
            prev_c = chars[i - 1] if i > 0 else ""
            next_c = chars[i + 1] if i + 1 < n else ""

            if c in "aeioujy":
                codes.append("0")
            elif c == "b":
                codes.append("1")
            elif c == "p":
                if next_c == "h":
                    codes.append("3")
                else:
                    codes.append("1")
            elif c in "dt":
                if next_c in "csz":
                    codes.append("8")
                else:
                    codes.append("2")
            elif c in "fvw":
                codes.append("3")
            elif c in "gkq":
                codes.append("4")
            elif c == "c":
                if i == 0:
                    if next_c in "ahkloqrux":
                        codes.append("4")
                    else:
                        codes.append("8")
                else:
                    if prev_c in "sz":
                        codes.append("8")
                    elif next_c in "ahkoqux":
                        codes.append("4")
                    else:
                        codes.append("8")
            elif c == "x":
                if prev_c in "ckq":
                    codes.append("8")
                else:
                    codes.append("4")
                    codes.append("8")
            elif c == "l":
                codes.append("5")
            elif c in "mn":
                codes.append("6")
            elif c == "r":
                codes.append("7")
            elif c in "sz":
                codes.append("8")
            elif c == "h":
                pass  # Ignored

        if not codes:
            return ""

        # 1. Collapse consecutive identical codes
        collapsed = [codes[0]]
        for code in codes[1:]:
            if code != collapsed[-1]:
                collapsed.append(code)

        # 2. Remove all '0's except if '0' is at the very beginning
        final_codes = []
        for idx, code in enumerate(collapsed):
            if code == "0":
                if idx == 0:
                    final_codes.append("0")
            else:
                final_codes.append(code)

        return "".join(final_codes)

    def cologne_similarity(self, word1: str, word2: str) -> float:
        """Returns Cologne Phonetic similarity ratio between 0.0 and 1.0."""
        code1 = self.cologne_phonetics(word1)
        code2 = self.cologne_phonetics(word2)
        if not code1 and not code2:
            return 1.0
        if not code1 or not code2:
            return 0.0
        if code1 == code2:
            return 1.0
        return difflib.SequenceMatcher(None, code1, code2).ratio()

    @staticmethod
    def classify_phonetic_error(target: str, user_input: str) -> dict:
        """
        Analyzes phonetic error patterns between target and user response
        specifically for Cochlear Implant (CI) hearing training.
        """
        norm_t = PhoneticMatcher.normalize(target)
        norm_u = PhoneticMatcher.normalize(user_input)

        if not norm_u or norm_t == norm_u:
            return {
                "category": "Exakttreffer",
                "tip": "Perfektes Hörverständnis! Exakter Treffer."
            }

        t_first = norm_t[0] if norm_t else ""
        u_first = norm_u[0] if norm_u else ""

        # Voiced vs Voiceless pairs (Stimmhaft vs Stimmlos)
        voiced_voiceless = {
            ("p", "b"), ("b", "p"),
            ("t", "d"), ("d", "t"),
            ("k", "g"), ("g", "k"),
            ("f", "v"), ("v", "f"),
            ("s", "z"), ("z", "s")
        }

        # Plosive vs Fricative pairs
        plosive_fricative = {
            ("p", "f"), ("f", "p"),
            ("t", "s"), ("s", "t"),
            ("k", "ch"), ("ch", "k")
        }

        nasals = {"m", "n"}

        if (t_first, u_first) in voiced_voiceless:
            return {
                "category": "Stimmhaft / Stimmlos Differenzierung",
                "tip": f"Anlaut '{t_first.upper()}' und '{u_first.upper()}' unterscheiden sich in der Stimmhaftigkeit. Achte auf den Luftstrom und die Kehlkopf-Vibration."
            }

        if (t_first, u_first) in plosive_fricative:
            return {
                "category": "Plosiv / Frikativ Unterscheidung",
                "tip": f"Anlaut '{t_first.upper()}' (Explosivlaut) vs '{u_first.upper()}' (Reibelaut). Achte auf das plötzliche 'Platzen' des Lautes."
            }

        if (t_first in nasals and u_first not in nasals) or (u_first in nasals and t_first not in nasals):
            return {
                "category": "Nasalität (M/N Lauterfassung)",
                "tip": f"Achte bei '{t_first.upper()}' auf den nasal strömenden Resonanzklang."
            }

        # Vowel difference
        vowels_t = [c for c in norm_t if c in "aeiouäöüy"]
        vowels_u = [c for c in norm_u if c in "aeiouäöüy"]
        if vowels_t != vowels_u:
            return {
                "category": "Vokaldifferenzierung",
                "tip": f"Vokale unterscheiden sich ('{''.join(vowels_t)}' vs '{''.join(vowels_u)}'). Vokale tragen die meiste Formant-Energie des Wortes."
            }

        return {
            "category": "Konsonantengruppe / Auslaut",
            "tip": "Konzentriere dich auf die Konsonanten-Details am Wortanfang und -ende."
        }

    def evaluate(self, target: str, user_input: str) -> dict:
        """
        Evaluates the user input against the target word using orthographic
        and Cologne Phonetics similarity algorithms.
        """
        norm_target = self.normalize(target)
        norm_user = self.normalize(user_input)

        if not norm_user:
            return {
                "score": 0.0,
                "status": "empty",
                "message": "Keine Eingabe / Sprache erkannt.",
                "is_correct": False,
                "cologne_target": self.cologne_phonetics(target),
                "cologne_user": "",
                "phonetic_category": "Keine Eingabe",
                "audiological_tip": "Bitte sprich oder tippe ein Wort ein."
            }

        cologne_target = self.cologne_phonetics(norm_target)
        cologne_user = self.cologne_phonetics(norm_user)
        cologne_sim = self.cologne_similarity(norm_target, norm_user)
        error_info = self.classify_phonetic_error(target, user_input)

        # Exact match
        if norm_target == norm_user:
            return {
                "score": 100.0,
                "status": "exact",
                "message": f"Perfekt! '{target}' wurde exakt richtig gehört.",
                "is_correct": True,
                "cologne_target": cologne_target,
                "cologne_user": cologne_user,
                "cologne_similarity": 100.0,
                "phonetic_category": error_info["category"],
                "audiological_tip": error_info["tip"]
            }

        # Calculate orthographic & Cologne Phonetics similarities
        ortho_ratio = difflib.SequenceMatcher(None, norm_target, norm_user).ratio()

        # Combined weighted score (60% orthographic, 40% Cologne Phonetics)
        combined_ratio = (ortho_ratio * 0.60) + (cologne_sim * 0.40)
        score = round(combined_ratio * 100, 1)
        is_correct = score >= 80.0 or cologne_sim == 1.0

        # Detailed phonetic breakdown
        feedback_parts = []

        # Check vowel matching
        target_vowels = [ch for ch in norm_target if ch in self.GERMAN_VOWELS]
        user_vowels = [ch for ch in norm_user if ch in self.GERMAN_VOWELS]

        if target_vowels == user_vowels and target_vowels:
            feedback_parts.append(f"Vokal ('{''.join(target_vowels)}') richtig gehört!")
        elif user_vowels:
            feedback_parts.append(f"Vokale unterscheiden sich: gehört '{''.join(user_vowels)}' statt '{''.join(target_vowels)}'.")

        # Check initial consonant (Anlaut)
        if norm_target and norm_user:
            if norm_target[0] == norm_user[0]:
                feedback_parts.append(f"Anlaut '{norm_target[0].upper()}' korrekt.")
            else:
                feedback_parts.append(f"Anlaut: '{norm_user[0].upper()}' statt '{norm_target[0].upper()}' gehört.")

        # Cologne Phonetics feedback
        if cologne_target == cologne_user:
            feedback_parts.append(f"Phonetischer Klang-Code: [{cologne_target}] (akustisch gleichwertig).")
        else:
            feedback_parts.append(f"Klang-Code: [{cologne_user}] vs [{cologne_target}].")

        msg = " ".join(feedback_parts) if feedback_parts else f"Ähnlichkeit: {score}%."

        return {
            "score": score,
            "status": "partial" if score > 50 else "incorrect",
            "message": f"Ziel: '{target}' | Gehört: '{user_input}'. {msg}",
            "is_correct": is_correct,
            "cologne_target": cologne_target,
            "cologne_user": cologne_user,
            "cologne_similarity": round(cologne_sim * 100, 1),
            "phonetic_category": error_info["category"],
            "audiological_tip": error_info["tip"]
        }

    @staticmethod
    def german_words_to_digits(text: str) -> str:
        """Converts German number words to digits for robust comparison."""
        if not text:
            return ""
        text = text.lower().strip()

        units = {
            "null": 0, "eins": 1, "ein": 1, "eine": 1, "einer": 1, "zwei": 2, "drei": 3,
            "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
            "zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13, "vierzehn": 14,
            "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19
        }
        tens = {
            "zwanzig": 20, "dreißig": 30, "vierzig": 40, "fünfzig": 50,
            "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90
        }
        hundreds = {
            "hundert": 100, "einhundert": 100, "zweihundert": 200, "dreihundert": 300,
            "vierhundert": 400, "fünfhundert": 500, "sechshundert": 600,
            "siebenhundert": 700, "achthundert": 800, "neunhundert": 900
        }

        words = text.split()
        converted_words = []
        for w in words:
            clean_w = re.sub(r'[^\w]', '', w)
            if not clean_w:
                converted_words.append(w)
                continue

            if clean_w in units:
                w = w.replace(clean_w, str(units[clean_w]))
            elif clean_w in tens:
                w = w.replace(clean_w, str(tens[clean_w]))
            elif clean_w in hundreds:
                w = w.replace(clean_w, str(hundreds[clean_w]))
            else:
                match = re.match(r'^(ein|zwei|drei|vier|fünf|sechs|sieben|acht|neun)und(zwanzig|dreißig|vierzig|fünfzig|sechzig|siebzig|achtzig|neunzig)$', clean_w)
                if match:
                    u_word, t_word = match.groups()
                    u_val = units.get(u_word, 0)
                    t_val = tens.get(t_word, 0)
                    val = t_val + u_val
                    w = w.replace(clean_w, str(val))
            converted_words.append(w)

        return " ".join(converted_words)

    def evaluate_number(self, target_value: str, spoken_text: str, user_input: str) -> dict:
        """
        Specialized evaluator for numbers, times, and currency amounts.
        Handles variations like '14:30', '14:30 Uhr', '14 Uhr 30', '12,50 €', '12 Euro 50', '12.50', '3 Euro 85'.
        """
        if not user_input or not user_input.strip():
            return {
                "score": 0.0,
                "status": "empty",
                "message": "Keine Eingabe / Sprache erkannt.",
                "is_correct": False
            }

        norm_user = self.german_words_to_digits(user_input.lower().strip())
        norm_target_val = self.german_words_to_digits(target_value.lower().strip())
        norm_spoken = self.german_words_to_digits(spoken_text.lower().strip())

        # Build comprehensive acceptable variants set for target
        target_variants = {
            norm_target_val,
            norm_spoken,
            self.normalize(norm_target_val),
            self.normalize(norm_spoken)
        }

        # Extract numbers from target & spoken text
        target_nums = re.findall(r'\d+', norm_target_val)
        spoken_nums = re.findall(r'\d+', norm_spoken)
        user_nums = re.findall(r'\d+', norm_user)

        # Handle time formats (e.g., 14:30, 14:30 Uhr, 14 Uhr 30)
        time_match = re.search(r'(\d{1,2})[:.\s](\d{2})', norm_target_val)
        if time_match:
            h, m = time_match.groups()
            target_variants.update([
                f"{h}:{m}", f"{h}:{m} uhr", f"{h} uhr {m}", f"{int(h)} uhr {int(m)}",
                f"{h} uhr {m} min", f"{h}.{m}", f"{h}.{m} uhr", f"{int(h)} {int(m)}",
                f"{h} {m}"
            ])

        # Handle currency formats (e.g. 12,50 €, 12 Euro 50, 12,50, 3 Euro 85)
        curr_match = re.search(r'(\d+)[\s,.]+(\d{1,2})', norm_target_val) or re.search(r'(\d+)[\s,.]+(\d{1,2})', norm_spoken)
        if curr_match:
            main_units, frac_units = curr_match.groups()
            if len(frac_units) == 1:
                frac_units = frac_units + "0"

            target_variants.update([
                f"{main_units},{frac_units}",
                f"{main_units}.{frac_units}",
                f"{main_units},{frac_units} €",
                f"{main_units},{frac_units} euro",
                f"{main_units}.{frac_units} €",
                f"{main_units}.{frac_units} euro",
                f"{main_units} euro {frac_units}",
                f"{main_units} euro {frac_units} cent",
                f"{main_units} € {frac_units}",
                f"{main_units} {frac_units}",
                f"{main_units}, {frac_units}"
            ])

        # Check direct variant matches
        user_clean = norm_user.replace("uhr", "").replace("€", "").replace("euro", "").replace("cent", "").strip()
        user_normalized = self.normalize(norm_user)

        if (norm_user in target_variants or
            user_clean in target_variants or
            user_normalized in target_variants or
            (user_nums and target_nums and user_nums == target_nums)):
            return {
                "score": 100.0,
                "status": "exact",
                "message": f"✓ Perfekt! '{user_input}' ist richtig.",
                "is_correct": True
            }

        # Sequence matcher similarity ratio fallback
        ratio = max(
            difflib.SequenceMatcher(None, norm_target_val, norm_user).ratio(),
            difflib.SequenceMatcher(None, norm_spoken, norm_user).ratio()
        )
        score = round(ratio * 100, 1)
        is_correct = score >= 75.0

        return {
            "score": score,
            "status": "exact" if is_correct else "incorrect",
            "message": f"✓ Richtig! ({spoken_text})" if is_correct else f"✗ Falsch. Gesprochen wurde '{spoken_text}' ({target_value}). Gehört: '{user_input}'.",
            "is_correct": is_correct
        }
