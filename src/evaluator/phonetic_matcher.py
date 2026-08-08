import difflib
import re

class PhoneticMatcher:
    """
    Evaluator for comparing user's spoken or typed answer with target words.
    Provides detailed phonetic feedback for CI auditory training.
    """
    GERMAN_VOWELS = set("aeiouäöüyAEIOUÄÖÜY")
    
    @staticmethod
    def normalize(text: str) -> str:
        """Strips punctuation and normalizes string for comparison."""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', '', text)
        return text

    def evaluate(self, target: str, user_input: str) -> dict:
        """
        Evaluates the user input against the target word.
        Returns a dictionary with score (0-100%), match_status, and constructive feedback.
        """
        norm_target = self.normalize(target)
        norm_user = self.normalize(user_input)

        if not norm_user:
            return {
                "score": 0.0,
                "status": "empty",
                "message": "Keine Eingabe / Sprache erkannt.",
                "is_correct": False
            }

        # Exact match
        if norm_target == norm_user:
            return {
                "score": 100.0,
                "status": "exact",
                "message": f"Perfekt! '{target}' wurde exakt richtig gehört.",
                "is_correct": True
            }

        # Sequence matcher similarity ratio
        ratio = difflib.SequenceMatcher(None, norm_target, norm_user).ratio()
        score = round(ratio * 100, 1)
        is_correct = score >= 80.0

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

        msg = " ".join(feedback_parts) if feedback_parts else f"Ähnlichkeit: {score}%."

        return {
            "score": score,
            "status": "partial" if score > 50 else "incorrect",
            "message": f"Ziel: '{target}' | Gehört: '{user_input}'. {msg}",
            "is_correct": is_correct
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
            "siebenhundert": 700, "achthandert": 800, "neunhundert": 900
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
                # Handle combined words like 'einundzwanzig', 'fünfundachtzig'
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
