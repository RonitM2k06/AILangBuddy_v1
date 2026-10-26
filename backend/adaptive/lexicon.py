"""A small, hand-written lexicon for the deterministic semantic grader. It exists ONLY for languages listed in SUPPORTED (Hindi and Marathi,
each in romanised and Devanagari form, Kannada, Tamil, Bengali, Telugu, Urdu, Kashmiri and Dogri, each romanised and in its own script, and French, in Roman letters with or without its accents). For any other language the grader reports "unsupported" and roleplay falls back to exact matching, so
nothing is ever guessed for a language this module knows nothing about. Each language has its own lexicon (`for_language`): Marathi words are
never matched with Hindi rules, or the other way round.

Three things live here: words that carry no meaning of their own for matching (function words and polite address), spelling
canonicalisation, and groups of words that mean the same thing. Everything is plain data: change a list and the tests that pin it change."""
import re
import unicodedata

SUPPORTED = {"hi", "mr", "kn", "ta", "fr", "bn", "te", "ur", "ks", "doi"}

# Words ignored on both sides of the comparison: auxiliaries, postpositions, polite address and plain pronouns.
STOP_ROMAN = {"hai", "hain", "ho", "hoon", "hun", "hu", "tha", "thi", "the", "hoga", "hogi", "honge", "hongi", "ka", "ki", "ke", "ko", "se", "mein", "me", "ne", "par",
              "pe", "to", "bhi", "ji", "na", "please", "plz", "main", "mai", "mujhe", "hum", "bhaiya", "bhai", "bhaiyya", "uncle", "aunty", "sir", "madam", "beta", "didi"}
STOP_DEVA = {"है", "हैं", "हो", "हूँ", "हूं", "था", "थी", "थे", "होगा", "होगी", "होंगे", "का", "की", "के", "को", "से", "में", "ने", "पर", "भी", "जी", "तो", "ना",
             "प्लीज", "मैं", "मुझे", "हम", "भैया", "भाई", "अंकल", "आंटी", "बेटा", "दीदी"}

# Groups of words with the same meaning (raw spellings; canonicalised below).
GROUPS_ROMAN = [
    ("kahan", "kahaan", "kaha", "kidhar"), ("kitna", "kitne", "kitni"), ("yeh", "yah", "ye"),
    ("chalo", "chaliye", "chaloge", "chalenge", "chalega", "jao", "jaoge", "jaiye", "jana", "jaana", "jaaiye", "jayenge"),
    ("paise", "paisa", "rupaye", "rupees", "rupay"), ("paas", "nazdeek", "nazdik"), ("door", "dur"), ("dena", "dijiye", "dijie", "do", "dedo", "de"),
    ("rok", "roko", "rokiye", "rukiye"), ("bhool", "bhula", "kho"), ("theek", "thik", "achha", "accha", "acha"), ("daam", "dam", "keemat", "kimat", "bhav"),
    ("namaste", "namaskar"), ("station", "stesan", "stn"), ("shukriya", "dhanyavaad", "dhanyavad"), ("haan", "han"), ("nahi", "nahin"),
]
GROUPS_DEVA = [("कहाँ", "कहां", "किधर"), ("कितने", "कितना", "कितनी"), ("यह", "ये"), ("पैसे", "रुपये", "रूपये"), ("पास", "नज़दीक", "नजदीक"), ("चलो", "चलिए", "चलोगे", "जाओ", "जाइए")]

_DEVANAGARI = range(0x0900, 0x0980)
_VOWELS = (("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"))


_KANNADA = range(0x0C80, 0x0D00)
_TAMIL = range(0x0B80, 0x0C00)


def has_devanagari(text):
    return any(ord(ch) in _DEVANAGARI and unicodedata.category(ch)[0] in ("L", "M") for ch in text)


def has_kannada(text):
    return any(ord(ch) in _KANNADA and unicodedata.category(ch)[0] in ("L", "M") for ch in text)


def has_tamil(text):
    return any(ord(ch) in _TAMIL and unicodedata.category(ch)[0] in ("L", "M") for ch in text)


