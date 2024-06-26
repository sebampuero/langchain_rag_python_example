from pydantic import BaseModel

class PromptInput(BaseModel):
    input: str
    session_id: str