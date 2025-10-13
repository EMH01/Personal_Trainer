#!/bin/bash

# Activa el entorno virtual
source .venv/bin/activate

# Lanza el asistente con Streamlit
streamlit run app.py

# Al cerrar Streamlit, desactiva el entorno virtual
deactivate