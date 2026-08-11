# DeepSeek MCP Role Translator

一个轻量 MCP 服务器，解决 Android Studio 与 DeepSeek API 之间的角色名不兼容问题。

## 问题

Android Studio 的 AI 助手在发送消息时使用 `developer` 角色来传递系统指令，但 DeepSeek API 只认识 `system` 角色，不认识 `developer`，直接请求会报错。

## 解决

这个 MCP 服务器像一个翻译官坐在中间：

```
Android Studio ──(developer)──▶ MCP Server ──(system)──▶ DeepSeek API
Android Studio ◀──────────────────────────────────────────── DeepSeek API
```

收到 `developer` 角色的消息时，自动替换成 `system`，其余角色原样透传。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 DeepSeek API key：

```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

### 3. 启动服务器

双击 `run_http.bat`，或者在终端运行：

```bash
python server.py --http
```

窗口保持开着，服务器跑在 `http://localhost:8765/mcp`。

### 4. 在 Android Studio 中导入

打开 Android Studio → Settings → MCP → **Import JSON file**，选择项目里的 `mcp-config.json`。

看到 `Successfully connected to MCP server DeepSeek Translator` 就成功了。

## 文件结构

```
├── server.py          # MCP 服务器（~120 行）
├── run_http.bat       # Windows 一键启动脚本
├── mcp-config.json    # Android Studio 导入用配置文件
├── requirements.txt   # Python 依赖
├── .env.example       # 配置模板
└── .env               # 你的密钥（不提交到 git）
```
