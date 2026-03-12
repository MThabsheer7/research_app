import React, { useState } from 'react';
import { useResearchStream } from './hooks/useResearchStream';
import { Search, Loader2, Cpu, Sparkles } from 'lucide-react';
import './App.css';

// Components (We will create these in the next step)
import ProcessVisualizer from './components/ProcessVisualizer';
import ReportView from './components/ReportView';
import PlanApproval from './components/PlanApproval';

function App() {
  const [query, setQuery] = useState('');

  const {
    startResearch,
    cancelResearch,
    sendFeedback,
    isConnecting,
    isStreaming,
    isWaitingForUser,
    interruptData,
    error,
    activeNode,
    threadId,
    state
  } = useResearchStream();

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim() || isStreaming || isConnecting) return;
    startResearch(query.trim());
  };

  const hasStarted = isStreaming || state.planner || error;

  return (
    <>
      <div className="ambient-bg">
        <div className="ambient-orb orb-1"></div>
        <div className="ambient-orb orb-2"></div>
      </div>

      <div className={`app-container ${hasStarted ? 'has-results' : ''}`}>

        <header className="header">
          <div className="logo-container">
            <Cpu size={32} className="logo-icon" />
            <h1 className="logo-text text-gradient">DeepResearch<span style={{ color: 'var(--text-primary)' }}>.ai</span></h1>
          </div>
        </header>

        {!hasStarted && (
          <div className="hero-section">
            <h2 className="hero-title">
              What do you want to <span className="text-gradient">understand?</span>
            </h2>
            <p className="hero-subtitle">
              Ask any complex question. Our multi-agent system will break it down,
              synthesize information from thousands of sources, and give you a perfectly cited report.
            </p>
          </div>
        )}

        <main className={`main-content ${hasStarted ? 'has-results' : ''}`}>

          <form className="search-form glass-panel" style={{ padding: hasStarted ? '1rem' : '2rem', borderRadius: hasStarted ? 'var(--radius-md)' : 'var(--radius-lg)' }} onSubmit={handleSearch}>
            <div className="search-input-wrapper">
              <Search className="search-icon" size={24} />
              <input
                type="text"
                className="glass-input search-input"
                placeholder="e.g. Compare the architecture of Next.js and Remix..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isStreaming || isConnecting}
              />
              <button
                type="submit"
                className="search-button"
                disabled={!query.trim() || isStreaming || isConnecting}
              >
                {(isStreaming || isConnecting) ? (
                  <><Loader2 size={20} className="spinner" /> Synthesizing...</>
                ) : (
                  <><Sparkles size={20} /> Research</>
                )}
              </button>
            </div>

            {error && (
              <div style={{ color: '#ff6b6b', marginTop: '1rem', padding: '1rem', background: 'rgba(255, 0, 0, 0.1)', borderRadius: '8px' }}>
                {error}
              </div>
            )}
          </form>

          {hasStarted && (
            <>
              {/* Left Column: Visualizer */}
              <div className="process-column">
                <ProcessVisualizer
                  activeNode={activeNode}
                  state={state}
                  isStreaming={isStreaming}
                />
              </div>

              {/* Right Column: Generated Report */}
              <div className="report-column">
                <ReportView
                  synthesizerState={state.synthesizer}
                  isStreaming={isStreaming}
                  activeNode={activeNode}
                />
              </div>
            </>
          )}

        </main>
      </div>

      {isWaitingForUser && (
        <PlanApproval 
          data={interruptData} 
          onApproved={(feedback) => {
            sendFeedback(feedback);
          }}
          onFeedback={(feedback) => {
            sendFeedback({ ...feedback, plan_approved: false });
          }}
        />
      )}
    </>
  );
}

export default App;
