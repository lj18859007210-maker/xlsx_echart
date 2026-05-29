import { useState } from "react";
import ReactECharts from "echarts-for-react";
import type { ChartSpec } from "../../types/results";

type Props = {
  charts: ChartSpec[];
  onDataPointClick?: (seriesIndex: number, dataIndex: number) => void;
};

export function ChartCanvas({ charts, onDataPointClick }: Props) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (charts.length === 0) {
    return (
      <section className="chart-section">
        <h2>图表</h2>
        <div className="empty-state">
          <p>暂无图表数据</p>
        </div>
      </section>
    );
  }

  const spec = charts[activeIndex];
  if (!spec) return null;

  const option = buildEChartsOption(spec);

  return (
    <section className="chart-section">
      <div className="chart-header">
        <h2>{spec.title}</h2>
        <div className="chart-tabs">
          {charts.map((c, i) => (
            <button
              key={i}
              className={`chart-tab${i === activeIndex ? " is-active" : ""}`}
              onClick={() => setActiveIndex(i)}
              type="button"
            >
              {_chartLabel(c.chart_type)}
            </button>
          ))}
        </div>
      </div>

      <div className="chart-container">
        <ReactECharts
          option={option}
          style={{ height: 400, width: "100%" }}
          notMerge
          onEvents={{
            click: (params: { seriesIndex?: number; dataIndex?: number }) => {
              if (params.dataIndex != null) {
                onDataPointClick?.(params.seriesIndex ?? 0, params.dataIndex);
              }
            },
          }}
        />
      </div>

      {spec.filter_conditions && (
        <p className="chart-meta">筛选条件: {spec.filter_conditions}</p>
      )}
      {spec.reason && (
        <p className="chart-meta">推荐理由: {spec.reason}</p>
      )}
      {spec.highlights.length > 0 && (
        <div className="chart-highlights">
          <p className="chart-meta">异常标注:</p>
          {spec.highlights.map((h, i) => (
            <span key={i} className="highlight-tag">
              {h.series_name}[{h.data_index}] = {h.value} ({h.reason})
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

function buildEChartsOption(spec: ChartSpec) {
  const typeMap: Record<string, string> = {
    bar: "bar", grouped_bar: "bar", stacked_bar: "bar", horizontal_bar: "bar",
    line: "line", pie: "pie", scatter: "scatter",
  };

  const eType = typeMap[spec.chart_type] ?? "bar";
  const isPie = spec.chart_type === "pie";
  const isHorizontal = spec.chart_type === "horizontal_bar";
  const isStacked = spec.chart_type === "stacked_bar";

  // Use x_data from spec, fall back to indices
  const xLabels: (string | number)[] =
    spec.x_data && spec.x_data.length > 0
      ? spec.x_data.map((v) => (typeof v === "string" || typeof v === "number" ? v : String(v)))
      : spec.series[0]?.data?.map((_, i) => i) ?? [];

  const seriesData = spec.series.map((s) => ({
    name: s.name,
    type: eType,
    data: s.data,
    ...(isStacked ? { stack: "total" } : {}),
  }));

  if (isPie) {
    const pieData = spec.series.flatMap((s) =>
      (s.data ?? []).map((v, i) => ({
        name: xLabels[i] != null ? String(xLabels[i]) : `${s.name}[${i}]`,
        value: v,
      })),
    );
    return {
      title: { text: spec.title, left: "center" },
      tooltip: { trigger: "item" },
      legend: { bottom: 0 },
      series: [{ type: "pie", radius: "60%", data: pieData }],
    };
  }

  const base: Record<string, unknown> = {
    title: { text: spec.title, left: "center" },
    tooltip: { trigger: "axis" },
    legend: { data: spec.y_fields, bottom: 0 },
    xAxis: { type: "category", data: xLabels },
    yAxis: { type: "value" },
    series: seriesData,
  };

  if (isHorizontal) {
    base.yAxis = { type: "category", data: xLabels };
    base.xAxis = { type: "value" };
  }

  return base;
}

function _chartLabel(chartType: string): string {
  const labels: Record<string, string> = {
    bar: "柱状图", line: "折线图", pie: "饼图", scatter: "散点图",
    grouped_bar: "分组柱状", stacked_bar: "堆叠柱状", horizontal_bar: "条形图",
  };
  return labels[chartType] ?? chartType;
}