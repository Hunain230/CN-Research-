import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, CircleAlert, Copy, Download, FileCheck2, FileWarning, GitBranch, Info, LoaderCircle, Pause, Play, Radio, RefreshCw, RotateCcw, ShieldCheck, Square, Workflow, X } from 'lucide-react';
import SignalPlot from './components/SignalPlot';
import Sparkline from './components/Sparkline';
import { apiPath, loadArchitecture, loadQueues, loadReplay, loadRun, loadRunEvents, loadRuns, requestJson } from './data/adapter';
import { clampCursor, createReplayIndex, currentAlert, eventsReached, stepEventMinute, stepRow } from './data/replay-engine';
import type { AcceptedLinkAtCursor, ReplayIndex } from './data/replay-engine';
import type { Arm, Lane, Mode, QueueSummary, ReplayBundle, RunEvent, RunRecord } from './data/types';
import './styles.css';

const lanes: { id: Lane; label: string; description: string }[] = [
  { id: 'incoming', label: 'Incoming', description: 'Alert rows by event minute' },
  { id: 'verification', label: 'Verification', description: 'Accepted links reached in replay' },
  { id: 'handoff', label: 'Human handoff', description: 'Static rejected relationships' },
  { id: 'provenance', label: 'Provenance', description: 'Distinct accepted roots reached' },
];
const speeds: (number | 'max')[] = [1, 5, 20, 60, 'max'];
const displaySpeed = (speed: number | 'max') => speed === 'max' ? 'Max' : `${speed}×`;
const errorText = (error: unknown) => error instanceof Error ? error.message : 'The research service could not complete this request.';
const shortId = (value: string) => value.length > 22 ? `${value.slice(0, 10)}…${value.slice(-7)}` : value;
const timeText = (value?: string) => value ? new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';
const activeRunStates = new Set(['queued', 'running', 'paused', 'evaluating', 'stopping']);

export default function App() {
  const [mode, setMode] = useState<Mode>('replay');
  const [health, setHealth] = useState<'checking' | 'ready' | 'degraded' | 'offline'>('checking');
  useEffect(() => {
    let alive = true;
    const check = () => requestJson<{ status: string }>('/api/health').then(result => { if (alive) setHealth(result.status === 'ready' ? 'ready' : 'degraded'); }).catch(() => { if (alive) setHealth('offline'); });
    void check(); const timer = window.setInterval(check, 12000);
    return () => { alive = false; window.clearInterval(timer); };
  }, []);

  return <div className="command-shell">
    <aside className="brand-rail" aria-label="CPV research console">
      <div className="rail-mark" aria-hidden="true"><svg viewBox="0 0 34 34"><path d="M17 3.5 28 8v7.1c0 6.4-4.6 11-11 14.4C10.6 26.1 6 21.5 6 15.1V8l11-4.5Z"/><path d="M10.5 17h4l2-4 2.1 8 2.3-4h2.6"/></svg></div>
      <span className="rail-divider" />
      <div className="rail-caption">CPV<br/>RESEARCH</div>
      <div className={`rail-health ${health}`} title={`API status: ${health}`}><i />{health === 'ready' ? 'API' : health === 'checking' ? '…' : 'OFF'}</div>
    </aside>
    <main className="workspace">
      <header className="topbar">
        <div className="product-lockup"><b>CPV</b><span>Evidence console</span></div>
        <nav className="mode-switch" aria-label="Workspace mode">
          <ModeButton mode="replay" current={mode} onClick={setMode} icon={<Radio size={14}/>} label="Recorded replay" />
          <ModeButton mode="walkthrough" current={mode} onClick={setMode} icon={<Workflow size={14}/>} label="Guided walkthrough" />
          <ModeButton mode="experiment" current={mode} onClick={setMode} icon={<GitBranch size={14}/>} label="Experiment run" />
        </nav>
        <div className="top-status"><span className={`status-dot ${health}`} /><span>{health === 'ready' ? 'Research artifacts available' : health === 'checking' ? 'Checking API' : health === 'degraded' ? 'Artifacts incomplete' : 'API unavailable'}</span></div>
      </header>

      {mode === 'replay' && <RecordedReplay />}
      {mode === 'walkthrough' && <GuidedWalkthrough openReplay={() => setMode('replay')} />}
      {mode === 'experiment' && <ExperimentRun />}
      <footer className="app-footer"><span>Recorded research evidence</span><span>Phase 33 · controlled synthetic holdout</span></footer>
    </main>
  </div>;
}

function ModeButton({ mode, current, onClick, icon, label }: { mode: Mode; current: Mode; onClick: (mode: Mode) => void; icon: React.ReactNode; label: string }) {
  return <button type="button" className={`mode-button ${current === mode ? 'selected' : ''}`} aria-pressed={current === mode} onClick={() => onClick(mode)}>{icon}<span>{label}</span></button>;
}

