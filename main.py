from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "app": "FastAPI 8082 funcionando"}

@app.get("/saludo/{nombre}")
def saludo(nombre: str):
    return {"msg": f"Hola, {nombre}"}
