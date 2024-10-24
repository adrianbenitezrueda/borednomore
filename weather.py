import streamlit as st
import requests
from datetime import datetime
from collections import Counter
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar la API Key desde Streamlit Secrets
AEMET_API_KEY = st.secrets["AEMET_API_KEY"]

def obtener_prediccion(codigo_municipio, tipo_prediccion):
    """Obtiene la predicción climática de AEMET"""
    try:
        if tipo_prediccion == 'diaria':
            url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{codigo_municipio}"
        else:
            url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/horaria/{codigo_municipio}"
        
        headers = {'api_key': AEMET_API_KEY}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if 'datos' not in data:
            logger.error("No se encontró la clave 'datos' en la respuesta de AEMET")
            return None
            
        datos_url = data['datos']
        datos_response = requests.get(datos_url, timeout=10)
        datos_response.raise_for_status()
        
        return datos_response.json()
    except Exception as e:
        logger.error(f"Error al obtener predicción: {str(e)}")
        return None

def obtener_bloque_tiempo(hora_actual):
    """Determina el bloque de tiempo actual"""
    bloques = [(0, 6), (6, 12), (12, 18), (18, 24)]
    for inicio, fin in bloques:
        if inicio <= hora_actual < fin:
            return f"{inicio:02d}-{fin:02d}"
    return None

def obtener_temperaturas(prediccion_hoy):
    """Extrae temperaturas máxima y mínima"""
    try:
        temp_max = prediccion_hoy['temperatura']['maxima']
        temp_min = prediccion_hoy['temperatura']['minima']
        return temp_max, temp_min
    except (KeyError, TypeError) as e:
        logger.error(f"Error al obtener temperaturas: {str(e)}")
        return None, None

def obtener_temperatura_actual(prediccion_hoy):
    """Obtiene la temperatura actual basada en la hora"""
    try:
        hora_actual = datetime.now().hour
        if 'temperatura' in prediccion_hoy:
            for temp_dato in prediccion_hoy['temperatura']:
                if isinstance(temp_dato, dict) and 'periodo' in temp_dato and int(temp_dato['periodo']) == hora_actual:
                    return temp_dato.get('value')
    except Exception as e:
        logger.error(f"Error al obtener temperatura actual: {str(e)}")
    return None

def obtener_estado_cielo_mas_frecuente(prediccion_hoy):
    """Obtiene el estado del cielo más común"""
    try:
        estados_cielo = [periodo.get('descripcion', '') 
                        for periodo in prediccion_hoy.get('estadoCielo', []) 
                        if periodo.get('descripcion')]
        if estados_cielo:
            contador_estados = Counter(estados_cielo)
            return contador_estados.most_common(1)[0][0]
    except Exception as e:
        logger.error(f"Error al obtener estado del cielo: {str(e)}")
    return None

def obtener_dato_por_bloque(datos, bloque, clave):
    """Función genérica para obtener datos por bloque de tiempo"""
    try:
        for dato in datos:
            if dato.get('periodo') == bloque:
                if clave == 'estadoCielo':
                    return dato.get('descripcion')
                elif clave == 'viento':
                    return dato.get('velocidad')
                else:  # probPrecipitacion
                    return dato.get('value')
    except Exception as e:
        logger.error(f"Error al obtener {clave} por bloque: {str(e)}")
    return None

def procesar_datos_clima(codigo_municipio):
    """Función principal para procesar y devolver los datos del clima"""
    try:
        # Inicializar diccionario de respuesta con valores None
        datos = {
            "max_temp": None,
            "min_temp": None,
            "estado_cielo": None,
            "temp_actual": None,
            "viento_actual": None,
            "lluvia_actual": None
        }

        # Obtener predicciones
        clima_diario = obtener_prediccion(codigo_municipio, 'diaria')
        clima_horario = obtener_prediccion(codigo_municipio, 'horaria')

        if not clima_diario or not clima_horario:
            logger.error("No se pudieron obtener los datos del clima")
            return datos

        # Procesar datos diarios
        try:
            prediccion_diaria = clima_diario[0]['prediccion']['dia'][0]
            datos["max_temp"], datos["min_temp"] = obtener_temperaturas(prediccion_diaria)
            datos["estado_cielo"] = obtener_estado_cielo_mas_frecuente(prediccion_diaria)
        except (IndexError, KeyError) as e:
            logger.error(f"Error al procesar datos diarios: {str(e)}")

        # Procesar datos horarios
        try:
            prediccion_horaria = clima_horario[0]['prediccion']['dia'][0]
            hora_actual = datetime.now().hour
            bloque = obtener_bloque_tiempo(hora_actual)
            
            datos["temp_actual"] = obtener_temperatura_actual(prediccion_horaria)
            if bloque:
                datos["viento_actual"] = obtener_dato_por_bloque(
                    prediccion_horaria.get('viento', []), bloque, 'viento')
                datos["lluvia_actual"] = obtener_dato_por_bloque(
                    prediccion_horaria.get('probPrecipitacion', []), bloque, 'probPrecipitacion')
        except (IndexError, KeyError) as e:
            logger.error(f"Error al procesar datos horarios: {str(e)}")

        return datos

    except Exception as e:
        logger.error(f"Error general al procesar datos del clima: {str(e)}")
        return {
            "max_temp": None,
            "min_temp": None,
            "estado_cielo": None,
            "temp_actual": None,
            "viento_actual": None,
            "lluvia_actual": None
        }