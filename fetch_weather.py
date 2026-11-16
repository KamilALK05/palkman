"""
=============================================================================
Skrypt Dynamicznej Aktualizacji Pogody dla Gry "Kozminski Escape"
Projekt: Laboratorium GitHub Actions & CI/CD - Akademia Leona Koźmińskiego
Integracja: AccuWeather API z automatycznym fallbackiem do Open-Meteo API
=============================================================================
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Zapewnienie kodowania UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Współrzędne Kampusu Akademii Leona Koźmińskiego (Warszawa, ul. Jagiellońska 57/59)
KOZMINSKI_LAT = 52.2618
KOZMINSKI_LON = 21.0189
ACCUWEATHER_WARSAW_KEY = "274663"  # Oficjalny LocationKey Warszawy w AccuWeather

def fetch_accuweather(api_key: str) -> dict:
    """Pobiera aktualną pogodę dla Warszawy z oficjalnego AccuWeather Current Conditions API."""
    url = f"http://dataservice.accuweather.com/currentconditions/v1/{ACCUWEATHER_WARSAW_KEY}?apikey={api_key}&language=pl-pl&details=true"
    print(f"--> [AccuWeather] Odpytywanie endpointu dla Warszawy (Key: {ACCUWEATHER_WARSAW_KEY})...")
    
    req = urllib.request.Request(url, headers={"User-Agent": "Kozminski-Weather-Pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        if response.status != 200:
            raise RuntimeError(f"AccuWeather zwrocił kod HTTP {response.status}")
        data = json.loads(response.read().decode('utf-8'))
    
    if not data or not isinstance(data, list):
        raise ValueError("Nieoczekiwana struktura odpowiedzi AccuWeather")
    
    current = data[0]
    weather_text = current.get("WeatherText", "Brak danych")
    has_precip = current.get("HasPrecipitation", False)
    precip_type = current.get("PrecipitationType")  # 'Rain', 'Snow', etc.
    temp_c = current.get("Temperature", {}).get("Metric", {}).get("Value", 15.0)
    is_day = current.get("IsDayTime", True)
    humidity = current.get("RelativeHumidity", 60)
    
    # Klasyfikacja aury
    if has_precip:
        if precip_type == "Snow":
            condition = "snow"
        else:
            condition = "rain"
    elif not is_day:
        condition = "night"
    elif "słoneczn" in weather_text.lower() or "pogodn" in weather_text.lower() or "jasn" in weather_text.lower():
        condition = "sunny"
    elif "deszcz" in weather_text.lower() or "mżawk" in weather_text.lower():
        condition = "rain"
    elif "śnieg" in weather_text.lower():
        condition = "snow"
    else:
        condition = "cloudy"
        
    return {
        "source": "AccuWeather API",
        "condition": condition,
        "description": weather_text,
        "temp_c": round(float(temp_c), 1),
        "humidity": humidity,
        "precipitation_mm": 1.5 if has_precip else 0.0,
        "is_day": is_day
    }

def fetch_open_meteo() -> dict:
    """Fallback: Pobiera aktualne dane pogodowe z darmowego i stabilnego Open-Meteo API dla Kampusu ALK."""
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={KOZMINSKI_LAT}&longitude={KOZMINSKI_LON}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,is_day"
    )
    print(f"--> [Open-Meteo Fallback] Pobieranie współrzędnych ALK ({KOZMINSKI_LAT}, {KOZMINSKI_LON})...")
    
    req = urllib.request.Request(url, headers={"User-Agent": "Kozminski-Weather-Pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=12) as response:
        data = json.loads(response.read().decode('utf-8'))
        
    curr = data.get("current", {})
    temp = curr.get("temperature_2m", 15.0)
    humidity = curr.get("relative_humidity_2m", 70)
    precip = curr.get("precipitation", 0.0)
    w_code = curr.get("weather_code", 0)
    is_day = bool(curr.get("is_day", 1))
    
    # Mapowanie kodów WMO
    # 0 = Bezchmurnie, 1-3 = Częściowo pochmurno
    # 51-67 = Mżawka / Deszcz, 71-77 = Śnieg, 80-82 = Ulewa, 95-99 = Burza
    if precip > 0.1 or (51 <= w_code <= 67) or (80 <= w_code <= 82) or (95 <= w_code <= 99):
        condition = "rain"
        desc = "Opady deszczu na Jagiellońskiej"
    elif (71 <= w_code <= 77) or (85 <= w_code <= 86):
        condition = "snow"
        desc = "Opady śniegu nad Pragą-Północ"
    elif not is_day:
        condition = "night"
        desc = "Nocna sesja na ALK"
    elif w_code in [0, 1]:
        condition = "sunny"
        desc = "Słonecznie nad Kampusem ALK"
    else:
        condition = "cloudy"
        desc = "Umiarkowane zachmurzenie"
        
    return {
        "source": "Open-Meteo API (Fallback)",
        "condition": condition,
        "description": desc,
        "temp_c": round(float(temp), 1),
        "humidity": humidity,
        "precipitation_mm": round(float(precip), 1),
        "is_day": is_day
    }

def get_simulated_weather(override: str) -> dict:
    """Zwraca zdefiniowane parametry pogody dla celów testowych/manualnych (override)."""
    presets = {
        "rain": {
            "source": "Symulacja manualna (Workflow Dispatch)",
            "condition": "rain",
            "description": "Ulewny deszcz nad Kampusem ALK (Test CI/CD)",
            "temp_c": 9.5,
            "humidity": 95,
            "precipitation_mm": 5.8,
            "is_day": True
        },
        "sunny": {
            "source": "Symulacja manualna (Workflow Dispatch)",
            "condition": "sunny",
            "description": "Pełne słońce nad Patio ALK (Test CI/CD)",
            "temp_c": 24.0,
            "humidity": 45,
            "precipitation_mm": 0.0,
            "is_day": True
        },
        "snow": {
            "source": "Symulacja manualna (Workflow Dispatch)",
            "condition": "snow",
            "description": "Zimowa śnieżyca na Jagiellońskiej (Test CI/CD)",
            "temp_c": -2.0,
            "humidity": 88,
            "precipitation_mm": 2.2,
            "is_day": True
        },
        "night": {
            "source": "Symulacja manualna (Workflow Dispatch)",
            "condition": "night",
            "description": "Nocne zakuwanie przed egzaminem (Test CI/CD)",
            "temp_c": 12.0,
            "humidity": 70,
            "precipitation_mm": 0.0,
            "is_day": False
        }
    }
    return presets.get(override.lower(), presets["sunny"])

def assemble_game_weather(weather_info: dict) -> dict:
    """Wzbogaca dane pogodowe o parametry mechaniki i wizualne dla gry Kozminski Escape."""
    cond = weather_info["condition"]
    
    if cond == "rain":
        icon = "🌧️"
        alert = "Uwaga: Posadzka na Patio jest śliska! Profesor narzeka na zmoknięte arkusze ocen."
        professor_quote = "Brrr, w taki deszcz moje arkusze ocen zamokną! Panie Kolego, zmykajmy do auli!"
        theme_class = "weather-rain"
        particles = "rain"
        friction = 0.90  # Poślizg studenta
    elif cond == "sunny":
        icon = "☀️"
        alert = "Słoneczna pogoda! ECTS lśnią na Patio, a profesor w dobrym humorze chętnie stawia 5.0!"
        professor_quote = "Piękna pogoda na zaliczenie w pierwszym terminie! Złapmy trochę słońca!"
        theme_class = "weather-sunny"
        particles = "sunbeams"
        friction = 0.98
    elif cond == "snow":
        icon = "❄️"
        alert = "Zimowa aura na ALK! Prószy śnieg, uważaj na zaspy przy wejściu do Budynku D."
        professor_quote = "Zaspy śnieżne na Jagiellońskiej, a ja muszę sprawdzić 150 egzaminów!"
        theme_class = "weather-snow"
        particles = "snow"
        friction = 0.85
    else:  # cloudy / night
        icon = "🌙" if not weather_info.get("is_day", True) else "☁️"
        alert = "Umiarkowane zachmurzenie nad kampusem. Idealne warunki do nauki i ucieczki przed sesją."
        professor_quote = "Gdzie podziały się arkusze z egzaminu z mikroekonomii?!"
        theme_class = "weather-cloudy"
        particles = "none"
        friction = 0.98

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return {
        "city": "Warszawa (Kampus ALK, ul. Jagiellońska)",
        "source": weather_info["source"],
        "condition": cond,
        "condition_label": weather_info["description"],
        "icon": icon,
        "temp_c": weather_info["temp_c"],
        "humidity": weather_info["humidity"],
        "precipitation_mm": weather_info["precipitation_mm"],
        "is_day": weather_info["is_day"],
        "campus_alert": alert,
        "game_effects": {
            "theme_class": theme_class,
            "particles": particles,
            "player_friction": friction,
            "professor_quote": professor_quote,
            "hud_badge": f"{icon} {weather_info['temp_c']}°C | {weather_info['description']}"
        },
        "last_updated": now_str
    }

def update_game_files(weather_data: dict, base_dir: str):
    """Zapisuje dane pogodowe do data/weather.json, js/weather.js oraz aktualizuje index.html."""
    data_dir = os.path.join(base_dir, "data")
    js_dir = os.path.join(base_dir, "js")
    reports_dir = os.path.join(base_dir, "reports")
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(js_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)
    
    # 1. Zapis do data/weather.json
    json_path = os.path.join(data_dir, "weather.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(weather_data, f, ensure_ascii=False, indent=2)
    print(f"--> [Zapisano] {json_path}")
    
    # 2. Zapis do js/weather.js (pozwala na odczyt w przeglądarce bez restrykcji CORS na file://)
    js_path = os.path.join(js_dir, "weather.js")
    js_content = f"""// Automatycznie wygenerowane przez potok GitHub Actions ({weather_data['last_updated']})
