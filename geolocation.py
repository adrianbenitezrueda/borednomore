import streamlit as st
import requests
import pandas as pd

# Cargar la API Key de Google desde Streamlit Secrets
GOOGLE_API_KEY = st.secrets["google_api_key"]

# Ruta del archivo CSV con los municipios
CSV_PATH = "data/raw/municipios_aemet.csv"

# Cargar los municipios desde el CSV
municipios_df = pd.read_csv(CSV_PATH)

# Definir la función para obtener la geolocalización (latitud y longitud)
def obtener_geolocalizacion():
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
    data = {"considerIp": True}
    
    response = requests.post(url, json=data)
    if response.status_code == 200:
        data = response.json()
        latitud = data['location']['lat']
        longitud = data['location']['lng']
        return latitud, longitud
    else:
        return None, None

# Función para convertir latitud y longitud a municipio usando Google Geocoding API
def obtener_municipio(latitud, longitud):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitud},{longitud}&key={GOOGLE_API_KEY}"
    
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if len(data['results']) > 0:
            address_components = data['results'][0]['address_components']
            for component in address_components:
                if 'locality' in component['types']:
                    return component['long_name']
            for component in address_components:
                if 'administrative_area_level_4' in component['types']:
                    return component['long_name']
            for component in address_components:
                if 'administrative_area_level_3' in component['types']:
                    return component['long_name']
        return None
    else:
        return None

# Función para verificar si el municipio está en el CSV y obtener el código sin las dos primeras letras
def obtener_codigo_municipio(nombre_municipio):
    if nombre_municipio in municipios_df['municipio'].values:
        codigo_municipio = municipios_df[municipios_df['municipio'] == nombre_municipio].iloc[0]['id']
        return codigo_municipio[2:]  # Eliminar las dos primeras letras del código
    return None

# Función principal para obtener la ubicación del usuario y validarla con el CSV
def get_user_location():
    latitud, longitud = obtener_geolocalizacion()
    if latitud and longitud:
        nombre_municipio = obtener_municipio(latitud, longitud)
        if nombre_municipio:
            codigo_municipio = obtener_codigo_municipio(nombre_municipio)
            if codigo_municipio:
                return nombre_municipio, codigo_municipio
            else:
                return None, None  # El municipio no está en el CSV
        else:
            return None, None  # No se encontró el municipio
    else:
        return None, None  # Error al obtener la geolocalización