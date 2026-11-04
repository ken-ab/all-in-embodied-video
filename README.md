# All In 具身视频 Skill

用 Codex 把学习笔记做成短视频。先交独立 HTML 和录制关键词，创作者围绕重点自由讲。收到实录后整理口播稿，从笔记取图做上半屏，再完成剪辑、封面和手机预览。确认发布笔记时可另做抖音或小红书图文。

## 安装

安装一次这个 Skill 即可使用内置的笔记、口播粗剪、封面和手机预览流程。

下载或克隆仓库，把整个 `all-in-embodied-video` 文件夹复制到 Codex 的 `~/.agents/skills/`。在 Windows 上用用户目录下的 `.agents/skills/`。开启新的 Codex 对话，输入 `$all-in-embodied-video` 并附上当期笔记。

```text
用 $all-in-embodied-video 开始这一期。先给我学习笔记 HTML 和录制关键词。
```

[Skill 入口](SKILL.md) · [完整制作流程](references/剪辑与上传规则.md) · [口播粗剪](references/口播粗剪.md) · [手机预览工具](references/手机预览.md) · [反馈与学习](references/反馈与学习.md)

粗剪和预览工具需要 Python 3.11 或更新版本，以及环境中可用的 FFmpeg 和 FFprobe。粗剪提供静音候选、保留清单渲染、SRT 时间重排和解码检查。成片剪辑和发布使用创作者自己的编辑软件、素材和平台会话。

发布后的数据采集和复盘依赖 [cheat-on-content](https://github.com/XBuilderLAB/cheat-on-content)：在制作项目根说「初始化 cheat-on-content」，内容形态选教程类，复盘数据来源选 adapter，并按它的适配器说明登录抖音、小红书和视频号。定时复盘由 Dot 触发。返修记录、制作规则和 Dot 交接单的模板在 `templates/`，整条回路见 [反馈与学习](references/反馈与学习.md)。

## 许可证

仓库使用 MIT 许可证，保留版权和许可声明即可使用、修改及再分发。[MIT 许可证](LICENSE)
