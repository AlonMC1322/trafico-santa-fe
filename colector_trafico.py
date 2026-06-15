# colector_trafico.py  — versión GitHub Actions
import os, time, requests, json
from datetime import datetime, timezone
import gspread
from google.oauth2.service_account import Credentials
from segmentos_santa_fe import SEGMENTOS

API_KEY      = os.environ["GOOGLE_MAPS_KEY"]
SHEET_ID     = os.environ["SHEET_ID"]           # ID de tu Google Sheet
ROUTES_URL   = "https://routes.googleapis.com/directions/v2:computeRoutes"

def get_sheet():
    # Las credenciales vienen de variable de entorno en GitHub Actions
    creds_json = json.loads(os.environ["GSHEET_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).sheet1

def consultar_segmento(seg):
    payload = {
        "origin":      {"location": {"latLng": seg["origen"]}},
        "destination": {"location": {"latLng": seg["destino"]}},
        "travelMode":  "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        "departureTime": datetime.now(timezone.utc).isoformat(),
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "routes.duration,routes.staticDuration",
    }
    r = requests.post(ROUTES_URL, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    ruta = r.json()["routes"][0]
    dur_t = int(ruta["duration"].replace("s",""))
    dur_n = int(ruta["staticDuration"].replace("s",""))
    return dur_n, dur_t

def muestrear():
    sheet = get_sheet()
    now   = datetime.now(timezone.utc)
    filas = []
    for seg in SEGMENTOS:
        try:
            dur_n, dur_t = consultar_segmento(seg)
            ratio = round(dur_t / dur_n, 4) if dur_n > 0 else None
            filas.append([
                now.isoformat(),
                now.weekday(),
                now.hour,
                seg["nombre"],
                dur_n,
                dur_t,
                ratio
            ])
            print(f"✓ {seg['nombre']:25s} ratio={ratio}")
        except Exception as e:
            print(f"✗ {seg['nombre']}: {e}")
        time.sleep(0.5)

    # Un solo append por ejecución — eficiente y dentro del rate limit
    if filas:
        sheet.append_rows(filas, value_input_option="USER_ENTERED")
        print(f"  → {len(filas)} filas guardadas en Sheets")

if __name__ == "__main__":
    muestrear()
