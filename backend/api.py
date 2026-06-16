# api.py
from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter(prefix="/api")


@router.get("/status")
def get_status(request: Request):
    """Vrátí aktuální stavy z app.state."""
    # Data taháme z request.app.state
    return {
        "sunrise": str(request.app.state.sunrise),
        "sunset": str(request.app.state.sunset),
        "aktualni_cas": datetime.now().time().strftime('%H:%M:%S')
    }


@router.post("/light/set")
def set_light_manual(request: Request, address: int, output_id: int, value: int):
    """Endpoint pro manuální zapnutí/vypnutí světla z Nuxtu."""
    state = request.app.state

    if not state.sock:
        return {"status": "error", "message": "MTB socket není připojen"}

    try:
        # Voláme funkci přímo z mtb.py (který klidně můžeme importovat)
        from mtb import request_response

        request_response(state.sock, {
            'command': 'module_set_outputs',
            'address': address,
            'outputs': {
                output_id: {'type': 'plain', 'value': value},
            },
        })
        return {"status": "ok", "message": f"Výstup {output_id} na adrese {address} nastaven na {value}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}