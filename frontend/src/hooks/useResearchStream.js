import { useState, useRef, useCallback } from 'react';

export function useResearchStream() {
    const [isConnecting, setIsConnecting] = useState(false);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState(null);

    // State accumulation
    const [threadId, setThreadId] = useState(null);
    const [plannerState, setPlannerState] = useState(null);
    const [decomposerState, setDecomposerState] = useState(null);
    const [enhancerState, setEnhancerState] = useState(null);
    const [synthesizerState, setSynthesizerState] = useState(null);

    // Active node tracking for UI highlighting
    const [activeNode, setActiveNode] = useState(null);

    const wsRef = useRef(null);

    const startResearch = useCallback((query) => {
        // Reset state
        setError(null);
        setThreadId(null);
        setPlannerState(null);
        setDecomposerState(null);
        setEnhancerState(null);
        setSynthesizerState(null);
        setActiveNode(null);

        setIsConnecting(true);
        setIsStreaming(true);

        // Add error handling if WS connection fails outright
        try {
            // Connect to the FastAPI WebSocket endpoint
            const ws = new WebSocket('ws://localhost:8001/ws/research');
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnecting(false);
                // Send initial query
                ws.send(JSON.stringify({ query }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);

                switch (data.type) {
                    case 'start':
                        setThreadId(data.thread_id);
                        setActiveNode('planner');
                        break;

                    case 'update':
                        const { node, state } = data;
                        setActiveNode(node);

                        // Cumulatively update the state based on node
                        if (node === 'planner') {
                            setPlannerState(state);
                        } else if (node === 'decomposer') {
                            setDecomposerState(state);
                        } else if (node === 'context_enhancer') {
                            // context_enhancer runs multiple times (fan-out), so we merge results
                            setEnhancerState(prevState => {
                                if (!prevState) return state;

                                // Merge search results
                                const newResults = state.search_results || [];
                                const oldResults = prevState.search_results || [];

                                // Ensure unique subquestions
                                const mergedMap = new Map();
                                [...oldResults, ...newResults].forEach(item => {
                                    if (item && item.query) {
                                        mergedMap.set(item.query, item);
                                    }
                                });

                                return {
                                    ...state,
                                    search_results: Array.from(mergedMap.values())
                                };
                            });
                        } else if (node === 'synthesizer') {
                            setSynthesizerState(state);
                        }
                        break;

                    case 'end':
                        setIsStreaming(false);
                        setActiveNode('done');
                        ws.close();
                        break;

                    case 'error':
                        setError(data.message);
                        setIsStreaming(false);
                        setActiveNode(null);
                        ws.close();
                        break;

                    default:
                        console.log("Unknown WS event:", data);
                }
            };

            ws.onerror = (err) => {
                console.error("WebSocket error:", err);
                setError("Connection to research server failed.");
                setIsConnecting(false);
                setIsStreaming(false);
            };

            ws.onclose = () => {
                setIsConnecting(false);
                if (isStreaming) {
                    // If closed unexpectedly while streaming
                    setIsStreaming(false);
                }
            };

        } catch (err) {
            console.error("Failed to establish WS:", err);
            setError(err.message || "Failed to connect to server");
            setIsConnecting(false);
            setIsStreaming(false);
        }
    }, [isStreaming]);

    const cancelResearch = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setIsStreaming(false);
        setActiveNode(null);
    }, []);

    return {
        startResearch,
        cancelResearch,
        isConnecting,
        isStreaming,
        error,
        activeNode,
        threadId,
        state: {
            planner: plannerState,
            decomposer: decomposerState,
            enhancer: enhancerState,
            synthesizer: synthesizerState
        }
    };
}
