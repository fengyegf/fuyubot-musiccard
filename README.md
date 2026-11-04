# FuyuBot MusicCard

网易云音乐卡片插件，基于 FuyuBot Plugin SDK 构建。收到歌曲 ID、网易云歌曲链接或
搜索关键词后，插件会获取歌曲信息和歌词，生成一张 `650 x 1220` 的 JPEG 卡片，并以
照片回复触发命令的消息。

## 功能

- 支持歌曲 ID、网易云歌曲链接和关键词搜索。
- 自动读取中英文歌词，并按时间匹配原文与译文。
- 生成包含封面、歌曲信息、歌词、日期和歌曲二维码的卡片。
- 处理期间发送进度消息，完成后自动删除。
- 失败时回复具体原因，并清理临时文件与进度消息。

## 使用

```text
/musiccard 347230
/musiccard https://music.163.com/song?id=347230
/musiccard 周杰伦 晴天
```

无参数时会返回用法提示。命令前缀由宿主顶层配置 `[config] PREFIXES` 提供，默认支持
`/`、`!`、`！`、`.` 和 `#`。

## 处理流程

1. 解析命令并提取歌曲 ID、链接或关键词。
2. 调用网易云接口完成搜索、歌曲详情与歌词获取。
3. 下载封面，筛选最多 5 行歌词并匹配译文。
4. 通过 HTML 版面与 Rust 图像合成生成 JPEG 卡片。
5. 将图片发送到触发命令的聊天，并回复原消息。
6. 删除进度消息和本地临时文件。

任何一步失败都会结束当前任务并回复错误原因，不会影响其他正在执行的命令。

## 项目结构

| 路径 | 说明 |
| --- | --- |
| `src/lib.rs` | 插件入口、生命周期与消息订阅 |
| `src/config.rs` | 插件配置读取与临时目录处理 |
| `src/host/` | 宿主消息收发、更新路由与业务线程 |
| `src/cmd/` | 命令解析、分发与卡片业务流程 |
| `src/netease/` | 搜索、歌曲详情、歌词、封面下载与 LRC 解析 |
| `src/render/` | HTML 版面、二维码、背景与最终图片合成 |
| `src/model.rs` | 跨模块共享的数据结构 |
| `src/util/` | 文本处理等通用工具 |

## 配置

插件默认可以直接运行。需要自定义临时目录时，在主程序配置中增加：

```toml
[plugin.musiccard]
temp_dir = "C:/Temp/fuyubot-musiccard"

[config]
PREFIXES = ["/", "!", "！", ".", "#"]
```

`temp_dir` 未填写时使用 `<系统临时目录>/fuyubot-musiccard`。如果该目录无法创建，
插件会尝试使用宿主工作目录下的 `.musiccard-tmp`。

## 构建

需要 Rust 工具链。在插件目录执行：

```powershell
cargo fmt --check
cargo check
cargo clippy -- -D warnings
cargo build --release
```

发布产物为：

```text
target/release/musiccard.dll
```

仓库保留 `Cargo.lock`，用于固定依赖版本。`fuyubot-plugin-api` 的已发布版本已被
yank，因此不要直接删除锁文件或执行 `cargo update`。

可以继续检查动态库的导出符号和 ABI：

```powershell
..\..\fuyubot-sdk.exe check target\release\musiccard.dll
```

## 安装

将构建产物复制到主程序的 `plugins` 目录：

```powershell
Copy-Item target\release\musiccard.dll <FuyuBot目录>\plugins\
```

或使用主程序提供的安装命令：

```powershell
<FuyuBot目录>\fuyubot.exe plugin install target\release\musiccard.dll
```

启动后可以在日志中确认插件已激活。使用 `--no-tdlib` 可以在不连接 Telegram 的情况下
检查插件是否能够正常加载。

## 实现说明

- 卡片尺寸为 `650 x 1220`，最终以质量约 90 的 JPEG 输出。
- HTML 版面由 `hyper-render` 渲染；封面和二维码由 `image` 与 `qrcode` 在 Rust 侧
  合成。
- 网络请求使用阻塞式 `ureq`，运行在命令专用业务线程中，不阻塞宿主的消息接收线程。
- 临时文件名包含进程号、纳秒时间戳和递增序号，避免并发任务重名。
- 歌词按字符截断，避免中文和 emoji 被字节边界切坏。
- 卡片优先使用系统字体，常见中文环境会回退到 Microsoft YaHei 或 PingFang SC。
