"""Rules for the legacy prototype AI endpoint (POST /api/ai). No HTTP in here.

The endpoint predates the Phase 11 tutor and talks to the LLM configured in .env, so it is fenced in:
  * who may reach the real model: an anonymous visitor only if DEMO_LIVE_AI is on; a signed-in learner only if their profile puts them in a
    LIVE_AGE_GROUPS age group. A child never does, a learner with no profile (age unknown) never does, and parents and admins never do.
    Everyone else gets {"ok": false, "reason": "offline"} and the frontend's built-in engine answers;
  * what may reach it: a strict request shape. The roleplay scene is named by id and its text comes from SCENARIOS below, never from the
    client; city and level must exist in the database; messages and history are bounded and anything larger is refused, not cut;
  * how often: a per-caller sliding window (per process, like the login throttle)."""
import math
import time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from .. import settings
from ..db import connect
from ..personalization.context import NeedsProfile, learner_context

LIVE_AGE_GROUPS = ("teen", "adult")

# The legacy roleplay scenes (frontend/content.js SCENARIOS): the only scene text that can reach the system prompt.
SCENARIOS = {
    "auto": {"partner": "Raju bhaiya", "role": "Auto driver", "place": "Outside Kashmere Gate metro", "goal": "Get to Connaught Place for a fair price."},
    "smalltalk": {"partner": "Priya", "role": "Classmate", "place": "Chai stall outside North Campus", "goal": "Introduce yourself and make weekend plans."},
    "greetings": {"partner": "Sharma aunty", "role": "PG owner", "place": "Your PG in Laxmi Nagar", "goal": "Greet politely and introduce yourself."},
    "food": {"partner": "Sethi ji", "role": "Stall owner", "place": "Chhole bhature stall, Kamla Nagar", "goal": "Order lunch, ask for less spice and pay."},
    "shopping": {"partner": "Vicky", "role": "Shopkeeper", "place": "Sarojini Nagar market", "goal": "Buy a jacket at a fair price."},
    "directions": {"partner": "Uncle ji", "role": "Passerby", "place": "Near Lajpat Nagar market", "goal": "Find the nearest metro station."},
    "college": {"partner": "Rohan", "role": "Senior", "place": "Main gate, Delhi University", "goal": "Find your class and ask for help."},
    # Mumbai (frontend/content.js PACKS.mumbai)
    "mum_greetings": {"partner": "Joshi kaka", "role": "Society secretary", "place": "Your building in Andheri West", "goal": "Greet politely, introduce yourself and ask about the water timings."},
    "mum_taxi": {"partner": "Sharma ji", "role": "Taxi driver", "place": "Outside Andheri station (West)", "goal": "Get to Churchgate by the meter."},
    "mum_food": {"partner": "Ganesh bhau", "role": "Stall owner", "place": "Vada pav stall outside Dadar station", "goal": "Order a vada pav and a cutting chai, and pay."},
    "mum_shopping": {"partner": "Imran bhai", "role": "Shopkeeper", "place": "Colaba Causeway", "goal": "Buy a kurta at a fair price."},
    "mum_directions": {"partner": "Kulkarni kaku", "role": "Passerby", "place": "Outside Andheri station", "goal": "Find out which side you need and how to get there."},
    "mum_college": {"partner": "Neha", "role": "Colleague", "place": "Office in BKC (Bandra Kurla Complex)", "goal": "Introduce yourself and find out about the meeting and lunch."},
    "mum_smalltalk": {"partner": "Aditya", "role": "Flatmate", "place": "Marine Drive, at the start of the monsoon", "goal": "Chat about Mumbai and make weekend plans."},
    # Mumbai in Marathi (frontend/content.js LANGUAGE_PACKS.mumbai.mr)
    "mum_mr_greetings": {"partner": "Joshi kaka", "role": "Society secretary", "place": "Your building in Andheri West", "goal": "Greet politely in Marathi, introduce yourself and ask about the water timings."},
    "mum_mr_taxi": {"partner": "Shinde kaka", "role": "Taxi driver", "place": "Outside Andheri station (West)", "goal": "Get to Churchgate by the meter, in Marathi."},
    "mum_mr_food": {"partner": "Ganesh bhau", "role": "Stall owner", "place": "Vada pav stall outside Dadar station", "goal": "Order a vada pav and a cutting chai in Marathi, and pay."},
    "mum_mr_shopping": {"partner": "Pawar kaka", "role": "Shopkeeper", "place": "Ranade Road market, Dadar", "goal": "Buy a kurta at a fair price, in Marathi."},
    "mum_mr_directions": {"partner": "Kulkarni kaku", "role": "Passerby", "place": "Outside Andheri station", "goal": "Find out in Marathi which side you need and how to get there."},
    "mum_mr_college": {"partner": "Sayali", "role": "Colleague", "place": "Office in BKC (Bandra Kurla Complex)", "goal": "Introduce yourself in Marathi and find out about the meeting and lunch."},
    "mum_mr_smalltalk": {"partner": "Aditya", "role": "Flatmate", "place": "Marine Drive, at the start of the monsoon", "goal": "Chat in Marathi about Mumbai and make weekend plans."},
    # Bengaluru, in Kannada (frontend/content.js PACKS.bengaluru)
    "blr_greetings": {"partner": "Lakshmamma", "role": "House owner", "place": "Your rented flat in Jayanagar", "goal": "Greet politely, introduce yourself and ask when the water comes."},
    "blr_auto": {"partner": "Manju", "role": "Auto driver", "place": "Outside MG Road metro station", "goal": "Get to Indiranagar by the meter."},
    "blr_food": {"partner": "Raghu", "role": "Counter staff", "place": "A darshini in Malleshwaram", "goal": "Order a dosa and a coffee, ask for water and pay."},
    "blr_shopping": {"partner": "Prakash", "role": "Shopkeeper", "place": "Commercial Street", "goal": "Buy a kurta in your size at a fair price, and pay by UPI."},
    "blr_directions": {"partner": "Shankar", "role": "Passerby", "place": "Near Jayanagar 4th Block", "goal": "Find the nearest metro station, and a pharmacy on the way."},
    "blr_college": {"partner": "Divya", "role": "Colleague", "place": "A tech park in Whitefield", "goal": "Introduce yourself and find out about the meeting and lunch."},
    "blr_smalltalk": {"partner": "Kiran", "role": "Flatmate", "place": "Cubbon Park on a Sunday morning", "goal": "Chat about Bengaluru and make weekend plans."},
    # Chennai, in Tamil (frontend/content.js PACKS.chennai)
    "chn_greetings": {"partner": "Saroja amma", "role": "House owner", "place": "Your rented flat in Mylapore", "goal": "Greet politely, introduce yourself and ask when the water comes."},
    "chn_auto": {"partner": "Murugan", "role": "Auto driver", "place": "Outside Chennai Central station", "goal": "Get to T. Nagar for a fair fare."},
    "chn_food": {"partner": "Selvam", "role": "Waiter", "place": "A tiffin centre in Mylapore", "goal": "Order idli and a filter coffee, ask for water and pay."},
    "chn_shopping": {"partner": "Kumar", "role": "Shopkeeper", "place": "Ranganathan Street, T. Nagar", "goal": "Buy a kurta in your size at a fair price, and pay by GPay."},
    "chn_directions": {"partner": "Raghavan", "role": "Passerby", "place": "Near the Mylapore tank", "goal": "Find the nearest metro station, and a pharmacy on the way."},
    "chn_college": {"partner": "Priya", "role": "Colleague", "place": "An office on the OMR IT corridor", "goal": "Introduce yourself and find out about the meeting and lunch."},
    "chn_smalltalk": {"partner": "Karthik", "role": "Flatmate", "place": "Marina Beach in the evening", "goal": "Chat about Chennai and make weekend plans."},
    # Puducherry, in Tamil (frontend/content.js PACKS.puducherry) and in French (LANGUAGE_PACKS.puducherry.fr)
    "pdy_greetings": {"partner": "Selvi", "role": "Guesthouse owner", "place": "Your guesthouse in White Town", "goal": "Greet your host, introduce yourself and ask when breakfast is."},
    "pdy_scooter": {"partner": "Velu", "role": "Rental shop owner", "place": "A scooter rental shop on Mission Street", "goal": "Rent a scooter for the day at a fair price, with a helmet."},
    "pdy_food": {"partner": "Rajesh", "role": "Waiter", "place": "A seaside restaurant on the Promenade", "goal": "Order a fish curry meal and a fresh lime soda, ask for less spice and pay."},
    "pdy_shopping": {"partner": "Anand", "role": "Shopkeeper", "place": "Nehru Street, near Goubert Market", "goal": "Buy a handloom bag at a fair price."},
    "pdy_directions": {"partner": "Arul", "role": "Passerby", "place": "Outside the Puducherry bus stand", "goal": "Find the way to the Promenade beach, and a café near it."},
    "pdy_college": {"partner": "Kavitha", "role": "Classmate", "place": "Pondicherry University campus", "goal": "Find your department and the library, and make a friend."},
    "pdy_smalltalk": {"partner": "Bala", "role": "Friend", "place": "The Promenade at sunrise", "goal": "Chat about Puducherry and plan a trip to Auroville."},
    "pdy_fr_greetings": {"partner": "Madame Rosaline", "role": "Host", "place": "A heritage home on Rue Dumas, White Town", "goal": "Greet your host in French, introduce yourself and ask about breakfast."},
    "pdy_fr_bike": {"partner": "Monsieur Pierre", "role": "Bicycle rental owner", "place": "A bicycle rental on Rue Suffren", "goal": "Rent a bicycle for the day, with a helmet, and find the way to Auroville."},
    "pdy_fr_food": {"partner": "Julien", "role": "Café owner", "place": "A café on Rue Romain Rolland", "goal": "Order breakfast in French, ask what's good and pay."},
    "pdy_fr_shopping": {"partner": "Madame Claire", "role": "Boutique owner", "place": "A boutique on Rue Suffren", "goal": "Buy a handmade bag and pay by card."},
    "pdy_fr_directions": {"partner": "Monsieur Joseph", "role": "Passerby", "place": "Near the French Consulate, White Town", "goal": "Find the Promenade and the Alliance française."},
    "pdy_fr_college": {"partner": "Sophie", "role": "Classmate", "place": "A French class at the Alliance française", "goal": "Introduce yourself, find out when the class starts and make a friend."},
    "pdy_fr_smalltalk": {"partner": "Marc", "role": "Friend", "place": "A café terrace on the Promenade", "goal": "Chat about Pondicherry and plan a Sunday trip to Auroville."},
    # Jaipur and Lucknow, in Hindi (frontend/content.js PACKS.jaipur, PACKS.lucknow)
    "jpr_greetings": {"partner": "Kamla ji", "role": "PG owner", "place": "Your PG in Malviya Nagar", "goal": "Greet politely, introduce yourself and ask about the meal times."},
    "jpr_auto": {"partner": "Ramesh", "role": "Auto driver", "place": "Outside Jaipur Junction railway station", "goal": "Get to Hawa Mahal for a fair fare."},
    "jpr_food": {"partner": "Gopal ji", "role": "Shopkeeper", "place": "A sweet shop in Johari Bazaar", "goal": "Order a pyaaz kachori and a lassi, and pay."},
    "jpr_shopping": {"partner": "Vikram", "role": "Shopkeeper", "place": "Bapu Bazaar", "goal": "Buy a pair of mojaris at a fair price."},
    "jpr_directions": {"partner": "Mohan ji", "role": "Passerby", "place": "Badi Chaupar, in the old city", "goal": "Find the way to Hawa Mahal, and a pharmacy."},
    "jpr_college": {"partner": "Pooja", "role": "Classmate", "place": "A college campus in Malviya Nagar", "goal": "Find your class and the canteen, and make a friend."},
    "jpr_smalltalk": {"partner": "Rohit", "role": "Flatmate", "place": "Nahargarh Fort at sunset", "goal": "Chat about Jaipur and plan a weekend trip."},
    "lko_greetings": {"partner": "Mirza sahab", "role": "Landlord", "place": "Your rented flat in Gomti Nagar", "goal": "Greet your landlord the Lucknowi way, introduce yourself and ask about the water."},
    "lko_auto": {"partner": "Rafiq", "role": "Auto driver", "place": "Outside Charbagh railway station", "goal": "Get to Hazratganj for a fair fare."},
    "lko_food": {"partner": "Haji sahab", "role": "Kebab shop owner", "place": "A kebab shop in Aminabad", "goal": "Order kebabs and biryani, or a vegetarian dish, and pay."},
    "lko_shopping": {"partner": "Naseem", "role": "Shopkeeper", "place": "A chikankari shop in Chowk", "goal": "Buy a chikankari kurta at a fair price."},
    "lko_directions": {"partner": "Verma ji", "role": "Passerby", "place": "Near the Bara Imambara", "goal": "Find the way to the Rumi Darwaza, and a pharmacy."},
    "lko_college": {"partner": "Ayesha", "role": "Classmate", "place": "Lucknow University campus", "goal": "Find your department and the library, and make a friend."},
    "lko_smalltalk": {"partner": "Faraz", "role": "Friend", "place": "The Gomti riverfront at sunset", "goal": "Chat about Lucknow and plan a Sunday food walk."},
    # Kolkata, in Bengali (frontend/content.js PACKS.kolkata)
    "kol_greetings": {"partner": "Mitra mashima", "role": "Landlady", "place": "Your rented flat in Salt Lake", "goal": "Greet your landlady politely, introduce yourself and ask when the water comes."},
    "kol_taxi": {"partner": "Bapi da", "role": "Taxi driver", "place": "The taxi stand outside Howrah Station", "goal": "Get to Park Street by the meter."},
    "kol_food": {"partner": "Shibu da", "role": "Roll stall owner", "place": "A kathi roll stall near Park Street", "goal": "Order a roll and a cup of tea, ask for less chilli and pay."},
    "kol_shopping": {"partner": "Rina di", "role": "Shopkeeper", "place": "A saree stall in Gariahat Market", "goal": "Buy a handloom cotton saree at a fair price."},
    "kol_directions": {"partner": "Ghosh babu", "role": "Passerby", "place": "Outside Esplanade metro station", "goal": "Find the way to the Victoria Memorial, and a pharmacy."},
    "kol_college": {"partner": "Priya", "role": "Classmate", "place": "Jadavpur University campus", "goal": "Find your class and the canteen, and make a friend."},
    "kol_smalltalk": {"partner": "Arko", "role": "Friend", "place": "Prinsep Ghat at sunset", "goal": "Have an adda about Kolkata and plan a Sunday at College Street."},
    # Hyderabad, in Telugu (frontend/content.js PACKS.hyderabad) and in Urdu (LANGUAGE_PACKS.hyderabad.ur)
    "hyd_greetings": {"partner": "Lakshmi garu", "role": "House owner", "place": "Your rented flat in Madhapur", "goal": "Greet politely, introduce yourself and ask when the water comes."},
    "hyd_auto": {"partner": "Srinu", "role": "Auto driver", "place": "Outside Secunderabad railway station", "goal": "Get to Banjara Hills for a fair fare."},
    "hyd_food": {"partner": "Raju", "role": "Waiter", "place": "An Irani café in the old city", "goal": "Order biryani and an Irani chai, ask for less chilli and pay."},
    "hyd_shopping": {"partner": "Farida", "role": "Shopkeeper", "place": "A bangle shop in Laad Bazaar, near the Charminar", "goal": "Buy a set of lac bangles at a fair price."},
    "hyd_directions": {"partner": "Venkat", "role": "Passerby", "place": "By the Charminar", "goal": "Find the way to Chowmahalla Palace, and a pharmacy."},
    "hyd_college": {"partner": "Sneha", "role": "Colleague", "place": "An office in HITEC City", "goal": "Introduce yourself and find out about the meeting and the canteen."},
    "hyd_smalltalk": {"partner": "Ravi", "role": "Flatmate", "place": "Tank Bund, by Hussain Sagar, at sunset", "goal": "Chat about Hyderabad and plan a trip to Golconda Fort."},
    "hyd_ur_greetings": {"partner": "Nawab sahab", "role": "Landlord", "place": "Your rented flat in Tolichowki", "goal": "Greet your landlord, introduce yourself and ask about the water."},
    "hyd_ur_auto": {"partner": "Salim bhai", "role": "Auto driver", "place": "Outside Nampally station", "goal": "Get to the Charminar by the meter."},
    "hyd_ur_food": {"partner": "Anwar", "role": "Waiter", "place": "An Irani café near the Charminar", "goal": "Order biryani and Irani chai, ask for less chilli and pay."},
    "hyd_ur_shopping": {"partner": "Kareem sahab", "role": "Shopkeeper", "place": "A pearl shop in Pathargatti", "goal": "Buy a string of pearls at a fair price."},
    "hyd_ur_directions": {"partner": "Habeeb bhai", "role": "Passerby", "place": "By the Charminar", "goal": "Find the way to the Mecca Masjid, and a pharmacy."},
    "hyd_ur_college": {"partner": "Sana", "role": "Classmate", "place": "Maulana Azad National Urdu University, Gachibowli", "goal": "Find the library and the canteen, and make a friend."},
    "hyd_ur_smalltalk": {"partner": "Imran", "role": "Friend", "place": "By the Charminar in the evening", "goal": "Chat about Hyderabad and plan a Sunday at Golconda."},
    # Bhopal, in Hindi (frontend/content.js PACKS.bhopal)
    "bpl_greetings": {"partner": "Sharma aunty", "role": "Neighbour", "place": "Your rented flat in Arera Colony", "goal": "Greet your neighbour, introduce yourself and ask about the water."},
    "bpl_auto": {"partner": "Rafiq bhai", "role": "Auto driver", "place": "Outside Rani Kamlapati railway station", "goal": "Get to New Market for a fair fare."},
    "bpl_food": {"partner": "Mishra ji", "role": "Stall owner", "place": "A breakfast stall near New Market", "goal": "Order poha-jalebi and a chai, and pay."},
    "bpl_shopping": {"partner": "Saleem miyan", "role": "Shopkeeper", "place": "Chowk Bazaar, in the old city", "goal": "Buy a zari batua at a fair price."},
    "bpl_directions": {"partner": "Qureshi sahab", "role": "Passerby", "place": "Peer Gate, in the old city", "goal": "Find the way to the Taj-ul-Masajid, and a pharmacy."},
    "bpl_college": {"partner": "Neha", "role": "Classmate", "place": "A college near MP Nagar", "goal": "Find your class and the canteen, and make a friend."},
    "bpl_smalltalk": {"partner": "Arif", "role": "Friend", "place": "The Boat Club on the Upper Lake at sunset", "goal": "Chat about Bhopal and plan a Sunday trip to Sanchi."},
    # Shimla, in Hindi (frontend/content.js PACKS.shimla)
    "shm_greetings": {"partner": "Negi aunty", "role": "Landlady", "place": "Your rented room in Sanjauli", "goal": "Greet your landlady, introduce yourself and ask about the water."},
    "shm_taxi": {"partner": "Pawan bhai", "role": "Taxi driver", "place": "The Tutikandi bus stand (ISBT)", "goal": "Get to the Lift, below the Mall, for a fair fare."},
    "shm_food": {"partner": "Thakur ji", "role": "Dhaba owner", "place": "A dhaba in Lower Bazaar", "goal": "Order siddu and a chai, ask about the dham, and pay."},
    "shm_shopping": {"partner": "Rajesh bhai", "role": "Shopkeeper", "place": "Lakkar Bazaar, by the Ridge", "goal": "Buy a Himachali topi at a fair price."},
    "shm_directions": {"partner": "Verma ji", "role": "Passerby", "place": "Scandal Point, on the Mall", "goal": "Find the way to the Jakhu Temple, and a pharmacy."},
    "shm_college": {"partner": "Kritika", "role": "Classmate", "place": "Himachal Pradesh University, Summer Hill", "goal": "Find your class and the canteen, and make a friend."},
    "shm_smalltalk": {"partner": "Ankit", "role": "Friend", "place": "The Ridge at sunset", "goal": "Chat about Shimla and plan a Sunday trip to Kufri."},
    # Jammu & Kashmir, in Kashmiri (PACKS.jk), Dogri and Urdu (LANGUAGE_PACKS.jk)
    "jk_greetings": {"partner": "Bashir sahab", "role": "Houseboat owner", "place": "A houseboat on the Dal Lake", "goal": "Greet your host, introduce yourself and ask for a kahwa."},
    "jk_auto": {"partner": "Mushtaq", "role": "Auto driver", "place": "Lal Chowk", "goal": "Get to Nishat Bagh for a fair fare."},
    "jk_food": {"partner": "Rafiq", "role": "Baker", "place": "A kandur (bakery) near Lal Chowk", "goal": "Order kahwa or noon chai with bread, and pay."},
    "jk_shopping": {"partner": "Showkat", "role": "Shopkeeper", "place": "A shawl shop on Polo View, near Lal Chowk", "goal": "Buy a pashmina shawl at a fair price."},
    "jk_directions": {"partner": "Ghulam Rasool", "role": "Passerby", "place": "The clock tower, Lal Chowk", "goal": "Find the way to the Dal Lake, and a pharmacy."},
    "jk_college": {"partner": "Insha", "role": "Classmate", "place": "University of Kashmir, Hazratbal", "goal": "Find your class, have tea and make a friend."},
    "jk_smalltalk": {"partner": "Aamir", "role": "Friend", "place": "The Nishat Bagh at sunset", "goal": "Chat about Kashmir and plan a Sunday trip to Gulmarg."},
    "jk_doi_greetings": {"partner": "Sharma ji", "role": "Landlord", "place": "Your rented room in Gandhi Nagar, Jammu", "goal": "Greet your landlord, introduce yourself and ask about the water."},
    "jk_doi_auto": {"partner": "Kuldeep", "role": "Auto driver", "place": "Outside Jammu Tawi railway station", "goal": "Get to Raghunath Bazaar for a fair fare."},
    "jk_doi_food": {"partner": "Bittu", "role": "Dhaba owner", "place": "A dhaba near the Raghunath Bazaar", "goal": "Order kalari kulcha and rajmah-chawal, and pay."},
    "jk_doi_shopping": {"partner": "Gupta ji", "role": "Shopkeeper", "place": "A dry-fruit shop in Raghunath Bazaar", "goal": "Buy walnuts and almonds at a fair price."},
    "jk_doi_directions": {"partner": "Pandit ji", "role": "Passerby", "place": "The old city, Jammu", "goal": "Find the way to the Raghunath Temple, and a pharmacy."},
    "jk_doi_college": {"partner": "Ritika", "role": "Classmate", "place": "University of Jammu campus", "goal": "Find your class and the canteen, and make a friend."},
    "jk_doi_smalltalk": {"partner": "Ankush", "role": "Friend", "place": "The Bagh-e-Bahu gardens by the Tawi", "goal": "Chat about Jammu and plan a Sunday trip to Katra."},
    "jk_ur_greetings": {"partner": "Mir sahab", "role": "Landlord", "place": "Your rented room in Rajbagh, Srinagar", "goal": "Greet your landlord, introduce yourself and ask about the heating."},
    "jk_ur_auto": {"partner": "Farooq", "role": "Auto driver", "place": "Lal Chowk, Srinagar", "goal": "Get to Dal Gate for a fair fare, and find a shikara."},
    "jk_ur_food": {"partner": "Javed", "role": "Waiter", "place": "A café on Residency Road, Srinagar", "goal": "Order kahwa or noon chai with bread, and pay."},
    "jk_ur_shopping": {"partner": "Nazir sahab", "role": "Shopkeeper", "place": "A shawl shop on Residency Road", "goal": "Buy a shawl at a fair price."},
    "jk_ur_directions": {"partner": "Bhat sahab", "role": "Passerby", "place": "Near the Jammu bus stand", "goal": "Find the way to the Raghunath Temple, and a pharmacy."},
    "jk_ur_college": {"partner": "Mehvish", "role": "Classmate", "place": "University of Kashmir, Srinagar", "goal": "Find the library and the canteen, and make a friend."},
    "jk_ur_smalltalk": {"partner": "Zoya", "role": "Friend", "place": "The Shalimar Bagh at sunset", "goal": "Chat about Kashmir and plan a Sunday trip to Gulmarg."},
}
# A language the prototype's AI may be asked to answer in only where the city offers it (city_languages): its catalogue code.
CITY_LANGUAGE_CODES = {"Marathi": "mr", "Kannada": "kn", "Tamil": "ta", "French": "fr", "Bengali": "bn", "Telugu": "te", "Urdu": "ur", "Kashmiri": "ks", "Dogri": "doi"}


class HistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["me", "ai"]
    text: StrictStr = Field(max_length=settings.LEGACY_AI_MAX_MESSAGE_CHARS)


class LegacyAiIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["tutor", "roleplay"] = "tutor"
    city: StrictStr = Field(default="Delhi", min_length=1, max_length=40)      # checked against the cities table by the route
    language: Literal["Hindi", "Hindi (Hinglish)", "Marathi", "Kannada", "Tamil", "French", "Bengali", "Telugu", "Urdu", "Kashmiri", "Dogri"] = "Hindi"
    level: StrictStr = Field(default="A1", min_length=1, max_length=4)        # checked against cefr_levels by the route
    scenario: Literal[tuple(SCENARIOS)] | None = None
    history: list[HistoryItem] = Field(default_factory=list, max_length=settings.LEGACY_AI_MAX_HISTORY)

    @model_validator(mode="after")
    def roleplay_needs_a_scene(self):
        if self.mode == "roleplay" and self.scenario is None:
            raise ValueError("a roleplay needs a scenario")
        return self


def live_allowed(db_path, user) -> bool:
    """May this caller's request go to the real model? (Whether a model is configured at all is checked separately.)"""
    if user is None:
        return settings.demo_live_ai()
    if not user.has_any_role("learner"):
        return False
    with connect(db_path) as conn:
        try:
            ctx = learner_context(conn, user.id)
        except NeedsProfile:
            return False
    return ctx["age_group_code"] in LIVE_AGE_GROUPS


