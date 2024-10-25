import streamlit as st
import pandas as pd
import requests
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
    .search-button {
        display: inline-block;
        background-color: #4285f4;
        color: white !important;
        padding: 10px 20px;
        border-radius: 5px;
        text-decoration: none;
        margin-top: 10px;
        font-weight: 500;
        transition: background-color 0.2s ease;
        text-align: center;
    }
    .search-button:hover {
        background-color: #357abd;
        text-decoration: none;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# Cargar API keys desde streamlit secrets
google_api_key = st.secrets["GOOGLE_API_KEY"]
aemet_api_key = st.secrets["AEMET_API_KEY"]

# Cargar los datasets
@st.cache_data
def load_data():
    indoor_activities = pd.read_csv('data/cleaned/home_activities.csv')
    outdoor_activities = pd.read_csv('data/cleaned/outdoor_activities.csv')
    municipios_aemet = pd.read_csv('data/raw/municipios_aemet.csv')
    return indoor_activities, outdoor_activities, municipios_aemet

indoor_activities, outdoor_activities, municipios_aemet = load_data()

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

def obtener_municipio(latitud, longitud):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={latitud},{longitud}&key={google_api_key}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if len(data['results']) > 0:
                address_components = data['results'][0]['address_components']
                municipio_locality = None
                municipio_alternative = None
                
                # 1. Intentar obtener el 'locality' primero
                for component in address_components:
                    if 'locality' in component['types']:
                        municipio_locality = component['long_name']
                        # Verificar si el municipio está en el CSV
                        if obtener_codigo_municipio(municipio_locality) is not None:
                            return municipio_locality

                # 2. Buscar en 'administrative_area_level_4' o superior
                for result in data['results']:
                    for component in result['address_components']:
                        if 'locality' in component['types'] or 'administrative_area_level_4' in component['types']:
                            municipio_alternative = component['long_name']
                            if obtener_codigo_municipio(municipio_alternative) is not None:
                                return municipio_alternative

                # 3. Intentar con 'administrative_area_level_3'
                for result in data['results']:
                    for component in result['address_components']:
                        if 'administrative_area_level_3' in component['types']:
                            municipio_alternative = component['long_name']
                            if obtener_codigo_municipio(municipio_alternative) is not None:
                                return municipio_alternative
        return None
    except Exception as e:
        st.error(f"Error al obtener el municipio: {str(e)}")
        return None

def obtener_codigo_municipio(municipio_nombre):
    """
    Obtiene el código del municipio sin el prefijo 'id'
    
    Args:
        municipio_nombre (str): Nombre del municipio
        
    Returns:
        str: Código del municipio sin el prefijo 'id', o None si no se encuentra
    """
    municipio_fila = municipios_aemet[municipios_aemet['nombre'].str.lower() == municipio_nombre.lower()]
    if not municipio_fila.empty:
        codigo_completo = municipio_fila.iloc[0]['id']
        # Si el código empieza con 'id', lo eliminamos
        if codigo_completo.startswith('id'):
            return codigo_completo[2:]
        return codigo_completo
    return None

def get_nearest_municipio(lat, lon):
    """
    Obtiene el municipio más cercano a las coordenadas dadas
    
    Args:
        lat (float): Latitud
        lon (float): Longitud
        
    Returns:
        dict: Datos del municipio incluyendo el código sin prefijo
    """
    # Primero intentamos obtener el municipio por nombre
    municipio_nombre = obtener_municipio(lat, lon)
    if municipio_nombre:
        codigo = obtener_codigo_municipio(municipio_nombre)
        if codigo:
            municipio_data = municipios_aemet[municipios_aemet['id'] == f"id{codigo}"].iloc[0].copy()
            # Aseguramos que el código no tiene el prefijo 'id'
            municipio_data['id'] = codigo
            return municipio_data

    # Si no funciona, usamos el método de distancia como fallback
    municipios_aemet['distancia'] = ((municipios_aemet['latitud_dec'] - lat)**2 + 
                                    (municipios_aemet['longitud_dec'] - lon)**2)**0.5
    municipio_data = municipios_aemet.loc[municipios_aemet['distancia'].idxmin()].copy()
    
    # Aseguramos que el código no tiene el prefijo 'id'
    if municipio_data['id'].startswith('id'):
        municipio_data['id'] = municipio_data['id'][2:]
    
    return municipio_data

    # Si no funciona, usamos el método de distancia como fallback
    municipios_aemet['distancia'] = ((municipios_aemet['latitud_dec'] - lat)**2 + 
                                    (municipios_aemet['longitud_dec'] - lon)**2)**0.5
    return municipios_aemet.loc[municipios_aemet['distancia'].idxmin()]

def obtener_bloque_tiempo(hora_actual):
    bloques = [
        (0, 6),
        (6, 12),
        (12, 18),
        (18, 24)
    ]
    for inicio, fin in bloques:
        if inicio <= hora_actual < fin:
            return f"{inicio:02d}-{fin:02d}"
    return None

def obtener_viento_por_bloque(prediccion_hoy, bloque):
    for viento in prediccion_hoy['viento']:
        if viento['periodo'] == bloque:
            return viento.get('velocidad', 'Información no disponible')
    return 'Información no disponible'

def obtener_lluvia_por_bloque(prediccion_hoy, bloque):
    for precipitacion in prediccion_hoy['probPrecipitacion']:
        if precipitacion['periodo'] == bloque:
            return precipitacion.get('value', 'Información no disponible')
    return 'Información no disponible'

def get_weather(nearest_municipio):
    municipio_id = nearest_municipio['id']
    if municipio_id.startswith('id'):
        municipio_id = municipio_id[2:]  # Eliminamos el "id" si existe
        
    url = f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{municipio_id}"
    headers = {
        'api_key': aemet_api_key
    }
    
    try:
        # Primera llamada para obtener la URL de los datos
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if 'datos' in data:
                # Segunda llamada para obtener los datos del clima
                datos_response = requests.get(data['datos'])
                if datos_response.status_code == 200:
                    clima_data = datos_response.json()
                    
                    # Obtener el primer día de predicción
                    prediccion_hoy = clima_data[0]['prediccion']['dia'][0]
                    
                    # Obtener la hora actual y el bloque correspondiente
                    hora_actual = datetime.now().hour
                    bloque = obtener_bloque_tiempo(hora_actual)
                    
                    # Obtener probabilidad de lluvia y viento
                    prob_lluvia = obtener_lluvia_por_bloque(prediccion_hoy, bloque)
                    velocidad_viento = obtener_viento_por_bloque(prediccion_hoy, bloque)
                    
                    # Convertir a números si son strings
                    try:
                        prob_lluvia = float(prob_lluvia) if prob_lluvia != 'Información no disponible' else 0
                        velocidad_viento = float(velocidad_viento) if velocidad_viento != 'Información no disponible' else 0
                    except (ValueError, TypeError):
                        return 'good'  # Si hay error en la conversión, asumimos buen tiempo
                    
                    # Para debugging
                    st.sidebar.write(f"Prob. lluvia: {prob_lluvia}%")
                    st.sidebar.write(f"Vel. viento: {velocidad_viento} km/h")
                    
                    # Determinar si el tiempo es bueno basado en los criterios
                    if prob_lluvia > 30 or velocidad_viento > 50:
                        return 'bad'
                    return 'good'
                    
        return 'good'  # Si hay algún error en las llamadas, asumimos buen tiempo
    except Exception as e:
        st.warning("No se pudo obtener información del clima. Asumiendo buen tiempo.")
        return 'good'

def suggest_task(is_good_weather, available_time, excluded_tasks=None):
    if is_good_weather:
        all_activities = pd.concat([indoor_activities, outdoor_activities])
        st.sidebar.write("🎯 Buscando en actividades de interior y exterior")
    else:
        all_activities = indoor_activities
        st.sidebar.write("🏠 Buscando solo en actividades de interior")
        
    filtered_activities = all_activities[all_activities['Tiempo_Estimado_Minutos'] <= available_time]
    
    if excluded_tasks:
        filtered_activities = filtered_activities[~filtered_activities['Nombre_Tarea'].isin(excluded_tasks)]
    
    if filtered_activities.empty:
        return None
        
    selected_task = filtered_activities.sample(n=1).iloc[0]
    st.sidebar.write(f"📍 Categoría seleccionada: {selected_task['Categoria_Principal']}")
    return selected_task

def suggest_similar_task(category, subcategory, available_time, is_good_weather, excluded_tasks=None):
    if is_good_weather:
        all_activities = pd.concat([indoor_activities, outdoor_activities])
        st.sidebar.write("🎯 Buscando tarea similar en actividades de interior y exterior")
    else:
        all_activities = indoor_activities
        st.sidebar.write("🏠 Buscando tarea similar solo en actividades de interior")
        
    filtered_activities = all_activities[
        (all_activities['Categoria_Principal'] == category) &
        (all_activities['Subcategoria'] != subcategory) &
        (all_activities['Tiempo_Estimado_Minutos'] <= available_time)
    ]
    
    if excluded_tasks:
        filtered_activities = filtered_activities[~filtered_activities['Nombre_Tarea'].isin(excluded_tasks)]
        
    if not filtered_activities.empty:
        selected_task = filtered_activities.sample(n=1).iloc[0]
        st.sidebar.write(f"📍 Nueva subcategoría: {selected_task['Subcategoria']}")
        return selected_task
    return None

def suggest_different_task(category, available_time, is_good_weather, excluded_tasks=None):
    if is_good_weather:
        all_activities = pd.concat([indoor_activities, outdoor_activities])
        st.sidebar.write("🎯 Buscando tarea diferente en actividades de interior y exterior")
    else:
        all_activities = indoor_activities
        st.sidebar.write("🏠 Buscando tarea diferente solo en actividades de interior")
        
    filtered_activities = all_activities[
        (all_activities['Categoria_Principal'] != category) &
        (all_activities['Tiempo_Estimado_Minutos'] <= available_time)
    ]
    
    if excluded_tasks:
        filtered_activities = filtered_activities[~filtered_activities['Nombre_Tarea'].isin(excluded_tasks)]
        
    if not filtered_activities.empty:
        selected_task = filtered_activities.sample(n=1).iloc[0]
        st.sidebar.write(f"📍 Nueva categoría: {selected_task['Categoria_Principal']}")
        return selected_task
    return None

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
   st.markdown('# 🎯 Bored no more\n ## ¡Encuentra algo divertido que hacer en tu tiempo libre!')
   
   # Inicializar el estado del clima como 'good' por defecto
   weather = 'good'
   
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

   # Definir is_good_weather aquí, después de obtener weather
   is_good_weather = weather == 'good'
   
   # Contenido principal
   col1, col2 = st.columns([2, 1])
   
   with col1:
       st.markdown("### ⏰ ¿Cuánto tiempo tienes disponible?")
       # Antes del slider, añade esto para mantener el último valor
       if 'last_time' not in st.session_state:
           st.session_state.last_time = 60

       # Modifica la línea del slider así
       available_time = st.slider("", 10, 240, 60, help="Arrastra para seleccionar los minutos disponibles", key='time_slider')

       # Después del slider, añade esto
       if st.session_state.last_time != available_time:
           # Inicializar excluded_tasks si no existe
           if 'excluded_tasks' not in st.session_state:
               st.session_state.excluded_tasks = set()
               
           st.session_state.current_task = suggest_task(is_good_weather, available_time, st.session_state.excluded_tasks)
           if st.session_state.current_task is not None:
               st.session_state.excluded_tasks.add(st.session_state.current_task['Nombre_Tarea'])
           st.session_state.last_time = available_time
       
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
               # Construir la URL de búsqueda de Google
               query = f"{st.session_state.current_task['Nombre_Tarea']} cómo hacer tutorial"
               google_search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
               
               st.success("¡Excelente elección! Aquí tienes algunos recursos que te pueden ayudar:")
               st.markdown(f"""
               <div class='card'>
                   <h4>🔍 Buscar guías y tutoriales</h4>
                   <p>Encuentra información útil sobre cómo realizar esta actividad</p>
                   <a href="{google_search_url}" target="_blank" class="search-button">
                       Buscar en Google 🔎
                   </a>
               </div>
               """, unsafe_allow_html=True)

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