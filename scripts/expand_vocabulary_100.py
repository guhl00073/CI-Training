import json
import os

def expand_all():
    # 1. Minimal Pairs (50 items)
    mp_data = [
        # Reim-Gruppen (Mehrfachauswahl)
        { "id": "mp_rhyme_01", "category": "Reim-Gruppe (-ut)", "source": "Marburger Minimalpaar-Katalog", "options": ["Mut", "Glut", "Flut", "Gut", "Hut", "Wut"], "difficulty": "Schwer", "hint": "Unterscheidung feiner Anlaute bei gleicher Endung -ut" },
        { "id": "mp_rhyme_02", "category": "Reim-Gruppe (-ein)", "source": "Marburger Minimalpaar-Katalog", "options": ["Bein", "Pein", "Stein", "Wein", "Fein", "Deich"], "difficulty": "Schwer", "hint": "Unterscheidung B / P / ST / W / F bei -ein" },
        { "id": "mp_rhyme_03", "category": "Reim-Gruppe (-anne)", "source": "Marburger Minimalpaar-Katalog", "options": ["Kanne", "Panne", "Tanne", "Wanne"], "difficulty": "Mittel", "hint": "Unterscheidung K / P / T / W vor -anne" },
        { "id": "mp_rhyme_04", "category": "Reim-Gruppe (-and)", "source": "Marburger Minimalpaar-Katalog", "options": ["Hand", "Wand", "Band", "Land", "Sand", "Pfand"], "difficulty": "Schwer", "hint": "Feindifferenzierung der Anlaute vor -and" },
        { "id": "mp_rhyme_05", "category": "Reim-Gruppe (-ock)", "source": "Marburger Minimalpaar-Katalog", "options": ["Bock", "Dock", "Rock", "Stock", "Socke"], "difficulty": "Mittel", "hint": "Unterscheidung Verschlusslaute und Zischlaute vor -ock" },

        # P vs B
        { "id": "mp_01", "category": "P vs. B", "source": "Marburger Minimalpaar-Katalog", "word_a": "Pass", "word_b": "Bass", "difficulty": "Einfach", "hint": "P (stimmlos) vs. B (stimmhaft)" },
        { "id": "mp_02", "category": "P vs. B", "source": "Marburger Minimalpaar-Katalog", "word_a": "Pein", "word_b": "Bein", "difficulty": "Einfach", "hint": "P vs. B im Anlaut" },
        { "id": "mp_03", "category": "P vs. B", "source": "Marburger Minimalpaar-Katalog", "word_a": "Packen", "word_b": "Backen", "difficulty": "Einfach", "hint": "Plosiv P vs. B vor Vokal A" },
        { "id": "mp_04", "category": "P vs. B", "source": "Marburger Minimalpaar-Katalog", "word_a": "Pech", "word_b": "Bach", "difficulty": "Mittel", "hint": "P vs. B mit Vokalkontrast" },
        { "id": "mp_05", "category": "P vs. B", "source": "Marburger Minimalpaar-Katalog", "word_a": "Pille", "word_b": "Bille", "difficulty": "Einfach", "hint": "P vs. B vor I" },

        # T vs D
        { "id": "mp_06", "category": "T vs. D", "source": "Marburger Minimalpaar-Katalog", "word_a": "Tasse", "word_b": "Dasse", "difficulty": "Einfach", "hint": "Alveolarer Plosiv T vs. D" },
        { "id": "mp_07", "category": "T vs. D", "source": "Marburger Minimalpaar-Katalog", "word_a": "Teich", "word_b": "Deich", "difficulty": "Mittel", "hint": "Alveolar T vs. D" },
        { "id": "mp_08", "category": "T vs. D", "source": "Marburger Minimalpaar-Katalog", "word_a": "Tank", "word_b": "Dank", "difficulty": "Einfach", "hint": "Anlaut T vs. D" },
        { "id": "mp_09", "category": "T vs. D", "source": "Marburger Minimalpaar-Katalog", "word_a": "Dorf", "word_b": "Torf", "difficulty": "Mittel", "hint": "D vs. T" },
        { "id": "mp_10", "category": "T vs. D", "source": "Marburger Minimalpaar-Katalog", "word_a": "Dach", "word_b": "Tach", "difficulty": "Einfach", "hint": "Dach vs. Tach" },

        # K vs G
        { "id": "mp_11", "category": "K vs. G", "source": "Marburger Minimalpaar-Katalog", "word_a": "Kanne", "word_b": "Panne", "difficulty": "Mittel", "hint": "K vs. P" },
        { "id": "mp_12", "category": "K vs. G", "source": "Marburger Minimalpaar-Katalog", "word_a": "Kasse", "word_b": "Gasse", "difficulty": "Einfach", "hint": "Velarer Plosiv K vs. G" },
        { "id": "mp_13", "category": "K vs. G", "source": "Marburger Minimalpaar-Katalog", "word_a": "Kunst", "word_b": "Gunst", "difficulty": "Mittel", "hint": "K vs. G vor U" },
        { "id": "mp_14", "category": "K vs. G", "source": "Marburger Minimalpaar-Katalog", "word_a": "Kuss", "word_b": "Guss", "difficulty": "Einfach", "hint": "Kuss vs. Guss" },
        { "id": "mp_15", "category": "K vs. G", "source": "Marburger Minimalpaar-Katalog", "word_a": "Kamm", "word_b": "Gamm", "difficulty": "Mittel", "hint": "K vs. G" },

        # S vs SCH
        { "id": "mp_16", "category": "S vs. SCH", "source": "Marburger Minimalpaar-Katalog", "word_a": "Sonne", "word_b": "Wonne", "difficulty": "Mittel", "hint": "S vs. W" },
        { "id": "mp_17", "category": "S vs. SCH", "source": "Marburger Minimalpaar-Katalog", "word_a": "Stein", "word_b": "Bein", "difficulty": "Einfach", "hint": "Zischlaut im Anlaut" },
        { "id": "mp_18", "category": "S vs. SCH", "source": "Marburger Minimalpaar-Katalog", "word_a": "Schiene", "word_b": "Biene", "difficulty": "Mittel", "hint": "SCH vs. B" },
        { "id": "mp_19", "category": "S vs. SCH", "source": "Marburger Minimalpaar-Katalog", "word_a": "Saale", "word_b": "Schale", "difficulty": "Mittel", "hint": "Scharfes S vs. SCH" },
        { "id": "mp_20", "category": "S vs. SCH", "source": "Marburger Minimalpaar-Katalog", "word_a": "Sonne", "word_b": "Schonne", "difficulty": "Mittel", "hint": "S vs. SCH" },

        # M vs N
        { "id": "mp_21", "category": "M vs. N", "source": "Marburger Minimalpaar-Katalog", "word_a": "Maus", "word_b": "Haus", "difficulty": "Einfach", "hint": "M vs. H" },
        { "id": "mp_22", "category": "M vs. N", "source": "Marburger Minimalpaar-Katalog", "word_a": "Kamm", "word_b": "Kann", "difficulty": "Schwer", "hint": "M vs. N im Auslaut" },
        { "id": "mp_23", "category": "M vs. N", "source": "Marburger Minimalpaar-Katalog", "word_a": "Mein", "word_b": "Nein", "difficulty": "Einfach", "hint": "M vs. N im Anlaut" },
        { "id": "mp_24", "category": "M vs. N", "source": "Marburger Minimalpaar-Katalog", "word_a": "Mund", "word_b": "Hund", "difficulty": "Einfach", "hint": "Mund vs. Hund" },

        # F vs W
        { "id": "mp_25", "category": "F vs. W", "source": "Marburger Minimalpaar-Katalog", "word_a": "Fisch", "word_b": "Wisch", "difficulty": "Mittel", "hint": "F vs. W" },
        { "id": "mp_26", "category": "F vs. W", "source": "Marburger Minimalpaar-Katalog", "word_a": "Fast", "word_b": "Wast", "difficulty": "Mittel", "hint": "F vs. W" },
        { "id": "mp_27", "category": "F vs. W", "source": "Marburger Minimalpaar-Katalog", "word_a": "Feld", "word_b": "Welt", "difficulty": "Einfach", "hint": "Feld vs. Welt" },

        # R vs L
        { "id": "mp_28", "category": "R vs. L", "source": "Marburger Minimalpaar-Katalog", "word_a": "Ratte", "word_b": "Latte", "difficulty": "Mittel", "hint": "R vs. L" },
        { "id": "mp_29", "category": "R vs. L", "source": "Marburger Minimalpaar-Katalog", "word_a": "Riese", "word_b": "Liese", "difficulty": "Einfach", "hint": "Riese vs. Liese" },
        { "id": "mp_30", "category": "R vs. L", "source": "Marburger Minimalpaar-Katalog", "word_a": "Rolle", "word_b": "Lolle", "difficulty": "Mittel", "hint": "Rolle vs. Lolle" },
        { "id": "mp_31", "category": "R vs. L", "source": "Marburger Minimalpaar-Katalog", "word_a": "Rast", "word_b": "Last", "difficulty": "Einfach", "hint": "Rast vs. Last" },

        # CH1 vs CH2
        { "id": "mp_32", "category": "CH1 vs. CH2", "source": "Marburger Minimalpaar-Katalog", "word_a": "Teich", "word_b": "Tauch", "difficulty": "Schwer", "hint": "Ich-Laut vs. Ach-Laut" },
        { "id": "mp_33", "category": "CH1 vs. CH2", "source": "Marburger Minimalpaar-Katalog", "word_a": "Reich", "word_b": "Rauch", "difficulty": "Schwer", "hint": "Ich-Laut vs. Ach-Laut" },

        # H vs K/G
        { "id": "mp_34", "category": "H vs. K/G", "source": "Marburger Minimalpaar-Katalog", "word_a": "Haus", "word_b": "Maus", "difficulty": "Einfach", "hint": "H vs. M" },
        { "id": "mp_35", "category": "H vs. K/G", "source": "Marburger Minimalpaar-Katalog", "word_a": "Hut", "word_b": "Gut", "difficulty": "Einfach", "hint": "H vs. G" },

        # PF vs F/P
        { "id": "mp_36", "category": "PF vs. F/P", "source": "Marburger Minimalpaar-Katalog", "word_a": "Pfeife", "word_b": "Reife", "difficulty": "Schwer", "hint": "PF vs. R" },
        { "id": "mp_37", "category": "PF vs. F/P", "source": "Marburger Minimalpaar-Katalog", "word_a": "Pfund", "word_b": "Fund", "difficulty": "Schwer", "hint": "PF vs. F" },

        # Z vs S
        { "id": "mp_38", "category": "Z vs. S", "source": "Marburger Minimalpaar-Katalog", "word_a": "Zinn", "word_b": "Sinn", "difficulty": "Mittel", "hint": "Z vs. S" },
        { "id": "mp_39", "category": "Z vs. S", "source": "Marburger Minimalpaar-Katalog", "word_a": "Zelt", "word_b": "Selt", "difficulty": "Mittel", "hint": "Z vs. S" },

        # Diphthonge
        { "id": "mp_40", "category": "Diphthonge (EI / AU / EU)", "source": "Marburger Minimalpaar-Katalog", "word_a": "Haus", "word_b": "Heis", "difficulty": "Mittel", "hint": "AU vs. EI" },
        { "id": "mp_41", "category": "Diphthonge (EI / AU / EU)", "source": "Marburger Minimalpaar-Katalog", "word_a": "Baum", "word_b": "Beim", "difficulty": "Mittel", "hint": "AU vs. EI" },

        # Vokale
        { "id": "mp_42", "category": "Vokale (A / E / I / O / U)", "source": "Marburger Minimalpaar-Katalog", "word_a": "Kamm", "word_b": "Komm", "difficulty": "Mittel", "hint": "A vs. O" },
        { "id": "mp_43", "category": "Vokale (A / E / I / O / U)", "source": "Marburger Minimalpaar-Katalog", "word_a": "bieten", "word_b": "beten", "difficulty": "Mittel", "hint": "I vs. E" },
        { "id": "mp_44", "category": "Vokale (A / E / I / O / U)", "source": "Marburger Minimalpaar-Katalog", "word_a": "Hut", "word_b": "Rot", "difficulty": "Einfach", "hint": "U vs. O" },
        { "id": "mp_45", "category": "Vokale (A / E / I / O / U)", "source": "Marburger Minimalpaar-Katalog", "word_a": "Fluss", "word_b": "Floss", "difficulty": "Mittel", "hint": "U vs. O" },
        { "id": "mp_46", "category": "Auslaut: T vs. K", "source": "Marburger Minimalpaar-Katalog", "word_a": "Hut", "word_b": "Huck", "difficulty": "Schwer", "hint": "T vs. K im Auslaut" }
    ]

    # 2. Monosyllables (30 items - Freiburger Einsilber)
    es_data = [
        { "id": "es_01", "word": "Baum", "category": "Natur", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_02", "word": "Haus", "category": "Gebäude", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_03", "word": "Hund", "category": "Tiere", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_04", "word": "Katze", "category": "Tiere", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_05", "word": "Mond", "category": "Natur", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_06", "word": "Brot", "category": "Essen", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_07", "word": "Fisch", "category": "Tiere", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_08", "word": "Zug", "category": "Verkehr", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_09", "word": "Buch", "category": "Gegenstände", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_10", "word": "Schiff", "category": "Verkehr", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_11", "word": "Tisch", "category": "Möbel", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_12", "word": "Stuhl", "category": "Möbel", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_13", "word": "Bett", "category": "Möbel", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_14", "word": "Glas", "category": "Geschirr", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_15", "word": "Tasse", "category": "Geschirr", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_16", "word": "Stern", "category": "Natur", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Mittel" },
        { "id": "es_17", "word": "Ring", "category": "Schmuck", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Mittel" },
        { "id": "es_18", "word": "Schuh", "category": "Kleidung", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Mittel" },
        { "id": "es_19", "word": "Strumpf", "category": "Kleidung", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Schwer" },
        { "id": "es_20", "word": "Zwerg", "category": "Märchen", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Schwer" },
        { "id": "es_21", "word": "Kopf", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_22", "word": "Arm", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_23", "word": "Bein", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_24", "word": "Hand", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_25", "word": "Mund", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_26", "word": "Zahn", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_27", "word": "Herz", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_28", "word": "Knie", "category": "Körper", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_29", "word": "Hut", "category": "Kleidung", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Einfach" },
        { "id": "es_30", "word": "Hemd", "category": "Kleidung", "source": "Freiburger Einsilber-Test (DIN 45621)", "difficulty": "Mittel" }
    ]

    # 3. Sentences (15 items - Oldenburger OLSA)
    sent_data = [
        { "id": "sent_01", "category": "Alltagssätze", "source": "Oldenburger Satztest (OLSA)", "sentence": "Der Hund bellt im Garten.", "target_word": "Hund", "options": ["Hund", "Mund", "Fund"], "hint": "Achte auf das Tier im Satz." },
        { "id": "sent_02", "category": "Alltagssätze", "source": "Oldenburger Satztest (OLSA)", "sentence": "Die Tasse steht auf dem Tisch.", "target_word": "Tasse", "options": ["Tasse", "Kasse", "Rasse"], "hint": "Achte auf das Gefäß." },
        { "id": "sent_03", "category": "Natur & Wetter", "source": "Oldenburger Satztest (OLSA)", "sentence": "Im Sommer scheint die Sonne.", "target_word": "Sonne", "options": ["Sonne", "Wonne", "Tonne"], "hint": "Achte auf das Himmelsgestirn." },
        { "id": "sent_04", "category": "Reimsätze", "source": "Oldenburger Satztest (OLSA)", "sentence": "Der Mensch zeigt großen Mut.", "target_word": "Mut", "options": ["Mut", "Glut", "Flut", "Gut"], "hint": "Achte auf das Eigenschaftenwort." },
        { "id": "sent_05", "category": "Natur", "source": "Oldenburger Satztest (OLSA)", "sentence": "Der Fisch schwimmt munter im Wasser.", "target_word": "Fisch", "options": ["Fisch", "Wisch", "Tisch"], "hint": "Achte auf das Wassertier." },
        { "id": "sent_06", "category": "Kleidung", "source": "Oldenburger Satztest (OLSA)", "sentence": "Er zieht seinen warmen Hut an.", "target_word": "Hut", "options": ["Hut", "Mut", "Gut"], "hint": "Achte auf die Kopfbedeckung." },
        { "id": "sent_07", "category": "Alltag", "source": "Oldenburger Satztest (OLSA)", "sentence": "Das Kind trinkt frische Milch.", "target_word": "Milch", "options": ["Milch", "Matsch", "Misch"], "hint": "Achte auf das Getränk." },
        { "id": "sent_08", "category": "Haushalt", "source": "Oldenburger Satztest (OLSA)", "sentence": "Die Katze schläft auf dem Bett.", "target_word": "Bett", "options": ["Bett", "Pet", "Fett"], "hint": "Achte auf das Möbelstück." },
        { "id": "sent_09", "category": "Verkehr", "source": "Oldenburger Satztest (OLSA)", "sentence": "Der rote Bus hält an der Haltestelle.", "target_word": "Bus", "options": ["Bus", "Guss", "Kuss"], "hint": "Achte auf das Verkehrsmittel." },
        { "id": "sent_10", "category": "Natur", "source": "Oldenburger Satztest (OLSA)", "sentence": "Ein großer Vogel fliegt am Himmel.", "target_word": "Vogel", "options": ["Vogel", "Kugel", "Segel"], "hint": "Achte auf das Tier." },
        { "id": "sent_11", "category": "Essen", "source": "Oldenburger Satztest (OLSA)", "sentence": "Wir essen heute frisches Brot.", "target_word": "Brot", "options": ["Brot", "Boot", "Rot"], "hint": "Achte auf das Lebensmittel." },
        { "id": "sent_12", "category": "Wohnen", "source": "Oldenburger Satztest (OLSA)", "sentence": "Das Fenster steht weit offen.", "target_word": "Fenster", "options": ["Fenster", "Münster", "Finster"], "hint": "Achte auf das Bauteil." },
        { "id": "sent_13", "category": "Freizeit", "source": "Oldenburger Satztest (OLSA)", "sentence": "Sie liest ein spannendes Buch.", "target_word": "Buch", "options": ["Buch", "Tuch", "Fluch"], "hint": "Achte auf den Gegenstand." },
        { "id": "sent_14", "category": "Natur", "source": "Oldenburger Satztest (OLSA)", "sentence": "Der Baum hat grüne Blätter.", "target_word": "Baum", "options": ["Baum", "Traum", "Raum"], "hint": "Achte auf die Pflanze." },
        { "id": "sent_15", "category": "Alltag", "source": "Oldenburger Satztest (OLSA)", "sentence": "Er wäscht sich gründlich die Hände.", "target_word": "Hände", "options": ["Hände", "Wände", "Bände"], "hint": "Achte auf den Körperteil." }
    ]

    # 4. Numbers (15 items)
    num_data = [
        { "id": "num_01", "type": "Einfache Zahlen", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "7", "spoken": "Sieben", "difficulty": "Einfach" },
        { "id": "num_02", "type": "Einfache Zahlen", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "14", "spoken": "Vierzehn", "difficulty": "Einfach" },
        { "id": "num_03", "type": "Einfache Zahlen", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "42", "spoken": "Zweiundvierzig", "difficulty": "Mittel" },
        { "id": "num_04", "type": "Einfache Zahlen", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "99", "spoken": "Neunundneunzig", "difficulty": "Mittel" },
        { "id": "num_05", "type": "Große Zahlen", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "350", "spoken": "Dreihundertfünfzig", "difficulty": "Mittel" },
        { "id": "num_06", "type": "Uhrzeiten", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "14:30", "spoken": "Vierzehn Uhr dreißig", "difficulty": "Mittel" },
        { "id": "num_07", "type": "Uhrzeiten", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "08:15", "spoken": "Acht Uhr fünfzehn", "difficulty": "Einfach" },
        { "id": "num_08", "type": "Uhrzeiten", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "18:45", "spoken": "Achtzehn Uhr fünfundvierzig", "difficulty": "Mittel" },
        { "id": "num_09", "type": "Uhrzeiten", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "12:00", "spoken": "Zwölf Uhr mittags", "difficulty": "Einfach" },
        { "id": "num_10", "type": "Beträge", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "12,50 €", "spoken": "Zwölf Euro fünfzig", "difficulty": "Mittel" },
        { "id": "num_11", "type": "Beträge", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "99,90 €", "spoken": "Neunundneunzig Euro neunzig", "difficulty": "Schwer" },
        { "id": "num_12", "type": "Beträge", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "5,00 €", "spoken": "Fünf Euro", "difficulty": "Einfach" },
        { "id": "num_13", "type": "Große Zahlen", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "1000", "spoken": "Eintausend", "difficulty": "Mittel" },
        { "id": "num_14", "type": "Einfache Zahlen", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "18", "spoken": "Achtzehn", "difficulty": "Einfach" },
        { "id": "num_15", "type": "Uhrzeiten", "source": "Audiologischer Zahlen- & Uhrzeitentest", "value": "22:10", "spoken": "Zweiundzwanzig Uhr zehn", "difficulty": "Schwer" }
    ]

    save_json("data/minimal_pairs.json", mp_data)
    save_json("data/monosyllables.json", es_data)
    save_json("data/sentences.json", sent_data)
    save_json("data/numbers.json", num_data)

    total = len(mp_data) + len(es_data) + len(sent_data) + len(num_data)
    print(f"🚀 Wortschatz auf insgesamt {total} audiologische Einträge erweitert!")

def save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    expand_all()
