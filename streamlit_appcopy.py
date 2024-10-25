import streamlit as st
import pandas as pd
import requests
from googleplaces import GooglePlaces
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Bored No More",
    page_icon="🎯",
    layout="wide"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .big-font {
        font-size:25px !important;
        font-weight: bold;
    }
    .card {
        padding: 1.5rem;
        border-radius: 10px;
        background-color: #f8f9fa;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .highlight {
        background-color: #e6f3ff;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Cargar API keys desde streamlit secrets
google_api_key = st.secrets["GOOGLE_API_KEY"]
aemet_api_key = st.secrets["AEMET_API_KEY"]

# Función para obtener la ubicación del usuario usando Google Geocoding API
def get_user_location():
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address=Cádiz,Spain&key={google_api_key}"
    try:
        response = requests.get(url)
        location_data = response.json()
        if location_data['status'] == 'OK':
            location = location_data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    except Exception as e:
        st.error(f"Error al obtener la ubicación: {str(e)}")
    return None, None

# Cargar los datasets
@st.cache_data
def load_data():
    indoor_activities = pd.read_csv('data/cleaned/home_activities.csv')
    outdoor_activities = pd.read_csv('data/cleaned/outdoor_activities.csv')
    municipios_aemet = pd.read_csv('data/raw/municipios_aemet.csv')
    return indoor_activities, outdoor_activities, municipios_aemet

indoor_activities, outdoor_activities, municipios_aemet = load_data()

# Función para buscar el municipio más cercano según la ubicación
def get_nearest_municipio(lat, lon):
    municipios_aemet['distancia'] = ((municipios_aemet['latitud_dec'] - lat)**2 + 
                                     (municipios_aemet['longitud_dec'] - lon)**2)**0.5
    return municipios_aemet.loc[municipios_aemet['distancia'].idxmin()]

# Función para obtener el clima actual desde AEMET
def get_weather(nearest_municipio):
    municipio_id = nearest_municipio['id']
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{municipio_id}?api_key={aemet_api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        return data.get('state', 'good')
    except Exception as e:
        st.warning("No se pudo obtener información del clima. Asumiendo buen tiempo.")
        return 'good'

def suggest_task(is_good_weather, available_time, excluded_tasks=None):
    all_activities = pd.concat([indoor_activities, outdoor_activities]) if is_good_weather else indoor_activities
    filtered_activities = all_activities[all_activities['Tiempo_Estimado_Minutos'] <= available_time]
    
    if excluded_tasks:
        filtered_activities = filtered_activities[~filtered_activities['Nombre_Tarea'].isin(excluded_tasks)]
    
    if filtered_activities.empty:
        return None
    return filtered_activities.sample(n=1).iloc[0]

def suggest_similar_task(category, subcategory, available_time, is_good_weather, excluded_tasks=None):
    all_activities = pd.concat([indoor_activities, outdoor_activities]) if is_good_weather else indoor_activities
    filtered_activities = all_activities[
        (all_activities['Categoria_Principal'] == category) &
        (all_activities['Subcategoria'] != subcategory) &
        (all_activities['Tiempo_Estimado_Minutos'] <= available_time)
    ]
    
    if excluded_tasks:
        filtered_activities = filtered_activities[~filtered_activities['Nombre_Tarea'].isin(excluded_tasks)]
        
    return filtered_activities.sample(n=1).iloc[0] if not filtered_activities.empty else None

def suggest_different_task(category, available_time, is_good_weather, excluded_tasks=None):
    all_activities = pd.concat([indoor_activities, outdoor_activities]) if is_good_weather else indoor_activities
    filtered_activities = all_activities[
        (all_activities['Categoria_Principal'] != category) &
        (all_activities['Tiempo_Estimado_Minutos'] <= available_time)
    ]
    
    if excluded_tasks:
        filtered_activities = filtered_activities[~filtered_activities['Nombre_Tarea'].isin(excluded_tasks)]
        
    return filtered_activities.sample(n=1).iloc[0] if not filtered_activities.empty else None

def display_task_card(task):
    st.markdown(f"""
    <div class='card'>
        <h4>{task['Nombre_Tarea']}</h4>
        <p>Categoría: {task['Categoria_Principal']}</p>
        <p>Tiempo estimado: {task['Tiempo_Estimado_Minutos']} minutos</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    # Header con estilo
    st.markdown('# 🎯 Bored no more')
    st.markdown('## ¡Encuentra algo divertido que hacer!')
    
    # Sidebar con información del tiempo y ubicación
    with st.sidebar:
        st.markdown("### 📍 Tu ubicación")
        user_lat, user_lon = get_user_location()
        if user_lat and user_lon:
            nearest_municipio = get_nearest_municipio(user_lat, user_lon)
            st.info(f"📌 {nearest_municipio['nombre']}")
            
            # Mostrar el tiempo actual
            weather = get_weather(nearest_municipio)
            weather_icon = "🌞" if weather == 'good' else "🌧"
            st.markdown(f"### {weather_icon} Tiempo actual")
            st.write("Perfecto para actividades al aire libre" if weather == 'good' else "Mejor quedarse en interior")

    # Contenido principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### ⏰ ¿Cuánto tiempo tienes disponible?")
        available_time = st.slider("", 10, 240, 60, help="Arrastra para seleccionar los minutos disponibles")
        
        # Mostrar el tiempo seleccionado de forma más visual
        hours = available_time // 60
        minutes = available_time % 60
        time_text = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
        st.markdown(f"<div class='highlight'>Tiempo seleccionado: {time_text}</div>", unsafe_allow_html=True)

    # Contenedor para la tarea principal
    task_container = st.container()
    
    # Contenedor para los botones
    button_container = st.container()
    
    # Contenedor para los lugares
    places_container = st.container()

    is_good_weather = weather == 'good'
    
    # Inicializar o actualizar la lista de tareas excluidas
    if 'excluded_tasks' not in st.session_state:
        st.session_state.excluded_tasks = set()

    # Obtener la tarea inicial si no existe
    if 'current_task' not in st.session_state:
        st.session_state.current_task = suggest_task(is_good_weather, available_time)
        if st.session_state.current_task is not None:
            st.session_state.excluded_tasks.add(st.session_state.current_task['Nombre_Tarea'])

    # Mostrar la tarea actual
    with task_container:
        st.markdown("### 💡 Sugerencia de actividad")
        if st.session_state.current_task is not None:
            display_task_card(st.session_state.current_task)

    # Botones de acción
    with button_container:
        col1, col2, col3 = st.columns(3)
        
        if col1.button('✅ ¡Voy a hacerlo!'):
            with places_container:
                st.success("¡Excelente elección! Aquí tienes algunos lugares cercanos donde puedes realizar esta actividad:")
                places = find_nearby_places(st.session_state.current_task['Nombre_Tarea'], user_lat, user_lon)
                if places:
                    for place in places:
                        st.markdown(f"""
                        <div class='card'>
                            <h4>🏢 {place.name}</h4>
                            <p>📍 {place.vicinity}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No se encontraron lugares específicos para esta actividad en tu zona.")

        if col2.button('🤔 Algo similar...'):
            similar_task = suggest_similar_task(
                st.session_state.current_task['Categoria_Principal'],
                st.session_state.current_task['Subcategoria'],
                available_time,
                is_good_weather,
                st.session_state.excluded_tasks
            )
            if similar_task is not None:
                st.session_state.current_task = similar_task
                st.session_state.excluded_tasks.add(similar_task['Nombre_Tarea'])
                with task_container:
                    st.markdown("### 💡 Nueva sugerencia de actividad")
                    display_task_card(similar_task)
            else:
                st.warning("No encontramos actividades similares para el tiempo disponible.")

        if col3.button('❌ Algo diferente'):
            different_task = suggest_different_task(
                st.session_state.current_task['Categoria_Principal'],
                available_time,
                is_good_weather,
                st.session_state.excluded_tasks
            )
            if different_task is not None:
                st.session_state.current_task = different_task
                st.session_state.excluded_tasks.add(different_task['Nombre_Tarea'])
                with task_container:
                    st.markdown("### 💡 Nueva sugerencia de actividad")
                    display_task_card(different_task)
            else:
                st.warning("No encontramos actividades diferentes para el tiempo disponible.")

    # Footer
    st.markdown("---")
    st.markdown("Made with ❤️ using Streamlit")

if __name__ == '__main__':
    main()