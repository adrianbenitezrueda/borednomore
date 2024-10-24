import streamlit as st
import pandas as pd
import datetime
import logging
from geolocation import get_user_location
from weather import procesar_datos_clima

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
        if is_good_weather:
            all_activities = pd.concat([indoor_activities, outdoor_activities])
        else:
            all_activities = indoor_activities
        
        # Excluir actividades ya sugeridas
        if exclude_activities:
            all_activities = all_activities[~all_activities['Nombre_Tarea'].isin(exclude_activities)]
            
        filtered_activities = all_activities[all_activities['Tiempo_Estimado_Minutos'] <= available_time]
        if filtered_activities.empty:
            return None
        return filtered_activities.sample(n=1).iloc[0]
    except Exception as e:
        logger.error(f"Error al sugerir tarea: {str(e)}")
        return None

def display_task_recommendations(task, weather_data):
    """Muestra recomendaciones personalizadas para la tarea"""
    st.subheader("📝 Recomendaciones para realizar la actividad")
    
    # Recomendaciones basadas en el clima
    if weather_data['lluvia_actual'] > 30:
        st.warning("☔ Hay probabilidad de lluvia. Considera llevar paraguas o realizar la actividad en interior.")
    
    if weather_data['temp_actual'] > 30:
        st.warning("🌡️ Hace bastante calor. Recuerda mantenerte hidratado.")
    
    # Recomendaciones específicas según el tipo de tarea
    if 'Categoria' in task:
        if task['Categoria'] == 'Deporte':
            st.info("🏃‍♂️ Recuerda hacer calentamiento antes de empezar.")
        elif task['Categoria'] == 'Cocina':
            st.info("👩‍🍳 Revisa que tienes todos los ingredientes necesarios.")
        elif task['Categoria'] == 'Manualidades':
            st.info("🎨 Prepara un espacio de trabajo adecuado y bien iluminado.")

def main():
    try:
        st.title("Bored no more: proposal for doing things")
        
        # Cargar actividades
        indoor_activities, outdoor_activities = load_activities()
        if indoor_activities is None or outdoor_activities is None:
            st.error("Error al cargar la base de datos de actividades")
            return

        # Obtener ubicación
        with st.spinner("Obteniendo tu ubicación..."):
            nombre_municipio, codigo_municipio = get_user_location()
            
        if not nombre_municipio or not codigo_municipio:
            st.error("No se pudo determinar tu ubicación")
            st.info("Por favor, asegúrate de que tu navegador permite el acceso a la ubicación")
            return

        # Obtener clima
        with st.spinner("Consultando el clima..."):
            datos_clima = procesar_datos_clima(codigo_municipio)

        # Mostrar información
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📍 Tu ubicación y clima actual")
            st.write(f"📌 Ubicación: {nombre_municipio}")
            st.write(f"🕒 Hora actual: {datetime.datetime.now().strftime('%H:%M')}")
            
            if datos_clima["temp_actual"]:
                st.write(f"🌡️ Temperatura actual: {datos_clima['temp_actual']}°C")
            if datos_clima["max_temp"]:
                st.write(f"📈 Máxima: {datos_clima['max_temp']}°C")
            if datos_clima["min_temp"]:
                st.write(f"📉 Mínima: {datos_clima['min_temp']}°C")
            if datos_clima["estado_cielo"]:
                st.write(f"☁️ Cielo: {datos_clima['estado_cielo']}")
            if datos_clima["viento_actual"]:
                st.write(f"💨 Viento: {datos_clima['viento_actual']} km/h")
            if datos_clima["lluvia_actual"]:
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

        # Decidir si el clima es bueno
        is_good_weather = datos_clima['lluvia_actual'] < 50

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
            display_task_recommendations(st.session_state.current_task, datos_clima)
            st.balloons()
            
        if col2.button('🤔 No me apetece mucho'):
            # Sugerir tarea similar (misma categoría)
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
            # Sugerir tarea completamente diferente
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