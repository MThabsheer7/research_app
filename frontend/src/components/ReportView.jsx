import React from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, Loader2 } from 'lucide-react';
import './ReportView.css';

export default function ReportView({ synthesizerState, isStreaming, activeNode }) {

    if (!synthesizerState && activeNode !== 'done' && isStreaming) {
        return (
            <div className="report-view glass-panel loading-state">
                <Loader2 className="spinner" size={32} />
                <p>Agents are researching and drafting...</p>
                <span className="subtext">The final report will appear here.</span>
            </div>
        );
    }

    const report = synthesizerState?.final_report;
    if (!report) return null;

    return (
        <div className="report-view glass-panel">
            <div className="report-header">
                <div className="report-title-row">
                    <FileText className="report-icon" size={24} />
                    <h2>Synthesized Intel</h2>
                </div>
                {!isStreaming && <div className="badge success-badge">Complete</div>}
                {isStreaming && activeNode === 'synthesizer' && (
                    <div className="badge drafting-badge">Drafting...</div>
                )}
            </div>

            <div className="report-content markdown-body">
                {/* Summary - safe to use ReactMarkdown since it's just text */}
                {report.summary && (
                    <div className="summary-section">
                        <h3>Executive Summary</h3>
                        <ReactMarkdown>{report.summary}</ReactMarkdown>
                        <hr />
                    </div>
                )}

                {/* Findings: render as plain JSX so <sup> citations render as real HTML */}
                {report.sentences && report.sentences.length > 0 && (
                    <div className="findings-section">
                        <h3>Findings</h3>
                        {report.sentences.map((s, i) => (
                            <p key={i} className="finding-sentence">
                                {s.sentence}
                                {s.source_url && (
                                    <sup>
                                        <a
                                            href={s.source_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            title={s.source_url}
                                        >
                                            source
                                        </a>
                                    </sup>
                                )}
                            </p>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
