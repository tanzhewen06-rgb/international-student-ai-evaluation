# batch_007：五模型各两遍

本批固定模型：gpt-6.1-sol、gpt-5.4-nano、gemini-3.8-flash、gemini-3.5-flash-lite、deepseek-flash。

先运行 Response Agent/main.py 一次：每模型5个情景各2遍，每模型10份，共50份回答，保存到 Response Agent/experiments/batch_007。两遍是独立请求，不带上一遍聊天上下文。角色V2、背景V1、场景V4保持不变。

再运行 Evaluation Agent/main.py 一次：V4.12 从上述5个回答文件读取全部50份回答，由 Gemini 和 DeepSeek 独立评分，共100次初始评分，保存到 Evaluation Agent/evaluations/batch_007。必要的格式修复可能增加请求数；没有合并总分。

Response 的同一模型文件已有内容时会停止，避免误点再次追加50份。部分生成失败时应先检查失败记录；Evaluation 在回答不满50份、出现错误或重复遍次时会在付费评分前停止。

Response Agent/main.py 的 main(preview=True) 仅预览50次生成计划，不调用API、不写回答。Evaluation 的预览需先有完整回答。本次接线仅做离线模拟，未调用付费接口。

历史 Evaluation batch_005 评的是 Response batch_005；Evaluation batch_006 评的是 Response batch_004，保留原样。新批次双方编号统一007。
