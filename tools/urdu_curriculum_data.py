"""The Urdu curriculum (A1): data only (tools/gen_urdu_curriculum.py turns it into migration SQL).

The 7 First Week lessons take their phrases from Hyderabad's Urdu pack (frontend/content.js LANGUAGE_PACKS.hyderabad.ur); this file adds what
the pack does not have: their words, exercises and grammar notes, two more A1 lessons, the situations (server roleplays) and their steps. Every
phrase is (Urdu script, romanised, literal English, natural English[, feminine form as (Urdu script, romanised)]). Urdu is written right to
left; the romanisation is the one learners type (Hindustani, no diacritics). The Urdu is Hyderabad's, with its Dakhini words ("hau", "nakko").
Written by the LingoBuddy team with an AI-assisted editorial pass; NOT reviewed by a native speaker (docs/CONTENT_REVIEW.md)."""

# ------------------------------------------------------------------------------------------------------------------------------------
# What the First Week lessons add to the pack's phrases: words (each with an example phrase of the lesson) and exercises
# (what a phrase means, translate a phrase, fill in a word).
# ------------------------------------------------------------------------------------------------------------------------------------
FIRST_WEEK = {
    "greetings": {"description": "Greet people the Hyderabadi way and introduce yourself in Urdu.",
                  "words": [("نام", "Naam", "Name", "میرا نام ایلکس ہے۔"), ("شکریہ", "Shukriya", "Thank you", "بہت شکریہ!")],
                  "exercises": ("Assalaam alaikum! Aap kaise hain?", "Bahut shukriya!", ("Mera naam Alex hai.", "naam"))},
    "transport": {"description": "Take an auto by the meter, and the metro.",
                  "words": [("میٹر", "Meter", "Meter (in an auto)", "میٹر سے چلو۔"), ("کدھر", "Kidhar", "Which way, where", "میٹرو اسٹیشن کدھر ہے؟")],
                  "exercises": ("Meter se chalo.", "Bas, idhar roko.", ("Kitne paise hue?", "paise"))},
    "food": {"description": "Order biryani, Irani chai and Osmania biscuits.",
             "words": [("مرچی", "Mirchi", "Chilli", "مرچی کم ڈالو۔"), ("پانی", "Paani", "Water", "تھوڑا پانی دینا۔")],
             "exercises": ("Mirchi kam daalo.", "Ek plate biryani dena.", ("Thoda paani dena.", "paani"))},
    "shopping": {"description": "Buy pearls in the old city at a fair price.",
                 "words": [("موتی", "Moti", "Pearl", "اصلی موتی ہیں؟"), ("زیادہ", "Zyaada", "Too much, more", "بہت زیادہ ہے۔")],
                 "exercises": ("Asli moti hain?", "Ye kitne ka hai?", ("Thoda kam karo na.", "kam"))},
    "directions": {"description": "Find your way round the old city, the Hyderabadi way.",
                   "words": [("ہاتھ", "Haath", "Hand", "سیدھا جا کر سیدھے ہاتھ کو مڑو۔"), ("قریب", "Qareeb", "Near", "یہاں قریب میں میڈیکل شاپ ہے؟")],
                   "exercises": ("Paidal kitna time lagega?", "Mecca Masjid kidhar hai?", ("Zara aahista boliye.", "aahista"))},
    "college": {"description": "Settle in at university and make friends.", "ages": ("teen", "adult"),
                "words": [("دن", "Din", "Day", "آج میرا پہلا دن ہے۔"), ("مدد", "Madad", "Help", "کیا آپ میری مدد کریں گے؟")],
                "exercises": ("Kya aap meri madad karenge?", "Library kidhar hai?", ("Phir milte hain!", "milte"))},
    "smalltalk": {"description": "Put everything together in a natural conversation.",
                  "words": [("اتوار", "Itwaar", "Sunday", "اتوار کو گولکنڈہ چلیں؟"), ("جواب", "Jawaab", "Answer", "حیدرآباد کی بریانی کا جواب نہیں!")],
                  "exercises": ("Tum yaheen ke ho?", "Hau, pakka!", ("Itwaar ko Golconda chalein?", "itwaar"))},
}

