# QF-QD-018 — Windows 迁移与续跑交接

历史前置审计：下文“尚无恢复入口”的状态已由 QF-QD-019 的实现与副本验证
取代。实际操作请看 `docs/WINDOWS_LOCAL_REPLAY.md` 和 QD019 报告。

日期：2026-10-29，Australia/Melbourne。本文提供迁移准备和恢复要求；
尚未实现或验证跨机器续跑入口。当前 Mac 回放继续暂停。

## 当前状态与必须携带的内容

- 开发目录：`/Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot`，
  分支 `codex/qd-cache-safety`。主目录的 `main` 不含这些开发提交。
- 当前版本基线：`91b02b429072a01f9876706352056a497a97c98b`；本文提交只添加文档。
- 本地市场缓存、账户、派生输入、累计配额记录和失败证据都在
  `research/.data/qd015/`。Git 不会携带这些未跟踪数据。
- 最新已提交账本时点：1026，`2024-02-04T03:00:00Z`；HEAD 审计前缀
  `7152d4294c0e71df250ef03632d865c101a1c8ae9d3c80d3826b03059ca4340d`。
- 本机 PID 13604 的状态是 `Ts`。它只是被操作系统挂起，不能迁移内存。
  CONTROL 3082 是尚未完成的 `write_guard`，且 `cache.sqlite3-journal` 存在。
  因此 HEAD 是最新已提交位置，不代表进程正停在干净的事务边界。

只迁移已确认的研究数据和代码，不携带 `.env`、真实 `config.yaml`、
`data/credentials.json`、真实账户文件或 Mac 虚拟环境。worktree 的 `.git`
是指向旧 Mac 主仓库的文件，不能当作独立 Git 仓库直接复制使用。

## 可以先做的迁移准备

Mac 上在开发目录导出已提交源码，输出文件名必须尚不存在：

```sh
cd /Users/lzh/.codex/worktrees/qd-cache-safety/gate_quant_bot
git archive --format=tar.gz --output="$HOME/Desktop/gate-qd-code.tar.gz" HEAD
```

迁移研究数据时必须保持所有写入者停止，完整保留
`research/.data/qd015/`（包括隐藏文件、SQLite 的 journal/WAL/SHM 旁文件，
不得只拷贝主 SQLite 文件）。这是冻结备份，不是已经验收的可续跑检查点。
复制前后应核对文件清单、大小和 SHA256；不删除旧目录或旧失败记录。
本任务没有实际制作数据包或重启进程。

Windows 管理员 PowerShell：

```powershell
wsl --install -d Ubuntu
```

按提示重启、启动 Ubuntu 并创建 Linux 用户，然后检查发行版运行在 WSL2：

```powershell
wsl -l -v
```

项目和数据放在 Ubuntu 的 `/home/<用户>/projects/gate_quant_bot` 下。
不要以 Windows 挂载目录 `/mnt/c/...` 作为这次大量账本写入的运行目录。
例如把源码压缩包放到 Windows 的 `C:\quant-transfer\` 后，在 Ubuntu 中：

```sh
mkdir -p ~/projects/gate_quant_bot
cd ~/projects/gate_quant_bot
tar -xzf /mnt/c/quant-transfer/gate-qd-code.tar.gz
```

Mac 的 `venv` 不可复用；新机需要重新创建 Linux Python 环境。先核对
Python/NumPy/pandas 和 SQLite 的兼容性，再确定依赖安装清单。
本次原环境为 Python 3.13.7、NumPy 2.5.2、pandas 3.0.5、SQLite 3.50.4。
当前身份校验包含整个 `sys.version`（含 Mac Clang 构建信息），只安装相同
版本号也不能让 Linux 自动通过原身份校验。

## 真正续跑前必须完成的适配

1. 在冻结副本上核对 HEAD、控制链、journal、索引和缓存，按已有恢复协议
   解决当前未完成 guard 的提交结果；不得凭 HEAD 序号猜测、删除 guard 或
   强制把状态改成 ACTIVE。
2. 为派生 source 根路径和资源日志中的旧绝对路径建立明确的迁移映射。
   GENESIS、旧 manifest、cache identity 和旧运行证据保持原样；不能全文
   替换 `/Users/lzh/...` 来假装原始身份没有改变。
3. 对 Linux 运行环境作明确的兼容性登记与必要的数值一致性检查，保留旧缓存
   身份，不改写 `sys.version` 或关闭校验来绕过绑定。
4. 新建一次有独立身份的迁移续跑入口，复用同一账户/缓存、保持原时间范围，
   保留前两次调用的资源消耗并排除明确记录的暂停/运输时间。继续遵守剩余
   外层资源限制；不能重置资金、序号或资源计数来重新开始。
5. 只在这些恢复检查通过后给出并执行新的启动命令；仍以失败即停、保留证据
   为准。数据和计算留在新电脑本地；不启动模型训练或实盘服务。

旧命令 `python -m research.qd016.entry --continue-approved ...` 已消费一次性
授权记录，重复运行会报 `CONTINUATION_ALREADY_CONSUMED_NO_RETRY`。
旧 QD015 入口也不是通用 resume 工具。当前没有可直接给 Windows 使用的
跨机器续跑命令，不应把环境安装或文件复制报告成恢复成功。

## 验证与后续交接

本任务只读检查：Git/worktrees、暂停进程、运行时版本、GENESIS 的环境绑定、
CONTROL/HEAD、SQLite 旁文件以及入口的一次性限制。未读取真实凭据、恢复
进程、转换数据、运行回放或安装依赖。仅新增本文，未更改金融逻辑、共享契约、
main 或 QR 文件。文档执行 whitespace 检查；没有声称完成 Windows 测试。

新电脑上的后续任务应是“实现并验证现有 BTC/ETH P0 账户的 WSL2 迁移恢复”，
而非重新跑一份账户。它需要 QD 处理恢复/路径/资源计数，并请 QR 审核运行环境
变化对数值和现有研究契约的影响。

官方环境说明：
- [安装 WSL](https://learn.microsoft.com/en-us/windows/wsl/install)
- [WSL 文件位置与性能](https://learn.microsoft.com/en-us/windows/wsl/filesystems)
