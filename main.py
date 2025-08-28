from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3, os, datetime

# --- Paths / DB ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "bots.db")

app = FastAPI(title="Activador Bots Trading", version="0.1.0")


# --- Helpers ---
def _now_iso() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS bots(
                id INTEGER PRIMARY KEY,
                is_on INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
        """)
        con.commit()

def get_bot(bot_id: int) -> Optional[tuple]:
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id, is_on, updated_at FROM bots WHERE id=?", (bot_id,))
        return cur.fetchone()

def set_bot_state(bot_id: int, is_on: bool) -> dict:
    ts = _now_iso()
    with sqlite3.connect(DB_PATH) as con:
        if get_bot(bot_id) is None:
            con.execute(
                "INSERT INTO bots(id, is_on, updated_at) VALUES(?,?,?)",
                (bot_id, 1 if is_on else 0, ts),
            )
        else:
            con.execute(
                "UPDATE bots SET is_on=?, updated_at=? WHERE id=?",
                (1 if is_on else 0, ts, bot_id),
            )
        con.commit()
    return {"idBot": bot_id, "is_on": is_on, "updated_at": ts}

def toggle_bot(bot_id: int) -> dict:
    row = get_bot(bot_id)
    if row is None:
        # Si no existe, lo registramos apagado y luego togglamos => quedará encendido
        set_bot_state(bot_id, False)
        row = get_bot(bot_id)
    _, is_on, _ = row
    new_state = not bool(is_on)
    result = set_bot_state(bot_id, new_state)
    result["toggled_from"] = bool(is_on)
    return result


# --- Schemas ---
class SetStateBody(BaseModel):
    is_on: bool

class BotOut(BaseModel):
    idBot: int
    is_on: bool
    updated_at: str


# --- FastAPI lifecycle ---
@app.on_event("startup")
def on_startup():
    init_db()


# --- Endpoints ---
@app.get("/bots/{bot_id}", response_model=BotOut)
def read_bot(bot_id: int):
    row = get_bot(bot_id)
    if row is None:
        data = set_bot_state(bot_id, False)
    else:
        data = {"idBot": row[0], "is_on": bool(row[1]), "updated_at": row[2]}
    return data

@app.get("/bots", response_model=List[BotOut])
def list_bots():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id, is_on, updated_at FROM bots ORDER BY id")
        items = [{"idBot": r[0], "is_on": bool(r[1]), "updated_at": r[2]} for r in cur.fetchall()]
    return items

@app.post("/bots/{bot_id}/toggle")
def toggle_endpoint(bot_id: int):
    """
    Cambia el estado actual del bot:
    - Si estaba encendido -> lo apaga
    - Si estaba apagado  -> lo enciende
    Persiste el estado en SQLite.
    """
    return toggle_bot(bot_id)

@app.put("/bots/{bot_id}", response_model=BotOut)
def set_state(bot_id: int, body: SetStateBody):
    """
    Fija explícitamente el estado del bot (true/false).
    """
    return set_bot_state(bot_id, body.is_on)


# --- Dev runner (útil en VS Code) ---
if __name__ == "__main__":
    import uvicorn
    # Cambia host/port si lo necesitas para pruebas locales
    uvicorn.run("main:app", host="0.0.0.0", port=8082, reload=True)