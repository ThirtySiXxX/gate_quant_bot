# 安全须知

这个项目会用你的 Gate.io API Key 下真实订单，请务必读完这一页。

## API Key 存在哪里

```
data/credentials.json
```

**明文存储**，结构如下：

```json
{
  "api_key": "……",
  "api_secret": "……",
  "api_host": "https://api.gateio.ws/api/v4"
}
```

这个文件已经写进 `.gitignore`，不会被 git 跟踪。整个 `data/` 目录都被忽略了。

另有一份 `.env.example` 是早期版本留下的模板，当前程序**不再从 .env 读取密钥**，
密钥统一在网页「设置 → ① Gate.io API Key」里填写并保存到上面那个文件。

## 推到 GitHub 之前，务必确认

```bash
# 1. 确认凭证文件不在待提交列表里（应该没有任何输出）
git status --porcelain | grep credentials

# 2. 确认它确实被忽略了（应该输出 .gitignore 里那条规则）
git check-ignore -v data/credentials.json

# 3. 最保险：搜一遍暂存区里有没有像密钥的字符串
git diff --cached | grep -iE "api_key|api_secret" | grep -v example
```

## 申请 API Key 时的权限设置

申请地址：<https://www.gate.com/myaccount/apiv4keys>

- ✅ 只勾选 **合约交易（Futures Trade）** 和 **读取（Read）**
- ❌ **绝对不要勾选提现（Withdraw）** —— 程序完全用不到，勾了等于给密钥泄露后转走资金的权限
- ✅ 建议绑定 **IP 白名单**，限制为运行这个程序的机器的公网 IP

## 万一密钥泄露了怎么办

立刻去 Gate 后台 **删除该 API Key**（不是改权限，是删掉），然后重新申请一个。
如果已经推到了 GitHub，注意：**删除文件再提交是没用的**，密钥仍然留在 git 历史里，
必须先去 Gate 吊销密钥，然后再考虑用 `git filter-repo` 之类的工具清理历史。

## 其他风险提醒

- 程序默认 `mode: paper`（模拟盘）。切到 `live` 会用真实资金下单，
  网页上会有红色警告条和二次确认弹窗。
- `config.yaml` 也被 gitignore 了 —— 它不含密钥，但包含你的运行模式和参数，
  属于个人配置。别人 clone 后会从 `config.example.yaml` 自动生成一份。
- 「🧪 手动开单」页面在实盘模式下会真实成交，测试完记得平仓。
