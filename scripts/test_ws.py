import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8001/ws/research"
    async with websockets.connect(uri) as websocket:
        
        # Send query
        query = {"query": "What are the core differences between React and Vue?"}
        print(f"Sending query: {query}")
        await websocket.send(json.dumps(query))
        
        # Listen for updates
        while True:
            try:
                response_str = await websocket.recv()
                response = json.loads(response_str)
                
                msg_type = response.get("type")
                
                if msg_type == "start":
                    print(f"\\nStarted thread: {response.get('thread_id')}\\n")
                elif msg_type == "update":
                    node = response.get("node")
                    print(f"[{node.upper()}] Update:")
                    state = response.get("state", {})
                    
                    if node == "planner":
                        print(f"  Complexity: {state.get('query_complexity')}")
                    elif node == "decomposer":
                        print(f"  Subquestions: {len(state.get('subquestions', []))}")
                    elif node == "context_enhancer":
                        if "search_results" in state:
                            print(f"  Fetched {len(state['search_results'][0].get('results_count', 0) * 'x')} chunks")
                    elif node == "synthesizer":
                        report = state.get("final_report", {})
                        print(f"  Sentences generated: {len(report.get('sentences', []))}")
                        
                elif msg_type == "end":
                    print("\\nStream ended naturally.")
                    break
                elif msg_type == "error":
                    print(f"\\nError: {response.get('message')}")
                    break
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by server.")
                break

if __name__ == "__main__":
    asyncio.run(test_websocket())
