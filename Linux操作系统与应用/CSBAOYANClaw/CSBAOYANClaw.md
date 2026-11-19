# CSBAOYANClaw 汇报材料速览

## 1. 项目一句话介绍

CSBAOYANClaw 是一个部署在 Linux 云服务器上的计算机保研 QQ 群情报日报 Agent。它通过 NapCat 接入 QQ 群，自动收集保研群消息，先在本地进行规则筛选和质量打分，再调用 AI 生成每日 Markdown 日报，并支持 QQ 私发、Web UI 查看历史日报和基于历史信息问答。

一句话版本：

> CSBAOYANClaw 是一个面向计算机保研 QQ 群的信息整理 Agent，能自动从海量群消息中筛选有价值保研情报，生成日报并支持历史问答。

------

## 2. 项目背景

计算机保研 QQ 群每天会产生大量消息，其中包含很多有价值的信息，例如：

- 夏令营、预推免、九推通知；
- 报名截止时间；
- 材料要求；
- 导师招生信息；
- 推荐入营、优营经验；
- 群友对院校和项目的经验分享；
- 待核实传闻和线索。

但问题是：

- 群消息太多，人工逐条查看成本高；
- 有用信息经常被闲聊、表情、图片淹没；
- 保研信息有时效性，错过可能影响报名；
- 群友经验和官方通知混在一起，需要区分可信度；
- 历史信息不好检索，过几天很难再找到。

因此我们设计了 CSBAOYANClaw，用 AI 放大学生处理信息的能力。

------

## 3. 项目目标

项目目标包括：

1. 自动监听指定计算机保研 QQ 群；
2. 自动保存群消息到本地数据库；
3. 自动筛选保研相关高价值消息；
4. 调用 AI 生成每日保研情报日报；
5. 生成 Markdown 日报文件；
6. 将日报私发给自己的 QQ；
7. 支持 Web UI 查看历史日报；
8. 支持基于历史日报和群消息的问答；
9. 通过 OpenClaw Skill 让 OpenClaw 能以自然语言命令调用日报生成和问答能力。

------

## 4. 系统整体架构

推荐画成一张架构图：

```text
QQ 保研群
   ↓
NapCat
   ↓ HTTP 上报
FastAPI 后端
   ↓
SQLite 原始消息库
   ↓
本地清洗 / 筛选 / 打分
   ↓
DeepSeek AI 结构化抽取
   ↓
Markdown 日报 + SQLite 结构化情报
   ↓
QQ 私发 / Web UI / OpenClaw Skill
```

各模块职责：

- **阿里云 ECS + Ubuntu**：Linux 部署环境；
- **Docker / Docker Compose**：容器化部署；
- **NapCat**：登录主 QQ，监听指定 QQ 群，接收群消息；
- **FastAPI**：核心业务后端，负责消息接收、日报生成、问答接口、Web UI；
- **SQLite**：保存原始消息、结构化情报和日报记录；
- **DeepSeek API**：负责 AI 信息抽取、日报总结和问答生成；
- **Markdown**：保存每日保研情报日报；
- **Web UI**：用于生成日报、查看历史日报和输入自然语言命令；
- **OpenClaw Skill**：将 CSBAOYANClaw 后端封装为 OpenClaw 可调用技能。

------

## 5. 核心工作流

### 5.1 消息采集流程

```text
NapCat 登录主 QQ
   ↓
监听指定 QQ 群 943826679
   ↓
群消息通过 HTTP POST 上报到 FastAPI
   ↓
FastAPI 过滤目标群
   ↓
消息写入 SQLite
```

数据库中保存：

- 消息时间；
- 群号；
- 脱敏后的发送者 hash；
- 原始消息文本；
- 是否为关键词候选；
- 原始 payload JSON。

------

### 5.2 日报生成流程

现在的日报不是直接把全部群消息丢给 AI，而是先本地筛选：

