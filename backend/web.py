from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Nastavení CORS pro povolení komunikace s frontendem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/structure")
def get_structure(request: Request):
    # Přes request.app.state přistoupíme ke správci, kterého nám sem dodá main.py
    manager = request.app.state.manager

    # Vracíme proměnnou tree_data, kterou si správce drží ve své paměti
    return manager.tree_data


class UpdateRequest(BaseModel):
    item_id: int
    new_algorithm: str


@app.post("/api/algorithm")
def update_algorithm(req: UpdateRequest, request: Request):
    manager = request.app.state.manager
    daemon = getattr(request.app.state, 'daemon', None)
    sunrise = getattr(request.app.state, 'sunrise', "05:00")
    sunset = getattr(request.app.state, 'sunset', "21:00")

    # Zápis nového algoritmu do vnitřní paměti
    success = manager.change_algorithm(req.item_id, req.new_algorithm)

    # OPRAVA: Metodu pro aktualizaci voláme VŽDY.
    # Tím se uvnitř vypočítá proměnná 'is_on', díky které se obarví web.
    # O neodeslání dat do odpojeného hardwaru se postará úprava z kroku 1.
    if success:
        manager.update_hardware(daemon, sunrise, sunset)

    return {"success": success, "updated_id": req.item_id, "algorithm": req.new_algorithm}