import logging

import uvicorn

from configurate import load_settings
from web import app


def main():
    settings = load_settings()
    server = settings["server"]
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host=server["host"],
                port=int(server["port"]))


if __name__ == "__main__":
    main()
