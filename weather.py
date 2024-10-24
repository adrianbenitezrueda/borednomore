import streamlit as st
import requests
from datetime import datetime
from collections import Counter

# Cargar la API Key desde Streamlit Secrets
AEMET_API_KEY = st.secrets["aemet_api_key"]

# Función para obtener la predicción climática (general) de AEMET
def obtener_prediccion(codigo_municipio, tipo_prediccion):
    if tipo_prediccion == 'diaria':
        url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{codigo_municipio}"
    elif tipo_prediccion == 'horaria':
        url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/horaria/{codigo_municipio}"
    
    headers = {'api_key': AEMET_API_KEY}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if 'datos' in data:
            datos_url = data['datos']
            datos_response = requests.get(datos_url)
            if datos_response.status_code == 200:
                return datos_response.json()
            else:
                st.error(f"Error al obtener los datos del clima: {datos_response.status_code}")
        else:
            st.error(f"Error: no se encontró la clave 'datos' en la respuesta.")
    else:
        st.error(f"Error en la solicitud a AEMET: {response.status_code}")
        
    return None

 # Función para obtener el bloque de tiempo actual
def obtener_bloque_tiempo(hora_actual):
    bloques = [(0, 6), (6, 12), (12, 18), (18, 24)]
    for inicio, fin in bloques:
        if inicio <= hora_actual < fin:
            return f"{inicio:02d}-{fin:02d}"
    return None

# Función para extraer las temperaturas máximas y mínimas
def obtener_temperaturas(prediccion_hoy):
    temp_max = prediccion_hoy['temperatura']['maxima']
    temp_min = prediccion_hoy['temperatura']['minima']
    return temp_max, temp_min

# Función para obtener la temperatura actual basada en la hora
def obtener_temperatura_actual(prediccion_hoy):
    hora_actual = datetime.now().hour
    for temp_dato in prediccion_hoy['temperatura']:
        if int(temp_dato['periodo']) == hora_actual:
            return temp_dato['value']
    return 'Información no disponible'

# Función para obtener el estado del cielo más frecuente
def obtener_estado_cielo_mas_frecuente(prediccion_hoy):
    estados_cielo = [periodo.get('descripcion', '') for periodo in prediccion_hoy['estadoCielo'] if periodo.get('descripcion', '')]
    if estados_cielo:
        contador_estados = Counter(estados_cielo)
        return contador_estados.most_common(1)[0][0]
    return 'Información no disponible'

# Función para obtener el estado del cielo, viento y lluvia por bloque
def obtener_estado_cielo_por_bloque(prediccion_hoy, bloque):
    for periodo in prediccion_hoy['estadoCielo']:
        if periodo['periodo'] == bloque:
            return periodo.get('descripcion', 'Información no disponible')
    return 'Información no disponible'

def obtener_viento_por_bloque(prediccion_hoy, bloque):
    if 'viento' in prediccion_hoy:
        for viento in prediccion_hoy['viento']:
            if viento['periodo'] == bloque:
                return viento.get('velocidad', 'Información no disponible')
    return 'Información no disponible'

def obtener_lluvia_por_bloque(prediccion_hoy, bloque):
    for precipitacion in prediccion_hoy['probPrecipitacion']:
        if precipitacion['periodo'] == bloque:
            return precipitacion.get('value', 'Información no disponible')
    return 'Información no disponible'

# Función principal para procesar y devolver los datos del clima
def procesar_datos_clima(codigo_municipio):
    clima_diario = obtener_prediccion(codigo_municipio, 'diaria')
    clima_horario = obtener_prediccion(codigo_municipio, 'horaria')

    # Variables a extraer
    max_temp = min_temp = estado_cielo = temp_actual = viento_actual = lluvia_actual = estado_cielo_actual = None

    # Procesar datos diarios
    if clima_diario:
        prediccion_diaria = clima_diario[0]['prediccion']['dia'][0]
        max_temp, min_temp = obtener_temperaturas(prediccion_diaria)
        estado_cielo = obtener_estado_cielo_mas_frecuente(prediccion_diaria)

    # Procesar datos horarios
    if clima_horario:
        prediccion_horaria = clima_horario[0]['prediccion']['dia'][0]
        hora_actual = datetime.now().hour
        bloque = obtener_bloque_tiempo(hora_actual)
            
        temp_actual = obtener_temperatura_actual(prediccion_horaria)
        viento_actual = obtener_viento_por_bloque(prediccion_diaria, bloque)
        lluvia_actual = obtener_lluvia_por_bloque(prediccion_diaria, bloque)

    # Retornar los resultados como un diccionario
    return {
        "max_temp": max_temp,
        "min_temp": min_temp,
        "estado_cielo": estado_cielo,
        "temp_actual": temp_actual,
        "viento_actual": viento_actual,
        "lluvia_actual": lluvia_actual
    }


# Obtener los datos del clima
datos_clima = procesar_datos_clima(codigo_municipio)

# Usar los datos en la app principal
st.write(f"Temperatura máxima: {datos_clima['max_temp']}°C")
st.write(f"Temperatura mínima: {datos_clima['min_temp']}°C")
st.write(f"Estado del cielo más frecuente: {datos_clima['estado_cielo']}")
st.write(f"Temperatura actual: {datos_clima['temp_actual']}°C")
st.write(f"Velocidad del viento actual: {datos_clima['viento_actual']} km/h")
st.write(f"Probabilidad de lluvia actual: {datos_clima['lluvia_actual']}%")
