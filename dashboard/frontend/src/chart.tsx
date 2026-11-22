import { useEffect, useRef } from 'react';
import { init, use } from 'echarts/core';
import type { EChartsCoreOption, EChartsType } from 'echarts/core';
import { BarChart, LineChart, ScatterChart } from 'echarts/charts';
import { DataZoomInsideComponent, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

use([BarChart, LineChart, ScatterChart, GridComponent, LegendComponent, MarkAreaComponent, MarkLineComponent, DataZoomInsideComponent, TooltipComponent, CanvasRenderer]);

export default function ScientificChart({ option, style, onEvent }: { option: EChartsCoreOption; style: React.CSSProperties; onEvent?: (event: any) => void }) {
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
  useEffect(() => {
    const chart = instance.current;
    if (!chart || !onEvent) return;
    chart.on('click', onEvent);
    return () => { chart.off('click', onEvent); };
  }, [onEvent]);
  useEffect(() => { instance.current?.setOption(option, { notMerge: true, lazyUpdate: true }); }, [option]);
  return <div ref={host} style={style} role="img" aria-label="Scientific time-series visualization"/>;
}