def canon_roman(token):
    """Collapses the common romanisation variants of one word to one form: long vowels, doubled letters, w/v, a trailing 'h'."""
    t = token.casefold().replace("w", "v")
    for a, b in _VOWELS:
        t = t.replace(a, b)
    t = re.sub(r"(.)\1+", r"\1", t)
    if len(t) > 3 and t[-1] == "h" and t[-2] in "ae":
        t = t[:-1]
    return t


def canon_deva(token):
    t = unicodedata.normalize("NFKC", token).replace("ँ", "ं").replace("़", "")
    return t.replace("ी", "ि").replace("ू", "ु")


def _index(groups, canon):
    out = {}
    for i, g in enumerate(groups):
        for w in g:
            out[canon(w)] = i
    return out


GROUP_ROMAN = _index(GROUPS_ROMAN, canon_roman)
GROUP_DEVA = _index(GROUPS_DEVA, canon_deva)
STOP_ROMAN_CANON = {canon_roman(w) for w in STOP_ROMAN}
STOP_DEVA_CANON = {canon_deva(w) for w in STOP_DEVA}


# ---------------------------------------------------------------- Marathi
# Romanised Marathi is written many ways. Beyond the shared rules above (long vowels, doubled letters, w/v, a final h), these are folded:
# "zh"/"jh"/"z" -> "j" (zhale, jhale, zale), so the same word typed three ways is one word. Documented in docs/ARCHITECTURE.md section 34.
STOP_ROMAN_MR = {"aahe", "aahet", "aahat", "aahes", "ka", "la", "na", "re", "ga", "tar", "aani", "pan", "hota", "hote", "hoti", "please", "plz", "mi",
                 "mala", "aamhi", "aapan", "tumhi", "tu", "dada", "kaka", "kaku", "tai", "bhau", "bala", "ji", "sir", "madam"}
STOP_DEVA_MR = {"आहे", "आहेत", "आहात", "आहेस", "का", "ला", "ना", "रे", "ग", "तर", "आणि", "पण", "होता", "होते", "होती", "प्लीज", "मी", "मला", "आम्ही",
                "आपण", "तुम्ही", "तू", "दादा", "काका", "काकू", "ताई", "भाऊ", "बाळा"}
GROUPS_ROMAN_MR = [
    ("kuthe", "kute", "kutha"), ("kiti", "kitti"), ("dya", "de", "dyaa"), ("sanga", "sang", "saanga"), ("chala", "chal"), ("bara", "theek", "thik", "ok", "okay"),
    ("ho", "hoy"), ("nahi", "nahin"), ("nako", "naka"), ("pahije", "hava", "havi", "have"), ("dhanyavaad", "dhanyavad", "aabhaar", "abhar", "thanks", "thank"),
    ("namaskar", "namaste"), ("station", "steshan", "stesan", "stn"), ("paani", "pani"), ("zhale", "zhala", "zhali"), ("kay", "kaay", "kai"),
    ("mahaag", "mahag", "mahaga"), ("swasta", "svasta", "swast"), ("changla", "changli", "changle"), ("aavadta", "aavadte", "aavadto"),
    ("yenar", "yenaar"), ("jaaycha", "jaycha", "jayacha", "jaaicha"),
]
GROUPS_DEVA_MR = [("कुठे", "कुठं"), ("द्या", "दे"), ("सांगा", "सांग"), ("चला", "चल"), ("बरं", "बर", "ठीक"), ("हवं", "हवा", "हवी", "हवे", "पाहिजे"),
                  ("धन्यवाद", "आभार"), ("झाले", "झालं", "झाला", "झाली"), ("आवडतं", "आवडते", "आवडतो"), ("चांगला", "चांगली", "चांगले")]


def canon_roman_mr(token):
    t = canon_roman(token)
    return t.replace("zh", "j").replace("jh", "j").replace("z", "j")


def canon_deva_mr(token):
    return canon_deva(token)


