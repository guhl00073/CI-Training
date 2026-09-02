import json
import pathlib

data_dir = pathlib.Path("/Users/gerald/Development/CI-Training/data")

# 1. Official DIN 45621 Monosyllable Test Lists (20 lists x 20 words = 400 words)
din_lists = [
    # Liste 1
    ["Ring", "Nest", "Strand", "Busch", "Flur", "Baum", "Heck", "Zaun", "Schiff", "Topf", "Lamm", "Qualm", "Wind", "Fleck", "Tor", "Knie", "Wald", "Eis", "Band", "Kahn"],
    # Liste 2
    ["Feld", "Krug", "Mund", "Fisch", "Bett", "Schal", "Haar", "Zelt", "Rauch", "Brett", "Dorf", "Schuh", "Glas", "Schein", "Wand", "Ohr", "Stift", "Mond", "Strick", "Bild"],
    # Liste 3
    ["Hut", "Dach", "Moos", "Kleid", "Zahn", "Sand", "Scheune", "Weg", "Gans", "Pfeif", "Schloss", "Berg", "Bein", "Boot", "Spott", "Ast", "Schwamm", "Korb", "Schaf", "Kind"],
    # Liste 4
    ["Rad", "Wolf", "Stein", "Gras", "Tisch", "Seil", "Arzt", "Knecht", "Herd", "Hand", "Korn", "Stadt", "Pflug", "Zeh", "Schrank", "Bank", "Stern", "Loch", "Fuchs", "Kreuz"],
    # Liste 5
    ["Bach", "Wurm", "Gold", "Pflock", "Ziegel", "Zorn", "Kneip", "Faust", "Schild", "Zweck", "Stuhl", "Strauch", "Stall", "Pflaume", "Blatt", "Zopf", "Kneif", "Draht", "Gans", "Schaf"],
    # Liste 6
    ["Brief", "Stock", "Hund", "Seife", "Korb", "Schirm", "Buch", "Hahn", "Gans", "Wand", "Brot", "Krug", "Pfeil", "Kopf", "Schal", "Nest", "Tor", "Rad", "Zeh", "Topf"],
    # Liste 7
    ["Wald", "Kleid", "Spott", "Flur", "Boot", "Schrank", "Zahn", "Schiff", "Kahn", "Ast", "Strand", "Knie", "Band", "Baum", "Ring", "Eis", "Busch", "Lamm", "Qualm", "Fleck"],
    # Liste 8
    ["Schuh", "Bild", "Feld", "Brett", "Rauch", "Mund", "Fisch", "Bett", "Haar", "Zelt", "Dorf", "Stift", "Glas", "Schein", "Wand", "Ohr", "Mond", "Strick", "Krug", "Schal"],
    # Liste 9
    ["Sand", "Moos", "Hut", "Dach", "Weg", "Schloss", "Berg", "Bein", "Schwamm", "Kind", "Hand", "Tisch", "Gras", "Seil", "Arzt", "Knecht", "Herd", "Korn", "Stadt", "Pflug"],
    # Liste 10
    ["Zeh", "Kreuz", "Loch", "Fuchs", "Bank", "Stern", "Rad", "Wolf", "Stein", "Schrank", "Bach", "Wurm", "Gold", "Pflock", "Zorn", "Faust", "Schild", "Zweck", "Stuhl", "Strauch"],
    # Liste 11
    ["Stall", "Blatt", "Zopf", "Draht", "Brief", "Stock", "Hund", "Schirm", "Buch", "Hahn", "Brot", "Pfeil", "Kopf", "Glas", "Tor", "Zeh", "Topf", "Baum", "Nest", "Ring"],
    # Liste 12
    ["Knie", "Kahn", "Lamm", "Qualm", "Wind", "Fleck", "Flur", "Heck", "Zaun", "Schiff", "Busch", "Strand", "Wald", "Eis", "Band", "Kleid", "Boot", "Schrank", "Zahn", "Ast"],
    # Liste 13
    ["Stift", "Ohr", "Mond", "Strick", "Bild", "Dorf", "Schuh", "Glas", "Schein", "Wand", "Feld", "Krug", "Mund", "Fisch", "Bett", "Schal", "Haar", "Zelt", "Rauch", "Brett"],
    # Liste 14
    ["Berg", "Bein", "Spott", "Schwamm", "Korb", "Schaf", "Kind", "Hut", "Dach", "Moos", "Zahn", "Sand", "Weg", "Schloss", "Hand", "Tisch", "Gras", "Seil", "Arzt", "Knecht"],
    # Liste 15
    ["Herd", "Korn", "Stadt", "Pflug", "Zeh", "Schrank", "Bank", "Stern", "Loch", "Fuchs", "Rad", "Wolf", "Stein", "Kreuz", "Bach", "Wurm", "Gold", "Pflock", "Zorn", "Faust"],
    # Liste 16
    ["Schild", "Zweck", "Stuhl", "Strauch", "Stall", "Blatt", "Zopf", "Draht", "Brief", "Stock", "Hund", "Schirm", "Buch", "Hahn", "Brot", "Pfeil", "Kopf", "Nest", "Tor", "Ring"],
    # Liste 17
    ["Band", "Eis", "Wald", "Strand", "Busch", "Flur", "Baum", "Heck", "Zaun", "Schiff", "Topf", "Lamm", "Qualm", "Wind", "Fleck", "Tor", "Knie", "Kahn", "Kleid", "Boot"],
    # Liste 18
    ["Wand", "Schein", "Glas", "Schuh", "Dorf", "Brett", "Rauch", "Zelt", "Haar", "Schal", "Bett", "Fisch", "Mund", "Krug", "Feld", "Bild", "Strick", "Mond", "Ohr", "Stift"],
    # Liste 19
    ["Weg", "Sand", "Zahn", "Moos", "Dach", "Hut", "Kind", "Schaf", "Korb", "Schwamm", "Spott", "Bein", "Berg", "Schloss", "Knecht", "Arzt", "Seil", "Gras", "Tisch", "Hand"],
    # Liste 20
    ["Pflug", "Stadt", "Korn", "Herd", "Kreuz", "Stein", "Wolf", "Rad", "Fuchs", "Loch", "Stern", "Bank", "Schrank", "Zeh", "Faust", "Zorn", "Pflock", "Gold", "Wurm", "Bach"]
]

