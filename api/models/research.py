from pydantic import BaseModel
from typing import Optional


class ResearchRequest(BaseModel):
    query: str


class CitedSentenceResponse(BaseModel):
    sentence: str
    source_url: str


class ResearchResponse(BaseModel):
    query: str
    query_complexity: str
    subquestions: list[str]
    summary: str
    sentences: list[CitedSentenceResponse]
    failed_tasks: int          # count of failed searches
    iteration_count: int
