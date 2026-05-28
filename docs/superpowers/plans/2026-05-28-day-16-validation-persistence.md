# Day 16：校验结果落库

**日期：** 2026-05-28
**状态：** in_progress
**依赖：** Day 15（validation engine 完成）

---

## 目标

将 Day 15 的校验结果持久化到数据库，实现：

1. **记录误差**：期望值 vs 实际值写入 alidation_issues 表
2. **记录定位**：sheet_id / row_index / col_index 精确到单元格
3. **记录命中规则**：关联到 ormula_rules.id，标明是哪个公式触发了问题

---

## 技术方案

### 1. 新模型：ValidationIssueRecordModel

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 自增主键 |
| task_id | FK → tasks.id | 所属任务 |
| sheet_id | FK → sheets.id | 所属 Sheet |
| formula_rule_id | FK → formula_rules.id, nullable | 命中公式（nullable 允许无规则匹配的异常） |
| row_index | Integer | 行号 |
| col_index | Integer | 列号 |
| expected_value | String(500) | 期望值 |
| actual_value | String(500) | 实际值 |
| formula_text | Text | 公式文本 |
| severity | String(20) | error / warning |
| issue_type | String(50) | row_mismatch / division_by_zero / aggregate_mismatch |
| created_at | DateTime(tz) | 创建时间 |

### 2. 落库逻辑

在 alidation_service.validate_task_formulas() 中：
- 校验完成后，将 ll_issues 批量写入 alidation_issues 表
- 先删旧数据（task_id 维度），再插入新数据（幂等）
- 写入成功后更新 	ask.status 为 "validated"

### 3. API 端点修改

修改 POST /{task_id}/validate：
- 返回 ValidationResult 后，结果已入库
- 新增 GET /{task_id}/validation-issues 用于查询历史落库结果

### 4. 不变更部分

- 不建立历史版本（Day 15 已声明 no DB writes）
- 不做增量校验
- 不引入新的质量过滤

---

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| pp/db/models/validation_issue_record.py | NEW | ORM 模型 |
| lembic/versions/20260528_0005_add_validation_issues.py | NEW | 数据库迁移 |
| pp/db/base.py | MOD | 注册新模型 |
| pp/services/validation/validation_service.py | MOD | 落库逻辑 |
| pp/api/routes/tasks.py | MOD | GET 查询端点 |
| 	ests/unit/test_validation_persistence.py | NEW | 持久化测试 |

---

## 测试策略

1. **test_persist_issues_on_validate**：验证 validate 后 issues 写入 DB
2. **test_validate_clears_old_issues**：幂等——再次 validate 先删旧数据
3. **test_validate_updates_task_status**：validate 后 task.status → "validated"
4. **test_get_validation_issues_endpoint**：GET 端点返回已入库数据
5. **test_empty_validation_no_persistence_error**：无 issue 时不报错
