import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from configurate import SUPPORTED_ALGORITHMS, load_settings
from service import LightingService


class UpdateRequest(BaseModel):
    item_id: int
    new_algorithm: str


def create_app(settings=None):
    settings = settings if settings is not None else load_settings()

    @asynccontextmanager
    async def lifespan(app):
        service = LightingService(settings)
        app.state.service = service
        await service.start()
        try:
            yield
        finally:
            await service.stop()

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(
        # Browsers still require these headers when frontend/backend use different ports.
        CORSMiddleware, allow_origins=["*"],
        allow_credentials=False, allow_methods=["*"], allow_headers=["*"],
    )

    @app.get("/api/structure")
    async def get_structure(request: Request):
        return request.app.state.service.manager.tree_data

    @app.post("/api/algorithm", status_code=202)
    async def update_algorithm(req: UpdateRequest, request: Request):
        service = request.app.state.service
        if req.new_algorithm not in SUPPORTED_ALGORITHMS:
            raise HTTPException(422, "Neznámý algoritmus.")
        if not service.manager.change_algorithm(req.item_id, req.new_algorithm):
            raise HTTPException(404, "Prvek neexistuje.")
        service.recalculate()
        # Accepted into desired state; TCP acknowledgement arrives independently.
        return {"success": True, "updated_id": req.item_id, "algorithm": req.new_algorithm}

    @app.websocket("/api/ws")
    async def state_socket(websocket: WebSocket):
        await websocket.accept()
        service = websocket.app.state.service
        queue = service.subscribe()

        async def send_updates():
            while True:
                snapshot = await queue.get()
                await asyncio.wait_for(websocket.send_text(snapshot), 10)

        async def receive_until_closed():
            while True:
                await websocket.receive_text()

        tasks = [asyncio.create_task(send_updates()),
                 asyncio.create_task(receive_until_closed())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (WebSocketDisconnect, OSError, TimeoutError, RuntimeError):
            pass
        finally:
            service.subscribers.discard(queue)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await websocket.close()
            except (RuntimeError, OSError):
                pass

    return app


app = create_app()
