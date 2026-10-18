import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, ShieldCheck, FileCode, CheckCircle2 } from 'lucide-react';

interface ChainItem {
  chain_id: string;
  source: string;
  target: string;
  total_difficulty: number;
  hop_count: number;
  evidence_summary: string;
  hops?: Array<{
    source: string;
    target: string;
    kind: string;
    evidence_file: string;
    evidence_line: number;
  }>;
}

export const AttackChainsCanvas: React.FC = () => {
  const [chains, setChains] = useState<ChainItem[]>([
    {
      chain_id: 'chain-0',
      source: 'input:github.event.issue.title',
      target: 'secret:AWS_PROD_ROLE',
      total_difficulty: 2,
      hop_count: 3,
      evidence_summary: 'Inline bash script interpolation allows shell execution inside triage job holding production deploy tokens.',
      hops: [
        { source: 'input:github.event.issue.title', target: 'step:Parse Title', kind: 'inject', evidence_file: '.github/workflows/triage-deploy.yml', evidence_line: 22 },
        { source: 'step:Parse Title', target: 'job:deploy', kind: 'exec', evidence_file: '.github/workflows/triage-deploy.yml', evidence_line: 28 },
        { source: 'job:deploy', target: 'secret:AWS_PROD_ROLE', kind: 'expose', evidence_file: '.github/workflows/triage-deploy.yml', evidence_line: 35 },
      ]
    },
    {
      chain_id: 'chain-1',
      source: 'action:tj-actions/changed-files@v44',
      target: 'secret:PROD_DEPLOY_KEY',
      total_difficulty: 3,
      hop_count: 2,
      evidence_summary: 'Unpinned mutable tag on compromised third-party action runs with access to production release credentials.',
      hops: [
        { source: 'action:tj-actions/changed-files@v44', target: 'step:changed-files', kind: 'expose', evidence_file: '.github/workflows/ci-release.yml', evidence_line: 16 },
        { source: 'step:changed-files', target: 'secret:PROD_DEPLOY_KEY', kind: 'consume', evidence_file: '.github/workflows/ci-release.yml', evidence_line: 27 },
      ]
    },
    {
      chain_id: 'chain-2',
      source: 'input:github.event.pull_request.head.sha',
      target: 'secret:KUBE_CONFIG_DATA',
      total_difficulty: 4,
      hop_count: 4,
      evidence_summary: 'pull_request_target checks out untrusted PR head branch, building untrusted artifact uploaded and consumed in prod deploy.',
      hops: [
        { source: 'input:pull_request.head.sha', target: 'step:Checkout PR Head', kind: 'inject', evidence_file: '.github/workflows/artifact-pipeline.yml', evidence_line: 14 },
        { source: 'step:Checkout PR Head', target: 'step:Upload Dist', kind: 'poison', evidence_file: '.github/workflows/artifact-pipeline.yml', evidence_line: 24 },
        { source: 'step:Upload Dist', target: 'step:Download Dist', kind: 'inherit', evidence_file: '.github/workflows/artifact-pipeline.yml', evidence_line: 32 },
        { source: 'step:Download Dist', target: 'secret:KUBE_CONFIG_DATA', kind: 'expose', evidence_file: '.github/workflows/artifact-pipeline.yml', evidence_line: 38 },
      ]
    }
  ]);

  const [selectedChain, setSelectedChain] = useState<ChainItem>(chains[0]);

  return (
    <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: '1fr 380px', gap: '24px' }}>
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff' }}>Discovered Attack Paths</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Variable-depth traversal (1..8 hops) from untrusted inputs to crown jewel secrets
            </p>
          </div>
          <div style={{
            fontSize: '12px',
            backgroundColor: 'rgba(244, 63, 94, 0.15)',
            color: 'var(--accent-crimson)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            padding: '4px 10px',
            borderRadius: '6px',
            fontWeight: '600'
          }}>
            {chains.length} Active Attack Vectors
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {chains.map((c) => {
            const isSelected = selectedChain.chain_id === c.chain_id;
            return (
              <div
                key={c.chain_id}
                onClick={() => setSelectedChain(c)}
                style={{
                  padding: '16px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--bg-secondary)',
                  border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-color)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isSelected ? '0 0 15px rgba(6, 182, 212, 0.15)' : 'none',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: '700',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: 'rgba(244, 63, 94, 0.2)',
                      color: 'var(--accent-crimson)',
                    }}>
                      {c.chain_id.toUpperCase()}
                    </span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Exploit Cost: {c.total_difficulty} • {c.hop_count} Hops
                    </span>
                  </div>
                  <span style={{ fontSize: '12px', color: 'var(--accent-cyan)', fontWeight: '600' }}>
                    Click to Inspect →
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '8px 0', fontSize: '13px' }}>
                  <code style={{ color: '#fb7185', backgroundColor: 'rgba(244, 63, 94, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                    {c.source}
                  </code>
                  <ArrowRight size={14} color="var(--text-muted)" />
                  <code style={{ color: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                    FLOWS*
                  </code>
                  <ArrowRight size={14} color="var(--text-muted)" />
                  <code style={{ color: '#f43f5e', backgroundColor: 'rgba(244, 63, 94, 0.2)', padding: '2px 6px', borderRadius: '4px', fontWeight: '600' }}>
                    {c.target}
                  </code>
                </div>

                <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
                  {c.evidence_summary}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detail panel */}
      <div style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '20px',
        height: 'fit-content',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
          <FileCode size={18} color="var(--accent-cyan)" />
          <h3 style={{ fontSize: '15px', fontWeight: '700', color: '#fff' }}>
            Hop-by-Hop Evidence
          </h3>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
          Trace for <strong style={{ color: '#fff' }}>{selectedChain.chain_id}</strong>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {selectedChain.hops?.map((h, i) => (
            <div key={i} style={{
              position: 'relative',
              paddingLeft: '16px',
              borderLeft: '2px solid var(--accent-cyan)',
            }}>
              <div style={{ fontSize: '11px', color: 'var(--accent-cyan)', fontWeight: '600', marginBottom: '2px' }}>
                Hop #{i + 1}: {h.kind.toUpperCase()}
              </div>
              <div style={{ fontSize: '12px', color: '#fff', fontWeight: '500' }}>
                {h.source} → {h.target}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                File: {h.evidence_file}:{h.evidence_line}
              </div>
            </div>
          ))}
        </div>

        <div style={{
          marginTop: '24px',
          padding: '12px',
          borderRadius: '6px',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--accent-emerald)', fontSize: '12px', fontWeight: '600' }}>
            <CheckCircle2 size={14} />
            <span>Remediation Choke Point</span>
          </div>
          <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Severing this single edge breaks reachability for all downstream crown jewel targets.
          </p>
        </div>
      </div>
    </div>
  );
};