# ---------- rate limit ----------
_hits: dict = {}          # caller key -> times of recent requests, oldest first
_clock = time.monotonic   # replaced in tests


def reset_throttle():
    _hits.clear()


def caller_key(user, client_host):
    return f"user:{user.id}" if user is not None else f"ip:{client_host or '-'}"


def hit(key):
    """Record one request. Returns None if it is within the limit, otherwise the seconds until the caller may try again
    (the over-limit request is not recorded). Memory is bounded: at most LEGACY_AI_MAX_TRACKED_CALLERS callers are remembered."""
    now, window = _clock(), settings.LEGACY_AI_WINDOW_SECONDS
    recent = [t for t in _hits.get(key, ()) if now - t < window]
    if len(recent) >= settings.LEGACY_AI_MAX_REQUESTS:
        _hits[key] = recent
        return max(1, math.ceil(recent[0] + window - now))
    if key not in _hits and len(_hits) >= settings.LEGACY_AI_MAX_TRACKED_CALLERS:
        for stale in [k for k, times in _hits.items() if not times or now - times[-1] >= window]:
            del _hits[stale]
        while len(_hits) >= settings.LEGACY_AI_MAX_TRACKED_CALLERS:
            del _hits[next(iter(_hits))]                       # the longest-remembered caller goes first
    recent.append(now)
    _hits[key] = recent
    return None