function RecordedReplay() {
  const [arm, setArm] = useState<Arm>('candidate');
  const [queues, setQueues] = useState<QueueSummary | null>(null);
  const [queueId, setQueueId] = useState('');
  const [bundle, setBundle] = useState<ReplayBundle | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<number | 'max'>(5);
  const [lane, setLane] = useState<Lane>('incoming');
  const [reviewed, setReviewed] = useState<Set<string>>(() => new Set());
  const [queueError, setQueueError] = useState('');
  const [bundleError, setBundleError] = useState('');
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const [copied, setCopied] = useState(false);
  const index = useMemo(() => bundle ? createReplayIndex(bundle) : null, [bundle]);
  const current = bundle ? currentAlert(bundle.alerts, cursor) : undefined;
  const acceptedReached = index ? eventsReached(index, cursor) : [];
  const handoffOpen = bundle ? bundle.decisions.rejected.filter(item => !reviewed.has(item.relationship_token)).length : 0;

  const refreshQueues = useCallback(async (targetArm: Arm) => {
    setQueueError('');
    try {
      const result = await loadQueues(targetArm);
      setQueues(result);
      setQueueId(previous => result.queues.some(q => q.queueId === previous) ? previous : result.queues[0]?.queueId || '');
    } catch (error) { setQueueError(errorText(error)); setQueues(null); }
  }, []);
  useEffect(() => { void refreshQueues(arm); }, [arm, refreshQueues]);
  useEffect(() => {
    if (!queueId) { setBundle(null); return; }
    let active = true; setLoading(true); setBundleError(''); setBundle(null); setCursor(0); setPlaying(false); setReviewed(new Set());
    loadReplay(arm, queueId).then(value => { if (active) setBundle(value); }).catch(error => { if (active) setBundleError(errorText(error)); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [arm, queueId]);

  useEffect(() => {
    if (!playing || !bundle) return;
    let raf = 0; let last = 0; let carry = 0;
    const tick = (now: number) => {
      if (!last) last = now;
      const elapsed = Math.min(250, now - last); last = now;
      const increment = speed === 'max' ? 1 : (elapsed * speed) / 1000;
      carry += increment;
      const rows = speed === 'max' ? 1 : Math.floor(carry);
      if (rows > 0) {
        carry -= rows;
        setCursor(value => clampCursor(value + rows, bundle.alerts.length));
        if (cursor + rows >= bundle.alerts.length) setPlaying(false);
      }
      if (playing) raf = window.requestAnimationFrame(tick);
    };
    raf = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(raf);
  }, [playing, speed, bundle, cursor]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && (['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName) || target.isContentEditable)) return;
      if (event.code === 'Space') { event.preventDefault(); setPlaying(value => !value); }
      else if (event.key === 'ArrowRight' && bundle) { event.preventDefault(); setPlaying(false); setCursor(value => event.shiftKey ? stepEventMinute(bundle.alerts, value, 1) : stepRow(value, bundle.alerts.length, 1)); }
      else if (event.key === 'ArrowLeft' && bundle) { event.preventDefault(); setPlaying(false); setCursor(value => event.shiftKey ? stepEventMinute(bundle.alerts, value, -1) : stepRow(value, bundle.alerts.length, -1)); }
      else if (event.key === '[') setSpeed(value => speeds[Math.max(0, speeds.indexOf(value) - 1)]);
      else if (event.key === ']') setSpeed(value => speeds[Math.min(speeds.length - 1, speeds.indexOf(value) + 1)]);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [bundle]);

  const setPosition = (next: number) => { setPlaying(false); setCursor(clampCursor(next, bundle?.alerts.length || 0)); };
  const exportEvidence = () => {
    if (!bundle) return;
    const evidence = { exportType: 'recorded_phase33_evidence', queueName: bundle.queueId, arm: bundle.arm, artifactPaths: bundle.evidence.artifactPaths, replayPosition: cursor, prediction: bundle.prediction, decisions: bundle.decisions, alerts: bundle.alerts, claims: bundle.claims, ledger: bundle.ledger };
    const blob = new Blob([JSON.stringify(evidence, null, 2)], { type: 'application/json' });
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `${bundle.queueId}-${bundle.arm}-evidence.json`; link.click(); URL.revokeObjectURL(link.href);
    setNotice('Evidence export saved with queue and artifact paths.');
  };
  const copyEvidence = async () => {
    if (!bundle) return;
    await navigator.clipboard.writeText(JSON.stringify({ queueName: bundle.queueId, arm: bundle.arm, artifactPaths: bundle.evidence.artifactPaths, cursor, sampleId: current?.alert_id || null }));
    setCopied(true); window.setTimeout(() => setCopied(false), 1800);
  };

  return <section className="screen replay-screen">
    <div className="screen-head">
      <div><div className="mode-tag"><span className="recorded-dot"/>Recorded replay <span className="tag-rule"/> saved Phase 33 holdout</div><h1>Receiver-visible evidence</h1><p>Replay rows in saved file order. The event-minute axis is a separate recorded field.</p></div>
      <div className="head-actions"><button className="button secondary" onClick={copyEvidence} disabled={!bundle} title="Copy queue, source paths, and current sample reference"><Copy size={14}/>{copied ? 'Copied' : 'Copy reference'}</button><button className="button primary" onClick={exportEvidence} disabled={!bundle}><Download size={14}/>Export evidence</button></div>
    </div>
    <div className="replay-toolbar">
      <div className="toolbar-source"><label className="field-control"><span>Model arm</span><select value={arm} onChange={e => { setPlaying(false); setArm(e.target.value as Arm); }}><option value="candidate">Phase 32 +1 candidate · frozen Phase 33</option><option value="baseline">Phase 31 baseline · frozen Phase 33</option></select></label>
        <label className="field-control queue-control"><span>Saved queue</span><select value={queueId} onChange={e => { setPlaying(false); setQueueId(e.target.value); }} disabled={!queues?.queues.length}>{queues?.queues.map(row => <option key={row.queueId} value={row.queueId}>{row.queueId} · {row.alerts} rows</option>)}</select></label></div>
      <div className="transport" aria-label="Replay controls">
        <button className="transport-button" onClick={() => setPosition(0)} title="Reset to first row" aria-label="Reset replay"><RotateCcw size={14}/></button>
        <button className="transport-button" onClick={() => { setPlaying(false); setCursor(c => bundle ? stepEventMinute(bundle.alerts, c, -1) : c); }} disabled={!bundle || cursor <= 0} title="Step to previous distinct event minute" aria-label="Previous event minute"><ArrowLeft size={14}/><span>min</span></button>
        <button className="transport-button" onClick={() => { setPlaying(false); setCursor(c => bundle ? stepRow(c, bundle.alerts.length, -1) : c); }} disabled={!bundle || cursor <= 0} title="Step back one saved row" aria-label="Previous row"><ArrowLeft size={14}/><span>row</span></button>
        <button className="transport-play" onClick={() => { if (bundle && cursor >= bundle.alerts.length) setCursor(0); setPlaying(value => !value); }} disabled={!bundle} aria-label={playing ? 'Pause replay' : 'Play replay'} title={playing ? 'Pause replay (Space)' : 'Play replay (Space)'}>{playing ? <Pause size={15}/> : <Play size={15}/>}</button>
        <button className="transport-button" onClick={() => { setPlaying(false); setCursor(c => bundle ? stepRow(c, bundle.alerts.length, 1) : c); }} disabled={!bundle || cursor >= bundle.alerts.length} title="Step forward one saved row" aria-label="Next row"><span>row</span><ArrowRight size={14}/></button>
        <button className="transport-button" onClick={() => { setPlaying(false); setCursor(c => bundle ? stepEventMinute(bundle.alerts, c, 1) : c); }} disabled={!bundle || cursor >= bundle.alerts.length} title="Step to next distinct event minute" aria-label="Next event minute"><span>min</span><ArrowRight size={14}/></button>
        <label className="speed-control"><span>Speed</span><select value={String(speed)} onChange={e => setSpeed(e.target.value === 'max' ? 'max' : Number(e.target.value))}>{speeds.map(x => <option key={String(x)} value={x}>{displaySpeed(x)}</option>)}</select></label>
      </div>
    </div>

    {(queueError || bundleError) && <div className="error-state" role="alert"><FileWarning size={17}/><div><b>Saved replay data unavailable</b><span>{queueError || bundleError}</span><small>The API reports expected paths when a required artifact is missing.</small></div><button className="icon-button" onClick={() => void refreshQueues(arm)} aria-label="Retry loading saved replay"><RefreshCw size={15}/></button></div>}
    {notice && <div className="notice-state" role="status"><Check size={14}/>{notice}<button onClick={() => setNotice('')} aria-label="Dismiss"><X size={13}/></button></div>}
    <div className="replay-grid">
      <aside className="lane-list" aria-label="Recorded signal lanes">
        <div className="lane-list-head"><span>Signal lanes</span><span>QUEUE</span></div>
        {lanes.map(item => <LaneButton key={item.id} item={item} current={lane} onSelect={next => setLane(next)} index={index} bundle={bundle} cursor={cursor} handoffOpen={handoffOpen}/ >)}
        <div className="lane-note"><Info size={13}/><span>All lanes read saved Phase 33 artifacts. Nothing here is an external input feed.</span></div>
      </aside>

      <div className="main-column">
        <section className="plot-panel">
          <div className="panel-heading"><div><h2>{laneTitle(lane)}</h2><p>{laneSubtitle(lane)}</p></div><span className="plot-source">{bundle ? bundle.queueId : 'Loading queue'}</span></div>
          {loading && <div className="panel-loading"><LoaderCircle className="spinner" size={16}/>Reading saved artifacts…</div>}
          {!loading && !bundle && !bundleError && !queueError && <div className="panel-empty"><LoaderCircle className="spinner" size={16}/><b>Loading recorded queue</b><span>Waiting for the API response.</span></div>}
          {!loading && bundle && lane !== 'handoff' && index && <>
            <div className="chart-legend">{lane === 'incoming' ? <><span><i className="legend-mark volume"/>Rows per event minute</span><span><i className="legend-mark severity"/>Maximum source severity</span><span><i className="legend-mark accepted"/>Accepted endpoints</span></> : <><span><i className="legend-mark line"/>{lane === 'verification' ? 'Accepted links' : 'Distinct roots'} reached by saved row</span><span className="legend-explain">Source-order replay · no interpolated values</span></>}</div>
            <SignalPlot lane={lane} bundle={bundle} index={index} cursor={cursor}/>
          </>}
          {!loading && bundle && lane === 'handoff' && <HandoffPanel bundle={bundle}/>}
          {!loading && bundle && lane !== 'handoff' && lane === 'verification' && <div className="plot-footnote"><Info size={13}/>Only accepted relationships can be tied to alert rows. Rejected items stay in the separate handoff queue.</div>}
          {!loading && bundle && lane === 'provenance' && <div className="plot-footnote"><Info size={13}/>Root count uses the saved upstream roots on accepted decisions, revealed after both endpoint rows are reached.</div>}
          {!loading && bundle && lane === 'incoming' && <div className="plot-footnote"><Info size={13}/>Alert file order is preserved. Event minute is not monotonic in these files; the cursor can move backwards on this axis.</div>}
        </section>

        <ReplayReadout bundle={bundle} current={current} cursor={cursor} speed={speed} acceptedReached={acceptedReached.length} rejectedCount={bundle?.decisions.rejected.length || 0} handoffOpen={handoffOpen}/>

        {bundle && <div className="scrub-row"><span>Replay position</span><input aria-label="Replay position in saved row order" type="range" min="0" max={bundle.alerts.length} value={cursor} onChange={event => setPosition(Number(event.target.value))}/><b>{cursor.toLocaleString()} / {bundle.alerts.length.toLocaleString()}</b><span className="kbd-hint"><kbd>Space</kbd> play <kbd>←</kbd><kbd>→</kbd> row · <kbd>Shift</kbd> minute · <kbd>[ ]</kbd> speed</span></div>}
      </div>

      <aside className="evidence-column">
        {lane === 'handoff' ? <HandoffQueue bundle={bundle} reviewed={reviewed} onReview={token => setReviewed(currentSet => { const next = new Set(currentSet); if (next.has(token)) next.delete(token); else next.add(token); return next; })} /> : <AcceptedStream bundle={bundle} reached={acceptedReached} quiet={playing && speed !== 1} />}
        <section className="source-panel">
          <div className="source-heading"><h3>Evidence source</h3><span>READ ONLY</span></div>
          {bundle ? <><p>{bundle.evidence.source} · {bundle.prediction.split}</p><code>{bundle.evidence.artifactPaths.alerts}</code><div className="source-foot"><span>Rows {bundle.evidence.alertRows}</span><span>Claims {bundle.evidence.claimRows}</span><span>Ledger {bundle.evidence.ledgerRows}</span></div></> : <div className="panel-empty compact">No artifact loaded.</div>}
        </section>
      </aside>
    </div>
  </section>;
}

function LaneButton({ item, current, onSelect, index, bundle, cursor, handoffOpen }: { item: (typeof lanes)[number]; current: Lane; onSelect: (lane: Lane) => void; index: ReplayIndex | null; bundle: ReplayBundle | null; cursor: number; handoffOpen: number }) {
  const isActive = current === item.id;
  const values = item.id === 'incoming' ? (index?.minutes.map(p => p.rows) || []) : item.id === 'verification' ? (index?.acceptedByCursor.slice(0, cursor + 1) || []) : item.id === 'provenance' ? (index?.rootsByCursor.slice(0, cursor + 1) || []) : [];
  const value = item.id === 'incoming' ? cursor : item.id === 'verification' ? index?.acceptedByCursor[cursor] || 0 : item.id === 'provenance' ? index?.rootsByCursor[cursor] || 0 : handoffOpen;
  const readout = item.id === 'incoming' ? `${value.toLocaleString()} / ${bundle?.alerts.length.toLocaleString() || '—'} rows` : item.id === 'verification' ? `${value.toLocaleString()} accepted` : item.id === 'provenance' ? `${value.toLocaleString()} roots reached` : `${handoffOpen.toLocaleString()} awaiting review`;
  return <button type="button" className={`lane-button ${isActive ? 'active' : ''} ${item.id === 'handoff' ? 'handoff-lane' : ''}`} aria-pressed={isActive} onClick={() => onSelect(item.id)}>
    <span className="lane-label"><b>{item.label}</b><strong>{item.id === 'handoff' ? handoffOpen.toLocaleString() : value.toLocaleString()}</strong></span>
    <span className="lane-description">{item.description}</span>
    {item.id === 'handoff' ? <span className="lane-no-time">Count only · no event time</span> : <Sparkline values={values} label={`${item.label} values from saved records`} />}
    <span className="lane-readout">{readout}</span>
  </button>;
}

function ReplayReadout({ bundle, current, cursor, speed, acceptedReached, rejectedCount, handoffOpen }: { bundle: ReplayBundle | null; current: ReturnType<typeof currentAlert>; cursor: number; speed: number | 'max'; acceptedReached: number; rejectedCount: number; handoffOpen: number }) {
  const values = [
    ['Queue', bundle?.queueId || '—', 'saved holdout'],
    ['Sample ID', current?.alert_id || '—', current ? 'current row' : 'no row reached'],
    ['Event minute', current ? String(current.event_minute) : '—', 'source field'],
    ['Replay speed', displaySpeed(speed), 'rows per second · Max = one per frame'],
    ['Rows replayed', `${cursor.toLocaleString()} / ${bundle?.alerts.length.toLocaleString() || '—'}`, 'saved row order'],
    ['Accepted', bundle ? acceptedReached.toLocaleString() : '—', 'reached by endpoint rows'],
    ['Rejected', bundle ? rejectedCount.toLocaleString() : '—', 'saved relationship items'],
    ['Abstention status', 'Not emitted', 'no item-level field'],
    ['Handoff open', bundle ? handoffOpen.toLocaleString() : '—', 'local review state'],
  ];
  return <section className="readout-panel" aria-label="Replay readout"><div className="readout-heading"><h2>Replay readout</h2><span>Selected queue</span></div><div className="readout-grid">{values.map(([label, value, note]) => <div className={`readout-cell ${label === 'Accepted' ? 'semantic-accepted' : label === 'Rejected' ? 'semantic-rejected' : label === 'Handoff open' ? 'semantic-handoff' : ''}`} key={label}><span>{label}</span><b title={value}>{value}</b><small>{note}</small></div>)}</div></section>;
}

function AcceptedStream({ bundle, reached, quiet }: { bundle: ReplayBundle | null; reached: AcceptedLinkAtCursor[]; quiet: boolean }) {
  return <section className="decision-panel">
    <div className="decision-heading"><div><h2>Saved verifier decisions</h2><p>Accepted links reached in recorded row order</p></div><span className="count-pill accepted-pill">{reached.length.toLocaleString()}</span></div>
    <div className="decision-list" aria-live={quiet ? 'off' : 'polite'} aria-atomic="false">
      {!bundle && <EmptyList title="No saved queue" detail="Select a queue to inspect recorded decisions."/>}
      {bundle && reached.length === 0 && <EmptyList title="No accepted link reached yet" detail="Play or step until both endpoint rows have appeared."/>}
      {bundle && [...reached].slice(-18).reverse().map((link, i) => <article className="accepted-entry" key={link.decision.relationship_token}>
        <div className="entry-top"><span className="decision-label accepted-label"><Check size={12}/>Accepted</span><span className="row-reference">row {link.visibleAt}</span></div>
        <div className="endpoint-pair"><code title={link.decision.left_alert_id}>{shortId(link.decision.left_alert_id)}</code><ArrowRight size={12}/><code title={link.decision.right_alert_id}>{shortId(link.decision.right_alert_id)}</code></div>
        <div className="entry-meta"><span>minute {link.minuteByEndpoint[link.decision.left_alert_id]} / {link.minuteByEndpoint[link.decision.right_alert_id]}</span><span>{link.decision.upstream_roots.length} roots</span></div>
        {i === 0 && <details className="entry-detail"><summary>Inspect relationship token and roots</summary><code>{link.decision.relationship_token}</code><span>{link.decision.upstream_roots.join(' · ') || 'No roots emitted'}</span></details>}
      </article>)}
      {bundle && reached.length > 18 && <p className="list-cap">Showing the latest 18 reached decisions of {reached.length}.</p>}
    </div>
    <p className="decision-footnote"><Info size={12}/>Rejected records have no endpoint IDs or event minute; they appear only in Human handoff.</p>
  </section>;
}

function HandoffPanel({ bundle }: { bundle: ReplayBundle }) {
  return <div className="handoff-chart-replacement"><ClipboardHeading count={bundle.decisions.rejected.length}/><p>These saved records have no endpoint ID or event-time field. They are not placed on a chart.</p><div className="handoff-summary"><span>Saved rejected items</span><b>{bundle.decisions.rejected.length.toLocaleString()}</b><small>No separate item-level abstention state is recorded.</small></div><div className="handoff-queue-hint"><ArrowRight size={14}/><span>Inspect each saved reason in the bounded review queue.</span></div></div>;
}
function ClipboardHeading({ count }: { count: number }) { return <div className="handoff-title"><FileCheck2 size={17}/><div><h3>Awaiting human review</h3><span>{count.toLocaleString()} saved rejected relationships</span></div></div>; }

function HandoffQueue({ bundle, reviewed, onReview }: { bundle: ReplayBundle | null; reviewed: Set<string>; onReview: (token: string) => void }) {
  const items = bundle?.decisions.rejected || [];
  return <section className="decision-panel handoff-panel">
    <div className="decision-heading"><div><h2>Awaiting human review</h2><p>Static queue · no event-time field</p></div><span className="count-pill handoff-pill">{items.filter(item => !reviewed.has(item.relationship_token)).length.toLocaleString()} open</span></div>
    {!bundle ? <EmptyList title="No saved queue" detail="Select a queue to load its review items."/> : items.length === 0 ? <EmptyList title="No rejected relationship items" detail="This saved audit has no handoff rows for this queue."/> : <HandoffItems bundle={bundle} reviewed={reviewed} onReview={onReview}/>}
    {bundle && items.length > 0 && <p className="handoff-integrity"><Info size={13}/>Audit does not record endpoint IDs or event times for these decisions; not placed on the timeline.</p>}
    {bundle && <p className="local-review-note">Review marks apply to this browser session only. They are not saved to the research backend.</p>}
  </section>;
}

function HandoffItems({ bundle, reviewed, onReview }: { bundle: ReplayBundle; reviewed: Set<string>; onReview: (token: string) => void }) {
  return <div className="handoff-list">{bundle.decisions.rejected.map((item, i) => {
    const done = reviewed.has(item.relationship_token);
    return <article key={item.relationship_token} className={`handoff-item ${done ? 'reviewed' : ''}`}>
      <div className="handoff-item-head"><span className="decision-label rejected-label"><CircleAlert size={12}/>Rejected · saved verifier record</span><span className="handoff-index">{String(i + 1).padStart(2, '0')}</span></div>
      <code className="relationship-token">{item.relationship_token}</code>
      <div className="reason-line"><span>Recorded reason</span><code>{item.reason}</code></div>
      <div className="suggested-check"><b>Suggested check</b><span>{suggestedCheck(item.reason)}</span></div>
      <button className={`review-mark ${done ? 'marked' : ''}`} onClick={() => onReview(item.relationship_token)}>{done ? <><Check size={12}/>Reviewed this session</> : <>Mark reviewed <ArrowRight size={12}/></>}</button>
    </article>;
  })}</div>;
}

function suggestedCheck(reason: string): string {
  const checks: Record<string, string> = {
    missing_family: 'Check whether the receiver-visible claims include each required evidence family before considering this relationship.',
    derived_or_duplicate_family: 'Inspect claim derivation and confirm each required family has an original, independent claim.',
    shared_upstream_root: 'Check whether the claims trace to distinct upstream roots in the evidence ledger.',
    late_claim: 'Compare claim availability time with the verifier cutoff used by the saved run.',
    time_conflict: 'Review the recorded event-minute relationship against the verifier time window.',
    causal_fields_conflict: 'Compare the recorded process, session, and flow references on the linked claims.',
    endpoint_conflict: 'Check that claims for this token refer to the same ordered endpoint pair.',
    event_conflict: 'Check whether claim event IDs match the endpoint alert records.',
    context_conflict: 'Review the host and account context recorded on both alert endpoints.',
    cap_reject: 'Review the group size cap and the current group memberships.',
  };
  return checks[reason] || 'Inspect the saved claims and verifier rule associated with this recorded reason.';
}

function EmptyList({ title, detail }: { title: string; detail: string }) { return <div className="empty-list"><span>{title}</span><small>{detail}</small></div>; }

function GuidedWalkthrough({ openReplay }: { openReplay: () => void }) {
  const [step, setStep] = useState(0);
  const [architecture, setArchitecture] = useState<{ components: { id: string; label: string; source: string; purpose: string }[]; actions: string; readiness: string } | null>(null);
  const [queueOptions, setQueueOptions] = useState<{ queueId: string; alerts: number }[]>([]);
  const [queueId, setQueueId] = useState('');
  const [bundle, setBundle] = useState<ReplayBundle | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    loadArchitecture().then(value => {
      if (!Array.isArray(value.components) || value.components.length !== 5) throw new Error('Architecture response does not match the documented five-component research path.');
      setArchitecture(value);
    }).catch(error => setError(errorText(error)));
    loadQueues('candidate').then(value => { setQueueOptions(value.queues); setQueueId(value.queues[0]?.queueId || ''); }).catch(error => setError(errorText(error)));
  }, []);
  useEffect(() => {
    if (!queueId) return;
    let alive = true; setPlaying(false); setBundle(null); setCursor(0);
    loadReplay('candidate', queueId).then(value => { if (alive) setBundle(value); }).catch(error => { if (alive) setError(errorText(error)); });
    return () => { alive = false; };
  }, [queueId]);
  useEffect(() => {
    if (!playing || !bundle) return;
    const timer = window.setInterval(() => setCursor(value => { if (value + 1 >= bundle.alerts.length) { setPlaying(false); return bundle.alerts.length; } return value + 1; }), 200);
    return () => window.clearInterval(timer);
  }, [playing, bundle]);
  const current = architecture?.components[step];
  return <section className="screen walkthrough-screen">
    <div className="screen-head"><div><div className="mode-tag"><Workflow size={14}/>Guided walkthrough <span className="tag-rule"/>saved research artifacts</div><h1>Follow the CPV evidence path</h1><p>Five implementation stages, grounded in the backend architecture contract.</p></div><button className="button primary" onClick={openReplay}><Radio size={14}/>Open recorded replay</button></div>
    {error && <div className="error-state" role="alert"><FileWarning size={16}/><span>{error}</span></div>}
    {!architecture && !error && <div className="panel-loading"><LoaderCircle className="spinner" size={16}/>Loading code-grounded architecture…</div>}
    {architecture && current && <div className="walkthrough-layout">
      <section className="path-panel">
        <div className="path-heading"><span>RESEARCH PIPELINE</span><span>{step + 1} / {architecture.components.length}</span></div>
        <div className="pipeline-path">{architecture.components.map((component, i) => <button key={component.id} className={`path-node ${step === i ? 'active' : ''} ${i < step ? 'visited' : ''}`} onClick={() => setStep(i)} aria-current={step === i ? 'step' : undefined}><span className="node-index">{String(i + 1).padStart(2, '0')}</span><b>{component.label}</b><small>{component.source}</small>{i < architecture.components.length - 1 && <i className="path-connector"/>}</button>)}</div>
        <div className="path-foot"><Info size={13}/><span>Displayed architecture comes from <code>GET /api/architecture</code>. No per-component runtime state is emitted.</span></div>
      </section>
      <section className="stage-detail">
        <div className="stage-number">{String(step + 1).padStart(2, '0')}</div><div className="stage-body"><div className="stage-kicker">IMPLEMENTED COMPONENT</div><h2>{current.label}</h2><p>{current.purpose}</p><div className="stage-source"><span>Source</span><code>{current.source}</code></div></div>
        <div className="stage-controls"><button className="button secondary" onClick={() => setStep(value => Math.max(0, value - 1))} disabled={step === 0}><ArrowLeft size={13}/>Previous</button><button className="button secondary" onClick={() => setStep(value => Math.min(architecture.components.length - 1, value + 1))} disabled={step === architecture.components.length - 1}>Next<ArrowRight size={13}/></button></div>
      </section>
      <section className="walkthrough-replay panel-flat"><div className="panel-title"><div><h2>Saved queue replay</h2><p>Recorded Phase 33 candidate rows · no generated events</p></div><select aria-label="Walkthrough queue" value={queueId} onChange={event => setQueueId(event.target.value)}>{queueOptions.map(option => <option key={option.queueId} value={option.queueId}>{option.queueId} · {option.alerts} rows</option>)}</select></div>
        {bundle ? <><div className="walkthrough-row"><span className="recorded-dot"/><div><b>{bundle.alerts[Math.max(0, cursor - 1)]?.alert_id || 'Ready at first saved row'}</b><small>{cursor > 0 ? `Event minute ${bundle.alerts[cursor - 1].event_minute} · source severity ${bundle.alerts[cursor - 1].severity}` : `${bundle.alerts.length} rows in recorded file order`}</small></div><span>{cursor} / {bundle.alerts.length}</span></div><input className="walkthrough-scrub" aria-label="Walkthrough saved row position" type="range" min="0" max={bundle.alerts.length} value={cursor} onChange={event => { setPlaying(false); setCursor(Number(event.target.value)); }}/><div className="walkthrough-replay-actions"><button className="button secondary" onClick={() => { setPlaying(false); setCursor(value => stepRow(value, bundle.alerts.length, -1)); }}><ArrowLeft size={13}/>One row</button><button className="button primary" onClick={() => { if (cursor >= bundle.alerts.length) setCursor(0); setPlaying(value => !value); }}>{playing ? <Pause size={13}/> : <Play size={13}/>} {playing ? 'Pause replay' : 'Play replay'}</button><span>Replay state is separate from experimental evidence.</span></div></> : <div className="panel-empty compact"><LoaderCircle className="spinner" size={14}/>Loading saved queue rows…</div>}
      </section>
      <section className="walkthrough-boundary"><ShieldCheck size={15}/><div><b>Research boundary</b><span>{architecture.actions} {architecture.readiness}</span></div></section>
    </div>}
  </section>;
}

function ExperimentRun() {
  const [runs, setRuns] = useState<RunRecord[]>([]);
  const [run, setRun] = useState<RunRecord | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [runName, setRunName] = useState('Phase 32 development comparison');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [socketState, setSocketState] = useState<'connecting' | 'connected' | 'reconnecting'>('connecting');
  const [lastSocketMessage, setLastSocketMessage] = useState(0);
  const [clock, setClock] = useState(Date.now());
  const runRef = useRef<RunRecord | null>(null);
  const seqRef = useRef(0);
  runRef.current = run;
  const active = !!run && activeRunStates.has(run.status);
  const latestProgress = [...events].reverse().find(event => event.kind === 'queue_complete')?.progress ?? (run?.status === 'completed' ? 1 : 0);

  const refreshRuns = useCallback(async () => {
    const result = await loadRuns();
    setRuns(result.runs);
    setRun(current => current && result.runs.some(item => item.id === current.id) ? current : result.runs.find(item => activeRunStates.has(item.status)) || result.runs[0] || null);
  }, []);
  const syncRun = useCallback(async (id: string, after = 0) => {
    const [fresh, page] = await Promise.all([loadRun(id), loadRunEvents(id, after)]);
    setRun(fresh);
    if (page.events.length) {
      seqRef.current = Math.max(seqRef.current, ...page.events.map(event => event.seq || 0));
      setEvents(current => {
        const seen = new Set(current.map(item => item.seq));
        return [...current, ...page.events.filter(item => !seen.has(item.seq))].slice(-250);
      });
    }
    return fresh;
  }, []);
  useEffect(() => { void refreshRuns().catch(error => setError(errorText(error))); }, [refreshRuns]);
  useEffect(() => {
    if (!run?.id) { setEvents([]); seqRef.current = 0; return; }
    setEvents([]); seqRef.current = 0;
    void syncRun(run.id, 0).catch(error => setError(errorText(error)));
  }, [run?.id, syncRun]);
  useEffect(() => {
    let socket: WebSocket | null = null; let retry = 0; let disposed = false; let timer = 0;
    const connect = () => {
      if (disposed) return;
      setSocketState(retry ? 'reconnecting' : 'connecting');
      const url = new URL(apiPath('/ws'), window.location.href); url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(url);
      socket.onopen = () => { retry = 0; setSocketState('connected'); setLastSocketMessage(Date.now()); socket?.send('subscribe'); const id = runRef.current?.id; if (id) void syncRun(id, seqRef.current).catch(error => setError(errorText(error))); };
      socket.onmessage = message => {
        setLastSocketMessage(Date.now());
        let event: RunEvent;
        try { event = JSON.parse(message.data) as RunEvent; } catch { return; }
        const id = runRef.current?.id;
        if (id && event.runId === id) void syncRun(id, seqRef.current).then(() => refreshRuns()).catch(error => setError(errorText(error)));
      };
      socket.onclose = () => { if (!disposed) { retry += 1; setSocketState('reconnecting'); timer = window.setTimeout(connect, Math.min(8000, 1000 + retry * 700)); } };
      socket.onerror = () => socket?.close();
    };
    connect(); return () => { disposed = true; window.clearTimeout(timer); socket?.close(); };
  }, [refreshRuns, syncRun]);
  useEffect(() => { const timer = window.setInterval(() => setClock(Date.now()), 3000); return () => window.clearInterval(timer); }, []);
  const stale = active && socketState === 'connected' && lastSocketMessage > 0 && clock - lastSocketMessage > 30000;

  const selectRun = async (id: string) => { setError(''); setEvents([]); seqRef.current = 0; try { const value = await loadRun(id); setRun(value); } catch (e) { setError(errorText(e)); } };
  const start = async (event: React.FormEvent) => {
    event.preventDefault(); setBusy(true); setError('');
    try { const created = await requestJson<{ id: string; status: string; config: Record<string, unknown> }>('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: runName, seed: 31102, split: 'development' }) }); setRun({ ...created, name: String(created.config.name || runName) }); setEvents([]); seqRef.current = 0; await refreshRuns(); }
    catch (e) { setError(errorText(e)); }
    finally { setBusy(false); }
  };
  const control = async (action: 'pause' | 'resume' | 'stop') => {
    if (!run) return; setBusy(true); setError('');
    try { await requestJson(`/api/runs/${encodeURIComponent(run.id)}/${action}`, { method: 'POST' }); await syncRun(run.id, seqRef.current); await refreshRuns(); }
    catch (e) { setError(errorText(e)); }
    finally { setBusy(false); }
  };
  const download = () => { if (run) window.open(apiPath(`/api/runs/${encodeURIComponent(run.id)}/export`), '_blank'); };

  return <section className="screen experiment-screen">
    <div className="screen-head"><div><div className="mode-tag"><GitBranch size={14}/>Experiment run <span className="tag-rule"/>Phase 31 / 32 development split</div><h1>Queue-level execution</h1><p>Real lifecycle events from the research runner. This backend emits queue progress, not per-row predictions.</p></div><div className={`socket-badge ${stale ? 'stale' : socketState}`}><span className="status-dot"/>{stale ? 'Run state stale' : socketState === 'connected' ? 'Lifecycle channel connected' : socketState === 'reconnecting' ? 'Reconnecting lifecycle channel' : 'Connecting lifecycle channel'}</div></div>
    {error && <div className="error-state" role="alert"><FileWarning size={16}/><span>{error}</span></div>}
    <div className="run-layout">
      <section className="run-setup panel-flat">
        <div className="panel-title"><div><h2>Run configuration</h2><p>Fixed research runner contract</p></div><span className="read-only">FIXED SPLIT</span></div>
        <form onSubmit={start}>
          <label className="form-field"><span>Run name</span><input value={runName} onChange={event => setRunName(event.target.value)} maxLength={80} required /></label>
          <div className="config-field"><span>Dataset split</span><b>Development · 10 queues</b></div>
          <div className="config-field"><span>Random seed</span><b>31102</b></div>
          <div className="config-field"><span>Models</span><b>Phase 31 baseline + Phase 32 +1 / +2</b></div>
          <p className="run-caveat">This split was previously used for candidate selection. Results are development evidence, not an independent confirmation.</p>
          <button className="button primary start-button" type="submit" disabled={busy || active}><Play size={13}/>{busy ? 'Starting…' : active ? 'A run is active' : 'Start development run'}</button>
        </form>
        <div className="saved-runs"><label htmlFor="saved-run">Saved runs</label><select id="saved-run" value={run?.id || ''} onChange={event => void selectRun(event.target.value)}><option value="">Select run record</option>{runs.map(item => <option key={item.id} value={item.id}>{item.name} · {item.status} · {item.id.slice(0, 8)}</option>)}</select></div>
      </section>
      <section className="run-progress panel-flat">
        <div className="panel-title"><div><h2>Run progress</h2><p>Only backend-emitted lifecycle state</p></div><span className={`run-state ${run?.status || 'none'}`}>{run?.status || 'no run selected'}</span></div>
        {run ? <>
          <div className="run-identity"><code>{run.id}</code><span>{run.name}</span></div>
          <div className="progress-label"><span>Queues completed</span><b>{Math.round(latestProgress * 100)}%</b></div><div className="progress-track"><i style={{ width: `${Math.max(0, Math.min(1, latestProgress)) * 100}%` }}/></div>
          <div className="progress-counts"><span>{events.filter(item => item.kind === 'queue_complete').at(-1)?.completed ?? '—'} completed</span><span>{events.filter(item => item.kind === 'queue_complete').at(-1)?.total ?? '—'} total evaluations</span></div>
          {active && <div className="run-controls">{run.status === 'running' && <button className="button secondary" onClick={() => void control('pause')} disabled={busy}><Pause size={13}/>Pause</button>}{run.status === 'paused' && <button className="button secondary" onClick={() => void control('resume')} disabled={busy}><Play size={13}/>Resume</button>}{['running', 'paused', 'queued'].includes(run.status) && <button className="button danger-quiet" onClick={() => void control('stop')} disabled={busy}><Square size={12}/>Stop run</button>}</div>}
          {run.status === 'completed' && <button className="button secondary export-run" onClick={download}><Download size={13}/>Download run archive</button>}
          {run.error && <div className="run-error"><CircleAlert size={13}/>{run.error}</div>}
          <div className="channel-detail"><span>Last channel event</span><b>{lastSocketMessage ? `${Math.round((clock - lastSocketMessage) / 1000)} sec ago` : 'Waiting for lifecycle event'}</b></div>
        </> : <div className="panel-empty"><GitBranch size={18}/><b>No run selected</b><span>Start the fixed development comparison or choose a saved run record.</span></div>}
      </section>
      <section className="run-events panel-flat">
        <div className="panel-title"><div><h2>Lifecycle events</h2><p>Persisted event order · latest 250</p></div><span className="read-only">{events.length} EVENTS</span></div>
        {!run && <EmptyList title="No run event history" detail="Events appear here after a backend run is selected."/>}
        {run && events.length === 0 && <div className="panel-empty compact">No lifecycle events have been persisted for this run yet.</div>}
        {run && events.length > 0 && <div className="run-event-list" aria-live={active && socketState === 'connected' ? 'off' : 'polite'}>{[...events].reverse().map(event => <RunEventRow key={`${event.seq}-${event.kind}`} event={event}/>)}</div>}
      </section>
    </div>
  </section>;
}

function RunEventRow({ event }: { event: RunEvent }) {
  const details = event.kind === 'queue_complete' ? `${event.queueId} · ${event.arm} · ${event.alerts} alerts · ${event.groups} groups · ${event.accepted} accepted · ${Number(event.runtimeSeconds || 0).toFixed(3)} sec` : event.message || event.status || event.kind;
  return <article className={`run-event ${event.kind}`}><time>{timeText(event.at)}</time><span className="event-kind">{event.kind.replaceAll('_', ' ')}</span><span className="event-detail">{details}</span>{event.progress !== undefined && <b>{Math.round(event.progress * 100)}%</b>}</article>;
}

function laneTitle(lane: Lane) { return ({ incoming: 'Incoming alert rows', verification: 'Accepted links in replay', handoff: 'Human handoff', provenance: 'Provenance roots' } as const)[lane]; }
function laneSubtitle(lane: Lane) { return ({ incoming: 'Recorded fields grouped by event minute', verification: 'A relationship is reached after both saved endpoint rows', handoff: 'Static rejected records without saved event times', provenance: 'Distinct roots on accepted links reached by the cursor' } as const)[lane]; }