window.CAMPUS_WEATHER = {json.dumps(weather_data, ensure_ascii=False, indent=2)};
"""
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"--> [Zapisano] {js_path}")
    
    # 3. Aktualizacja index.html - statyczne wstrzyknięcie etykiety i klasy motywu
    html_path = os.path.join(base_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
            
        badge_text = weather_data["game_effects"]["hud_badge"]
        theme_class = weather_data["game_effects"]["theme_class"]
        
        # Aktualizacja lub wstrzyknięcie widżetu pogody
        if 'id="hud-weather-text"' in html:
            import re
            html = re.sub(
                r'<div class="hud-value" id="hud-weather-text">.*?</div>',
                f'<div class="hud-value" id="hud-weather-text">{badge_text}</div>',
                html
            )
            # Aktualizacja klasy motywu na body
            def _replace_body_class(m):
                clean_cls = re.sub(r'weather-\w+', '', m.group(2)).strip()
                new_cls = f"{clean_cls} {theme_class}".strip()
                return f'<body{m.group(1)}class="{new_cls}"'

            html = re.sub(r'<body([^>]*)class="([^"]*)"', _replace_body_class, html)
            if 'class="' not in html.split('<body')[1].split('>')[0]:
                html = html.replace('<body', f'<body class="{theme_class}"', 1)
                
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"--> [Zaktualizowano] {html_path} z motywem: {theme_class}")
            
    # 4. Wygenerowanie raportu wykonawczego w reports/latest_weather_report.md
    report_path = os.path.join(reports_dir, "latest_weather_report.md")
    report_md = f"""# 🌦️ Raport Aury na Kampusie ALK – Potok GitHub Actions

