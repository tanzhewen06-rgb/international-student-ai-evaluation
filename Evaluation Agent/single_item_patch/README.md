# Single-item evaluation patch (V4.12)

补评某个原始 run 中的一条回答，可采用全部六维或指定维度。正常 Evaluation Agent 的代码、提示词和历史记录保持原样。只有运行本文件夹的 `main.py` 才会发起补评。

## 直接运行

默认设置已指向 batch_007 当前唯一缺失的整条评分：

- 回答模型：`gpt-5.4-nano`
- 场景：`scenario_5` (Social Challenges)，回答生成第 2 遍
- 原评委：`deepseek-flash`
- Response ID：`be3e9b64d51549a6b78bd285b7886fd4`
- 采用全部六个维度。这里缺的是该评委的全部六维，不只是 D6。

在本文件夹打开终端：

```powershell
& '..\..\.venv\Scripts\python.exe' '.\main.py' --preview
& '..\..\.venv\Scripts\python.exe' '.\main.py'
```

第一条只检查，不调用 API、不写文件。第二条会实际调用原评委，沿用现有凭据。也可在编辑器中选择项目 `.venv` 后直接运行 `main.py`。

## 修改目标

修改 `main.py` 开头的设置：批次、comparison run 文件夹名称、回答模型、评委、场景、回答生成遍次及维度。`REPEAT_INDEX` 是回答生成的第几遍，不是补评次数。可选的 `RESPONSE_ID` 必须同时满足其他筛选条件。每次恰好选一条回答，否则停止。

```python
DIMENSIONS = ["D6"]
```

也可用命令行：

```powershell
& '..\..\.venv\Scripts\python.exe' '.\main.py' --dimensions D6
```

| Alias | Dimension |
| --- | --- |
| D1 | problem_understanding |
| D2 | empathy_and_emotional_support |
| D3 | cultural_respect_and_autonomy |
| D4 | clarity_and_accessibility |
| D5 | reasonableness_and_practicality |
| D6 | factual_reliability_and_faithfulness |

已有分数默认禁止覆盖；主动重评时加 `--allow-rejudge`（或把设置改为 True）。每次都独立留档；后一次成功补评的指定维度优先。若只补一维，其他五维保持原来的分数或空缺，未补齐的记录标记为 partial。不能自动反复请求直到取得满意分数。

## 评分口径

复用原 run 保存的 rubric/checklist/calibration 快照、原始回答和背景、原评委模型配置及正常 V4.12 的 `judge_response()`。执行前核验原评分代码、API 客户端、输入及首次请求的哈希；不一致则停止。不会发送原来的失败输出、历史分数或其他评委的分数给模型。

**指定单维度时，仍让评委完成原来的六维评估与全部校验，最后只采用指定维度。** 这是为了不改变原提示词及其跨维度检查，因此单维度补评并不只消耗单维度的 API 用量。最多是一次初始请求加正常逻辑允许的一次结构修复；没有额外网络重试或历史分数回填。

同样的输入及规则不能保证随机模型返回完全相同的分数；这是一次有来源记录的新判断。暂用分仍保留 provisional 标记，失败或 needs_review 不会成为正式补分。

## 保存位置及后续汇总

原评委/回答模型的 run 目录下新增：

```text
supplements/patch_<UTC时间>_<ID>/
  manifest.json          # 原 run、选择器、输入哈希和设置
  rubric.md / checklist.md / calibration.md
  task.txt / instructions.txt
  judgment.jsonl        # 全部六维、证据、校验、原文、请求次数和用量
  accepted_patch.json   # 仅成功时产生；只包含指定维度
  completion.json
```

请求失败则保存 `errors.jsonl`；校验失败保存 `judgment.jsonl`，均不产生 accepted_patch。中途退出留下的目录不会被当作成功分数。锁文件用于防止同一组评委/回答模型并发补评；程序异常中断后，确认进程已退出再删除遗留锁。

同时在原 comparison run 中生成：

```text
supplemented/<patch_ID>/effective_scores.json
supplemented/<patch_ID>/effective_scores.csv
supplemented/<patch_ID>/summary.json
```

这份汇总包含原批次所有模型和评委，按维度叠加成功补评；CSV 的每维包含分数、短评、校验状态和来源。JSON 保留详细维度信息。它是明确标注的补评合并视图，不会伪装成一次完整的新评估；完整证据分别在原记录和各补评记录中。用量留在各原始/补评记录，不能将合并视图当作新的用量账本。

原 run 的 JSONL、失败记录、manifest 和原比较报告不覆盖；桌面 Excel 不自动更新。后续导入数据应使用最新 `supplemented` 导出，旧版导出器若只读原始日志不会自动看到补分。

若分数已保存但导出失败，运行以下命令只重建汇总，不重新调用 AI：

```powershell
& '..\..\.venv\Scripts\python.exe' '.\main.py' --refresh-only
```

此版本针对当前 V4.12 已存档的双评委 comparison run；不支持旧评分版本、临时换评委或修改后的评分代码。
