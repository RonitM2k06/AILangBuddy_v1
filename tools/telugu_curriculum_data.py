"""The Telugu curriculum (A1): data only (tools/gen_telugu_curriculum.py turns it into migration SQL).

The 7 First Week lessons take their phrases from the Hyderabad pack (frontend/content.js PACKS.hyderabad); this file adds what the pack does
not have: their words, exercises and grammar notes, two more A1 lessons, the situations (server roleplays) and their steps. Every phrase is
(Telugu script, romanised, literal English, natural English). Telugu verbs for "I" and "you" do not change for gender, so no phrase has a
feminine form. The romanisation follows the pack: spoken Hyderabad Telugu, no diacritics, long vowels doubled (aa, ee, oo).
Written by the LingoBuddy team with an AI-assisted editorial pass; NOT reviewed by a native speaker (docs/CONTENT_REVIEW.md)."""

# ------------------------------------------------------------------------------------------------------------------------------------
# What the First Week lessons add to the pack's phrases: words (each with an example phrase of the lesson) and exercises
# (what a phrase means, translate a phrase, fill in a word).
# ------------------------------------------------------------------------------------------------------------------------------------
FIRST_WEEK = {
    "greetings": {"description": "Greet people politely and introduce yourself in Telugu.",
                  "words": [("పేరు", "Peru", "Name", "నా పేరు అలెక్స్."), ("కొత్త", "Kotta", "New", "నేను ఇక్కడ కొత్త.")],
                  "exercises": ("Namaskaram! Baagunnaara?", "Chaala dhanyavaadaalu!", ("Naa peru Alex.", "peru"))},
    "transport": {"description": "Take autos and the Hyderabad Metro.",
                  "words": [("మీటర్", "Meter", "Meter (in an auto)", "మీటర్ వేయండి."), ("ఎక్కడ", "Ekkada", "Where", "మెట్రో స్టేషన్ ఎక్కడ?")],
                  "exercises": ("Meter veyandi.", "Ikkada aapandi.", ("Entha avutundi?", "entha"))},
    "food": {"description": "Order Hyderabadi biryani and an Irani chai.",
             "words": [("కారం", "Kaaram", "Chilli-hot, spicy", "కారం తక్కువ వేయండి."), ("నీళ్ళు", "Neellu", "Water", "మంచి నీళ్ళు ఇవ్వండి.")],
             "exercises": ("Kaaram takkuva veyandi.", "Oka plate biryani ivvandi.", ("Manchi neellu ivvandi.", "neellu"))},
    "shopping": {"description": "Ask prices and colours, and bargain where it's normal.",
                 "words": [("రంగు", "Rangu", "Colour", "వేరే రంగు ఉందా?"), ("ఎక్కువ", "Ekkuva", "Too much, more", "చాలా ఎక్కువ.")],
                 "exercises": ("Vere rangu undaa?", "Idi entha?", ("Konchem thagginchandi.", "thagginchandi"))},
    "directions": {"description": "Find your way, a pharmacy and the metro, and ask people to slow down.",
                   "words": [("కుడి", "Kudi", "Right (direction)", "నేరుగా వెళ్ళి, కుడి వైపు తిరగండి."), ("దగ్గర", "Daggara", "Near", "దగ్గరలో మెడికల్ షాప్ ఉందా?")],
                   "exercises": ("Nadichi velthe entha sepu?", "Chowmahalla Palace ekkada?", ("Neruga velli, kudi vaipu tiragandi.", "kudi"))},
    "college": {"description": "Settle in with colleagues and classmates.", "ages": ("teen", "adult"),
                "words": [("రోజు", "Roju", "Day", "ఈ రోజు నా మొదటి రోజు."), ("సహాయం", "Sahaayam", "Help", "కొంచెం సహాయం చేస్తారా?")],
                "exercises": ("Konchem sahaayam chestaaraa?", "Canteen ekkada undi?", ("Malli kaluddaam!", "malli"))},
    "smalltalk": {"description": "Put everything together in a natural conversation.",
                  "words": [("వాతావరణం", "Vaatavaranam", "Weather", "హైదరాబాద్ వాతావరణం బాగుంది కదా?"), ("ఆదివారం", "Aadivaaram", "Sunday", "ఆదివారం గోల్కొండ కోటకి వెళ్దామా?")],
                  "exercises": ("Nuvvu ikkade puttaavaa?", "Traffic chaala ekkuva.", ("Aadivaaram Golconda kotaki veldaamaa?", "golconda"))},
}

