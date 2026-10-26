from .conftest import register


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["ok"] is True


def test_languages(client):
    body = client.get("/api/languages").json()
    langs = body["languages"]
    assert len(langs) == 19                                   # Marathi joined in 0030, Kannada in 0036, Tamil in 0039, Bengali in 0047, Telugu and Urdu in 0050, Kashmiri and Dogri in 0054
    assert langs[0] == {"code": "en", "name": "English", "native_name": "English", "tts_locale": "en-IN"}
    assert {"hi", "hinglish"} <= {l["code"] for l in langs}
    assert langs[-8] == {"code": "mr", "name": "Marathi", "native_name": "मराठी", "tts_locale": "mr-IN"}   # migration 0030
    assert langs[-7] == {"code": "kn", "name": "Kannada", "native_name": "ಕನ್ನಡ", "tts_locale": "kn-IN"}   # migration 0036
    assert langs[-6] == {"code": "ta", "name": "Tamil", "native_name": "தமிழ்", "tts_locale": "ta-IN"}   # migration 0039
    assert langs[-5] == {"code": "bn", "name": "Bengali", "native_name": "বাংলা", "tts_locale": "bn-IN"}   # migration 0047
    assert langs[-4] == {"code": "te", "name": "Telugu", "native_name": "తెలుగు", "tts_locale": "te-IN"}   # migration 0050
    assert langs[-3] == {"code": "ur", "name": "Urdu", "native_name": "اردو", "tts_locale": "ur-IN"}   # migration 0050
    assert langs[-2] == {"code": "ks", "name": "Kashmiri", "native_name": "کٲشُر", "tts_locale": "ks-IN"}   # migration 0054
    assert langs[-1] == {"code": "doi", "name": "Dogri", "native_name": "डोगरी", "tts_locale": "doi-IN"}   # migration 0054


def test_cities(client):
    cities = client.get("/api/cities").json()["cities"]
    assert [c["slug"] for c in cities] == ["delhi", "mumbai", "bengaluru", "hyderabad", "chennai", "puducherry", "jaipur", "lucknow", "kolkata", "bhopal", "jk", "shimla"]
    delhi = cities[0]
    assert delhi["ready"] is True and delhi["languages"] == ["hi", "hinglish", "en"]
    assert cities[1]["ready"] is True and cities[1]["languages"] == ["hi", "mr", "en"]    # Mumbai's pack (0029), in Marathi too (0030)
    assert cities[2]["ready"] is True and cities[2]["languages"] == ["kn", "en"]          # Bengaluru's Kannada pack (0036)
    assert cities[3]["ready"] is True and cities[3]["languages"] == ["te", "ur", "en"]    # Hyderabad, in Telugu and Urdu (0050)
    assert cities[4]["ready"] is True and cities[4]["languages"] == ["ta", "en"]          # Chennai's Tamil pack (0039)
    assert cities[5]["ready"] is True and cities[5]["languages"] == ["ta", "fr", "en"]    # Puducherry (0043)
    assert set(delhi) == {"slug", "name", "flag", "emoji", "tagline", "blurb", "ready", "languages"}


def test_legacy_state_contract_unchanged_for_a_signed_in_user(client):
    """The state contract itself is unchanged; since Phase 14A it is only ever a signed-in user's own (see test_legacy_hardening.py)."""
    me = register(client, "state@example.com")
    url = f"/api/state/{me['handle']}"
    assert client.get(url).json() == {"state": None}
    assert client.put(url, json={"v": 1, "xp": 5}).json() == {"ok": True}
    assert client.get(url).json() == {"state": {"v": 1, "xp": 5}}
    client.put(url, json={"v": 1, "xp": 6})
    assert client.get(url).json()["state"]["xp"] == 6


def test_ai_endpoint_falls_back_without_provider(client, monkeypatch):
    from backend import main
    monkeypatch.setattr(main, "provider", lambda: None)
    assert client.post("/api/ai", json={"mode": "tutor", "history": [{"role": "me", "text": "hi"}]}).json() == {"ok": False, "reason": "offline"}


def test_static_routes(client):
    assert client.get("/").status_code == 200
    for f in ("app.js", "engine.js", "content.js", "bits.js", "styles.css"):
        assert client.get(f"/static/{f}").status_code == 200
