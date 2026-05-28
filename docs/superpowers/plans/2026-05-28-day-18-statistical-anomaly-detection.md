# Day 18：统计异常检测（IQR）

**日期：** 2026-05-28
**状态：** in_progress
**依赖：** Day 17（业务规则异常检测完成）

---

## 目标

在 Day 17 业务规则基础上，接入 IQR 四分位距统计模型，按样本量自动切换检测模式。

三条核心要求：
1. **接入 IQR** — 对 measure 列逐列计算 Q1/Q3/IQR，标记 1.5×IQR 之外的值
2. **按样本量切换** — 有效样本数 N<30 只走规则；N≥30 规则+IQR 双路并行
3. **合并规则异常结果** — 统计结果与业务规则结果统一去重输出，用 `detection_source` 区分来源

---

## 技术方案

### 1. IQR 检测器 (`iqr_detector.py`)

```
对每列 measure：
  1. 收集所有有效数值 → values[]
  2. 排序，计算 Q1（25%分位）、Q3（75%分位）
  3. IQR = Q3 - Q1
  4. 下界 = Q1 - 1.5 * IQR
  5. 上界 = Q3 + 1.5 * IQR
  6. 遍历每个 cell：值 < 下界 或 > 上界 → 标记为异常
```

- Q1/Q3 使用线性插值法（与 numpy/pandas 一致）
- score = 偏离度 / IQR（归一化到 0-1）
- reason：中文描述带分位值和偏离倍数

### 2. 编排层改造

在 `anomaly_service.detect_task_anomalies()` 中：

```
对每个 Sheet 的每列 measure：
  统计有效样本数 N
  if N >= 30:
      在 4 个业务规则检测器之外，追加 IQR 检测器
      detection_mode = "hybrid"
  else:
      仅业务规则
      detection_mode = "business_rule"

合并时：
  统计 detection_source == "business_rule" 的数量 → rule_hits
  统计 detection_source == "statistical" 的数量 → stat_hits
```

### 3. 不变更

- 不新增模型/表（复用 `anomaly_issues`）
- 不新增 API 端点
- 不修改 Schema
- 不新增 Alembic 迁移

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/services/anomaly/iqr_detector.py` | NEW | IQR 四分位距检测器 |
| `app/services/anomaly/anomaly_service.py` | MOD | N>=30 切换 + 双路合并 |
| `app/services/anomaly/__init__.py` | MOD | 导出 iqr_detector |
| `tests/unit/test_anomaly_service.py` | MOD | 新增 IQR 测试用例 |

---

## 测试策略

1. **test_iqr_flags_outliers** — 构造有明显离群值的数据，验证被捕获
2. **test_iqr_no_false_positives_on_normal_data** — 正态分布数据不误报
3. **test_iqr_respects_sample_threshold** — N<30 不启用 IQR
4. **test_hybrid_mode_sets_correct_counts** — detection_mode="hybrid" 时 rule_hits+stat_hits 分开计数