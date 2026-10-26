// Content + configuration. New languages/cities plug in here.
// LANGUAGES is an offline fallback: profile.js replaces it with the database catalogue (/api/languages) when reachable.
window.LANGUAGES = [
  { code: "en", name: "English", native: "English", tts: "en-IN" },
  { code: "es", name: "Spanish", native: "Español", tts: "es-ES" },
  { code: "fr", name: "French", native: "Français", tts: "fr-FR" },
  { code: "de", name: "German", native: "Deutsch", tts: "de-DE" },
  { code: "it", name: "Italian", native: "Italiano", tts: "it-IT" },
  { code: "pt", name: "Portuguese", native: "Português", tts: "pt-PT" },
  { code: "ja", name: "Japanese", native: "日本語", tts: "ja-JP" },
  { code: "ko", name: "Korean", native: "한국어", tts: "ko-KR" },
  { code: "zh", name: "Chinese", native: "中文", tts: "zh-CN" },
  { code: "hi", name: "Hindi", native: "हिन्दी", tts: "hi-IN" },
  { code: "hinglish", name: "Hinglish", native: "Hinglish", tts: "hi-IN" },
  { code: "mr", name: "Marathi", native: "मराठी", tts: "mr-IN" },
  { code: "kn", name: "Kannada", native: "ಕನ್ನಡ", tts: "kn-IN" },
  { code: "ta", name: "Tamil", native: "தமிழ்", tts: "ta-IN" },
  { code: "bn", name: "Bengali", native: "বাংলা", tts: "bn-IN" },
  { code: "te", name: "Telugu", native: "తెలుగు", tts: "te-IN" },
  { code: "ur", name: "Urdu", native: "اردو", tts: "ur-IN" },
  { code: "ks", name: "Kashmiri", native: "کٲشُر", tts: "ks-IN" },
  { code: "doi", name: "Dogri", native: "डोगरी", tts: "doi-IN" },
];

window.CITIES = [
  { id: "delhi", name: "Delhi", flag: "🇮🇳", tag: "Dilli", blurb: "Metro, autos, chaat & Sarojini", langs: ["hi", "hinglish", "en"], ready: true, emoji: "🕌" },
  { id: "mumbai", name: "Mumbai", flag: "🇮🇳", tag: "Marathi · Hindi", blurb: "Locals, vada pav & the sea", langs: ["hi", "mr", "en"], ready: true, emoji: "🌊" },
  { id: "bengaluru", name: "Bengaluru", flag: "🇮🇳", tag: "Kannada", blurb: "Filter coffee & tech parks", langs: ["kn", "en"], ready: true, emoji: "☕" },
  { id: "hyderabad", name: "Hyderabad", flag: "🇮🇳", tag: "Telugu · Urdu", blurb: "Biryani & Charminar", langs: ["te", "ur", "en"], ready: true, emoji: "🍚" },
  { id: "chennai", name: "Chennai", flag: "🇮🇳", tag: "Tamil", blurb: "Marina, idli & auto talk", langs: ["ta", "en"], ready: true, emoji: "🏖️" },
  { id: "puducherry", name: "Puducherry", flag: "🇮🇳", tag: "Tamil · French", blurb: "French quarter, beaches & cafés", langs: ["ta", "fr", "en"], ready: true, emoji: "🌅" },
  { id: "jaipur", name: "Jaipur", flag: "🇮🇳", tag: "Hindi", blurb: "Forts, bazaars & dal baati", langs: ["hi", "en"], ready: true, emoji: "🏰" },
  { id: "lucknow", name: "Lucknow", flag: "🇮🇳", tag: "Hindi", blurb: "Kebabs, chikankari & tehzeeb", langs: ["hi", "en"], ready: true, emoji: "🕌" },
  { id: "kolkata", name: "Kolkata", flag: "🇮🇳", tag: "Bengali", blurb: "Adda, rolls & the yellow taxi", langs: ["bn", "en"], ready: true, emoji: "🌉" },
  { id: "bhopal", name: "Bhopal", flag: "🇮🇳", tag: "Hindi", blurb: "Lakes, poha & the old city", langs: ["hi", "en"], ready: true, emoji: "🏞️" },
  { id: "jk", name: "Jammu & Kashmir", flag: "🇮🇳", tag: "Kashmiri · Dogri · Urdu", blurb: "Houseboats, kahwa & the temples of Jammu", langs: ["ks", "doi", "ur", "en"], ready: true, emoji: "🛶" },
  { id: "shimla", name: "Shimla", flag: "🇮🇳", tag: "Hindi", blurb: "The Mall, the Ridge & the toy train", langs: ["hi", "en"], ready: true, emoji: "🏔️" },
];

// "I'm New Here" destinations: every Indian state capital and union territory, for display. Learning packs live in CITIES (above, kept in step
// with the database); a destination only links to one. status: "available" (pack ready), "in_development" (pack usable, still being refined),
// "coming_soon" (no pack yet). A destination can be picked ONLY if its status is not "coming_soon" AND its linked city is ready in CITIES, so a
// mistake here can never enable a city that has no pack. `serves`: the states and union territories it is the capital of (Chandigarh serves three).
window.DESTINATIONS = [
  { id: "delhi", name: "New Delhi", emoji: "🕌", status: "available", city: "delhi", serves: [{ name: "Delhi", type: "ut" }], note: "Capital of India" },
  { id: "mumbai", name: "Mumbai", emoji: "🌊", status: "available", city: "mumbai", serves: [{ name: "Maharashtra", type: "state" }] },
  { id: "amaravati", name: "Amaravati", emoji: "🏛️", status: "coming_soon", serves: [{ name: "Andhra Pradesh", type: "state" }] },
  { id: "itanagar", name: "Itanagar", emoji: "🏔️", status: "coming_soon", serves: [{ name: "Arunachal Pradesh", type: "state" }] },
  { id: "dispur", name: "Dispur", emoji: "🍵", status: "coming_soon", serves: [{ name: "Assam", type: "state" }] },
  { id: "patna", name: "Patna", emoji: "🛕", status: "coming_soon", serves: [{ name: "Bihar", type: "state" }] },
  { id: "raipur", name: "Raipur", emoji: "🌾", status: "coming_soon", serves: [{ name: "Chhattisgarh", type: "state" }] },
  { id: "panaji", name: "Panaji", emoji: "🏖️", status: "coming_soon", serves: [{ name: "Goa", type: "state" }] },
  { id: "gandhinagar", name: "Gandhinagar", emoji: "🏛️", status: "coming_soon", serves: [{ name: "Gujarat", type: "state" }] },
  { id: "chandigarh", name: "Chandigarh", emoji: "🌹", status: "coming_soon", serves: [{ name: "Punjab", type: "state" }, { name: "Haryana", type: "state" }, { name: "Chandigarh", type: "ut" }] },
  { id: "shimla", name: "Shimla", emoji: "🏔️", status: "in_development", city: "shimla", serves: [{ name: "Himachal Pradesh", type: "state" }], alt: "The Queen of the Hills",
    intro: "Himachal Pradesh's capital, strung along a ridge in the hills, where Hindi is spoken with a Himachali touch: people greet you with “Ram Ram”, the Mall is for walking only, and a public lift carries you up from Cart Road.",
    preview: ["Ram Ram: meet your landlady", "Taxis, HRTC buses and the Lift to the Mall", "Siddu with ghee at a dhaba", "A Himachali topi in Lakkar Bazaar", "Finding the Jakhu Temple", "First day at university", "Sunset on the Ridge"] },
  { id: "ranchi", name: "Ranchi", emoji: "🌳", status: "coming_soon", serves: [{ name: "Jharkhand", type: "state" }] },
  { id: "bengaluru", name: "Bengaluru", emoji: "☕", status: "available", city: "bengaluru", serves: [{ name: "Karnataka", type: "state" }], alt: "Bangalore",
    intro: "India's tech capital, where Kannada is the local language and English, Hindi, Tamil and Telugu are all heard. A few words of Kannada go a long way with neighbours, auto drivers and darshini staff.",
    preview: ["Namaskara: greet your house owner", "Autos by the meter, buses and Namma Metro", "Breakfast at a darshini", "Bargaining on Commercial Street", "Directions by Main, Cross and landmark", "First day at a Whitefield tech park", "Weekend plans with a flatmate"] },
  { id: "thiruvananthapuram", name: "Thiruvananthapuram", emoji: "🌴", status: "coming_soon", serves: [{ name: "Kerala", type: "state" }] },
  { id: "bhopal", name: "Bhopal", emoji: "🏞️", status: "available", city: "bhopal", serves: [{ name: "Madhya Pradesh", type: "state" }], alt: "The City of Lakes",
    intro: "Madhya Pradesh's capital, built around its lakes, where Hindi is spoken with a Bhopali touch: friends call each other “khan” and “miyan”, and the old city still chats for hours on its patiyas.",
    preview: ["Namaste: meet your neighbour", "Autos, shared 'magic' vans and the new metro", "Poha-jalebi for breakfast", "A zari batua in Chowk Bazaar", "Finding the Taj-ul-Masajid", "First day at college", "Sunset at the Boat Club"] },
  { id: "imphal", name: "Imphal", emoji: "🌸", status: "coming_soon", serves: [{ name: "Manipur", type: "state" }] },
  { id: "shillong", name: "Shillong", emoji: "🌧️", status: "coming_soon", serves: [{ name: "Meghalaya", type: "state" }] },
  { id: "aizawl", name: "Aizawl", emoji: "⛰️", status: "coming_soon", serves: [{ name: "Mizoram", type: "state" }] },
  { id: "kohima", name: "Kohima", emoji: "🌄", status: "coming_soon", serves: [{ name: "Nagaland", type: "state" }] },
  { id: "bhubaneswar", name: "Bhubaneswar", emoji: "🛕", status: "coming_soon", serves: [{ name: "Odisha", type: "state" }] },
  { id: "jaipur", name: "Jaipur", emoji: "🏰", status: "available", city: "jaipur", serves: [{ name: "Rajasthan", type: "state" }], alt: "The Pink City",
    intro: "Rajasthan's capital of forts, palaces and bazaars, where Hindi is spoken everywhere with a Rajasthani touch: “Khamma ghani” to greet, “padharo” to welcome you.",
    preview: ["Khamma ghani: greet your PG owner", "Autos, e-rickshaws and the Pink Line metro", "Pyaaz kachori and lassi in Johari Bazaar", "Bargaining for mojaris in Bapu Bazaar", "Finding your way round the walled city", "First day at college", "Sunset at Nahargarh Fort"] },
  { id: "gangtok", name: "Gangtok", emoji: "🏔️", status: "coming_soon", serves: [{ name: "Sikkim", type: "state" }] },
  { id: "chennai", name: "Chennai", emoji: "🏖️", status: "available", city: "chennai", serves: [{ name: "Tamil Nadu", type: "state" }], alt: "Madras",
    intro: "Tamil Nadu's capital by the Bay of Bengal, where Tamil is spoken everywhere: in markets, autos, offices and at the tiffin counter. A few words of Tamil open a lot of doors.",
    preview: ["Vanakkam: greet your house owner", "Autos, MTC buses and the Chennai Metro", "Breakfast at a tiffin centre", "Bargaining on Ranganathan Street", "Directions by street and landmark", "First day at an office on OMR", "An evening on Marina Beach"] },
  { id: "hyderabad", name: "Hyderabad", emoji: "🍚", status: "available", city: "hyderabad", serves: [{ name: "Telangana", type: "state" }], alt: "The City of Pearls",
    intro: "Telangana's capital, where Telugu and Urdu live side by side: Telugu in the new city's offices and markets, Hyderabadi Urdu in the old city around the Charminar. Learn Telugu, Urdu, or both.",
    preview: ["Namaskaram or Assalaam alaikum: meet your landlord", "Autos by the meter, and the Hyderabad Metro", "Biryani and Irani chai", "Bangles in Laad Bazaar, pearls in Pathargatti", "Finding your way round the Charminar", "A first day in HITEC City or at university", "Sunset on Tank Bund, an evening in the old city"] },
  { id: "agartala", name: "Agartala", emoji: "🏯", status: "coming_soon", serves: [{ name: "Tripura", type: "state" }] },
  { id: "lucknow", name: "Lucknow", emoji: "🕌", status: "available", city: "lucknow", serves: [{ name: "Uttar Pradesh", type: "state" }], alt: "The City of Nawabs",
    intro: "Uttar Pradesh's capital, famous for its tehzeeb (courtesy), Awadhi food and chikankari. Hindi here is softened with Urdu: “Aadaab”, “shukriya” and the legendary “pehle aap”.",
    preview: ["Aadaab: meet your landlord", "Shared autos, tempos and the metro", "Kebabs and biryani in Aminabad", "Buying chikankari in Chowk", "Old Lucknow's monuments", "First day at Lucknow University", "An evening by the Gomti"] },
  { id: "dehradun", name: "Dehradun", emoji: "🌲", status: "coming_soon", serves: [{ name: "Uttarakhand", type: "state" }] },
  { id: "kolkata", name: "Kolkata", emoji: "🌉", status: "available", city: "kolkata", serves: [{ name: "West Bengal", type: "state" }], alt: "Calcutta",
    intro: "West Bengal's capital on the Hooghly, where Bengali is spoken everywhere: in the markets, the yellow taxis, the tea stalls and the endless adda. A little Bengali goes a long way.",
    preview: ["Nomoshkar: meet your landlady", "Yellow taxis by the meter, and the metro", "Kathi rolls and tea in a clay cup", "Bargaining for a saree in Gariahat", "Finding the Victoria Memorial", "First day at Jadavpur University", "Adda at Prinsep Ghat"] },
  { id: "sri-vijaya-puram", name: "Sri Vijaya Puram", emoji: "🏝️", status: "coming_soon", serves: [{ name: "Andaman and Nicobar Islands", type: "ut" }], note: "Formerly Port Blair" },
  { id: "daman", name: "Daman", emoji: "⛵", status: "coming_soon", serves: [{ name: "Dadra and Nagar Haveli and Daman and Diu", type: "ut" }] },
  { id: "srinagar-jammu", name: "Srinagar & Jammu", emoji: "🛶", status: "in_development", city: "jk", serves: [{ name: "Jammu and Kashmir", type: "ut" }], note: "Summer and winter capitals",
    intro: "Jammu and Kashmir's two capitals: Srinagar in summer, by the Dal Lake, where people speak Kashmiri, and Jammu in winter, the City of Temples, where they speak Dogri. Urdu, the official language, is understood in both. The Kashmiri and Dogri are an early draft awaiting a native speaker.",
    preview: ["A houseboat on the Dal, or a room in Jammu", "Autos, shikaras and matadors", "Kahwa and noon chai, kalari kulcha", "A pashmina in Srinagar, dry fruits in Jammu", "Lal Chowk and the Raghunath Temple", "A first day at university", "The Mughal gardens and the Bagh-e-Bahu"] },
  { id: "leh", name: "Leh", emoji: "🏔️", status: "coming_soon", serves: [{ name: "Ladakh", type: "ut" }] },
  { id: "kavaratti", name: "Kavaratti", emoji: "🐠", status: "coming_soon", serves: [{ name: "Lakshadweep", type: "ut" }] },
  { id: "puducherry", name: "Puducherry", emoji: "🌅", status: "available", city: "puducherry", serves: [{ name: "Puducherry", type: "ut" }], alt: "Pondicherry",
    intro: "A seaside union territory where Tamil is spoken everywhere and French lives on in White Town: its heritage homes, the Lycée français, the Alliance française and the consulate. Learn Tamil for the town, French for the French quarter.",
    preview: ["Vanakkam or Bonjour: settle into your stay", "Rent a scooter or a bicycle", "Seafood by the sea, croissants in White Town", "Goubert Market and the boutiques", "The Promenade, the canal and the landmarks", "A first class at university or the Alliance", "Sunrise on the Promenade, Sunday in Auroville"] },
];

window.CATEGORIES = [
  { key: "greetings", label: "Greetings", icon: "👋", weight: 1.5 },
  { key: "transport", label: "Transport", icon: "🚌", weight: 2 },
  { key: "food", label: "Food", icon: "🍛", weight: 1 },
  { key: "shopping", label: "Shopping", icon: "🛍️", weight: 1 },
  { key: "directions", label: "Directions", icon: "📍", weight: 1.5 },
  { key: "college", label: "College / Work", icon: "🎓", weight: 1 },
  { key: "smalltalk", label: "Small Talk", icon: "🗣️", weight: 0.5 },
];

// Delhi survival pack (Hindi). Each phrase: hi (Devanagari), roman (how to say it / Hinglish), en (literal), natural.
window.PACKS = {
  delhi: [
    { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Learn how to greet people naturally.",
      situation: "You just moved into your PG. Your landlady, Sharma aunty, says hello.", scenario: "greetings",
      tip: "Add “ji” after a name (Sharma ji, aunty ji) to sound respectful — Delhi loves it.",
      phrases: [
        { hi: "नमस्ते, आप कैसे हैं?", roman: "Namaste, aap kaise hain?", en: "Hello, how are you?", natural: "Hi! How are you doing?" },
        { hi: "मेरा नाम एलेक्स है।", roman: "Mera naam Alex hai.", en: "My name is Alex.", natural: "I'm Alex." },
        { hi: "आपका नाम क्या है?", roman: "Aapka naam kya hai?", en: "What is your name?", natural: "What's your name?" },
        { hi: "आपसे मिलकर अच्छा लगा।", roman: "Aapse milkar accha laga.", en: "Felt good meeting you.", natural: "Nice to meet you." },
        { hi: "बहुत शुक्रिया!", roman: "Bahut shukriya!", en: "Many thanks!", natural: "Thanks a lot!" },
      ] },
    { day: 2, key: "transport", icon: "🚌", title: "Transport", desc: "Talk to drivers and navigate public transport.",
      situation: "You need to get to Connaught Place.", scenario: "auto",
      tip: "Call auto drivers “bhaiya” (brother). It's friendly and polite — never rude.",
      phrases: [
        { hi: "भैया, कनॉट प्लेस चलोगे?", roman: "Bhaiya, Connaught Place chaloge?", en: "Brother, will you go to Connaught Place?", natural: "Could you take me to Connaught Place?" },
        { hi: "कितने पैसे होंगे?", roman: "Kitne paise honge?", en: "How much money will it be?", natural: "How much will it cost?" },
        { hi: "यहाँ से कितनी दूर है?", roman: "Yahan se kitni door hai?", en: "How far is it from here?", natural: "Is it far from here?" },
        { hi: "यहीं रोक दीजिए।", roman: "Yahin rok dijiye.", en: "Please stop right here.", natural: "You can drop me here." },
        { hi: "राजीव चौक के लिए कौन सी लाइन?", roman: "Rajiv Chowk ke liye kaun si line?", en: "Which line for Rajiv Chowk?", natural: "Which metro line goes to Rajiv Chowk?" },
      ] },
    { day: 3, key: "food", icon: "🍛", title: "Food", desc: "Order food and understand common phrases.",
      situation: "Lunch time at a chhole bhature stall in Kamla Nagar.", scenario: "food",
      tip: "“Kam teekha” (less spicy) is the most useful food phrase you'll ever learn.",
      phrases: [
        { hi: "एक प्लेट छोले भटूरे देना।", roman: "Ek plate chhole bhature dena.", en: "Give one plate of chhole bhature.", natural: "One plate of chhole bhature, please." },
        { hi: "कम तीखा बनाना, प्लीज़।", roman: "Kam teekha banana, please.", en: "Make it less spicy, please.", natural: "Not too spicy, please." },
        { hi: "पानी मिलेगा?", roman: "Paani milega?", en: "Will I get water?", natural: "Could I get some water?" },
        { hi: "बिल दे दीजिए।", roman: "Bill de dijiye.", en: "Please give the bill.", natural: "Can I have the bill?" },
      ] },
    { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Ask prices and negotiate politely.",
      situation: "You're at Sarojini Nagar market looking for a jacket.", scenario: "shopping",
      tip: "Bargaining is normal in street markets — smile, stay polite, and offer ~60% to start.",
      phrases: [
        { hi: "यह कितने का है?", roman: "Yeh kitne ka hai?", en: "How much is this?", natural: "What's the price of this?" },
        { hi: "थोड़ा कम कीजिए ना।", roman: "Thoda kam kijiye na.", en: "Please reduce it a little.", natural: "Can you do a better price?" },
        { hi: "कोई और रंग है?", roman: "Koi aur rang hai?", en: "Is there another colour?", natural: "Do you have it in another colour?" },
        { hi: "यूपीआई चलेगा?", roman: "UPI chalega?", en: "Will UPI work?", natural: "Can I pay by UPI?" },
      ] },
    { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Ask for and understand directions.",
      situation: "You got off at the wrong gate and need the metro station.", scenario: "directions",
      tip: "Listen for “seedhe” (straight), “baayein” (left) and “daayein” (right).",
      phrases: [
        { hi: "मेट्रो स्टेशन कहाँ है?", roman: "Metro station kahan hai?", en: "Where is the metro station?", natural: "Which way to the metro?" },
        { hi: "सीधे जाइए, फिर बाएँ मुड़िए।", roman: "Seedhe jaiye, phir baayein mudiye.", en: "Go straight, then turn left.", natural: "Go straight and take a left." },
        { hi: "क्या यह पास में है?", roman: "Kya yeh paas mein hai?", en: "Is it nearby?", natural: "Is it close?" },
        { hi: "मैं रास्ता भूल गया हूँ।", roman: "Main raasta bhool gaya hoon.", en: "I have forgotten the way.", natural: "I'm lost." },
      ] },
    { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Communicate with classmates, colleagues and locals.",
      situation: "First day on campus. You need to find your class.", scenario: "college",
      tip: "Seniors are called “bhaiya/didi” on many campuses — it's warm, not formal.",
      phrases: [
        { hi: "मैं यहाँ नया हूँ।", roman: "Main yahan naya hoon.", en: "I am new here.", natural: "I'm new here." },
        { hi: "क्लास कितने बजे शुरू होगी?", roman: "Class kitne baje shuru hogi?", en: "At what time will class start?", natural: "When does class start?" },
        { hi: "क्या आप मेरी मदद कर सकते हैं?", roman: "Kya aap meri madad kar sakte hain?", en: "Can you help me?", natural: "Could you help me out?" },
        { hi: "कैंटीन कहाँ है?", roman: "Canteen kahan hai?", en: "Where is the canteen?", natural: "Where's the canteen?" },
      ] },
    { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
      situation: "Chai break with Priya, a classmate you just met.", scenario: "smalltalk",
      tip: "End sentences with “na?” to invite agreement — it makes you sound instantly local.",
      phrases: [
        { hi: "आप कहाँ से हैं?", roman: "Aap kahan se hain?", en: "Where are you from?", natural: "Where are you from?" },
        { hi: "आजकल बहुत गर्मी है, ना?", roman: "Aajkal bahut garmi hai, na?", en: "These days it's very hot, no?", natural: "It's so hot these days, right?" },
        { hi: "चाय पिएँगे?", roman: "Chai piyenge?", en: "Will you drink tea?", natural: "Fancy a chai?" },
        { hi: "फिर मिलते हैं!", roman: "Phir milte hain!", en: "Will meet again!", natural: "See you later!" },
      ] },
  ],
};

// Roleplay scenarios. Rules are matched in order (keywords, lowercase). Used when no LLM is configured.
window.SCENARIOS = {
  auto: { category: "transport", icon: "🛺", title: "Auto-rickshaw ride", partner: "Raju bhaiya", role: "Auto driver", place: "Outside Kashmere Gate metro",
    goal: "Get to Connaught Place for a fair price.",
    opening: { text: "Namaste! Kahan jaana hai?", en: "Hello! Where do you want to go?" },
    start: ["Connaught Place jaana hai.", "Bhaiya, airport chaloge?", "Kitne paise honge?"],
    rules: [
      { m: ["100", "sau"], text: "Chalo theek hai, 100 mein chalte hain. Baith jaiye!", en: "Okay fine, let's go for 100. Hop in!", s: ["Kitni door hai?", "Dhanyavaad bhaiya!"] },
      { m: ["kam", "meter", "mehenga", "zyada", "expensive", "too much", "less"], text: "Arre bhaiya, petrol mehenga hai… achha, 120 de dena. Isse kam nahi.", en: "Come on, fuel is expensive… okay, give 120. Not less than that.", s: ["Theek hai, chaliye.", "100 mein chaloge?"], hint: "Thoda kam kijiye na." },
      { m: ["rok", "yahin", "stop", "drop"], text: "Lijiye, aa gaye! 120 rupaye. UPI bhi chalega.", en: "Here we are! ₹120. UPI works too.", s: ["Dhanyavaad bhaiya!", "UPI se de raha hoon."], hint: "Yahin rok dijiye." },
      { m: ["dhanyavaad", "shukriya", "thank", "upi"], text: "Aapka bhi shukriya! Dilli mein dhyan rakhna. 🙏", en: "Thank you too! Take care in Delhi.", s: ["Phir milte hain!"], end: true, hint: "Dhanyavaad bhaiya!" },
      { m: ["naya", "nayi", "new", "se hoon", "from"], text: "Arre wah! Dilli mein swagat hai. Chhole bhature zaroor try karna!", en: "Oh nice! Welcome to Delhi. Definitely try chhole bhature!", s: ["Zaroor! Kitni door hai?", "Yahin rok dijiye."], hint: "Main yahan naya hoon." },
      { m: ["door", "far", "time", "minute", "kitni"], text: "Bas 15-20 minute. Aaj traffic kam hai.", en: "Just 15–20 minutes. Traffic is light today.", s: ["Achha, theek hai.", "Yahin rok dijiye."], hint: "Kitni door hai?" },
      { m: ["kitne", "paise", "price", "cost", "how much", "kiraya"], text: "150 rupaye lagenge.", en: "It'll be ₹150.", s: ["Bhaiya, thoda kam kijiye.", "Meter se chaliye.", "Theek hai, chaliye."], hint: "Kitne paise honge?" },
      { m: ["theek", "ok", "okay", "chaliye", "chalo", "haan", "fine"], text: "Baithiye! Aap Dilli mein naye ho kya?", en: "Have a seat! Are you new to Delhi?", s: ["Haan, main yahan naya hoon.", "Main London se hoon."] },
      { m: ["connaught", "cp", "rajiv", "airport", "station", "india gate", "hauz khas", "chandni", "karol", "jaana", "chaloge", "chalenge", "go to", "take me"], text: "Haan, chalenge. {place}? 150 rupaye lagenge.", en: "Yes, I'll go. {place}? It'll be ₹150.", s: ["Bhaiya, thoda kam kijiye.", "Meter se chaliye.", "Theek hai, chaliye."], hint: "Bhaiya, {place} chaloge?" },
    ],
    fallback: { text: "Maaf kijiye, samjha nahi. Kahan jaana hai aapko?", en: "Sorry, didn't get that. Where do you need to go?", s: ["Connaught Place jaana hai.", "Bhaiya, airport chaloge?"] } },

  smalltalk: { category: "smalltalk", icon: "☕", title: "Chai with a classmate", partner: "Priya", role: "Classmate", place: "Chai stall outside North Campus",
    goal: "Introduce yourself and make weekend plans.",
    opening: { text: "Hi! Tum naye ho na? Main Priya. Tumhara naam kya hai?", en: "Hi! You're new, right? I'm Priya. What's your name?" },
    start: ["Mera naam Alex hai.", "Haan, main yahan naya hoon."],
    rules: [
      { m: ["phir milte", "bye", "milte hain", "badhiya", "great", "awesome"], text: "Phir milte hain! Kal class mein milte hain. 👋", en: "See you! See you in class tomorrow.", s: ["Bye Priya!"], end: true, hint: "Phir milte hain!" },
      { m: ["plan", "weekend", "india gate", "kuch nahi", "nothing", "free"], text: "Chalo phir saath chalte hain! Main tumhe Chandni Chowk ka khana bhi dikhaungi.", en: "Then let's go together! I'll show you Chandni Chowk's food too.", s: ["Wah, bahut badhiya!", "Phir milte hain!"] },
      { m: ["naam", "mera", "name", "i am", "i'm", "main alex"], text: "Nice! Tumse milkar accha laga. Tum kahan se ho?", en: "Nice! Great to meet you. Where are you from?", s: ["Main Bengaluru se hoon.", "Main London se hoon."], hint: "Mera naam Alex hai." },
      { m: ["se hoon", "se hu", "from", "naya", "new"], text: "Achha! Toh Dilli kaisi lag rahi hai ab tak?", en: "Oh nice! So how are you finding Delhi so far?", s: ["Bahut acchi hai!", "Thodi garmi hai, par mazaa aa raha hai."], hint: "Main London se hoon." },
      { m: ["acchi", "achhi", "achi", "mazaa", "maza", "good", "nice", "garmi", "hot", "love"], text: "Haha, sahi baat! Aajkal bahut garmi hai, na? Chai piyoge?", en: "Haha, true! It's really hot these days, right? Want chai?", s: ["Haan, zaroor!", "Nahi, shukriya."], hint: "Bahut acchi hai!" },
      { m: ["haan", "zaroor", "yes", "sure", "chalo"], text: "Bhaiya, do cutting chai! ☕ Aur weekend pe kya plan hai?", en: "Two cutting chais please! So what's the plan this weekend?", s: ["Abhi kuch nahi.", "India Gate jaana hai."], hint: "Haan, zaroor!" },
      { m: ["nahi", "no"], text: "Koi baat nahi! Weekend pe kya plan hai?", en: "No worries! What's your weekend plan?", s: ["Abhi kuch nahi.", "India Gate jaana hai."] },
    ],
    fallback: { text: "Haha, acchha! Aur batao, Dilli mein sabse accha kya laga?", en: "Haha, okay! Tell me more — what did you like most about Delhi?", s: ["Khana bahut accha hai!", "Metro bahut acchi hai."] } },

  greetings: { category: "greetings", icon: "🏠", title: "Meet your landlady", partner: "Sharma aunty", role: "PG owner", place: "Your PG in Laxmi Nagar",
    goal: "Greet politely and introduce yourself.",
    opening: { text: "Namaste beta! Aap naye aaye ho? Aapka naam kya hai?", en: "Hello dear! You're new here? What's your name?" },
    start: ["Namaste aunty ji! Mera naam Alex hai.", "Aap kaise hain?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank"], text: "Arre, koi baat nahi beta. Kuch chahiye toh batana! 🙏", en: "Oh, no problem dear. Tell me if you need anything!", s: ["Ji, zaroor. Namaste!"], end: true },
      { m: ["naam", "mera", "name", "i am", "i'm"], text: "Bahut accha naam hai! Aapse milkar accha laga. Khana khaya?", en: "Lovely name! Nice to meet you. Have you eaten?", s: ["Ji, kha liya.", "Abhi nahi, aunty ji."], hint: "Mera naam Alex hai." },
      { m: ["kaise", "how are"], text: "Main bilkul theek hoon, beta. Aap batao?", en: "I'm totally fine, dear. How about you?", s: ["Main bhi theek hoon, shukriya!"] },
      { m: ["kha liya", "ji", "haan", "yes"], text: "Accha! Wifi ka password fridge pe likha hai. Aur kuch?", en: "Good! The wifi password is written on the fridge. Anything else?", s: ["Bahut shukriya, aunty ji!"] },
      { m: ["nahi", "abhi", "not yet"], text: "Chalo, main aapke liye parathe bana deti hoon!", en: "Come on, I'll make you some parathas!", s: ["Bahut shukriya, aunty ji!"] },
      { m: ["namaste", "hello", "hi"], text: "Namaste, namaste! Aapka naam kya hai?", en: "Hello! What's your name?", s: ["Mera naam Alex hai."], hint: "Namaste aunty ji!" },
    ],
    fallback: { text: "Accha beta. Aapka naam kya hai?", en: "Okay dear. What's your name?", s: ["Mera naam Alex hai."] } },

  food: { category: "food", icon: "🍛", title: "Street food stall", partner: "Sethi ji", role: "Stall owner", place: "Chhole bhature stall, Kamla Nagar",
    goal: "Order lunch, ask for less spice and pay.",
    opening: { text: "Aaiye aaiye! Kya khaoge? Chhole bhature ekdum garam hain!", en: "Come in! What will you eat? The chhole bhature are piping hot!" },
    start: ["Ek plate chhole bhature dena.", "Menu kya hai?"],
    rules: [
      { m: ["bill", "kitne", "paise", "how much", "pay"], text: "90 rupaye ho gaye. UPI ya cash?", en: "That's ₹90. UPI or cash?", s: ["UPI se.", "Shukriya, bahut tasty tha!"], hint: "Bill de dijiye." },
      { m: ["shukriya", "dhanyavaad", "tasty", "thank", "upi", "cash"], text: "Phir aana! Kal rajma chawal bhi try karna. 😄", en: "Come again! Try rajma chawal tomorrow too.", s: ["Zaroor aaunga!"], end: true },
      { m: ["teekha", "spicy", "mirchi"], text: "Koi tension nahi, kam teekha bana dete hain. Lassi bhi loge?", en: "No worries, we'll make it less spicy. Want a lassi too?", s: ["Haan, ek meethi lassi.", "Nahi, paani milega?"], hint: "Kam teekha banana, please." },
      { m: ["paani", "water"], text: "Haan ji, yeh lijiye bottle. 20 rupaye extra.", en: "Yes, here's a bottle. ₹20 extra.", s: ["Bill de dijiye."], hint: "Paani milega?" },
      { m: ["lassi", "haan"], text: "Ek meethi lassi aa rahi hai! Aur kuch?", en: "One sweet lassi coming! Anything else?", s: ["Bas, bill de dijiye."] },
      { m: ["plate", "chhole", "bhature", "dena", "order", "want", "menu"], text: "Ek plate chhole bhature! Teekha chalega?", en: "One plate of chhole bhature! Is spicy okay?", s: ["Kam teekha banana, please.", "Haan, chalega!"], hint: "Ek plate chhole bhature dena." },
    ],
    fallback: { text: "Ji? Chhole bhature, rajma chawal, aloo paratha — kya dun?", en: "Sorry? Chhole bhature, rajma rice, potato paratha — what can I get you?", s: ["Ek plate chhole bhature dena."] } },

  shopping: { category: "shopping", icon: "🛍️", title: "Bargain at Sarojini", partner: "Vicky", role: "Shopkeeper", place: "Sarojini Nagar market",
    goal: "Buy a jacket at a fair price.",
    opening: { text: "Aao didi/bhaiya, dekho! Ekdum branded jacket, sirf 800 ka.", en: "Come, have a look! Totally branded jacket, only ₹800." },
    start: ["Yeh kitne ka hai?", "Thoda kam kijiye na."],
    rules: [
      { m: ["upi", "pack", "le lunga", "le leti", "done", "deal", "theek"], text: "Pack kar diya! UPI scanner yeh raha. Phir aana! 🛍️", en: "Packed it! Here's the UPI scanner. Come again!", s: ["Shukriya bhaiya!"], end: true, hint: "UPI chalega?" },
      { m: ["400", "500", "300"], text: "Arre nahi… chalo aapke liye 500 final. Isse kam nahi hoga.", en: "Oh no… okay, ₹500 final just for you. Can't go lower.", s: ["Theek hai, le lunga.", "UPI chalega?"] },
      { m: ["kam", "less", "discount", "mehenga", "expensive"], text: "Achha, 650 de do. Quality dekho, ekdum mast hai!", en: "Okay, give ₹650. Look at the quality, it's great!", s: ["400 mein doge?", "Koi aur rang hai?"], hint: "Thoda kam kijiye na." },
      { m: ["rang", "colour", "color"], text: "Haan, black aur blue dono hai. Kaunsa chahiye?", en: "Yes, both black and blue. Which one?", s: ["Blue wala.", "Thoda kam kijiye na."], hint: "Koi aur rang hai?" },
      { m: ["kitne", "price", "how much", "kya daam"], text: "Sirf 800! Market mein sabse sasta.", en: "Only ₹800! Cheapest in the market.", s: ["Thoda kam kijiye na.", "Bahut mehenga hai!"], hint: "Yeh kitne ka hai?" },
      { m: ["blue", "black", "wala"], text: "Badhiya choice! 650 mein de dunga.", en: "Great choice! I'll give it for ₹650.", s: ["400 mein doge?", "Theek hai, le lunga."] },
    ],
    fallback: { text: "Dekho dekho, aur bhi designs hain! Kya chahiye?", en: "Look around, there are more designs! What do you need?", s: ["Yeh kitne ka hai?"] } },

  directions: { category: "directions", icon: "🚇", title: "Find the metro", partner: "Uncle ji", role: "Passerby", place: "Near Lajpat Nagar market",
    goal: "Find the nearest metro station.",
    opening: { text: "Haan beta, kuch dhoondh rahe ho?", en: "Yes dear, looking for something?" },
    start: ["Metro station kahan hai?", "Main raasta bhool gaya hoon."],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank"], text: "Koi baat nahi! Dhyan se jaana. 👍", en: "No problem! Go carefully.", s: ["Namaste!"], end: true },
      { m: ["door", "paas", "far", "near", "kitni"], text: "Bas 5 minute paidal. Ekdum paas hai.", en: "Just a 5-minute walk. Very close.", s: ["Bahut shukriya, uncle ji!"], hint: "Kya yeh paas mein hai?" },
      { m: ["metro", "station", "kahan", "where", "raasta", "lost", "bhool"], text: "Seedhe jaiye, phir mithai ki dukaan se baayein mudiye. Station saamne hai.", en: "Go straight, then turn left at the sweet shop. The station is right there.", s: ["Kya yeh paas mein hai?", "Phir se boliye?"], hint: "Metro station kahan hai?" },
      { m: ["phir se", "again", "repeat", "samjha nahi"], text: "Seedhe… phir baayein. Left! Mithai ki dukaan ke paas.", en: "Straight… then left. Near the sweet shop.", s: ["Samajh gaya, shukriya!"] },
    ],
    fallback: { text: "Kahan jaana hai beta? Metro, market, ya bus stop?", en: "Where do you need to go? Metro, market or bus stop?", s: ["Metro station kahan hai?"] } },

  college: { category: "college", icon: "🎓", title: "First day on campus", partner: "Rohan", role: "Senior", place: "Main gate, Delhi University",
    goal: "Find your class and ask for help.",
    opening: { text: "Hey! Kaafi confused lag rahe ho. Fresher ho?", en: "Hey! You look pretty confused. Are you a fresher?" },
    start: ["Haan, main yahan naya hoon.", "Kya aap meri madad kar sakte hain?"],
    rules: [
      { m: ["shukriya", "thank", "dhanyavaad"], text: "Koi scene nahi! All the best. Canteen mein milte hain. ✌️", en: "No big deal! All the best. See you at the canteen.", s: ["Phir milte hain!"], end: true },
      { m: ["canteen", "khana", "food"], text: "Canteen library ke peeche hai. Maggi try karna, legendary hai!", en: "The canteen is behind the library. Try the Maggi, it's legendary!", s: ["Bahut shukriya!"], hint: "Canteen kahan hai?" },
      { m: ["baje", "time", "class", "when"], text: "Pehli class 9:30 baje hai, Room 204, second floor.", en: "First class is at 9:30, Room 204, second floor.", s: ["Canteen kahan hai?", "Bahut shukriya!"], hint: "Class kitne baje shuru hogi?" },
      { m: ["naya", "new", "fresher", "haan", "madad", "help"], text: "Welcome! Koi tension nahi. Kaunsa course hai tumhara?", en: "Welcome! No stress. Which course are you in?", s: ["B.Com. Class kitne baje shuru hogi?", "Computer Science."], hint: "Main yahan naya hoon." },
      { m: ["b.com", "computer", "science", "course", "arts"], text: "Nice! Tumhari class 9:30 baje hai, Room 204.", en: "Nice! Your class is at 9:30, Room 204.", s: ["Canteen kahan hai?", "Bahut shukriya!"] },
    ],
    fallback: { text: "Bolo bolo, kya chahiye? Class, library ya canteen?", en: "Tell me, what do you need? Class, library or canteen?", s: ["Class kitne baje shuru hogi?"] } },
};

// Mumbai survival pack (Hindi, with the Bambaiya and Marathi touches Mumbaikars actually use). Same shape as Delhi's.
window.PACKS.mumbai = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your neighbours and settle into your building.",
    situation: "You've just moved into a flat in Andheri West. Joshi kaka, your building society's secretary, comes to say hello.", scenario: "mum_greetings",
    tip: "Mumbai mixes Hindi and Marathi. “Namaskar” works with everyone, and older Marathi neighbours love a friendly “Kasa kay?”",
    phrases: [
      { hi: "नमस्कार, कैसे हैं आप?", roman: "Namaskar, kaise hain aap?", en: "Greetings, how are you?", natural: "Hello, how are you?" },
      { hi: "मैं यहाँ नया आया हूँ, फ्लैट नंबर बारह में।", roman: "Main yahan naya aaya hoon, flat number barah mein.", en: "I have newly come here, in flat number twelve.", natural: "I've just moved into flat 12.",
        fem: { hi: "मैं यहाँ नई आई हूँ, फ्लैट नंबर बारह में।", roman: "Main yahan nayi aayi hoon, flat number barah mein." } },
      { hi: "कसं काय?", roman: "Kasa kay?", en: "How is it? (Marathi)", natural: "How's it going?" },
      { hi: "सोसाइटी में पानी कब आता है?", roman: "Society mein paani kab aata hai?", en: "When does water come in the society?", natural: "What time is the water supply here?" },
      { hi: "बहुत धन्यवाद!", roman: "Bahut dhanyavaad!", en: "Many thanks!", natural: "Thanks so much!" },
    ] },
  { day: 2, key: "transport", icon: "🚆", title: "Transport", desc: "Take the local train, and get taxis and autos to use the meter.",
    situation: "You need to get from Andheri to Churchgate in the morning rush.", scenario: "mum_taxi",
    tip: "Local trains run on the Western, Central and Harbour lines. “Fast” locals skip stations: check the board (F or S) before you board. Taxis and autos go by the meter.",
    phrases: [
      { hi: "भैया, मीटर से चलोगे?", roman: "Bhaiya, meter se chaloge?", en: "Brother, will you go by the meter?", natural: "Will you go by the meter?" },
      { hi: "चर्चगेट का एक टिकट देना।", roman: "Churchgate ka ek ticket dena.", en: "Give one ticket for Churchgate.", natural: "One ticket to Churchgate, please." },
      { hi: "ये फ़ास्ट लोकल है या स्लो?", roman: "Yeh fast local hai ya slow?", en: "Is this a fast local or a slow one?", natural: "Is this the fast train or the slow one?" },
      { hi: "दादर पे रुकेगी?", roman: "Dadar pe rukegi?", en: "Will it stop at Dadar?", natural: "Does it stop at Dadar?" },
      { hi: "अगला स्टेशन कौन सा है?", roman: "Agla station kaun sa hai?", en: "Which is the next station?", natural: "What's the next station?" },
    ] },
  { day: 3, key: "food", icon: "🍔", title: "Food", desc: "Order street food the Mumbai way.",
    situation: "Evening snack at a vada pav stall outside Dadar station.", scenario: "mum_food",
    tip: "Ask for “sukhi chutney” (the dry garlic chutney) on your vada pav, and order chai as “ek cutting”: half a glass, the Mumbai standard.",
    phrases: [
      { hi: "एक वड़ा पाव देना।", roman: "Ek vada pav dena.", en: "Give one vada pav.", natural: "One vada pav, please." },
      { hi: "सूखी चटनी डालना।", roman: "Sukhi chutney daalna.", en: "Put the dry chutney.", natural: "With the dry chutney, please." },
      { hi: "एक कटिंग चाय।", roman: "Ek cutting chai.", en: "One cutting tea.", natural: "One half-glass chai, please." },
      { hi: "कम तीखा, प्लीज़।", roman: "Kam teekha, please.", en: "Less spicy, please.", natural: "Not too spicy, please." },
      { hi: "कितना हुआ?", roman: "Kitna hua?", en: "How much did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain politely at Mumbai's street markets.",
    situation: "You're at Colaba Causeway looking for a kurta.", scenario: "mum_shopping",
    tip: "At Colaba Causeway and Linking Road, start at about half the first price and settle in the middle, with a smile.",
    phrases: [
      { hi: "ये कितने का है?", roman: "Yeh kitne ka hai?", en: "How much is this?", natural: "How much is this?" },
      { hi: "बहुत महँगा है, भाई।", roman: "Bahut mehenga hai, bhai.", en: "It's very expensive, brother.", natural: "That's too pricey." },
      { hi: "आख़िरी दाम बोलो।", roman: "Aakhri daam bolo.", en: "Say the final price.", natural: "What's your best price?" },
      { hi: "दो लें तो कितना?", roman: "Do lein toh kitna?", en: "If (I) take two, how much?", natural: "How much if I buy two?" },
      { hi: "जीपे चलेगा?", roman: "GPay chalega?", en: "Will GPay work?", natural: "Can I pay with GPay?" },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way around stations and streets.",
    situation: "You came out of Andheri station on the wrong side.", scenario: "mum_directions",
    tip: "Most stations have an East and a West side, so always ask “East ki West?” before you walk. The “bridge” is the footbridge over the tracks.",
    phrases: [
      { hi: "स्टेशन किधर है?", roman: "Station kidhar hai?", en: "Where is the station?", natural: "Which way is the station?" },
      { hi: "ईस्ट साइड या वेस्ट साइड?", roman: "East side ya West side?", en: "East side or west side?", natural: "Is that the east side or the west side?" },
      { hi: "ब्रिज से उस पार जाओ।", roman: "Bridge se us paar jao.", en: "Go to the other side by the bridge.", natural: "Take the footbridge across." },
      { hi: "सीधा जाके राइट लेना।", roman: "Seedha jaake right lena.", en: "Go straight and take a right.", natural: "Go straight, then turn right." },
      { hi: "यहाँ से पैदल कितना टाइम?", roman: "Yahan se paidal kitna time?", en: "How much time on foot from here?", natural: "How long is the walk from here?" },
    ] },
  { day: 6, key: "college", icon: "💼", title: "College & Work", desc: "Settle in with colleagues and classmates.",
    situation: "Your first day at an office in BKC (Bandra Kurla Complex).", scenario: "mum_college",
    tip: "Mumbai runs on time and on lunch dabbas. “Bindaas” means relaxed and carefree, and colleagues use it a lot.",
    phrases: [
      { hi: "मेरा आज पहला दिन है।", roman: "Mera aaj pehla din hai.", en: "Today is my first day.", natural: "It's my first day today." },
      { hi: "मीटिंग कितने बजे है?", roman: "Meeting kitne baje hai?", en: "At what time is the meeting?", natural: "What time's the meeting?" },
      { hi: "कैंटीन किस फ़्लोर पे है?", roman: "Canteen kis floor pe hai?", en: "On which floor is the canteen?", natural: "Which floor is the canteen on?" },
      { hi: "लंच साथ में करें?", roman: "Lunch saath mein karein?", en: "Shall we do lunch together?", natural: "Want to grab lunch together?" },
      { hi: "मुझे थोड़ी मदद चाहिए।", roman: "Mujhe thodi madad chahiye.", en: "I need a little help.", natural: "Could you help me with something?" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "Cutting chai on Marine Drive with Aditya, your new flatmate, as the monsoon begins.", scenario: "mum_smalltalk",
    tip: "Mumbai slang: “bindaas” (carefree), “jhakaas” (awesome) and “kya re?” (what's up?). Use them with friends, not with your boss.",
    phrases: [
      { hi: "आज बहुत बारिश हो रही है, ना?", roman: "Aaj bahut baarish ho rahi hai, na?", en: "It's raining a lot today, no?", natural: "It's really pouring today, isn't it?" },
      { hi: "मुंबई में कितने साल से हो?", roman: "Mumbai mein kitne saal se ho?", en: "Since how many years are you in Mumbai?", natural: "How long have you lived in Mumbai?" },
      { hi: "एकदम झकास!", roman: "Ekdum jhakaas!", en: "Totally awesome!", natural: "That's awesome!" },
      { hi: "वीकेंड पे जुहू चलें?", roman: "Weekend pe Juhu chalein?", en: "Shall we go to Juhu on the weekend?", natural: "Want to go to Juhu this weekend?" },
      { hi: "चल, फिर मिलते हैं!", roman: "Chal, phir milte hain!", en: "Okay, will meet again!", natural: "Alright, see you!" },
    ] },
];

// Mumbai roleplay scenarios (offline engine rules, as for Delhi). Their scene text is also on the server's allowlist (backend/legacy/ai.py).
Object.assign(window.SCENARIOS, {
  mum_greetings: { category: "greetings", icon: "🏢", title: "Meet your society secretary", partner: "Joshi kaka", role: "Society secretary", place: "Your building in Andheri West",
    goal: "Greet politely, introduce yourself and ask about the water timings.",
    opening: { text: "Namaskar! Abhi shift kiya kya? Main Joshi, society ka secretary.", en: "Hello! Have you just moved in? I'm Joshi, the society secretary." },
    start: ["Namaskar, kaise hain aap?", "Haan, flat barah mein shift kiya hai.", "Kasa kay?"],
    rules: [
      { m: ["phir milte", "bye", "chalta", "dhanyavaad", "shukriya", "thank", "samajh"], text: "Arre koi baat nahi! Kuch bhi chahiye toh bindaas bolna. 🙏", en: "No problem at all! If you need anything, just ask freely.", s: ["Phir milte hain!"], end: true, hint: "Bahut dhanyavaad!" },
      { m: ["kasa"], text: "Arre wah, Marathi! Majet. Tumhala Mumbai aavadli ka?", en: "Oh nice, Marathi! I'm doing great. Do you like Mumbai?", s: ["Haan, bahut acchi lagi!", "Thoda naya hai abhi."], hint: "Kasa kay?" },
      { m: ["paani", "water", "kab aata", "timing"], text: "Paani subah chhe se aath aur shaam ko saat se nau aata hai. Tanki bhar lena!", en: "Water comes 6 to 8 in the morning and 7 to 9 in the evening. Fill your tank!", s: ["Achha, samajh aa gaya.", "Bahut dhanyavaad!"], hint: "Society mein paani kab aata hai?" },
      { m: ["flat", "barah", "shift", "naya", "nayi", "new", "aaya", "aayi", "moved"], text: "Swagat hai! Watchman ka naam Ramesh hai, aur society ka maintenance mahine ki paanch tarikh tak dena hota hai.", en: "Welcome! The watchman's name is Ramesh, and the society maintenance is due by the 5th of the month.", s: ["Society mein paani kab aata hai?", "Bahut dhanyavaad!"], hint: "Flat barah mein shift kiya hai." },
      { m: ["namaskar", "namaste", "kaise", "hello", " hi "], text: "Main ekdum badhiya! Aapne kaun sa flat liya hai?", en: "I'm doing very well! Which flat have you moved into?", s: ["Flat number barah mein.", "Kasa kay?"], hint: "Namaskar, kaise hain aap?" },
      { m: ["acchi", "achhi", "badhiya", "good", "nice", "love", "naya hai"], text: "Mumbai sabko apna bana leti hai. Paani ki timing pata hai na?", en: "Mumbai makes everyone its own. You know the water timings, right?", s: ["Society mein paani kab aata hai?"], hint: "Bahut acchi lagi!" },
    ],
    fallback: { text: "Achha achha. Aur batao, kuch chahiye toh? Paani, parking, watchman?", en: "I see. Tell me, do you need anything? Water, parking, the watchman?", s: ["Society mein paani kab aata hai?", "Bahut dhanyavaad!"] } },

  mum_taxi: { category: "transport", icon: "🚕", title: "Kaali-peeli taxi", partner: "Sharma ji", role: "Taxi driver", place: "Outside Andheri station (West)",
    goal: "Get to Churchgate by the meter.", places: ["Churchgate", "Bandra", "Dadar", "Colaba", "Juhu", "Airport", "CST", "Marine Drive"],
    opening: { text: "Haan bolo, kidhar jaana hai?", en: "Yes, tell me, where do you want to go?" },
    start: ["Churchgate jaana hai.", "Bhaiya, meter se chaloge?", "Kitna lagega?"],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "gpay", "upi", "phir milte"], text: "Aapka bhi shukriya! Mumbai mein dhyan rakhna, aur monsoon mein chhatri saath rakhna. 🙏", en: "Thank you too! Take care in Mumbai, and keep an umbrella with you in the monsoon.", s: ["Phir milte hain!"], end: true, hint: "Dhanyavaad bhaiya!" },
      { m: ["meter"], text: "Haan haan, meter se hi chalega. Baitho!", en: "Yes, yes, it'll go by the meter. Get in!", s: ["Kitna time lagega?", "Yahin rok do."], hint: "Bhaiya, meter se chaloge?" },
      { m: ["fix", "zyada", "mehenga", "expensive", "too much", "kam"], text: "Arre nahi, sab meter se. Jo meter bolega wahi.", en: "No, no, everything by the meter. Whatever the meter says.", s: ["Theek hai, chalo.", "Kitna time lagega?"], hint: "Meter se chalo." },
      { m: ["rok", "yahin", "stop", "drop", "utaar"], text: "Lo, aa gaye! Meter mein 312 rupaye hua. GPay bhi chalega.", en: "Here we are! The meter says ₹312. GPay works too.", s: ["GPay le lo, bhaiya.", "Dhanyavaad bhaiya!"], hint: "Yahin rok do." },
      { m: ["time", "kitni der", "minute", "door", "far"], text: "Is time traffic hai, ek ghanta toh lagega. Train jaldi pahunchayegi!", en: "There's traffic at this hour, it'll take an hour. The train would get you there faster!", s: ["Koi baat nahi, chalo.", "Yahin rok do."], hint: "Kitna time lagega?" },
      { m: ["naya", "nayi", "new", "se hoon", "from"], text: "Arre wah! Mumbai mein swagat hai. Juhu ka pav bhaji zaroor khana!", en: "Oh nice! Welcome to Mumbai. Definitely try the pav bhaji at Juhu!", s: ["Zaroor! Kitna time lagega?", "Yahin rok do."], hint: "Mumbai mere liye naya hai." },
      { m: ["kitna", "kitne", "price", "cost", "how much", "lagega"], text: "Meter se jitna aaye, lagbhag teen sau. Chalo?", en: "Whatever the meter shows, around three hundred. Shall we go?", s: ["Theek hai, chalo.", "Bhaiya, meter se chaloge?"], hint: "Kitna lagega?" },
      // the destination rule comes before the general “okay” one: “chaloge” contains “chalo”
      { m: ["churchgate", "bandra", "dadar", "colaba", "juhu", "airport", "cst", "marine", "jaana", "chaloge", "chalenge", "go to", "take me"], text: "{place}? Haan, chalo. Meter se chalega.", en: "{place}? Sure, let's go. By the meter.", s: ["Kitna time lagega?", "Theek hai, chalo."], hint: "Bhaiya, {place} chaloge?" },
      { m: ["theek", "ok", "okay", "chalo", "haan", "fine"], text: "Baitho! Mumbai pehli baar?", en: "Have a seat! First time in Mumbai?", s: ["Haan, Mumbai mere liye naya hai.", "Kitna time lagega?"] },
    ],
    fallback: { text: "Samjha nahi, boss. Kidhar jaana hai?", en: "Didn't get that, boss. Where do you need to go?", s: ["Churchgate jaana hai.", "Bhaiya, meter se chaloge?"] } },

  mum_food: { category: "food", icon: "🍔", title: "Vada pav stall", partner: "Ganesh bhau", role: "Stall owner", place: "Vada pav stall outside Dadar station",
    goal: "Order a vada pav and a cutting chai, and pay.",
    opening: { text: "Bolo boss, kya doon? Garam garam vada nikla hai!", en: "Tell me, boss, what can I get you? Hot vadas just came out!" },
    start: ["Ek vada pav dena.", "Ek cutting chai.", "Kitna hua?"],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "gpay", "upi", "paise", "zaroor"], text: "Thank you boss! Kal bhi aana. 🙏", en: "Thank you, boss! Come again tomorrow.", s: ["Zaroor!"], end: true, hint: "Dhanyavaad!" },
      { m: ["kitna", "kitne", "how much", "bill", "price"], text: "Ek vada pav aur ek cutting, total tees rupaye.", en: "One vada pav and one cutting chai, thirty rupees in total.", s: ["GPay chalega?", "Ye lo, dhanyavaad!"], hint: "Kitna hua?" },
      { m: ["teekha", "spicy", "mirchi", "chilli"], text: "Theek hai, mirchi alag se deta hoon. Aur kuch?", en: "Okay, I'll give the chilli on the side. Anything else?", s: ["Ek cutting chai.", "Kitna hua?"], hint: "Kam teekha, please." },
      { m: ["chutney", "sukhi", "lehsun", "garlic"], text: "Sukhi chutney toh zaroori hai! Hari chutney bhi daalun?", en: "The dry chutney is a must! Shall I add the green chutney too?", s: ["Haan, daal do.", "Kam teekha, please."], hint: "Sukhi chutney daalna." },
      { m: ["cutting", "chai", "tea"], text: "Ek cutting garam garam! Kuch khaane ka bhi?", en: "One hot cutting chai! Anything to eat as well?", s: ["Ek vada pav dena.", "Kitna hua?"], hint: "Ek cutting chai." },
      { m: ["vada", "pav", "do ", "ek "], text: "Ek vada pav! Sukhi chutney daalun?", en: "One vada pav! Shall I add the dry chutney?", s: ["Haan, sukhi chutney daalna.", "Kam teekha, please."], hint: "Ek vada pav dena." },
      { m: ["haan", "yes", "daal", "theek"], text: "Ye lo, garam garam! Aur cutting chai?", en: "Here you go, piping hot! And a cutting chai?", s: ["Ek cutting chai.", "Kitna hua?"] },
    ],
    fallback: { text: "Boss, vada pav, samosa pav ya bhajji? Kya doon?", en: "Boss, vada pav, samosa pav or bhajji? What can I get you?", s: ["Ek vada pav dena.", "Ek cutting chai."] } },

  mum_shopping: { category: "shopping", icon: "🛍️", title: "Bargain at Colaba Causeway", partner: "Imran bhai", role: "Shopkeeper", place: "Colaba Causeway",
    goal: "Buy a kurta at a fair price.",
    opening: { text: "Aao aao, dekho! Ekdum fresh maal hai. Kya chahiye?", en: "Come, come, have a look! Brand-new stock. What do you need?" },
    start: ["Yeh kitne ka hai?", "Koi aur colour hai?", "Bahut mehenga hai, bhai."],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "gpay", "upi", "le leta", "le lunga", "deal", "pack", "phir milte"], text: "Pack kar diya! Phir aana, aapke liye special rate. 🙏", en: "Packed it! Come again, a special rate for you.", s: ["Zaroor, phir milte hain!"], end: true, hint: "Theek hai, pack kar do." },
      { m: ["400", "chaar sau", "char sau", "450"], text: "Chalo, aapke liye saadhe chaar sau. Last price!", en: "Okay, four hundred and fifty for you. Last price!", s: ["Theek hai, pack kar do.", "GPay chalega?"] },
      { m: ["do lein", "do loon", "do loonga", "two", "do piece"], text: "Do loge toh nau sau mein dono le jao!", en: "If you take two, have both for nine hundred!", s: ["Theek hai, pack kar do.", "Bahut mehenga hai, bhai."], hint: "Do lein toh kitna?" },
      { m: ["mehenga", "mehnga", "expensive", "kam", "aakhri", "last", "best price", "too much"], text: "Arre, cotton ka hai! Chalo, aapke liye saat sau.", en: "Come on, it's cotton! Okay, seven hundred for you.", s: ["Chaar sau mein do.", "Do lein toh kitna?"], hint: "Aakhri daam bolo." },
      { m: ["colour", "color", "rang", "size", "neela", "safed", "dikhao"], text: "Haan, neela aur safed bhi hai. Size bhi sab hai.", en: "Yes, there's blue and white too. All sizes as well.", s: ["Yeh kitne ka hai?", "Neela dikhao."], hint: "Koi aur colour hai?" },
      { m: ["kitne", "kitna", "price", "how much", "daam"], text: "Yeh kurta? Sirf baarah sau!", en: "This kurta? Only twelve hundred!", s: ["Bahut mehenga hai, bhai.", "Aakhri daam bolo."], hint: "Yeh kitne ka hai?" },
    ],
    fallback: { text: "Aaram se dekho. Kurta, bag, jewellery, sab hai!", en: "Take your time looking. Kurtas, bags, jewellery, we have it all!", s: ["Yeh kitne ka hai?", "Koi aur colour hai?"] } },

  mum_directions: { category: "directions", icon: "🚉", title: "Find your way at the station", partner: "Kulkarni kaku", role: "Passerby", place: "Outside Andheri station",
    goal: "Find out which side you need and how to get there.",
    opening: { text: "Kya hua beta, kuch chahiye?", en: "What happened, dear? Do you need something?" },
    start: ["Station kidhar hai?", "Mujhe Lokhandwala jaana hai.", "East side ya West side?"],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "phir milte", "achha, theek"], text: "Koi baat nahi beta. Dhyan se jaana! 🙏", en: "No problem, dear. Go carefully!", s: ["Phir milte hain!"], end: true, hint: "Bahut dhanyavaad!" },
      { m: ["time", "paidal", "walk", "kitna", "door", "far"], text: "Paidal das minute. Auto se paanch minute, meter se tees-chaalees rupaye.", en: "Ten minutes on foot. Five minutes by auto, thirty or forty rupees on the meter.", s: ["Achha, theek hai.", "Bahut dhanyavaad!"], hint: "Yahan se paidal kitna time?" },
      { m: ["bridge", "us paar", "other side", "cross"], text: "Haan, platform ke upar wala bridge le lo, aur seedha jaake right lena.", en: "Yes, take the footbridge over the platforms, then go straight and turn right.", s: ["Paidal kitna time?", "Bahut dhanyavaad!"], hint: "Bridge se us paar jao?" },
      { m: ["east", "west", "side"], text: "Lokhandwala West side mein hai. Aap abhi East mein ho, bridge se us paar jao.", en: "Lokhandwala is on the West side. You're on the East side now; cross by the footbridge.", s: ["Bridge kidhar hai?", "Paidal kitna time?"], hint: "East side ya West side?" },
      { m: ["lokhandwala", "jaana", "versova", "juhu", "market"], text: "Lokhandwala? Woh station ke West side pe hai. Aap East mein ho!", en: "Lokhandwala? That's on the West side of the station. You're on the East side!", s: ["Bridge se us paar jaun?", "Paidal kitna time?"], hint: "Mujhe Lokhandwala jaana hai." },
      { m: ["station", "kidhar", "kahan", "where"], text: "Station toh yeh raha! Aapko kis taraf jaana hai?", en: "The station is right here! Which side do you need?", s: ["Mujhe Lokhandwala jaana hai.", "East side ya West side?"], hint: "Station kidhar hai?" },
    ],
    fallback: { text: "Beta, kahan jaana hai batao, main raasta bata deti hoon.", en: "Tell me where you need to go, dear, and I'll show you the way.", s: ["Mujhe Lokhandwala jaana hai.", "Station kidhar hai?"] } },

  mum_college: { category: "college", icon: "💼", title: "First day at the office", partner: "Neha", role: "Colleague", place: "Office in BKC (Bandra Kurla Complex)",
    goal: "Introduce yourself and find out about the meeting and lunch.",
    opening: { text: "Hi! Tum new joinee ho na? Main Neha, same team mein.", en: "Hi! You're the new joiner, right? I'm Neha, same team." },
    start: ["Haan, mera aaj pehla din hai.", "Meeting kitne baje hai?", "Canteen kis floor pe hai?"],
    rules: [
      { m: ["phir milte", "bye", "thank", "dhanyavaad", "shukriya", "great", "badhiya"], text: "Koi baat nahi! Welcome to the team. Bindaas raho! 👋", en: "No problem! Welcome to the team. Stay relaxed!", s: ["Phir milte hain!"], end: true, hint: "Thank you, Neha!" },
      { m: ["lunch", "saath", "khana", "dabba"], text: "Haan, ek baje saath chalte hain! Mera dabba ghar se aata hai, dabbawala laata hai.", en: "Yes, let's go together at one! My lunchbox comes from home; the dabbawala brings it.", s: ["Wah, bahut badhiya!", "Thank you, Neha!"], hint: "Lunch saath mein karein?" },
      { m: ["canteen", "floor", "cafeteria"], text: "Canteen chauthe floor pe hai. Wahan ka vada pav bhi accha hai!", en: "The canteen is on the fourth floor. The vada pav there is good too!", s: ["Lunch saath mein karein?", "Thank you, Neha!"], hint: "Canteen kis floor pe hai?" },
      { m: ["meeting", "kitne baje", "time"], text: "Team meeting gyarah baje hai, conference room B mein.", en: "The team meeting is at eleven, in conference room B.", s: ["Canteen kis floor pe hai?", "Lunch saath mein karein?"], hint: "Meeting kitne baje hai?" },
      { m: ["madad", "help", "laptop", "login", "access"], text: "Haan bolo! IT desk doosre floor pe hai, laptop wahin milega.", en: "Sure, tell me! The IT desk is on the second floor; you'll get your laptop there.", s: ["Meeting kitne baje hai?", "Thank you, Neha!"], hint: "Mujhe thodi madad chahiye." },
      { m: ["pehla", "first", "naya", "nayi", "new", "haan"], text: "Welcome! Pehle din thoda overwhelming lagta hai. Kuch bhi poochna ho toh bata.", en: "Welcome! The first day feels a bit overwhelming. Ask me anything.", s: ["Meeting kitne baje hai?", "Mujhe thodi madad chahiye."], hint: "Mera aaj pehla din hai." },
    ],
    fallback: { text: "Bolo, kya chahiye? Meeting, canteen ya IT desk?", en: "Tell me, what do you need? The meeting, the canteen or the IT desk?", s: ["Meeting kitne baje hai?", "Canteen kis floor pe hai?"] } },

  mum_smalltalk: { category: "smalltalk", icon: "🌊", title: "Chai on Marine Drive", partner: "Aditya", role: "Flatmate", place: "Marine Drive, at the start of the monsoon",
    goal: "Chat about Mumbai and make weekend plans.",
    opening: { text: "Kya re, kaisa laga Mumbai ab tak? Baarish dekh, ekdum shuru ho gayi!", en: "Hey, how's Mumbai so far? Look at the rain, it's really started!" },
    start: ["Aaj bahut baarish ho rahi hai, na?", "Mumbai ekdum jhakaas hai!", "Tum Mumbai mein kitne saal se ho?"],
    rules: [
      { m: ["phir milte", "bye", "chal", "badhiya", "great", "awesome"], text: "Chal, phir milte hain! Ghar pe chai banata hoon. 👋", en: "Alright, see you! I'll make chai at home.", s: ["Bye Aditya!"], end: true, hint: "Chal, phir milte hain!" },
      { m: ["weekend", "juhu", "plan", "free", "kuch nahi"], text: "Bindaas! Juhu chalte hain, pav bhaji khaate hain. Sunday shaam?", en: "Sure! Let's go to Juhu and eat pav bhaji. Sunday evening?", s: ["Ekdum jhakaas!", "Chal, phir milte hain!"], hint: "Weekend pe Juhu chalein?" },
      { m: ["kitne saal", "kab se", "how long", "years"], text: "Main yahin paida hua, pakka Mumbaikar! Tumhare liye toh Mumbai abhi nayi hai na?", en: "I was born here, a true Mumbaikar! Mumbai's still new for you, right?", s: ["Haan, abhi ek hafta hua.", "Weekend pe Juhu chalein?"], hint: "Tum Mumbai mein kitne saal se ho?" },
      { m: ["baarish", "barish", "rain", "monsoon", "paani"], text: "Haan yaar, ab chaar mahine aisa hi! Chhatri hamesha saath rakhna.", en: "Yeah, it'll be like this for four months now! Always keep an umbrella with you.", s: ["Tum Mumbai mein kitne saal se ho?", "Weekend pe Juhu chalein?"], hint: "Aaj bahut baarish ho rahi hai, na?" },
      { m: ["jhakaas", "acchi", "achhi", "accha", "good", "love", "amazing", "nice"], text: "Haha, ekdum sahi! Mumbai meri jaan. Weekend pe kya plan hai?", en: "Haha, absolutely! Mumbai, my love. What's your plan for the weekend?", s: ["Kuch nahi, free hoon.", "Weekend pe Juhu chalein?"], hint: "Mumbai ekdum jhakaas hai!" },
      { m: ["thoda", "abhi nahi", "not yet", "dheere"], text: "Fikar mat kar, ek mahine mein Mumbai tujhe apna bana legi! Weekend pe kya plan hai?", en: "Don't worry, in a month Mumbai will make you its own! What's your weekend plan?", s: ["Kuch nahi, free hoon.", "Weekend pe Juhu chalein?"] },
      { m: ["haan", "hafta", "naya", "new", "week"], text: "Achha! Local train ki aadat padi ya nahi?", en: "Oh nice! Have you got used to the local trains yet?", s: ["Thoda thoda!", "Weekend pe Juhu chalein?"] },
    ],
    fallback: { text: "Haha, sahi hai! Aur bata, Mumbai mein sabse accha kya laga?", en: "Haha, nice! Tell me, what do you like most about Mumbai?", s: ["Mumbai ekdum jhakaas hai!", "Aaj bahut baarish ho rahi hai, na?"] } },
});

// Packs in a city's other languages, by city then language code: the learner's choice picks the pack (frontend/engine.js pack()); a city's
// own PACKS entry (above) is used otherwise. Same shape as every pack: `hi` holds the Devanagari text, which for Marathi is Marathi.
window.LANGUAGE_PACKS = {
  // Mumbai in Marathi: everyday Mumbai Marathi, with the English and Hindi loanwords Mumbaikars actually use (local, meter, bridge).
  mumbai: { mr: [
    { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your neighbours and settle into your building, in Marathi.",
      situation: "You've just moved into a flat in Andheri West. Joshi kaka, your building society's secretary, comes to say hello.", scenario: "mum_mr_greetings",
      tip: "Use “tumhi” (you, polite) with elders and neighbours, and “tu” only with friends. “Kasa kay?” is the friendly Mumbai hello.",
      phrases: [
        { hi: "नमस्कार, कसे आहात?", roman: "Namaskar, kase aahat?", en: "Greetings, how are you?", natural: "Hello, how are you?" },
        { hi: "मी इथे नवीन आलो आहे, फ्लॅट नंबर बारामध्ये.", roman: "Mi ithe navin aalo aahe, flat number baaramadhye.", en: "I have newly come here, in flat number twelve.", natural: "I've just moved into flat 12.",
          fem: { hi: "मी इथे नवीन आले आहे, फ्लॅट नंबर बारामध्ये.", roman: "Mi ithe navin aale aahe, flat number baaramadhye." } },
        { hi: "कसं काय?", roman: "Kasa kay?", en: "How is it?", natural: "How's it going?" },
        { hi: "सोसायटीत पाणी किती वाजता येतं?", roman: "Societyt paani kiti vaajta yeta?", en: "At what time does water come in the society?", natural: "What time is the water supply here?" },
        { hi: "खूप धन्यवाद!", roman: "Khup dhanyavaad!", en: "Many thanks!", natural: "Thanks so much!" },
      ] },
    { day: 2, key: "transport", icon: "🚆", title: "Transport", desc: "Take the local train, and get taxis and autos to use the meter.",
      situation: "You need to get from Andheri to Churchgate in the morning rush.", scenario: "mum_mr_taxi",
      tip: "Ask a taxi “…la yenar ka?” (will you come to …?): that's how Mumbaikars ask. Check the board for F (fast) or S (slow) before you board a local.",
      phrases: [
        { hi: "दादा, मीटरने येणार का?", roman: "Dada, meterne yenar ka?", en: "Brother, will you come by the meter?", natural: "Will you go by the meter?" },
        { hi: "चर्चगेटचं एक तिकीट द्या.", roman: "Churchgatecha ek tikit dya.", en: "Give one ticket of Churchgate.", natural: "One ticket to Churchgate, please." },
        { hi: "ही फास्ट लोकल आहे की स्लो?", roman: "Hi fast local aahe ki slow?", en: "Is this a fast local or a slow one?", natural: "Is this the fast train or the slow one?" },
        { hi: "दादरला थांबेल का?", roman: "Dadarla thaambel ka?", en: "Will it stop at Dadar?", natural: "Does it stop at Dadar?" },
        { hi: "पुढचं स्टेशन कोणतं?", roman: "Pudhcha station konta?", en: "Which is the next station?", natural: "What's the next station?" },
      ] },
    { day: 3, key: "food", icon: "🍔", title: "Food", desc: "Order street food the Mumbai way, in Marathi.",
      situation: "Evening snack at a vada pav stall outside Dadar station.", scenario: "mum_mr_food",
      tip: "“Dya” (please give) is the polite way to order. Ask for “suki chatni”, the dry garlic chutney, and order chai as “ek cutting”.",
      phrases: [
        { hi: "एक वडापाव द्या.", roman: "Ek vadapav dya.", en: "Give one vada pav.", natural: "One vada pav, please." },
        { hi: "सुकी चटणी घाला.", roman: "Suki chatni ghala.", en: "Put the dry chutney.", natural: "With the dry chutney, please." },
        { hi: "एक कटिंग चहा.", roman: "Ek cutting chaha.", en: "One cutting tea.", natural: "One half-glass chai, please." },
        { hi: "कमी तिखट, प्लीज.", roman: "Kami tikhat, please.", en: "Less spicy, please.", natural: "Not too spicy, please." },
        { hi: "किती झाले?", roman: "Kiti zhale?", en: "How much did it become?", natural: "How much is it?" },
      ] },
    { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain politely at a Marathi market.",
      situation: "You're at the Ranade Road market in Dadar, looking for a kurta.", scenario: "mum_mr_shopping",
      tip: "Shopkeepers at Dadar's markets warm up quickly when you bargain in Marathi. Start at about half and settle in the middle, with a smile.",
      phrases: [
        { hi: "हे कितीला आहे?", roman: "He kitila aahe?", en: "For how much is this?", natural: "How much is this?" },
        { hi: "खूप महाग आहे, दादा.", roman: "Khup mahaag aahe, dada.", en: "It's very expensive, brother.", natural: "That's too pricey." },
        { hi: "शेवटचा भाव सांगा.", roman: "Shevatcha bhaav sanga.", en: "Tell the last price.", natural: "What's your best price?" },
        { hi: "दोन घेतले तर किती?", roman: "Don ghetle tar kiti?", en: "If I take two, how much?", natural: "How much if I buy two?" },
        { hi: "जीपे चालेल का?", roman: "GPay chalel ka?", en: "Will GPay work?", natural: "Can I pay with GPay?" },
      ] },
    { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way around stations and streets.",
      situation: "You came out of Andheri station on the wrong side.", scenario: "mum_mr_directions",
      tip: "Most stations have an East and a West side, so ask “Eastla ki Westla?” before you walk. “Pul” is the footbridge over the tracks.",
      phrases: [
        { hi: "स्टेशन कुठे आहे?", roman: "Station kuthe aahe?", en: "Where is the station?", natural: "Which way is the station?" },
        { hi: "ईस्टला की वेस्टला?", roman: "Eastla ki Westla?", en: "To the east or to the west?", natural: "Is that the east side or the west side?" },
        { hi: "पुलावरून पलीकडे जा.", roman: "Pulavarun palikade ja.", en: "Go across by the bridge.", natural: "Take the footbridge across." },
        { hi: "सरळ जाऊन उजवीकडे वळा.", roman: "Saral jaaun ujavikade vala.", en: "Go straight and turn to the right.", natural: "Go straight, then turn right." },
        { hi: "इथून चालत किती वेळ?", roman: "Ithun chaalat kiti vel?", en: "How much time walking from here?", natural: "How long is the walk from here?" },
      ] },
    { day: 6, key: "college", icon: "💼", title: "College & Work", desc: "Settle in with colleagues and classmates, in Marathi.",
      situation: "Your first day at an office in BKC (Bandra Kurla Complex).", scenario: "mum_mr_college",
      tip: "Colleagues often switch between Marathi, Hindi and English mid-sentence. “Mast” means great, and you'll hear it all day.",
      phrases: [
        { hi: "आज माझा पहिला दिवस आहे.", roman: "Aaj maajha pahila divas aahe.", en: "Today is my first day.", natural: "It's my first day today." },
        { hi: "मीटिंग किती वाजता आहे?", roman: "Meeting kiti vaajta aahe?", en: "At what time is the meeting?", natural: "What time's the meeting?" },
        { hi: "कॅन्टीन कोणत्या मजल्यावर आहे?", roman: "Canteen konatya majlyavar aahe?", en: "On which floor is the canteen?", natural: "Which floor is the canteen on?" },
        { hi: "जेवायला एकत्र जाऊया का?", roman: "Jevayla ekatra jaauya ka?", en: "Shall we go to eat together?", natural: "Want to grab lunch together?" },
        { hi: "मला थोडी मदत हवी आहे.", roman: "Mala thodi madat havi aahe.", en: "I need a little help.", natural: "Could you help me with something?" },
      ] },
    { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
      situation: "Cutting chai on Marine Drive with Aditya, your new flatmate, as the monsoon begins.", scenario: "mum_mr_smalltalk",
      tip: "With friends, Marathi turns casual: “Kay re?” (what's up?), “jhakaas” (awesome), “bindhast” (no worries). Keep “tumhi” for elders.",
      phrases: [
        { hi: "आज खूप पाऊस पडतोय, ना?", roman: "Aaj khup paaus padtoy, na?", en: "It's raining a lot today, no?", natural: "It's really pouring today, isn't it?" },
        { hi: "तू मुंबईत किती वर्षांपासून आहेस?", roman: "Tu Mumbait kiti varshanpasun aahes?", en: "Since how many years are you in Mumbai?", natural: "How long have you lived in Mumbai?" },
        { hi: "एकदम झकास!", roman: "Ekdum jhakaas!", en: "Totally awesome!", natural: "That's awesome!" },
        { hi: "वीकेंडला जुहूला जाऊया?", roman: "Weekendla Juhula jaauya?", en: "Shall we go to Juhu on the weekend?", natural: "Want to go to Juhu this weekend?" },
        { hi: "चल, भेटू नंतर!", roman: "Chal, bhetu nantar!", en: "Okay, we'll meet later!", natural: "Alright, see you!" },
      ] },
  ] },
};

// Who has checked a pack's language, by city then language (the English learner view shows the Hindi pack). The same fields as the server's
// content_reviews table (migration 0034): editorial_status "ai_assisted_review" (the team's editorial pass, helped by AI tools),
// native_review_status "pending" until a fluent speaker has reviewed it. Only a real native review may set "approved"; an AI pass never
// counts as one (docs/CONTENT_REVIEW.md lists what the reviewer should check).
window.CONTENT_REVIEW = {
  mumbai: {
    hi: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-18",
      known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Fares and practical tips change over time."],
      note: "Mumbai Hindi (with Bambaiya touches): AI-assisted editorial review only, not yet checked by a native speaker from Mumbai." },
    mr: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-18",
      known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Fares and practical tips change over time."],
      note: "Mumbai Marathi: AI-assisted editorial review only, not yet checked by a native Marathi speaker." },
  },
};

// Mumbai roleplays in Marathi (offline engine rules, romanised as learners type). Their scene text is also on the server's allowlist.
Object.assign(window.SCENARIOS, {
  mum_mr_greetings: { category: "greetings", icon: "🏢", title: "Meet your society secretary (Marathi)", partner: "Joshi kaka", role: "Society secretary", place: "Your building in Andheri West",
    goal: "Greet politely in Marathi, introduce yourself and ask about the water timings.",
    opening: { text: "Namaskar! Tumhi navin aalaat ka? Mi Joshi, societycha secretary.", en: "Hello! Have you just moved in? I'm Joshi, the society secretary." },
    start: ["Namaskar, kase aahat?", "Ho, flat baaramadhye shift kela aahe.", "Kasa kay?"],
    rules: [
      { m: ["bhetu", "bye", "dhanyavaad", "thank", "aabhaar", "samajla", "kalla"], text: "Kahi harkat nahi! Kahi lagla tar bindhast sanga. 🙏", en: "No problem at all! If you need anything, just tell me.", s: ["Bhetu nantar!"], end: true, hint: "Khup dhanyavaad!" },
      { m: ["kasa"], text: "Majet! Tumhala Mumbai aavadli ka?", en: "I'm doing great! Do you like Mumbai?", s: ["Ho, khup aavadli!", "Ajun navin aahe."], hint: "Kasa kay?" },
      { m: ["paani", "pani", "water", "vaajta", "timing"], text: "Paani sakali saha te aath aani sandhyakali saat te nau yeta. Taaki bharun theva!", en: "Water comes 6 to 8 in the morning and 7 to 9 in the evening. Keep your tank filled!", s: ["Ho, kalla.", "Khup dhanyavaad!"], hint: "Societyt paani kiti vaajta yeta?" },
      // before the "new here" rule: "ajun navin aahe" (still new) is about liking Mumbai, not about the flat
      { m: ["aavadli", "avadli", "chhan", "good", "nice", "love", "ajun navin"], text: "Mumbai saglyanna aaplasa karte. Paanyachi vel mahit aahe na?", en: "Mumbai makes everyone its own. You know the water timings, right?", s: ["Societyt paani kiti vaajta yeta?"], hint: "Ho, khup aavadli!" },
      { m: ["flat", "baara", "shift", "navin", "new", "aalo", "aale", "moved"], text: "Swagat aahe! Watchmanche naav Ramesh aahe, aani maintenance mahinyachya paach tarkhepparyant dyaycha asta.", en: "Welcome! The watchman's name is Ramesh, and the maintenance is due by the 5th of the month.", s: ["Societyt paani kiti vaajta yeta?", "Khup dhanyavaad!"], hint: "Flat baaramadhye shift kela aahe." },
      { m: ["namaskar", "namaste", "kase", "hello", " hi "], text: "Mi ekdum majet! Tumhi konatya flatmadhye aalaat?", en: "I'm doing great! Which flat have you moved into?", s: ["Flat number baaramadhye.", "Kasa kay?"], hint: "Namaskar, kase aahat?" },
    ],
    fallback: { text: "Bara. Aani kahi hava asel tar sanga. Paani, parking, watchman?", en: "I see. Tell me if you need anything else. Water, parking, the watchman?", s: ["Societyt paani kiti vaajta yeta?", "Khup dhanyavaad!"] } },

  mum_mr_taxi: { category: "transport", icon: "🚕", title: "Kaali-peeli taxi (Marathi)", partner: "Shinde kaka", role: "Taxi driver", place: "Outside Andheri station (West)",
    goal: "Get to Churchgate by the meter, in Marathi.", places: ["Churchgate", "Bandra", "Dadar", "Colaba", "Juhu", "Airport", "CST", "Marine Drive"],
    opening: { text: "Bola, kuthe jaaycha aahe?", en: "Tell me, where do you want to go?" },
    start: ["Churchgatela jaaycha aahe.", "Dada, meterne yenar ka?", "Kiti hotil?"],
    rules: [
      { m: ["dhanyavaad", "thank", "gpay", "upi", "bhetu", "aabhaar"], text: "Tumche pan aabhaar! Mumbait kaalji ghya, aani pavsalyat chhatri javal theva. 🙏", en: "Thank you too! Take care in Mumbai, and keep an umbrella with you in the monsoon.", s: ["Bhetu nantar!"], end: true, hint: "Dhanyavaad dada!" },
      { m: ["meter"], text: "Ho ho, meternech jaaycha. Basa!", en: "Yes, yes, by the meter of course. Get in!", s: ["Kiti vel lagel?", "Ithech thaamba."], hint: "Dada, meterne yenar ka?" },
      { m: ["fix", "jaast", "mahaag", "expensive", "too much", "kami"], text: "Nahi ho, sagla meterne. Meter je dakhvel tevdhech.", en: "No, everything by the meter. Just what the meter shows.", s: ["Theek aahe, chala.", "Kiti vel lagel?"], hint: "Meterne chala." },
      { m: ["thaamba", "thamba", "ithech", "stop", "drop", "utarva"], text: "He ghya, aalo! Meterwar 312 rupaye zhale. GPay pan chalel.", en: "Here we are! The meter says ₹312. GPay works too.", s: ["GPay ghya, dada.", "Dhanyavaad dada!"], hint: "Ithech thaamba." },
      { m: ["vel", "minute", "laamb", "far", "time"], text: "Ya veli traffic aahe, ek taas tari lagel. Trainne lavkar pohochal!", en: "There's traffic at this hour, it'll take at least an hour. You'd get there faster by train!", s: ["Harkat nahi, chala.", "Ithech thaamba."], hint: "Kiti vel lagel?" },
      { m: ["navin", "new", "from"], text: "Arre wa! Mumbait swagat aahe. Juhuchi pav bhaji nakki khaa!", en: "Oh nice! Welcome to Mumbai. Definitely try the pav bhaji at Juhu!", s: ["Nakki! Kiti vel lagel?", "Ithech thaamba."], hint: "Mi ithe navin aahe." },
      { m: ["kiti", "price", "cost", "how much", "bhaada"], text: "Meter je dakhvel te, saadharan teenshe. Chalaycha?", en: "Whatever the meter shows, about three hundred. Shall we go?", s: ["Theek aahe, chala.", "Dada, meterne yenar ka?"], hint: "Kiti hotil?" },
      { m: ["churchgate", "bandra", "dadar", "colaba", "juhu", "airport", "cst", "marine", "jaaycha", "yenar", "go to", "take me"], text: "{place}? Ho, chala. Meterne jaauya.", en: "{place}? Sure, let's go. By the meter.", s: ["Kiti vel lagel?", "Theek aahe, chala."], hint: "Dada, {place}la yenar ka?" },
      { m: ["theek", "ok", "okay", "chala", " ho", "fine"], text: "Basa! Tumhi Mumbait navin aahat ka?", en: "Have a seat! Are you new to Mumbai?", s: ["Ho, mi ithe navin aahe.", "Kiti vel lagel?"] },
    ],
    fallback: { text: "Samajla nahi. Kuthe jaaycha aahe?", en: "Didn't get that. Where do you need to go?", s: ["Churchgatela jaaycha aahe.", "Dada, meterne yenar ka?"] } },

  mum_mr_food: { category: "food", icon: "🍔", title: "Vada pav stall (Marathi)", partner: "Ganesh bhau", role: "Stall owner", place: "Vada pav stall outside Dadar station",
    goal: "Order a vada pav and a cutting chai in Marathi, and pay.",
    opening: { text: "Bola, kay deu? Garam garam vade aale aahet!", en: "Tell me, what can I get you? Hot vadas just came out!" },
    start: ["Ek vadapav dya.", "Ek cutting chaha.", "Kiti zhale?"],
    rules: [
      { m: ["dhanyavaad", "thank", "gpay", "upi", "paise", "nakki"], text: "Dhanyavaad! Udya pan ya. 🙏", en: "Thank you! Come again tomorrow.", s: ["Nakki!"], end: true, hint: "Dhanyavaad!" },
      { m: ["kiti", "how much", "bill", "price"], text: "Ek vadapav aani ek cutting, ekun tees rupaye.", en: "One vada pav and one cutting chai, thirty rupees in total.", s: ["GPay chalel ka?", "He ghya, dhanyavaad!"], hint: "Kiti zhale?" },
      { m: ["tikhat", "spicy", "mirchi", "chilli"], text: "Theek aahe, mirchi vegli deto. Aani kahi?", en: "Okay, I'll give the chilli on the side. Anything else?", s: ["Ek cutting chaha.", "Kiti zhale?"], hint: "Kami tikhat, please." },
      { m: ["chatni", "chutney", "suki", "lasun", "garlic"], text: "Suki chatni tar havich! Hirvi chatni pan ghalu?", en: "The dry chutney is a must! Shall I add the green chutney too?", s: ["Ho, ghala.", "Kami tikhat, please."], hint: "Suki chatni ghala." },
      { m: ["cutting", "chaha", "chai", "tea"], text: "Ek cutting garam garam! Khayla pan kahi?", en: "One hot cutting chai! Anything to eat as well?", s: ["Ek vadapav dya.", "Kiti zhale?"], hint: "Ek cutting chaha." },
      { m: ["vada", "pav", "don ", "ek "], text: "Ek vadapav! Suki chatni ghalu?", en: "One vada pav! Shall I add the dry chutney?", s: ["Ho, suki chatni ghala.", "Kami tikhat, please."], hint: "Ek vadapav dya." },
      { m: [" ho", "yes", "ghala", "theek"], text: "He ghya, garam garam! Aani cutting chaha?", en: "Here you go, piping hot! And a cutting chai?", s: ["Ek cutting chaha.", "Kiti zhale?"] },
    ],
    fallback: { text: "Vadapav, samosa pav ki bhaji? Kay deu?", en: "Vada pav, samosa pav or bhaji? What can I get you?", s: ["Ek vadapav dya.", "Ek cutting chaha."] } },

  mum_mr_shopping: { category: "shopping", icon: "🛍️", title: "Bargain at Dadar market (Marathi)", partner: "Pawar kaka", role: "Shopkeeper", place: "Ranade Road market, Dadar",
    goal: "Buy a kurta at a fair price, in Marathi.",
    opening: { text: "Ya ya, bagha! Ekdum navin maal aahe. Kay pahije?", en: "Come, come, have a look! Brand-new stock. What do you need?" },
    start: ["He kitila aahe?", "Dusra rang aahe ka?", "Khup mahaag aahe, dada."],
    rules: [
      { m: ["dhanyavaad", "thank", "gpay", "upi", "ghein", "gheto", "deal", "pack", "bhetu"], text: "Pack kela! Parat ya, tumchyasathi special bhaav. 🙏", en: "Packed it! Come again, a special price for you.", s: ["Nakki, bhetu parat!"], end: true, hint: "Theek aahe, pack kara." },
      { m: ["400", "450", "chaarshe", "saadechaarshe"], text: "Chala, tumchyasathi saadechaarshe. Shevatcha bhaav!", en: "Okay, four hundred and fifty for you. Final price!", s: ["Theek aahe, pack kara.", "GPay chalel ka?"] },
      { m: ["don ", "two"], text: "Don ghetle tar donhi naushela!", en: "If you take two, both for nine hundred!", s: ["Theek aahe, pack kara.", "Khup mahaag aahe, dada."], hint: "Don ghetle tar kiti?" },
      { m: ["mahaag", "mahag", "expensive", "kami", "shevatcha", "last", "best price", "too much"], text: "Arre dada, cotton aahe! Chala, tumchyasathi saatshe.", en: "Come on, it's cotton! Okay, seven hundred for you.", s: ["Chaarshela dya.", "Don ghetle tar kiti?"], hint: "Shevatcha bhaav sanga." },
      { m: ["rang", "colour", "color", "size", "nila", "pandhra", "dakhva"], text: "Ho, nila aani pandhra pan aahe. Saglya size aahet.", en: "Yes, there's blue and white too. All sizes as well.", s: ["He kitila aahe?", "Nila dakhva."], hint: "Dusra rang aahe ka?" },
      { m: ["kitila", "kiti", "price", "how much", "bhaav"], text: "Ha kurta? Fakt baaraashe!", en: "This kurta? Only twelve hundred!", s: ["Khup mahaag aahe, dada.", "Shevatcha bhaav sanga."], hint: "He kitila aahe?" },
    ],
    fallback: { text: "Aaramat bagha. Kurta, saadi, bag, sagla aahe!", en: "Take your time looking. Kurtas, saris, bags, we have it all!", s: ["He kitila aahe?", "Dusra rang aahe ka?"] } },

  mum_mr_directions: { category: "directions", icon: "🚉", title: "Find your way at the station (Marathi)", partner: "Kulkarni kaku", role: "Passerby", place: "Outside Andheri station",
    goal: "Find out in Marathi which side you need and how to get there.",
    opening: { text: "Kay zhala bala, kahi shodhtay ka?", en: "What happened, dear? Are you looking for something?" },
    start: ["Station kuthe aahe?", "Mala Lokhandwalala jaaycha aahe.", "Eastla ki Westla?"],
    rules: [
      { m: ["dhanyavaad", "thank", "bhetu", "bara, theek"], text: "Kahi harkat nahi bala. Saambhalun ja! 🙏", en: "No problem, dear. Go carefully!", s: ["Bhetu nantar!"], end: true, hint: "Khup dhanyavaad!" },
      { m: ["vel", "chaalat", "walk", "kiti", "laamb", "far"], text: "Chaalat daha minita. Rikshane paach minita, meterne tees-chaalees rupaye.", en: "Ten minutes on foot. Five minutes by auto, thirty or forty rupees on the meter.", s: ["Bara, theek aahe.", "Khup dhanyavaad!"], hint: "Ithun chaalat kiti vel?" },
      { m: ["pul", "bridge", "palikade", "other side", "cross"], text: "Ho, platformvarcha pul ghya, aani saral jaaun ujavikade vala.", en: "Yes, take the footbridge over the platforms, then go straight and turn right.", s: ["Chaalat kiti vel?", "Khup dhanyavaad!"], hint: "Pulavarun palikade jaau?" },
      { m: ["east", "west", "side"], text: "Lokhandwala Westla aahe. Tumhi aata Eastla aahat, pulavarun palikade ja.", en: "Lokhandwala is on the West side. You're on the East side now; cross by the footbridge.", s: ["Pul kuthe aahe?", "Chaalat kiti vel?"], hint: "Eastla ki Westla?" },
      { m: ["lokhandwala", "jaaycha", "versova", "juhu", "market"], text: "Lokhandwala? Te stationchya Westla aahe. Tumhi Eastla aahat!", en: "Lokhandwala? That's on the West side of the station. You're on the East side!", s: ["Pulavarun palikade jaau ka?", "Chaalat kiti vel?"], hint: "Mala Lokhandwalala jaaycha aahe." },
      { m: ["station", "kuthe", "where"], text: "Station tar ithech aahe! Tumhala konatya baajula jaaycha aahe?", en: "The station is right here! Which side do you need?", s: ["Mala Lokhandwalala jaaycha aahe.", "Eastla ki Westla?"], hint: "Station kuthe aahe?" },
    ],
    fallback: { text: "Bala, kuthe jaaycha aahe sang, mi rasta sangte.", en: "Tell me where you need to go, dear, and I'll show you the way.", s: ["Mala Lokhandwalala jaaycha aahe.", "Station kuthe aahe?"] } },

  mum_mr_college: { category: "college", icon: "💼", title: "First day at the office (Marathi)", partner: "Sayali", role: "Colleague", place: "Office in BKC (Bandra Kurla Complex)",
    goal: "Introduce yourself in Marathi and find out about the meeting and lunch.",
    opening: { text: "Hi! Tu navin joinee aahes na? Mi Sayali, aaplya teammadhli.", en: "Hi! You're the new joiner, right? I'm Sayali, from our team." },
    start: ["Ho, aaj maajha pahila divas aahe.", "Meeting kiti vaajta aahe?", "Canteen konatya majlyavar aahe?"],
    rules: [
      { m: ["bhetu", "bye", "thank", "dhanyavaad", "great", "mast"], text: "Kahi harkat nahi! Teammadhye swagat. Bindhast raha! 👋", en: "No problem! Welcome to the team. Stay relaxed!", s: ["Bhetu nantar!"], end: true, hint: "Thank you, Sayali!" },
      { m: ["jevayla", "jevan", "lunch", "ekatra", "dabba"], text: "Ho, ek vaajta ekatra jaauya! Maajha dabba gharun yeto, dabbawala aanto.", en: "Yes, let's go together at one! My lunchbox comes from home; the dabbawala brings it.", s: ["Wa, mast!", "Thank you, Sayali!"], hint: "Jevayla ekatra jaauya ka?" },
      { m: ["canteen", "majla", "majlya", "floor", "cafeteria"], text: "Canteen chauthya majlyavar aahe. Tithla vadapav pan chhan aahe!", en: "The canteen is on the fourth floor. The vada pav there is good too!", s: ["Jevayla ekatra jaauya ka?", "Thank you, Sayali!"], hint: "Canteen konatya majlyavar aahe?" },
      { m: ["meeting", "vaajta", "time"], text: "Team meeting akra vaajta aahe, conference room Bmadhye.", en: "The team meeting is at eleven, in conference room B.", s: ["Canteen konatya majlyavar aahe?", "Jevayla ekatra jaauya ka?"], hint: "Meeting kiti vaajta aahe?" },
      { m: ["madat", "help", "laptop", "login", "access"], text: "Ho, sang na! IT desk dusrya majlyavar aahe, laptop tithech milel.", en: "Sure, tell me! The IT desk is on the second floor; you'll get your laptop there.", s: ["Meeting kiti vaajta aahe?", "Thank you, Sayali!"], hint: "Mala thodi madat havi aahe." },
      { m: ["pahila", "first", "navin", "new", " ho"], text: "Swagat! Pahilya divashi thoda overwhelming vatta. Kahi pan vichar.", en: "Welcome! The first day feels a bit overwhelming. Ask me anything.", s: ["Meeting kiti vaajta aahe?", "Mala thodi madat havi aahe."], hint: "Aaj maajha pahila divas aahe." },
    ],
    fallback: { text: "Bol, kay hava? Meeting, canteen ki IT desk?", en: "Tell me, what do you need? The meeting, the canteen or the IT desk?", s: ["Meeting kiti vaajta aahe?", "Canteen konatya majlyavar aahe?"] } },

  mum_mr_smalltalk: { category: "smalltalk", icon: "🌊", title: "Chai on Marine Drive (Marathi)", partner: "Aditya", role: "Flatmate", place: "Marine Drive, at the start of the monsoon",
    goal: "Chat in Marathi about Mumbai and make weekend plans.",
    opening: { text: "Kay re, kashi vatli Mumbai ajun paryant? Paaus bagh, ekdum suru zhala!", en: "Hey, how do you find Mumbai so far? Look at the rain, it's really started!" },
    start: ["Aaj khup paaus padtoy, na?", "Mumbai ekdum jhakaas aahe!", "Tu Mumbait kiti varshanpasun aahes?"],
    rules: [
      { m: ["bhetu", "bye", "chal,", "mast", "great", "awesome"], text: "Chal, bhetu nantar! Ghari chaha banavto. 👋", en: "Alright, see you later! I'll make chai at home.", s: ["Bye Aditya!"], end: true, hint: "Chal, bhetu nantar!" },
      { m: ["weekend", "juhu", "plan", "free", "kahi nahi"], text: "Bindhast! Juhula jaauya, pav bhaji khauya. Ravivari sandhyakali?", en: "Sure! Let's go to Juhu and eat pav bhaji. Sunday evening?", s: ["Ekdum jhakaas!", "Chal, bhetu nantar!"], hint: "Weekendla Juhula jaauya?" },
      { m: ["varsh", "kadhipasun", "how long", "years"], text: "Mi ithech janmalo, pakka Mumbaikar! Tu tar ajun navin aahes na?", en: "I was born right here, a true Mumbaikar! You're still new, right?", s: ["Ho, aata ek aathavda zhala.", "Weekendla Juhula jaauya?"], hint: "Tu Mumbait kiti varshanpasun aahes?" },
      { m: ["paaus", "paus", "rain", "monsoon", "paani"], text: "Ho re, aata chaar mahine asach! Chhatri nehmi javal thev.", en: "Yeah, it'll be like this for four months now! Always keep an umbrella with you.", s: ["Tu Mumbait kiti varshanpasun aahes?", "Weekendla Juhula jaauya?"], hint: "Aaj khup paaus padtoy, na?" },
      { m: ["jhakaas", "chhan", "aavadli", "good", "love", "amazing", "nice"], text: "Haha, ekdum barobar! Aamchi Mumbai! Weekendla kay plan aahe?", en: "Haha, absolutely! That's our Mumbai! What's your plan for the weekend?", s: ["Kahi nahi, free aahe.", "Weekendla Juhula jaauya?"], hint: "Mumbai ekdum jhakaas aahe!" },
      { m: ["thoda", "ajun nahi", "not yet", "halu"], text: "Kaalji karu nakos, ek mahinyat tu pan pakka Mumbaikar hoshil! Weekendla kay plan aahe?", en: "Don't worry, in a month you'll be a true Mumbaikar too! What's your weekend plan?", s: ["Kahi nahi, free aahe.", "Weekendla Juhula jaauya?"] },
      { m: [" ho", "aathavda", "navin", "new", "week"], text: "Arre wa! Local trainchi savay zhali ka?", en: "Oh nice! Have you got used to the local trains yet?", s: ["Thoda thoda!", "Weekendla Juhula jaauya?"] },
    ],
    fallback: { text: "Haha, barobar! Aani sang, Mumbait sagalyat jaast kay aavadla?", en: "Haha, right! Tell me, what do you like most about Mumbai?", s: ["Mumbai ekdum jhakaas aahe!", "Aaj khup paaus padtoy, na?"] } },
});

// City-and-language content beyond the First Week pack: the tutor's ready-made answers, readings, the level check and achievement names.
// By city, then by the language the learner is taught in ("hi" also serves the English view). Anything missing falls back to the shared
// (Delhi) content above, so a city without an entry behaves exactly as before. The tutor's `build` answers name a destination.
const PLACE_MUM = {
  churchgate: ["Churchgate", "चर्चगेट", "Churchgate"], bandra: ["Bandra", "बांद्रा", "Bandra"], dadar: ["Dadar", "दादर", "Dadar"],
  colaba: ["Colaba", "कोलाबा", "Colaba"], juhu: ["Juhu", "जुहू", "Juhu"], airport: ["airport", "एयरपोर्ट", "the airport"], cst: ["CST", "सीएसटी", "CST station"],
  "marine drive": ["Marine Drive", "मरीन ड्राइव", "Marine Drive"], andheri: ["Andheri", "अंधेरी", "Andheri"], bkc: ["BKC", "बीकेसी", "BKC"],
  "gateway of india": ["Gateway of India", "गेटवे ऑफ़ इंडिया", "the Gateway of India"],
};
// Marathi adds -la ("to") to the place, and a few places change their ending first (Bandra → Bandryala, Colaba → Kulabyala).
const PLACE_MUM_MR = {
  churchgate: ["Churchgatela", "चर्चगेटला", "Churchgate"], bandra: ["Bandryala", "बांद्र्याला", "Bandra"], dadar: ["Dadarla", "दादरला", "Dadar"],
  colaba: ["Kulabyala", "कुलाब्याला", "Colaba"], juhu: ["Juhula", "जुहूला", "Juhu"], airport: ["airportla", "एअरपोर्टला", "the airport"], cst: ["CSTla", "सीएसटीला", "CST station"],
  "marine drive": ["Marine Drivela", "मरीन ड्राइव्हला", "Marine Drive"], andheri: ["Andherila", "अंधेरीला", "Andheri"], bkc: ["BKCla", "बीकेसीला", "BKC"],
  "gateway of india": ["Gateway of Indiala", "गेटवे ऑफ इंडियाला", "the Gateway of India"],
};
const MUMBAI_PLACES = ["Churchgate", "Bandra", "Dadar", "Colaba", "Juhu", "Airport", "CST", "Marine Drive", "Andheri", "BKC", "Gateway of India"];
const MUM_RIDE_NOTE = "In Mumbai autos and kaali-peeli taxis go by the meter: ask for it before you sit in. Autos don't run in South Mumbai (south of Bandra and Sion), so take a taxi there.";
const MUM_TRAIN_NOTE = "Western line: Churchgate ↔ Virar. Central line: CST ↔ Kalyan and beyond. Harbour line: CST ↔ Panvel. Check F (fast) or S (slow) on the board; ladies' coaches are marked on the platform and the train.";

window.LOCAL_CONTENT = {
  mumbai: {
    // ---------- Mumbai, in Hindi (and the English view) ----------
    hi: {
      tutor: {
        greet: "Namaskar", places: MUMBAI_PLACES, defaultPlace: "Churchgate",
        starters: ["I need a taxi to Churchgate.", "How do I order a vada pav less spicy?", "How do I bargain at Colaba Causeway?", "What does 'bindaas' mean?", "How do I ask if a local train is fast or slow?"],
        glossary: {
          bindaas: "“Carefree / no worries” — very Mumbai. “Bindaas bolo” = just say it.", jhakaas: "“Awesome!” Mumbai slang, with friends.",
          "kya re": "“What's up?” — friendly, with friends only.", cutting: "Half a glass of chai, the Mumbai standard (“ek cutting”).",
          local: "Mumbai's suburban train. “Fast” locals skip stations, “slow” ones stop everywhere.", "kaali peeli": "The black-and-yellow Mumbai taxi. Goes by the meter.",
          dabbawala: "The men who deliver home-cooked lunch boxes across Mumbai, on time, every day.", jugaad: "A clever, improvised fix. Mumbai runs on it too.",
        },
        intents: [
          { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
            build: (dest) => { const d = PLACE_MUM[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
              { roman: `Bhaiya, ${r} chaloge? Meter se.`, hi: d ? `भैया, ${d[1]} चलोगे? मीटर से।` : "", en: `Will you go to ${d ? d[2] : dest}? By the meter.` },
              { roman: `Bhaiya, ${r} tak chalenge?`, hi: d ? `भैया, ${d[1]} तक चलेंगे?` : "", en: `A more polite version: Would you take me to ${d ? d[2] : dest}?`, label: "More polite" },
              { roman: "Meter chalu kijiye.", hi: "मीटर चालू कीजिए।", en: "Please start the meter." },
            ], note: MUM_RIDE_NOTE }; } },
          { m: ["local", "train", "metro", "platform", "fast", "slow"], topic: "transport", intro: "At the station, try:", phrases: [
              { roman: "Churchgate ke liye kaun si local?", hi: "चर्चगेट के लिए कौन सी लोकल?", en: "Which local for Churchgate?" },
              { roman: "Ye fast hai ya slow?", hi: "ये फ़ास्ट है या स्लो?", en: "Is this a fast or a slow one?" },
              { roman: "Dadar pe rukegi?", hi: "दादर पे रुकेगी?", en: "Does it stop at Dadar?" },
            ], note: MUM_TRAIN_NOTE },
          { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
              { roman: "Thoda kam karo na.", hi: "थोड़ा कम करो ना।", en: "Please lower it a little." },
              { roman: "Bahut mehenga hai, bhai.", hi: "बहुत महँगा है, भाई।", en: "It's too expensive, brother." },
              { roman: "Aakhri daam bolo.", hi: "आख़िरी दाम बोलो।", en: "What's your best price?" },
            ], note: "At Colaba Causeway and Linking Road start around half the first price, smile, and be ready to walk away." },
          { m: ["price", "how much", "cost", "kitna", "kitne", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
              { roman: "Ye kitne ka hai?", hi: "ये कितने का है?", en: "How much is this?" },
              { roman: "UPI chalega?", hi: "यूपीआई चलेगा?", en: "Can I pay by UPI?" },
            ] },
          { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "vada", "pav", "bill"], topic: "food", intro: "Ordering food:", phrases: [
              { roman: "Ek vada pav dena.", hi: "एक वड़ा पाव देना।", en: "One vada pav, please." },
              { roman: "Kam teekha, please.", hi: "कम तीखा, प्लीज़।", en: "Less spicy, please." },
              { roman: "Bill de dijiye.", hi: "बिल दे दीजिए।", en: "Can I have the bill?" },
            ], note: "Ask for “sukhi chutney” on your vada pav. “Dena” is casual (stalls); “dijiye” is polite (restaurants)." },
          { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
              { roman: "Station kidhar hai?", hi: "स्टेशन किधर है?", en: "Which way is the station?" },
              { roman: "Main raasta bhool gaya hoon.", hi: "मैं रास्ता भूल गया हूँ।", en: "I'm lost. (women say: bhool gayi hoon)" },
              { roman: "East side ya West side?", hi: "ईस्ट साइड या वेस्ट साइड?", en: "The east side or the west side?" },
            ], note: "Most stations have an East and a West side, so ask before you walk. The “bridge” is the footbridge over the tracks." },
          { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At work or college:", phrases: [
              { roman: "Mera aaj pehla din hai.", hi: "मेरा आज पहला दिन है।", en: "It's my first day today." },
              { roman: "Meeting kitne baje hai?", hi: "मीटिंग कितने बजे है?", en: "What time's the meeting?" },
              { roman: "Kya aap meri madad kar sakte hain?", hi: "क्या आप मेरी मदद कर सकते हैं?", en: "Could you help me?" },
            ] },
          { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
              { roman: "Aap kahan se ho?", hi: "आप कहाँ से हो?", en: "Where are you from?" },
              { roman: "Aaj bahut baarish ho rahi hai, na?", hi: "आज बहुत बारिश हो रही है, ना?", en: "It's really pouring today, isn't it?" },
              { roman: "Ek cutting chai piyenge?", hi: "एक कटिंग चाय पिएँगे?", en: "Fancy a cutting chai?" },
            ], note: "Mumbai small talk: the rain, the locals and food. “Kya re?” is a friendly “what's up?” with friends." },
          { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
              { roman: "Mera naam Alex hai.", hi: "मेरा नाम एलेक्स है।", en: "My name is Alex." },
              { roman: "Aapka naam kya hai?", hi: "आपका नाम क्या है?", en: "What's your name?" },
              { roman: "Aapse milkar accha laga.", hi: "आपसे मिलकर अच्छा लगा।", en: "Nice to meet you." },
            ] },
          { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
              { roman: "Bahut dhanyavaad!", hi: "बहुत धन्यवाद!", en: "Thanks a lot!" },
              { roman: "Maaf kijiye.", hi: "माफ़ कीजिए।", en: "Sorry / Excuse me." },
              { roman: "Suniye…", hi: "सुनिए…", en: "Excuse me… (to get attention)" },
            ] },
          { m: ["hello", "hi", "greet", "namaste", "namaskar", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Mumbai:", phrases: [
              { roman: "Namaskar, kaise hain aap?", hi: "नमस्कार, कैसे हैं आप?", en: "Hello, how are you?" },
              { roman: "Phir milte hain!", hi: "फिर मिलते हैं!", en: "See you later!" },
            ], note: "“Namaskar” works with everyone; older Marathi neighbours love a friendly “Kasa kay?”." },
          { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
              { roman: "Mujhe madad chahiye.", hi: "मुझे मदद चाहिए।", en: "I need help." },
              { roman: "Paas mein hospital kahan hai?", hi: "पास में हॉस्पिटल कहाँ है?", en: "Where's the nearest hospital?" },
            ], note: "Emergency number in India: 112." },
        ],
        generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
            { roman: "Namaskar, kaise hain aap?", hi: "नमस्कार, कैसे हैं आप?", en: "Hello, how are you?" },
            { roman: "Kitna hua?", hi: "कितना हुआ?", en: "How much is it?" },
            { roman: "Kya aap meri madad kar sakte hain?", hi: "क्या आप मेरी मदद कर सकते हैं?", en: "Could you help me?" },
          ], note: "Tell me a situation — like “I want to order a vada pav” or “ask the way to Churchgate” — and I'll give you the exact words." },
      },
      readings: [
        { title: "Asha in Mumbai", level: "A1", lines: [
            { hi: "आशा मुंबई में नई है।", roman: "Asha Mumbai mein nayi hai.", en: "Asha is new in Mumbai." },
            { hi: "वह ऑफ़िस जा रही है।", roman: "Vah office ja rahi hai.", en: "She is going to the office." },
            { hi: "वह लोकल ट्रेन लेती है।", roman: "Vah local train leti hai.", en: "She takes the local train." },
            { hi: "वह पूछती है, “ये फ़ास्ट लोकल है?”", roman: "Vah poochti hai, “Ye fast local hai?”", en: "She asks, “Is this a fast local?”" },
            { hi: "एक आंटी कहती हैं, “नहीं, स्लो है।”", roman: "Ek aunty kehti hain, “Nahi, slow hai.”", en: "An aunty says, “No, it's a slow one.”" },
          ],
          questions: [
            { q: "Where is Asha new?", options: ["Delhi", "Mumbai", "Chennai"], a: 1 },
            { q: "How does Asha travel?", options: ["By local train", "By bus", "By auto"], a: 0 },
            { q: "What kind of train is it?", options: ["Fast", "Slow", "Express"], a: 1 },
          ] },
        { title: "A snack at Dadar", level: "A1", lines: [
            { hi: "रोहन को भूख लगी है।", roman: "Rohan ko bhookh lagi hai.", en: "Rohan is hungry." },
            { hi: "वह दादर स्टेशन के बाहर जाता है।", roman: "Vah Dadar station ke baahar jaata hai.", en: "He goes outside Dadar station." },
            { hi: "वह वड़ा पाव और कटिंग चाय लेता है।", roman: "Vah vada pav aur cutting chai leta hai.", en: "He has a vada pav and a cutting chai." },
            { hi: "सब मिलाकर तीस रुपये हुए।", roman: "Sab milaakar tees rupaye hue.", en: "It all came to thirty rupees." },
          ],
          questions: [
            { q: "How does Rohan feel?", options: ["Tired", "Hungry", "Cold"], a: 1 },
            { q: "What does he eat?", options: ["Vada pav", "Biryani", "Idli"], a: 0 },
            { q: "How much did it cost?", options: ["₹13", "₹30", "₹300"], a: 1 },
          ] },
      ],
      placement: [
        { q: "What does “Namaskar” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
        { q: "How would you ask a taxi to go by the meter?", options: ["Bhaiya, meter se chaloge?", "Kitna hua?", "Ek cutting chai.", "Phir milte hain!"], a: 0 },
        { q: "What does “kitna hua” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
        { q: "“Bridge se us paar jao” means…", options: ["Stop here", "Take the footbridge across", "Turn right twice", "Wait for the train"], a: 1 },
        { q: "Which is the most polite way to ask for the bill?", options: ["Bill do", "Bill de dijiye", "Bill!", "Bill dena yaar"], a: 1 },
      ],
      achievements: {
        "auto-pro": ["🚕", "Meter pro", "Took a ride by the meter"], foodie: ["🍔", "Mumbai foodie", "Ordered street food"],
        bargainer: ["🛍️", "Colaba bargainer", "Won a bargain"],
      },
    },
    // ---------- Mumbai, in Marathi ----------
    mr: {
      tutor: {
        greet: "Namaskar", places: MUMBAI_PLACES, defaultPlace: "Churchgate", language: "Marathi",
        starters: ["I need a taxi to Churchgate.", "How do I order a vada pav in Marathi?", "How do I bargain at Dadar market?", "What does 'bara' mean?", "How do I ask if a local train is fast or slow?"],
        glossaryOnly: true,                                // Hindi words are not Marathi: the shared (Hindi) glossary is not used
        glossary: {
          namaskar: "A respectful hello (and goodbye). Works with anyone, any time.", "kasa kay": "“How's it going?” The friendly Mumbai Marathi hello.",
          bara: "“Okay / alright / I see.” Said all the time.", dada: "“Elder brother” — a friendly way to address a driver or shopkeeper.",
          tai: "“Elder sister” — the female equivalent of dada.", kaka: "“Uncle” — for an older man.", kaku: "“Aunty” — for an older woman.",
          majet: "“Doing great!” The answer to “Kasa kay?”.", bindhast: "“No worries / carefree.”", jhakaas: "“Awesome!” Slang, with friends.",
          chala: "“Let's go / alright then.”", ho: "Yes.", nahi: "No.", nako: "“Don't want / no thanks.”", pahije: "“Want / need.” Kay pahije? = What do you need?",
          kiti: "“How much / how many.” Kiti zhale? = How much is it?", kuthe: "Where.", kay: "What.", dhanyavaad: "Thank you.",
          aho: "A polite way to get someone's attention: “Aho, aika…” = Excuse me, listen…",
        },
        polite: { intro: "Marathi's polite forms use “tumhi” and verbs ending in -a (“dya”, “sanga”, “kara”):", rules: [["\\bde\\b", "dya"], ["\\bsang\\b", "sanga"], ["\\bkar\\b", "kara"], ["\\btu\\b", "tumhi"]],
          note: "e.g. “de” → “dya”, “sang” → “sanga”, “tu” → “tumhi”. With friends the short forms are fine." },
        intents: [
          { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
            build: (dest) => { const d = PLACE_MUM_MR[dest.toLowerCase()]; const r = d ? d[0] : `${dest}la`; return { intro: "Try:", phrases: [
              { roman: `Dada, ${r} yenar ka? Meterne.`, hi: d ? `दादा, ${d[1]} येणार का? मीटरने.` : "", en: `Will you come to ${d ? d[2] : dest}? By the meter.` },
              { roman: `Kaka, ${r} nyal ka?`, hi: d ? `काका, ${d[1]} न्याल का?` : "", en: `A more polite version: Would you take me to ${d ? d[2] : dest}?`, label: "More polite" },
              { roman: "Meter chalu kara.", hi: "मीटर चालू करा.", en: "Please start the meter." },
            ], note: MUM_RIDE_NOTE }; } },
          { m: ["local", "train", "metro", "platform", "fast", "slow"], topic: "transport", intro: "At the station, try:", phrases: [
              { roman: "Churchgatela jaanari local konti?", hi: "चर्चगेटला जाणारी लोकल कोणती?", en: "Which local goes to Churchgate?" },
              { roman: "Hi fast aahe ki slow?", hi: "ही फास्ट आहे की स्लो?", en: "Is this a fast or a slow one?" },
              { roman: "Dadarla thaambel ka?", hi: "दादरला थांबेल का?", en: "Does it stop at Dadar?" },
            ], note: MUM_TRAIN_NOTE },
          { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
              { roman: "Thoda kami kara na.", hi: "थोडं कमी करा ना.", en: "Please lower it a little." },
              { roman: "Khup mahaag aahe, dada.", hi: "खूप महाग आहे, दादा.", en: "It's too expensive." },
              { roman: "Shevatcha bhaav sanga.", hi: "शेवटचा भाव सांगा.", en: "What's your best price?" },
            ], note: "At Dadar's markets start around half the first price, smile, and be ready to walk away. Bargaining in Marathi helps." },
          { m: ["price", "how much", "cost", "kiti", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
              { roman: "He kitila aahe?", hi: "हे कितीला आहे?", en: "How much is this?" },
              { roman: "UPI chalel ka?", hi: "यूपीआय चालेल का?", en: "Can I pay by UPI?" },
            ] },
          { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "vada", "pav", "bill"], topic: "food", intro: "Ordering food:", phrases: [
              { roman: "Ek vadapav dya.", hi: "एक वडापाव द्या.", en: "One vada pav, please." },
              { roman: "Kami tikhat, please.", hi: "कमी तिखट, प्लीज.", en: "Less spicy, please." },
              { roman: "Ek cutting chaha.", hi: "एक कटिंग चहा.", en: "One cutting chai." },
            ], note: "“Dya” is the polite “please give”. Ask for “suki chatni”, the dry garlic chutney, on your vada pav." },
          { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
              { roman: "Station kuthe aahe?", hi: "स्टेशन कुठे आहे?", en: "Where is the station?" },
              { roman: "Mi rasta chuklo.", hi: "मी रस्ता चुकलो.", en: "I've lost my way. (women say: chukle)" },
              { roman: "Eastla ki Westla?", hi: "ईस्टला की वेस्टला?", en: "To the east side or the west side?" },
            ], note: "Key words: saral = straight, davikade = left, ujavikade = right. “Pul” is the footbridge over the tracks." },
          { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At work or college:", phrases: [
              { roman: "Mi ithe navin aahe.", hi: "मी इथे नवीन आहे.", en: "I'm new here." },
              { roman: "Meeting kiti vaajta aahe?", hi: "मीटिंग किती वाजता आहे?", en: "What time's the meeting?" },
              { roman: "Tumhi mala madat karal ka?", hi: "तुम्ही मला मदत कराल का?", en: "Could you help me?" },
            ] },
          { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
              { roman: "Tumhi kuthle?", hi: "तुम्ही कुठले?", en: "Where are you from?" },
              { roman: "Aaj khup paaus aahe, na?", hi: "आज खूप पाऊस आहे, ना?", en: "It's really raining today, isn't it?" },
              { roman: "Chaha ghenar ka?", hi: "चहा घेणार का?", en: "Will you have some chai?" },
            ], note: "Mumbai small talk: the rain, the locals and food. With friends, “Kay re?” is a friendly “what's up?”." },
          { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
              { roman: "Maajha naav Alex aahe.", hi: "माझं नाव ॲलेक्स आहे.", en: "My name is Alex." },
              { roman: "Tumcha naav kay?", hi: "तुमचं नाव काय?", en: "What's your name?" },
              { roman: "Tumhala bhetun aanand zhala.", hi: "तुम्हाला भेटून आनंद झाला.", en: "Nice to meet you." },
            ] },
          { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
              { roman: "Khup dhanyavaad!", hi: "खूप धन्यवाद!", en: "Thanks a lot!" },
              { roman: "Maaf kara.", hi: "माफ करा.", en: "Sorry / Excuse me." },
              { roman: "Aho, aika…", hi: "अहो, ऐका…", en: "Excuse me… (to get attention)" },
            ] },
          { m: ["hello", "hi", "greet", "namaste", "namaskar", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere:", phrases: [
              { roman: "Namaskar, kase aahat?", hi: "नमस्कार, कसे आहात?", en: "Hello, how are you?" },
              { roman: "Bhetu nantar!", hi: "भेटू नंतर!", en: "See you later!" },
            ], note: "“Namaskar” works with everyone; “Kasa kay?” is the friendly version." },
          { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
              { roman: "Mala madat havi aahe.", hi: "मला मदत हवी आहे.", en: "I need help." },
              { roman: "Javalcha hospital kuthe aahe?", hi: "जवळचं हॉस्पिटल कुठे आहे?", en: "Where's the nearest hospital?" },
            ], note: "Emergency number in India: 112." },
        ],
        generic: { intro: "Here are three Marathi phrases that'll get you through almost anything in your first week:", phrases: [
            { roman: "Namaskar, kase aahat?", hi: "नमस्कार, कसे आहात?", en: "Hello, how are you?" },
            { roman: "Kiti zhale?", hi: "किती झाले?", en: "How much is it?" },
            { roman: "Tumhi mala madat karal ka?", hi: "तुम्ही मला मदत कराल का?", en: "Could you help me?" },
          ], note: "Tell me a situation — like “I want to order a vada pav” or “ask the way to Churchgate” — and I'll give you the Marathi words." },
      },
      readings: [
        { title: "Asha in Mumbai", level: "A1", lines: [
            { hi: "आशा मुंबईत नवीन आहे.", roman: "Asha Mumbait navin aahe.", en: "Asha is new in Mumbai." },
            { hi: "ती ऑफिसला जात आहे.", roman: "Ti officela jaat aahe.", en: "She is going to the office." },
            { hi: "ती लोकल ट्रेन घेते.", roman: "Ti local train ghete.", en: "She takes the local train." },
            { hi: "ती विचारते, “ही फास्ट लोकल आहे का?”", roman: "Ti vicharte, “Hi fast local aahe ka?”", en: "She asks, “Is this a fast local?”" },
            { hi: "एक काकू म्हणतात, “नाही, स्लो आहे.”", roman: "Ek kaku mhantat, “Nahi, slow aahe.”", en: "An aunty says, “No, it's a slow one.”" },
          ],
          questions: [
            { q: "Where is Asha new?", options: ["Delhi", "Mumbai", "Chennai"], a: 1 },
            { q: "How does Asha travel?", options: ["By local train", "By bus", "By auto"], a: 0 },
            { q: "What kind of train is it?", options: ["Fast", "Slow", "Express"], a: 1 },
          ] },
        { title: "A snack at Dadar", level: "A1", lines: [
            { hi: "रोहनला भूक लागली आहे.", roman: "Rohanla bhook laagli aahe.", en: "Rohan is hungry." },
            { hi: "तो दादर स्टेशनच्या बाहेर जातो.", roman: "To Dadar stationchya baaher jaato.", en: "He goes outside Dadar station." },
            { hi: "तो वडापाव आणि कटिंग चहा घेतो.", roman: "To vadapav aani cutting chaha gheto.", en: "He has a vada pav and a cutting chai." },
            { hi: "सगळे मिळून तीस रुपये झाले.", roman: "Sagle milun tees rupaye zhale.", en: "It all came to thirty rupees." },
          ],
          questions: [
            { q: "How does Rohan feel?", options: ["Tired", "Hungry", "Cold"], a: 1 },
            { q: "What does he eat?", options: ["Vada pav", "Biryani", "Idli"], a: 0 },
            { q: "How much did it cost?", options: ["₹13", "₹30", "₹300"], a: 1 },
          ] },
      ],
      placement: [
        { q: "What does “Namaskar” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
        { q: "How would you ask a taxi to go by the meter?", options: ["Dada, meterne yenar ka?", "Kiti zhale?", "Ek cutting chaha.", "Bhetu nantar!"], a: 0 },
        { q: "What does “kiti zhale” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
        { q: "“Pulavarun palikade ja” means…", options: ["Stop here", "Take the footbridge across", "Turn right twice", "Wait for the train"], a: 1 },
        { q: "Which is the polite way to say “please give”?", options: ["De", "Dya", "Ghe", "Bas"], a: 1 },
      ],
      achievements: {
        "first-words": ["👋", "First words", "Said your first Marathi phrase"], "auto-pro": ["🚕", "Meter pro", "Took a ride by the meter"],
        foodie: ["🍔", "Mumbai foodie", "Ordered street food"], bargainer: ["🛍️", "Dadar bargainer", "Won a bargain"],
      },
    },
  },
};

// Bengaluru's First Week pack, in Kannada (the English view shows the same pack in English first). Same shape as every pack: `hi` holds the
// text in the language's own script, which here is Kannada. AI-assisted editorial review only; awaiting a native Kannada speaker.
window.PACKS.bengaluru = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your neighbours and introduce yourself in Kannada.",
    situation: "You've just moved into a rented flat in Jayanagar. Lakshmamma, the house owner, comes to say hello.", scenario: "blr_greetings",
    tip: "“Namaskara” works with everyone. Bengaluru is very mixed and many people switch to English or Hindi, so even “Kannada swalpa swalpa baratte” (I know a little Kannada) is warmly received.",
    phrases: [
      { hi: "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?", roman: "Namaskara, hegiddira?", en: "Greetings, how are you?", natural: "Hello, how are you?" },
      { hi: "ನನ್ನ ಹೆಸರು ಅಲೆಕ್ಸ್.", roman: "Nanna hesaru Alex.", en: "My name Alex.", natural: "I'm Alex." },
      { hi: "ನಿಮ್ಮ ಹೆಸರೇನು?", roman: "Nimma hesarenu?", en: "Your name is what?", natural: "What's your name?" },
      { hi: "ನಾನು ಇಲ್ಲಿ ಹೊಸಬ.", roman: "Naanu illi hosaba.", en: "I am a newcomer here.", natural: "I'm new here.",
        fem: { hi: "ನಾನು ಇಲ್ಲಿ ಹೊಸಬಳು.", roman: "Naanu illi hosabalu." } },
      { hi: "ತುಂಬಾ ಧನ್ಯವಾದಗಳು!", roman: "Tumba dhanyavaadagalu!", en: "Very many thanks!", natural: "Thanks so much!" },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Take autos, buses and Namma Metro, and get the meter used.",
    situation: "You need to get from MG Road to Indiranagar in the evening rush.", scenario: "blr_auto",
    tip: "Autos are meant to go by the meter, but many drivers quote a fixed price or ask for a little over it (“meter mele”). Agree before you sit in, or book through an app. Namma Metro and BMTC buses are cheap, and women who live in Karnataka travel free on BMTC's ordinary (non-AC) buses.",
    phrases: [
      { hi: "ಇಂದಿರಾನಗರಕ್ಕೆ ಬರ್ತೀರಾ?", roman: "Indiranagarakke bartira?", en: "Will you come to Indiranagar?", natural: "Will you go to Indiranagar?" },
      { hi: "ಮೀಟರ್ ಹಾಕಿ.", roman: "Meter haaki.", en: "Put the meter.", natural: "Please use the meter." },
      { hi: "ಎಷ್ಟು ಆಗುತ್ತೆ?", roman: "Eshtu aagutte?", en: "How much will it become?", natural: "How much will it be?" },
      { hi: "ಈ ಬಸ್ ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ ಹೋಗುತ್ತಾ?", roman: "Ee bus Majesticge hogutta?", en: "Does this bus go to Majestic?", natural: "Does this bus go to Majestic?" },
      { hi: "ಇಲ್ಲೇ ನಿಲ್ಲಿಸಿ.", roman: "Ille nillisi.", en: "Stop right here.", natural: "Stop here, please." },
    ] },
  { day: 3, key: "food", icon: "🍽️", title: "Food", desc: "Order breakfast the Bengaluru way, at a darshini.",
    situation: "Breakfast at a busy darshini in Malleshwaram.", scenario: "blr_food",
    tip: "In a darshini you pay at the counter, take a token and eat standing up. “Coffee” means filter coffee. Most darshinis are vegetarian; “Naanu veg maatra tinnodu” (I only eat veg) is understood everywhere.",
    phrases: [
      { hi: "ಒಂದು ಮಸಾಲೆ ದೋಸೆ ಕೊಡಿ.", roman: "Ondu masale dose kodi.", en: "Give one masala dosa.", natural: "One masala dosa, please." },
      { hi: "ಖಾರ ಕಡಿಮೆ ಮಾಡಿ.", roman: "Khaara kadime maadi.", en: "Make the spice less.", natural: "Not too spicy, please." },
      { hi: "ನಾನು ವೆಜ್ ಮಾತ್ರ ತಿನ್ನೋದು.", roman: "Naanu veg maatra tinnodu.", en: "I eat only veg.", natural: "I'm vegetarian." },
      { hi: "ಸ್ವಲ್ಪ ನೀರು ಕೊಡಿ.", roman: "Swalpa neeru kodi.", en: "Give a little water.", natural: "Some water, please." },
      { hi: "ಪಾರ್ಸೆಲ್ ಮಾಡಿ.", roman: "Parcel maadi.", en: "Make it a parcel.", natural: "Can I have it to take away?" },
      { hi: "ಎಷ್ಟು ಆಯ್ತು?", roman: "Eshtu aaytu?", en: "How much did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Ask prices, sizes and pay, and bargain where it's normal.",
    situation: "You're on Commercial Street looking for a kurta.", scenario: "blr_shopping",
    tip: "Bargain at street markets like Commercial Street and Chickpet, never in malls or shops with price tags. Numbers: ondu, eradu, mooru, naalku, aidu, aaru, elu, entu, ombattu, hattu; nooru (100), saavira (1000).",
    phrases: [
      { hi: "ಇದು ಎಷ್ಟು?", roman: "Idu eshtu?", en: "This is how much?", natural: "How much is this?" },
      { hi: "ತುಂಬಾ ಜಾಸ್ತಿ ಆಯ್ತು.", roman: "Tumba jaasti aaytu.", en: "It became too much.", natural: "That's too much." },
      { hi: "ಸ್ವಲ್ಪ ಕಡಿಮೆ ಮಾಡಿ.", roman: "Swalpa kadime maadi.", en: "Make it a little less.", natural: "Can you lower it a little?" },
      { hi: "ಬೇರೆ ಸೈಜ್ ಇದೆಯಾ?", roman: "Bere size ideya?", en: "Is there another size?", natural: "Do you have another size?" },
      { hi: "ಯುಪಿಐ ಆಗುತ್ತಾ?", roman: "UPI aagutta?", en: "Will UPI work?", natural: "Can I pay by UPI?" },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find the metro, a pharmacy and your way, and ask people to repeat.",
    situation: "You're near Jayanagar 4th Block and need the metro and a pharmacy.", scenario: "blr_directions",
    tip: "Bengaluru addresses go by area, “main”, “cross” and a landmark: “4th Block, 11th Main, near the temple”. Ask “Landmark enu?” (what's the landmark?) and you'll find almost anything.",
    phrases: [
      { hi: "ಮೆಟ್ರೋ ಸ್ಟೇಷನ್ ಎಲ್ಲಿದೆ?", roman: "Metro station ellide?", en: "Where is the metro station?", natural: "Where's the metro station?" },
      { hi: "ನೇರವಾಗಿ ಹೋಗಿ, ಆಮೇಲೆ ಎಡಕ್ಕೆ ತಿರುಗಿ.", roman: "Neravaagi hogi, aamele edakke tirugi.", en: "Go straight, then turn to the left.", natural: "Go straight, then turn left." },
      { hi: "ಇಲ್ಲಿಂದ ದೂರ ಇದೆಯಾ?", roman: "Illinda doora ideya?", en: "Is it far from here?", natural: "Is it far from here?" },
      { hi: "ಹತ್ತಿರ ಮೆಡಿಕಲ್ ಶಾಪ್ ಇದೆಯಾ?", roman: "Hattira medical shop ideya?", en: "Is there a medical shop near?", natural: "Is there a pharmacy nearby?" },
      { hi: "ಇನ್ನೊಂದು ಸಲ ಹೇಳಿ, ನಿಧಾನವಾಗಿ.", roman: "Innondu sala heli, nidhaanavaagi.", en: "Say one more time, slowly.", natural: "Could you say that again, slowly?" },
    ] },
  { day: 6, key: "college", icon: "💼", title: "College & Work", desc: "Settle in with classmates and colleagues.",
    situation: "Your first day at an office in a Whitefield tech park.", scenario: "blr_college",
    tip: "Tech parks run on English, but colleagues love a Kannada “oota aytha?” (have you eaten?): it's how Bengaluru says hello at lunchtime.",
    phrases: [
      { hi: "ಇವತ್ತು ನನ್ನ ಮೊದಲನೇ ದಿನ.", roman: "Ivattu nanna modalane dina.", en: "Today my first day.", natural: "It's my first day today." },
      { hi: "ಮೀಟಿಂಗ್ ಎಷ್ಟು ಹೊತ್ತಿಗೆ?", roman: "Meeting eshtu hottige?", en: "The meeting at what time?", natural: "What time's the meeting?" },
      { hi: "ಕ್ಯಾಂಟೀನ್ ಎಲ್ಲಿದೆ?", roman: "Canteen ellide?", en: "Where is the canteen?", natural: "Where's the canteen?" },
      { hi: "ಸ್ವಲ್ಪ ಸಹಾಯ ಮಾಡ್ತೀರಾ?", roman: "Swalpa sahaaya maadtira?", en: "Will you do a little help?", natural: "Could you help me a bit?" },
      { hi: "ಒಟ್ಟಿಗೆ ಊಟ ಮಾಡೋಣ.", roman: "Ottige oota maadona.", en: "Let's eat a meal together.", natural: "Let's have lunch together." },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "Sunday-morning coffee in Cubbon Park with Kiran, your new flatmate.", scenario: "blr_smalltalk",
    tip: "Bengaluru slang: “sakkath” (awesome), “maga” (mate, with friends only), and “swalpa adjust maadi” (please adjust a little), the city's motto in buses and queues.",
    phrases: [
      { hi: "ಬೆಂಗಳೂರು ಹವಾಮಾನ ಚೆನ್ನಾಗಿದೆ ಅಲ್ವಾ?", roman: "Bengaluru havaamaana chennaagide alva?", en: "Bengaluru's weather is nice, isn't it?", natural: "The weather here is lovely, isn't it?" },
      { hi: "ಟ್ರಾಫಿಕ್ ತುಂಬಾ ಜಾಸ್ತಿ.", roman: "Traffic tumba jaasti.", en: "Traffic is very much.", natural: "The traffic is terrible." },
      { hi: "ನೀವು ಬೆಂಗಳೂರಿಗೆ ಯಾವಾಗ ಬಂದ್ರಿ?", roman: "Neevu Bengalurige yaavaaga bandri?", en: "When did you come to Bengaluru?", natural: "When did you move to Bengaluru?" },
      { hi: "ವೀಕೆಂಡ್ ನಂದಿ ಹಿಲ್ಸ್‌ಗೆ ಹೋಗೋಣ್ವಾ?", roman: "Weekend Nandi Hillsge hogonva?", en: "Shall we go to Nandi Hills at the weekend?", natural: "Fancy Nandi Hills this weekend?" },
      { hi: "ಸಖತ್! ಮತ್ತೆ ಸಿಗೋಣ.", roman: "Sakkath! Matte sigona.", en: "Awesome! We'll meet again.", natural: "Brilliant! See you later." },
    ] },
];

// Bengaluru roleplays in Kannada (offline engine rules, romanised as learners type). Their scene text is also on the server's allowlist.
Object.assign(window.SCENARIOS, {
  blr_greetings: { category: "greetings", icon: "🏠", title: "Meet your house owner", partner: "Lakshmamma", role: "House owner", place: "Your rented flat in Jayanagar",
    goal: "Greet politely, introduce yourself and ask when the water comes.",
    opening: { text: "Namaskara! Neevu hosa tenant-aa? Naanu Lakshmamma, mane owner.", en: "Hello! Are you the new tenant? I'm Lakshmamma, the house owner." },
    start: ["Namaskara, hegiddira?", "Haudu, ivattu bande.", "Nanna hesaru Alex."],
    rules: [
      { m: ["dhanyavaada", "thank", "sigona", "bye", "sari", "aaytu"], text: "Paravagilla! Enu beku andru keli. 🙏", en: "No problem! Ask me if you need anything.", s: ["Matte sigona!"], end: true, hint: "Tumba dhanyavaadagalu!" },
      { m: ["neeru", "water", "yaavaga", "timing"], text: "Neeru beligge aaru gantege, saayankaala elu gantege barutte. Tank tumbisikolli!", en: "Water comes at six in the morning and seven in the evening. Fill your tank!", s: ["Sari, gottaaytu.", "Tumba dhanyavaadagalu!"], hint: "Neeru yaavaga barutte?" },
      { m: ["hesaru", "name", "alex"], text: "Olle hesaru! Nimage Bengaluru hegide?", en: "Nice name! How do you like Bengaluru?", s: ["Tumba chennaagide!", "Swalpa hosadu."], hint: "Nanna hesaru Alex." },
      { m: ["chennaag", "olle", "nice", "good", "hosadu"], text: "Bengaluru ellarannu tanna maadkollutte. Neeru yaavaga barutte gottideya?", en: "Bengaluru makes everyone its own. Do you know when the water comes?", s: ["Neeru yaavaga barutte?"], hint: "Tumba chennaagide!" },
      { m: ["bande", "hosaba", "hosabalu", "new", "tenant", "haudu"], text: "Swagata! Watchman hesaru Ramesh. Rent tingala aidaneya taarikhina olage kodi.", en: "Welcome! The watchman is Ramesh. Pay the rent by the 5th of the month.", s: ["Neeru yaavaga barutte?", "Tumba dhanyavaadagalu!"], hint: "Naanu illi hosaba." },
      { m: ["namaskara", "namaste", "hegiddira", "hello", " hi "], text: "Naanu chennaagiddini! Nimma hesarenu?", en: "I'm well! What's your name?", s: ["Nanna hesaru Alex.", "Haudu, ivattu bande."], hint: "Namaskara, hegiddira?" },
    ],
    fallback: { text: "Haa, sari. Inn enu beku? Neeru, parking, watchman?", en: "Right. What else do you need? Water, parking, the watchman?", s: ["Neeru yaavaga barutte?", "Tumba dhanyavaadagalu!"] } },

  blr_auto: { category: "transport", icon: "🛺", title: "Auto to Indiranagar", partner: "Manju", role: "Auto driver", place: "Outside MG Road metro station",
    goal: "Get to Indiranagar by the meter.", places: ["Indiranagar", "Koramangala", "Majestic", "MG Road", "Jayanagar", "Whitefield", "Airport", "Malleshwaram"],
    opening: { text: "Ellige hogbeku?", en: "Where do you need to go?" },
    start: ["Indiranagarakke bartira?", "Meter haaki.", "Eshtu aagutte?"],
    rules: [
      { m: ["dhanyavaada", "thank", "upi", "gpay", "sigona"], text: "Dhanyavaadagalu! Jopaana hogi. 🙏", en: "Thank you! Go carefully.", s: ["Matte sigona!"], end: true, hint: "Dhanyavaadagalu!" },
      // before the meter rule: "beda, meter maatra" (no, only the meter) and "meter mele" (over the meter) both contain "meter"
      { m: ["beda", "maatra", "no extra"], text: "Sari sari, meter maatra. Kootkolli!", en: "Okay, okay, just the meter. Get in!", s: ["Eshtu hottu aagutte?", "Ille nillisi."], hint: "Beda, meter maatra." },
      { m: ["mele", "twenty", "extra"], text: "Sari, kootkolli!", en: "Okay, get in!", s: ["Eshtu hottu aagutte?", "Ille nillisi."] },
      { m: ["meter"], text: "Meter haaktini, aadre twenty rupees mele kodi.", en: "I'll put the meter on, but give twenty rupees over it.", s: ["Sari, meter mele twenty.", "Beda, meter maatra."], hint: "Meter haaki." },
      { m: ["nillisi", "ille", "stop", "drop"], text: "Bantu! Meter-alli 112 rupaayi aaytu.", en: "Here we are! The meter says ₹112.", s: ["UPI aagutta?", "Dhanyavaadagalu!"], hint: "Ille nillisi." },
      { m: ["hottu", "time", "minute", "doora", "far"], text: "Ee time traffic jaasti, ardha ganta aagutte.", en: "There's a lot of traffic at this time; it'll take half an hour.", s: ["Paravagilla, hogona.", "Ille nillisi."], hint: "Eshtu hottu aagutte?" },
      { m: ["eshtu", "price", "cost", "how much", "duddu"], text: "Meter-alli suumaaru nooru rupaayi aagutte.", en: "By the meter it's about a hundred rupees.", s: ["Sari, hogona.", "Meter haaki."], hint: "Eshtu aagutte?" },
      { m: ["indiranagar", "koramangala", "majestic", "mg road", "jayanagar", "whitefield", "airport", "malleshwaram", "bartira", "hogbeku"], text: "{place}? Sari, kootkolli.", en: "{place}? Okay, get in.", s: ["Meter haaki.", "Eshtu aagutte?"], hint: "{place}ge bartira?" },
      { m: ["haudu", "bande", "hosa", "new"], text: "Swagata! Ee city-alli traffic ondu bitre ella super.", en: "Welcome! Apart from the traffic, everything in this city is great.", s: ["Eshtu hottu aagutte?", "Ille nillisi."] },
      { m: ["sari", "ok", "okay", "hogona", "paravagilla"], text: "Kootkolli! Neevu Bengalurige hosabra?", en: "Sit down! Are you new to Bengaluru?", s: ["Haudu, ivattu bande.", "Eshtu hottu aagutte?"] },
    ],
    fallback: { text: "Artha aagalilla. Ellige hogbeku?", en: "I didn't understand. Where do you need to go?", s: ["Indiranagarakke bartira?", "Meter haaki."] } },

  blr_food: { category: "food", icon: "🍽️", title: "Breakfast at a darshini", partner: "Raghu", role: "Counter staff", place: "A darshini in Malleshwaram",
    goal: "Order a dosa and a coffee, ask for water and pay.",
    opening: { text: "Banni, enu beku?", en: "Come, what would you like?" },
    start: ["Ondu masale dose kodi.", "Ondu coffee kodi.", "Eshtu aaytu?"],
    rules: [
      { m: ["dhanyavaada", "thank", "upi", "gpay", "sigona", "tagolli"], text: "Dhanyavaada! Matte banni. 🙏", en: "Thank you! Come again.", s: ["Matte sigona!"], end: true, hint: "Dhanyavaadagalu!" },
      { m: ["eshtu", "bill", "price", "how much"], text: "Dose mattu coffee, ottu tombattu rupaayi.", en: "Dosa and coffee, ninety rupees in total.", s: ["UPI aagutta?", "Sari, idu tagolli."], hint: "Eshtu aaytu?" },
      { m: ["khaara", "spicy", "chilli"], text: "Sari, khaara kadime maadtini.", en: "Okay, I'll make it less spicy.", s: ["Swalpa neeru kodi.", "Eshtu aaytu?"], hint: "Khaara kadime maadi." },
      { m: ["neeru", "water"], text: "Idu tagolli, neeru.", en: "Here's your water.", s: ["Ondu coffee kodi.", "Eshtu aaytu?"], hint: "Swalpa neeru kodi." },
      { m: ["parcel", "takeaway", "pack"], text: "Parcel maadtini, aidu nimisha.", en: "I'll pack it, five minutes.", s: ["Eshtu aaytu?", "Dhanyavaadagalu!"], hint: "Parcel maadi." },
      { m: ["veg", "motte", "egg"], text: "Illi ella veg, chinte maadbedi.", en: "Everything here is veg, don't worry.", s: ["Ondu masale dose kodi.", "Ondu coffee kodi."], hint: "Naanu veg maatra tinnodu." },
      { m: ["coffee", "kaapi", "tea", "chai"], text: "Ondu filter coffee, bisi bisi! Tindi enu beku?", en: "One filter coffee, piping hot! What would you like to eat?", s: ["Ondu masale dose kodi.", "Eshtu aaytu?"], hint: "Ondu coffee kodi." },
      { m: ["dose", "dosa", "idli", "vada", "ondu"], text: "Ondu masale dose! Khaara beka?", en: "One masala dosa! Do you want it spicy?", s: ["Khaara kadime maadi.", "Parcel maadi."], hint: "Ondu masale dose kodi." },
    ],
    fallback: { text: "Dose, idli, vada, coffee... enu beku?", en: "Dosa, idli, vada, coffee... what would you like?", s: ["Ondu masale dose kodi.", "Ondu coffee kodi."] } },

  blr_shopping: { category: "shopping", icon: "🛍️", title: "Shopping on Commercial Street", partner: "Prakash", role: "Shopkeeper", place: "Commercial Street",
    goal: "Buy a kurta in your size at a fair price, and pay by UPI.",
    opening: { text: "Banni, nodi! Hosa stock ide. Enu beku?", en: "Come in, take a look! New stock. What do you need?" },
    start: ["Idu eshtu?", "Bere size ideya?", "Tumba jaasti aaytu."],
    rules: [
      { m: ["dhanyavaada", "thank", "pack", "tagoltini", "upi", "sigona"], text: "Pack maadide! Matte banni. 🙏", en: "Packed! Come again.", s: ["Matte sigona!"], end: true, hint: "Sari, pack maadi." },
      { m: ["munnooru", "naanooru", "300", "400"], text: "Sari, nimge naanooru-ge kodtini. Last price!", en: "Okay, I'll give it to you for four hundred. Last price!", s: ["Sari, pack maadi.", "UPI aagutta?"] },
      { m: ["jaasti", "expensive", "kadime", "last", "too much"], text: "Idu pure cotton! Sari, nimge aaru nooru.", en: "It's pure cotton! Okay, six hundred for you.", s: ["Naanooru kodtini.", "Swalpa kadime maadi."], hint: "Swalpa kadime maadi." },
      { m: ["size", "bere", "colour", "color", "dodda", "chikka", "tori"], text: "Haudu, ella size ide. Neeli colour-u ide.", en: "Yes, all sizes. There's a blue one too.", s: ["Idu eshtu?", "Neeli tori."], hint: "Bere size ideya?" },
      { m: ["eshtu", "price", "how much", "rate"], text: "Ee kurta? Ombainooru maatra!", en: "This kurta? Only nine hundred!", s: ["Tumba jaasti aaytu.", "Swalpa kadime maadi."], hint: "Idu eshtu?" },
    ],
    fallback: { text: "Nidhaanavaagi nodi. Kurta, shirt, bag, ella ide!", en: "Take your time. Kurtas, shirts, bags, we have it all!", s: ["Idu eshtu?", "Bere size ideya?"] } },

  blr_directions: { category: "directions", icon: "🚇", title: "Find the metro", partner: "Shankar", role: "Passerby", place: "Near Jayanagar 4th Block",
    goal: "Find the nearest metro station, and a pharmacy on the way.",
    opening: { text: "Enu hudukta iddira?", en: "What are you looking for?" },
    start: ["Metro station ellide?", "Hattira medical shop ideya?", "Illinda doora ideya?"],
    rules: [
      { m: ["dhanyavaada", "thank", "sigona", "sari, gottaaytu"], text: "Paravagilla! Jopaana hogi. 🙏", en: "No problem! Go carefully.", s: ["Matte sigona!"], end: true, hint: "Tumba dhanyavaadagalu!" },
      { m: ["innondu", "nidhaana", "slow", "repeat"], text: "Sari: nera hogi, signal-alli edakke. Ashte!", en: "Okay: go straight, left at the signal. That's all!", s: ["Sari, gottaaytu.", "Illinda doora ideya?"], hint: "Innondu sala heli, nidhaanavaagi." },
      { m: ["medical", "pharmacy", "aaspatre", "hospital", "chemist"], text: "Haudu, signal hattira ondu medical shop ide, metro daariyalle.", en: "Yes, there's a pharmacy by the signal, on the way to the metro.", s: ["Metro station ellide?", "Innondu sala heli, nidhaanavaagi."], hint: "Hattira medical shop ideya?" },
      { m: ["doora", "far", "nimisha", "walk", "nadkondu"], text: "Nadkondu hattu nimisha. Auto-alli aidu nimisha.", en: "Ten minutes on foot. Five minutes by auto.", s: ["Sari, gottaaytu.", "Tumba dhanyavaadagalu!"], hint: "Illinda doora ideya?" },
      { m: ["metro", "station", "ellide", "where"], text: "Nera hogi, aamele edakke tirugi. Signal daati balakke metro.", en: "Go straight, then turn left. Past the signal, the metro is on the right.", s: ["Illinda doora ideya?", "Innondu sala heli, nidhaanavaagi."], hint: "Metro station ellide?" },
    ],
    fallback: { text: "Ellige hogbeku heli, naanu daari helteeni.", en: "Tell me where you need to go and I'll show you the way.", s: ["Metro station ellide?", "Hattira medical shop ideya?"] } },

  blr_college: { category: "college", icon: "💼", title: "First day at the office", partner: "Divya", role: "Colleague", place: "A tech park in Whitefield",
    goal: "Introduce yourself and find out about the meeting and lunch.",
    opening: { text: "Hi! Neevu hosa joinee alva? Naanu Divya, same team.", en: "Hi! You're the new joiner, right? I'm Divya, same team." },
    start: ["Haudu, ivattu nanna modalane dina.", "Meeting eshtu hottige?", "Canteen ellide?"],
    rules: [
      { m: ["sigona", "bye", "thank", "dhanyavaada", "super"], text: "Welcome to the team! Enu beku andru keli. 👋", en: "Welcome to the team! Ask me for anything.", s: ["Matte sigona!"], end: true, hint: "Thank you, Divya!" },
      // not "ottige" (together) as a keyword: it is inside "hottige" (at what time)
      { m: ["oota", "lunch", "tiffin"], text: "Haudu, ondu gantege ottige hogona! Canteen-alli bisibele bath chennaagirutte.", en: "Yes, let's go together at one! The bisibele bath in the canteen is good.", s: ["Super!", "Thank you, Divya!"], hint: "Ottige oota maadona." },
      { m: ["canteen", "cafeteria", "floor"], text: "Canteen naalkane floor-alli ide.", en: "The canteen is on the fourth floor.", s: ["Ottige oota maadona.", "Thank you, Divya!"], hint: "Canteen ellide?" },
      { m: ["meeting", "hottige", "time"], text: "Team meeting hattu gantege, conference room B-alli.", en: "The team meeting is at ten, in conference room B.", s: ["Canteen ellide?", "Swalpa sahaaya maadtira?"], hint: "Meeting eshtu hottige?" },
      { m: ["sahaaya", "help", "laptop", "login", "access"], text: "Khanditha! IT desk eradane floor-alli ide, laptop alle sigutte.", en: "Of course! The IT desk is on the second floor; you'll get your laptop there.", s: ["Meeting eshtu hottige?", "Thank you, Divya!"], hint: "Swalpa sahaaya maadtira?" },
      { m: ["modalane", "first", "hosa", "haudu", "new"], text: "Swagata! Modalane dina swalpa kashta, aadre paravagilla.", en: "Welcome! The first day is a little hard, but that's fine.", s: ["Meeting eshtu hottige?", "Swalpa sahaaya maadtira?"], hint: "Ivattu nanna modalane dina." },
    ],
    fallback: { text: "Heli, enu beku? Meeting, canteen, illa IT desk?", en: "Tell me, what do you need? The meeting, the canteen or the IT desk?", s: ["Meeting eshtu hottige?", "Canteen ellide?"] } },

  blr_smalltalk: { category: "smalltalk", icon: "🌳", title: "Coffee in Cubbon Park", partner: "Kiran", role: "Flatmate", place: "Cubbon Park on a Sunday morning",
    goal: "Chat about Bengaluru and make weekend plans.",
    opening: { text: "Enu maga, Bengaluru hegide ivaga?", en: "Hey mate, how's Bengaluru treating you?" },
    start: ["Bengaluru havaamaana chennaagide alva?", "Traffic tumba jaasti.", "Neevu Bengalurige yaavaaga bandri?"],
    rules: [
      { m: ["sigona", "bye", "sakkath", "super", "awesome"], text: "Sakkath! Matte sigona, coffee nandu. 👋", en: "Awesome! See you later, coffee's on me.", s: ["Bye Kiran!"], end: true, hint: "Sakkath! Matte sigona." },
      { m: ["weekend", "nandi", "plan", "free", "hogonva"], text: "Sari! Bhanuvaara beligge Nandi Hills-ge hogona, sunrise nodona.", en: "Sure! Let's go to Nandi Hills on Sunday morning and watch the sunrise.", s: ["Sakkath!", "Matte sigona."], hint: "Weekend Nandi Hillsge hogonva?" },
      { m: ["yaavaaga", "bandri", "how long", "years"], text: "Naanu ille huttiddu, pakka Bengaluru huduga! Neevu?", en: "I was born right here, a true Bengaluru boy! And you?", s: ["Ondu vaara aaytu.", "Weekend Nandi Hillsge hogonva?"] },
      { m: ["havaamaana", "weather", "male", "rain", "chali"], text: "Haudu, ide Bengaluru speciality! Aadre male bandre traffic innu jaasti.", en: "Yes, that's Bengaluru's speciality! But when it rains the traffic gets even worse.", s: ["Neevu Bengalurige yaavaaga bandri?", "Weekend Nandi Hillsge hogonva?"], hint: "Bengaluru havaamaana chennaagide alva?" },
      { m: ["traffic", "jam", "silk board"], text: "Ayyo, Silk Board junction nodidira? Metro tagolli, swalpa better.", en: "Oh no, have you seen Silk Board junction? Take the metro, it's a bit better.", s: ["Sari, metro tagolteeni.", "Weekend Nandi Hillsge hogonva?"], hint: "Traffic tumba jaasti." },
      { m: ["vaara", "week"], text: "Ondu vaara aaytu andre, innu tumba ide nodokke!", en: "Just a week? There's still so much to see!", s: ["Weekend Nandi Hillsge hogonva?", "Traffic tumba jaasti."] },
      { m: ["sari", "ok", "okay", "metro"], text: "Olle idea! Swalpa adjust maadi, ella sari aagutte.", en: "Good idea! Adjust a little and everything works out.", s: ["Sakkath!", "Weekend Nandi Hillsge hogonva?"] },
    ],
    fallback: { text: "Haha, sari! Bengalurinalli nimge yaavudu ishta?", en: "Haha, right! What do you like most in Bengaluru?", s: ["Bengaluru havaamaana chennaagide alva?", "Traffic tumba jaasti."] } },
});

// Bengaluru's Kannada content: AI-assisted editorial review only (see CONTENT_REVIEW above and docs/CONTENT_REVIEW.md).
window.CONTENT_REVIEW.bengaluru = {
  kn: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-18",
    known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Romanised Kannada has no fixed spelling: long vowels are written double (aa, ee) and the retroflex sounds are not marked.", "Fares and practical tips change over time."],
    note: "Bengaluru Kannada: AI-assisted editorial review only, not yet checked by a native Kannada speaker." },
};

// Kannada adds -ge or -kke ("to") to a place: Majesticge, Indiranagarakke.
const PLACE_BLR = {
  indiranagar: ["Indiranagarakke", "ಇಂದಿರಾನಗರಕ್ಕೆ", "Indiranagar"], koramangala: ["Koramangalakke", "ಕೋರಮಂಗಲಕ್ಕೆ", "Koramangala"],
  majestic: ["Majesticge", "ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ", "Majestic"], "mg road": ["MG Roadge", "ಎಂ.ಜಿ. ರೋಡ್‌ಗೆ", "MG Road"], jayanagar: ["Jayanagarakke", "ಜಯನಗರಕ್ಕೆ", "Jayanagar"],
  whitefield: ["Whitefieldge", "ವೈಟ್‌ಫೀಲ್ಡ್‌ಗೆ", "Whitefield"], airport: ["airportge", "ಏರ್‌ಪೋರ್ಟ್‌ಗೆ", "the airport"], malleshwaram: ["Malleshwarakke", "ಮಲ್ಲೇಶ್ವರಕ್ಕೆ", "Malleshwaram"],
  "cubbon park": ["Cubbon Parkge", "ಕಬ್ಬನ್ ಪಾರ್ಕ್‌ಗೆ", "Cubbon Park"],
};
const BENGALURU_PLACES = ["MG Road", "Indiranagar", "Koramangala", "Majestic", "Jayanagar", "Whitefield", "Airport", "Malleshwaram", "Cubbon Park"];
const BLR_RIDE_NOTE = "Bengaluru autos should go by the meter (₹36 for the first 2 km, then ₹18 a km; up to one and a half times that from 10 pm to 5 am), but many drivers ask for a little over it. Agree before you sit in, or book through an app.";
const BLR_METRO_NOTE = "Namma Metro: the Purple line runs east–west (Whitefield ↔ Challaghatta), the Green line north–south (Madavara ↔ Silk Institute); change between them at Majestic (Nadaprabhu Kempegowda station). The Yellow line runs from RV Road to Bommasandra. Buy a token at the counter or a QR ticket in the Namma Metro app.";

window.LOCAL_CONTENT.bengaluru = {
  // ---------- Bengaluru, in Kannada (and the English view) ----------
  kn: {
    tutor: {
      greet: "Namaskara", places: BENGALURU_PLACES, defaultPlace: "MG Road", language: "Kannada",
      starters: ["I need a ride to Indiranagar.", "How do I order a dosa less spicy?", "How do I bargain on Commercial Street?", "What does 'swalpa' mean?", "Which metro line goes to Whitefield?"],
      glossaryOnly: true,                                // Hindi words are not Kannada: the shared (Hindi) glossary is not used
      glossary: {
        namaskara: "A respectful hello (and goodbye). Works with anyone, any time.", swalpa: "“A little.” The most useful word in Bengaluru: “swalpa adjust maadi” = please adjust a little.",
        maga: "“Mate / dude.” With friends only.", sakkath: "“Awesome!” Bengaluru slang.", guru: "“Boss / mate.” Friendly, with people your age.",
        oota: "“A meal.” “Oota aytha?” (have you eaten?) is a friendly hello.", beku: "“Want / need.” Enu beku? = What do you need?", beda: "“Don't want / no thanks.”",
        eshtu: "“How much.” Eshtu aaytu? = How much is it?", elli: "Where. Ellide? = Where is it?", haudu: "Yes.", illa: "No.", sari: "“Okay / right.”",
        darshini: "A quick, cheap self-service eatery: pay at the counter, eat standing up.", kodi: "“Please give.” The polite form of “kodu”.",
        dhanyavaadagalu: "Thank you.", banni: "“Come (in)!” What shopkeepers and hosts say.",
      },
      polite: { intro: "Kannada's polite forms use “neevu” and verbs ending in -i (“kodi”, “heli”, “maadi”):", rules: [["\\bkodu\\b", "kodi"], ["\\bhelu\\b", "heli"], ["\\bmaadu\\b", "maadi"], ["\\bneenu\\b", "neevu"]],
        note: "e.g. “kodu” → “kodi”, “helu” → “heli”, “neenu” → “neevu”. With friends the short forms are fine." },
      intents: [
        { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
          build: (dest) => { const d = PLACE_BLR[dest.toLowerCase()]; const r = d ? d[0] : `${dest}ge`; return { intro: "Try:", phrases: [
            { roman: `${r} bartira? Meter haaki.`, hi: d ? `${d[1]} ಬರ್ತೀರಾ? ಮೀಟರ್ ಹಾಕಿ.` : "", en: `Will you go to ${d ? d[2] : dest}? Please use the meter.` },
            { roman: `Dayavittu ${r} bartira?`, hi: d ? `ದಯವಿಟ್ಟು ${d[1]} ಬರ್ತೀರಾ?` : "", en: `A more polite version: Would you please take me to ${d ? d[2] : dest}?`, label: "More polite" },
            { roman: "Meter haaki.", hi: "ಮೀಟರ್ ಹಾಕಿ.", en: "Please use the meter." },
          ], note: BLR_RIDE_NOTE }; } },
        { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
            { roman: "Majesticge yaava line?", hi: "ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ ಯಾವ ಲೈನ್?", en: "Which line for Majestic?" },
            { roman: "Ee train Whitefieldge hogutta?", hi: "ಈ ಟ್ರೈನ್ ವೈಟ್‌ಫೀಲ್ಡ್‌ಗೆ ಹೋಗುತ್ತಾ?", en: "Does this train go to Whitefield?" },
            { roman: "Token elli sigutte?", hi: "ಟೋಕನ್ ಎಲ್ಲಿ ಸಿಗುತ್ತೆ?", en: "Where do I get a token?" },
          ], note: BLR_METRO_NOTE },
        { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
            { roman: "Swalpa kadime maadi.", hi: "ಸ್ವಲ್ಪ ಕಡಿಮೆ ಮಾಡಿ.", en: "Please lower it a little." },
            { roman: "Tumba jaasti aaytu.", hi: "ತುಂಬಾ ಜಾಸ್ತಿ ಆಯ್ತು.", en: "That's too much." },
            { roman: "Last price eshtu?", hi: "ಲಾಸ್ಟ್ ಪ್ರೈಸ್ ಎಷ್ಟು?", en: "What's your best price?" },
          ], note: "On Commercial Street and in Chickpet start around half the first price, smile, and be ready to walk away. Malls and shops with price tags don't bargain." },
        { m: ["price", "how much", "cost", "eshtu", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
            { roman: "Idu eshtu?", hi: "ಇದು ಎಷ್ಟು?", en: "How much is this?" },
            { roman: "UPI aagutta?", hi: "ಯುಪಿಐ ಆಗುತ್ತಾ?", en: "Can I pay by UPI?" },
          ] },
        { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "dosa", "dose", "idli", "coffee", "bill"], topic: "food", intro: "Ordering food:", phrases: [
            { roman: "Ondu masale dose kodi.", hi: "ಒಂದು ಮಸಾಲೆ ದೋಸೆ ಕೊಡಿ.", en: "One masala dosa, please." },
            { roman: "Khaara kadime maadi.", hi: "ಖಾರ ಕಡಿಮೆ ಮಾಡಿ.", en: "Not too spicy, please." },
            { roman: "Ondu filter coffee kodi.", hi: "ಒಂದು ಫಿಲ್ಟರ್ ಕಾಫಿ ಕೊಡಿ.", en: "One filter coffee, please." },
          ], note: "“Kodi” is the polite “please give”. In a darshini you pay at the counter first and take a token." },
        { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
            { roman: "Metro station ellide?", hi: "ಮೆಟ್ರೋ ಸ್ಟೇಷನ್ ಎಲ್ಲಿದೆ?", en: "Where's the metro station?" },
            { roman: "Nanage daari gottilla.", hi: "ನನಗೆ ದಾರಿ ಗೊತ್ತಿಲ್ಲ.", en: "I don't know the way." },
            { roman: "Landmark enu?", hi: "ಲ್ಯಾಂಡ್‌ಮಾರ್ಕ್ ಏನು?", en: "What's the landmark?" },
          ], note: "Key words: nera = straight, edakke = to the left, balakke = to the right. Addresses go by area, Main, Cross and a landmark." },
        { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At work or college:", phrases: [
            { roman: "Ivattu nanna modalane dina.", hi: "ಇವತ್ತು ನನ್ನ ಮೊದಲನೇ ದಿನ.", en: "It's my first day today." },
            { roman: "Meeting eshtu hottige?", hi: "ಮೀಟಿಂಗ್ ಎಷ್ಟು ಹೊತ್ತಿಗೆ?", en: "What time's the meeting?" },
            { roman: "Swalpa sahaaya maadtira?", hi: "ಸ್ವಲ್ಪ ಸಹಾಯ ಮಾಡ್ತೀರಾ?", en: "Could you help me a bit?" },
          ] },
        { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
            { roman: "Neevu yaava ooru?", hi: "ನೀವು ಯಾವ ಊರು?", en: "Where are you from?" },
            { roman: "Havaamaana chennaagide alva?", hi: "ಹವಾಮಾನ ಚೆನ್ನಾಗಿದೆ ಅಲ್ವಾ?", en: "The weather's lovely, isn't it?" },
            { roman: "Coffee kudiyona?", hi: "ಕಾಫಿ ಕುಡಿಯೋಣ?", en: "Shall we have a coffee?" },
          ], note: "Bengaluru small talk: the weather, the traffic and food. “Oota aytha?” (have you eaten?) is a friendly hello." },
        { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
            { roman: "Nanna hesaru Alex.", hi: "ನನ್ನ ಹೆಸರು ಅಲೆಕ್ಸ್.", en: "My name is Alex." },
            { roman: "Nimma hesarenu?", hi: "ನಿಮ್ಮ ಹೆಸರೇನು?", en: "What's your name?" },
            { roman: "Nimmannu bheti maadi santosha aaytu.", hi: "ನಿಮ್ಮನ್ನು ಭೇಟಿ ಮಾಡಿ ಸಂತೋಷ ಆಯ್ತು.", en: "Nice to meet you." },
          ] },
        { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
            { roman: "Tumba dhanyavaadagalu!", hi: "ತುಂಬಾ ಧನ್ಯವಾದಗಳು!", en: "Thanks a lot!" },
            { roman: "Kshamisi.", hi: "ಕ್ಷಮಿಸಿ.", en: "Sorry / Excuse me." },
            { roman: "Swalpa nidhaanavaagi heli.", hi: "ಸ್ವಲ್ಪ ನಿಧಾನವಾಗಿ ಹೇಳಿ.", en: "Please say it a little slowly." },
          ] },
        { m: ["hello", "hi", "greet", "namaste", "namaskara", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere:", phrases: [
            { roman: "Namaskara, hegiddira?", hi: "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?", en: "Hello, how are you?" },
            { roman: "Matte sigona!", hi: "ಮತ್ತೆ ಸಿಗೋಣ!", en: "See you later!" },
          ], note: "“Namaskara” works with everyone. With friends, “Enu maga?” is a friendly “what's up?”." },
        { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
            { roman: "Nanage sahaaya beku.", hi: "ನನಗೆ ಸಹಾಯ ಬೇಕು.", en: "I need help." },
            { roman: "Hattira aaspatre ellide?", hi: "ಹತ್ತಿರ ಆಸ್ಪತ್ರೆ ಎಲ್ಲಿದೆ?", en: "Where's the nearest hospital?" },
          ], note: "Emergency number in India: 112." },
      ],
      generic: { intro: "Here are three Kannada phrases that'll get you through almost anything in your first week:", phrases: [
          { roman: "Namaskara, hegiddira?", hi: "ನಮಸ್ಕಾರ, ಹೇಗಿದ್ದೀರಾ?", en: "Hello, how are you?" },
          { roman: "Eshtu aaytu?", hi: "ಎಷ್ಟು ಆಯ್ತು?", en: "How much is it?" },
          { roman: "Swalpa sahaaya maadtira?", hi: "ಸ್ವಲ್ಪ ಸಹಾಯ ಮಾಡ್ತೀರಾ?", en: "Could you help me a bit?" },
        ], note: "Tell me a situation — like “I want to order a dosa” or “ask the way to MG Road” — and I'll give you the Kannada words." },
    },
    readings: [
      { title: "Asha in Bengaluru", level: "A1", lines: [
          { hi: "ಆಶಾ ಬೆಂಗಳೂರಿಗೆ ಹೊಸಬಳು.", roman: "Asha Bengalurige hosabalu.", en: "Asha is new to Bengaluru." },
          { hi: "ಅವಳು ಆಫೀಸಿಗೆ ಹೋಗುತ್ತಿದ್ದಾಳೆ.", roman: "Avalu officige hoguttiddaale.", en: "She is going to the office." },
          { hi: "ಅವಳು ಮೆಟ್ರೋ ತಗೊಳ್ತಾಳೆ.", roman: "Avalu metro tagoltaale.", en: "She takes the metro." },
          { hi: "ಅವಳು ಕೇಳ್ತಾಳೆ, “ಈ ಟ್ರೈನ್ ವೈಟ್‌ಫೀಲ್ಡ್‌ಗೆ ಹೋಗುತ್ತಾ?”", roman: "Avalu keltaale, “Ee train Whitefieldge hogutta?”", en: "She asks, “Does this train go to Whitefield?”" },
          { hi: "ಒಬ್ಬರು ಆಂಟಿ ಹೇಳ್ತಾರೆ, “ಹೌದು, ಹೋಗುತ್ತೆ.”", roman: "Obbaru aunty heltaare, “Haudu, hogutte.”", en: "An aunty says, “Yes, it does.”" },
        ],
        questions: [
          { q: "Where is Asha new?", options: ["Delhi", "Bengaluru", "Chennai"], a: 1 },
          { q: "How does Asha travel?", options: ["By metro", "By bus", "By auto"], a: 0 },
          { q: "Where does the train go?", options: ["Majestic", "Whitefield", "The airport"], a: 1 },
        ] },
      { title: "Breakfast in Malleshwaram", level: "A1", lines: [
          { hi: "ರವಿಗೆ ಹಸಿವಾಗಿದೆ.", roman: "Ravige hasivaagide.", en: "Ravi is hungry." },
          { hi: "ಅವನು ಒಂದು ದರ್ಶಿನಿಗೆ ಹೋಗ್ತಾನೆ.", roman: "Avanu ondu darshinige hogtaane.", en: "He goes to a darshini." },
          { hi: "ಅವನು ಮಸಾಲೆ ದೋಸೆ ಮತ್ತು ಫಿಲ್ಟರ್ ಕಾಫಿ ತಗೊಳ್ತಾನೆ.", roman: "Avanu masale dose mattu filter coffee tagoltaane.", en: "He has a masala dosa and a filter coffee." },
          { hi: "ಎಲ್ಲಾ ಸೇರಿ ತೊಂಬತ್ತು ರೂಪಾಯಿ ಆಯ್ತು.", roman: "Ella seri tombattu rupaayi aaytu.", en: "It all came to ninety rupees." },
        ],
        questions: [
          { q: "How does Ravi feel?", options: ["Tired", "Hungry", "Cold"], a: 1 },
          { q: "What does he eat?", options: ["Masala dosa", "Biryani", "Vada pav"], a: 0 },
          { q: "How much did it cost?", options: ["₹19", "₹90", "₹900"], a: 1 },
        ] },
    ],
    placement: [
      { q: "What does “Namaskara” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
      { q: "How would you ask an auto driver to use the meter?", options: ["Meter haaki.", "Eshtu aaytu?", "Ondu coffee kodi.", "Matte sigona!"], a: 0 },
      { q: "What does “eshtu aaytu” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
      { q: "“Neravaagi hogi, aamele edakke tirugi” means…", options: ["Stop here", "Go straight, then turn left", "Turn right twice", "Wait for the bus"], a: 1 },
      { q: "Which is the polite way to say “please give”?", options: ["Kodu", "Kodi", "Beda", "Saaku"], a: 1 },
    ],
    achievements: {
      "first-words": ["👋", "First words", "Said your first Kannada phrase"], "auto-pro": ["🛺", "Meter pro", "Got an auto to use the meter"],
      foodie: ["☕", "Darshini regular", "Ordered breakfast at a darshini"], bargainer: ["🛍️", "Commercial Street bargainer", "Won a bargain"],
    },
    // the home page's "Right now" card: [from hour, to hour, icon, title, text, roleplay, phrase]
    rightNow: [
      [5, 11, "☕", "Morning coffee", "Darshinis are busiest at breakfast. Order like a local.", "blr_food", { roman: "Ondu filter coffee kodi.", hi: "ಒಂದು ಫಿಲ್ಟರ್ ಕಾಫಿ ಕೊಡಿ.", en: "One filter coffee, please." }],
      [11, 15, "💼", "Lunch time", "Tech-park canteens fill up around one. Ask a colleague along.", "blr_college", { roman: "Ottige oota maadona.", hi: "ಒಟ್ಟಿಗೆ ಊಟ ಮಾಡೋಣ.", en: "Let's have lunch together." }],
      [15, 18, "🛍️", "Market hours", "Commercial Street and Chickpet are open. Time to bargain.", "blr_shopping", { roman: "Swalpa kadime maadi.", hi: "ಸ್ವಲ್ಪ ಕಡಿಮೆ ಮಾಡಿ.", en: "Can you lower it a little?" }],
      [18, 22, "🚦", "Evening rush", "The traffic peaks now; the metro is often quicker.", "blr_directions", { roman: "Metro station ellide?", hi: "ಮೆಟ್ರೋ ಸ್ಟೇಷನ್ ಎಲ್ಲಿದೆ?", en: "Where's the metro station?" }],
      [22, 29, "🌙", "Late night ride home", "From 10 pm to 5 am autos may charge up to one and a half times the meter. Agree before you sit in.", "blr_auto", { roman: "Meter haaki.", hi: "ಮೀಟರ್ ಹಾಕಿ.", en: "Please use the meter." }],
    ],
    // what the fair-price check tells the learner to say (app.js A.priceCheck)
    priceSay: (max, mid) => ({
      ticket: { roman: "Majesticge ondu token kodi.", hi: "ಮೆಜೆಸ್ಟಿಕ್‌ಗೆ ಒಂದು ಟೋಕನ್ ಕೊಡಿ.", en: "One token to Majestic, please." },
      meter: { roman: "Meter haaki.", hi: "ಮೀಟರ್ ಹಾಕಿ.", en: "Please use the meter." },
      fair: { roman: "Sari, aaytu.", hi: "ಸರಿ, ಆಯ್ತು.", en: "Okay, deal." },
      counter: { roman: `${max} rupaayige kodtira?`, hi: `${max} ರೂಪಾಯಿಗೆ ಕೊಡ್ತೀರಾ?`, en: `Will you do it for ₹${max}?` },
      high: { roman: `Tumba jaasti aaytu. ${mid} rupaayige kodtira?`, hi: `ತುಂಬಾ ಜಾಸ್ತಿ ಆಯ್ತು. ${mid} ರೂಪಾಯಿಗೆ ಕೊಡ್ತೀರಾ?`, en: `That's too much. Will you do ₹${mid}?` },
    }),
  },
};

// Chennai's First Week pack, in Tamil (the English view shows the same pack in English first). Same shape as every pack: `hi` holds the
// text in the language's own script, which here is Tamil. Spoken Chennai Tamil, polite "-nga" forms. AI-assisted editorial review only.
window.PACKS.chennai = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your neighbours and introduce yourself in Tamil.",
    situation: "You've just moved into a rented flat in Mylapore. Saroja amma, the house owner, comes to say hello.", scenario: "chn_greetings",
    tip: "“Vanakkam” works with everyone. Add “-nga” to be polite: “irukeenga”, “sollunga”. Even “Tamil konjam konjam theriyum” (I know a little Tamil) gets a smile.",
    phrases: [
      { hi: "வணக்கம், எப்படி இருக்கீங்க?", roman: "Vanakkam, eppadi irukeenga?", en: "Greetings, how are you?", natural: "Hello, how are you?" },
      { hi: "என் பேரு அலெக்ஸ்.", roman: "En peru Alex.", en: "My name Alex.", natural: "I'm Alex." },
      { hi: "உங்க பேரு என்ன?", roman: "Unga peru enna?", en: "Your name is what?", natural: "What's your name?" },
      { hi: "நான் இங்க புதுசா வந்திருக்கேன்.", roman: "Naan inga pudhusaa vandhirukken.", en: "I have newly come here.", natural: "I'm new here." },
      { hi: "ரொம்ப நன்றி!", roman: "Romba nandri!", en: "Very many thanks!", natural: "Thanks so much!" },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Take autos, MTC buses and the Chennai Metro, and agree the fare.",
    situation: "You need to get from Chennai Central to T. Nagar in the evening rush.", scenario: "chn_auto",
    tip: "Autos are meant to use the meter, but most Chennai drivers quote a fixed fare: agree on it before you sit in, or book through an app. MTC buses and the Metro are cheap, and women travel free on MTC's ordinary buses.",
    phrases: [
      { hi: "டி. நகர் போகுமா?", roman: "T. Nagar pogumaa?", en: "Will it go to T. Nagar?", natural: "Will you go to T. Nagar?" },
      { hi: "மீட்டர் போடுங்க.", roman: "Meter podunga.", en: "Put the meter.", natural: "Please use the meter." },
      { hi: "எவ்வளவு ஆகும்?", roman: "Evvalavu aagum?", en: "How much will it become?", natural: "How much will it be?" },
      { hi: "இந்த பஸ் பாரிஸ் போகுமா?", roman: "Indha bus Parrys pogumaa?", en: "Will this bus go to Parrys?", natural: "Does this bus go to Parrys?" },
      { hi: "இங்க நிறுத்துங்க.", roman: "Inga niruthunga.", en: "Stop here.", natural: "Stop here, please." },
    ] },
  { day: 3, key: "food", icon: "🍽️", title: "Food", desc: "Order breakfast the Chennai way, at a tiffin centre.",
    situation: "Breakfast at a busy tiffin centre in Mylapore.", scenario: "chn_food",
    tip: "“Tiffin” means a light meal: idli, dosai, pongal, vadai. “Coffee” means filter coffee, served in a tumbler and dabara: pour it between them to cool it. Say “saivam” for vegetarian.",
    phrases: [
      { hi: "ரெண்டு இட்லி குடுங்க.", roman: "Rendu idli kudunga.", en: "Give two idli.", natural: "Two idlis, please." },
      { hi: "காரம் கம்மியா போடுங்க.", roman: "Kaaram kammiyaa podunga.", en: "Put the spice less.", natural: "Not too spicy, please." },
      { hi: "நான் சைவம் மட்டும் சாப்பிடுவேன்.", roman: "Naan saivam mattum saapiduven.", en: "I eat only vegetarian.", natural: "I'm vegetarian." },
      { hi: "கொஞ்சம் தண்ணி குடுங்க.", roman: "Konjam thanni kudunga.", en: "Give a little water.", natural: "Some water, please." },
      { hi: "பார்சல் பண்ணுங்க.", roman: "Parcel pannunga.", en: "Do a parcel.", natural: "Can I have it to take away?" },
      { hi: "எவ்வளவு ஆச்சு?", roman: "Evvalavu aachu?", en: "How much did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Ask prices, sizes and pay, and bargain where it's normal.",
    situation: "You're on Ranganathan Street in T. Nagar looking for a kurta.", scenario: "chn_shopping",
    tip: "Bargain on Ranganathan Street and in Pondy Bazaar, never in malls or shops with price tags. Numbers: onnu, rendu, moonu, naalu, anju, aaru, ezhu, ettu, onbadhu, patthu; nooru (100), aayiram (1000).",
    phrases: [
      { hi: "இது என்ன விலை?", roman: "Idhu enna vilai?", en: "This is what price?", natural: "How much is this?" },
      { hi: "ரொம்ப அதிகம்.", roman: "Romba adhigam.", en: "Very much.", natural: "That's too much." },
      { hi: "கொஞ்சம் குறைச்சுக்கோங்க.", roman: "Konjam koraichukonga.", en: "Reduce a little.", natural: "Can you lower it a little?" },
      { hi: "வேற சைஸ் இருக்கா?", roman: "Vera size irukkaa?", en: "Is there another size?", natural: "Do you have another size?" },
      { hi: "ஜிபே பண்ணலாமா?", roman: "GPay pannalaamaa?", en: "May I do GPay?", natural: "Can I pay with GPay?" },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find the metro, a pharmacy and your way, and ask people to repeat.",
    situation: "You're near the Mylapore tank and need the metro and a pharmacy.", scenario: "chn_directions",
    tip: "Chennai addresses go by area, street and a landmark: “near the temple”, “opposite the bus stop”. Ask “Landmark enna?” (what's the landmark?) and you'll find almost anything.",
    phrases: [
      { hi: "மெட்ரோ ஸ்டேஷன் எங்க இருக்கு?", roman: "Metro station enga irukku?", en: "Where is the metro station?", natural: "Where's the metro station?" },
      { hi: "நேரா போய் லெஃப்ட்ல திரும்புங்க.", roman: "Neraa poi leftla thirumbunga.", en: "Go straight and turn at the left.", natural: "Go straight, then turn left." },
      { hi: "இங்கிருந்து தூரமா?", roman: "Ingirundhu dhooramaa?", en: "From here is it far?", natural: "Is it far from here?" },
      { hi: "பக்கத்துல மெடிக்கல் ஷாப் இருக்கா?", roman: "Pakkathula medical shop irukkaa?", en: "Nearby is there a medical shop?", natural: "Is there a pharmacy nearby?" },
      { hi: "இன்னொரு தடவை மெதுவா சொல்லுங்க.", roman: "Innoru thadavai medhuvaa sollunga.", en: "Say one more time slowly.", natural: "Could you say that again, slowly?" },
    ] },
  { day: 6, key: "college", icon: "💼", title: "College & Work", desc: "Settle in with classmates and colleagues.",
    situation: "Your first day at an office on the OMR IT corridor.", scenario: "chn_college",
    tip: "IT offices on OMR run on English, but colleagues love a Tamil “Saaptingalaa?” (have you eaten?): it's how Chennai says hello at lunchtime.",
    phrases: [
      { hi: "இன்னிக்கு என் முதல் நாள்.", roman: "Innikku en mudhal naal.", en: "Today my first day.", natural: "It's my first day today." },
      { hi: "மீட்டிங் எத்தனை மணிக்கு?", roman: "Meeting ethanai manikku?", en: "The meeting at how many o'clock?", natural: "What time's the meeting?" },
      { hi: "கேன்டீன் எங்க இருக்கு?", roman: "Canteen enga irukku?", en: "Where is the canteen?", natural: "Where's the canteen?" },
      { hi: "கொஞ்சம் உதவி பண்ணுவீங்களா?", roman: "Konjam udhavi pannuveengalaa?", en: "Will you do a little help?", natural: "Could you help me a bit?" },
      { hi: "சேர்ந்து சாப்பிடலாம்.", roman: "Serndhu saapidalaam.", en: "Let's eat together.", natural: "Let's have lunch together." },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "An evening walk on Marina Beach with Karthik, your new flatmate.", scenario: "chn_smalltalk",
    tip: "Chennai slang: “semma” (awesome), “machi” (mate, with friends only), and “gethu” (stylish, cool).",
    phrases: [
      { hi: "சென்னை வெயில் ரொம்ப அதிகம், இல்ல?", roman: "Chennai veyil romba adhigam, illa?", en: "Chennai's heat is very much, no?", natural: "Chennai is really hot, isn't it?" },
      { hi: "டிராஃபிக் ரொம்ப மோசம்.", roman: "Traffic romba mosam.", en: "Traffic is very bad.", natural: "The traffic is terrible." },
      { hi: "நீங்க சென்னைக்கு எப்போ வந்தீங்க?", roman: "Neenga Chennaikku eppo vandheenga?", en: "When did you come to Chennai?", natural: "When did you move to Chennai?" },
      { hi: "வீக்கெண்ட் மகாபலிபுரம் போலாமா?", roman: "Weekend Mahabalipuram polaamaa?", en: "Shall we go to Mahabalipuram at the weekend?", natural: "Fancy Mahabalipuram this weekend?" },
      { hi: "சூப்பர்! அப்புறம் பாக்கலாம்.", roman: "Super! Appuram paakkalaam.", en: "Super! We'll see later.", natural: "Brilliant! See you later." },
    ] },
];

// Chennai roleplays in Tamil (offline engine rules, romanised as learners type). Their scene text is also on the server's allowlist.
Object.assign(window.SCENARIOS, {
  chn_greetings: { category: "greetings", icon: "🏠", title: "Meet your house owner", partner: "Saroja amma", role: "House owner", place: "Your rented flat in Mylapore",
    goal: "Greet politely, introduce yourself and ask when the water comes.",
    opening: { text: "Vanakkam! Neenga dhaan pudhu tenant-aa? Naan Saroja, veettu owner.", en: "Hello! Are you the new tenant? I'm Saroja, the house owner." },
    start: ["Vanakkam, eppadi irukeenga?", "Aamaa, innikku dhaan vandhen.", "En peru Alex."],
    rules: [
      { m: ["nandri", "thank", "paakkalaam", "bye", "sari"], text: "Paravaayilla! Edhavadhu venumnaa kelunga. 🙏", en: "No problem! Ask me if you need anything.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri!" },
      { m: ["thanni", "water", "eppo varum", "timing"], text: "Thanni kaalaila aaru manikku, saayangaalam ezhu manikku varum. Tank-a fill pannikonga!", en: "Water comes at six in the morning and seven in the evening. Keep your tank filled!", s: ["Sari, purinjudhu.", "Romba nandri!"], hint: "Thanni eppo varum?" },
      { m: ["peru", "name", "alex"], text: "Nalla peru! Chennai eppadi irukku?", en: "Nice name! How do you like Chennai?", s: ["Romba nallaa irukku!", "Konjam pudhusaa irukku."], hint: "En peru Alex." },
      { m: ["nallaa irukku", "nice", "good", "pudhusaa irukku"], text: "Chennai ellaaraiyum yethukkum. Thanni eppo varumnu theriyumaa?", en: "Chennai welcomes everyone. Do you know when the water comes?", s: ["Thanni eppo varum?"], hint: "Romba nallaa irukku!" },
      { m: ["vandhen", "pudhusaa", "tenant", "aamaa", "new"], text: "Vaanga! Watchman peru Ramesh. Rent maasam anjaam thedhikkulla kudunga.", en: "Welcome! The watchman is Ramesh. Pay the rent by the 5th of the month.", s: ["Thanni eppo varum?", "Romba nandri!"], hint: "Naan inga pudhusaa vandhirukken." },
      { m: ["vanakkam", "eppadi", "hello", " hi "], text: "Naan nallaa irukken! Unga peru enna?", en: "I'm well! What's your name?", s: ["En peru Alex.", "Aamaa, innikku dhaan vandhen."], hint: "Vanakkam, eppadi irukeenga?" },
    ],
    fallback: { text: "Sari sari. Vera enna venum? Thanni, parking, watchman?", en: "Right. What else do you need? Water, parking, the watchman?", s: ["Thanni eppo varum?", "Romba nandri!"] } },

  chn_auto: { category: "transport", icon: "🛺", title: "Auto to T. Nagar", partner: "Murugan", role: "Auto driver", place: "Outside Chennai Central station",
    goal: "Get to T. Nagar for a fair fare.", places: ["T. Nagar", "Mylapore", "Egmore", "Adyar", "Guindy", "Airport", "Marina", "Velachery"],
    opening: { text: "Enga poganum?", en: "Where do you need to go?" },
    start: ["T. Nagar pogumaa?", "Meter podunga.", "Evvalavu aagum?"],
    rules: [
      { m: ["nandri", "thank", "gpay", "upi", "paakkalaam"], text: "Nandri! Paathu ponga. 🙏", en: "Thank you! Go carefully.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri!" },
      // before the meter rule: "venaam, meter mattum" (no, only the meter) and "meter-ku mela" (over the meter) both contain "meter"
      { m: ["venaam", "mattum", "no extra"], text: "Sari sari, meter mattum. Ukkaarunga!", en: "Okay, okay, just the meter. Get in!", s: ["Evvalavu neram aagum?", "Inga niruthunga."], hint: "Venaam, meter mattum." },
      { m: ["mela", "fifty", "extra"], text: "Sari, ukkaarunga!", en: "Okay, get in!", s: ["Evvalavu neram aagum?", "Inga niruthunga."] },
      { m: ["meter"], text: "Meter podren, aanaa meter-ku mela fifty rupees kudunga.", en: "I'll put the meter on, but give fifty rupees over the meter.", s: ["Sari, meter-ku mela fifty.", "Venaam, meter mattum."], hint: "Meter podunga." },
      { m: ["niruthunga", "inga", "stop", "drop"], text: "Vandhaachu! Nooru rupaa aachu.", en: "Here we are! That's ₹100.", s: ["GPay pannalaamaa?", "Romba nandri!"], hint: "Inga niruthunga." },
      // before the price rule: "evvalavu neram" (how long) also contains "evvalavu" (how much)
      { m: ["neram", "time", "minute", "dhooram", "far"], text: "Indha neram traffic adhigam, arai mani neram aagum.", en: "There's a lot of traffic at this time; it'll take half an hour.", s: ["Paravaayilla, polaam.", "Inga niruthunga."], hint: "Evvalavu neram aagum?" },
      { m: ["evvalavu", "price", "cost", "how much", "rate"], text: "Sumaar nooru rupaa aagum.", en: "It'll be about a hundred rupees.", s: ["Sari, polaam.", "Meter podunga."], hint: "Evvalavu aagum?" },
      { m: ["t. nagar", "nagar", "mylapore", "egmore", "adyar", "guindy", "airport", "marina", "velachery", "pogumaa", "poganum"], text: "{place}? Sari, ukkaarunga.", en: "{place}? Okay, get in.", s: ["Meter podunga.", "Evvalavu aagum?"], hint: "{place} pogumaa?" },
      { m: ["aamaa", "vandhen", "pudhusaa", "new"], text: "Vaanga! Chennai-la traffic thavira ellaam super.", en: "Welcome! Apart from the traffic, everything in Chennai is great.", s: ["Evvalavu neram aagum?", "Inga niruthunga."] },
      { m: ["sari", "ok", "okay", "polaam", "paravaayilla"], text: "Ukkaarunga! Neenga Chennai-ku pudhusaa?", en: "Sit down! Are you new to Chennai?", s: ["Aamaa, innikku dhaan vandhen.", "Evvalavu neram aagum?"] },
    ],
    fallback: { text: "Puriyala. Enga poganum?", en: "I didn't understand. Where do you need to go?", s: ["T. Nagar pogumaa?", "Meter podunga."] } },

  chn_food: { category: "food", icon: "🍽️", title: "Breakfast at a tiffin centre", partner: "Selvam", role: "Waiter", place: "A tiffin centre in Mylapore",
    goal: "Order idli and a filter coffee, ask for water and pay.",
    opening: { text: "Vaanga, enna venum?", en: "Come in, what would you like?" },
    start: ["Rendu idli kudunga.", "Oru filter coffee kudunga.", "Evvalavu aachu?"],
    rules: [
      { m: ["nandri", "thank", "gpay", "upi", "paakkalaam", "vechukonga"], text: "Nandri! Thirumba vaanga. 🙏", en: "Thank you! Come again.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri!" },
      { m: ["evvalavu", "bill", "price", "how much"], text: "Idli, coffee, motham thonnooru rupaa.", en: "Idli and coffee, ninety rupees in total.", s: ["GPay pannalaamaa?", "Sari, idhu vechukonga."], hint: "Evvalavu aachu?" },
      { m: ["kaaram", "spicy", "chilli"], text: "Sari, kaaram kammiyaa podren.", en: "Okay, I'll make it less spicy.", s: ["Konjam thanni kudunga.", "Evvalavu aachu?"], hint: "Kaaram kammiyaa podunga." },
      { m: ["thanni", "water"], text: "Indhaanga, thanni.", en: "Here's your water.", s: ["Oru filter coffee kudunga.", "Evvalavu aachu?"], hint: "Konjam thanni kudunga." },
      { m: ["parcel", "takeaway", "pack"], text: "Parcel panren, anju nimisham.", en: "I'll pack it, five minutes.", s: ["Evvalavu aachu?", "Romba nandri!"], hint: "Parcel pannunga." },
      { m: ["saivam", "veg", "muttai", "egg"], text: "Inga ellaame saivam dhaan, kavalai venaam.", en: "Everything here is vegetarian, don't worry.", s: ["Rendu idli kudunga.", "Oru filter coffee kudunga."], hint: "Naan saivam mattum saapiduven." },
      { m: ["coffee", "kaapi", "tea"], text: "Oru filter coffee, soodaa! Saapida enna venum?", en: "One filter coffee, piping hot! What would you like to eat?", s: ["Rendu idli kudunga.", "Evvalavu aachu?"], hint: "Oru filter coffee kudunga." },
      { m: ["idli", "dosai", "dosa", "vadai", "pongal", "rendu"], text: "Rendu idli! Kaaram venumaa?", en: "Two idlis! Do you want it spicy?", s: ["Kaaram kammiyaa podunga.", "Parcel pannunga."], hint: "Rendu idli kudunga." },
    ],
    fallback: { text: "Idli, dosai, vadai, pongal, coffee... enna venum?", en: "Idli, dosa, vada, pongal, coffee... what would you like?", s: ["Rendu idli kudunga.", "Oru filter coffee kudunga."] } },

  chn_shopping: { category: "shopping", icon: "🛍️", title: "Shopping on Ranganathan Street", partner: "Kumar", role: "Shopkeeper", place: "Ranganathan Street, T. Nagar",
    goal: "Buy a kurta in your size at a fair price, and pay by GPay.",
    opening: { text: "Vaanga, paarunga! Pudhu stock vandhirukku. Enna venum?", en: "Come in, take a look! New stock. What do you need?" },
    start: ["Idhu enna vilai?", "Vera size irukkaa?", "Romba adhigam."],
    rules: [
      { m: ["nandri", "thank", "pack", "edukkaren", "gpay", "paakkalaam"], text: "Pack pannitten! Thirumba vaanga. 🙏", en: "Packed! Come again.", s: ["Appuram paakkalaam!"], end: true, hint: "Sari, pack pannunga." },
      { m: ["munnooru", "naanooru", "300", "400"], text: "Sari, ungalukku naanooru-ku tharen. Last price!", en: "Okay, four hundred for you. Last price!", s: ["Sari, pack pannunga.", "GPay pannalaamaa?"] },
      { m: ["adhigam", "expensive", "koraich", "last", "too much"], text: "Idhu pure cotton! Sari, ungalukku aaranooru.", en: "It's pure cotton! Okay, six hundred for you.", s: ["Naanooru tharen.", "Konjam koraichukonga."], hint: "Konjam koraichukonga." },
      { m: ["size", "vera", "colour", "color", "periya", "chinna", "blue"], text: "Aamaa, ellaa size-um irukku. Blue colour-um irukku.", en: "Yes, every size. There's a blue one too.", s: ["Idhu enna vilai?", "Blue kudunga."], hint: "Vera size irukkaa?" },
      { m: ["vilai", "price", "how much", "evvalavu", "rate"], text: "Indha kurta? Thollaayiram mattum dhaan!", en: "This kurta? Only nine hundred!", s: ["Romba adhigam.", "Konjam koraichukonga."], hint: "Idhu enna vilai?" },
    ],
    fallback: { text: "Medhuvaa paarunga. Kurta, shirt, bag, ellaam irukku!", en: "Take your time. Kurtas, shirts, bags, we have it all!", s: ["Idhu enna vilai?", "Vera size irukkaa?"] } },

  chn_directions: { category: "directions", icon: "🚇", title: "Find the metro", partner: "Raghavan", role: "Passerby", place: "Near the Mylapore tank",
    goal: "Find the nearest metro station, and a pharmacy on the way.",
    opening: { text: "Enna thedureenga?", en: "What are you looking for?" },
    start: ["Metro station enga irukku?", "Pakkathula medical shop irukkaa?", "Ingirundhu dhooramaa?"],
    rules: [
      { m: ["nandri", "thank", "paakkalaam", "purinjudhu"], text: "Paravaayilla! Paathu ponga. 🙏", en: "No problem! Go carefully.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri!" },
      { m: ["innoru", "medhuvaa", "slow", "repeat"], text: "Sari: neraa ponga, signal-la leftu. Avvalavu dhaan!", en: "Okay: go straight, left at the signal. That's all!", s: ["Sari, purinjudhu.", "Ingirundhu dhooramaa?"], hint: "Innoru thadavai medhuvaa sollunga." },
      { m: ["medical", "pharmacy", "hospital", "aaspathri", "chemist"], text: "Aamaa, signal pakkathula oru medical shop irukku, metro pora vazhila.", en: "Yes, there's a pharmacy by the signal, on the way to the metro.", s: ["Metro station enga irukku?", "Innoru thadavai medhuvaa sollunga."], hint: "Pakkathula medical shop irukkaa?" },
      { m: ["dhooram", "far", "nimisham", "walk", "nadandhu"], text: "Nadandhaa pathu nimisham. Auto-la anju nimisham.", en: "Ten minutes on foot. Five minutes by auto.", s: ["Sari, purinjudhu.", "Romba nandri!"], hint: "Ingirundhu dhooramaa?" },
      { m: ["metro", "station", "enga", "where"], text: "Neraa poi leftla thirumbunga. Signal thaandi rightla metro.", en: "Go straight, then turn left. Past the signal, the metro is on the right.", s: ["Ingirundhu dhooramaa?", "Innoru thadavai medhuvaa sollunga."], hint: "Metro station enga irukku?" },
    ],
    fallback: { text: "Enga poganum-nu sollunga, naan vazhi solren.", en: "Tell me where you need to go and I'll show you the way.", s: ["Metro station enga irukku?", "Pakkathula medical shop irukkaa?"] } },

  chn_college: { category: "college", icon: "💼", title: "First day at the office", partner: "Priya", role: "Colleague", place: "An office on the OMR IT corridor",
    goal: "Introduce yourself and find out about the meeting and lunch.",
    opening: { text: "Hi! Neenga dhaan pudhu joinee-aa? Naan Priya, same team.", en: "Hi! You're the new joiner, right? I'm Priya, same team." },
    start: ["Aamaa, innikku en mudhal naal.", "Meeting ethanai manikku?", "Canteen enga irukku?"],
    rules: [
      { m: ["paakkalaam", "bye", "thank", "nandri", "super"], text: "Welcome to the team! Edhavadhu venumnaa kelunga. 👋", en: "Welcome to the team! Ask me for anything.", s: ["Appuram paakkalaam!"], end: true, hint: "Thank you, Priya!" },
      { m: ["saapidalaam", "lunch", "serndhu", "saapadu"], text: "Aamaa, oru manikku serndhu polaam! Canteen-la sambar saadham nallaa irukkum.", en: "Yes, let's go together at one! The sambar rice in the canteen is good.", s: ["Super!", "Thank you, Priya!"], hint: "Serndhu saapidalaam." },
      { m: ["canteen", "cafeteria", "floor"], text: "Canteen naalaavadhu floor-la irukku.", en: "The canteen is on the fourth floor.", s: ["Serndhu saapidalaam.", "Thank you, Priya!"], hint: "Canteen enga irukku?" },
      { m: ["meeting", "manikku", "time"], text: "Team meeting pathu manikku, conference room B-la.", en: "The team meeting is at ten, in conference room B.", s: ["Canteen enga irukku?", "Konjam udhavi pannuveengalaa?"], hint: "Meeting ethanai manikku?" },
      { m: ["udhavi", "help", "laptop", "login", "access"], text: "Kandippaa! IT desk rendaavadhu floor-la irukku, laptop anga kidaikkum.", en: "Of course! The IT desk is on the second floor; you'll get your laptop there.", s: ["Meeting ethanai manikku?", "Thank you, Priya!"], hint: "Konjam udhavi pannuveengalaa?" },
      { m: ["mudhal", "first", "pudhu", "aamaa", "new"], text: "Vaanga! Mudhal naal konjam kashtam, aanaa paravaayilla.", en: "Welcome! The first day is a little hard, but that's fine.", s: ["Meeting ethanai manikku?", "Konjam udhavi pannuveengalaa?"], hint: "Innikku en mudhal naal." },
    ],
    fallback: { text: "Sollunga, enna venum? Meeting, canteen, illa IT desk?", en: "Tell me, what do you need? The meeting, the canteen or the IT desk?", s: ["Meeting ethanai manikku?", "Canteen enga irukku?"] } },

  chn_smalltalk: { category: "smalltalk", icon: "🌊", title: "Evening at the Marina", partner: "Karthik", role: "Flatmate", place: "Marina Beach in the evening",
    goal: "Chat about Chennai and make weekend plans.",
    opening: { text: "Enna machi, Chennai eppadi irukku?", en: "Hey mate, how's Chennai treating you?" },
    start: ["Chennai veyil romba adhigam, illa?", "Traffic romba mosam.", "Neenga Chennaikku eppo vandheenga?"],
    rules: [
      { m: ["paakkalaam", "bye", "semma", "super", "awesome"], text: "Semma! Appuram paakkalaam, coffee en treat. 👋", en: "Awesome! See you later, coffee's on me.", s: ["Bye Karthik!"], end: true, hint: "Super! Appuram paakkalaam." },
      { m: ["weekend", "mahabalipuram", "plan", "free", "polaamaa"], text: "Sari! Sunday kaalaila Mahabalipuram polaam.", en: "Sure! Let's go to Mahabalipuram on Sunday morning.", s: ["Semma!", "Appuram paakkalaam."], hint: "Weekend Mahabalipuram polaamaa?" },
      { m: ["eppo", "vandheenga", "how long", "years"], text: "Naan inga dhaan porandhen, pakkaa Chennai paiyan! Neenga?", en: "I was born right here, a true Chennai boy! And you?", s: ["Oru vaaram aachu.", "Weekend Mahabalipuram polaamaa?"] },
      { m: ["veyil", "weather", "mazhai", "rain", "hot"], text: "Aamaa, adhu dhaan Chennai special! Aanaa mazhai vandhaa traffic innum mosam.", en: "Yes, that's Chennai's speciality! But when it rains the traffic gets even worse.", s: ["Neenga Chennaikku eppo vandheenga?", "Weekend Mahabalipuram polaamaa?"], hint: "Chennai veyil romba adhigam, illa?" },
      { m: ["traffic", "jam", "signal"], text: "Ayyo, Kathipara paatheengalaa? Metro-la ponga, konjam better.", en: "Oh no, have you seen Kathipara junction? Take the metro, it's a bit better.", s: ["Sari, metro-la poren.", "Weekend Mahabalipuram polaamaa?"], hint: "Traffic romba mosam." },
      { m: ["vaaram", "week"], text: "Oru vaaram dhaanaa? Innum paakka niraiya irukku!", en: "Just a week? There's still so much to see!", s: ["Weekend Mahabalipuram polaamaa?", "Traffic romba mosam."] },
      { m: ["sari", "ok", "okay", "metro"], text: "Nalla idea! Konjam adjust pannikitta ellaam sari aagidum.", en: "Good idea! Adjust a little and everything works out.", s: ["Semma!", "Weekend Mahabalipuram polaamaa?"] },
    ],
    fallback: { text: "Haha, sari! Chennai-la ungalukku edhu pidikkum?", en: "Haha, right! What do you like most in Chennai?", s: ["Chennai veyil romba adhigam, illa?", "Traffic romba mosam."] } },
});

// Chennai's Tamil content: AI-assisted editorial review only (docs/CONTENT_REVIEW.md).
window.CONTENT_REVIEW.chennai = {
  ta: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-18",
    known_limitations: ["The content teaches spoken Chennai Tamil, which differs from written Tamil.", "Romanised Tamil has no fixed spelling: long vowels are written double (aa, ee, oo) and the retroflex sounds are not marked.", "Fares and practical tips change over time."],
    note: "Chennai Tamil: AI-assisted editorial review only, not yet checked by a native Tamil speaker." },
};

// With "pogumaa?" (will it go?) Chennai Tamil names the place on its own: "T. Nagar pogumaa?".
const PLACE_CHN = {
  "t. nagar": ["T. Nagar", "டி. நகர்", "T. Nagar"], central: ["Central", "சென்ட்ரல்", "Chennai Central"], mylapore: ["Mylapore", "மயிலாப்பூர்", "Mylapore"],
  egmore: ["Egmore", "எழும்பூர்", "Egmore"], adyar: ["Adyar", "அடையார்", "Adyar"], guindy: ["Guindy", "கிண்டி", "Guindy"], airport: ["airport", "ஏர்போர்ட்", "the airport"],
  marina: ["Marina", "மெரினா", "Marina Beach"], velachery: ["Velachery", "வேளச்சேரி", "Velachery"], "anna nagar": ["Anna Nagar", "அண்ணா நகர்", "Anna Nagar"],
};
const CHENNAI_PLACES = ["T. Nagar", "Central", "Mylapore", "Egmore", "Adyar", "Guindy", "Airport", "Marina", "Velachery", "Anna Nagar"];
const CHN_RIDE_NOTE = "Chennai's official auto meter fare (₹25 for the first 1.8 km, then ₹12 a km) dates from 2013 and a revision is pending, so most drivers quote their own fare. Agree on it before you sit in, or book through an app.";
const CHN_METRO_NOTE = "Chennai Metro: the Blue line runs from Wimco Nagar to the Airport, the Green line from Chennai Central to St Thomas Mount; change at Chennai Central or Alandur. More lines are opening under Phase II. Tokens and QR tickets cost ₹10–50.";

window.LOCAL_CONTENT.chennai = {
  // ---------- Chennai, in Tamil (and the English view) ----------
  ta: {
    tutor: {
      greet: "Vanakkam", places: CHENNAI_PLACES, defaultPlace: "T. Nagar", language: "Tamil",
      starters: ["I need a ride to Adyar.", "How do I order idli, not too spicy?", "How do I bargain on Ranganathan Street?", "What does 'konjam' mean?", "Which metro line goes to Guindy?"],
      glossaryOnly: true,                                // Hindi words are not Tamil: the shared (Hindi) glossary is not used
      glossary: {
        vanakkam: "A respectful hello (and goodbye). Works with anyone, any time.", konjam: "“A little.” “Konjam medhuvaa” = a little slowly.",
        machi: "“Mate.” With friends only.", semma: "“Awesome!” Chennai slang.", gethu: "“Stylish, cool.” Slang, with friends.",
        saaptingalaa: "“Have you eaten?” A friendly hello at lunchtime.", venum: "“Want / need.” Enna venum? = What do you need?", venaam: "“Don't want / no thanks.”",
        evvalavu: "“How much.” Evvalavu aachu? = How much is it?", enga: "Where. Enga irukku? = Where is it?", aamaa: "Yes.", illa: "No.", sari: "“Okay / right.”",
        tiffin: "A light meal: idli, dosai, pongal or vadai, at breakfast or in the evening.", kudunga: "“Please give.” The polite form of “kudu”.",
        nandri: "Thank you.", vaanga: "“Come (in)!” What shopkeepers and hosts say.",
      },
      polite: { intro: "Tamil's polite forms use “neenga” and verbs ending in -unga (“kudunga”, “sollunga”, “pannunga”):", rules: [["\\bkudu\\b", "kudunga"], ["\\bsollu\\b", "sollunga"], ["\\bpannu\\b", "pannunga"], ["\\bnee\\b", "neenga"]],
        note: "e.g. “kudu” → “kudunga”, “sollu” → “sollunga”, “nee” → “neenga”. With friends the short forms are fine." },
      intents: [
        { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
          build: (dest) => { const d = PLACE_CHN[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
            { roman: `${r} pogumaa? Meter podunga.`, hi: d ? `${d[1]} போகுமா? மீட்டர் போடுங்க.` : "", en: `Will you go to ${d ? d[2] : dest}? Please use the meter.` },
            { roman: `${r} varuveengalaa?`, hi: d ? `${d[1]} வருவீங்களா?` : "", en: `A more polite version: Would you come to ${d ? d[2] : dest}?`, label: "More polite" },
            { roman: "Evvalavu aagum?", hi: "எவ்வளவு ஆகும்?", en: "How much will it be?" },
          ], note: CHN_RIDE_NOTE }; } },
        { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
            { roman: "Airportukku endha line?", hi: "ஏர்போர்ட்டுக்கு எந்த லைன்?", en: "Which line for the airport?" },
            { roman: "Indha train Guindy pogumaa?", hi: "இந்த ட்ரெயின் கிண்டி போகுமா?", en: "Does this train go to Guindy?" },
            { roman: "Ticket enga vaanganum?", hi: "டிக்கெட் எங்க வாங்கணும்?", en: "Where do I buy a ticket?" },
          ], note: CHN_METRO_NOTE },
        { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
            { roman: "Konjam koraichukonga.", hi: "கொஞ்சம் குறைச்சுக்கோங்க.", en: "Please lower it a little." },
            { roman: "Romba adhigam.", hi: "ரொம்ப அதிகம்.", en: "That's too much." },
            { roman: "Last price enna?", hi: "லாஸ்ட் பிரைஸ் என்ன?", en: "What's your best price?" },
          ], note: "On Ranganathan Street and in Pondy Bazaar start around half the first price, smile, and be ready to walk away. Malls and shops with price tags don't bargain." },
        { m: ["price", "how much", "cost", "evvalavu", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
            { roman: "Idhu enna vilai?", hi: "இது என்ன விலை?", en: "How much is this?" },
            { roman: "GPay pannalaamaa?", hi: "ஜிபே பண்ணலாமா?", en: "Can I pay with GPay?" },
          ] },
        { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "idli", "dosa", "coffee", "bill"], topic: "food", intro: "Ordering food:", phrases: [
            { roman: "Rendu idli kudunga.", hi: "ரெண்டு இட்லி குடுங்க.", en: "Two idlis, please." },
            { roman: "Kaaram kammiyaa podunga.", hi: "காரம் கம்மியா போடுங்க.", en: "Not too spicy, please." },
            { roman: "Oru filter coffee kudunga.", hi: "ஒரு ஃபில்டர் காபி குடுங்க.", en: "One filter coffee, please." },
          ], note: "“Kudunga” is the polite “please give”. Coffee comes in a tumbler and dabara: pour it between them to cool it." },
        { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
            { roman: "Metro station enga irukku?", hi: "மெட்ரோ ஸ்டேஷன் எங்க இருக்கு?", en: "Where's the metro station?" },
            { roman: "Enakku vazhi theriyala.", hi: "எனக்கு வழி தெரியல.", en: "I don't know the way." },
            { roman: "Landmark enna?", hi: "லேண்ட்மார்க் என்ன?", en: "What's the landmark?" },
          ], note: "Key words: neraa = straight, leftla = to the left, rightla = to the right. Addresses go by area, street and a landmark." },
        { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At work or college:", phrases: [
            { roman: "Innikku en mudhal naal.", hi: "இன்னிக்கு என் முதல் நாள்.", en: "It's my first day today." },
            { roman: "Meeting ethanai manikku?", hi: "மீட்டிங் எத்தனை மணிக்கு?", en: "What time's the meeting?" },
            { roman: "Konjam udhavi pannuveengalaa?", hi: "கொஞ்சம் உதவி பண்ணுவீங்களா?", en: "Could you help me a bit?" },
          ] },
        { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
            { roman: "Neenga endha ooru?", hi: "நீங்க எந்த ஊரு?", en: "Where are you from?" },
            { roman: "Chennai veyil romba adhigam, illa?", hi: "சென்னை வெயில் ரொம்ப அதிகம், இல்ல?", en: "Chennai is really hot, isn't it?" },
            { roman: "Coffee kudikkalaamaa?", hi: "காபி குடிக்கலாமா?", en: "Shall we have a coffee?" },
          ], note: "Chennai small talk: the heat, the traffic, cricket and food. “Saaptingalaa?” (have you eaten?) is a friendly hello." },
        { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
            { roman: "En peru Alex.", hi: "என் பேரு அலெக்ஸ்.", en: "My name is Alex." },
            { roman: "Unga peru enna?", hi: "உங்க பேரு என்ன?", en: "What's your name?" },
            { roman: "Ungala paathadhula romba santhosham.", hi: "உங்கள பாத்ததுல ரொம்ப சந்தோஷம்.", en: "Nice to meet you." },
          ] },
        { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
            { roman: "Romba nandri!", hi: "ரொம்ப நன்றி!", en: "Thanks a lot!" },
            { roman: "Mannichikonga.", hi: "மன்னிச்சிக்கோங்க.", en: "Sorry / Excuse me." },
            { roman: "Konjam medhuvaa sollunga.", hi: "கொஞ்சம் மெதுவா சொல்லுங்க.", en: "Please say it a little slowly." },
          ] },
        { m: ["hello", "hi", "greet", "namaste", "vanakkam", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere:", phrases: [
            { roman: "Vanakkam, eppadi irukeenga?", hi: "வணக்கம், எப்படி இருக்கீங்க?", en: "Hello, how are you?" },
            { roman: "Appuram paakkalaam!", hi: "அப்புறம் பாக்கலாம்!", en: "See you later!" },
          ], note: "“Vanakkam” works with everyone. With friends, “Enna machi?” is a friendly “what's up?”." },
        { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
            { roman: "Enakku udhavi venum.", hi: "எனக்கு உதவி வேணும்.", en: "I need help." },
            { roman: "Pakkathula aaspathri enga irukku?", hi: "பக்கத்துல ஆஸ்பத்திரி எங்க இருக்கு?", en: "Where's the nearest hospital?" },
          ], note: "Emergency number in India: 112." },
      ],
      generic: { intro: "Here are three Tamil phrases that'll get you through almost anything in your first week:", phrases: [
          { roman: "Vanakkam, eppadi irukeenga?", hi: "வணக்கம், எப்படி இருக்கீங்க?", en: "Hello, how are you?" },
          { roman: "Evvalavu aachu?", hi: "எவ்வளவு ஆச்சு?", en: "How much is it?" },
          { roman: "Konjam udhavi pannuveengalaa?", hi: "கொஞ்சம் உதவி பண்ணுவீங்களா?", en: "Could you help me a bit?" },
        ], note: "Tell me a situation — like “I want to order idli” or “ask the way to T. Nagar” — and I'll give you the Tamil words." },
    },
    readings: [
      { title: "Asha in Chennai", level: "A1", lines: [
          { hi: "ஆஷா சென்னைக்கு புதுசு.", roman: "Asha Chennaikku pudhusu.", en: "Asha is new to Chennai." },
          { hi: "அவங்க ஆஃபீஸுக்கு போயிட்டு இருக்காங்க.", roman: "Avanga officekku poittu irukkaanga.", en: "She is going to the office." },
          { hi: "அவங்க மெட்ரோல போறாங்க.", roman: "Avanga metrola poraanga.", en: "She takes the metro." },
          { hi: "அவங்க கேக்கறாங்க, “இந்த ட்ரெயின் ஏர்போர்ட் போகுமா?”", roman: "Avanga kekkaraanga, “Indha train airport pogumaa?”", en: "She asks, “Does this train go to the airport?”" },
          { hi: "ஒரு ஆன்ட்டி சொல்றாங்க, “ஆமா, போகும்.”", roman: "Oru aunty solraanga, “Aamaa, pogum.”", en: "An aunty says, “Yes, it does.”" },
        ],
        questions: [
          { q: "Where is Asha new?", options: ["Delhi", "Chennai", "Bengaluru"], a: 1 },
          { q: "How does Asha travel?", options: ["By metro", "By bus", "By auto"], a: 0 },
          { q: "Where does the train go?", options: ["Guindy", "The airport", "Egmore"], a: 1 },
        ] },
      { title: "Breakfast in Mylapore", level: "A1", lines: [
          { hi: "ரவிக்கு பசிக்குது.", roman: "Ravikku pasikkudhu.", en: "Ravi is hungry." },
          { hi: "அவன் ஒரு டிஃபன் சென்டருக்கு போறான்.", roman: "Avan oru tiffin centerukku poraan.", en: "He goes to a tiffin centre." },
          { hi: "அவன் ரெண்டு இட்லியும் ஒரு காபியும் வாங்கறான்.", roman: "Avan rendu idliyum oru coffeeyum vaangaraan.", en: "He has two idlis and a coffee." },
          { hi: "மொத்தம் எழுபது ரூபாய் ஆச்சு.", roman: "Motham ezhubadhu rupaai aachu.", en: "It all came to seventy rupees." },
        ],
        questions: [
          { q: "How does Ravi feel?", options: ["Tired", "Hungry", "Cold"], a: 1 },
          { q: "What does he eat?", options: ["Idli", "Biryani", "Vada pav"], a: 0 },
          { q: "How much did it cost?", options: ["₹17", "₹70", "₹700"], a: 1 },
        ] },
    ],
    placement: [
      { q: "What does “Vanakkam” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
      { q: "How would you ask an auto driver to use the meter?", options: ["Meter podunga.", "Evvalavu aachu?", "Oru coffee kudunga.", "Appuram paakkalaam!"], a: 0 },
      { q: "What does “evvalavu aachu” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
      { q: "“Neraa poi leftla thirumbunga” means…", options: ["Stop here", "Go straight, then turn left", "Turn right twice", "Wait for the bus"], a: 1 },
      { q: "Which is the polite way to say “please give”?", options: ["Kudu", "Kudunga", "Venaam", "Podhum"], a: 1 },
    ],
    achievements: {
      "first-words": ["👋", "First words", "Said your first Tamil phrase"], "auto-pro": ["🛺", "Fair-fare pro", "Agreed a fair auto fare"],
      foodie: ["☕", "Tiffin regular", "Ordered breakfast at a tiffin centre"], bargainer: ["🛍️", "T. Nagar bargainer", "Won a bargain"],
    },
    rightNow: [
      [5, 11, "☕", "Morning coffee", "Tiffin centres are busiest at breakfast. Order like a local.", "chn_food", { roman: "Oru filter coffee kudunga.", hi: "ஒரு ஃபில்டர் காபி குடுங்க.", en: "One filter coffee, please." }],
      [11, 15, "💼", "Lunch time", "Office canteens on OMR fill up around one. Ask a colleague along.", "chn_college", { roman: "Serndhu saapidalaam.", hi: "சேர்ந்து சாப்பிடலாம்.", en: "Let's have lunch together." }],
      [15, 18, "🛍️", "Market hours", "Ranganathan Street and Pondy Bazaar are open. Time to bargain.", "chn_shopping", { roman: "Konjam koraichukonga.", hi: "கொஞ்சம் குறைச்சுக்கோங்க.", en: "Can you lower it a little?" }],
      [18, 22, "🌊", "Evening at the Marina", "The Marina is where Chennai goes when the sun goes down.", "chn_smalltalk", { roman: "Coffee kudikkalaamaa?", hi: "காபி குடிக்கலாமா?", en: "Shall we have a coffee?" }],
      [22, 29, "🌙", "Late night ride home", "Autos charge more late at night. Agree on the fare before you sit in.", "chn_auto", { roman: "Evvalavu aagum?", hi: "எவ்வளவு ஆகும்?", en: "How much will it be?" }],
    ],
    priceSay: (max, mid) => ({
      ticket: { roman: "Airportukku oru ticket kudunga.", hi: "ஏர்போர்ட்டுக்கு ஒரு டிக்கெட் குடுங்க.", en: "One ticket to the airport, please." },
      meter: { roman: "Meter podunga.", hi: "மீட்டர் போடுங்க.", en: "Please use the meter." },
      fair: { roman: "Sari, edukkaren.", hi: "சரி, எடுக்கறேன்.", en: "Okay, I'll take it." },
      counter: { roman: `${max} rupaaikku tharuveengalaa?`, hi: `${max} ரூபாய்க்கு தருவீங்களா?`, en: `Will you do it for ₹${max}?` },
      high: { roman: `Romba adhigam. ${mid} rupaaikku tharuveengalaa?`, hi: `ரொம்ப அதிகம். ${mid} ரூபாய்க்கு தருவீங்களா?`, en: `That's too much. Will you do ₹${mid}?` },
    }),
  },
};

// Puducherry's First Week pack, in Tamil (the English view shows the same pack in English first). Spoken Tamil, polite "-nga" forms;
// AI-assisted editorial review only. The server's Tamil curriculum is shared with Chennai (it is per language, not per city).
window.PACKS.puducherry = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your hosts and introduce yourself in Tamil.",
    situation: "You've just checked into a guesthouse in White Town. Selvi, the owner, comes to say hello.", scenario: "pdy_greetings",
    tip: "“Vanakkam” works with everyone; some older residents also greet visitors with a French “Bonjour”. Tamil is the language of the streets, the markets and the autos.",
    phrases: [
      { hi: "வணக்கம், நல்லா இருக்கீங்களா?", roman: "Vanakkam, nallaa irukeengalaa?", en: "Greetings, are you well?", natural: "Hello, are you well?" },
      { hi: "என் பேரு அலெக்ஸ், லண்டன்லேர்ந்து வந்திருக்கேன்.", roman: "En peru Alex, Londonlerndhu vandhirukken.", en: "My name Alex, I have come from London.", natural: "I'm Alex, from London." },
      { hi: "இங்க ஒரு வாரம் தங்கப் போறேன்.", roman: "Inga oru vaaram thanga poren.", en: "Here I'm going to stay one week.", natural: "I'm staying here for a week." },
      { hi: "காலை டிஃபன் எத்தனை மணிக்கு?", roman: "Kaalai tiffin ethanai manikku?", en: "Morning tiffin at how many o'clock?", natural: "What time is breakfast?" },
      { hi: "ரொம்ப நன்றி, ரூம் சூப்பரா இருக்கு!", roman: "Romba nandri, room superaa irukku!", en: "Many thanks, the room is super!", natural: "Thanks so much, the room is lovely!" },
    ] },
  { day: 2, key: "transport", icon: "🛵", title: "Transport", desc: "Rent a scooter, find petrol and agree auto fares.",
    situation: "You want a scooter for the day to ride to Auroville.", scenario: "pdy_scooter",
    tip: "White Town is best on foot or by bicycle; rent a scooter (about ₹300–700 a day) for Auroville and the beaches. Carry your driving licence. Puducherry's autos don't use meters: agree on the fare before you sit in.",
    phrases: [
      { hi: "ஸ்கூட்டர் வாடகைக்கு கிடைக்குமா?", roman: "Scooter vaadagaikku kidaikkumaa?", en: "Will a scooter be got for rent?", natural: "Can I rent a scooter?" },
      { hi: "ஒரு நாளைக்கு எவ்வளவு?", roman: "Oru naalaikku evvalavu?", en: "For one day how much?", natural: "How much for a day?" },
      { hi: "ஹெல்மெட் குடுப்பீங்களா?", roman: "Helmet kudupeengalaa?", en: "Will you give a helmet?", natural: "Do you give a helmet?" },
      { hi: "ஆரோவில்லுக்கு எந்த வழி?", roman: "Aurovillukku endha vazhi?", en: "To Auroville which way?", natural: "Which way is Auroville?" },
      { hi: "பெட்ரோல் எங்க போடணும்?", roman: "Petrol enga podanum?", en: "Where must I put petrol?", natural: "Where can I get petrol?" },
    ] },
  { day: 3, key: "food", icon: "🐟", title: "Food", desc: "Order seafood by the sea, and ask for less spice.",
    situation: "Lunch at a seaside restaurant on the Promenade.", scenario: "pdy_food",
    tip: "Puducherry is known for its seafood and for Creole dishes that mix Tamil and French cooking. Vegetarian? Say “Naan saivam” and ask for a “meals” plate.",
    phrases: [
      { hi: "ஒரு மீன் குழம்பு சாப்பாடு குடுங்க.", roman: "Oru meen kuzhambu saapaadu kudunga.", en: "Give one fish curry meal.", natural: "One fish curry meal, please." },
      { hi: "இன்னிக்கு என்ன ஃப்ரெஷ் மீன் இருக்கு?", roman: "Innikku enna fresh meen irukku?", en: "Today what fresh fish is there?", natural: "What's the fresh fish today?" },
      { hi: "காரம் கொஞ்சம் கம்மியா போடுங்க.", roman: "Kaaram konjam kammiyaa podunga.", en: "Put the spice a little less.", natural: "Not too spicy, please." },
      { hi: "ஒரு ஃப்ரெஷ் லைம் சோடா.", roman: "Oru fresh lime soda.", en: "One fresh lime soda.", natural: "A fresh lime soda, please." },
      { hi: "பில் குடுங்க, ப்ளீஸ்.", roman: "Bill kudunga, please.", en: "Give the bill, please.", natural: "Can I have the bill, please?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Ask prices, check what things are made of, and bargain where it's normal.",
    situation: "You're on Nehru Street near Goubert Market, looking for a handmade bag.", scenario: "pdy_shopping",
    tip: "Bargain at Goubert Market and the Sunday market on Mahatma Gandhi Road. Boutiques in White Town and shops in Auroville have fixed prices.",
    phrases: [
      { hi: "இந்த பை என்ன விலை?", roman: "Indha pai enna vilai?", en: "This bag what price?", natural: "How much is this bag?" },
      { hi: "இது கைத்தறியா?", roman: "Idhu kaithariyaa?", en: "Is this handloom?", natural: "Is this handloom?" },
      { hi: "ரொம்ப அதிகம், கொஞ்சம் குறைங்க.", roman: "Romba adhigam, konjam koraiyunga.", en: "Very much, reduce a little.", natural: "That's too much, can you lower it?" },
      { hi: "ரெண்டு எடுத்தா எவ்வளவு?", roman: "Rendu eduthaa evvalavu?", en: "If I take two, how much?", natural: "How much if I buy two?" },
      { hi: "கார்டு எடுப்பீங்களா?", roman: "Card edupeengalaa?", en: "Will you take a card?", natural: "Do you take cards?" },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find the beach, a café and your way back.",
    situation: "You've come out of the Puducherry bus stand and want the Promenade.", scenario: "pdy_directions",
    tip: "White Town's streets run in a grid between the canal and the sea, and their signs are in French and Tamil (“Rue” means street). Ask for a landmark: the lighthouse, the Ashram or the Manakula Vinayagar temple.",
    phrases: [
      { hi: "பீச்சுக்கு எந்த வழியா போகணும்?", roman: "Beachukku endha vazhiyaa poganum?", en: "By which way must I go to the beach?", natural: "Which way to the beach?" },
      { hi: "ரைட்ல திரும்பி நேரா போங்க.", roman: "Rightla thirumbi neraa ponga.", en: "Turning right, go straight.", natural: "Turn right and go straight on." },
      { hi: "நடந்து போகலாமா?", roman: "Nadandhu pogalaamaa?", en: "May one go walking?", natural: "Can I walk there?" },
      { hi: "இங்க பக்கத்துல நல்ல கஃபே இருக்கா?", roman: "Inga pakkathula nalla cafe irukkaa?", en: "Nearby here is there a good café?", natural: "Is there a good café nearby?" },
      { hi: "வழி மாறிட்டேன், உதவி பண்ணுங்க.", roman: "Vazhi maaritten, udhavi pannunga.", en: "I changed the way, do help.", natural: "I'm lost, please help me." },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in with classmates and colleagues.",
    situation: "Your first day on the Pondicherry University campus.", scenario: "pdy_college",
    tip: "Pondicherry University's campus is large and green, south of the town, with campus buses between the departments. Students switch between Tamil and English all the time.",
    phrases: [
      { hi: "இன்னிக்கு எனக்கு முதல் கிளாஸ்.", roman: "Innikku enakku mudhal class.", en: "Today to me first class.", natural: "It's my first class today." },
      { hi: "லைப்ரரி எங்க இருக்கு?", roman: "Library enga irukku?", en: "Where is the library?", natural: "Where's the library?" },
      { hi: "இந்த டிபார்ட்மென்ட் எந்த பில்டிங்?", roman: "Indha department endha building?", en: "This department which building?", natural: "Which building is this department in?" },
      { hi: "நோட்ஸ் ஷேர் பண்ணுவீங்களா?", roman: "Notes share pannuveengalaa?", en: "Will you share notes?", natural: "Could you share your notes?" },
      { hi: "கேன்டீன்ல டீ குடிக்கலாமா?", roman: "Canteenla tea kudikkalaamaa?", en: "Shall we drink tea in the canteen?", natural: "Shall we get tea in the canteen?" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "Sunrise on the Promenade with Bala, a friend from the guesthouse.", scenario: "pdy_smalltalk",
    tip: "Locals call the town “Pondy”. The Promenade (Beach Road) closes to traffic in the evening and the whole town walks there; sunrise is just as popular.",
    phrases: [
      { hi: "கடல் ரொம்ப அழகா இருக்கு!", roman: "Kadal romba azhagaa irukku!", en: "The sea is very beautiful!", natural: "The sea is beautiful!" },
      { hi: "பாண்டிச்சேரி ரொம்ப அமைதியான ஊரு.", roman: "Pondicherry romba amaidhiyaana ooru.", en: "Pondicherry is a very peaceful town.", natural: "Pondicherry is such a peaceful place." },
      { hi: "நீங்க இங்கயே பொறந்தீங்களா?", roman: "Neenga ingaye porandheengalaa?", en: "Were you born here itself?", natural: "Were you born here?" },
      { hi: "சண்டே ஆரோவில் போலாமா?", roman: "Sunday Auroville polaamaa?", en: "Shall we go to Auroville on Sunday?", natural: "Shall we go to Auroville on Sunday?" },
      { hi: "சரி, அப்போ சண்டே பாக்கலாம்!", roman: "Sari, appo Sunday paakkalaam!", en: "Okay, then we'll see on Sunday!", natural: "Great, see you on Sunday!" },
    ] },
];

// Puducherry roleplays in Tamil (offline engine rules, romanised as learners type). Their scene text is also on the server's allowlist.
Object.assign(window.SCENARIOS, {
  pdy_greetings: { category: "greetings", icon: "🏡", title: "Check in at your guesthouse", partner: "Selvi", role: "Guesthouse owner", place: "Your guesthouse in White Town",
    goal: "Greet your host, introduce yourself and ask when breakfast is.",
    opening: { text: "Vanakkam! Neenga dhaan London guest-aa? Naan Selvi, indha guesthouse owner.", en: "Hello! Are you the guest from London? I'm Selvi, the guesthouse owner." },
    start: ["Vanakkam, nallaa irukeengalaa?", "En peru Alex, Londonlerndhu vandhirukken.", "Kaalai tiffin ethanai manikku?"],
    rules: [
      { m: ["nandri", "thank", "paakkalaam", "bye"], text: "Paravaayilla! Edhavadhu venumnaa sollunga. 🙏", en: "No problem! Tell me if you need anything.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri, room superaa irukku!" },
      { m: ["tiffin", "breakfast", "saapadu"], text: "Tiffin kaalaila ezhu manilerndhu pathu mani varaikkum. Idli, dosai, croissant-um irukku!", en: "Breakfast is from seven to ten. Idli, dosa, and croissants too!", s: ["Super!", "Romba nandri, room superaa irukku!"], hint: "Kaalai tiffin ethanai manikku?" },
      { m: ["vaaram", "naal", "thanga", "week", "stay"], text: "Oru vaaram-aa? Nalla dhaan! Beach, Auroville ellaam paarunga.", en: "A week? Lovely! See the beach, Auroville, everything.", s: ["Kaalai tiffin ethanai manikku?", "Romba nandri, room superaa irukku!"], hint: "Inga oru vaaram thanga poren." },
      { m: ["peru", "name", "alex", "london"], text: "London-aa! Nalla peru. Inga evvalavu naal irukkeenga?", en: "London! Nice name. How many days are you here for?", s: ["Inga oru vaaram thanga poren.", "Rendu naal dhaan."], hint: "En peru Alex, Londonlerndhu vandhirukken." },
      { m: ["super", "nallaa irukku", "room", "nice", "azhagaa"], text: "Romba santhosham! Kadal pakkathula dhaan, kaalaila nadandhu ponga.", en: "So glad! The sea is close by; take a walk in the morning.", s: ["Kaalai tiffin ethanai manikku?", "Romba nandri!"], hint: "Room superaa irukku!" },
      { m: ["vanakkam", "nallaa", "eppadi", "hello", "bonjour", " hi "], text: "Naan nallaa irukken! Unga peru enna?", en: "I'm well! What's your name?", s: ["En peru Alex, Londonlerndhu vandhirukken.", "Inga oru vaaram thanga poren."], hint: "Vanakkam, nallaa irukeengalaa?" },
    ],
    fallback: { text: "Sari. Vera edhavadhu venumaa? Tiffin, towel, Wi-Fi?", en: "Right. Do you need anything else? Breakfast, a towel, the Wi-Fi?", s: ["Kaalai tiffin ethanai manikku?", "Romba nandri!"] } },

  pdy_scooter: { category: "transport", icon: "🛵", title: "Rent a scooter", partner: "Velu", role: "Rental shop owner", place: "A scooter rental shop on Mission Street",
    goal: "Rent a scooter for the day at a fair price, with a helmet.",
    opening: { text: "Vaanga! Scooter-aa, cycle-aa?", en: "Come in! A scooter or a bicycle?" },
    start: ["Scooter vaadagaikku kidaikkumaa?", "Oru naalaikku evvalavu?", "Helmet kudupeengalaa?"],
    rules: [
      { m: ["nandri", "thank", "gpay", "upi", "paakkalaam", "edukkaren"], text: "Nandri! Paathu ottunga, helmet podunga. 🙏", en: "Thank you! Ride carefully, and wear the helmet.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri!" },
      { m: ["license", "licence"], text: "Sari, license paathaachu. Indhaanga key!", en: "Okay, licence checked. Here's the key!", s: ["Petrol enga podanum?", "Romba nandri!"], hint: "Indhaanga license." },
      { m: ["koraiyunga", "koraichu", "adhigam", "kammi"], text: "Sari, ungalukku munnooru-ambadhu. Last price!", en: "Okay, three hundred and fifty for you. Last price!", s: ["Sari, edukkaren.", "Helmet kudupeengalaa?"], hint: "Romba adhigam, konjam koraiyunga." },
      { m: ["helmet"], text: "Helmet free dhaan. Petrol neenga dhaan podanum.", en: "The helmet is free. You fill the petrol yourself.", s: ["Petrol enga podanum?", "Sari, edukkaren."], hint: "Helmet kudupeengalaa?" },
      { m: ["petrol", "fuel", "bunk"], text: "Mission Street mudivula oru petrol bunk irukku.", en: "There's a petrol station at the end of Mission Street.", s: ["Aurovillukku endha vazhi?", "Romba nandri!"], hint: "Petrol enga podanum?" },
      { m: ["auroville", "vazhi", "beach", "route"], text: "ECR-la neraa ponga, Auroville board paathu leftla thirumbunga. Arai mani dhaan.", en: "Go straight on the ECR and turn left at the Auroville sign. It's only half an hour.", s: ["Romba nandri!", "Helmet kudupeengalaa?"], hint: "Aurovillukku endha vazhi?" },
      { m: ["evvalavu", "price", "rate", "naalaikku"], text: "Oru naalaikku naanooru rupaai. License kaattunga.", en: "Four hundred rupees a day. Show me your licence.", s: ["Indhaanga license.", "Romba adhigam, konjam koraiyunga."], hint: "Oru naalaikku evvalavu?" },
      { m: ["scooter", "vaadagai", "cycle", "bike", "kidaikkumaa"], text: "Kidaikkum! Activa irukku, nalla condition.", en: "Yes! There's an Activa in good condition.", s: ["Oru naalaikku evvalavu?", "Helmet kudupeengalaa?"], hint: "Scooter vaadagaikku kidaikkumaa?" },
    ],
    fallback: { text: "Scooter, cycle, helmet... enna venum?", en: "A scooter, a bicycle, a helmet... what do you need?", s: ["Scooter vaadagaikku kidaikkumaa?", "Oru naalaikku evvalavu?"] } },

  pdy_food: { category: "food", icon: "🐟", title: "Lunch by the sea", partner: "Rajesh", role: "Waiter", place: "A seaside restaurant on the Promenade",
    goal: "Order a fish curry meal and a fresh lime soda, ask for less spice and pay.",
    opening: { text: "Vaanga! Enna saapidareenga?", en: "Welcome! What would you like to eat?" },
    start: ["Oru meen kuzhambu saapaadu kudunga.", "Innikku enna fresh meen irukku?", "Oru fresh lime soda."],
    rules: [
      { m: ["nandri", "thank", "gpay", "card", "paakkalaam", "vechukonga"], text: "Nandri! Thirumba vaanga. 🙏", en: "Thank you! Come again.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri!" },
      { m: ["bill", "evvalavu", "how much"], text: "Saapaadu, soda, motham munnooru rupaai.", en: "The meal and the soda, three hundred rupees in total.", s: ["Card edupeengalaa?", "Sari, idhu vechukonga."], hint: "Bill kudunga, please." },
      { m: ["kaaram", "spicy"], text: "Sari, kaaram kammiyaa podren.", en: "Okay, I'll make it less spicy.", s: ["Oru fresh lime soda.", "Bill kudunga, please."], hint: "Kaaram konjam kammiyaa podunga." },
      // before the meal rule: "fresh meen" (fresh fish) also contains "meen" (fish)
      { m: ["fresh meen", "enna meen", "fish today"], text: "Innikku vanjiram, eraal irukku. Vanjiram fry semma!", en: "Today there's seer fish and prawns. The seer fish fry is excellent!", s: ["Oru meen kuzhambu saapaadu kudunga.", "Vanjiram fry kudunga."], hint: "Innikku enna fresh meen irukku?" },
      { m: ["sweet", "salt"], text: "Sari, udane varum.", en: "Okay, coming right up.", s: ["Bill kudunga, please.", "Kaaram konjam kammiyaa podunga."] },
      { m: ["soda", "lime", "juice", "coffee", "tea"], text: "Oru fresh lime soda, sweet-aa salt-aa?", en: "One fresh lime soda, sweet or salted?", s: ["Sweet.", "Salt."], hint: "Oru fresh lime soda." },
      { m: ["meen", "kuzhambu", "saapaadu", "vanjiram", "fry", "meals", "saivam"], text: "Oru meen kuzhambu saapaadu! Kaaram venumaa?", en: "One fish curry meal! Do you want it spicy?", s: ["Kaaram konjam kammiyaa podunga.", "Oru fresh lime soda."], hint: "Oru meen kuzhambu saapaadu kudunga." },
    ],
    fallback: { text: "Meen, eraal, saivam meals... enna venum?", en: "Fish, prawns, a vegetarian meals plate... what would you like?", s: ["Oru meen kuzhambu saapaadu kudunga.", "Oru fresh lime soda."] } },

  pdy_shopping: { category: "shopping", icon: "👜", title: "Shopping near Goubert Market", partner: "Anand", role: "Shopkeeper", place: "Nehru Street, near Goubert Market",
    goal: "Buy a handloom bag at a fair price.",
    opening: { text: "Vaanga, paarunga! Ellaam handmade.", en: "Come in, take a look! It's all handmade." },
    start: ["Indha pai enna vilai?", "Idhu kaithariyaa?", "Rendu eduthaa evvalavu?"],
    rules: [
      { m: ["nandri", "thank", "pack", "edukkaren", "card", "gpay", "paakkalaam"], text: "Pack pannitten! Thirumba vaanga. 🙏", en: "Packed! Come again.", s: ["Appuram paakkalaam!"], end: true, hint: "Sari, edukkaren." },
      { m: ["rendu", "two"], text: "Rendu eduthaa aaranooru, ungalukku special.", en: "If you take two, six hundred: a special price for you.", s: ["Sari, edukkaren.", "Card edupeengalaa?"], hint: "Rendu eduthaa evvalavu?" },
      { m: ["adhigam", "koraiyunga", "kammi", "last"], text: "Sari, ungalukku munnooru. Idhukku mela kammi panna mudiyaadhu.", en: "Okay, three hundred for you. I can't go lower than that.", s: ["Sari, edukkaren.", "Rendu eduthaa evvalavu?"], hint: "Romba adhigam, konjam koraiyunga." },
      { m: ["kaithari", "handloom", "cotton", "handmade"], text: "Aamaa, ellaame kaithari dhaan, Puducherry-la senjadhu.", en: "Yes, it's all handloom, made in Puducherry.", s: ["Indha pai enna vilai?", "Rendu eduthaa evvalavu?"], hint: "Idhu kaithariyaa?" },
      { m: ["vilai", "price", "evvalavu", "how much"], text: "Indha pai? Naanooru-ambadhu rupaai.", en: "This bag? Four hundred and fifty rupees.", s: ["Romba adhigam, konjam koraiyunga.", "Idhu kaithariyaa?"], hint: "Indha pai enna vilai?" },
    ],
    fallback: { text: "Bag, scarf, notebook, ellaam irukku. Medhuvaa paarunga!", en: "Bags, scarves, notebooks, we have it all. Take your time!", s: ["Indha pai enna vilai?", "Idhu kaithariyaa?"] } },

  pdy_directions: { category: "directions", icon: "🏖️", title: "Find the Promenade", partner: "Arul", role: "Passerby", place: "Outside the Puducherry bus stand",
    goal: "Find the way to the Promenade beach, and a café near it.",
    opening: { text: "Enna thedureenga?", en: "What are you looking for?" },
    start: ["Beachukku endha vazhiyaa poganum?", "Inga pakkathula nalla cafe irukkaa?", "Nadandhu pogalaamaa?"],
    rules: [
      { m: ["nandri", "thank", "paakkalaam", "purinjudhu"], text: "Paravaayilla! Enjoy pannunga. 🙏", en: "No problem! Enjoy.", s: ["Appuram paakkalaam!"], end: true, hint: "Romba nandri!" },
      // before the beach rule: "vazhi maaritten" (I'm lost) also contains "vazhi" (way)
      { m: ["vazhi maari", "lost", "udhavi"], text: "Kavalai venaam! Neenga ippo bus stand pakkathula irukeenga. Beach pathu nimisham dhaan.", en: "Don't worry! You're near the bus stand now. The beach is just ten minutes away.", s: ["Beachukku endha vazhiyaa poganum?", "Romba nandri!"], hint: "Vazhi maaritten, udhavi pannunga." },
      { m: ["cafe", "coffee", "saapida"], text: "Rue Romain Rolland-la niraiya cafe irukku, beach pakkathula.", en: "There are lots of cafés on Rue Romain Rolland, near the beach.", s: ["Nadandhu pogalaamaa?", "Romba nandri!"], hint: "Inga pakkathula nalla cafe irukkaa?" },
      { m: ["nadandhu", "walk", "dhooram", "far"], text: "Aamaa, nadandhaa pathu nimisham dhaan.", en: "Yes, it's only ten minutes on foot.", s: ["Sari, purinjudhu.", "Romba nandri!"], hint: "Nadandhu pogalaamaa?" },
      { m: ["beach", "promenade", "kadal", "vazhi"], text: "Rightla thirumbi neraa ponga. Kadal munnaadi dhaan Promenade.", en: "Turn right and go straight on. The Promenade is right in front of the sea.", s: ["Nadandhu pogalaamaa?", "Inga pakkathula nalla cafe irukkaa?"], hint: "Beachukku endha vazhiyaa poganum?" },
    ],
    fallback: { text: "Enga poganum-nu sollunga, naan vazhi solren.", en: "Tell me where you need to go and I'll show you the way.", s: ["Beachukku endha vazhiyaa poganum?", "Vazhi maaritten, udhavi pannunga."] } },

  pdy_college: { category: "college", icon: "🎓", title: "First day at Pondicherry University", partner: "Kavitha", role: "Classmate", place: "Pondicherry University campus",
    goal: "Find your department and the library, and make a friend.",
    opening: { text: "Hi! Neenga pudhu student-aa? Naan Kavitha, same class.", en: "Hi! Are you a new student? I'm Kavitha, same class." },
    start: ["Aamaa, innikku enakku mudhal class.", "Library enga irukku?", "Indha department endha building?"],
    rules: [
      { m: ["paakkalaam", "bye", "thank", "nandri", "super"], text: "Welcome! Edhavadhu venumnaa kelunga. 👋", en: "Welcome! Ask me for anything.", s: ["Appuram paakkalaam!"], end: true, hint: "Thank you, Kavitha!" },
      { m: ["tea", "canteen", "coffee", "kudikkalaamaa"], text: "Aamaa, class mudinjadhum canteen polaam!", en: "Yes, let's go to the canteen after class!", s: ["Super!", "Thank you, Kavitha!"], hint: "Canteenla tea kudikkalaamaa?" },
      { m: ["notes", "share"], text: "Kandippaa! Naan WhatsApp-la anupparen.", en: "Of course! I'll send them on WhatsApp.", s: ["Canteenla tea kudikkalaamaa?", "Thank you, Kavitha!"], hint: "Notes share pannuveengalaa?" },
      { m: ["library", "book"], text: "Library main building pakkathula, rendu nimisham dhaan.", en: "The library is next to the main building, just two minutes away.", s: ["Notes share pannuveengalaa?", "Thank you, Kavitha!"], hint: "Library enga irukku?" },
      { m: ["department", "building"], text: "Adhu moonaavadhu building. Campus bus-la ponga.", en: "That's the third building. Take the campus bus.", s: ["Library enga irukku?", "Notes share pannuveengalaa?"], hint: "Indha department endha building?" },
      { m: ["mudhal", "first", "pudhu", "aamaa", "new"], text: "Vaanga! Mudhal naal konjam confusing, aanaa paravaayilla.", en: "Welcome! The first day is a bit confusing, but that's fine.", s: ["Library enga irukku?", "Indha department endha building?"], hint: "Innikku enakku mudhal class." },
    ],
    fallback: { text: "Sollunga, enna venum? Library, canteen, illa department?", en: "Tell me, what do you need? The library, the canteen or the department?", s: ["Library enga irukku?", "Canteenla tea kudikkalaamaa?"] } },

  pdy_smalltalk: { category: "smalltalk", icon: "🌅", title: "Sunrise on the Promenade", partner: "Bala", role: "Friend", place: "The Promenade at sunrise",
    goal: "Chat about Puducherry and plan a trip to Auroville.",
    opening: { text: "Enna, Pondy pidichirukkaa?", en: "So, do you like Pondy?" },
    start: ["Kadal romba azhagaa irukku!", "Pondicherry romba amaidhiyaana ooru.", "Neenga ingaye porandheengalaa?"],
    rules: [
      { m: ["paakkalaam", "bye", "semma", "super"], text: "Semma! Sunday paakkalaam. 👋", en: "Brilliant! See you on Sunday.", s: ["Bye Bala!"], end: true, hint: "Sari, appo Sunday paakkalaam!" },
      { m: ["auroville", "sunday", "plan", "polaamaa"], text: "Sari! Sunday kaalaila scooter-la Auroville polaam, Matrimandir-um paarkalaam.", en: "Sure! Let's ride to Auroville on Sunday morning and see the Matrimandir too.", s: ["Semma!", "Sari, appo Sunday paakkalaam!"], hint: "Sunday Auroville polaamaa?" },
      { m: ["porandheengalaa", "born", "ingaye"], text: "Aamaa, naan inga dhaan porandhen. Pondy maadhiri ooru vera illa!", en: "Yes, I was born right here. There's no town like Pondy!", s: ["Sunday Auroville polaamaa?", "Kadal romba azhagaa irukku!"] },
      { m: ["kadal", "azhagaa", "sea", "beach", "sunrise"], text: "Aamaa, kaalaila sunrise paakka ellaarum inga varuvaanga.", en: "Yes, everyone comes here in the morning to see the sunrise.", s: ["Neenga ingaye porandheengalaa?", "Sunday Auroville polaamaa?"], hint: "Kadal romba azhagaa irukku!" },
      { m: ["amaidhi", "peaceful", "ooru", "quiet"], text: "Correct! Chennai-ai vida romba amaidhi. Aanaa weekend-la tourist koottam!", en: "True! Much quieter than Chennai. But at weekends the tourists flood in!", s: ["Sunday Auroville polaamaa?", "Neenga ingaye porandheengalaa?"], hint: "Pondicherry romba amaidhiyaana ooru." },
      { m: ["sari", "ok", "okay"], text: "Nalla idea! Pondy-la ellaame medhuvaa dhaan nadakkum.", en: "Good idea! In Pondy everything moves slowly.", s: ["Semma!", "Sunday Auroville polaamaa?"] },
    ],
    fallback: { text: "Haha! Pondy-la ungalukku enna pidichadhu?", en: "Haha! What do you like about Pondy?", s: ["Kadal romba azhagaa irukku!", "Pondicherry romba amaidhiyaana ooru."] } },
});

window.CONTENT_REVIEW.puducherry = {
  ta: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-18",
    known_limitations: ["The content teaches spoken Tamil, which differs from written Tamil.", "Romanised Tamil has no fixed spelling: long vowels are written double (aa, ee, oo) and the retroflex sounds are not marked.", "Fares, rental prices and practical tips change over time."],
    note: "Puducherry Tamil: AI-assisted editorial review only, not yet checked by a native Tamil speaker." },
};

const PLACE_PDY = {
  "white town": ["White Town", "வைட் டவுன்", "White Town"], promenade: ["Promenade", "பிரொமனேட்", "the Promenade"], auroville: ["Auroville", "ஆரோவில்", "Auroville"],
  "bus stand": ["bus stand", "பஸ் ஸ்டாண்ட்", "the bus stand"], "paradise beach": ["Paradise Beach", "பாரடைஸ் பீச்", "Paradise Beach"],
  "mission street": ["Mission Street", "மிஷன் ஸ்ட்ரீட்", "Mission Street"], "goubert market": ["Goubert Market", "கூபர் மார்க்கெட்", "Goubert Market"],
  "railway station": ["railway station", "ரயில்வே ஸ்டேஷன்", "the railway station"], "serenity beach": ["Serenity Beach", "செரினிட்டி பீச்", "Serenity Beach"],
};
const PUDUCHERRY_PLACES = ["White Town", "Promenade", "Auroville", "Bus stand", "Paradise Beach", "Mission Street", "Goubert Market", "Railway station", "Serenity Beach"];
const PDY_RIDE_NOTE = "Puducherry's autos don't use meters: agree on the fare before you sit in, or book through an app. For a day out, rent a scooter (about ₹300–700 a day) or a bicycle.";

window.LOCAL_CONTENT.puducherry = {
  // ---------- Puducherry, in Tamil (and the English view) ----------
  ta: {
    tutor: {
      greet: "Vanakkam", places: PUDUCHERRY_PLACES, defaultPlace: "White Town", language: "Tamil",
      starters: ["I need a ride to Auroville.", "How do I rent a scooter?", "How do I bargain at Goubert Market?", "What does 'konjam' mean?", "How do I ask the way to the beach?"],
      glossaryOnly: true,                                // Hindi words are not Tamil: the shared (Hindi) glossary is not used
      glossary: {
        vanakkam: "A respectful hello (and goodbye). Works with anyone, any time.", konjam: "“A little.” “Konjam kammi” = a little less.",
        pondy: "What locals call Puducherry.", rue: "French for “street”: White Town's street signs say “Rue …” in French and Tamil.",
        kaithari: "“Handloom.” Handwoven cloth, sold all over Puducherry.", saapaadu: "“A meal.” A “meals” plate is rice with several curries.",
        venum: "“Want / need.” Enna venum? = What do you need?", venaam: "“Don't want / no thanks.”", evvalavu: "“How much.” Evvalavu aachu? = How much is it?",
        enga: "Where. Enga irukku? = Where is it?", aamaa: "Yes.", illa: "No.", sari: "“Okay / right.”", kudunga: "“Please give.” The polite form of “kudu”.",
        nandri: "Thank you.", vaanga: "“Come (in)!” What shopkeepers and hosts say.", semma: "“Awesome!” Slang, with friends.",
      },
      polite: { intro: "Tamil's polite forms use “neenga” and verbs ending in -unga (“kudunga”, “sollunga”, “pannunga”):", rules: [["\\bkudu\\b", "kudunga"], ["\\bsollu\\b", "sollunga"], ["\\bpannu\\b", "pannunga"], ["\\bnee\\b", "neenga"]],
        note: "e.g. “kudu” → “kudunga”, “sollu” → “sollunga”, “nee” → “neenga”. With friends the short forms are fine." },
      intents: [
        { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
          build: (dest) => { const d = PLACE_PDY[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
            { roman: `${r} pogumaa? Evvalavu?`, hi: d ? `${d[1]} போகுமா? எவ்வளவு?` : "", en: `Will you go to ${d ? d[2] : dest}? How much?` },
            { roman: `${r} varuveengalaa?`, hi: d ? `${d[1]} வருவீங்களா?` : "", en: `A more polite version: Would you come to ${d ? d[2] : dest}?`, label: "More polite" },
            { roman: "Konjam kammi pannunga.", hi: "கொஞ்சம் கம்மி பண்ணுங்க.", en: "Please make it a bit less." },
          ], note: PDY_RIDE_NOTE }; } },
        { m: ["scooter", "bike", "cycle", "rent", "bus", "train", "helmet"], topic: "transport", intro: "At a rental shop, try:", phrases: [
            { roman: "Scooter vaadagaikku kidaikkumaa?", hi: "ஸ்கூட்டர் வாடகைக்கு கிடைக்குமா?", en: "Can I rent a scooter?" },
            { roman: "Oru naalaikku evvalavu?", hi: "ஒரு நாளைக்கு எவ்வளவு?", en: "How much for a day?" },
            { roman: "Helmet kudupeengalaa?", hi: "ஹெல்மெட் குடுப்பீங்களா?", en: "Do you give a helmet?" },
          ], note: "Carry your driving licence: most shops keep a copy or ask for a deposit. Petrol is usually not included." },
        { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
            { roman: "Romba adhigam, konjam koraiyunga.", hi: "ரொம்ப அதிகம், கொஞ்சம் குறைங்க.", en: "That's too much, can you lower it?" },
            { roman: "Rendu eduthaa evvalavu?", hi: "ரெண்டு எடுத்தா எவ்வளவு?", en: "How much if I buy two?" },
            { roman: "Last price enna?", hi: "லாஸ்ட் பிரைஸ் என்ன?", en: "What's your best price?" },
          ], note: "Bargain at Goubert Market and the Sunday market on Mahatma Gandhi Road. White Town boutiques and Auroville shops have fixed prices." },
        { m: ["price", "how much", "cost", "evvalavu", "pay", "upi", "card"], topic: "shopping", intro: "Ask the price like this:", phrases: [
            { roman: "Indha pai enna vilai?", hi: "இந்த பை என்ன விலை?", en: "How much is this bag?" },
            { roman: "Card edupeengalaa?", hi: "கார்டு எடுப்பீங்களா?", en: "Do you take cards?" },
          ] },
        { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "fish", "seafood", "bill"], topic: "food", intro: "Ordering food:", phrases: [
            { roman: "Oru meen kuzhambu saapaadu kudunga.", hi: "ஒரு மீன் குழம்பு சாப்பாடு குடுங்க.", en: "One fish curry meal, please." },
            { roman: "Kaaram konjam kammiyaa podunga.", hi: "காரம் கொஞ்சம் கம்மியா போடுங்க.", en: "Not too spicy, please." },
            { roman: "Oru fresh lime soda.", hi: "ஒரு ஃப்ரெஷ் லைம் சோடா.", en: "A fresh lime soda, please." },
          ], note: "Puducherry is known for seafood and for Creole dishes that mix Tamil and French cooking." },
        { m: ["direction", "where is", "lost", "way", "find", "left", "right", "beach"], topic: "directions", intro: "Asking for directions:", phrases: [
            { roman: "Beachukku endha vazhiyaa poganum?", hi: "பீச்சுக்கு எந்த வழியா போகணும்?", en: "Which way to the beach?" },
            { roman: "Vazhi maaritten, udhavi pannunga.", hi: "வழி மாறிட்டேன், உதவி பண்ணுங்க.", en: "I'm lost, please help me." },
            { roman: "Landmark enna?", hi: "லேண்ட்மார்க் என்ன?", en: "What's the landmark?" },
          ], note: "White Town's streets run in a grid between the canal and the sea. Landmarks: the lighthouse, the Ashram, the Manakula Vinayagar temple." },
        { m: ["class", "college", "university", "professor", "teacher", "office", "work", "colleague", "canteen", "library"], topic: "college", intro: "At college or work:", phrases: [
            { roman: "Innikku enakku mudhal class.", hi: "இன்னிக்கு எனக்கு முதல் கிளாஸ்.", en: "It's my first class today." },
            { roman: "Library enga irukku?", hi: "லைப்ரரி எங்க இருக்கு?", en: "Where's the library?" },
            { roman: "Notes share pannuveengalaa?", hi: "நோட்ஸ் ஷேர் பண்ணுவீங்களா?", en: "Could you share your notes?" },
          ] },
        { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
            { roman: "Neenga endha ooru?", hi: "நீங்க எந்த ஊரு?", en: "Where are you from?" },
            { roman: "Kadal romba azhagaa irukku!", hi: "கடல் ரொம்ப அழகா இருக்கு!", en: "The sea is beautiful!" },
            { roman: "Coffee kudikkalaamaa?", hi: "காபி குடிக்கலாமா?", en: "Shall we have a coffee?" },
          ], note: "Puducherry small talk: the sea, Auroville, the cafés and the weekend crowds from Chennai." },
        { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
            { roman: "En peru Alex.", hi: "என் பேரு அலெக்ஸ்.", en: "My name is Alex." },
            { roman: "Unga peru enna?", hi: "உங்க பேரு என்ன?", en: "What's your name?" },
            { roman: "Ungala paathadhula romba santhosham.", hi: "உங்கள பாத்ததுல ரொம்ப சந்தோஷம்.", en: "Nice to meet you." },
          ] },
        { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
            { roman: "Romba nandri!", hi: "ரொம்ப நன்றி!", en: "Thanks a lot!" },
            { roman: "Mannichikonga.", hi: "மன்னிச்சிக்கோங்க.", en: "Sorry / Excuse me." },
            { roman: "Konjam medhuvaa sollunga.", hi: "கொஞ்சம் மெதுவா சொல்லுங்க.", en: "Please say it a little slowly." },
          ] },
        { m: ["hello", "hi", "greet", "namaste", "vanakkam", "bonjour", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere:", phrases: [
            { roman: "Vanakkam, nallaa irukeengalaa?", hi: "வணக்கம், நல்லா இருக்கீங்களா?", en: "Hello, are you well?" },
            { roman: "Appuram paakkalaam!", hi: "அப்புறம் பாக்கலாம்!", en: "See you later!" },
          ], note: "“Vanakkam” works with everyone; some older residents also say a French “Bonjour”." },
        { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
            { roman: "Enakku udhavi venum.", hi: "எனக்கு உதவி வேணும்.", en: "I need help." },
            { roman: "Pakkathula aaspathri enga irukku?", hi: "பக்கத்துல ஆஸ்பத்திரி எங்க இருக்கு?", en: "Where's the nearest hospital?" },
          ], note: "Emergency number in India: 112." },
      ],
      generic: { intro: "Here are three Tamil phrases that'll get you through almost anything in your first week:", phrases: [
          { roman: "Vanakkam, nallaa irukeengalaa?", hi: "வணக்கம், நல்லா இருக்கீங்களா?", en: "Hello, are you well?" },
          { roman: "Evvalavu aachu?", hi: "எவ்வளவு ஆச்சு?", en: "How much is it?" },
          { roman: "Konjam udhavi pannuveengalaa?", hi: "கொஞ்சம் உதவி பண்ணுவீங்களா?", en: "Could you help me a bit?" },
        ], note: "Tell me a situation — like “I want to rent a scooter” or “ask the way to the beach” — and I'll give you the Tamil words." },
    },
    readings: [
      { title: "Asha in Puducherry", level: "A1", lines: [
          { hi: "ஆஷா பாண்டிச்சேரிக்கு புதுசு.", roman: "Asha Pondicherrykku pudhusu.", en: "Asha is new to Puducherry." },
          { hi: "அவங்க ஸ்கூட்டர் வாடகைக்கு எடுத்தாங்க.", roman: "Avanga scooter vaadagaikku eduthaanga.", en: "She rented a scooter." },
          { hi: "அவங்க ஆரோவில்லுக்கு போனாங்க.", roman: "Avanga Aurovillukku ponaanga.", en: "She went to Auroville." },
          { hi: "அங்க ஒரு கஃபேல காபி குடிச்சாங்க.", roman: "Anga oru cafela coffee kudichaanga.", en: "She had a coffee at a café there." },
        ],
        questions: [
          { q: "Where is Asha new?", options: ["Chennai", "Puducherry", "Bengaluru"], a: 1 },
          { q: "What did she rent?", options: ["A scooter", "A car", "A bicycle"], a: 0 },
          { q: "Where did she go?", options: ["Auroville", "The airport", "Chennai"], a: 0 },
        ] },
      { title: "Lunch by the sea", level: "A1", lines: [
          { hi: "ரவி பீச் பக்கத்துல ஒரு ஹோட்டலுக்கு போனான்.", roman: "Ravi beach pakkathula oru hotelukku ponaan.", en: "Ravi went to a restaurant near the beach." },
          { hi: "அவன் மீன் குழம்பு சாப்பாடு சாப்பிட்டான்.", roman: "Avan meen kuzhambu saapaadu saapittaan.", en: "He ate a fish curry meal." },
          { hi: "அவன் ஒரு லைம் சோடாவும் குடிச்சான்.", roman: "Avan oru lime sodaavum kudichaan.", en: "He also drank a lime soda." },
          { hi: "மொத்தம் முன்னூறு ரூபாய் ஆச்சு.", roman: "Motham munnooru rupaai aachu.", en: "It all came to three hundred rupees." },
        ],
        questions: [
          { q: "Where did Ravi eat?", options: ["Near the beach", "At home", "At the station"], a: 0 },
          { q: "What did he eat?", options: ["Fish curry", "Idli", "Biryani"], a: 0 },
          { q: "How much did it cost?", options: ["₹30", "₹300", "₹3000"], a: 1 },
        ] },
    ],
    placement: [
      { q: "What does “Vanakkam” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
      { q: "How would you ask to rent a scooter?", options: ["Scooter vaadagaikku kidaikkumaa?", "Evvalavu aachu?", "Oru coffee kudunga.", "Appuram paakkalaam!"], a: 0 },
      { q: "What does “evvalavu aachu” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
      { q: "“Rightla thirumbi neraa ponga” means…", options: ["Stop here", "Turn right and go straight on", "Turn left twice", "Wait for the bus"], a: 1 },
      { q: "Which is the polite way to say “please give”?", options: ["Kudu", "Kudunga", "Venaam", "Podhum"], a: 1 },
    ],
    achievements: {
      "first-words": ["👋", "First words", "Said your first Tamil phrase"], "auto-pro": ["🛵", "Scooter rider", "Rented a scooter"],
      foodie: ["🐟", "Seafood lover", "Ordered a seafood meal"], bargainer: ["🛍️", "Goubert Market bargainer", "Won a bargain"],
    },
    rightNow: [
      [5, 11, "🌅", "Sunrise on the Promenade", "The whole town walks by the sea in the early morning.", "pdy_smalltalk", { roman: "Kadal romba azhagaa irukku!", hi: "கடல் ரொம்ப அழகா இருக்கு!", en: "The sea is beautiful!" }],
      [11, 15, "🐟", "Lunch time", "Seaside restaurants serve the morning's catch. Order like a local.", "pdy_food", { roman: "Oru meen kuzhambu saapaadu kudunga.", hi: "ஒரு மீன் குழம்பு சாப்பாடு குடுங்க.", en: "One fish curry meal, please." }],
      [15, 18, "🛍️", "Market hours", "Goubert Market and Nehru Street are busy. Time to bargain.", "pdy_shopping", { roman: "Indha pai enna vilai?", hi: "இந்த பை என்ன விலை?", en: "How much is this bag?" }],
      [18, 22, "🚶", "Evening on the Promenade", "Beach Road closes to traffic in the evening and the town comes out to walk.", "pdy_directions", { roman: "Beachukku endha vazhiyaa poganum?", hi: "பீச்சுக்கு எந்த வழியா போகணும்?", en: "Which way to the beach?" }],
      [22, 29, "🌙", "Late night walk home", "White Town is quiet at night; keep to the lit streets near the sea.", "pdy_directions", { roman: "Vazhi maaritten, udhavi pannunga.", hi: "வழி மாறிட்டேன், உதவி பண்ணுங்க.", en: "I'm lost, please help me." }],
    ],
    priceSay: (max, mid) => ({
      ticket: { roman: "Oru ticket kudunga.", hi: "ஒரு டிக்கெட் குடுங்க.", en: "One ticket, please." },
      meter: { roman: "Evvalavu aagum?", hi: "எவ்வளவு ஆகும்?", en: "How much will it be?" },
      fair: { roman: "Sari, edukkaren.", hi: "சரி, எடுக்கறேன்.", en: "Okay, I'll take it." },
      counter: { roman: `${max} rupaaikku tharuveengalaa?`, hi: `${max} ரூபாய்க்கு தருவீங்களா?`, en: `Will you do it for ₹${max}?` },
      high: { roman: `Romba adhigam. ${mid} rupaaikku tharuveengalaa?`, hi: `ரொம்ப அதிகம். ${mid} ரூபாய்க்கு தருவீங்களா?`, en: `That's too much. Will you do ₹${mid}?` },
    }),
  },
};

// Puducherry in French (Tamil · French · English): the language of White Town's heritage homes, the Lycée français, the Alliance française
// and the French consulate. `hi` holds the French as written (with accents), `roman` the same without accents (how it is often typed; the
// server accepts both) and `pron` an English-speaker's pronunciation guide. AI-assisted editorial review only.
window.LANGUAGE_PACKS.puducherry = { fr: [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your hosts and introduce yourself in French.",
    situation: "You arrive at a heritage home on Rue Dumas, in White Town. Madame Rosaline, your host, opens the door.", scenario: "pdy_fr_greetings",
    tip: "French is spoken by Franco-Pondicherrian families, at the Lycée français, the Alliance française and the French consulate. Use “vous” with people you have just met; “tu” is for friends and children.",
    phrases: [
      { hi: "Bonjour, comment allez-vous ?", roman: "Bonjour, comment allez-vous ?", pron: "bon-ZHOOR, ko-mahn-ta-lay-VOO", en: "Good day, how are you going?", natural: "Hello, how are you?" },
      { hi: "Je m'appelle Alex, je viens de Londres.", roman: "Je m'appelle Alex, je viens de Londres.", pron: "zhuh ma-PEL a-LEX, zhuh vyen duh LONDR", en: "I call myself Alex, I come from London.", natural: "I'm Alex, from London." },
      { hi: "Je suis nouveau ici.", roman: "Je suis nouveau ici.", pron: "zhuh swee noo-VOH ee-SEE", en: "I am new here.", natural: "I'm new here.",
        fem: { hi: "Je suis nouvelle ici.", roman: "Je suis nouvelle ici.", pron: "zhuh swee noo-VEL ee-SEE" } },
      { hi: "Le petit-déjeuner est à quelle heure ?", roman: "Le petit-dejeuner est a quelle heure ?", pron: "luh puh-TEE day-zhuh-NAY ay ta kel UR", en: "The breakfast is at what hour?", natural: "What time is breakfast?" },
      { hi: "Merci beaucoup, c'est très joli !", roman: "Merci beaucoup, c'est tres joli !", pron: "mair-SEE boh-KOO, say tray zho-LEE", en: "Thank you much, it's very pretty!", natural: "Thanks so much, it's lovely!" },
    ] },
  { day: 2, key: "transport", icon: "🚲", title: "Transport", desc: "Rent a bicycle and find your way out of town.",
    situation: "You want a bicycle for the day from a rental shop on Rue Suffren.", scenario: "pdy_fr_bike",
    tip: "White Town is flat and compact: a bicycle is the best way round its streets. Rental shops usually ask for an ID and a deposit. Auto and taxi drivers speak Tamil and some English rather than French.",
    phrases: [
      { hi: "Je voudrais louer un vélo.", roman: "Je voudrais louer un velo.", pron: "zhuh voo-DRAY loo-AY uhn vay-LOH", en: "I would like to rent a bicycle.", natural: "I'd like to rent a bike." },
      { hi: "C'est combien pour la journée ?", roman: "C'est combien pour la journee ?", pron: "say kom-BYEN poor la zhoor-NAY", en: "It is how much for the day?", natural: "How much for the day?" },
      { hi: "Il y a un casque ?", roman: "Il y a un casque ?", pron: "eel ee a uhn KASK", en: "There is a helmet?", natural: "Is there a helmet?" },
      { hi: "Pour aller à Auroville, s'il vous plaît ?", roman: "Pour aller a Auroville, s'il vous plait ?", pron: "poor a-LAY a o-ro-VEEL, seel voo PLAY", en: "For going to Auroville, please?", natural: "Which way to Auroville, please?" },
      { hi: "Je peux le rendre à six heures ?", roman: "Je peux le rendre a six heures ?", pron: "zhuh puh luh RAHNDR a see ZUR", en: "I can give it back at six hours?", natural: "Can I bring it back at six?" },
    ] },
  { day: 3, key: "food", icon: "🥐", title: "Food", desc: "Order breakfast in a White Town café.",
    situation: "Breakfast at a café on Rue Romain Rolland.", scenario: "pdy_fr_food",
    tip: "White Town's cafés serve French bakery classics next to filter coffee and Creole dishes. Say “s'il vous plaît” with every order; in many cafés a service charge is already on the bill.",
    phrases: [
      { hi: "Un café et un croissant, s'il vous plaît.", roman: "Un cafe et un croissant, s'il vous plait.", pron: "uhn ka-FAY ay uhn krwa-SAHN, seel voo PLAY", en: "A coffee and a croissant, please.", natural: "A coffee and a croissant, please." },
      { hi: "Qu'est-ce que vous recommandez ?", roman: "Qu'est-ce que vous recommandez ?", pron: "kes-kuh voo ruh-ko-mahn-DAY", en: "What is it that you recommend?", natural: "What do you recommend?" },
      { hi: "Je suis végétarien.", roman: "Je suis vegetarien.", pron: "zhuh swee vay-zhay-ta-RYEN", en: "I am vegetarian.", natural: "I'm vegetarian.",
        fem: { hi: "Je suis végétarienne.", roman: "Je suis vegetarienne.", pron: "zhuh swee vay-zhay-ta-RYEN" } },
      { hi: "Pas trop épicé, s'il vous plaît.", roman: "Pas trop epice, s'il vous plait.", pron: "pa troh ay-pee-SAY, seel voo PLAY", en: "Not too spiced, please.", natural: "Not too spicy, please." },
      { hi: "L'addition, s'il vous plaît.", roman: "L'addition, s'il vous plait.", pron: "la-dee-SYOHN, seel voo PLAY", en: "The bill, please.", natural: "Can I have the bill, please?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Shop in White Town's boutiques.",
    situation: "You're in a boutique on Rue Suffren, looking at handmade bags.", scenario: "pdy_fr_shopping",
    tip: "White Town boutiques have fixed prices, so don't bargain there; bargaining is for Goubert Market, in Tamil. “Je le prends” (I'll take it) closes any sale.",
    phrases: [
      { hi: "Combien coûte ce sac ?", roman: "Combien coute ce sac ?", pron: "kom-BYEN koot suh SAK", en: "How much costs this bag?", natural: "How much is this bag?" },
      { hi: "C'est fait à la main ?", roman: "C'est fait a la main ?", pron: "say fay a la MAN", en: "It is made by the hand?", natural: "Is it handmade?" },
      { hi: "Vous l'avez dans une autre couleur ?", roman: "Vous l'avez dans une autre couleur ?", pron: "voo la-VAY dahn zün OHTR koo-LUR", en: "You have it in another colour?", natural: "Do you have it in another colour?" },
      { hi: "Je peux payer par carte ?", roman: "Je peux payer par carte ?", pron: "zhuh puh pay-YAY par KART", en: "I can pay by card?", natural: "Can I pay by card?" },
      { hi: "Je le prends, merci.", roman: "Je le prends, merci.", pron: "zhuh luh PRAHN, mair-SEE", en: "I take it, thank you.", natural: "I'll take it, thanks." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find the Promenade, the Alliance française and your way.",
    situation: "You're near the French Consulate in White Town.", scenario: "pdy_fr_directions",
    tip: "The street signs in the French quarter say “Rue” in French and Tamil. Landmarks everyone knows: the French Consulate, the Lycée français, the Alliance française and the statue of Joan of Arc.",
    phrases: [
      { hi: "Excusez-moi, où est la promenade ?", roman: "Excusez-moi, ou est la promenade ?", pron: "ex-kü-zay-MWA, oo ay la prom-NAD", en: "Excuse me, where is the promenade?", natural: "Excuse me, where's the Promenade?" },
      { hi: "Allez tout droit, puis tournez à gauche.", roman: "Allez tout droit, puis tournez a gauche.", pron: "a-LAY too DRWA, pwee toor-NAY a GOHSH", en: "Go all straight, then turn to the left.", natural: "Go straight on, then turn left." },
      { hi: "C'est loin d'ici ?", roman: "C'est loin d'ici ?", pron: "say LWAN dee-SEE", en: "It is far from here?", natural: "Is it far from here?" },
      { hi: "Je cherche l'Alliance française.", roman: "Je cherche l'Alliance francaise.", pron: "zhuh SHAIRSH la-lee-AHNS frahn-SEZ", en: "I am looking for the Alliance française.", natural: "I'm looking for the Alliance française." },
      { hi: "Vous pouvez répéter plus lentement ?", roman: "Vous pouvez repeter plus lentement ?", pron: "voo poo-VAY ray-pay-TAY plü lahnt-MAHN", en: "You can repeat more slowly?", natural: "Could you say that again, more slowly?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle into a French class and make friends.",
    situation: "Your first French class at the Alliance française.", scenario: "pdy_fr_college",
    tip: "The Alliance française in White Town runs French classes and cultural events, and classmates use “tu” with each other. Puducherry also has a Lycée français and the French Institute of Pondicherry.",
    phrases: [
      { hi: "C'est mon premier cours aujourd'hui.", roman: "C'est mon premier cours aujourd'hui.", pron: "say mon pruh-MYAY KOOR oh-zhoor-DWEE", en: "It is my first class today.", natural: "It's my first class today." },
      { hi: "Le cours commence à quelle heure ?", roman: "Le cours commence a quelle heure ?", pron: "luh KOOR ko-MAHNS a kel UR", en: "The class begins at what hour?", natural: "What time does the class start?" },
      { hi: "Où est la bibliothèque ?", roman: "Ou est la bibliotheque ?", pron: "oo ay la bee-blee-oh-TEK", en: "Where is the library?", natural: "Where's the library?" },
      { hi: "Tu peux m'aider ?", roman: "Tu peux m'aider ?", pron: "tü puh may-DAY", en: "You can help me?", natural: "Can you help me?" },
      { hi: "On prend un café après ?", roman: "On prend un cafe apres ?", pron: "on PRAHN uhn ka-FAY a-PRAY", en: "We take a coffee after?", natural: "Coffee afterwards?" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "A café terrace on the Promenade with Marc, a friend from your French class.", scenario: "pdy_fr_smalltalk",
    tip: "Franco-Pondicherrian families mix French, Tamil and English, so you'll hear “Bonjour” and “Vanakkam” in the same conversation. “À dimanche” means “see you on Sunday”.",
    phrases: [
      { hi: "Il fait beau aujourd'hui !", roman: "Il fait beau aujourd'hui !", pron: "eel fay BOH oh-zhoor-DWEE", en: "It makes fine today!", natural: "Lovely weather today!" },
      { hi: "Pondichéry est une ville très calme.", roman: "Pondichery est une ville tres calme.", pron: "pon-dee-shay-REE ay tün VEEL tray KALM", en: "Pondicherry is a very calm town.", natural: "Pondicherry is such a peaceful town." },
      { hi: "Vous êtes d'ici ?", roman: "Vous etes d'ici ?", pron: "voo ZET dee-SEE", en: "You are from here?", natural: "Are you from here?" },
      { hi: "On va à Auroville dimanche ?", roman: "On va a Auroville dimanche ?", pron: "on VA a o-ro-VEEL dee-MAHNSH", en: "We go to Auroville Sunday?", natural: "Shall we go to Auroville on Sunday?" },
      { hi: "Super, à dimanche !", roman: "Super, a dimanche !", pron: "sü-PAIR, a dee-MAHNSH", en: "Super, until Sunday!", natural: "Great, see you Sunday!" },
    ] },
] };

// Puducherry roleplays in French (offline engine rules; the engine ignores accents, so “très” and “tres” match the same rule).
Object.assign(window.SCENARIOS, {
  pdy_fr_greetings: { category: "greetings", icon: "🏡", title: "Arrive at a heritage home (French)", partner: "Madame Rosaline", role: "Host", place: "A heritage home on Rue Dumas, White Town",
    goal: "Greet your host in French, introduce yourself and ask about breakfast.",
    opening: { text: "Bonjour ! Vous êtes Alex ? Bienvenue à Pondichéry !", en: "Hello! Are you Alex? Welcome to Pondicherry!" },
    start: ["Bonjour, comment allez-vous ?", "Oui, je m'appelle Alex.", "Le petit-déjeuner est à quelle heure ?"],
    rules: [
      { m: ["merci", "au revoir", "a bientot", "bonne journee"], text: "Avec plaisir ! N'hésitez pas si vous avez besoin de quelque chose. 🙏", en: "My pleasure! Just ask if you need anything.", s: ["Au revoir, à bientôt !"], end: true, hint: "Merci beaucoup, c'est très joli !" },
      { m: ["petit-dejeuner", "dejeuner", "breakfast", "heure"], text: "Le petit-déjeuner est servi de sept heures à dix heures, dans le jardin.", en: "Breakfast is served from seven to ten, in the garden.", s: ["Parfait !", "Merci beaucoup, c'est très joli !"], hint: "Le petit-déjeuner est à quelle heure ?" },
      { m: ["premiere fois", "nouveau", "nouvelle", "first"], text: "C'est votre première fois ici ? Vous allez adorer le quartier français.", en: "Is this your first time here? You'll love the French quarter.", s: ["Le petit-déjeuner est à quelle heure ?", "Merci beaucoup, c'est très joli !"], hint: "C'est ma première fois ici." },
      { m: ["semaine", "jours", "week"], text: "Une semaine, c'est parfait pour visiter Pondichéry et Auroville.", en: "A week is perfect for seeing Pondicherry and Auroville.", s: ["Le petit-déjeuner est à quelle heure ?", "Merci beaucoup !"] },
      { m: ["m'appelle", "appelle", "alex", "londres", "london"], text: "Enchantée, Alex ! Vous venez de Londres ? Vous restez combien de temps ?", en: "Pleased to meet you, Alex! Are you from London? How long are you staying?", s: ["Une semaine.", "C'est ma première fois ici."], hint: "Je m'appelle Alex, je viens de Londres." },
      { m: ["joli", "parfait", "super", "beau", "belle", "nice"], text: "Merci ! La maison a cent ans. Le petit-déjeuner est dans le jardin.", en: "Thank you! The house is a hundred years old. Breakfast is in the garden.", s: ["Le petit-déjeuner est à quelle heure ?", "Merci beaucoup !"], hint: "C'est très joli !" },
      { m: ["bonjour", "comment allez", "ca va", "salut", "hello"], text: "Très bien, merci ! Vous êtes bien Alex, n'est-ce pas ?", en: "Very well, thank you! You're Alex, aren't you?", s: ["Oui, je m'appelle Alex.", "C'est ma première fois ici."], hint: "Bonjour, comment allez-vous ?" },
    ],
    fallback: { text: "Pardon ? Vous avez besoin du Wi-Fi, d'une serviette ?", en: "Sorry? Do you need the Wi-Fi, a towel?", s: ["Le petit-déjeuner est à quelle heure ?", "Merci beaucoup !"] } },

  pdy_fr_bike: { category: "transport", icon: "🚲", title: "Rent a bicycle (French)", partner: "Monsieur Pierre", role: "Bicycle rental owner", place: "A bicycle rental on Rue Suffren",
    goal: "Rent a bicycle for the day, with a helmet, and find the way to Auroville.",
    opening: { text: "Bonjour ! Vous voulez un vélo ?", en: "Hello! Would you like a bicycle?" },
    start: ["Je voudrais louer un vélo.", "C'est combien pour la journée ?", "Il y a un casque ?"],
    rules: [
      { m: ["merci", "au revoir", "a bientot", "d'accord", "je le prends"], text: "Bonne balade ! Faites attention sur la route. 🙏", en: "Enjoy the ride! Take care on the road.", s: ["Au revoir !"], end: true, hint: "Merci beaucoup !" },
      { m: ["passeport", "piece d'identite", "carte d'identite", "voila"], text: "Parfait, merci. Voilà la clé du cadenas !", en: "Perfect, thank you. Here's the key to the lock!", s: ["Je peux le rendre à six heures ?", "Pour aller à Auroville, s'il vous plaît ?"], hint: "Voilà mon passeport." },
      { m: ["trop cher", "moins cher", "reduction", "cher"], text: "Bon, pour vous, cent vingt roupies. C'est mon dernier prix !", en: "All right, a hundred and twenty rupees for you. That's my last price!", s: ["D'accord, je le prends.", "Il y a un casque ?"], hint: "C'est un peu cher." },
      { m: ["casque", "helmet"], text: "Oui, le casque est gratuit. Il me faut une pièce d'identité.", en: "Yes, the helmet is free. I need an ID.", s: ["Voilà mon passeport.", "D'accord, je le prends."], hint: "Il y a un casque ?" },
      { m: ["rendre", "six heures", "ce soir"], text: "Oui, avant sept heures, s'il vous plaît.", en: "Yes, before seven, please.", s: ["Pour aller à Auroville, s'il vous plaît ?", "Merci beaucoup !"], hint: "Je peux le rendre à six heures ?" },
      // before the price rule: "combien de temps" (how long) also contains "combien" (how much)
      { m: ["loin", "far", "combien de temps"], text: "À vélo, à peu près une heure. Partez tôt, avant la chaleur !", en: "About an hour by bike. Leave early, before the heat!", s: ["Merci beaucoup !", "Je peux le rendre à six heures ?"] },
      { m: ["auroville", "pour aller", "route", "chemin"], text: "Auroville, c'est à une douzaine de kilomètres. Prenez l'ECR vers le nord, c'est indiqué.", en: "Auroville is about twelve kilometres away. Take the ECR north; it's signposted.", s: ["Merci beaucoup !", "C'est loin d'ici ?"], hint: "Pour aller à Auroville, s'il vous plaît ?" },
      { m: ["combien", "prix", "tarif"], text: "C'est cent cinquante roupies pour la journée.", en: "It's a hundred and fifty rupees for the day.", s: ["C'est un peu cher.", "D'accord, je le prends."], hint: "C'est combien pour la journée ?" },
      { m: ["velo", "louer", "bicyclette", "bike"], text: "Bien sûr ! J'ai un très bon vélo, presque neuf.", en: "Of course! I have a very good bike, almost new.", s: ["C'est combien pour la journée ?", "Il y a un casque ?"], hint: "Je voudrais louer un vélo." },
    ],
    fallback: { text: "Pardon ? Un vélo, un casque, un cadenas ?", en: "Sorry? A bike, a helmet, a lock?", s: ["Je voudrais louer un vélo.", "C'est combien pour la journée ?"] } },

  pdy_fr_food: { category: "food", icon: "🥐", title: "Breakfast in a White Town café (French)", partner: "Julien", role: "Café owner", place: "A café on Rue Romain Rolland",
    goal: "Order breakfast in French, ask what's good and pay.",
    opening: { text: "Bonjour ! Qu'est-ce que je vous sers ?", en: "Hello! What can I get you?" },
    start: ["Un café et un croissant, s'il vous plaît.", "Qu'est-ce que vous recommandez ?", "L'addition, s'il vous plaît."],
    rules: [
      { m: ["merci", "au revoir", "a bientot", "carte", "gpay"], text: "Merci à vous, bonne journée ! 🙏", en: "Thank you, have a good day!", s: ["Au revoir !"], end: true, hint: "Merci beaucoup !" },
      { m: ["addition", "combien", "payer"], text: "Ça fait trois cent cinquante roupies, s'il vous plaît.", en: "That's three hundred and fifty rupees, please.", s: ["Par carte, s'il vous plaît.", "Merci beaucoup !"], hint: "L'addition, s'il vous plaît." },
      { m: ["epice", "piquant", "spicy"], text: "Pas de problème, le chef le fera moins épicé.", en: "No problem, the chef will make it less spicy.", s: ["L'addition, s'il vous plaît.", "Merci beaucoup !"], hint: "Pas trop épicé, s'il vous plaît." },
      { m: ["vegetarien", "vegetarienne", "viande"], text: "Nous avons une quiche aux légumes et un curry créole végétarien.", en: "We have a vegetable quiche and a vegetarian Creole curry.", s: ["Le curry créole, s'il vous plaît.", "Pas trop épicé, s'il vous plaît."], hint: "Pas de viande, s'il vous plaît." },
      { m: ["recommandez", "conseillez", "specialite"], text: "Le curry créole de poisson, c'est notre spécialité !", en: "The Creole fish curry is our speciality!", s: ["Le curry créole, s'il vous plaît.", "Pas trop épicé, s'il vous plaît."], hint: "Qu'est-ce que vous recommandez ?" },
      { m: ["cafe", "croissant", "jus", "curry", "creole", "quiche"], text: "Très bien ! Et avec ça ?", en: "Very good! Anything else?", s: ["C'est tout, merci.", "Pas trop épicé, s'il vous plaît."], hint: "Un café et un croissant, s'il vous plaît." },
    ],
    fallback: { text: "Pardon ? Un café, un croissant, un jus de fruits ?", en: "Sorry? A coffee, a croissant, a fruit juice?", s: ["Un café et un croissant, s'il vous plaît.", "Qu'est-ce que vous recommandez ?"] } },

  pdy_fr_shopping: { category: "shopping", icon: "👜", title: "Shopping in a boutique (French)", partner: "Madame Claire", role: "Boutique owner", place: "A boutique on Rue Suffren",
    goal: "Buy a handmade bag and pay by card.",
    opening: { text: "Bonjour ! Je peux vous aider ?", en: "Hello! Can I help you?" },
    start: ["Combien coûte ce sac ?", "C'est fait à la main ?", "Vous l'avez dans une autre couleur ?"],
    rules: [
      { m: ["merci", "au revoir", "je le prends", "je la prends"], text: "Merci beaucoup, bonne journée ! 🙏", en: "Thank you very much, have a good day!", s: ["Au revoir !"], end: true, hint: "Je le prends, merci." },
      { m: ["carte", "payer", "especes"], text: "Oui, bien sûr, nous acceptons les cartes.", en: "Yes, of course, we take cards.", s: ["Je le prends, merci.", "Combien coûte ce sac ?"], hint: "Je peux payer par carte ?" },
      { m: ["couleur", "bleu", "rouge", "vert", "autre"], text: "Oui, nous l'avons aussi en bleu et en vert.", en: "Yes, we also have it in blue and green.", s: ["En bleu, s'il vous plaît.", "Combien coûte ce sac ?"], hint: "Vous l'avez dans une autre couleur ?" },
      { m: ["a la main", "artisanal", "coton"], text: "Oui, c'est fait à la main ici, à Pondichéry, en coton.", en: "Yes, it's handmade here in Pondicherry, in cotton.", s: ["Combien coûte ce sac ?", "Vous l'avez dans une autre couleur ?"], hint: "C'est fait à la main ?" },
      { m: ["combien", "prix", "coute", "cher"], text: "Ce sac coûte mille deux cents roupies. Ici, les prix sont fixes.", en: "This bag costs twelve hundred rupees. Prices are fixed here.", s: ["Je peux payer par carte ?", "Je le prends, merci."], hint: "Combien coûte ce sac ?" },
    ],
    fallback: { text: "Prenez votre temps ! Sacs, foulards, carnets…", en: "Take your time! Bags, scarves, notebooks…", s: ["Combien coûte ce sac ?", "C'est fait à la main ?"] } },

  pdy_fr_directions: { category: "directions", icon: "🧭", title: "Find your way in White Town (French)", partner: "Monsieur Joseph", role: "Passerby", place: "Near the French Consulate, White Town",
    goal: "Find the Promenade and the Alliance française.",
    opening: { text: "Bonjour ! Vous cherchez quelque chose ?", en: "Hello! Are you looking for something?" },
    start: ["Excusez-moi, où est la promenade ?", "Je cherche l'Alliance française.", "C'est loin d'ici ?"],
    rules: [
      { m: ["merci", "au revoir", "compris"], text: "Je vous en prie, bonne promenade ! 🙏", en: "You're welcome, enjoy your walk!", s: ["Au revoir !"], end: true, hint: "Merci beaucoup !" },
      { m: ["repeter", "lentement", "pardon"], text: "Bien sûr : tout droit, puis à gauche. C'est tout !", en: "Of course: straight on, then left. That's all!", s: ["D'accord, j'ai compris.", "C'est loin d'ici ?"], hint: "Vous pouvez répéter plus lentement ?" },
      { m: ["alliance", "francaise", "cours de francais"], text: "L'Alliance française ? C'est rue Suffren, à cinq minutes à pied.", en: "The Alliance française? It's on Rue Suffren, five minutes' walk.", s: ["Merci beaucoup !", "Vous pouvez répéter plus lentement ?"], hint: "Je cherche l'Alliance française." },
      { m: ["loin", "minutes", "a pied", "marcher"], text: "Non, c'est tout près, à cinq minutes à pied.", en: "No, it's very close, five minutes' walk.", s: ["D'accord, j'ai compris.", "Merci beaucoup !"], hint: "C'est loin d'ici ?" },
      { m: ["promenade", "plage", "mer", "ou est"], text: "Allez tout droit, puis tournez à gauche. La promenade est au bout de la rue.", en: "Go straight on, then turn left. The Promenade is at the end of the street.", s: ["C'est loin d'ici ?", "Vous pouvez répéter plus lentement ?"], hint: "Excusez-moi, où est la promenade ?" },
    ],
    fallback: { text: "Vous cherchez la promenade, le consulat ou l'Alliance française ?", en: "Are you looking for the Promenade, the consulate or the Alliance française?", s: ["Excusez-moi, où est la promenade ?", "Je cherche l'Alliance française."] } },

  pdy_fr_college: { category: "college", icon: "🎓", title: "A French class at the Alliance (French)", partner: "Sophie", role: "Classmate", place: "A French class at the Alliance française",
    goal: "Introduce yourself, find out when the class starts and make a friend.",
    opening: { text: "Salut ! C'est ton premier cours ? Moi, c'est Sophie.", en: "Hi! Is this your first class? I'm Sophie." },
    start: ["Oui, c'est mon premier cours aujourd'hui.", "Le cours commence à quelle heure ?", "Où est la bibliothèque ?"],
    rules: [
      { m: ["a plus", "au revoir", "merci", "a demain", "super"], text: "Avec plaisir ! À demain ! 👋", en: "My pleasure! See you tomorrow!", s: ["À demain !"], end: true, hint: "Merci, Sophie !" },
      { m: ["cafe", "apres", "boire"], text: "Oui, bonne idée ! Il y a un café juste en face.", en: "Yes, good idea! There's a café just opposite.", s: ["Super !", "Merci, Sophie !"], hint: "On prend un café après ?" },
      { m: ["aider", "aide", "help"], text: "Bien sûr ! Je te prête mes notes.", en: "Of course! I'll lend you my notes.", s: ["On prend un café après ?", "Merci, Sophie !"], hint: "Tu peux m'aider ?" },
      { m: ["bibliotheque", "livre", "library"], text: "La bibliothèque est au premier étage.", en: "The library is on the first floor.", s: ["Tu peux m'aider ?", "Merci, Sophie !"], hint: "Où est la bibliothèque ?" },
      { m: ["heure", "commence", "quand"], text: "Le cours commence à dix heures, salle B.", en: "The class starts at ten, in room B.", s: ["Où est la bibliothèque ?", "Tu peux m'aider ?"], hint: "Le cours commence à quelle heure ?" },
      { m: ["premier", "premiere", "oui", "nouveau", "nouvelle"], text: "Bienvenue ! Le prof est très sympa, tu vas voir.", en: "Welcome! The teacher is really nice, you'll see.", s: ["Le cours commence à quelle heure ?", "Où est la bibliothèque ?"], hint: "C'est mon premier cours aujourd'hui." },
    ],
    fallback: { text: "Tu cherches la salle, la bibliothèque ou le café ?", en: "Are you looking for the room, the library or the café?", s: ["Le cours commence à quelle heure ?", "Où est la bibliothèque ?"] } },

  pdy_fr_smalltalk: { category: "smalltalk", icon: "☕", title: "On a café terrace (French)", partner: "Marc", role: "Friend", place: "A café terrace on the Promenade",
    goal: "Chat about Pondicherry and plan a Sunday trip to Auroville.",
    opening: { text: "Alors, Pondichéry, ça te plaît ?", en: "So, do you like Pondicherry?" },
    start: ["Il fait beau aujourd'hui !", "Pondichéry est une ville très calme.", "Tu es d'ici ?"],
    rules: [
      { m: ["a dimanche", "au revoir", "super", "genial", "a plus", "salut"], text: "Génial ! À dimanche ! 👋", en: "Great! See you on Sunday!", s: ["Salut Marc !"], end: true, hint: "Super, à dimanche !" },
      { m: ["auroville", "dimanche", "week-end", "on va"], text: "Bonne idée ! On part dimanche matin à vélo, et on visite le Matrimandir.", en: "Good idea! Let's cycle there on Sunday morning and visit the Matrimandir.", s: ["Génial !", "Super, à dimanche !"], hint: "On va à Auroville dimanche ?" },
      { m: ["d'ici", "ne ici"], text: "Oui, je suis né ici ! Ma famille est franco-pondichérienne.", en: "Yes, I was born here! My family is Franco-Pondicherrian.", s: ["On va à Auroville dimanche ?", "Il fait beau aujourd'hui !"] },
      { m: ["beau", "soleil", "chaud", "pluie", "temps"], text: "Oui, mais à midi, il fait très chaud ! Le matin, c'est parfait.", en: "Yes, but at noon it's very hot! The mornings are perfect.", s: ["Tu es d'ici ?", "On va à Auroville dimanche ?"], hint: "Il fait beau aujourd'hui !" },
      { m: ["calme", "tranquille", "ville"], text: "C'est vrai ! Mais le week-end, les touristes de Chennai arrivent.", en: "True! But at weekends the tourists from Chennai arrive.", s: ["On va à Auroville dimanche ?", "Tu es d'ici ?"], hint: "Pondichéry est une ville très calme." },
    ],
    fallback: { text: "Ha ha ! Qu'est-ce que tu aimes le plus ici ?", en: "Ha ha! What do you like most here?", s: ["Il fait beau aujourd'hui !", "Pondichéry est une ville très calme."] } },
});

window.CONTENT_REVIEW.puducherry.fr = { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-18",
  known_limitations: ["The content teaches standard French with Puducherry settings; local Franco-Pondicherrian expressions are not covered yet.", "The pronunciation guides are approximate English-letter spellings, not phonetic transcriptions.", "Masculine forms are taught first; the feminine form is shown where it differs."],
  note: "Puducherry French: AI-assisted editorial review only, not yet checked by a native French speaker." };

// French has no separate script: `roman` is the French itself (accents and all) for the tutor and the reading lines, which are not graded.
const PLACE_PDY_FR = {
  "white town": ["White Town", "White Town"], promenade: ["la promenade", "the Promenade"], auroville: ["Auroville", "Auroville"], "bus stand": ["la gare routière", "the bus stand"],
  "paradise beach": ["Paradise Beach", "Paradise Beach"], "mission street": ["la rue de la Mission", "Mission Street"], "goubert market": ["le marché Goubert", "Goubert Market"],
  "railway station": ["la gare", "the railway station"], "serenity beach": ["Serenity Beach", "Serenity Beach"],
};
const fr = (text, en, extra) => ({ hi: text, roman: text, en, ...(extra || {}) });

window.LOCAL_CONTENT.puducherry.fr = {
  tutor: {
    greet: "Bonjour", places: PUDUCHERRY_PLACES, defaultPlace: "White Town", language: "French",
    starters: ["How do I ask the way to the Promenade in French?", "How do I order breakfast in a café?", "How do I rent a bicycle?", "What does 'bonsoir' mean?", "How do I introduce myself in French?"],
    glossaryOnly: true,
    glossary: {
      bonjour: "“Hello / good day.” Used until early evening.", bonsoir: "“Good evening.” Used from early evening on.", merci: "Thank you. “Merci beaucoup” = thanks a lot.",
      pardon: "“Sorry? / Excuse me.” Also used to squeeze past someone.", vous: "“You”, polite or plural: with people you've just met.", tu: "“You”, familiar: with friends and children.",
      rue: "“Street.” White Town's signs say “Rue …” in French and Tamil.", combien: "“How much.” C'est combien ? = How much is it?", oui: "Yes.", non: "No.",
      super: "“Great!”", voila: "“Here you are / there it is.” (Written voilà.)", enchante: "“Pleased to meet you.” (Written enchanté; a woman writes enchantée.)",
      pondichery: "The French spelling of Pondicherry (Pondichéry).", alliance: "The Alliance française: the French cultural centre in White Town, with classes and events.",
      creole: "Puducherry's Creole cooking mixes Tamil and French: think fish curry with a French touch.", lycee: "The Lycée français: the French state school in White Town.",
    },
    polite: { intro: "French is polite with “vous” and “s'il vous plaît”:", rules: [["\\btu\\b", "vous"], ["\\bpeux\\b", "pouvez"]],
      note: "e.g. “tu peux” → “vous pouvez”. Use “tu” only with friends, classmates and children." },
    intents: [
      { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
        build: (dest) => { const d = PLACE_PDY_FR[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
          fr(`Pour aller à ${r}, s'il vous plaît ?`, `Which way to ${d ? d[1] : dest}, please?`),
          fr(`Vous pouvez m'emmener à ${r} ?`, `A more polite version: Could you take me to ${d ? d[1] : dest}?`, { label: "More polite" }),
          fr("C'est combien ?", "How much is it?"),
        ], note: "Auto and taxi drivers in Puducherry speak Tamil and some English rather than French, and they don't use meters: agree on the fare first. In White Town a bicycle is easiest." }; } },
      { m: ["bike", "bicycle", "cycle", "rent", "scooter", "helmet", "bus", "train"], topic: "transport", intro: "At a rental shop, try:", phrases: [
          fr("Je voudrais louer un vélo.", "I'd like to rent a bike."), fr("C'est combien pour la journée ?", "How much for the day?"), fr("Il y a un casque ?", "Is there a helmet?"),
        ], note: "Most rental shops ask for an ID and a deposit." },
      { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To ask for a better price, politely:", phrases: [
          fr("C'est un peu cher.", "It's a bit expensive."), fr("Vous pouvez faire un prix ?", "Could you give me a better price?"), fr("C'est votre dernier prix ?", "Is that your best price?"),
        ], note: "White Town boutiques have fixed prices; bargaining is for street markets like Goubert Market, in Tamil." },
      { m: ["price", "how much", "cost", "combien", "pay", "upi", "card"], topic: "shopping", intro: "Ask the price like this:", phrases: [
          fr("Combien coûte ce sac ?", "How much is this bag?"), fr("Je peux payer par carte ?", "Can I pay by card?"),
        ] },
      { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "breakfast", "cafe", "bill"], topic: "food", intro: "Ordering food:", phrases: [
          fr("Un café et un croissant, s'il vous plaît.", "A coffee and a croissant, please."), fr("Pas trop épicé, s'il vous plaît.", "Not too spicy, please."),
          fr("L'addition, s'il vous plaît.", "Can I have the bill, please?"),
        ], note: "Say “s'il vous plaît” with every order. Puducherry's Creole dishes mix Tamil and French cooking." },
      { m: ["direction", "where is", "lost", "way", "find", "left", "right", "beach"], topic: "directions", intro: "Asking for directions:", phrases: [
          fr("Excusez-moi, où est la promenade ?", "Excuse me, where's the Promenade?"), fr("Je suis perdu.", "I'm lost. (women say: perdue)"), fr("C'est loin d'ici ?", "Is it far from here?"),
        ], note: "Landmarks everyone knows: the French Consulate, the Lycée français, the Alliance française and the statue of Joan of Arc." },
      { m: ["class", "college", "university", "professor", "teacher", "office", "work", "colleague", "canteen", "library"], topic: "college", intro: "At a class or at work:", phrases: [
          fr("C'est mon premier cours aujourd'hui.", "It's my first class today."), fr("Le cours commence à quelle heure ?", "What time does the class start?"), fr("Vous pouvez m'aider ?", "Could you help me?"),
        ] },
      { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
          fr("Vous êtes d'où ?", "Where are you from?"), fr("Il fait beau aujourd'hui !", "Lovely weather today!"), fr("On prend un café ?", "Shall we get a coffee?"),
        ], note: "Franco-Pondicherrian families mix French, Tamil and English: “Bonjour” and “Vanakkam” in the same conversation." },
      { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
          fr("Je m'appelle Alex.", "My name is Alex."), fr("Comment vous appelez-vous ?", "What's your name?"), fr("Enchanté.", "Nice to meet you. (women write: Enchantée)"),
        ] },
      { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
          fr("Merci beaucoup !", "Thanks a lot!"), fr("Excusez-moi.", "Excuse me / Sorry."), fr("Vous pouvez parler plus lentement ?", "Could you speak more slowly?"),
        ] },
      { m: ["hello", "hi", "greet", "bonjour", "vanakkam", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere:", phrases: [
          fr("Bonjour, comment allez-vous ?", "Hello, how are you?"), fr("Au revoir, à bientôt !", "Goodbye, see you soon!"),
        ], note: "Say “Bonjour” until early evening, then “Bonsoir”." },
      { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
          fr("J'ai besoin d'aide.", "I need help."), fr("Où est l'hôpital le plus proche ?", "Where's the nearest hospital?"),
        ], note: "Emergency number in India: 112. In an emergency, Tamil or English will be understood more widely than French." },
    ],
    generic: { intro: "Here are three French phrases that'll get you through almost anything in your first week:", phrases: [
        fr("Bonjour, comment allez-vous ?", "Hello, how are you?"), fr("C'est combien ?", "How much is it?"), fr("Vous pouvez m'aider ?", "Could you help me?"),
      ], note: "Tell me a situation — like “I want to order breakfast” or “ask the way to the Promenade” — and I'll give you the French words." },
  },
  readings: [
    { title: "Asha à Pondichéry", level: "A1", lines: [
        fr("Asha est nouvelle à Pondichéry.", "Asha is new to Pondicherry."), fr("Elle loue un vélo rue Suffren.", "She rents a bicycle on Rue Suffren."),
        fr("Elle va à l'Alliance française.", "She goes to the Alliance française."), fr("Après le cours, elle prend un café avec Sophie.", "After the class, she has a coffee with Sophie."),
      ],
      questions: [
        { q: "Where is Asha new?", options: ["Chennai", "Pondicherry", "Paris"], a: 1 },
        { q: "What does she rent?", options: ["A bicycle", "A car", "A scooter"], a: 0 },
        { q: "Who does she have a coffee with?", options: ["Marc", "Sophie", "Julien"], a: 1 },
      ] },
    { title: "Un dimanche à Auroville", level: "A1", lines: [
        fr("Marc et Asha partent tôt le matin.", "Marc and Asha leave early in the morning."), fr("Ils vont à Auroville à vélo.", "They cycle to Auroville."),
        fr("Ils déjeunent dans un petit café.", "They have lunch in a small café."), fr("Le déjeuner coûte quatre cents roupies.", "Lunch costs four hundred rupees."),
      ],
      questions: [
        { q: "When do they leave?", options: ["Early in the morning", "At noon", "In the evening"], a: 0 },
        { q: "How do they travel?", options: ["By bus", "By bicycle", "On foot"], a: 1 },
        { q: "How much does lunch cost?", options: ["₹40", "₹400", "₹4000"], a: 1 },
      ] },
  ],
  placement: [
    { q: "What does “Bonjour” mean?", options: ["Goodbye only", "Hello / good day", "Thank you", "How much?"], a: 1 },
    { q: "How would you ask to rent a bicycle?", options: ["Je voudrais louer un vélo.", "L'addition, s'il vous plaît.", "Il fait beau.", "À dimanche !"], a: 0 },
    { q: "What does “C'est combien ?” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
    { q: "“Allez tout droit, puis tournez à gauche” means…", options: ["Stop here", "Go straight on, then turn left", "Turn right twice", "Wait for the bus"], a: 1 },
    { q: "Which “you” do you use with someone you've just met?", options: ["Tu", "Vous", "Toi", "Te"], a: 1 },
  ],
  achievements: {
    "first-words": ["👋", "First words", "Said your first French phrase"], "auto-pro": ["🚲", "Bike rider", "Rented a bicycle"],
    foodie: ["🥐", "Café regular", "Ordered breakfast in French"], bargainer: ["🛍️", "Boutique shopper", "Shopped in French"],
  },
  rightNow: [
    [5, 11, "🥐", "Breakfast time", "White Town's cafés open early. Order in French.", "pdy_fr_food", fr("Un café et un croissant, s'il vous plaît.", "A coffee and a croissant, please.")],
    [11, 15, "🎓", "Class time", "Morning classes are on at the Alliance française.", "pdy_fr_college", fr("Le cours commence à quelle heure ?", "What time does the class start?")],
    [15, 18, "🛍️", "Boutique hours", "Rue Suffren's boutiques are open. Prices are fixed.", "pdy_fr_shopping", fr("Combien coûte ce sac ?", "How much is this bag?")],
    [18, 22, "🌅", "Evening on the Promenade", "The seafront closes to traffic and the café terraces fill up.", "pdy_fr_smalltalk", fr("Il fait beau aujourd'hui !", "Lovely weather today!")],
    [22, 29, "🌙", "Late night walk home", "White Town is quiet at night; keep to the lit streets near the sea.", "pdy_fr_directions", fr("Excusez-moi, où est la promenade ?", "Excuse me, where's the Promenade?")],
  ],
  priceSay: (max, mid) => ({
    ticket: fr("Un ticket, s'il vous plaît.", "One ticket, please."), meter: fr("C'est combien ?", "How much is it?"),
    fair: fr("D'accord, je le prends.", "Okay, I'll take it."), counter: fr(`Vous me le faites à ${max} roupies ?`, `Will you do it for ₹${max}?`),
    high: fr(`C'est trop cher. ${mid} roupies, ça va ?`, `That's too expensive. Is ₹${mid} okay?`),
  }),
};

// Jaipur and Lucknow First Week packs, in Hindi (the English view shows the same packs in English first): Jaipur's Hindi with Rajasthani
// touches ("Khamma ghani", "padharo"), Lucknow's with its Urdu-flavoured courtesy ("Aadaab", "pehle aap"). AI-assisted editorial review only.
window.PACKS.jaipur = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your hosts the Rajasthani way and introduce yourself.",
    situation: "You've just moved into a PG in Malviya Nagar. Kamla ji, the owner, comes to say hello.", scenario: "jpr_greetings",
    tip: "“Khamma ghani” is the warm Rajasthani hello, used with elders and hosts; “Namaste” works everywhere. Add “ji” to names and replies to sound respectful: “haan ji”, “Kamla ji”.",
    phrases: [
      { hi: "खम्मा घणी! आप कैसे हैं?", roman: "Khamma ghani! Aap kaise hain?", en: "Khamma ghani (a Rajasthani greeting)! How are you?", natural: "Hello! How are you?" },
      { hi: "मेरा नाम एलेक्स है।", roman: "Mera naam Alex hai.", en: "My name is Alex.", natural: "I'm Alex." },
      { hi: "मैं यहाँ नया हूँ।", roman: "Main yahan naya hoon.", en: "I am new here.", natural: "I'm new here.", fem: { hi: "मैं यहाँ नई हूँ।", roman: "Main yahan nayi hoon." } },
      { hi: "खाना कितने बजे मिलता है?", roman: "Khaana kitne baje milta hai?", en: "At what time is food served?", natural: "What time are meals served?" },
      { hi: "बहुत-बहुत धन्यवाद, जी!", roman: "Bahut-bahut dhanyavaad, ji!", en: "Very many thanks, ji!", natural: "Thank you so much!" },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Agree auto fares and use the Pink Line metro.",
    situation: "You've arrived at Jaipur Junction and want to see Hawa Mahal.", scenario: "jpr_auto",
    tip: "Jaipur autos rarely use the meter: agree the fare before you get in, or book an app ride. The Pink Line metro runs from Mansarovar to Badi Chaupar in the old city; e-rickshaws and city buses cover the rest.",
    phrases: [
      { hi: "हवा महल चलोगे?", roman: "Hawa Mahal chaloge?", en: "Will you go to Hawa Mahal?", natural: "Will you take me to Hawa Mahal?" },
      { hi: "कितने पैसे लगेंगे?", roman: "Kitne paise lagenge?", en: "How much money will it take?", natural: "How much will it cost?" },
      { hi: "सौ रुपये में चलो।", roman: "Sau rupaye mein chalo.", en: "Go for a hundred rupees.", natural: "Let's go for a hundred." },
      { hi: "मेट्रो स्टेशन कहाँ है?", roman: "Metro station kahan hai?", en: "Where is the metro station?", natural: "Where's the metro station?" },
      { hi: "यहीं रोक दीजिए।", roman: "Yahin rok dijiye.", en: "Stop right here.", natural: "Stop here, please." },
    ] },
  { day: 3, key: "food", icon: "🍽️", title: "Food", desc: "Eat like a Jaipurite: kachori, lassi and dal baati.",
    situation: "Breakfast at a sweet shop in Johari Bazaar.", scenario: "jpr_food",
    tip: "Try pyaaz kachori for breakfast and dal baati churma for lunch; Jaipur's famous lassi comes thick, in a clay cup (kulhad). “Mirch kam” (less chilli) helps: Rajasthani food can be fiery.",
    phrases: [
      { hi: "एक प्याज़ कचौरी देना।", roman: "Ek pyaaz kachori dena.", en: "Give one onion kachori.", natural: "One pyaaz kachori, please." },
      { hi: "एक लस्सी, कम मीठी।", roman: "Ek lassi, kam meethi.", en: "One lassi, less sweet.", natural: "A lassi, not too sweet." },
      { hi: "ये दाल बाटी चूरमा है?", roman: "Ye daal baati choorma hai?", en: "Is this dal baati churma?", natural: "Is this dal baati churma?" },
      { hi: "मिर्च कम डालना।", roman: "Mirch kam daalna.", en: "Put less chilli.", natural: "Not too spicy, please." },
      { hi: "कितना हुआ?", roman: "Kitna hua?", en: "How much did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain for mojaris and block prints in the old bazaars.",
    situation: "You're in Bapu Bazaar, looking for a pair of mojaris.", scenario: "jpr_shopping",
    tip: "Bapu Bazaar and Johari Bazaar are famous for mojaris (embroidered shoes), block-print cloth and bangles. Start at about half the first price and settle in between; shops with price tags don't bargain.",
    phrases: [
      { hi: "ये मोजड़ी कितने की है?", roman: "Ye mojdi kitne ki hai?", en: "These mojaris are of how much?", natural: "How much are these mojaris?" },
      { hi: "बहुत महँगा है, भैया।", roman: "Bahut mehenga hai, bhaiya.", en: "It's very expensive, brother.", natural: "That's too expensive." },
      { hi: "थोड़ा कम कर दो।", roman: "Thoda kam kar do.", en: "Make it a little less.", natural: "Can you lower it a bit?" },
      { hi: "इसमें दूसरा रंग है?", roman: "Ismein doosra rang hai?", en: "In this is there another colour?", natural: "Do you have this in another colour?" },
      { hi: "ठीक है, पैक कर दो।", roman: "Theek hai, pack kar do.", en: "Okay, pack it.", natural: "Okay, pack it up." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way round the walled Pink City.",
    situation: "You're at Badi Chaupar in the old city and want Hawa Mahal.", scenario: "jpr_directions",
    tip: "The walled old city is a grid of bazaars. Its gates and chaupars (big crossroads) are the best landmarks: Badi Chaupar, Choti Chaupar, Sanganeri Gate.",
    phrases: [
      { hi: "हवा महल किधर है?", roman: "Hawa Mahal kidhar hai?", en: "Hawa Mahal is which way?", natural: "Which way is Hawa Mahal?" },
      { hi: "सीधे जाइए, फिर दाएँ मुड़िए।", roman: "Seedhe jaiye, phir daayen mudiye.", en: "Go straight, then turn right.", natural: "Go straight, then turn right." },
      { hi: "पैदल कितनी देर लगेगी?", roman: "Paidal kitni der lagegi?", en: "On foot how much time will it take?", natural: "How long is it on foot?" },
      { hi: "पास में कोई केमिस्ट है?", roman: "Paas mein koi chemist hai?", en: "Nearby is there any chemist?", natural: "Is there a pharmacy nearby?" },
      { hi: "ज़रा धीरे बोलिए।", roman: "Zara dheere boliye.", en: "Speak a little slowly.", natural: "Could you speak a bit more slowly?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in with classmates and colleagues.",
    situation: "Your first day at a college in Malviya Nagar.", scenario: "jpr_college",
    tip: "Jaipur has many colleges and coaching centres; students mix Hindi, English and a little Rajasthani. “Kya haal hai?” is a friendly “how's it going?”.",
    phrases: [
      { hi: "आज मेरा पहला दिन है।", roman: "Aaj mera pehla din hai.", en: "Today is my first day.", natural: "It's my first day today." },
      { hi: "क्लास कहाँ है?", roman: "Class kahan hai?", en: "Where is the class?", natural: "Where's the class?" },
      { hi: "क्या आप मेरी थोड़ी मदद कर सकते हैं?", roman: "Kya aap meri thodi madad kar sakte hain?", en: "Can you help me a little?", natural: "Could you help me a bit?" },
      { hi: "कैंटीन में चाय पिएँ?", roman: "Canteen mein chai piyen?", en: "Shall we drink tea in the canteen?", natural: "Shall we get chai at the canteen?" },
      { hi: "फिर मिलते हैं!", roman: "Phir milte hain!", en: "We meet again!", natural: "See you later!" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "Sunset at Nahargarh Fort with Rohit, your flatmate.", scenario: "jpr_smalltalk",
    tip: "Rajasthani touches you'll hear: “padharo” (welcome), “ghani” (very, a lot) and “kai haal hai?” (how are you?).",
    phrases: [
      { hi: "यहाँ से पूरा शहर दिखता है!", roman: "Yahan se poora shehar dikhta hai!", en: "From here the whole city is seen!", natural: "You can see the whole city from here!" },
      { hi: "जयपुर में गर्मी बहुत है, ना?", roman: "Jaipur mein garmi bahut hai, na?", en: "In Jaipur the heat is a lot, no?", natural: "It's really hot in Jaipur, isn't it?" },
      { hi: "आप जयपुर के ही हो?", roman: "Aap Jaipur ke hi ho?", en: "Are you from Jaipur itself?", natural: "Are you from Jaipur?" },
      { hi: "संडे आमेर क़िला चलें?", roman: "Sunday Amer qila chalein?", en: "Shall we go to Amer Fort on Sunday?", natural: "Fancy Amer Fort on Sunday?" },
      { hi: "बढ़िया, पक्का!", roman: "Badhiya, pakka!", en: "Great, sure!", natural: "Great, it's a plan!" },
    ] },
];

window.PACKS.lucknow = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet people the Lucknowi way and introduce yourself.",
    situation: "You've just rented a flat in Gomti Nagar. Mirza sahab, your landlord, welcomes you.", scenario: "lko_greetings",
    tip: "Lucknow is famous for its tehzeeb (courtesy): “Aadaab” with a small raised hand, “aap” for everyone, and the legendary “pehle aap” (after you). Urdu words like “shukriya” and “meherbaan” are everyday Hindi here.",
    phrases: [
      { hi: "आदाब! आप कैसे हैं?", roman: "Aadaab! Aap kaise hain?", en: "Respects! How are you?", natural: "Hello! How are you?" },
      { hi: "मेरा नाम एलेक्स है।", roman: "Mera naam Alex hai.", en: "My name is Alex.", natural: "I'm Alex." },
      { hi: "मैं लखनऊ में नया हूँ।", roman: "Main Lucknow mein naya hoon.", en: "I am new in Lucknow.", natural: "I'm new to Lucknow.", fem: { hi: "मैं लखनऊ में नई हूँ।", roman: "Main Lucknow mein nayi hoon." } },
      { hi: "आपसे मिलकर बहुत ख़ुशी हुई।", roman: "Aapse milkar bahut khushi hui.", en: "Having met you, much happiness happened.", natural: "It's lovely to meet you." },
      { hi: "शुक्रिया, आप बहुत मेहरबान हैं।", roman: "Shukriya, aap bahut meherbaan hain.", en: "Thanks, you are very kind.", natural: "Thank you, that's very kind of you." },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Take shared autos, private autos and the metro.",
    situation: "You've arrived at Charbagh station and need to get to Hazratganj.", scenario: "lko_auto",
    tip: "Shared autos and tempos run fixed routes for a few rupees a seat; a private auto costs more and doesn't use a meter, so agree first. The metro's Red Line runs from the airport through Charbagh and Hazratganj to Munshi Pulia.",
    phrases: [
      { hi: "हज़रतगंज चलेंगे?", roman: "Hazratganj chalenge?", en: "Will you go to Hazratganj?", natural: "Will you go to Hazratganj?" },
      { hi: "कितना किराया होगा?", roman: "Kitna kiraaya hoga?", en: "How much will the fare be?", natural: "What's the fare?" },
      { hi: "मेट्रो से कितनी देर लगेगी?", roman: "Metro se kitni der lagegi?", en: "By metro how long will it take?", natural: "How long by metro?" },
      { hi: "शेयरिंग वाला ऑटो कहाँ मिलेगा?", roman: "Sharing waala auto kahan milega?", en: "Where will a sharing auto be found?", natural: "Where can I get a shared auto?" },
      { hi: "बस, यहीं उतार दीजिए।", roman: "Bas, yahin utaar dijiye.", en: "Enough, drop me right here.", natural: "Just drop me here, please." },
    ] },
  { day: 3, key: "food", icon: "🍢", title: "Food", desc: "Order Awadhi kebabs and biryani, or the vegetarian dishes.",
    situation: "Dinner at a kebab shop in Aminabad.", scenario: "lko_food",
    tip: "Lucknow is the home of Awadhi cooking: galouti kebabs, biryani and nihari, and for vegetarians basket chaat and, in winter, malai makhan. Old Lucknow's kebab shops are in Aminabad and Chowk.",
    phrases: [
      { hi: "दो प्लेट गलौटी कबाब दीजिए।", roman: "Do plate galouti kebab dijiye.", en: "Give two plates of galouti kebab.", natural: "Two plates of galouti kebabs, please." },
      { hi: "एक प्लेट बिरयानी भी।", roman: "Ek plate biryani bhi.", en: "One plate of biryani too.", natural: "And a plate of biryani." },
      { hi: "मिर्च ज़रा कम रखिए।", roman: "Mirch zara kam rakhiye.", en: "Keep the chilli a little less.", natural: "Not too spicy, please." },
      { hi: "मैं शाकाहारी हूँ, वेज क्या है?", roman: "Main shaakaahaari hoon, veg kya hai?", en: "I am vegetarian, what is veg?", natural: "I'm vegetarian; what's vegetarian here?" },
      { hi: "बिल ले आइए।", roman: "Bill le aaiye.", en: "Bring the bill.", natural: "Could I have the bill, please?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Buy chikankari, Lucknow's famous embroidery, at a fair price.",
    situation: "You're in a chikankari shop in Chowk.", scenario: "lko_shopping",
    tip: "Chikankari, Lucknow's white-on-white hand embroidery, is sold all over Chowk and Aminabad; Hazratganj's showrooms have fixed prices. Ask “haath ka kaam hai?” (is it handwork?): machine embroidery is cheaper.",
    phrases: [
      { hi: "ये चिकनकारी कुर्ता कितने का है?", roman: "Ye chikankari kurta kitne ka hai?", en: "This chikankari kurta is of how much?", natural: "How much is this chikankari kurta?" },
      { hi: "ये हाथ की कढ़ाई है?", roman: "Ye haath ki kadhaai hai?", en: "Is this embroidery of the hand?", natural: "Is this hand-embroidered?" },
      { hi: "कुछ कम हो जाएगा?", roman: "Kuch kam ho jaayega?", en: "Will it become somewhat less?", natural: "Could you do it for a bit less?" },
      { hi: "बड़ा साइज़ दिखाइए।", roman: "Bada size dikhaaiye.", en: "Show the big size.", natural: "Could you show me a bigger size?" },
      { hi: "ठीक है, ले लेता हूँ।", roman: "Theek hai, le leta hoon.", en: "Okay, I take it.", natural: "Okay, I'll take it.", fem: { hi: "ठीक है, ले लेती हूँ।", roman: "Theek hai, le leti hoon." } },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way round old Lucknow's monuments.",
    situation: "You're near the Bara Imambara and want the Rumi Darwaza.", scenario: "lko_directions",
    tip: "Old Lucknow's landmarks are close together: the Bara Imambara, the Rumi Darwaza and the clock tower. People give directions by landmark: “Ghanta Ghar ke paas” (near the clock tower).",
    phrases: [
      { hi: "रूमी दरवाज़ा किस तरफ़ है?", roman: "Rumi Darwaza kis taraf hai?", en: "Rumi Darwaza is on which side?", natural: "Which way is the Rumi Darwaza?" },
      { hi: "सीधे जाकर बाएँ मुड़ जाइए।", roman: "Seedhe jaakar baayen mud jaaiye.", en: "Going straight, turn left.", natural: "Go straight and turn left." },
      { hi: "क्या ये पैदल दूर है?", roman: "Kya ye paidal door hai?", en: "Is this far on foot?", natural: "Is it far to walk?" },
      { hi: "यहाँ पास में कोई दवाख़ाना है?", roman: "Yahan paas mein koi davaakhaana hai?", en: "Near here is there any pharmacy?", natural: "Is there a pharmacy nearby?" },
      { hi: "माफ़ कीजिए, एक बार फिर बताइए।", roman: "Maaf kijiye, ek baar phir bataaiye.", en: "Forgive me, tell once again.", natural: "Sorry, could you say that again?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in at university and make friends.",
    situation: "Your first day at Lucknow University.", scenario: "lko_college",
    tip: "Lucknow University's campus is by the Gomti. Students mix Hindi, Urdu and English; “Kya scene hai?” is a casual “what's up?”.",
    phrases: [
      { hi: "आज मेरी पहली क्लास है।", roman: "Aaj meri pehli class hai.", en: "Today is my first class.", natural: "It's my first class today." },
      { hi: "लाइब्रेरी किधर है?", roman: "Library kidhar hai?", en: "Which way is the library?", natural: "Where's the library?" },
      { hi: "ये डिपार्टमेंट किस बिल्डिंग में है?", roman: "Ye department kis building mein hai?", en: "This department is in which building?", natural: "Which building is this department in?" },
      { hi: "नोट्स शेयर कर सकते हो?", roman: "Notes share kar sakte ho?", en: "Can you share notes?", natural: "Could you share your notes?" },
      { hi: "कैंटीन में चाय हो जाए?", roman: "Canteen mein chai ho jaaye?", en: "Shall chai happen in the canteen?", natural: "Chai at the canteen?" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "An evening by the Gomti with Faraz, a friend from college.", scenario: "lko_smalltalk",
    tip: "“Pehle aap” (after you) is Lucknow's famous courtesy; friends also say “aur sunaao?” (so, what's new?). Sunday mornings are for kachori-jalebi in Aminabad or Chowk.",
    phrases: [
      { hi: "लखनऊ की शाम बहुत ख़ूबसूरत है।", roman: "Lucknow ki shaam bahut khoobsoorat hai.", en: "Lucknow's evening is very beautiful.", natural: "Evenings in Lucknow are beautiful." },
      { hi: "यहाँ के लोग बहुत तहज़ीब वाले हैं।", roman: "Yahan ke log bahut tehzeeb waale hain.", en: "The people here are very courteous.", natural: "People here are so polite." },
      { hi: "आप पुराने लखनऊ से हो?", roman: "Aap puraane Lucknow se ho?", en: "Are you from old Lucknow?", natural: "Are you from old Lucknow?" },
      { hi: "संडे चौक में खाने चलें?", roman: "Sunday Chowk mein khaane chalein?", en: "Shall we go to eat in Chowk on Sunday?", natural: "Fancy a food walk in Chowk on Sunday?" },
      { hi: "बिलकुल, पक्का!", roman: "Bilkul, pakka!", en: "Absolutely, sure!", natural: "Absolutely, it's a plan!" },
    ] },
];

Object.assign(window.SCENARIOS, {
  // ---------- Jaipur ----------
  jpr_greetings: { category: "greetings", icon: "🏠", title: "Meet your PG owner", partner: "Kamla ji", role: "PG owner", place: "Your PG in Malviya Nagar",
    goal: "Greet politely, introduce yourself and ask about the meal times.",
    opening: { text: "Padharo! Aap hi Alex hain? Main Kamla, is PG ki maalkin.", en: "Welcome! Are you Alex? I'm Kamla, the owner of this PG." },
    start: ["Khamma ghani! Aap kaise hain?", "Ji, mera naam Alex hai.", "Khaana kitne baje milta hai?"],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "milte hain", "bye"], text: "Koi baat nahi! Kuch chahiye toh bataana. 🙏", en: "No problem! Let me know if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Bahut-bahut dhanyavaad, ji!" },
      { m: ["khaana", "khana", "baje", "nashta", "dinner", "lunch"], text: "Nashta aath baje, raat ka khaana nau baje. Daal baati Sunday ko banti hai!", en: "Breakfast at eight, dinner at nine. Dal baati is made on Sundays!", s: ["Wah, badhiya!", "Bahut-bahut dhanyavaad, ji!"], hint: "Khaana kitne baje milta hai?" },
      { m: ["pehla hafta", "pehli baar", "naya", "nayi", "new"], text: "Koi baat nahi, Jaipur sabko apna bana leta hai. Khaane ka time pata hai?", en: "Don't worry, Jaipur makes everyone its own. Do you know the meal times?", s: ["Khaana kitne baje milta hai?"], hint: "Jaipur mein mera pehla hafta hai." },
      { m: ["naam", "alex", "name"], text: "Achha naam hai! Jaipur kaisa lag raha hai?", en: "Nice name! How are you finding Jaipur?", s: ["Bahut sundar hai!", "Jaipur mein mera pehla hafta hai."], hint: "Mera naam Alex hai." },
      { m: ["sundar", "badhiya", "wah", "nice", "good"], text: "Gulabi shehar hai, sabko pasand aata hai. Khaane ka time pata hai?", en: "It's the Pink City; everyone loves it. Do you know the meal times?", s: ["Khaana kitne baje milta hai?"], hint: "Bahut sundar hai!" },
      { m: ["khamma", "ghani", "namaste", "kaise", "hello", " hi "], text: "Main badhiya hoon! Aapka naam kya hai?", en: "I'm very well! What's your name?", s: ["Mera naam Alex hai.", "Jaipur mein mera pehla hafta hai."], hint: "Khamma ghani! Aap kaise hain?" },
    ],
    fallback: { text: "Haan ji, boliye. Khaana, paani, Wi-Fi, kya chahiye?", en: "Yes, tell me. Meals, water, the Wi-Fi: what do you need?", s: ["Khaana kitne baje milta hai?", "Bahut-bahut dhanyavaad, ji!"] } },

  jpr_auto: { category: "transport", icon: "🛺", title: "Auto to Hawa Mahal", partner: "Ramesh", role: "Auto driver", place: "Outside Jaipur Junction railway station",
    goal: "Get to Hawa Mahal for a fair fare.", places: ["Hawa Mahal", "Amer", "Johari Bazaar", "Bapu Bazaar", "MI Road", "Airport", "Jal Mahal", "Malviya Nagar"],
    opening: { text: "Kahan jaana hai?", en: "Where do you need to go?" },
    start: ["Hawa Mahal chaloge?", "Kitne paise lagenge?", "Sau rupaye mein chalo."],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "upi", "paytm", "milte hain"], text: "Shukriya! Jaipur aaraam se ghoomiye. 🙏", en: "Thank you! Enjoy exploring Jaipur.", s: ["Phir milte hain!"], end: true, hint: "Dhanyavaad, bhaiya!" },
      { m: ["sau rupaye", "hundred", "100"], text: "Theek hai, sau mein chalo. Baithiye!", en: "Okay, a hundred it is. Get in!", s: ["Kitni der lagegi?", "Yahin rok dijiye."], hint: "Sau rupaye mein chalo." },
      { m: ["rok", "yahin", "utaar", "stop"], text: "Lo, aa gaye Hawa Mahal! Sau rupaye.", en: "Here we are, Hawa Mahal! A hundred rupees.", s: ["UPI chalega?", "Dhanyavaad, bhaiya!"], hint: "Yahin rok dijiye." },
      { m: ["der", "minute", "kitni der"], text: "Traffic hai, bees minute lagenge.", en: "There's traffic; it'll take twenty minutes.", s: ["Theek hai, chalo.", "Yahin rok dijiye."] },
      { m: ["metro"], text: "Metro station Sindhi Camp pe hai, wahan se Badi Chaupar tak jaati hai.", en: "The metro station is at Sindhi Camp; it goes to Badi Chaupar.", s: ["Nahi, auto se chalo.", "Kitne paise lagenge?"], hint: "Metro station kahan hai?" },
      { m: ["zyaada", "mehenga", "jyada"], text: "Achha, ek sau bees de dena.", en: "All right, give a hundred and twenty.", s: ["Sau rupaye mein chalo.", "Theek hai, chalo."], hint: "Bahut zyaada hai, bhaiya." },
      { m: ["kitne", "paise", "kiraaya", "rate", "price"], text: "Hawa Mahal? Dedh sau lagenge.", en: "Hawa Mahal? A hundred and fifty.", s: ["Sau rupaye mein chalo.", "Bahut zyaada hai, bhaiya."], hint: "Kitne paise lagenge?" },
      { m: ["hawa mahal", "amer", "johari", "bapu", "mi road", "airport", "jal mahal", "malviya", "chaloge", "jaana"], text: "{place}? Haan, chalo. Baithiye.", en: "{place}? Yes, let's go. Get in.", s: ["Kitne paise lagenge?", "Sau rupaye mein chalo."], hint: "{place} chaloge?" },
      { m: ["pehla hafta", "pehli baar", "new"], text: "Swagat hai! Amer qila zaroor dekhna.", en: "Welcome! Don't miss Amer Fort.", s: ["Kitni der lagegi?", "Yahin rok dijiye."] },
      { m: ["theek", "chalo", "ok", "haan", "auto se"], text: "Baithiye! Jaipur pehli baar?", en: "Get in! First time in Jaipur?", s: ["Haan, pehla hafta hai.", "Kitni der lagegi?"] },
    ],
    fallback: { text: "Samjha nahi. Kahan jaana hai?", en: "I didn't get that. Where do you need to go?", s: ["Hawa Mahal chaloge?", "Kitne paise lagenge?"] } },

  jpr_food: { category: "food", icon: "🍽️", title: "Breakfast in Johari Bazaar", partner: "Gopal ji", role: "Shopkeeper", place: "A sweet shop in Johari Bazaar",
    goal: "Order a pyaaz kachori and a lassi, and pay.",
    opening: { text: "Aaiye, kya loge?", en: "Come in, what will you have?" },
    start: ["Ek pyaaz kachori dena.", "Ek lassi, kam meethi.", "Kitna hua?"],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "upi", "paytm", "milte hain", "lijiye"], text: "Shukriya! Phir aana. 🙏", en: "Thank you! Come again.", s: ["Phir milte hain!"], end: true, hint: "Dhanyavaad!" },
      { m: ["kitna", "bill", "paise"], text: "Kachori aur lassi, assi rupaye.", en: "Kachori and lassi, eighty rupees.", s: ["UPI chalega?", "Ye lijiye."], hint: "Kitna hua?" },
      { m: ["mirch", "teekha", "spicy"], text: "Theek hai, mirch kam.", en: "Okay, less chilli.", s: ["Ek lassi, kam meethi.", "Kitna hua?"], hint: "Mirch kam daalna." },
      { m: ["daal", "baati", "choorma", "thali"], text: "Haan ji, daal baati choorma, dopahar mein milega.", en: "Yes, dal baati churma, served at lunchtime.", s: ["Ek pyaaz kachori dena.", "Kitna hua?"], hint: "Ye daal baati choorma hai?" },
      { m: ["lassi", "chai", "meethi"], text: "Ek lassi, kulhad mein! Aur kuch?", en: "One lassi, in a clay cup! Anything else?", s: ["Ek pyaaz kachori dena.", "Kitna hua?"], hint: "Ek lassi, kam meethi." },
      { m: ["kachori", "pyaaz", "samosa"], text: "Garam-garam pyaaz kachori! Chutney ke saath?", en: "Piping hot pyaaz kachori! With chutney?", s: ["Haan, chutney ke saath.", "Mirch kam daalna."], hint: "Ek pyaaz kachori dena." },
      { m: ["chutney", "haan"], text: "Ye lo, garam-garam.", en: "Here you are, piping hot.", s: ["Ek lassi, kam meethi.", "Kitna hua?"] },
    ],
    fallback: { text: "Kachori, samosa, lassi, ghewar... kya loge?", en: "Kachori, samosa, lassi, ghewar... what will you have?", s: ["Ek pyaaz kachori dena.", "Ek lassi, kam meethi."] } },

  jpr_shopping: { category: "shopping", icon: "🛍️", title: "Bargain in Bapu Bazaar", partner: "Vikram", role: "Shopkeeper", place: "Bapu Bazaar",
    goal: "Buy a pair of mojaris at a fair price.",
    opening: { text: "Aaiye, dekhiye! Mojdi, chunri, bedsheet, sab hai.", en: "Come in, take a look! Mojaris, scarves, bedsheets: we have it all." },
    start: ["Ye mojdi kitne ki hai?", "Ismein doosra rang hai?", "Bahut mehenga hai, bhaiya."],
    rules: [
      { m: ["pack", "dhanyavaad", "shukriya", "upi", "milte hain"], text: "Pack kar diya! Phir aaiye. 🙏", en: "Packed! Come again.", s: ["Phir milte hain!"], end: true, hint: "Theek hai, pack kar do." },
      { m: ["teen sau", "chaar sau", "300", "400"], text: "Chaliye, aapke liye chaar sau. Last price!", en: "All right, four hundred for you. Last price!", s: ["Theek hai, pack kar do.", "UPI chalega?"] },
      { m: ["mehenga", "kam", "zyaada", "last"], text: "Asli kaam hai, haath ka! Chaliye, chhah sau.", en: "It's real handwork! All right, six hundred.", s: ["Chaar sau theek rahega.", "Thoda kam kar do."], hint: "Thoda kam kar do." },
      { m: ["rang", "colour", "color", "size", "laal", "neela"], text: "Haan, laal aur neela bhi hai.", en: "Yes, there's red and blue too.", s: ["Ye mojdi kitne ki hai?", "Neela dikhaao."], hint: "Ismein doosra rang hai?" },
      { m: ["kitne", "price", "daam"], text: "Ye mojdi? Nau sau rupaye.", en: "These mojaris? Nine hundred rupees.", s: ["Bahut mehenga hai, bhaiya.", "Thoda kam kar do."], hint: "Ye mojdi kitne ki hai?" },
    ],
    fallback: { text: "Aaraam se dekhiye. Mojdi, chunri, sab hai!", en: "Take your time. Mojaris, scarves, we have it all!", s: ["Ye mojdi kitne ki hai?", "Ismein doosra rang hai?"] } },

  jpr_directions: { category: "directions", icon: "🏰", title: "Find Hawa Mahal", partner: "Mohan ji", role: "Passerby", place: "Badi Chaupar, in the old city",
    goal: "Find the way to Hawa Mahal, and a pharmacy.",
    opening: { text: "Kuch dhoondhna hai?", en: "Looking for something?" },
    start: ["Hawa Mahal kidhar hai?", "Paas mein koi chemist hai?", "Paidal kitni der lagegi?"],
    rules: [
      { m: ["dhanyavaad", "shukriya", "thank", "samajh", "milte hain"], text: "Koi baat nahi! Ghoomte rahiye. 🙏", en: "Not at all! Enjoy your walk.", s: ["Phir milte hain!"], end: true, hint: "Bahut dhanyavaad!" },
      { m: ["dheere", "phir se", "dobara", "slow"], text: "Seedhe jaiye, phir daayen. Bas!", en: "Straight on, then right. That's it!", s: ["Theek hai, samajh aa gaya.", "Paidal kitni der lagegi?"], hint: "Zara dheere boliye." },
      { m: ["chemist", "dawai", "medical", "hospital"], text: "Haan, chaupar ke kone pe ek chemist hai.", en: "Yes, there's a chemist at the corner of the crossroads.", s: ["Hawa Mahal kidhar hai?", "Zara dheere boliye."], hint: "Paas mein koi chemist hai?" },
      { m: ["paidal", "der", "door", "walk"], text: "Paidal paanch minute bas.", en: "Just five minutes on foot.", s: ["Theek hai, samajh aa gaya.", "Bahut dhanyavaad!"], hint: "Paidal kitni der lagegi?" },
      { m: ["hawa mahal", "kidhar", "kahan", "metro"], text: "Seedhe jaiye, phir daayen mudiye. Saamne Hawa Mahal dikhega.", en: "Go straight, then turn right. You'll see Hawa Mahal ahead.", s: ["Paidal kitni der lagegi?", "Zara dheere boliye."], hint: "Hawa Mahal kidhar hai?" },
    ],
    fallback: { text: "Kahan jaana hai, bataiye.", en: "Tell me where you need to go.", s: ["Hawa Mahal kidhar hai?", "Paas mein koi chemist hai?"] } },

  jpr_college: { category: "college", icon: "🎓", title: "First day at college", partner: "Pooja", role: "Classmate", place: "A college campus in Malviya Nagar",
    goal: "Find your class and the canteen, and make a friend.",
    opening: { text: "Hi! Aaj pehla din hai kya? Main Pooja.", en: "Hi! Is it your first day? I'm Pooja." },
    start: ["Haan, aaj mera pehla din hai.", "Class kahan hai?", "Canteen mein chai piyen?"],
    rules: [
      { m: ["milte hain", "bye", "thank", "dhanyavaad", "shukriya", "badhiya"], text: "Welcome! Kuch chahiye toh batana. 👋", en: "Welcome! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Thank you, Pooja!" },
      { m: ["chai", "canteen", "piyen"], text: "Haan, break mein chalte hain!", en: "Yes, let's go at the break!", s: ["Badhiya!", "Thank you, Pooja!"], hint: "Canteen mein chai piyen?" },
      { m: ["madad", "help"], text: "Haan, bilkul! Timetable WhatsApp kar deti hoon.", en: "Of course! I'll WhatsApp you the timetable.", s: ["Canteen mein chai piyen?", "Thank you, Pooja!"], hint: "Kya aap meri thodi madad kar sakte hain?" },
      { m: ["class", "room", "kahan"], text: "Class doosri manzil pe hai, room 204.", en: "The class is on the second floor, room 204.", s: ["Kya aap meri thodi madad kar sakte hain?", "Canteen mein chai piyen?"], hint: "Class kahan hai?" },
      { m: ["pehla", "haan", "first"], text: "Welcome! Pehle din sab thoda confusing hota hai.", en: "Welcome! Everything's a bit confusing on the first day.", s: ["Class kahan hai?", "Kya aap meri thodi madad kar sakte hain?"], hint: "Aaj mera pehla din hai." },
    ],
    fallback: { text: "Bolo, kya chahiye? Class, library, ya canteen?", en: "Tell me, what do you need? The class, the library or the canteen?", s: ["Class kahan hai?", "Canteen mein chai piyen?"] } },

  jpr_smalltalk: { category: "smalltalk", icon: "🌇", title: "Sunset at Nahargarh", partner: "Rohit", role: "Flatmate", place: "Nahargarh Fort at sunset",
    goal: "Chat about Jaipur and plan a weekend trip.",
    opening: { text: "Kya view hai na? Jaipur kaisa lag raha hai?", en: "What a view, right? How are you liking Jaipur?" },
    start: ["Yahan se poora shehar dikhta hai!", "Jaipur mein garmi bahut hai, na?", "Aap Jaipur ke hi ho?"],
    rules: [
      { m: ["pakka", "bye", "badhiya", "milte hain"], text: "Pakka! Sunday subah nikalte hain. 👋", en: "Deal! We'll head out on Sunday morning.", s: ["Bye Rohit!"], end: true, hint: "Badhiya, pakka!" },
      { m: ["baje", "subah"], text: "Subah saat baje, garmi se pehle.", en: "Seven in the morning, before the heat.", s: ["Badhiya, pakka!"] },
      { m: ["amer", "sunday", "weekend", "qila", "plan"], text: "Haan! Sunday subah Amer qila chalte hain, phir Jal Mahal.", en: "Yes! Amer Fort on Sunday morning, then Jal Mahal.", s: ["Badhiya, pakka!", "Kitne baje niklein?"], hint: "Sunday Amer qila chalein?" },
      { m: ["jaipur ke", "yahin", "born"], text: "Haan, main yahin paida hua, purane shehar mein!", en: "Yes, I was born right here, in the old city!", s: ["Sunday Amer qila chalein?", "Jaipur mein garmi bahut hai, na?"] },
      { m: ["garmi", "dhoop", "hot", "mausam"], text: "Haan, par shaam ko thandi hawa chalti hai, jaise abhi.", en: "Yes, but in the evening a cool breeze blows, like now.", s: ["Aap Jaipur ke hi ho?", "Sunday Amer qila chalein?"], hint: "Jaipur mein garmi bahut hai, na?" },
      { m: ["shehar", "view", "dikhta", "sundar"], text: "Haan, isliye Pink City kehte hain. Shaam ko sab gulabi lagta hai!", en: "Yes, that's why it's the Pink City. Everything looks pink in the evening!", s: ["Jaipur mein garmi bahut hai, na?", "Sunday Amer qila chalein?"], hint: "Yahan se poora shehar dikhta hai!" },
    ],
    fallback: { text: "Haha, sahi hai! Jaipur mein sabse achha kya laga?", en: "Haha, true! What do you like most about Jaipur?", s: ["Yahan se poora shehar dikhta hai!", "Jaipur mein garmi bahut hai, na?"] } },

  // ---------- Lucknow ----------
  lko_greetings: { category: "greetings", icon: "🏠", title: "Meet your landlord", partner: "Mirza sahab", role: "Landlord", place: "Your rented flat in Gomti Nagar",
    goal: "Greet your landlord the Lucknowi way, introduce yourself and ask about the water.",
    opening: { text: "Aadaab! Tashreef laaiye. Aap hi Alex hain?", en: "Greetings! Do come in. Are you Alex?" },
    start: ["Aadaab! Aap kaise hain?", "Ji, mera naam Alex hai.", "Aapse milkar bahut khushi hui."],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "khuda hafiz", "bye", "milte hain", "samajh"], text: "Arey, shukriya kis baat ka! Kuch zaroorat ho toh bataiyega. 🙏", en: "Oh, no need to thank me! Let me know if you need anything.", s: ["Khuda hafiz!"], end: true, hint: "Shukriya, aap bahut meherbaan hain." },
      { m: ["paani", "bijli", "light", "timing"], text: "Paani subah-shaam aata hai. Bijli jaaye toh inverter hai.", en: "Water comes morning and evening. If the power goes, there's an inverter.", s: ["Ji, samajh aa gaya.", "Shukriya, aap bahut meherbaan hain."], hint: "Paani kab aata hai?" },
      { m: ["khushi", "milkar", "pleasure"], text: "Humein bhi bahut khushi hui. Lucknow pehli baar?", en: "The pleasure is mine. First time in Lucknow?", s: ["Ji, pehli baar.", "Paani kab aata hai?"], hint: "Aapse milkar bahut khushi hui." },
      { m: ["pehli baar", "naya", "nayi", "new"], text: "Phir toh Lucknow ki tehzeeb aur kebab, dono ka mazaa lijiye!", en: "Then enjoy both Lucknow's courtesy and its kebabs!", s: ["Paani kab aata hai?", "Shukriya, aap bahut meherbaan hain."], hint: "Ji, pehli baar." },
      { m: ["naam", "alex", "name"], text: "Bahut khoob! Lucknow pehli baar?", en: "Lovely! First time in Lucknow?", s: ["Ji, pehli baar.", "Aapse milkar bahut khushi hui."], hint: "Mera naam Alex hai." },
      { m: ["aadaab", "adaab", "namaste", "kaise", "hello", " hi "], text: "Main bilkul theek hoon, shukriya! Aapka naam?", en: "I'm very well, thank you! Your name?", s: ["Ji, mera naam Alex hai.", "Aapse milkar bahut khushi hui."], hint: "Aadaab! Aap kaise hain?" },
    ],
    fallback: { text: "Ji, farmaaiye. Paani, bijli, parking, kya jaanna hai?", en: "Yes, please tell me. Water, power, parking: what would you like to know?", s: ["Paani kab aata hai?", "Shukriya, aap bahut meherbaan hain."] } },

  lko_auto: { category: "transport", icon: "🛺", title: "Auto to Hazratganj", partner: "Rafiq", role: "Auto driver", place: "Outside Charbagh railway station",
    goal: "Get to Hazratganj for a fair fare.", places: ["Hazratganj", "Aminabad", "Chowk", "Gomti Nagar", "Airport", "Imambara", "Kapoorthala", "Alambagh"],
    opening: { text: "Kahan chalna hai?", en: "Where to?" },
    start: ["Hazratganj chalenge?", "Kitna kiraaya hoga?", "Sharing waala auto kahan milega?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "upi", "khuda hafiz"], text: "Shukriya! Lucknow mein aapka swagat hai. 🙏", en: "Thank you! Welcome to Lucknow.", s: ["Khuda hafiz!"], end: true, hint: "Shukriya, bhai!" },
      { m: ["utaar", "rok", "yahin", " bas,"], text: "Lijiye, aa gaya Hazratganj. Sau rupaye.", en: "Here's Hazratganj. A hundred rupees.", s: ["UPI chalega?", "Shukriya, bhai!"], hint: "Bas, yahin utaar dijiye." },
      { m: ["sharing", "share", "tempo"], text: "Sharing auto bahar stand se milega, bees rupaye sawaari.", en: "Shared autos leave from the stand outside, twenty rupees a person.", s: ["Nahi, aap hi chaliye.", "Metro se kitni der lagegi?"], hint: "Sharing waala auto kahan milega?" },
      { m: ["metro", "der", "time"], text: "Metro se Hazratganj das minute. Station saamne hai.", en: "Hazratganj is ten minutes by metro. The station's right there.", s: ["Nahi, aap hi chaliye.", "Kitna kiraaya hoga?"], hint: "Metro se kitni der lagegi?" },
      { m: ["zyaada", "mehenga", "kam"], text: "Achha, assi de dijiye.", en: "All right, give eighty.", s: ["Theek hai, chaliye.", "Bas, yahin utaar dijiye."], hint: "Thoda kam kijiye." },
      { m: ["kiraaya", "kitna", "paise"], text: "Hazratganj? Sau rupaye lagenge.", en: "Hazratganj? A hundred rupees.", s: ["Thoda kam kijiye.", "Theek hai, chaliye."], hint: "Kitna kiraaya hoga?" },
      { m: ["hazratganj", "aminabad", "chowk", "gomti", "airport", "imambara", "kapoorthala", "alambagh", "chalenge"], text: "{place}? Ji, baithiye.", en: "{place}? Sure, get in.", s: ["Kitna kiraaya hoga?", "Bas, yahin utaar dijiye."], hint: "{place} chalenge?" },
      { m: ["pehli baar", "new"], text: "Toh Tunday ke kebab zaroor khaaiyega!", en: "Then you must try Tunday's kebabs!", s: ["Bas, yahin utaar dijiye.", "Shukriya, bhai!"] },
      { m: ["theek", "chaliye", "haan", "ok"], text: "Baithiye! Lucknow pehli baar?", en: "Get in! First time in Lucknow?", s: ["Ji, pehli baar.", "Metro se kitni der lagegi?"] },
    ],
    fallback: { text: "Samjha nahi. Kahan chalna hai?", en: "I didn't get that. Where to?", s: ["Hazratganj chalenge?", "Kitna kiraaya hoga?"] } },

  lko_food: { category: "food", icon: "🍢", title: "Kebabs in Aminabad", partner: "Haji sahab", role: "Kebab shop owner", place: "A kebab shop in Aminabad",
    goal: "Order kebabs and biryani, or a vegetarian dish, and pay.",
    opening: { text: "Aaiye, aaiye! Kya pesh karein?", en: "Come in, come in! What may we serve you?" },
    start: ["Do plate galouti kebab dijiye.", "Ek plate biryani bhi.", "Main shaakaahaari hoon, veg kya hai?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "upi", "khuda hafiz", "rakh lijiye"], text: "Shukriya! Phir tashreef laaiyega. 🙏", en: "Thank you! Do come again.", s: ["Khuda hafiz!"], end: true, hint: "Shukriya!" },
      { m: ["bill", "kitna", "paise"], text: "Kebab aur biryani, teen sau bees rupaye.", en: "Kebabs and biryani, three hundred and twenty rupees.", s: ["UPI chalega?", "Ye rakh lijiye."], hint: "Bill le aaiye." },
      { m: ["mirch", "teekha", "spicy"], text: "Ji, mirch kam rakhenge.", en: "Sure, we'll keep it mild.", s: ["Bill le aaiye.", "Ek plate biryani bhi."], hint: "Mirch zara kam rakhiye." },
      { m: ["shaakaahaari", "shakahari", "veg", "sabzi"], text: "Veg mein dum aloo, paneer aur kulche hain.", en: "For vegetarians there's dum aloo, paneer and kulchas.", s: ["Ek plate dum aloo, kulche ke saath.", "Mirch zara kam rakhiye."], hint: "Main shaakaahaari hoon, veg kya hai?" },
      { m: ["kebab", "galouti", "biryani", "aloo", "kulche", "nihari", "plate"], text: "Bahut khoob! Garma-garam aa raha hai. Aur kuch?", en: "Excellent! It's coming piping hot. Anything else?", s: ["Bas, itna hi.", "Mirch zara kam rakhiye."], hint: "Do plate galouti kebab dijiye." },
      { m: ["itna hi", "bas"], text: "Ji, abhi laate hain.", en: "Right away.", s: ["Bill le aaiye.", "Shukriya!"] },
    ],
    fallback: { text: "Kebab, biryani, nihari, kulche... kya pesh karein?", en: "Kebabs, biryani, nihari, kulchas... what may we serve you?", s: ["Do plate galouti kebab dijiye.", "Main shaakaahaari hoon, veg kya hai?"] } },

  lko_shopping: { category: "shopping", icon: "🧵", title: "Chikankari in Chowk", partner: "Naseem", role: "Shopkeeper", place: "A chikankari shop in Chowk",
    goal: "Buy a chikankari kurta at a fair price.",
    opening: { text: "Aaiye! Asli Lucknowi chikankari, haath ka kaam.", en: "Come in! Real Lucknow chikankari, all handwork." },
    start: ["Ye chikankari kurta kitne ka hai?", "Ye haath ki kadhaai hai?", "Bada size dikhaaiye."],
    rules: [
      { m: ["le leta", "le leti", "pack", "shukriya", "dhanyavaad", "upi", "khuda hafiz"], text: "Mubarak ho! Pack kar diya. 🙏", en: "Congratulations! It's packed.", s: ["Khuda hafiz!"], end: true, hint: "Theek hai, pack kar dijiye." },
      { m: ["paanch sau", "chhah sau", "500", "600"], text: "Chaliye, aapke liye chhah sau. Isse kam nahi.", en: "All right, six hundred for you. No lower than that.", s: ["Theek hai, pack kar dijiye.", "UPI chalega?"] },
      { m: ["kam", "mehenga", "zyaada"], text: "Haath ka kaam hai! Chaliye, aath sau.", en: "It's handwork! All right, eight hundred.", s: ["Paanch sau theek rahega.", "Kuch kam ho jaayega?"], hint: "Kuch kam ho jaayega?" },
      { m: ["haath", "kadhaai", "machine", "asli"], text: "Ji, poora haath ka kaam hai. Machine waala sasta milta hai.", en: "Yes, it's all handwork. Machine-made is cheaper.", s: ["Ye chikankari kurta kitne ka hai?", "Bada size dikhaaiye."], hint: "Ye haath ki kadhaai hai?" },
      { m: ["size", "bada", "chhota", "rang", "colour", "aasmaani"], text: "Ji, bada bhi hai, aur aasmaani rang mein bhi.", en: "Yes, there's a bigger one, and a sky-blue one too.", s: ["Ye chikankari kurta kitne ka hai?", "Aasmaani waala dikhaaiye."], hint: "Bada size dikhaaiye." },
      { m: ["kitne", "daam", "price"], text: "Ye kurta? Bas baarah sau.", en: "This kurta? Just twelve hundred.", s: ["Kuch kam ho jaayega?", "Bahut mehenga hai."], hint: "Ye chikankari kurta kitne ka hai?" },
    ],
    fallback: { text: "Aaraam se dekhiye. Kurte, dupatte, sab hai.", en: "Take your time. Kurtas, dupattas, we have it all.", s: ["Ye chikankari kurta kitne ka hai?", "Ye haath ki kadhaai hai?"] } },

  lko_directions: { category: "directions", icon: "🕌", title: "Find the Rumi Darwaza", partner: "Verma ji", role: "Passerby", place: "Near the Bara Imambara",
    goal: "Find the way to the Rumi Darwaza, and a pharmacy.",
    opening: { text: "Kuch dhoondhna hai?", en: "Looking for something?" },
    start: ["Rumi Darwaza kis taraf hai?", "Yahan paas mein koi davaakhaana hai?", "Kya ye paidal door hai?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "samajh", "khuda hafiz"], text: "Koi baat nahi! Lucknow ka lutf uthaaiye. 🙏", en: "Not at all! Enjoy Lucknow.", s: ["Khuda hafiz!"], end: true, hint: "Shukriya!" },
      { m: ["phir se", "ek baar phir", "dobara", "dheere", "maaf"], text: "Ji: seedhe, phir baayen. Saamne Rumi Darwaza.", en: "Sure: straight on, then left. The Rumi Darwaza is ahead.", s: ["Ji, samajh aa gaya.", "Kya ye paidal door hai?"], hint: "Maaf kijiye, ek baar phir bataaiye." },
      { m: ["davaakhaana", "dawakhana", "chemist", "medical", "dawai"], text: "Haan, Ghanta Ghar ke paas ek medical store hai.", en: "Yes, there's a pharmacy near the clock tower.", s: ["Rumi Darwaza kis taraf hai?", "Maaf kijiye, ek baar phir bataaiye."], hint: "Yahan paas mein koi davaakhaana hai?" },
      { m: ["paidal", "door", "der", "walk"], text: "Bilkul nahi, paidal paanch minute.", en: "Not at all, five minutes' walk.", s: ["Ji, samajh aa gaya.", "Shukriya!"], hint: "Kya ye paidal door hai?" },
      { m: ["rumi", "darwaza", "imambara", "kis taraf", "kidhar"], text: "Seedhe jaakar baayen mud jaaiye. Rumi Darwaza saamne hi hai.", en: "Go straight and turn left. The Rumi Darwaza is right ahead.", s: ["Kya ye paidal door hai?", "Maaf kijiye, ek baar phir bataaiye."], hint: "Rumi Darwaza kis taraf hai?" },
    ],
    fallback: { text: "Bataaiye, kahan jaana hai?", en: "Tell me, where do you need to go?", s: ["Rumi Darwaza kis taraf hai?", "Yahan paas mein koi davaakhaana hai?"] } },

  lko_college: { category: "college", icon: "🎓", title: "First day at Lucknow University", partner: "Ayesha", role: "Classmate", place: "Lucknow University campus",
    goal: "Find your department and the library, and make a friend.",
    opening: { text: "Hi! Pehli class hai kya? Main Ayesha.", en: "Hi! Is it your first class? I'm Ayesha." },
    start: ["Haan, aaj meri pehli class hai.", "Library kidhar hai?", "Ye department kis building mein hai?"],
    rules: [
      { m: ["milte hain", "bye", "thank", "shukriya", "badhiya"], text: "Welcome! Kuch chahiye ho toh batana. 👋", en: "Welcome! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Thank you, Ayesha!" },
      { m: ["chai", "canteen"], text: "Haan, class ke baad chalte hain!", en: "Yes, let's go after class!", s: ["Badhiya!", "Thank you, Ayesha!"], hint: "Canteen mein chai ho jaaye?" },
      { m: ["notes", "share"], text: "Haan, main WhatsApp pe bhej deti hoon.", en: "Yes, I'll send them on WhatsApp.", s: ["Canteen mein chai ho jaaye?", "Thank you, Ayesha!"], hint: "Notes share kar sakte ho?" },
      { m: ["library", "kitaab"], text: "Tagore Library main gate ke paas hai.", en: "The Tagore Library is near the main gate.", s: ["Notes share kar sakte ho?", "Thank you, Ayesha!"], hint: "Library kidhar hai?" },
      { m: ["department", "building"], text: "Wo nayi building mein hai, doosri manzil pe.", en: "It's in the new building, on the second floor.", s: ["Library kidhar hai?", "Notes share kar sakte ho?"], hint: "Ye department kis building mein hai?" },
      { m: ["pehli", "pehla", "haan", "first"], text: "Welcome! Pehle din thoda confusing hota hai, koi baat nahi.", en: "Welcome! The first day is a bit confusing, but that's fine.", s: ["Library kidhar hai?", "Ye department kis building mein hai?"], hint: "Aaj meri pehli class hai." },
    ],
    fallback: { text: "Bolo, kya chahiye? Library, canteen, ya department?", en: "Tell me, what do you need? The library, the canteen or the department?", s: ["Library kidhar hai?", "Canteen mein chai ho jaaye?"] } },

  lko_smalltalk: { category: "smalltalk", icon: "🌆", title: "An evening by the Gomti", partner: "Faraz", role: "Friend", place: "The Gomti riverfront at sunset",
    goal: "Chat about Lucknow and plan a Sunday food walk.",
    opening: { text: "Kya baat hai, Lucknow pasand aaya?", en: "So, how do you like Lucknow?" },
    start: ["Lucknow ki shaam bahut khoobsoorat hai.", "Yahan ke log bahut tehzeeb waale hain.", "Aap puraane Lucknow se ho?"],
    rules: [
      { m: ["pakka", "bye", "bilkul", "khuda hafiz", "milte hain"], text: "Pakka! Sunday subah Chowk mein milte hain. 👋", en: "Deal! See you in Chowk on Sunday morning.", s: ["Khuda hafiz!"], end: true, hint: "Bilkul, pakka!" },
      { m: ["baje", "subah"], text: "Subah aath baje, bheed se pehle.", en: "Eight in the morning, before the crowds.", s: ["Bilkul, pakka!"] },
      { m: ["chowk", "khaane", "sunday", "plan", "kebab", "walk"], text: "Haan! Sunday ko Chowk mein kachori-jalebi, phir Tunday ke kebab.", en: "Yes! Kachori-jalebi in Chowk on Sunday, then Tunday's kebabs.", s: ["Bilkul, pakka!", "Kitne baje?"], hint: "Sunday Chowk mein khaane chalein?" },
      { m: ["puraane", "yahin", "born", "se ho"], text: "Haan, Chowk ki galiyon mein bada hua hoon!", en: "Yes, I grew up in the lanes of Chowk!", s: ["Sunday Chowk mein khaane chalein?", "Lucknow ki shaam bahut khoobsoorat hai."] },
      { m: ["tehzeeb", " log ", "pehle aap", "polite"], text: "Haha, “pehle aap” toh yahan ki pehchaan hai!", en: "Haha, “after you” is what Lucknow is known for!", s: ["Aap puraane Lucknow se ho?", "Sunday Chowk mein khaane chalein?"], hint: "Yahan ke log bahut tehzeeb waale hain." },
      { m: ["shaam", "khoobsoorat", "gomti", "sunset"], text: "Haan, Gomti ke kinaare shaam ka alag hi mazaa hai.", en: "Yes, evenings by the Gomti are something else.", s: ["Yahan ke log bahut tehzeeb waale hain.", "Sunday Chowk mein khaane chalein?"], hint: "Lucknow ki shaam bahut khoobsoorat hai." },
    ],
    fallback: { text: "Haha, waah! Lucknow mein sabse achha kya laga?", en: "Haha, wonderful! What do you like most about Lucknow?", s: ["Lucknow ki shaam bahut khoobsoorat hai.", "Yahan ke log bahut tehzeeb waale hain."] } },
});

Object.assign(window.CONTENT_REVIEW, {
  jaipur: { hi: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
    known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Rajasthani words are touches in Hindi, not a course in Rajasthani.", "Fares and practical tips change over time."],
    note: "Jaipur Hindi (with Rajasthani touches): AI-assisted editorial review only, not yet checked by a native speaker from Jaipur." } },
  lucknow: { hi: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
    known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Lucknow's Urdu-flavoured words are taught as everyday Hindi; Urdu script is not covered.", "Fares and practical tips change over time."],
    note: "Lucknow Hindi (with its Urdu-flavoured courtesy): AI-assisted editorial review only, not yet checked by a native speaker from Lucknow." } },
});

// ---------- local content: the tutor, readings, level check, achievements, "Right now" and price phrases ----------
const PLACE_JPR = {
  "hawa mahal": ["Hawa Mahal", "हवा महल", "Hawa Mahal"], amer: ["Amer", "आमेर", "Amer Fort"], "johari bazaar": ["Johari Bazaar", "जौहरी बाज़ार", "Johari Bazaar"],
  "bapu bazaar": ["Bapu Bazaar", "बापू बाज़ार", "Bapu Bazaar"], "mi road": ["MI Road", "एमआई रोड", "MI Road"], airport: ["airport", "एयरपोर्ट", "the airport"],
  "jal mahal": ["Jal Mahal", "जल महल", "Jal Mahal"], "sindhi camp": ["Sindhi Camp", "सिंधी कैंप", "Sindhi Camp bus stand"], station: ["station", "स्टेशन", "the railway station"],
  "malviya nagar": ["Malviya Nagar", "मालवीय नगर", "Malviya Nagar"],
};
const JAIPUR_PLACES = ["Hawa Mahal", "Amer", "Johari Bazaar", "Bapu Bazaar", "MI Road", "Airport", "Jal Mahal", "Sindhi Camp", "Station", "Malviya Nagar"];
const PLACE_LKO = {
  hazratganj: ["Hazratganj", "हज़रतगंज", "Hazratganj"], aminabad: ["Aminabad", "अमीनाबाद", "Aminabad"], chowk: ["Chowk", "चौक", "Chowk"],
  "gomti nagar": ["Gomti Nagar", "गोमती नगर", "Gomti Nagar"], charbagh: ["Charbagh", "चारबाग", "Charbagh station"], airport: ["airport", "एयरपोर्ट", "the airport"],
  imambara: ["Bara Imambara", "बड़ा इमामबाड़ा", "the Bara Imambara"], kapoorthala: ["Kapoorthala", "कपूरथला", "Kapoorthala"], alambagh: ["Alambagh", "आलमबाग", "Alambagh"],
};
const LUCKNOW_PLACES = ["Hazratganj", "Aminabad", "Chowk", "Gomti Nagar", "Charbagh", "Airport", "Imambara", "Kapoorthala", "Alambagh"];
const hiP = (hi, roman, en, extra) => ({ hi, roman, en, ...(extra || {}) });

window.LOCAL_CONTENT.jaipur = { hi: {
  tutor: {
    greet: "Khamma ghani", places: JAIPUR_PLACES, defaultPlace: "Hawa Mahal",
    starters: ["I need a ride to Hawa Mahal.", "How do I order pyaaz kachori?", "How do I bargain in Bapu Bazaar?", "What does 'padharo' mean?", "Which metro goes to the old city?"],
    glossary: {
      "khamma ghani": "The warm Rajasthani hello, for elders and hosts.", padharo: "“Welcome!” As in “padharo mhare des” (welcome to my land).", ghani: "Rajasthani for “very / a lot”.",
      mojdi: "Mojaris: Jaipur's embroidered leather shoes.", kachori: "A fried pastry; Jaipur's pyaaz (onion) kachori is the breakfast classic.", kulhad: "A small clay cup for lassi or chai.",
      chaupar: "A big crossroads in the walled city: Badi Chaupar, Choti Chaupar.", ghewar: "A honeycomb-like Rajasthani sweet, especially around Teej.",
    },
    intents: [
      { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
        build: (dest) => { const d = PLACE_JPR[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
          hiP(d ? `${d[1]} चलोगे? कितने पैसे?` : "", `${r} chaloge? Kitne paise?`, `Will you go to ${d ? d[2] : dest}? How much?`),
          hiP(d ? `भैया, ${d[1]} चलेंगे?` : "", `Bhaiya, ${r} chalenge?`, `A more polite version: Would you take me to ${d ? d[2] : dest}?`, { label: "More polite" }),
          hiP("पहले रेट बता दीजिए।", "Pehle rate bata dijiye.", "Please tell me the fare first."),
        ], note: "Jaipur's autos rarely use the meter: agree the fare before you get in, or book an app ride." }; } },
      { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
          hiP("मेट्रो बड़ी चौपड़ जाती है?", "Metro Badi Chaupar jaati hai?", "Does the metro go to Badi Chaupar?"), hiP("टोकन कहाँ मिलेगा?", "Token kahan milega?", "Where do I get a token?"),
          hiP("अगला स्टेशन कौन सा है?", "Agla station kaun sa hai?", "Which is the next station?"),
        ], note: "Jaipur Metro's Pink Line runs from Mansarovar to Badi Chaupar in the old city, via Sindhi Camp and Chandpole. Fares are ₹10–30." },
      { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
          hiP("थोड़ा कम कर दो।", "Thoda kam kar do.", "Please lower it a little."), hiP("बहुत महँगा है, भैया।", "Bahut mehenga hai, bhaiya.", "That's too expensive."),
          hiP("आख़िरी दाम बोलो।", "Aakhri daam bolo.", "What's your best price?"),
        ], note: "In Bapu Bazaar and Johari Bazaar start at about half the first price and settle in between." },
      { m: ["price", "how much", "cost", "kitna", "kitne", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
          hiP("ये कितने का है?", "Ye kitne ka hai?", "How much is this?"), hiP("यूपीआई चलेगा?", "UPI chalega?", "Can I pay by UPI?"),
        ] },
      { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "kachori", "lassi", "bill"], topic: "food", intro: "Ordering food:", phrases: [
          hiP("एक प्याज़ कचौरी देना।", "Ek pyaaz kachori dena.", "One pyaaz kachori, please."), hiP("मिर्च कम डालना।", "Mirch kam daalna.", "Not too spicy, please."),
          hiP("एक लस्सी, कम मीठी।", "Ek lassi, kam meethi.", "A lassi, not too sweet."),
        ], note: "“Dena” is casual (stalls); “dijiye” is polite (restaurants). Rajasthani food can be fiery: ask for “kam mirch”." },
      { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
          hiP("हवा महल किधर है?", "Hawa Mahal kidhar hai?", "Which way is Hawa Mahal?"), hiP("मैं रास्ता भूल गया हूँ।", "Main raasta bhool gaya hoon.", "I'm lost. (women say: bhool gayi hoon)"),
          hiP("सबसे पास का गेट कौन सा है?", "Sabse paas ka gate kaun sa hai?", "Which is the nearest gate?"),
        ], note: "In the old city, give and ask directions by the gates and chaupars: Sanganeri Gate, Badi Chaupar, Choti Chaupar." },
      { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At college or work:", phrases: [
          hiP("आज मेरा पहला दिन है।", "Aaj mera pehla din hai.", "It's my first day today."), hiP("क्लास कहाँ है?", "Class kahan hai?", "Where's the class?"),
          hiP("क्या आप मेरी थोड़ी मदद कर सकते हैं?", "Kya aap meri thodi madad kar sakte hain?", "Could you help me a bit?"),
        ] },
      { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
          hiP("आप कहाँ से हो?", "Aap kahan se ho?", "Where are you from?"), hiP("जयपुर में गर्मी बहुत है, ना?", "Jaipur mein garmi bahut hai, na?", "It's really hot in Jaipur, isn't it?"),
          hiP("चाय पिएँगे?", "Chai piyenge?", "Fancy a chai?"),
        ], note: "Jaipur small talk: the heat, the forts, the food and the festivals. “Kai haal hai?” is a Rajasthani “how are you?”." },
      { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
          hiP("मेरा नाम एलेक्स है।", "Mera naam Alex hai.", "My name is Alex."), hiP("आपका नाम क्या है?", "Aapka naam kya hai?", "What's your name?"),
          hiP("आपसे मिलकर अच्छा लगा।", "Aapse milkar accha laga.", "Nice to meet you."),
        ] },
      { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
          hiP("बहुत-बहुत धन्यवाद!", "Bahut-bahut dhanyavaad!", "Thanks a lot!"), hiP("माफ़ कीजिए।", "Maaf kijiye.", "Sorry / Excuse me."), hiP("सुनिए…", "Suniye…", "Excuse me… (to get attention)"),
        ] },
      { m: ["hello", "hi", "greet", "namaste", "khamma", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Jaipur:", phrases: [
          hiP("खम्मा घणी!", "Khamma ghani!", "Hello! (the Rajasthani greeting)"), hiP("फिर मिलते हैं!", "Phir milte hain!", "See you later!"),
        ], note: "“Khamma ghani” is warm and respectful; “Namaste” works with everyone." },
      { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
          hiP("मुझे मदद चाहिए।", "Mujhe madad chahiye.", "I need help."), hiP("पास में हॉस्पिटल कहाँ है?", "Paas mein hospital kahan hai?", "Where's the nearest hospital?"),
        ], note: "Emergency number in India: 112." },
    ],
    generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
        hiP("खम्मा घणी! आप कैसे हैं?", "Khamma ghani! Aap kaise hain?", "Hello! How are you?"), hiP("कितना हुआ?", "Kitna hua?", "How much is it?"),
        hiP("क्या आप मेरी थोड़ी मदद कर सकते हैं?", "Kya aap meri thodi madad kar sakte hain?", "Could you help me a bit?"),
      ], note: "Tell me a situation — like “I want to order a kachori” or “ask the way to Hawa Mahal” — and I'll give you the exact words." },
  },
  readings: [
    { title: "Asha in Jaipur", level: "A1", lines: [
        hiP("आशा जयपुर में नई है।", "Asha Jaipur mein nayi hai.", "Asha is new in Jaipur."), hiP("वह मेट्रो से बड़ी चौपड़ जाती है।", "Vah metro se Badi Chaupar jaati hai.", "She takes the metro to Badi Chaupar."),
        hiP("वहाँ से वह हवा महल देखने जाती है।", "Vahan se vah Hawa Mahal dekhne jaati hai.", "From there she goes to see Hawa Mahal."), hiP("फिर वह एक कुल्हड़ लस्सी पीती है।", "Phir vah ek kulhad lassi peeti hai.", "Then she has a lassi in a clay cup."),
      ],
      questions: [
        { q: "Where is Asha new?", options: ["Delhi", "Jaipur", "Lucknow"], a: 1 }, { q: "How does she travel?", options: ["By metro", "By bus", "By auto"], a: 0 },
        { q: "What does she drink?", options: ["Chai", "Lassi", "Coffee"], a: 1 },
      ] },
    { title: "Shopping in Bapu Bazaar", level: "A1", lines: [
        hiP("रवि बापू बाज़ार जाता है।", "Ravi Bapu Bazaar jaata hai.", "Ravi goes to Bapu Bazaar."), hiP("उसे एक जोड़ी मोजड़ी पसंद आती है।", "Use ek jodi mojdi pasand aati hai.", "He likes a pair of mojaris."),
        hiP("दुकानदार नौ सौ रुपये माँगता है।", "Dukaandaar nau sau rupaye maangta hai.", "The shopkeeper asks for nine hundred rupees."), hiP("रवि छह सौ में ले लेता है।", "Ravi chhah sau mein le leta hai.", "Ravi buys them for six hundred."),
      ],
      questions: [
        { q: "Where does Ravi go?", options: ["Bapu Bazaar", "Johari Bazaar", "MI Road"], a: 0 }, { q: "What does he like?", options: ["Mojaris", "A kurta", "Bangles"], a: 0 },
        { q: "How much does he pay?", options: ["₹600", "₹900", "₹60"], a: 0 },
      ] },
  ],
  placement: [
    { q: "What does “Khamma ghani” mean?", options: ["Goodbye only", "A warm Rajasthani hello", "Thank you", "How much?"], a: 1 },
    { q: "How would you ask an auto driver to go to Hawa Mahal?", options: ["Hawa Mahal chaloge?", "Kitna hua?", "Ek lassi, kam meethi.", "Phir milte hain!"], a: 0 },
    { q: "What does “kitne paise lagenge” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
    { q: "“Seedhe jaiye, phir daayen mudiye” means…", options: ["Stop here", "Go straight, then turn right", "Turn left twice", "Wait for the bus"], a: 1 },
    { q: "Which is the most polite way to ask someone to stop?", options: ["Rok", "Yahin rok dijiye", "Roko!", "Bas"], a: 1 },
  ],
  achievements: {
    "auto-pro": ["🛺", "Fair-fare pro", "Agreed a fair auto fare"], foodie: ["🥟", "Kachori lover", "Ordered a Jaipur breakfast"], bargainer: ["🛍️", "Bapu Bazaar bargainer", "Won a bargain"],
  },
  rightNow: [
    [5, 11, "🥟", "Breakfast time", "Kachori shops are busiest in the morning. Order like a local.", "jpr_food", hiP("एक प्याज़ कचौरी देना।", "Ek pyaaz kachori dena.", "One pyaaz kachori, please.")],
    [11, 15, "🏰", "Fort hours", "Amer and Nahargarh are open. Get there before the midday heat.", "jpr_auto", hiP("आमेर चलोगे?", "Amer chaloge?", "Will you go to Amer?")],
    [15, 18, "🛍️", "Market hours", "Bapu Bazaar and Johari Bazaar are buzzing. Time to bargain.", "jpr_shopping", hiP("थोड़ा कम कर दो।", "Thoda kam kar do.", "Can you lower it a bit?")],
    [18, 22, "🌇", "Sunset at Nahargarh", "The whole city turns pink in the evening light.", "jpr_smalltalk", hiP("यहाँ से पूरा शहर दिखता है!", "Yahan se poora shehar dikhta hai!", "You can see the whole city from here!")],
    [22, 29, "🌙", "Late night ride home", "Autos charge more at night. Agree on the fare first.", "jpr_auto", hiP("पहले रेट बता दीजिए।", "Pehle rate bata dijiye.", "Please tell me the fare first.")],
  ],
  priceSay: (max, mid) => ({
    ticket: hiP("बड़ी चौपड़ का एक टोकन।", "Badi Chaupar ka ek token.", "One token to Badi Chaupar."), meter: hiP("पहले रेट बता दीजिए।", "Pehle rate bata dijiye.", "Please tell me the fare first."),
    fair: hiP("ठीक है, चलिए।", "Theek hai, chaliye.", "Okay, deal."), counter: hiP(`भैया, ${max} में दोगे?`, `Bhaiya, ${max} mein doge?`, `Will you do it for ₹${max}?`),
    high: hiP(`बहुत महँगा है, भैया। ${mid} में दोगे?`, `Bahut mehenga hai, bhaiya. ${mid} mein doge?`, `That's too expensive. Will you do ₹${mid}?`),
  }),
} };

window.LOCAL_CONTENT.lucknow = { hi: {
  tutor: {
    greet: "Aadaab", places: LUCKNOW_PLACES, defaultPlace: "Hazratganj",
    starters: ["I need a ride to Hazratganj.", "How do I order galouti kebabs?", "How do I bargain for chikankari in Chowk?", "What does 'tehzeeb' mean?", "Which metro station is near Hazratganj?"],
    glossary: {
      aadaab: "A respectful hello, said with a small raised hand.", tehzeeb: "“Courtesy, refinement”: what Lucknow is famous for.", "pehle aap": "“After you”: Lucknow's legendary politeness.",
      chikankari: "Lucknow's white-on-white hand embroidery.", galouti: "Galouti kebabs: melt-in-the-mouth minced-meat kebabs, an Awadhi classic.", "khuda hafiz": "“Goodbye” (literally, may God protect you).",
      meherbaan: "“Kind.” Aap bahut meherbaan hain = you're very kind.", tashreef: "As in “tashreef laaiye”: please come in / do come.", janaab: "A respectful “sir”.",
    },
    intents: [
      { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
        build: (dest) => { const d = PLACE_LKO[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
          hiP(d ? `भाई, ${d[1]} चलेंगे?` : "", `Bhai, ${r} chalenge?`, `Will you go to ${d ? d[2] : dest}?`),
          hiP(d ? `${d[1]} तक चलिए, प्लीज़।` : "", `${r} tak chaliye, please.`, `A more polite version: Please take me to ${d ? d[2] : dest}.`, { label: "More polite" }),
          hiP("किराया पहले बता दीजिए।", "Kiraaya pehle bata dijiye.", "Please tell me the fare first."),
        ], note: "Private autos don't use meters in Lucknow: agree the fare first. Shared autos and tempos run fixed routes for a few rupees a seat." }; } },
      { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
          hiP("हज़रतगंज के लिए कौन सा स्टेशन?", "Hazratganj ke liye kaun sa station?", "Which station for Hazratganj?"), hiP("एयरपोर्ट तक मेट्रो जाती है?", "Airport tak metro jaati hai?", "Does the metro go to the airport?"),
          hiP("टोकन कहाँ मिलेगा?", "Token kahan milega?", "Where do I get a token?"),
        ], note: "Lucknow Metro's Red Line runs from CCS Airport through Charbagh and Hazratganj to Munshi Pulia. Fares are ₹10–60." },
      { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely, the Lucknowi way:", phrases: [
          hiP("कुछ कम हो जाएगा?", "Kuch kam ho jaayega?", "Could you do it for a bit less?"), hiP("ये ज़्यादा है।", "Ye zyaada hai.", "That's a lot."),
          hiP("आख़िरी दाम बता दीजिए।", "Aakhri daam bata dijiye.", "Please tell me your best price."),
        ], note: "In Chowk and Aminabad, bargain gently and politely; Hazratganj's showrooms have fixed prices." },
      { m: ["price", "how much", "cost", "kitna", "kitne", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
          hiP("ये कितने का है?", "Ye kitne ka hai?", "How much is this?"), hiP("यूपीआई चलेगा?", "UPI chalega?", "Can I pay by UPI?"),
        ] },
      { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "kebab", "biryani", "bill"], topic: "food", intro: "Ordering food:", phrases: [
          hiP("दो प्लेट गलौटी कबाब दीजिए।", "Do plate galouti kebab dijiye.", "Two plates of galouti kebabs, please."), hiP("मिर्च ज़रा कम रखिए।", "Mirch zara kam rakhiye.", "Not too spicy, please."),
          hiP("बिल ले आइए।", "Bill le aaiye.", "Could I have the bill, please?"),
        ], note: "Awadhi classics: galouti kebabs, biryani, nihari; vegetarians try basket chaat, kulchas and, in winter, malai makhan." },
      { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
          hiP("रूमी दरवाज़ा किस तरफ़ है?", "Rumi Darwaza kis taraf hai?", "Which way is the Rumi Darwaza?"), hiP("मैं रास्ता भूल गया हूँ।", "Main raasta bhool gaya hoon.", "I'm lost. (women say: bhool gayi hoon)"),
          hiP("घंटा घर के पास कैसे जाऊँ?", "Ghanta Ghar ke paas kaise jaaun?", "How do I get near the clock tower?"),
        ], note: "Old Lucknow's landmarks are close together: the Bara Imambara, the Rumi Darwaza and the clock tower (Ghanta Ghar)." },
      { m: ["class", "college", "university", "professor", "teacher", "office", "work", "colleague", "canteen", "library"], topic: "college", intro: "At college or work:", phrases: [
          hiP("आज मेरी पहली क्लास है।", "Aaj meri pehli class hai.", "It's my first class today."), hiP("लाइब्रेरी किधर है?", "Library kidhar hai?", "Where's the library?"),
          hiP("क्या आप मेरी मदद कर सकते हैं?", "Kya aap meri madad kar sakte hain?", "Could you help me?"),
        ] },
      { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
          hiP("आप कहाँ से हैं?", "Aap kahan se hain?", "Where are you from?"), hiP("लखनऊ की शाम बहुत ख़ूबसूरत है।", "Lucknow ki shaam bahut khoobsoorat hai.", "Evenings in Lucknow are beautiful."),
          hiP("चाय हो जाए?", "Chai ho jaaye?", "How about some chai?"),
        ], note: "Lucknow small talk: the food, the monuments and the famous “pehle aap”. Friends say “aur sunaao?” (so, what's new?)." },
      { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
          hiP("मेरा नाम एलेक्स है।", "Mera naam Alex hai.", "My name is Alex."), hiP("आपका नाम क्या है?", "Aapka naam kya hai?", "What's your name?"),
          hiP("आपसे मिलकर बहुत ख़ुशी हुई।", "Aapse milkar bahut khushi hui.", "It's lovely to meet you."),
        ] },
      { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials, the Lucknowi way:", phrases: [
          hiP("शुक्रिया!", "Shukriya!", "Thank you!"), hiP("माफ़ कीजिए।", "Maaf kijiye.", "Sorry / Excuse me."), hiP("पहले आप।", "Pehle aap.", "After you."),
        ] },
      { m: ["hello", "hi", "greet", "namaste", "aadaab", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Lucknow:", phrases: [
          hiP("आदाब!", "Aadaab!", "Hello! (respectful)"), hiP("ख़ुदा हाफ़िज़!", "Khuda hafiz!", "Goodbye!"),
        ], note: "“Aadaab” and “Namaste” are both everyday greetings in Lucknow." },
      { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
          hiP("मुझे मदद चाहिए।", "Mujhe madad chahiye.", "I need help."), hiP("पास में अस्पताल कहाँ है?", "Paas mein aspataal kahan hai?", "Where's the nearest hospital?"),
        ], note: "Emergency number in India: 112." },
    ],
    generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
        hiP("आदाब! आप कैसे हैं?", "Aadaab! Aap kaise hain?", "Hello! How are you?"), hiP("कितना हुआ?", "Kitna hua?", "How much is it?"),
        hiP("क्या आप मेरी मदद कर सकते हैं?", "Kya aap meri madad kar sakte hain?", "Could you help me?"),
      ], note: "Tell me a situation — like “I want to order kebabs” or “ask the way to Hazratganj” — and I'll give you the exact words." },
  },
  readings: [
    { title: "Asha in Lucknow", level: "A1", lines: [
        hiP("आशा लखनऊ में नई है।", "Asha Lucknow mein nayi hai.", "Asha is new in Lucknow."), hiP("वह मेट्रो से हज़रतगंज जाती है।", "Vah metro se Hazratganj jaati hai.", "She takes the metro to Hazratganj."),
        hiP("वहाँ वह एक चिकनकारी कुर्ता ख़रीदती है।", "Vahan vah ek chikankari kurta khareedti hai.", "There she buys a chikankari kurta."), hiP("शाम को वह गोमती के किनारे घूमती है।", "Shaam ko vah Gomti ke kinaare ghoomti hai.", "In the evening she walks by the Gomti."),
      ],
      questions: [
        { q: "Where is Asha new?", options: ["Jaipur", "Lucknow", "Delhi"], a: 1 }, { q: "What does she buy?", options: ["A chikankari kurta", "Mojaris", "A bag"], a: 0 },
        { q: "Where does she walk in the evening?", options: ["By the Gomti", "In a mall", "At home"], a: 0 },
      ] },
    { title: "Kebabs in Aminabad", level: "A1", lines: [
        hiP("रवि को भूख लगी है।", "Ravi ko bhookh lagi hai.", "Ravi is hungry."), hiP("वह अमीनाबाद में कबाब की दुकान पर जाता है।", "Vah Aminabad mein kebab ki dukaan par jaata hai.", "He goes to a kebab shop in Aminabad."),
        hiP("वह गलौटी कबाब और पराँठा खाता है।", "Vah galouti kebab aur paraantha khaata hai.", "He eats galouti kebabs and a paratha."), hiP("सब मिलाकर दो सौ रुपये हुए।", "Sab milaakar do sau rupaye hue.", "It all came to two hundred rupees."),
      ],
      questions: [
        { q: "How does Ravi feel?", options: ["Tired", "Hungry", "Cold"], a: 1 }, { q: "What does he eat?", options: ["Galouti kebabs", "Idli", "Vada pav"], a: 0 },
        { q: "How much did it cost?", options: ["₹20", "₹200", "₹2000"], a: 1 },
      ] },
  ],
  placement: [
    { q: "What does “Aadaab” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
    { q: "How would you ask an auto driver to go to Hazratganj?", options: ["Hazratganj chalenge?", "Kitna hua?", "Bill le aaiye.", "Khuda hafiz!"], a: 0 },
    { q: "What does “kitna kiraaya hoga” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
    { q: "“Seedhe jaakar baayen mud jaaiye” means…", options: ["Stop here", "Go straight and turn left", "Turn right twice", "Wait for the bus"], a: 1 },
    { q: "What is Lucknow's famous courtesy?", options: ["Pehle aap", "Jaldi karo", "Hatt jao", "Bas karo"], a: 0 },
  ],
  achievements: {
    "auto-pro": ["🛺", "Fair-fare pro", "Agreed a fair auto fare"], foodie: ["🍢", "Kebab connoisseur", "Ordered an Awadhi meal"], bargainer: ["🧵", "Chikankari bargainer", "Won a bargain"],
  },
  rightNow: [
    [5, 11, "🍩", "Breakfast time", "Kachori-jalebi stalls in Aminabad and Chowk are busiest now.", "lko_food", hiP("एक प्लेट कचौरी दीजिए।", "Ek plate kachori dijiye.", "A plate of kachori, please.")],
    [11, 15, "🕌", "Monument hours", "The Bara Imambara and the Rumi Darwaza are open.", "lko_directions", hiP("रूमी दरवाज़ा किस तरफ़ है?", "Rumi Darwaza kis taraf hai?", "Which way is the Rumi Darwaza?")],
    [15, 18, "🧵", "Market hours", "Chowk's chikankari shops are open. Time to bargain, gently.", "lko_shopping", hiP("कुछ कम हो जाएगा?", "Kuch kam ho jaayega?", "Could you do it for a bit less?")],
    [18, 22, "🍢", "Kebab hour", "Aminabad's kebab shops fill up in the evening.", "lko_food", hiP("दो प्लेट गलौटी कबाब दीजिए।", "Do plate galouti kebab dijiye.", "Two plates of galouti kebabs, please.")],
    [22, 29, "🌙", "Late night ride home", "Private autos charge more at night. Agree on the fare first.", "lko_auto", hiP("किराया पहले बता दीजिए।", "Kiraaya pehle bata dijiye.", "Please tell me the fare first.")],
  ],
  priceSay: (max, mid) => ({
    ticket: hiP("हज़रतगंज का एक टोकन दीजिए।", "Hazratganj ka ek token dijiye.", "One token to Hazratganj, please."), meter: hiP("किराया पहले बता दीजिए।", "Kiraaya pehle bata dijiye.", "Please tell me the fare first."),
    fair: hiP("ठीक है, दे दीजिए।", "Theek hai, de dijiye.", "Okay, I'll take it."), counter: hiP(`${max} में दे देंगे?`, `${max} mein de denge?`, `Will you do it for ₹${max}?`),
    high: hiP(`ये ज़्यादा है। ${mid} में दे देंगे?`, `Ye zyaada hai. ${mid} mein de denge?`, `That's a lot. Will you do ₹${mid}?`),
  }),
} };

// Kolkata First Week pack, in Bengali (the English view shows the same pack in English first): everyday spoken Kolkata Bengali, written in
// Bengali script with a romanised line as learners type it. Bengali verbs do not change for the speaker's gender, so no feminine forms.
// AI-assisted editorial review only.
window.PACKS.kolkata = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet people politely and introduce yourself in Bengali.",
    situation: "You've just rented a flat in Salt Lake. Mitra mashima, your landlady, comes to say hello.", scenario: "kol_greetings",
    tip: "“Nomoshkar” is the respectful hello. Use “apni” (polite “you”) with elders and strangers, and verbs ending in -un or -en: “bolun”, “kemon achhen?”. Older women are “mashima” (aunty), older men “kaku”, and anyone a little older “dada” or “didi”.",
    phrases: [
      { hi: "নমস্কার! কেমন আছেন?", roman: "Nomoshkar! Kemon achhen?", en: "Respects! How are you?", natural: "Hello! How are you?" },
      { hi: "আমার নাম অ্যালেক্স।", roman: "Amar naam Alex.", en: "My name Alex.", natural: "I'm Alex." },
      { hi: "আমি এখানে নতুন।", roman: "Ami ekhane notun.", en: "I here new.", natural: "I'm new here." },
      { hi: "আপনার সঙ্গে আলাপ করে ভালো লাগল।", roman: "Apnar shonge alap kore bhalo laglo.", en: "Having talked with you, it felt good.", natural: "Lovely to meet you." },
      { hi: "অনেক ধন্যবাদ!", roman: "Onek dhonnobad!", en: "Many thanks!", natural: "Thank you so much!" },
    ] },
  { day: 2, key: "transport", icon: "🚕", title: "Transport", desc: "Take a yellow taxi by the meter, and the metro.",
    situation: "You've arrived at Howrah Station and need to get to Park Street.", scenario: "kol_taxi",
    tip: "Kolkata's yellow taxis should go by the meter: ask “Meter-e jaben to?” before you get in, and expect some drivers to ask for a little extra or refuse short trips. Autos run on fixed shared routes, and the metro (India's first) runs north–south from Dakshineswar to Kavi Subhash; the Green Line goes under the Hooghly to Howrah and on to Salt Lake.",
    phrases: [
      { hi: "পার্ক স্ট্রিট যাবেন?", roman: "Park Street jaben?", en: "Park Street, will you go?", natural: "Will you go to Park Street?" },
      { hi: "মিটারে যাবেন তো?", roman: "Meter-e jaben to?", en: "By the meter you'll go, right?", natural: "You'll go by the meter, won't you?" },
      { hi: "কত লাগবে?", roman: "Koto lagbe?", en: "How much will it take?", natural: "How much will it cost?" },
      { hi: "মেট্রো স্টেশন কোথায়?", roman: "Metro station kothay?", en: "Metro station where?", natural: "Where's the metro station?" },
      { hi: "এখানে থামুন।", roman: "Ekhane thamun.", en: "Here please stop.", natural: "Stop here, please." },
    ] },
  { day: 3, key: "food", icon: "🌯", title: "Food", desc: "Order a kathi roll, tea in a clay cup and the famous sweets.",
    situation: "An evening snack at a roll stall near Park Street.", scenario: "kol_food",
    tip: "Kolkata's street food: kathi rolls, phuchka (its pani puri) and ghugni; then the sweets, roshogolla, sandesh and mishti doi. Tea comes in a “bhaar”, a small clay cup. “Jhal kom” means less chilli.",
    phrases: [
      { hi: "একটা এগ রোল দিন।", roman: "Ekta egg roll din.", en: "One egg roll please give.", natural: "One egg roll, please." },
      { hi: "ঝাল কম দেবেন।", roman: "Jhal kom deben.", en: "Chilli less please give.", natural: "Not too spicy, please." },
      { hi: "এক ভাঁড় চা।", roman: "Ek bhaar cha.", en: "One clay cup of tea.", natural: "A cup of tea, please." },
      { hi: "দুটো রসগোল্লা দিন।", roman: "Duto roshogolla din.", en: "Two roshogollas please give.", natural: "Two roshogollas, please." },
      { hi: "কত হল?", roman: "Koto holo?", en: "How much did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain for a handloom saree in Gariahat or New Market.",
    situation: "You're at a saree stall in Gariahat Market.", scenario: "kol_shopping",
    tip: "Gariahat and New Market are the places to bargain: start at about half the first price and settle in between. “Taant” is Bengal's light handwoven cotton saree, perfect for the heat. Shops with price tags don't bargain.",
    phrases: [
      { hi: "এটার দাম কত?", roman: "Etar daam koto?", en: "This one's price how much?", natural: "How much is this?" },
      { hi: "খুব বেশি দাম।", roman: "Khub beshi daam.", en: "Very much price.", natural: "That's too expensive." },
      { hi: "একটু কম করুন।", roman: "Ektu kom korun.", en: "A little less please make.", natural: "Can you lower it a bit?" },
      { hi: "অন্য রং আছে?", roman: "Onno rong achhe?", en: "Another colour is there?", natural: "Do you have another colour?" },
      { hi: "ঠিক আছে, প্যাক করে দিন।", roman: "Thik achhe, pack kore din.", en: "Okay, having packed please give.", natural: "Okay, pack it up." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way round central Kolkata.",
    situation: "You've come out of Esplanade metro and want the Victoria Memorial.", scenario: "kol_directions",
    tip: "People give directions by landmark: the Maidan, the metro stations, a famous sweet shop. “Daan” is right, “baan” is left and “shoja” is straight on.",
    phrases: [
      { hi: "ভিক্টোরিয়া মেমোরিয়াল কোন দিকে?", roman: "Victoria Memorial kon dike?", en: "Victoria Memorial which way?", natural: "Which way is the Victoria Memorial?" },
      { hi: "সোজা যান, তারপর ডান দিকে।", roman: "Shoja jan, tarpor daan dike.", en: "Straight go, then to the right.", natural: "Go straight, then turn right." },
      { hi: "হেঁটে কতক্ষণ লাগবে?", roman: "Hete kotokkhon lagbe?", en: "Walking how long will it take?", natural: "How long is it on foot?" },
      { hi: "কাছে কোনো ওষুধের দোকান আছে?", roman: "Kachhe kono oshudher dokan achhe?", en: "Nearby any medicine shop is there?", natural: "Is there a pharmacy nearby?" },
      { hi: "একটু আস্তে বলুন।", roman: "Ektu aste bolun.", en: "A little slowly please speak.", natural: "Could you speak a bit more slowly?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in with classmates and colleagues.",
    situation: "Your first day at Jadavpur University.", scenario: "kol_college",
    tip: "Classmates use “tumi” with each other; teachers and colleagues you've just met get “apni”. A cup of tea at the canteen is how friendships start, and long chats over it are “adda”.",
    phrases: [
      { hi: "আজ আমার প্রথম দিন।", roman: "Aaj amar prothom din.", en: "Today my first day.", natural: "It's my first day today." },
      { hi: "ক্লাসটা কোথায়?", roman: "Class-ta kothay?", en: "The class where?", natural: "Where's the class?" },
      { hi: "একটু সাহায্য করবেন?", roman: "Ektu shahajjo korben?", en: "A little help will you do?", natural: "Could you help me a bit?" },
      { hi: "ক্যান্টিনে চা খাবে?", roman: "Canteen-e cha khabe?", en: "In the canteen tea will you have?", natural: "Shall we get tea at the canteen?" },
      { hi: "পরে দেখা হবে!", roman: "Pore dekha hobe!", en: "Later meeting will happen!", natural: "See you later!" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a proper Kolkata adda.",
    situation: "Sunset at Prinsep Ghat with Arko, a friend from college.", scenario: "kol_smalltalk",
    tip: "“Adda” (a long, easy chat with friends) is Kolkata's favourite pastime. “Darun!” means “brilliant!”, and Sunday mornings are for the book stalls of College Street and a coffee at the Indian Coffee House.",
    phrases: [
      { hi: "আড্ডা দিতে খুব ভালো লাগে!", roman: "Adda dite khub bhalo lage!", en: "To do adda feels very good!", natural: "I love a good adda!" },
      { hi: "কলকাতায় খুব গরম, না?", roman: "Kolkatay khub gorom, na?", en: "In Kolkata very hot, no?", natural: "It's really hot in Kolkata, isn't it?" },
      { hi: "তুমি কি কলকাতারই?", roman: "Tumi ki Kolkatar-i?", en: "You, of Kolkata itself?", natural: "Are you from Kolkata?" },
      { hi: "রবিবার কলেজ স্ট্রিট যাবে?", roman: "Robibar College Street jabe?", en: "Sunday College Street will you go?", natural: "Fancy College Street on Sunday?" },
      { hi: "দারুণ, পাকা!", roman: "Darun, paka!", en: "Brilliant, fixed!", natural: "Brilliant, it's a plan!" },
    ] },
];

Object.assign(window.SCENARIOS, {
  kol_greetings: { category: "greetings", icon: "🏠", title: "Meet your landlady", partner: "Mitra mashima", role: "Landlady", place: "Your rented flat in Salt Lake",
    goal: "Greet your landlady politely, introduce yourself and ask when the water comes.",
    opening: { text: "Esho, esho! Tumi-i Alex? Ami Mitra mashima.", en: "Come in, come in! Are you Alex? I'm Mrs Mitra." },
    start: ["Nomoshkar! Kemon achhen?", "Hyan, amar naam Alex.", "Jol kokhon ashe?"],
    rules: [
      { m: ["dhonnobad", "thank", "bujhechhi", "aschhi", "pore dekha"], text: "Kichhu dorkar hole bolbe. 🙏", en: "Tell me if you need anything.", s: ["Aschhi, mashima!"], end: true, hint: "Onek dhonnobad, mashima!" },
      { m: ["jol", "pani", "kokhon", "current"], text: "Jol shokale ar bikele ashe. Current gele inverter achhe.", en: "Water comes in the morning and the afternoon. If the power goes, there's an inverter.", s: ["Thik achhe, bujhechhi.", "Onek dhonnobad, mashima!"], hint: "Jol kokhon ashe?" },
      { m: ["alap", "bhalo laglo"], text: "Amaro khub bhalo laglo. Kolkatay prothom baar?", en: "Lovely to meet you too. First time in Kolkata?", s: ["Hyan, prothom baar.", "Jol kokhon ashe?"], hint: "Apnar shonge alap kore bhalo laglo." },
      { m: ["prothom baar", "notun", "new"], text: "Tahole Kolkatar adda ar mishti, dutoi upobhog koro!", en: "Then enjoy both Kolkata's adda and its sweets!", s: ["Jol kokhon ashe?", "Onek dhonnobad, mashima!"], hint: "Hyan, prothom baar." },
      { m: ["naam", "alex", "name"], text: "Bah, shundor naam! Kolkatay prothom baar?", en: "What a lovely name! First time in Kolkata?", s: ["Hyan, prothom baar.", "Apnar shonge alap kore bhalo laglo."], hint: "Hyan, amar naam Alex." },
      { m: ["nomoshkar", "namaskar", "kemon", "hello", " hi "], text: "Bhalo achhi! Tomar naam ki?", en: "I'm well! What's your name?", s: ["Hyan, amar naam Alex.", "Apnar shonge alap kore bhalo laglo."], hint: "Nomoshkar! Kemon achhen?" },
    ],
    fallback: { text: "Bolo, ki lagbe? Jol, current, Wi-Fi?", en: "Tell me, what do you need? Water, power, the Wi-Fi?", s: ["Jol kokhon ashe?", "Onek dhonnobad, mashima!"] } },

  kol_taxi: { category: "transport", icon: "🚕", title: "Yellow taxi to Park Street", partner: "Bapi da", role: "Taxi driver", place: "The taxi stand outside Howrah Station",
    goal: "Get to Park Street by the meter.", places: ["Park Street", "Esplanade", "Gariahat", "Salt Lake", "Airport", "College Street", "Victoria", "New Market", "Sealdah"],
    opening: { text: "Kothay jaben?", en: "Where to?" },
    start: ["Park Street jaben?", "Meter-e jaben to?", "Koto lagbe?"],
    rules: [
      { m: ["dhonnobad", "thank", "upi", "aschhi"], text: "Dhonnobad! Bhalo thakben. 🙏", en: "Thank you! Take care.", s: ["Aschhi!"], end: true, hint: "Dhonnobad, dada!" },
      { m: ["thamun", "ekhane", "rakhun", "stop"], text: "Eshe gechhi, Park Street! Meter-e eksho kuri taka.", en: "Here we are, Park Street! A hundred and twenty on the meter.", s: ["UPI hobe?", "Dhonnobad, dada!"], hint: "Ekhane thamun." },
      // before the meter rule: "meter-er beshi" (more than the meter) contains "meter"
      { m: ["beshi", "extra", "upore"], text: "Thik achhe, meter-ei jabo.", en: "All right, I'll go by the meter.", s: ["Cholun.", "Kotokkhon lagbe?"], hint: "Na, meter-er beshi debo na." },
      { m: ["meter"], text: "Meter-e jabo, kintu kuri taka beshi lagbe. Bridge-e jaam.", en: "I'll go by the meter, but it's twenty extra. There's a jam on the bridge.", s: ["Na, meter-er beshi debo na.", "Thik achhe, cholun."], hint: "Meter-e jaben to?" },
      // before the price rule: "kotokkhon" (how long) contains "koto" (how much)
      { m: ["kotokkhon", "minute", "deri"], text: "Jaam thakle kuri minute.", en: "Twenty minutes if there's traffic.", s: ["Thik achhe, cholun.", "Ekhane thamun."], hint: "Kotokkhon lagbe?" },
      { m: ["koto", "bhara", "taka", "price"], text: "Meter-e jabo, eksho-r moto hobe.", en: "By the meter: about a hundred.", s: ["Meter-e jaben to?", "Thik achhe, cholun."], hint: "Koto lagbe?" },
      { m: ["metro"], text: "Metro chaile Howrah Maidan station kachhei.", en: "If you want the metro, Howrah Maidan station is close by.", s: ["Na, taxi-tei jabo.", "Koto lagbe?"], hint: "Metro station kothay?" },
      { m: ["park street", "esplanade", "gariahat", "salt lake", "airport", "college street", "victoria", "new market", "sealdah", "jaben"], text: "{place}? Hyan, cholun. Uthe porun.", en: "{place}? Yes, let's go. Get in.", s: ["Meter-e jaben to?", "Koto lagbe?"], hint: "{place} jaben?" },
      { m: ["prothom baar", "notun", "new"], text: "Kolkatay shagotom! Phuchka khete bhulben na.", en: "Welcome to Kolkata! Don't forget to try phuchka.", s: ["Kotokkhon lagbe?", "Ekhane thamun."] },
      { m: ["thik achhe", "cholun", "taxi", "hyan"], text: "Uthe porun! Kolkatay prothom baar?", en: "Get in! First time in Kolkata?", s: ["Hyan, prothom baar.", "Kotokkhon lagbe?"] },
    ],
    fallback: { text: "Bujhlam na. Kothay jaben?", en: "I didn't get that. Where to?", s: ["Park Street jaben?", "Koto lagbe?"] } },

  kol_food: { category: "food", icon: "🌯", title: "Rolls near Park Street", partner: "Shibu da", role: "Roll stall owner", place: "A kathi roll stall near Park Street",
    goal: "Order a roll and a cup of tea, ask for less chilli and pay.",
    opening: { text: "Bolun, ki debo?", en: "Tell me, what can I get you?" },
    start: ["Ekta egg roll din.", "Jhal kom deben.", "Koto holo?"],
    rules: [
      { m: ["dhonnobad", "thank", "upi", "ei nin", "aschhi"], text: "Dhonnobad! Abar ashben. 🙏", en: "Thank you! Come again.", s: ["Aschhi!"], end: true, hint: "Ei nin." },
      { m: ["koto", "bill", "taka"], text: "Egg roll ar cha, shottor taka.", en: "An egg roll and a tea, seventy rupees.", s: ["UPI hobe?", "Ei nin."], hint: "Koto holo?" },
      { m: ["jhal", "lonka", "spicy"], text: "Thik achhe, jhal kom.", en: "Okay, less chilli.", s: ["Ek bhaar cha.", "Koto holo?"], hint: "Jhal kom deben." },
      { m: ["roshogolla", "rosogolla", "mishti", "sandesh"], text: "Roshogolla pasher dokane paben. Ami shudhu roll ar cha rakhi!", en: "You'll find roshogollas at the shop next door. I only do rolls and tea!", s: ["Thik achhe. Koto holo?", "Ek bhaar cha."], hint: "Roshogolla achhe?" },
      { m: ["cha", "bhaar", "tea"], text: "Ek bhaar garam cha! Ar kichhu?", en: "A clay cup of hot tea! Anything else?", s: ["Koto holo?", "Ekta egg roll din."], hint: "Ek bhaar cha." },
      { m: ["roll", "egg", "chicken", "mutton", "paneer"], text: "Garam garam egg roll! Peyaj, lonka debo?", en: "A piping-hot egg roll! Onion and chilli in it?", s: ["Peyaj din, lonka kom.", "Jhal kom deben."], hint: "Ekta egg roll din." },
    ],
    fallback: { text: "Egg roll, chicken roll, cha... ki debo?", en: "Egg roll, chicken roll, tea... what can I get you?", s: ["Ekta egg roll din.", "Ek bhaar cha."] } },

  kol_shopping: { category: "shopping", icon: "🛍️", title: "A saree in Gariahat", partner: "Rina di", role: "Shopkeeper", place: "A saree stall in Gariahat Market",
    goal: "Buy a handloom cotton saree at a fair price.",
    opening: { text: "Ashun, dekhun! Taant, tussar, sob achhe.", en: "Come in, take a look! Taant, tussar, we have it all." },
    start: ["Etar daam koto?", "Onno rong achhe?", "Khub beshi daam."],
    rules: [
      { m: ["pack", "dhonnobad", "upi", "aschhi"], text: "Pack kore dilam! Abar ashben. 🙏", en: "Packed! Come again.", s: ["Aschhi!"], end: true, hint: "Thik achhe, pack kore din." },
      { m: ["char sho", "panch sho", "400", "500"], text: "Accha, apnar jonno chhoy sho. Er kome hobe na.", en: "All right, six hundred for you. I can't go lower.", s: ["Thik achhe, pack kore din.", "UPI hobe?"], hint: "Panch sho hobe?" },
      { m: ["beshi", "kom", "last"], text: "Haate bona taant! Accha, aat sho.", en: "It's handwoven taant! All right, eight hundred.", s: ["Panch sho hobe?", "Ektu kom korun."], hint: "Ektu kom korun." },
      { m: ["rong", "colour", "color", "lal", "neel"], text: "Hyan, lal ar neel-o achhe.", en: "Yes, there's red and blue too.", s: ["Etar daam koto?", "Neel-ta dekhan."], hint: "Onno rong achhe?" },
      { m: ["daam", "koto", "price"], text: "Ei taant? Hajar taka.", en: "This taant saree? A thousand rupees.", s: ["Khub beshi daam.", "Ektu kom korun."], hint: "Etar daam koto?" },
      { m: ["haate", "taant", "tant", "tussar", "cotton"], text: "Hyan, sob haate bona, Shantipur-er taant.", en: "Yes, all handwoven: taant from Shantipur.", s: ["Etar daam koto?", "Onno rong achhe?"], hint: "Eta ki haate bona?" },
    ],
    fallback: { text: "Shomoy niye dekhun. Taant, tussar, sob achhe.", en: "Take your time. Taant, tussar, we have it all.", s: ["Etar daam koto?", "Onno rong achhe?"] } },

  kol_directions: { category: "directions", icon: "🏛️", title: "Find the Victoria Memorial", partner: "Ghosh babu", role: "Passerby", place: "Outside Esplanade metro station",
    goal: "Find the way to the Victoria Memorial, and a pharmacy.",
    opening: { text: "Kichhu khunjchhen?", en: "Looking for something?" },
    start: ["Victoria Memorial kon dike?", "Kachhe kono oshudher dokan achhe?", "Hete kotokkhon lagbe?"],
    rules: [
      { m: ["dhonnobad", "thank", "bujhechhi", "aschhi"], text: "Kichhu na! Bhalo kore ghurun. 🙏", en: "Not at all! Enjoy your walk.", s: ["Aschhi!"], end: true, hint: "Onek dhonnobad!" },
      { m: ["aste", "abar bolun", "slow"], text: "Shoja jan, tarpor daan dike. Bas!", en: "Straight on, then right. That's it!", s: ["Thik achhe, bujhechhi.", "Hete kotokkhon lagbe?"], hint: "Ektu aste bolun." },
      { m: ["oshudh", "pharmacy", "medical", "chemist", "hospital"], text: "Hyan, metro station-er ulto dike ekta oshudher dokan achhe.", en: "Yes, there's a pharmacy opposite the metro station.", s: ["Victoria Memorial kon dike?", "Ektu aste bolun."], hint: "Kachhe kono oshudher dokan achhe?" },
      { m: ["hete", "kotokkhon", "walk"], text: "Hete kuri-pochish minute, Maidan-er pash diye.", en: "Twenty to twenty-five minutes on foot, along the Maidan.", s: ["Metro-te jawa jay?", "Thik achhe, bujhechhi."], hint: "Hete kotokkhon lagbe?" },
      { m: ["metro", "bus"], text: "Metro-te Maidan station, dui stop. Okhan theke hete paanch minute.", en: "Take the metro to Maidan, two stops. It's five minutes' walk from there.", s: ["Thik achhe, bujhechhi.", "Onek dhonnobad!"], hint: "Metro-te jawa jay?" },
      { m: ["victoria", "memorial", "kon dike", "kothay", "maidan"], text: "Shoja jan, tarpor daan dike. Maidan perolei Victoria Memorial.", en: "Go straight, then turn right. Past the Maidan is the Victoria Memorial.", s: ["Hete kotokkhon lagbe?", "Ektu aste bolun."], hint: "Victoria Memorial kon dike?" },
    ],
    fallback: { text: "Bolun, kothay jaben?", en: "Tell me, where do you need to go?", s: ["Victoria Memorial kon dike?", "Kachhe kono oshudher dokan achhe?"] } },

  kol_college: { category: "college", icon: "🎓", title: "First day at Jadavpur University", partner: "Priya", role: "Classmate", place: "Jadavpur University campus",
    goal: "Find your class and the canteen, and make a friend.",
    opening: { text: "Hi! Aaj prothom din? Ami Priya.", en: "Hi! First day today? I'm Priya." },
    start: ["Hyan, aaj amar prothom din.", "Class-ta kothay?", "Canteen-e cha khabe?"],
    rules: [
      { m: ["pore dekha", "bye", "thank", "dhonnobad", "darun"], text: "Welcome! Kichhu lagle bolo. 👋", en: "Welcome! Tell me if you need anything.", s: ["Pore dekha hobe!"], end: true, hint: "Thank you, Priya!" },
      { m: ["cha", "canteen", "milan da"], text: "Hyan, break-e Milan da-r canteen-e jai!", en: "Yes, let's go to Milan da's canteen at the break!", s: ["Darun!", "Thank you, Priya!"], hint: "Canteen-e cha khabe?" },
      { m: ["shahajjo", "help"], text: "Hyan, nishchoy! Routine-ta WhatsApp kore dichhi.", en: "Of course! I'll WhatsApp you the timetable.", s: ["Canteen-e cha khabe?", "Thank you, Priya!"], hint: "Ektu shahajjo korben?" },
      { m: ["class", "room", "kothay", "library"], text: "Class-ta dotolay, ghor dusho char.", en: "The class is on the first floor, room 204.", s: ["Ektu shahajjo korben?", "Canteen-e cha khabe?"], hint: "Class-ta kothay?" },
      { m: ["prothom", "hyan", "first"], text: "Welcome! Prothom din-e sob ektu gulie jay.", en: "Welcome! Everything's a bit confusing on the first day.", s: ["Class-ta kothay?", "Ektu shahajjo korben?"], hint: "Aaj amar prothom din." },
    ],
    fallback: { text: "Bolo, ki lagbe? Class, library, na canteen?", en: "Tell me, what do you need? The class, the library or the canteen?", s: ["Class-ta kothay?", "Canteen-e cha khabe?"] } },

  kol_smalltalk: { category: "smalltalk", icon: "🌇", title: "Adda at Prinsep Ghat", partner: "Arko", role: "Friend", place: "Prinsep Ghat at sunset",
    goal: "Have an adda about Kolkata and plan a Sunday at College Street.",
    opening: { text: "Ki shundor, na? Kolkata kemon lagchhe?", en: "Beautiful, isn't it? How are you liking Kolkata?" },
    start: ["Adda dite khub bhalo lage!", "Kolkatay khub gorom, na?", "Tumi ki Kolkatar-i?"],
    rules: [
      { m: ["paka", "bye", "darun", "pore dekha"], text: "Paka! Robibar shokale College Street-e dekha hobe. 👋", en: "Deal! See you at College Street on Sunday morning.", s: ["Bye, Arko!"], end: true, hint: "Darun, paka!" },
      { m: ["kota", "shokale"], text: "Shokal noy-tay, bhir-er age.", en: "Nine in the morning, before the crowds.", s: ["Darun, paka!"], hint: "Kota-y?" },
      { m: ["college street", "robibar", "sunday", "boi", "coffee house"], text: "Hyan! Robibar College Street-e boi dekhbo, tarpor Coffee House-e adda.", en: "Yes! Books at College Street on Sunday, then adda at the Coffee House.", s: ["Darun, paka!", "Kota-y?"], hint: "Robibar College Street jabe?" },
      { m: ["kolkatar", "ekhanei", "born"], text: "Hyan, ami Uttar Kolkatay boro hoyechhi!", en: "Yes, I grew up in North Kolkata!", s: ["Robibar College Street jabe?", "Kolkatay khub gorom, na?"], hint: "Tumi ki Kolkatar-i?" },
      { m: ["gorom", "brishti", "weather"], text: "Hyan, kintu bikele Gongar haowa khub aram.", en: "Yes, but in the evening the breeze off the river is lovely.", s: ["Tumi ki Kolkatar-i?", "Robibar College Street jabe?"], hint: "Kolkatay khub gorom, na?" },
      { m: ["adda", "shundor", "ghat"], text: "Kolkata mane-i adda! Ar ei ghat-e shondhe-ta sobcheye bhalo.", en: "Kolkata means adda! And evenings at this ghat are the best.", s: ["Kolkatay khub gorom, na?", "Robibar College Street jabe?"], hint: "Adda dite khub bhalo lage!" },
    ],
    fallback: { text: "Haha, thik! Kolkatay tomar sobcheye bhalo ki lagchhe?", en: "Haha, true! What do you like most about Kolkata?", s: ["Adda dite khub bhalo lage!", "Kolkatay khub gorom, na?"] } },
});

window.CONTENT_REVIEW.kolkata = {
  bn: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
    known_limitations: ["The content teaches spoken Kolkata Bengali (cholito bhasha), not the formal written style.", "Romanised Bengali has no fixed spelling: “sh” is written for শ/ষ/স as Kolkata speakers say it, and long vowels are not marked.", "Fares and practical tips change over time."],
    note: "Kolkata Bengali: AI-assisted editorial review only, not yet checked by a native Bengali speaker." },
};

const PLACE_KOL = {
  "park street": ["Park Street", "পার্ক স্ট্রিট", "Park Street"], esplanade: ["Esplanade", "এসপ্ল্যানেড", "Esplanade"], gariahat: ["Gariahat", "গড়িয়াহাট", "Gariahat"],
  "salt lake": ["Salt Lake", "সল্টলেক", "Salt Lake"], howrah: ["Howrah", "হাওড়া", "Howrah Station"], airport: ["airport", "এয়ারপোর্ট", "the airport"],
  "college street": ["College Street", "কলেজ স্ট্রিট", "College Street"], victoria: ["Victoria", "ভিক্টোরিয়া", "the Victoria Memorial"],
  "new market": ["New Market", "নিউ মার্কেট", "New Market"], sealdah: ["Sealdah", "শিয়ালদা", "Sealdah Station"],
};
const KOLKATA_PLACES = ["Park Street", "Esplanade", "Gariahat", "Salt Lake", "Howrah", "Airport", "College Street", "Victoria", "New Market", "Sealdah"];
const KOL_RIDE_NOTE = "Kolkata's yellow taxis should go by the meter: ask before you sit in. Some drivers ask for a little extra or refuse short trips; app cabs are an alternative. Autos run on fixed shared routes and are paid per seat.";
const KOL_METRO_NOTE = "Kolkata Metro: the Blue Line runs north–south from Dakshineswar to Kavi Subhash (via Esplanade, Park Street and Maidan); the Green Line runs under the Hooghly from Howrah Maidan through Esplanade and Sealdah to Salt Lake Sector V; the Purple and Orange Lines are newer. Blue Line fares are ₹5–25: buy a token or a QR ticket.";
const bnP = (hi, roman, en, extra) => ({ hi, roman, en, ...(extra || {}) });

window.LOCAL_CONTENT.kolkata = {
  // ---------- Kolkata, in Bengali (and the English view) ----------
  bn: {
    tutor: {
      greet: "Nomoshkar", places: KOLKATA_PLACES, defaultPlace: "Park Street", language: "Bengali",
      starters: ["I need a taxi to Park Street.", "How do I order a kathi roll, not too spicy?", "How do I bargain in Gariahat?", "What does 'adda' mean?", "Which metro line goes to Esplanade?"],
      glossaryOnly: true,                                // Hindi words are not Bengali: the shared (Hindi) glossary is not used
      glossary: {
        nomoshkar: "A respectful hello (and goodbye). Works with anyone, any time.", adda: "A long, easy chat with friends, over tea: Kolkata's favourite pastime.",
        darun: "“Brilliant! / Great!”", dada: "“Elder brother”: a friendly way to address a man a little older, a driver or a shopkeeper.",
        didi: "“Elder sister”: the female equivalent of dada.", mashima: "“Aunty”: for an older woman.", kaku: "“Uncle”: for an older man.",
        apni: "The polite “you”, for elders and strangers. “Tumi” is for friends and classmates.", bhaar: "A small clay cup for tea.",
        jhal: "“Spicy / chilli-hot.” Jhal kom = less spicy.", koto: "“How much.” Koto holo? = How much is it?", kothay: "Where. Kothay jaben? = Where are you going?",
        hyan: "Yes.", na: "No.", "thik achhe": "“Okay / all right.”", din: "“Please give.” The polite form of “dao”.", dhonnobad: "Thank you.",
        phuchka: "Kolkata's pani puri: crisp shells with spiced potato and tamarind water.", mishti: "“Sweet.” Mishti doi = sweet yoghurt.",
      },
      polite: { intro: "Bengali's polite forms use “apni” and verbs ending in -un or -en (“din”, “bolun”, “korun”):", rules: [["\\bdao\\b", "din"], ["\\bbolo\\b", "bolun"], ["\\bkoro\\b", "korun"], ["\\btumi\\b", "apni"]],
        note: "e.g. “dao” → “din”, “bolo” → “bolun”, “tumi” → “apni”. With friends the short forms are fine." },
      intents: [
        { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
          build: (dest) => { const d = PLACE_KOL[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
            bnP(d ? `${d[1]} যাবেন? মিটারে।` : "", `${r} jaben? Meter-e.`, `Will you go to ${d ? d[2] : dest}? By the meter.`),
            bnP(d ? `দাদা, ${d[1]} যাবেন, প্লিজ?` : "", `Dada, ${r} jaben, please?`, `A more polite version: Would you take me to ${d ? d[2] : dest}, please?`, { label: "More polite" }),
            bnP("মিটারে চলুন।", "Meter-e cholun.", "Please go by the meter."),
          ], note: KOL_RIDE_NOTE }; } },
        { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
            bnP("এসপ্ল্যানেড কোন লাইনে?", "Esplanade kon line-e?", "Which line for Esplanade?"), bnP("এই মেট্রো পার্ক স্ট্রিট যাবে?", "Ei metro Park Street jabe?", "Does this metro go to Park Street?"),
            bnP("টোকেন কোথায় পাব?", "Token kothay pabo?", "Where do I get a token?"),
          ], note: KOL_METRO_NOTE },
        { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
            bnP("একটু কম করুন।", "Ektu kom korun.", "Please lower it a little."), bnP("খুব বেশি দাম।", "Khub beshi daam.", "That's too expensive."),
            bnP("শেষ দাম কত?", "Shesh daam koto?", "What's your best price?"),
          ], note: "In Gariahat and New Market start at about half the first price and settle in between." },
        { m: ["price", "how much", "cost", "koto", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
            bnP("এটার দাম কত?", "Etar daam koto?", "How much is this?"), bnP("ইউপিআই হবে?", "UPI hobe?", "Can I pay by UPI?"),
          ] },
        { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "roll", "sweet", "bill"], topic: "food", intro: "Ordering food:", phrases: [
            bnP("একটা এগ রোল দিন।", "Ekta egg roll din.", "One egg roll, please."), bnP("ঝাল কম দেবেন।", "Jhal kom deben.", "Not too spicy, please."),
            bnP("বিলটা দিন।", "Bill-ta din.", "Could I have the bill, please?"),
          ], note: "“Din” is the polite “please give”. Finish with mishti doi or a roshogolla." },
        { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
            bnP("ভিক্টোরিয়া মেমোরিয়াল কোন দিকে?", "Victoria Memorial kon dike?", "Which way is the Victoria Memorial?"), bnP("আমি রাস্তা হারিয়ে ফেলেছি।", "Ami rasta hariye phelechhi.", "I'm lost."),
            bnP("সবচেয়ে কাছের মেট্রো কোনটা?", "Sobcheye kachher metro konta?", "Which is the nearest metro station?"),
          ], note: "“Daan” is right, “baan” is left and “shoja” is straight on. People give directions by landmark." },
        { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At college or work:", phrases: [
            bnP("আজ আমার প্রথম দিন।", "Aaj amar prothom din.", "It's my first day today."), bnP("মিটিং কটায়?", "Meeting kotay?", "What time's the meeting?"),
            bnP("একটু সাহায্য করবেন?", "Ektu shahajjo korben?", "Could you help me a bit?"),
          ] },
        { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
            bnP("আপনি কোথা থেকে এসেছেন?", "Apni kotha theke eshechhen?", "Where are you from?"), bnP("আজ খুব গরম, না?", "Aaj khub gorom, na?", "It's really hot today, isn't it?"),
            bnP("এক কাপ চা হবে?", "Ek cup cha hobe?", "How about a cup of tea?"),
          ], note: "Kolkata small talk: football, food, books and films. A good adda can last all evening." },
        { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
            bnP("আমার নাম অ্যালেক্স।", "Amar naam Alex.", "My name is Alex."), bnP("আপনার নাম কী?", "Apnar naam ki?", "What's your name?"),
            bnP("আপনার সঙ্গে আলাপ করে ভালো লাগল।", "Apnar shonge alap kore bhalo laglo.", "Lovely to meet you."),
          ] },
        { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
            bnP("অনেক ধন্যবাদ!", "Onek dhonnobad!", "Thanks a lot!"), bnP("মাফ করবেন।", "Maaf korben.", "Sorry / Excuse me."), bnP("শুনছেন?", "Shunchhen?", "Excuse me… (to get attention)"),
          ] },
        { m: ["hello", "hi", "greet", "namaste", "nomoshkar", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Kolkata:", phrases: [
            bnP("নমস্কার! কেমন আছেন?", "Nomoshkar! Kemon achhen?", "Hello! How are you?"), bnP("পরে দেখা হবে!", "Pore dekha hobe!", "See you later!"),
          ], note: "“Nomoshkar” works with everyone; with friends, “Ki khobor?” (what's new?)." },
        { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
            bnP("আমার সাহায্য লাগবে।", "Amar shahajjo lagbe.", "I need help."), bnP("কাছে হাসপাতাল কোথায়?", "Kachhe haspatal kothay?", "Where's the nearest hospital?"),
          ], note: "Emergency number in India: 112." },
      ],
      generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
          bnP("নমস্কার! কেমন আছেন?", "Nomoshkar! Kemon achhen?", "Hello! How are you?"), bnP("কত হল?", "Koto holo?", "How much is it?"),
          bnP("একটু সাহায্য করবেন?", "Ektu shahajjo korben?", "Could you help me a bit?"),
        ], note: "Tell me a situation — like “I want to order a roll” or “ask the way to Park Street” — and I'll give you the exact Bengali words." },
    },
    readings: [
      { title: "Asha in Kolkata", level: "A1", lines: [
          bnP("আশা কলকাতায় নতুন।", "Asha Kolkatay notun.", "Asha is new in Kolkata."), bnP("ও মেট্রো করে পার্ক স্ট্রিট যায়।", "O metro kore Park Street jay.", "She takes the metro to Park Street."),
          bnP("সেখানে ও একটা এগ রোল খায়।", "Shekhane o ekta egg roll khay.", "There she eats an egg roll."), bnP("তারপর ও এক ভাঁড় চা খায়।", "Tarpor o ek bhaar cha khay.", "Then she has a clay cup of tea."),
        ],
        questions: [
          { q: "Where is Asha new?", options: ["Delhi", "Kolkata", "Chennai"], a: 1 }, { q: "How does she travel?", options: ["By metro", "By tram", "By auto"], a: 0 },
          { q: "What does she drink?", options: ["Coffee", "Lassi", "Tea"], a: 2 },
        ] },
      { title: "A saree in Gariahat", level: "A1", lines: [
          bnP("রিয়া গড়িয়াহাটে যায়।", "Riya Gariahat-e jay.", "Riya goes to Gariahat."), bnP("ওর একটা তাঁতের শাড়ি পছন্দ হয়।", "Or ekta taanter shari pochhondo hoy.", "She likes a taant saree."),
          bnP("দোকানদার হাজার টাকা চায়।", "Dokandar hajar taka chay.", "The shopkeeper asks for a thousand rupees."), bnP("রিয়া ছশো টাকায় কেনে।", "Riya chhosho takay kene.", "Riya buys it for six hundred."),
        ],
        questions: [
          { q: "Where does Riya go?", options: ["Gariahat", "Park Street", "Howrah"], a: 0 }, { q: "What does she like?", options: ["A saree", "A book", "A bag"], a: 0 },
          { q: "How much does she pay?", options: ["₹1000", "₹600", "₹60"], a: 1 },
        ] },
    ],
    placement: [
      { q: "What does “Nomoshkar” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
      { q: "How would you ask a taxi to go by the meter?", options: ["Meter-e jaben to?", "Koto holo?", "Ek bhaar cha.", "Pore dekha hobe!"], a: 0 },
      { q: "What does “koto lagbe” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
      { q: "“Shoja jan, tarpor daan dike” means…", options: ["Stop here", "Go straight, then turn right", "Turn left twice", "Wait for the bus"], a: 1 },
      { q: "Which is the polite way to ask for one egg roll?", options: ["Ekta egg roll dao", "Ekta egg roll din", "Egg roll!", "Roll de"], a: 1 },
    ],
    achievements: {
      "first-words": ["🗣️", "First words", "Said your first Bengali phrase"], "auto-pro": ["🚕", "Meter pro", "Took a taxi by the meter"],
      foodie: ["🌯", "Roll lover", "Ordered Kolkata street food"], bargainer: ["🛍️", "Gariahat bargainer", "Won a bargain"],
    },
    rightNow: [
      [5, 11, "☕", "Morning tea", "Tea stalls are busiest now. Order a cup like a local.", "kol_food", bnP("এক ভাঁড় চা।", "Ek bhaar cha.", "A cup of tea, please.")],
      [11, 15, "🏛️", "Sightseeing hours", "The Victoria Memorial and the Indian Museum are open.", "kol_directions", bnP("ভিক্টোরিয়া মেমোরিয়াল কোন দিকে?", "Victoria Memorial kon dike?", "Which way is the Victoria Memorial?")],
      [15, 18, "🛍️", "Market hours", "Gariahat and New Market are buzzing. Time to bargain.", "kol_shopping", bnP("একটু কম করুন।", "Ektu kom korun.", "Can you lower it a bit?")],
      [18, 22, "🌇", "Adda o'clock", "Evenings by the river are for a long chat with friends.", "kol_smalltalk", bnP("আড্ডা দিতে খুব ভালো লাগে!", "Adda dite khub bhalo lage!", "I love a good adda!")],
      [22, 29, "🌙", "Late night ride home", "Ask for the meter before you get into a taxi.", "kol_taxi", bnP("মিটারে যাবেন তো?", "Meter-e jaben to?", "You'll go by the meter, won't you?")],
    ],
    priceSay: (max, mid) => ({
      ticket: bnP("এসপ্ল্যানেডের একটা টোকেন দিন।", "Esplanade-er ekta token din.", "One token to Esplanade, please."), meter: bnP("মিটারে চলুন।", "Meter-e cholun.", "Please go by the meter."),
      fair: bnP("ঠিক আছে, দিন।", "Thik achhe, din.", "Okay, I'll take it."), counter: bnP(`${max} টাকায় দেবেন?`, `${max} takay deben?`, `Will you do it for ₹${max}?`),
      high: bnP(`খুব বেশি দাম। ${mid} টাকায় দেবেন?`, `Khub beshi daam. ${mid} takay deben?`, `That's too expensive. Will you do ₹${mid}?`),
    }),
  },
};

// Hyderabad First Week pack, in Telugu (the English view shows the same pack in English first): everyday spoken Hyderabad Telugu, written in
// Telugu script with a romanised line as learners type it. Telugu verbs for "I" and "you" do not change for gender, so no feminine forms.
// AI-assisted editorial review only.
window.PACKS.hyderabad = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet people politely and introduce yourself in Telugu.",
    situation: "You've just rented a flat in Madhapur. Lakshmi garu, the house owner, comes to say hello.", scenario: "hyd_greetings",
    tip: "“Namaskaram” is the respectful hello. Add “garu” after a name to be respectful (“Lakshmi garu”), and “andi” to soften a reply (“avunandi”, yes). The polite “you” is “meeru”, and polite requests end in -andi: “cheppandi” (please say), “ivvandi” (please give).",
    phrases: [
      { hi: "నమస్కారం! బాగున్నారా?", roman: "Namaskaram! Baagunnaara?", en: "Respects! Are you well?", natural: "Hello! How are you?" },
      { hi: "నా పేరు అలెక్స్.", roman: "Naa peru Alex.", en: "My name Alex.", natural: "I'm Alex." },
      { hi: "నేను ఇక్కడ కొత్త.", roman: "Nenu ikkada kotta.", en: "I here new.", natural: "I'm new here." },
      { hi: "మిమ్మల్ని కలవడం సంతోషంగా ఉంది.", roman: "Mimmalni kalavadam santoshamga undi.", en: "Meeting you, it is happily.", natural: "Lovely to meet you." },
      { hi: "చాలా ధన్యవాదాలు!", roman: "Chaala dhanyavaadaalu!", en: "Many thanks!", natural: "Thank you so much!" },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Take autos and the Hyderabad Metro.",
    situation: "You've arrived at Secunderabad station and need to get to Banjara Hills.", scenario: "hyd_auto",
    tip: "Hyderabad autos should go by the meter, but many drivers quote a fare instead: ask for the meter, agree the fare first, or book an app ride. The metro has three lines: Red (Miyapur–LB Nagar), Blue (Nagole–Raidurg) and Green (JBS Parade Ground–MGBS).",
    phrases: [
      { hi: "బంజారా హిల్స్ వస్తారా?", roman: "Banjara Hills vastaaraa?", en: "Banjara Hills, will you come?", natural: "Will you go to Banjara Hills?" },
      { hi: "మీటర్ వేయండి.", roman: "Meter veyandi.", en: "The meter please put.", natural: "Please use the meter." },
      { hi: "ఎంత అవుతుంది?", roman: "Entha avutundi?", en: "How much will it become?", natural: "How much will it cost?" },
      { hi: "మెట్రో స్టేషన్ ఎక్కడ?", roman: "Metro station ekkada?", en: "Metro station where?", natural: "Where's the metro station?" },
      { hi: "ఇక్కడ ఆపండి.", roman: "Ikkada aapandi.", en: "Here please stop.", natural: "Stop here, please." },
    ] },
  { day: 3, key: "food", icon: "🍛", title: "Food", desc: "Order Hyderabadi biryani and an Irani chai.",
    situation: "Lunch at an Irani café in the old city.", scenario: "hyd_food",
    tip: "Hyderabad means biryani, haleem in Ramzan, and Irani chai with Osmania biscuits. Food can be fiery: “kaaram takkuva” means less chilli. “Manchi neellu” is drinking water.",
    phrases: [
      { hi: "ఒక ప్లేట్ బిర్యానీ ఇవ్వండి.", roman: "Oka plate biryani ivvandi.", en: "One plate biryani please give.", natural: "One plate of biryani, please." },
      { hi: "కారం తక్కువ వేయండి.", roman: "Kaaram takkuva veyandi.", en: "Chilli less please put.", natural: "Not too spicy, please." },
      { hi: "ఒక ఇరానీ చాయ్.", roman: "Oka Irani chai.", en: "One Irani tea.", natural: "One Irani chai, please." },
      { hi: "మంచి నీళ్ళు ఇవ్వండి.", roman: "Manchi neellu ivvandi.", en: "Good water please give.", natural: "Some drinking water, please." },
      { hi: "బిల్ ఎంత అయింది?", roman: "Bill entha ayindi?", en: "Bill how much did it become?", natural: "How much is the bill?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain for bangles in Laad Bazaar.",
    situation: "You're in Laad Bazaar, near the Charminar, looking for bangles.", scenario: "hyd_shopping",
    tip: "Laad Bazaar, by the Charminar, is famous for lac bangles; Hyderabad is also the city of pearls. Start at about half the first price and settle in between. Shops with price tags don't bargain.",
    phrases: [
      { hi: "ఇది ఎంత?", roman: "Idi entha?", en: "This how much?", natural: "How much is this?" },
      { hi: "చాలా ఎక్కువ.", roman: "Chaala ekkuva.", en: "Very much.", natural: "That's too much." },
      { hi: "కొంచెం తగ్గించండి.", roman: "Konchem thagginchandi.", en: "A little please reduce.", natural: "Can you lower it a bit?" },
      { hi: "వేరే రంగు ఉందా?", roman: "Vere rangu undaa?", en: "Another colour, is there?", natural: "Do you have another colour?" },
      { hi: "సరే, ప్యాక్ చేయండి.", roman: "Sare, pack cheyandi.", en: "Okay, please pack.", natural: "Okay, pack it up." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way round the old city.",
    situation: "You're by the Charminar and want Chowmahalla Palace.", scenario: "hyd_directions",
    tip: "The Charminar is the landmark of the old city: people give directions from it. “Kudi” is right, “edama” is left and “neruga” is straight on.",
    phrases: [
      { hi: "చౌమహల్లా ప్యాలెస్ ఎక్కడ?", roman: "Chowmahalla Palace ekkada?", en: "Chowmahalla Palace where?", natural: "Where's Chowmahalla Palace?" },
      { hi: "నేరుగా వెళ్ళి, కుడి వైపు తిరగండి.", roman: "Neruga velli, kudi vaipu tiragandi.", en: "Having gone straight, to the right side turn.", natural: "Go straight, then turn right." },
      { hi: "నడిచి వెళ్తే ఎంత సేపు?", roman: "Nadichi velthe entha sepu?", en: "If going walking, how much time?", natural: "How long is it on foot?" },
      { hi: "దగ్గరలో మెడికల్ షాప్ ఉందా?", roman: "Daggaralo medical shop undaa?", en: "Nearby a medical shop, is there?", natural: "Is there a pharmacy nearby?" },
      { hi: "కొంచెం నెమ్మదిగా చెప్పండి.", roman: "Konchem nemmadiga cheppandi.", en: "A little slowly please say.", natural: "Could you speak a bit more slowly?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in with colleagues and classmates.",
    situation: "Your first day at an office in HITEC City.", scenario: "hyd_college",
    tip: "Offices in HITEC City and Gachibowli mix Telugu, Hindi and English. Use “meeru” and -andi with colleagues you've just met. Lunch together is how friendships start.",
    phrases: [
      { hi: "ఈ రోజు నా మొదటి రోజు.", roman: "Ee roju naa modati roju.", en: "This day my first day.", natural: "It's my first day today." },
      { hi: "మీటింగ్ ఎన్ని గంటలకు?", roman: "Meeting enni gantalaku?", en: "Meeting at how many hours?", natural: "What time is the meeting?" },
      { hi: "కొంచెం సహాయం చేస్తారా?", roman: "Konchem sahaayam chestaaraa?", en: "A little help will you do?", natural: "Could you help me a bit?" },
      { hi: "క్యాంటీన్ ఎక్కడ ఉంది?", roman: "Canteen ekkada undi?", en: "Canteen where is it?", natural: "Where's the canteen?" },
      { hi: "మళ్ళీ కలుద్దాం!", roman: "Malli kaluddaam!", en: "Again let's meet!", natural: "See you later!" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "Sunset on Tank Bund, by Hussain Sagar, with Ravi, your flatmate.", scenario: "hyd_smalltalk",
    tip: "With friends Telugu uses “nuvvu” (you) and short forms. “Super!” and “pakka!” (for sure) are everywhere, and so is Hyderabadi Hindi: “kya re?”, “hau” (yes), “nakko” (don't).",
    phrases: [
      { hi: "హైదరాబాద్ వాతావరణం బాగుంది కదా?", roman: "Hyderabad vaatavaranam baagundi kadaa?", en: "Hyderabad weather is good, isn't it?", natural: "Hyderabad's weather is lovely, isn't it?" },
      { hi: "ట్రాఫిక్ చాలా ఎక్కువ.", roman: "Traffic chaala ekkuva.", en: "Traffic very much.", natural: "The traffic is terrible." },
      { hi: "నువ్వు ఇక్కడే పుట్టావా?", roman: "Nuvvu ikkade puttaavaa?", en: "You, were you born right here?", natural: "Were you born here?" },
      { hi: "ఆదివారం గోల్కొండ కోటకి వెళ్దామా?", roman: "Aadivaaram Golconda kotaki veldaamaa?", en: "Sunday to Golconda fort shall we go?", natural: "Fancy Golconda Fort on Sunday?" },
      { hi: "సూపర్, పక్కా!", roman: "Super, pakka!", en: "Super, for sure!", natural: "Brilliant, it's a plan!" },
    ] },
];

Object.assign(window.SCENARIOS, {
  hyd_greetings: { category: "greetings", icon: "🏠", title: "Meet your house owner", partner: "Lakshmi garu", role: "House owner", place: "Your rented flat in Madhapur",
    goal: "Greet politely, introduce yourself and ask when the water comes.",
    opening: { text: "Randi, randi! Meere Alex aa? Nenu Lakshmi, ee illu maadi.", en: "Come in, come in! Are you Alex? I'm Lakshmi, this is our house." },
    start: ["Namaskaram! Baagunnaara?", "Avunu, naa peru Alex.", "Neellu eppudu vastaayi?"],
    rules: [
      { m: ["dhanyavaadaalu", "thanks", "thank", "kaluddaam", "ardham"], text: "Emaina kaavaalante cheppandi. 🙏", en: "Tell me if you need anything.", s: ["Malli kaluddaam!"], end: true, hint: "Chaala dhanyavaadaalu!" },
      { m: ["neellu", "eppudu", "current"], text: "Neellu podduna, saayantram vastaayi. Current pothe inverter undi.", en: "Water comes in the morning and the evening. If the power goes, there's an inverter.", s: ["Sare, ardham ayyindi.", "Chaala dhanyavaadaalu!"], hint: "Neellu eppudu vastaayi?" },
      { m: ["kalavadam", "santosham"], text: "Naaku kooda santoshamga undi. Hyderabad ki modatisaari aa?", en: "I'm happy too. First time in Hyderabad?", s: ["Avunu, modatisaari.", "Neellu eppudu vastaayi?"], hint: "Mimmalni kalavadam santoshamga undi." },
      { m: ["modatisaari", "kotta", "new"], text: "Ayite Hyderabad biryani, Irani chai, rendu try cheyandi!", en: "Then try both the Hyderabad biryani and the Irani chai!", s: ["Neellu eppudu vastaayi?", "Chaala dhanyavaadaalu!"], hint: "Avunu, modatisaari." },
      { m: ["peru", "alex", "name"], text: "Manchi peru! Hyderabad ki modatisaari aa?", en: "Nice name! First time in Hyderabad?", s: ["Avunu, modatisaari.", "Mimmalni kalavadam santoshamga undi."], hint: "Avunu, naa peru Alex." },
      { m: ["namaskaram", "namaste", "baagunnaara", "hello", " hi "], text: "Baagunnaanu! Mee peru enti?", en: "I'm well! What's your name?", s: ["Avunu, naa peru Alex.", "Mimmalni kalavadam santoshamga undi."], hint: "Namaskaram! Baagunnaara?" },
    ],
    fallback: { text: "Cheppandi, emi kaavaali? Neellu, current, Wi-Fi?", en: "Tell me, what do you need? Water, power, the Wi-Fi?", s: ["Neellu eppudu vastaayi?", "Chaala dhanyavaadaalu!"] } },

  hyd_auto: { category: "transport", icon: "🛺", title: "Auto to Banjara Hills", partner: "Srinu", role: "Auto driver", place: "Outside Secunderabad railway station",
    goal: "Get to Banjara Hills for a fair fare.", places: ["Banjara Hills", "Jubilee Hills", "Charminar", "HITEC City", "Ameerpet", "Airport", "Madhapur", "Koti", "Gachibowli"],
    opening: { text: "Ekkadiki vellaali?", en: "Where do you need to go?" },
    start: ["Banjara Hills vastaaraa?", "Meter veyandi.", "Entha avutundi?"],
    rules: [
      { m: ["dhanyavaadaalu", "thanks", "thank", "upi", "kaluddaam"], text: "Thanks andi! Jaagrattaga vellandi. 🙏", en: "Thank you! Go carefully.", s: ["Malli kaluddaam!"], end: true, hint: "Chaala dhanyavaadaalu!" },
      { m: ["aapandi", "ikkada", "stop"], text: "Vacchesaam, Banjara Hills! Nooru yaabhai.", en: "Here we are, Banjara Hills! A hundred and fifty.", s: ["UPI ok aa?", "Chaala dhanyavaadaalu!"], hint: "Ikkada aapandi." },
      { m: ["nooru ki", "100"], text: "Sare, nooru ki padandi. Ekkandi.", en: "All right, a hundred it is. Get in.", s: ["Entha sepu padutundi?", "Ikkada aapandi."], hint: "Nooru ki vastaaraa?" },
      // before the meter rule: "meter meeda ekkuva" (over the meter) contains "meter"
      { m: ["ekkuva", "extra", "paina"], text: "Sare, meter meedane vastaanu.", en: "All right, I'll go by the meter.", s: ["Sare, padandi.", "Entha sepu padutundi?"], hint: "Vaddu, meter meeda ekkuva ivvanu." },
      { m: ["meter"], text: "Meter vestaanu, kaani meter meeda iravai ivvandi. Traffic undi.", en: "I'll put the meter on, but give twenty over it. There's traffic.", s: ["Vaddu, meter meeda ekkuva ivvanu.", "Sare, padandi."], hint: "Meter veyandi." },
      // before the price rule: "entha sepu" (how long) contains "entha" (how much)
      { m: ["sepu", "nimishaalu", "time"], text: "Traffic unte iravai nimishaalu.", en: "Twenty minutes if there's traffic.", s: ["Sare, padandi.", "Ikkada aapandi."], hint: "Entha sepu padutundi?" },
      { m: ["entha", "rate", "dabbulu", "price"], text: "Banjara Hills aa? Nooru yaabhai avutundi.", en: "Banjara Hills? It'll be a hundred and fifty.", s: ["Meter veyandi.", "Nooru ki vastaaraa?"], hint: "Entha avutundi?" },
      { m: ["metro"], text: "Metro kaavaalante Parade Ground station daggare.", en: "If you want the metro, Parade Ground station is close by.", s: ["Vaddu, auto lone veldaam.", "Entha avutundi?"], hint: "Metro station ekkada?" },
      { m: ["banjara hills", "jubilee hills", "charminar", "hitec city", "ameerpet", "airport", "madhapur", "koti", "gachibowli", "vastaaraa", "vellaali"], text: "{place}? Sare, ekkandi.", en: "{place}? Sure, get in.", s: ["Meter veyandi.", "Entha avutundi?"], hint: "{place} vastaaraa?" },
      { m: ["modatisaari", "kotta", "new"], text: "Hyderabad ki swaagatam! Charminar tappakunda chudandi.", en: "Welcome to Hyderabad! Don't miss the Charminar.", s: ["Entha sepu padutundi?", "Ikkada aapandi."] },
      { m: ["sare", "padandi", "auto", "avunu"], text: "Ekkandi! Hyderabad ki modatisaari aa?", en: "Get in! First time in Hyderabad?", s: ["Avunu, modatisaari.", "Entha sepu padutundi?"] },
    ],
    fallback: { text: "Ardham kaaledu. Ekkadiki vellaali?", en: "I didn't get that. Where to?", s: ["Banjara Hills vastaaraa?", "Entha avutundi?"] } },

  hyd_food: { category: "food", icon: "🍛", title: "Biryani in the old city", partner: "Raju", role: "Waiter", place: "An Irani café in the old city",
    goal: "Order biryani and an Irani chai, ask for less chilli and pay.",
    opening: { text: "Randi, emi kaavaali?", en: "Come in, what would you like?" },
    start: ["Oka plate biryani ivvandi.", "Kaaram takkuva veyandi.", "Bill entha ayindi?"],
    rules: [
      { m: ["dhanyavaadaalu", "thanks", "thank", "upi", "teesukondi", "kaluddaam"], text: "Thanks andi! Malli randi. 🙏", en: "Thank you! Come again.", s: ["Malli kaluddaam!"], end: true, hint: "Idigo, teesukondi." },
      { m: ["bill", "entha", "dabbulu"], text: "Biryani, chai, rendu kalipi rendu vandala yaabhai.", en: "Biryani and chai together: two hundred and fifty.", s: ["UPI ok aa?", "Idigo, teesukondi."], hint: "Bill entha ayindi?" },
      { m: ["kaaram", "karam", "spicy"], text: "Sare, kaaram takkuva.", en: "Okay, less chilli.", s: ["Oka Irani chai.", "Bill entha ayindi?"], hint: "Kaaram takkuva veyandi." },
      { m: ["neellu", "water"], text: "Idigo, manchi neellu.", en: "Here's some drinking water.", s: ["Bill entha ayindi?", "Oka Irani chai."], hint: "Manchi neellu ivvandi." },
      { m: ["chai", "osmania", "biscuit"], text: "Oka Irani chai, Osmania biscuits tho! Inkaa emaina?", en: "One Irani chai, with Osmania biscuits! Anything else?", s: ["Bill entha ayindi?", "Manchi neellu ivvandi."], hint: "Oka Irani chai." },
      { m: ["biryani", "plate", "haleem", "mutton", "chicken", "veg"], text: "Vedi vedi biryani! Chicken aa, mutton aa, veg aa?", en: "Piping-hot biryani! Chicken, mutton or veg?", s: ["Chicken biryani.", "Kaaram takkuva veyandi."], hint: "Oka plate biryani ivvandi." },
    ],
    fallback: { text: "Biryani, haleem, Irani chai... emi kaavaali?", en: "Biryani, haleem, Irani chai... what would you like?", s: ["Oka plate biryani ivvandi.", "Oka Irani chai."] } },

  hyd_shopping: { category: "shopping", icon: "🛍️", title: "Bangles in Laad Bazaar", partner: "Farida", role: "Shopkeeper", place: "A bangle shop in Laad Bazaar, near the Charminar",
    goal: "Buy a set of lac bangles at a fair price.",
    opening: { text: "Randi, chudandi! Gaajulu, mutyaalu, anni unnaayi.", en: "Come in, take a look! Bangles, pearls, we have it all." },
    start: ["Idi entha?", "Vere rangu undaa?", "Chaala ekkuva."],
    rules: [
      { m: ["pack", "dhanyavaadaalu", "upi", "kaluddaam"], text: "Pack chesaanu! Malli randi. 🙏", en: "Packed! Come again.", s: ["Malli kaluddaam!"], end: true, hint: "Sare, pack cheyandi." },
      { m: ["naalugu vandalu", "aidu vandalu", "400", "500"], text: "Sare, meeku aaru vandalu. Inka taggadu.", en: "All right, six hundred for you. It won't go lower.", s: ["Sare, pack cheyandi.", "UPI ok aa?"], hint: "Aidu vandalu ki istaaraa?" },
      { m: ["ekkuva", "thagginchandi", "last"], text: "Chetitho chesindi! Sare, enimidi vandalu.", en: "It's handmade! All right, eight hundred.", s: ["Aidu vandalu ki istaaraa?", "Konchem thagginchandi."], hint: "Konchem thagginchandi." },
      { m: ["rangu", "colour", "color", "erupu", "neelam"], text: "Undi, erupu, neelam kooda unnaayi.", en: "Yes, there's red and blue too.", s: ["Idi entha?", "Neelam choopinchandi."], hint: "Vere rangu undaa?" },
      { m: ["entha", "price", "rate"], text: "Ee set aa? Veyyi rupaayalu.", en: "This set? A thousand rupees.", s: ["Chaala ekkuva.", "Konchem thagginchandi."], hint: "Idi entha?" },
      { m: ["lakk", "lac", "chetitho", "mutyaalu", "pearl"], text: "Avunu, ivi lakk gaajulu, ikkade chestaaru.", en: "Yes, these are lac bangles, made right here.", s: ["Idi entha?", "Vere rangu undaa?"], hint: "Ivi lakk gaajulaa?" },
    ],
    fallback: { text: "Nemmadiga chudandi. Gaajulu, mutyaalu, anni unnaayi.", en: "Take your time. Bangles, pearls, we have it all.", s: ["Idi entha?", "Vere rangu undaa?"] } },

  hyd_directions: { category: "directions", icon: "🕌", title: "Find Chowmahalla Palace", partner: "Venkat", role: "Passerby", place: "By the Charminar",
    goal: "Find the way to Chowmahalla Palace, and a pharmacy.",
    opening: { text: "Emaina vetukutunnaaraa?", en: "Looking for something?" },
    start: ["Chowmahalla Palace ekkada?", "Daggaralo medical shop undaa?", "Nadichi velthe entha sepu?"],
    rules: [
      { m: ["dhanyavaadaalu", "thanks", "thank", "ardham", "kaluddaam"], text: "Parledu! Baaga tirigi randi. 🙏", en: "No problem! Enjoy your walk.", s: ["Malli kaluddaam!"], end: true, hint: "Chaala dhanyavaadaalu!" },
      { m: ["nemmadiga", "malli cheppandi", "slow"], text: "Neruga velli, kudi vaipu. Antey!", en: "Straight on, then right. That's it!", s: ["Sare, ardham ayyindi.", "Nadichi velthe entha sepu?"], hint: "Konchem nemmadiga cheppandi." },
      { m: ["medical", "pharmacy", "mandula", "hospital"], text: "Undi, Charminar pakkane oka medical shop undi.", en: "Yes, there's a pharmacy right by the Charminar.", s: ["Chowmahalla Palace ekkada?", "Konchem nemmadiga cheppandi."], hint: "Daggaralo medical shop undaa?" },
      { m: ["nadichi", "sepu", "dooram", "walk"], text: "Nadichi padi nimishaalu.", en: "About ten minutes on foot.", s: ["Sare, ardham ayyindi.", "Chaala dhanyavaadaalu!"], hint: "Nadichi velthe entha sepu?" },
      { m: ["chowmahalla", "palace", "ekkada"], text: "Neruga velli, kudi vaipu tiragandi. Mundu Chowmahalla Palace kanipistundi.", en: "Go straight, then turn right. You'll see Chowmahalla Palace ahead.", s: ["Nadichi velthe entha sepu?", "Konchem nemmadiga cheppandi."], hint: "Chowmahalla Palace ekkada?" },
    ],
    fallback: { text: "Cheppandi, ekkadiki vellaali?", en: "Tell me, where do you need to go?", s: ["Chowmahalla Palace ekkada?", "Daggaralo medical shop undaa?"] } },

  hyd_college: { category: "college", icon: "💼", title: "First day in HITEC City", partner: "Sneha", role: "Colleague", place: "An office in HITEC City",
    goal: "Introduce yourself and find out about the meeting and the canteen.",
    opening: { text: "Hi! Meeru kotta joinee aa? Nenu Sneha, same team.", en: "Hi! Are you the new joiner? I'm Sneha, same team." },
    start: ["Avunu, ee roju naa modati roju.", "Meeting enni gantalaku?", "Canteen ekkada undi?"],
    rules: [
      { m: ["kaluddaam", "bye", "thank", "dhanyavaadaalu", "super"], text: "Welcome! Emaina kaavaalante cheppandi. 👋", en: "Welcome! Tell me if you need anything.", s: ["Malli kaluddaam!"], end: true, hint: "Thanks, Sneha!" },
      { m: ["canteen", "lunch", "bhojanam", "chai"], text: "Canteen ground floor lo undi. Lunch ki kalisi veldaam!", en: "The canteen's on the ground floor. Let's go for lunch together!", s: ["Super!", "Thanks, Sneha!"], hint: "Canteen ekkada undi?" },
      { m: ["sahaayam", "help"], text: "Tappakunda! Laptop setup lo help chestaanu.", en: "Of course! I'll help you set up your laptop.", s: ["Canteen ekkada undi?", "Thanks, Sneha!"], hint: "Konchem sahaayam chestaaraa?" },
      { m: ["meeting", "gantalaku", "time"], text: "Team meeting padi gantalaku.", en: "The team meeting is at ten.", s: ["Konchem sahaayam chestaaraa?", "Canteen ekkada undi?"], hint: "Meeting enni gantalaku?" },
      { m: ["modati", "avunu", "first"], text: "Welcome! Modati roju konchem confusing gaa untundi.", en: "Welcome! The first day is a bit confusing.", s: ["Meeting enni gantalaku?", "Konchem sahaayam chestaaraa?"], hint: "Ee roju naa modati roju." },
    ],
    fallback: { text: "Cheppandi, emi kaavaali? Meeting, canteen, laptop?", en: "Tell me, what do you need? The meeting, the canteen, your laptop?", s: ["Meeting enni gantalaku?", "Canteen ekkada undi?"] } },

  hyd_smalltalk: { category: "smalltalk", icon: "🌇", title: "Sunset on Tank Bund", partner: "Ravi", role: "Flatmate", place: "Tank Bund, by Hussain Sagar, at sunset",
    goal: "Chat about Hyderabad and plan a trip to Golconda Fort.",
    opening: { text: "Ela undi Hyderabad?", en: "How's Hyderabad treating you?" },
    start: ["Hyderabad vaatavaranam baagundi kadaa?", "Traffic chaala ekkuva.", "Nuvvu ikkade puttaavaa?"],
    rules: [
      { m: ["pakka", "bye", "super", "kaluddaam"], text: "Pakka! Aadivaaram podduna Golconda ki veldaam. 👋", en: "Deal! Golconda on Sunday morning.", s: ["Bye, Ravi!"], end: true, hint: "Super, pakka!" },
      { m: ["gantalaku", "podduna"], text: "Podduna enimidi gantalaku, endaku mundu.", en: "Eight in the morning, before the heat.", s: ["Super, pakka!"], hint: "Enni gantalaku?" },
      { m: ["golconda", "aadivaaram", "sunday", "kota", "plan"], text: "Avunu! Aadivaaram Golconda kota, saayantram light show.", en: "Yes! Golconda Fort on Sunday, then the light show in the evening.", s: ["Super, pakka!", "Enni gantalaku?"], hint: "Aadivaaram Golconda kotaki veldaamaa?" },
      { m: ["puttaavaa", "ikkade", "born"], text: "Avunu, nenu ikkade, Secunderabad lo puttaanu!", en: "Yes, I was born right here, in Secunderabad!", s: ["Aadivaaram Golconda kotaki veldaamaa?", "Traffic chaala ekkuva."], hint: "Nuvvu ikkade puttaavaa?" },
      { m: ["traffic", "ekkuva"], text: "Avunu, kaani metro lo ayite tondaragaa vellochu.", en: "Yes, but by metro you get there quickly.", s: ["Nuvvu ikkade puttaavaa?", "Aadivaaram Golconda kotaki veldaamaa?"], hint: "Traffic chaala ekkuva." },
      { m: ["vaatavaranam", "weather", "baagundi", "varsham"], text: "Avunu, saayantram Hussain Sagar daggara challaga untundi.", en: "Yes, evenings by Hussain Sagar are cool.", s: ["Traffic chaala ekkuva.", "Nuvvu ikkade puttaavaa?"], hint: "Hyderabad vaatavaranam baagundi kadaa?" },
    ],
    fallback: { text: "Haha, nijame! Hyderabad lo neeku emi baaga nachindi?", en: "Haha, true! What do you like most about Hyderabad?", s: ["Hyderabad vaatavaranam baagundi kadaa?", "Traffic chaala ekkuva."] } },
});

window.CONTENT_REVIEW.hyderabad = {
  te: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
    known_limitations: ["The content teaches spoken Hyderabad Telugu, which differs from written Telugu.", "Romanised Telugu has no fixed spelling: long vowels are written double (aa, ee, oo) and the retroflex sounds are not marked.", "Fares and practical tips change over time."],
    note: "Hyderabad Telugu: AI-assisted editorial review only, not yet checked by a native Telugu speaker." },
};

const PLACE_HYD = {
  "banjara hills": ["Banjara Hills", "బంజారా హిల్స్", "Banjara Hills"], "jubilee hills": ["Jubilee Hills", "జూబ్లీ హిల్స్", "Jubilee Hills"], charminar: ["Charminar", "చార్మినార్", "the Charminar"],
  "hitec city": ["HITEC City", "హైటెక్ సిటీ", "HITEC City"], ameerpet: ["Ameerpet", "అమీర్‌పేట్", "Ameerpet"], airport: ["Airport", "ఎయిర్‌పోర్ట్", "the airport"],
  madhapur: ["Madhapur", "మాదాపూర్", "Madhapur"], koti: ["Koti", "కోఠి", "Koti"], gachibowli: ["Gachibowli", "గచ్చిబౌలి", "Gachibowli"], secunderabad: ["Secunderabad", "సికింద్రాబాద్", "Secunderabad"],
};
const HYDERABAD_PLACES = ["Banjara Hills", "Jubilee Hills", "Charminar", "HITEC City", "Ameerpet", "Airport", "Madhapur", "Koti", "Gachibowli", "Secunderabad"];
const HYD_RIDE_NOTE = "Hyderabad's autos should go by the meter, but many drivers quote their own fare: ask for the meter, agree on the fare before you sit in, or book through an app.";
const HYD_METRO_NOTE = "Hyderabad Metro: the Red Line runs from Miyapur to LB Nagar, the Blue Line from Nagole to Raidurg (for HITEC City) and the Green Line from JBS Parade Ground to MGBS; change at Ameerpet, MGBS or Parade Ground. Fares are ₹11–69 (from 24 May 2025).";
const teP = (hi, roman, en, extra) => ({ hi, roman, en, ...(extra || {}) });

window.LOCAL_CONTENT.hyderabad = {
  // ---------- Hyderabad, in Telugu (and the English view) ----------
  te: {
    tutor: {
      greet: "Namaskaram", places: HYDERABAD_PLACES, defaultPlace: "Banjara Hills", language: "Telugu",
      starters: ["I need a ride to Banjara Hills.", "How do I order biryani, not too spicy?", "How do I bargain in Laad Bazaar?", "What does 'garu' mean?", "Which metro line goes to HITEC City?"],
      glossaryOnly: true,                                // Hindi words are not Telugu: the shared (Hindi) glossary is not used
      glossary: {
        namaskaram: "A respectful hello (and goodbye). Works with anyone, any time.", garu: "Added after a name to show respect: “Lakshmi garu”.",
        andi: "Softens what you say and makes it polite: “avunandi” (yes), “ledandi” (no).", entha: "“How much.” Idi entha? = How much is this?",
        ekkada: "Where. Metro station ekkada? = Where's the metro station?", avunu: "Yes.", ledu: "No / there isn't.", sare: "“Okay / all right.”",
        kaavaali: "“Want / need.” Emi kaavaali? = What do you need?", vaddu: "“Don't want / no thanks.”", ivvandi: "“Please give.” The polite form of “ivvu”.",
        kaaram: "“Chilli-hot.” Kaaram takkuva = less spicy.", baagundi: "“It's good / nice.”", pakka: "“For sure!” With friends.",
        dhanyavaadaalu: "Thank you.", randi: "“Come (in)!” What hosts and shopkeepers say.", "irani chai": "Strong, milky tea from Hyderabad's Irani cafés, with Osmania biscuits.",
      },
      polite: { intro: "Telugu's polite forms use “meeru” and requests ending in -andi (“ivvandi”, “cheppandi”, “cheyandi”):", rules: [["\\bivvu\\b", "ivvandi"], ["\\bcheppu\\b", "cheppandi"], ["\\bchey\\b", "cheyandi"], ["\\bnuvvu\\b", "meeru"]],
        note: "e.g. “ivvu” → “ivvandi”, “cheppu” → “cheppandi”, “nuvvu” → “meeru”. With friends the short forms are fine." },
      intents: [
        { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
          build: (dest) => { const d = PLACE_HYD[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
            teP(d ? `${d[1]} కి వస్తారా? మీటర్ వేయండి.` : "", `${r} ki vastaaraa? Meter veyandi.`, `Will you go to ${d ? d[2] : dest}? Please use the meter.`),
            teP(d ? `దయచేసి ${d[1]} కి వస్తారా?` : "", `Dayachesi ${r} ki vastaaraa?`, `A more polite version: Would you please take me to ${d ? d[2] : dest}?`, { label: "More polite" }),
            teP("మీటర్ వేయండి.", "Meter veyandi.", "Please use the meter."),
          ], note: HYD_RIDE_NOTE }; } },
        { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
            teP("హైటెక్ సిటీకి ఏ లైన్?", "HITEC City ki ee line?", "Which line for HITEC City?"), teP("ఈ మెట్రో అమీర్‌పేట్ వెళ్తుందా?", "Ee metro Ameerpet veltundaa?", "Does this metro go to Ameerpet?"),
            teP("టికెట్ ఎక్కడ దొరుకుతుంది?", "Ticket ekkada dorukutundi?", "Where do I get a ticket?"),
          ], note: HYD_METRO_NOTE },
        { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
            teP("కొంచెం తగ్గించండి.", "Konchem thagginchandi.", "Please lower it a little."), teP("చాలా ఎక్కువ.", "Chaala ekkuva.", "That's too much."),
            teP("చివరి ధర ఎంత?", "Chivari dhara entha?", "What's your best price?"),
          ], note: "In Laad Bazaar and the old city's markets start at about half the first price and settle in between." },
        { m: ["price", "how much", "cost", "entha", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
            teP("ఇది ఎంత?", "Idi entha?", "How much is this?"), teP("యూపీఐ ఓకేనా?", "UPI okenaa?", "Can I pay by UPI?"),
          ] },
        { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "biryani", "chai", "bill"], topic: "food", intro: "Ordering food:", phrases: [
            teP("ఒక ప్లేట్ బిర్యానీ ఇవ్వండి.", "Oka plate biryani ivvandi.", "One plate of biryani, please."), teP("కారం తక్కువ వేయండి.", "Kaaram takkuva veyandi.", "Not too spicy, please."),
            teP("బిల్ ఇవ్వండి.", "Bill ivvandi.", "Could I have the bill, please?"),
          ], note: "“Ivvandi” is the polite “please give”. Finish with an Irani chai and Osmania biscuits." },
        { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
            teP("చార్మినార్ ఎక్కడ?", "Charminar ekkada?", "Where's the Charminar?"), teP("నాకు దారి తప్పింది.", "Naaku daari tappindi.", "I'm lost."),
            teP("దగ్గరలో మెట్రో స్టేషన్ ఏది?", "Daggaralo metro station edi?", "Which is the nearest metro station?"),
          ], note: "“Kudi” is right, “edama” is left and “neruga” is straight on. In the old city, give directions from the Charminar." },
        { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At work or college:", phrases: [
            teP("ఈ రోజు నా మొదటి రోజు.", "Ee roju naa modati roju.", "It's my first day today."), teP("మీటింగ్ ఎన్ని గంటలకు?", "Meeting enni gantalaku?", "What time's the meeting?"),
            teP("కొంచెం సహాయం చేస్తారా?", "Konchem sahaayam chestaaraa?", "Could you help me a bit?"),
          ] },
        { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
            teP("మీది ఏ ఊరు?", "Meedi ee ooru?", "Where are you from?"), teP("ఈ రోజు చాలా ఎండగా ఉంది కదా?", "Ee roju chaala endagaa undi kadaa?", "It's really hot today, isn't it?"),
            teP("చాయ్ తాగుదామా?", "Chai taagudaamaa?", "Shall we have a chai?"),
          ], note: "Hyderabad small talk: biryani, cricket, the traffic and films. With friends, Hyderabadi Hindi slips in: “kya re?”." },
        { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
            teP("నా పేరు అలెక్స్.", "Naa peru Alex.", "My name is Alex."), teP("మీ పేరు ఏంటి?", "Mee peru enti?", "What's your name?"),
            teP("మిమ్మల్ని కలవడం సంతోషంగా ఉంది.", "Mimmalni kalavadam santoshamga undi.", "Lovely to meet you."),
          ] },
        { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
            teP("చాలా ధన్యవాదాలు!", "Chaala dhanyavaadaalu!", "Thanks a lot!"), teP("క్షమించండి.", "Kshaminchandi.", "Sorry / Excuse me."), teP("ఏమండీ…", "Emandi…", "Excuse me… (to get attention)"),
          ] },
        { m: ["hello", "hi", "greet", "namaste", "namaskaram", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Hyderabad:", phrases: [
            teP("నమస్కారం! బాగున్నారా?", "Namaskaram! Baagunnaara?", "Hello! How are you?"), teP("మళ్ళీ కలుద్దాం!", "Malli kaluddaam!", "See you later!"),
          ], note: "“Namaskaram” works with everyone; in the old city “Assalaam alaikum” and “Adaab” are just as common." },
        { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
            teP("నాకు సహాయం కావాలి.", "Naaku sahaayam kaavaali.", "I need help."), teP("దగ్గరలో హాస్పిటల్ ఎక్కడ?", "Daggaralo hospital ekkada?", "Where's the nearest hospital?"),
          ], note: "Emergency number in India: 112." },
      ],
      generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
          teP("నమస్కారం! బాగున్నారా?", "Namaskaram! Baagunnaara?", "Hello! How are you?"), teP("ఇది ఎంత?", "Idi entha?", "How much is this?"),
          teP("కొంచెం సహాయం చేస్తారా?", "Konchem sahaayam chestaaraa?", "Could you help me a bit?"),
        ], note: "Tell me a situation — like “I want to order biryani” or “ask the way to the Charminar” — and I'll give you the exact Telugu words." },
    },
    readings: [
      { title: "Asha in Hyderabad", level: "A1", lines: [
          teP("ఆశ హైదరాబాద్‌కి కొత్త.", "Aasha Hyderabad ki kotta.", "Asha is new to Hyderabad."), teP("ఆమె మెట్రోలో అమీర్‌పేట్ వెళ్తుంది.", "Aame metro lo Ameerpet veltundi.", "She takes the metro to Ameerpet."),
          teP("అక్కడ ఆమె బిర్యానీ తింటుంది.", "Akkada aame biryani tintundi.", "There she eats biryani."), teP("తర్వాత ఒక ఇరానీ చాయ్ తాగుతుంది.", "Tarvaata oka Irani chai taagutundi.", "Then she has an Irani chai."),
        ],
        questions: [
          { q: "Where is Asha new?", options: ["Chennai", "Hyderabad", "Kolkata"], a: 1 }, { q: "How does she travel?", options: ["By metro", "By bus", "By auto"], a: 0 },
          { q: "What does she drink?", options: ["Coffee", "Lassi", "Irani chai"], a: 2 },
        ] },
      { title: "Bangles in Laad Bazaar", level: "A1", lines: [
          teP("రవి లాడ్ బజార్‌కి వెళ్తాడు.", "Ravi Laad Bazaar ki veltaadu.", "Ravi goes to Laad Bazaar."), teP("అతనికి ఎర్రటి గాజులు నచ్చాయి.", "Ataniki errati gaajulu nachchaayi.", "He likes some red bangles."),
          teP("షాపు వాళ్ళు వెయ్యి రూపాయలు అడిగారు.", "Shaapu vaallu veyyi roopaayalu adigaaru.", "The shopkeeper asked for a thousand rupees."), teP("రవి ఆరు వందలకు కొన్నాడు.", "Ravi aaru vandalaku konnaadu.", "Ravi bought them for six hundred."),
        ],
        questions: [
          { q: "Where does Ravi go?", options: ["Laad Bazaar", "HITEC City", "Koti"], a: 0 }, { q: "What does he buy?", options: ["Bangles", "A book", "A shirt"], a: 0 },
          { q: "How much does he pay?", options: ["₹1000", "₹600", "₹60"], a: 1 },
        ] },
    ],
    placement: [
      { q: "What does “Namaskaram” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
      { q: "How would you ask an auto driver to use the meter?", options: ["Meter veyandi.", "Idi entha?", "Oka Irani chai.", "Malli kaluddaam!"], a: 0 },
      { q: "What does “entha avutundi” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
      { q: "“Neruga velli, kudi vaipu tiragandi” means…", options: ["Stop here", "Go straight, then turn right", "Turn left twice", "Wait for the bus"], a: 1 },
      { q: "Which is the polite way to ask for a plate of biryani?", options: ["Oka plate biryani ivvu", "Oka plate biryani ivvandi", "Biryani!", "Biryani ivvu ra"], a: 1 },
    ],
    achievements: {
      "first-words": ["🗣️", "First words", "Said your first Telugu phrase"], "auto-pro": ["🛺", "Meter pro", "Got an auto to use the meter"],
      foodie: ["🍛", "Biryani lover", "Ordered a Hyderabadi meal"], bargainer: ["🛍️", "Laad Bazaar bargainer", "Won a bargain"],
    },
    rightNow: [
      [5, 11, "☕", "Irani chai time", "Irani cafés are busiest in the morning. Order like a local.", "hyd_food", teP("ఒక ఇరానీ చాయ్.", "Oka Irani chai.", "One Irani chai, please.")],
      [11, 15, "🕌", "Sightseeing hours", "The Charminar and Chowmahalla Palace are open.", "hyd_directions", teP("చౌమహల్లా ప్యాలెస్ ఎక్కడ?", "Chowmahalla Palace ekkada?", "Where's Chowmahalla Palace?")],
      [15, 18, "🛍️", "Market hours", "Laad Bazaar is buzzing. Time to bargain.", "hyd_shopping", teP("కొంచెం తగ్గించండి.", "Konchem thagginchandi.", "Can you lower it a bit?")],
      [18, 22, "🌇", "Sunset on Tank Bund", "Evenings by Hussain Sagar are cool and lively.", "hyd_smalltalk", teP("హైదరాబాద్ వాతావరణం బాగుంది కదా?", "Hyderabad vaatavaranam baagundi kadaa?", "Hyderabad's weather is lovely, isn't it?")],
      [22, 29, "🌙", "Late night ride home", "Autos charge more at night. Agree on the fare first.", "hyd_auto", teP("మీటర్ వేయండి.", "Meter veyandi.", "Please use the meter.")],
    ],
    priceSay: (max, mid) => ({
      ticket: teP("అమీర్‌పేట్‌కి ఒక టికెట్ ఇవ్వండి.", "Ameerpet ki oka ticket ivvandi.", "One ticket to Ameerpet, please."), meter: teP("మీటర్ వేయండి.", "Meter veyandi.", "Please use the meter."),
      fair: teP("సరే, ఇవ్వండి.", "Sare, ivvandi.", "Okay, I'll take it."), counter: teP(`${max} కి ఇస్తారా?`, `${max} ki istaaraa?`, `Will you do it for ₹${max}?`),
      high: teP(`చాలా ఎక్కువ. ${mid} కి ఇస్తారా?`, `Chaala ekkuva. ${mid} ki istaaraa?`, `That's too much. Will you do ₹${mid}?`),
    }),
  },
};

// Hyderabad in Urdu: Hyderabad's second First Week pack, in Hyderabadi Urdu (Dakhini touches: "hau", "nakko", "kya re"), written in Urdu
// script (right to left) with a romanised line as learners type it. Urdu verbs change with the speaker's gender, so a gendered phrase shows
// its feminine form. AI-assisted editorial review only.
window.LANGUAGE_PACKS.hyderabad = { ur: [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet people the Hyderabadi way and introduce yourself in Urdu.",
    situation: "Your first evening in a rented flat in Tolichowki. Nawab sahab, your landlord, comes to welcome you.", scenario: "hyd_ur_greetings",
    tip: "Greet with “Assalaam alaikum” (answered “Walaikum assalaam”) or “Aadaab”. Hyderabadi Urdu has its own words: “hau” (yes), “nakko” (no, don't) and “kya re?” (what's up?), used with friends.",
    phrases: [
      { hi: "السلام علیکم! آپ کیسے ہیں؟", roman: "Assalaam alaikum! Aap kaise hain?", en: "Peace be upon you! How are you?", natural: "Hello! How are you?" },
      { hi: "میرا نام ایلکس ہے۔", roman: "Mera naam Alex hai.", en: "My name is Alex.", natural: "I'm Alex." },
      { hi: "میں یہاں نیا ہوں۔", roman: "Main yahan naya hoon.", en: "I am new here.", natural: "I'm new here.", fem: { hi: "میں یہاں نئی ہوں۔", roman: "Main yahan nayi hoon." } },
      { hi: "آپ سے مل کر بہت خوشی ہوئی۔", roman: "Aap se mil kar bahut khushi hui.", en: "Having met you, much happiness happened.", natural: "It's lovely to meet you." },
      { hi: "بہت شکریہ!", roman: "Bahut shukriya!", en: "Many thanks!", natural: "Thank you so much!" },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Take an auto by the meter, and the metro.",
    situation: "You're outside Nampally station and need to get to the Charminar.", scenario: "hyd_ur_auto",
    tip: "Ask for the meter before you get in (“meter se chalo”), or agree the fare first. In Hyderabad “idhar” and “udhar” (here, there) are everywhere: “bas, idhar roko” (just stop here).",
    phrases: [
      { hi: "چارمینار چلو گے؟", roman: "Charminar chaloge?", en: "Charminar, will you go?", natural: "Will you go to the Charminar?" },
      { hi: "میٹر سے چلو۔", roman: "Meter se chalo.", en: "Go by the meter.", natural: "Please go by the meter." },
      { hi: "کتنے پیسے ہوئے؟", roman: "Kitne paise hue?", en: "How much money did it become?", natural: "How much is it?" },
      { hi: "میٹرو اسٹیشن کدھر ہے؟", roman: "Metro station kidhar hai?", en: "Metro station is which way?", natural: "Which way is the metro station?" },
      { hi: "بس، ادھر روکو۔", roman: "Bas, idhar roko.", en: "Enough, stop here.", natural: "Just stop here, please." },
    ] },
  { day: 3, key: "food", icon: "🍛", title: "Food", desc: "Order biryani, Irani chai and Osmania biscuits.",
    situation: "Dinner at an Irani café near the Charminar.", scenario: "hyd_ur_food",
    tip: "In the old city, order biryani or, in Ramzan, haleem; finish with an Irani chai and Osmania biscuits. “Mirchi kam” is less chilli.",
    phrases: [
      { hi: "ایک پلیٹ بریانی دینا۔", roman: "Ek plate biryani dena.", en: "Give one plate of biryani.", natural: "One plate of biryani, please." },
      { hi: "مرچی کم ڈالو۔", roman: "Mirchi kam daalo.", en: "Put less chilli.", natural: "Not too spicy, please." },
      { hi: "دو ایرانی چائے اور عثمانیہ بسکٹ۔", roman: "Do Irani chai aur Osmania biscuit.", en: "Two Irani teas and Osmania biscuits.", natural: "Two Irani chais and some Osmania biscuits." },
      { hi: "تھوڑا پانی دینا۔", roman: "Thoda paani dena.", en: "Give a little water.", natural: "Some water, please." },
      { hi: "بل کتنا ہوا؟", roman: "Bill kitna hua?", en: "Bill how much did it become?", natural: "How much is the bill?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Buy pearls in the old city at a fair price.",
    situation: "You're at a pearl shop in Pathargatti, near the Charminar.", scenario: "hyd_ur_shopping",
    tip: "Hyderabad is the city of pearls: Pathargatti's shops sell them by the string. Ask “asli hain?” (are they real?), and bargain gently where there are no price tags.",
    phrases: [
      { hi: "یہ کتنے کا ہے؟", roman: "Ye kitne ka hai?", en: "This is of how much?", natural: "How much is this?" },
      { hi: "بہت زیادہ ہے۔", roman: "Bahut zyaada hai.", en: "It is very much.", natural: "That's too much." },
      { hi: "تھوڑا کم کرو نا۔", roman: "Thoda kam karo na.", en: "Make it a little less, no.", natural: "Can you lower it a bit?" },
      { hi: "اصلی موتی ہیں؟", roman: "Asli moti hain?", en: "Are they real pearls?", natural: "Are these real pearls?" },
      { hi: "ٹھیک ہے، پیک کر دو۔", roman: "Theek hai, pack kar do.", en: "Okay, pack it.", natural: "Okay, pack it up." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way round the old city, the Hyderabadi way.",
    situation: "You're by the Charminar and want the Mecca Masjid.", scenario: "hyd_ur_directions",
    tip: "Hyderabad says “seedhe haath” (right hand) and “ulte haath” (left hand) for right and left. “Seedha” is straight on.",
    phrases: [
      { hi: "مکہ مسجد کدھر ہے؟", roman: "Mecca Masjid kidhar hai?", en: "Mecca Masjid is which way?", natural: "Which way is the Mecca Masjid?" },
      { hi: "سیدھا جا کر سیدھے ہاتھ کو مڑو۔", roman: "Seedha jaa kar seedhe haath ko mudo.", en: "Going straight, turn to the right hand.", natural: "Go straight, then turn right." },
      { hi: "پیدل کتنا ٹائم لگے گا؟", roman: "Paidal kitna time lagega?", en: "On foot how much time will it take?", natural: "How long is it on foot?" },
      { hi: "یہاں قریب میں میڈیکل شاپ ہے؟", roman: "Yahan qareeb mein medical shop hai?", en: "Here nearby is there a medical shop?", natural: "Is there a pharmacy nearby?" },
      { hi: "ذرا آہستہ بولیے۔", roman: "Zara aahista boliye.", en: "Speak a little slowly.", natural: "Could you speak a bit more slowly?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in at university and make friends.",
    situation: "Your first day at the Maulana Azad National Urdu University in Gachibowli.", scenario: "hyd_ur_college",
    tip: "The Maulana Azad National Urdu University teaches in Urdu. Use “aap” with teachers and new classmates; “tum” comes later, with friends.",
    phrases: [
      { hi: "آج میرا پہلا دن ہے۔", roman: "Aaj mera pehla din hai.", en: "Today is my first day.", natural: "It's my first day today." },
      { hi: "لائبریری کدھر ہے؟", roman: "Library kidhar hai?", en: "Library is which way?", natural: "Where's the library?" },
      { hi: "کیا آپ میری مدد کریں گے؟", roman: "Kya aap meri madad karenge?", en: "Will you do my help?", natural: "Could you help me?" },
      { hi: "کینٹین میں چائے پئیں؟", roman: "Canteen mein chai piyen?", en: "Shall we drink tea in the canteen?", natural: "Shall we get chai at the canteen?" },
      { hi: "پھر ملتے ہیں!", roman: "Phir milte hain!", en: "We meet again!", natural: "See you later!" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "An evening by the Charminar with Imran, a friend from university.", scenario: "hyd_ur_smalltalk",
    tip: "Hyderabadi friends say “kya re?” (what's up?), “hau” (yes) and “nakko” (don't). “Ka jawaab nahi!” means “there's nothing like it!”.",
    phrases: [
      { hi: "کیا رے، کیسا چل رہا ہے؟", roman: "Kya re, kaisa chal raha hai?", en: "What re, how is it going?", natural: "Hey, how's it going?" },
      { hi: "حیدرآباد کی بریانی کا جواب نہیں!", roman: "Hyderabad ki biryani ka jawaab nahi!", en: "Hyderabad's biryani has no answer!", natural: "There's nothing like Hyderabadi biryani!" },
      { hi: "تم یہیں کے ہو؟", roman: "Tum yaheen ke ho?", en: "Are you of right here?", natural: "Are you from here?" },
      { hi: "اتوار کو گولکنڈہ چلیں؟", roman: "Itwaar ko Golconda chalein?", en: "Shall we go to Golconda on Sunday?", natural: "Fancy Golconda on Sunday?" },
      { hi: "ہاؤ، پکا!", roman: "Hau, pakka!", en: "Yes, for sure!", natural: "Yes, it's a plan!" },
    ] },
] };

Object.assign(window.SCENARIOS, {
  hyd_ur_greetings: { category: "greetings", icon: "🏠", title: "Meet your landlord", partner: "Nawab sahab", role: "Landlord", place: "Your rented flat in Tolichowki",
    goal: "Greet your landlord, introduce yourself and ask about the water.",
    opening: { text: "Assalaam alaikum! Aaiye, aaiye. Aap hi Alex hain?", en: "Hello! Come in, come in. Are you Alex?" },
    start: ["Walaikum assalaam! Aap kaise hain?", "Ji, mera naam Alex hai.", "Paani kab aata hai?"],
    rules: [
      { m: ["shukriya", "thank", "khuda hafiz", "milte hain", "samajh"], text: "Shukriya kis baat ka! Kuch chahiye toh bolo. 🙏", en: "No need to thank me! Tell me if you need anything.", s: ["Khuda hafiz!"], end: true, hint: "Bahut shukriya!" },
      { m: ["paani", "bijli", "current"], text: "Paani subah aur shaam ko aata. Current gaya toh inverter hai.", en: "Water comes in the morning and the evening. If the power goes, there's an inverter.", s: ["Ji, samajh aa gaya.", "Bahut shukriya!"], hint: "Paani kab aata hai?" },
      { m: ["khushi", "mil kar"], text: "Humko bhi bahut khushi hui. Hyderabad pehli baar?", en: "I'm very happy too. First time in Hyderabad?", s: ["Ji, pehli baar.", "Paani kab aata hai?"], hint: "Aap se mil kar bahut khushi hui." },
      { m: ["pehli baar", "naya", "nayi", "new"], text: "Toh biryani aur Irani chai, dono zaroor try karo!", en: "Then you must try both the biryani and the Irani chai!", s: ["Paani kab aata hai?", "Bahut shukriya!"], hint: "Ji, pehli baar." },
      { m: ["naam", "alex", "name"], text: "Bahut khoob! Hyderabad pehli baar?", en: "Lovely! First time in Hyderabad?", s: ["Ji, pehli baar.", "Aap se mil kar bahut khushi hui."], hint: "Ji, mera naam Alex hai." },
      { m: ["salaam", "alaikum", "aadaab", "kaise", "hello", " hi "], text: "Alhamdulillah, theek hoon! Aapka naam?", en: "Thank God, I'm well! Your name?", s: ["Ji, mera naam Alex hai.", "Aap se mil kar bahut khushi hui."], hint: "Walaikum assalaam! Aap kaise hain?" },
    ],
    fallback: { text: "Ji, boliye. Paani, current, parking, kya jaanna hai?", en: "Yes, tell me. Water, power, parking: what would you like to know?", s: ["Paani kab aata hai?", "Bahut shukriya!"] } },

  hyd_ur_auto: { category: "transport", icon: "🛺", title: "Auto to the Charminar", partner: "Salim bhai", role: "Auto driver", place: "Outside Nampally station",
    goal: "Get to the Charminar by the meter.", places: ["Charminar", "Mehdipatnam", "Tolichowki", "Abids", "Koti", "Banjara Hills", "Golconda", "Airport"],
    opening: { text: "Kidhar jaana?", en: "Where to?" },
    start: ["Charminar chaloge?", "Meter se chalo.", "Kitne paise hue?"],
    rules: [
      { m: ["shukriya", "thank", "upi", "khuda hafiz"], text: "Shukriya! Hyderabad mein khush raho. 🙏", en: "Thank you! Enjoy Hyderabad.", s: ["Khuda hafiz!"], end: true, hint: "Shukriya, bhai!" },
      // " idhar" (here), not the "idhar" inside "kidhar" (where)
      { m: ["roko", " idhar", "utaar", "stop"], text: "Lo, aa gaye Charminar! Meter mein ek sau bees.", en: "Here we are, the Charminar! A hundred and twenty on the meter.", s: ["UPI chalega?", "Shukriya, bhai!"], hint: "Bas, idhar roko." },
      // before the meter rule: "meter se zyaada" (more than the meter) contains "meter"
      { m: ["zyaada", "extra", "upar"], text: "Achha, achha, meter se hi chalte.", en: "All right, all right, we'll go by the meter.", s: ["Theek hai, chalo.", "Kitna time lagega?"], hint: "Nakko, meter se zyaada nahi." },
      { m: ["meter"], text: "Meter se chalte, lekin bees rupaye upar dena. Traffic hai.", en: "We'll go by the meter, but give twenty extra. There's traffic.", s: ["Nakko, sirf meter.", "Theek hai, chalo."], hint: "Meter se chalo." },
      { m: ["time", "der", "minute"], text: "Traffic hai toh bees minute.", en: "Twenty minutes, with the traffic.", s: ["Theek hai, chalo.", "Bas, idhar roko."], hint: "Kitna time lagega?" },
      { m: ["kitne", "kitna", "paise", "kiraaya"], text: "Meter se chalte, sau ke aas paas.", en: "By the meter: around a hundred.", s: ["Meter se chalo.", "Theek hai, chalo."], hint: "Kitne paise hue?" },
      { m: ["metro"], text: "Metro chahiye toh Nampally station saamne hai.", en: "If you want the metro, Nampally station is right there.", s: ["Nakko, auto mein hi chalo.", "Kitne paise hue?"], hint: "Metro station kidhar hai?" },
      { m: ["charminar", "mehdipatnam", "tolichowki", "abids", "koti", "banjara", "golconda", "airport", "chaloge", "jaana"], text: "{place}? Hau, baitho.", en: "{place}? Yes, get in.", s: ["Meter se chalo.", "Kitne paise hue?"], hint: "{place} chaloge?" },
      { m: ["sirf meter", "nakko", "theek", "chalo", "hau"], text: "Baitho! Hyderabad pehli baar?", en: "Get in! First time in Hyderabad?", s: ["Ji, pehli baar.", "Kitna time lagega?"] },
      { m: ["pehli baar", "new"], text: "Toh Charminar ke paas Irani chai zaroor peena!", en: "Then you must have an Irani chai by the Charminar!", s: ["Bas, idhar roko.", "Shukriya, bhai!"] },
    ],
    fallback: { text: "Samjha nahi. Kidhar jaana?", en: "I didn't get that. Where to?", s: ["Charminar chaloge?", "Kitne paise hue?"] } },

  hyd_ur_food: { category: "food", icon: "🍛", title: "Dinner at an Irani café", partner: "Anwar", role: "Waiter", place: "An Irani café near the Charminar",
    goal: "Order biryani and Irani chai, ask for less chilli and pay.",
    opening: { text: "Aaiye, kya laaun?", en: "Come in, what can I bring you?" },
    start: ["Ek plate biryani dena.", "Mirchi kam daalo.", "Bill kitna hua?"],
    rules: [
      { m: ["shukriya", "thank", "upi", "rakh lo", "khuda hafiz"], text: "Shukriya! Phir aana. 🙏", en: "Thank you! Come again.", s: ["Khuda hafiz!"], end: true, hint: "Ye rakh lo." },
      { m: ["bill", "kitna", "paise"], text: "Biryani aur do chai, teen sau bees.", en: "Biryani and two chais: three hundred and twenty.", s: ["UPI chalega?", "Ye rakh lo."], hint: "Bill kitna hua?" },
      { m: ["mirchi", "teekha", "spicy"], text: "Hau, mirchi kam.", en: "Sure, less chilli.", s: ["Do Irani chai aur Osmania biscuit.", "Bill kitna hua?"], hint: "Mirchi kam daalo." },
      { m: ["paani", "water"], text: "Ye lo paani.", en: "Here's some water.", s: ["Bill kitna hua?", "Do Irani chai aur Osmania biscuit."], hint: "Thoda paani dena." },
      { m: ["chai", "osmania", "biscuit"], text: "Do Irani chai, garam garam! Aur kuch?", en: "Two Irani chais, piping hot! Anything else?", s: ["Bas, itna hi.", "Thoda paani dena."], hint: "Do Irani chai aur Osmania biscuit." },
      { m: ["biryani", "plate", "haleem", "mutton", "chicken", "veg"], text: "Ek plate biryani! Mutton ya chicken?", en: "One plate of biryani! Mutton or chicken?", s: ["Chicken biryani.", "Mirchi kam daalo."], hint: "Ek plate biryani dena." },
      { m: ["itna hi", "bas"], text: "Abhi laata.", en: "Coming right up.", s: ["Bill kitna hua?", "Ye rakh lo."] },
    ],
    fallback: { text: "Biryani, haleem, Irani chai... kya laaun?", en: "Biryani, haleem, Irani chai... what can I bring you?", s: ["Ek plate biryani dena.", "Do Irani chai aur Osmania biscuit."] } },

  hyd_ur_shopping: { category: "shopping", icon: "🦪", title: "Pearls in Pathargatti", partner: "Kareem sahab", role: "Shopkeeper", place: "A pearl shop in Pathargatti",
    goal: "Buy a string of pearls at a fair price.",
    opening: { text: "Aaiye! Asli Hyderabadi moti, dekhiye.", en: "Come in! Real Hyderabad pearls, take a look." },
    start: ["Ye kitne ka hai?", "Asli moti hain?", "Bahut zyaada hai."],
    rules: [
      { m: ["pack", "shukriya", "upi", "khuda hafiz"], text: "Pack kar diya! Phir aaiye. 🙏", en: "Packed! Come again.", s: ["Khuda hafiz!"], end: true, hint: "Theek hai, pack kar do." },
      { m: ["do hazaar", "dhai hazaar", "2000", "2500"], text: "Chaliye, aapke liye dhai hazaar. Isse kam nahi.", en: "All right, two and a half thousand for you. No lower.", s: ["Theek hai, pack kar do.", "UPI chalega?"], hint: "Do hazaar mein doge?" },
      { m: ["zyaada", "kam", "last"], text: "Asli moti hain! Chaliye, teen hazaar.", en: "They're real pearls! All right, three thousand.", s: ["Do hazaar mein doge?", "Thoda kam karo na."], hint: "Thoda kam karo na." },
      { m: ["asli", "nakli", "real", "certificate"], text: "Bilkul asli! Certificate bhi dete hain.", en: "Absolutely real! We give a certificate too.", s: ["Ye kitne ka hai?", "Bahut zyaada hai."], hint: "Asli moti hain?" },
      { m: ["kitne", "daam", "price"], text: "Ye maala? Chaar hazaar.", en: "This string? Four thousand.", s: ["Bahut zyaada hai.", "Thoda kam karo na."], hint: "Ye kitne ka hai?" },
    ],
    fallback: { text: "Aaraam se dekhiye. Maala, baaliyan, sab hai.", en: "Take your time. Strings, earrings, we have it all.", s: ["Ye kitne ka hai?", "Asli moti hain?"] } },

  hyd_ur_directions: { category: "directions", icon: "🕌", title: "Find the Mecca Masjid", partner: "Habeeb bhai", role: "Passerby", place: "By the Charminar",
    goal: "Find the way to the Mecca Masjid, and a pharmacy.",
    opening: { text: "Kuch dhoondna hai? Bolo.", en: "Looking for something? Tell me." },
    start: ["Mecca Masjid kidhar hai?", "Yahan qareeb mein medical shop hai?", "Paidal kitna time lagega?"],
    rules: [
      { m: ["shukriya", "thank", "samajh", "khuda hafiz"], text: "Koi baat nahi! Aaraam se ghoomo. 🙏", en: "Not at all! Enjoy your walk.", s: ["Khuda hafiz!"], end: true, hint: "Bahut shukriya!" },
      { m: ["aahista", "phir se", "dobara", "slow"], text: "Seedha, phir seedhe haath. Bas!", en: "Straight on, then right. That's it!", s: ["Ji, samajh aa gaya.", "Paidal kitna time lagega?"], hint: "Zara aahista boliye." },
      { m: ["medical", "dawai", "pharmacy", "hospital"], text: "Hau, Charminar ke ulte haath ek medical shop hai.", en: "Yes, there's a pharmacy on the left of the Charminar.", s: ["Mecca Masjid kidhar hai?", "Zara aahista boliye."], hint: "Yahan qareeb mein medical shop hai?" },
      { m: ["paidal", "time", "door", "walk"], text: "Paidal do minute, bilkul paas hai.", en: "Two minutes on foot; it's very close.", s: ["Ji, samajh aa gaya.", "Bahut shukriya!"], hint: "Paidal kitna time lagega?" },
      { m: ["mecca", "masjid", "kidhar"], text: "Seedha jaa kar seedhe haath ko mudo. Saamne hi Mecca Masjid hai.", en: "Go straight and turn right. The Mecca Masjid is right ahead.", s: ["Paidal kitna time lagega?", "Zara aahista boliye."], hint: "Mecca Masjid kidhar hai?" },
    ],
    fallback: { text: "Bolo, kidhar jaana?", en: "Tell me, where do you need to go?", s: ["Mecca Masjid kidhar hai?", "Yahan qareeb mein medical shop hai?"] } },

  hyd_ur_college: { category: "college", icon: "🎓", title: "First day at the Urdu University", partner: "Sana", role: "Classmate", place: "Maulana Azad National Urdu University, Gachibowli",
    goal: "Find the library and the canteen, and make a friend.",
    opening: { text: "Assalaam alaikum! Aaj pehla din hai? Main Sana.", en: "Hello! Is it your first day? I'm Sana." },
    start: ["Ji, aaj mera pehla din hai.", "Library kidhar hai?", "Canteen mein chai piyen?"],
    rules: [
      { m: ["milte hain", "bye", "thank", "shukriya", "zaroor"], text: "Welcome! Kuch chahiye toh batana. 👋", en: "Welcome! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Shukriya, Sana!" },
      { m: ["chai", "canteen"], text: "Hau, class ke baad chalte!", en: "Yes, let's go after class!", s: ["Zaroor!", "Shukriya, Sana!"], hint: "Canteen mein chai piyen?" },
      { m: ["madad", "help"], text: "Bilkul! Timetable WhatsApp kar deti hoon.", en: "Of course! I'll WhatsApp you the timetable.", s: ["Canteen mein chai piyen?", "Shukriya, Sana!"], hint: "Kya aap meri madad karenge?" },
      { m: ["library", "kitaab", "kidhar"], text: "Library admin building ke saamne hai.", en: "The library is opposite the admin building.", s: ["Kya aap meri madad karenge?", "Canteen mein chai piyen?"], hint: "Library kidhar hai?" },
      { m: ["pehla", "ji", "first"], text: "Welcome! Pehle din thoda confusing hota, fikr nakko.", en: "Welcome! The first day is a bit confusing; don't worry.", s: ["Library kidhar hai?", "Kya aap meri madad karenge?"], hint: "Aaj mera pehla din hai." },
    ],
    fallback: { text: "Bolo, kya chahiye? Library, canteen, ya class?", en: "Tell me, what do you need? The library, the canteen or the class?", s: ["Library kidhar hai?", "Canteen mein chai piyen?"] } },

  hyd_ur_smalltalk: { category: "smalltalk", icon: "🌙", title: "An evening by the Charminar", partner: "Imran", role: "Friend", place: "By the Charminar in the evening",
    goal: "Chat about Hyderabad and plan a Sunday at Golconda.",
    opening: { text: "Kya re, Hyderabad kaisa lag raha?", en: "Hey, how are you liking Hyderabad?" },
    start: ["Kya re, kaisa chal raha hai?", "Hyderabad ki biryani ka jawaab nahi!", "Tum yaheen ke ho?"],
    rules: [
      { m: ["pakka", "bye", "khuda hafiz", "milte hain"], text: "Pakka! Itwaar ko subah Golconda. 👋", en: "Deal! Golconda on Sunday morning.", s: ["Khuda hafiz!"], end: true, hint: "Hau, pakka!" },
      { m: ["baje", "subah"], text: "Subah saat baje, dhoop se pehle.", en: "Seven in the morning, before the sun.", s: ["Hau, pakka!"], hint: "Kitne baje?" },
      { m: ["golconda", "itwaar", "sunday", "plan", "qila"], text: "Hau! Itwaar ko Golconda, shaam ko light show.", en: "Yes! Golconda on Sunday, the light show in the evening.", s: ["Hau, pakka!", "Kitne baje?"], hint: "Itwaar ko Golconda chalein?" },
      { m: ["yaheen", "yahin", "born"], text: "Hau, purane shehar mein paida hua, Charminar ke paas!", en: "Yes, I was born in the old city, near the Charminar!", s: ["Itwaar ko Golconda chalein?", "Hyderabad ki biryani ka jawaab nahi!"], hint: "Tum yaheen ke ho?" },
      { m: ["biryani", "jawaab", "khana"], text: "Bilkul! Aur Ramzan mein haleem, uska bhi jawaab nahi.", en: "Absolutely! And haleem in Ramzan: there's nothing like that either.", s: ["Tum yaheen ke ho?", "Itwaar ko Golconda chalein?"], hint: "Hyderabad ki biryani ka jawaab nahi!" },
      { m: ["kya re", "kaisa", "chal raha"], text: "Sab badhiya! Tum bolo, Hyderabad kaisa laga?", en: "All good! You tell me, how do you like Hyderabad?", s: ["Hyderabad ki biryani ka jawaab nahi!", "Tum yaheen ke ho?"], hint: "Kya re, kaisa chal raha hai?" },
    ],
    fallback: { text: "Haha, sahi hai! Hyderabad mein sabse achha kya laga?", en: "Haha, true! What do you like most about Hyderabad?", s: ["Hyderabad ki biryani ka jawaab nahi!", "Tum yaheen ke ho?"] } },
});

window.CONTENT_REVIEW.hyderabad.ur = { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
  known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Hyderabadi (Dakhini) words are taught as everyday Urdu; standard Urdu sometimes says them differently.", "Fares and practical tips change over time."],
  note: "Hyderabad Urdu: AI-assisted editorial review only, not yet checked by a native Urdu speaker." };

// Hyderabad's local content in Urdu: the tutor, readings, level check, achievements, "Right now" and price phrases, in Urdu script with a
// romanised line.
const PLACE_HYD_UR = {
  charminar: ["Charminar", "چارمینار", "the Charminar"], mehdipatnam: ["Mehdipatnam", "مہدی پٹنم", "Mehdipatnam"], tolichowki: ["Tolichowki", "ٹولی چوکی", "Tolichowki"],
  abids: ["Abids", "عابڈز", "Abids"], koti: ["Koti", "کوٹھی", "Koti"], "banjara hills": ["Banjara Hills", "بنجارہ ہلز", "Banjara Hills"],
  golconda: ["Golconda", "گولکنڈہ", "Golconda Fort"], airport: ["Airport", "ایئرپورٹ", "the airport"], nampally: ["Nampally", "نامپلی", "Nampally station"],
};
const HYDERABAD_UR_PLACES = ["Charminar", "Mehdipatnam", "Tolichowki", "Abids", "Koti", "Banjara Hills", "Golconda", "Airport", "Nampally"];
const urP = (hi, roman, en, extra) => ({ hi, roman, en, ...(extra || {}) });

window.LOCAL_CONTENT.hyderabad.ur = {
  tutor: {
    greet: "Assalaam alaikum", places: HYDERABAD_UR_PLACES, defaultPlace: "Charminar", language: "Urdu",
    starters: ["I need an auto to the Charminar.", "How do I order biryani, not too spicy?", "How do I bargain for pearls?", "What does 'nakko' mean?", "Which metro goes to the old city?"],
    glossaryOnly: true,                                  // Hyderabad's own words: the shared (Delhi Hindi) glossary is not used
    glossary: {
      "assalaam alaikum": "“Peace be upon you”: the everyday hello. The answer is “walaikum assalaam”.", aadaab: "A respectful hello, said with a small raised hand.",
      hau: "Hyderabadi for “yes”. With friends; say “ji haan” to elders.", nakko: "Hyderabadi for “no / don't”: “nakko re!” (don't!).", "kya re": "“What's up?” With friends.",
      shukriya: "Thank you.", "khuda hafiz": "Goodbye.", "khush aamdeed": "Welcome!", sahab: "“Sir”: added after a name to show respect (“Nawab sahab”).",
      "seedhe haath": "“Right hand”: to the right. “Ulte haath” is to the left.", dawakhana: "A pharmacy.", "irani chai": "Strong, milky tea from Hyderabad's Irani cafés.",
    },
    polite: { intro: "Urdu is polite with “aap” and verbs ending in -iye (“dijiye”, “boliye”, “chaliye”):", rules: [["\\btum\\b", "aap"], ["\\bdo\\b", "dijiye"], ["\\bbolo\\b", "boliye"], ["\\bchalo\\b", "chaliye"]],
      note: "e.g. “tum” → “aap”, “bolo” → “boliye”, “chalo” → “chaliye”. With friends and in the market the short forms are fine." },
    intents: [
      { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
        build: (dest) => { const d = PLACE_HYD_UR[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
          urP(d ? `${d[1]} چلو گے؟ میٹر سے۔` : "", `${r} chaloge? Meter se.`, `Will you go to ${d ? d[2] : dest}? By the meter.`),
          urP(d ? `بھائی، ${d[1]} چلیں گے؟` : "", `Bhai, ${r} chalenge?`, `A more polite version: Would you take me to ${d ? d[2] : dest}?`, { label: "More polite" }),
          urP("میٹر سے چلو۔", "Meter se chalo.", "Please go by the meter."),
        ], note: HYD_RIDE_NOTE }; } },
      { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
          urP("ایم جی بی ایس کے لیے کون سی لائن؟", "MGBS ke liye kaun si line?", "Which line for MGBS?"), urP("یہ میٹرو امیرپیٹ جاتی ہے؟", "Ye metro Ameerpet jaati hai?", "Does this metro go to Ameerpet?"),
          urP("ٹکٹ کدھر ملے گا؟", "Ticket kidhar milega?", "Where do I get a ticket?"),
        ], note: HYD_METRO_NOTE },
      { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
          urP("تھوڑا کم کرو نا۔", "Thoda kam karo na.", "Please lower it a little."), urP("بہت زیادہ ہے۔", "Bahut zyaada hai.", "That's too much."),
          urP("آخری دام بولیے۔", "Aakhri daam boliye.", "What's your best price?"),
        ], note: "In Pathargatti and Laad Bazaar bargain gently where there are no price tags; ask “asli hain?” (are they real?) about pearls." },
      { m: ["price", "how much", "cost", "kitna", "kitne", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
          urP("یہ کتنے کا ہے؟", "Ye kitne ka hai?", "How much is this?"), urP("یو پی آئی چلے گا؟", "UPI chalega?", "Can I pay by UPI?"),
        ] },
      { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "biryani", "chai", "bill"], topic: "food", intro: "Ordering food:", phrases: [
          urP("ایک پلیٹ بریانی دینا۔", "Ek plate biryani dena.", "One plate of biryani, please."), urP("مرچی کم ڈالو۔", "Mirchi kam daalo.", "Not too spicy, please."),
          urP("بل دیجیے۔", "Bill dijiye.", "Could I have the bill, please?"),
        ], note: "In Ramzan, haleem is everywhere in the old city. Finish with an Irani chai and Osmania biscuits." },
      { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
          urP("چارمینار کدھر ہے؟", "Charminar kidhar hai?", "Which way is the Charminar?"), urP("میں راستہ بھول گیا ہوں۔", "Main raasta bhool gaya hoon.", "I'm lost. (women say: bhool gayi hoon)"),
          urP("سیدھے ہاتھ کو یا الٹے ہاتھ کو؟", "Seedhe haath ko ya ulte haath ko?", "To the right or to the left?"),
        ], note: "Hyderabad says “seedhe haath” (right hand) for right and “ulte haath” for left." },
      { m: ["class", "college", "university", "professor", "teacher", "office", "work", "colleague", "canteen", "library"], topic: "college", intro: "At college or work:", phrases: [
          urP("آج میرا پہلا دن ہے۔", "Aaj mera pehla din hai.", "It's my first day today."), urP("لائبریری کدھر ہے؟", "Library kidhar hai?", "Where's the library?"),
          urP("کیا آپ میری مدد کریں گے؟", "Kya aap meri madad karenge?", "Could you help me?"),
        ] },
      { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
          urP("آپ کہاں کے ہیں؟", "Aap kahan ke hain?", "Where are you from?"), urP("آج بہت گرمی ہے نا؟", "Aaj bahut garmi hai na?", "It's really hot today, isn't it?"),
          urP("چائے ہو جائے؟", "Chai ho jaaye?", "How about some chai?"),
        ], note: "Hyderabad small talk: biryani, cricket and the old city. With friends: “kya re?”, “hau” and “nakko”." },
      { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
          urP("میرا نام ایلکس ہے۔", "Mera naam Alex hai.", "My name is Alex."), urP("آپ کا نام کیا ہے؟", "Aap ka naam kya hai?", "What's your name?"),
          urP("آپ سے مل کر بہت خوشی ہوئی۔", "Aap se mil kar bahut khushi hui.", "It's lovely to meet you."),
        ] },
      { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
          urP("بہت شکریہ!", "Bahut shukriya!", "Thanks a lot!"), urP("معاف کیجیے۔", "Maaf kijiye.", "Sorry / Excuse me."), urP("سنیے…", "Suniye…", "Excuse me… (to get attention)"),
        ] },
      { m: ["hello", "hi", "greet", "salaam", "aadaab", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Hyderabad:", phrases: [
          urP("السلام علیکم!", "Assalaam alaikum!", "Hello! (peace be upon you)"), urP("خدا حافظ!", "Khuda hafiz!", "Goodbye!"),
        ], note: "“Assalaam alaikum” and “Aadaab” work with everyone; the answer to the first is “Walaikum assalaam”." },
      { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
          urP("مجھے مدد چاہیے۔", "Mujhe madad chahiye.", "I need help."), urP("قریب میں ہسپتال کہاں ہے؟", "Qareeb mein hospital kahan hai?", "Where's the nearest hospital?"),
        ], note: "Emergency number in India: 112." },
    ],
    generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
        urP("السلام علیکم! آپ کیسے ہیں؟", "Assalaam alaikum! Aap kaise hain?", "Hello! How are you?"), urP("یہ کتنے کا ہے؟", "Ye kitne ka hai?", "How much is this?"),
        urP("کیا آپ میری مدد کریں گے؟", "Kya aap meri madad karenge?", "Could you help me?"),
      ], note: "Tell me a situation — like “I want to order biryani” or “ask the way to the Charminar” — and I'll give you the exact Urdu words." },
  },
  readings: [
    { title: "Asha in the old city", level: "A1", lines: [
        urP("آشا حیدرآباد میں نئی ہے۔", "Asha Hyderabad mein nayi hai.", "Asha is new in Hyderabad."), urP("وہ آٹو سے چارمینار جاتی ہے۔", "Woh auto se Charminar jaati hai.", "She takes an auto to the Charminar."),
        urP("وہاں وہ بریانی کھاتی ہے۔", "Wahan woh biryani khaati hai.", "There she eats biryani."), urP("پھر وہ ایرانی چائے پیتی ہے۔", "Phir woh Irani chai peeti hai.", "Then she has an Irani chai."),
      ],
      questions: [
        { q: "Where is Asha new?", options: ["Kolkata", "Hyderabad", "Lucknow"], a: 1 }, { q: "How does she travel?", options: ["By auto", "By metro", "By bus"], a: 0 },
        { q: "What does she drink?", options: ["Coffee", "Irani chai", "Lassi"], a: 1 },
      ] },
    { title: "Pearls in Pathargatti", level: "A1", lines: [
        urP("روی پتھر گٹی جاتا ہے۔", "Ravi Pathargatti jaata hai.", "Ravi goes to Pathargatti."), urP("اسے موتیوں کی ایک مالا پسند آتی ہے۔", "Use motiyon ki ek maala pasand aati hai.", "He likes a string of pearls."),
        urP("دکاندار چار ہزار مانگتا ہے۔", "Dukaandaar chaar hazaar maangta hai.", "The shopkeeper asks for four thousand."), urP("روی ڈھائی ہزار میں لیتا ہے۔", "Ravi dhai hazaar mein leta hai.", "Ravi buys it for two and a half thousand."),
      ],
      questions: [
        { q: "Where does Ravi go?", options: ["Pathargatti", "HITEC City", "Abids"], a: 0 }, { q: "What does he buy?", options: ["Pearls", "Bangles", "A kurta"], a: 0 },
        { q: "How much does he pay?", options: ["₹4000", "₹2500", "₹250"], a: 1 },
      ] },
  ],
  placement: [
    { q: "What does “hau” mean in Hyderabad?", options: ["No", "Yes", "Thank you", "How much?"], a: 1 },
    { q: "How would you ask an auto driver to go by the meter?", options: ["Meter se chalo.", "Ye kitne ka hai?", "Bill dijiye.", "Khuda hafiz!"], a: 0 },
    { q: "What does “nakko” mean?", options: ["Yes", "No / don't", "Here", "Tomorrow"], a: 1 },
    { q: "“Seedhe haath ko mudo” means…", options: ["Go straight", "Turn right", "Turn left", "Stop here"], a: 1 },
    { q: "Which is the most polite way to ask for the bill?", options: ["Bill do", "Bill dijiye", "Bill!", "Bill de re"], a: 1 },
  ],
  achievements: {
    "first-words": ["🗣️", "First words", "Said your first Urdu phrase"], "auto-pro": ["🛺", "Meter pro", "Took an auto by the meter"],
    foodie: ["🍛", "Biryani lover", "Ordered a Hyderabadi meal"], bargainer: ["🦪", "Pearl bargainer", "Won a bargain"],
  },
  rightNow: [
    [5, 11, "☕", "Irani chai time", "Irani cafés are busiest in the morning. Order like a local.", "hyd_ur_food", urP("دو ایرانی چائے اور عثمانیہ بسکٹ۔", "Do Irani chai aur Osmania biscuit.", "Two Irani chais and some Osmania biscuits.")],
    [11, 15, "🕌", "Old city hours", "The Charminar and the Mecca Masjid are close together. Ask the way.", "hyd_ur_directions", urP("مکہ مسجد کدھر ہے؟", "Mecca Masjid kidhar hai?", "Which way is the Mecca Masjid?")],
    [15, 18, "🦪", "Market hours", "Pathargatti's pearl shops are open. Time to bargain, gently.", "hyd_ur_shopping", urP("تھوڑا کم کرو نا۔", "Thoda kam karo na.", "Can you lower it a bit?")],
    [18, 22, "🌙", "Evening by the Charminar", "The old city comes alive in the evening.", "hyd_ur_smalltalk", urP("کیا رے، کیسا چل رہا ہے؟", "Kya re, kaisa chal raha hai?", "Hey, how's it going?")],
    [22, 29, "🛺", "Late night ride home", "Autos charge more at night. Ask for the meter.", "hyd_ur_auto", urP("میٹر سے چلو۔", "Meter se chalo.", "Please go by the meter.")],
  ],
  priceSay: (max, mid) => ({
    ticket: urP("امیرپیٹ کا ایک ٹکٹ دیجیے۔", "Ameerpet ka ek ticket dijiye.", "One ticket to Ameerpet, please."), meter: urP("میٹر سے چلو۔", "Meter se chalo.", "Please go by the meter."),
    fair: urP("ٹھیک ہے، دے دیجیے۔", "Theek hai, de dijiye.", "Okay, I'll take it."), counter: urP(`${max} میں دو گے؟`, `${max} mein doge?`, `Will you do it for ₹${max}?`),
    high: urP(`بہت زیادہ ہے۔ ${mid} میں دو گے؟`, `Bahut zyaada hai. ${mid} mein doge?`, `That's too much. Will you do ₹${mid}?`),
  }),
};

// Bhopal First Week pack, in Hindi (the English view shows the same pack in English first): Bhopal's Hindi with its own touches ("khan" and
// "miyan" as a friendly address, "patiya" chats in the old city). AI-assisted editorial review only.
window.PACKS.bhopal = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your neighbours and introduce yourself.",
    situation: "You've just rented a flat in Arera Colony. Sharma aunty, your neighbour, comes to say hello.", scenario: "bpl_greetings",
    tip: "“Namaste” works with everyone, and in the old city “Aadaab” and “Assalaam alaikum” are just as common. Bhopalis call a friend “khan” or “miyan” whatever their name: “Kya haal hai, khan?”.",
    phrases: [
      { hi: "नमस्ते आंटी! आप कैसी हैं?", roman: "Namaste aunty! Aap kaisi hain?", en: "Hello aunty! How are you?", natural: "Hello! How are you?" },
      { hi: "मेरा नाम एलेक्स है।", roman: "Mera naam Alex hai.", en: "My name is Alex.", natural: "I'm Alex." },
      { hi: "मैं भोपाल में नया हूँ।", roman: "Main Bhopal mein naya hoon.", en: "I am new in Bhopal.", natural: "I'm new to Bhopal.", fem: { hi: "मैं भोपाल में नई हूँ।", roman: "Main Bhopal mein nayi hoon." } },
      { hi: "यहाँ पानी कब आता है?", roman: "Yahan paani kab aata hai?", en: "Here when does water come?", natural: "When does the water come here?" },
      { hi: "बहुत-बहुत शुक्रिया!", roman: "Bahut-bahut shukriya!", en: "Very many thanks!", natural: "Thank you so much!" },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Take autos, shared 'magic' vans and the new metro.",
    situation: "You've arrived at Rani Kamlapati station and need to get to New Market.", scenario: "bpl_auto",
    tip: "Bhopal's autos rarely use the meter: agree the fare first, or book an app ride. Shared “magic” vans run fixed routes for a few rupees a seat, and the metro's Orange Line runs from Subhash Nagar through MP Nagar and Rani Kamlapati to AIIMS.",
    phrases: [
      { hi: "न्यू मार्केट चलोगे?", roman: "New Market chaloge?", en: "Will you go to New Market?", natural: "Will you go to New Market?" },
      { hi: "कितना किराया लोगे?", roman: "Kitna kiraaya loge?", en: "How much fare will you take?", natural: "How much will it cost?" },
      { hi: "अस्सी रुपये में चलो।", roman: "Assi rupaye mein chalo.", en: "Go for eighty rupees.", natural: "Let's go for eighty." },
      { hi: "मैजिक कहाँ से मिलेगी?", roman: "Magic kahan se milegi?", en: "From where will a magic be got?", natural: "Where can I get a shared van?" },
      { hi: "बस, यहीं उतार दो।", roman: "Bas, yahin utaar do.", en: "Enough, drop me right here.", natural: "Just drop me here." },
    ] },
  { day: 3, key: "food", icon: "🍽️", title: "Food", desc: "Start the day with poha-jalebi and end it with sulemani chai.",
    situation: "Breakfast at a stall near New Market.", scenario: "bpl_food",
    tip: "Bhopal's breakfast is poha with jalebi, sprinkled with sev and a squeeze of lemon. The old city is famous for its meat dishes and, late at night, sulemani chai (salty-sweet tea) near the Chowk.",
    phrases: [
      { hi: "एक प्लेट पोहा-जलेबी देना।", roman: "Ek plate poha-jalebi dena.", en: "Give one plate of poha-jalebi.", natural: "One plate of poha-jalebi, please." },
      { hi: "पोहे में सेव ज़्यादा डालना।", roman: "Pohe mein sev zyaada daalna.", en: "In the poha put more sev.", natural: "Extra sev on the poha, please." },
      { hi: "एक सुलेमानी चाय भी।", roman: "Ek sulemani chai bhi.", en: "One sulemani tea too.", natural: "And a sulemani chai." },
      { hi: "मिर्च कम रखना।", roman: "Mirch kam rakhna.", en: "Keep the chilli less.", natural: "Not too spicy, please." },
      { hi: "कितने पैसे हुए?", roman: "Kitne paise hue?", en: "How much money did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain for a zari batua in the old city's Chowk Bazaar.",
    situation: "You're in Chowk Bazaar, in the old city, looking for a batua.", scenario: "bpl_shopping",
    tip: "Chowk Bazaar sells Bhopal's zari and bead-work batuas (small drawstring purses); New Market has clothes and everything else. Start at about half the first price where there are no price tags.",
    phrases: [
      { hi: "ये बटुआ कितने का है?", roman: "Ye batua kitne ka hai?", en: "This purse is of how much?", natural: "How much is this batua?" },
      { hi: "ये तो बहुत महँगा है।", roman: "Ye toh bahut mehenga hai.", en: "This is very expensive.", natural: "That's far too expensive." },
      { hi: "कुछ कम करो, खान।", roman: "Kuch kam karo, khan.", en: "Make it somewhat less, khan.", natural: "Come on, a little less." },
      { hi: "ये हाथ का काम है?", roman: "Ye haath ka kaam hai?", en: "Is this work of the hand?", natural: "Is this handmade?" },
      { hi: "ठीक है, दे दो।", roman: "Theek hai, de do.", en: "Okay, give it.", natural: "Okay, I'll take it." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way round the lakes and the old city.",
    situation: "You're at Peer Gate in the old city and want the Taj-ul-Masajid.", scenario: "bpl_directions",
    tip: "Bhopal is the City of Lakes: the Upper Lake (Bada Talab) and its Boat Club are the city's favourite landmark. In the old city people give directions from the gates and the Chowk.",
    phrases: [
      { hi: "ताज-उल-मसाजिद किधर है?", roman: "Taj-ul-Masajid kidhar hai?", en: "Taj-ul-Masajid is which way?", natural: "Which way is the Taj-ul-Masajid?" },
      { hi: "सीधे जाइए, फिर बाएँ मुड़िए।", roman: "Seedhe jaiye, phir baayen mudiye.", en: "Go straight, then turn left.", natural: "Go straight, then turn left." },
      { hi: "पैदल कितनी दूर है?", roman: "Paidal kitni door hai?", en: "On foot how far is it?", natural: "How far is it on foot?" },
      { hi: "पास में कोई मेडिकल स्टोर है?", roman: "Paas mein koi medical store hai?", en: "Nearby is there any medical store?", natural: "Is there a pharmacy nearby?" },
      { hi: "ज़रा फिर से बताइए।", roman: "Zara phir se bataiye.", en: "Tell a little again.", natural: "Could you say that again?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in with classmates and colleagues.",
    situation: "Your first day at a college near MP Nagar.", scenario: "bpl_college",
    tip: "Bhopal is a student city: MANIT, Barkatullah University and many colleges around MP Nagar. Classmates say “aur khan, kya scene hai?” (so, what's up?).",
    phrases: [
      { hi: "आज मेरा पहला दिन है।", roman: "Aaj mera pehla din hai.", en: "Today is my first day.", natural: "It's my first day today." },
      { hi: "मेरी क्लास किस फ़्लोर पर है?", roman: "Meri class kis floor par hai?", en: "My class is on which floor?", natural: "Which floor is my class on?" },
      { hi: "थोड़ी मदद कर दो ना?", roman: "Thodi madad kar do na?", en: "Do a little help, no?", natural: "Could you help me out?" },
      { hi: "कैंटीन में पोहा मिलता है?", roman: "Canteen mein poha milta hai?", en: "Is poha available in the canteen?", natural: "Do they have poha in the canteen?" },
      { hi: "फिर मिलते हैं!", roman: "Phir milte hain!", en: "We meet again!", natural: "See you later!" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "Sunset at the Boat Club on the Upper Lake with Arif, a friend from college.", scenario: "bpl_smalltalk",
    tip: "Bhopal loves a slow chat: in the old city people still gather on a “patiya” (a wooden platform) to talk for hours. Weekend trips: the Sanchi Stupa and the Bhimbetka rock shelters.",
    phrases: [
      { hi: "बड़ा तालाब कितना सुंदर है!", roman: "Bada Talab kitna sundar hai!", en: "How beautiful the big lake is!", natural: "The Upper Lake is so beautiful!" },
      { hi: "भोपाल बहुत शांत शहर है।", roman: "Bhopal bahut shaant shehar hai.", en: "Bhopal is a very calm city.", natural: "Bhopal is such a calm city." },
      { hi: "तुम पुराने भोपाल के हो?", roman: "Tum puraane Bhopal ke ho?", en: "Are you of old Bhopal?", natural: "Are you from old Bhopal?" },
      { hi: "संडे को साँची चलें?", roman: "Sunday ko Saanchi chalein?", en: "Shall we go to Sanchi on Sunday?", natural: "Fancy Sanchi on Sunday?" },
      { hi: "पक्का, मज़ा आएगा!", roman: "Pakka, mazaa aayega!", en: "Sure, it will be fun!", natural: "Definitely, it'll be fun!" },
    ] },
];

Object.assign(window.SCENARIOS, {
  bpl_greetings: { category: "greetings", icon: "🏠", title: "Meet your neighbour", partner: "Sharma aunty", role: "Neighbour", place: "Your rented flat in Arera Colony",
    goal: "Greet your neighbour, introduce yourself and ask about the water.",
    opening: { text: "Namaste! Aap hi Alex hain? Main Sharma aunty, saamne waale flat mein.", en: "Hello! Are you Alex? I'm Mrs Sharma, from the flat opposite." },
    start: ["Namaste aunty! Aap kaisi hain?", "Ji, mera naam Alex hai.", "Yahan paani kab aata hai?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "milte hain", "samajh"], text: "Arey, shukriya kis baat ka! Kuch chahiye toh bolna. 🙏", en: "No need to thank me! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Bahut-bahut shukriya!" },
      { m: ["paani", "bijli", "light"], text: "Paani subah chhe se aath aata hai. Tanki bhar ke rakhna!", en: "Water comes from six to eight in the morning. Keep the tank full!", s: ["Ji, samajh aa gaya.", "Bahut-bahut shukriya!"], hint: "Yahan paani kab aata hai?" },
      { m: ["pehli baar", "naya", "nayi", "new"], text: "Bhopal mein swagat hai! Bada Talab zaroor dekhna.", en: "Welcome to Bhopal! Don't miss the Upper Lake.", s: ["Yahan paani kab aata hai?", "Bahut-bahut shukriya!"], hint: "Ji, pehli baar." },
      { m: ["naam", "alex", "name"], text: "Achha naam hai! Bhopal pehli baar aana hua?", en: "Nice name! Is this your first time in Bhopal?", s: ["Ji, pehli baar.", "Yahan paani kab aata hai?"], hint: "Ji, mera naam Alex hai." },
      { m: ["namaste", "kaisi", "kaise", "aadaab", "hello", " hi "], text: "Main badhiya hoon, beta! Aapka naam kya hai?", en: "I'm very well, dear! What's your name?", s: ["Ji, mera naam Alex hai.", "Yahan paani kab aata hai?"], hint: "Namaste aunty! Aap kaisi hain?" },
    ],
    fallback: { text: "Haan ji, boliye. Paani, bijli, doodhwala, kya jaanna hai?", en: "Yes, tell me. Water, power, the milkman: what would you like to know?", s: ["Yahan paani kab aata hai?", "Bahut-bahut shukriya!"] } },

  bpl_auto: { category: "transport", icon: "🛺", title: "Auto to New Market", partner: "Rafiq bhai", role: "Auto driver", place: "Outside Rani Kamlapati railway station",
    goal: "Get to New Market for a fair fare.", places: ["New Market", "MP Nagar", "Boat Club", "Chowk Bazaar", "Arera Colony", "Airport", "DB Mall", "Bhopal Junction", "Van Vihar"],
    opening: { text: "Kahan chalna hai?", en: "Where to?" },
    start: ["New Market chaloge?", "Kitna kiraaya loge?", "Magic kahan se milegi?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "upi", "khuda hafiz", "milte hain"], text: "Shukriya! Bhopal mein maze karo. 🙏", en: "Thank you! Enjoy Bhopal.", s: ["Phir milte hain!"], end: true, hint: "Shukriya, bhai!" },
      { m: ["utaar", "rok", "yahin", "stop"], text: "Lo, aa gaya New Market! Assi rupaye.", en: "Here's New Market! Eighty rupees.", s: ["UPI chalega?", "Shukriya, bhai!"], hint: "Bas, yahin utaar do." },
      { m: ["assi", "80"], text: "Theek hai, assi mein chalo. Baitho!", en: "Okay, eighty it is. Get in!", s: ["Kitni der lagegi?", "Bas, yahin utaar do."], hint: "Assi rupaye mein chalo." },
      { m: ["magic", "sharing", "shared", "tempo"], text: "Magic bahar stand se milti hai, das-bees rupaye sawaari.", en: "Shared vans leave from the stand outside, ten or twenty rupees a person.", s: ["Nahi, auto se chalo.", "Kitna kiraaya loge?"], hint: "Magic kahan se milegi?" },
      { m: ["der", "minute", "time"], text: "Pandrah minute, traffic kam hai abhi.", en: "Fifteen minutes; there's not much traffic now.", s: ["Theek hai, chalo.", "Bas, yahin utaar do."], hint: "Kitni der lagegi?" },
      { m: ["metro"], text: "Metro bhi hai, Rani Kamlapati se MP Nagar tak jaati hai.", en: "There's the metro too: it goes from Rani Kamlapati to MP Nagar.", s: ["Nahi, auto se chalo.", "Kitna kiraaya loge?"], hint: "Metro kidhar se milegi?" },
      { m: ["zyaada", "mehenga", "kam"], text: "Achha, sau de dena.", en: "All right, give a hundred.", s: ["Assi rupaye mein chalo.", "Theek hai, chalo."], hint: "Bahut zyaada hai, bhai." },
      { m: ["kiraaya", "kitna", "paise"], text: "New Market? Ek sau bees lagenge.", en: "New Market? A hundred and twenty.", s: ["Assi rupaye mein chalo.", "Bahut zyaada hai, bhai."], hint: "Kitna kiraaya loge?" },
      { m: ["new market", "mp nagar", "boat club", "chowk", "arera", "airport", "db mall", "junction", "van vihar", "chaloge"], text: "{place}? Haan, baitho.", en: "{place}? Yes, get in.", s: ["Kitna kiraaya loge?", "Assi rupaye mein chalo."], hint: "{place} chaloge?" },
      { m: ["pehli baar", "new"], text: "Swagat hai! Shaam ko Boat Club zaroor jaana.", en: "Welcome! Do go to the Boat Club in the evening.", s: ["Kitni der lagegi?", "Bas, yahin utaar do."] },
      { m: ["theek", "chalo", "haan", "ok"], text: "Baitho! Bhopal pehli baar?", en: "Get in! First time in Bhopal?", s: ["Haan, pehli baar.", "Kitni der lagegi?"] },
    ],
    fallback: { text: "Samjha nahi. Kahan chalna hai?", en: "I didn't get that. Where to?", s: ["New Market chaloge?", "Kitna kiraaya loge?"] } },

  bpl_food: { category: "food", icon: "🍽️", title: "Poha-jalebi for breakfast", partner: "Mishra ji", role: "Stall owner", place: "A breakfast stall near New Market",
    goal: "Order poha-jalebi and a chai, and pay.",
    opening: { text: "Aao, aao! Garam poha taiyaar hai.", en: "Come, come! Hot poha's ready." },
    start: ["Ek plate poha-jalebi dena.", "Mirch kam rakhna.", "Kitne paise hue?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "upi", "lijiye", "milte hain"], text: "Shukriya! Kal bhi aana. 🙏", en: "Thank you! Come again tomorrow.", s: ["Phir milte hain!"], end: true, hint: "Ye lijiye." },
      { m: ["kitne", "paise", "bill"], text: "Poha-jalebi aur chai, saath rupaye.", en: "Poha-jalebi and chai, sixty rupees.", s: ["UPI chalega?", "Ye lijiye."], hint: "Kitne paise hue?" },
      { m: ["mirch", "teekha", "spicy"], text: "Theek hai, mirch kam.", en: "Okay, less chilli.", s: ["Ek sulemani chai bhi.", "Kitne paise hue?"], hint: "Mirch kam rakhna." },
      { m: ["sev", "nimbu", "lemon"], text: "Sev bhi, nimbu bhi! Bhopal ka poha aisa hi khaate hain.", en: "Sev and lemon too! That's how Bhopal eats its poha.", s: ["Ek sulemani chai bhi.", "Kitne paise hue?"], hint: "Pohe mein sev zyaada daalna." },
      { m: ["chai", "sulemani"], text: "Sulemani chai toh raat ko Chowk mein milegi. Yahan adrak waali chai hai.", en: "For sulemani chai go to the Chowk at night. Here we have ginger chai.", s: ["Theek hai, adrak waali do.", "Kitne paise hue?"], hint: "Ek sulemani chai bhi." },
      { m: ["poha", "jalebi", "plate", "adrak"], text: "Ye lo, garam garam! Sev daalun?", en: "Here you go, piping hot! Shall I add sev?", s: ["Pohe mein sev zyaada daalna.", "Mirch kam rakhna."], hint: "Ek plate poha-jalebi dena." },
    ],
    fallback: { text: "Poha, jalebi, samosa, chai... kya loge?", en: "Poha, jalebi, samosa, chai... what will you have?", s: ["Ek plate poha-jalebi dena.", "Ek sulemani chai bhi."] } },

  bpl_shopping: { category: "shopping", icon: "👛", title: "A batua in Chowk Bazaar", partner: "Saleem miyan", role: "Shopkeeper", place: "Chowk Bazaar, in the old city",
    goal: "Buy a zari batua at a fair price.",
    opening: { text: "Aaiye! Asli Bhopali batua, zari ka kaam.", en: "Come in! Real Bhopal batuas, zari work." },
    start: ["Ye batua kitne ka hai?", "Ye haath ka kaam hai?", "Ye toh bahut mehenga hai."],
    rules: [
      { m: ["de do", "pack", "shukriya", "upi", "milte hain"], text: "Ye lijiye! Phir aaiye. 🙏", en: "Here you are! Come again.", s: ["Phir milte hain!"], end: true, hint: "Theek hai, de do." },
      { m: ["chaar sau", "teen sau", "400", "300"], text: "Chaliye, aapke liye chaar sau. Isse kam nahi.", en: "All right, four hundred for you. No lower.", s: ["Theek hai, de do.", "UPI chalega?"], hint: "Teen sau mein doge?" },
      { m: ["mehenga", "kam", "zyaada"], text: "Haath ka kaam hai, khan! Chaliye, saadhe paanch sau.", en: "It's handwork, my friend! All right, five hundred and fifty.", s: ["Teen sau mein doge?", "Kuch kam karo, khan."], hint: "Kuch kam karo, khan." },
      { m: ["haath", "zari", "asli", "machine"], text: "Bilkul, ghar ki auraton ka haath ka kaam hai.", en: "Of course: it's handwork by women from the old city.", s: ["Ye batua kitne ka hai?", "Ye toh bahut mehenga hai."], hint: "Ye haath ka kaam hai?" },
      { m: ["kitne", "daam", "price"], text: "Ye batua? Aath sau.", en: "This batua? Eight hundred.", s: ["Ye toh bahut mehenga hai.", "Kuch kam karo, khan."], hint: "Ye batua kitne ka hai?" },
    ],
    fallback: { text: "Aaraam se dekhiye. Batue, chooriyaan, sab hai.", en: "Take your time. Batuas, bangles, we have it all.", s: ["Ye batua kitne ka hai?", "Ye haath ka kaam hai?"] } },

  bpl_directions: { category: "directions", icon: "🕌", title: "Find the Taj-ul-Masajid", partner: "Qureshi sahab", role: "Passerby", place: "Peer Gate, in the old city",
    goal: "Find the way to the Taj-ul-Masajid, and a pharmacy.",
    opening: { text: "Kuch dhoondhna hai?", en: "Looking for something?" },
    start: ["Taj-ul-Masajid kidhar hai?", "Paas mein koi medical store hai?", "Paidal kitni door hai?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "samajh", "milte hain"], text: "Koi baat nahi! Aaraam se ghoomiye. 🙏", en: "Not at all! Enjoy your walk.", s: ["Phir milte hain!"], end: true, hint: "Bahut-bahut shukriya!" },
      { m: ["phir se", "dobara", "dheere", "slow"], text: "Seedhe, phir baayen. Saamne masjid.", en: "Straight on, then left. The mosque is ahead.", s: ["Ji, samajh aa gaya.", "Paidal kitni door hai?"], hint: "Zara phir se bataiye." },
      { m: ["medical", "dawai", "chemist", "hospital"], text: "Haan, Peer Gate ke paas ek medical store hai.", en: "Yes, there's a pharmacy by Peer Gate.", s: ["Taj-ul-Masajid kidhar hai?", "Zara phir se bataiye."], hint: "Paas mein koi medical store hai?" },
      { m: ["paidal", "door", "walk", "der"], text: "Paidal das minute, zyaada nahi.", en: "Ten minutes on foot, no more.", s: ["Ji, samajh aa gaya.", "Bahut-bahut shukriya!"], hint: "Paidal kitni door hai?" },
      { m: ["taj", "masajid", "masjid", "kidhar"], text: "Seedhe jaiye, phir baayen mudiye. Taj-ul-Masajid saamne dikhegi.", en: "Go straight, then turn left. You'll see the Taj-ul-Masajid ahead.", s: ["Paidal kitni door hai?", "Zara phir se bataiye."], hint: "Taj-ul-Masajid kidhar hai?" },
    ],
    fallback: { text: "Bataiye, kahan jaana hai?", en: "Tell me, where do you need to go?", s: ["Taj-ul-Masajid kidhar hai?", "Paas mein koi medical store hai?"] } },

  bpl_college: { category: "college", icon: "🎓", title: "First day at college", partner: "Neha", role: "Classmate", place: "A college near MP Nagar",
    goal: "Find your class and the canteen, and make a friend.",
    opening: { text: "Hi! Pehla din hai kya? Main Neha.", en: "Hi! Is it your first day? I'm Neha." },
    start: ["Haan, aaj mera pehla din hai.", "Meri class kis floor par hai?", "Canteen mein poha milta hai?"],
    rules: [
      { m: ["milte hain", "bye", "thank", "shukriya", "badhiya"], text: "Welcome! Kuch chahiye toh batana. 👋", en: "Welcome! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Thank you, Neha!" },
      { m: ["canteen", "poha", "chai"], text: "Haan! Subah poha, dopahar mein samose. Break mein chalte hain.", en: "Yes! Poha in the morning, samosas at lunch. Let's go at the break.", s: ["Badhiya!", "Thank you, Neha!"], hint: "Canteen mein poha milta hai?" },
      { m: ["madad", "help"], text: "Haan, bilkul! Timetable WhatsApp kar deti hoon.", en: "Of course! I'll WhatsApp you the timetable.", s: ["Canteen mein poha milta hai?", "Thank you, Neha!"], hint: "Thodi madad kar do na?" },
      { m: ["class", "floor", "room"], text: "Teesre floor par, room teen sau do.", en: "On the third floor, room 302.", s: ["Thodi madad kar do na?", "Canteen mein poha milta hai?"], hint: "Meri class kis floor par hai?" },
      { m: ["pehla", "haan", "first"], text: "Welcome! Pehle din sab thoda confusing hota hai.", en: "Welcome! Everything's a bit confusing on the first day.", s: ["Meri class kis floor par hai?", "Thodi madad kar do na?"], hint: "Aaj mera pehla din hai." },
    ],
    fallback: { text: "Bolo, kya chahiye? Class, library, ya canteen?", en: "Tell me, what do you need? The class, the library or the canteen?", s: ["Meri class kis floor par hai?", "Canteen mein poha milta hai?"] } },

  bpl_smalltalk: { category: "smalltalk", icon: "🌅", title: "Sunset at the Boat Club", partner: "Arif", role: "Friend", place: "The Boat Club on the Upper Lake at sunset",
    goal: "Chat about Bhopal and plan a Sunday trip to Sanchi.",
    opening: { text: "Kya haal hai, khan? Bhopal kaisa lag raha?", en: "How's it going, my friend? How are you liking Bhopal?" },
    start: ["Bada Talab kitna sundar hai!", "Bhopal bahut shaant shehar hai.", "Tum puraane Bhopal ke ho?"],
    rules: [
      { m: ["pakka", "bye", "mazaa", "milte hain"], text: "Pakka! Sunday subah nikalte hain. 👋", en: "Deal! We'll head out on Sunday morning.", s: ["Bye, Arif!"], end: true, hint: "Pakka, mazaa aayega!" },
      { m: ["baje", "subah"], text: "Subah saat baje, dhoop se pehle.", en: "Seven in the morning, before the sun.", s: ["Pakka, mazaa aayega!"], hint: "Kitne baje?" },
      { m: ["saanchi", "sanchi", "sunday", "bhimbetka", "plan"], text: "Haan! Sunday ko Saanchi ka stupa, aur waapsi mein Bhojpur ka mandir.", en: "Yes! The Sanchi Stupa on Sunday, and the Bhojpur temple on the way back.", s: ["Pakka, mazaa aayega!", "Kitne baje?"], hint: "Sunday ko Saanchi chalein?" },
      { m: ["puraane", "yahin", "born", "ke ho"], text: "Haan, Peer Gate ke paas bada hua hoon. Patiye par baith ke baatein karte the!", en: "Yes, I grew up by Peer Gate. We used to sit on the patiya and chat!", s: ["Sunday ko Saanchi chalein?", "Bhopal bahut shaant shehar hai."], hint: "Tum puraane Bhopal ke ho?" },
      { m: ["shaant", "shehar", "calm"], text: "Haan, isliye toh Bhopal mein sab aaraam se hota hai, khan!", en: "Yes, that's why everything in Bhopal happens at an easy pace, my friend!", s: ["Tum puraane Bhopal ke ho?", "Sunday ko Saanchi chalein?"], hint: "Bhopal bahut shaant shehar hai." },
      { m: ["talab", "lake", "sundar", "sunset"], text: "Haan, isliye Bhopal ko jheelon ka shehar kehte hain.", en: "Yes, that's why they call Bhopal the City of Lakes.", s: ["Bhopal bahut shaant shehar hai.", "Sunday ko Saanchi chalein?"], hint: "Bada Talab kitna sundar hai!" },
    ],
    fallback: { text: "Haha, sahi baat! Bhopal mein sabse achha kya laga?", en: "Haha, true! What do you like most about Bhopal?", s: ["Bada Talab kitna sundar hai!", "Bhopal bahut shaant shehar hai."] } },
});

window.CONTENT_REVIEW.bhopal = { hi: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
  known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Bhopali words (“khan”, “miyan”, “patiya”) are touches in Hindi, not a course in Bhopali.", "Fares and practical tips change over time."],
  note: "Bhopal Hindi (with Bhopali touches): AI-assisted editorial review only, not yet checked by a native speaker from Bhopal." } };

const PLACE_BPL = {
  "new market": ["New Market", "न्यू मार्केट", "New Market"], "mp nagar": ["MP Nagar", "एमपी नगर", "MP Nagar"], "boat club": ["Boat Club", "बोट क्लब", "the Boat Club"],
  "chowk bazaar": ["Chowk Bazaar", "चौक बाज़ार", "Chowk Bazaar"], "arera colony": ["Arera Colony", "अरेरा कॉलोनी", "Arera Colony"], airport: ["airport", "एयरपोर्ट", "the airport"],
  "db mall": ["DB Mall", "डीबी मॉल", "DB Mall"], "bhopal junction": ["Bhopal Junction", "भोपाल जंक्शन", "Bhopal Junction"], "van vihar": ["Van Vihar", "वन विहार", "Van Vihar"],
  "rani kamlapati": ["Rani Kamlapati", "रानी कमलापति", "Rani Kamlapati station"],
};
const BHOPAL_PLACES = ["New Market", "MP Nagar", "Boat Club", "Chowk Bazaar", "Arera Colony", "Airport", "DB Mall", "Bhopal Junction", "Van Vihar", "Rani Kamlapati"];
const bpP = (hi, roman, en, extra) => ({ hi, roman, en, ...(extra || {}) });

window.LOCAL_CONTENT.bhopal = { hi: {
  tutor: {
    greet: "Namaste", places: BHOPAL_PLACES, defaultPlace: "New Market",
    starters: ["I need a ride to New Market.", "How do I order poha-jalebi?", "How do I bargain in Chowk Bazaar?", "What does 'khan' mean?", "Which metro goes to MP Nagar?"],
    glossary: {
      khan: "A friendly Bhopali way to address anyone, whatever their name: “Kya haal hai, khan?”.", miyan: "“Mister / mate”: a friendly address, especially in the old city.",
      patiya: "A wooden platform outside old-city homes where people sit and chat for hours.", batua: "A small drawstring purse; Bhopal's are embroidered with zari and beads.",
      "bada talab": "The Upper Lake, Bhopal's great lake; the Boat Club is on its shore.", magic: "A shared van on a fixed route, paid per seat.",
      sulemani: "Sulemani chai: salty-sweet tea, drunk late at night in the old city.", poha: "Flattened rice with onion and spices: Bhopal's breakfast, with jalebi.",
    },
    intents: [
      { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
        build: (dest) => { const d = PLACE_BPL[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
          bpP(d ? `${d[1]} चलोगे? कितना लोगे?` : "", `${r} chaloge? Kitna loge?`, `Will you go to ${d ? d[2] : dest}? How much?`),
          bpP(d ? `भैया, ${d[1]} चलेंगे?` : "", `Bhaiya, ${r} chalenge?`, `A more polite version: Would you take me to ${d ? d[2] : dest}?`, { label: "More polite" }),
          bpP("पहले किराया बता दीजिए।", "Pehle kiraaya bata dijiye.", "Please tell me the fare first."),
        ], note: "Bhopal's autos rarely use the meter: agree the fare first, or book an app ride. Shared “magic” vans are cheaper on their fixed routes." }; } },
      { m: ["metro", "train", "bus", "platform", "line", "token"], topic: "transport", intro: "At the metro, try:", phrases: [
          bpP("एमपी नगर के लिए कौन सा स्टेशन?", "MP Nagar ke liye kaun sa station?", "Which station for MP Nagar?"), bpP("टोकन कहाँ मिलेगा?", "Token kahan milega?", "Where do I get a token?"),
          bpP("ये मेट्रो एम्स जाती है?", "Ye metro AIIMS jaati hai?", "Does this metro go to AIIMS?"),
        ], note: "Bhopal Metro's Orange Line runs from Subhash Nagar through MP Nagar and Rani Kamlapati to AIIMS (8 stations). Fares are ₹20–40." },
      { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain the Bhopali way:", phrases: [
          bpP("कुछ कम करो, खान।", "Kuch kam karo, khan.", "Come on, a little less."), bpP("ये तो बहुत महँगा है।", "Ye toh bahut mehenga hai.", "That's far too expensive."),
          bpP("आख़िरी दाम बोलो।", "Aakhri daam bolo.", "What's your best price?"),
        ], note: "In Chowk Bazaar and New Market start at about half the first price where there are no price tags." },
      { m: ["price", "how much", "cost", "kitna", "kitne", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
          bpP("ये कितने का है?", "Ye kitne ka hai?", "How much is this?"), bpP("यूपीआई चलेगा?", "UPI chalega?", "Can I pay by UPI?"),
        ] },
      { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "poha", "chai", "bill"], topic: "food", intro: "Ordering food:", phrases: [
          bpP("एक प्लेट पोहा-जलेबी देना।", "Ek plate poha-jalebi dena.", "One plate of poha-jalebi, please."), bpP("मिर्च कम रखना।", "Mirch kam rakhna.", "Not too spicy, please."),
          bpP("बिल दे दीजिए।", "Bill de dijiye.", "Could I have the bill, please?"),
        ], note: "Poha-jalebi in the morning; in the old city, sulemani chai late at night." },
      { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
          bpP("बड़ा तालाब किधर है?", "Bada Talab kidhar hai?", "Which way is the Upper Lake?"), bpP("मैं रास्ता भूल गया हूँ।", "Main raasta bhool gaya hoon.", "I'm lost. (women say: bhool gayi hoon)"),
          bpP("पीर गेट कैसे जाऊँ?", "Peer Gate kaise jaaun?", "How do I get to Peer Gate?"),
        ], note: "The lakes and the old city's gates are the landmarks everyone uses." },
      { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At college or work:", phrases: [
          bpP("आज मेरा पहला दिन है।", "Aaj mera pehla din hai.", "It's my first day today."), bpP("मेरी क्लास किस फ़्लोर पर है?", "Meri class kis floor par hai?", "Which floor is my class on?"),
          bpP("क्या आप मेरी मदद कर सकते हैं?", "Kya aap meri madad kar sakte hain?", "Could you help me?"),
        ] },
      { m: ["friend", "small talk", "chat", "conversation", "weather", "rain", "classmate", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
          bpP("आप कहाँ से हो?", "Aap kahan se ho?", "Where are you from?"), bpP("भोपाल बहुत शांत शहर है।", "Bhopal bahut shaant shehar hai.", "Bhopal is such a calm city."),
          bpP("चाय पिएँगे, खान?", "Chai piyenge, khan?", "Fancy a chai, my friend?"),
        ], note: "Bhopal small talk: the lakes, the food and cricket. “Khan” and “miyan” are friendly with anyone." },
      { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
          bpP("मेरा नाम एलेक्स है।", "Mera naam Alex hai.", "My name is Alex."), bpP("आपका नाम क्या है?", "Aapka naam kya hai?", "What's your name?"),
          bpP("आपसे मिलकर अच्छा लगा।", "Aapse milkar accha laga.", "Nice to meet you."),
        ] },
      { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
          bpP("बहुत-बहुत शुक्रिया!", "Bahut-bahut shukriya!", "Thanks a lot!"), bpP("माफ़ कीजिए।", "Maaf kijiye.", "Sorry / Excuse me."), bpP("सुनिए…", "Suniye…", "Excuse me… (to get attention)"),
        ] },
      { m: ["hello", "hi", "greet", "namaste", "aadaab", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Bhopal:", phrases: [
          bpP("नमस्ते!", "Namaste!", "Hello!"), bpP("क्या हाल है, खान?", "Kya haal hai, khan?", "How's it going, my friend?"),
        ], note: "“Namaste” works with everyone; in the old city, “Aadaab” too. “Kya haal hai, khan?” is for friends." },
      { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
          bpP("मुझे मदद चाहिए।", "Mujhe madad chahiye.", "I need help."), bpP("पास में हॉस्पिटल कहाँ है?", "Paas mein hospital kahan hai?", "Where's the nearest hospital?"),
        ], note: "Emergency number in India: 112." },
    ],
    generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
        bpP("नमस्ते! आप कैसे हैं?", "Namaste! Aap kaise hain?", "Hello! How are you?"), bpP("कितने पैसे हुए?", "Kitne paise hue?", "How much is it?"),
        bpP("क्या आप मेरी मदद कर सकते हैं?", "Kya aap meri madad kar sakte hain?", "Could you help me?"),
      ], note: "Tell me a situation — like “I want to order poha-jalebi” or “ask the way to the Upper Lake” — and I'll give you the exact words." },
  },
  readings: [
    { title: "Asha in Bhopal", level: "A1", lines: [
        bpP("आशा भोपाल में नई है।", "Asha Bhopal mein nayi hai.", "Asha is new in Bhopal."), bpP("वह मेट्रो से एमपी नगर जाती है।", "Vah metro se MP Nagar jaati hai.", "She takes the metro to MP Nagar."),
        bpP("सुबह वह पोहा-जलेबी खाती है।", "Subah vah poha-jalebi khaati hai.", "In the morning she eats poha-jalebi."), bpP("शाम को वह बोट क्लब जाती है।", "Shaam ko vah Boat Club jaati hai.", "In the evening she goes to the Boat Club."),
      ],
      questions: [
        { q: "Where is Asha new?", options: ["Indore", "Bhopal", "Jaipur"], a: 1 }, { q: "What does she eat in the morning?", options: ["Poha-jalebi", "Idli", "Biryani"], a: 0 },
        { q: "Where does she go in the evening?", options: ["The Boat Club", "A mall", "The station"], a: 0 },
      ] },
    { title: "A batua in Chowk Bazaar", level: "A1", lines: [
        bpP("रवि चौक बाज़ार जाता है।", "Ravi Chowk Bazaar jaata hai.", "Ravi goes to Chowk Bazaar."), bpP("उसे एक ज़री का बटुआ पसंद आता है।", "Use ek zari ka batua pasand aata hai.", "He likes a zari batua."),
        bpP("दुकानदार आठ सौ रुपये माँगता है।", "Dukaandaar aath sau rupaye maangta hai.", "The shopkeeper asks for eight hundred rupees."), bpP("रवि चार सौ में ले लेता है।", "Ravi chaar sau mein le leta hai.", "Ravi buys it for four hundred."),
      ],
      questions: [
        { q: "Where does Ravi go?", options: ["Chowk Bazaar", "New Market", "DB Mall"], a: 0 }, { q: "What does he like?", options: ["A batua", "A kurta", "A book"], a: 0 },
        { q: "How much does he pay?", options: ["₹800", "₹400", "₹40"], a: 1 },
      ] },
  ],
  placement: [
    { q: "What does “khan” mean when a Bhopali says “Kya haal hai, khan?”", options: ["Uncle", "A friendly “mate”", "Shopkeeper", "Goodbye"], a: 1 },
    { q: "How would you ask an auto driver to go to New Market?", options: ["New Market chaloge?", "Kitne paise hue?", "Mirch kam rakhna.", "Phir milte hain!"], a: 0 },
    { q: "What does “kitna kiraaya loge” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
    { q: "“Seedhe jaiye, phir baayen mudiye” means…", options: ["Stop here", "Go straight, then turn left", "Turn right twice", "Wait for the bus"], a: 1 },
    { q: "What is Bhopal's famous breakfast?", options: ["Poha-jalebi", "Idli-vada", "Vada pav", "Chhole bhature"], a: 0 },
  ],
  achievements: {
    "auto-pro": ["🛺", "Fair-fare pro", "Agreed a fair auto fare"], foodie: ["🥣", "Poha lover", "Ordered a Bhopal breakfast"], bargainer: ["👛", "Chowk bargainer", "Won a bargain"],
  },
  rightNow: [
    [5, 11, "🥣", "Poha time", "Breakfast stalls are busiest now. Order poha-jalebi like a local.", "bpl_food", bpP("एक प्लेट पोहा-जलेबी देना।", "Ek plate poha-jalebi dena.", "One plate of poha-jalebi, please.")],
    [11, 15, "🕌", "Old city hours", "The Taj-ul-Masajid and Chowk Bazaar are open.", "bpl_directions", bpP("ताज-उल-मसाजिद किधर है?", "Taj-ul-Masajid kidhar hai?", "Which way is the Taj-ul-Masajid?")],
    [15, 18, "👛", "Market hours", "Chowk Bazaar is buzzing. Time to bargain.", "bpl_shopping", bpP("कुछ कम करो, खान।", "Kuch kam karo, khan.", "Come on, a little less.")],
    [18, 22, "🌅", "Sunset at the lake", "The Boat Club on the Upper Lake is where Bhopal spends its evenings.", "bpl_smalltalk", bpP("बड़ा तालाब कितना सुंदर है!", "Bada Talab kitna sundar hai!", "The Upper Lake is so beautiful!")],
    [22, 29, "🌙", "Late night ride home", "Autos charge more at night. Agree on the fare first.", "bpl_auto", bpP("पहले किराया बता दीजिए।", "Pehle kiraaya bata dijiye.", "Please tell me the fare first.")],
  ],
  priceSay: (max, mid) => ({
    ticket: bpP("एमपी नगर का एक टोकन दीजिए।", "MP Nagar ka ek token dijiye.", "One token to MP Nagar, please."), meter: bpP("पहले किराया बता दीजिए।", "Pehle kiraaya bata dijiye.", "Please tell me the fare first."),
    fair: bpP("ठीक है, दे दो।", "Theek hai, de do.", "Okay, I'll take it."), counter: bpP(`${max} में दोगे?`, `${max} mein doge?`, `Will you do it for ₹${max}?`),
    high: bpP(`ये तो बहुत महँगा है। ${mid} में दोगे?`, `Ye toh bahut mehenga hai. ${mid} mein doge?`, `That's far too expensive. Will you do ₹${mid}?`),
  }),
} };

// Shimla First Week pack, in Hindi (the English view shows the same pack in English first): Shimla's Hindi with Himachali touches ("Ram Ram"
// as a greeting, "bhaiji" and "didi ji", siddu and dham). AI-assisted editorial review only.
window.PACKS.shimla = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your landlady and introduce yourself.",
    situation: "You've just rented a room in Sanjauli. Mrs Negi, your landlady, comes to say hello.", scenario: "shm_greetings",
    tip: "“Namaste” works with everyone, and in Himachal “Ram Ram” is a warm everyday greeting. Add “ji” to be polite: “bhaiji”, “didi ji”.",
    phrases: [
      { hi: "नमस्ते आंटी! आप कैसी हैं?", roman: "Namaste aunty! Aap kaisi hain?", en: "Hello aunty! How are you?", natural: "Hello! How are you?" },
      { hi: "मेरा नाम एलेक्स है।", roman: "Mera naam Alex hai.", en: "My name is Alex.", natural: "I'm Alex." },
      { hi: "मैं शिमला में नया हूँ।", roman: "Main Shimla mein naya hoon.", en: "I am new in Shimla.", natural: "I'm new to Shimla.", fem: { hi: "मैं शिमला में नई हूँ।", roman: "Main Shimla mein nayi hoon." } },
      { hi: "यहाँ पानी कब आता है?", roman: "Yahan paani kab aata hai?", en: "Here when does water come?", natural: "When does the water come here?" },
      { hi: "बहुत-बहुत धन्यवाद!", roman: "Bahut-bahut dhanyavaad!", en: "Very many thanks!", natural: "Thank you so much!" },
    ] },
  { day: 2, key: "transport", icon: "🚕", title: "Transport", desc: "Take taxis, HRTC buses and the Lift up to the Mall.",
    situation: "You've arrived at the Tutikandi bus stand (ISBT) and need to get to the Lift, below the Mall.", scenario: "shm_taxi",
    tip: "Shimla has no autos: the hills are too steep. Taxis charge union rates (agree the fare first), HRTC buses run along Cart Road, and the public Lift carries you from Cart Road up to the Mall. The Mall and the Ridge are for walking only.",
    phrases: [
      { hi: "लिफ़्ट तक चलोगे?", roman: "Lift tak chaloge?", en: "Will you go up to the Lift?", natural: "Will you go to the Lift?" },
      { hi: "कितना लोगे?", roman: "Kitna loge?", en: "How much will you take?", natural: "How much will it cost?" },
      { hi: "तीन सौ में चलो।", roman: "Teen sau mein chalo.", en: "Go for three hundred.", natural: "Let's go for three hundred." },
      { hi: "बस कहाँ से मिलेगी?", roman: "Bus kahan se milegi?", en: "From where will the bus be got?", natural: "Where can I get a bus?" },
      { hi: "बस, यहीं उतार दो।", roman: "Bas, yahin utaar do.", en: "Enough, drop me right here.", natural: "Just drop me here." },
    ] },
  { day: 3, key: "food", icon: "🍽️", title: "Food", desc: "Siddu with ghee, a hot chai, and the Himachali dham.",
    situation: "Lunch at a dhaba in Lower Bazaar.", scenario: "shm_food",
    tip: "Siddu is a steamed bread stuffed with walnut or poppy seed, eaten with ghee. Dham, the Himachali feast of rice, madra and sweet rice, is cooked for weddings and festivals. On the Mall, a coffee at the Indian Coffee House is a Shimla habit.",
    phrases: [
      { hi: "एक प्लेट सिड्डू देना।", roman: "Ek plate siddu dena.", en: "Give one plate of siddu.", natural: "One plate of siddu, please." },
      { hi: "सिड्डू के साथ घी देना।", roman: "Siddu ke saath ghee dena.", en: "Give ghee with the siddu.", natural: "Ghee with the siddu, please." },
      { hi: "एक चाय भी।", roman: "Ek chai bhi.", en: "One tea too.", natural: "And a chai." },
      { hi: "मिर्च कम रखना।", roman: "Mirch kam rakhna.", en: "Keep the chilli less.", natural: "Not too spicy, please." },
      { hi: "कितने पैसे हुए?", roman: "Kitne paise hue?", en: "How much money did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain for a Kullu topi in Lakkar Bazaar.",
    situation: "You're in Lakkar Bazaar, by the Ridge, looking for a Himachali topi.", scenario: "shm_shopping",
    tip: "Lakkar Bazaar is known for woodwork (walking sticks, toys) and woollens; the Himachali topi with its coloured band is worn with pride. Start at about half the first price where there are no price tags.",
    phrases: [
      { hi: "ये टोपी कितने की है?", roman: "Ye topi kitne ki hai?", en: "This cap is of how much?", natural: "How much is this topi?" },
      { hi: "ये तो बहुत महँगी है।", roman: "Ye toh bahut mehengi hai.", en: "This is very expensive.", natural: "That's far too expensive." },
      { hi: "कुछ कम करो, भाईजी।", roman: "Kuch kam karo, bhaiji.", en: "Make it somewhat less, brother.", natural: "Come on, a little less." },
      { hi: "ये हाथ का काम है?", roman: "Ye haath ka kaam hai?", en: "Is this work of the hand?", natural: "Is this handmade?" },
      { hi: "ठीक है, दे दो।", roman: "Theek hai, de do.", en: "Okay, give it.", natural: "Okay, I'll take it." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way on the Mall, the Ridge and up to Jakhu.",
    situation: "You're at Scandal Point on the Mall and want the Jakhu Temple.", scenario: "shm_directions",
    tip: "Central Shimla hangs off the Mall and the Ridge: Scandal Point, Christ Church and the Lift are the landmarks everyone uses. Jakhu's monkeys snatch glasses and snacks: keep them in your bag.",
    phrases: [
      { hi: "जाखू मंदिर किधर है?", roman: "Jakhu Mandir kidhar hai?", en: "Jakhu Temple is which way?", natural: "Which way is the Jakhu Temple?" },
      { hi: "सीधे जाइए, फिर बाएँ मुड़िए।", roman: "Seedhe jaiye, phir baayen mudiye.", en: "Go straight, then turn left.", natural: "Go straight, then turn left." },
      { hi: "पैदल कितनी दूर है?", roman: "Paidal kitni door hai?", en: "On foot how far is it?", natural: "How far is it on foot?" },
      { hi: "पास में कोई मेडिकल स्टोर है?", roman: "Paas mein koi medical store hai?", en: "Nearby is there any medical store?", natural: "Is there a pharmacy nearby?" },
      { hi: "ज़रा फिर से बताइए।", roman: "Zara phir se bataiye.", en: "Tell a little again.", natural: "Could you say that again?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in with classmates and colleagues.",
    situation: "Your first day at Himachal Pradesh University, Summer Hill.", scenario: "shm_college",
    tip: "Shimla's students are at Himachal Pradesh University in Summer Hill and at colleges around the town. Everything is uphill: people give distances in minutes of climbing, not kilometres.",
    phrases: [
      { hi: "आज मेरा पहला दिन है।", roman: "Aaj mera pehla din hai.", en: "Today is my first day.", natural: "It's my first day today." },
      { hi: "मेरी क्लास किस फ़्लोर पर है?", roman: "Meri class kis floor par hai?", en: "My class is on which floor?", natural: "Which floor is my class on?" },
      { hi: "थोड़ी मदद कर दो ना?", roman: "Thodi madad kar do na?", en: "Do a little help, no?", natural: "Could you help me out?" },
      { hi: "कैंटीन में क्या मिलता है?", roman: "Canteen mein kya milta hai?", en: "In the canteen what is available?", natural: "What do they have in the canteen?" },
      { hi: "फिर मिलते हैं!", roman: "Phir milte hain!", en: "We meet again!", natural: "See you later!" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "Sunset on the Ridge with Ankit, a friend from university.", scenario: "shm_smalltalk",
    tip: "The Ridge is where Shimla meets in the evening. Weekend trips: Kufri, Mashobra and Chail, and snow in December and January. At a festival you may be pulled into a Nati, the Himachali folk dance.",
    phrases: [
      { hi: "यहाँ से पहाड़ कितने सुंदर दिखते हैं!", roman: "Yahan se pahaad kitne sundar dikhte hain!", en: "From here how beautiful the mountains look!", natural: "The mountains look so beautiful from here!" },
      { hi: "शिमला में बहुत ठंड है।", roman: "Shimla mein bahut thand hai.", en: "In Shimla there is a lot of cold.", natural: "It's so cold in Shimla." },
      { hi: "तुम यहीं के हो?", roman: "Tum yahin ke ho?", en: "Are you of right here?", natural: "Are you from here?" },
      { hi: "संडे को कुफ़री चलें?", roman: "Sunday ko Kufri chalein?", en: "Shall we go to Kufri on Sunday?", natural: "Fancy Kufri on Sunday?" },
      { hi: "पक्का, मज़ा आएगा!", roman: "Pakka, mazaa aayega!", en: "Sure, it will be fun!", natural: "Definitely, it'll be fun!" },
    ] },
];

Object.assign(window.SCENARIOS, {
  shm_greetings: { category: "greetings", icon: "🏠", title: "Meet your landlady", partner: "Negi aunty", role: "Landlady", place: "Your rented room in Sanjauli",
    goal: "Greet your landlady, introduce yourself and ask about the water.",
    opening: { text: "Ram Ram! Aap hi Alex hain? Main Negi aunty, makaan-maalkin.", en: "Hello! Are you Alex? I'm Mrs Negi, your landlady." },
    start: ["Ram Ram aunty! Aap kaisi hain?", "Ji, mera naam Alex hai.", "Yahan paani kab aata hai?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "milte hain", "samajh"], text: "Arey, dhanyavaad kis baat ka! Kuch chahiye toh bolna. 🙏", en: "No need to thank me! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Bahut-bahut dhanyavaad!" },
      { m: ["paani", "tanki", "water"], text: "Paani har doosre din subah aata hai. Baaltiyan bhar ke rakhna!", en: "Water comes every other morning. Keep your buckets full!", s: ["Heater chalega?", "Bahut-bahut dhanyavaad!"], hint: "Yahan paani kab aata hai?" },
      { m: ["heater", "thand", "bijli", "geyser"], text: "Haan, heater hai. Sardiyon mein raat ko bahut thand hoti hai.", en: "Yes, there's a heater. Winter nights get very cold.", s: ["Ji, samajh aa gaya.", "Bahut-bahut dhanyavaad!"], hint: "Heater chalega?" },
      { m: ["pehli baar", "naya", "nayi", "new"], text: "Shimla mein swagat hai! Shaam ko Ridge zaroor jaana.", en: "Welcome to Shimla! Do go to the Ridge in the evening.", s: ["Yahan paani kab aata hai?", "Bahut-bahut dhanyavaad!"], hint: "Ji, pehli baar." },
      { m: ["naam", "alex", "name"], text: "Achha naam hai! Shimla pehli baar aana hua?", en: "Nice name! Is this your first time in Shimla?", s: ["Ji, pehli baar.", "Yahan paani kab aata hai?"], hint: "Ji, mera naam Alex hai." },
      { m: ["ram ram", "namaste", "kaisi", "kaise", "hello", " hi "], text: "Main theek hoon, beta! Aapka naam kya hai?", en: "I'm well, dear! What's your name?", s: ["Ji, mera naam Alex hai.", "Yahan paani kab aata hai?"], hint: "Ram Ram aunty! Aap kaisi hain?" },
    ],
    fallback: { text: "Haan ji, boliye. Paani, heater, doodhwala, kya jaanna hai?", en: "Yes, tell me. Water, the heater, the milkman: what would you like to know?", s: ["Yahan paani kab aata hai?", "Heater chalega?"] } },

  shm_taxi: { category: "transport", icon: "🚕", title: "Taxi to the Lift", partner: "Pawan bhai", role: "Taxi driver", place: "The Tutikandi bus stand (ISBT)",
    goal: "Get to the Lift, below the Mall, for a fair fare.", places: ["Lift", "Sanjauli", "Chhota Shimla", "Summer Hill", "Kufri", "Railway Station", "Mashobra", "Boileauganj", "Jakhu"],
    opening: { text: "Kahan jaana hai?", en: "Where to?" },
    start: ["Lift tak chaloge?", "Kitna loge?", "Bus kahan se milegi?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "upi", "milte hain"], text: "Dhanyavaad! Shimla mein maze karo. 🙏", en: "Thank you! Enjoy Shimla.", s: ["Phir milte hain!"], end: true, hint: "Dhanyavaad, bhaiji!" },
      { m: ["utaar", "rok", "yahin", "stop"], text: "Lo, aa gaya Lift! Teen sau rupaye.", en: "Here's the Lift! Three hundred rupees.", s: ["UPI chalega?", "Dhanyavaad, bhaiji!"], hint: "Bas, yahin utaar do." },
      { m: ["teen sau", "300"], text: "Theek hai, teen sau mein chalo. Baitho!", en: "Okay, three hundred it is. Get in!", s: ["Kitni der lagegi?", "Bas, yahin utaar do."], hint: "Teen sau mein chalo." },
      { m: ["bus", "hrtc"], text: "Local bus bahar stand se milti hai, bees-tees rupaye.", en: "Local buses leave from the stand outside, twenty or thirty rupees.", s: ["Nahi, taxi se chalo.", "Kitna loge?"], hint: "Bus kahan se milegi?" },
      { m: ["der", "minute", "time"], text: "Bees minute, Victory Tunnel par jam na ho toh.", en: "Twenty minutes, if there's no jam at Victory Tunnel.", s: ["Theek hai, chalo.", "Bas, yahin utaar do."], hint: "Kitni der lagegi?" },
      { m: ["mall", "ridge"], text: "Mall Road pe gaadi nahi jaati. Lift se upar jaana, das-bees rupaye.", en: "Cars can't go on the Mall. Take the Lift up, ten or twenty rupees.", s: ["Theek hai, chalo.", "Kitna loge?"], hint: "Mall Road tak chaloge?" },
      { m: ["zyaada", "mehenga", "kam"], text: "Achha, saadhe teen sau de dena.", en: "All right, give three hundred and fifty.", s: ["Teen sau mein chalo.", "Theek hai, chalo."], hint: "Bahut zyaada hai, bhaiji." },
      { m: ["kitna", "paise", "kiraaya"], text: "Lift tak? Chaar sau lagenge.", en: "To the Lift? Four hundred.", s: ["Teen sau mein chalo.", "Bahut zyaada hai, bhaiji."], hint: "Kitna loge?" },
      { m: ["lift", "sanjauli", "chhota shimla", "summer hill", "kufri", "railway", "mashobra", "boileauganj", "jakhu", "chaloge"], text: "{place}? Haan, baitho.", en: "{place}? Yes, get in.", s: ["Kitna loge?", "Teen sau mein chalo."], hint: "{place} chaloge?" },
      { m: ["pehli baar", "new"], text: "Swagat hai! Shaam ko Ridge pe zaroor ghoomna.", en: "Welcome! Do take a walk on the Ridge in the evening.", s: ["Kitni der lagegi?", "Bas, yahin utaar do."] },
      { m: ["theek", "chalo", "haan", "ok"], text: "Baitho! Shimla pehli baar?", en: "Get in! First time in Shimla?", s: ["Haan, pehli baar.", "Kitni der lagegi?"] },
    ],
    fallback: { text: "Samjha nahi. Kahan jaana hai?", en: "I didn't get that. Where to?", s: ["Lift tak chaloge?", "Kitna loge?"] } },

  shm_food: { category: "food", icon: "🍽️", title: "Siddu at a dhaba", partner: "Thakur ji", role: "Dhaba owner", place: "A dhaba in Lower Bazaar",
    goal: "Order siddu and a chai, ask about the dham, and pay.",
    opening: { text: "Aao ji! Garam siddu taiyaar hai.", en: "Come in! Hot siddu's ready." },
    start: ["Ek plate siddu dena.", "Mirch kam rakhna.", "Kitne paise hue?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "upi", "lijiye", "milte hain"], text: "Dhanyavaad! Phir aana. 🙏", en: "Thank you! Come again.", s: ["Phir milte hain!"], end: true, hint: "Ye lijiye." },
      { m: ["kitne", "paise", "bill"], text: "Siddu aur chai, assi rupaye.", en: "Siddu and chai, eighty rupees.", s: ["UPI chalega?", "Ye lijiye."], hint: "Kitne paise hue?" },
      { m: ["mirch", "teekha", "spicy"], text: "Theek hai, mirch kam.", en: "Okay, less chilli.", s: ["Dham milega?", "Kitne paise hue?"], hint: "Mirch kam rakhna." },
      { m: ["ghee"], text: "Haan ji! Siddu toh ghee ke saath hi khaate hain.", en: "Of course! Siddu is always eaten with ghee.", s: ["Ek chai bhi.", "Kitne paise hue?"], hint: "Siddu ke saath ghee dena." },
      { m: ["dham", "madra", "thali"], text: "Dham toh shaadi-tyohaar mein banti hai. Par Sunday ko madra-chawal milte hain.", en: "Dham is cooked for weddings and festivals. But on Sundays we have madra and rice.", s: ["Ek chai bhi.", "Kitne paise hue?"], hint: "Dham milega?" },
      { m: ["chai", "coffee"], text: "Ye lo, garam chai! Thand mein yahi chahiye.", en: "Here's a hot chai! Just what you need in the cold.", s: ["Kitne paise hue?", "Dham milega?"], hint: "Ek chai bhi." },
      { m: ["siddu", "plate", "momo"], text: "Ye lo, garam garam! Ghee daalun?", en: "Here you go, piping hot! Shall I add ghee?", s: ["Siddu ke saath ghee dena.", "Mirch kam rakhna."], hint: "Ek plate siddu dena." },
    ],
    fallback: { text: "Siddu, momo, madra, chai... kya loge?", en: "Siddu, momos, madra, chai... what will you have?", s: ["Ek plate siddu dena.", "Ek chai bhi."] } },

  shm_shopping: { category: "shopping", icon: "🧢", title: "A topi in Lakkar Bazaar", partner: "Rajesh bhai", role: "Shopkeeper", place: "Lakkar Bazaar, by the Ridge",
    goal: "Buy a Himachali topi at a fair price.",
    opening: { text: "Aaiye! Asli Kullu topi, haath ki bunaai.", en: "Come in! Real Kullu caps, hand-woven." },
    start: ["Ye topi kitne ki hai?", "Ye haath ka kaam hai?", "Ye toh bahut mehengi hai."],
    rules: [
      { m: ["de do", "pack", "shukriya", "dhanyavaad", "upi", "milte hain"], text: "Ye lijiye! Phir aaiye. 🙏", en: "Here you are! Come again.", s: ["Phir milte hain!"], end: true, hint: "Theek hai, de do." },
      { m: ["teen sau", "dhai sau", "300", "250"], text: "Chaliye, aapke liye teen sau. Isse kam nahi.", en: "All right, three hundred for you. No lower.", s: ["Theek hai, de do.", "UPI chalega?"], hint: "Dhai sau mein doge?" },
      { m: ["mehengi", "mehenga", "kam", "zyaada"], text: "Haath ka kaam hai, ji! Chaliye, saadhe chaar sau.", en: "It's handwork! All right, four hundred and fifty.", s: ["Dhai sau mein doge?", "Kuch kam karo, bhaiji."], hint: "Kuch kam karo, bhaiji." },
      { m: ["haath", "asli", "machine", "bunaai", "wool"], text: "Bilkul, Kullu ki oon, haath se buni hui.", en: "Of course: Kullu wool, woven by hand.", s: ["Ye topi kitne ki hai?", "Ye toh bahut mehengi hai."], hint: "Ye haath ka kaam hai?" },
      { m: ["kitne", "daam", "price"], text: "Ye topi? Chhe sau.", en: "This topi? Six hundred.", s: ["Ye toh bahut mehengi hai.", "Kuch kam karo, bhaiji."], hint: "Ye topi kitne ki hai?" },
    ],
    fallback: { text: "Aaraam se dekhiye. Topi, shawl, lakdi ka saamaan, sab hai.", en: "Take your time. Caps, shawls, woodwork, we have it all.", s: ["Ye topi kitne ki hai?", "Ye haath ka kaam hai?"] } },

  shm_directions: { category: "directions", icon: "🛕", title: "Find the Jakhu Temple", partner: "Verma ji", role: "Passerby", place: "Scandal Point, on the Mall",
    goal: "Find the way to the Jakhu Temple, and a pharmacy.",
    opening: { text: "Kuch dhoondhna hai?", en: "Looking for something?" },
    start: ["Jakhu Mandir kidhar hai?", "Paas mein koi medical store hai?", "Paidal kitni door hai?"],
    rules: [
      { m: ["shukriya", "dhanyavaad", "thank", "samajh", "milte hain"], text: "Koi baat nahi! Bandaron se bach ke. 🙏", en: "Not at all! Watch out for the monkeys.", s: ["Phir milte hain!"], end: true, hint: "Bahut-bahut dhanyavaad!" },
      { m: ["phir se", "dobara", "dheere", "slow"], text: "Ridge se, Christ Church ke paas se upar. Seedhi chadhaai hai.", en: "From the Ridge, up past Christ Church. It's a steep climb.", s: ["Ji, samajh aa gaya.", "Paidal kitni door hai?"], hint: "Zara phir se bataiye." },
      { m: ["medical", "dawai", "chemist", "hospital"], text: "Haan, Mall pe hi, Scandal Point ke paas ek medical store hai.", en: "Yes, there's a pharmacy right on the Mall, by Scandal Point.", s: ["Jakhu Mandir kidhar hai?", "Zara phir se bataiye."], hint: "Paas mein koi medical store hai?" },
      { m: ["ropeway", "rope"], text: "Haan, ropeway bhi hai, paanch minute mein upar.", en: "Yes, there's a ropeway too: five minutes to the top.", s: ["Ji, samajh aa gaya.", "Bahut-bahut dhanyavaad!"], hint: "Ropeway hai kya?" },
      { m: ["paidal", "door", "walk", "der"], text: "Paidal aadha ghanta, chadhaai hai.", en: "Half an hour on foot; it's uphill.", s: ["Ropeway hai kya?", "Bahut-bahut dhanyavaad!"], hint: "Paidal kitni door hai?" },
      { m: ["jakhu", "mandir", "temple", "kidhar"], text: "Ridge se upar jaiye, Christ Church ke baayen se. Raaste mein bandar milenge, chashma sambhaal ke!", en: "Go up from the Ridge, to the left of Christ Church. You'll meet monkeys on the way: hold on to your glasses!", s: ["Paidal kitni door hai?", "Zara phir se bataiye."], hint: "Jakhu Mandir kidhar hai?" },
    ],
    fallback: { text: "Bataiye, kahan jaana hai?", en: "Tell me, where do you need to go?", s: ["Jakhu Mandir kidhar hai?", "Paas mein koi medical store hai?"] } },

  shm_college: { category: "college", icon: "🎓", title: "First day at university", partner: "Kritika", role: "Classmate", place: "Himachal Pradesh University, Summer Hill",
    goal: "Find your class and the canteen, and make a friend.",
    opening: { text: "Hi! Pehla din hai kya? Main Kritika.", en: "Hi! Is it your first day? I'm Kritika." },
    start: ["Haan, aaj mera pehla din hai.", "Meri class kis floor par hai?", "Canteen mein kya milta hai?"],
    rules: [
      { m: ["milte hain", "bye", "thank", "shukriya", "dhanyavaad", "badhiya"], text: "Welcome! Kuch chahiye toh batana. 👋", en: "Welcome! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Thank you, Kritika!" },
      { m: ["canteen", "chai", "momo"], text: "Chai, momos aur Maggi! Break mein chalte hain.", en: "Chai, momos and Maggi! Let's go at the break.", s: ["Badhiya!", "Thank you, Kritika!"], hint: "Canteen mein kya milta hai?" },
      { m: ["madad", "help"], text: "Haan, bilkul! Timetable WhatsApp kar deti hoon.", en: "Of course! I'll WhatsApp you the timetable.", s: ["Canteen mein kya milta hai?", "Thank you, Kritika!"], hint: "Thodi madad kar do na?" },
      { m: ["shehar", "town", "bus", "train"], text: "University bus hai, ya Summer Hill station se toy train!", en: "There's the university bus, or the toy train from Summer Hill station!", s: ["Badhiya!", "Thank you, Kritika!"], hint: "Shehar kaise jaate hain?" },
      { m: ["class", "floor", "room"], text: "Doosre floor par, room do sau paanch.", en: "On the second floor, room 205.", s: ["Thodi madad kar do na?", "Shehar kaise jaate hain?"], hint: "Meri class kis floor par hai?" },
      { m: ["pehla", "haan", "first"], text: "Welcome! Pehle din sab thoda confusing hota hai.", en: "Welcome! Everything's a bit confusing on the first day.", s: ["Meri class kis floor par hai?", "Thodi madad kar do na?"], hint: "Aaj mera pehla din hai." },
    ],
    fallback: { text: "Bolo, kya chahiye? Class, library, ya canteen?", en: "Tell me, what do you need? The class, the library or the canteen?", s: ["Meri class kis floor par hai?", "Canteen mein kya milta hai?"] } },

  shm_smalltalk: { category: "smalltalk", icon: "🌄", title: "Sunset on the Ridge", partner: "Ankit", role: "Friend", place: "The Ridge at sunset",
    goal: "Chat about Shimla and plan a Sunday trip to Kufri.",
    opening: { text: "Kya haal hai? Shimla kaisa lag raha?", en: "How's it going? How are you liking Shimla?" },
    start: ["Yahan se pahaad kitne sundar dikhte hain!", "Shimla mein bahut thand hai.", "Tum yahin ke ho?"],
    rules: [
      { m: ["pakka", "bye", "mazaa", "milte hain"], text: "Pakka! Sunday subah nikalte hain. 👋", en: "Deal! We'll head out on Sunday morning.", s: ["Bye, Ankit!"], end: true, hint: "Pakka, mazaa aayega!" },
      { m: ["baje", "subah"], text: "Subah aath baje, Old Bus Stand se bus.", en: "Eight in the morning, the bus from the Old Bus Stand.", s: ["Pakka, mazaa aayega!"], hint: "Kitne baje?" },
      { m: ["kufri", "sunday", "mashobra", "chail", "plan"], text: "Haan! Sunday ko Kufri, aur sardiyon mein wahan barf bhi milegi.", en: "Yes! Kufri on Sunday, and in winter there's snow there too.", s: ["Pakka, mazaa aayega!", "Kitne baje?"], hint: "Sunday ko Kufri chalein?" },
      { m: ["yahin", "ke ho", "born", "rehte"], text: "Haan, Chhota Shimla mein bada hua hoon. Bachpan mein Ridge pe hi khelte the!", en: "Yes, I grew up in Chhota Shimla. As kids we played right here on the Ridge!", s: ["Sunday ko Kufri chalein?", "Shimla mein bahut thand hai."], hint: "Tum yahin ke ho?" },
      { m: ["thand", "barf", "snow", "sardi"], text: "Abhi kya thand hai! Dec-Jan mein barf padti hai, tab dekhna.", en: "This isn't cold! It snows in December and January: wait till then.", s: ["Tum yahin ke ho?", "Sunday ko Kufri chalein?"], hint: "Shimla mein bahut thand hai." },
      { m: ["pahaad", "sundar", "sunset", "view"], text: "Haan, isliye Shimla ko pahaadon ki rani kehte hain.", en: "Yes, that's why they call Shimla the Queen of the Hills.", s: ["Shimla mein bahut thand hai.", "Sunday ko Kufri chalein?"], hint: "Yahan se pahaad kitne sundar dikhte hain!" },
    ],
    fallback: { text: "Haha, sahi baat! Shimla mein sabse achha kya laga?", en: "Haha, true! What do you like most about Shimla?", s: ["Yahan se pahaad kitne sundar dikhte hain!", "Shimla mein bahut thand hai."] } },
});

window.CONTENT_REVIEW.shimla = { hi: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-26",
  known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Himachali touches (“Ram Ram”, “bhaiji”, siddu, dham) are touches in Hindi, not a course in Pahari.", "Fares and practical tips change over time."],
  note: "Shimla Hindi (with Himachali touches): AI-assisted editorial review only, not yet checked by a native speaker from Shimla." } };

const PLACE_SHM = {
  lift: ["Lift", "लिफ़्ट", "the Lift"], sanjauli: ["Sanjauli", "संजौली", "Sanjauli"], "chhota shimla": ["Chhota Shimla", "छोटा शिमला", "Chhota Shimla"],
  "summer hill": ["Summer Hill", "समर हिल", "Summer Hill"], kufri: ["Kufri", "कुफ़री", "Kufri"], "railway station": ["Railway Station", "रेलवे स्टेशन", "the railway station"],
  mashobra: ["Mashobra", "मशोबरा", "Mashobra"], boileauganj: ["Boileauganj", "बालूगंज", "Boileauganj"], jakhu: ["Jakhu", "जाखू", "Jakhu"],
  "isbt": ["ISBT", "आईएसबीटी", "the Tutikandi bus stand"],
};
const SHIMLA_PLACES = ["Lift", "Sanjauli", "Chhota Shimla", "Summer Hill", "Kufri", "Railway Station", "Mashobra", "Boileauganj", "Jakhu", "ISBT"];
const shP = (hi, roman, en, extra) => ({ hi, roman, en, ...(extra || {}) });

window.LOCAL_CONTENT.shimla = { hi: {
  tutor: {
    greet: "Ram Ram", places: SHIMLA_PLACES, defaultPlace: "Lift",
    starters: ["I need a taxi to the Lift.", "How do I order siddu?", "How do I bargain in Lakkar Bazaar?", "What does 'bhaiji' mean?", "How do I get up to the Mall?"],
    glossary: {
      "ram ram": "A warm everyday greeting in Himachal, used like “namaste”.", bhaiji: "“Brother” with respect: a polite way to address a man you don't know.",
      siddu: "A steamed wheat bread stuffed with walnut or poppy seed, eaten with ghee.", dham: "The Himachali feast of rice, madra, dal and sweet rice, cooked for weddings and festivals.",
      madra: "Chickpeas or beans cooked in yoghurt with spices: a dham favourite.", topi: "The Himachali cap with a coloured woven band.",
      nati: "The Himachali folk dance, danced in a long, slow circle at festivals.", lift: "The public lift that carries people from Cart Road up to the Mall.",
    },
    intents: [
      { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
        build: (dest) => { const d = PLACE_SHM[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: [
          shP(d ? `${d[1]} चलोगे? कितना लोगे?` : "", `${r} chaloge? Kitna loge?`, `Will you go to ${d ? d[2] : dest}? How much?`),
          shP(d ? `भाईजी, ${d[1]} चलेंगे?` : "", `Bhaiji, ${r} chalenge?`, `A more polite version: Would you take me to ${d ? d[2] : dest}?`, { label: "More polite" }),
          shP("पहले किराया बता दीजिए।", "Pehle kiraaya bata dijiye.", "Please tell me the fare first."),
        ], note: "Shimla has no autos. Taxis charge union rates: agree the fare first. The Mall and the Ridge are for walking only." }; } },
      { m: ["bus", "train", "lift", "mall", "ridge", "toy train", "ticket"], topic: "transport", intro: "Getting about, try:", phrases: [
          shP("लिफ़्ट का टिकट कहाँ मिलेगा?", "Lift ka ticket kahan milega?", "Where do I get a ticket for the Lift?"), shP("ये बस संजौली जाती है?", "Ye bus Sanjauli jaati hai?", "Does this bus go to Sanjauli?"),
          shP("माल रोड कैसे जाऊँ?", "Mall Road kaise jaaun?", "How do I get to the Mall?"),
        ], note: "The public Lift carries you from Cart Road up to the Mall; HRTC buses run along Cart Road. The toy train from Kalka ends at Shimla station." },
      { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
          shP("कुछ कम करो, भाईजी।", "Kuch kam karo, bhaiji.", "Come on, a little less."), shP("ये तो बहुत महँगा है।", "Ye toh bahut mehenga hai.", "That's far too expensive."),
          shP("आख़िरी दाम बोलो।", "Aakhri daam bolo.", "What's your best price?"),
        ], note: "In Lakkar Bazaar and Lower Bazaar start at about half the first price where there are no price tags; shops on the Mall usually have fixed prices." },
      { m: ["price", "how much", "cost", "kitna", "kitne", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
          shP("ये कितने का है?", "Ye kitne ka hai?", "How much is this?"), shP("यूपीआई चलेगा?", "UPI chalega?", "Can I pay by UPI?"),
        ] },
      { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "siddu", "chai", "bill"], topic: "food", intro: "Ordering food:", phrases: [
          shP("एक प्लेट सिड्डू देना।", "Ek plate siddu dena.", "One plate of siddu, please."), shP("मिर्च कम रखना।", "Mirch kam rakhna.", "Not too spicy, please."),
          shP("बिल दे दीजिए।", "Bill de dijiye.", "Could I have the bill, please?"),
        ], note: "Siddu with ghee and a hot chai; ask about madra, and if you're invited to a wedding, the dham." },
      { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
          shP("रिज किधर है?", "Ridge kidhar hai?", "Which way is the Ridge?"), shP("मैं रास्ता भूल गया हूँ।", "Main raasta bhool gaya hoon.", "I'm lost. (women say: bhool gayi hoon)"),
          shP("जाखू मंदिर कैसे जाऊँ?", "Jakhu Mandir kaise jaaun?", "How do I get to the Jakhu Temple?"),
        ], note: "The Mall, the Ridge, Scandal Point and Christ Church are the landmarks everyone uses. Mind the monkeys near Jakhu." },
      { m: ["class", "college", "university", "professor", "teacher", "office", "work", "colleague", "canteen", "meeting"], topic: "college", intro: "At college or work:", phrases: [
          shP("आज मेरा पहला दिन है।", "Aaj mera pehla din hai.", "It's my first day today."), shP("मेरी क्लास किस फ़्लोर पर है?", "Meri class kis floor par hai?", "Which floor is my class on?"),
          shP("क्या आप मेरी मदद कर सकते हैं?", "Kya aap meri madad kar sakte hain?", "Could you help me?"),
        ] },
      { m: ["friend", "small talk", "chat", "conversation", "weather", "snow", "cold", "classmate", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
          shP("आप कहाँ से हो?", "Aap kahan se ho?", "Where are you from?"), shP("शिमला में बहुत ठंड है।", "Shimla mein bahut thand hai.", "It's so cold in Shimla."),
          shP("चाय पिएँगे?", "Chai piyenge?", "Fancy a chai?"),
        ], note: "Shimla small talk: the weather, the snow, the view and weekend trips to Kufri." },
      { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
          shP("मेरा नाम एलेक्स है।", "Mera naam Alex hai.", "My name is Alex."), shP("आपका नाम क्या है?", "Aapka naam kya hai?", "What's your name?"),
          shP("आपसे मिलकर अच्छा लगा।", "Aapse milkar accha laga.", "Nice to meet you."),
        ] },
      { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
          shP("बहुत-बहुत धन्यवाद!", "Bahut-bahut dhanyavaad!", "Thanks a lot!"), shP("माफ़ कीजिए।", "Maaf kijiye.", "Sorry / Excuse me."), shP("सुनिए…", "Suniye…", "Excuse me… (to get attention)"),
        ] },
      { m: ["hello", "hi", "greet", "namaste", "ram ram", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere in Shimla:", phrases: [
          shP("नमस्ते!", "Namaste!", "Hello!"), shP("राम राम जी!", "Ram Ram ji!", "Hello! (a warm Himachali greeting)"),
        ], note: "“Namaste” works with everyone; “Ram Ram” is the warm everyday greeting in Himachal." },
      { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
          shP("मुझे मदद चाहिए।", "Mujhe madad chahiye.", "I need help."), shP("पास में हॉस्पिटल कहाँ है?", "Paas mein hospital kahan hai?", "Where's the nearest hospital?"),
        ], note: "Emergency number in India: 112." },
    ],
    generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: [
        shP("नमस्ते! आप कैसे हैं?", "Namaste! Aap kaise hain?", "Hello! How are you?"), shP("कितने पैसे हुए?", "Kitne paise hue?", "How much is it?"),
        shP("क्या आप मेरी मदद कर सकते हैं?", "Kya aap meri madad kar sakte hain?", "Could you help me?"),
      ], note: "Tell me a situation — like “I want to order siddu” or “ask the way to the Ridge” — and I'll give you the exact words." },
  },
  readings: [
    { title: "Meera in Shimla", level: "A1", lines: [
        shP("मीरा शिमला में नई है।", "Meera Shimla mein nayi hai.", "Meera is new in Shimla."), shP("वह लिफ़्ट से माल रोड जाती है।", "Vah lift se Mall Road jaati hai.", "She takes the Lift to the Mall."),
        shP("दोपहर में वह सिड्डू खाती है।", "Dopahar mein vah siddu khaati hai.", "At lunchtime she eats siddu."), shP("शाम को वह रिज पर घूमती है।", "Shaam ko vah Ridge par ghoomti hai.", "In the evening she walks on the Ridge."),
      ],
      questions: [
        { q: "Where is Meera new?", options: ["Manali", "Shimla", "Dehradun"], a: 1 }, { q: "What does she eat at lunchtime?", options: ["Siddu", "Idli", "Biryani"], a: 0 },
        { q: "Where does she walk in the evening?", options: ["On the Ridge", "In a mall", "At the station"], a: 0 },
      ] },
    { title: "A topi in Lakkar Bazaar", level: "A1", lines: [
        shP("अमन लक्कड़ बाज़ार जाता है।", "Aman Lakkar Bazaar jaata hai.", "Aman goes to Lakkar Bazaar."), shP("उसे एक हिमाचली टोपी पसंद आती है।", "Use ek Himachali topi pasand aati hai.", "He likes a Himachali topi."),
        shP("दुकानदार छह सौ रुपये माँगता है।", "Dukaandaar chhe sau rupaye maangta hai.", "The shopkeeper asks for six hundred rupees."), shP("अमन तीन सौ में ले लेता है।", "Aman teen sau mein le leta hai.", "Aman buys it for three hundred."),
      ],
      questions: [
        { q: "Where does Aman go?", options: ["Lakkar Bazaar", "The Mall", "Kufri"], a: 0 }, { q: "What does he like?", options: ["A topi", "A kurta", "A book"], a: 0 },
        { q: "How much does he pay?", options: ["₹600", "₹300", "₹30"], a: 1 },
      ] },
  ],
  placement: [
    { q: "What does “Ram Ram” mean when someone in Shimla says it to you?", options: ["Goodbye forever", "Hello", "Sorry", "How much?"], a: 1 },
    { q: "How would you ask a taxi driver to go to the Lift?", options: ["Lift tak chaloge?", "Kitne paise hue?", "Mirch kam rakhna.", "Phir milte hain!"], a: 0 },
    { q: "What does “kitna loge” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
    { q: "“Seedhe jaiye, phir baayen mudiye” means…", options: ["Stop here", "Go straight, then turn left", "Turn right twice", "Wait for the bus"], a: 1 },
    { q: "What is siddu?", options: ["A steamed stuffed bread", "A woollen cap", "A folk dance", "A shared taxi"], a: 0 },
  ],
  achievements: {
    "auto-pro": ["🚕", "Fair-fare pro", "Agreed a fair taxi fare"], foodie: ["🥟", "Siddu lover", "Ordered a Himachali meal"], bargainer: ["🧢", "Lakkar Bazaar bargainer", "Won a bargain"],
  },
  rightNow: [
    [5, 11, "☕", "Morning chai", "Dhabas in Lower Bazaar are serving chai and siddu. Order like a local.", "shm_food", shP("एक प्लेट सिड्डू देना।", "Ek plate siddu dena.", "One plate of siddu, please.")],
    [11, 15, "🛕", "Up to Jakhu", "Clear skies are best for the climb to the Jakhu Temple.", "shm_directions", shP("जाखू मंदिर किधर है?", "Jakhu Mandir kidhar hai?", "Which way is the Jakhu Temple?")],
    [15, 18, "🧢", "Market hours", "Lakkar Bazaar is open. Time to bargain.", "shm_shopping", shP("कुछ कम करो, भाईजी।", "Kuch kam karo, bhaiji.", "Come on, a little less.")],
    [18, 22, "🌄", "Sunset on the Ridge", "The Ridge is where Shimla spends its evenings.", "shm_smalltalk", shP("यहाँ से पहाड़ कितने सुंदर दिखते हैं!", "Yahan se pahaad kitne sundar dikhte hain!", "The mountains look so beautiful from here!")],
    [22, 29, "🌙", "Late night ride home", "Few taxis run late. Agree on the fare first.", "shm_taxi", shP("पहले किराया बता दीजिए।", "Pehle kiraaya bata dijiye.", "Please tell me the fare first.")],
  ],
  priceSay: (max, mid) => ({
    ticket: shP("लिफ़्ट का एक टिकट दीजिए।", "Lift ka ek ticket dijiye.", "One ticket for the Lift, please."), meter: shP("पहले किराया बता दीजिए।", "Pehle kiraaya bata dijiye.", "Please tell me the fare first."),
    fair: shP("ठीक है, दे दो।", "Theek hai, de do.", "Okay, I'll take it."), counter: shP(`${max} में दोगे?`, `${max} mein doge?`, `Will you do it for ₹${max}?`),
    high: shP(`ये तो बहुत महँगा है। ${mid} में दोगे?`, `Ye toh bahut mehenga hai. ${mid} mein doge?`, `That's far too expensive. Will you do ₹${mid}?`),
  }),
} };

// Jammu & Kashmir's own First Week pack, in Kashmiri (Srinagar and the Valley), written in Kashmiri's Perso-Arabic script (right to left) with a
// romanised line as learners type it. Kashmiri verbs change with the speaker's gender, so a gendered phrase shows its feminine form.
// DRAFT: an AI-assisted first version with lower confidence than the other languages, especially in the script; awaiting a native speaker.
window.PACKS.jk = [
  { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet your hosts and introduce yourself in Kashmiri.",
    situation: "You've just checked in to a houseboat on the Dal Lake. Bashir sahab, the owner, welcomes you.", scenario: "jk_greetings",
    tip: "“Assalaam alaikum” (or “Namaskar”) is the everyday hello. Kashmiri is polite with “tuhi” (you) and requests ending in -iv: “diyiv” (please give), “kariv” (please do). Call a man “baya” (brother) and a woman “beni” (sister).",
    phrases: [
      { hi: "السلام علیکم! وارےٚ چھِوا؟", roman: "Assalaam alaikum! Vaaray chhivaa?", en: "Peace be upon you! Are you well?", natural: "Hello! How are you?" },
      { hi: "مےٚون ناو چھُ ایلیکس۔", roman: "Myon naav chhu Alex.", en: "My name is Alex.", natural: "I'm Alex." },
      { hi: "بہٕ چھُس یتہِ نوٚو۔", roman: "Bu chhus yeti nov.", en: "I am here new.", natural: "I'm new here.", fem: { hi: "بہٕ چھےس یتہِ نٔو۔", roman: "Bu chhes yeti nev." } },
      { hi: "تُہُنٛد ناو کیاہ چھُ؟", roman: "Tuhund naav kyah chhu?", en: "Your name what is?", natural: "What's your name?" },
      { hi: "واریاہ شُکریہ!", roman: "Vaariyah shukriya!", en: "Many thanks!", natural: "Thank you so much!" },
    ] },
  { day: 2, key: "transport", icon: "🛺", title: "Transport", desc: "Take autos and shikaras, and agree the fare first.",
    situation: "You're at Lal Chowk and need an auto to Nishat Bagh.", scenario: "jk_auto",
    tip: "Srinagar's autos don't use meters: agree the fare before you get in. Shikaras on the Dal Lake have official hourly rates set by the tourism department, but boatmen at Dal Gate often ask for more, so agree the price and the route first.",
    phrases: [
      { hi: "نشاط باغ گژھِو؟", roman: "Nishat Bagh gatshiv?", en: "Nishat Bagh, will you go?", natural: "Will you go to Nishat Bagh?" },
      { hi: "کوتاہ پونٛسہٕ؟", roman: "Kotah poonsa?", en: "How much money?", natural: "How much?" },
      { hi: "واریاہ چھُ، کم کٔرِو۔", roman: "Vaariyah chhu, kam kariv.", en: "It is a lot, please make it less.", natural: "That's a lot, can you lower it?" },
      { hi: "شِکارہ کتہِ میلہِ؟", roman: "Shikaara kati meli?", en: "Shikara, where will it be found?", natural: "Where can I get a shikara?" },
      { hi: "یتہِ رُکِو۔", roman: "Yeti rukiv.", en: "Here please stop.", natural: "Stop here, please." },
    ] },
  { day: 3, key: "food", icon: "🍵", title: "Food", desc: "Order kahwa, noon chai and bread from the kandur.",
    situation: "Tea time at a bakery near Lal Chowk.", scenario: "jk_food",
    tip: "Kashmir drinks kahwa (green tea with saffron and almonds) and pink noon chai (salt tea), with breads from the kandur (baker): girda, lavaas and kulcha. A wazwan is the great Kashmiri feast.",
    phrases: [
      { hi: "اَکھ کہوہ دِیِو۔", roman: "Akh kahwa diyiv.", en: "One kahwa please give.", natural: "One kahwa, please." },
      { hi: "نون چاے چھا؟", roman: "Noon chai chha?", en: "Salt tea, is there?", natural: "Do you have noon chai?" },
      { hi: "زٕ گِردہ دِیِو۔", roman: "Zah girda diyiv.", en: "Two girdas please give.", natural: "Two girdas, please." },
      { hi: "مرٚچ کم۔", roman: "Marats kam.", en: "Chilli less.", natural: "Not too spicy, please." },
      { hi: "کوتاہ گو؟", roman: "Kotah gav?", en: "How much did it become?", natural: "How much is it?" },
    ] },
  { day: 4, key: "shopping", icon: "🧣", title: "Shopping", desc: "Buy a pashmina shawl at a fair price.",
    situation: "You're at a shawl shop on Polo View, near Lal Chowk.", scenario: "jk_shopping",
    tip: "Kashmir's crafts are pashmina shawls, papier-mâché and walnut-wood carving. Ask whether it's real pashmina, and bargain where there are no price tags.",
    phrases: [
      { hi: "یہِ کوتاہ چھُ؟", roman: "Yi kotah chhu?", en: "This, how much is it?", natural: "How much is this?" },
      { hi: "یہِ چھا اَصل پشمینہ؟", roman: "Yi chha asal pashmina?", en: "Is this real pashmina?", natural: "Is this real pashmina?" },
      { hi: "واریاہ مہنگ چھُ۔", roman: "Vaariyah mahang chhu.", en: "It is very expensive.", natural: "That's too expensive." },
      { hi: "بیٚاکھ رنگ چھا؟", roman: "Byakh rang chha?", en: "Another colour, is there?", natural: "Do you have another colour?" },
      { hi: "ٹھیک چھُ، پیک کٔرِو۔", roman: "Theek chhu, pack kariv.", en: "It's fine, please pack it.", natural: "Okay, pack it up." },
    ] },
  { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way round Srinagar.",
    situation: "You're at the clock tower in Lal Chowk and want the Dal Lake.", scenario: "jk_directions",
    tip: "Lal Chowk's clock tower (Ghanta Ghar) is the centre of Srinagar, and the Boulevard runs along the Dal Lake. “Dachhun” is right and “khovur” is left.",
    phrases: [
      { hi: "ڈل کتہِ چھُ؟", roman: "Dal kati chhu?", en: "The Dal, where is it?", natural: "Where's the Dal Lake?" },
      { hi: "سیود گژھِو، پتہٕ دٔچھِن۔", roman: "Syod gatshiv, pata dachhun.", en: "Go straight, then right.", natural: "Go straight, then turn right." },
      { hi: "پیدل کوتاہ وقت لگہِ؟", roman: "Paidal kotah waqt lagi?", en: "On foot how much time will it take?", natural: "How long is it on foot?" },
      { hi: "نزدیک چھا میڈیکل شاپ؟", roman: "Nazdeek chha medical shop?", en: "Nearby, is there a medical shop?", natural: "Is there a pharmacy nearby?" },
      { hi: "آہستہ وَنِو۔", roman: "Aahista vaniv.", en: "Slowly please say.", natural: "Could you speak more slowly?" },
    ] },
  { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in at university and make friends.",
    situation: "Your first day at the University of Kashmir, by the Hazratbal.", scenario: "jk_college",
    tip: "The University of Kashmir's campus is by the Hazratbal shrine and the Dal Lake. Students mix Kashmiri, Urdu and English; use “tuhi” with teachers and new classmates.",
    phrases: [
      { hi: "اَز چھُ مےٚون گۄڈنیُک دۄہ۔", roman: "Az chhu myon gwodaniuk doh.", en: "Today is my first day.", natural: "It's my first day today." },
      { hi: "کلاس کتہِ چھےٚ؟", roman: "Class kati chhe?", en: "The class, where is it?", natural: "Where's the class?" },
      { hi: "مےٚ کٔرِو مدد؟", roman: "Me kariv madad?", en: "Will you do me help?", natural: "Could you help me?" },
      { hi: "چاے چَوَو؟", roman: "Chai chavav?", en: "Shall we drink tea?", natural: "Shall we have some tea?" },
      { hi: "پتہٕ مُلاقات!", roman: "Pata mulaqaat!", en: "Meeting afterwards!", natural: "See you later!" },
    ] },
  { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
    situation: "An evening in the Nishat Bagh with Aamir, a friend from university.", scenario: "jk_smalltalk",
    tip: "Kashmiris love to talk about the seasons, the snow and the food. Gulmarg and Pahalgam are the classic day trips; “Aathwaar” is Sunday.",
    phrases: [
      { hi: "کشیر چھےٚ واریاہ خوبصورت!", roman: "Kasheer chhe vaariyah khoobsoorat!", en: "Kashmir is very beautiful!", natural: "Kashmir is so beautiful!" },
      { hi: "اَز چھُ واریاہ تُر۔", roman: "Az chhu vaariyah tur.", en: "Today it is very cold.", natural: "It's really cold today." },
      { hi: "تُہۍ چھِوا سِرینگرُک؟", roman: "Tuhi chhivaa Sirinagaruk?", en: "Are you of Srinagar?", natural: "Are you from Srinagar?" },
      { hi: "آتھوار گُلمرگ گژھو؟", roman: "Aathwaar Gulmarg gatshav?", en: "Sunday, shall we go to Gulmarg?", natural: "Fancy Gulmarg on Sunday?" },
      { hi: "آ، ضرور!", roman: "Aa, zaroor!", en: "Yes, of course!", natural: "Yes, definitely!" },
    ] },
];

Object.assign(window.SCENARIOS, {
  jk_greetings: { category: "greetings", icon: "🛶", title: "Welcome to the houseboat", partner: "Bashir sahab", role: "Houseboat owner", place: "A houseboat on the Dal Lake",
    goal: "Greet your host, introduce yourself and ask for a kahwa.",
    opening: { text: "Assalaam alaikum! Tuhi chhivaa Alex?", en: "Hello! Are you Alex?" },
    start: ["Assalaam alaikum! Vaaray chhivaa?", "Aa, myon naav chhu Alex.", "Akh kahwa diyiv."],
    rules: [
      { m: ["shukriya", "thank", "khuda hafiz", "mulaqaat"], text: "Kenh zaroorat aasi, vaniv. 🙏", en: "If you need anything, tell me.", s: ["Pata mulaqaat!"], end: true, hint: "Vaariyah shukriya!" },
      { m: ["kahwa", "chai", "chaay"], text: "Aa, kahwa banaavaan! Kesar ti baadaam seeth.", en: "Yes, I'll make kahwa! With saffron and almonds.", s: ["Vaariyah shukriya!", "Pata mulaqaat!"], hint: "Akh kahwa diyiv." },
      { m: ["nov", "nev", "gwodaniuk", "new"], text: "Kasheer manz khosh aamdeed! Shikaara ti ziv karun.", en: "Welcome to Kashmir! Take a shikara ride too.", s: ["Akh kahwa diyiv.", "Vaariyah shukriya!"], hint: "Aa, gwodaniuk lati." },
      { m: ["naav", "alex", "name"], text: "Vaaray! Kasheer chhivaa gwodaniuk lati?", en: "Lovely! Is this your first time in Kashmir?", s: ["Aa, gwodaniuk lati.", "Akh kahwa diyiv."], hint: "Aa, myon naav chhu Alex." },
      { m: ["salaam", "alaikum", "namaskar", "vaaray", "hello"], text: "Vaaray chhus, shukriya! Tuhund naav kyah chhu?", en: "I'm well, thank you! What's your name?", s: ["Aa, myon naav chhu Alex.", "Akh kahwa diyiv."], hint: "Assalaam alaikum! Vaaray chhivaa?" },
    ],
    fallback: { text: "Vaniv, kyah chhu zaroori? Kahwa, poen, shikaara?", en: "Tell me, what do you need? Kahwa, water, a shikara?", s: ["Akh kahwa diyiv.", "Vaariyah shukriya!"] } },

  jk_auto: { category: "transport", icon: "🛺", title: "Auto to Nishat Bagh", partner: "Mushtaq", role: "Auto driver", place: "Lal Chowk",
    goal: "Get to Nishat Bagh for a fair fare.", places: ["Nishat Bagh", "Shalimar Bagh", "Dal Gate", "Hazratbal", "Airport", "Boulevard", "Rajbagh", "Lal Chowk"],
    opening: { text: "Kot gatshun chhu?", en: "Where do you need to go?" },
    start: ["Nishat Bagh gatshiv?", "Kotah poonsa?", "Shikaara kati meli?"],
    rules: [
      { m: ["shukriya", "thank", "upi", "khuda hafiz", "mulaqaat"], text: "Shukriya! Kasheer chhu tuhund. 🙏", en: "Thank you! Kashmir is yours.", s: ["Pata mulaqaat!"], end: true, hint: "Vaariyah shukriya!" },
      { m: ["rukiv", "stop"], text: "Vaatav, Nishat Bagh! Akh hath ti panzaah.", en: "We're here, Nishat Bagh! A hundred and fifty.", s: ["UPI chha?", "Vaariyah shukriya!"], hint: "Yeti rukiv." },
      { m: ["kam kariv", "vaariyah chhu", "kam"], text: "Theek chhu, akh hath.", en: "All right, a hundred.", s: ["Theek chhu, chaliv.", "Yeti rukiv."], hint: "Vaariyah chhu, kam kariv." },
      { m: ["shikaara", "shikara", "boat"], text: "Shikaara meli Dal Gate-as peth. Rate chhu board-as peth lyukhith.", en: "You'll find shikaras at Dal Gate. The rate is written on the board.", s: ["Na, auto-as manz chaliv.", "Kotah poonsa?"], hint: "Shikaara kati meli?" },
      { m: ["kotah", "poonsa", "kiraaya", "price"], text: "Nishat Bagh? Doyi hath.", en: "Nishat Bagh? Two hundred.", s: ["Vaariyah chhu, kam kariv.", "Theek chhu, chaliv."], hint: "Kotah poonsa?" },
      { m: ["nishat", "shalimar", "dal gate", "hazratbal", "airport", "boulevard", "rajbagh", "lal chowk", "gatshiv"], text: "{place}? Aa, bihiv.", en: "{place}? Yes, sit down.", s: ["Kotah poonsa?", "Yeti rukiv."], hint: "{place} gatshiv?" },
      { m: ["theek", "chaliv", "auto"], text: "Bihiv! Kasheer gwodaniuk lati?", en: "Get in! First time in Kashmir?", s: ["Aa, gwodaniuk lati.", "Yeti rukiv."] },
      { m: ["gwodaniuk", "nov", "nev", "new"], text: "Khosh aamdeed! Shaamas Boulevard-as peth pakiv.", en: "Welcome! Take a walk on the Boulevard in the evening.", s: ["Yeti rukiv.", "Vaariyah shukriya!"] },
    ],
    fallback: { text: "Samajh na aav. Kot gatshun chhu?", en: "I didn't get that. Where do you need to go?", s: ["Nishat Bagh gatshiv?", "Kotah poonsa?"] } },

  jk_food: { category: "food", icon: "🍵", title: "Tea at the kandur", partner: "Rafiq", role: "Baker", place: "A kandur (bakery) near Lal Chowk",
    goal: "Order kahwa or noon chai with bread, and pay.",
    opening: { text: "Aaiv, kyah diyav?", en: "Come in, what shall I give you?" },
    start: ["Akh kahwa diyiv.", "Noon chai chha?", "Kotah gav?"],
    rules: [
      { m: ["shukriya", "thank", "upi", "khuda hafiz", "mulaqaat"], text: "Shukriya! Pagah ti aaiv. 🙏", en: "Thank you! Come again tomorrow.", s: ["Pata mulaqaat!"], end: true, hint: "Vaariyah shukriya!" },
      { m: ["kotah", "bill", "poonsa"], text: "Kahwa ti girda, shath rupay.", en: "Kahwa and girda, sixty rupees.", s: ["UPI chha?", "Vaariyah shukriya!"], hint: "Kotah gav?" },
      { m: ["marats", "mirch", "spicy"], text: "Theek, marats kam.", en: "Okay, less chilli.", s: ["Zah girda diyiv.", "Kotah gav?"], hint: "Marats kam." },
      { m: ["noon chai", "noon"], text: "Aa, garam noon chai! Kulcha ti diyav?", en: "Yes, hot noon chai! Shall I give you a kulcha too?", s: ["Zah girda diyiv.", "Kotah gav?"], hint: "Noon chai chha?" },
      { m: ["girda", "kulcha", "lavaas", "tsot"], text: "Ye, taaz girda!", en: "Here you are, fresh girdas!", s: ["Kotah gav?", "Akh kahwa diyiv."], hint: "Zah girda diyiv." },
      { m: ["kahwa", "chai"], text: "Akh kahwa, kesar seeth! Kenh beyi?", en: "One kahwa, with saffron! Anything else?", s: ["Zah girda diyiv.", "Kotah gav?"], hint: "Akh kahwa diyiv." },
    ],
    fallback: { text: "Kahwa, noon chai, girda, kulcha... kyah diyav?", en: "Kahwa, noon chai, girda, kulcha... what shall I give you?", s: ["Akh kahwa diyiv.", "Noon chai chha?"] } },

  jk_shopping: { category: "shopping", icon: "🧣", title: "A pashmina on Polo View", partner: "Showkat", role: "Shopkeeper", place: "A shawl shop on Polo View, near Lal Chowk",
    goal: "Buy a pashmina shawl at a fair price.",
    opening: { text: "Aaiv, vuchiv! Asal Kashir pashmina.", en: "Come in, take a look! Real Kashmiri pashmina." },
    start: ["Yi kotah chhu?", "Yi chha asal pashmina?", "Vaariyah mahang chhu."],
    rules: [
      { m: ["pack", "shukriya", "upi", "mulaqaat"], text: "Pack kor! Pata ti aaiv. 🙏", en: "Packed! Come again.", s: ["Pata mulaqaat!"], end: true, hint: "Theek chhu, pack kariv." },
      { m: ["tsor saas", "trah saas", "4000", "3000"], text: "Theek, tuhund khaatre tsor saas. Kam na.", en: "All right, four thousand for you. No lower.", s: ["Theek chhu, pack kariv.", "UPI chha?"], hint: "Trah saas diyiv?" },
      { m: ["mahang", "kam", "vaariyah"], text: "Asal pashmina chhu! Theek, panch saas.", en: "It's real pashmina! All right, five thousand.", s: ["Trah saas diyiv?", "Theek chhu, pack kariv."], hint: "Vaariyah mahang chhu." },
      { m: ["asal", "real", "pashmina"], text: "Aa, asal! Vuchiv, ring-as manz chhu gatshaan.", en: "Yes, real! Look, it passes through a ring.", s: ["Yi kotah chhu?", "Byakh rang chha?"], hint: "Yi chha asal pashmina?" },
      { m: ["rang", "colour", "color"], text: "Aa, vozul ti neel ti chhu.", en: "Yes, there's red and blue too.", s: ["Yi kotah chhu?", "Theek chhu, pack kariv."], hint: "Byakh rang chha?" },
      { m: ["kotah", "price", "daam"], text: "Yi? Shah saas rupay.", en: "This one? Six thousand rupees.", s: ["Vaariyah mahang chhu.", "Yi chha asal pashmina?"], hint: "Yi kotah chhu?" },
    ],
    fallback: { text: "Aaraam seeth vuchiv. Pashmina, papier-mâché, sab chhu.", en: "Take your time. Pashmina, papier-mâché, we have it all.", s: ["Yi kotah chhu?", "Yi chha asal pashmina?"] } },

  jk_directions: { category: "directions", icon: "🕰️", title: "Find the Dal Lake", partner: "Ghulam Rasool", role: "Passerby", place: "The clock tower, Lal Chowk",
    goal: "Find the way to the Dal Lake, and a pharmacy.",
    opening: { text: "Kyah chhiv tshaandaan?", en: "What are you looking for?" },
    start: ["Dal kati chhu?", "Nazdeek chha medical shop?", "Paidal kotah waqt lagi?"],
    rules: [
      { m: ["shukriya", "thank", "samajh", "mulaqaat"], text: "Kenh na! Vaaray pakiv. 🙏", en: "Not at all! Walk safely.", s: ["Pata mulaqaat!"], end: true, hint: "Vaariyah shukriya!" },
      { m: ["aahista", "beyi", "slow"], text: "Syod, pata dachhun. Bas!", en: "Straight on, then right. That's it!", s: ["Aa, samajh aav.", "Paidal kotah waqt lagi?"], hint: "Aahista vaniv." },
      { m: ["medical", "dawai", "pharmacy", "hospital"], text: "Aa, Ghanta Ghar-as nazdeek chhu akh medical shop.", en: "Yes, there's a pharmacy near the clock tower.", s: ["Dal kati chhu?", "Aahista vaniv."], hint: "Nazdeek chha medical shop?" },
      { m: ["paidal", "waqt", "walk"], text: "Paidal vuh minute, ya auto-as manz paanch.", en: "Twenty minutes on foot, or five by auto.", s: ["Aa, samajh aav.", "Vaariyah shukriya!"], hint: "Paidal kotah waqt lagi?" },
      { m: ["dal", "boulevard", "kati"], text: "Syod gatshiv, pata dachhun. Boulevard-as peth chhu Dal.", en: "Go straight, then turn right. The Dal is along the Boulevard.", s: ["Paidal kotah waqt lagi?", "Aahista vaniv."], hint: "Dal kati chhu?" },
    ],
    fallback: { text: "Vaniv, kot gatshun chhu?", en: "Tell me, where do you need to go?", s: ["Dal kati chhu?", "Nazdeek chha medical shop?"] } },

  jk_college: { category: "college", icon: "🎓", title: "First day at the University of Kashmir", partner: "Insha", role: "Classmate", place: "University of Kashmir, Hazratbal",
    goal: "Find your class, have tea and make a friend.",
    opening: { text: "Hi! Az chhu tuhund gwodaniuk doh? Bu chhes Insha.", en: "Hi! Is it your first day today? I'm Insha." },
    start: ["Aa, az chhu myon gwodaniuk doh.", "Class kati chhe?", "Chai chavav?"],
    rules: [
      { m: ["mulaqaat", "bye", "thank", "shukriya"], text: "Welcome! Kenh zaroorat aasi, vaniv. 👋", en: "Welcome! Tell me if you need anything.", s: ["Pata mulaqaat!"], end: true, hint: "Shukriya, Insha!" },
      { m: ["chai", "canteen", "chavav"], text: "Aa, class-as pata chavav noon chai!", en: "Yes, after class let's have noon chai!", s: ["Shukriya, Insha!", "Pata mulaqaat!"], hint: "Chai chavav?" },
      { m: ["madad", "help"], text: "Aa, zaroor! Timetable soozay WhatsApp-as peth.", en: "Of course! I'll send the timetable on WhatsApp.", s: ["Chai chavav?", "Shukriya, Insha!"], hint: "Me kariv madad?" },
      { m: ["class", "kati", "room"], text: "Class chhe doyimi manzil-as peth.", en: "The class is on the second floor.", s: ["Me kariv madad?", "Chai chavav?"], hint: "Class kati chhe?" },
      { m: ["gwodaniuk", "aa,", "first"], text: "Welcome! Gwodaniuk doh chhu ath-ti mushkil.", en: "Welcome! The first day is always a bit hard.", s: ["Class kati chhe?", "Me kariv madad?"], hint: "Az chhu myon gwodaniuk doh." },
    ],
    fallback: { text: "Vaniv, kyah chhu zaroori? Class, library, chai?", en: "Tell me, what do you need? The class, the library, tea?", s: ["Class kati chhe?", "Chai chavav?"] } },

  jk_smalltalk: { category: "smalltalk", icon: "🌷", title: "An evening in the Nishat Bagh", partner: "Aamir", role: "Friend", place: "The Nishat Bagh at sunset",
    goal: "Chat about Kashmir and plan a Sunday trip to Gulmarg.",
    opening: { text: "Kasheer kyuthaa laagaan?", en: "How are you liking Kashmir?" },
    start: ["Kasheer chhe vaariyah khoobsoorat!", "Az chhu vaariyah tur.", "Tuhi chhivaa Sirinagaruk?"],
    rules: [
      { m: ["zaroor", "bye", "mulaqaat"], text: "Zaroor! Aathwaar subuh nerav. 👋", en: "Definitely! We'll set off on Sunday morning.", s: ["Pata mulaqaat!"], end: true, hint: "Aa, zaroor!" },
      { m: ["baje", "subuh", "waqt"], text: "Subuh sath baje, sheen pheran brounh.", en: "Seven in the morning, before the snow melts.", s: ["Aa, zaroor!"], hint: "Kotah baje?" },
      { m: ["gulmarg", "aathwaar", "sunday", "pahalgam"], text: "Aa! Aathwaar Gulmarg, gondola-as manz.", en: "Yes! Gulmarg on Sunday, on the gondola.", s: ["Aa, zaroor!", "Kotah baje?"], hint: "Aathwaar Gulmarg gatshav?" },
      { m: ["sirinagar", "srinagar", "yeti", "born"], text: "Aa, bu chhus shehr-e-khaas-uk, Jhelum-as nazdeek!", en: "Yes, I'm from the old city, by the Jhelum!", s: ["Aathwaar Gulmarg gatshav?", "Az chhu vaariyah tur."], hint: "Tuhi chhivaa Sirinagaruk?" },
      { m: ["tur", "sheen", "cold", "moasam"], text: "Aa, magar kangri chhu! Ti noon chai.", en: "Yes, but there's the kangri! And noon chai.", s: ["Tuhi chhivaa Sirinagaruk?", "Aathwaar Gulmarg gatshav?"], hint: "Az chhu vaariyah tur." },
      { m: ["khoobsoorat", "kasheer", "kashmir", "bagh"], text: "Aa, Nishat Bagh chhu shaamas sab-ti khoobsoorat.", en: "Yes, the Nishat Bagh is at its most beautiful in the evening.", s: ["Az chhu vaariyah tur.", "Aathwaar Gulmarg gatshav?"], hint: "Kasheer chhe vaariyah khoobsoorat!" },
    ],
    fallback: { text: "Haha, poz chhu! Kasheer manz kyah gav sab-ti vaaray?", en: "Haha, true! What do you like most about Kashmir?", s: ["Kasheer chhe vaariyah khoobsoorat!", "Az chhu vaariyah tur."] } },
});

// Jammu & Kashmir's other two First Week packs: Dogri (Jammu, Devanagari, with a romanised line) and Urdu (the official language understood
// across J&K, Urdu script, right to left). Both change verbs with the speaker's gender, so gendered phrases show their feminine form.
// DRAFT for Dogri: an AI-assisted first version with lower confidence than Hindi or Urdu; awaiting a native speaker.
window.LANGUAGE_PACKS.jk = {
  doi: [
    { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet people in Dogri and introduce yourself.",
      situation: "You've just rented a room in Gandhi Nagar, Jammu. Sharma ji, the landlord, comes to say hello.", scenario: "jk_doi_greetings",
      tip: "“Namaste” and “Ram Ram” are everyday greetings in Jammu, and “Jai Mata Di” is heard everywhere, for the Vaishno Devi pilgrimage. Dogri says “tus” (you, polite) and adds “ji” to be respectful.",
      phrases: [
        { hi: "नमस्ते जी! तुस कियां ओ?", roman: "Namaste ji! Tus kiyaan o?", en: "Hello ji! How are you?", natural: "Hello! How are you?" },
        { hi: "मेरा नां एलेक्स ऐ।", roman: "Mera naan Alex ai.", en: "My name is Alex.", natural: "I'm Alex." },
        { hi: "मैं इत्थें नमां आं।", roman: "Main itthen namaan aan.", en: "I am new here.", natural: "I'm new here.", fem: { hi: "मैं इत्थें नमीं आं।", roman: "Main itthen nameen aan." } },
        { hi: "पानी कदूं औंदा ऐ?", roman: "Paani kadoon aunda ai?", en: "Water, when does it come?", natural: "When does the water come?" },
        { hi: "बड़ा धन्नवाद!", roman: "Bada dhannvaad!", en: "Big thanks!", natural: "Thank you so much!" },
      ] },
    { day: 2, key: "transport", icon: "🚐", title: "Transport", desc: "Take autos and Jammu's matadors.",
      situation: "You've arrived at Jammu Tawi station and need to get to Raghunath Bazaar.", scenario: "jk_doi_auto",
      tip: "Jammu's matadors (shared minibuses) run fixed routes for a few rupees; autos don't use meters, so agree the fare first.",
      phrases: [
        { hi: "रघुनाथ बजार चलगे ओ?", roman: "Raghunath Bazaar chalge o?", en: "Will you go to Raghunath Bazaar?", natural: "Will you go to Raghunath Bazaar?" },
        { hi: "कितने पैसे लग्गन?", roman: "Kitne paise laggan?", en: "How much money will it take?", natural: "How much will it cost?" },
        { hi: "सौ रपे च चलो।", roman: "Sau rape ch chalo.", en: "Go for a hundred rupees.", natural: "Let's go for a hundred." },
        { hi: "मटाडोर कुत्थें थम्मदी ऐ?", roman: "Matador kutthen thammdi ai?", en: "Matador, where does it stop?", natural: "Where does the matador stop?" },
        { hi: "इत्थें रोकी देओ।", roman: "Itthen roki deo.", en: "Stop here.", natural: "Stop here, please." },
      ] },
    { day: 3, key: "food", icon: "🧀", title: "Food", desc: "Try kalari kulcha and rajmah-chawal.",
      situation: "Lunch at a dhaba near the Raghunath Bazaar.", scenario: "jk_doi_food",
      tip: "Try kalari kulcha (fried local cheese in bread) on the street, and Jammu's rajmah-chawal. “Mirch ghat” means less chilli; tea is “chaah”.",
      phrases: [
        { hi: "इक प्लेट कलाड़ी कुलचा देओ।", roman: "Ik plate kalari kulcha deo.", en: "Give one plate of kalari kulcha.", natural: "One kalari kulcha, please." },
        { hi: "मिर्च घट्ट पाओ।", roman: "Mirch ghatt pao.", en: "Put less chilli.", natural: "Not too spicy, please." },
        { hi: "राजमाह्-चौल बी देओ।", roman: "Rajmah-chaul bi deo.", en: "Give rajmah-rice too.", natural: "And some rajmah-chawal." },
        { hi: "इक कप चाह्।", roman: "Ik cup chaah.", en: "One cup of tea.", natural: "A cup of tea, please." },
        { hi: "कितने होए?", roman: "Kitne hoye?", en: "How much did it become?", natural: "How much is it?" },
      ] },
    { day: 4, key: "shopping", icon: "🛍️", title: "Shopping", desc: "Bargain for dry fruits and shawls in Raghunath Bazaar.",
      situation: "You're at a dry-fruit shop in Raghunath Bazaar.", scenario: "jk_doi_shopping",
      tip: "Raghunath Bazaar is Jammu's old market: dry fruits, shawls and basmati. Bargain gently where there are no price tags.",
      phrases: [
        { hi: "एह् कितने दा ऐ?", roman: "Eh kitne da ai?", en: "This is of how much?", natural: "How much is this?" },
        { hi: "बड़ा म्हंगा ऐ।", roman: "Bada mehnga ai.", en: "It's very expensive.", natural: "That's too expensive." },
        { hi: "थोढ़ा घट्ट करो।", roman: "Thodha ghatt karo.", en: "Make it a little less.", natural: "Can you lower it a bit?" },
        { hi: "होर रंग ऐ?", roman: "Hor rang ai?", en: "Is there another colour?", natural: "Do you have another colour?" },
        { hi: "ठीक ऐ, पैक करी देओ।", roman: "Theek ai, pack kari deo.", en: "Okay, pack it.", natural: "Okay, pack it up." },
      ] },
    { day: 5, key: "directions", icon: "🛕", title: "Directions", desc: "Find your way round the City of Temples.",
      situation: "You're in the old city and want the Raghunath Temple.", scenario: "jk_doi_directions",
      tip: "Jammu is the City of Temples: the Raghunath Temple is the old city's landmark, and the Bahu Fort looks over the Tawi. “Sajje” is right and “khabbe” is left.",
      phrases: [
        { hi: "रघुनाथ मंदर कुत्थें ऐ?", roman: "Raghunath Mandar kutthen ai?", en: "Raghunath Temple, where is it?", natural: "Where's the Raghunath Temple?" },
        { hi: "सिद्धे जाओ, फ्ही सज्जे मुड़ो।", roman: "Siddhe jao, phi sajje mudo.", en: "Go straight, then turn right.", natural: "Go straight, then turn right." },
        { hi: "पैदल कितना दूर ऐ?", roman: "Paidal kitna door ai?", en: "On foot how far is it?", natural: "How far is it on foot?" },
        { hi: "नेड़ें कोई दुआई दी हट्टी ऐ?", roman: "Neden koi duaai di hatti ai?", en: "Nearby is there any medicine shop?", natural: "Is there a pharmacy nearby?" },
        { hi: "फ्ही दस्सो, जी।", roman: "Phi dasso, ji.", en: "Tell again, ji.", natural: "Could you say that again?" },
      ] },
    { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in with classmates and colleagues.",
      situation: "Your first day at the University of Jammu.", scenario: "jk_doi_college",
      tip: "The University of Jammu's campus is by the Tawi. Students mix Dogri, Hindi, Punjabi and English; “tus” and “ji” are always polite.",
      phrases: [
        { hi: "अज्ज मेरा पैह्ला दिन ऐ।", roman: "Ajj mera paihla din ai.", en: "Today is my first day.", natural: "It's my first day today." },
        { hi: "क्लास कुत्थें ऐ?", roman: "Class kutthen ai?", en: "The class, where is it?", natural: "Where's the class?" },
        { hi: "थोढ़ी मदद करी देओ?", roman: "Thodhi madad kari deo?", en: "Do a little help?", natural: "Could you help me a bit?" },
        { hi: "कैंटीन च चाह् पीचै?", roman: "Canteen ch chaah peechai?", en: "Shall we drink tea in the canteen?", natural: "Shall we get tea at the canteen?" },
        { hi: "फ्ही मिलचै!", roman: "Phi milchai!", en: "Let's meet again!", natural: "See you later!" },
      ] },
    { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
      situation: "An evening at the Bagh-e-Bahu gardens by the Tawi with Ankush, a friend from university.", scenario: "jk_doi_smalltalk",
      tip: "Weekend trips from Jammu: the Vaishno Devi shrine above Katra, and Patnitop in the hills. “Jai Mata Di!” is the greeting on the way up.",
      phrases: [
        { hi: "बाग-ए-बाहु किन्ना सोह्णा ऐ!", roman: "Bagh-e-Bahu kinna sohna ai!", en: "How beautiful the Bagh-e-Bahu is!", natural: "The Bagh-e-Bahu is so beautiful!" },
        { hi: "जम्मू च गर्मी बड़ी ऐ, ना?", roman: "Jammu ch garmi badi ai, na?", en: "In Jammu the heat is a lot, no?", natural: "It's really hot in Jammu, isn't it?" },
        { hi: "तुस जम्मू दे ओ?", roman: "Tus Jammu de o?", en: "Are you of Jammu?", natural: "Are you from Jammu?" },
        { hi: "ऐतवार कटड़ा चलचै?", roman: "Aitwaar Katra chalchai?", en: "Sunday shall we go to Katra?", natural: "Fancy Katra on Sunday?" },
        { hi: "पक्का, जै माता दी!", roman: "Pakka, Jai Mata Di!", en: "Sure, victory to the Mother Goddess!", natural: "Definitely! Jai Mata Di!" },
      ] },
  ],
  ur: [
    { day: 1, key: "greetings", icon: "👋", title: "Greetings", desc: "Greet people politely in Urdu and introduce yourself.",
      situation: "You've just rented a room in Rajbagh, Srinagar. Mir sahab, your landlord, welcomes you.", scenario: "jk_ur_greetings",
      tip: "Urdu is J&K's official language and is understood in Srinagar and Jammu alike. Greet with “Assalaam alaikum” or “Aadaab”, and use “aap” with everyone you've just met.",
      phrases: [
        { hi: "السلام علیکم! مزاج کیسے ہیں؟", roman: "Assalaam alaikum! Mizaaj kaise hain?", en: "Peace be upon you! How is your temper?", natural: "Hello! How are you?" },
        { hi: "میرا نام ایلکس ہے۔", roman: "Mera naam Alex hai.", en: "My name is Alex.", natural: "I'm Alex." },
        { hi: "میں یہاں نیا ہوں۔", roman: "Main yahan naya hoon.", en: "I am new here.", natural: "I'm new here.", fem: { hi: "میں یہاں نئی ہوں۔", roman: "Main yahan nayi hoon." } },
        { hi: "آپ سے مل کر خوشی ہوئی۔", roman: "Aap se mil kar khushi hui.", en: "Having met you, happiness happened.", natural: "It's a pleasure to meet you." },
        { hi: "بہت مہربانی!", roman: "Bahut meherbaani!", en: "Much kindness!", natural: "Thank you so much!" },
      ] },
    { day: 2, key: "transport", icon: "🛶", title: "Transport", desc: "Take an auto and a shikara, and agree the fare first.",
      situation: "You're at Lal Chowk and need to get to Dal Gate.", scenario: "jk_ur_auto",
      tip: "Autos in Srinagar and Jammu don't use meters: agree the fare first. On the Dal Lake, the tourism department sets an official hourly rate for shikaras; ask to see it.",
      phrases: [
        { hi: "ڈل گیٹ چلیں گے؟", roman: "Dal Gate chalenge?", en: "Will you go to Dal Gate?", natural: "Will you go to Dal Gate?" },
        { hi: "کتنا کرایہ ہوگا؟", roman: "Kitna kiraaya hoga?", en: "How much will the fare be?", natural: "What's the fare?" },
        { hi: "تھوڑا کم کیجیے۔", roman: "Thoda kam kijiye.", en: "Make it a little less.", natural: "Can you lower it a bit?" },
        { hi: "شکارا کہاں ملے گا؟", roman: "Shikaara kahan milega?", en: "Where will a shikara be found?", natural: "Where can I get a shikara?" },
        { hi: "یہاں روک دیجیے۔", roman: "Yahan rok dijiye.", en: "Stop here.", natural: "Stop here, please." },
      ] },
    { day: 3, key: "food", icon: "🍵", title: "Food", desc: "Order kahwa, noon chai and Kashmiri bread.",
      situation: "Breakfast at a café on Residency Road, Srinagar.", scenario: "jk_ur_food",
      tip: "Order kahwa (saffron green tea) or noon chai (pink salt tea) with fresh bread from the kandur; for a feast, a wazwan.",
      phrases: [
        { hi: "ایک قہوہ دیجیے۔", roman: "Ek kahwa dijiye.", en: "Give one kahwa.", natural: "One kahwa, please." },
        { hi: "نون چائے ملے گی؟", roman: "Noon chai milegi?", en: "Will salt tea be had?", natural: "Do you have noon chai?" },
        { hi: "دو کلچے دیجیے۔", roman: "Do kulche dijiye.", en: "Give two kulchas.", natural: "Two kulchas, please." },
        { hi: "مرچ کم رکھیے۔", roman: "Mirch kam rakhiye.", en: "Keep the chilli less.", natural: "Not too spicy, please." },
        { hi: "کتنے پیسے ہوئے؟", roman: "Kitne paise hue?", en: "How much money did it become?", natural: "How much is it?" },
      ] },
    { day: 4, key: "shopping", icon: "🧣", title: "Shopping", desc: "Buy a shawl at a fair price.",
      situation: "You're at a shawl shop on Residency Road.", scenario: "jk_ur_shopping",
      tip: "Ask whether a pashmina is real (“asli pashmina hai?”), and bargain where there are no price tags. Government emporiums have fixed prices.",
      phrases: [
        { hi: "یہ شال کتنے کی ہے؟", roman: "Ye shawl kitne ki hai?", en: "This shawl is of how much?", natural: "How much is this shawl?" },
        { hi: "کیا یہ اصلی پشمینہ ہے؟", roman: "Kya ye asli pashmina hai?", en: "Is this real pashmina?", natural: "Is this real pashmina?" },
        { hi: "بہت مہنگی ہے۔", roman: "Bahut mehngi hai.", en: "It is very expensive.", natural: "That's too expensive." },
        { hi: "دوسرا رنگ دکھائیے۔", roman: "Doosra rang dikhaaiye.", en: "Show another colour.", natural: "Could you show me another colour?" },
        { hi: "ٹھیک ہے، پیک کر دیجیے۔", roman: "Theek hai, pack kar dijiye.", en: "Okay, pack it.", natural: "Okay, pack it up." },
      ] },
    { day: 5, key: "directions", icon: "📍", title: "Directions", desc: "Find your way in Jammu's old city.",
      situation: "You're near the Jammu bus stand and want the Raghunath Temple.", scenario: "jk_ur_directions",
      tip: "In Jammu the Raghunath Temple and the bazaar around it are the landmarks; in Srinagar, Lal Chowk's clock tower.",
      phrases: [
        { hi: "رگھوناتھ مندر کس طرف ہے؟", roman: "Raghunath Mandir kis taraf hai?", en: "Raghunath Temple is on which side?", natural: "Which way is the Raghunath Temple?" },
        { hi: "سیدھے جائیے، پھر دائیں مڑیے۔", roman: "Seedhe jaaiye, phir daayen mudiye.", en: "Go straight, then turn right.", natural: "Go straight, then turn right." },
        { hi: "پیدل کتنی دور ہے؟", roman: "Paidal kitni door hai?", en: "On foot how far is it?", natural: "How far is it on foot?" },
        { hi: "قریب میں دواخانہ ہے؟", roman: "Qareeb mein dawakhana hai?", en: "Nearby is there a pharmacy?", natural: "Is there a pharmacy nearby?" },
        { hi: "ذرا آہستہ بولیے۔", roman: "Zara aahista boliye.", en: "Speak a little slowly.", natural: "Could you speak a bit more slowly?" },
      ] },
    { day: 6, key: "college", icon: "🎓", title: "College & Work", desc: "Settle in at university and make friends.",
      situation: "Your first day at the University of Kashmir in Srinagar.", scenario: "jk_ur_college",
      tip: "Urdu is the shared language of classes across J&K, alongside English. Use “aap” with teachers and new classmates.",
      phrases: [
        { hi: "آج میرا پہلا دن ہے۔", roman: "Aaj mera pehla din hai.", en: "Today is my first day.", natural: "It's my first day today." },
        { hi: "لائبریری کہاں ہے؟", roman: "Library kahan hai?", en: "Where is the library?", natural: "Where's the library?" },
        { hi: "کیا آپ میری مدد کریں گے؟", roman: "Kya aap meri madad karenge?", en: "Will you do my help?", natural: "Could you help me?" },
        { hi: "کینٹین میں چائے پئیں؟", roman: "Canteen mein chai piyen?", en: "Shall we drink tea in the canteen?", natural: "Shall we get tea at the canteen?" },
        { hi: "پھر ملتے ہیں!", roman: "Phir milte hain!", en: "We meet again!", natural: "See you later!" },
      ] },
    { day: 7, key: "smalltalk", icon: "🗣️", title: "Real Conversation", desc: "Put everything together in a natural conversation.",
      situation: "An evening in the Shalimar Bagh with Zoya, a friend from university.", scenario: "jk_ur_smalltalk",
      tip: "Small talk in J&K: the weather, the snow, the gardens and the food. Gulmarg, Pahalgam and Sonamarg are the classic trips.",
      phrases: [
        { hi: "کشمیر کتنا خوبصورت ہے!", roman: "Kashmir kitna khoobsoorat hai!", en: "How beautiful Kashmir is!", natural: "Kashmir is so beautiful!" },
        { hi: "آج بہت سردی ہے۔", roman: "Aaj bahut sardi hai.", en: "Today there is much cold.", natural: "It's really cold today." },
        { hi: "آپ کہاں کی ہیں؟", roman: "Aap kahan ki hain?", en: "Where are you from? (to a woman)", natural: "Where are you from?" },
        { hi: "اتوار کو گلمرگ چلیں؟", roman: "Itwaar ko Gulmarg chalein?", en: "Shall we go to Gulmarg on Sunday?", natural: "Fancy Gulmarg on Sunday?" },
        { hi: "ضرور، بہت مزہ آئے گا!", roman: "Zaroor, bahut mazaa aayega!", en: "Certainly, much fun will come!", natural: "Definitely, it'll be great fun!" },
      ] },
  ],
};

Object.assign(window.SCENARIOS, {
  // ---------- Dogri, in Jammu ----------
  jk_doi_greetings: { category: "greetings", icon: "🏠", title: "Meet your landlord", partner: "Sharma ji", role: "Landlord", place: "Your rented room in Gandhi Nagar, Jammu",
    goal: "Greet your landlord, introduce yourself and ask about the water.",
    opening: { text: "Namaste ji! Tus Alex o?", en: "Hello! Are you Alex?" },
    start: ["Namaste ji! Tus kiyaan o?", "Haan ji, mera naan Alex ai.", "Paani kadoon aunda ai?"],
    rules: [
      { m: ["dhannvaad", "shukriya", "thank", "milchai", "samajh"], text: "Koi gal nahin! Kish chahida hove, dasso. 🙏", en: "No problem! Tell me if you need anything.", s: ["Phi milchai!"], end: true, hint: "Bada dhannvaad!" },
      { m: ["paani", "bijli", "light"], text: "Paani savere chhe baje aunda ai, te shaami ik ghanta.", en: "Water comes at six in the morning, and for an hour in the evening.", s: ["Theek ai, samajh aayi gaya.", "Bada dhannvaad!"], hint: "Paani kadoon aunda ai?" },
      { m: ["namaan", "nameen", "pehli baar", "new"], text: "Jammu ch swagat ai! Raghunath Mandar zaroor dikhna.", en: "Welcome to Jammu! Do see the Raghunath Temple.", s: ["Paani kadoon aunda ai?", "Bada dhannvaad!"], hint: "Haan ji, pehli baar." },
      { m: ["naan", "alex", "name"], text: "Bada changa naan ai! Jammu pehli baar?", en: "Lovely name! First time in Jammu?", s: ["Haan ji, pehli baar.", "Paani kadoon aunda ai?"], hint: "Haan ji, mera naan Alex ai." },
      { m: ["namaste", "ram ram", "kiyaan", "jai mata", "hello"], text: "Main theek aan, ji! Tusen da naan ki ai?", en: "I'm well! What's your name?", s: ["Haan ji, mera naan Alex ai.", "Paani kadoon aunda ai?"], hint: "Namaste ji! Tus kiyaan o?" },
    ],
    fallback: { text: "Haan ji, dasso. Paani, bijli, kish chahida?", en: "Yes, tell me. Water, power, what do you need?", s: ["Paani kadoon aunda ai?", "Bada dhannvaad!"] } },

  jk_doi_auto: { category: "transport", icon: "🛺", title: "Auto to Raghunath Bazaar", partner: "Kuldeep", role: "Auto driver", place: "Outside Jammu Tawi railway station",
    goal: "Get to Raghunath Bazaar for a fair fare.", places: ["Raghunath Bazaar", "Gandhi Nagar", "Bahu Fort", "Bus Stand", "Airport", "Residency Road", "Panjtirthi", "Trikuta Nagar"],
    opening: { text: "Kutthen jaana ai?", en: "Where do you need to go?" },
    start: ["Raghunath Bazaar chalge o?", "Kitne paise laggan?", "Matador kutthen thammdi ai?"],
    rules: [
      { m: ["dhannvaad", "shukriya", "thank", "upi", "milchai"], text: "Dhannvaad! Jai Mata Di! 🙏", en: "Thank you! Jai Mata Di!", s: ["Phi milchai!"], end: true, hint: "Bada dhannvaad!" },
      { m: ["roki", "rok", "stop"], text: "Lao, aayi gaya Raghunath Bazaar! Sau rape.", en: "Here we are, Raghunath Bazaar! A hundred rupees.", s: ["UPI chalda ai?", "Bada dhannvaad!"], hint: "Itthen roki deo." },
      { m: ["sau rape", "100"], text: "Theek ai, sau ch chalo. Baitho!", en: "Okay, a hundred it is. Get in!", s: ["Kinna time lagga?", "Itthen roki deo."], hint: "Sau rape ch chalo." },
      { m: ["matador", "minibus", "bus"], text: "Matador baahar stand thammdi ai, das-pandrah rape.", en: "The matadors stop at the stand outside, ten or fifteen rupees.", s: ["Nahin, auto ch chalo.", "Kitne paise laggan?"], hint: "Matador kutthen thammdi ai?" },
      { m: ["time", "der", "minute"], text: "Pandrah minute, je jam nahin hoye.", en: "Fifteen minutes, if there's no jam.", s: ["Theek ai, chalo.", "Itthen roki deo."], hint: "Kinna time lagga?" },
      { m: ["kitne", "paise", "kiraaya"], text: "Raghunath Bazaar? Dedh sau laggan.", en: "Raghunath Bazaar? A hundred and fifty.", s: ["Sau rape ch chalo.", "Theek ai, chalo."], hint: "Kitne paise laggan?" },
      { m: ["raghunath", "gandhi nagar", "bahu", "bus stand", "airport", "residency", "panjtirthi", "trikuta", "chalge"], text: "{place}? Haan ji, baitho.", en: "{place}? Yes, get in.", s: ["Kitne paise laggan?", "Sau rape ch chalo."], hint: "{place} chalge o?" },
      { m: ["theek", "chalo", "haan", "auto"], text: "Baitho! Jammu pehli baar?", en: "Get in! First time in Jammu?", s: ["Haan ji, pehli baar.", "Kinna time lagga?"] },
      { m: ["pehli baar", "new"], text: "Swagat ai! Bahu Fort zaroor jaana.", en: "Welcome! Do go to the Bahu Fort.", s: ["Itthen roki deo.", "Bada dhannvaad!"] },
    ],
    fallback: { text: "Samjheya nahin. Kutthen jaana ai?", en: "I didn't get that. Where do you need to go?", s: ["Raghunath Bazaar chalge o?", "Kitne paise laggan?"] } },

  jk_doi_food: { category: "food", icon: "🧀", title: "Kalari kulcha at a dhaba", partner: "Bittu", role: "Dhaba owner", place: "A dhaba near the Raghunath Bazaar",
    goal: "Order kalari kulcha and rajmah-chawal, and pay.",
    opening: { text: "Aao ji, ki laiyo?", en: "Come in, what will you have?" },
    start: ["Ik plate kalari kulcha deo.", "Mirch ghatt pao.", "Kitne hoye?"],
    rules: [
      { m: ["dhannvaad", "shukriya", "thank", "upi", "lao ji", "milchai"], text: "Dhannvaad ji! Phi aaneyo. 🙏", en: "Thank you! Come again.", s: ["Phi milchai!"], end: true, hint: "Lao ji, pakdo." },
      { m: ["kitne", "paise", "bill"], text: "Kalari kulcha te chaah, assi rape.", en: "Kalari kulcha and tea, eighty rupees.", s: ["UPI chalda ai?", "Lao ji, pakdo."], hint: "Kitne hoye?" },
      { m: ["mirch", "teekha", "spicy"], text: "Theek ai, mirch ghatt.", en: "Okay, less chilli.", s: ["Ik cup chaah.", "Kitne hoye?"], hint: "Mirch ghatt pao." },
      { m: ["rajmah", "chaul", "chawal"], text: "Rajmah-chaul garam ai! Ghee bi paaiye?", en: "The rajmah-chawal is hot! Shall I add ghee?", s: ["Haan ji, ghee paao.", "Kitne hoye?"], hint: "Rajmah-chaul bi deo." },
      { m: ["chaah", "chai", "cup"], text: "Ik cup chaah, garam garam!", en: "One cup of tea, piping hot!", s: ["Kitne hoye?", "Rajmah-chaul bi deo."], hint: "Ik cup chaah." },
      { m: ["kalari", "kulcha", "plate", "ghee"], text: "Garam kalari kulcha! Hor kish?", en: "Hot kalari kulcha! Anything else?", s: ["Rajmah-chaul bi deo.", "Mirch ghatt pao."], hint: "Ik plate kalari kulcha deo." },
    ],
    fallback: { text: "Kalari kulcha, rajmah-chaul, chaah... ki laiyo?", en: "Kalari kulcha, rajmah-chawal, tea... what will you have?", s: ["Ik plate kalari kulcha deo.", "Ik cup chaah."] } },

  jk_doi_shopping: { category: "shopping", icon: "🥜", title: "Dry fruits in Raghunath Bazaar", partner: "Gupta ji", role: "Shopkeeper", place: "A dry-fruit shop in Raghunath Bazaar",
    goal: "Buy walnuts and almonds at a fair price.",
    opening: { text: "Aao ji! Kashmiri akhrot, badaam, sab kish ai.", en: "Come in! Kashmiri walnuts, almonds, we have everything." },
    start: ["Eh kitne da ai?", "Hor rang ai?", "Bada mehnga ai."],
    rules: [
      { m: ["pack", "dhannvaad", "upi", "milchai"], text: "Pack kari ditta! Phi aaneyo. 🙏", en: "Packed! Come again.", s: ["Phi milchai!"], end: true, hint: "Theek ai, pack kari deo." },
      { m: ["chhe sau", "panj sau", "600", "500"], text: "Chalo, tusen layi chhe sau. Iss thon ghatt nahin.", en: "All right, six hundred for you. No lower.", s: ["Theek ai, pack kari deo.", "UPI chalda ai?"], hint: "Panj sau ch deo?" },
      { m: ["mehnga", "ghatt", "zyaada"], text: "Asli Kashmiri akhrot ne! Chalo, aath sau.", en: "These are real Kashmiri walnuts! All right, eight hundred.", s: ["Panj sau ch deo?", "Thodha ghatt karo."], hint: "Thodha ghatt karo." },
      { m: ["rang", "colour", "color", "shawl"], text: "Shawl bi ne, laal te neele.", en: "We have shawls too, red and blue.", s: ["Eh kitne da ai?", "Theek ai, pack kari deo."], hint: "Hor rang ai?" },
      { m: ["kitne", "daam", "price"], text: "Ik kilo akhrot? Hazaar rape.", en: "A kilo of walnuts? A thousand rupees.", s: ["Bada mehnga ai.", "Thodha ghatt karo."], hint: "Eh kitne da ai?" },
    ],
    fallback: { text: "Aaraam naal dikho. Akhrot, badaam, shawl, sab kish ai.", en: "Take your time. Walnuts, almonds, shawls, we have it all.", s: ["Eh kitne da ai?", "Hor rang ai?"] } },

  jk_doi_directions: { category: "directions", icon: "🛕", title: "Find the Raghunath Temple", partner: "Pandit ji", role: "Passerby", place: "The old city, Jammu",
    goal: "Find the way to the Raghunath Temple, and a pharmacy.",
    opening: { text: "Kish labhde o?", en: "What are you looking for?" },
    start: ["Raghunath Mandar kutthen ai?", "Neden koi duaai di hatti ai?", "Paidal kitna door ai?"],
    rules: [
      { m: ["dhannvaad", "shukriya", "thank", "samajh", "milchai"], text: "Koi gal nahin! Jai Mata Di. 🙏", en: "Not at all! Jai Mata Di.", s: ["Phi milchai!"], end: true, hint: "Bada dhannvaad!" },
      { m: ["phi dasso", "dobara", "slow"], text: "Siddhe, phi sajje. Bas!", en: "Straight on, then right. That's it!", s: ["Theek ai, samajh aayi gaya.", "Paidal kitna door ai?"], hint: "Phi dasso, ji." },
      { m: ["duaai", "medical", "chemist", "hospital"], text: "Haan, mandar de saahmne ik medical store ai.", en: "Yes, there's a pharmacy opposite the temple.", s: ["Raghunath Mandar kutthen ai?", "Phi dasso, ji."], hint: "Neden koi duaai di hatti ai?" },
      { m: ["paidal", "door", "walk"], text: "Paidal panj minute, bilkul nede.", en: "Five minutes on foot, very close.", s: ["Theek ai, samajh aayi gaya.", "Bada dhannvaad!"], hint: "Paidal kitna door ai?" },
      { m: ["raghunath", "mandar", "mandir", "kutthen"], text: "Siddhe jao, phi sajje mudo. Mandar saahmne ai.", en: "Go straight, then turn right. The temple is ahead.", s: ["Paidal kitna door ai?", "Phi dasso, ji."], hint: "Raghunath Mandar kutthen ai?" },
    ],
    fallback: { text: "Dasso, kutthen jaana ai?", en: "Tell me, where do you need to go?", s: ["Raghunath Mandar kutthen ai?", "Neden koi duaai di hatti ai?"] } },

  jk_doi_college: { category: "college", icon: "🎓", title: "First day at the University of Jammu", partner: "Ritika", role: "Classmate", place: "University of Jammu campus",
    goal: "Find your class and the canteen, and make a friend.",
    opening: { text: "Hi! Ajj paihla din ai? Main Ritika.", en: "Hi! Is it your first day? I'm Ritika." },
    start: ["Haan, ajj mera paihla din ai.", "Class kutthen ai?", "Canteen ch chaah peechai?"],
    rules: [
      { m: ["milchai", "bye", "thank", "dhannvaad"], text: "Welcome! Kish chahida hove, dasseyo. 👋", en: "Welcome! Tell me if you need anything.", s: ["Phi milchai!"], end: true, hint: "Thank you, Ritika!" },
      { m: ["chaah", "canteen", "chai"], text: "Haan, class de baad chalchai!", en: "Yes, let's go after class!", s: ["Thank you, Ritika!", "Phi milchai!"], hint: "Canteen ch chaah peechai?" },
      { m: ["madad", "help"], text: "Haan, zaroor! Timetable WhatsApp kari dinni aan.", en: "Of course! I'll WhatsApp you the timetable.", s: ["Canteen ch chaah peechai?", "Thank you, Ritika!"], hint: "Thodhi madad kari deo?" },
      { m: ["class", "kutthen", "room"], text: "Class duji manzil par ai, kamra do sau do.", en: "The class is on the second floor, room 202.", s: ["Thodhi madad kari deo?", "Canteen ch chaah peechai?"], hint: "Class kutthen ai?" },
      { m: ["paihla", "haan", "first"], text: "Welcome! Paihle din sab kish thodha confusing hunda ai.", en: "Welcome! Everything's a bit confusing on the first day.", s: ["Class kutthen ai?", "Thodhi madad kari deo?"], hint: "Ajj mera paihla din ai." },
    ],
    fallback: { text: "Dasso, ki chahida? Class, library, ja canteen?", en: "Tell me, what do you need? The class, the library or the canteen?", s: ["Class kutthen ai?", "Canteen ch chaah peechai?"] } },

  jk_doi_smalltalk: { category: "smalltalk", icon: "🌳", title: "An evening at the Bagh-e-Bahu", partner: "Ankush", role: "Friend", place: "The Bagh-e-Bahu gardens by the Tawi",
    goal: "Chat about Jammu and plan a Sunday trip to Katra.",
    opening: { text: "Ki haal ai? Jammu kiyaan lagda?", en: "How's it going? How are you liking Jammu?" },
    start: ["Bagh-e-Bahu kinna sohna ai!", "Jammu ch garmi badi ai, na?", "Tus Jammu de o?"],
    rules: [
      { m: ["pakka", "bye", "jai mata", "milchai"], text: "Pakka! Aitwaar savere nikalchai. 👋", en: "Deal! We'll set off on Sunday morning.", s: ["Phi milchai!"], end: true, hint: "Pakka, Jai Mata Di!" },
      { m: ["baje", "savere"], text: "Savere chhe baje, dhoop thon pehlen.", en: "Six in the morning, before the sun.", s: ["Pakka, Jai Mata Di!"], hint: "Kinne baje?" },
      { m: ["katra", "aitwaar", "sunday", "vaishno", "patnitop"], text: "Haan! Aitwaar Katra, te phi Vaishno Devi di yatra.", en: "Yes! Katra on Sunday, then the walk up to Vaishno Devi.", s: ["Pakka, Jai Mata Di!", "Kinne baje?"], hint: "Aitwaar Katra chalchai?" },
      { m: ["jammu de", "itthen", "born"], text: "Haan, main purane shehar da aan, Raghunath Bazaar de nede!", en: "Yes, I'm from the old city, near Raghunath Bazaar!", s: ["Aitwaar Katra chalchai?", "Jammu ch garmi badi ai, na?"], hint: "Tus Jammu de o?" },
      { m: ["garmi", "dhoop", "hot"], text: "Haan, par shaami Tawi kanne thandi hawa chaldi ai.", en: "Yes, but in the evening a cool breeze blows by the Tawi.", s: ["Tus Jammu de o?", "Aitwaar Katra chalchai?"], hint: "Jammu ch garmi badi ai, na?" },
      { m: ["sohna", "bagh", "sundar"], text: "Haan, Bahu Fort to poora shehar dikhda ai.", en: "Yes, you can see the whole city from the Bahu Fort.", s: ["Jammu ch garmi badi ai, na?", "Tus Jammu de o?"], hint: "Bagh-e-Bahu kinna sohna ai!" },
    ],
    fallback: { text: "Haha, sach! Jammu ch sab thon changa ki lagga?", en: "Haha, true! What do you like most about Jammu?", s: ["Bagh-e-Bahu kinna sohna ai!", "Jammu ch garmi badi ai, na?"] } },

  // ---------- Urdu, across Jammu & Kashmir ----------
  jk_ur_greetings: { category: "greetings", icon: "🏠", title: "Meet your landlord", partner: "Mir sahab", role: "Landlord", place: "Your rented room in Rajbagh, Srinagar",
    goal: "Greet your landlord, introduce yourself and ask about the heating.",
    opening: { text: "Assalaam alaikum! Tashreef laaiye. Aap hi Alex hain?", en: "Hello! Do come in. Are you Alex?" },
    start: ["Walaikum assalaam! Mizaaj kaise hain?", "Ji, mera naam Alex hai.", "Raat ko heater milega?"],
    rules: [
      { m: ["meherbaani", "shukriya", "thank", "khuda hafiz", "samajh"], text: "Meherbaani kis baat ki! Kuch chahiye toh boliye. 🙏", en: "No need to thank me! Tell me if you need anything.", s: ["Khuda hafiz!"], end: true, hint: "Bahut meherbaani!" },
      { m: ["heater", "kangri", "sardi", "bijli"], text: "Ji, heater hai, aur bijli jaaye toh kangri bhi.", en: "Yes, there's a heater, and a kangri too if the power goes.", s: ["Ji, samajh aa gaya.", "Bahut meherbaani!"], hint: "Raat ko heater milega?" },
      { m: ["khushi", "mil kar"], text: "Humein bhi khushi hui. Kashmir pehli baar?", en: "The pleasure is mine. First time in Kashmir?", s: ["Ji, pehli baar.", "Raat ko heater milega?"], hint: "Aap se mil kar khushi hui." },
      { m: ["pehli baar", "naya", "nayi", "new"], text: "Khush aamdeed! Dal mein shikaara zaroor kijiye.", en: "Welcome! Do take a shikara on the Dal.", s: ["Raat ko heater milega?", "Bahut meherbaani!"], hint: "Ji, pehli baar." },
      { m: ["naam", "alex", "name"], text: "Bahut khoob! Kashmir pehli baar?", en: "Lovely! First time in Kashmir?", s: ["Ji, pehli baar.", "Aap se mil kar khushi hui."], hint: "Ji, mera naam Alex hai." },
      { m: ["salaam", "alaikum", "aadaab", "mizaaj", "hello"], text: "Alhamdulillah, theek hoon! Aapka naam?", en: "Thank God, I'm well! Your name?", s: ["Ji, mera naam Alex hai.", "Aap se mil kar khushi hui."], hint: "Walaikum assalaam! Mizaaj kaise hain?" },
    ],
    fallback: { text: "Ji, farmaaiye. Heater, paani, Wi-Fi, kya jaanna hai?", en: "Yes, please tell me. Heating, water, Wi-Fi: what would you like to know?", s: ["Raat ko heater milega?", "Bahut meherbaani!"] } },

  jk_ur_auto: { category: "transport", icon: "🛶", title: "Auto to Dal Gate", partner: "Farooq", role: "Auto driver", place: "Lal Chowk, Srinagar",
    goal: "Get to Dal Gate for a fair fare, and find a shikara.", places: ["Dal Gate", "Nishat Bagh", "Shalimar Bagh", "Hazratbal", "Airport", "Rajbagh", "Residency Road", "Boulevard"],
    opening: { text: "Kahan chalna hai?", en: "Where to?" },
    start: ["Dal Gate chalenge?", "Kitna kiraaya hoga?", "Shikaara kahan milega?"],
    rules: [
      { m: ["shukriya", "meherbaani", "thank", "upi", "khuda hafiz"], text: "Shukriya! Kashmir mein khush rahiye. 🙏", en: "Thank you! Enjoy Kashmir.", s: ["Khuda hafiz!"], end: true, hint: "Bahut meherbaani!" },
      { m: ["rok", "yahan", "stop"], text: "Lijiye, Dal Gate aa gaya. Sau rupaye.", en: "Here's Dal Gate. A hundred rupees.", s: ["UPI chalega?", "Bahut meherbaani!"], hint: "Yahan rok dijiye." },
      { m: ["shikaara", "shikara", "boat"], text: "Shikaara Dal Gate ke ghaat par milega. Sarkari rate board par likha hai.", en: "You'll get a shikara at the Dal Gate ghat. The official rate is on the board.", s: ["Theek hai, chaliye.", "Kitna kiraaya hoga?"], hint: "Shikaara kahan milega?" },
      { m: ["kam", "zyaada", "mehenga"], text: "Achha, assi de dijiye.", en: "All right, give eighty.", s: ["Theek hai, chaliye.", "Yahan rok dijiye."], hint: "Thoda kam kijiye." },
      { m: ["kiraaya", "kitna", "paise"], text: "Dal Gate? Sau rupaye.", en: "Dal Gate? A hundred rupees.", s: ["Thoda kam kijiye.", "Theek hai, chaliye."], hint: "Kitna kiraaya hoga?" },
      { m: ["dal gate", "nishat", "shalimar", "hazratbal", "airport", "rajbagh", "residency", "boulevard", "chalenge"], text: "{place}? Ji, baithiye.", en: "{place}? Sure, get in.", s: ["Kitna kiraaya hoga?", "Yahan rok dijiye."], hint: "{place} chalenge?" },
      { m: ["theek", "chaliye", "ji haan"], text: "Baithiye! Kashmir pehli baar?", en: "Get in! First time in Kashmir?", s: ["Ji, pehli baar.", "Yahan rok dijiye."] },
      { m: ["pehli baar", "new"], text: "Khush aamdeed! Shaam ko Boulevard par zaroor ghoomiye.", en: "Welcome! Do take a walk on the Boulevard in the evening.", s: ["Yahan rok dijiye.", "Bahut meherbaani!"] },
    ],
    fallback: { text: "Samjha nahi. Kahan chalna hai?", en: "I didn't get that. Where to?", s: ["Dal Gate chalenge?", "Kitna kiraaya hoga?"] } },

  jk_ur_food: { category: "food", icon: "🍵", title: "Breakfast on Residency Road", partner: "Javed", role: "Waiter", place: "A café on Residency Road, Srinagar",
    goal: "Order kahwa or noon chai with bread, and pay.",
    opening: { text: "Aaiye, kya laaun?", en: "Come in, what can I bring you?" },
    start: ["Ek kahwa dijiye.", "Noon chai milegi?", "Kitne paise hue?"],
    rules: [
      { m: ["shukriya", "meherbaani", "thank", "upi", "rakh lijiye", "khuda hafiz"], text: "Shukriya! Phir tashreef laaiye. 🙏", en: "Thank you! Do come again.", s: ["Khuda hafiz!"], end: true, hint: "Ye rakh lijiye." },
      { m: ["kitne", "paise", "bill"], text: "Kahwa aur kulche, assi rupaye.", en: "Kahwa and kulchas, eighty rupees.", s: ["UPI chalega?", "Ye rakh lijiye."], hint: "Kitne paise hue?" },
      { m: ["mirch", "teekha", "spicy"], text: "Ji, mirch kam rakhenge.", en: "Sure, we'll keep it mild.", s: ["Do kulche dijiye.", "Kitne paise hue?"], hint: "Mirch kam rakhiye." },
      { m: ["noon chai", "noon"], text: "Ji haan, garam noon chai! Kulche bhi laaun?", en: "Yes, hot noon chai! Shall I bring kulchas too?", s: ["Do kulche dijiye.", "Kitne paise hue?"], hint: "Noon chai milegi?" },
      { m: ["kulche", "kulcha", "girda", "roti"], text: "Taaze kulche, abhi laata hoon.", en: "Fresh kulchas, coming right up.", s: ["Kitne paise hue?", "Ek kahwa dijiye."], hint: "Do kulche dijiye." },
      { m: ["kahwa", "chai"], text: "Ek kahwa, kesar aur badaam ke saath! Aur kuch?", en: "One kahwa, with saffron and almonds! Anything else?", s: ["Do kulche dijiye.", "Kitne paise hue?"], hint: "Ek kahwa dijiye." },
    ],
    fallback: { text: "Kahwa, noon chai, kulche... kya laaun?", en: "Kahwa, noon chai, kulchas... what can I bring you?", s: ["Ek kahwa dijiye.", "Noon chai milegi?"] } },

  jk_ur_shopping: { category: "shopping", icon: "🧣", title: "A shawl on Residency Road", partner: "Nazir sahab", role: "Shopkeeper", place: "A shawl shop on Residency Road",
    goal: "Buy a shawl at a fair price.",
    opening: { text: "Aaiye! Pashmina, kani, sozni, sab dekhiye.", en: "Come in! Pashmina, kani, sozni embroidery: take a look." },
    start: ["Ye shawl kitne ki hai?", "Kya ye asli pashmina hai?", "Bahut mehngi hai."],
    rules: [
      { m: ["pack", "shukriya", "meherbaani", "upi"], text: "Pack kar di! Phir aaiye. 🙏", en: "Packed! Come again.", s: ["Khuda hafiz!"], end: true, hint: "Theek hai, pack kar dijiye." },
      { m: ["khuda hafiz"], text: "Khuda hafiz! Phir aaiyega.", en: "Goodbye! Do come again.", s: ["Khuda hafiz!"], end: true },
      { m: ["chaar hazaar", "teen hazaar", "4000", "3000"], text: "Chaliye, aapke liye chaar hazaar. Isse kam nahi.", en: "All right, four thousand for you. No lower.", s: ["Theek hai, pack kar dijiye.", "UPI chalega?"], hint: "Teen hazaar mein denge?" },
      { m: ["mehngi", "mehenga", "kam", "zyaada"], text: "Asli pashmina hai! Chaliye, paanch hazaar.", en: "It's real pashmina! All right, five thousand.", s: ["Teen hazaar mein denge?", "Doosra rang dikhaaiye."], hint: "Bahut mehngi hai." },
      { m: ["asli", "pashmina", "real"], text: "Bilkul asli! Haath ka kaam hai, certificate bhi hai.", en: "Absolutely real! It's handwork, and there's a certificate.", s: ["Ye shawl kitne ki hai?", "Doosra rang dikhaaiye."], hint: "Kya ye asli pashmina hai?" },
      { m: ["rang", "colour", "color", "dikhaaiye"], text: "Ji, laal aur aasmaani bhi hai.", en: "Yes, there's red and sky blue too.", s: ["Ye shawl kitne ki hai?", "Theek hai, pack kar dijiye."], hint: "Doosra rang dikhaaiye." },
      { m: ["kitne", "daam", "price"], text: "Ye shawl? Chhe hazaar.", en: "This shawl? Six thousand.", s: ["Bahut mehngi hai.", "Kya ye asli pashmina hai?"], hint: "Ye shawl kitne ki hai?" },
    ],
    fallback: { text: "Aaraam se dekhiye. Shawl, pheran, sab hai.", en: "Take your time. Shawls, pherans, we have it all.", s: ["Ye shawl kitne ki hai?", "Kya ye asli pashmina hai?"] } },

  jk_ur_directions: { category: "directions", icon: "🛕", title: "Find the Raghunath Temple", partner: "Bhat sahab", role: "Passerby", place: "Near the Jammu bus stand",
    goal: "Find the way to the Raghunath Temple, and a pharmacy.",
    opening: { text: "Kuch dhoondna hai?", en: "Looking for something?" },
    start: ["Raghunath Mandir kis taraf hai?", "Qareeb mein dawakhana hai?", "Paidal kitni door hai?"],
    rules: [
      { m: ["shukriya", "meherbaani", "thank", "samajh", "khuda hafiz"], text: "Koi baat nahi! Aaraam se jaaiye. 🙏", en: "Not at all! Go easy.", s: ["Khuda hafiz!"], end: true, hint: "Bahut meherbaani!" },
      { m: ["aahista", "phir se", "dobara", "slow"], text: "Seedhe, phir daayen. Bas!", en: "Straight on, then right. That's it!", s: ["Ji, samajh aa gaya.", "Paidal kitni door hai?"], hint: "Zara aahista boliye." },
      { m: ["dawakhana", "medical", "chemist", "hospital"], text: "Ji, bus stand ke saamne ek dawakhana hai.", en: "Yes, there's a pharmacy opposite the bus stand.", s: ["Raghunath Mandir kis taraf hai?", "Zara aahista boliye."], hint: "Qareeb mein dawakhana hai?" },
      { m: ["paidal", "door", "walk"], text: "Paidal das minute, zyaada nahi.", en: "Ten minutes on foot, no more.", s: ["Ji, samajh aa gaya.", "Bahut meherbaani!"], hint: "Paidal kitni door hai?" },
      { m: ["raghunath", "mandir", "kis taraf"], text: "Seedhe jaaiye, phir daayen mudiye. Mandir bazaar ke beech mein hai.", en: "Go straight, then turn right. The temple is in the middle of the bazaar.", s: ["Paidal kitni door hai?", "Zara aahista boliye."], hint: "Raghunath Mandir kis taraf hai?" },
    ],
    fallback: { text: "Boliye, kahan jaana hai?", en: "Tell me, where do you need to go?", s: ["Raghunath Mandir kis taraf hai?", "Qareeb mein dawakhana hai?"] } },

  jk_ur_college: { category: "college", icon: "🎓", title: "First day at the University of Kashmir", partner: "Mehvish", role: "Classmate", place: "University of Kashmir, Srinagar",
    goal: "Find the library and the canteen, and make a friend.",
    opening: { text: "Assalaam alaikum! Aaj pehla din hai? Main Mehvish.", en: "Hello! First day today? I'm Mehvish." },
    start: ["Ji, aaj mera pehla din hai.", "Library kahan hai?", "Canteen mein chai piyen?"],
    rules: [
      { m: ["milte hain", "bye", "thank", "shukriya", "zaroor"], text: "Khush aamdeed! Kuch chahiye toh batana. 👋", en: "Welcome! Tell me if you need anything.", s: ["Phir milte hain!"], end: true, hint: "Shukriya, Mehvish!" },
      { m: ["chai", "canteen"], text: "Haan, class ke baad noon chai peete hain!", en: "Yes, let's have noon chai after class!", s: ["Zaroor!", "Shukriya, Mehvish!"], hint: "Canteen mein chai piyen?" },
      { m: ["madad", "help"], text: "Bilkul! Timetable WhatsApp kar deti hoon.", en: "Of course! I'll WhatsApp you the timetable.", s: ["Canteen mein chai piyen?", "Shukriya, Mehvish!"], hint: "Kya aap meri madad karenge?" },
      { m: ["library", "kitaab", "kahan"], text: "Library Allama Iqbal ke naam par hai, main gate ke paas.", en: "The library is named after Allama Iqbal, near the main gate.", s: ["Kya aap meri madad karenge?", "Canteen mein chai piyen?"], hint: "Library kahan hai?" },
      { m: ["pehla", "ji,", "first"], text: "Khush aamdeed! Pehle din thoda mushkil lagta hai.", en: "Welcome! The first day always feels a bit hard.", s: ["Library kahan hai?", "Kya aap meri madad karenge?"], hint: "Aaj mera pehla din hai." },
    ],
    fallback: { text: "Boliye, kya chahiye? Library, canteen, ya class?", en: "Tell me, what do you need? The library, the canteen or the class?", s: ["Library kahan hai?", "Canteen mein chai piyen?"] } },

  jk_ur_smalltalk: { category: "smalltalk", icon: "🌷", title: "An evening in the Shalimar Bagh", partner: "Zoya", role: "Friend", place: "The Shalimar Bagh at sunset",
    goal: "Chat about Kashmir and plan a Sunday trip to Gulmarg.",
    opening: { text: "Kashmir kaisa lag raha hai?", en: "How are you liking Kashmir?" },
    start: ["Kashmir kitna khoobsoorat hai!", "Aaj bahut sardi hai.", "Aap kahan ki hain?"],
    rules: [
      { m: ["zaroor", "bye", "khuda hafiz", "mazaa"], text: "Zaroor! Itwaar ko subah nikalte hain. 👋", en: "Definitely! We'll set off on Sunday morning.", s: ["Khuda hafiz!"], end: true, hint: "Zaroor, bahut mazaa aayega!" },
      { m: ["baje", "subah"], text: "Subah saat baje, taaki gondola mil jaaye.", en: "Seven in the morning, so we get the gondola.", s: ["Zaroor, bahut mazaa aayega!"], hint: "Kitne baje?" },
      { m: ["gulmarg", "itwaar", "sunday", "pahalgam", "sonamarg"], text: "Haan! Itwaar ko Gulmarg, gondola mein.", en: "Yes! Gulmarg on Sunday, on the gondola.", s: ["Zaroor, bahut mazaa aayega!", "Kitne baje?"], hint: "Itwaar ko Gulmarg chalein?" },
      { m: ["kahan ki", "kahan ke", "yahin", "born"], text: "Main Srinagar ki hoon, purane shehar ki, Jhelum ke kinaare.", en: "I'm from Srinagar, the old city, by the Jhelum.", s: ["Itwaar ko Gulmarg chalein?", "Aaj bahut sardi hai."], hint: "Aap kahan ki hain?" },
      { m: ["sardi", "barf", "cold", "thand"], text: "Haan, lekin kangri aur noon chai ho toh sab theek!", en: "Yes, but with a kangri and noon chai, all's well!", s: ["Aap kahan ki hain?", "Itwaar ko Gulmarg chalein?"], hint: "Aaj bahut sardi hai." },
      { m: ["khoobsoorat", "kashmir", "bagh"], text: "Haan, Shalimar Bagh shaam ko sabse khoobsoorat lagta hai.", en: "Yes, the Shalimar Bagh is at its most beautiful in the evening.", s: ["Aaj bahut sardi hai.", "Itwaar ko Gulmarg chalein?"], hint: "Kashmir kitna khoobsoorat hai!" },
    ],
    fallback: { text: "Haha, sach hai! Kashmir mein sabse achha kya laga?", en: "Haha, true! What do you like most about Kashmir?", s: ["Kashmir kitna khoobsoorat hai!", "Aaj bahut sardi hai."] } },
});

window.CONTENT_REVIEW.jk = {
  ks: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
    known_limitations: ["Draft: written with lower confidence than the other languages, especially the Kashmiri script; a native speaker should check every phrase before learners rely on it.", "Masculine forms are taught first; the feminine form is shown where it differs.", "Browsers have no Kashmiri voice, so Kashmiri phrases are shown but not read aloud.", "Fares and practical tips change over time."],
    note: "Kashmiri: an AI-assisted first draft, not yet checked by a native Kashmiri speaker." },
  doi: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
    known_limitations: ["Draft: written with lower confidence than Hindi or Urdu; a native speaker should check every phrase before learners rely on it.", "Masculine forms are taught first; the feminine form is shown where it differs.", "Browsers have no Dogri voice, so Dogri phrases are shown but not read aloud.", "Fares and practical tips change over time."],
    note: "Dogri: an AI-assisted first draft, not yet checked by a native Dogri speaker." },
  ur: { editorial_status: "ai_assisted_review", native_review_status: "pending", last_editorial_reviewed_at: "2026-10-19",
    known_limitations: ["Masculine forms are taught first; the feminine form is shown where it differs.", "Standard Urdu in J&K settings; Kashmiri and Dogri words are not mixed in.", "Fares and practical tips change over time."],
    note: "J&K Urdu: AI-assisted editorial review only, not yet checked by a native Urdu speaker." },
};

const PLACE_JK = {
  ks: { "nishat bagh": ["Nishat Bagh", "نشاط باغ", "the Nishat Bagh"], "shalimar bagh": ["Shalimar Bagh", "شالیمار باغ", "the Shalimar Bagh"], "dal gate": ["Dal Gate", "ڈل گیٹ", "Dal Gate"],
        hazratbal: ["Hazratbal", "حضرتبل", "the Hazratbal"], airport: ["Airport", "ایئرپورٹ", "the airport"], "lal chowk": ["Lal Chowk", "لال چوک", "Lal Chowk"], rajbagh: ["Rajbagh", "راجباغ", "Rajbagh"] },
  doi: { "raghunath bazaar": ["Raghunath Bazaar", "रघुनाथ बजार", "Raghunath Bazaar"], "gandhi nagar": ["Gandhi Nagar", "गांधी नगर", "Gandhi Nagar"], "bahu fort": ["Bahu Fort", "बाहु किला", "the Bahu Fort"],
         "bus stand": ["Bus Stand", "बस अड्डा", "the bus stand"], airport: ["Airport", "एयरपोर्ट", "the airport"], "jammu tawi": ["Jammu Tawi", "जम्मू तवी", "Jammu Tawi station"], katra: ["Katra", "कटड़ा", "Katra"] },
  ur: { "dal gate": ["Dal Gate", "ڈل گیٹ", "Dal Gate"], "nishat bagh": ["Nishat Bagh", "نشاط باغ", "the Nishat Bagh"], "lal chowk": ["Lal Chowk", "لال چوک", "Lal Chowk"],
        "raghunath bazaar": ["Raghunath Bazaar", "رگھوناتھ بازار", "Raghunath Bazaar"], airport: ["Airport", "ایئرپورٹ", "the airport"], "residency road": ["Residency Road", "ریزیڈنسی روڈ", "Residency Road"], hazratbal: ["Hazratbal", "حضرت بل", "the Hazratbal"] },
};
const jkP = (hi, roman, en, extra) => ({ hi, roman, en, ...(extra || {}) });
const JK_RIDE_NOTE = "Autos in Srinagar and Jammu don't use meters: agree the fare before you sit in. On the Dal Lake the tourism department sets an official hourly shikara rate; boatmen often ask for more, so agree the price first.";
// One tutor answer set per language: [topic, keywords, intro, phrases, note]. The transport answer that names a place is built separately.
const jkTutor = (lang, cfg) => ({
  greet: cfg.greet, places: Object.values(PLACE_JK[lang]).map((p) => p[0]), defaultPlace: Object.values(PLACE_JK[lang])[0][0], language: cfg.language,
  starters: cfg.starters, glossaryOnly: true, glossary: cfg.glossary, polite: cfg.polite,
  intents: [
    { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
      build: (dest) => { const d = PLACE_JK[lang][dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: "Try:", phrases: cfg.ride(r, d, dest), note: JK_RIDE_NOTE }; } },
    ...cfg.intents.map(([topic, m, intro, phrases, note]) => ({ m, topic, intro, phrases: phrases.map((p) => jkP(...p)), ...(note ? { note } : {}) })),
  ],
  generic: { intro: "Here are three phrases that'll get you through almost anything in your first week:", phrases: cfg.generic.map((p) => jkP(...p)),
    note: `Tell me a situation — like “I want to order tea” or “ask the way” — and I'll give you the exact ${cfg.language} words.` },
});
const JK_INTENT_KEYS = {
  metro: ["metro", "train", "bus", "platform", "line", "token", "matador", "shikara"], bargain: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"],
  price: ["price", "how much", "cost", "pay", "upi"], food: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "tea", "kahwa", "bill"],
  directions: ["direction", "where is", "lost", "way", "find", "left", "right"], college: ["class", "college", "university", "professor", "teacher", "office", "work", "colleague", "canteen"],
  smalltalk: ["friend", "small talk", "chat", "conversation", "weather", "rain", "snow", "classmate"], name: ["name", "introduce", "myself", "meet"],
  thanks: ["thank", "sorry", "excuse", "please"], hello: ["hello", "hi", "greet", "salaam", "namaste", "bye", "good morning"], help: ["help", "emergency", "doctor", "police", "sick"],
};

window.LOCAL_CONTENT.jk = {
  // ---------- Kashmiri (draft) ----------
  ks: {
    tutor: jkTutor("ks", {
      greet: "Assalaam alaikum", language: "Kashmiri",
      starters: ["I need a ride to the Nishat Bagh.", "How do I order a kahwa?", "How do I bargain for a pashmina?", "What does 'baya' mean?", "Where do I get a shikara?"],
      glossary: { baya: "“Brother”: a friendly way to address a man, a driver or a shopkeeper.", beni: "“Sister”: the female equivalent of baya.", kahwa: "Green tea with saffron, cardamom and almonds.",
        "noon chai": "Pink salt tea, drunk with bread from the kandur.", kandur: "The baker: girda, lavaas and kulcha come from his oven.", shikara: "The wooden boat of the Dal Lake.",
        kangri: "A fire-pot carried under the pheran in winter.", pheran: "The long woollen Kashmiri cloak.", vaaray: "“Well / fine.” Vaaray chhivaa? = Are you well?", kotah: "“How much / how many.”", kati: "Where.", aa: "Yes.", na: "No." },
      polite: { intro: "Kashmiri is polite with “tuhi” and requests ending in -iv (“diyiv”, “kariv”, “vaniv”):", rules: [["\\bdi\\b", "diyiv"], ["\\bkar\\b", "kariv"], ["\\bvan\\b", "vaniv"]], note: "e.g. “di” → “diyiv”. With friends the short forms are fine." },
      ride: (r, d, dest) => [jkP(d ? `${d[1]} گژھِو؟ کوتاہ پونٛسہٕ؟` : "", `${r} gatshiv? Kotah poonsa?`, `Will you go to ${d ? d[2] : dest}? How much?`),
        jkP(d ? `بایا، ${d[1]} گژھِو؟` : "", `Baya, ${r} gatshiv?`, `A more friendly version: Brother, will you go to ${d ? d[2] : dest}?`, { label: "Friendly" }),
        jkP("گۄڈہٕ وَنِو کوتاہ۔", "Gwodah vaniv kotah.", "Tell me how much first.")],
      intents: [
        ["transport", JK_INTENT_KEYS.metro, "On the lake, try:", [["شِکارہ کتہِ میلہِ؟", "Shikaara kati meli?", "Where can I get a shikara?"], ["اَکھ گنٹہٕ کوتاہ؟", "Akh ganta kotah?", "How much for one hour?"]], "Shikara rates are set by the tourism department; ask to see the board at the ghat."],
        ["shopping", JK_INTENT_KEYS.bargain, "To bargain politely:", [["واریاہ مہنگ چھُ۔", "Vaariyah mahang chhu.", "That's too expensive."], ["کم کٔرِو۔", "Kam kariv.", "Please lower it."]], "Bargain where there are no price tags; government emporiums have fixed prices."],
        ["shopping", JK_INTENT_KEYS.price, "Ask the price like this:", [["یہِ کوتاہ چھُ؟", "Yi kotah chhu?", "How much is this?"], ["UPI چھا؟", "UPI chha?", "Can I pay by UPI?"]]],
        ["food", JK_INTENT_KEYS.food, "Ordering tea and bread:", [["اَکھ کہوہ دِیِو۔", "Akh kahwa diyiv.", "One kahwa, please."], ["نون چاے چھا؟", "Noon chai chha?", "Do you have noon chai?"], ["مرٚچ کم۔", "Marats kam.", "Not too spicy, please."]], "Kahwa in the afternoon, noon chai with bread from the kandur."],
        ["directions", JK_INTENT_KEYS.directions, "Asking for directions:", [["ڈل کتہِ چھُ؟", "Dal kati chhu?", "Where's the Dal Lake?"], ["سیود گژھِو، پتہٕ دٔچھِن۔", "Syod gatshiv, pata dachhun.", "Go straight, then right."]], "“Dachhun” is right and “khovur” is left."],
        ["college", JK_INTENT_KEYS.college, "At university or work:", [["اَز چھُ مےٚون گۄڈنیُک دۄہ۔", "Az chhu myon gwodaniuk doh.", "It's my first day today."], ["کلاس کتہِ چھےٚ؟", "Class kati chhe?", "Where's the class?"]]],
        ["smalltalk", JK_INTENT_KEYS.smalltalk, "Easy small-talk starters:", [["کشیر چھےٚ واریاہ خوبصورت!", "Kasheer chhe vaariyah khoobsoorat!", "Kashmir is so beautiful!"], ["اَز چھُ واریاہ تُر۔", "Az chhu vaariyah tur.", "It's really cold today."]], "Kashmiris love to talk about the seasons, the snow and the food."],
        ["greetings", JK_INTENT_KEYS.name, "Introduce yourself:", [["مےٚون ناو چھُ ایلیکس۔", "Myon naav chhu Alex.", "My name is Alex."], ["تُہُنٛد ناو کیاہ چھُ؟", "Tuhund naav kyah chhu?", "What's your name?"]]],
        ["greetings", JK_INTENT_KEYS.thanks, "Polite essentials:", [["واریاہ شُکریہ!", "Vaariyah shukriya!", "Thanks a lot!"], ["آہستہ وَنِو۔", "Aahista vaniv.", "Please speak more slowly."]]],
        ["greetings", JK_INTENT_KEYS.hello, "Greetings that work everywhere in the Valley:", [["السلام علیکم! وارےٚ چھِوا؟", "Assalaam alaikum! Vaaray chhivaa?", "Hello! How are you?"], ["پتہٕ مُلاقات!", "Pata mulaqaat!", "See you later!"]], "“Assalaam alaikum” and “Namaskar” are both everyday greetings."],
        ["directions", JK_INTENT_KEYS.help, "If you need help:", [["نزدیک چھا میڈیکل شاپ؟", "Nazdeek chha medical shop?", "Is there a pharmacy nearby?"], ["مےٚ کٔرِو مدد۔", "Me kariv madad.", "Please help me."]], "Emergency number in India: 112."],
      ],
      generic: [["السلام علیکم! وارےٚ چھِوا؟", "Assalaam alaikum! Vaaray chhivaa?", "Hello! How are you?"], ["یہِ کوتاہ چھُ؟", "Yi kotah chhu?", "How much is this?"], ["مےٚ کٔرِو مدد؟", "Me kariv madad?", "Could you help me?"]],
    }),
    readings: [
      { title: "Asha in Srinagar", level: "A1", lines: [jkP("آشا چھےٚ سِرینگر منٛز نٔو۔", "Asha chhe Sirinagar manz nev.", "Asha is new in Srinagar."), jkP("سۄ چھےٚ شِکارس منٛز ڈل وچھان۔", "So chhe shikaaras manz Dal vuchhaan.", "She sees the Dal from a shikara."), jkP("پتہٕ چھےٚ سۄ کہوہ چَوان۔", "Pata chhe so kahwa chavaan.", "Then she drinks a kahwa."), jkP("کشیر چھےٚ واریاہ خوبصورت۔", "Kasheer chhe vaariyah khoobsoorat.", "Kashmir is very beautiful.")],
        questions: [{ q: "Where is Asha new?", options: ["Jammu", "Srinagar", "Delhi"], a: 1 }, { q: "What does she drink?", options: ["Kahwa", "Coffee", "Lassi"], a: 0 }] },
      { title: "A shawl on Polo View", level: "A1", lines: [jkP("روی چھُ دُکانہِ گژھان۔", "Ravi chhu dukaani gatshaan.", "Ravi goes to a shop."), jkP("تس چھُ اَکھ پشمینہ پسند۔", "Tas chhu akh pashmina pasand.", "He likes a pashmina."), jkP("دُکاندار چھُ شہ ساس وَنان۔", "Dukaandaar chhu shah saas vanaan.", "The shopkeeper says six thousand."), jkP("روی چھُ ژور ساسس ہیوان۔", "Ravi chhu tsor saasas hyevaan.", "Ravi buys it for four thousand.")],
        questions: [{ q: "What does Ravi like?", options: ["A pashmina", "A book", "A kangri"], a: 0 }, { q: "How much does he pay?", options: ["₹6000", "₹4000", "₹400"], a: 1 }] },
    ],
    placement: [
      { q: "What does “Vaaray chhivaa?” mean?", options: ["How much?", "Are you well?", "Where is it?", "Thank you"], a: 1 },
      { q: "How do you ask for one kahwa?", options: ["Akh kahwa diyiv.", "Yi kotah chhu?", "Yeti rukiv.", "Pata mulaqaat!"], a: 0 },
      { q: "What does “kati” mean?", options: ["Where", "When", "How much", "Who"], a: 0 },
      { q: "“Syod gatshiv, pata dachhun” means…", options: ["Stop here", "Go straight, then right", "Turn left", "Wait here"], a: 1 },
      { q: "What is noon chai?", options: ["Pink salt tea", "Coffee", "Lemon water", "Lassi"], a: 0 },
    ],
    achievements: { "first-words": ["🗣️", "First words", "Said your first Kashmiri phrase"], "auto-pro": ["🛺", "Fair-fare pro", "Agreed a fair fare"], foodie: ["🍵", "Kahwa lover", "Ordered tea at the kandur"], bargainer: ["🧣", "Pashmina bargainer", "Won a bargain"] },
    rightNow: [
      [5, 11, "🍞", "Kandur time", "The bakers' ovens are busiest in the morning: noon chai and fresh girda.", "jk_food", jkP("نون چاے چھا؟", "Noon chai chha?", "Do you have noon chai?")],
      [11, 15, "🛶", "Shikara hours", "The Dal Lake is calm at midday. Agree the price first.", "jk_auto", jkP("شِکارہ کتہِ میلہِ؟", "Shikaara kati meli?", "Where can I get a shikara?")],
      [15, 18, "🧣", "Market hours", "The shawl shops of Polo View and Lal Chowk are open.", "jk_shopping", jkP("یہِ کوتاہ چھُ؟", "Yi kotah chhu?", "How much is this?")],
      [18, 22, "🌷", "Garden evening", "The Mughal gardens are at their best in the evening light.", "jk_smalltalk", jkP("کشیر چھےٚ واریاہ خوبصورت!", "Kasheer chhe vaariyah khoobsoorat!", "Kashmir is so beautiful!")],
      [22, 29, "🌙", "Late ride home", "Agree the fare before you get into an auto.", "jk_auto", jkP("کوتاہ پونٛسہٕ؟", "Kotah poonsa?", "How much?")],
    ],
    priceSay: (max, mid) => ({
      ticket: jkP("اَکھ گنٹہٕ کوتاہ؟", "Akh ganta kotah?", "How much for one hour?"), meter: jkP("گۄڈہٕ وَنِو کوتاہ۔", "Gwodah vaniv kotah.", "Tell me how much first."),
      fair: jkP("ٹھیک چھُ۔", "Theek chhu.", "Okay, deal."), counter: jkP(`${max} دِیِو؟`, `${max} diyiv?`, `Will you do it for ₹${max}?`),
      high: jkP(`واریاہ مہنگ چھُ۔ ${mid} دِیِو؟`, `Vaariyah mahang chhu. ${mid} diyiv?`, `That's too expensive. Will you do ₹${mid}?`),
    }),
  },
  // ---------- Dogri (draft) ----------
  doi: {
    tutor: jkTutor("doi", {
      greet: "Namaste ji", language: "Dogri",
      starters: ["I need a ride to Raghunath Bazaar.", "How do I order kalari kulcha?", "How do I bargain for dry fruits?", "What does 'kutthen' mean?", "Where does the matador stop?"],
      glossary: { kutthen: "Where. Raghunath Mandar kutthen ai? = Where's the Raghunath Temple?", kalari: "Jammu's own fried cheese, eaten in a kulcha.", matador: "A shared minibus on a fixed route.",
        "jai mata di": "“Victory to the Mother Goddess”: the greeting of Vaishno Devi pilgrims, heard all over Jammu.", tus: "The polite “you”.", ai: "“Is”. Eh kitne da ai? = How much is this?",
        aan: "“(I) am”.", ghatt: "“Less”. Thodha ghatt karo = make it a bit less.", sajje: "To the right.", khabbe: "To the left.", chaah: "Tea.", dhannvaad: "Thank you." },
      polite: { intro: "Dogri is polite with “tus” and “ji”:", rules: [["\\btu\\b", "tus"], ["\\bkar\\b", "karo ji"]], note: "e.g. “tu” → “tus”; add “ji” to any answer to be respectful." },
      ride: (r, d, dest) => [jkP(d ? `${d[1]} चलगे ओ? कितने पैसे?` : "", `${r} chalge o? Kitne paise?`, `Will you go to ${d ? d[2] : dest}? How much?`),
        jkP(d ? `भाऊ जी, ${d[1]} चलगे ओ?` : "", `Bhau ji, ${r} chalge o?`, `A more polite version: Brother, will you go to ${d ? d[2] : dest}?`, { label: "More polite" }),
        jkP("पैह्लें किराया दस्सो।", "Paihlen kiraaya dasso.", "Tell me the fare first.")],
      intents: [
        ["transport", JK_INTENT_KEYS.metro, "On a matador, try:", [["मटाडोर कुत्थें थम्मदी ऐ?", "Matador kutthen thammdi ai?", "Where does the matador stop?"], ["एह् रघुनाथ बजार जंदी ऐ?", "Eh Raghunath Bazaar jandi ai?", "Does this go to Raghunath Bazaar?"]], "Jammu's matadors run fixed routes for a few rupees a seat."],
        ["shopping", JK_INTENT_KEYS.bargain, "To bargain politely:", [["थोढ़ा घट्ट करो।", "Thodha ghatt karo.", "Please lower it a little."], ["बड़ा म्हंगा ऐ।", "Bada mehnga ai.", "That's too expensive."]], "Bargain where there are no price tags."],
        ["shopping", JK_INTENT_KEYS.price, "Ask the price like this:", [["एह् कितने दा ऐ?", "Eh kitne da ai?", "How much is this?"], ["UPI चलदा ऐ?", "UPI chalda ai?", "Can I pay by UPI?"]]],
        ["food", JK_INTENT_KEYS.food, "Ordering food:", [["इक प्लेट कलाड़ी कुलचा देओ।", "Ik plate kalari kulcha deo.", "One kalari kulcha, please."], ["मिर्च घट्ट पाओ।", "Mirch ghatt pao.", "Not too spicy, please."], ["इक कप चाह्।", "Ik cup chaah.", "A cup of tea, please."]], "Try kalari kulcha and rajmah-chawal."],
        ["directions", JK_INTENT_KEYS.directions, "Asking for directions:", [["रघुनाथ मंदर कुत्थें ऐ?", "Raghunath Mandar kutthen ai?", "Where's the Raghunath Temple?"], ["सिद्धे जाओ, फ्ही सज्जे मुड़ो।", "Siddhe jao, phi sajje mudo.", "Go straight, then turn right."]], "“Sajje” is right and “khabbe” is left."],
        ["college", JK_INTENT_KEYS.college, "At university or work:", [["अज्ज मेरा पैह्ला दिन ऐ।", "Ajj mera paihla din ai.", "It's my first day today."], ["क्लास कुत्थें ऐ?", "Class kutthen ai?", "Where's the class?"]]],
        ["smalltalk", JK_INTENT_KEYS.smalltalk, "Easy small-talk starters:", [["जम्मू च गर्मी बड़ी ऐ, ना?", "Jammu ch garmi badi ai, na?", "It's really hot in Jammu, isn't it?"], ["तुस जम्मू दे ओ?", "Tus Jammu de o?", "Are you from Jammu?"]], "Jammu small talk: the temples, the heat and the trip to Vaishno Devi."],
        ["greetings", JK_INTENT_KEYS.name, "Introduce yourself:", [["मेरा नां एलेक्स ऐ।", "Mera naan Alex ai.", "My name is Alex."], ["तुंदा नां के ऐ?", "Tunda naan ke ai?", "What's your name?"]]],
        ["greetings", JK_INTENT_KEYS.thanks, "Polite essentials:", [["बड़ा धन्नवाद!", "Bada dhannvaad!", "Thanks a lot!"], ["फ्ही दस्सो, जी।", "Phi dasso, ji.", "Could you say that again?"]]],
        ["greetings", JK_INTENT_KEYS.hello, "Greetings that work everywhere in Jammu:", [["नमस्ते जी! तुस कियां ओ?", "Namaste ji! Tus kiyaan o?", "Hello! How are you?"], ["जै माता दी!", "Jai Mata Di!", "Victory to the Mother Goddess! (a Jammu greeting)"]], "“Namaste”, “Ram Ram” and “Jai Mata Di” all work."],
        ["directions", JK_INTENT_KEYS.help, "If you need help:", [["नेड़ें कोई दुआई दी हट्टी ऐ?", "Neden koi duaai di hatti ai?", "Is there a pharmacy nearby?"], ["मेरी मदद करो!", "Meri madad karo!", "Please help me!"]], "Emergency number in India: 112."],
      ],
      generic: [["नमस्ते जी! तुस कियां ओ?", "Namaste ji! Tus kiyaan o?", "Hello! How are you?"], ["एह् कितने दा ऐ?", "Eh kitne da ai?", "How much is this?"], ["थोढ़ी मदद करी देओ?", "Thodhi madad kari deo?", "Could you help me a bit?"]],
    }),
    readings: [
      { title: "Asha in Jammu", level: "A1", lines: [jkP("आशा जम्मू च नमीं ऐ।", "Asha Jammu ch nameen ai.", "Asha is new in Jammu."), jkP("ओह् मटाडोर च रघुनाथ बजार जंदी ऐ।", "Oh matador ch Raghunath Bazaar jandi ai.", "She takes a matador to Raghunath Bazaar."), jkP("उत्थें ओह् कलाड़ी कुलचा खंदी ऐ।", "Utthen oh kalari kulcha khandi ai.", "There she eats a kalari kulcha."), jkP("फ्ही ओह् रघुनाथ मंदर जंदी ऐ।", "Phi oh Raghunath Mandar jandi ai.", "Then she goes to the Raghunath Temple.")],
        questions: [{ q: "Where is Asha new?", options: ["Srinagar", "Jammu", "Delhi"], a: 1 }, { q: "How does she travel?", options: ["By matador", "By shikara", "By metro"], a: 0 }] },
      { title: "Dry fruits in Raghunath Bazaar", level: "A1", lines: [jkP("रवि रघुनाथ बजार जंदा ऐ।", "Ravi Raghunath Bazaar janda ai.", "Ravi goes to Raghunath Bazaar."), jkP("ओह् अखरोट लैना चांह्दा ऐ।", "Oh akhrot laina chaanhda ai.", "He wants to buy walnuts."), jkP("हट्टीआला हज़ार रपे मंगदा ऐ।", "Hattiaala hazaar rape mangda ai.", "The shopkeeper asks for a thousand rupees."), jkP("रवि छे सौ च लैंदा ऐ।", "Ravi chhe sau ch lainda ai.", "Ravi buys them for six hundred.")],
        questions: [{ q: "What does Ravi want?", options: ["Walnuts", "A shawl", "Tea"], a: 0 }, { q: "How much does he pay?", options: ["₹1000", "₹600", "₹60"], a: 1 }] },
    ],
    placement: [
      { q: "What does “Tus kiyaan o?” mean?", options: ["How much?", "How are you?", "Where is it?", "Thank you"], a: 1 },
      { q: "How do you ask an auto driver to go to Raghunath Bazaar?", options: ["Raghunath Bazaar chalge o?", "Kitne hoye?", "Ik cup chaah.", "Phi milchai!"], a: 0 },
      { q: "What does “kutthen” mean?", options: ["Where", "When", "How much", "Who"], a: 0 },
      { q: "“Siddhe jao, phi sajje mudo” means…", options: ["Stop here", "Go straight, then turn right", "Turn left", "Wait here"], a: 1 },
      { q: "What is a matador in Jammu?", options: ["A shared minibus", "A sweet", "A temple", "A shawl"], a: 0 },
    ],
    achievements: { "first-words": ["🗣️", "First words", "Said your first Dogri phrase"], "auto-pro": ["🛺", "Fair-fare pro", "Agreed a fair fare"], foodie: ["🧀", "Kalari lover", "Ordered a Jammu snack"], bargainer: ["🥜", "Bazaar bargainer", "Won a bargain"] },
    rightNow: [
      [5, 11, "🛕", "Temple morning", "The Raghunath Temple is busiest in the morning.", "jk_doi_directions", jkP("रघुनाथ मंदर कुत्थें ऐ?", "Raghunath Mandar kutthen ai?", "Where's the Raghunath Temple?")],
      [11, 15, "🧀", "Lunch time", "Kalari kulcha and rajmah-chawal at the dhabas.", "jk_doi_food", jkP("इक प्लेट कलाड़ी कुलचा देओ।", "Ik plate kalari kulcha deo.", "One kalari kulcha, please.")],
      [15, 18, "🥜", "Market hours", "Raghunath Bazaar is busy. Time to bargain.", "jk_doi_shopping", jkP("थोढ़ा घट्ट करो।", "Thodha ghatt karo.", "Can you lower it a bit?")],
      [18, 22, "🌳", "Evening by the Tawi", "The Bagh-e-Bahu gardens fill up in the evening.", "jk_doi_smalltalk", jkP("बाग-ए-बाहु किन्ना सोह्णा ऐ!", "Bagh-e-Bahu kinna sohna ai!", "The Bagh-e-Bahu is so beautiful!")],
      [22, 29, "🌙", "Late ride home", "Agree the fare before you get into an auto.", "jk_doi_auto", jkP("कितने पैसे लग्गन?", "Kitne paise laggan?", "How much will it cost?")],
    ],
    priceSay: (max, mid) => ({
      ticket: jkP("इक टिकट देओ।", "Ik ticket deo.", "One ticket, please."), meter: jkP("पैह्लें किराया दस्सो।", "Paihlen kiraaya dasso.", "Tell me the fare first."),
      fair: jkP("ठीक ऐ, देओ।", "Theek ai, deo.", "Okay, I'll take it."), counter: jkP(`${max} च देगे?`, `${max} ch dege?`, `Will you do it for ₹${max}?`),
      high: jkP(`बड़ा म्हंगा ऐ। ${mid} च देगे?`, `Bada mehnga ai. ${mid} ch dege?`, `That's too expensive. Will you do ₹${mid}?`),
    }),
  },
  // ---------- Urdu ----------
  ur: {
    tutor: jkTutor("ur", {
      greet: "Assalaam alaikum", language: "Urdu",
      starters: ["I need a ride to Dal Gate.", "How do I order a kahwa?", "How do I bargain for a shawl?", "What does 'meherbaani' mean?", "Where do I get a shikara?"],
      glossary: { meherbaani: "“Kindness”: bahut meherbaani = thank you so much.", "assalaam alaikum": "The everyday hello; the answer is “walaikum assalaam”.", aadaab: "A respectful hello.",
        "khuda hafiz": "Goodbye.", "khush aamdeed": "Welcome!", kahwa: "Green tea with saffron and almonds.", "noon chai": "Pink salt tea.", shikara: "The wooden boat of the Dal Lake.",
        kangri: "A fire-pot carried under the pheran in winter.", pheran: "The long woollen Kashmiri cloak.", sahab: "“Sir”: added after a name to show respect." },
      polite: { intro: "Urdu is polite with “aap” and verbs ending in -iye (“dijiye”, “boliye”, “chaliye”):", rules: [["\\btum\\b", "aap"], ["\\bdo\\b", "dijiye"], ["\\bbolo\\b", "boliye"]], note: "e.g. “tum” → “aap”, “bolo” → “boliye”." },
      ride: (r, d, dest) => [jkP(d ? `${d[1]} چلیں گے؟ کتنا کرایہ ہوگا؟` : "", `${r} chalenge? Kitna kiraaya hoga?`, `Will you go to ${d ? d[2] : dest}? What's the fare?`),
        jkP(d ? `بھائی صاحب، ${d[1]} تک چلیے۔` : "", `Bhai sahab, ${r} tak chaliye.`, `A more polite version: Please take me to ${d ? d[2] : dest}.`, { label: "More polite" }),
        jkP("پہلے کرایہ بتا دیجیے۔", "Pehle kiraaya bata dijiye.", "Please tell me the fare first.")],
      intents: [
        ["transport", JK_INTENT_KEYS.metro, "On the lake, try:", [["شکارا کہاں ملے گا؟", "Shikaara kahan milega?", "Where can I get a shikara?"], ["ایک گھنٹے کا کتنا ہوگا؟", "Ek ghante ka kitna hoga?", "How much for one hour?"]], "Shikara rates are set by the tourism department; ask to see the board at the ghat."],
        ["shopping", JK_INTENT_KEYS.bargain, "To bargain politely:", [["تھوڑا کم کیجیے۔", "Thoda kam kijiye.", "Please lower it a little."], ["بہت مہنگی ہے۔", "Bahut mehngi hai.", "That's too expensive."]], "Bargain where there are no price tags; government emporiums have fixed prices."],
        ["shopping", JK_INTENT_KEYS.price, "Ask the price like this:", [["یہ کتنے کا ہے؟", "Ye kitne ka hai?", "How much is this?"], ["یو پی آئی چلے گا؟", "UPI chalega?", "Can I pay by UPI?"]]],
        ["food", JK_INTENT_KEYS.food, "Ordering tea and bread:", [["ایک قہوہ دیجیے۔", "Ek kahwa dijiye.", "One kahwa, please."], ["نون چائے ملے گی؟", "Noon chai milegi?", "Do you have noon chai?"], ["مرچ کم رکھیے۔", "Mirch kam rakhiye.", "Not too spicy, please."]], "Kahwa in the afternoon, noon chai with fresh bread; for a feast, a wazwan."],
        ["directions", JK_INTENT_KEYS.directions, "Asking for directions:", [["ڈل گیٹ کس طرف ہے؟", "Dal Gate kis taraf hai?", "Which way is Dal Gate?"], ["سیدھے جائیے، پھر دائیں مڑیے۔", "Seedhe jaaiye, phir daayen mudiye.", "Go straight, then turn right."]]],
        ["college", JK_INTENT_KEYS.college, "At university or work:", [["آج میرا پہلا دن ہے۔", "Aaj mera pehla din hai.", "It's my first day today."], ["لائبریری کہاں ہے؟", "Library kahan hai?", "Where's the library?"]]],
        ["smalltalk", JK_INTENT_KEYS.smalltalk, "Easy small-talk starters:", [["کشمیر کتنا خوبصورت ہے!", "Kashmir kitna khoobsoorat hai!", "Kashmir is so beautiful!"], ["آج بہت سردی ہے۔", "Aaj bahut sardi hai.", "It's really cold today."]], "Small talk in J&K: the weather, the snow, the gardens and the food."],
        ["greetings", JK_INTENT_KEYS.name, "Introduce yourself:", [["میرا نام ایلکس ہے۔", "Mera naam Alex hai.", "My name is Alex."], ["آپ کا نام کیا ہے؟", "Aap ka naam kya hai?", "What's your name?"]]],
        ["greetings", JK_INTENT_KEYS.thanks, "Polite essentials:", [["بہت مہربانی!", "Bahut meherbaani!", "Thank you so much!"], ["معاف کیجیے۔", "Maaf kijiye.", "Sorry / Excuse me."]]],
        ["greetings", JK_INTENT_KEYS.hello, "Greetings that work everywhere in J&K:", [["السلام علیکم!", "Assalaam alaikum!", "Hello!"], ["خدا حافظ!", "Khuda hafiz!", "Goodbye!"]], "“Assalaam alaikum”, “Aadaab” and “Namaste” are all everyday greetings."],
        ["directions", JK_INTENT_KEYS.help, "If you need help:", [["مجھے مدد چاہیے۔", "Mujhe madad chahiye.", "I need help."], ["قریب میں ہسپتال کہاں ہے؟", "Qareeb mein hospital kahan hai?", "Where's the nearest hospital?"]], "Emergency number in India: 112."],
      ],
      generic: [["السلام علیکم! مزاج کیسے ہیں؟", "Assalaam alaikum! Mizaaj kaise hain?", "Hello! How are you?"], ["یہ کتنے کا ہے؟", "Ye kitne ka hai?", "How much is this?"], ["کیا آپ میری مدد کریں گے؟", "Kya aap meri madad karenge?", "Could you help me?"]],
    }),
    readings: [
      { title: "Asha in Srinagar", level: "A1", lines: [jkP("آشا سری نگر میں نئی ہے۔", "Asha Srinagar mein nayi hai.", "Asha is new in Srinagar."), jkP("وہ شکارے میں ڈل جھیل دیکھتی ہے۔", "Woh shikaare mein Dal Jheel dekhti hai.", "She sees the Dal Lake from a shikara."), jkP("پھر وہ ایک قہوہ پیتی ہے۔", "Phir woh ek kahwa peeti hai.", "Then she drinks a kahwa."), jkP("شام کو وہ شالیمار باغ جاتی ہے۔", "Shaam ko woh Shalimar Bagh jaati hai.", "In the evening she goes to the Shalimar Bagh.")],
        questions: [{ q: "Where is Asha new?", options: ["Jammu", "Srinagar", "Lucknow"], a: 1 }, { q: "What does she drink?", options: ["Kahwa", "Coffee", "Lassi"], a: 0 }] },
      { title: "A shawl on Residency Road", level: "A1", lines: [jkP("روی ریزیڈنسی روڈ جاتا ہے۔", "Ravi Residency Road jaata hai.", "Ravi goes to Residency Road."), jkP("اسے ایک پشمینہ شال پسند آتی ہے۔", "Use ek pashmina shawl pasand aati hai.", "He likes a pashmina shawl."), jkP("دکاندار چھ ہزار مانگتا ہے۔", "Dukaandaar chhe hazaar maangta hai.", "The shopkeeper asks for six thousand."), jkP("روی چار ہزار میں لیتا ہے۔", "Ravi chaar hazaar mein leta hai.", "Ravi buys it for four thousand.")],
        questions: [{ q: "What does Ravi like?", options: ["A shawl", "A book", "A kangri"], a: 0 }, { q: "How much does he pay?", options: ["₹6000", "₹4000", "₹400"], a: 1 }] },
    ],
    placement: [
      { q: "What does “bahut meherbaani” mean?", options: ["Goodbye", "Thank you so much", "How much?", "Welcome"], a: 1 },
      { q: "How do you ask an auto driver to go to Dal Gate?", options: ["Dal Gate chalenge?", "Kitne paise hue?", "Ek kahwa dijiye.", "Khuda hafiz!"], a: 0 },
      { q: "What does “kitna kiraaya hoga” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
      { q: "“Seedhe jaaiye, phir daayen mudiye” means…", options: ["Stop here", "Go straight, then turn right", "Turn left", "Wait here"], a: 1 },
      { q: "What is a shikara?", options: ["A boat on the Dal Lake", "A shawl", "A bread", "A garden"], a: 0 },
    ],
    achievements: { "first-words": ["🗣️", "First words", "Said your first Urdu phrase"], "auto-pro": ["🛺", "Fair-fare pro", "Agreed a fair fare"], foodie: ["🍵", "Kahwa lover", "Ordered kahwa or noon chai"], bargainer: ["🧣", "Shawl bargainer", "Won a bargain"] },
    rightNow: [
      [5, 11, "🍵", "Breakfast time", "Noon chai and fresh bread are on every table now.", "jk_ur_food", jkP("نون چائے ملے گی؟", "Noon chai milegi?", "Do you have noon chai?")],
      [11, 15, "🛶", "Shikara hours", "The Dal Lake is calm at midday. Agree the price first.", "jk_ur_auto", jkP("شکارا کہاں ملے گا؟", "Shikaara kahan milega?", "Where can I get a shikara?")],
      [15, 18, "🧣", "Market hours", "The shawl shops of Residency Road are open.", "jk_ur_shopping", jkP("یہ شال کتنے کی ہے؟", "Ye shawl kitne ki hai?", "How much is this shawl?")],
      [18, 22, "🌷", "Garden evening", "The Shalimar Bagh is at its best in the evening light.", "jk_ur_smalltalk", jkP("کشمیر کتنا خوبصورت ہے!", "Kashmir kitna khoobsoorat hai!", "Kashmir is so beautiful!")],
      [22, 29, "🌙", "Late ride home", "Agree the fare before you get into an auto.", "jk_ur_auto", jkP("پہلے کرایہ بتا دیجیے۔", "Pehle kiraaya bata dijiye.", "Please tell me the fare first.")],
    ],
    priceSay: (max, mid) => ({
      ticket: jkP("ایک گھنٹے کا کتنا ہوگا؟", "Ek ghante ka kitna hoga?", "How much for one hour?"), meter: jkP("پہلے کرایہ بتا دیجیے۔", "Pehle kiraaya bata dijiye.", "Please tell me the fare first."),
      fair: jkP("ٹھیک ہے، دے دیجیے۔", "Theek hai, de dijiye.", "Okay, I'll take it."), counter: jkP(`${max} میں دیں گے؟`, `${max} mein denge?`, `Will you do it for ₹${max}?`),
      high: jkP(`بہت مہنگا ہے۔ ${mid} میں دیں گے؟`, `Bahut mehenga hai. ${mid} mein denge?`, `That's too expensive. Will you do ₹${mid}?`),
    }),
  },
};

const PLACE_HI = {
  airport: ["airport", "एयरपोर्ट", "the airport"], "connaught place": ["Connaught Place", "कनॉट प्लेस", "Connaught Place"],
  "india gate": ["India Gate", "इंडिया गेट", "India Gate"], "railway station": ["railway station", "रेलवे स्टेशन", "the railway station"],
  station: ["station", "स्टेशन", "the station"], "rajiv chowk": ["Rajiv Chowk", "राजीव चौक", "Rajiv Chowk"],
  "hauz khas": ["Hauz Khas", "हौज़ ख़ास", "Hauz Khas"], "chandni chowk": ["Chandni Chowk", "चाँदनी चौक", "Chandni Chowk"],
  "karol bagh": ["Karol Bagh", "करोल बाग", "Karol Bagh"], "north campus": ["North Campus", "नॉर्थ कैंपस", "North Campus"],
};
window.TUTOR_INTENTS = [
  { m: ["airport", "auto", "rickshaw", "driver", "cab", "taxi", "take me", "go to", "ride"], topic: "transport",
    build: (dest) => { const d = PLACE_HI[dest.toLowerCase()]; const r = d ? d[0] : dest; return { intro: `Try:`, phrases: [
      { roman: `Bhaiya, ${r} chaloge?`, hi: d ? `भैया, ${d[1]} चलोगे?` : "", en: `Brother, will you go to ${d ? d[2] : dest}?` },
      { roman: `Bhaiya, ${r} tak chalenge?`, hi: d ? `भैया, ${d[1]} तक चलेंगे?` : "", en: `A more polite version: Would you take me to ${d ? d[2] : dest}?`, label: "More polite" },
      { roman: "Kitne paise honge?", hi: "कितने पैसे होंगे?", en: "Then ask: How much will it cost?" },
    ], note: "Always agree on the fare (or ask “Meter se chaloge?”) before you sit in." }; } },
  { m: ["metro", "line", "train"], topic: "transport", intro: "At the metro, try:", phrases: [
      { roman: "Rajiv Chowk ke liye kaun si line?", hi: "राजीव चौक के लिए कौन सी लाइन?", en: "Which line for Rajiv Chowk?" },
      { roman: "Yeh metro Huda City Centre jaayegi?", hi: "यह मेट्रो हुडा सिटी सेंटर जाएगी?", en: "Does this metro go to Huda City Centre?" },
    ], note: "Yellow Line = North ↔ South. Blue Line = East ↔ West. Rajiv Chowk is where they meet." },
  { m: ["bargain", "cheaper", "discount", "negotiate", "expensive", "less"], topic: "shopping", intro: "To bargain politely:", phrases: [
      { roman: "Thoda kam kijiye na.", hi: "थोड़ा कम कीजिए ना।", en: "Please lower it a little." },
      { roman: "Bahut mehenga hai, bhaiya.", hi: "बहुत महंगा है, भैया।", en: "It's too expensive, brother." },
      { roman: "400 mein doge?", hi: "400 में दोगे?", en: "Will you give it for 400?" },
    ], note: "Smile, stay friendly, and be ready to walk away — that's usually when the best price appears." },
  { m: ["price", "how much", "cost", "kitne", "pay", "upi"], topic: "shopping", intro: "Ask the price like this:", phrases: [
      { roman: "Yeh kitne ka hai?", hi: "यह कितने का है?", en: "How much is this?" },
      { roman: "UPI chalega?", hi: "यूपीआई चलेगा?", en: "Can I pay by UPI?" },
    ] },
  { m: ["spicy", "food", "order", "eat", "hungry", "restaurant", "menu", "water", "bill"], topic: "food", intro: "Ordering food:", phrases: [
      { roman: "Ek plate chhole bhature dena.", hi: "एक प्लेट छोले भटूरे देना।", en: "One plate of chhole bhature, please." },
      { roman: "Kam teekha banana, please.", hi: "कम तीखा बनाना, प्लीज़।", en: "Less spicy, please." },
      { roman: "Bill de dijiye.", hi: "बिल दे दीजिए।", en: "Can I have the bill?" },
    ], note: "“Dena” is casual (stalls); “dijiye” is polite (restaurants)." },
  { m: ["direction", "where is", "lost", "way", "find", "left", "right"], topic: "directions", intro: "Asking for directions:", phrases: [
      { roman: "Metro station kahan hai?", hi: "मेट्रो स्टेशन कहाँ है?", en: "Where is the metro station?" },
      { roman: "Main raasta bhool gaya hoon.", hi: "मैं रास्ता भूल गया हूँ।", en: "I'm lost. (women say: bhool gayi hoon)" },
      { roman: "Kya yeh paas mein hai?", hi: "क्या यह पास में है?", en: "Is it nearby?" },
    ], note: "Key words: seedhe = straight, baayein = left, daayein = right." },
  { m: ["class", "college", "professor", "teacher", "office", "work", "colleague", "canteen"], topic: "college", intro: "On campus or at work:", phrases: [
      { roman: "Main yahan naya hoon.", hi: "मैं यहाँ नया हूँ।", en: "I'm new here." },
      { roman: "Class kitne baje shuru hogi?", hi: "क्लास कितने बजे शुरू होगी?", en: "When does class start?" },
      { roman: "Kya aap meri madad kar sakte hain?", hi: "क्या आप मेरी मदद कर सकते हैं?", en: "Could you help me?" },
    ] },
  { m: ["friend", "small talk", "chat", "conversation", "weather", "classmate", "chai", "tea"], topic: "smalltalk", intro: "Easy small-talk starters:", phrases: [
      { roman: "Aap kahan se hain?", hi: "आप कहाँ से हैं?", en: "Where are you from?" },
      { roman: "Aajkal bahut garmi hai, na?", hi: "आजकल बहुत गर्मी है, ना?", en: "It's so hot these days, right?" },
      { roman: "Chai piyenge?", hi: "चाय पिएँगे?", en: "Fancy a chai?" },
    ], note: "Adding “na?” at the end invites the other person to agree — very Delhi." },
  { m: ["name", "introduce", "myself", "meet"], topic: "greetings", intro: "Introduce yourself:", phrases: [
      { roman: "Mera naam Alex hai.", hi: "मेरा नाम एलेक्स है।", en: "My name is Alex." },
      { roman: "Aapka naam kya hai?", hi: "आपका नाम क्या है?", en: "What's your name?" },
      { roman: "Aapse milkar accha laga.", hi: "आपसे मिलकर अच्छा लगा।", en: "Nice to meet you." },
    ] },
  { m: ["thank", "sorry", "excuse", "please"], topic: "greetings", intro: "Polite essentials:", phrases: [
      { roman: "Bahut shukriya!", hi: "बहुत शुक्रिया!", en: "Thanks a lot!" },
      { roman: "Maaf kijiye.", hi: "माफ़ कीजिए।", en: "Sorry / Excuse me." },
      { roman: "Suniye…", hi: "सुनिए…", en: "Excuse me… (to get attention)" },
    ] },
  { m: ["hello", "hi", "greet", "namaste", "bye", "good morning"], topic: "greetings", intro: "Greetings that work everywhere:", phrases: [
      { roman: "Namaste, aap kaise hain?", hi: "नमस्ते, आप कैसे हैं?", en: "Hello, how are you?" },
      { roman: "Phir milte hain!", hi: "फिर मिलते हैं!", en: "See you later!" },
    ] },
  { m: ["help", "emergency", "doctor", "police", "sick"], topic: "directions", intro: "If you need help:", phrases: [
      { roman: "Mujhe madad chahiye.", hi: "मुझे मदद चाहिए।", en: "I need help." },
      { roman: "Paas mein hospital kahan hai?", hi: "पास में हॉस्पिटल कहाँ है?", en: "Where's the nearest hospital?" },
    ], note: "Emergency number in India: 112." },
];

window.GLOSSARY = {
  namaste: "A respectful hello (and goodbye). Works with anyone, any time.",
  bhaiya: "“Brother” — friendly way to address drivers, shopkeepers, anyone male around your age or older.",
  didi: "“Elder sister” — the female equivalent of bhaiya.",
  accha: "“Okay / I see / Really?” — the most versatile word in Hindi.",
  achha: "“Okay / I see / Really?” — the most versatile word in Hindi.",
  "theek hai": "“Okay / Fine / Alright.”",
  chalo: "“Let's go / Alright then.” Also used to wrap up a conversation.",
  yaar: "“Buddy / dude” — casual, use with friends only.",
  arre: "An exclamation like “Oh!” or “Hey!” — surprise or mild protest.",
  ji: "Respect marker. Add after names or “haan ji” (yes, politely).",
  jugaad: "A clever, improvised fix. A very Delhi concept!",
  kitne: "“How many / how much.” Kitne paise? = How much money?",
  paise: "Money (literally the smallest unit of a rupee).",
  shukriya: "Thank you (common in everyday speech).",
  dhanyavaad: "Thank you (a bit more formal).",
  haan: "Yes.", nahi: "No.", "kya": "What.", kahan: "Where.",
};

window.READINGS = [
  { title: "Ravi in Delhi", level: "A1", lines: [
      { hi: "रवि दिल्ली में नया है।", roman: "Ravi Dilli mein naya hai.", en: "Ravi is new in Delhi." },
      { hi: "वह कॉलेज जा रहा है।", roman: "Vah college ja raha hai.", en: "He is going to college." },
      { hi: "वह ऑटो लेता है।", roman: "Vah auto leta hai.", en: "He takes an auto." },
      { hi: "ऑटो वाला पूछता है, “कहाँ जाना है?”", roman: "Auto wala poochta hai, “Kahan jaana hai?”", en: "The auto driver asks, “Where to?”" },
      { hi: "रवि कहता है, “नॉर्थ कैंपस, भैया।”", roman: "Ravi kehta hai, “North Campus, bhaiya.”", en: "Ravi says, “North Campus, brother.”" },
    ],
    questions: [
      { q: "Where is Ravi new?", options: ["Mumbai", "Delhi", "Chennai"], a: 1 },
      { q: "How does Ravi travel?", options: ["By metro", "By bus", "By auto"], a: 2 },
      { q: "Where is Ravi going?", options: ["North Campus", "Airport", "Market"], a: 0 },
    ] },
  { title: "Lunch at the market", level: "A1", lines: [
      { hi: "प्रिया को भूख लगी है।", roman: "Priya ko bhookh lagi hai.", en: "Priya is hungry." },
      { hi: "वह चाँदनी चौक जाती है।", roman: "Vah Chandni Chowk jaati hai.", en: "She goes to Chandni Chowk." },
      { hi: "वह पराठे खाती है।", roman: "Vah paraathe khaati hai.", en: "She eats parathas." },
      { hi: "पराठे बहुत स्वादिष्ट हैं!", roman: "Paraathe bahut swaadisht hain!", en: "The parathas are very tasty!" },
    ],
    questions: [
      { q: "How does Priya feel?", options: ["Tired", "Hungry", "Cold"], a: 1 },
      { q: "What does she eat?", options: ["Parathas", "Samosa", "Biryani"], a: 0 },
    ] },
];

window.PLACEMENT = [
  { q: "What does “Namaste” mean?", options: ["Goodbye only", "A respectful hello", "Thank you", "How much?"], a: 1 },
  { q: "How would you ask someone's name?", options: ["Aapka naam kya hai?", "Kitne paise?", "Yahin rok dijiye.", "Chai piyenge?"], a: 0 },
  { q: "What does “kitne paise” relate to?", options: ["Directions", "Time", "Price / money", "Food"], a: 2 },
  { q: "“Seedhe jaiye, phir baayein mudiye” means…", options: ["Stop here", "Go straight, then left", "Turn right twice", "Come back later"], a: 1 },
  { q: "Which is the most polite way to ask for the bill?", options: ["Bill do", "Bill de dijiye", "Bill!", "Bill dena yaar"], a: 1 },
];