# ---------------------------------------------------------------- Kannada
# Romanised Kannada is written many ways too. Beyond the shared rules (long vowels, doubled letters, w/v, a final h), "th" -> "t" and
# "dh" -> "d" (thumba / tumba) and "ai" -> "ay" (aithu / aytu) are folded. In Kannada script the long vowel signs fold into the short ones
# (as Hindi's do) and the zero-width non-joiner of loanwords (ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ) is dropped. Documented in docs/ARCHITECTURE.md section 38.
STOP_ROMAN_KN = {"please", "plz", "ri", "sir", "madam", "anna", "akka", "guru", "maga", "naanu", "neevu", "nanage", "nimage", "swalpa"}
STOP_KN = {"ಪ್ಲೀಸ್", "ರೀ", "ಸರ್", "ಮೇಡಂ", "ಅಣ್ಣ", "ಅಕ್ಕ", "ಗುರು", "ಮಗ", "ನಾನು", "ನೀವು", "ನನಗೆ", "ನಿಮಗೆ", "ಸ್ವಲ್ಪ"}
GROUPS_ROMAN_KN = [
    ("eshtu", "estu", "yeshtu", "yestu"), ("ellide", "yellide", "elide"), ("elli", "yelli"), ("kodi", "kodu", "kodri"), ("maadi", "madi", "maadu", "maadri"),
    ("haudu", "howdu", "houdu"), ("illa", "ilaa"), ("sari", "ok", "okay"), ("dhanyavaadagalu", "dhanyavaada", "dhanyavada", "thanks", "thank"),
    ("namaskara", "namaskaara", "namaste", "namaskar"), ("tumba", "thumba"), ("jaasti", "jasti", "jaasthi"), ("aaytu", "aithu", "aytu", "aitu", "aaithu"),
    ("aagutta", "agutta", "aagatta", "aagutha"), ("aagutte", "agutte", "aagatte", "aaguthe"), ("ideya", "idya", "ideyaa"), ("beku", "beko"), ("beda", "bedaa"),
    ("heli", "helu", "helri"), ("hogi", "hogu", "hogri"),
]
GROUPS_KN = [("ಕೊಡಿ", "ಕೊಡು"), ("ಮಾಡಿ", "ಮಾಡು"), ("ಹೇಳಿ", "ಹೇಳು"), ("ಹೋಗಿ", "ಹೋಗು"), ("ಧನ್ಯವಾದಗಳು", "ಧನ್ಯವಾದ"), ("ಆಯ್ತು", "ಆಯಿತು")]
_KN_LONG = (("\u0CC0", "\u0CBF"), ("\u0CC2", "\u0CC1"), ("\u0CC7", "\u0CC6"), ("\u0CCB", "\u0CCA"), ("\u0CC4", "\u0CC3"))


def canon_roman_kn(token):
    t = token.casefold().replace("th", "t").replace("dh", "d").replace("ai", "ay")
    return canon_roman(t)


def drop_joiners(text):
    """Kannada script writes loanwords with a zero-width non-joiner (ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ) that learners rarely type: dropped before the text is split."""
    return text.replace("\u200c", "").replace("\u200d", "")


def canon_kannada(token):
    t = unicodedata.normalize("NFKC", token).replace("\u200c", "").replace("\u200d", "")
    for a, b in _KN_LONG:
        t = t.replace(a, b)
    return t


# ---------------------------------------------------------------- Tamil
# Spoken Chennai Tamil, romanised. Beyond the shared rules, "th" -> "t" and "dh" -> "d" (thanni / tanni, dhooram / dooram) are folded; "zh"
# (ழ) is NOT folded, because "mazhai" (rain) and "malai" (hill) are different words. In Tamil script the long vowel signs fold into the short
# ones and zero-width joiners are dropped. Documented in docs/ARCHITECTURE.md section 40.
STOP_ROMAN_TA = {"please", "plz", "sir", "madam", "anna", "akka", "machi", "machan", "naan", "neenga", "enakku", "ungalukku", "konjam", "dhaan", "nga"}
STOP_TA = {"ப்ளீஸ்", "சார்", "மேடம்", "அண்ணா", "அக்கா", "மச்சி", "நான்", "நீங்க", "எனக்கு", "உங்களுக்கு", "கொஞ்சம்", "தான்"}
GROUPS_ROMAN_TA = [
    ("evvalavu", "evlo", "evlavu", "evvalo", "evalavu"), ("enga", "enge"), ("kudunga", "kudu", "kodunga", "kodu"), ("pannunga", "pannu"), ("podunga", "podu"),
    ("sollunga", "sollu"), ("aamaa", "aama", "amam"), ("illa", "illai", "ille"), ("sari", "ok", "okay"), ("nandri", "nanri", "thanks", "thank"),
    ("vanakkam", "vanakam"), ("romba", "rombha"), ("adhigam", "athigam", "adhikam"), ("aachu", "achu", "aachchu"), ("irukkaa", "iruka", "irukka"),
    ("irukku", "iruku"), ("venum", "venumm", "vendum"), ("venaam", "vendaam", "vendam"), ("pogumaa", "poguma"),
]
GROUPS_TA = [("குடுங்க", "குடு", "கொடுங்க"), ("பண்ணுங்க", "பண்ணு"), ("சொல்லுங்க", "சொல்லு"), ("நன்றி", "தேங்க்ஸ்"), ("ஆச்சு", "ஆயிற்று")]
_TA_LONG = (("\u0BC0", "\u0BBF"), ("\u0BC2", "\u0BC1"), ("\u0BC7", "\u0BC6"), ("\u0BCB", "\u0BCA"))


