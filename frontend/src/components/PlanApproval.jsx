import React, { useState, useEffect } from 'react';
import { Check, Edit3, MessageSquare, Plus, Trash2, Send, Zap } from 'lucide-react';
import './PlanApproval.css';

const PlanApproval = ({ data, onApproved, onFeedback }) => {
  const [subquestions, setSubquestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [isEditing, setIsEditing] = useState(false);
  const [newQuestion, setNewQuestion] = useState('');

  const clarifyingQuestions = data?.clarifying_questions || [];
  const initialSubquestions = data?.subquestions || [];

  useEffect(() => {
    setSubquestions(initialSubquestions);
  }, [initialSubquestions]);

  const handleTogglePlan = (index, value) => {
    const updated = [...subquestions];
    updated[index] = value;
    setSubquestions(updated);
  };

  const removeSubquestion = (index) => {
    setSubquestions(subquestions.filter((_, i) => i !== index));
  };

  const addSubquestion = () => {
    if (newQuestion.trim()) {
      setSubquestions([...subquestions, newQuestion.trim()]);
      setNewQuestion('');
    }
  };

  const handleAnswerChange = (q, val) => {
    setAnswers(prev => ({ ...prev, [q]: val }));
  };

  const handleSubmitSimple = () => {
    // Collect answers as feedback
    const feedbackParts = Object.entries(answers)
      .filter(([_, val]) => val.trim())
      .map(([q, val]) => `Answer to "${q}": ${val}`);
    
    const feedback = feedbackParts.join('\n');

    onApproved({
      plan_approved: true,
      user_feedback: feedback,
      subquestions: subquestions
    });
  };

  const handleRequestChanges = () => {
    // Construct feedback string from the answers and state
    const feedbackParts = Object.entries(answers)
      .filter(([_, val]) => val.trim())
      .map(([q, val]) => `Answer to "${q}": ${val}`);
    
    onApproved({
      plan_approved: false,
      user_feedback: feedbackParts.join('\n'),
      subquestions: subquestions
    });
  };

  return (
    <div className="plan-approval-overlay">
      <div className="plan-approval-modal glass-panel">
        <header className="modal-header">
          <div className="icon-badge">
            <Zap size={24} className="zap-icon" />
          </div>
          <div>
            <h2 className="modal-title">Research Action Plan</h2>
            <p className="modal-subtitle">The lead agent has proposed a plan. Review and refine it below.</p>
          </div>
        </header>

        <div className="modal-body custom-scrollbar">
          {clarifyingQuestions.length > 0 && (
            <section className="modal-section scroll-reveal">
              <h3 className="section-title">
                <MessageSquare size={18} /> Clarifying Questions
              </h3>
              <div className="questions-list">
                {clarifyingQuestions.map((q, i) => (
                  <div key={i} className="question-item glass-input">
                    <p className="question-text">{q}</p>
                    <textarea
                      placeholder="Your answer..."
                      className="answer-input"
                      value={answers[q] || ''}
                      onChange={(e) => handleAnswerChange(q, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            </section>
          )}

          <section className="modal-section scroll-reveal">
            <div className="section-header">
              <h3 className="section-title">
                <Edit3 size={18} /> Research Sub-tasks
              </h3>
              <button 
                className={`edit-toggle ${isEditing ? 'active' : ''}`}
                onClick={() => setIsEditing(!isEditing)}
              >
                {isEditing ? 'Done Editing' : 'Customize Plan'}
              </button>
            </div>
            
            <div className="subquestions-list">
              {subquestions.map((q, i) => (
                <div key={i} className={`subquestion-card ${isEditing ? 'editable' : ''}`}>
                  <div className="card-index">{i + 1}</div>
                  {isEditing ? (
                    <input 
                      type="text" 
                      value={q} 
                      onChange={(e) => handleTogglePlan(i, e.target.value)}
                      className="inline-input"
                    />
                  ) : (
                    <p className="card-text">{q}</p>
                  )}
                  {isEditing && (
                    <button className="remove-btn" onClick={() => removeSubquestion(i)}>
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              ))}
              
              {isEditing && (
                <div className="add-question-wrapper">
                  <input 
                    type="text" 
                    placeholder="Add custom research task..." 
                    value={newQuestion}
                    onChange={(e) => setNewQuestion(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addSubquestion()}
                  />
                  <button onClick={addSubquestion} className="add-btn">
                    <Plus size={18} />
                  </button>
                </div>
              )}
            </div>
          </section>
        </div>

        <footer className="modal-footer">
          <div className="actions">
            <button className="btn-secondary" onClick={handleRequestChanges}>
              Request Changes
            </button>
            <button className="btn-primary" onClick={handleSubmitSimple}>
              <Check size={18} /> Approve & Start Research
            </button>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default PlanApproval;