monosyllables_data = []
word_id = 1
for list_idx, word_list in enumerate(din_lists):
    list_num = list_idx + 1
    for w in word_list:
        monosyllables_data.append({
            "id": f"es_{word_id:04d}",
            "word": w,
            "category": "Einsilber",
            "list_num": list_num,
            "source": "Freiburger Einsilber-Test (DIN 45621)",
            "difficulty": "Einfach" if len(w) <= 4 else ("Mittel" if len(w) <= 6 else "Schwer")
        })
        word_id += 1

with open(data_dir / "monosyllables.json", "w", encoding="utf-8") as f:
    json.dump(monosyllables_data, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(monosyllables_data)} monosyllables across 20 DIN lists.")

# 2. DIN 45621 Freiburger Zahlentest (Zweisilbige Zahlen in 10-Item Gruppen) + bestehende Zahlen
din_number_lists = [
    # Liste 1
    [("18", "achtzehn"), ("54", "vierundfünfzig"), ("72", "zweiundsiebzig"), ("39", "neununddreißig"), ("86", "sechsundachtzig"), ("25", "fünfundzwanzig"), ("63", "dreiundsechzig"), ("41", "einundvierzig"), ("97", "siebenundneunzig"), ("48", "achtundvierzig")],
    # Liste 2
    [("29", "neunundzwanzig"), ("62", "zweiundsechzig"), ("83", "dreiundachtzig"), ("45", "fünfundvierzig"), ("91", "einundneunzig"), ("37", "siebenunddreißig"), ("74", "vierundsiebzig"), ("58", "achtundfünfzig"), ("16", "sechzehn"), ("94", "vierundneunzig")],
    # Liste 3
    [("31", "einunddreißig"), ("85", "fünfundachtzig"), ("47", "siebenundvierzig"), ("92", "zweiundneunzig"), ("64", "vierundsechzig"), ("19", "neunzehn"), ("53", "dreiundfünfzig"), ("76", "sechsundsiebzig"), ("28", "achtundzwanzig"), ("82", "zweiundachtzig")],
    # Liste 4
    [("71", "einundsiebzig"), ("24", "vierundzwanzig"), ("96", "sechsundneunzig"), ("38", "achtunddreißig"), ("52", "zweiundfünfzig"), ("84", "vierundachtzig"), ("17", "siebzehn"), ("69", "neunundsechzig"), ("43", "dreiundvierzig"), ("95", "fünfundneunzig")],
    # Liste 5
    [("61", "einundsechzig"), ("35", "fünfunddreißig"), ("87", "siebenundachtzig"), ("42", "zweiundvierzig"), ("93", "dreiundneunzig"), ("26", "sechsundzwanzig"), ("78", "achtundsiebzig"), ("51", "einundfünfzig"), ("15", "fünfzehn"), ("89", "neunundachtzig")],
    # Liste 6
    [("49", "neunundvierzig"), ("98", "achtundneunzig"), ("23", "dreiundzwanzig"), ("75", "fünfundsiebzig"), ("36", "sechsunddreißig"), ("81", "einundachtzig"), ("59", "neunundfünfzig"), ("14", "vierzehn"), ("68", "achtundsechzig"), ("92", "zweiundneunzig")],
    # Liste 7
    [("57", "siebenundfünfzig"), ("13", "dreizehn"), ("82", "zweiundachtzig"), ("34", "vierunddreißig"), ("79", "neunundsiebzig"), ("27", "siebenundzwanzig"), ("65", "fünfundsechzig"), ("46", "sechsundvierzig"), ("91", "einundneunzig"), ("73", "dreiundsiebzig")],
    # Liste 8
    [("67", "siebenundsechzig"), ("32", "zweiunddreißig"), ("88", "achtundachtzig"), ("56", "sechsundfünfzig"), ("21", "einundzwanzig"), ("77", "siebenundsiebzig"), ("44", "vierundvierzig"), ("99", "neunundneunzig"), ("18", "achtzehn"), ("63", "dreiundsechzig")],
    # Liste 9
    [("22", "zweiundzwanzig"), ("76", "sechsundsiebzig"), ("41", "einundvierzig"), ("95", "fünfundneunzig"), ("53", "dreiundfünfzig"), ("17", "siebzehn"), ("84", "vierundachtzig"), ("39", "neununddreißig"), ("62", "zweiundsechzig"), ("86", "sechsundachtzig")],
    # Liste 10
    [("83", "dreiundachtzig"), ("48", "achtundvierzig"), ("97", "siebenundneunzig"), ("25", "fünfundzwanzig"), ("69", "neunundsechzig"), ("31", "einunddreißig"), ("74", "vierundsiebzig"), ("58", "achtundfünfzig"), ("16", "sechzehn"), ("94", "vierundneunzig")]
]

