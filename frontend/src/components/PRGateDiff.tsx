import React from 'react';
import { GitCompare, XCircle, CheckCircle, ArrowRight, ShieldCheck, ShieldAlert } from 'lucide-react';

export const PRGateDiff: React.FC = () => {
  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GitCompare size={20} color="var(--accent-cyan)" />
            PR Gate Graph Snapshot Diff
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Compares base and head graph snapshots (<code style={{ color: 'var(--accent-cyan)' }}>cp:tenant:base_sha</code> vs <code style={{ color: 'var(--accent-cyan)' }}>cp:tenant:head_sha</code>).
          </p>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '6px 14px',
          backgroundColor: 'rgba(244, 63, 94, 0.15)',
          border: '1px solid var(--accent-crimson)',
          borderRadius: '6px',
          color: 'var(--accent-crimson)',
          fontSize: '12px',
          fontWeight: '700',
        }}>
          <XCircle size={16} />
          GATE VERDICT: BLOCKED (Exit 1)
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '20px',
        marginBottom: '24px',
      }}>
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '16px',
        }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>BASE COMMIT (main)</div>
          <div style={{ fontFamily: 'Fira Code', fontSize: '13px', color: '#fff', marginTop: '4px' }}>
            7a393d1f... (Active Chains: 0)
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--accent-crimson)',
          borderRadius: '8px',
          padding: '16px',
        }}>
          <div style={{ fontSize: '11px', color: 'var(--accent-crimson)', fontWeight: '600' }}>PR HEAD (feature/webhook-handler)</div>
          <div style={{ fontFamily: 'Fira Code', fontSize: '13px', color: '#fff', marginTop: '4px' }}>
            9ac7a7b8... (Active Chains: 1 NEW)
          </div>
        </div>
      </div>

      <div style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '20px',
      }}>
        <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#fff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <ShieldAlert size={16} color="var(--accent-crimson)" />
          New Attack Chains Introduced in PR
        </h3>

        <div style={{
          padding: '14px',
          borderRadius: '6px',
          backgroundColor: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: '600', color: '#fff' }}>
            <span style={{ color: 'var(--accent-crimson)' }}>[NEW CHAIN]</span>
            <code>github.event.comment.body</code>
            <ArrowRight size={14} />
            <code>run: eval "$COMMENT"</code>
            <ArrowRight size={14} />
            <code>secret:TERRAFORM_TOKEN</code>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px' }}>
            This pull request introduces an unquoted comment evaluation step in <code>.github/workflows/monorepo.yml:14</code> that directly exposes cloud provisioning credentials.
          </p>
        </div>
      </div>
    </div>
  );
};
