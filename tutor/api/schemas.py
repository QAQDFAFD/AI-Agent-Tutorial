from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    message: str = Field(min_length=1, max_length=2000)


class ChapterSummary(BaseModel):
    id: str
    title: str


class ChapterContent(BaseModel):
    id: str
    title: str
    html: str
