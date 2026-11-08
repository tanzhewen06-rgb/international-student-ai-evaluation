# batch_008 Type2 pilot

## 当前操作：仅重新评分

batch_008 已有完整的10份回答。本轮只运行 Evaluation Agent/main.py，复用这些回答，使用当前 Type1 对齐后的 V4.12 Type2 评分说明。无需再次运行 Response Agent/main.py。

回答模型仍为 gpt-5.4-nano、gemini-3.5-flash-lite；两个评委仍为 gemini-3.8-flash、deepseek-flash。共20次初评，必要的既有格式修复可能增加请求。每次启动生成新的时间戳评分目录，保留旧轮结果；不复用历史分数。

新轮 manifest 记录 run_purpose、reuse_saved_responses 和实际评分说明哈希。2026-11-01 00:27 UTC 的首轮采用对齐前说明；请使用新轮报告查看本次结果。Type2 场景和Checklist内容保持原样。

回答模型：gpt-5.4-nano、gemini-3.5-flash-lite。两个模型各回答5个Type2情景，每个情景独立生成1次，共10份回答。

首次采集时先运行 Response Agent/main.py，再运行 Evaluation Agent/main.py。评分沿用 gemini-3.8-flash 与 deepseek-flash 两位独立评委，每份回答每位评委初评1次，共20次初评；既有的必要格式修复可能增加请求次数。六维独立0–10分，不合成总分。

角色仍为Counselor V2，学生背景仍为Background V1。情景切换为Type2 V1，Checklist数量为5/3/3/3/4。V4.12 Type2适配文件保留原六维分数锚点、扣分和严重性规则，只替换情景专用规则、事实摘要及精确文本绑定。旧Type1资源和batch_007结果保留。

Word审核文件的英文正文与18条英文Checklist逐字导出；中文对照、批注、高亮、陷阱说明和页眉页脚不进入回答模型输入。参考资料仅为机制背景，不添加未提供的机构政策。

重复运行Response入口会在已有回答文件非空时停止，防止追加重复回答。Evaluation会先检查模型、批次、5个情景、重复次数和情景哈希；遇到缺失、重复或旧Type1回答会在评分请求前停止。

默认实际API运行仍由用户启动。Response的main(preview=True)不调用API、不写回答；Evaluation预览需已有完整回答，离线模拟输出不能当成实验结果。
