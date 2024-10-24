import streamlit as st
import pandas as pd
import datetime
from geolocation import get_user_location  # Importar desde geolocation.py
from weather import procesar_datos_clima  # Importar desde weather.py
from googleplaces import GooglePlaces  # Para Google Places

# Cargar los datasets de actividades y municipios
indoor_activities = pd.read_csv('data/cleaned/home_activities.csv')
outdoor_activities = pd.read_csv('data/cleaned/outdoor_activities.csv')

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

    # Obtener la geolocalización del usuario desde geolocation.py
    nombre_municipio, codigo_municipio = get_user_location()

    if not nombre_municipio or not codigo_municipio:
        st.error("No se pudo determinar la ubicación del usuario.")
        return

    # Obtener el clima desde weather.py
    datos_clima = procesar_datos_clima(codigo_municipio)

    # Mostrar la leyenda con la ubicación, clima y detalles meteorológicos
    st.subheader("Tu ubicación y clima actual")
    st.write(f"Ubicación: {nombre_municipio}")
    st.write(f"Hora actual: {datetime.datetime.now().strftime('%H:%M')}")
    st.write(f"Temperatura actual: {datos_clima['temp_actual']} °C")
    st.write(f"Temperatura máxima: {datos_clima['max_temp']} °C")
    st.write(f"Temperatura mínima: {datos_clima['min_temp']} °C")
    st.write(f"Estado del cielo: {datos_clima['estado_cielo']}")
    st.write(f"Velocidad del viento: {datos_clima['viento_actual']} km/h")
    st.write(f"Probabilidad de lluvia: {datos_clima['lluvia_actual']}%")

    # Preguntar cuánto tiempo libre tiene el usuario
    available_time = st.slider("¿Cuánto tiempo libre tienes? (en minutos)", 10, 240, 60)

    # Decidir si el clima es bueno o malo
    is_good_weather = int(datos_clima['lluvia_actual']) < 50  # Buen clima si la probabilidad de lluvia es menor al 50%

    # Sugerir una tarea
    suggested_task = suggest_task(is_good_weather, available_time)
    st.write(f"Te sugerimos la siguiente tarea: {suggested_task['Nombre_Tarea']}")

    # Mostrar opciones de respuesta
    col1, col2, col3 = st.columns(3)
    
    if col1.button('Voy a hacerlo'):
        st.write("¡Genial! Aquí tienes algunas recomendaciones para hacer la tarea.")
        
        # Obtener recomendaciones de ChatGPT (lógica pendiente)
        st.write("Recomendaciones de ChatGPT:")

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
