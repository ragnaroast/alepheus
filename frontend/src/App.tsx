import React, { useState } from 'react';
import { Header } from './components/Header';
import { AttackChainsCanvas } from './components/AttackChainsCanvas';
import { MinCutPanel } from './components/MinCutPanel';
import { AgentInvestigation } from './components/AgentInvestigation';
import { PatchViewer } from './components/PatchViewer';
import { IncidentMode } from './components/IncidentMode';
import { PRGateDiff } from './components/PRGateDiff';
import { CorpusAnalytics } from './components/CorpusAnalytics';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('chains');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        status="healthy"
      />

      <main style={{ flex: 1 }}>
        {activeTab === 'chains' && <AttackChainsCanvas />}
        {activeTab === 'mincut' && <MinCutPanel />}
        {activeTab === 'agent' && <AgentInvestigation />}
        {activeTab === 'patch' && <PatchViewer />}
        {activeTab === 'incident' && <IncidentMode />}
        {activeTab === 'gate' && <PRGateDiff />}
        {activeTab === 'corpus' && <CorpusAnalytics />}
      </main>

      <footer style={{
        padding: '12px 24px',
        borderTop: '1px solid var(--border-color)',
        backgroundColor: 'var(--bg-secondary)',
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '11px',
        color: 'var(--text-muted)',
      }}>
        <div>
          ChokePoint — Graph-based CI/CD attack-path analysis and minimum-cut remediation
        </div>
        <div>
          FalkorDB • Google Gemini 2.5 Flash • FastMCP • ruamel.yaml
        </div>
      </footer>
    </div>
  );
};

export default App;