* **Data aktualizacji:** `{weather_data['last_updated']}`
* **Źródło danych:** `{weather_data['source']}`
* **Lokalizacja:** Warszawa, ul. Jagiellońska 57/59 (Kampus ALK)

## Parametry Aury:
| Parametr | Wartość |
| :--- | :--- |
| **Stan ogólny** | {weather_data['icon']} {weather_data['condition_label']} (`{weather_data['condition']}`) |
| **Temperatura** | **{weather_data['temp_c']} °C** |
| **Wilgotność względna** | {weather_data['humidity']} % |
| **Opady** | {weather_data['precipitation_mm']} mm |
| **Pora doby** | {'Dzień ☀️' if weather_data['is_day'] else 'Noc 🌙'} |

## Wpływ na Rozgrywkę „Kozminski Escape”:
* **Komunikat Dziekanatu:** *„{weather_data['campus_alert']}”*
* **Kwestia Profesora:** *„{weather_data['game_effects']['professor_quote']}”*
* **Efekt graficzny:** `{weather_data['game_effects']['particles']}`
* **Współczynnik tarcia (poślizg gracza):** `{weather_data['game_effects']['player_friction']}`

---
*Wygenerowano autonomicznie przez maszynę wykonawczą GitHub Actions Runner.*
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"--> [Wygenerowano] {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Pobiera pogodę z AccuWeather/Open-Meteo i modyfikuje interfejs Kozminski Escape")
    parser.add_argument("--override", choices=["auto", "rain", "sunny", "snow", "night"], default="auto",
                        help="Wymuszenie aury (do testów manualnych workflow_dispatch)")
    parser.add_argument("--api-key", default=os.getenv("ACCUWEATHER_API_KEY", ""),
                        help="Klucz API AccuWeather (opcjonalny, domyślnie z env ACCUWEATHER_API_KEY)")
    parser.add_argument("--project-dir", default=os.path.dirname(os.path.abspath(__file__)),
                        help="Katalog projektu zawierający index.html")
    args = parser.parse_args()

    print("=" * 65)
    print("  ALK CI/CD WEATHER ENGINE: KOZMINSKI ESCAPE DYNAMIC WEATHER   ")
    print("=" * 65)
    
    weather_info = None
    
    # 1. Sprawdzenie wymuszenia (override)
    if args.override != "auto":
        print(f"--> [TRYB MANUALNY] Wymuszono aurę: '{args.override}'")
        weather_info = get_simulated_weather(args.override)
    else:
        # 2. Próba pobrania z AccuWeather
        if args.api_key and args.api_key.strip():
            try:
                weather_info = fetch_accuweather(args.api_key.strip())
            except Exception as e:
                print(f"    [OSTRZEŻENIE] Błąd AccuWeather ({e}). Przełączanie na fallback...")
        else:
            print("--> [INFO] Brak klucza ACCUWEATHER_API_KEY. Użycie bezpiecznego źródła Open-Meteo...")
            
        # 3. Fallback do Open-Meteo
        if not weather_info:
            try:
                weather_info = fetch_open_meteo()
            except Exception as e:
                print(f"    [BŁĄD KRYTYCZNY] Błąd pobierania pogody: {e}")
                print("    Użycie domyślnej aury słonecznej...")
                weather_info = get_simulated_weather("sunny")

    # Przetworzenie danych dla gry
    game_weather = assemble_game_weather(weather_info)
    print(f"\n[AURA]: {game_weather['icon']} {game_weather['condition_label']} ({game_weather['temp_c']}°C)")
    print(f"[ALERT]: {game_weather['campus_alert']}")
    
    # Zapis do plików projektu
    update_game_files(game_weather, args.project_dir)
    print("\n[SUKCES] Potok pogody zakończył działanie pomyślnie!")

if __name__ == "__main__":
    main()
