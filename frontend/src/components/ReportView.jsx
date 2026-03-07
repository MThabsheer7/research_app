import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import { FileText, ExternalLink, Loader2 } from 'lucide-react';
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

    // Once synthesizer has state, compile the markdown
    const report = synthesizerState?.final_report;

    if (!report) return null;

    // We construct final markdown representation from the chunks and summary
    const markdownText = useMemo(() => {
        let md = '';

        // Add summary if it exists
        if (report.summary) {
            md += `### Executive Summary\n\n${report.summary}\n\n---\n\n`;
        }

        // Add sentences
        if (report.sentences && report.sentences.length > 0) {
            md += `### Findings\n\n`;
            report.sentences.forEach(s => {
                // Find if this sentence has a citation
                if (s.source_url) {
                    // Check if markdown link already exists in the sentence
                    if (s.sentence.includes('](')) {
                        md += `${s.sentence}\n\n`;
                    } else {
                        md += `${s.sentence} <sup>[source](${s.source_url})</sup>\n\n`;
                    }
                } else {
                    md += `${s.sentence}\n\n`;
                }
            });
        }

        return md;
    }, [report]);

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
                {markdownText ? (
                    <ReactMarkdown
                        components={{
                            a: ({ node, ...props }) => (
                                <a target="_blank" rel="noopener noreferrer" {...props}>
                                    {props.children}
                                    {props.children === 'source' ? null : <ExternalLink size={12} className="inline-icon" />}
                                </a>
                            )
                        }}
                    >
                        {markdownText}
                    </ReactMarkdown>
                ) : (
                    <p className="placeholder-text">Drafting in progress...</p>
                )}
            </div>
        </div>
    );
}
