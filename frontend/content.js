// Content + configuration. New languages/cities plug in here.
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
];

window.CITIES = [
  { id: "delhi", name: "Delhi", flag: "🇮🇳", tag: "Dilli", blurb: "Metro, autos, chaat & Sarojini", langs: ["hi", "hinglish", "en"], ready: true, emoji: "🕌" },
  { id: "mumbai", name: "Mumbai", flag: "🇮🇳", tag: "Marathi · Hindi", blurb: "Locals, vada pav & the sea", langs: ["hi", "en"], ready: false, emoji: "🌊" },
  { id: "bengaluru", name: "Bengaluru", flag: "🇮🇳", tag: "Kannada", blurb: "Filter coffee & tech parks", langs: ["en"], ready: false, emoji: "☕" },
  { id: "hyderabad", name: "Hyderabad", flag: "🇮🇳", tag: "Telugu · Urdu", blurb: "Biryani & Charminar", langs: ["en"], ready: false, emoji: "🍚" },
  { id: "chennai", name: "Chennai", flag: "🇮🇳", tag: "Tamil", blurb: "Marina, idli & auto talk", langs: ["en"], ready: false, emoji: "🏖️" },
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