def canon_roman_ta(token):
    return canon_roman(token.casefold().replace("th", "t").replace("dh", "d"))


def canon_tamil(token):
    t = unicodedata.normalize("NFKC", token).replace("\u200c", "").replace("\u200d", "")
    for a, b in _TA_LONG:
        t = t.replace(a, b)
    return t


# ---------------------------------------------------------------- Bengali
# Spoken Kolkata Bengali, romanised. Beyond the shared rules, "chh" -> "ch", "sh" -> "s", "th" -> "t" and "dh" -> "d" are folded (achhe / ache,
# shoja / soja, thik / tik, dhonnobad / donnobad): learners and Kolkata speakers write each both ways. "Na" (no, not) is NOT a stop word, because
# "debo na" (won't give) is not "debo" (will give). In Bengali script the long vowel signs fold into the short ones, the nukta (য় / য়) and
# zero-width joiners are dropped. Documented in docs/ARCHITECTURE.md section 44.
STOP_ROMAN_BN = {"please", "plz", "sir", "madam", "dada", "didi", "mashima", "kaku", "ami", "apni", "tumi", "amar", "apnar", "ektu", "to", "re"}
STOP_BN = {"প্লিজ", "স্যার", "ম্যাডাম", "দাদা", "দিদি", "মাসিমা", "কাকু", "আমি", "আপনি", "তুমি", "আমার", "আপনার", "একটু", "তো"}
GROUPS_ROMAN_BN = [
    ("koto", "kato", "kot"), ("kothay", "kothai", "kotay", "kotai"), ("din", "dao", "dio", "den"), ("korun", "koro", "koren", "koriye"),
    ("bolun", "bolo", "bolen"), ("hyan", "haan", "han", "ha", "hya", "yes"), ("thik", "theek", "ok", "okay"),
    ("dhonnobad", "dhonyobad", "dhanyabad", "dhanyavad", "thanks", "thank"), ("nomoshkar", "nomoskar", "namaskar", "namaste"),
    ("khub", "khoob"), ("beshi", "besi", "bashi"), ("achhe", "ache"), ("achhen", "achen"), ("lagbe", "laagbe"), ("holo", "hol", "hoilo"),
    ("shoja", "soja", "sojha"), ("aste", "asthe"), ("jaben", "jaaben", "jabe"), ("thamun", "thamo", "thaman"), ("cholun", "cholo", "chalun", "chalo"),
    ("darun", "daroon"),
]
GROUPS_BN = [("দিন", "দাও"), ("করুন", "করো"), ("বলুন", "বলো"), ("ধন্যবাদ", "থ্যাংকস"), ("হ্যাঁ", "হাঁ"), ("চলুন", "চলো")]
_BN_LONG = (("ী", "ি"), ("ূ", "ু"))
_BENGALI = range(0x0980, 0x0A00)


def has_bengali(text):
    return any(ord(ch) in _BENGALI and unicodedata.category(ch)[0] in ("L", "M") for ch in text)


def canon_roman_bn(token):
    t = token.casefold().replace("chh", "ch").replace("sh", "s").replace("th", "t").replace("dh", "d")
    return canon_roman(t)


