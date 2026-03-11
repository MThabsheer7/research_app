from pydantic import BaseModel
import operator
from typing_extensions import TypedDict
from typing import Annotated, Optional, List, Literal

# Pydantic Models
class SearchResultModel(BaseModel):
    query: str
    result: List[str]         # top-k text chunks
    source_urls: List[str]    # one URL per chunk (parallel to result list)

class FailedTaskModel(BaseModel):
    query: str
    error: str

class SentenceModel(BaseModel):
    sentence: str
    source_url: str

class ReportModel(BaseModel):
    summary: str
    sentences: List[SentenceModel]

# Top level State Schema
class ResearchState(TypedDict):
    user_input: str
    subquestions: List[str]
    search_results: Annotated[List[SearchResultModel], operator.add]
    failed_tasks: Annotated[List[FailedTaskModel], operator.add]
    final_report: Optional[ReportModel] = None
    iteration_count: int = 0
    planner_iteration_count: int = 0
    query_complexity: Literal["simple", "complex"] = "simple"
    reasoning: str = ""
    
    # Human-in-the-Loop properties
    clarifying_questions: List[str]  # Agent asks the user for more info
    user_feedback: str               # User's response/edits to the plan
    plan_approved: bool              # Whether the user approved the subquestions to execute