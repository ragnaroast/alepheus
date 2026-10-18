import React from 'react';
import { Scissors, CheckCircle, TrendingDown, ShieldAlert, Cpu } from 'lucide-react';

export const MinCutPanel: React.FC = () => {
  const fixes = [
    {
      id: 'fix-1',
      kind: 'env_var',
      strategy: 'Environment Variable Indirection',
      target: 'github.event.issue.title',
      file: '.github/workflows/triage-deploy.yml',
      line: 22,
      flowCost: 1,
      impact: 'Severs 4 shell script injection paths to production publish secrets',
      status: 'Ready to patch',
    },
    {
      id: 'fix-2',
      kind: 'pin',
      strategy: 'Immutable Commit SHA Pinning',
      target: 'tj-actions/changed-files@v44',
      file: '.github/workflows/ci-release.yml',
      line: 16,
      flowCost: 1,
      impact: 'Eliminates compromised action tag takeover across entire release pipeline',
      status: 'Ready to patch',
    },
    {
      id: 'fix-3',
      kind: 'permission',
      strategy: 'Least-Privilege Token Restriction',
      target: 'permissions: write-all',
      file: '.github/workflows/monorepo.yml',
      line: 8,
      flowCost: 2,
      impact: 'Reduces GITHUB_TOKEN scope from write-all to read-only',
      status: 'Ready to patch',
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Scissors size={20} color="var(--accent-emerald)" />
            Minimum Fix Set (Min-Cut Optimization)
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Solved via FalkorDB <code style={{ color: 'var(--accent-cyan)' }}>algo.maxFlow</code> with fix capacity weights and residual graph BFS.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            padding: '12px 18px',
            borderRadius: '8px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>FLAT LINTER PROPOSAL</div>
            <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--accent-crimson)' }}>24 Fixes</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Fix everything blindly</div>
          </div>

          <div style={{
            backgroundColor: 'var(--bg-secondary)',
            border: '1px solid var(--accent-emerald)',
            padding: '12px 18px',
            borderRadius: '8px',
            textAlign: 'center',
            boxShadow: '0 0 15px rgba(16, 185, 129, 0.15)',
          }}>
            <div style={{ fontSize: '11px', color: 'var(--accent-emerald)', fontWeight: '600' }}>CHOKEPOINT MIN-CUT</div>
            <div style={{ fontSize: '20px', fontWeight: '700', color: '#fff' }}>3 Fixes</div>
            <div style={{ fontSize: '11px', color: 'var(--accent-emerald)' }}>87.5% Work Reduction</div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
        {fixes.map((fix) => (
          <div
            key={fix.id}
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '18px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{
                  fontSize: '11px',
                  fontWeight: '700',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  backgroundColor: 'rgba(16, 185, 129, 0.15)',
                  color: 'var(--accent-emerald)',
                }}>
                  {fix.kind.toUpperCase()} STRATEGY
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Flow Capacity: {fix.flowCost}
                </span>
              </div>

              <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#fff', marginBottom: '4px' }}>
                {fix.strategy}
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--accent-cyan)', fontFamily: 'Fira Code' }}>
                {fix.target}
              </p>

              <div style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '10px 0' }}>
                Location: {fix.file}:{fix.line}
              </div>

              <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                {fix.impact}
              </p>
            </div>

            <div style={{
              marginTop: '16px',
              paddingTop: '12px',
              borderTop: '1px solid var(--border-color)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--accent-emerald)' }}>
                <CheckCircle size={14} />
                {fix.status}
              </span>
              <button
                style={{
                  padding: '6px 12px',
                  fontSize: '12px',
                  borderRadius: '4px',
                  border: 'none',
                  backgroundColor: 'var(--accent-cyan)',
                  color: '#000',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
                onClick={() => alert(`Patch staged for ${fix.target}`)}
              >
                Draft Patch
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
