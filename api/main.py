import argparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .first100 import First100Set, ValidationError

app = FastAPI(title="First 100 Set API", version="1.0.0")

# instancia simple en memoria
state = First100Set()

class ExtractRequest(BaseModel):
    number: int = Field(..., ge=1, le=100, description="Número a extraer (1..100)")

class MissingResponse(BaseModel):
    missing: int

@app.post("/extract", summary="Extrae un número del conjunto 1..100")
def extract_number(payload: ExtractRequest):
    global state
    try:
        state.extract(payload.number)
        return {"status": "ok", "extracted": payload.number}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/missing", response_model=MissingResponse, summary="Calcula el número faltante")
def get_missing():
    global state
    try:
        return MissingResponse(missing=state.missing_by_sum())
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/reset", summary="Reinicia el conjunto (utilidad)")
def reset():
    global state
    state = First100Set()
    return {"status": "ok"}

def run_cli():
    """
    Ejecucion por argumento del usuario:
    python -m api.main --extract 57
    """
    parser = argparse.ArgumentParser(description="First100Set CLI")
    parser.add_argument("--extract", type=int, required=True, help="Número a extraer (1..100)")
    args = parser.parse_args()

    s = First100Set()
    try:
        s.extract(args.extract)
        print(f"Número extraído: {args.extract}")
        print(f"Número faltante calculado: {s.missing_by_sum()}")
    except ValidationError as e:
        print(f"Error: {e}")
        raise SystemExit(1)

if __name__ == "__main__":
    run_cli()