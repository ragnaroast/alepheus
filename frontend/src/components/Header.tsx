import React from 'react';
import { ShieldAlert, Cpu, Database, Activity, GitBranch } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  status: string;
}

export const Header: React.FC<HeaderProps> = ({ activeTab, setActiveTab, status }) => {
  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '16px 24px',
      borderBottom: '1px solid var(--border-color)',
      backgroundColor: 'var(--bg-secondary)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: '8px',
          backgroundColor: 'rgba(6, 182, 212, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid var(--accent-cyan)',
        }}>
          <ShieldAlert size={22} color="var(--accent-cyan)" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h1 style={{ fontSize: '18px', fontWeight: '700', letterSpacing: '-0.02em', color: '#fff' }}>
              CHOKEPOINT
            </h1>
            <span style={{
              fontSize: '11px',
              fontWeight: '600',
              padding: '2px 6px',
              borderRadius: '4px',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              color: 'var(--accent-emerald)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
            }}>
              FalkorDB Powered
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            CI/CD Attack-Path Agent & Minimum-Cut Remediation Engine
          </p>
        </div>
      </div>

      <nav style={{ display: 'flex', gap: '8px' }}>
        {[
          { id: 'chains', label: 'Attack Chains' },
          { id: 'mincut', label: 'Minimum Fix Set' },
          { id: 'agent', label: 'AI Investigation' },
          { id: 'patch', label: 'Verified Patches' },
          { id: 'incident', label: 'Incident Mode' },
          { id: 'gate', label: 'PR Gate Diff' },
          { id: 'corpus', label: 'Ecosystem Insights' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '8px 14px',
              fontSize: '13px',
              fontWeight: activeTab === tab.id ? '600' : '500',
              borderRadius: '6px',
              border: activeTab === tab.id ? '1px solid var(--accent-cyan)' : '1px solid transparent',
              backgroundColor: activeTab === tab.id ? 'rgba(6, 182, 212, 0.12)' : 'transparent',
              color: activeTab === tab.id ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <Cpu size={14} color="var(--accent-cyan)" />
          <span>Gemini 2.5 Flash</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--accent-emerald)' }}>
          <Activity size={14} />
          <span>Online</span>
        </div>
      </div>
    </header>
  );
};
