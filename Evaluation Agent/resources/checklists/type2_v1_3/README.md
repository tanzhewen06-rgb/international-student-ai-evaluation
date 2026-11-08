# batch_011 Type2 V1.3小范围试跑

先运行Response Agent/main.py，再运行Evaluation Agent/main.py。回答模型仍为gpt-5.4-nano和gemini-3.5-flash-lite，五场景各生成一遍，共10份新回答；评委仍为gemini-3.8-flash、deepseek-flash，共20次初评，格式修复或失败请求可能增加实际调用。

两个入口均锁定V1.3及batch_011。评分使用V4.12 Type2 V1.3提示词、新版21条要求、Checklist文件哈希和五段场景原文哈希；拒绝旧回答或错配材料。评分维度、整数尺度、主维度、上限和FINAL=min规则仍沿用Type1。

旧批次保持原样。GPT在batch_007上的三遍稳定性测试仍是独立入口，不混进这次小范围试跑。此次配置已离线模拟，实际接口由用户启动；离线分数不作研究数据。

本版Scenario和21条Checklist正文沿用已审核的V1.3材料，仅更新接入状态；桌面对应Word同步状态说明。
