from __future__ import annotations

import datetime as dt
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


class VirtualAssistant:
    """Local-first wellness planning assistant with optional Azure AI services."""

    def __init__(
        self,
        *,
        base_dir: str | Path = ".",
        openai_client: AzureOpenAI | None = None,
        http_session: requests.Session | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.docs_folder = self.base_dir / "bibliografia_dietas"
        self.measurements_file = self.base_dir / "mediciones.csv"
        self.plan_file = self.base_dir / "plan_semanal.csv"
        self.hist_file = self.base_dir / "historial_cambios.csv"

        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.api_version = os.getenv("AZURE_OPENAI_VERSION")

        self.docintel_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.docintel_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        self.docintel_api_version = os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_API_VERSION",
            "2024-11-30",
        )

        self._openai_client = openai_client
        self._http = http_session or requests.Session()
        self.usuario, self.using_example_config = self._load_user_config()

    def _load_user_config(self) -> tuple[dict[str, Any], bool]:
        private_config = self.base_dir / "config_usuario.yaml"
        example_config = self.base_dir / "config_usuario.example.yaml"
        config_path = private_config if private_config.exists() else example_config

        if not config_path.exists():
            raise FileNotFoundError(
                "Missing config_usuario.yaml and config_usuario.example.yaml."
            )

        with config_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}

        if "nombre" not in data:
            raise ValueError("User configuration must define 'nombre'.")

        return data, config_path == example_config

    def _client(self) -> AzureOpenAI:
        if self._openai_client is not None:
            return self._openai_client

        missing = [
            name
            for name, value in {
                "AZURE_OPENAI_ENDPOINT": self.openai_endpoint,
                "AZURE_OPENAI_API_KEY": self.openai_key,
                "AZURE_OPENAI_DEPLOYMENT_NAME": self.deployment,
                "AZURE_OPENAI_VERSION": self.api_version,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(
                "Azure OpenAI is not configured. Missing: " + ", ".join(missing)
            )

        self._openai_client = AzureOpenAI(
            api_key=self.openai_key,
            azure_endpoint=self.openai_endpoint,
            api_version=self.api_version,
        )
        return self._openai_client

    # Documents and optional bibliography context
    def list_documents(self) -> list[dict[str, str]]:
        docs: list[dict[str, str]] = []
        if not self.docs_folder.exists():
            return docs

        for path in sorted(self.docs_folder.iterdir()):
            suffix = path.suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg"}:
                docs.append({"name": path.name, "path": str(path), "type": "image"})
            elif suffix == ".txt":
                docs.append(
                    {
                        "name": path.name,
                        "content": path.read_text(encoding="utf-8"),
                        "type": "text",
                    }
                )
            elif suffix == ".pdf":
                docs.append({"name": path.name, "path": str(path), "type": "pdf"})
        return docs

    def analizar_pdf(
        self,
        file_path: str | Path,
        *,
        poll_interval_seconds: float = 1.0,
        max_polls: int = 60,
    ) -> str:
        if not self.docintel_endpoint or not self.docintel_key:
            raise RuntimeError("Azure Document Intelligence is not configured.")

        analyze_url = (
            f"{self.docintel_endpoint.rstrip('/')}/documentintelligence/"
            "documentModels/prebuilt-layout:analyze"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self.docintel_key,
            "Content-Type": "application/pdf",
        }
        params = {"api-version": self.docintel_api_version}

        with Path(file_path).open("rb") as handle:
            response = self._http.post(
                analyze_url,
                headers=headers,
                params=params,
                data=handle,
                timeout=30,
            )
        response.raise_for_status()

        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            raise RuntimeError("Document Intelligence response has no Operation-Location.")

        for _ in range(max_polls):
            result_response = self._http.get(
                operation_url,
                headers={"Ocp-Apim-Subscription-Key": self.docintel_key},
                timeout=30,
            )
            result_response.raise_for_status()
            payload = result_response.json()
            status = str(payload.get("status", "")).lower()

            if status == "succeeded":
                result = payload.get("analyzeResult", {})
                return "\n".join(
                    line.get("content", "")
                    for page in result.get("pages", [])
                    for line in page.get("lines", [])
                    if line.get("content")
                )
            if status in {"failed", "canceled"}:
                raise RuntimeError(f"Document analysis ended with status: {status}")

            time.sleep(poll_interval_seconds)

        raise TimeoutError("Document analysis did not finish within the polling limit.")

    def get_bibliografia_resumida(self) -> str:
        summaries: list[str] = []
        for doc in self.list_documents():
            if doc["type"] == "text":
                content = doc["content"]
            elif doc["type"] == "pdf":
                content = self.analizar_pdf(doc["path"])
            else:
                continue
            preview = content[:500]
            suffix = "..." if len(content) > 500 else ""
            summaries.append(f"{doc['name']}: {preview}{suffix}")
        return "\n".join(summaries)

    # Measurements
    def get_measurements(self) -> pd.DataFrame | None:
        if not self.measurements_file.exists():
            return None
        return pd.read_csv(self.measurements_file)

    def save_measurements(self, measurements: pd.DataFrame) -> None:
        measurements.to_csv(self.measurements_file, index=False)

    def register_measurements(
        self,
        fecha: dt.date,
        cintura: float,
        cadera: float,
        muslo: float,
        peso: float | None = None,
        altura: float | None = None,
    ) -> None:
        entry: dict[str, Any] = {
            "fecha": fecha.strftime("%Y-%m-%d"),
            "cintura": cintura,
            "cadera": cadera,
            "muslo": muslo,
        }
        if peso is not None:
            entry["peso"] = peso
        if altura is not None:
            entry["altura"] = altura

        existing = self.get_measurements()
        if existing is None:
            updated = pd.DataFrame([entry])
        else:
            updated = pd.concat([existing, pd.DataFrame([entry])], ignore_index=True)

        self.save_measurements(updated)
        self.registrar_cambio(
            "mediciones",
            f"Nuevo registro de medición: {entry['fecha']}",
            "",
            str(entry),
        )

    def get_measurements_resumen(self) -> str:
        df = self.get_measurements()
        if df is None or df.empty:
            return "Sin registros de mediciones."

        summary: list[str] = []
        for _, row in df.tail(5).iterrows():
            pieces = [
                f"Cintura: {row.get('cintura', '—')} cm",
                f"Cadera: {row.get('cadera', '—')} cm",
                f"Muslo: {row.get('muslo', '—')} cm",
            ]
            if pd.notna(row.get("peso")):
                pieces.append(f"Peso: {row['peso']} kg")
            summary.append(f"{row['fecha']}: " + ", ".join(pieces))
        return "\n".join(summary)

    # Weekly plan
    def get_plan_semanal(self) -> pd.DataFrame | None:
        if not self.plan_file.exists():
            return None
        return pd.read_csv(self.plan_file)

    def save_plan_semanal(self, plan_df: pd.DataFrame) -> None:
        previous = self.get_plan_semanal()
        tracked_columns = ["Desayuno", "Comida", "Cena", "Ejercicio"]

        if previous is not None and "Día" in plan_df.columns and "Día" in previous.columns:
            previous_by_day = previous.set_index("Día")
            for _, row in plan_df.iterrows():
                day = row["Día"]
                if day not in previous_by_day.index:
                    continue
                for column in tracked_columns:
                    if column not in plan_df.columns:
                        continue
                    before = previous_by_day.at[day, column] if column in previous.columns else ""
                    after = row[column]
                    before_normalized = "" if pd.isna(before) else str(before)
                    after_normalized = "" if pd.isna(after) else str(after)
                    if before_normalized != after_normalized:
                        self.registrar_cambio(
                            "plan_semanal",
                            f"Cambio en {column} de {day}",
                            before_normalized,
                            after_normalized,
                        )

        plan_df.to_csv(self.plan_file, index=False)

    def registrar_cambio(
        self,
        tipo: str,
        descripcion: str,
        valor_antes: Any,
        valor_despues: Any,
    ) -> None:
        entry = {
            "fecha": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tipo": tipo,
            "descripcion": descripcion,
            "valor_antes": valor_antes,
            "valor_despues": valor_despues,
        }
        if self.hist_file.exists():
            history = pd.read_csv(self.hist_file)
            history = pd.concat([history, pd.DataFrame([entry])], ignore_index=True)
        else:
            history = pd.DataFrame([entry])
        history.to_csv(self.hist_file, index=False)

    def get_historial_cambios(self) -> pd.DataFrame:
        if not self.hist_file.exists():
            return pd.DataFrame()
        return pd.read_csv(self.hist_file)

    def propuestas_automaticas(self) -> list[str]:
        plan = self.get_plan_semanal()
        messages: list[str] = []

        if plan is not None and not plan.empty:
            if "Comida" in plan.columns:
                meals = plan["Comida"].fillna("").value_counts()
                if not meals.empty and meals.max() > 2 and meals.idxmax():
                    messages.append(
                        f"La comida '{meals.idxmax()}' se repite {meals.max()} veces "
                        "esta semana. ¿Quieres variarla?"
                    )
            if "Ejercicio" in plan.columns and not any(
                plan["Ejercicio"].astype(str).str.lower().str.contains("casa", na=False)
            ):
                messages.append(
                    "No tienes ejercicio en casa esta semana. "
                    "¿Quieres añadir una rutina en casa?"
                )

        measurements = self.get_measurements()
        if measurements is not None and not measurements.empty and "fecha" in measurements:
            latest = pd.to_datetime(measurements["fecha"]).max().date()
            if (dt.date.today() - latest).days > 7:
                messages.append(
                    "No has registrado mediciones en más de una semana. "
                    "¿Quieres hacerlo ahora?"
                )
        return messages

    def construir_instruccion_modificacion(
        self,
        user_input: str,
    ) -> tuple[str | None, str | None]:
        days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        types = ["desayuno", "comida", "cena", "ejercicio"]
        lowered = user_input.lower()
        day = next((value.capitalize() for value in days if value in lowered), None)
        plan_type = next((value.capitalize() for value in types if value in lowered), None)
        return day, plan_type

    def build_prompt(self, user_input: str, chat_history: list[dict[str, str]]) -> str:
        user = self.usuario
        history = "\n".join(
            f"{message['role']}: {message['content']}" for message in chat_history
        )
        now = dt.datetime.now()
        plan = self.get_plan_semanal()
        if plan is None or plan.empty:
            plan_text = "Sin plan semanal registrado."
        else:
            plan_text = "\n".join(
                (
                    f"{row['Día']}: Desayuno: {row.get('Desayuno', '')}, "
                    f"Comida: {row.get('Comida', '')}, Cena: {row.get('Cena', '')}, "
                    f"Ejercicio: {row.get('Ejercicio', '')}"
                )
                for _, row in plan.iterrows()
            )

        preferences = ", ".join(map(str, user.get("preferencias", [])))
        goals = ", ".join(map(str, user.get("objetivos", [])))
        fridge = "\n".join(f"- {item}" for item in user.get("refrigerador", []))
        materials = ", ".join(map(str, user.get("materiales_casa", [])))

        bibliography = ""
        try:
            bibliography = self.get_bibliografia_resumida()
        except (RuntimeError, requests.RequestException, TimeoutError):
            bibliography = "Bibliografía externa no disponible en esta sesión."

        return (
            f"Usuario: {user.get('nombre', 'Usuario')}.\n"
            f"Preferencias: {preferences or 'No registradas'}.\n"
            f"Objetivos: {goals or 'No registrados'}.\n"
            f"Material disponible: {materials or 'No registrado'}.\n"
            f"Alimentos disponibles:\n{fridge or '- No registrados'}\n"
            f"Fecha y hora actual: {now.isoformat(timespec='minutes')}.\n"
            f"Últimos registros:\n{self.get_measurements_resumen()}\n"
            f"Plan semanal actual:\n{plan_text}\n"
            f"Bibliografía resumida:\n{bibliography or 'No disponible'}\n"
            f"Historial de chat:\n{history or 'Sin historial'}\n"
            f"Consulta: {user_input}\n\n"
            "Responde de forma práctica y estructurada. No diagnostiques enfermedades, "
            "no sustituyas a profesionales sanitarios y evita recomendaciones extremas. "
            "Para menús semanales, devuelve JSON con los días como claves y los campos "
            "Desayuno, Comida y Cena."
        )

    def respond(
        self,
        user_input: str,
        chat_history: list[dict[str, str]],
    ) -> dict[str, Any]:
        greetings = {
            "hola",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "hey",
            "hello",
        }
        if user_input.strip().lower() in greetings:
            return {
                "respuesta": (
                    f"¡Hola {self.usuario['nombre']}! ¿En qué puedo ayudarte hoy?"
                ),
                "propuesta_plan": None,
            }

        response = self._client().chat.completions.create(
            model=self.deployment,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente de planificación de bienestar, alimentación "
                        "cotidiana y actividad física. Personaliza usando solo el contexto "
                        "proporcionado. No hagas diagnósticos médicos ni presentes tus "
                        "respuestas como consejo sanitario profesional."
                    ),
                },
                {"role": "user", "content": self.build_prompt(user_input, chat_history)},
            ],
            temperature=0.5,
            max_tokens=1500,
        )
        return {
            "respuesta": response.choices[0].message.content or "",
            "propuesta_plan": None,
        }
