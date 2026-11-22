import { describe, expect, it } from 'vitest';
import { clampCursor, createReplayIndex, eventsReached, stepEventMinute, stepRow } from '../src/data/replay-engine';
import type { AlertRow, ReplayBundle } from '../src/data/types';

const alert = (id: string, minute: number): AlertRow => ({ queue_id: 'q', alert_id: id, event_minute: minute, evidence_available_minute: minute + 1, event_type: 'recorded', severity: 2, asset_criticality: 3 });
const bundle: ReplayBundle = {
  arm: 'candidate', classification: 'recorded_synthetic_holdout_replay', queueId: 'q',
  prediction: { queue_id: 'q', split: 'locked_test', method: 'candidate', ranker: 'ranker', cutoff: 100, candidate_pairs: 2, eligible_alert_ids: ['a', 'b', 'c'], groups_ranked: [['a', 'b', 'c']], decisions: {}, runtime_seconds: 0.1 },
  decisions: { queue_id: 'q', accepted: [
    { left_alert_id: 'a', right_alert_id: 'c', relationship_token: 'token-1', upstream_roots: ['endpoint-1', 'idp-1'] },
    { left_alert_id: 'b', right_alert_id: 'c', relationship_token: 'token-2', upstream_roots: ['endpoint-1', 'network-1'] },
  ], rejected: [{ relationship_token: 'reject-1', reason: 'missing_family' }], decision_counts: {}, visible_claims: 0 },
  alerts: [alert('a', 8), alert('b', 8), alert('c', 3)], claims: [], ledger: [], groupByAlert: { a: 1, b: 1, c: 1 },
  evidence: { alertRows: 3, claimRows: 0, ledgerRows: 0, source: 'receiver_visible only', artifactPaths: { predictions: 'p', decisions: 'd', alerts: 'a', claims: 'c', ledger: 'l' } },
};

describe('deterministic recorded replay engine', () => {
  it('clamps and steps rows without leaving source order', () => {
    expect(clampCursor(-2, 3)).toBe(0);
    expect(clampCursor(9, 3)).toBe(3);
    expect(stepRow(1, 3, 1)).toBe(2);
    expect(stepRow(0, 3, -1)).toBe(0);
  });
  it('steps to the next distinct event minute in recorded row order, including backwards minutes', () => {
    expect(stepEventMinute(bundle.alerts, 0, 1)).toBe(1);
    expect(stepEventMinute(bundle.alerts, 1, 1)).toBe(3);
    expect(stepEventMinute(bundle.alerts, 3, -1)).toBe(2);
    expect(stepEventMinute(bundle.alerts, 1, -1)).toBe(0);
  });
  it('reveals accepted links only after both recorded endpoint rows are reached', () => {
    const first = createReplayIndex(bundle);
    const second = createReplayIndex(bundle);
    expect(first).toEqual(second);
    expect(first.acceptedByCursor).toEqual([0, 0, 0, 2]);
    expect(eventsReached(first, 2)).toHaveLength(0);
    expect(eventsReached(first, 3)).toHaveLength(2);
  });
  it('counts distinct saved provenance roots at the relationship replay point', () => {
    const index = createReplayIndex(bundle);
    expect(index.rootsByCursor).toEqual([0, 0, 0, 3]);
    expect(index.minutes.map(point => point.minute)).toEqual([3, 8]);
    expect(index.minutes.find(point => point.minute === 8)?.rows).toBe(2);
  });
});
