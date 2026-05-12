# Literature Manager

## 产品功能

- 本地文件存储与上传（PDF/DOCX/TXT），自动抽取文本。
- 文献元数据管理（标题、作者、年份、期刊、摘要、引用）。
- 分类管理、列表浏览、分页与排序。
- 关键词检索与全文检索（SQLite FTS5 + 降级 like）。
- 导入/导出（CSV、BibTeX）。
- Agent 辅助建议。

### Agent API 接入说明

环境变量配置：

- AI_PROVIDER=api
- AI_CUSTOM_ENDPOINT
- AI_API_KEY=your-key (可选)
- AI_MODEL=your-model
- AI_TIMEOUT_SECONDS=30

API 返回格式示例：

```json
{
  "title": "My Paper Title",
  "authors": "Alice; Bob",
  "year": 2024,
  "category_suggest": "Machine Learning"
}
```

curl 调用示例：

```bash
curl -s http://127.0.0.1:8000/agent/status
```

```bash
curl -s -X POST http://127.0.0.1:8000/agent/suggest \
   -H "Content-Type: application/json" \
   -d '{"literature_id": 1}'
```

```bash
curl -s -X POST http://127.0.0.1:8000/agent/suggest \
   -H "Content-Type: application/json" \
   -d '{"text": "Paper Title\nAuthor: Alice\n2024\n..."}'
```

## 技术栈

- 后端：FastAPI、Uvicorn、SQLAlchemy、SQLite（含 FTS5）、Pydantic。
- 文件解析：pdfplumber、python-docx、chardet。
- Agent 接口：OpenAI 兼容或自定义 HTTP API（httpx）。
- 前端：原生 HTML/CSS/JavaScript。
- 测试：pytest。

## 环境依赖

- Python >= 3.13（见 pyproject.toml）。
- SQLite（需支持 FTS5）。
- Windows 下推荐 PowerShell 5+。

## 项目目录结构预览

```
Literature management/
├── Backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── utils.py
│   ├── migrations/
│   ├── packaging/
│   ├── tests/
│   ├── requirements.txt
│   └── run.py
├── DesktopApp/
│   ├── Frontend/
│   ├── main.js
│   ├── package.json
│   └── preload.js
├── Frontend/
│   ├── css/
│   ├── js/
│   └── index.html
├── docs/
├── scripts/
├── launch.bat
├── launch_portable.bat
├── main.py
├── pyproject.toml
├── README.md
└── start.bat
```

## 环境变量说明

通用配置：

- DB_PATH：数据库文件路径，默认 store.db。
- STORAGE_ROOT：上传文件存储根目录，默认 Backend/uploads。
- CORS_ORIGINS：允许跨域来源，逗号分隔，默认 \*。
- AUTH_ENABLED：是否开启 API Key 校验，默认 false。
- API_KEY：API Key，默认 change-me。
- ALLOWED_EXTENSIONS：允许上传的文件扩展名，默认 pdf,docx,txt。
- LOG_LEVEL：日志级别，默认 INFO。

运行与入口：

- LM_HOST：打包入口使用的监听地址，默认 127.0.0.1。
- LM_PORT：打包入口使用的端口，默认 8000。

## Agent 配置

Agent 配置支持两种来源：

- 环境变量。
- 运行时配置文件 Backend/agent_config.json（通过 /config/agent 写入）。

字段说明：

- AI_PROVIDER：disabled | openai | api/custom。
- AI_BASE_URL：OpenAI 兼容接口基础地址。
- AI_CUSTOM_ENDPOINT：自定义接口地址。
- AI_API_KEY：API Key（可选）。
- AI_MODEL：模型名称。
- AI_TIMEOUT_SECONDS：超时时间（秒），默认 30。
- AI_CACHE_TTL_SECONDS：缓存有效期（秒），默认 300。
- AI_CACHE_MAX_ITEMS：缓存最大条目数，默认 256。

## 开发进度

- 已完成：文献 CRUD、上传与解析、分类管理、全文检索、导入/导出、Agent API 接入与规则降级、Storage Root 配置。
- 已完成：前端编辑页显示 Agent 模式与模型名（/agent/status）。
- 已完成：前端搜索结果渲染与后端返回结构对齐。
- 已完成：后端标题校验、上传路径安全校验、导入结果统计与错误输出。
- 运行方式：进入 Backend 安装依赖后，使用 `python run.py` 或 `start.bat` 启动服务。

## 开发调试说明

依赖安装：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r Backend\requirements.txt
```

启动后端：

```powershell
python Backend\run.py
```

开发模式工作流（简述）：

1. 修改后端代码（Backend/app）。
2. Uvicorn 在 --reload 模式下自动重载。
3. 前端直接打开 Frontend/index.html 或通过桌面版加载。
4. 使用 /agent/status、/agent/suggest 或业务接口进行功能验证。

## 项目智能体（Agent）功能概述

这个文献管理项目的智能体系统由 services/ 目录下的三个核心模块组成，主要负责自动元数据提取与建议：

1. agent_service.py — 智能体核心服务
   这是智能体的主控制器，提供两种元数据提取模式：

AI 模式（OpenAI / Custom API）：当配置了 OpenAI 或自定义 AI 接口时，将文献文本片段（前 2000 字符）发送给大语言模型，让 AI 自动提取 JSON 格式的元数据（标题、作者、年份、建议分类）。
规则模式（回退方案）：当 AI 不可用时，自动降级为基于规则的本地提取（调用 agent_tools.extract_basic_metadata）。
核心方法：

方法 功能
suggest_metadata() 接收文本/文件名，返回元数据建议（带缓存）
get_status() 返回 AI 是否可用、当前模式、使用的模型
\_call_openai() 调用 OpenAI 兼容 API 提取元数据
\_call_custom() 调用自定义 AI 端点提取元数据 2. agent_tools.py — 规则引擎工具
当 AI 不可用时，使用纯规则方法提取元数据：

extract_basic_metadata()：从文本中提取标题（取第一行有效内容）、作者（识别 "Author/Authors/By" 开头的行）、年份（正则匹配 19xx/20xx）、分类建议。
suggest_category()：基于关键词匹配推荐分类，支持识别机器学习、计算机视觉、NLP、信息检索、图学习、量子计算、大语言模型等领域。
read_text_from_path()：从 .txt 文件读取文本内容。3. agent_memory.py — 智能体记忆/缓存
一个带 TTL 和容量限制的 LRU 缓存系统：

对相同的文本内容进行 MD5 哈希去重，避免重复调用 AI（节省成本和延迟）。
支持可配置的过期时间（ttl_seconds）和最大条目数（max_items）。
自动淘汰过期条目和超出容量限制的最旧条目。
整体工作流程
配套服务（支撑智能体运行）
file_parser.py：文件解析器，支持从 PDF（pdfplumber）、DOCX（python-docx）、TXT（自动检测编码）中提取文本，为智能体提供原始文本输入。
fts_manager.py：全文搜索管理器（FTS5），使用 BM25 算法对文献的标题、作者、摘要、正文建立全文索引，支持高亮片段生成，让用户能快速检索文献库。
