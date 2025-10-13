# Asistente Virtual Personal 🏋️‍♀️🥗💪

Este proyecto es una **aplicación web en Streamlit** que funciona como asistente virtual personal, orientado a salud, fitness, nutrición y gestión de rutinas semanales. Permite visualizar, editar y guardar datos personales, rutinas y conversaciones, todo desde una interfaz web adaptable a cualquier dispositivo (móvil, PC, tablet).

Puedes desplegar la app en Streamlit Cloud y acceder a ella desde cualquier lugar mediante un enlace. Si el repositorio es privado, tus archivos personales estarán protegidos y solo tú podrás acceder tras autenticarte en GitHub/Streamlit.

---

## Características principales

- **Chat inteligente**: Conversa con tu asistente, guarda el historial en `historial_chat.json` y visualízalo tipo WhatsApp/Telegram.
- **Plan semanal**: Edita y visualiza rutinas y comidas en `plan_semanal.csv`, mostrado en tablas y tarjetas interactivas.
- **Histórico de mediciones**: Guarda y consulta tus datos en `mediciones.csv`, con cálculos automáticos de IMC y evolución semanal.
- **Gestión de documentos**: Accede a tu biblioteca personal (PDFs, imágenes) en la carpeta `bibliografia_dietas/` (no incluida en el repo público).
- **Exportación y edición**: Exporta tu plan semanal y mediciones a CSV con un clic.
- **Personalización total**: Cambia emojis, colores, textos y funcionalidades fácilmente.

---

## Cómo instalar y ejecutar

1. **Clona el repositorio**  
   ```bash
   git clone https://github.com/tu_usuario/tu_repo.git
   cd tu_repo
   ```

2. **Crea y activa un entorno virtual** (recomendado)
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Linux/Mac
   .venv\Scripts\activate     # En Windows
   ```

3. **Instala las dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecuta la aplicación**
   ```bash
   streamlit run app.py
   ```

---

## Personalización

Para adaptar el asistente a tus necesidades:

- **Emojis, títulos y textos**: Edita las líneas iniciales de `app.py` (por ejemplo, `st.title`).
- **Lógica de asistente**: El archivo `assistant.py` gestiona la interacción con el modelo o la base de datos. Modifícalo para cambiar el comportamiento.
- **Plan semanal**: Añade o quita columnas, cambia los días, personaliza la visualización mejorada con tarjetas y emojis.
- **Mediciones**: Añade más métricas, modifica el cálculo del IMC, cambia la visualización.
- **Chat y visualización de mensajes**: Aprovecha `st.chat_message` para una experiencia tipo WhatsApp/Telegram.
- **Exportación y edición**: Puedes añadir exportación a PDF, edición de otros datos, integración con otras APIs, etc.

---

## Estructura de archivos principales

- `app.py`: Aplicación principal Streamlit. Organiza la interfaz, pestañas y lógica de visualización.
- `assistant.py`: Lógica del asistente virtual. Gestiona respuestas, interacción y procesamiento de mensajes.
- `config_usuario.yaml`: Configuración personalizada del usuario (no incluida en el repo público).
- `historial_chat.json`: Guarda el historial completo de conversaciones.
- `historial_cambios.csv`: Registro de cambios realizados en rutinas y datos.
- `ideas_msjs.txt`: Notas rápidas y mensajes frecuentes para el asistente.
- `mediciones.csv`: Datos de mediciones corporales, IMC y evolución.
- `plan_semanal.csv`: Rutinas y comidas semanales, editable desde la app.
- `requirements.txt`: Lista de dependencias necesarias para ejecutar la app.
- `bibliografia_dietas/`: Carpeta para documentos personales, PDFs y recursos (no incluida en el repo público).

---

## Dependencias recomendadas

Incluye, como mínimo:
- `streamlit >= 1.25`
- `pandas`
- (Agrega las que uses en assistant.py: por ejemplo, OpenAI, scikit-learn, etc.)

---

## Visualización en el front

- El chat se muestra en formato conversación, con mensajes diferenciados para usuario y asistente.
- El plan semanal y las mediciones se visualizan en tablas interactivas y tarjetas con emojis.
- Los documentos personales pueden listarse y abrirse desde la interfaz (solo si están presentes y permitidos).
- Los cambios y el historial se muestran en pestañas separadas para fácil consulta.

## Despliegue y acceso

Puedes desplegar la app en Streamlit Cloud y conectarla a tu repositorio (público o privado):

- **Repo privado**: Sube tus archivos personales y accede a la app tras autenticarte en GitHub/Streamlit. Tus datos estarán protegidos.
- **Repo público**: Sube solo el código y ejemplos, excluyendo archivos personales y la carpeta de bibliografía mediante `.gitignore`.

Accede a la app desde cualquier dispositivo (móvil, PC, tablet) usando el enlace proporcionado por Streamlit Cloud.

## Ejemplo de personalización

Si quieres crear un asistente para otro ámbito (idiomas, productividad, psicología...):
1. Cambia los textos, emojis y títulos en `app.py`.
2. Modifica las pestañas y los campos del plan semanal y mediciones.
3. Adapta la lógica de `assistant.py` para responder acorde al nuevo tema.
4. Personaliza la visualización con tus propios iconos y colores.

---

## Créditos y soporte

Desarrollado por Esther Martin para uso personal.

---

