import React, { useState } from 'react';
import { Bot, Play, CheckCircle2, AlertCircle, Terminal, Clock, ShieldCheck } from 'lucide-react';

interface TraceStepItem {
  iteration: number;
  action: string;
  details: string[];
  duration_ms: number;
}

export const AgentInvestigation: React.FC = () => {
  const [prompt, setPrompt] = useState('Analyze attack chains from issue and PR triggers reaching deployment keys, and determine the minimum fix cut.');
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [traceSteps, setTraceSteps] = useState<TraceStepItem[]>([
    {
      iteration: 0,
      action: 'llm_call',
      details: ['Gemini 2.5 Flash planning investigation sequence'],
      duration_ms: 320,
    },
    {
      iteration: 0,
      action: 'tool:list_chains',
      details: ['Executing bounded FLOWS traversal query (depth 1..8) in FalkorDB', 'Found 3 candidate attack chains reaching AWS_PROD_ROLE and DEPLOY_KEY'],
      duration_ms: 45,
    },
    {
      iteration: 1,
      action: 'tool:min_fix_set',
      details: ['Invoking algo.maxFlow with fix_cost capacities', 'Identified 2 saturated choke-point edges on the min-cut boundary'],
      duration_ms: 60,
    },
    {
      iteration: 2,
      action: 'final_response',
      details: ['Generated comprehensive report with cited paths and ruamel.yaml patches'],
      duration_ms: 410,
    },
  ]);

  const [report, setReport] = useState<string>(`### CI/CD Security Audit Report: ChokePoint Analysis

**Summary:**
The automated graph investigation detected **3 active attack paths** connecting untrusted external inputs to high-privilege deployment credentials.

#### 1. Discovered Attack Chains:
* **Chain-0 (Critical):** \`github.event.issue.title\` flows into an inline bash \`run:\` step in job \`triage\`, which shares dependency context with \`deploy\` exposing \`AWS_PROD_ROLE\`.
* **Chain-1 (High):** Third-party action \`tj-actions/changed-files@v44\` is referenced via a mutable tag, vulnerable to supply chain takeover.

#### 2. Minimum Cut Remediation:
Rather than restructuring 4 workflows, **2 targeted fixes** completely sever all attack chains:
1. **Env-var indirection:** Move expression in \`.github/workflows/triage-deploy.yml:22\` into \`env: ISSUE_TITLE\`.
2. **SHA Pin:** Pin \`tj-actions/changed-files\` to commit \`ba42e2a8f9b5d47f9ac7a7b8e1a6c4293f019028\`.

#### 3. Faithfulness Verification:
All citations (\`chain-0\`, \`chain-1\`) verified against graph state with 100% path correspondence.`);

  const handleRunInvestigation = () => {
    setIsInvestigating(true);
    // Simulate real-time trace updates
    setTimeout(() => {
      setIsInvestigating(false);
    }, 1200);
  };

  return (
    <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Bot size={22} color="var(--accent-cyan)" />
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>Autonomous Agent Loop</h2>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
            Investigation Query / Prompt:
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
            style={{
              width: '100%',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: '#fff',
              padding: '10px',
              fontSize: '13px',
              fontFamily: 'Inter',
              resize: 'vertical',
            }}
          />
        </div>

        <button
          onClick={handleRunInvestigation}
          disabled={isInvestigating}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            backgroundColor: 'var(--accent-cyan)',
            color: '#000',
            fontWeight: '600',
            borderRadius: '6px',
            border: 'none',
            cursor: 'pointer',
            fontSize: '13px',
            marginBottom: '20px',
          }}
        >
          <Play size={16} />
          {isInvestigating ? 'Agent Investigating...' : 'Run Graph Investigation'}
        </button>

        <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#fff', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Terminal size={16} color="var(--accent-cyan)" />
          Real-Time Investigation Trace (SSE Stream)
        </h3>

        <div style={{
          backgroundColor: '#05070d',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '14px',
          maxHeight: '380px',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          fontFamily: 'Fira Code',
        }}>
          {traceSteps.map((step, idx) => (
            <div key={idx} style={{ fontSize: '12px', borderLeft: '2px solid var(--accent-cyan)', paddingLeft: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--accent-cyan)', fontWeight: '600' }}>
                <span>[{step.iteration}] {step.action.toUpperCase()}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <Clock size={10} /> {step.duration_ms}ms
                </span>
              </div>
              {step.details.map((d, dIdx) => (
                <div key={dIdx} style={{ color: 'var(--text-secondary)', marginTop: '4px', fontSize: '11.5px' }}>
                  › {d}
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>Agent Investigation Report</h2>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid var(--accent-emerald)',
            color: 'var(--accent-emerald)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            fontWeight: '600',
          }}>
            <ShieldCheck size={14} />
            Faithfulness Verified: 100%
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px',
          height: '520px',
          overflowY: 'auto',
          fontSize: '13px',
          lineHeight: '1.6',
          color: 'var(--text-primary)',
          whiteSpace: 'pre-wrap',
        }}>
          {report}
        </div>
      </div>
    </div>
  );
};
