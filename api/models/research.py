from pydantic import BaseModel


class ResearchRequest(BaseModel):
    query: str


class CitedSentenceResponse(BaseModel):
    sentence: str
    source_url: str


class ResearchResponse(BaseModel):
    thread_id: str                          # use this to retrieve results later
    query: str
    query_complexity: str
    subquestions: list[str]
    summary: str
    sentences: list[CitedSentenceResponse]
    failed_tasks: int                       # count of failed searches
    iteration_count: int