def canon_bengali(token):
    t = unicodedata.normalize("NFKC", token).replace("‌", "").replace("‍", "").replace("়", "")
    for a, b in _BN_LONG:
        t = t.replace(a, b)
    return t


# ---------------------------------------------------------------- Telugu
# Spoken Hyderabad Telugu, romanised. Beyond the shared rules, "th" -> "t" and "dh" -> "d" (entha / enta, dhanyavaadaalu / danyavaadaalu) are
# folded, as for Kannada and Tamil. In Telugu script the long vowel signs fold into the short ones and zero-width joiners (అమీర్‌పేట్) are
# dropped. Documented in docs/ARCHITECTURE.md section 45.
STOP_ROMAN_TE = {"please", "plz", "sir", "madam", "anna", "akka", "garu", "andi", "nenu", "meeru", "naaku", "meeku", "konchem"}
STOP_TE = {"ప్లీజ్", "సార్", "మేడం", "అన్న", "అక్క", "గారు", "అండి", "నేను", "మీరు", "నాకు", "మీకు", "కొంచెం"}
GROUPS_ROMAN_TE = [
    ("entha", "yentha", "enta"), ("ekkada", "yekkada", "ekkda"), ("ivvandi", "ivvu", "ivandi"), ("cheyandi", "cheyyi", "cheyyandi"),
    ("cheppandi", "cheppu"), ("avunu", "avnu", "avunandi", "yes"), ("ledu", "ledhu", "ledandi"), ("sare", "sari", "ok", "okay"),
    ("dhanyavaadaalu", "dhanyavaadalu", "dhanyavadalu", "thanks", "thank"), ("namaskaram", "namaskaaram", "namaste"), ("chaala", "chala"),
    ("ekkuva", "ekuva"), ("undaa", "unda"), ("undi", "undhi"), ("vastaaraa", "vastara", "vasthara", "vastaara"), ("kaavaali", "kavali"),
    ("vaddu", "vadhu", "vaddandi"), ("takkuva", "thakkuva"), ("aapandi", "aapu", "apandi"),
]
GROUPS_TE = [("ఇవ్వండి", "ఇవ్వు"), ("చేయండి", "చెయ్యి"), ("చెప్పండి", "చెప్పు"), ("ధన్యవాదాలు", "థాంక్స్"), ("ఆపండి", "ఆపు")]
_TE_LONG = (("ీ", "ి"), ("ూ", "ు"), ("ే", "ె"), ("ో", "ొ"))
_TELUGU = range(0x0C00, 0x0C80)


def has_telugu(text):
    return any(ord(ch) in _TELUGU and unicodedata.category(ch)[0] in ("L", "M") for ch in text)


def canon_roman_te(token):
    return canon_roman(token.casefold().replace("th", "t").replace("dh", "d"))


def canon_telugu(token):
    t = unicodedata.normalize("NFKC", token).replace("‌", "").replace("‍", "")
    for a, b in _TE_LONG:
        t = t.replace(a, b)
    return t


# ---------------------------------------------------------------- Urdu
# Hyderabadi Urdu. Romanised, it is written like romanised Hindi, so the Hindi rules apply (the same shared canonicalisation, function words
# and same-meaning groups), with Hyderabad's own words added ("hau" = yes, "nakko" = no). In Urdu script, letters typed from Arabic keyboards
# fold into their Urdu forms (ي -> ی, ك -> ک, ه -> ہ), the vowel marks (zer, zabar, pesh...) are dropped, and zero-width joiners too.
# Documented in docs/ARCHITECTURE.md section 45.
STOP_ROMAN_UR = STOP_ROMAN | {"re", "sahab"}
STOP_UR = {"ہے", "ہیں", "ہو", "ہوں", "تھا", "تھی", "تھے", "کا", "کی", "کے", "کو", "سے", "میں", "نے", "پر", "بھی", "جی", "تو", "نا", "مجھے", "ہم",
           "بھائی", "صاحب"}
GROUPS_ROMAN_UR = GROUPS_ROMAN + [("hau", "haan", "han"), ("nakko", "nahi", "nahin", "mat"), ("idhar", "yahan"), ("udhar", "wahan"),
                                  ("shukriya", "dhanyavaad", "thanks", "thank"), ("aadaab", "salaam", "assalaam")]
