# Dot 任务指令

每期实际发表后，按交接单在 Dot 里建下面 5 个一次性任务。尖括号换成交接单里的值，时间以各平台的实际发表时间为起点。每条指令都写明「无人值守」，让 skill 不当场等待回答。执行规则见 [归档与复盘](../references/归档与复盘.md)。

**72 小时那三个任务的顺序**：抖音复盘排在最前，小红书和视频号快照至少晚 30 分钟。两个平台发表时间接近时，按这个间隔错开。

### 1. 抖音 24 小时（发表后 24 小时）

```text
在 <项目根> 用 $all-in-embodied-video 执行：All In 具身 Day <N> 抖音 24 小时快照，无人值守。
作品 aweme_id <ID>。按 references/归档与复盘.md 的「快照怎么跑」执行，只取快照，不跑 cheat-retro。
核对报告属于本作品；失败按运行规则记 deferred_login 或 deferred_access。结果写进本期归档。
```

### 2. 小红书 24 小时（发表后 24 小时）

```text
在 <项目根> 用 $all-in-embodied-video 执行：All In 具身 Day <N> 小红书 24 小时快照，无人值守。
作品 note_id <ID>。按 references/归档与复盘.md 的「快照怎么跑」执行。
核对报告属于本作品；失败按运行规则记 deferred_login 或 deferred_access。结果写进本期归档。
```

### 3. 抖音 72 小时（发表后 72 小时）

```text
在 <项目根> 用 $all-in-embodied-video 执行：复盘 <predictions/xxx.md> — source: adapter，无人值守。
这是 All In 具身 Day <N> 的抖音正式复盘，作品 aweme_id <ID>，作品文件夹 <videos/...>。
开始前校验预测锁定；按 cheat/flows/cheat-retro/FLOW.md 的无人值守模式执行，需要创作者回答的事写进 待确认.md。
本期没有预测文件时改为 72 小时快照。
```

### 4. 小红书 72 小时（发表后 72 小时，排在抖音复盘之后）

```text
在 <项目根> 用 $all-in-embodied-video 执行：All In 具身 Day <N> 小红书 72 小时快照，无人值守。
作品 note_id <ID>。按 references/归档与复盘.md 执行快照，并把关键数字和报告路径追加到 <predictions/xxx.md> 复盘段的「附加平台数据」小节，注明不参与校准。
抖音正式复盘还没完成时，先只写本期归档，下次抖音复盘完成后再追加。
```

### 5. 视频号 72 小时（发表后 72 小时，排在抖音复盘之后）

```text
在 <项目根> 用 $all-in-embodied-video 执行：All In 具身 Day <N> 视频号 72 小时快照，无人值守。
作品 post_id <ID>。按 references/归档与复盘.md 执行快照，并把关键数字和报告路径追加到 <predictions/xxx.md> 复盘段的「附加平台数据」小节，注明不参与校准。
抖音正式复盘还没完成时，先只写本期归档，下次抖音复盘完成后再追加。
```
