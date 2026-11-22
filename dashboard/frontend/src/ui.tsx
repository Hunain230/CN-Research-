import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
const ScientificChart = lazy(() => import('./chart'));
import {
  Activity, AlertTriangle, ArrowDownToLine, Check, ChevronDown, Ellipsis,
  CircleHelp, CirclePause, CirclePlay, Clock3, CloudUpload, Database, Download,
  FileCheck2, FileJson2, GitBranch, HardDrive, Layers3, ListFilter,
  LoaderCircle, Pause, Play, Radio, RefreshCw, Search, ShieldCheck,
  Square, X,
} from 'lucide-react';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';

type View = 'command' | 'replay' | 'experiments' | 'datasets' | 'architecture' | 'history';
type Overview = {
  systemStatus: string; activeRun: Run | null;
  benchmark: { id: string; name: string; candidate: Metric; baseline: Metric; classification: string; fallbackUnions: number; fallbackTrue: number };
  readiness: { decision: string; realRecallMeasured: boolean; approvedModelFields: number; note: string };
  availableExperiment: { name: string; queues: number; classification: string };
  systemResources: { cpuPercent: number | null; memoryPercent: number | null };
  dataset: { name: string; rows: number; status: string };
  lastChecked: string;
};
type Metric = Record<string, any>;
type Run = { id: string; status: string; created_at?: string; createdAt?: string; result?: any; error?: string | null; config?: any; artifact_dir?: string };
type ReplayIndex = { arm: string; summary: Metric; queues: { queueId: string; alerts: number; groups: number; accepted: number; visibleClaims: number }[] };
type Replay = { arm: string; classification: string; queueId: string; prediction: any; decisions: any; alerts: AlertRow[]; claims: any[]; ledger: any[]; groupByAlert: Record<string, number>; evidence: Record<string, any> };
type AlertRow = { alert_id: string; event_minute: number; severity: number; asset_criticality: number; host?: string; account?: string; event_type?: string; source_id?: string; process_tree_ref?: string };
type Dataset = { id: string; name: string; uploadedAt: string; bytes: number; sha256: string; format: string; rows: number; columns: string[]; profile: any; validation: any };
type RunEvent = { seq?: number; runId: string; kind: string; at?: string; status?: string; progress?: number; completed?: number; total?: number; queueId?: string; arm?: string; alerts?: number; groups?: number; accepted?: number; runtimeSeconds?: number; message?: string; result?: any };

const API_BASE = import.meta.env.VITE_API_BASE || '';
const apiPath = (path: string) => `${API_BASE}${path}`;
const api = async <T,>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(apiPath(url), init);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
};
const formatPct = (value?: number) => typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '—';
const formatNum = (value?: number) => typeof value === 'number' ? value.toLocaleString() : '—';
const formatBytes = (value: number) => value >= 1_048_576 ? `${(value / 1_048_576).toFixed(1)} MiB` : `${(value / 1024).toFixed(0)} KiB`;
const arms = ['baseline', 'candidate'] as const;

const nav: { id: View; label: string; icon: typeof Activity }[] = [
  { id: 'replay', label: 'Operations', icon: Activity },
  { id: 'command', label: 'Research results', icon: Radio },
  { id: 'experiments', label: 'Experiments', icon: GitBranch },
  { id: 'history', label: 'Run records', icon: Clock3 },
];

export default function App() {
  const [view, setView] = useState<View>('replay');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [socketLive, setSocketLive] = useState(false);
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [searchOpen, setSearchOpen] = useState(false);
  const [globalQuery, setGlobalQuery] = useState('');
  const [demoOpen, setDemoOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const load = useCallback(async () => {
    try {
      const [summary, ping] = await Promise.all([api<Overview>('/api/overview'), api<any>('/api/health')]);
      setOverview(summary); setHealth(ping); setError('');
    } catch (e) { setError(e instanceof Error ? e.message : 'Backend unavailable'); }
  }, []);
  useEffect(() => { void load(); const timer = window.setInterval(() => setRefresh(x => x + 1), 5000); return () => clearInterval(timer); }, [load]);
  useEffect(() => { void load(); }, [refresh, load]);
  useEffect(() => {
    let socket: WebSocket;
    let timer: number;
    const connect = () => {
      const socketUrl = new URL(apiPath('/ws'), location.href);
      socketUrl.protocol = socketUrl.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(socketUrl);
      wsRef.current = socket;
      socket.onopen = () => { setSocketLive(true); socket.send('subscribe'); };
      socket.onclose = () => { setSocketLive(false); timer = window.setTimeout(connect, 2500); };
      socket.onerror = () => { setSocketLive(false); socket.close(); };
      socket.onmessage = event => { try { const item = JSON.parse(event.data) as RunEvent; window.dispatchEvent(new CustomEvent('run-event', { detail: item })); } catch { /* Ignore malformed transport frames. */ } };
    };
    connect(); return () => { clearTimeout(timer); socket?.close(); };
  }, []);
  useEffect(() => { if (toast) { const t = window.setTimeout(() => setToast(''), 3200); return () => clearTimeout(t); } }, [toast]);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); setSearchOpen(x => !x); }
      if (event.key === 'Escape') { setSearchOpen(false); }
      if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes((event.target as HTMLElement)?.tagName)) { event.preventDefault(); setSearchOpen(true); }
    };
    window.addEventListener('keydown', onKey); return () => window.removeEventListener('keydown', onKey);
  }, []);
  const notify = (message: string) => setToast(message);

  return <div className="app-shell">
    <aside className="rail">
      <button className="brand-mark" title="CPV Research Command" onClick={() => setView('command')}>
        <svg viewBox="0 0 32 32" aria-hidden="true"><path d="M16 3.5 27 8v7.2c0 6.3-4.5 10.8-11 13.3C9.5 26 5 21.5 5 15.2V8l11-4.5Z"/><path d="M10.5 16.1h4l2.1-4.3 2.2 8.3 2-4h2.7"/></svg>
      </button>
      <div className="rail-rule" />
      <nav className="rail-nav" aria-label="Main navigation">
        {nav.map(({ id, label, icon: Icon }) => <button key={id} className={`rail-item ${view === id ? 'active' : ''}`} aria-label={label} title={label} onClick={() => setView(id)}><Icon size={19} strokeWidth={1.7}/><span>{label}</span></button>)}
      </nav>
      <div className="rail-bottom"><span className={`status-light ${health?.status === 'ready' ? 'green' : 'amber'}`} /><button title="API connection status" className="rail-health" onClick={() => setView('command')}>API</button><span className="build-mark">R.01</span></div>
    </aside>
    <main className="workspace">
      <header className="topbar">
        <div className="crumb"><span>Research systems</span><b>/</b><strong>{nav.find(x => x.id === view)?.label}</strong></div>
        <div className="top-actions">
          <button className="demo-trigger" onClick={() => setDemoOpen(true)}><Play size={12}/> Guided demo</button>
          <button className="search-trigger" onClick={() => setSearchOpen(true)}><Search size={15}/><span>Search runs, queues, datasets</span><kbd>Ctrl K</kbd></button>
          <span className={`connection ${socketLive ? 'online' : ''}`} title="This WebSocket carries experiment lifecycle events, not external sensor telemetry."><i />{socketLive ? 'job events connected' : 'job events offline'}</span>
          <div className="more-wrap"><button className="icon-button" aria-label="More workspaces" aria-expanded={moreOpen} title="Dataset and architecture tools" onClick={() => setMoreOpen(x => !x)}><Ellipsis size={17}/></button>{moreOpen && <div className="more-menu" role="menu"><button role="menuitem" onClick={() => { setView('datasets'); setMoreOpen(false); }}><Database size={15}/> Dataset lab</button><button role="menuitem" onClick={() => { setView('architecture'); setMoreOpen(false); }}><Layers3 size={15}/> Architecture</button></div>}</div>
          <button className="icon-button" aria-label="Refresh data" title="Refresh backend data" onClick={() => setRefresh(x => x + 1)}><RefreshCw size={16}/></button>
        </div>
      </header>
      {error && <div className="backend-banner"><AlertTriangle size={17}/><span><b>Backend unavailable.</b> Start the API to load repository evidence. {error}</span></div>}
      {view === 'command' && <CommandView overview={overview} go={setView} />}
      {view === 'replay' && <ReplayView notify={notify} />}
      {view === 'experiments' && <ExperimentsView notify={notify} />}
      {view === 'datasets' && <DatasetView notify={notify} />}
      {view === 'architecture' && <ArchitectureView />}
      {view === 'history' && <HistoryView notify={notify} />}
      <footer className="footer"><span>CPV Research Command <b>·</b> repository connected</span><span>Research prototype <b>·</b> 2026</span></footer>
    </main>
    {toast && <div className="toast" role="status"><Check size={16}/>{toast}</div>}
    {searchOpen && <SearchDialog query={globalQuery} setQuery={setGlobalQuery} close={() => setSearchOpen(false)} navigate={id => { setView(id); setSearchOpen(false); }} />}
    {demoOpen && <GuidedDemo overview={overview} close={() => setDemoOpen(false)} navigate={id => setView(id)} />}
  </div>;
}