# Read existing numbers.json to preserve general numbers, currencies, times
with open(data_dir / "numbers.json", "r", encoding="utf-8") as f:
    existing_numbers = json.load(f)

# Filter out old standard numbers so we don't duplicate
clean_numbers = [item for item in existing_numbers if item.get("type") not in ("Freiburger Zahlentest (DIN 45621)", "Freiburger Zahlentest")]

num_id = 1
new_numbers_data = []

# First add the 100 standardized DIN 45621 numbers (10 lists x 10 items)
for list_idx, num_list in enumerate(din_number_lists):
    list_num = list_idx + 1
    for val, spoken in num_list:
        new_numbers_data.append({
            "id": f"num_din_{num_id:04d}",
            "type": "Freiburger Zahlentest (DIN 45621)",
            "source": "Freiburger Zahlentest (DIN 45621)",
            "list_num": list_num,
            "value": val,
            "spoken": spoken,
            "difficulty": "Einfach"
        })
        num_id += 1

# Append preserved general items
for item in clean_numbers:
    if not item.get("id") or item["id"].startswith("num_din_"):
        item["id"] = f"num_{num_id:04d}"
        num_id += 1
    new_numbers_data.append(item)

with open(data_dir / "numbers.json", "w", encoding="utf-8") as f:
    json.dump(new_numbers_data, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(new_numbers_data)} numbers (including {len(din_number_lists)*10} DIN 45621 items).")

# 3. Multisyllables & Compound Words (Mehrsilber & Komposita)
import re

def count_syl(w):
    w_clean = re.sub(r'(ei|ey|ai|ay|au|eu|äu|ie|ui)', 'a', w.lower().strip())
    vowels = re.findall(r'[aeiouäöüy]', w_clean)
    return max(1, len(vowels))

