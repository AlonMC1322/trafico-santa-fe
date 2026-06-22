# colector_trafico.py  — versión mejorada con velocidades e índices de congestión
import os, time, requests, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
from segmentos_santa_fe import SEGMENTOS

API_KEY    = os.environ["GOOGLE_MAPS_KEY"]
SHEET_ID   = os.environ["SHEET_ID"]
ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
TZ_CDMX    = ZoneInfo("America/Mexico_City")

# Columnas del Sheet — el orden importa
ENCABEZADOS = [
    "timestamp_cdmx", "timestamp_utc", "dia_semana", "hora", "minuto",
    "segmento",
    "dur_normal_s", "dur_trafico_s", "distance_m",
    "ratio", "delay_s", "congestion_index",
    "vel_normal_ms", "vel_trafico_ms",
    "vel_normal_kmh", "vel_trafico_kmh",
    "polyline", "speed_intervals_json",
]


def get_sheet():
    creds_json = json.loads(os.environ["GSHEET_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_json,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(SHEET_ID).sheet1

    # Inicializar encabezados si la hoja está vacía o no los tiene
    primera_celda = sheet.cell(1, 1).value
    if not primera_celda or primera_celda != ENCABEZADOS[0]:
        sheet.insert_row(ENCABEZADOS, 1)
        print("  → Encabezados inicializados en la hoja")

    return sheet


def consultar_segmento(seg):
    origen  = {"latitude": seg["origen"]["lat"],  "longitude": seg["origen"]["lng"]}
    destino = {"latitude": seg["destino"]["lat"], "longitude": seg["destino"]["lng"]}

    payload = {
        "origin":      {"location": {"latLng": origen}},
        "destination": {"location": {"latLng": destino}},
        "travelMode":  "DRIVE",
        "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
        # Necesario para obtener speedReadingIntervals
        "extraComputations": ["TRAFFIC_ON_POLYLINE"],
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": (
            "routes.duration,"
            "routes.staticDuration,"
            "routes.distanceMeters,"
            "routes.polyline.encodedPolyline,"
            "routes.travelAdvisory.speedReadingIntervals"
        ),
    }

    r = requests.post(ROUTES_URL, json=payload, headers=headers, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} → {r.text}")

    ruta     = r.json()["routes"][0]
    dur_t    = int(ruta["duration"].replace("s", ""))
    dur_n    = int(ruta["staticDuration"].replace("s", ""))
    dist_m   = ruta.get("distanceMeters")
    polyline = ruta.get("polyline", {}).get("encodedPolyline")
    speed_iv = ruta.get("travelAdvisory", {}).get("speedReadingIntervals")

    return dur_n, dur_t, dist_m, polyline, speed_iv


def calcular_variables(dur_n, dur_t, dist_m):
    """Calcula velocidades e índices derivados de los tiempos y la distancia."""
    ratio            = round(dur_t / dur_n, 4) if dur_n > 0 else None
    delay_s          = dur_t - dur_n
    congestion_index = round(ratio - 1, 4)     if ratio is not None else None

    if dist_m and dur_t > 0:
        vel_t_ms  = round(dist_m / dur_t, 4)
        vel_t_kmh = round(vel_t_ms * 3.6, 2)
    else:
        vel_t_ms = vel_t_kmh = None

    if dist_m and dur_n > 0:
        vel_n_ms  = round(dist_m / dur_n, 4)
        vel_n_kmh = round(vel_n_ms * 3.6, 2)
    else:
        vel_n_ms = vel_n_kmh = None

    return ratio, delay_s, congestion_index, vel_n_ms, vel_t_ms, vel_n_kmh, vel_t_kmh


def muestrear():
    sheet    = get_sheet()
    now_utc  = datetime.now(timezone.utc)
    now_cdmx = now_utc.astimezone(TZ_CDMX)
    filas    = []

    for seg in SEGMENTOS:
        try:
            dur_n, dur_t, dist_m, polyline, speed_iv = consultar_segmento(seg)
            ratio, delay_s, ci, vel_n_ms, vel_t_ms, vel_n_kmh, vel_t_kmh = \
                calcular_variables(dur_n, dur_t, dist_m)

            fila = [
                now_cdmx.isoformat(),           # timestamp_cdmx
                now_utc.isoformat(),             # timestamp_utc
                now_cdmx.weekday(),              # dia_semana (0=lun, 6=dom)
                now_cdmx.hour,                   # hora (CDMX)
                now_cdmx.minute,                 # minuto
                seg["nombre"],                   # segmento
                dur_n,                           # dur_normal_s
                dur_t,                           # dur_trafico_s
                dist_m,                          # distance_m
                ratio,                           # ratio = dur_t / dur_n
                delay_s,                         # delay_s = dur_t - dur_n
                ci,                              # congestion_index = ratio - 1
                vel_n_ms,                        # vel_normal_ms
                vel_t_ms,                        # vel_trafico_ms
                vel_n_kmh,                       # vel_normal_kmh
                vel_t_kmh,                       # vel_trafico_kmh
                polyline,                        # polyline encodedPolyline
                json.dumps(speed_iv) if speed_iv else None,  # speed_intervals_json
            ]
            filas.append(fila)
            print(f"✓ {seg['nombre']:25s}  ratio={ratio}  V={vel_t_kmh} km/h  delay={delay_s}s")

        except Exception as e:
            print(f"✗ {seg['nombre']}: {e}")

        time.sleep(0.5)

    if filas:
        sheet.append_rows(filas, value_input_option="USER_ENTERED")
        print(f"  → {len(filas)} filas guardadas en Sheets")


if __name__ == "__main__":
    muestrear()
