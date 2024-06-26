from fastapi import FastAPI
from server.routes import router
from server.langchain_handler import LangchainHandler

app = FastAPI()

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    LangchainHandler()
    uvicorn.run(app, host="127.0.0.1", port=8000)