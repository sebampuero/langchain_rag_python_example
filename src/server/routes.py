from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from models.PromptInput import PromptInput
from server.langchain_handler import LangchainHandler
import time
import logging

router = APIRouter()
logger = logging.getLogger("Langchain")


@router.post("/prompt", response_class=StreamingResponse, responses={
    200: {"description": "Successful Response"},
    400: {"description": "Bad Request"},
    500: {"description": "Internal Server Error"}
})
async def post_prompt(body: PromptInput):
    logger.debug(f"Received: {body}")
    input = body.input
    session_id = body.session_id
    try:
        async_iterator = await LangchainHandler().prompt(input, session_id)
        message_id = int(time.time() * 1000)
        logger.debug(f"Generated {message_id} for {async_iterator}")
        async def generate_stream():
            async for item in async_iterator:
                if 'answer' in item:
                    yield JSONResponse(content={
                        'type': 'chunk',
                        'id': str(message_id),
                        'content': item['answer']
                    }).body + b'\n'
            yield JSONResponse(content={
                'type': 'end',
                'id': str(message_id),
                'content': ''
            }).body + b'\n'

        return StreamingResponse(generate_stream(), media_type="application/json")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))