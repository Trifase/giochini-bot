import os
import re
import sqlite3
import logging
import asyncio
from typing import Optional, Tuple, List, Any
import httpx

try:
    import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)

DB_SCHEMA_PROMPT = """Sei un esperto sviluppatore SQLite per un bot Telegram di giochi giornalieri (Wordle, Connections, Geozee, Timdle, ecc.).
Il tuo compito è convertire la richiesta dell'utente in una singola query SQL SQLite valida ed efficiente.

Schema del Database SQLite:
Tabella 'punteggi':
- date (TEXT, data 'YYYY-MM-DD')
- timestamp (INTEGER, unix timestamp in secondi)
- chat_id (INTEGER, ID chat Telegram)
- user_id (INTEGER, ID univoco utente)
- user_name (TEXT, nome del giocatore)
- game (TEXT, nome del gioco es. 'Wordle', 'Connections', 'Geozee', 'Linxicon', 'BracketCity', ecc.)
- day (TEXT, numero del giorno/edizione del gioco)
- tries (INTEGER, numero di tentativi o punteggio. Minore è MEGLIO: per giochi standard sono i tentativi 1..6; per giochi a punteggio come Geozee e MinuteCryptic sono memorizzati come numeri NEGATIVI es. -576, quindi tries ASC è SEMPRE l'ordine dal migliore al peggiore).
- extra (TEXT, tiebreaker o stelle)
- streak (INTEGER, striscia consecutiva)
- lost (INTEGER, 1 se partita persa, 0 se vinta. Escludi partite perse usando WHERE (lost IS NOT 1 AND tries != 9999999) quando cerchi vincitori o calcoli percentuali di vittoria).

Tabella 'medaglie':
- date (TEXT, data del giorno)
- timestamp (INTEGER)
- chat_id (INTEGER)
- user_id (INTEGER)
- user_name (TEXT)
- gold (INTEGER, medaglie d'oro del giorno)
- silver (INTEGER, medaglie d'argento)
- bronze (INTEGER, medaglie di bronzo)

Regole per la query:
1. Restituisci SOLO ed esclusivamente la query SQL pura, senza blocchi markdown (no ```sql), senza spiegazioni.
2. Per calcolare il 1° posto di una giornata, usa:
   ROW_NUMBER() OVER (PARTITION BY game, day ORDER BY tries ASC, timestamp ASC) = 1
3. Usa solo sintassi SQLite standard.
"""


def get_api_credentials() -> Tuple[Optional[str], str]:
    """Ritorna (api_key, provider), dove provider può essere 'gemini' o 'openai'."""
    gemini_key = (
        getattr(config, "GEMINI_API_KEY", None)
        or os.environ.get("GEMINI_API_KEY")
    )
    if gemini_key:
        return gemini_key, "gemini"

    openai_key = (
        getattr(config, "OPENAI_API_KEY", None)
        or os.environ.get("OPENAI_API_KEY")
    )
    if openai_key:
        return openai_key, "openai"

    return None, ""


_AVAILABLE_GEMINI_MODELS: List[str] = []


