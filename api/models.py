from pydantic import BaseModel


class Section(BaseModel):
    heading: str
    text: str


class ExtractionResponse(BaseModel):
    file_name: str
    file_text: list[Section]
