import streamlit as st
import pandas as pd
import requests
import random
from googleplaces import GooglePlaces  # Para Google Places

# Cargar API keys desde streamlit secrets
google_api_key = st.secrets["GOOGLE_API_KEY"]
aemet_api_key = st.secrets["AEMET_API_KEY"]

# Función para obtener la ubicación del usuario usando Google Geocoding API
def get_user_location():
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address=Cádiz,Spain&key={google_api_key}"
    response = requests.get(url)
    location_data = response.json()
    if location_data['status'] == 'OK':
        location = location_data['results'][0]['geometry']['location']
        return location['lat'], location['lng']
    else:
        st.error("No se pudo obtener la ubicación.")
        return None, None

# Cargar los datasets de actividades y municipios
indoor_activities = pd.read_csv('data/cleaned/home_activities.csv')
outdoor_activities = pd.read_csv('data/cleaned/outdoor_activities.csv')
municipios_aemet = pd.read_csv('data/raw/municipios_aemet.csv')

# Función para buscar el municipio más cercano según la ubicación
def get_nearest_municipio(lat, lon):
    municipios_aemet['distancia'] = ((municipios_aemet['latitud_dec'] - lat)**2 + 
                                     (municipios_aemet['longitud_dec'] - lon)**2)**0.5
    nearest_municipio = municipios_aemet.loc[municipios_aemet['distancia'].idxmin()]
    return nearest_municipio

# Función para obtener el clima actual desde AEMET.
def get_weather(nearest_municipio):
    municipio_id = nearest_municipio['id']
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{municipio_id}?api_key={aemet_api_key}"
    response = requests.get(url)
    data = response.json()
    
    # Asumir buen clima si no hay lluvias o mal tiempo (simplificación)
    weather_state = data['state'] if 'state' in data else 'good'
    return weather_state

# Función para sugerir una tarea según el clima
def suggest_task(is_good_weather, available_time):
    if is_good_weather:
        all_activities = pd.concat([indoor_activities, outdoor_activities])
    else:
        all_activities = indoor_activities
    
    filtered_activities = all_activities[all_activities['Tiempo_Estimado_Minutos'] <= available_time]
    suggested_task = filtered_activities.sample(n=1).iloc[0]
    return suggested_task

# Función para sugerir una tarea similar (misma categoría, diferente subcategoría)
def suggest_similar_task(category, subcategory, available_time, is_good_weather):
    if is_good_weather:
        all_activities = pd.concat([indoor_activities, outdoor_activities])
    else:
        all_activities = indoor_activities
    
    # Filtrar tareas de la misma categoría, pero subcategoría diferente
    filtered_activities = all_activities[
        (all_activities['Categoria_Principal'] == category) &
        (all_activities['Subcategoria'] != subcategory) &
        (all_activities['Tiempo_Estimado_Minutos'] <= available_time)
    ]
    
    if not filtered_activities.empty:
        return filtered_activities.sample(n=1).iloc[0]
    else:
        return None

# Función para sugerir una tarea diferente (otra categoría)
def suggest_different_task(category, available_time, is_good_weather):
    if is_good_weather:
        all_activities = pd.concat([indoor_activities, outdoor_activities])
    else:
        all_activities = indoor_activities
    
    # Filtrar tareas de una categoría diferente
    filtered_activities = all_activities[
        (all_activities['Categoria_Principal'] != category) &
        (all_activities['Tiempo_Estimado_Minutos'] <= available_time)
    ]
    
    if not filtered_activities.empty:
        return filtered_activities.sample(n=1).iloc[0]
    else:
        return None

# Función para buscar en Google Places
def find_place(task):
    google_places = GooglePlaces(google_api_key)
    query_result = google_places.nearby_search(
        location=get_user_location(), keyword=task, radius=5000)
    return query_result.places

# Streamlit app
def main():
    st.title("Bored no more: proposal for doing things")

    # Preguntar cuánto tiempo libre tiene el usuario
    available_time = st.slider("¿Cuánto tiempo libre tienes? (en minutos)", 10, 240, 60)

    # Obtener la geolocalización y el clima
    user_lat, user_lon = get_user_location()
    nearest_municipio = get_nearest_municipio(user_lat, user_lon)
    weather = get_weather(nearest_municipio)

    # Decidir si el clima es bueno o malo
    is_good_weather = weather == 'good'

    # Sugerir una tarea
    suggested_task = suggest_task(is_good_weather, available_time)
    st.write(f"Te sugerimos la siguiente tarea: {suggested_task['Nombre_Tarea']}")

    # Mostrar opciones de respuesta
    col1, col2, col3 = st.columns(3)
    
    if col1.button('Voy a hacerlo'):
        st.write("¡Genial! Aquí tienes algunas recomendaciones para hacer la tarea.")
        
        # Obtener recomendaciones de ChatGPT
        st.write("Recomendaciones de ChatGPT:")
        # (Aquí iría la lógica para usar ChatGPT con tu API)

        # Buscar lugares relacionados con Google Places
        st.write("Lugares cercanos para hacer o comprar lo que necesitas:")
        places = find_place(suggested_task['Nombre_Tarea'])
        for place in places:
            st.write(f"Nombre: {place.name}, Dirección: {place.vicinity}")
    
    if col2.button('No me apetece mucho'):
        st.write("Te sugerimos otra tarea similar...")
        similar_task = suggest_similar_task(
            category=suggested_task['Categoria_Principal'],
            subcategory=suggested_task['Subcategoria'],
            available_time=available_time,
            is_good_weather=is_good_weather
        )
        if similar_task is not None:
            st.write(f"Te sugerimos: {similar_task['Nombre_Tarea']}")
        else:
            st.write("Lo siento, no encontramos tareas similares.")

    if col3.button('No me apetece nada hacer esto'):
        st.write("Te sugerimos una tarea completamente diferente...")
        different_task = suggest_different_task(
            category=suggested_task['Categoria_Principal'],
            available_time=available_time,
            is_good_weather=is_good_weather
        )
        if different_task is not None:
            st.write(f"Te sugerimos: {different_task['Nombre_Tarea']}")
        else:
            st.write("Lo siento, no encontramos tareas de otras categorías.")

if __name__ == '__main__':
    main()
