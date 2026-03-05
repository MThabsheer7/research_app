import json
import uuid
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from api.services.agent_client import stream_research

router = APIRouter()

@router.websocket("/ws/research")
async def websocket_research(websocket: WebSocket):
    """
    WebSocket endpoint for real-time research streaming.
    Client sends a JSON message: {"query": "Some topic"}
    Server streams back state updates as they happen in LangGraph.
    """
    await websocket.accept()
    
    try:
        # Wait for the initial message from the client
        data = await websocket.receive_text()
        request = json.loads(data)
        query = request.get("query")
        
        if not query:
            await websocket.send_json({"error": "Query is required"})
            await websocket.close()
            return
            
        thread_id = str(uuid.uuid4())
        await websocket.send_json({"type": "start", "thread_id": thread_id, "query": query})
        
        # Stream updates from the agent
        async for step in stream_research(query, thread_id):
            # step is a dict like {'planner': {'query_complexity': 'complex', ...}}
            for node_name, state_update in step.items():
                
                # We format the payload to send over WS
                payload = {
                    "type": "update",
                    "node": node_name,
                    "state": _sanitize_state(state_update)
                }
                await websocket.send_json(payload)
                
        await websocket.send_json({"type": "end", "thread_id": thread_id})
        await websocket.close()
        
    except WebSocketDisconnect:
        # Client disconnected early, perfectly fine
        pass
    except Exception as e:
        # If there's a problem, send an error event before closing
        try:
            await websocket.send_json({"type": "error", "message": f"Agent error: {str(e)}"})
            await websocket.close()
        except Exception:
            pass


def _sanitize_state(state_update: dict) -> dict:
    """
    Convert internal pydantic models or complex objects into valid JSON dicts
    for transmission over the WebSocket.
    """
    sanitized = {}
    
    for key, value in state_update.items():
        if key == "final_report" and value is not None:
            # value is a ReportModel instance
            sanitized[key] = {
                "summary": value.summary,
                "sentences": [
                    {"sentence": s.sentence, "source_url": s.source_url} 
                    for s in value.sentences
                ]
            }
        elif key == "search_results":
            # list of SearchResultModel
            sanitized[key] = [
                {
                    "query": r.query, 
                    "results_count": len(r.result), 
                    "top_url": r.source_urls[0] if r.source_urls else None
                } 
                for r in value
            ]
        elif key == "failed_tasks":
            # list of FailedTaskModel
            sanitized[key] = [
                {"query": f.query, "error": f.error} 
                for f in value
            ]
        else:
            # Everything else (strings, lists of strings) is json serializable
            sanitized[key] = value
            
    return sanitized
