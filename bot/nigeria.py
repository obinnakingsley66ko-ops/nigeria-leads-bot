"""Nigerian geography + industry taxonomy and resolvers.

`CITIES` maps a normalised key to an Overpass bounding box (S, W, N, E).
`INDUSTRIES` maps an industry key to its display label, aliases and the
OpenStreetMap tag queries used by the collector.
"""
import re

# key -> (south, west, north, east)
CITIES = {
    "lagos": (6.39, 3.10, 6.70, 3.75),
    "abuja": (8.85, 7.20, 9.28, 7.70),
    "port_harcourt": (4.70, 6.90, 4.98, 7.15),
    "benin_city": (6.28, 5.55, 6.45, 5.72),
    "kano": (11.88, 8.42, 12.12, 8.68),
    "ibadan": (7.30, 3.80, 7.52, 4.02),
    "enugu": (6.38, 7.42, 6.52, 7.58),
    "aba": (5.05, 7.28, 5.20, 7.45),
    "onitsha": (6.10, 6.75, 6.22, 6.87),
    "warri": (5.48, 5.70, 5.62, 5.85),
    "uyo": (4.98, 7.85, 5.06, 7.98),
    "calabar": (4.90, 8.28, 5.02, 8.42),
    "kaduna": (10.45, 7.35, 10.62, 7.52),
    "jos": (9.85, 8.85, 10.00, 8.98),
    # Additional state capitals (best-effort bboxes) to cover more of Nigeria.
    "owerri": (5.42, 7.00, 5.52, 7.08),
    "abeokuta": (7.10, 3.28, 7.20, 3.40),
    "ilorin": (8.45, 4.50, 8.55, 4.60),
    "akure": (7.22, 5.16, 7.32, 5.25),
    "asaba": (6.16, 6.72, 6.26, 6.80),
    "sokoto": (13.00, 5.18, 13.12, 5.28),
    "maiduguri": (11.78, 13.10, 11.90, 13.22),
    "katsina": (12.95, 7.55, 13.05, 7.65),
    "minna": (9.58, 6.52, 9.68, 6.62),
    "bauchi": (10.28, 9.80, 10.38, 9.92),
    "makurdi": (7.70, 8.50, 7.80, 8.62),
    "ado_ekiti": (7.58, 5.18, 7.68, 5.30),
    "osogbo": (7.75, 4.52, 7.85, 4.62),
    "gombe": (10.28, 11.15, 10.38, 11.28),
    "yola": (9.18, 12.42, 9.30, 12.52),
    "jalingo": (8.86, 11.32, 8.98, 11.45),
    "damaturu": (11.72, 11.92, 11.85, 12.02),
    "lokoja": (7.78, 6.72, 7.90, 6.85),
    "umuahia": (5.50, 7.45, 5.60, 7.55),
    "awka": (6.20, 7.02, 6.30, 7.12),
    "gusau": (12.15, 6.65, 12.25, 6.75),
    "dutse": (11.70, 9.28, 11.85, 9.42),
    "birnin_kebbi": (12.42, 4.15, 12.55, 4.25),
    "lafia": (8.45, 8.50, 8.55, 8.62),
}

CITY_NAMES = {
    "lagos": "Lagos", "abuja": "Abuja", "port_harcourt": "Port Harcourt",
    "benin_city": "Benin City", "kano": "Kano", "ibadan": "Ibadan",
    "enugu": "Enugu", "aba": "Aba", "onitsha": "Onitsha", "warri": "Warri",
    "uyo": "Uyo", "calabar": "Calabar", "kaduna": "Kaduna", "jos": "Jos",
    "owerri": "Owerri", "abeokuta": "Abeokuta", "ilorin": "Ilorin",
    "akure": "Akure", "asaba": "Asaba", "sokoto": "Sokoto",
    "maiduguri": "Maiduguri", "katsina": "Katsina", "minna": "Minna",
    "bauchi": "Bauchi", "makurdi": "Makurdi", "ado_ekiti": "Ado-Ekiti",
    "osogbo": "Osogbo", "gombe": "Gombe", "yola": "Yola", "jalingo": "Jalingo",
    "damaturu": "Damaturu", "lokoja": "Lokoja", "umuahia": "Umuahia",
    "awka": "Awka", "gusau": "Gusau", "dutse": "Dutse",
    "birnin_kebbi": "Birnin Kebbi", "lafia": "Lafia",
}

