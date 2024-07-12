from fastapi import FastAPI
from server.routes import router
from server.langchain_handler import LangchainHandler
import pathlib
import json

import logging.config

def setup_logging():
    config_file = pathlib.Path("log_config.json")
    with open(config_file) as f_in:
        config = json.load(f_in)

    logging.config.dictConfig(config)

setup_logging()
app = FastAPI()

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    LangchainHandler()
    uvicorn.run(app, host="0.0.0.0", port=8000)