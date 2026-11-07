# All In 具身视频 Skill

用 Codex 把学习笔记做成短视频，发布后自动复盘。先交独立 HTML 和录制关键词，创作者围绕重点自由讲。收到实录后整理口播稿，从笔记取图做上半屏，再完成剪辑、封面和手机预览。确认发布笔记时可另做抖音或小红书图文。

发布后的打分、盲预测、数据抓取和复盘由内置的 `cheat/` 模块完成，它合并自 [cheat-on-content](https://github.com/XBuilderLAB/cheat-on-content)。返修和数据怎样回到下一期，见 [反馈与学习](references/反馈与学习.md)。

## 安装

把整个 `all-in-embodied-video` 文件夹复制到 Codex 的 `~/.agents/skills/`（Windows 上是用户目录下的 `.agents/skills/`）。在 Claude Code 里使用时复制到 `~/.claude/skills/`。开启新的对话，输入 `$all-in-embodied-video` 并附上当期笔记。

```text
用 $all-in-embodied-video 开始这一期。先给我学习笔记 HTML 和录制关键词。
```

整个包只有根目录一个 `SKILL.md`，`cheat/` 里的子流程叫 `FLOW.md`，不会被当成独立 skill。**如果以前单独装过 cheat-on-content**（例如 `~/.codex/skills/cheat-on-content`），请先移走那份，避免同一句「复盘」触发两套流程。你的内容数据都在制作项目里，移走 skill 不影响数据。

[Skill 入口](SKILL.md) · [完整制作流程](references/剪辑与上传规则.md) · [口播粗剪](references/口播粗剪.md) · [手机预览工具](references/手机预览.md) · [账号建档](references/账号建档.md) · [反馈与学习](references/反馈与学习.md) · [归档与复盘](references/归档与复盘.md)

## 环境

粗剪和预览工具需要 Python 3.11 或更新版本，以及环境中可用的 FFmpeg 和 FFprobe。粗剪提供静音候选、保留清单渲染、SRT 时间重排和解码检查。成片剪辑和发布使用创作者自己的编辑软件、素材和平台会话。

## 数据抓取准备

在制作项目根执行一次。`SKILL_DIR` 换成你实际安装的位置。

```sh
SKILL_DIR="$HOME/.agents/skills/all-in-embodied-video"
A="$SKILL_DIR/cheat/adapters/perf-data"

python3 -m venv .venv
source .venv/bin/activate
pip install -r "$A/douyin-session/requirements.txt" -r "$A/xhs-explore/requirements.txt" -r "$A/wechat-channels/requirements.txt"
playwright install chromium
```

然后逐个扫码登录，登录态只存在项目根：

```sh
python "$A/douyin-session/review.py" login      # 抖音创作者中心 → .auth/
python "$A/xhs-explore/review.py" login         # 小红书 → .auth-xhs/
python "$A/wechat-channels/review.py" login     # 视频号助手 → .auth-wechat-channels/
```

登录后把 `login` 换成 `list` 各跑一次，确认能看到自己最近的作品。登录态过期时重跑对应的 login。

## 第一次使用：建档

装好之后直接开始第一期就行。项目还没建档时，skill 会先一问一答帮你建档，大约 10 到 20 分钟：

1. 确认预设：教程类内容、自动抓数据、选题来自笔记。
2. 你的账号：三个平台的账号、这个系列讲什么给谁看、常见时长和发布节奏（能从项目里查到的会先查好请你确认）。
3. 导入历史：从抖音列出最近的作品，稿子直接用往期的口播稿，算出你的基准播放。
4. 对标账号：给 1 到 3 个想做成那样的账号，每个挑 5 到 10 条高中低都有的视频，粘贴文案、手填数据，再说说你觉得它好在哪、差在哪。

建档结果写进 `.cheat-state.json`、`benchmark.md`、`script_patterns.md` 和人能读的 `账号档案.md`。也可以随时说「建档」或「找对标」单独做。流程见 [账号建档](references/账号建档.md)。

## 定时复盘

定时复盘由 Dot 按 [归档与复盘](references/归档与复盘.md) 的排期触发：抖音 24 小时快照、72 小时正式复盘；小红书 24 和 72 小时快照；视频号 72 小时快照。

## 自检

```sh
bash cheat/adapters/perf-data/test_run_isolation.sh        # 数据脚本不会拿错或删掉其他期的报告
bash cheat/tools/prediction_lock_test.sh                   # 预测锁定与校验
bash cheat/adapters/perf-data/wechat-channels/test_run_contract.sh
python3 -m unittest discover -s cheat/adapters/perf-data/wechat-channels -p 'test_*.py'
bash cheat/tools/diff_pct_test.sh
```

## 许可证

仓库使用 MIT 许可证，保留版权和许可声明即可使用、修改及再分发。[MIT 许可证](LICENSE)

`cheat/` 来自 XBuilderLAB 的 cheat-on-content，同样是 MIT 许可证，原版权声明保留在 [cheat/LICENSE](cheat/LICENSE)。合并来源与改动见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