# ------------------------------------------------------------------------------------------------------------------------------------
# A1, after the 7 First Week lessons (sort_order 8-9)
# ------------------------------------------------------------------------------------------------------------------------------------
A1_LESSONS = [
    {"slug": "numbers-money", "topic": "shopping", "title": "Numbers and Money", "description": "Count, pay and understand prices.",
     "situation": "Paying at a shop in Mehdipatnam.",
     "tip": "Urdu numbers: ek, do, teen, chaar, paanch, chhe, saat, aath, nau, das; sau = 100, hazaar = 1000. In Hyderabad prices are said in Urdu, Telugu or English, so listen for all three.",
     "phrases": [
         ("کل کتنا ہوا؟", "Kul kitna hua?", "In total how much did it become?", "How much is it altogether?"),
         ("سو روپے۔", "Sau rupaye.", "Hundred rupees.", "A hundred rupees."),
         ("کھلے پیسے ہیں؟", "Khulle paise hain?", "Is there loose money?", "Do you have change?"),
         ("پچاس کا نوٹ چلے گا؟", "Pachaas ka note chalega?", "Will a note of fifty work?", "Is a fifty-rupee note okay?"),
         ("بل دیجیے۔", "Bill dijiye.", "Please give the bill.", "Can I have the bill, please?"),
     ],
     "words": [("روپے", "Rupaye", "Rupees", "سو روپے۔"), ("نوٹ", "Note", "Banknote", "پچاس کا نوٹ چلے گا؟")],
     "exercises": ("Khulle paise hain?", "Sau rupaye.", ("Kul kitna hua?", "kul"))},
    {"slug": "help-health", "topic": "emergency", "title": "Help and Health", "description": "Ask for help, a doctor or a pharmacy.",
     "situation": "You feel unwell late at night in Tolichowki.",
     "tip": "India's emergency number is 112 (police, fire and ambulance). A pharmacy is a “medical shop” or a “dawakhana”, and many stay open late.",
     "phrases": [
         ("مجھے مدد چاہیے!", "Mujhe madad chahiye!", "To me help is needed!", "I need help!"),
         ("قریب میں ہسپتال کہاں ہے؟", "Qareeb mein hospital kahan hai?", "Nearby where is a hospital?", "Where's the nearest hospital?"),
         ("میری طبیعت ٹھیک نہیں ہے۔", "Meri tabiyat theek nahi hai.", "My health is not fine.", "I don't feel well."),
         ("مجھے بخار ہے۔", "Mujhe bukhaar hai.", "To me there is fever.", "I have a fever."),
         ("دواخانہ کھلا ہے؟", "Dawakhana khula hai?", "Is the medicine house open?", "Is the pharmacy open?"),
         ("پولیس کو بلائیے!", "Police ko bulaaiye!", "Please call the police!", "Please call the police!"),
     ],
     "words": [("ہسپتال", "Hospital", "Hospital", "قریب میں ہسپتال کہاں ہے؟"), ("بخار", "Bukhaar", "Fever", "مجھے بخار ہے۔")],
     "exercises": ("Meri tabiyat theek nahi hai.", "Police ko bulaaiye!", ("Mujhe bukhaar hai.", "bukhaar"))},
]

GRAMMAR = [
    # (slug, level, title, explanation, example phrases, lesson slugs)
    ("polite-requests", "A1", "Polite requests: “-iye”, “-o” and “-na”",
     "Urdu asks politely with “aap” and verbs ending in -iye: “dijiye” (please give), “boliye” (please say), “bulaaiye” (please call). In the "
     "market and with friends the “tum” form in -o is common: “chalo”, “roko”, “daalo”; the -na form (“dena”) is a friendly request.",
     ["بل دیجیے۔", "ذرا آہستہ بولیے۔", "مرچی کم ڈالو۔"], ["food", "directions", "numbers-money"]),
    ("gender", "A1", "Masculine and feminine: “naya” and “nayi”",
     "Urdu adjectives and verbs change with the speaker's gender: a man says “main yahan naya hoon”, a woman “main yahan nayi hoon”. Lessons "
     "show both forms where they differ.",
     ["میں یہاں نیا ہوں۔", "میں یہاں نئی ہوں۔"], ["greetings"]),
    ("hyderabadi-words", "A1", "Hyderabadi words: “hau”, “nakko”, “kya re”",
     "Hyderabad's Urdu (Dakhini) has its own everyday words: “hau” (yes), “nakko” (no, don't), “kya re?” (what's up?) and “idhar / udhar” "
     "(here / there). They are informal: use them with friends and in the market, and “ji haan” / “ji nahi” with elders.",
     ["ہاؤ، پکا!", "کیا رے، کیسا چل رہا ہے؟", "بس، ادھر روکو۔"], ["smalltalk", "transport"]),
]

