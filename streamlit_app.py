import streamlit as st
import pandas as pd
import requests
import datetime
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
        address = location_data['results'][0]['formatted_address']
        return location['lat'], location['lng'], address
    else:
        st.error("No se pudo obtener la ubicación.")
        return None, None, None

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

# Función para obtener la predicción horaria de AEMET (para la temperatura actual)
def get_hourly_temperature(nearest_municipio):
    municipio_id = nearest_municipio['id']
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/horaria/{municipio_id}?api_key={aemet_api_key}"
    response = requests.get(url)
    data = response.json()
    
    current_time = datetime.datetime.now().hour  # Hora actual
    if 'prediccion' in data and 'temperatura' in data['prediccion']:
        # Obtener la predicción horaria más cercana a la hora actual
        hourly_temps = data['prediccion']['temperatura']['datos']
        current_temp = next((t['valor'] for t in hourly_temps if int(t['hora']) == current_time), 'N/A')
    else:
        current_temp = 'N/A'
    
    return current_temp

# Función para obtener la predicción diaria de AEMET (para lluvia y viento)
def get_daily_weather(nearest_municipio):
    municipio_id = nearest_municipio['id']
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{municipio_id}?api_key={aemet_api_key}"
    response = requests.get(url)
    data = response.json()

    if 'prediccion' in data:
        prediccion = data['prediccion']
        prob_lluvia = prediccion['prob_precipitacion'][0]['value'] if 'prob_precipitacion' in prediccion else 'N/A'
        velocidad_viento = prediccion['viento'][0]['velocidad'] if 'viento' in prediccion else 'N/A'
    else:
        prob_lluvia = 'N/A'
        velocidad_viento = 'N/A'

    return prob_lluvia, velocidad_viento

# Función para sugerir una tarea según el clima
def suggest_task(is_good_weather, available_time):
    if is_good_weather:
        all_activities = pd.concat([indoor_activities, outdoor_activities])
    else:
        all_activities = indoor_activities
    
    filtered_activities = all_activities[all_activities['Tiempo_Estimado_Minutos'] <= available_time]
    suggested_task = filtered_activities.sample(n=1).iloc[0]
    return suggested_task

# Streamlit app
def main():
    st.title("Bored no more: proposal for doing things")

    # Obtener la geolocalización y el clima
    user_lat, user_lon, user_address = get_user_location()
    nearest_municipio = get_nearest_municipio(user_lat, user_lon)
    
    # Obtener la temperatura actual (predicción horaria) y las demás variables (predicción diaria)
    temperatura_actual = get_hourly_temperature(nearest_municipio)
    prob_lluvia, velocidad_viento = get_daily_weather(nearest_municipio)

    # Mostrar la leyenda con la ubicación, clima y detalles meteorológicos
    st.subheader("Tu ubicación y clima actual")
    st.write(f"Ubicación: {user_address}")
    st.write(f"Hora actual: {datetime.datetime.now().strftime('%H:%M')}")
    st.write(f"Temperatura actual: {temperatura_actual} °C")
    st.write(f"Probabilidad de lluvia: {prob_lluvia}%")
    st.write(f"Velocidad del viento: {velocidad_viento} km/h")

    # Preguntar cuánto tiempo libre tiene el usuario
    available_time = st.slider("¿Cuánto tiempo libre tienes? (en minutos)", 10, 240, 60)

    # Decidir si el clima es bueno o malo
    is_good_weather = int(prob_lluvia) < 50  # Buen clima si la probabilidad de lluvia es menor al 50%

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

    if col3.button('No me apetece nada hacer esto'):
        st.write("Te sugerimos una tarea completamente diferente...")

if __name__ == '__main__':
    main()