```text
今日全部已入库群消息
   ↓
清理 CQ 码
   ↓
关键词初筛
   ↓
本地质量打分
   ↓
选出高分候选
   ↓
补充前后上下文
   ↓
送入 AI 总结
   ↓
生成结构化情报
   ↓
生成 Markdown 日报
```

示例运行数据：

```text
今日入库群消息：2122 条
关键词候选：325 条
打分候选：148 条
核心候选：60 条
送入 AI 上下文：159 条
提取高价值信息：19 条
```

这说明系统不是简单套壳 AI，而是先通过本地规则降低噪声，再让 AI 做更高质量的总结。

------

### 5.3 问答流程

用户在 Web UI 输入问题，例如：

```text
今天群里提到了哪些保研信息？
群里有没有提到中科大夏令营？
最近有没有推荐入营相关信息？
```

系统会：

```text
用户问题
   ↓
关键词提取
   ↓
检索结构化情报 extracted_items
   ↓
检索日报 reports
   ↓
检索原始群消息 raw_messages
   ↓
组合上下文
   ↓
调用 AI 生成回答
```

问答不是只看 Markdown 文件，而是综合检索三层数据：

1. 原始群消息；
2. AI 提取后的结构化情报；
3. 每日 Markdown 日报。

------

## 6. 数据存储设计

### 6.1 raw_messages：原始群消息表

用于保存目标 QQ 群的原始消息。

字段包括：

```text
id
event_time
group_id
sender_hash
message_id
raw_message
is_candidate
payload_json
created_at
```

特点：

- 保存全量目标群消息；
- 发送者 QQ 做 hash 脱敏；
- 保留原始 payload，方便排查；
- 标记是否为关键词候选。

------

### 6.2 extracted_items：结构化情报表

AI 从群消息中提取出的高价值信息。

字段包括：

```text
report_date
category
title
school
college
stage
deadline
credibility
summary
action_suggestion
source_message_ids
item_json
```

例如：

```text
标题：中科院软件所推荐入营可获优营
类别：经验分享
学校：中国科学院软件研究所
阶段：夏令营 / 导师招生
可信度：C
摘要：群友表示导师已同意推荐入营，躺平等待优营。
建议：有意申请软件所的同学应尽早联系导师。
来源消息 ID：若干条群消息
```

------

### 6.3 reports：日报表

保存每日生成的日报。

字段包括：

```text
report_date
plain_text
markdown
message_count
candidate_count
pushed
report_path
created_at
```

同时生成 Markdown 文件：

```text
/opt/csbaoyanclaw/reports/2026-05-31.md
```

同一天多次生成日报时，系统会覆盖当天旧日报，保持“一天一份最新日报”。

------

## 7. 可信度分级

为了避免把群友传闻当成官方信息，系统设计了可信度等级：

```text
A：官方通知、官方文件、官方截图或官网链接；
B：群友转发且有明确来源；
C：群友经验分享；
D：未经证实的传闻或待核验线索。
```

日报中每条信息都会标注可信度，并给出行动建议。

重点表达：

> CSBAOYANClaw 不替代官网核验，而是帮助用户从海量群消息中发现线索，并提醒用户区分官方信息、经验分享和待核实传闻。

------

## 8. Web UI 功能

Web UI 风格参考 ChatGPT，主要功能：

1. 左侧边栏显示历史日报；
2. 日报按日期从新到旧排序；
3. 点击历史日报后以文件阅读面板打开；
4. 主界面输入框用于向 CSBAOYANClaw 输入自然语言命令；
5. 支持命令：
   - 生成今日日报；
   - 生成今日日报并私发 QQ；
   - 今天群里提到了哪些保研信息；
   - 查看某天日报；
6. 生成新日报后自动刷新日报列表并打开新日报；
7. 支持复制 Markdown。

页面展示点：