# ------------------------------------------------------------------------------------------------------------------------------------
# A1, after the 7 First Week lessons (sort_order 8-9)
# ------------------------------------------------------------------------------------------------------------------------------------
A1_LESSONS = [
    {"slug": "numbers-money", "topic": "shopping", "title": "Numbers and Money", "description": "Count, pay and understand prices.",
     "situation": "Paying at a kirana shop in Ameerpet.",
     "tip": "Telugu numbers: okati, rendu, moodu, naalugu, aidu, aaru, edu, enimidi, tommidi, padi; vanda = 100, veyyi = 1000. Prices are often said in English or Hindi too, so listen for all three.",
     "phrases": [
         ("మొత్తం ఎంత అయింది?", "Mottam entha ayindi?", "Altogether how much did it become?", "How much is it altogether?"),
         ("వంద రూపాయలు.", "Vanda roopaayalu.", "Hundred rupees.", "A hundred rupees."),
         ("చిల్లర ఉందా?", "Chillara undaa?", "Change, is there?", "Do you have change?"),
         ("యాభై నోటు చెల్లుతుందా?", "Yaabhai notu chellutundaa?", "Will a fifty note work?", "Is a fifty-rupee note okay?"),
         ("బిల్ ఇవ్వండి.", "Bill ivvandi.", "The bill please give.", "Can I have the bill, please?"),
     ],
     "words": [("వంద", "Vanda", "Hundred", "వంద రూపాయలు."), ("చిల్లర", "Chillara", "Change (coins and small notes)", "చిల్లర ఉందా?")],
     "exercises": ("Chillara undaa?", "Vanda roopaayalu.", ("Mottam entha ayindi?", "mottam"))},
    {"slug": "help-health", "topic": "emergency", "title": "Help and Health", "description": "Ask for help, a doctor or a pharmacy.",
     "situation": "You feel unwell late at night in Gachibowli.",
     "tip": "India's emergency number is 112 (police, fire and ambulance). A pharmacy is a “medical shop” in Hyderabad, and many stay open late.",
     "phrases": [
         ("నాకు సహాయం కావాలి!", "Naaku sahaayam kaavaali!", "To me help is needed!", "I need help!"),
         ("దగ్గరలో హాస్పిటల్ ఎక్కడ?", "Daggaralo hospital ekkada?", "Nearby hospital where?", "Where's the nearest hospital?"),
         ("నాకు ఒంట్లో బాలేదు.", "Naaku ontlo baaledu.", "To me in the body it is not good.", "I don't feel well."),
         ("నాకు జ్వరం ఉంది.", "Naaku jvaram undi.", "To me there is fever.", "I have a fever."),
         ("మెడికల్ షాప్ తెరిచి ఉందా?", "Medical shop terichi undaa?", "Is the medical shop open?", "Is the pharmacy open?"),
         ("పోలీసులను పిలవండి!", "Poleesulanu pilavandi!", "Please call the police!", "Please call the police!"),
     ],
     "words": [("హాస్పిటల్", "Hospital", "Hospital", "దగ్గరలో హాస్పిటల్ ఎక్కడ?"), ("జ్వరం", "Jvaram", "Fever", "నాకు జ్వరం ఉంది.")],
     "exercises": ("Naaku ontlo baaledu.", "Poleesulanu pilavandi!", ("Daggaralo hospital ekkada?", "hospital"))},
]

GRAMMAR = [
    # (slug, level, title, explanation, example phrases, lesson slugs)
    ("polite-requests", "A1", "Polite requests: “ivvandi”, “cheyandi”, “cheppandi”",
     "Telugu asks politely with the “meeru” (you, polite) form, which ends in -andi: “ivvandi” (please give), “cheyandi” (please do), “cheppandi” "
     "(please say), “aapandi” (please stop). With friends the short form is used: “ivvu”, “cheyyi”, “cheppu”.",
     ["ఒక ప్లేట్ బిర్యానీ ఇవ్వండి.", "సరే, ప్యాక్ చేయండి.", "ఇక్కడ ఆపండి."], ["food", "shopping", "transport"]),
    ("yes-no-questions", "A1", "Yes-no questions: “-aa”",
     "Add -aa to a sentence to ask a yes-no question: “undi” (there is) becomes “undaa?” (is there?), “vastaaru” (you'll come) becomes "
     "“vastaaraa?” (will you come?).",
     ["వేరే రంగు ఉందా?", "బంజారా హిల్స్ వస్తారా?", "దగ్గరలో మెడికల్ షాప్ ఉందా?"], ["shopping", "transport", "directions"]),
    ("question-words", "A1", "Question words: “ekkada”, “entha”, “enni”",
     "Question words come at the end of the sentence: “Metro station ekkada?” (the metro station, where?), “Idi entha?” (this, how much?), "
     "“Meeting enni gantalaku?” (the meeting, at how many o'clock?).",
     ["మెట్రో స్టేషన్ ఎక్కడ?", "ఇది ఎంత?", "మీటింగ్ ఎన్ని గంటలకు?"], ["transport", "shopping", "college"]),
]

