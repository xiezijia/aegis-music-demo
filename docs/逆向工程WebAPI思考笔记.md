# 如何逆向工程一个没有公开 API 的 Web 服务

> 以对接 Suno 为例，完整记录思考过程与试错逻辑
> 
> 作者：通过 Claude Code 实战整理 | 2026-04-09

---

## 一、核心思维模型：把浏览器当成"参考样本"

当一个服务没有公开 API 时，你面对的不是一堵墙，而是一扇窗——**浏览器**。

浏览器每次打开网页、点击按钮，背后都在发送 HTTP 请求。这些请求和我们用代码发的请求，本质上完全一样。区别只有一个：**浏览器带着登录凭证（Cookie/Token），我们的代码没有**。

所以，解决问题的核心思路是：
1. 让浏览器帮你登录，拿到凭证
2. 弄清楚浏览器在发什么请求
3. 用代码模拟同样的请求，带上同样的凭证

这就是所谓的"Cookie 注入"或"会话劫持"方法（在自己账号上合法使用）。

---

## 二、第一步：搞清楚"凭证"是什么

### 什么是 Cookie？

你登录任何网站后，服务器会给你的浏览器一个"通行证"，存在 Cookie 里。之后每次请求，浏览器自动把这个通行证带上，服务器就知道是你。

### Suno 的凭证结构

Suno 使用 **Clerk** 作为认证系统，凭证分两层：

| Cookie 名 | 作用 | 有效期 |
|-----------|------|--------|
| `__session` | 短期 JWT 访问令牌，每次 API 请求都要带 | 约 1 小时 |
| `__client` | 长期刷新令牌，用来换取新的 `__session` | 约 1 年 |
| `sessionid` | 旧域名（studio-api.prod.suno.com）的 Django session | 随 __session 变化 |