- 左侧日报列表；
- 中间自然语言命令入口；
- 日报阅读页面；
- AI 思考呼吸动画；
- QQ 私发结果。

------

## 9. OpenClaw 参与方式

项目不是只部署 OpenClaw，而是将 CSBAOYANClaw 后端能力封装为 OpenClaw Skill。

OpenClaw 的角色：

```text
OpenClaw = Agent 层 / 自然语言工具调用层
FastAPI = 具体业务工具服务
NapCat = QQ 接入层
SQLite + Markdown = 知识沉淀层
DeepSeek = AI 信息抽取和问答模型
```

通过自定义 OpenClaw Skill，OpenClaw 可以调用：

```text
生成今日日报
生成并私发 QQ
查询历史保研信息
查看往日日报
```

可以这样汇报：

> 我们将 CSBAOYANClaw 后端封装为 OpenClaw Skill，使 OpenClaw 能够通过自然语言调用“生成日报”“查询历史保研信息”“查看往日日报”等工具能力。OpenClaw 负责 Agent 层的意图理解和工具调用，FastAPI 负责具体业务执行。

------

## 10. 技术难点

### 10.1 Docker 网络

项目中有多个容器：

- NapCat；
- FastAPI；
- OpenClaw gateway；
- OpenClaw cli。

需要处理：

- 容器之间互相访问；
- NapCat HTTP Client 上报；
- NapCat HTTP Server 发私聊；
- FastAPI 与 NapCat 同网络；
- OpenClaw 访问 CSBAOYANClaw API。

------

### 10.2 NapCat HTTP Client / Server 区分

NapCat 里需要同时配置两个方向：

```text
HTTP Client：NapCat → FastAPI
负责把 QQ 群消息上报到后端。

HTTP Server：FastAPI → NapCat
负责让后端调用 /send_private_msg 私发 QQ。
```

如果只配置 HTTP Client，就只能收消息，不能私发 QQ。

------

### 10.3 CQ 码清理

QQ 消息中有大量 CQ 码：

```text
[CQ:image,...]
[CQ:face,...]
[CQ:reply,...]
[CQ:at,...]
```

系统将其清理为：

```text
[图片]
[表情]
[回复消息]
[@用户]
```

这样日报更适合阅读。

------

### 10.4 消息去噪和筛选

保研群中大量消息是闲聊、表情和短句。

如果全部交给 AI，会导致：

- 成本高；
- 延迟高；
- AI 容易忽略重点；
- 日报可能为空；
- 生成质量不稳定。

因此系统设计了本地筛选和打分。

------

### 10.5 AI 输出可靠性

系统要求 AI 输出结构化 JSON，并进行解析。

如果 AI 输出空内容或格式不对，系统会记录错误并启用 fallback 逻辑，避免静默生成空日报。

------

## 11. 如何体现“AI 能力放大”

老师要求写“如何使用 AI：提示词、工作流、tool、skills”。

可以从两层讲：

### 11.1 开发过程中使用 AI

开发时使用 AI 辅助：

- 设计系统架构；
- 拆解 NapCat、FastAPI、SQLite、OpenClaw 的职责；
- 编写 Docker Compose；
- 编写 FastAPI 后端；
- 分析报错日志；
- 修复 Docker 网络问题；
- 设计 Web UI；
- 优化日报 prompt；
- 设计可信度分级；
- 整理课程报告和展示材料。

### 11.2 系统运行时使用 AI

运行时 AI 负责：

- 从候选群消息中抽取结构化信息；
- 区分官方通知、经验分享和传闻；
- 生成日报摘要；
- 给出行动建议；
- 基于历史日报和群消息回答问题。

重点表达：

> AI 不是替代全部程序逻辑，而是嵌入到本地规则、工具调用和知识沉淀工作流中，帮助我们从海量碎片化消息中提炼有用信息。

------

## 12. 演示流程建议

### 演示 1：消息采集

展示 NapCat 日志：