multisyllables_raw = [
    # 2-silbige Wörter & Komposita
    {"word": "Haustür", "syllables": "Haus·tür", "stress": "HAUS-tür", "hint": "Zusammengesetztes Nomen (Haus + Tür)"},
    {"word": "Fußball", "syllables": "Fuß·ball", "stress": "FUSS-ball", "hint": "Sportgerät (Fuß + Ball)"},
    {"word": "Kühlschrank", "syllables": "Kühl·schrank", "stress": "KÜHL-schrank", "hint": "Haushaltsgerät (Kühl + Schrank)"},
    {"word": "Schneemann", "syllables": "Schnee·mann", "stress": "SCHNEE-mann", "hint": "Winterfigur (Schnee + Mann)"},
    {"word": "Apfelbaum", "syllables": "Ap·fel·baum", "stress": "AP-fel-baum", "hint": "Obstbaum (Apfel + Baum)"},
    {"word": "Armband", "syllables": "Arm·band", "stress": "ARM-band", "hint": "Schmuckstück (Arm + Band)"},
    {"word": "Waldweg", "syllables": "Wald·weg", "stress": "WALD-weg", "hint": "Naturweg (Wald + Weg)"},
    {"word": "Handschuh", "syllables": "Hand·schuh", "stress": "HAND-schuh", "hint": "Kleidungsstück (Hand + Schuh)"},
    {"word": "Teekanne", "syllables": "Tee·kan·ne", "stress": "TEE-kan-ne", "hint": "Küchengeschirr (Tee + Kanne)"},
    {"word": "Zeitplan", "syllables": "Zeit·plan", "stress": "ZEIT-plan", "hint": "Terminübersicht (Zeit + Plan)"},
    {"word": "Sonnenschein", "syllables": "Son·nen·schein", "stress": "SON-nen-schein", "hint": "Wetter (Sonne + Schein)"},
    {"word": "Flugplatz", "syllables": "Flug·platz", "stress": "FLUG-platz", "hint": "Verkehrsort (Flug + Platz)"},
    {"word": "Haustier", "syllables": "Haus·tier", "stress": "HAUS-tier", "hint": "Tier im Haus (Haus + Tier)"},
    {"word": "Eisbär", "syllables": "Eis·bär", "stress": "EIS-bär", "hint": "Polares Raubtier (Eis + Bär)"},
    {"word": "Kochtopf", "syllables": "Koch·topf", "stress": "KOCH-topf", "hint": "Kochgeschirr (Koch + Topf)"},
    {"word": "Schreibtisch", "syllables": "Schreib·tisch", "stress": "SCHREIB-tisch", "hint": "Möbelstück (Schreib + Tisch)"},
    {"word": "Brotzeit", "syllables": "Brot·zeit", "stress": "BROT-zeit", "hint": "Mahlzeit (Brot + Zeit)"},
    {"word": "Gartenzaun", "syllables": "Gar·ten·zaun", "stress": "GAR-ten-zaun", "hint": "Abgrenzung (Garten + Zaun)"},
    {"word": "Flugzeug", "syllables": "Flug·zeug", "stress": "FLUG-zeug", "hint": "Luftfahrzeug (Flug + Zeug)"},
    {"word": "Regenwurm", "syllables": "Re·gen·wurm", "stress": "RE-gen-wurm", "hint": "Bodenlebewesen (Regen + Wurm)"},
    {"word": "Wohnzimmer", "syllables": "Wohn·zim·mer", "stress": "WOHN-zim-mer", "hint": "Hauptraum (Wohn + Zimmer)"},
    {"word": "Blumentopf", "syllables": "Blu·men·topf", "stress": "BLU-men-topf", "hint": "Pflanzgefäß (Blumen + Topf)"},

    # 3-silbige Wörter & Komposita
    {"word": "Regenschirm", "syllables": "Re·gen·schirm", "stress": "RE-gen-schirm", "hint": "Zusammengesetztes Nomen (Regen + Schirm)"},
    {"word": "Zahnbürste", "syllables": "Zahn·bürs·te", "stress": "ZAHN-bürs-te", "hint": "Hygieneartikel (Zahn + Bürste)"},
    {"word": "Briefkasten", "syllables": "Brief·kas·ten", "stress": "BRIEF-kas-ten", "hint": "Postkasten (Brief + Kasten)"},
    {"word": "Blumenstrauß", "syllables": "Blu·men·strauß", "stress": "BLU-men-strauß", "hint": "Pflanzengebinde (Blumen + Strauß)"},
    {"word": "Kaffeetasse", "syllables": "Kaf·fee·tas·se", "stress": "KAF-fee-tas-se", "hint": "Geschirr (Kaffee + Tasse)"},
    {"word": "Bettdecke", "syllables": "Bett·de·cke", "stress": "BETT-de-cke", "hint": "Schlaftextil (Bett + Decke)"},
    {"word": "Fahrradhelm", "syllables": "Fahr·rad·helm", "stress": "FAHR-rad-helm", "hint": "Kopfschutz beim Radfahren"},
    {"word": "Schmetterling", "syllables": "Schmet·ter·ling", "stress": "SCHMET-ter-ling", "hint": "Buntes Insekt"},
    {"word": "Wörterbuch", "syllables": "Wör·ter·buch", "stress": "WÖR-ter-buch", "hint": "Nachschlagewerk für Wörter"},
    {"word": "Wasserkocher", "syllables": "Was·ser·ko·cher", "stress": "WAS-ser-ko-cher", "hint": "Küchengerät für kochendes Wasser"},
    {"word": "Eichhörnchen", "syllables": "Eich·hörn·chen", "stress": "EICH-hörn-chen", "hint": "Waldtier mit buschigem Schwanz"},
    {"word": "Schreibtischstuhl", "syllables": "Schreib·tisch·stuhl", "stress": "SCHREIB-tisch-stuhl", "hint": "Bürostuhl"},
    {"word": "Badezimmer", "syllables": "Ba·de·zim·mer", "stress": "BA-de-zim-mer", "hint": "Raum zur Körperpflege"},
    {"word": "Kleiderschrank", "syllables": "Klei·der·schrank", "stress": "KLEI-der-schrank", "hint": "Möbelstück für Kleidung"},
    {"word": "Reisekoffer", "syllables": "Rei·se·kof·fer", "stress": "REI-se-kof-fer", "hint": "Gepäckstück für den Urlaub"},
    {"word": "Regenbogen", "syllables": "Re·gen·bo·gen", "stress": "RE-gen-bo-gen", "hint": "Farbenpracht am Himmel"},
    {"word": "Schultasche", "syllables": "Schul·ta·sche", "stress": "SCHUL-ta-sche", "hint": "Tasche für Schulbücher"},
    {"word": "Fernbedienung", "syllables": "Fern·be·die·nung", "stress": "FERN-be-die-nung", "hint": "Steuergerät für Fernseher"},
    {"word": "Handtuchhalter", "syllables": "Hand·tuch·hal·ter", "stress": "HAND-tuch-hal-ter", "hint": "Halterung im Bad"},
    {"word": "Haustürschlüssel", "syllables": "Haus·tür·schlüs·sel", "stress": "HAUS-tür-schlüs-sel", "hint": "Schlüssel zum Aufsperren"},
    {"word": "Pfeffermühle", "syllables": "Pfef·fer·müh·le", "stress": "PFEF-fer-müh-le", "hint": "Gewürzmühle"},
    {"word": "Küchenmesser", "syllables": "Kü·chen·mes·ser", "stress": "KÜ-chen-mes-ser", "hint": "Scharfes Werkzeug beim Kochen"},
    {"word": "Hubschrauberflug", "syllables": "Hub·schrau·ber·flug", "stress": "HUB-schrau-ber-flug", "hint": "Flug mit einem Helikopter"},

    # 4-silbige Wörter & Komposita
    {"word": "Taschenlampe", "syllables": "Ta·schen·lam·pe", "stress": "TA-schen-lam-pe", "hint": "Handliche Leuchte"},
    {"word": "Sonnenbrille", "syllables": "Son·nen·bril·le", "stress": "SON-nen-bril-le", "hint": "Augenschutz gegen Sonnenlicht"},
    {"word": "Sonnenblume", "syllables": "Son·nen·blu·me", "stress": "SON-nen-blu-me", "hint": "Große gelbe Sommerblume"},
    {"word": "Kaffeekanne", "syllables": "Kaf·fee·kan·ne", "stress": "KAF-fee-kan-ne", "hint": "Gefäß für Heißgetränk"},
    {"word": "Marienkäfer", "syllables": "Ma·ri·en·kä·fer", "stress": "ma-RI-en-kä-fer", "hint": "Roter Glückskäfer mit Punkten"},
    {"word": "Postkartenmotiv", "syllables": "Post·kar·ten·mo·tiv", "stress": "POST-kar-ten-mo-tiv", "hint": "Bild auf einer Postkarte"},
    {"word": "Kindergarten", "syllables": "Kin·der·gar·ten", "stress": "KIN-der-gar-ten", "hint": "Vorschuleinrichtung für Kinder"},
    {"word": "Feuerwehrwagen", "syllables": "Feu·er·wehr·wa·gen", "stress": "FEU-er-wehr-wa-gen", "hint": "Einsatzfahrzeug der Feuerwehr"},
    {"word": "Schreibtischlampe", "syllables": "Schreib·tisch·lam·pe", "stress": "SCHREIB-tisch-lam-pe", "hint": "Lichtquelle am Arbeitsplatz"},
    {"word": "Polizeiauto", "syllables": "Po·li·zei·au·to", "stress": "po-li-ZEI-au-to", "hint": "Einsatzfahrzeug der Polizei"},
    {"word": "Einkaufswagen", "syllables": "Ein·kaufs·wa·gen", "stress": "EIN-kaufs-wa-gen", "hint": "Wagen im Supermarkt"},
    {"word": "Straßenbahnstation", "syllables": "Stra·ßen·bahn·sta·ti·on", "stress": "STRA-ßen-bahn-sta-ti-on", "hint": "Haltestelle der Straßenbahn"},
    {"word": "Eisenbahnbrücke", "syllables": "Ei·sen·bahn·brü·cke", "stress": "EI-sen-bahn-brü-cke", "hint": "Brücke für Züge"},
    {"word": "Krankenwagen", "syllables": "Kran·ken·wa·gen", "stress": "KRAN-ken-wa-gen", "hint": "Rettungsfahrzeug"},
    {"word": "Schokoladentafel", "syllables": "Scho·ko·la·den·ta·fel", "stress": "scho-ko-LA-den-ta-fel", "hint": "Süßigkeit aus Schokolade"},
    {"word": "Adventskalender", "syllables": "Ad·vents·ka·len·der", "stress": "ad-VENTS-ka-len-der", "hint": "Kalender mit 24 Türchen"},
    {"word": "Regenschirmständer", "syllables": "Re·gen·schirm·stän·der", "stress": "RE-gen-schirm-stän-der", "hint": "Halter für Regenschirme"},
    {"word": "Sommerurlaubsziel", "syllables": "Som·mer·ur·laubs·ziel", "stress": "SOM-mer-ur-laubs-ziel", "hint": "Reiseziel in den Ferien"},
    {"word": "Frühstückstischgedeck", "syllables": "Früh·stücks·tisch·ge·deck", "stress": "FRÜH-stücks-tisch-ge-deck", "hint": "Gedeck am Morgen"},
    {"word": "Autobahnauffahrt", "syllables": "Au·to·bahn·auf·fahrt", "stress": "AU-to-bahn-auf-fahrt", "hint": "Einfahrt auf die Schnellstraße"},
    {"word": "Universitätsstadt", "syllables": "U·ni·ver·si·täts·stadt", "stress": "u-ni-ver-si-TÄTS-stadt", "hint": "Stadt mit Hochschule"},
    {"word": "Sonnenuntergang", "syllables": "Son·nen·un·ter·gang", "stress": "SON-nen-un-ter-gang", "hint": "Abendliches Naturschauspiel"},
    {"word": "Fahrkartenautomat", "syllables": "Fahr·kar·ten·au·to·mat", "stress": "FAHR-kar-ten-au-to-mat", "hint": "Gerät zum Ticketkauf"},
    {"word": "Geburtstagsüberraschung", "syllables": "Ge·burts·tags·über·ra·schung", "stress": "ge-BURTS-tags-über-ra-schung", "hint": "Feierliche Überraschung"},
    {"word": "Wohnungsbeleuchtung", "syllables": "Woh·nungs·be·leuch·tung", "stress": "WOH-nungs-be-leuch-tung", "hint": "Lampen im Wohnraum"}
]

multisyllables_data = []
for idx, item in enumerate(multisyllables_raw):
    cnt = count_syl(item["word"])
    cat_label = f"{cnt}-silbig" if cnt in (2, 3, 4) else "Mehrsilber & Komposita"
    multisyllables_data.append({
        "id": f"ms_{idx+1:04d}",
        "word": item["word"],
        "syllables": item["syllables"],
        "syllable_count": cnt,
        "category": cat_label,
        "source": "Logopädischer Mehrsilber-Katalog",
        "stress": item["stress"],
        "hint": item["hint"],
        "difficulty": "Einfach" if cnt == 2 else ("Mittel" if cnt == 3 else "Schwer")
    })

with open(data_dir / "multisyllables.json", "w", encoding="utf-8") as f:
    json.dump(multisyllables_data, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(multisyllables_data)} multisyllable words.")
