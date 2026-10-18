import React from 'react';
import { Globe, BarChart3, ShieldCheck, AlertTriangle } from 'lucide-react';

export const CorpusAnalytics: React.FC = () => {
  const topActions = [
    { rank: 1, slug: 'actions/checkout', usages: 248, unpinned: '32.4%', repos: 248, risk: 'High Centrality Hub' },
    { rank: 2, slug: 'actions/setup-node', usages: 142, unpinned: '41.5%', repos: 139, risk: 'High Centrality Hub' },
    { rank: 3, slug: 'tj-actions/changed-files', usages: 68, unpinned: '58.8%', repos: 65, risk: 'Critical Blast Choke Point' },
    { rank: 4, slug: 'docker/build-push-action', usages: 54, unpinned: '44.4%', repos: 52, risk: 'Registry Token Access' },
    { rank: 5, slug: 'actions/upload-artifact', usages: 88, unpinned: '28.4%', repos: 82, risk: 'Poison Flow Conduit' },
    { rank: 6, slug: 'codecov/codecov-action', usages: 42, unpinned: '62.0%', repos: 40, risk: 'Exfiltration Exposure' },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Globe size={20} color="var(--accent-cyan)" />
            Ecosystem Corpus Choke-Point Insights
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Aggregated graph metrics across 250+ scanned repositories. Identifies systemic supply chain choke points without naming individual repositories.
          </p>
        </div>

        <div style={{
          padding: '6px 12px',
          borderRadius: '6px',
          backgroundColor: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid var(--accent-emerald)',
          color: 'var(--accent-emerald)',
          fontSize: '11px',
          fontWeight: '600',
        }}>
          Privacy-Preserving Aggregate Only
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>REPOSITORIES ANALYZED</div>
          <div style={{ fontSize: '22px', fontWeight: '700', color: '#fff', marginTop: '4px' }}>250</div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Ecosystem sample</div>
        </div>

        <div style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>ACTION INVOCATIONS</div>
          <div style={{ fontSize: '22px', fontWeight: '700', color: '#fff', marginTop: '4px' }}>736</div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Graph edge count</div>
        </div>

        <div style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>AVG UNPINNED RATIO</div>
          <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--accent-amber)', marginTop: '4px' }}>43.8%</div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Mutable tag references</div>
        </div>

        <div style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SECRETS IN BLAST SCOPE</div>
          <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--accent-crimson)', marginTop: '4px' }}>412</div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Deploy/cloud tokens</div>
        </div>
      </div>

      <div style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        overflow: 'hidden',
      }}>
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border-color)' }}>
          <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>
            Top Ecosystem Choke Points Ranked by Action Centrality
          </h3>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--bg-tertiary)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '10px 16px' }}>Rank</th>
              <th style={{ padding: '10px 16px' }}>Third-Party Action</th>
              <th style={{ padding: '10px 16px' }}>Corpus Usages</th>
              <th style={{ padding: '10px 16px' }}>Unpinned %</th>
              <th style={{ padding: '10px 16px' }}>Repos Exposed</th>
              <th style={{ padding: '10px 16px' }}>Ecosystem Risk Assessment</th>
            </tr>
          </thead>
          <tbody>
            {topActions.map((action) => (
              <tr key={action.rank} style={{ borderBottom: '1px solid var(--border-color)' }}>
                <td style={{ padding: '12px 16px', color: 'var(--accent-cyan)', fontWeight: '600' }}>#{action.rank}</td>
                <td style={{ padding: '12px 16px', fontFamily: 'Fira Code', color: '#fff' }}>{action.slug}</td>
                <td style={{ padding: '12px 16px' }}>{action.usages}</td>
                <td style={{ padding: '12px 16px', color: 'var(--accent-amber)' }}>{action.unpinned}</td>
                <td style={{ padding: '12px 16px' }}>{action.repos}</td>
                <td style={{ padding: '12px 16px', color: 'var(--text-secondary)' }}>{action.risk}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
