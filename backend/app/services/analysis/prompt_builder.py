"""Day 20 - analysis prompt builder.

Constructs the system + user prompt for the LLM analysis call.
The prompt is CRITICAL - it enforces evidence citation and hallucination prevention.
"""

from __future__ import annotations

import json

SYSTEM_PROMPT = """\
You are a senior financial data analyst. You analyze structured data summaries
and produce actionable business insights.

CRITICAL RULES - YOU MUST FOLLOW ALL OF THEM:

1. DATA-ONLY: Only use data explicitly present in the context package below.
   Do NOT fabricate, guess, or extrapolate numbers not shown.

2. EVIDENCE REQUIRED: Every finding MUST include an "evidence" array citing
   the source: sheet name, metric name, row index, column index, and the
   actual value from the data.

3. UNCERTAINTY: If you are unsure about any conclusion, say so explicitly
   and mark it as "needs_human_review": true.

4. HIGH-RISK FINDINGS: Any finding with severity "critical" MUST include
   the phrase "\u5efa\u8bae\u4eba\u5de5\u590d\u6838" in the description.

5. LANGUAGE: Respond in Chinese (Simplified). Keep descriptions concise
   and actionable. Avoid vague statements like "\u6570\u636e\u8868\u73b0\u826f\u597d".

6. JSON ONLY: Your entire response must be a single valid JSON object.
   No markdown, no code fences, no explanatory text outside the JSON.

7. CHARTS: Suggest up to 3 chart types that would best visualize the data,
   with specific metrics and dimensions from the semantic schema.
"""

USER_PROMPT_TEMPLATE = """\
Analyze the following data context package and produce a structured business
analysis report in JSON format.

=== CONTEXT PACKAGE ===
{context_json}

=== REQUIRED OUTPUT STRUCTURE ===
{{
  "executive_summary": "2-4 sentence overview of the key findings in Chinese",
  "key_findings": [
    {{
      "title": "Short finding title",
      "description": "Detailed explanation with specific numbers",
      "severity": "info|warning|critical",
      "needs_human_review": false,
      "evidence": [
        {{
          "sheet": "Sheet name",
          "metric": "Metric/column name",
          "row": 1,
          "col": 2,
          "value": "actual value from data",
          "context": "why this evidence matters"
        }}
      ]
    }}
  ],
  "risks": [
    {{
      "title": "Risk title",
      "description": "What could go wrong and impact",
      "severity": "warning|critical",
      "mitigation": "Suggested action"
    }}
  ],
  "recommendations": [
    {{
      "title": "Recommendation title",
      "description": "Specific actionable recommendation",
      "priority": "high|medium|low",
      "expected_impact": "What happens if implemented"
    }}
  ],
  "chart_hints": [
    {{
      "chart_type": "bar|line|pie|scatter",
      "title": "Chart title",
      "metrics": ["metric_name_1", "metric_name_2"],
      "dimension": "dimension_column_name",
      "reason": "Why this chart type fits the data"
    }}
  ]
}}
"""


def build_analysis_prompt(context_package: dict[str, object]) -> tuple[str, str]:
    """Build system and user prompts for the analysis LLM call.

    Returns (system_prompt, user_prompt).
    """
    context_json = json.dumps(context_package, ensure_ascii=False, indent=2, default=str)
    user_prompt = USER_PROMPT_TEMPLATE.format(context_json=context_json)
    return SYSTEM_PROMPT, user_prompt