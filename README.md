# DeepSeek Role Translator

HTTP 代理 + MCP 服务器。解决 Android Studio 的 Gemini/Claude 等 AI 插件发送 `developer` 角色给 DeepSeek API 时报错的问题——自动把 `developer` 翻译成 DeepSeek 认识的 `system`。

## 原理

```
Android Studio ──(developer)──▶ localhost:8765 ──(system)──▶ api.deepseek.com
Android Studio ◀─────────────────────────────────────────────── api.deepseek.com
```

代理在本地拦截所有 `/v1/chat/completions` 请求，把 messages 里的 `developer` 角色替换成 `system`，其余字段原样透传。同时暴露 MCP 端点，供 Android Studio 发现和调用。

## 使用步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入 DeepSeek API key 和模型：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-pro
```

> 模型可选 `deepseek-v4-pro` 或 `deepseek-v4-flash`。

### 3. 启动服务器

双击 `run_http.bat`，或在终端运行：

```bash
python server.py --http
```

看到以下输出表示启动成功：

```
代理 + MCP 已启动: http://localhost:8765
  代理端点:     http://localhost:8765/v1
  MCP 端点:     http://localhost:8765/mcp
INFO:     Uvicorn running on http://127.0.0.1:8765
```

> 窗口保持开着，不要关。

### 4. 配置 Android Studio

两步都要做：

**① 导入 MCP 配置**

Settings → MCP → Import JSON file → 选择项目里的 `mcp-config.json`。看到 `Successfully connected to MCP server DeepSeek Translator` 即完成。

**② 配置 AI Provider**

Settings → AI Provider（或你使用的 AI 插件设置），添加一个新的 provider：

| 字段 | 值 |
|------|-----|
| URL Schema | OpenAI / OpenAI Compatible |
| Base URL | `http://localhost:8765/v1` |
| API Key | 和 `.env` 里一样的 DeepSeek key |
| Model | `deepseek-v4-pro` 或 `deepseek-v4-flash` |

> 关键：Base URL 必须是 `http://localhost:8765/v1`，不是 `https://api.deepseek.com`。这样请求才会经过本地代理做角色翻译。

### 5. 使用

正常在 Android Studio 里用 AI 聊天即可，角色翻译在后台自动完成，完全无感。

## 验证

启动服务器后，如果看到终端输出以下日志，说明代理正在工作：

```
GET /v1/models HTTP/1.1 200 OK
POST /v1/chat/completions HTTP/1.1 200 OK
```

## 常见问题

**Q: 提示 `unknown variant developer`？**

AI Provider 的 Base URL 没有指向本地代理，还是直连的 DeepSeek。确认 Base URL 是 `http://localhost:8765/v1`。

**Q: 提示 `UNAVAILABLE: io exception`？**

服务器没启动。双击 `run_http.bat` 启动。

**Q: 改了 `.env` 需要重启吗？**

需要。关掉 `run_http.bat` 窗口，重新打开。

## 文件结构

```
├── server.py          # 代理 + MCP 服务器
├── run_http.bat       # Windows 一键启动脚本
├── mcp-config.json    # Android Studio MCP 配置（导入用）
├── requirements.txt   # Python 依赖
├── .env.example       # 配置模板
└── .env               # API key（不提交 git）
```
