import { useEffect, useRef } from 'react';
import { init, use } from 'echarts/core';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import { LineChart, ScatterChart } from 'echarts/charts';
import { GridComponent, LegendComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

use([LineChart, ScatterChart, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, CanvasRenderer]);

export default function ScientificChart({ option, style }: { option: EChartsCoreOption; style: React.CSSProperties }) {
  const host = useRef<HTMLDivElement>(null);
  const instance = useRef<EChartsType | null>(null);
  useEffect(() => {
    if (!host.current) return;
    const chart = init(host.current, undefined, { renderer: 'canvas' });
    instance.current = chart;
    const resize = new ResizeObserver(() => chart.resize());
    resize.observe(host.current);
    return () => { resize.disconnect(); chart.dispose(); instance.current = null; };
  }, []);
  useEffect(() => { instance.current?.setOption(option, true); }, [option]);
  return <div ref={host} style={style} role="img" aria-label="Scientific time-series visualization"/>;
}