INDUSTRIES = {
    "construction": {"label": "Construction", "aliases": ["construction", "builder", "building", "contractor"],
                     "tags": [{"k": "office", "v": "construction_company"},
                              {"k": "craft", "v": "builder"},
                              {"k": "craft", "v": "plumber"},
                              {"k": "craft", "v": "electrician"},
                              {"k": "craft", "v": "carpenter"},
                              {"k": "office", "v": "architect"},
                              {"k": "shop", "v": "trade"},
                              {"k": "building", "v": "construction"}]},
    "real_estate": {"label": "Real Estate", "aliases": ["real estate", "realestate", "property", "realtor", "estate agent"],
                    "tags": [{"k": "office", "v": "estate_agent"},
                             {"k": "shop", "v": "estate_agent"},
                             {"k": "office", "v": "real_estate"}]},
    "accounting": {"label": "Accounting", "aliases": ["accounting", "accountant", "accountancy", "audit", "tax"],
                   "tags": [{"k": "office", "v": "accountant"},
                            {"k": "office", "v": "financial"}]},
    "law": {"label": "Law", "aliases": ["law", "lawyer", "lawyers", "legal", "solicitor", "attorney"],
            "tags": [{"k": "office", "v": "lawyer"},
                     {"k": "office", "v": "notary"}]},
    "schools": {"label": "Schools", "aliases": ["school", "schools", "primary school", "secondary school"],
                "tags": [{"k": "amenity", "v": "school"}]},
    "universities": {"label": "Universities", "aliases": ["university", "universities", "college", "polytechnic"],
                     "tags": [{"k": "amenity", "v": "university"},
                              {"k": "amenity", "v": "college"}]},
    "hospitals": {"label": "Hospitals", "aliases": ["hospital", "hospitals", "medical centre", "medical center"],
                  "tags": [{"k": "amenity", "v": "hospital"}]},
    "clinics": {"label": "Clinics", "aliases": ["clinic", "clinics", "pharmacy", "health centre", "health center"],
                "tags": [{"k": "amenity", "v": "clinic"},
                         {"k": "amenity", "v": "doctors"}]},
    "hotels": {"label": "Hotels", "aliases": ["hotel", "hotels", "guest house", "lodging"],
               "tags": [{"k": "tourism", "v": "hotel"},
                        {"k": "tourism", "v": "guest_house"}]},
    "restaurants": {"label": "Restaurants", "aliases": ["restaurant", "restaurants", "food", "eatery", "cafe", "café", "bar"],
                    "tags": [{"k": "amenity", "v": "restaurant"},
                             {"k": "amenity", "v": "cafe"},
                             {"k": "amenity", "v": "bar"}]},
    "logistics": {"label": "Logistics", "aliases": ["logistics", "transport", "haulage", "courier", "shipping", "freight"],
                  "tags": [{"k": "office", "v": "logistics"},
                           {"k": "office", "v": "courier"},
                           {"k": "amenity", "v": "post_office"}]},
    "manufacturing": {"label": "Manufacturing", "aliases": ["manufacturing", "manufacturer", "factory", "production", "industrial"],
                      "tags": [{"k": "man_made", "v": "works"},
                               {"k": "industrial", "v": "factory"}]},
    "retail": {"label": "Retail", "aliases": ["retail", "shop", "shops", "store", "supermarket", "mall"],
               "tags": [{"k": "shop", "v": "supermarket"},
                        {"k": "shop", "v": "department_store"},
                        {"k": "shop", "v": "mall"}]},
    "churches": {"label": "Churches", "aliases": ["church", "churches", "ministry", "worship", "mosque"],
                 "tags": [{"k": "amenity", "v": "place_of_worship"},
                          {"k": "religion", "v": "christian"},
                          {"k": "religion", "v": "muslim"}]},
    "ngos": {"label": "NGOs", "aliases": ["ngo", "ngos", "nonprofit", "non profit", "non-profit", "charity", "foundation"],
             "tags": [{"k": "office", "v": "ngo"},
                      {"k": "office", "v": "foundation"},
                      {"k": "office", "v": "charity"}]},
    "tech": {"label": "Tech", "aliases": ["tech", "technology", "software", "it", "information technology", "startup"],
             "tags": [{"k": "office", "v": "it"},
                      {"k": "office", "v": "software"}]},
    "smes": {"label": "SMEs", "aliases": ["sme", "smes", "small business", "small businesses", "business"],
             "tags": [{"k": "office", "v": "company"},
                      {"k": "shop", "v": "yes"}]},
    "cleaning": {"label": "Commercial Cleaning", "aliases": ["cleaning", "commercial cleaning", "janitorial", "cleaners"],
                 "tags": [{"k": "office", "v": "cleaning"},
                          {"k": "craft", "v": "cleaner"}]},
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def resolve_city(text: str):
    """Return (display_name, bbox) for a city phrase, or (None, None)."""
    phrase = _norm(text)
    if not phrase:
        return None, None
    key = phrase.replace(" ", "_")
    if key in CITIES:
        return CITY_NAMES.get(key, key), CITIES[key]
    for k, bbox in CITIES.items():
        name = CITY_NAMES.get(k, k)
        if _norm(name) == phrase or phrase in _norm(name) or _norm(name) in phrase:
            return name, bbox
    for k, bbox in CITIES.items():
        if key in k or k in key:
            return CITY_NAMES.get(k, k), bbox
    return None, None


def resolve_industry(text: str):
    """Return an industry key for a phrase, or None."""
    phrase = _norm(text)
    if not phrase:
        return None
    if phrase.replace(" ", "_") in INDUSTRIES:
        return phrase.replace(" ", "_")
    for key, spec in INDUSTRIES.items():
        if phrase in _norm(key):
            return key
        for alias in spec.get("aliases", []):
            if phrase == _norm(alias) or phrase in _norm(alias) or _norm(alias) in phrase:
                return key
    return None


def city_name_for_bbox(bbox) -> str:
    for k, b in CITIES.items():
        if tuple(b) == tuple(bbox):
            return CITY_NAMES.get(k, k)
    return ""
