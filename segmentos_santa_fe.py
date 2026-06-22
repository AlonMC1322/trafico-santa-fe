# Segmentos inmediatos alrededor de la Universidad Iberoamericana CDMX.
# Cada segmento define origen y destino (lat/lng); el colector calcula
# el trafico de manejar de un punto al otro. Los tres tramos forman un
# anillo alrededor del campus (sus extremos se conectan entre si).
SEGMENTOS = [
    {
        "nombre": "Prol_Paseo_Reforma",
        "origen":  {"lat": 19.36564100720713, "lng": -99.26631701603404},  # sur, antes del campus
        "destino": {"lat": 19.37291918199356, "lng": -99.26312945716585},  # norte, hacia Joaquin Gallo
    },
    {
        "nombre": "Joaquin_Gallo",
        "origen":  {"lat": 19.372863118421773, "lng": -99.26306024937871},  # norte, saliendo de la autopista
        "destino": {"lat": 19.371032074894455, "lng": -99.26111155601929},  # Puertas 6 y 7
    },
    {
        "nombre": "Vasco_de_Quiroga",
        "origen":  {"lat": 19.371097818974295, "lng": -99.26088961117327},  # nororiente
        "destino": {"lat": 19.365829988869006, "lng": -99.26703600766014},  # sur, de regreso a Reforma
    },
]
