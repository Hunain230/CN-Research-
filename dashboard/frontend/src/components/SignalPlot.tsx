import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import type { Lane, ReplayBundle } from '../data/types';
import type { ReplayIndex } from '../data/replay-engine';

type Hover = { x: number; y: number; heading: string; lines: string[] } | null;
type Props = { lane: Exclude<Lane, 'handoff'>; bundle: ReplayBundle; index: ReplayIndex; cursor: number };
const color = { paper: '#17191d', grid: '#30353b', text: '#d9dde1', muted: '#8b929b', accent: '#a86ddd', accepted: '#59c58d', cursor: '#e1dce5' };

export default function SignalPlot({ lane, bundle, index, cursor }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<Hover>(null);
  const visibleEndpoints = useMemo(() => {
    const byMinute = new Map<number, string[]>();
    index.acceptedLinks.filter(link => link.visibleAt <= cursor).forEach(link => {
      Object.entries(link.minuteByEndpoint).forEach(([alertId, minute]) => {
        const list = byMinute.get(minute) || [];
        list.push(`${alertId} · ${link.decision.relationship_token}`);
        byMinute.set(minute, list);
      });
    });
    return byMinute;
  }, [cursor, index]);
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    canvas.width = Math.floor(rect.width * ratio); canvas.height = Math.floor(rect.height * ratio);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(ratio, ratio);
    const w = rect.width; const h = rect.height; const left = 54; const right = 18; const top = 30; const bottom = 38;
    ctx.clearRect(0, 0, w, h); ctx.fillStyle = color.paper; ctx.fillRect(0, 0, w, h);
    const pw = Math.max(1, w - left - right); const ph = Math.max(1, h - top - bottom);
    const upper = lane === 'incoming' ? Math.floor(ph * .57) : ph;
    const lowerTop = top + upper + 33; const lowerH = Math.max(1, h - bottom - lowerTop);
    const label = (x: number, y: number, text: string, align: CanvasTextAlign = 'left') => { ctx.fillStyle = color.muted; ctx.font = '10px "IBM Plex Mono", monospace'; ctx.textAlign = align; ctx.fillText(text, x, y); };
    ctx.strokeStyle = color.grid; ctx.lineWidth = 1; ctx.setLineDash([2, 5]);
    for (let i = 0; i <= 4; i += 1) { const y = top + (upper * i) / 4; ctx.beginPath(); ctx.moveTo(left, y + .5); ctx.lineTo(w - right, y + .5); ctx.stroke(); }
    ctx.setLineDash([]);
    if (lane === 'incoming') {
      const points = index.minutes;
      if (!points.length) return;
      const min = points[0].minute; const max = points[points.length - 1].minute; const span = Math.max(1, max - min);
      const xAt = (minute: number) => left + ((minute - min) / span) * pw;
      const peak = Math.max(1, ...points.map(p => p.rows)); const barW = Math.max(1.2, Math.min(7, (pw / points.length) * .74));
      ctx.fillStyle = 'rgba(168,109,221,.84)';
      points.forEach(point => { const x = xAt(point.minute); const bh = (point.rows / peak) * Math.max(1, upper - 19); ctx.fillRect(x - barW / 2, top + upper - bh, barW, bh); });
      label(left - 8, top + 4, String(peak), 'right'); label(left - 8, top + upper, '0', 'right');
      label(left, top - 9, 'Alert rows / event minute'); label(w - right, top - 9, 'RECORDED ROWS', 'right');
      const sevMax = Math.max(1, ...points.map(p => p.maxSeverity)); const sevBottom = h - bottom; const yAt = (v: number) => sevBottom - (v / sevMax) * lowerH;
      ctx.strokeStyle = color.accent; ctx.lineWidth = 1.8; ctx.beginPath();
      points.forEach((point, i) => { const x = xAt(point.minute); const y = yAt(point.maxSeverity); if (i === 0) ctx.moveTo(x, y); else { const prev = points[i - 1]; ctx.lineTo(x, yAt(prev.maxSeverity)); ctx.lineTo(x, y); } }); ctx.stroke();
      label(left - 8, lowerTop + 4, String(sevMax), 'right'); label(left - 8, sevBottom, '0', 'right');
      label(left, lowerTop - 8, 'Source severity · maximum recorded value');
      label(left, h - 10, String(min)); label(left + pw / 2, h - 10, String(Math.round((min + max) / 2)), 'center'); label(w - right, h - 10, String(max), 'right'); label(left + pw / 2, h - 23, 'Event minute', 'center');
      // Mark only endpoints whose accepted relationship names an alert and whose alert has a recorded minute.
      ctx.fillStyle = color.accepted;
      for (const minute of visibleEndpoints.keys()) { const x = xAt(minute); const y = top + 8; ctx.beginPath(); ctx.moveTo(x, y - 4); ctx.lineTo(x + 4, y); ctx.lineTo(x, y + 4); ctx.lineTo(x - 4, y); ctx.closePath(); ctx.fill(); }
      const current = cursor > 0 ? bundle.alerts[cursor - 1] : undefined;
      if (current) { const x = xAt(current.event_minute); ctx.strokeStyle = color.cursor; ctx.globalAlpha = .72; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, h - bottom); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1; }
      if (hover) { const target = min + ((hover.x - left) / pw) * span; const point = points.reduce((best, p) => Math.abs(p.minute - target) < Math.abs(best.minute - target) ? p : best, points[0]); const x = xAt(point.minute); crosshair(ctx, x, top, h - bottom); }
    } else {
      const values = lane === 'verification' ? index.acceptedByCursor : index.rootsByCursor;
      const maximum = Math.max(1, ...values); const xAt = (i: number) => left + (i / Math.max(1, values.length - 1)) * pw; const yAt = (v: number) => top + upper - (v / maximum) * Math.max(1, upper - 20);
      ctx.strokeStyle = color.accent; ctx.lineWidth = 2; ctx.beginPath();
      values.forEach((v, i) => { const x = xAt(i); const y = yAt(v); if (i === 0) ctx.moveTo(x, y); else { ctx.lineTo(x, yAt(values[i - 1])); ctx.lineTo(x, y); } }); ctx.stroke();
      for (let i = 0; i <= 4; i += 1) label(left - 8, top + (upper * i) / 4 + 4, String(Math.round(maximum - (maximum * i) / 4)), 'right');
      label(left, top - 9, lane === 'verification' ? 'Accepted relationships reached' : 'Distinct provenance roots reached'); label(w - right, top - 9, 'RECORDED ROW ORDER', 'right');
      const cx = xAt(cursor); ctx.strokeStyle = color.cursor; ctx.globalAlpha = .72; ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(cx, top); ctx.lineTo(cx, top + upper); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
      label(left, h - 10, '0'); label(left + pw / 2, h - 10, String(Math.floor(bundle.alerts.length / 2)), 'center'); label(w - right, h - 10, String(bundle.alerts.length), 'right'); label(left + pw / 2, h - 23, 'Replay row index', 'center');
      if (hover) { const row = Math.max(0, Math.min(values.length - 1, Math.round(((hover.x - left) / pw) * (values.length - 1)))); crosshair(ctx, xAt(row), top, top + upper); }
    }
  }, [bundle, cursor, hover, index, lane, visibleEndpoints]);
  useEffect(() => {
    draw(); const node = canvasRef.current; if (!node) return;
    const observer = new ResizeObserver(draw); observer.observe(node); return () => observer.disconnect();
  }, [draw]);

  function onMove(event: ReactPointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect(); const x = event.clientX - rect.left; const y = event.clientY - rect.top; const px = Math.max(0, Math.min(1, (x - 54) / Math.max(1, rect.width - 72)));
    if (lane === 'incoming' && index.minutes.length) {
      const min = index.minutes[0].minute; const max = index.minutes.at(-1)!.minute; const target = min + px * Math.max(1, max - min);
      const p = index.minutes.reduce((best, item) => Math.abs(item.minute - target) < Math.abs(best.minute - target) ? item : best, index.minutes[0]);
      const endpoints = visibleEndpoints.get(p.minute) || [];
      setHover({ x, y, heading: `Event minute ${p.minute}`, lines: [`Alert rows: ${p.rows}`, `Source severity max: ${p.maxSeverity}`, ...(endpoints.length ? [`Accepted endpoints: ${endpoints.length}`, ...endpoints.slice(0, 3)] : [])] });
    } else {
      const row = Math.round(px * bundle.alerts.length); const values = lane === 'verification' ? index.acceptedByCursor : index.rootsByCursor; const value = values[Math.max(0, Math.min(values.length - 1, row))] || 0;
      setHover({ x, y, heading: `Recorded row ${row}`, lines: [`${lane === 'verification' ? 'Accepted relationships' : 'Distinct provenance roots'}: ${value}`] });
    }
  }

  return <div className="plot-wrap" onPointerLeave={() => setHover(null)}>
    <canvas ref={canvasRef} className="signal-canvas" onPointerMove={onMove} role="img" aria-label={lane === 'incoming' ? 'Recorded alert rows and maximum source severity by event minute. Green markers identify accepted relationship endpoints.' : lane === 'verification' ? 'Accepted verifier relationships reached in recorded row order.' : 'Distinct emitted provenance roots reached in recorded row order.'} />
    {hover && <div className="plot-tooltip" style={{ left: `${Math.max(55, Math.min(72, (hover.x / (canvasRef.current?.clientWidth || 1)) * 100))}%`, top: `${Math.max(18, hover.y - 12)}px` }}><b>{hover.heading}</b>{hover.lines.map(line => <span key={line}>{line}</span>)}</div>}
  </div>;
}

function crosshair(ctx: CanvasRenderingContext2D, x: number, top: number, bottom: number) {
  ctx.strokeStyle = color.cursor; ctx.globalAlpha = .5; ctx.setLineDash([3, 4]); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, bottom); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
}
