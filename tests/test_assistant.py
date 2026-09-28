import datetime as dt
from types import SimpleNamespace

import pandas as pd

from assistant import VirtualAssistant


def make_assistant(tmp_path, monkeypatch):
    (tmp_path / "config_usuario.example.yaml").write_text(
        "nombre: Demo\npreferencias: []\nobjetivos: []\nrefrigerador: []\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    return VirtualAssistant(base_dir=tmp_path)


def test_uses_example_config_when_private_config_is_missing(tmp_path, monkeypatch):
    assistant = make_assistant(tmp_path, monkeypatch)

    assert assistant.usuario["nombre"] == "Demo"
    assert assistant.using_example_config is True


def test_register_measurements_preserves_weight_and_height(tmp_path, monkeypatch):
    assistant = make_assistant(tmp_path, monkeypatch)

    assistant.register_measurements(
        dt.date(2026, 9, 28),
        cintura=80,
        cadera=95,
        muslo=55,
        peso=64,
        altura=168,
    )

    measurements = pd.read_csv(tmp_path / "mediciones.csv")
    assert measurements.loc[0, "peso"] == 64
    assert measurements.loc[0, "altura"] == 168


def test_save_measurements_supports_editing_existing_row(tmp_path, monkeypatch):
    assistant = make_assistant(tmp_path, monkeypatch)
    original = pd.DataFrame(
        [
            {
                "fecha": "2026-09-28",
                "cintura": 80,
                "cadera": 95,
                "muslo": 55,
                "peso": 64,
                "altura": 168,
            }
        ]
    )
    assistant.save_measurements(original)

    edited = assistant.get_measurements()
    edited.loc[0, "peso"] = 63.5
    assistant.save_measurements(edited)

    reloaded = assistant.get_measurements()
    assert reloaded.loc[0, "peso"] == 63.5


def test_openai_client_is_injectable(tmp_path, monkeypatch):
    captured = {}

    class Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Respuesta demo"))]
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    assistant = make_assistant(tmp_path, monkeypatch)
    assistant._openai_client = client
    assistant.deployment = "demo-deployment"

    result = assistant.respond("Dame una idea de desayuno", [])

    assert result["respuesta"] == "Respuesta demo"
    assert captured["model"] == "demo-deployment"
    assert "No hagas diagnósticos médicos" in captured["messages"][0]["content"]