# ------------------------------------------------------------------------------------------------------------------------------------
# Situations (server roleplays): the 7 First Week roleplays and Help and Health. learn: lesson phrases (romanised); choose: the partner's
# opening line with options (the first is right); reply: the partner's answer with accepted replies; translate: optional.
# ------------------------------------------------------------------------------------------------------------------------------------
SITUATIONS = [
    {"slug": "greetings", "level": "A1", "topic": "greetings", "difficulty": 1, "title": "Meet your landlord",
     "description": "Your first evening in a rented flat in Tolichowki. Nawab sahab, your landlord, comes to welcome you.",
     "goal": "Greet your landlord and introduce yourself.", "setting": "Your rented flat in Tolichowki",
     "partner": ("Nawab sahab", "Landlord"),
     "learn": ["Assalaam alaikum! Aap kaise hain?", "Mera naam Alex hai.", "Bahut shukriya!"],
     "choose": ("Aadaab! Aap hi naye kirayedaar hain? Main Nawab.", "Hello! Are you the new tenant? I'm Nawab.",
                ["Ji, mera naam Alex hai.", "Ek plate biryani dena.", "Metro station kidhar hai?"]),
     "reply": ("Khush aamdeed! Kuch chahiye toh boliye.", "Welcome! Tell me if you need anything.", ["Bahut shukriya!", "Shukriya!", "Ji, shukriya."]),
     "translate": ("How would you say “It's lovely to meet you” in Urdu?", "Aap se mil kar bahut khushi hui.")},
    {"slug": "transport", "level": "A1", "topic": "transport", "difficulty": 1, "title": "Auto to the Charminar",
     "description": "You're outside Nampally station and need an auto to the Charminar.", "goal": "Get to the Charminar by the meter.",
     "setting": "Outside Nampally station", "partner": ("Salim bhai", "Auto driver"),
     "learn": ["Charminar chaloge?", "Meter se chalo.", "Bas, idhar roko."],
     "choose": ("Kidhar jaana?", "Where to?", ["Charminar chaloge?", "Ek plate biryani dena.", "Mera naam Alex hai."]),
     "reply": ("Meter se chalte, lekin bees rupaye upar.", "We'll go by the meter, but twenty extra.", ["Nakko, sirf meter.", "Theek hai, bees upar.", "Meter se chalo."])},
    {"slug": "food", "level": "A1", "topic": "food", "difficulty": 1, "title": "Dinner at an Irani café", "description": "Dinner at an Irani café near the Charminar.",
     "goal": "Order biryani and Irani chai, ask for less chilli and pay.", "setting": "An Irani café near the Charminar", "partner": ("Anwar", "Waiter"),
     "learn": ["Ek plate biryani dena.", "Mirchi kam daalo.", "Bill kitna hua?"],
     "choose": ("Aaiye, kya laaun?", "Come in, what can I bring you?", ["Ek plate biryani dena.", "Bas, idhar roko.", "Asli moti hain?"]),
     "reply": ("Ek plate biryani! Mirchi zyaada?", "One plate of biryani! Extra spicy?", ["Mirchi kam daalo.", "Nakko, mirchi kam.", "Thodi si mirchi chalegi."]),
     "translate": ("How would you say “Some water, please” in Urdu?", "Thoda paani dena.")},
    {"slug": "shopping", "level": "A1", "topic": "shopping", "difficulty": 2, "title": "Pearls in Pathargatti", "description": "You're at a pearl shop in Pathargatti, near the Charminar.",
     "goal": "Buy a string of pearls at a fair price.", "setting": "A pearl shop in Pathargatti", "partner": ("Kareem sahab", "Shopkeeper"),
     "learn": ["Ye kitne ka hai?", "Bahut zyaada hai.", "Thoda kam karo na."],
     "choose": ("Aaiye! Asli Hyderabadi moti.", "Come in! Real Hyderabad pearls.", ["Ye kitne ka hai?", "Meter se chalo.", "Library kidhar hai?"]),
     "reply": ("Ye maala? Chaar hazaar.", "This string? Four thousand.", ["Bahut zyaada hai.", "Thoda kam karo na.", "Aakhri daam boliye."])},
    {"slug": "directions", "level": "A1", "topic": "directions", "difficulty": 2, "title": "Find the Mecca Masjid", "description": "You're by the Charminar and want the Mecca Masjid.",
     "goal": "Find the way to the Mecca Masjid, and a pharmacy.", "setting": "By the Charminar", "partner": ("Habeeb bhai", "Passerby"),
     "learn": ["Mecca Masjid kidhar hai?", "Seedha jaa kar seedhe haath ko mudo.", "Zara aahista boliye."],
     "choose": ("Kuch dhoondna hai?", "Looking for something?", ["Mecca Masjid kidhar hai?", "Ek plate biryani dena.", "Ye kitne ka hai?"]),
     "reply": ("Seedha jaa kar seedhe haath ko mudo. Saamne hi masjid hai.", "Go straight and turn right. The mosque is right ahead.",
               ["Paidal kitna time lagega?", "Zara aahista boliye.", "Bahut shukriya!"])},
    {"slug": "college", "level": "A1", "topic": "college", "difficulty": 2, "title": "First day at the Urdu University",
     "description": "Your first day at the Maulana Azad National Urdu University in Gachibowli.",
     "goal": "Introduce yourself and find the library and the canteen.", "setting": "Maulana Azad National Urdu University, Gachibowli", "partner": ("Sana", "Classmate"),
     "ages": ("teen", "adult"),
     "learn": ["Aaj mera pehla din hai.", "Library kidhar hai?", "Canteen mein chai piyen?"],
     "choose": ("Assalaam alaikum! Aaj pehla din hai? Main Sana.", "Hello! First day today? I'm Sana.", ["Ji, aaj mera pehla din hai.", "Meter se chalo.", "Bill kitna hua?"]),
     "reply": ("Khush aamdeed! Library admin building ke saamne hai.", "Welcome! The library is opposite the admin building.",
               ["Kya aap meri madad karenge?", "Canteen mein chai piyen?", "Ji, shukriya."])},
    {"slug": "smalltalk", "level": "A1", "topic": "smalltalk", "difficulty": 2, "title": "An evening by the Charminar", "description": "An evening by the Charminar with Imran, a friend from university.",
     "goal": "Chat about Hyderabad and make Sunday plans.", "setting": "By the Charminar in the evening", "partner": ("Imran", "Friend"),
     "learn": ["Kya re, kaisa chal raha hai?", "Hyderabad ki biryani ka jawaab nahi!", "Itwaar ko Golconda chalein?"],
     "choose": ("Kya re, Hyderabad kaisa lag raha?", "Hey, how are you liking Hyderabad?", ["Hyderabad ki biryani ka jawaab nahi!", "Meter se chalo.", "Bill dijiye."]),
     "reply": ("Hau! Aur Ramzan mein haleem bhi.", "Yes! And haleem in Ramzan too.", ["Itwaar ko Golconda chalein?", "Tum yaheen ke ho?", "Hau, pakka!"]),
     "translate": ("How would you say “Are you from here?” in Urdu?", "Tum yaheen ke ho?")},
    {"slug": "help-health", "level": "A1", "topic": "emergency", "difficulty": 2, "title": "At the pharmacy late at night", "description": "You feel unwell late at night in Tolichowki.",
     "goal": "Say what is wrong and find out where the hospital is.", "setting": "A dawakhana in Tolichowki", "partner": ("Rashid", "Pharmacist"),
     "learn": ["Meri tabiyat theek nahi hai.", "Mujhe bukhaar hai.", "Qareeb mein hospital kahan hai?"],
     "choose": ("Aaiye, kya hua?", "Come in, what happened?", ["Meri tabiyat theek nahi hai.", "Ye kitne ka hai?", "Itwaar ko Golconda chalein?"]),
     "reply": ("Bukhaar hai? Ye goli lijiye. Zyaada ho toh hospital jaaiye.", "A fever? Take this tablet. If it gets worse, go to the hospital.",
               ["Qareeb mein hospital kahan hai?", "Mujhe bukhaar hai.", "Bahut shukriya!"])},
]
