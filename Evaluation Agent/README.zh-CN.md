> Layout update: current configuration and shared Sample Data paths are documented in [the project README](../README.md) and [README.en.md](README.en.md). The text below describes historical configurations.

# Evaluation Agent

直接运行本目录的 `main.py`。实际 API 调用全部由用户自行启动；离线预览为 `main(preview=True)`。

当前配置：评分 prompt **V4.11**；结果 **batch_006**；复用 batch_004 两个弱模型各前五条回答，由 Gemini 与 DeepSeek 各评一次，共二十次初始评分。每次运行新建 run，保留旧结果；六维独立0–10分，不合并总分。评分规则与整理前相同。

## 文件位置

| 位置 | 内容 |
| --- | --- |
| `main.py` | 唯一日常运行入口；选择输入、评委、prompt和输出批次 |
| `runtime/` | 公共流程、文件读写、评分计算与报告模块 |
| `versions/v4_11/` | 当前版本专用实现及 `prompts/` 下的评分prompt |
| `versions/v4_9/` 等 | 各历史版本的实现及对应评分prompt |
| `resources/checklists/v4_4/` | 当前Checklist；其他版本分目录保存 |
| `resources/human_calibration/v3/` | 当前人工评分原则；V1/V2原样本各自存档 |
| `evaluations/` | 所有已有评分记录与报告，原位置保留 |
| `history/` | 历史变更记录和整理前的缓存 |

Checklist 仍按五场景5/3/4/5/4条输出。Gemini low、DeepSeek none，双方temperature=0，输出上限4096。每轮初评输入会核对是否一致。稳定性表只比较同一评委、同回答和相同规则/代码/参数的历史运行；没有匹配历史时不宣称稳定。

读取或重新导出旧报告可使用 `python -m runtime.report <原run文件夹>`；不调用模型。`versions` 中的模块由程序自动选择，无需逐个运行或手动复制。

V4.11沿用原短输出，不新增清单理由字段或标签；六维仅需分数档位和一句短评。缺陷引文或标签未核实时，保留原声明的数值上限并明确标暂用，不能当作已验证评分。未新增语义复核调用，原数值规则不变。
