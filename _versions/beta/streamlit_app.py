import streamlit as st
import pandas as pd
import datetime
import logging
from geolocation import get_user_location  # Importa la función para obtener la ubicación
from weather import procesar_datos_clima   # Importa la función para procesar datos del clima

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configurar la página
st.set_page_config(
    page_title="Bored no more",
    page_icon="🎯",
    layout="wide"
)

# Cargar los datasets de actividades
@st.cache_data
def load_activities():
    """Carga los datasets de actividades desde los archivos CSV"""
    try:
        indoor = pd.read_csv('data/cleaned/home_activities.csv')
        outdoor = pd.read_csv('data/cleaned/outdoor_activities.csv')
        return indoor, outdoor
    except Exception as e:
        logger.error(f"Error al cargar actividades: {str(e)}")
        return None, None

def suggest_task(is_good_weather, available_time, indoor_activities, outdoor_activities, exclude_activities=None):
    """Sugiere una tarea según el clima y tiempo disponible"""
    try:
        # Si el clima es bueno (lluvia < 50%), incluir actividades al aire libre
        if is_good_weather:
            all_activities = pd.concat([indoor_activities, outdoor_activities])
        else:
            all_activities = indoor_activities
        
        # Excluir actividades ya sugeridas
        if exclude_activities:
            all_activities = all_activities[~all_activities['Nombre_Tarea'].isin(exclude_activities)]
            
        # Filtrar por tiempo disponible
        filtered_activities = all_activities[all_activities['Tiempo_Estimado_Minutos'] <= available_time]
        if filtered_activities.empty:
            return None
        return filtered_activities.sample(n=1).iloc[0]
    except Exception as e:
        logger.error(f"Error al sugerir tarea: {str(e)}")
        return None

def main():
    try:
        st.title("Bored no more: proposal for doing things")
        
        # Cargar actividades
        indoor_activities, outdoor_activities = load_activities()
        if indoor_activities is None or outdoor_activities is None:
            st.error("Error al cargar la base de datos de actividades")
            return

        # Obtener ubicación usando el servicio de geolocation.py
        with st.spinner("Obteniendo tu ubicación..."):
            nombre_municipio, codigo_municipio = get_user_location()
            
        if not nombre_municipio or not codigo_municipio:
            st.error("No se pudo determinar tu ubicación")
            st.info("Por favor, asegúrate de que tu navegador permite el acceso a la ubicación")
            return

        # Obtener datos del clima usando el servicio de weather.py
        with st.spinner("Consultando el clima..."):
            datos_clima = procesar_datos_clima(codigo_municipio)
            if not datos_clima:
                st.error("No se pudieron obtener los datos del clima")
                return

        # Mostrar información del clima y ubicación
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📍 Tu ubicación y clima actual")
            st.write(f"📌 Ubicación: {nombre_municipio}")
            st.write(f"🕒 Hora actual: {datetime.datetime.now().strftime('%H:%M')}")
            
            if datos_clima.get("temp_actual"):
                st.write(f"🌡️ Temperatura actual: {datos_clima['temp_actual']}°C")
            if datos_clima.get("max_temp"):
                st.write(f"📈 Máxima: {datos_clima['max_temp']}°C")
            if datos_clima.get("min_temp"):
                st.write(f"📉 Mínima: {datos_clima['min_temp']}°C")
            if datos_clima.get("estado_cielo"):
                st.write(f"☁️ Cielo: {datos_clima['estado_cielo']}")
            if datos_clima.get("viento_actual"):
                st.write(f"💨 Viento: {datos_clima['viento_actual']} km/h")
            if datos_clima.get("lluvia_actual"):
                st.write(f"🌧️ Prob. lluvia: {datos_clima['lluvia_actual']}%")

        with col2:
            st.subheader("⏱️ Tiempo disponible")
            available_time = st.slider(
                "¿Cuánto tiempo libre tienes?",
                min_value=10,
                max_value=240,
                value=60,
                step=10,
                help="Arrastra el slider para indicar los minutos disponibles"
            )

        # Decidir si el clima es bueno basado en la probabilidad de lluvia
        is_good_weather = datos_clima.get('lluvia_actual', 100) < 50  # Por defecto considera mal tiempo si no hay dato

        # Mantener un historial de tareas sugeridas en la sesión
        if 'suggested_tasks_history' not in st.session_state:
            st.session_state.suggested_tasks_history = []

        # Sugerir tarea inicial si no hay ninguna en la sesión
        if 'current_task' not in st.session_state:
            st.session_state.current_task = suggest_task(
                is_good_weather, 
                available_time, 
                indoor_activities, 
                outdoor_activities,
                st.session_state.suggested_tasks_history
            )

        if st.session_state.current_task is None:
            st.error("No se encontraron actividades que coincidan con tu tiempo disponible")
            return

        # Mostrar la tarea sugerida
        st.subheader("🎯 Sugerencia de actividad")
        st.write(f"Te sugerimos: **{st.session_state.current_task['Nombre_Tarea']}**")
        st.write(f"Tiempo estimado: {st.session_state.current_task['Tiempo_Estimado_Minutos']} minutos")

        # Botones de acción
        col1, col2, col3 = st.columns(3)
        
        if col1.button('✅ ¡Voy a hacerlo!'):
            st.success("¡Excelente elección! ¡Disfruta de la actividad!")
            st.balloons()
            
        if col2.button('🤔 No me apetece mucho'):
            st.session_state.suggested_tasks_history.append(st.session_state.current_task['Nombre_Tarea'])
            nueva_tarea = suggest_task(
                is_good_weather, 
                available_time, 
                indoor_activities, 
                outdoor_activities,
                st.session_state.suggested_tasks_history
            )
            if nueva_tarea is not None:
                st.session_state.current_task = nueva_tarea
                st.experimental_rerun()
            else:
                st.warning("No hay más sugerencias similares disponibles")
                
        if col3.button('❌ No me apetece nada hacer esto'):
            st.session_state.suggested_tasks_history.append(st.session_state.current_task['Nombre_Tarea'])
            nueva_tarea = suggest_task(
                is_good_weather, 
                available_time, 
                indoor_activities, 
                outdoor_activities,
                st.session_state.suggested_tasks_history
            )
            if nueva_tarea is not None:
                st.session_state.current_task = nueva_tarea
                st.experimental_rerun()
            else:
                st.warning("No hay más sugerencias disponibles")

    except Exception as e:
        logger.error(f"Error en la aplicación: {str(e)}")
        st.error("Ha ocurrido un error inesperado. Por favor, intenta recargar la página.")

if __name__ == '__main__':
    main()