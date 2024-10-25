import streamlit as st
import requests
import pandas as pd
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar la API Key de Google desde Streamlit Secrets
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

# Ruta del archivo CSV con los municipios
CSV_PATH = "data/raw/municipios_aemet.csv"

def load_municipios():
    """Carga el CSV de municipios con manejo de errores"""
    try:
        return pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        logger.error(f"No se encontró el archivo CSV en la ruta: {CSV_PATH}")
        st.error(f"Error: No se encontró la base de datos de municipios")
        return None
    except Exception as e:
        logger.error(f"Error al cargar el CSV: {str(e)}")
        st.error("Error al cargar la base de datos de municipios")
        return None

# Cargar los municipios desde el CSV
municipios_df = load_municipios()

def obtener_geolocalizacion():
    """Obtiene la geolocalización usando la API de Google"""
    try:
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
        data = {"considerIp": True}
        
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()  # Lanza una excepción para códigos de error HTTP
        
        data = response.json()
        return data['location']['lat'], data['location']['lng']
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al obtener geolocalización: {str(e)}")
        return None, None

def obtener_municipio(latitud, longitud):
    """Convierte coordenadas en nombre de municipio usando Google Geocoding"""
    try:
        url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitud},{longitud}&key={GOOGLE_API_KEY}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data['status'] != 'OK' or not data['results']:
            logger.error(f"Error en geocoding: {data['status']}")
            return None
            
        for result in data['results'][0]['address_components']:
            if 'locality' in result['types']:
                return result['long_name']
        for result in data['results'][0]['address_components']:
            if 'administrative_area_level_4' in result['types']:
                return result['long_name']
        for result in data['results'][0]['address_components']:
            if 'administrative_area_level_3' in result['types']:
                return result['long_name']
                
        return None
    except Exception as e:
        logger.error(f"Error al obtener municipio: {str(e)}")
        return None

def obtener_codigo_municipio(nombre_municipio):
    """Obtiene el código del municipio desde el DataFrame"""
    if municipios_df is None:
        return None
        
    try:
        if nombre_municipio in municipios_df['municipio'].values:
            codigo_municipio = municipios_df[municipios_df['municipio'] == nombre_municipio].iloc[0]['id']
            return codigo_municipio[2:]  # Eliminar las dos primeras letras del código
    except Exception as e:
        logger.error(f"Error al obtener código de municipio: {str(e)}")
    return None

def get_user_location():
    """Función principal para obtener la ubicación del usuario"""
    try:
        latitud, longitud = obtener_geolocalizacion()
        if not latitud or not longitud:
            logger.error("No se pudo obtener la geolocalización")
            return None, None

        nombre_municipio = obtener_municipio(latitud, longitud)
        if not nombre_municipio:
            logger.error("No se pudo obtener el nombre del municipio")
            return None, None

        codigo_municipio = obtener_codigo_municipio(nombre_municipio)
        if not codigo_municipio:
            logger.error(f"No se encontró código para el municipio: {nombre_municipio}")
            return None, None

        return nombre_municipio, codigo_municipio
    except Exception as e:
        logger.error(f"Error en get_user_location: {str(e)}")
        return None, None