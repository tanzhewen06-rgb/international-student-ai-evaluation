# 面向国际学生支持场景的 AI 回答评估

**Evaluating AI Support for International Students**

[English](README.md) | 简体中文

本项目通过国际学生可能遇到的具体情景，比较不同大语言模型生成的回答，并使用多个评估模型从六个维度独立评分。仓库包含回答生成程序、评估程序、各版本提示词、保存的模型回答和评分结果。

研究关注的不只是回答是否清晰、是否具有支持性，也关注模型能否正确理解问题、忠实使用学生提供的信息，以及给出合理且可执行的建议。

## 项目组成

项目分为三个部分：

- **Response Agent**：读取角色、学生背景和情景提示词，生成不同模型的回答。
- **Evaluation Agent**：读取已保存的回答，依据评估提示词、情景核对清单和人工校准参考进行评分。
- **Sample Data**：统一保存回答、评分、补评分记录和分析报告。

每次回答生成都是独立请求，不沿用上一条回答的聊天上下文。不同评估模型分别评分，不将它们的结果直接合并为一个总分。

```text
项目根目录/
├── Response Agent/
│   ├── main.py                 # 回答生成入口与主要配置
│   ├── prompts/                # 各版本角色、背景和情景提示词
│   ├── models.py               # 模型接口与生成参数
│   └── requirements.txt        # 依赖列表
├── Evaluation Agent/
│   ├── main.py                 # 评估入口与主要配置
│   ├── runtime/                # 评分流程、校验、保存与报告代码
│   ├── versions/               # 各版本评估提示词与相关实现
│   └── resources/              # 核对清单和人工校准等参考材料
├── Sample Data/
│   ├── responses/              # 按批次保存的模型回答
│   ├── evaluations/            # 评分、试验、补评分和导出结果
│   ├── analysis/               # 保存的离线分析
│   └── reference_data/         # 冻结的基线元数据与分数
├── tests/                      # 离线路径与数据读取检查
├── README.md                   # 英文说明
├── README.zh-CN.md             # 简体中文说明
├── PUBLICATION_NOTES.md        # 公开副本、路径处理和文件指纹说明
└── PUBLICATION_INVENTORY.json  # 公开文件校验清单
```

两个 Agent 与 `Sample Data` 应保持在同一层级。提示词和程序保存在各自的 Agent 目录内，实验数据统一保存在 `Sample Data`。

## 评估维度

评估使用六个独立的 0–10 分维度：

| 维度 | 主要关注内容 |
| --- | --- |
| 问题理解与回答相关性 | 是否理解学生的问题、条件和真实需求 |
| 共情与情绪支持 | 是否回应学生的感受，提供合适的情绪支持 |
| 文化尊重与学生自主性 | 是否尊重文化背景，保留学生的选择权 |
| 清晰度与可理解性 | 表达是否清楚，学生是否容易理解 |
| 建议的合理性与可行性 | 建议是否适合情景，并具有实际操作价值 |
| 事实可靠性与情景忠实度 | 是否准确使用已知信息，避免捏造事实或误读情景 |

评估提示词规定评分程序和扣分规则；核对清单提供情景层面的支持证据。实际评分规则以所选版本的评估提示词和对应程序为准。

## 数据说明

`Sample Data` 中保存的是真实模型调用产生的研究记录，包括历史试验批次；文件夹名称不表示其中的数据是虚构演示数据，也不表示每个历史批次都是最终研究样本。

当前正式报告使用 **Type 1**，最终批次为 `Final_Batch_Type_1`：

| 项目 | 数量 |
| --- | --- |
| 回答生成模型 | 5 个 |
| 情景 | 5 个 |
| 每个模型、每个情景的生成次数 | 5 次 |
| 保存的回答 | 125 份 |
| 独立评估模型 | 3 个 |
| 完成补评分后的有效评分记录 | 375 条 |

其中 **5 条评分仍带有暂定标记（provisional）**，使用数据时应保留该标记。Type 2 相关材料和试验属于探索性工作，不包含在上述正式 Type 1 结果中。

最终完成补评分的数据位于：

```text
Sample Data/evaluations/Final_Batch_Type_1/
└── judge_comparison_v4_17/
    └── trial_20261102T211905.670197Z_251b2721/
        └── supplements/missing_scores/
            └── judgments_supplemented.json
```

