import logging

import uvicorn

from configurate import load_settings
from web import app


def main():
    settings = load_settings()
    server = settings.get("server", {})
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=server.get("host", "0.0.0.0"),
                port=int(server.get("port", 8000)))


if __name__ == "__main__":
    main()
