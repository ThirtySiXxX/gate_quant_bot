# Windows：从空环境接着本地 BTC/ETH P0 回放

适用分支：`codex/qd-cache-safety`。这份迁移只继续原研究账户，不改变交易
规则、不重置资金、不训练模型。经济区间仍为 2024-01-01 至 2026-10-01
（终点不含），保留 2023 预热数据和原来的 2 小时尾段。

## 需要的文件与机器

- Windows 11，或支持 WSL2 的 Windows 10；管理员权限、联网安装环境。
- 本地 SSD 至少预留 25 GB。回放主要使用 CPU；无需显卡/CUDA。
- 源码：GitHub 的 `codex/qd-cache-safety` 分支，或迁移包内的源码压缩包。
- 数据：单独的 `gate-qd-data.tar.gz`。数据留在本地，没有提交到 Git。
- 空环境不能直接运行 Python 模块；下面的安装脚本会准备 Python 3.13.7
  和固定依赖，然后校验代码与数据。不要复制 Mac 的虚拟环境。

## 1. 安装 WSL2

管理员 PowerShell：

```powershell
wsl --install -d Ubuntu
```

按提示重启电脑，打开 Ubuntu，创建 Linux 用户与密码。PowerShell 中运行
`wsl -l -v` 确认 Ubuntu 的 VERSION 为 2。若已有 Ubuntu 但版本是 1，执行
`wsl --set-version Ubuntu 2`。后续命令都在 Ubuntu 窗口中执行。

## 2. 放好代码与数据

