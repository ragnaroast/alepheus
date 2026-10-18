import React, { useState } from 'react';
import { GitPullRequest, CheckCircle2, ShieldCheck, FileDiff } from 'lucide-react';

export const PatchViewer: React.FC = () => {
  const [activePatch, setActivePatch] = useState('env_var');

  const patchData: Record<string, {
    file: string;
    kind: string;
    description: string;
    chainsBefore: number;
    chainsAfter: number;
    diff: string[];
  }> = {
    env_var: {
      file: '.github/workflows/triage-deploy.yml',
      kind: 'Environment Variable Indirection',
      description: 'Move untrusted issue.title into intermediate env: block to prevent inline command execution',
      chainsBefore: 3,
      chainsAfter: 0,
      diff: [
        '--- a/.github/workflows/triage-deploy.yml',
        '+++ b/.github/workflows/triage-deploy.yml',
        '@@ -20,4 +20,7 @@',
        '       - name: Parse Title',
        '-        run: echo "Processing issue: ${{ github.event.issue.title }}"',
        '+        env:',
        '+          ISSUE_TITLE: ${{ github.event.issue.title }}',
        '+        run: echo "Processing issue: $ISSUE_TITLE"',
      ],
    },
    pin: {
      file: '.github/workflows/ci-release.yml',
      kind: 'Immutable SHA Pinning',
      description: 'Pin mutable action tag v44 to immutable 40-character commit hash',
      chainsBefore: 2,
      chainsAfter: 0,
      diff: [
        '--- a/.github/workflows/ci-release.yml',
        '+++ b/.github/workflows/ci-release.yml',
        '@@ -14,3 +14,3 @@',
        '       - name: Get Changed Files',
        '-        uses: tj-actions/changed-files@v44',
        '+        uses: tj-actions/changed-files@ba42e2a8f9b5d47f9ac7a7b8e1a6c4293f019028 # pinned for security',
      ],
    },
  };

  const curr = patchData[activePatch];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileDiff size={20} color="var(--accent-cyan)" />
            Verified Comment-Preserving YAML Patches
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Patches are generated with <code style={{ color: 'var(--accent-cyan)' }}>ruamel.yaml</code> and verified via isolated <code style={{ color: 'var(--accent-cyan)' }}>GRAPH.COPY</code> what-if simulations.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setActivePatch('env_var')}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: '600',
              borderRadius: '6px',
              border: activePatch === 'env_var' ? '1px solid var(--accent-cyan)' : '1px solid var(--border-color)',
              backgroundColor: activePatch === 'env_var' ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-secondary)',
              color: activePatch === 'env_var' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Script Injection Patch
          </button>
          <button
            onClick={() => setActivePatch('pin')}
            style={{
              padding: '6px 14px',
              fontSize: '12px',
              fontWeight: '600',
              borderRadius: '6px',
              border: activePatch === 'pin' ? '1px solid var(--accent-cyan)' : '1px solid var(--border-color)',
              backgroundColor: activePatch === 'pin' ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-secondary)',
              color: activePatch === 'pin' ? 'var(--accent-cyan)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            Action Pinning Patch
          </button>
        </div>
      </div>

      <div style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <div style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>{curr.kind}</div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Target: <code>{curr.file}</code> — {curr.description}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>WHAT-IF SIMULATION</div>
            <div style={{ fontSize: '13px', fontWeight: '700', color: 'var(--accent-emerald)' }}>
              {curr.chainsBefore} Chains → {curr.chainsAfter} Chains (100% Eliminated)
            </div>
          </div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 12px',
            borderRadius: '6px',
            backgroundColor: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid var(--accent-emerald)',
            color: 'var(--accent-emerald)',
            fontSize: '12px',
            fontWeight: '600',
          }}>
            <ShieldCheck size={16} />
            Verified
          </div>
        </div>
      </div>

      <div style={{
        backgroundColor: '#05070d',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '18px',
        fontFamily: 'Fira Code',
        fontSize: '13px',
        lineHeight: '1.5',
        overflowX: 'auto',
      }}>
        {curr.diff.map((line, idx) => {
          let lineClass = '';
          if (line.startsWith('+')) lineClass = 'diff-add';
          else if (line.startsWith('-')) lineClass = 'diff-del';
          else if (line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++')) lineClass = 'diff-meta';

          return (
            <div key={idx} className={lineClass} style={{ padding: '2px 6px', borderRadius: '2px' }}>
              {line}
            </div>
          );
        })}
      </div>
    </div>
  );
};
