# batch_009 Type2 V1.1 single paragraph pilot

本批使用Type2 V1.1单段场景，单独保存以便与batch_008的V1比较。

运行顺序：先运行 Response Agent/main.py，再运行 Evaluation Agent/main.py。
回答模型：gpt-5.4-nano、gemini-3.5-flash-lite，各5个场景、各1遍，共10份新回答。
评分评委：gemini-3.8-flash、deepseek-flash，共20次初评；既有必要格式修复可能增加请求。

场景来自单段精简Word审阅稿的英文正文。接入核对只恢复一处清单依赖的事实：社交情景使用“I haven't agreed to cancel”，而非仅“I haven't cancelled”；原稿未答应取消的事实得到保留。
Checklist仍为18条（5/3/3/3/4），全部条目原文不变，仅新建V1.1文本绑定。评分说明沿用上一轮对齐后的V4.12，不增加Gemini专用规则、不改变六维整数锚点或扣分公式。
Counselor V2、Background V1、模型和重复次数均保持不变。当前只改变场景表达及必要版本记录。

Response已有数据时会阻止重复追加。Evaluation检查完整的V1.1输入后再评分，生成独立时间戳目录，不沿用历史分数。batch_007、batch_008及Type2 V1原始资源均保留。
实际接口调用由用户启动。开发中的离线模拟数据保存在工作区测试目录，不能作为实验结果。