```text
收到目标保研群消息
HTTP 上报到 FastAPI
FastAPI /recent 可查看最新消息
```

### 演示 2：生成日报

在 Web UI 输入：

```text
生成今日日报
```

展示：

- AI 思考动画；
- 生成完成后的指标；
- 自动打开 Markdown 日报；
- 左侧日报列表更新。

### 演示 3：私发 QQ

在 Web UI 输入：

```text
生成今日日报并私发 QQ
```

展示自己的 QQ 收到日报。

### 演示 4：历史问答

输入：

```text
今天群里提到了哪些保研信息？
```

或者：

```text
群里有没有提到中科院软件所推荐入营？
```

展示系统基于历史日报和群消息回答。

### 演示 5：OpenClaw Skill

展示：

```text
/opt/csbaoyanclaw/openclaw/skills/csbaoyanclaw/SKILL.md
```

说明：

> 我们把后端能力封装成 OpenClaw Skill，使 OpenClaw 可以通过自然语言调用 CSBAOYANClaw 的日报生成和问答工具。

------

## 13. 幻灯片结构建议

建议 Marp 幻灯片按以下顺序制作：

### Slide 1：标题页

```text
CSBAOYANClaw
基于 OpenClaw 与 NapCat 的计算机保研 QQ 群情报日报 Agent
```

### Slide 2：问题背景

```text
保研 QQ 群消息量大
信息碎片化
重要通知易被淹没
人工查看成本高
```

### Slide 3：项目目标

```text
自动收集
自动筛选
自动日报
QQ 私发
历史问答
Web UI 展示
```

### Slide 4：系统架构图

展示：

```text
QQ 群 → NapCat → FastAPI → SQLite → AI → Markdown / QQ / Web UI / OpenClaw
```

### Slide 5：消息处理工作流

展示：

```text
全量消息 → 清理 → 初筛 → 打分 → 上下文补全 → AI 总结
```

### Slide 6：日报生成效果

展示实际指标：

```text
今日入库消息 2122 条
关键词候选 325 条
打分候选 148 条
送入 AI 159 条
提取高价值信息 19 条
```

### Slide 7：日报样例

截图展示 Web UI 的日报阅读页。

### Slide 8：历史问答

截图展示 QA 输入和回答。

### Slide 9：OpenClaw Skill

展示 Skill 的作用：

```text
OpenClaw 自然语言命令
→ CSBAOYANClaw Skill
→ FastAPI 工具
→ 日报 / 问答 / QQ 私发
```

### Slide 10：技术难点

```text
Docker 网络
NapCat HTTP Client / Server
CQ 码清理
本地消息打分
AI JSON 抽取
日报覆盖与知识沉淀
```

### Slide 11：AI 如何放大能力

```text
AI 辅助开发
AI 辅助日志分析
AI 运行时信息抽取
AI 历史问答
AI 与本地工具工作流结合
```

### Slide 12：总结与展望

```text
已实现完整 Agent 闭环
后续可扩展向量知识库、多群支持、官网链接自动核验、MCP 工具化
```

------

## 14. 汇报时要避免的说法

不要说：

```text
OpenClaw 完成了所有功能。
```

更准确的是：

```text
OpenClaw 作为 Agent 层和 Skill 调用入口，NapCat 负责 QQ 接入，FastAPI 负责业务工具编排，SQLite 和 Markdown 负责知识沉淀，DeepSeek 负责信息抽取和问答。
```

不要说：

```text
系统判断的信息都是真实的。
```

更准确的是：

```text
系统对信息做可信度标注，帮助用户发现线索，但最终仍需以官网和官方通知为准。
```

------

## 15. 一句话总结

CSBAOYANClaw 的核心价值是：

> 它把原本需要人工逐条浏览的保研 QQ 群消息，变成了一个可以自动整理、每日沉淀、历史检索和自然语言问答的保研情报 Agent。