例如把 `gate-qd-data.tar.gz` 放到 Windows 的 `C:\quant-transfer\`。
项目运行目录放在 Ubuntu 的 Linux 磁盘下，避免从 `/mnt/c/...` 运行账本。

若使用源码压缩包，在 Ubuntu 执行：

```sh
mkdir -p ~/projects/gate_quant_bot
cd ~/projects/gate_quant_bot
unzip /mnt/c/quant-transfer/gate-qd-code.zip
```

若 Ubuntu 尚无 unzip，可先执行 `sudo apt-get update` 和
`sudo apt-get install -y unzip`。源码包内文件直接位于项目根目录。

若从 Git 获取代码，在 Ubuntu 安装 Git 后执行：

```sh
sudo apt-get update
sudo apt-get install -y git
mkdir -p ~/projects
cd ~/projects
git clone --single-branch --branch codex/qd-cache-safety https://github.com/ThirtySiXxX/gate_quant_bot.git
cd gate_quant_bot
```

私有仓库使用你自己的 GitHub 登录权限，不需要任何交易所凭据。GitHub
网页下载的 ZIP 可能有外层目录；进入包含 `AGENTS.md` 和 `scripts/` 的目录。

## 3. 一次性准备 Python、固定依赖并校验迁移数据

在项目根目录运行：

```sh
bash scripts/qd019/setup-wsl.sh /mnt/c/quant-transfer/gate-qd-data.tar.gz
```

脚本需要输入 Ubuntu 的 sudo 密码；安装 curl、CA 证书、Git、uv、Python
3.13.7，以及 `requirements-qd019.lock` 的固定依赖。数据解压到
`research/.data/qd019-import/`，校验每个文件的大小与 SHA256，验证源代码
身份和运行环境。看到 `READY_FOR_LOCAL_RESUME` 后再进行下一步。

安装脚本避免覆盖已有导入目录或 `.venv`。若中途安装失败，保留终端输出，
先查明原因，不要删除运行证据或用旧入口强行启动。依赖安装联网；正式回放
期间 Python 的网络入口关闭，所有计算和输出保存在本机。

### 已安装环境遇到 `_sqlite3` 没有 `__file__` 时

保留原来的 `return-to-codex-20261029T074002190598Z.tar.gz` 和 `local-logs/`。
把小补丁 `qd020-sqlite-fix.zip` 解压到 Windows 的
`C:\quant-transfer\qd020-sqlite-fix`，然后在 Ubuntu 项目目录执行：

```sh
.venv/bin/python /mnt/c/quant-transfer/qd020-sqlite-fix/apply-fix.py
```

补丁仅在确认没有 launch/迁移记录且 HEAD/CONTROL/SPENT/GENESIS 仍匹配冻结
检查点时应用，拒绝覆盖自行改过的源码。原源码会备份；失败日志和返回包保留。
补丁自带固定版本、校验过的 Linux SQLite 接口安装包，不需要重建虚拟环境或
重新下载研究数据。数据 manifest 保持原样，新增源码通过明确的修复哈希覆盖表
验收，而非关闭身份校验。前次失败启动的日志时间区间保守计入剩余资源预算。

看到 `READY_FOR_LOCAL_RESUME` 后，继续下方启动命令。新的预检查还会在临时
数据库证明写入确实经过配额拦截，并拒绝超额写入；不打开研究账户。

## 4. 启动一次连续回放

```sh
bash scripts/qd019/run-local-replay.sh
```

这会从原来的第 1026 个已提交时点（2024-02-04 03:00 UTC）续跑。启动时
验证整个已提交 journal 哈希链，恢复复制过来的 SQLite 事务，并根据 HEAD、
索引与未发布请求的证据解决挂起 guard；不会重新回放已接受的 1026 个时点。
旧路径和构建环境通过明确的迁移记录映射，原始 GENESIS 和历史证据不改写。

新环境接下来的 16 个时点必须逐个与 Mac 原始适配器计算的数值参考完全一致，
每个检查发生在发布该时点之前；不一致立即停止。通过后显示
`New machine numerical validation passed.`。约每 30 秒打印当前账本进度。

原累计 wall 4 小时、CPU 3 小时、RSS 1 GiB、总输出 12 GiB 和账本 10 GiB
限制继续保留；前两次调用的消耗不清零。已记录的暂停/运输时间不算运行时间，
未落盘的暂停前消耗按保守上界补计。更快的 CPU 不保证一定在剩余限额内跑完。
任何新错误或超限都停止，不会自动重试。

保持电脑供电、避免睡眠，保留 Ubuntu 窗口。不要同时在 Mac 上恢复旧进程。
若主动 Ctrl+C 或断电，保留数据和日志；本入口不承诺任意中断后自动恢复，
需要根据新留下的事务证据另行处理。

## 5. 跑完或失败后发回什么

启动脚本结束时自动生成项目根目录的：

```text
return-to-codex-<UTC时间>.tar.gz
```

把这个文件给我即可。里面包含本次成功/失败结果、运行日志、环境一致性验证、
最新 HEAD/CONTROL/SPENT、缓存财务视图，以及已生成的 episode JSONL 和 manifest。
日志、无效/未成熟样本与失败原因一并保留，不会把未完成结果称为完整训练集。

若自动收集未执行，可在程序已停止后手动运行：

```sh
.venv/bin/python -B -m research.qd019.collect
```

如需从 Windows 文件管理器找到结果，在 Ubuntu 项目目录执行 `explorer.exe .`。
完整的 `research/.data/qd019-import/` 继续保留在新机，不必先传回数 GB 的账本。
若小结果包不足以定位问题，我会再明确指定所需的 journal 或完整状态文件。
不要发送 `.env`、真实配置、API 密钥、凭据文件或 Mac 虚拟环境。

完成标志是 `FULL_CONTINUOUS_P0_COMPLETED` 和 export manifest；这仍然只是
研究回放/样本导出完成，不表示已训练或批准任何模型，也不代表未来盈利能力。

发布前已在 Mac 的独立目录副本完成 16 个时点恢复验证，并验证错误数值参考
不会发布新提交。尚未在你的 Windows 实机上运行；新机首次启动的环境与数值
检查必须通过后才会继续，检查失败时发送自动收集的结果包。

官方环境说明：[安装 WSL](https://learn.microsoft.com/en-us/windows/wsl/install)、
[WSL 文件存放](https://learn.microsoft.com/en-us/windows/wsl/filesystems)、
[uv 安装](https://docs.astral.sh/uv/getting-started/installation/)、
[uv 安装指定 Python](https://docs.astral.sh/uv/guides/install-python/)。