async def get_available_gemini_models(client: httpx.AsyncClient, api_key: str, preferred_model: str) -> List[str]:
    """Interroga l'API di Gemini per ottenere i modelli di testo effettivamente disponibili per l'account."""
    global _AVAILABLE_GEMINI_MODELS
    if _AVAILABLE_GEMINI_MODELS:
        return _AVAILABLE_GEMINI_MODELS

    models = [preferred_model] if preferred_model else []
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = await client.get(url, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            discovered = []
            invalid_suffixes = ("-image", "-audio", "-tts", "-embedding", "embed", "-realtime", "-preview", "-experimental")
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    # Escludi modelli non testuali (immagini, audio, embedding, ecc.)
                    if not any(bad in name.lower() for bad in invalid_suffixes):
                        # Escludi vecchi modelli 2.x o 1.x se deprecati
                        if not name.startswith("gemini-1.") and not name.startswith("gemini-2."):
                            discovered.append(name)

            if discovered:
                def sort_key(name: str) -> tuple:
                    # 0: preferred, 1: 3.5-flash-lite, 2: 3.8-flash, 3: other 3.x
                    if name == preferred_model:
                        return (0, name)
                    if "3.5-flash-lite" in name.lower():
                        return (1, name)
                    if "3.8-flash" in name.lower():
                        return (2, name)
                    return (3, name)

                discovered.sort(key=sort_key)
                _AVAILABLE_GEMINI_MODELS = discovered
                logger.info(f"Modelli Gemini di testo disponibili: {_AVAILABLE_GEMINI_MODELS}")
                return _AVAILABLE_GEMINI_MODELS
    except Exception as e:
        logger.warning(f"Errore durante ListModels di Gemini: {e}")

    # Fallback statici moderni
    fallback_static = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    for m in fallback_static:
        if m not in models:
            models.append(m)
    return models


async def call_llm(prompt: str, system_instruction: str = "") -> str:
    """Esegue una chiamata all'LLM (Gemini o OpenAI) tramite HTTP."""
    api_key, provider = get_api_credentials()
    if not api_key:
        raise ValueError(
            "Nessuna API key configurata. Imposta GEMINI_API_KEY o OPENAI_API_KEY in config.py o nelle variabili d'ambiente."
        )

    async with httpx.AsyncClient(timeout=35.0) as client:
        if provider == "gemini":
            configured_model = (
                getattr(config, "GEMINI_MODEL", None)
                or os.environ.get("GEMINI_MODEL")
                or "gemini-3.5-flash-lite"
            )
            candidate_models = await get_available_gemini_models(client, api_key, configured_model)
            if "gemini-3.5-flash-lite" not in candidate_models:
                candidate_models.append("gemini-3.5-flash-lite")

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_instruction}\n\n{prompt}" if system_instruction else prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                }
            }

            last_error = None
            for model_name in candidate_models[:4]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise RuntimeError(f"Gemini non ha restituito risposte: {data}")
                        return candidates[0]["content"]["parts"][0]["text"].strip()
                    elif resp.status_code in (503, 429):
                        last_error = f"Gemini ({model_name}) sovraccarico (HTTP {resp.status_code})."
                        logger.warning(f"Gemini {model_name} HTTP {resp.status_code}, provo subito il modello successivo...")
                        continue
                    else:
                        last_error = f"Errore Gemini API ({resp.status_code}) su {model_name}: {resp.text}"
                        continue
                except Exception as e:
                    last_error = str(e)
                    continue

            raise RuntimeError(last_error or "Tutti i tentativi con i modelli Gemini sono falliti.")

        elif provider == "openai":
            base_url = getattr(config, "OPENAI_BASE_URL", None) or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
            url = f"{base_url.rstrip('/')}/chat/completions"
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            model = getattr(config, "OPENAI_MODEL", None) or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,
            }
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"Errore OpenAI API ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

        else:
            raise ValueError(f"Provider sconosciuto: {provider}")


def clean_sql_output(raw_sql: str) -> str:
    """Rimuove markdown e caratteri extra dalla risposta dell'LLM."""
    sql = raw_sql.strip()
    if sql.startswith("```"):
        lines = sql.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        sql = "\n".join(lines).strip()
    return sql.rstrip(";")


def execute_readonly_sql(db_path: str, sql_query: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    """Esegue una query SQLite in modalità rigorosamente read-only con protezioni di sicurezza."""
    cleaned = clean_sql_output(sql_query)
    if not cleaned:
        raise ValueError("La query generata è vuota.")

    first_word = cleaned.split()[0].upper() if cleaned.split() else ""
    if first_word not in ("SELECT", "WITH"):
        raise ValueError("Sono consentite esclusivamente query SELECT o WITH.")

    # Controllo parole chiave vietate
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "ATTACH", "DETACH", "CREATE", "PRAGMA", "REPLACE"]
    words = [w.upper() for w in re.findall(r"\b[A-Za-z]+\b", cleaned)]
    for f in forbidden:
        if f in words:
            raise ValueError(f"Parola chiave non permessa nella query: '{f}'.")

    # Apertura sicura in modalità read-only
    uri_path = f"file:{os.path.abspath(db_path)}?mode=ro"
    conn = sqlite3.connect(uri_path, uri=True, timeout=5.0)
    try:
        cursor = conn.cursor()
        cursor.execute(cleaned)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(50)
        return columns, rows
    finally:
        conn.close()


async def process_ask_query(db_path: str, user_prompt: str) -> Tuple[str, str]:
    """Flusso a 2 passaggi Text-to-SQL:
    1. Genera SQL da linguaggio naturale.
    2. Esegue query su SQLite locale (read-only).
    3. Converte i risultati in spiegazione discorsiva formattata.
    Ritorna: (risposta_testuale, query_sql_usata)
    """
    # Passo 1: LLM genera query SQL
    gen_sql_prompt = f"Richiesta utente: {user_prompt}\nQuery SQL:"
    raw_sql = await call_llm(gen_sql_prompt, system_instruction=DB_SCHEMA_PROMPT)
    sql_query = clean_sql_output(raw_sql)

    # Passo 2: Esecuzione su SQLite locale
    columns, rows = execute_readonly_sql(db_path, sql_query)

    # Passo 3: LLM formatta la risposta discorsiva per Telegram
    format_prompt = f"""L'utente ha fatto questa domanda sulle statistiche dei giochi:
"{user_prompt}"

La query SQL ha restituito questi risultati dal database:
Colonne: {columns}
Righe (fino a 50): {rows}

Genera una risposta chiara, piacevole e concisa in italiano per Telegram.
Usa formattazione HTML consentita da Telegram (<b>grassetto</b>, <i>corsivo</i>, <code>codice</code>) ed emoji pertinenti.
Se il risultato è vuoto, spiega con gentilezza che non ci sono dati corrispondenti.
"""
    explanation = await call_llm(format_prompt)
    return explanation, sql_query
