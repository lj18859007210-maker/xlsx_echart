/** Day 22 results page types. */

export type SummaryRecord = {
  task_id: number;
  statistical_summary: StatisticalColumn[];
  validation_issues_summary: IssueAggregation;
  anomaly_summary: IssueAggregation;
  slices: SliceItem[];
  semantic_schema: SemanticColumn[];
  token_estimate: number;
  token_budget: number;
  trimmed: boolean;
};

export type StatisticalColumn = {
  sheet_name: string;
  column_name: string;
  kind: string;
  count: number;
  mean: number | null;
  median: number | null;
  min: number | null;
  max: number | null;
  volatility: number | null;
  missing_rate: number;
  trend: string;
};

export type IssueAggregation = {
  total: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  top_issues: IssueItem[];
};

export type IssueItem = {
  id?: number;
  sheet_id?: number;
  sheet_name?: string;
  row_index: number;
  col_index: number;
  issue_type: string;
  severity: string;
  reason: string;
  expected_value?: number | null;
  actual_value?: number | null;
  metric_name?: string;
  detection_source?: string;
  formula_text?: string;
  score?: number;
};

export type SliceItem = {
  sheet_name: string;
  header: string[];
  rows: Array<Array<string | null>>;
  issue_cells: IssueCellRef[];
};

export type IssueCellRef = {
  row: number;
  col: number;
  reason: string;
  severity: string;
};

export type SemanticColumn = {
  sheet_name: string;
  column_kinds: string[];
  column_paths: Array<Array<string>>;
};

export type InsightRecord = {
  task_id: number;
  version_no: number;
  executive_summary: string;
  key_findings: Finding[];
  risks: Risk[];
  recommendations: Recommendation[];
  chart_hints: ChartHint[];
  citations: Citation[];
  model_name: string;
  prompt_version?: string;
};

export type Finding = {
  title: string;
  description: string;
  severity: string;
  needs_human_review?: boolean;
  evidence?: Evidence[];
};

export type Risk = {
  title: string;
  description: string;
  severity: string;
  mitigation?: string;
};

export type Recommendation = {
  title: string;
  description: string;
  priority: string;
  expected_impact?: string;
};

export type ChartHint = {
  chart_type: string;
  title: string;
  metrics: string[];
  dimension: string;
  reason: string;
};

export type Evidence = {
  sheet: string;
  metric: string;
  row: number;
  col: number;
  value: string;
  context: string;
};

export type Citation = {
  finding_index: number;
  finding_title: string;
  evidence_index: number;
  sheet: string;
  metric: string;
  row: number;
  col: number;
  value: string;
};

export type ChartSpecRecord = {
  task_id: number;
  total: number;
  charts: ChartSpec[];
};

export type ChartSpec = {
  x_data?: Array<string | number>;
  chart_index?: number;
  chart_type: string;
  title: string;
  x_field: string;
  y_fields: string[];
  series: ChartSeries[];
  highlights: ChartHighlight[];
  source_cells: string[];
  filter_conditions: string;
  reason: string;
};

export type ChartSeries = {
  name: string;
  data: Array<number | null>;
};

export type ChartHighlight = {
  series_index: number;
  series_name: string;
  data_index: number;
  value: number;
  reason: string;
};

export type ValidationIssueItem = {
  id: number;
  sheet_id: number;
  row_index: number;
  col_index: number;
  expected_value: number | null;
  actual_value: number | null;
  formula_text: string;
  formula_type: string;
  severity: string;
  issue_type: string;
};

export type AnomalyIssueItem = {
  id: number;
  sheet_id: number;
  row_index: number;
  col_index: number;
  issue_type: string;
  severity: string;
  reason: string;
  metric_name: string | null;
  detection_source: string;
  score: number | null;
};