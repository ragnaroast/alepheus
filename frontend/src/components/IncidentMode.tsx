import React, { useState } from 'react';
import { AlertOctagon, Key, FolderGit2, CheckSquare, Download, ShieldAlert } from 'lucide-react';

export const IncidentMode: React.FC = () => {
  const [selectedAction, setSelectedAction] = useState('tj-actions/changed-files');

  const blastData: Record<string, {
    action: string;
    affectedWorkflows: string[];
    affectedJobs: string[];
    secretsToRotate: string[];
    severity: string;
  }> = {
    'tj-actions/changed-files': {
      action: 'tj-actions/changed-files',
      severity: 'CRITICAL',
      affectedWorkflows: [
        '.github/workflows/ci-release.yml',
        '.github/workflows/pr-check.yml',
        '.github/workflows/nightly-build.yml',
      ],
      affectedJobs: [
        'detect-changes',
        'matrix-test',
        'build-and-tag',
      ],
      secretsToRotate: [
        'PROD_DEPLOY_KEY',
        'DOCKER_PASSWORD',
        'NPM_PUBLISH_TOKEN',
        'AWS_SECURITY_AUDIT_ROLE',
      ],
    },
    'actions/checkout': {
      action: 'actions/checkout',
      severity: 'CRITICAL',
      affectedWorkflows: [
        '.github/workflows/ci-release.yml',
        '.github/workflows/triage-deploy.yml',
        '.github/workflows/artifact-pipeline.yml',
      ],
      affectedJobs: [
        'triage',
        'deploy',
        'detect-changes',
        'release',
        'build-untrusted',
      ],
      secretsToRotate: [
        'AWS_PROD_ROLE',
        'NPM_PUBLISH_TOKEN',
        'PROD_DEPLOY_KEY',
        'KUBE_CONFIG_DATA',
      ],
    },
  };

  const current = blastData[selectedAction] || blastData['tj-actions/changed-files'];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertOctagon size={20} color="var(--accent-crimson)" />
            Incident Mode: Supply Chain Blast Radius
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
            Instant impact analysis when an upstream third-party action is compromised (tj-actions incident simulation).
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <select
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
            style={{
              backgroundColor: 'var(--bg-secondary)',
              color: '#fff',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '13px',
            }}
          >
            <option value="tj-actions/changed-files">tj-actions/changed-files</option>
            <option value="actions/checkout">actions/checkout</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginBottom: '24px' }}>
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '16px',
        }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>SEVERITY LEVEL</div>
          <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--accent-crimson)', margin: '4px 0' }}>
            {current.severity}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Action compromised upstream</div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '16px',
        }}>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>WORKFLOWS EXPOSED</div>
          <div style={{ fontSize: '20px', fontWeight: '700', color: '#fff', margin: '4px 0' }}>
            {current.affectedWorkflows.length} Pipelines
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{current.affectedJobs.length} execution jobs</div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--accent-crimson)',
          borderRadius: '8px',
          padding: '16px',
          boxShadow: '0 0 15px rgba(244, 63, 94, 0.15)',
        }}>
          <div style={{ fontSize: '11px', color: 'var(--accent-crimson)', fontWeight: '600' }}>SECRETS EXPOSED</div>
          <div style={{ fontSize: '20px', fontWeight: '700', color: '#fff', margin: '4px 0' }}>
            {current.secretsToRotate.length} Credentials
          </div>
          <div style={{ fontSize: '12px', color: 'var(--accent-crimson)' }}>Immediate rotation mandatory</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px',
        }}>
          <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#fff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Key size={16} color="var(--accent-crimson)" />
            Urgent Secret Rotation Checklist
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {current.secretsToRotate.map((secret, idx) => (
              <div key={idx} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                backgroundColor: 'rgba(244, 63, 94, 0.08)',
                border: '1px solid rgba(244, 63, 94, 0.2)',
                borderRadius: '6px',
              }}>
                <span style={{ fontFamily: 'Fira Code', fontSize: '13px', color: '#fff' }}>{secret}</span>
                <span style={{ fontSize: '11px', color: 'var(--accent-crimson)', fontWeight: '600' }}>PENDING ROTATION</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '20px',
        }}>
          <h3 style={{ fontSize: '14px', fontWeight: '600', color: '#fff', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <FolderGit2 size={16} color="var(--accent-cyan)" />
            Affected Workflows & Jobs
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {current.affectedWorkflows.map((wf, idx) => (
              <div key={idx} style={{
                padding: '10px 14px',
                backgroundColor: 'var(--bg-tertiary)',
                borderRadius: '6px',
                fontSize: '12px',
                color: 'var(--text-primary)',
                fontFamily: 'Fira Code',
              }}>
                {wf}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
