import logging

import uvicorn

from connection_config import ServerConfig
from configurate import load_settings
from web import app


def main():
    settings = load_settings()
    server = ServerConfig.from_mapping(settings["server"])
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=server.host, port=server.port)


if __name__ == "__main__":
    main()