function PageHeading({ title, subtitle, right }: { title: string; subtitle: string; right?: React.ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1><p>{subtitle}</p></div>{right}</div>;
}
function SourceTag({ children, tone = 'muted' }: { children: React.ReactNode; tone?: string }) { return <span className={`source-tag ${tone}`}>{children}</span>; }
function SectionTitle({ children, side }: { children: React.ReactNode; side?: React.ReactNode }) { return <div className="section-title"><h2>{children}</h2>{side}</div>; }
function MetricLine({ label, base, candidate, percent = true, lowerBetter = false, decimals = 0 }: { label: string; base: number; candidate: number; percent?: boolean; lowerBetter?: boolean; decimals?: number }) {
  const fmt = (x: number) => percent ? formatPct(x) : decimals ? x.toFixed(decimals) : formatNum(x);
  const diff = candidate - base;
  const improved = lowerBetter ? diff <= 0 : diff >= 0;
  const change = percent ? `${diff >= 0 ? '+' : ''}${(diff * 100).toFixed(2)} pp` : `${diff >= 0 ? '+' : ''}${formatNum(diff)}`;
  return <div className="metric-line"><span>{label}</span><b>{fmt(candidate)}</b><small>{fmt(base)}</small><em className={improved ? 'positive' : 'negative'}>{change}</em></div>;
}

function CommandView({ overview, go }: { overview: Overview | null; go: (v: View) => void }) {
  const [indices, setIndices] = useState<{ baseline: ReplayIndex | null; candidate: ReplayIndex | null }>({ baseline: null, candidate: null });
  useEffect(() => { Promise.all(arms.map(arm => api<ReplayIndex>(`/api/replay/${arm}/queues`))).then(([baseline, candidate]) => setIndices({ baseline, candidate })).catch(() => undefined); }, []);
  const b = overview?.benchmark.baseline, c = overview?.benchmark.candidate;
  const queueChart = useMemo(() => {
    const bqs = indices.baseline?.queues ?? []; const cqs = indices.candidate?.queues ?? [];
    return { tooltip: { trigger: 'axis', backgroundColor: '#111a22', borderColor: '#30404b', textStyle: { color: '#e7edf1' } },
      grid: { left: 39, right: 16, top: 18, bottom: 30 }, xAxis: { type: 'category', data: cqs.map((_, i) => `Q${String(i + 1).padStart(2, '0')}`), axisLine: { lineStyle: { color: '#26333d' } }, axisLabel: { color: '#82909a', fontSize: 10 } },
      yAxis: { type: 'value', axisLabel: { color: '#82909a', fontSize: 10 }, splitLine: { lineStyle: { color: '#202b34', type: 'dashed' } } },
      legend: { show: false }, series: [{ name: 'Baseline · group count', type: 'line', data: bqs.map(x => x.groups), showSymbol: true, symbolSize: 4, lineStyle: { color: '#47b8e8', width: 1.5 }, itemStyle: { color: '#47b8e8' } },
        { name: 'Candidate · group count', type: 'line', data: cqs.map(x => x.groups), showSymbol: true, symbolSize: 4, lineStyle: { color: '#16c784', width: 1.5 }, itemStyle: { color: '#16c784' } }],
    };
  }, [indices]);
  const [showEvidence, setShowEvidence] = useState(false);
  return <div className="page-content">
    <div className="hero-row"><div><div className="eyebrow"><span className="eyebrow-dot"/> SAVED RESEARCH · PHASE 33</div><h1 className="hero-title">Evidence before<br/><span>priority.</span></h1><p className="hero-copy">A paired, frozen comparison of provenance-aware incident reconstruction on a controlled synthetic holdout.</p><div className="hero-actions"><button className="button primary" onClick={() => go('replay')}><Radio size={15}/> Replay recorded holdout</button><button className="button quiet" onClick={() => go('experiments')}><Play size={14}/> Run development study</button></div></div>
      <div className="hero-verdict"><div className="verdict-kicker"><ShieldCheck size={15}/> HOLDOUT GATE <span className="pill green">PASSED</span></div><div className="verdict-number">{formatPct(c?.incident_recall20)}</div><div className="verdict-label">Incident Recall@20 · synthetic</div><div className="verdict-rule"/><div className="verdict-delta"><span>Matched baseline</span><b>{formatPct(b?.incident_recall20)}</b></div><div className="verdict-delta"><span>Paired change</span><b className="good">+{((c?.incident_recall20 - b?.incident_recall20 || 0) * 100).toFixed(2)} pp</b></div><div className="verdict-delta"><span>New fallback unions</span><b>{overview?.benchmark.fallbackTrue ?? '—'} / {overview?.benchmark.fallbackUnions ?? '—'} true</b></div></div>
    </div>
    <div className="truth-ribbon"><AlertTriangle size={15}/><span><b>Scope boundary</b> This is a controlled synthetic holdout. Phase 39 made no real-SOC predictions; shadow-study readiness remains NO-GO.</span><button onClick={() => setShowEvidence(x => !x)}>{showEvidence ? 'Hide detail' : 'Why this boundary?'} <ChevronDown size={13}/></button></div>
    {showEvidence && <div className="scope-detail"><p>The GUIDE file lacks original source-observation IDs, trust roots, derivation links, causal claim bundles and evidence-arrival times. The official real-data field allowlist is empty. The current models rely on those provenance and timing fields, so uploads cannot be used as a substitute.</p></div>}
    <div className="main-grid">
      <section className="panel queue-panel"><SectionTitle side={<SourceTag>{formatNum(c?.queues)} matched queues</SourceTag>}>Queue-level reconstruction</SectionTitle><div className="chart-legend-note"><span className="legend-line cyan"/> Baseline groups <span className="legend-line green"/> Candidate groups <span className="chart-note">Output groups by held-out queue</span></div><Suspense fallback={<LoadingLine/>}><ScientificChart option={queueChart} style={{ height: 238, width: '100%' }}/></Suspense><div className="queue-foot"><span>Queue count is fixed by the Phase 33 split manifest.</span><button className="text-link" onClick={() => go('replay')}>Inspect a queue <ArrowDownToLine size={13}/></button></div></section>
      <section className="panel pipeline-panel"><SectionTitle side={<SourceTag tone="blue">frozen pipeline</SourceTag>}>C / V / P decision path</SectionTitle><div className="pipeline-stack">{[
        ['C', 'Correlate', 'Proposes provenance-linked alert groups', 'phase16'],
        ['V', 'Verify', 'Checks roots, context and minute-100 cutoff', 'phase31 + phase32'],
        ['P', 'Prioritize', 'Orders verified groups for analyst review', 'source_depth + bonus'],
      ].map(([letter, label, detail, source], i) => <div className="pipeline-step" key={letter}><div className={`step-icon ${i === 1 ? 'verify' : ''}`}>{letter}</div><div className="step-body"><b>{label}</b><span>{detail}</span></div><code>{source}</code>{i < 2 && <div className="step-link"/>}</div>)}</div><div className="pipeline-foot"><span className="signal-dot green"/> Output action: human review queue <span className="separator"/> no automatic response</div><button className="text-link pipeline-link" onClick={() => go('architecture')}>Inspect implementation map <ArrowDownToLine size={13}/></button></section>
      <section className="panel measures-panel"><SectionTitle side={<SourceTag>paired aggregate</SourceTag>}>Research measures</SectionTitle><div className="measure-head"><span>Metric</span><span>Candidate</span><span>Baseline</span><span>Δ paired</span></div>
        {b && c ? <><MetricLine label="Incident Recall@20" base={b.incident_recall20} candidate={c.incident_recall20}/><MetricLine label="Group recoverability" base={b.group_recoverability} candidate={c.group_recoverability}/><MetricLine label="P@10" base={b.p10} candidate={c.p10}/><MetricLine label="Grouped-pair precision" base={b.grouped_pair_precision} candidate={c.grouped_pair_precision}/><MetricLine label="False grouped pairs" base={b.false_grouped_pairs} candidate={c.false_grouped_pairs} percent={false} lowerBetter/><MetricLine label="Mixed predicted groups" base={b.mixed_predicted_groups} candidate={c.mixed_predicted_groups} percent={false} lowerBetter/><MetricLine label="Recorded runtime · seconds" base={b.runtime_seconds} candidate={c.runtime_seconds} percent={false} lowerBetter decimals={3}/><MetricLine label="Derived throughput · alerts/s" base={b.eligible_alerts / b.runtime_seconds} candidate={c.eligible_alerts / c.runtime_seconds} percent={false} decimals={0}/></> : <div className="empty-inline">Waiting for saved Phase 33 metrics.</div>}
        <div className="measure-foot"><span>Runtime is the saved synthetic run measurement; derived throughput is machine-specific, not a deployment benchmark.</span><button className="text-link" onClick={() => window.open(apiPath('/api/metrics/export'), '_blank')}>Export JSON <Download size={13}/></button></div>
      </section>
      <section className="panel signal-panel"><SectionTitle side={<SourceTag tone="amber">live SOC: unavailable</SourceTag>}>System & provenance</SectionTitle><div className="signal-row"><span className="signal-name"><span className="signal-dot green"/> Backend artifacts</span><b>{overview?.systemStatus === 'ready' ? 'Available' : 'Checking'}</b><small>{healthCheckText(overview?.lastChecked)}</small></div><div className="signal-row"><span className="signal-name"><span className="signal-dot amber"/> Real data fields approved</span><b>0</b><small>Phase 39 readiness gate</small></div><div className="signal-row"><span className="signal-name"><span className="signal-dot cyan"/> Current experiment</span><b>{overview?.activeRun?.status || 'None'}</b><small>{overview?.activeRun?.id || 'No active job'}</small></div><div className="resource-bars">{[['CPU', overview?.systemResources.cpuPercent], ['Memory', overview?.systemResources.memoryPercent]].map(([name, value]) => <div className="resource" key={String(name)}><div><span>{name} utilization</span><b>{typeof value === 'number' ? `${value.toFixed(0)}%` : 'Unavailable'}</b></div><div className="resource-track"><i style={{ width: `${typeof value === 'number' ? Math.min(100, value) : 0}%` }}/></div></div>)}</div><div className="resource-note">Host utilization is sampled from the local API process host; it is not an experiment metric.</div></section>
    </div>
    <div className="subtle-note"><CircleHelp size={14}/><span>Model output has no confidence score or attack-class label. The console only exposes observed group decisions, supported ranking measures, source IDs and recorded timing.</span></div>
  </div>;
}
function healthCheckText(value?: string) { return value ? `Checked ${new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'Awaiting API'; }

function isAbstention(reason: string) { return /abstain|missing|not_exact|endpoint_unavailable|insufficient/i.test(reason); }
function humanizeReason(reason: string) { return reason.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase()); }
function diagnosticHint(reason: string) {
  if (/missing_family/i.test(reason)) return 'Inspect the source-family mapping in a development trace. This saved audit keeps the reason and token but omits the linked alert IDs.';
  if (/time_conflict|temporal|minute|cutoff/i.test(reason)) return 'Check the pair’s event and evidence-availability times in a development trace; this saved audit has no pair IDs or event times.';
  if (/causal_fields_conflict/i.test(reason)) return 'Compare the causal provenance fields in a development trace. The saved holdout audit does not include the paired input records.';
  if (/not_exact_auth_network_pair/i.test(reason)) return 'Inspect the exact authentication and network evidence pair in a development trace; the locked audit does not identify either alert.';
  return 'Use this reason and relationship token to locate the originating development trace. The saved holdout audit omits alert endpoints and event times.';
}

function ReplayView({ notify }: { notify: (s: string) => void }) {
  const [arm, setArm] = useState<'baseline' | 'candidate'>('candidate');
  const [index, setIndex] = useState<ReplayIndex | null>(null);
  const [queueId, setQueueId] = useState('');
  const [data, setData] = useState<Replay | null>(null);
  const [cursor, setCursor] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(12);
  const [filter, setFilter] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState('');
  const [selectedReason, setSelectedReason] = useState('');
  const [reviewLane, setReviewLane] = useState<'incoming' | 'accepted' | 'handoff'>('incoming');
  const [loadError, setLoadError] = useState('');
  useEffect(() => { api<ReplayIndex>(`/api/replay/${arm}/queues`).then(x => { setIndex(x); setQueueId(x.queues[0]?.queueId || ''); setData(null); setCursor(0); setSelectedAlert(''); }).catch(e => setLoadError(e.message)); }, [arm]);
  useEffect(() => { if (!queueId) return; api<Replay>(`/api/replay/${arm}/${queueId}`).then(x => { setData(x); const initial = x.alerts[0]?.alert_id || ''; setSelectedAlert(initial); setSelectedReason(x.decisions.rejected[0]?.reason || ''); setCursor(0); setLoadError(''); }).catch(e => setLoadError(e.message)); }, [arm, queueId]);
  useEffect(() => { if (!playing || !data) return; const interval = Math.max(30, 1000 / speed); const timer = window.setInterval(() => setCursor(x => { if (x + 1 >= data.alerts.length) { setPlaying(false); return data.alerts.length; } return x + 1; }), interval); return () => clearInterval(timer); }, [playing, speed, data]);
  const current = cursor > 0 ? data?.alerts[Math.min(cursor - 1, (data?.alerts.length || 1) - 1)] : undefined;
  useEffect(() => { if (playing && current) setSelectedAlert(current.alert_id); }, [playing, current]);
  const visibleAlerts = useMemo(() => {
    if (!data) return [];
    const chosen = filter === 'all' ? data.alerts : data.alerts.filter(x => filter === 'grouped' ? data.groupByAlert[x.alert_id] : !data.groupByAlert[x.alert_id]);
    return chosen.slice(0, 1200);
  }, [data, filter]);
  const eventMarkers = useMemo(() => {
    if (!data) return { accepted: [] as number[] };
    const alertMap = new Map(data.alerts.map(x => [x.alert_id, x.event_minute]));
    const accepted = data.decisions.accepted.map((x: any) => alertMap.get(x.left_alert_id)).filter((x: any) => typeof x === 'number');
    return { accepted };
  }, [data]);
  const chartOptions = useMemo(() => {
    if (!data) return [];
    const buckets = new Map<number, { count: number; severity: number }>();
    for (const row of data.alerts) { const bucket = buckets.get(row.event_minute) || { count: 0, severity: 0 }; bucket.count++; bucket.severity = Math.max(bucket.severity, row.severity || 0); buckets.set(row.event_minute, bucket); }
    const times = [...buckets.keys()].sort((a, b) => a - b);
    const acceptedByMinute = new Map<number, number>();
    eventMarkers.accepted.forEach((minute: number) => acceptedByMinute.set(minute, (acceptedByMinute.get(minute) || 0) + 1));
    const shownMinute = current?.event_minute ?? -1;
    const axis = { axisLine: { lineStyle: { color: '#363b41' } }, axisLabel: { color: '#818a92', fontSize: 9 }, splitLine: { lineStyle: { color: '#292e33', type: 'dashed' } } };
    const cursorLine = { symbol: 'none', label: { color: '#aab3ba', formatter: 'cursor' }, lineStyle: { color: '#aab3ba', type: 'dashed', opacity: .55 }, data: shownMinute < 0 ? [] : [{ xAxis: shownMinute }] };
    const activity = { animation: false, tooltip: { trigger: 'axis', backgroundColor: '#181b1f', borderColor: '#363b41', textStyle: { color: '#e7eaed' } }, grid: { left: 52, right: 16, top: 14, bottom: 27 }, dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'none' }], xAxis: { type: 'value', name: 'event minute', nameTextStyle: { color: '#818a92', fontSize: 9 }, ...axis, splitLine: { show: false } }, yAxis: { type: 'value', name: 'alerts / min', min: 0, nameTextStyle: { color: '#818a92', fontSize: 9 }, ...axis }, series: [
      { name: 'Receiver-visible alerts', type: 'line', data: times.map(t => [t, buckets.get(t)!.count]), showSymbol: false, lineStyle: { color: '#a855f7', width: 1.7 }, areaStyle: { color: 'rgba(168,85,247,.12)' }, markLine: cursorLine },
      { name: 'Accepted relationships', type: 'scatter', data: [...acceptedByMinute].map(([minute, count]) => [minute, buckets.get(minute)?.count || 0.3, count]), symbolSize: 6, itemStyle: { color: '#8ec6a4' }, tooltip: { formatter: (x: any) => `Accepted relationships<br/>minute ${x.value[0]}<br/>records ${x.value[2]}` } },
    ] };
    const severity = { animation: false, tooltip: { trigger: 'axis', backgroundColor: '#181b1f', borderColor: '#363b41', textStyle: { color: '#e7eaed' } }, grid: { left: 52, right: 16, top: 14, bottom: 27 }, dataZoom: [{ type: 'inside', xAxisIndex: 0, filterMode: 'none' }], xAxis: { type: 'value', name: 'event minute', nameTextStyle: { color: '#818a92', fontSize: 9 }, ...axis, splitLine: { show: false } }, yAxis: { type: 'value', name: 'source severity', min: 0, max: Math.max(1, ...[...buckets.values()].map(x => x.severity)), nameTextStyle: { color: '#818a92', fontSize: 9 }, ...axis }, series: [{ name: 'Maximum recorded source severity', type: 'line', data: times.map(t => [t, buckets.get(t)!.severity]), showSymbol: false, lineStyle: { color: '#9a87cb', width: 1.5 }, areaStyle: { color: 'rgba(154,135,203,.08)' }, markLine: cursorLine }] };
    return [activity, severity];
  }, [data, current, eventMarkers]);
  const groupRows: { rank: number; members: string[]; count: number }[] = (data?.prediction.groups_ranked || []).map((group: string[], i: number) => ({ rank: i + 1, members: group, count: group.length }));
  const selected = data?.alerts.find(x => x.alert_id === selectedAlert);
  const selectedDecision = data?.decisions.rejected.find((x: any) => x.reason === selectedReason);
  const decisionIsAbstention = !!selectedReason && isAbstention(selectedReason);
  const acceptedCount = data?.decisions.decision_counts.accepted || 0;
  const rejectedCount = data?.decisions.rejected.filter((x: any) => !isAbstention(x.reason || '')).length || 0;
  const abstainedCount = data?.decisions.rejected.filter((x: any) => isAbstention(x.reason || '')).length || 0;
  const decisionReasonRows = [...(data?.decisions.rejected || []).reduce((map: Map<string, number>, row: any) => map.set(row.reason || 'reason_not_emitted', (map.get(row.reason || 'reason_not_emitted') || 0) + 1), new Map<string, number>())].map(([reason, count]) => ({ reason, count, state: isAbstention(reason) ? 'abstained' : 'rejected' })).sort((a, b) => b.count - a.count);
  const incomingRows = data?.alerts.slice(Math.max(0, cursor - 1), Math.max(0, cursor - 1) + 6) || [];
  const acceptedRows = data?.decisions.accepted || [];
  const handoffRows = data?.decisions.rejected || [];
  const changeQueue = (value: string) => { setPlaying(false); setQueueId(value); };
  const download = (format: 'csv' | 'json') => { if (!data) return; window.open(apiPath(`/api/decisions/export/${arm}/${queueId}?format=${format}`), '_blank'); notify(`${format.toUpperCase()} replay evidence exported`); };
  return <div className="page-content ops-page">
    <PageHeading title="Operations" subtitle="Recorded CPV research replay" right={<Badge variant="outline" className="mode-badge"><span className="signal-dot amber"/> Recorded replay / no live sensor feed</Badge>}/>
    {loadError && <div className="inline-error"><AlertTriangle size={15}/>{loadError}</div>}
    <section className="ops-stat-grid" aria-label="Selected queue summary">
      <div className="ops-stat"><span>Records in queue</span><b>{formatNum(data?.alerts.length)}</b><small>{queueId || 'Loading queue'}</small></div>
      <div className="ops-stat"><span>Accepted relationships</span><b className="stat-good">{formatNum(acceptedCount)}</b><small>Verifier accepted</small></div>
      <div className="ops-stat"><span>Rejected relationships</span><b className="stat-bad">{formatNum(rejectedCount)}</b><small>Rule failed</small></div>
      <div className="ops-stat"><span>Abstentions</span><b className="stat-warn">{formatNum(abstainedCount)}</b><small>Evidence incomplete</small></div>
    </section>
    <section className="panel replay-controls ops-toolbar">
      <div className="control-cluster">
        <label>Model<select value={arm} onChange={e => setArm(e.target.value as 'baseline' | 'candidate')}><option value="candidate">Phase 33 candidate · Phase 32 +1</option><option value="baseline">Phase 31 baseline</option></select></label>
        <label>Queue<select value={queueId} onChange={e => changeQueue(e.target.value)}>{index?.queues.map(q => <option key={q.queueId} value={q.queueId}>{q.queueId} ({q.alerts} alerts)</option>)}</select></label>
      </div>
      <div className="playback-cluster">
        <Button variant="outline" size="icon-sm" title={playing ? 'Pause replay' : 'Play replay'} aria-label={playing ? 'Pause replay' : 'Play replay'} onClick={() => { if (data && cursor >= data.alerts.length) setCursor(0); setPlaying(x => !x); }}>{playing ? <Pause size={15}/> : <Play size={15}/>}</Button>
        <Button variant="ghost" size="icon-sm" title="Reset replay" aria-label="Reset replay" onClick={() => { setPlaying(false); setCursor(0); }}><Square size={13}/></Button>
        <label>Speed<select value={speed} onChange={e => setSpeed(Number(e.target.value))}><option value={4}>4 / sec</option><option value={12}>12 / sec</option><option value={30}>30 / sec</option><option value={60}>60 / sec</option></select></label>
        <span className="replay-position"><b>{Math.min(cursor, data?.alerts.length || 0).toLocaleString()}</b><span> / {formatNum(data?.alerts.length)}</span></span>
      </div>
    </section>
    <div className="ops-grid">
      <section className="panel ops-signal-panel">
        <SectionTitle side={<span className="ops-queue-tag">{queueId || 'Loading queue'}</span>}>Signal history</SectionTitle>
        <div className="ops-legend"><span><i className="violet-key"/>Alert volume</span><span><i className="green-key"/>Accepted link markers</span><span className="ops-zoom-note">Scroll to zoom</span></div>
        {data ? <div className="ops-chart-stack">
          <div className="ops-chart-lane"><div className="ops-chart-label"><b>Receiver-visible alerts</b><span>alerts / minute</span></div><Suspense fallback={<LoadingLine/>}><ScientificChart option={chartOptions[0]} style={{ height: 225, width: '100%' }}/></Suspense></div>
          <div className="ops-chart-lane severity-lane"><div className="ops-chart-label"><b>Source severity</b><span>maximum observed</span></div><Suspense fallback={<LoadingLine/>}><ScientificChart option={chartOptions[1]} style={{ height: 112, width: '100%' }}/></Suspense></div>
        </div> : <LoadingLine/>}
        <div className="scrubber"><input aria-label="Replay position" type="range" min="0" max={Math.max(0, (data?.alerts.length || 1) - 1)} value={Math.min(cursor, Math.max(0, (data?.alerts.length || 1) - 1))} onChange={e => { setPlaying(false); setCursor(Number(e.target.value)); }} style={{ '--progress': `${data && data.alerts.length ? (cursor / data.alerts.length) * 100 : 0}%` } as React.CSSProperties}/><span>sample</span></div>
      </section>
      <section className="panel ops-review-panel">
        <SectionTitle side={<span className="ops-queue-tag">{formatNum(acceptedRows.length + handoffRows.length)} relationships</span>}>Decision queue</SectionTitle>
        <p className="ops-panel-note">Recorded receiver-visible events flow through the saved verifier decisions.</p>
        <div className="review-lanes" role="tablist" aria-label="Replay decision queue">
          <button role="tab" aria-selected={reviewLane === 'incoming'} className={reviewLane === 'incoming' ? 'active' : ''} onClick={() => setReviewLane('incoming')}>Incoming <b>{formatNum(data?.alerts.length)}</b></button>
          <button role="tab" aria-selected={reviewLane === 'accepted'} className={reviewLane === 'accepted' ? 'active accepted' : ''} onClick={() => setReviewLane('accepted')}>Verified <b>{formatNum(acceptedRows.length)}</b></button>
          <button role="tab" aria-selected={reviewLane === 'handoff'} className={reviewLane === 'handoff' ? 'active handoff' : ''} onClick={() => setReviewLane('handoff')}>Human review <b>{formatNum(handoffRows.length)}</b></button>
        </div>
        <div className="review-lane-caption">{reviewLane === 'incoming' ? 'Alert rows at the replay cursor · recorded sample order' : reviewLane === 'accepted' ? 'Accepted evidence relationships · verifier audit' : 'Rejected or abstained relationships · analyst follow-up'}</div>
        <div className="review-queue" role="tabpanel">
          {reviewLane === 'incoming' && incomingRows.map(row => <button key={row.alert_id} className={`queue-entry ${selectedAlert === row.alert_id ? 'selected' : ''}`} onClick={() => { setSelectedAlert(row.alert_id); setCursor(data?.alerts.findIndex(x => x.alert_id === row.alert_id)! + 1); }}>
            <span className="queue-state-dot incoming"/><span className="queue-entry-main"><b>{row.event_type || 'Receiver-visible alert'}</b><small>{row.alert_id} · minute {row.event_minute}</small></span><span className="queue-entry-meta">S{row.severity}</span>
          </button>)}
          {reviewLane === 'accepted' && acceptedRows.slice(0, 24).map((row: any) => <div key={row.relationship_token} className="queue-entry static"><span className="queue-state-dot accepted"/><span className="queue-entry-main"><b>Verified relationship</b><small>{row.left_alert_id} ↔ {row.right_alert_id}</small><small className="roots-line">Roots: {(row.upstream_roots || []).join(' · ') || 'not emitted'}</small></span><span className="queue-entry-meta accepted-text">accepted</span></div>)}
          {reviewLane === 'handoff' && handoffRows.slice(0, 24).map((row: any) => <button key={row.relationship_token} className={`queue-entry handoff-entry ${selectedReason === row.reason ? 'selected' : ''}`} onClick={() => setSelectedReason(row.reason)}><span className={`queue-state-dot ${isAbstention(row.reason) ? 'abstained' : 'rejected'}`}/><span className="queue-entry-main"><b>{humanizeReason(row.reason || 'reason_not_emitted')}</b><small>{isAbstention(row.reason) ? 'Abstained · review evidence gap' : 'Rejected · verifier rule not satisfied'}</small><small className="roots-line">Token {row.relationship_token || 'not emitted'}</small></span><span className="queue-entry-meta">{isAbstention(row.reason) ? 'review' : 'inspect'}</span></button>)}
          {reviewLane === 'incoming' && !incomingRows.length && <div className="queue-empty">Replay cursor is at the end of this queue.</div>}
          {reviewLane === 'accepted' && !acceptedRows.length && <div className="queue-empty">No accepted relationships in this queue.</div>}
          {reviewLane === 'handoff' && !handoffRows.length && <div className="queue-empty">No rejected or abstained relationships in this queue.</div>}
        </div>
        {reviewLane === 'handoff' && selectedReason && <div className={`ops-diagnosis ${decisionIsAbstention ? 'amber' : 'red'}`}><div className="diagnosis-title"><span className={`signal-dot ${decisionIsAbstention ? 'amber' : 'red'}`}/><b>{decisionIsAbstention ? 'Abstention' : 'Rejected link'} / {humanizeReason(selectedReason)}</b></div><p>{decisionReasonRows.find(row => row.reason === selectedReason)?.count || 0} decisions in this queue.</p>{selectedDecision?.relationship_token && <div className="diagnosis-token"><span>Relationship token</span><code>{selectedDecision.relationship_token}</code></div>}<div className="diagnosis-next"><b>Analyst check</b><span>{diagnosticHint(selectedReason)}</span></div><small>Recorded verifier output has no endpoint IDs or event times for these decisions. Use this as a reason-level handoff, not a sample-linked incident ticket.</small></div>}
        {selected && <div className="ops-sample-peek"><span>Replay cursor sample</span><code>{selected.alert_id}</code><small>Minute {selected.event_minute} | severity {selected.severity} | {data?.groupByAlert[selected.alert_id] ? `group #${data.groupByAlert[selected.alert_id]}` : 'ungrouped'}</small></div>}
      </section>
    </div>
    <details className="evidence-details ops-records"><summary><span>Evidence records</span><small>Open ranked groups and source rows</small><ChevronDown size={15}/></summary>
      <div className="records-toolbar"><label>Show records<select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All</option><option value="grouped">Grouped</option><option value="ungrouped">Ungrouped</option></select></label><div><button className="text-link" onClick={() => download('csv')}>Export CSV <Download size={13}/></button><button className="text-link" onClick={() => download('json')}>Export JSON <FileJson2 size={13}/></button></div></div>
      <section className="panel group-panel"><SectionTitle side={<SourceTag>{data?.prediction.groups_ranked.length || 0} groups</SourceTag>}>Ranked groups</SectionTitle><div className="scroll-table"><table><thead><tr><th>Rank</th><th>Members</th><th>First member</th></tr></thead><tbody>{groupRows.slice(0, 60).map(row => <tr key={row.rank} className={selected && row.members.includes(selected.alert_id) ? 'selected' : ''} onClick={() => setSelectedAlert(row.members[0])}><td>{String(row.rank).padStart(2, '0')}</td><td>{row.count}</td><td><code>{row.members[0]}</code></td></tr>)}</tbody></table></div></section>
      <section className="panel alert-table-panel"><SectionTitle side={<span>{visibleAlerts.length.toLocaleString()} rows ? preview capped at 1,200</span>}>Receiver-visible records</SectionTitle><div className="scroll-table alert-scroll"><table><thead><tr><th>Sample</th><th>Minute</th><th>Event</th><th>Severity</th><th>Criticality</th><th>Group</th></tr></thead><tbody>{visibleAlerts.map((row, i) => <tr key={row.alert_id} className={selectedAlert === row.alert_id ? 'selected' : ''} onClick={() => { setSelectedAlert(row.alert_id); const realIndex = data?.alerts.findIndex(item => item.alert_id === row.alert_id) ?? i; if (realIndex >= 0) setCursor(realIndex + 1); }}><td><code>{row.alert_id}</code></td><td>{row.event_minute}</td><td>{row.event_type || '?'}</td><td>{row.severity}</td><td>{row.asset_criticality}</td><td>{data?.groupByAlert[row.alert_id] ? `#${data.groupByAlert[row.alert_id]}` : '?'}</td></tr>)}</tbody></table></div><div className="table-note">Replay input includes receiver-visible data only. Evaluator labels remain private.</div></section>
    </details>
  </div>;
}
function LoadingLine() { return <div className="loading-line"><LoaderCircle size={16}/> Loading saved receiver-visible records…</div>; }

function ExperimentsView({ notify }: { notify: (s: string) => void }) {
  const [active, setActive] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('Phase 32 development comparison');
  const [error, setError] = useState('');
  const progress = useMemo(() => events.filter(x => x.kind === 'queue_complete').slice(-1)[0]?.progress || (active?.status === 'completed' ? 1 : 0), [events, active]);
  const loadRuns = useCallback(async () => { try { const value = await api<{ runs: Run[] }>('/api/runs'); const running = value.runs.find(x => ['queued', 'running', 'paused', 'evaluating'].includes(x.status)); if (running) setActive(running); } catch { /* Backend banner carries the connection state. */ } }, []);
  useEffect(() => { void loadRuns(); }, [loadRuns]);
  useEffect(() => {
    const handler = (event: globalThis.Event) => { const item = (event as CustomEvent<RunEvent>).detail; if (item.runId !== active?.id) return; setEvents(x => [...x.slice(-180), item]); if (item.status) setActive(x => x ? { ...x, status: item.status!, result: item.result || x.result } : x); void loadRuns(); };
    window.addEventListener('run-event', handler); return () => window.removeEventListener('run-event', handler);
  }, [active?.id, loadRuns]);
  useEffect(() => { if (!active || !['queued', 'running', 'paused', 'evaluating'].includes(active.status)) return; const timer = window.setInterval(() => api<Run>(`/api/runs/${active.id}`).then(setActive).then(loadRuns).catch(() => undefined), 1100); return () => clearInterval(timer); }, [active?.id, active?.status, loadRuns]);
  const start = async () => { setBusy(true); setError(''); setEvents([]); try { const run = await api<Run>('/api/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, seed: 31102, split: 'development' }) }); setActive(run); notify('Development experiment started'); await loadRuns(); } catch (e) { setError(e instanceof Error ? e.message : 'Could not start experiment'); } finally { setBusy(false); } };
  const action = async (kind: string) => { if (!active) return; try { await api(`/api/runs/${active.id}/${kind}`, { method: 'POST' }); const current = await api<Run>(`/api/runs/${active.id}`); setActive(current); notify(kind === 'stop' ? 'Stop requested; current queue will finish' : `Experiment ${kind}d`); } catch (e) { setError(e instanceof Error ? e.message : `Could not ${kind} experiment`); } };
  const activeNow = active && ['queued', 'running', 'paused', 'evaluating'].includes(active.status);
  const result = active?.result;
  return <div className="page-content"><PageHeading title="Experiment bench" subtitle="Execute the existing Phase 31/32 models on the fixed, previously accessed development split." right={<SourceTag tone="amber">DEVELOPMENT · SYNTHETIC</SourceTag>}/>
    <div className="scope-callout"><AlertTriangle size={16}/><span><b>Not confirmatory.</b> This cohort was used during candidate selection. Phase 33’s locked-test predictions remain read-only and are never regenerated here.</span></div>
    <div className="experiment-layout"><section className="panel experiment-setup"><SectionTitle side={<SourceTag tone="blue">fixed protocol</SourceTag>}>Run configuration</SectionTitle><label className="field-label">Experiment name<input value={name} onChange={e => setName(e.target.value)} maxLength={100}/></label><div className="config-row"><span>Dataset / split</span><b>Phase 31 controlled synthetic · development</b></div><div className="config-row"><span>Queue count</span><b>10 fixed queues</b></div><div className="config-row"><span>Seed</span><b className="mono">31102 · fixed</b></div><div className="config-row"><span>Model arms</span><b>Phase 31 baseline + Phase 32 +1 / +2</b></div><div className="config-row"><span>Evidence cutoff</span><b>Minute 100 · fixed by study</b></div><div className="config-row"><span>Ranking component cap</span><b>100 alerts · fixed by study</b></div><p className="setup-note">Only the study label is configurable. Changing cohort, split seed, or model parameters would no longer reproduce the existing research protocol.</p><button className="button primary wide" disabled={busy || !!activeNow} onClick={() => void start()}>{busy ? <LoaderCircle className="spin" size={15}/> : <Play size={15}/>} Run fixed development comparison</button>{error && <div className="inline-error"><AlertTriangle size={14}/>{error}</div>}</section>
      <section className="panel execution-panel"><SectionTitle side={<span className={`pill ${active?.status === 'completed' ? 'green' : active?.status === 'failed' ? 'red' : activeNow ? 'amber' : ''}`}>{active?.status || 'idle'}</span>}>Execution state</SectionTitle>{active ? <><div className="run-id-row"><span>Experiment ID</span><code>{active.id}</code></div><div className="progress-heading"><b>{active.status === 'evaluating' ? 'Official evaluator' : active.status === 'completed' ? 'Run complete' : active.status === 'cancelled' ? 'Run cancelled' : active.status === 'failed' ? 'Run failed' : 'Queue inference'}</b><span>{active.status === 'evaluating' ? 'Predictions sealed' : `${Math.round(progress * 100)}%`}</span></div><div className="progress-track"><i style={{ width: `${active.status === 'evaluating' ? 96 : progress * 100}%` }}/></div><div className="progress-meta"><span>{events.filter(x => x.kind === 'queue_complete').slice(-1)[0]?.queueId || 'Waiting for queue output'}</span><span>{events.filter(x => x.kind === 'queue_complete').slice(-1)[0]?.arm || ''}</span></div><div className="execution-actions">{active.status === 'running' && <button className="button secondary" onClick={() => void action('pause')}><CirclePause size={15}/> Pause</button>}{active.status === 'paused' && <button className="button secondary" onClick={() => void action('resume')}><CirclePlay size={15}/> Resume</button>}{['queued', 'running', 'paused'].includes(active.status) && <button className="button danger-quiet" onClick={() => void action('stop')}><Square size={13}/> Stop safely</button>}{active.status === 'completed' && <button className="button secondary" onClick={() => window.open(apiPath(`/api/runs/${active.id}/export`), '_blank')}><Download size={14}/> Export evidence bundle</button>}</div>{active.error && <div className="inline-error"><AlertTriangle size={14}/>{active.error}</div>}{active.status === 'failed' && <p className="failed-detail">This job is stopped and its error is recorded. Start a new run after addressing the issue.</p>}</> : <div className="empty-state tall"><Activity size={23}/><b>No run selected</b><span>Start the fixed development comparison to create a new reproducible record.</span></div>}</section>
      <section className="panel event-log-panel"><SectionTitle side={<span className="log-count">{events.length} recent events</span>}>Execution stream</SectionTitle><div className="event-log">{events.slice(-30).reverse().map((item, i) => <div className="log-row" key={`${item.kind}-${item.seq || i}`}><time>{new Date(item.at || Date.now()).toLocaleTimeString()}</time><span className={`log-kind ${item.kind}`}>{item.kind.replaceAll('_', ' ')}</span><span>{item.message || [item.queueId, item.arm, item.alerts && `${item.alerts} alerts`, item.groups && `${item.groups} groups`].filter(Boolean).join(' · ')}</span></div>)}{!events.length && <div className="empty-inline">Execution events will appear here from model output.</div>}</div></section></div>
    {result?.arms && <section className="panel result-panel"><SectionTitle side={<SourceTag tone="amber">{result.classification.replaceAll('_', ' ')}</SourceTag>}>Finalized experiment result</SectionTitle><div className="result-columns">{Object.entries(result.arms as Record<string, Metric>).map(([arm, metric]) => <div className="result-arm" key={arm}><div className="arm-heading"><b>{arm.replaceAll('_', ' ')}</b><span>{arm === 'baseline' ? 'reference' : metric.development_gate ? 'development gate passed' : 'development gate not passed'}</span></div><div className="result-metrics"><div><span>Recall@20</span><b>{formatPct(metric.incident_recall20)}</b><small>{metric.recall20_count}/{metric.expert_top20}</small></div><div><span>Recoverability</span><b>{formatPct(metric.group_recoverability)}</b><small>{metric.recoverable}/{metric.expert_top20}</small></div><div><span>P@10</span><b>{formatPct(metric.p10)}</b><small>{metric.p10_count}/{10 * metric.queues}</small></div><div><span>Pair precision</span><b>{formatPct(metric.grouped_pair_precision)}</b><small>{formatNum(metric.false_grouped_pairs)} false pairs</small></div></div></div>)}</div><p className="result-caveat">These development results are exploratory and should not be compared as a fresh holdout. The authoritative synthetic holdout remains the saved Phase 33 result.</p></section>}
  </div>;
}

function DatasetView({ notify }: { notify: (s: string) => void }) {
  const [items, setItems] = useState<Dataset[]>([]);
  const [selected, setSelected] = useState<Dataset | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const load = useCallback(async () => { try { const result = await api<{ datasets: Dataset[] }>('/api/datasets'); setItems(result.datasets); } catch (e) { setError(e instanceof Error ? e.message : 'Unable to load datasets'); } }, []);
  useEffect(() => { void load(); }, [load]);
  const upload = async (file?: File) => { if (!file) return; setBusy(true); setUploadProgress(0); setError(''); const body = new FormData(); body.append('file', file); try { const result = await new Promise<any>((resolve, reject) => { const request = new XMLHttpRequest(); request.open('POST', apiPath('/api/datasets/upload')); request.upload.onprogress = event => { if (event.lengthComputable) setUploadProgress(Math.round(event.loaded / event.total * 100)); }; request.onload = () => { let value: any = {}; try { value = JSON.parse(request.responseText); } catch { /* Report the HTTP status below. */ } if (request.status >= 200 && request.status < 300) resolve(value); else reject(new Error(value.detail || `Upload failed (${request.status})`)); }; request.onerror = () => reject(new Error('Upload connection failed')); request.send(body); }); const row: Dataset = { id: result.id, name: result.name, uploadedAt: new Date().toISOString(), bytes: result.bytes, sha256: result.sha256, format: result.format, rows: result.profile.rows, columns: result.profile.headers, profile: result.profile, validation: result.validation }; setSelected(row); await load(); notify(`Validated ${result.name}`); } catch (e) { setError(e instanceof Error ? e.message : 'Upload failed'); } finally { setBusy(false); if (input.current) input.current.value = ''; } };
  return <div className="page-content"><PageHeading title="Dataset laboratory" subtitle="Upload and inspect tabular research data with bounded server-side validation." right={<SourceTag tone="amber">MODEL INPUTS: NOT ENABLED</SourceTag>}/>
    <div className="dataset-layout"><section className="panel upload-panel"><SectionTitle side={<span className="upload-limit">50 MiB max</span>}>Add a dataset</SectionTitle><input ref={input} type="file" accept=".csv,.json,.jsonl" hidden onChange={e => void upload(e.target.files?.[0])}/><button className={`dropzone ${drag ? 'dragging' : ''}`} onClick={() => input.current?.click()} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={e => { e.preventDefault(); setDrag(false); void upload(e.dataTransfer.files[0]); }}><div className="upload-glyph">{busy ? <LoaderCircle className="spin" size={24}/> : <CloudUpload size={25}/>}</div><b>{busy ? `Uploading · ${uploadProgress}%` : 'Drop CSV, JSON, or JSONL here'}</b><span>{busy ? 'Backend validation follows file transfer' : 'Or browse files · up to 50 MiB'}</span><small>{busy ? 'Upload progress from the browser transfer event' : 'Files stay in the local dashboard runtime folder.'}</small>{busy && <div className="upload-progress"><i style={{ width: `${uploadProgress}%` }}/></div>}</button>{error && <div className="inline-error"><AlertTriangle size={14}/>{error}</div>}<div className="upload-format"><span><FileCheck2 size={14}/> CSV with header row</span><span><FileJson2 size={14}/> JSON array / data[]</span><span><FileJson2 size={14}/> JSONL objects</span></div><div className="upload-boundary"><AlertTriangle size={15}/><span>A valid table is not necessarily model-compatible. The frozen pipeline needs a complete receiver-visible evidence bundle, provenance roots, and the fixed research split.</span></div></section>
      <section className="panel stored-panel"><SectionTitle side={<SourceTag>{items.length} uploads</SourceTag>}>Uploaded files</SectionTitle>{items.length ? <div className="stored-list">{items.map(item => <button className={`stored-row ${selected?.id === item.id ? 'selected' : ''}`} key={item.id} onClick={() => setSelected(item)}><div className="file-mark">{item.format === 'csv' ? 'CSV' : 'JSON'}</div><span className="stored-main"><b>{item.name}</b><small>{formatNum(item.rows)} rows · {item.columns.length} columns · {formatBytes(item.bytes)}</small></span><span className="stored-state"><span className="signal-dot amber"/> inspected</span></button>)}</div> : <div className="empty-state"><Database size={21}/><b>No uploaded files yet</b><span>Add a CSV or JSON file for schema inspection.</span></div>}</section>
      {selected && <><section className="panel validation-panel"><SectionTitle side={<span className="pill amber">not compatible</span>}>Compatibility check</SectionTitle><div className="validation-icon"><AlertTriangle size={18}/></div><h3>This file cannot be used for frozen inference</h3><p>{selected.validation?.reason || 'A standalone file does not meet the receiver-visible input contract.'}</p><div className="hash-line"><span>SHA-256 fingerprint</span><code>{selected.sha256}</code></div><div className="validation-source">Upload validation confirms file structure only. It does not fit, alter or invoke a model.</div></section><section className="panel schema-panel"><SectionTitle side={<span>{selected.profile?.rows?.toLocaleString()} rows · {selected.columns.length} columns</span>}>Feature profile</SectionTitle><div className="scroll-table schema-scroll"><table><thead><tr><th>Column</th><th>Type</th><th>Missing</th></tr></thead><tbody>{(selected.profile?.features || []).map((feature: any) => <tr key={feature.name}><td><code>{feature.name}</code></td><td>{feature.types.join(', ')}</td><td>{feature.missing ?? (feature.missing_in_preview != null ? `${feature.missing_in_preview} / preview` : '—')}</td></tr>)}</tbody></table></div><div className="preview-label"><span>First {selected.profile?.preview?.length || 0} rows · browser preview capped</span><button className="text-link" onClick={() => window.open(apiPath(`/api/datasets/${selected.id}/export`), '_blank')}>Download original <Download size={13}/></button></div><pre className="json-preview">{JSON.stringify(selected.profile?.preview?.slice(0, 6) || [], null, 2)}</pre></section></>}
    </div>
  </div>;
}

function ArchitectureView() {
  const [architecture, setArchitecture] = useState<any>(null);
  const [status, setStatus] = useState<any>(null);
  const [selected, setSelected] = useState('verify');
  useEffect(() => { Promise.all([api('/api/architecture'), api('/api/health')]).then(([a, s]) => { setArchitecture(a); setStatus(s); }).catch(() => undefined); }, []);
  const components = architecture?.components || [];
  const active = components.find((x: any) => x.id === selected);
  const labels = ['input', 'correlate', 'verify', 'prioritize', 'queue'];
  return <div className="page-content"><PageHeading title="CPV architecture" subtitle="Implementation map of the frozen synthetic pipeline; stages and outcomes follow repository code." right={<SourceTag tone="blue">2D COMPONENT MAP</SourceTag>}/>
    <section className="panel architecture-panel"><SectionTitle side={<SourceTag tone="amber">{architecture?.classification || 'loading code map'}</SourceTag>}>Evidence flow</SectionTitle><div className="arch-map">{labels.map((id, i) => { const node = components.find((x: any) => x.id === id); return <div className={`arch-node-wrap ${selected === id ? 'selected' : ''}`} key={id}><button className={`arch-node ${id === 'verify' ? 'verification' : ''} ${id === 'input' || id === 'queue' ? 'endpoint' : ''}`} onClick={() => setSelected(id)}><span className="arch-node-status"><i className={`signal-dot ${id === 'verify' ? 'amber' : 'green'}`}/>{id === 'input' ? 'receiver-visible' : id === 'queue' ? 'analyst review' : 'implemented'}</span><div className="arch-node-title">{node?.label}</div><div className="arch-node-source">{node?.source}</div></button>{i < labels.length - 1 && <div className="arch-connector"><span/><small>{i === 1 ? 'proposed links' : i === 2 ? 'verified groups' : 'ranked evidence'}</small><i/></div>}</div>; })}</div><div className="arch-detail"><div className="arch-detail-head"><div className="step-icon">{active?.label?.[0] || '·'}</div><div><span>SELECTED COMPONENT</span><h3>{active?.label}</h3></div></div><div className="arch-detail-copy"><div><span>Purpose</span><p>{active?.purpose || 'Select a component to inspect its contract.'}</p></div><div><span>Source implementation</span><p className="mono">{active?.source || '—'}</p></div><div><span>Latest state</span><p>{active?.id === 'verify' ? 'Recorded queue replay only · run-specific outcomes appear in replay and experiment views.' : status?.status === 'ready' ? 'Source module available · no current real SOC stream.' : 'Checking backend source availability.'}</p></div></div></div></section>
    <div className="architecture-lower"><section className="panel contract-panel"><SectionTitle>Decision contract</SectionTitle><div className="contract-row"><span className="decision-mark accepted"><Check size={12}/></span><div><b>Accepted</b><small>Relationship supported by the verifier’s visible evidence checks.</small></div></div><div className="contract-row"><span className="decision-mark rejected"><X size={12}/></span><div><b>Rejected</b><small>Evidence failed an explicit relationship or context rule.</small></div></div><div className="contract-row"><span className="decision-mark abstained"><CircleHelp size={12}/></span><div><b>Abstained</b><small>Evidence was missing, late, insufficient or ambiguous.</small></div></div></section><section className="panel scope-panel"><SectionTitle>System boundary</SectionTitle><p>{architecture?.readiness || 'Real-world inference status is unavailable.'}</p><p>{architecture?.actions || 'No automated response action is implemented.'}</p><SourceTag tone="amber">No containment / remediation stage</SourceTag></section></div>
  </div>;
}

function HistoryView({ notify }: { notify: (s: string) => void }) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [filter, setFilter] = useState('all');
  useEffect(() => { api<{ runs: Run[] }>('/api/runs').then(x => setRuns(x.runs)).catch(() => undefined); const t = window.setInterval(() => api<{ runs: Run[] }>('/api/runs').then(x => setRuns(x.runs)).catch(() => undefined), 3000); return () => clearInterval(t); }, []);
  const shown = runs.filter(x => filter === 'all' || x.status === filter);
  return <div className="page-content"><PageHeading title="Experiment history" subtitle="Persisted run states, configurations, model outputs, metrics and integrity seals." right={<label className="history-filter"><ListFilter size={14}/><select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All states</option>{['completed', 'running', 'paused', 'failed', 'cancelled'].map(x => <option key={x}>{x}</option>)}</select></label>}/>
    <section className="panel history-panel"><SectionTitle side={<SourceTag>{shown.length} records</SourceTag>}>Run ledger</SectionTitle>{shown.length ? <div className="scroll-table history-scroll"><table><thead><tr><th>Run / ID</th><th>Cohort</th><th>Created</th><th>Model arms</th><th>Status</th><th>Result</th><th>Evidence</th></tr></thead><tbody>{shown.map(run => <tr key={run.id}><td><b>{run.config?.name || run.result?.name || 'Untitled experiment'}</b><code className="sub-cell">{run.id}</code></td><td>Controlled synthetic · development</td><td>{run.created_at ? new Date(run.created_at).toLocaleString() : '—'}</td><td>Phase 31 + Phase 32 ×2</td><td><span className={`pill ${run.status === 'completed' ? 'green' : run.status === 'failed' ? 'red' : 'amber'}`}>{run.status}</span></td><td>{run.result ? formatPct(run.result.arms?.candidate_bonus1?.incident_recall20) + ' recall@20' : run.error || '—'}</td><td>{run.status === 'completed' ? <button className="text-link" onClick={() => { window.open(apiPath(`/api/runs/${run.id}/export`), '_blank'); notify('Evidence bundle download started'); }}>Export ZIP <Download size={12}/></button> : '—'}</td></tr>)}</tbody></table></div> : <div className="empty-state tall"><Clock3 size={22}/><b>No saved experiment runs</b><span>Completed Phase 32 development comparisons will appear here.</span></div>}</section>
    <div className="history-note"><HardDrive size={14}/><span>Run metadata and outputs are stored locally in SQLite and <code>dashboard/runtime/runs/</code>. The frozen Phase 33 benchmark remains a separate, immutable recorded artifact.</span></div>
  </div>;
}

function SearchDialog({ query, setQuery, close, navigate }: { query: string; setQuery: (x: string) => void; close: () => void; navigate: (x: View) => void }) {
  const [runs, setRuns] = useState<Run[]>([]); const [datasets, setDatasets] = useState<Dataset[]>([]);
  useEffect(() => { api<{ runs: Run[] }>('/api/runs').then(x => setRuns(x.runs)).catch(() => undefined); api<{ datasets: Dataset[] }>('/api/datasets').then(x => setDatasets(x.datasets)).catch(() => undefined); }, []);
  const q = query.trim().toLowerCase(); const runRows = runs.filter(x => !q || x.id.toLowerCase().includes(q) || x.config?.name?.toLowerCase().includes(q)); const fileRows = datasets.filter(x => !q || x.name.toLowerCase().includes(q));
  return <div className="dialog-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) close(); }}><div className="search-dialog" role="dialog" aria-modal="true" aria-label="Search command center"><div className="dialog-search"><Search size={17}/><input autoFocus placeholder="Search experiment IDs, uploaded datasets…" value={query} onChange={e => setQuery(e.target.value)}/><button onClick={close} aria-label="Close search"><X size={16}/></button></div><div className="search-results">{[['Navigation', nav.filter(x => !q || x.label.toLowerCase().includes(q)).map(x => ({ label: x.label, detail: 'Open workspace', action: () => navigate(x.id), icon: x.icon }))], ['Experiments', runRows.map(x => ({ label: x.config?.name || x.id, detail: `${x.id} · ${x.status}`, action: () => navigate('history'), icon: GitBranch }))], ['Datasets', fileRows.map(x => ({ label: x.name, detail: `${x.rows.toLocaleString()} rows · ${x.format.toUpperCase()}`, action: () => navigate('datasets'), icon: Database }))]].map(([heading, rows]: any) => rows.length > 0 && <div key={heading}><div className="search-group-label">{heading}</div>{rows.map((item: any, i: number) => <button className="search-result" key={`${heading}-${i}`} onClick={item.action}><item.icon size={15}/><span><b>{item.label}</b><small>{item.detail}</small></span></button>)}</div>)}{!runRows.length && !fileRows.length && !nav.some(x => x.label.toLowerCase().includes(q)) && <div className="empty-inline">No matching records.</div>}</div><div className="dialog-hint"><span><kbd>ESC</kbd> close</span><span><kbd>↵</kbd> open result</span></div></div></div>;
}

function GuidedDemo({ overview, close, navigate }: { overview: Overview | null; close: () => void; navigate: (x: View) => void }) {
  const [step, setStep] = useState(0);
  const candidate = overview?.benchmark.candidate;
  const baseline = overview?.benchmark.baseline;
  const stages: { title: string; detail: string; view: View; metric: string; value: string }[] = [
    { title: 'Research question', detail: 'Can independent, time-valid source evidence safely recover more related alert fragments before those groups are prioritized?', view: 'command', metric: 'Cohort', value: 'Controlled synthetic' },
    { title: 'Architecture', detail: 'C proposes links, V checks the original evidence and chronology, and P ranks verified groups for analyst review.', view: 'architecture', metric: 'Pipeline', value: 'Correlate · Verify · Prioritize' },
    { title: 'Evidence flow', detail: 'The verifier checks source-root independence, original endpoint observations, causal fields, matching context and a minute-100 cutoff.', view: 'architecture', metric: 'Evidence roots', value: 'Endpoint + identity + network' },
    { title: 'Dataset boundary', detail: 'The demonstrated holdout is a fixed, receiver-visible synthetic bundle. Uploaded tables can be inspected, but they cannot satisfy this input contract.', view: 'datasets', metric: 'Locked test', value: `${formatNum(candidate?.queues)} queues · ${formatNum(candidate?.eligible_alerts)} eligible alerts` },
    { title: 'Experiment setup', detail: 'A repeatable comparison runs the Phase 31 baseline and Phase 32 +1 / +2 candidates on the previously accessed development split.', view: 'experiments', metric: 'Development split', value: '10 queues · seed 31102' },
    { title: 'Processing', detail: 'Queue jobs execute the repository model functions. Prediction files are sealed before the official evaluator reads development truth.', view: 'experiments', metric: 'Lifecycle', value: 'Run · pause · resume · stop' },
    { title: 'Group reconstruction', detail: 'The output is a ranked partition of alerts into proposed groups. It does not classify malware or trigger containment.', view: 'replay', metric: 'Candidate groups', value: formatNum(candidate?.predicted_groups) },
    { title: 'Verifier decisions', detail: 'Inspect actual accepted, rejected and abstained relationships, their source IDs and reasons in the saved queue replay.', view: 'replay', metric: 'Fallback unions', value: `${overview?.benchmark.fallbackTrue ?? '—'} / ${overview?.benchmark.fallbackUnions ?? '—'} true in Phase 33 simulator truth` },
    { title: 'Paired outcome', detail: 'The unchanged candidate and baseline used the same 15-queue holdout and the same evaluator. The candidate recalled ten additional priority incidents at top 20.', view: 'command', metric: 'Recall@20', value: `${candidate?.recall20_count ?? '—'} / ${candidate?.expert_top20 ?? '—'} vs ${baseline?.recall20_count ?? '—'} / ${baseline?.expert_top20 ?? '—'}` },
    { title: 'Conclusion and readiness', detail: 'Phase 33 passed its declared synthetic gate. Phase 39 made no real-SOC predictions; authorization, provenance, temporal fields and a suitable external cohort remain required.', view: 'command', metric: 'Real-SOC readiness', value: 'NO-GO · not measured' },
  ];
  useEffect(() => {
    const key = (event: KeyboardEvent) => { if (event.key === 'Escape') close(); if (event.key === 'ArrowRight') setStep(x => Math.min(stages.length - 1, x + 1)); if (event.key === 'ArrowLeft') setStep(x => Math.max(0, x - 1)); };
    window.addEventListener('keydown', key); return () => window.removeEventListener('keydown', key);
  }, [close, stages.length]);
  const current = stages[step];
  return <div className="demo-screen" role="dialog" aria-modal="true" aria-label="Guided research demonstration"><header className="demo-top"><span><span className="demo-mark"/><b>Guided research demonstration</b><i>recorded evidence · synthetic cohort</i></span><button onClick={close} aria-label="Close guided demo"><X size={17}/> Exit</button></header><div className="demo-progress">{stages.map((x, i) => <button key={x.title} aria-label={`Go to step ${i + 1}: ${x.title}`} title={x.title} className={`${i === step ? 'current' : ''} ${i < step ? 'visited' : ''}`} onClick={() => setStep(i)}/>)}</div><main className="demo-main"><div className="demo-counter">RESEARCH WALKTHROUGH <span>{String(step + 1).padStart(2, '0')} / {String(stages.length).padStart(2, '0')}</span></div><h1>{current.title}</h1><p>{current.detail}</p><div className="demo-measure"><span>{current.metric}</span><b>{current.value}</b></div><button className="button secondary" onClick={() => { navigate(current.view); close(); }}>Open {nav.find(x => x.id === current.view)?.label}</button></main><footer className="demo-footer"><span>Phase 33 GO applies to the controlled synthetic cohort only.</span><div><button className="button quiet" disabled={step === 0} onClick={() => setStep(x => Math.max(0, x - 1))}>Previous</button><button className="button primary" onClick={() => step === stages.length - 1 ? close() : setStep(x => Math.min(stages.length - 1, x + 1))}>{step === stages.length - 1 ? 'Finish walkthrough' : 'Next section'}</button></div></footer></div>;
}
