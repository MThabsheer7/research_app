import React from 'react';
import { BrainCircuit, MessageCircle, Search, PenTool, CheckCircle2 } from 'lucide-react';
import './ProcessVisualizer.css';

const StepConfig = {
    planner: {
        icon: <BrainCircuit size={20} />,
        title: "Lead Agent",
        desc: "Strategic Planning"
    },
    wait_for_user: {
        icon: <MessageCircle size={20} />,
        title: "Plan Approval",
        desc: "Human-in-the-Loop check"
    },
    context_enhancer: {
        icon: <Search size={20} />,
        title: "Researching",
        desc: "Gathering live web data"
    },
    synthesizer: {
        icon: <PenTool size={20} />,
        title: "Synthesizer",
        desc: "Generating cited report"
    }
};

const STEPS_ORDER = ['planner', 'wait_for_user', 'context_enhancer', 'synthesizer'];

export default function ProcessVisualizer({ activeNode, state, isStreaming }) {

    // Helper to determine status of a step
    const getStepStatus = (stepId) => {
        if (activeNode === 'done') return 'completed';
        const currentIndex = STEPS_ORDER.indexOf(activeNode);
        const stepIndex = STEPS_ORDER.indexOf(stepId);

        if (stepIndex < currentIndex) return 'completed';
        if (stepIndex === currentIndex) return 'active';
        return 'pending';
    };

    return (
        <div className="process-visualizer glass-panel">
            <div className="pv-header">
                <h3>Live Agent Process</h3>
                {isStreaming && <span className="streaming-badge">
                    <span className="pulse-dot"></span> Streaming
                </span>}
            </div>

            <div className="stepper">
                {STEPS_ORDER.map((stepId, index) => {
                    const status = getStepStatus(stepId);
                    const config = StepConfig[stepId];
                    const stepData = state[stepId === 'context_enhancer' ? 'enhancer' : stepId];
                    const isLast = index === STEPS_ORDER.length - 1;

                    return (
                        <div key={stepId} className={`step-item status-${status}`}>
                            <div className="step-indicator-wrapper">
                                <div className="step-icon">
                                    {status === 'completed' ? <CheckCircle2 size={20} /> : config.icon}
                                </div>
                                {!isLast && <div className="step-connector" />}
                            </div>

                            <div className="step-content">
                                <h4 className="step-title">{config.title}</h4>
                                <p className="step-desc">{config.desc}</p>

                                {/* Dynamic live data rendering based on the node */}
                                {stepData && (
                                    <div className="step-data glass-panel-inner">

                                        {stepId === 'planner' && (
                                            <div className="data-col">
                                                <div className="data-row">
                                                    <span className="data-label">Complexity:</span>
                                                    <span className={`badge complexity-${stepData.query_complexity}`}>
                                                        {stepData.query_complexity}
                                                    </span>
                                                </div>
                                                {stepData.subquestions && stepData.subquestions.length > 0 && (
                                                    <div style={{marginTop: '0.5rem'}}>
                                                        <span className="data-label">Formulated Tasks ({stepData.subquestions.length})</span>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {stepId === 'wait_for_user' && (
                                            <div className="data-row">
                                                <span className="data-label">Status:</span>
                                                <span className="emphasis">Awaiting Input...</span>
                                            </div>
                                        )}

                                        {stepId === 'context_enhancer' && stepData.search_results && (
                                            <div className="data-col">
                                                <span className="data-label">Sources Retrieved:</span>
                                                <div className="results-grid">
                                                    {stepData.search_results.map((res, i) => (
                                                        <div key={i} className="search-result-pill" title={res.query}>
                                                            <span>{res.results_count} chunks</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {stepId === 'synthesizer' && stepData.final_report?.sentences && (
                                            <div className="data-row">
                                                <span className="data-label">Sentences drafted:</span>
                                                <span className="emphasis">{stepData.final_report.sentences.length}</span>
                                            </div>
                                        )}

                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
