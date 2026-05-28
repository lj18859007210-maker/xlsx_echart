# xlsx_echart

涓€涓潰鍚?Excel 琛ㄦ牸鍒嗘瀽鐨勭郴缁燂紝鐢ㄤ簬瀹屾垚琛ㄦ牸鎺ュ叆銆佺粨鏋勮瘑鍒€佷汉宸ョ‘璁ゃ€佸叕寮忔牎楠屻€佸紓甯告娴嬨€丄I 鍒嗘瀽鍜屽浘琛ㄧ敓鎴愩€?
## 浜у搧鐩爣

绗竴鐗堢洰鏍囨槸鏋勫缓涓€鏉＄ǔ瀹氥€佸彲瑙ｉ噴銆佸彲杩借釜鐨勮〃鏍煎垎鏋愪富閾捐矾锛岃鐢ㄦ埛涓婁紶 `.xlsx` 鏂囦欢鍚庯紝鍙互寰楀埌锛?
- 娓呮礂鍚庣殑琛ㄦ牸瑙嗗浘
- 鏍￠獙閿欒娓呭崟
- 寮傚父娓呭崟
- 鍒嗘瀽缁撹
- 鍥捐〃鎺ㄨ崘涓庢覆鏌撶粨鏋?
绯荤粺閲囩敤鈥淟LM 璐熻矗鐞嗚В涓庤В閲婏紝Python 璐熻矗纭畾鎬ц绠楋紝鍓嶇鎵挎帴浜哄伐纭鈥濈殑娣峰悎鏋舵瀯锛屼紭鍏堜繚璇佺粨鏋滃彲闈犳€э紝鑰屼笉鏄竴寮€濮嬭拷姹傝鐩栨墍鏈夊鏉傚満鏅€?
## 绗竴鐗堣寖鍥?
- 杈撳叆锛氫紭鍏堟敮鎸?`.xlsx`
- 琛ㄦ牸绫诲瀷锛氫紭鍏堟敮鎸侀€氱敤缁忚惀鍒嗘瀽琛ㄣ€佽储鍔＄被瑙勫垯鍖栬〃鏍?- 鏍稿績娴佺▼锛氫笂浼?-> 瑙ｆ瀽 -> 缁撴瀯纭 -> 鍏紡鎺ㄥ -> 鏍￠獙 -> 寮傚父妫€娴?-> 鎽樿 -> 鍒嗘瀽 -> 鍥捐〃
- 杈撳嚭锛氱粨鏋勫寲缁撴灉銆侀棶棰樻竻鍗曘€佸垎鏋愮粨璁恒€佸浘琛ㄧ粨鏋?
## 闈炵洰鏍?
绗竴鐗堟殏涓嶅寘鍚互涓嬪唴瀹癸細

- OCR 鍥剧墖琛ㄦ牸璇嗗埆
- 澶氱鎴?- 澶嶆潅鏉冮檺浣撶郴
- 绉诲姩绔€傞厤
- 澶ц妯℃壒閲忓紓姝ヤ换鍔＄紪鎺?- 鍙鍖栬鍒欑紪鎺掑櫒

## 鐢ㄦ埛涓绘祦绋?
1. 鐢ㄦ埛涓婁紶 Excel 鏂囦欢銆?2. 绯荤粺瑙ｆ瀽 workbook銆乻heet銆佸崟鍏冩牸鍜屽悎骞跺尯鍩熴€?3. 绯荤粺鐢熸垚缁撴瀯鍖栫綉鏍奸瑙堬紝杩涘叆 Gate 1 浜哄伐纭銆?4. 鐢ㄦ埛淇缁撴瀯骞剁‘璁ゅ悗锛岀郴缁熺户缁墽琛屽叕寮忔帹瀵煎拰瑙勫垯鏍￠獙銆?5. 绯荤粺杈撳嚭鏍￠獙闂銆佸紓甯搁棶棰樸€佹憳瑕佺粨鏋溿€丄I 鍒嗘瀽缁撹鍜屽浘琛ㄧ粨鏋溿€?
鏇磋缁嗚鏄庤锛?
- [闇€姹傚喕缁撴竻鍗昡(D:/AAA-Project/head/xlsx_echart/docs/闇€姹傚喕缁撴竻鍗?md)
- [鐢ㄦ埛涓绘祦绋媇(D:/AAA-Project/head/xlsx_echart/docs/鐢ㄦ埛涓绘祦绋?md)
- [浠诲姟鐘舵€佹満](D:/AAA-Project/head/xlsx_echart/docs/浠诲姟鐘舵€佹満.md)

## 浠诲姟鐘舵€?
绗竴鐗堢粺涓€浠诲姟鐘舵€佸涓嬶細

- `uploaded`
- `parsed`
- `waiting_confirm`
- `confirmed`
- `validated`
- `analyzed`
- `chart_ready`
- `failed`

## 鎶€鏈爤

- 鍚庣锛歚FastAPI`
- 鏁版嵁澶勭悊锛歚Pandas`銆乣OpenPyXL`
- 鏁版嵁妯″瀷锛歚Pydantic`
- 鍓嶇锛歚React`
- 鍥捐〃锛歚ECharts`
- 瀛樺偍锛歚SQLite`
- 缂撳瓨锛歚Redis`锛堝彲閫夛級
- AI 鑳藉姏锛歚LLM API`

## 褰撳墠闃舵

浠婂ぉ鐨勭洰鏍囨槸瀹屾垚绗竴澶╃殑鏂囨。鍐荤粨宸ヤ綔锛屽寘鎷細

- 浜у搧鐩爣
- 绗竴鐗堣寖鍥翠笌闈炵洰鏍?- 鐢ㄦ埛涓绘祦绋?- 浠诲姟鐘舵€佹満
- 鎶€鏈爤纭


## Day 13 公式推导 (Formula Inference)

### 环境变量

- `FORMULA_LLM_API_URL` - LLM API 地址
- `FORMULA_LLM_API_KEY` - LLM API 密钥
- `FORMULA_LLM_MODEL` - 模型名称

### 本地验证

```bash
cd backend
python -m pytest tests/unit/test_formula_inference_service.py -v
python -m pytest tests/unit/test_task_review.py -k infer_formulas -v
```


## Day 14 公式兜底与清洗

### 新增端点

- `GET /api/tasks/{task_id}/formula-rules` — 返回质量过滤后的规则列表及统计
- `POST /api/tasks/{task_id}/formula-rules/acknowledge-gap` — 确认空规则集，跳过后续校验

### 环境变量（新增）

- `FORMULA_QUALITY_THRESHOLD` — 公式质量最低分数阈值，默认 0.3

### 本地验证

```bash
cd backend
python -m pytest tests/unit/test_formula_quality_filter.py -v
python -m pytest tests/unit/test_task_review.py -k "formula_rules or acknowledge" -v
```


## Day 15 校验引擎

### 新增端点

- `POST /api/tasks/{task_id}/validate` — 执行公式校验，返回逐行/汇总误差清单

### 本地验证

```bash
cd backend
python -m pytest tests/unit/test_execution_plan.py tests/unit/test_row_validator.py tests/unit/test_aggregate_validator.py tests/unit/test_validation_service.py -v
```
