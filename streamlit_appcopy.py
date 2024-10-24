import streamlit as st
import pandas as pd
import requests
from googleplaces import GooglePlaces
from datetime import datetime

# [Mantener las funciones auxiliares y configuración inicial igual...]

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
    st.markdown('<p class="big-font">🎯 Bored no more: ¡Encuentra algo divertido que hacer!</p>', unsafe_allow_html=True)
    
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
                    st.markdown("### 💡 Sugerencia de actividad")
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
                    st.markdown("### 💡 Sugerencia de actividad")
                    display_task_card(different_task)
            else:
                st.warning("No encontramos actividades diferentes para el tiempo disponible.")

    # Footer
    st.markdown("---")
    st.markdown("Made with ❤️ using Streamlit")

if __name__ == '__main__':
    main()