# ------------------------------------------------------------------------------------------------------------------------------------
# Situations (server roleplays): the 7 First Week roleplays and Help and Health. learn: lesson phrases (romanised); choose: the partner's
# opening line with options (the first is right); reply: the partner's answer with accepted replies; translate: optional.
# ------------------------------------------------------------------------------------------------------------------------------------
SITUATIONS = [
    {"slug": "greetings", "level": "A1", "topic": "greetings", "difficulty": 1, "title": "Meet your house owner",
     "description": "You've just rented a flat in Madhapur. Lakshmi garu, the house owner, comes to say hello.",
     "goal": "Greet politely, introduce yourself and say you're new.", "setting": "Your rented flat in Madhapur",
     "partner": ("Lakshmi garu", "House owner"),
     "learn": ["Namaskaram! Baagunnaara?", "Naa peru Alex.", "Chaala dhanyavaadaalu!"],
     "choose": ("Namaskaram! Meere kotta tenant aa? Nenu Lakshmi.", "Hello! Are you the new tenant? I'm Lakshmi.",
                ["Avunandi, nenu ikkada kotta.", "Oka Irani chai.", "Metro station ekkada?"]),
     "reply": ("Swaagatam! Emaina kaavaalante cheppandi.", "Welcome! Tell me if you need anything.", ["Chaala dhanyavaadaalu!", "Dhanyavaadaalu!", "Sare, dhanyavaadaalu."]),
     "translate": ("How would you say “Lovely to meet you” in Telugu?", "Mimmalni kalavadam santoshamga undi.")},
    {"slug": "transport", "level": "A1", "topic": "transport", "difficulty": 1, "title": "Auto to Banjara Hills",
     "description": "You need to get from Secunderabad station to Banjara Hills by auto.", "goal": "Get to Banjara Hills by the meter.",
     "setting": "Outside Secunderabad railway station", "partner": ("Srinu", "Auto driver"),
     "learn": ["Banjara Hills vastaaraa?", "Meter veyandi.", "Ikkada aapandi."],
     "choose": ("Ekkadiki vellaali?", "Where do you need to go?", ["Banjara Hills vastaaraa?", "Oka Irani chai.", "Naa peru Alex."]),
     "reply": ("Meter vestaanu, kaani iravai ekkuva ivvandi.", "I'll put the meter on, but give twenty extra.",
               ["Vaddu, meter maatrame.", "Sare, iravai ekkuva.", "Meter veyandi."])},
    {"slug": "food", "level": "A1", "topic": "food", "difficulty": 1, "title": "Biryani in the old city", "description": "Lunch at an Irani café in the old city.",
     "goal": "Order biryani and an Irani chai, ask for less chilli and pay.", "setting": "An Irani café in the old city", "partner": ("Raju", "Waiter"),
     "learn": ["Oka plate biryani ivvandi.", "Kaaram takkuva veyandi.", "Bill entha ayindi?"],
     "choose": ("Randi, emi kaavaali?", "Come in, what would you like?", ["Oka plate biryani ivvandi.", "Ikkada aapandi.", "Vere rangu undaa?"]),
     "reply": ("Biryani! Kaaram ekkuva kaavaalaa?", "Biryani! Do you want it extra spicy?", ["Kaaram takkuva veyandi.", "Vaddu, kaaram takkuva.", "Konchem kaaram chaalu."]),
     "translate": ("How would you say “One Irani chai, please” in Telugu?", "Oka Irani chai.")},
    {"slug": "shopping", "level": "A1", "topic": "shopping", "difficulty": 2, "title": "Bangles in Laad Bazaar", "description": "You're in Laad Bazaar, near the Charminar, looking for bangles.",
     "goal": "Buy a set of lac bangles at a fair price.", "setting": "Laad Bazaar, near the Charminar", "partner": ("Farida", "Shopkeeper"),
     "learn": ["Idi entha?", "Chaala ekkuva.", "Konchem thagginchandi."],
     "choose": ("Randi, chudandi! Kotta designs unnaayi.", "Come in, take a look! New designs.", ["Idi entha?", "Meter veyandi.", "Canteen ekkada undi?"]),
     "reply": ("Ee set aa? Veyyi rupaayalu maatrame!", "This set? Only a thousand rupees!", ["Chaala ekkuva.", "Konchem thagginchandi.", "Chivari dhara entha?"])},
    {"slug": "directions", "level": "A1", "topic": "directions", "difficulty": 2, "title": "Find Chowmahalla Palace", "description": "You're by the Charminar and want Chowmahalla Palace.",
     "goal": "Find the way to Chowmahalla Palace, and a pharmacy.", "setting": "By the Charminar", "partner": ("Venkat", "Passerby"),
     "learn": ["Chowmahalla Palace ekkada?", "Neruga velli, kudi vaipu tiragandi.", "Konchem nemmadiga cheppandi."],
     "choose": ("Emaina vetukutunnaaraa?", "Looking for something?", ["Chowmahalla Palace ekkada?", "Oka plate biryani ivvandi.", "Idi entha?"]),
     "reply": ("Neruga velli, kudi vaipu tiragandi. Mundu palace kanipistundi.", "Go straight, then turn right. You'll see the palace ahead.",
               ["Nadichi velthe entha sepu?", "Konchem nemmadiga cheppandi.", "Chaala dhanyavaadaalu!"])},
    {"slug": "college", "level": "A1", "topic": "college", "difficulty": 2, "title": "First day in HITEC City", "description": "Your first day at an office in HITEC City.",
     "goal": "Introduce yourself and find out about the meeting and the canteen.", "setting": "An office in HITEC City", "partner": ("Sneha", "Colleague"),
     "ages": ("teen", "adult"),
     "learn": ["Ee roju naa modati roju.", "Meeting enni gantalaku?", "Canteen ekkada undi?"],
     "choose": ("Hi! Meeru kotta joinee aa? Nenu Sneha.", "Hi! Are you the new joiner? I'm Sneha.", ["Avunu, ee roju naa modati roju.", "Meter veyandi.", "Bill entha ayindi?"]),
     "reply": ("Swaagatam! Team meeting padi gantalaku.", "Welcome! The team meeting is at ten.", ["Canteen ekkada undi?", "Konchem sahaayam chestaaraa?", "Sare, dhanyavaadaalu."])},
    {"slug": "smalltalk", "level": "A1", "topic": "smalltalk", "difficulty": 2, "title": "Sunset on Tank Bund", "description": "Sunset on Tank Bund, by Hussain Sagar, with Ravi, your flatmate.",
     "goal": "Chat about Hyderabad and make Sunday plans.", "setting": "Tank Bund at sunset", "partner": ("Ravi", "Flatmate"),
     "learn": ["Hyderabad vaatavaranam baagundi kadaa?", "Traffic chaala ekkuva.", "Aadivaaram Golconda kotaki veldaamaa?"],
     "choose": ("Ela undi Hyderabad?", "How's Hyderabad treating you?", ["Hyderabad vaatavaranam baagundi kadaa?", "Meter veyandi.", "Bill ivvandi."]),
     "reply": ("Avunu! Kaani varsham padite traffic inkaa ekkuva.", "Yes! But when it rains the traffic gets even worse.",
               ["Traffic chaala ekkuva.", "Aadivaaram Golconda kotaki veldaamaa?", "Super, pakka!"]),
     "translate": ("How would you say “Were you born here?” in Telugu?", "Nuvvu ikkade puttaavaa?")},
    {"slug": "help-health", "level": "A1", "topic": "emergency", "difficulty": 2, "title": "At the pharmacy late at night", "description": "You feel unwell late at night in Gachibowli.",
     "goal": "Say what is wrong and find out where the hospital is.", "setting": "A medical shop in Gachibowli", "partner": ("Suresh", "Pharmacist"),
     "learn": ["Naaku ontlo baaledu.", "Naaku jvaram undi.", "Daggaralo hospital ekkada?"],
     "choose": ("Randi, emaindi?", "Come in, what happened?", ["Naaku ontlo baaledu.", "Idi entha?", "Aadivaaram Golconda kotaki veldaamaa?"]),
     "reply": ("Jvaram undaa? Ee tablet veskondi. Ekkuva aithe hospital ki vellandi.", "Do you have a fever? Take this tablet. If it gets worse, go to the hospital.",
               ["Daggaralo hospital ekkada?", "Naaku jvaram undi.", "Chaala dhanyavaadaalu!"])},
]
