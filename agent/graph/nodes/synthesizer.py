from agent.graph.state import ResearchState, ReportModel, SentenceModel
from agent.llm_client import llm
from pydantic import BaseModel
from typing import List
import time

MAX_ITERATIONS = 5


# ── Output schemas ────────────────────────────────────────────────────────────

class CitedSentence(BaseModel):
    sentence: str
    ref: int          # must match a [N] from the injected context block

class SynthesizerOutput(BaseModel):
    summary: str
    sentences: List[CitedSentence]


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a research synthesis assistant.

Your task is to produce a clear, factual research report that answers the user's query by synthesizing the provided context.

The context contains information gathered from multiple subquestions. Each piece of information is associated with a numbered citation like [1], [2], [3], etc.

You must strictly follow the citation rules below.

IMPORTANT CITATION RULES:

* Only cite references that appear in the provided context.
* Do NOT invent or hallucinate citation numbers.
* Each sentence must contain exactly ONE citation.
* A citation must appear at the end of the sentence.
* Use the format: [N]
* Do not include multiple citations in a sentence.
* Do not write sentences without citations.

GROUNDING RULES:

* Only use information present in the provided context.
* Do not add outside knowledge.
* If the context does not contain enough information to fully answer something, simply summarize what is available.

WRITING GUIDELINES:

* Write a coherent research-style report.
* Combine information from different subquestions where appropriate.
* Avoid repeating the same facts.
* Maintain a clear logical flow between sentences.
* Prefer concise and precise sentences.

OUTPUT FIELDS:

"summary" — A 1-2 sentence paragraph written FOR THE READER that gives a high-level overview of the TOPIC (not a description of your task or process). Write it as a human expert would open a research report.
Example good summary: "AlphaFold is a deep learning system by DeepMind that predicts 3D protein structures from amino acid sequences, representing a landmark advance in structural biology."
Example bad summary:  "The user is asking about AlphaFold and I need to synthesize the context into a report with citations."

"sentences" — The full body of the report as individual cited sentences, each grounded in the provided context with exactly one [N] reference.

REPORT STRUCTURE:

1. "summary": high-level overview of the topic addressed by the query.
2. "sentences": key findings, explanations, comparisons, then limitations.

CONTEXT FORMAT EXAMPLE:

Subquestion: What is AlphaFold?
[1] AlphaFold is a protein structure prediction system developed by DeepMind.
[2] It predicts 3D protein structures from amino acid sequences using deep learning.

Subquestion: What are AlphaFold's limitations?
[3] AlphaFold struggles with predicting protein complexes and dynamic structures.

Your output should be a research report where each sentence contains exactly one citation.

Example output:

AlphaFold is a protein structure prediction system developed to estimate the three-dimensional structure of proteins from their amino acid sequences. [1]

The system relies on deep learning methods to infer spatial relationships within protein chains. [2]

Despite its high accuracy, AlphaFold has limitations when predicting protein complexes and dynamic molecular interactions. [3]
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_citation_map_and_context(search_results) -> tuple[dict[int, str], str]:
    """
    Builds:
      citation_map  {1: url, 2: url, ...}  for post-processing ref -> URL
      context_block  formatted string grouped by subquestion for the prompt
    """
    citation_map: dict[int, str] = {}
    lines: list[str] = []
    ref = 1

    for sr in search_results:
        lines.append(f"Subquestion: {sr.query}")
        for chunk, url in zip(sr.result, sr.source_urls):
            citation_map[ref] = url
            lines.append(f"[{ref}] {chunk}")
            ref += 1
        lines.append("")    # blank line between subquestions

    return citation_map, "\n".join(lines)


# ── Node ──────────────────────────────────────────────────────────────────────

def synthesizer_node(state: ResearchState) -> dict:
    search_results = state["search_results"]

    # Simple query path — no search results, we answer directly from LLM knowledge
    if not search_results:
        answer = llm.generate_text(
            messages=[
                {"role": "system", "content": "You are an expert AI assistant. Please provide a clear, direct, and comprehensive answer to the user's query."},
                {"role": "user", "content": state["user_input"]}
            ],
            max_tokens=1024,
        )
        return {
            "final_report": ReportModel(
                summary=answer,
                sentences=[]
            ),
            "iteration_count": state["iteration_count"] + 1,
        }

    citation_map, context_block = _build_citation_map_and_context(search_results)

    user_content = (
        f"User Query: {state['user_input']}\n\n"
        f"Context:\n{context_block}"
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = llm.generate_structured(
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format=SynthesizerOutput,
                max_tokens=1800,
            )
            break
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)



    # Map ref indices -> real URLs; fall back to "" on hallucinated refs
    sentences = [
        SentenceModel(
            sentence=cs.sentence,
            source_url=citation_map.get(cs.ref, ""),
        )
        for cs in result.sentences
    ]

    return {
        "final_report": ReportModel(summary=result.summary, sentences=sentences),
        "iteration_count": state["iteration_count"] + 1,
    }


# ── Routing ────────────────────────────────────────────────────────────────────

def route_synthesizer(state: ResearchState) -> str:
    # Always stop if we've hit the iteration cap
    if state["iteration_count"] >= MAX_ITERATIONS:
        return "done"
    # Simple query path -- no subquestions, nothing to retry
    if not state["subquestions"]:
        return "done"
    # Complex query -- only retry if we had enough successful searches
    successful = len(state["subquestions"]) - len(state["failed_tasks"])
    if successful < 3:
        return "retry"
    return "done"