GROUPS_UR = [("کہاں", "کدھر"), ("کتنے", "کتنا", "کتنی"), ("شکریہ", "تھینکس"), ("ہاں", "ہاؤ"), ("نہیں", "نکو")]
_UR_FOLD = (("ي", "ی"), ("ى", "ی"), ("ك", "ک"), ("ه", "ہ"))
_URDU = list(range(0x0600, 0x0700)) + list(range(0x0750, 0x0780))
_UR_MARKS = set(range(0x064B, 0x0653)) | {0x0670}


def has_urdu(text):
    return any(ord(ch) in _URDU and unicodedata.category(ch)[0] in ("L", "M") for ch in text)


def canon_urdu(token):
    t = unicodedata.normalize("NFKC", token).replace("‌", "").replace("‍", "")
    t = "".join(ch for ch in t if ord(ch) not in _UR_MARKS)
    for a, b in _UR_FOLD:
        t = t.replace(a, b)
    return t


# ---------------------------------------------------------------- Kashmiri (draft)
# Kashmiri, romanised as learners type it, and in its Perso-Arabic script. Romanised: the shared rules. Script: the Urdu folding (Arabic-keyboard
# letters, joiners) and every vowel sign dropped, Kashmiri's own included, so a learner who leaves them out still matches. "Na" (no, not) is not a
# stop word. Documented in docs/ARCHITECTURE.md section 47.
STOP_ROMAN_KS = {"please", "plz", "sir", "madam", "baya", "beni", "sahab", "bu", "me", "tuhi", "myon", "chhu", "chhe", "chhus", "chhes", "chhiv"}
STOP_KS = {"بہٕ", "مےٚ", "تُہۍ", "چھُ", "چھےٚ"}
GROUPS_ROMAN_KS = [("kotah", "kota", "kotaah"), ("kati", "kot", "katy"), ("diyiv", "di", "dyiv"), ("kariv", "kar", "koriv"), ("vaniv", "van"),
                   ("shukriya", "shukria", "thanks", "thank"), ("vaariyah", "vaariya", "variya", "vaaryah"), ("aa", "haan", "yes"),
                   ("vaaray", "varay", "vaarai", "waarai"), ("theek", "thik", "ok", "okay"), ("chha", "chhaa"), ("gatshiv", "gatsiv", "gachhiv")]
_KS_MARKS = set(range(0x064B, 0x0660)) | {0x0670}


def canon_kashmiri(token):
    t = canon_urdu(token)
    return "".join(ch for ch in t if ord(ch) not in _KS_MARKS)


# ---------------------------------------------------------------- Dogri (draft)
# Dogri, romanised and in Devanagari. The shared romanisation rules and Hindi's Devanagari folding apply, with Dogri's own function words
# ("ai" is, "aan" am, "o" are, "da/di/de" of, "ch" in) and same-meaning groups. Documented in docs/ARCHITECTURE.md section 47.
STOP_ROMAN_DOI = {"ai", "aan", "o", "ji", "tus", "da", "di", "de", "ch", "bi", "main", "migi", "please", "plz", "bhau"}
STOP_DOI = {"ऐ", "आं", "ओ", "जी", "तुस", "दा", "दी", "दे", "च", "बी", "मैं", "मिगी"}
GROUPS_ROMAN_DOI = [("kutthen", "kuthe", "kithe", "kutthe"), ("kitne", "kinne", "kitna"), ("deo", "dao", "do", "dena"), ("ghatt", "ghat", "kam"),
                    ("dhannvaad", "dhanvaad", "dhanyavaad", "shukriya", "thanks", "thank"), ("haan", "han", "yes"), ("theek", "thik", "ok", "okay"),
                    ("phi", "fhi", "phir"), ("itthen", "ithe", "itthe"), ("namaste", "namaskar"), ("chaah", "chaa", "chai")]
GROUPS_DOI = [("कुत्थें", "कुत्थे"), ("देओ", "दओ"), ("धन्नवाद", "धन्यवाद")]


