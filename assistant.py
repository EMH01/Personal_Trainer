import os
import openai
import datetime
import pandas as pd
import requests
import yaml
from dotenv import load_dotenv

load_dotenv()

class VirtualAssistant:
    def __init__(self):
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.api_version = os.getenv("AZURE_OPENAI_VERSION")
        self.docintel_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.docintel_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.docs_folder = "bibliografia_dietas"
        self.evolution_file = "evolucion.csv"
        self.measurements_file = "mediciones.csv"
        self.plan_file = "plan_semanal.csv"
        self.hist_file = "historial_cambios.csv"

        with open("config_usuario.yaml", "r") as f:
            self.usuario = yaml.safe_load(f)

        openai.api_type = "azure"
        openai.api_base = self.openai_endpoint
        openai.api_key = self.openai_key
        openai.api_version = self.api_version

    # Documentos y biblioteca
    def list_documents(self):
        docs = []
        if not os.path.exists(self.docs_folder):
            return docs
        for fname in os.listdir(self.docs_folder):
            path = os.path.join(self.docs_folder, fname)
            if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                docs.append({"name": fname, "path": path, "type": "image"})
            elif fname.lower().endswith('.txt'):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                docs.append({"name": fname, "content": content, "type": "text"})
            elif fname.lower().endswith('.pdf'):
                docs.append({"name": fname, "path": path, "type": "pdf"})
        return docs

    def analizar_pdf(self, file_path):
        url = f"{self.docintel_endpoint}/formrecognizer/documentModels/prebuilt-layout/analyze?api-version=2023-07-31"
        headers = {
            "Ocp-Apim-Subscription-Key": self.docintel_key,
            "Content-Type": "application/pdf"
        }
        with open(file_path, "rb") as f:
            data = f.read()
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        texto = "\n".join([line['content'] for page in result.get('pages', []) for line in page.get('lines', [])])
        return texto

    def get_bibliografia_resumida(self):
        resumenes = []
        for doc in self.list_documents():
            if doc['type'] == "text":
                resumenes.append(f"{doc['name']}: {doc['content'][:500]}{'...' if len(doc['content'])>500 else ''}")
            elif doc['type'] == "pdf":
                texto = self.analizar_pdf(doc['path'])
                resumenes.append(f"{doc['name']}: {texto[:500]}{'...' if len(texto)>500 else ''}")
        return "\n".join(resumenes)

    # Evolución personal - mediciones
    def get_measurements(self):
        if not os.path.exists(self.measurements_file):
            return None
        df = pd.read_csv(self.measurements_file)
        # Solo columnas relevantes (sin peso)
        columnas = ["fecha", "cintura", "cadera", "muslo"]
        return df[columnas] if set(columnas).issubset(df.columns) else df

    def register_measurements(self, fecha, cintura, cadera, muslo):
        entry = {
            "fecha": fecha.strftime("%Y-%m-%d"),
            "cintura": cintura,
            "cadera": cadera,
            "muslo": muslo,
        }
        if os.path.exists(self.measurements_file):
            df = pd.read_csv(self.measurements_file)
            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        else:
            df = pd.DataFrame([entry])
        df.to_csv(self.measurements_file, index=False)
        self.registrar_cambio(
            "mediciones",
            f"Nuevo registro de medición: {entry['fecha']}",
            "",
            str(entry)
        )

    def get_measurements_resumen(self):
        df = self.get_measurements()
        if df is None or df.empty:
            return "Sin registros de mediciones."
        ultimos = df.tail(5)
        resumen = []
        for _, row in ultimos.iterrows():
            resumen.append(
                f"{row['fecha']}: Cintura: {row['cintura']}cm, Cadera: {row['cadera']}cm, Muslo: {row['muslo']}cm"
            )
        return "\n".join(resumen)

    # Plan semanal: comidas y rutinas
    def get_plan_semanal(self):
        if not os.path.exists(self.plan_file):
            return None
        return pd.read_csv(self.plan_file)

    def save_plan_semanal(self, plan_df):
        prev_plan = self.get_plan_semanal()
        # Solo guardar los cambios REALES
        if prev_plan is not None:
            for i in range(len(plan_df)):
                for col in ["Desayuno", "Comida", "Cena", "Ejercicio"]:
                    valor_antes = prev_plan.at[i, col] if col in prev_plan.columns else ""
                    valor_despues = plan_df.at[i, col]
                    if (
                        pd.notna(valor_despues) and valor_despues != valor_antes
                        and not (pd.isna(valor_antes) and valor_despues in [None, "", "nan", "None"])
                        and not (pd.isna(valor_despues) and valor_antes in [None, "", "nan", "None"])
                    ):
                        self.registrar_cambio(
                            "plan_semanal",
                            f"Cambio en {col} de {plan_df.at[i, 'Día']}",
                            valor_antes,
                            valor_despues
                        )
        plan_df.to_csv(self.plan_file, index=False)

    def registrar_cambio(self, tipo, descripcion, valor_antes, valor_despues):
        entry = {
            "fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tipo": tipo,
            "descripcion": descripcion,
            "valor_antes": valor_antes,
            "valor_despues": valor_despues
        }
        if os.path.exists(self.hist_file):
            df = pd.read_csv(self.hist_file)
            df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
        else:
            df = pd.DataFrame([entry])
        df.to_csv(self.hist_file, index=False)

    def get_historial_cambios(self):
        if not os.path.exists(self.hist_file):
            return pd.DataFrame()
        return pd.read_csv(self.hist_file)

    def propuestas_automaticas(self):
        plan = self.get_plan_semanal()
        mensajes = []
        # Propuesta: cambio de comida si se repite demasiado
        if plan is not None and not plan.empty:
            comidas = plan["Comida"].value_counts()
            if comidas.max() > 2 and comidas.idxmax() != "":
                comida_repetida = comidas.idxmax()
                mensajes.append(f"La comida '{comida_repetida}' se repite {comidas.max()} veces esta semana, ¿quieres cambiarla en tu plan?")
            if not any(plan["Ejercicio"].astype(str).str.lower().str.contains("casa", na=False)):
                mensajes.append("No tienes ejercicio en casa esta semana, ¿quieres añadir una rutina en casa?")
        # Propuesta: si han pasado X días desde la última medición
        df = self.get_measurements()
        if df is not None and not df.empty and "fecha" in df.columns:
            fechas = pd.to_datetime(df["fecha"])
            ult_fecha = fechas.max().date()
            hoy = datetime.datetime.now().date()
            if (hoy - ult_fecha).days > 7:
                mensajes.append("No has registrado mediciones en más de una semana, ¿quieres hacerlo ahora?")
        return mensajes

    def construir_instruccion_modificacion(self, user_input):
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        tipos = ["desayuno", "comida", "cena", "ejercicio"]
        dia = None
        tipo = None
        for d in dias:
            if d in user_input.lower():
                dia = d.capitalize()
        for t in tipos:
            if t in user_input.lower():
                tipo = t.capitalize()
        return dia, tipo

    def build_prompt(self, user_input, chat_history):
        u = self.usuario
        history = "\n".join([f"{m['role']}: {m['content']}" for m in chat_history])
        momento = datetime.datetime.now()
        hora_actual = momento.strftime('%H:%M')
        dia_actual = momento.strftime('%A, %d de %B de %Y')
        measurements_resumen = self.get_measurements_resumen()
        bibliografia = self.get_bibliografia_resumida()
        plan = self.get_plan_semanal()
        plan_text = ""
        if plan is not None and not plan.empty:
            plan_text = "\n".join([
                f"{row['Día']}: Desayuno: {row['Desayuno']}, Comida: {row['Comida']}, Cena: {row['Cena']}, Ejercicio: {row['Ejercicio']}"
                for _, row in plan.iterrows()
            ])
        else:
            plan_text = "Sin plan semanal registrado."
        preferencias = ", ".join(u.get("preferencias", []))
        rutina = "\n".join([f"- {r}" for r in u.get("rutina", [])])
        comentarios = "\n".join([f"- {c}" for c in u.get("comentarios", [])])
        horario_trabajo = u.get("horario_trabajo", "")
        materiales = ", ".join(u.get("materiales_casa", []))
        objetivos = ", ".join(u.get("objetivos", []))
        refrigerador = "\n".join([f"- {item}" for item in u.get("refrigerador", [])])

        prompt = (
            f"Usuario: {u['nombre']}, {u['edad']} años, {u['ciudad']}, {u['pais']}.\n"
            f"Estatura: {u['estatura']}m. Profesión: {u['profesion']}.\n"
            f"Preferencias: {preferencias}.\n"
            f"Rutina y actividades semanales:\n{rutina}\n"
            f"Horario de trabajo: {horario_trabajo}\n"
            f"Comentarios personales:\n{comentarios}\n"
            f"Material disponible en casa: {materiales}\n"
            f"Objetivos: {objetivos}\n"
            f"Alimentos disponibles en el refrigerador:\n{refrigerador}\n"
            f"Fecha y hora actual: {hora_actual} del {dia_actual}.\n"
            f"Últimos registros de mediciones:\n{measurements_resumen}\n"
            f"Plan semanal actual:\n{plan_text}\n"
            f"Bibliografía profesional resumida:\n{bibliografia}\n"
            f"Historial de chat:\n{history}\n"
            f"Consulta: {user_input}\n"
            "Analiza todos los datos, preferencias y lo que hay en el refrigerador/materiales para proponer rutinas o menús adaptados a la situación real del usuario y cada día en dependencia de la consulta que te haga. "
            "Si no tienes suficientes alimentos o materiales para hacer una rutina o menú adecuado, responde también con una lista de la compra breve y concreta y explica por qué. "
            "Si puedes, da la rutina o menú personalizado. Sé claro, breve, estructurado y fundamenta tus propuestas."
            "Si te pide menú semanal, responde SIEMPRE en formato JSON con los días como claves y los campos \"Desayuno\", \"Comida\", \"Cena\" por cada día. Si falta algún ingrediente importante, sugiere primero una lista de la compra y luego el menú. "
            "En cada sugerencia de comida, tras la propuesta, añade una frase tipo: 'Si te da hambre entre comidas, puedes merendar ....' Usa los alimentos que el usuario tiene en el refrigerador, si es posible, o los más saludables. "
            "Ejemplo de formato de respuesta:\n"
            "{\n  \"Lunes\": {\"Desayuno\": \"...\", \"Comida\": \"...\", \"Cena\": \"...\"},\n  ...\n}\n"
            "Así se podrá guardar el menú automáticamente en el plan semanal."
        )
        return prompt

    def respond(self, user_input, chat_history):
        saludos = ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "hello"]
        dia, tipo = self.construir_instruccion_modificacion(user_input)
        if user_input.strip().lower() in saludos:
            return {"respuesta": f"¡Hola {self.usuario['nombre']}! ¿En qué puedo ayudarte hoy?", "propuesta_plan": None}
        
        prompt = self.build_prompt(user_input, chat_history)
        response = openai.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": f"Eres el entrenador personal, dietista y consejero de {self.usuario['nombre']}. Conversa de manera empática y humana, adaptándote al ritmo del usuario. Analiza siempre el contexto real, preferencias, materiales, alimentos y objetivos antes de proponer rutinas o menús. Si no hay suficientes alimentos/materiales, sugiere primero una lista de la compra."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        respuesta = response.choices[0].message.content

        return {"respuesta": respuesta, "propuesta_plan": None}