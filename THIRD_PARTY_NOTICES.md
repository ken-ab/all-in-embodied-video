# Third-party notices

## cheat-on-content

- 来源：https://github.com/XBuilderLAB/cheat-on-content
- 合并版本：上游提交 `de3882d`（2026-11-02）
- 许可证：MIT，版权声明 `Copyright (c) 2026 cheat-on-content contributors`，原文保留在 [cheat/LICENSE](cheat/LICENSE)
- 位置：`cheat/`

### 合并时的改动

1. **改为本 skill 的子模块。** 上游根目录 `SKILL.md` 改名为 `cheat/PROTOCOL.md`，去掉 frontmatter，开头加入合并说明和路径约定；`skills/cheat-*/SKILL.md` 改为 `cheat/flows/cheat-*/FLOW.md`，文件之间的引用同步更新。这样整个包只有一个 `SKILL.md`，Codex 递归扫描时不会把子流程当成独立 skill。
2. **去掉独立安装相关文件**：`install.sh`、`uninstall.sh`、`README.md`、`docs/`、`.github/`、`.gitignore`、`tools/gen-star-history.py`、`tools/xkcd-font.css`。原来依赖 `~/.claude/skills`、`find ~ -path '*/cheat-on-content/...'` 或 `readlink` 定位源码的地方，改为 `<CHEAT_DIR>`（本 skill 目录下的 `cheat/`）。
3. **新增 `cheat/tools/reinstall-hooks.sh`**，替代上游 `install.sh --reinstall-hooks`。
4. **新增 `cheat/tools/prediction_lock.py`** 和测试 `prediction_lock_test.sh`。预测落盘后锁定各 `## 预测` 段的哈希，复盘前校验，不依赖 Claude Code 的 PreToolUse hook，Codex 里同样生效。`cheat-predict` 增加 Phase 6c，`cheat-retro` Phase 0 增加校验。
5. **修复 `douyin-session`、`xhs-explore`、`bilibili-stat`、`linkedin-session` 的 `run.sh`。** 上游在目标文件夹的上一级目录里查找第一个比目标文件夹新的 `report.md` 复制过来，`douyin-session` 随后删除找到的目录。连续多期时可能把别的期的报告当成本期结果并删除那一期的数据，抓取失败时还会返回成功。现在 `review.py` 写入项目 `.cheat-cache/` 下的私有临时目录，只接受恰好一份报告，抓取前删除旧报告，`review.py` 失败时返回 3，运行结束后只清理这个临时目录。同时支持 `CHEAT_PYTHON` 覆盖解释器（与 `wechat-channels` 一致），回归测试见 `cheat/adapters/perf-data/test_run_isolation.sh`。
6. 适配器 README、`cheat-migrate`、`cheat-seed` 和 `migrations/1.3-to-1.4.md` 中的安装路径说明相应更新。