# ---------------------------------------------------------------- French
# French is written in Roman letters: every text is compared as "romanised", with its accents folded away (café / cafe, très / tres) and
# the case ignored. Apostrophes split words (s'il -> s il), as normalisation turns punctuation into spaces. Documented in ARCHITECTURE.md 42.
STOP_ROMAN_FR = {"s", "il", "vous", "plait", "je", "j", "le", "la", "les", "l", "un", "une", "des", "de", "du", "d", "c", "ce", "est", "a", "et",
                 "madame", "monsieur", "please", "plz", "tu", "on", "y", "en", "excusez", "excuse", "moi", "pardon", "bien", "sur"}
GROUPS_ROMAN_FR = [
    ("bonjour", "salut", "bonsoir", "hello"), ("merci", "thanks", "thank"), ("velo", "bicyclette", "bike"), ("addition", "note", "bill"),
    ("cafe", "coffee", "kawa"), ("oui", "ouais", "yes"), ("accord", "ok", "okay"), ("combien", "prix"), ("ou", "where"), ("casque", "helmet"),
]


def canon_roman_fr(token):
    t = unicodedata.normalize("NFD", token.casefold())
    return "".join(ch for ch in t if unicodedata.category(ch) != "Mn")


def _never(text):
    return False


class Lexicon:
    """One language's words for the semantic grader: canonicalisation, function words and same-meaning groups, for its romanised form and
    its own script (Devanagari for Hindi and Marathi, Kannada script for Kannada). The `*_deva` names mean "the language's own script"."""

    def __init__(self, canon_roman_fn, canon_deva_fn, stop_roman, stop_deva, groups_roman, groups_deva, native=has_devanagari, prepare=None):
        self.native = native                                    # does a text use this language's own script?
        self.prepare = prepare or (lambda text: text)           # applied to a whole text before it is split into words
        self.canon_roman, self.canon_deva = canon_roman_fn, canon_deva_fn
        self.stop_roman, self.stop_deva = {canon_roman_fn(w) for w in stop_roman}, {canon_deva_fn(w) for w in stop_deva}
        self.group_roman, self.group_deva = _index(groups_roman, canon_roman_fn), _index(groups_deva, canon_deva_fn)


LEXICONS = {
    "hi": Lexicon(canon_roman, canon_deva, STOP_ROMAN, STOP_DEVA, GROUPS_ROMAN, GROUPS_DEVA),
    "mr": Lexicon(canon_roman_mr, canon_deva_mr, STOP_ROMAN_MR, STOP_DEVA_MR, GROUPS_ROMAN_MR, GROUPS_DEVA_MR),
    "kn": Lexicon(canon_roman_kn, canon_kannada, STOP_ROMAN_KN, STOP_KN, GROUPS_ROMAN_KN, GROUPS_KN, native=has_kannada, prepare=drop_joiners),
    "ta": Lexicon(canon_roman_ta, canon_tamil, STOP_ROMAN_TA, STOP_TA, GROUPS_ROMAN_TA, GROUPS_TA, native=has_tamil, prepare=drop_joiners),
    "fr": Lexicon(canon_roman_fr, canon_roman_fr, STOP_ROMAN_FR, set(), GROUPS_ROMAN_FR, [], native=_never),
    "bn": Lexicon(canon_roman_bn, canon_bengali, STOP_ROMAN_BN, STOP_BN, GROUPS_ROMAN_BN, GROUPS_BN, native=has_bengali, prepare=drop_joiners),
    "te": Lexicon(canon_roman_te, canon_telugu, STOP_ROMAN_TE, STOP_TE, GROUPS_ROMAN_TE, GROUPS_TE, native=has_telugu, prepare=drop_joiners),
    "ur": Lexicon(canon_roman, canon_urdu, STOP_ROMAN_UR, STOP_UR, GROUPS_ROMAN_UR, GROUPS_UR, native=has_urdu, prepare=drop_joiners),
    "ks": Lexicon(canon_roman, canon_kashmiri, STOP_ROMAN_KS, STOP_KS, GROUPS_ROMAN_KS, [], native=has_urdu, prepare=drop_joiners),
    "doi": Lexicon(canon_roman, canon_deva, STOP_ROMAN_DOI, STOP_DOI, GROUPS_ROMAN_DOI, GROUPS_DOI),
}


def for_language(code):
    """The lexicon of a supported language, or None."""
    return LEXICONS.get(code)
