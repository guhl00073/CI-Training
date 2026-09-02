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
    def count_syllables(word: str) -> int:
        """
        Calculates syllable count for a German word based on vowel nucleus heuristics
        (treating German diphthongs/digraphs au, eu, äu, ei, ey, ai, ay, ie, ui as single vowel kernels).
        """
        if not word:
            return 0
        w = word.lower().strip()
        # Collapse German diphthongs and vowel digraphs
        w = re.sub(r'(ei|ey|ai|ay|au|eu|äu|ie|ui)', 'a', w)
        vowels = re.findall(r'[aeiouäöüy]', w)
        count = len(vowels)
        return max(1, count) if any(c.isalpha() for c in word) else 0

    @classmethod
    def hyphenate_german(cls, word: str) -> str:
        """
        Provides visual syllable segmentation (e.g. 'Haus·tür', 'Son·nen·blu·me')
        for German words and compounds.
        """
        if not word or len(word.strip()) <= 3:
            return word.strip()
        norm = word.strip()
        if "·" in norm or "-" in norm:
            return norm

        # Dictionary of common compound and multi-syllable word segmentations
        SYL_DICT = {
            "haustür": "Haus·tür", "regenschirm": "Re·gen·schirm", "fußball": "Fuß·ball",
            "kühlschrank": "Kühl·schrank", "zahnbürste": "Zahn·bürs·te", "briefkasten": "Brief·kas·ten",
            "schneemann": "Schnee·mann", "apfelbaum": "Ap·fel·baum", "armband": "Arm·band",
            "blumenstrauß": "Blu·men·strauß", "waldweg": "Wald·weg", "handschuh": "Hand·schuh",
            "teekanne": "Tee·kan·ne", "kaffeetasse": "Kaf·fee·tas·se", "zeitplan": "Zeit·plan",
            "sonnenschein": "Son·nen·schein", "flugplatz": "Flug·platz", "haustier": "Haus·tier",
            "eisbär": "Eis·bär", "bettdecke": "Bett·de·cke", "kochtopf": "Koch·topf",
            "schreibtisch": "Schreib·tisch", "brotzeit": "Brot·zeit", "gartenzaun": "Gar·ten·zaun",
            "flugzeug": "Flug·zeug", "taschenlampe": "Ta·schen·lam·pe", "sonnenbrille": "Son·nen·bril·le",
            "fahrradhelm": "Fahr·rad·helm", "schmetterling": "Schmet·ter·ling", "wörterbuch": "Wör·ter·buch",
            "kaffeekanne": "Kaf·fee·kan·ne", "wasserkocher": "Was·ser·ko·cher", "eichhörnchen": "Eich·hörn·chen",
            "marienkäfer": "Ma·ri·en·kä·fer", "sonnenblume": "Son·nen·blu·me", "schreibtischstuhl": "Schreib·tisch·stuhl",
            "badezimmer": "Ba·de·zim·mer", "kleiderschrank": "Klei·der·schrank", "reisekoffer": "Rei·se·kof·fer",
            "regenbogen": "Re·gen·bo·gen", "schultasche": "Schul·ta·sche", "fernbedienung": "Fern·be·die·nung",
            "handtuchhalter": "Hand·tuch·hal·ter", "postkartenmotiv": "Post·kar·ten·mo·tiv",
            "regenwurm": "Re·gen·wurm", "wohnzimmer": "Wohn·zim·mer", "haustürschlüssel": "Haus·tür·schlüs·sel",
            "pfeffermühle": "Pfef·fer·müh·le", "küchenmesser": "Kü·chen·mes·ser", "blumentopf": "Blu·men·topf",
            "kindergarten": "Kin·der·gar·ten", "feuerwehrwagen": "Feu·er·wehr·wa·gen",
            "schreibtischlampe": "Schreib·tisch·lam·pe", "polizeiauto": "Po·li·zei·au·to",
            "hubschrauberflug": "Hub·schrau·ber·flug", "einkaufswagen": "Ein·kaufs·wa·gen",
            "straßenbahnstation": "Stra·ßen·bahn·sta·ti·on", "eisenbahnbrücke": "Ei·sen·bahn·brü·cke",
            "krankenwagen": "Kran·ken·wa·gen", "schokoladentafel": "Scho·ko·la·den·ta·fel",
            "adventskalender": "Ad·vents·ka·len·der", "regenschirmständer": "Re·gen·schirm·stän·der",
            "sommerurlaubsziel": "Som·mer·ur·laubs·ziel", "frühstückstischgedeck": "Früh·stücks·tisch·ge·deck",
            "autobahnauffahrt": "Au·to·bahn·auf·fahrt", "universitätsstadt": "U·ni·ver·si·täts·stadt",
            "sonnenuntergang": "Son·nen·un·ter·gang", "fahrkartenautomat": "Fahr·kar·ten·au·to·mat",
            "geburtstagsüberraschung": "Ge·burts·tags·über·ra·schung", "wohnungsbeleuchtung": "Woh·nungs·be·leuch·tung"
        }
        if norm.lower() in SYL_DICT:
            return SYL_DICT[norm.lower()]

        # Heuristic syllabification based on German phonotactics
        # Separate single consonant between vowels: V-CV (e.g. Ta-ge)
        # Separate multiple consonants: VC-CV (e.g. Gar-ten, Was-ser, Schmet-ter-ling)
        # Keep 'ch', 'sch', 'ck', 'ph' together where appropriate
        result = []
        i = 0
        n = len(norm)
        vowel_indices = []
        for idx, char in enumerate(norm.lower()):
            if char in "aeiouäöüy":
                vowel_indices.append(idx)

        if len(vowel_indices) <= 1:
            return norm

        # Simple vowel-guided syllable splitter
        split_points = set()
        for v_idx in range(len(vowel_indices) - 1):
            v1 = vowel_indices[v_idx]
            v2 = vowel_indices[v_idx + 1]
            # Check if this is a diphthong like au, ei, ie, eu, äu
            if v2 == v1 + 1 and norm[v1:v2+1].lower() in ("au", "ei", "ey", "ai", "ay", "eu", "äu", "ie", "ui"):
                continue
            consonants_between = norm[v1+1:v2]
            if len(consonants_between) == 1:
                # V-CV -> split before single consonant
                split_points.add(v1 + 1)
            elif len(consonants_between) >= 2:
                # VC-CV -> split after first consonant in cluster, keeping 'ch', 'sch'
                if consonants_between.lower().startswith("sch") and len(consonants_between) > 3:
                    split_points.add(v1 + 1)
                elif consonants_between.lower().startswith("ch") and len(consonants_between) > 2:
                    split_points.add(v1 + 1)
                else:
                    split_points.add(v1 + 2)

        chars = []
        for idx, char in enumerate(norm):
            if idx in split_points and idx > 0 and idx < n:
                chars.append("·")
            chars.append(char)
        return "".join(chars)


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
        w1 = (word1 or "").strip()
        w2 = (word2 or "").strip()
        if w1 == w2:
            return 1.0
        code1 = self.cologne_phonetics(w1)
        code2 = self.cologne_phonetics(w2)
        if not code1 or not code2:
            return 1.0 if (w1 and w1 == w2) else 0.0
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
            ("k", "ch"), ("ch", "k"),
            ("b", "w"), ("w", "b"),
            ("d", "s"), ("s", "d")
        }

        # Nasal confusions
        nasal_pairs = {
            ("m", "n"), ("n", "m")
        }

        pair = (t_first, u_first)
        if pair in voiced_voiceless:
            return {
                "category": "Stimmhaft vs. Stimmlos",
                "tip": "Achte auf die Schwingung der Stimmlippen (z. B. B/D/G = stimmhaft, P/T/K = stimmlos)."
            }
        elif pair in plosive_fricative:
            return {
                "category": "Plosiv vs. Frikativ",
                "tip": "Achte auf den Luftstrom: Plosive haben einen kurzen Verschlussknall, Frikative ein kontinuierliches Reibegeräusch."
            }
        elif pair in nasal_pairs:
            return {
                "category": "Nasal-Verwechslung",
                "tip": "M und N klingen sehr ähnlich. Konzentriere dich auf das Mundbild und den Resonanzraum."
            }

        # Vowel errors
        t_vowels = [c for c in norm_t if c in PhoneticMatcher.GERMAN_VOWELS]
        u_vowels = [c for c in norm_u if c in PhoneticMatcher.GERMAN_VOWELS]
        if t_vowels and u_vowels and t_vowels[0] != u_vowels[0]:
            return {
                "category": "Vokal-Kontrast",
                "tip": f"Vokalabweichung: Gesprochen wurde '{t_vowels[0].upper()}', gehört wurde '{u_vowels[0].upper()}'. Achte auf die Zungenhöhe und Lippenrundung."
            }

    @staticmethod
    def double_metaphone(word: str) -> tuple:
        """
        Pure Python implementation of Double Metaphone phonetic encoding for English words.
        Returns (primary_code, secondary_code).
        """
        w = re.sub(r'[^a-z]', '', (word or "").lower())
        if not w:
            return ("", "")

        primary = []
        i = 0
        n = len(w)
        while i < n:
            c = w[i]
            if c in "aeiouy":
                if i == 0:
                    primary.append("A")
            elif c == "b":
                primary.append("P")
                if i + 1 < n and w[i+1] == "b": i += 1
            elif c == "c":
                if i + 1 < n and w[i+1] == "h":
                    primary.append("X")
                    i += 1
                elif i + 1 < n and w[i+1] in "ei":
                    primary.append("S")
                    i += 1
                elif i + 1 < n and w[i+1] == "k":
                    primary.append("K")
                    i += 1
                else:
                    primary.append("K")
            elif c == "d":
                if i + 2 < n and w[i+1:i+3] == "ge":
                    primary.append("J")
                    i += 2
                else:
                    primary.append("T")
            elif c in "fgv":
                primary.append("F")
            elif c == "g":
                if i + 1 < n and w[i+1] in "ei":
                    primary.append("J")
                else:
                    primary.append("K")
            elif c == "h":
                if i == 0 or (i > 0 and w[i-1] in "aeiouy"):
                    primary.append("H")
            elif c in "klq":
                primary.append("K")
            elif c == "l":
                primary.append("L")
            elif c == "m":
                primary.append("M")
            elif c == "n":
                primary.append("N")
            elif c == "p":
                if i + 1 < n and w[i+1] == "h":
                    primary.append("F")
                    i += 1
                else:
                    primary.append("P")
            elif c == "r":
                primary.append("R")
            elif c == "s":
                if i + 1 < n and w[i+1] == "h":
                    primary.append("X")
                    i += 1
                else:
                    primary.append("S")
            elif c == "t":
                if i + 1 < n and w[i+1] == "h":
                    primary.append("0")
                    i += 1
                else:
                    primary.append("T")
            elif c == "w":
                if i == 0 or w[i-1] in "aeiou":
                    primary.append("W")
            elif c == "x":
                primary.append("KS")
            elif c == "z":
                primary.append("S")
            i += 1

        res = "".join(primary)
        return (res, res)

    @staticmethod
    def classify_english_phonetic_error(target: str, user_input: str) -> dict:
        """
        Analyzes phonetic error patterns for English auditory training (specifically for German CI wearers).
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

        # 1. Liquid Contrast (/r/ vs /l/)
        if (t_first == "r" and u_first == "l") or (t_first == "l" and u_first == "r"):
            return {
                "category": "Flüssiglaute (R vs. L)",
                "tip": "Achte auf den Zungenkontakt: L berührt den oberen Zahndamm; R wölbt die Zunge zurück."
            }

        # 2. Dental Fricative (/th/ /θ/ vs /f/, /t/, /s/)
        if norm_t.startswith("th") and not norm_u.startswith("th"):
            return {
                "category": "Dentale Frikative (TH)",
                "tip": "TH ist ein englischer Reibelaut: Lege die Zungenspitze leicht an die Schneidezähne."
            }

        # 3. Labiodental vs Semivowel (/v/ vs /w/)
        if (t_first == "v" and u_first == "w") or (t_first == "w" and u_first == "v"):
            return {
                "category": "Labiodental vs. Halbvokal (V vs. W)",
                "tip": "V nutzt Schneidezähne auf der Unterlippe; W wird mit gerundeten Lippen ohne Zahnkontakt gebildet."
            }

        # 4. Voiced vs Voiceless Consonants
        voiced_voiceless = {
            ("p", "b"), ("b", "p"),
            ("t", "d"), ("d", "t"),
            ("k", "g"), ("g", "k"),
            ("f", "v"), ("v", "f"),
            ("s", "z"), ("z", "s")
        }
        if (t_first, u_first) in voiced_voiceless:
            return {
                "category": "Stimmhaft vs. Stimmlos",
                "tip": "Achte auf die Stimmlippenschwingung (B/D/G = stimmhaft, P/T/K = stimmlos)."
            }

        # 5. English Vowel contrasts
        en_vowels = set("aeiouy")
        t_vowels = [c for c in norm_t if c in en_vowels]
        u_vowels = [c for c in norm_u if c in en_vowels]
        if t_vowels and u_vowels and t_vowels[0] != u_vowels[0]:
            return {
                "category": "Vokal-Kontrast",
                "tip": f"Vokalabweichung im Englischen: Gesprochen '{t_vowels[0].upper()}', gehört '{u_vowels[0].upper()}'."
            }

        return {
            "category": "Phonetische Abweichung",
            "tip": "Konzentriere dich auf die englischen Konsonanten am Wortanfang."
        }

    def evaluate(self, target: str, user_input: str, language: str = "de") -> dict:
        """
        Evaluates the user input against the target word using orthographic
        and Cologne Phonetics (for DE) or Double Metaphone (for EN) similarity algorithms.
        """
        is_en = (language or "de").lower().startswith("en")
        norm_target = self.normalize(target)
        norm_user = self.normalize(user_input)

        if not norm_user:
            return {
                "score": 0.0,
                "status": "empty",
                "message": "Keine Eingabe / Sprache erkannt.",
                "is_correct": False,
                "cologne_target": self.double_metaphone(target)[0] if is_en else self.cologne_phonetics(target),
                "cologne_user": "",
                "phonetic_category": "Keine Eingabe",
                "audiological_tip": "Bitte sprich oder tippe ein Wort ein."
            }

        # Check if number representations match
        target_num = self.german_words_to_digits(norm_target)
        user_num = self.german_words_to_digits(norm_user)
        if (target_num and user_num and target_num == user_num) or (norm_target == norm_user):
            return {
                "score": 100.0,
                "status": "exact",
                "message": f"Perfekt! '{target}' wurde richtig verstanden.",
                "is_correct": True,
                "cologne_target": self.double_metaphone(norm_target)[0] if is_en else self.cologne_phonetics(norm_target),
                "cologne_user": self.double_metaphone(norm_user)[0] if is_en else self.cologne_phonetics(norm_user),
                "cologne_similarity": 100.0,
                "phonetic_category": "Exakttreffer",
                "audiological_tip": "Perfektes Hörverständnis! Exakter Treffer."
            }

        if is_en:
            dm_t = self.double_metaphone(norm_target)[0]
            dm_u = self.double_metaphone(norm_user)[0]
            phonetic_sim = difflib.SequenceMatcher(None, dm_t, dm_u).ratio() if (dm_t and dm_u) else 0.0
            error_info = self.classify_english_phonetic_error(target, user_input)
            cologne_target = dm_t
            cologne_user = dm_u
        else:
            cologne_target = self.cologne_phonetics(norm_target)
            cologne_user = self.cologne_phonetics(norm_user)
            phonetic_sim = self.cologne_similarity(norm_target, norm_user)
            error_info = self.classify_phonetic_error(target, user_input)

        # Calculate orthographic & Cologne Phonetics similarities
        ortho_ratio = difflib.SequenceMatcher(None, norm_target, norm_user).ratio()

        # Combined weighted score (60% orthographic, 40% Phonetic similarity)
        combined_ratio = (ortho_ratio * 0.60) + (phonetic_sim * 0.40)
        score = round(combined_ratio * 100, 1)
        is_correct = score >= 80.0 or phonetic_sim == 1.0

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

        # Syllable count & hyphenation analysis
        target_syl_count = self.count_syllables(target)
        user_syl_count = self.count_syllables(user_input)
        hyphenated_target = self.hyphenate_german(target)
        hyphenated_user = self.hyphenate_german(user_input)

        if target_syl_count > 1:
            if target_syl_count == user_syl_count:
                feedback_parts.append(f"Silbenanzahl ({target_syl_count} Silben: {hyphenated_target}) korrekt erkannt.")
            else:
                feedback_parts.append(f"Silbenanzahl: {user_syl_count} Silbe(n) gehört statt {target_syl_count} ({hyphenated_target}).")

        # Phonetic feedback
        if cologne_target == cologne_user:
            feedback_parts.append(f"Phonetischer Klang-Code: [{cologne_target}] (akustisch gleichwertig).")
        else:
            feedback_parts.append(f"Klang-Code: [{cologne_user}] vs [{cologne_target}].")

        msg = " ".join(feedback_parts) if feedback_parts else f"Ähnlichkeit: {score}%."

        target_info = self.get_ipa_and_articulation(target)
        user_info = self.get_ipa_and_articulation(user_input)

        return {
            "score": score,
            "status": "partial" if score > 50 else "incorrect",
            "message": f"Ziel: '{target}' {target_info['ipa']} | Gehört: '{user_input}' {user_info['ipa']}. {msg}",
            "is_correct": is_correct,
            "cologne_target": cologne_target,
            "cologne_user": cologne_user,
            "cologne_similarity": round(phonetic_sim * 100, 1),
            "phonetic_category": error_info["category"] if error_info else "Allgemeine Abweichung",
            "audiological_tip": error_info["tip"] if error_info else "Achte auf die Lautkontraste und wiederhole das Audio aufmerksam.",
            "ipa_target": target_info["ipa"],
            "ipa_user": user_info["ipa"],
            "articulation_place": target_info["place"],
            "articulation_hint": target_info["hint"],
            "syllable_count_target": target_syl_count,
            "syllable_count_user": user_syl_count,
            "hyphenated_target": hyphenated_target,
            "hyphenated_user": hyphenated_user
        }

    @staticmethod
    def get_ipa_and_articulation(word: str) -> dict:
        """
        Provides International Phonetic Alphabet (IPA) transcription and Place of Articulation
        (Artikulationsort) details for German target words for CI speech therapy.
        """
        if not word:
            return {"ipa": "[-]", "place": "Unbekannt", "hint": ""}

        norm = word.lower().strip()

        # Dictionary of standard German target words in CI training
        IPA_DICT = {
            "pass": ("pass", "[pas]", "Bilabial", "Lippenverschluss (stimmlos P)"),
            "bass": ("bass", "[bas]", "Bilabial", "Lippenverschluss (stimmhaft B)"),
            "tasse": ("tasse", "['tasə]", "Alveolar", "Zungenspitze am Zahndamm (stimmlos T)"),
            "dasse": ("dasse", "['dasə]", "Alveolar", "Zungenspitze am Zahndamm (stimmhaft D)"),
            "haus": ("haus", "[haʊ̯s]", "Glottal", "Stimmritze (H-Anlaut) / Alveolar (S-Auslaut)"),
            "maus": ("maus", "[maʊ̯s]", "Bilabial", "Lippen-Nasal (M-Anlaut)"),
            "kamm": ("kamm", "[kam]", "Velar", "Gaumensegel-Verschluss (K-Anlaut)"),
            "komm": ("komm", "[kɔm]", "Velar", "Gaumensegel-Verschluss (K-Anlaut)"),
            "bus": ("bus", "[bʊs]", "Bilabial", "Lippenverschluss (B) / Alveolar (S-Auslaut)"),
            "dach": ("dach", "[dax]", "Alveolar", "Zungenspitze (D) / Ach-Laut (x) am Gaumen"),
            "fisch": ("fisch", "[fɪʃ]", "Labiodental", "Oberzähne auf Unterlippe (F) / Sch-Laut [ʃ]"),
            "brot": ("brot", "[bʁoːt]", "Bilabial", "Lippenverschluss (B) / Langvokal [oː]"),
            "strand": ("strand", "[ʃtʁant]", "Postalveolar", "Sch-Laut [ʃ] / Alveolar T-Auslaut"),
            "herbst": ("herbst", "[hɛʁpst]", "Glottal", "Glottaler Anlaut [h] / Auslautgruppe [pst]"),
            "katze": ("katze", "['katsə]", "Velar", "Gaumen [k] / Affrikate [ts]"),
            "mond": ("mond", "[moːnt]", "Bilabial", "Lippen-Nasal [m] / Auslaut-Verhärtung [t]"),
            "zug": ("zug", "[tsuːk]", "Alveolar", "Affrikate [ts] / Auslaut-Verhärtung [k]"),
            "buch": ("buch", "[buːx]", "Bilabial", "Lippenverschluss [b] / Ach-Laut [x]"),
            "schiff": ("schiff", "[ʃɪf]", "Postalveolar", "Sch-Laut [ʃ] / Labiodental [f]"),
            "sonne": ("sonne", "['zɔnə]", "Alveolar", "Zungenspitze (stimmhaftes Zisch-S [z])"),
            "tisch": ("tisch", "[tɪʃ]", "Alveolar", "Zungenspitze [t] / Postalveolar [ʃ]"),
            "bett": ("bett", "[bɛt]", "Bilabial", "Lippenverschluss [b] / Kurzvokal [ɛ]"),
            "hund": ("hund", "[hʊnt]", "Glottal", "H-Anlaut [h] / Auslaut-Verhärtung [t]")
        }

        if norm in IPA_DICT:
            _, ipa, place, hint = IPA_DICT[norm]
            return {"ipa": ipa, "place": place, "hint": hint}

        # Dynamic Rule-Based IPA & Articulation Generation:
        first_letter = norm[0] if norm else ""
        ipa_map = {
            "p": ("/p/", "Bilabial (Plosiv, stimmlos)", "Lippen kurz fest schließen und Luft stoßartig öffnen"),
            "b": ("/b/", "Bilabial (Plosiv, stimmhaft)", "Lippen schließen mit spürbarer Stimmlippenschwingung"),
            "t": ("/t/", "Alveolar (Plosiv, stimmlos)", "Zungenspitze am oberen Zahndamm anlegen"),
            "d": ("/d/", "Alveolar (Plosiv, stimmhaft)", "Zungenspitze am oberen Zahndamm mit Stimmton"),
            "k": ("/k/", "Velar (Plosiv, stimmlos)", "Zungenrücken am weichen Gaumen"),
            "g": ("/g/", "Velar (Plosiv, stimmhaft)", "Zungenrücken am weichen Gaumen mit Stimmton"),
            "f": ("/f/", "Labiodental (Frikativ, stimmlos)", "Oberzähne auf Unterlippe, Reibelaut"),
            "w": ("/v/", "Labiodental (Frikativ, stimmhaft)", "Oberzähne auf Unterlippe mit Stimmton"),
            "v": ("/f/ oder /v/", "Labiodental (Frikativ)", "Reibelaut an den Schneidezähnen"),
            "s": ("/s/ oder /z/", "Alveolar (Frikativ)", "Zischlaut an der Zungenspitze"),
            "z": ("/t͡s/", "Affrikate", "Kombination aus T-Verschluss und S-Zischen"),
            "sch": ("/ʃ/", "Postalveolar (Frikativ, stimmlos)", "Lippen runden, breiter Zischlaut"),
            "ch": ("/ç/ oder /x/", "Palatal / Velar (Frikativ)", "Reibelaut am Gaumen ('Ich-' oder 'Ach-Laut')"),
            "m": ("/m/", "Nasal (Bilabial)", "Lippen geschlossen, Luft strömt durch die Nase"),
            "n": ("/n/", "Nasal (Alveolar)", "Zungenspitze am Zahndamm, Nasenresonanz"),
            "l": ("/l/", "Lateral (Alveolar)", "Zungenspitze am Zahndamm, Luft strömt seitlich"),
            "r": ("/ʁ/ oder /r/", "Uvular (Vibrant/Frikativ)", "Zäpfchen-R oder gerolltes Zungen-R"),
            "h": ("/h/", "Glottal (Frikativ)", "Hauchlaut im Kehlkopf")
        }

        if norm.startswith("sch"):
            ipa, place, hint = ipa_map["sch"]
        elif norm.startswith("ch"):
            ipa, place, hint = ipa_map["ch"]
        elif first_letter in ipa_map:
            ipa, place, hint = ipa_map[first_letter]
        elif first_letter in "aeiouäöü":
            place = "Vokal-Kontrast"
            hint = "Offener Ansatzraum ohne Konsonanten-Hindernis"
            ipa = f"[{norm}]"
        else:
            place = "Artikulationsort"
            hint = "Standard-Artikulation"
            ipa = f"[{norm}]"

        return {"ipa": ipa, "place": place, "hint": hint}

    @classmethod
    def parse_german_number_word(cls, clean_w: str):
        """Parses a German number word (including complex compounds) into its integer value."""
        if not clean_w:
            return None
        clean_w = clean_w.lower().strip()

        units = {
            "null": 0, "eins": 1, "ein": 1, "eine": 1, "einen": 1, "einem": 1, "eines": 1, "einer": 1,
            "zwei": 2, "zwo": 2, "drei": 3, "vier": 4, "fünf": 5, "funf": 5, "sechs": 6,
            "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12, "zwolf": 12,
            "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "funfzehn": 15, "sechzehn": 16,
            "siebzehn": 17, "achtzehn": 18, "neunzehn": 19
        }
        tens = {
            "zwanzig": 20, "dreißig": 30, "dreissig": 30, "vierzig": 40, "fünfzig": 50,
            "funfzig": 50, "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90
        }

        if clean_w in units:
            return units[clean_w]
        if clean_w in tens:
            return tens[clean_w]

        # Single tens compound: einundzwanzig, fünfunddreißig, etc.
        match_tens = re.match(r'^(ein|zwei|zwo|drei|vier|fünf|funf|sechs|sieben|acht|neun)und(zwanzig|dreißig|dreissig|vierzig|fünfzig|funfzig|sechzig|siebzig|achtzig|neunzig)$', clean_w)
        if match_tens:
            u_word, t_word = match_tens.groups()
            return tens.get(t_word, 0) + units.get(u_word, 0)

        # A compound number word must contain 'tausend' or 'hundert'
        if "tausend" not in clean_w and "hundert" not in clean_w:
            return None

        total = 0
        rem = clean_w

        if "tausend" in rem:
            th_part, rem = rem.split("tausend", 1)
            if not th_part or th_part in ("ein", "eins", "eine"):
                total += 1000
            else:
                th_val = cls.parse_german_number_word(th_part)
                if th_val is not None:
                    total += th_val * 1000
                else:
                    return None
            if not rem:
                return total

        if "hundert" in rem:
            hd_part, rem = rem.split("hundert", 1)
            if not hd_part or hd_part in ("ein", "eins", "eine"):
                total += 100
            else:
                hd_val = cls.parse_german_number_word(hd_part)
                if hd_val is not None:
                    total += hd_val * 100
                else:
                    return None
            if not rem:
                return total

        if rem:
            if rem.startswith("und") and len(rem) > 3:
                rem = rem[3:]
            if rem in units:
                total += units[rem]
            elif rem in tens:
                total += tens[rem]
            else:
                match_rem = re.match(r'^(ein|zwei|zwo|drei|vier|fünf|funf|sechs|sieben|acht|neun)und(zwanzig|dreißig|dreissig|vierzig|fünfzig|funfzig|sechzig|siebzig|achtzig|neunzig)$', rem)
                if match_rem:
                    u_word, t_word = match_rem.groups()
                    total += tens.get(t_word, 0) + units.get(u_word, 0)
                else:
                    return None

        return total

    @classmethod
    def german_words_to_digits(cls, text: str) -> str:
        """Converts German number words to digits for robust comparison."""
        if not text:
            return ""
        text = text.lower().strip()

        words = text.split()
        converted_words = []
        for w in words:
            clean_w = re.sub(r'[^\w]', '', w)
            if not clean_w:
                converted_words.append(w)
                continue

            parsed_num = cls.parse_german_number_word(clean_w)
            if parsed_num is not None:
                num_str = str(parsed_num)
                w = re.sub(rf'\b{re.escape(clean_w)}\b', num_str, w, flags=re.IGNORECASE)
                if clean_w in re.findall(r'\b\w+\b', w):
                    w = w.replace(clean_w, num_str)

            converted_words.append(w)

        return " ".join(converted_words)

    def evaluate_number(self, target_value: str, spoken_text: str, user_input: str) -> dict:
        """
        Specialized evaluator for numbers, times, and currency amounts.
        Handles variations like '10' vs 'zehn', '14:30', '14:30 Uhr', '14 Uhr 30', '12,50 €', '12 Euro 50', '12.50', '3 Euro 85'.
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
                f"{h} uhr {m} min", f"{h} uhr {m} minuten", f"{h}.{m}", f"{h}.{m} uhr", f"{int(h)} {int(m)}",
                f"{h} {m}"
            ])

        # Handle currency formats (e.g. 12,50 €, 12 Euro 50, 12,50, 3 Euro 85, 12 €, 12 Euro)
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
        elif target_nums:
            # Whole currency amounts (e.g. 15 €, 15 Euro)
            for n in target_nums:
                target_variants.update([
                    f"{n} €", f"{n} euro", f"{n},00 €", f"{n}.00 €", f"{n},00", f"{n}.00", f"{n} euro 00"
                ])

        # Check direct variant matches
        user_clean = norm_user.replace("uhr", "").replace("€", "").replace("euro", "").replace("cent", "").strip()
        user_normalized = self.normalize(norm_user)

        if (norm_user in target_variants or
            user_clean in target_variants or
            user_normalized in target_variants or
            (norm_user and norm_target_val and norm_user == norm_target_val) or
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

    def evaluate_full_sentence(self, target_sentence: str, user_input: str) -> dict:
        """
        Evaluates full sentence dictation (e.g. OLSA Open-Set sentence understanding).
        Returns word-by-word accuracy, list of word matches with status ('correct', 'incorrect'),
        and overall percentage score. Converts number words and digits interchangeably.
        """
        raw_target_words = (target_sentence or "").strip().split()
        if not raw_target_words:
            return {"score": 0.0, "is_correct": False, "word_results": [], "message": "Leerer Satz."}

        user_raw_words = (user_input or "").strip().split()

        # Normalize words and convert number words to digits for both target and user input
        norm_target_words = [self.german_words_to_digits(self.normalize(w)) for w in raw_target_words]
        norm_user_words = [self.german_words_to_digits(self.normalize(w)) for w in user_raw_words]

        # Use SequenceMatcher on number-normalized words
        matcher = difflib.SequenceMatcher(None, norm_target_words, norm_user_words)
        matching_blocks = matcher.get_matching_blocks()

        matched_target_indices = set()
        for block in matching_blocks:
            for i in range(block.size):
                matched_target_indices.add(block.a + i)

        correct_count = len(matched_target_indices)
        total_target_words = len(raw_target_words)
        score = round((correct_count / total_target_words) * 100.0, 1)
        is_correct = score >= 85.0

        word_results = []
        for idx, t_word in enumerate(raw_target_words):
            is_matched = (idx in matched_target_indices)
            word_results.append({
                "word": t_word,
                "status": "correct" if is_matched else "incorrect"
            })

        msg = f"✓ Richtig! Ganzsatz-Trefferquote: {score}%" if is_correct else f"Satzverständnis: {correct_count}/{total_target_words} Wörtern richtig ({score}%)."

        return {
            "score": score,
            "is_correct": is_correct,
            "correct_words": correct_count,
            "total_words": total_target_words,
            "word_results": word_results,
            "target_sentence": target_sentence,
            "user_input": user_input,
            "message": msg
        }