[打开最终补全评分数据](Sample%20Data/evaluations/Final_Batch_Type_1/judge_comparison_v4_17/trial_20261102T211905.670197Z_251b2721/supplements/missing_scores/judgments_supplemented.json)

原始试验有 3 条未成功评分的记录，后续已通过补评分完成。分析最终结果时，应使用上述合并后的数据，避免直接拼接所有日志而重复计算同一条回答的评分或失败尝试。

这些结果反映所选情景、生成样本、提示词版本和评估模型下的表现。不同评估模型可能存在分歧；模型评分的一致性本身并不证明评分正确。本项目没有直接测量真实学生接受建议后的实际效果。

## 安装与密钥配置

本项目使用 Python 3.13。以下命令以 Windows PowerShell 为例，在项目根目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r ".\Response Agent\requirements.txt"
```

两个 Agent 共用 Response Agent 的模型接口层。需要调用相应服务时，请配置自己的环境变量：

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `DEEPSEEK_API_KEY`

Windows 用户也可以运行 `Response Agent/setup_keys.py`，将 OpenAI 和 Gemini 的密钥保存到 Windows 凭据管理器；DeepSeek 可以通过环境变量配置。不要将真实密钥写入程序或提交到仓库。

模型名称、可选模型和接口参数以 `main.py` 与 `models.py` 为准。运行新实验前，需要根据自己的接口访问权限调整相关配置。

## 先进行离线预览

离线预览用于检查输入和计划，**不会调用模型，也不会写入实验结果**。

在项目根目录依次运行：

```powershell
cd "Response Agent"
..\.venv\Scripts\python.exe -B -c "import main; main.main(preview=True)"
cd ..

cd "Evaluation Agent"
..\.venv\Scripts\python.exe -B main.py --preview
cd ..
```

当前评估入口默认指向已完成的最终批次补评分任务，因此预览会显示没有待补评分。这不代表缺少数据，也不会自动重新评估全部回答。

## 配置新实验

主要设置集中在两个 Agent 的 `main.py` 顶部。

1. 在 Response Agent 中选择模型、提示词、生成次数和一个新的批次名，例如 `batch_012`。
2. 在 Evaluation Agent 中，将回答输入目录、回答文件列表和评分输出目录指向该批次。
3. 将 Evaluation Agent 的 `MISSING_SCORE_TRIAL` 设为 `None`，切换到正常评估流程。
4. 确认两边的模型文件名、情景数和生成次数配置相互对应，并先进行离线预览。
5. 准备好以后，再由使用者主动启动模型调用。

从项目根目录运行实际生成或评估的入口为：

```powershell
.\.venv\Scripts\python.exe -B ".\Response Agent\main.py"
.\.venv\Scripts\python.exe -B ".\Evaluation Agent\main.py"
```

以上两条命令是实际运行入口，不是预览命令。应先完成新批次配置，再按需要分别执行。生成程序会拒绝向已有非空回答文件重复采集；不要直接复用最终批次作为新实验的输出位置。

## 离线检查

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

这些检查覆盖项目相对路径读写、路径范围校验，以及最终回答和评分数据的读取，不调用模型接口。

## 路径、文件校验与公开副本

公开副本中的本机绝对路径已处理为以 `project://` 开头的项目相对引用，或对外部本地路径进行脱敏。程序会按当前项目的位置解析引用，因此不要求使用原电脑的用户名、盘符或目录。

原始回答、提示词、分数和标记予以保留。包含路径的公开元数据文件经过处理后，文件指纹会发生变化；公开元数据之间的相关文件指纹引用也已对应调整。详情参见 [公开副本说明](PUBLICATION_NOTES.md) 和 [文件校验清单](PUBLICATION_INVENTORY.json)。

历史运行记录中的评分程序指纹仍代表当时使用的版本。当前公开代码不应被视为与原始冻结环境完全相同；历史试验的续跑校验不会自动绕过版本差异。

Windows 上部分历史试验路径较深。对于已经存在的本地仓库，可以在仓库根目录运行：

```powershell
git config --local core.longpaths true
```

如果准备通过 GitHub Desktop 克隆到 Windows，可以在克隆前启用当前用户的长路径支持：

```powershell
git config --global core.longpaths true
```

仓库中的 `.gitattributes` 用于保留文件的原始换行格式，避免自动转换导致已有文件指纹失效。
