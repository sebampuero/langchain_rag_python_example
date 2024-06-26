from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.PromptInput import PromptInput
from server.langchain_handler import LangchainHandler


router = APIRouter()


@router.post("/prompt", response_class=StreamingResponse, responses={
    200: {"description": "Successful Response"},
    400: {"description": "Bad Request"},
    500: {"description": "Internal Server Error"}
})
async def post_prompt(body: PromptInput):
    input = body.input
    session_id = body.session_id
    try:
        async_iterator = await LangchainHandler().prompt(input, session_id)
        async def generate_stream():
            async for item in async_iterator:
                if 'answer' in item:
                    yield item['answer']
        return StreamingResponse(generate_stream(), media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))