**关键认知**：`__session` 是一个 JWT（JSON Web Token）。你可以把它复制到 [jwt.io](https://jwt.io) 里解码，看到里面包含了用户 ID、邮箱、过期时间等信息。它本质上是一个"自包含的身份证明"。

### 如何拿到这些凭证

**方法一（手动）**：
1. 打开浏览器开发者工具（F12）
2. 切到 Application → Cookies → suno.com
3. 找到 `__session` 和 `__client`，复制值

**方法二（自动化，我们用的方式）**：
```python
# 用 Playwright 启动一个受控浏览器
playwright-cli open https://suno.com --headed
# 用户手动完成 Google 登录
# 然后自动提取所有 Cookie
playwright-cli cookie-list
playwright-cli state-save session.json  # 保存完整状态
```

---

## 三、第二步：找到真正的 API 端点

### 为什么要"找"端点？

大多数 Web 服务不公开他们的内部 API 文档。但这些 API 一直都在运行——你的浏览器每次操作都在调用它们。

### 抓包：看浏览器在发什么

工具：浏览器开发者工具的 **Network 标签页**，或者我们用的 Playwright 网络监控。

```bash
playwright-cli network  # 列出所有网络请求
```

**我们的试错过程**：

**第一次猜测（错误）**：
```
POST https://studio-api.prod.suno.com/api/generate/v2/
```
这是从旧版本的第三方博客找到的端点，但 Suno 已经迁移了域名。

**发现错误的方式**：
直接打 API → 返回 401 Unauthorized → 说明要么认证有问题，要么地址不对。

**用 Playwright 实际监控网络**：
```bash
playwright-cli network 2>&1 | grep "studio-api"
```
输出里看到了真正的域名：`studio-api-prod.suno.com`（连字符，不是点）

这是第一个关键发现：**域名从 `studio-api.prod.suno.com` 变成了 `studio-api-prod.suno.com`**。

**第二次发现（轮询接口不同）**：

我们以为生成请求提交后，要轮询 `/api/clip/{clip_id}` 来查状态。

但监控网络后发现 Suno 实际用的是：
```
POST /api/feed/v3   body: { "ids": ["clip_id_1", "clip_id_2"] }
```

这是第二个关键发现：**不是 GET 单个 clip，而是 POST 批量查询 feed**。

### 看不到请求体怎么办？

当网络日志只显示 URL 不显示 body 时，用 JavaScript 拦截：

```javascript
// 在 Playwright eval 里注入这段代码
window.__feedData = {};
const origFetch = window.fetch;
window.fetch = async (...args) => {
    const res = await origFetch(...args);
    const url = args[0]?.url || args[0] || '';
    if (url.includes('feed/v3') || url.includes('generate')) {
        const clone = res.clone();
        clone.json().then(data => {
            window.__feedData[url] = JSON.stringify(data).substring(0, 1000);
        });
    }
    return res;  // 原样返回，不影响正常流程
};
```

这个技巧叫**"Monkey Patching"**：偷偷替换浏览器内置的 `fetch` 函数，在它前后加入你的监听逻辑，但不影响原有功能。

---

## 四、第三步：理解 401 错误的真正原因

### 401 不一定是 Token 过期

我们第一次遇到 401 时的排查思路：

```
第一反应：Token 过期了 → 刷新 Token → 还是 401
→ 说明不是 Token 的问题

第二反应：端点地址错了 → 换成 v2-web → 还是 401
→ 说明不是端点的问题

第三反应：少了某个必要的 Header → 检查浏览器请求 Headers
→ 浏览器带了 Referer 和 Origin，我们的代码没有
```

### 关键 Header：Referer 和 Origin

很多 API 会检查请求来源，防止 CSRF 攻击：

```python
headers = {
    "Cookie": session_cookie,
    "Origin": "https://suno.com",        # 告诉服务器请求来自哪个页面
    "Referer": "https://suno.com/create", # 更具体的来源页面
    "User-Agent": "Mozilla/5.0 ...",      # 伪装成真实浏览器
}
```

**这三个 Header 缺一不可**：服务器看到没有 Origin/Referer，会怀疑是自动化脚本或跨站请求，直接拒绝。

### 神秘的 sessionid 域名问题

```
sessionid 设置在：studio-api.prod.suno.com（旧域名，点分隔）
API 实际地址：    studio-api-prod.suno.com（新域名，连字符）
```

浏览器发请求时，Cookie 只会发给对应域名。sessionid 对新域名无效，所以要去掉。

**教训**：Cookie 有"域名绑定"属性，不同域名之间不共享。迁移了域名的服务，旧 Cookie 可能悄悄失效。

---

## 五、第四步：Token 过期的自动刷新机制

### 为什么要自动刷新？

`__session` JWT 大约每小时过期一次。演示时不可能每小时手动重新登录。

### Clerk 的刷新机制

Suno 用 Clerk 管理认证。Clerk 的 Token 刷新接口：

```
GET https://clerk.suno.com/v1/client?_clerk_js_version=5.36.0
Cookie: __client={长期刷新令牌}
```

返回里会有新的 `__session` JWT：
```json
{
  "response": {
    "sessions": [{
      "last_active_token": {
        "jwt": "新的__session值"
      }
    }]
  }
}
```

**刷新策略**：
```python
for attempt in range(2):      # 最多尝试 2 次
    r = await http.post(endpoint, ...)
    if r.status_code == 401 and attempt == 0:
        await _refresh_token()  # 只在第一次失败时刷新
        continue                # 用新 Token 重试
    if r.status_code != 200:
        raise RuntimeError(...)
    # 成功
```

---

## 六、完整的 API 调用流程（最终版）

```
用户输入描述
     ↓
POST /api/generate/v2-web/
{
  "gpt_description_prompt": "忧郁的秋天，古筝意境",
  "tags": "古风 民族",
  "mv": "chirp-fenix",   # 最新模型版本
  "make_instrumental": true
}
     ↓
返回 clip_ids: ["abc123", "def456"]
     ↓
每 5 秒轮询一次：
POST /api/feed/v3
{ "ids": ["abc123", "def456"] }
     ↓
返回 clips[].status == "complete"
     ↓
clips[0].audio_url = "https://cdn1.suno.ai/abc123.mp3"
     ↓
播放
```

---

## 七、Playwright 作为"认证代理"的思路

当 Cookie 方法不稳定时，还有一个更可靠的方案：**让 Playwright 直接帮你操作浏览器**。

不是用 Python 发 HTTP 请求，而是让 Playwright 控制真实浏览器点击页面。

```python
# 让 Playwright 填写表单并点击
await page.fill('textbox[name="prompt"]', '忧郁的秋天，古筝意境')
await page.click('button[name="Create song"]')

# 等待生成完成，从 DOM 或网络拦截器拿音频 URL
await page.wait_for_selector('audio[src*="cdn1.suno.ai"]')
audio_url = await page.query_selector('audio')
```

这个方法的优点：**永远不会有 401 问题**，因为浏览器自己管理所有 Cookie 和 Token，你不需要理解任何认证细节。

缺点：比较慢（每次都要真正打开浏览器），不适合高并发。

---

## 八、文件系统权限问题：macOS TCC

这次遇到了一个意外：代码无法写入 Desktop 文件夹。

**原因**：macOS 的 TCC（Transparency, Consent, and Control）系统保护了 Desktop、Documents、Downloads 等目录，需要明确授权程序才能访问。

**解决思路**：
1. 识别哪些路径可写（home 目录 `~/` 通常没有额外限制）
2. 把要写的内容生成到可写路径
3. 让用户用自己的 Terminal（有完整权限）执行一步复制

**教训**：在自动化脚本里，要区分"哪些路径是程序可写的"和"哪些路径需要用户权限"。不要假设所有路径都可以写。

---

## 九、核心方法论总结

```
遇到"没有 API"的服务时：

1. 打开浏览器开发者工具 → 看 Network 标签
2. 手动操作一次，找到关键 HTTP 请求
3. 复制该请求的：URL、Method、Headers、Body
4. 用代码复现这个请求（带上 Cookie）
5. 如果返回 401：检查 Token 是否过期、Header 是否完整
6. 如果返回 200 但数据不对：检查 Body 格式是否正确
7. 写自动 Token 刷新，让它能长期运行
```

**最重要的一句话**：

> 浏览器能做到的事，代码都能做到——只要你搞清楚浏览器在做什么。

---

## 附：本次对接的关键发现时间线

| 时间 | 发现 | 方式 |
|------|------|------|
| 第1步 | 正确域名是 `studio-api-prod.suno.com` | Playwright network 监控 |
| 第2步 | 生成接口是 `/api/generate/v2-web/` 不是 `/api/generate/v2/` | Network 过滤 + 等待真实点击 |
| 第3步 | 轮询用 `POST /api/feed/v3` 不是 `GET /api/clip/{id}` | JS fetch 拦截器 |
| 第4步 | 最新模型名是 `chirp-fenix`（v5.5），不是 `chirp-v4-5` | feed/v3 响应数据 |
| 第5步 | 401 原因之一是 sessionid 绑定旧域名 | 对比新旧 Cookie 域名 |

---

*这份笔记的意义不在于记住步骤，而在于理解：**每一个运行中的 Web 服务，都是一个可以观察、可以学习的老师**。*
