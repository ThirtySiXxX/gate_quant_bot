# Windows / WSL：接着当前进度运行 QD021

适用：已经能运行 QD019、且成功应用 QD020 SQLite 修复的 Ubuntu 项目。
继续使用现有 `.venv`、Python 3.13.7、numpy 2.5.2、pandas 3.0.5 和已安装
的 `pysqlite3-binary==0.5.4.post2`。不需要重装系统、虚拟机、CUDA 或重新下载行情。

## 安装更新

1. 把 `qd021-fast-replay.zip` 放进 Windows 的 `C:\quant-transfer`，在资源管理器
   中解压。确认存在 `C:\quant-transfer\qd021-fast-replay\apply-update.py`。
2. **另开一个 Ubuntu 窗口**。旧回放可以继续运行，先不要手动中断或重新启动它。
3. 在新窗口执行：

```bash
cd ~/projects/gate_quant_bot
.venv/bin/python -B /mnt/c/quant-transfer/qd021-fast-replay/apply-update.py
```

更新器校验现有代码后，只增加 QD021 文件。它自动暂停此项目唯一的旧回放进程，
从它的**当前已提交时点**复制一份独立数据，并核对副本每个文件的哈希。
随后显示 `Ready at current sequence ...`。原数据和暂停的旧进程保留，不自动恢复。
复制过程需要额外约一份当前数据大小的磁盘空间；校验、复制可能需要数分钟。
若出现 `STOPPED`、文件不匹配、多个进程或其他异常，请保留输出，停止操作并反馈。

4. 只有看到 `Ready` 后，执行：

```bash
bash scripts/qd021/run-fast.sh
```

启动时会核验历史日志、处理副本中的未完成事务，再显示 `FAST_REPLAY_ACTIVE`。
旧窗口保持暂停；**不要对旧进程执行 `kill -CONT`，也不要再运行旧 QD019 启动脚本**。
新数据位于 `research/.data/qd021-active/<本次编号>/qd015`，当前入口记录在
`research/.data/qd021-handoff/current.json`。原始输入、原账户历史、交易规则均保留。

## 运行、暂停与恢复

- 总墙钟时间、CPU、RSS、存储及累计写入额度不再人为限制。缓存按可见内存设置，
  这是缓存容量目标，实际内存与磁盘仍受电脑自身容量约束。
- 仍逐次同步持久化、核对哈希、校验时间可用性、精度及格式。真实异常停止，
  不会自动反复重试。有限的单包/解码/页大小等格式保护仍保留。
- BTC/ETH 共用一个连续账户，顺序不能拆成多个独立账户并行。当前热点是 CPU、
  JSON 与数据库；本版本不使用 RTX4060，也不训练或激活模型。
- 每约 30 秒输出进度。不要让 Windows 睡眠；WSL 项目应留在 Ubuntu 的
  `~/projects` 中运行。此处进度和资源数字均为本机数据。
- 要暂停时，在**新运行窗口**按一次 `Ctrl+C`，等待当前提交完成，直到出现
  `PAUSED_AT_COMMIT_BOUNDARY` 以及返回压缩包路径。不要强制关闭终端。
- 正常暂停后需要继续：先执行 `.venv/bin/python -B -m research.qd021.handoff`，
  看到 `Ready` 后再执行 `bash scripts/qd021/run-fast.sh`。每次恢复建立新副本和
  独立记录；不要删除旧副本，除非已经明确决定不再需要它。
- 若是错误停止，先发送证据，不要自行重复启动。

## 跑完给我哪些文件

结束或错误停止时，脚本自动生成项目根目录中的：

```text
return-to-codex-qd021-<时间>.tar.gz
```

把该压缩包和终端打印的 SHA256 发回来即可。包内包含运行结果、进度、错误、
当前检查点和完成后导出的 `episodes.jsonl` / 导出清单；不包含完整行情数据库、
凭据或虚拟环境。可复制到 Windows：

```bash
cp return-to-codex-qd021-*.tar.gz /mnt/c/quant-transfer/
```

若启动前就失败、没有生成返回包，发完整终端输出；原数据和失败副本都先保留。
完成状态应为 `FULL_CONTINUOUS_P0_COMPLETED`；仅跑完回放并不等于已经满足训练
样本、标签成熟度、成本、时序隔离等研究验收条件。

## 验证范围

Mac 上同一连续 16 时点、无性能分析器的基准：旧版 24.74 秒，新版 7.90 秒，
约 3.13 倍；每步 HEAD、完整视图哈希和经济状态哈希完全一致。这是短段工程
测量，不能保证 Windows 整段也有同样倍数。完整 BTC/ETH 长段由新电脑继续完成。
