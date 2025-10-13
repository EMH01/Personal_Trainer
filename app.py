import streamlit as st
import pandas as pd
import datetime
import json
from assistant import VirtualAssistant

assistant = VirtualAssistant()
usuario_nombre = assistant.usuario["nombre"]

st.set_page_config(page_title=f"Asistente {usuario_nombre}", layout="wide")
st.title(f"🤖🏋️‍♀️Asistente Virtual Personal: {usuario_nombre} 🥗💪")

CHAT_FILE = "historial_chat.json"

def save_chat_history(chat_history):
    with open(CHAT_FILE, "w", encoding="utf-8") as f:
        json.dump(chat_history, f, ensure_ascii=False, indent=2)

def load_chat_history():
    try:
        with open(CHAT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def try_parse_menu_json(response_text):
    campos_validos = ["Desayuno", "Comida", "Cena"]
    try:
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")
        if start_idx == -1 or end_idx == -1:
            return None
        menu_json = json.loads(response_text[start_idx:end_idx+1])
        dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        menu_filtrado = {}
        for dia in dias:
            if dia in menu_json:
                menu_filtrado[dia] = {campo: menu_json[dia].get(campo, "") for campo in campos_validos}
        return menu_filtrado if menu_filtrado else None
    except Exception:
        return None

tab1, tab2, tab3, tab4 = st.tabs([
    "Chat y recomendaciones",
    "Evolución personal",
    "Biblioteca certificada",
    "Plan semanal"
])

def limpiar_texto():
    st.session_state["main_text_area"] = ""

# --- TAB 1: Chat y recomendaciones ---
with tab1:
    st.header("Chat y recomendaciones")
    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = load_chat_history()
    if 'propuesta_edicion' not in st.session_state:
        st.session_state['propuesta_edicion'] = None
    if 'menu_json_detectado' not in st.session_state:
        st.session_state['menu_json_detectado'] = None
    if "main_text_area" not in st.session_state:
        st.session_state["main_text_area"] = ""

    incluir_memoria = st.checkbox("Incluir historial del chat en la consulta", value=True)

    user_input = st.text_area(
        "¿En qué puedo ayudarte hoy?",
        value=st.session_state["main_text_area"],
        key="main_text_area"
    )

    col1, col2, col3 = st.columns([1,10,1])
    limpiar_cuadro = col1.button("🧹", on_click=limpiar_texto)
    limpiar_chat = col2.button("Limpiar chat")
    enviar = col3.button("Enviar consulta")

    # --- VISUALIZACIÓN TIPO CHAT ---
    for msg in st.session_state['chat_history']:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- PREVENCIÓN DE DOBLE ENVÍO ---
    if enviar and user_input.strip():
        historial_para_modelo = st.session_state['chat_history'] if incluir_memoria else []
        result = assistant.respond(user_input, historial_para_modelo)
        st.session_state['chat_history'].append({"role": "user", "content": user_input})
        st.session_state['chat_history'].append({"role": "assistant", "content": result["respuesta"]})
        st.session_state['propuesta_edicion'] = result.get("propuesta_plan")
        menu_json = try_parse_menu_json(result["respuesta"])
        st.session_state['menu_json_detectado'] = menu_json
        save_chat_history(st.session_state['chat_history'])

    if limpiar_chat:
        st.session_state['chat_history'] = []
        st.session_state['propuesta_edicion'] = None
        st.session_state['menu_json_detectado'] = None
        save_chat_history([])
        st.success("¡Chat limpiado!")

    menu_json = st.session_state.get('menu_json_detectado')
    if menu_json:
        st.success("¡Menú semanal detectado en formato automático! Puedes guardarlo en tu plan semanal.")
        if st.button("Guardar menú semanal en el plan semanal", key="guardar_menu_json"):
            plan = assistant.get_plan_semanal()
            if plan is None or plan.empty:
                dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
                plan = pd.DataFrame({
                    "Día": dias,
                    "Desayuno": [""]*7,
                    "Comida": [""]*7,
                    "Cena": [""]*7,
                    "Ejercicio": [""]*7,
                })
            for idx in plan.index:
                dia = plan.at[idx, "Día"]
                if dia in menu_json:
                    for campo in ["Desayuno", "Comida", "Cena"]:
                        plan.at[idx, campo] = menu_json[dia].get(campo, "")
            assistant.save_plan_semanal(plan)
            st.success("¡Menú semanal guardado automáticamente en tu plan semanal!")
            st.session_state['menu_json_detectado'] = None

    prop = st.session_state.get('propuesta_edicion')
    if prop and isinstance(prop, dict):
        if prop.get("tipo") == "rutina":
            if st.button("Guardar rutina en plan semanal", key="guardar_rutina_semanal"):
                plan = assistant.get_plan_semanal()
                for idx in plan.index:
                    dia = plan.at[idx, "Día"]
                    if dia in prop["dias"]:
                        plan.at[idx, "Ejercicio"] = prop["contenido"][dia]
                assistant.save_plan_semanal(plan)
                st.success("¡Rutina guardada automáticamente en tu plan semanal!")
                st.session_state['propuesta_edicion'] = None
        elif prop.get("tipo") == "menu":
            if st.button("Guardar menú semanal en plan semanal", key="guardar_menu_semanal"):
                plan = assistant.get_plan_semanal()
                for idx in plan.index:
                    dia = plan.at[idx, "Día"]
                    if dia in prop["dias"]:
                        plan.at[idx, "Desayuno"] = prop["dias"][dia]["Desayuno"]
                        plan.at[idx, "Comida"] = prop["dias"][dia]["Comida"]
                        plan.at[idx, "Cena"] = prop["dias"][dia]["Cena"]
                assistant.save_plan_semanal(plan)
                st.success("¡Menú guardado automáticamente en tu plan semanal!")
                st.session_state['propuesta_edicion'] = None

    if isinstance(st.session_state.get('propuesta_edicion'), dict) and "tipo" not in st.session_state['propuesta_edicion']:
        prop = st.session_state['propuesta_edicion']
        st.markdown(f"**Propuesta para modificar tu plan semanal:**")
        st.markdown(
            f"**Día:** {prop['dia']} &nbsp;&nbsp; **Tipo:** {prop['tipo']} &nbsp;&nbsp; **Sugerencia del asistente:**"
        )
        sugerencia_edit = st.text_input(
            "Edita la sugerencia antes de guardar:",
            value=prop['sugerencia'],
            key="sugerencia_edit"
        )
        if st.button("Guardar sugerencia en el plan semanal"):
            plan = assistant.get_plan_semanal()
            if plan is None or plan.empty:
                dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
                plan = pd.DataFrame({
                    "Día": dias,
                    "Desayuno": [""]*7,
                    "Comida": [""]*7,
                    "Cena": [""]*7,
                    "Ejercicio": [""]*7,
                })
            idx = plan.index[plan["Día"]==prop["dia"]]
            if not idx.empty:
                idx = idx[0]
                plan.at[idx, prop["tipo"]] = sugerencia_edit
                assistant.save_plan_semanal(plan)
                st.success(f"¡Plan semanal actualizado para {prop['dia']} ({prop['tipo']})!")
                st.session_state['propuesta_edicion'] = None

# --- TAB 2: Evolución personal ---
with tab2:
    st.header("Evolución personal")

    st.subheader("Histórico de mediciones")
    measurements = assistant.get_measurements()
    if measurements is not None and not measurements.empty:
        # --- IMC Y VARIACIONES ---
        if "peso" in measurements.columns and "altura" in measurements.columns:
            measurements["IMC"] = measurements["peso"] / (measurements["altura"]/100)**2
        measurements["variación_cintura_%"] = measurements["cintura"].pct_change() * 100

        metricas = ["fecha", "cintura", "variación_cintura_%", "cadera", "muslo"]
        if "IMC" in measurements.columns:
            metricas += ["IMC"]

        st.dataframe(measurements[metricas])
        st.line_chart(measurements.set_index("fecha")[["cintura", "cadera", "muslo"]])
        if "IMC" in measurements.columns:
            st.line_chart(measurements.set_index("fecha")[["IMC"]])
    else:
        st.info("No hay registros de mediciones aún.")

    st.subheader("Registrar nueva medición")
    fecha_med = st.date_input("Fecha de la medición", value=datetime.date.today())
    cintura = st.number_input("Cintura (cm)", min_value=0.0, format="%.1f", key="cintura_med")
    cadera = st.number_input("Cadera (cm)", min_value=0.0, format="%.1f", key="cadera_med")
    muslo = st.number_input("Muslo (cm)", min_value=0.0, format="%.1f", key="muslo_med")
    peso = st.number_input("Peso (kg)", min_value=0.0, format="%.1f", key="peso_med")
    altura = st.number_input("Altura (cm)", min_value=0.0, format="%.1f", key="altura_med")

    # --- VALIDACIÓN DE FECHA DUPLICADA ---
    if st.button("Guardar medición"):
        if measurements is not None and not measurements.empty and fecha_med in pd.to_datetime(measurements["fecha"]).dt.date.values:
            st.warning("Ya existe una medición para esa fecha. Se sobrescribirá el registro.")
            idx = measurements.index[pd.to_datetime(measurements["fecha"]).dt.date == fecha_med]
            measurements.at[idx, "cintura"] = cintura
            measurements.at[idx, "cadera"] = cadera
            measurements.at[idx, "muslo"] = muslo
            measurements.at[idx, "peso"] = peso
            measurements.at[idx, "altura"] = altura
            assistant.save_measurements(measurements)
        else:
            assistant.register_measurements(fecha_med, cintura, cadera, muslo, peso, altura)
        st.success("¡Medición registrada! Recarga la pestaña para ver los datos actualizados.")

# --- TAB 3: Biblioteca certificada ---
with tab3:
    st.header("Biblioteca certificada")
    docs = assistant.list_documents()
    for doc in docs:
        st.markdown(f"**{doc['name']}**")
        if doc['type'] == "text":
            with st.expander("Ver contenido"):
                st.write(doc['content'])
        elif doc['type'] == "image":
            st.image(doc['path'])
        elif doc['type'] == "pdf":
            st.info(f"PDF disponible: {doc['name']}")

# --- TAB 4: Plan semanal ---
with tab4:
    st.header("Plan semanal de comidas y rutinas")

    plan = assistant.get_plan_semanal()
    dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]

    if plan is None or plan.empty:
        plan = pd.DataFrame({
            "Día": dias,
            "Desayuno": [""]*7,
            "Comida": [""]*7,
            "Cena": [""]*7,
            "Ejercicio": [""]*7,
        })
    
    st.subheader("🌟 Vista semanal 🌟")
    cols = st.columns(len(dias))
    for i, dia in enumerate(dias):
        with cols[i]:
            st.markdown(f"<div style='text-align:center'><b>{dia}</b></div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:15px;'>🥣 <b>Desayuno:</b><br>{plan.at[i,'Desayuno']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:15px;'>🍽 <b>Comida:</b><br>{plan.at[i,'Comida']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:15px;'>🍲 <b>Cena:</b><br>{plan.at[i,'Cena']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:15px;'>🏃 <b>Ejercicio:</b><br>{plan.at[i,'Ejercicio']}</div>", unsafe_allow_html=True)
            st.write("")  # Espacio extra
    st.markdown("---")

    st.subheader("Editar y exportar plan semanal")
    edited_plan = st.data_editor(plan, num_rows="dynamic", width='stretch')

    col_a, col_b = st.columns(2)
    if col_a.button("Guardar plan editado"):
        assistant.save_plan_semanal(edited_plan)
        st.success("¡Plan semanal actualizado!")

    if col_b.button("Exportar plan semanal a CSV"):
        edited_plan.to_csv("plan_semanal.csv", index=False)
        st.success("Plan exportado como CSV.")

    st.subheader("Historial de cambios")
    hist = assistant.get_historial_cambios()
    if not hist.empty:
        st.dataframe(hist)
    else:
        st.info("No hay historial de cambios aún.")