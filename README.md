# Literature Manager

Local-first literature manager with FastAPI backend and a minimal frontend.

## Folders

- Backend: FastAPI app, SQLite database, uploads
- Frontend: static HTML/JS UI
- Store: optional data storage if needed later

## Quick Start

1. Create a Python environment
2. Install dependencies in Backend
3. Start the API with `python run.py` or `start.bat`

## Dev Schema Reset (Fast Path)

During development, if models change and the DB schema is out of date, delete
`Backend/store.db` and restart the backend to recreate tables.

## Storage Root (Plan A)

The server stores uploads under a storage root directory. By default it uses `Backend/uploads`.
You can change it at runtime with:

- GET `/config/storage-root`
- PUT `/config/storage-root` with `{ "storage_root": "D:\\Your\\Path" }`

The updated path is saved to `Backend/storage_config.json`.

## 总体设计目标

构建一个**完全本地运行、本地存储**的文献管理系统，具备：

- **文献文件识别与存储**：支持 TXT、PDF、DOCX 等格式，提取并保存全文文本，同时保存原始文件副本。
- **分类管理**：用户可自定义分类（如“机器学习”、“量子物理”），文献归属到某分类（一对多或单分类，初期简化为一对一）。
- **查询功能**：支持按标题、作者、年份、分类、正文内容模糊检索，可选全文检索。
- **人工填写元数据**：提供表单，手动录入/编辑文献的标题、作者、发表年份、期刊/会议、摘要等基本信息。
- **智能 Agent**：自动从文献内容中提取元数据（标题、作者、年份等），并推荐分类；可选摘要生成；用户可以采纳建议并一键填充表单。

技术栈选择原则：**轻量、纯本地、易于 AI 辅助编码**。最终交付是一个可在本地启动的 Web 应用（通过浏览器访问），所有数据存储在本地目录。

---

## 技术栈详细推荐

| 模块           | 技术选型                                                                      | 理由                                                                 |
| -------------- | ----------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **后端框架**   | Python 3.10 + FastAPI                                                         | 自动生成 API 文档、异步支持、易于与 AI 库集成。                      |
| **数据库**     | SQLite + SQLAlchemy ORM                                                       | 嵌入式无服务器，文件级存储，符合“本地存储”。配合 FTS5 实现全文检索。 |
| **文件解析**   | `pdfplumber`（PDF）<br>`python-docx`（DOCX）<br>`chardet`（TXT 编码）         | 准确提取文本内容及部分元数据。                                       |
| **前端**       | HTML5 + TailwindCSS + Alpine.js（或轻量 Vue）                                 | 无需 node 构建，直接在模板中开发，快速实现动态交互。                 |
| **Agent 引擎** | **Ollama** + 本地 LLM（如 `llama3.2:3b` 或 `qwen2:7b`）<br>备选：轻量规则提取 | 完全本地推理，不依赖网络。通过 HTTP API 调用，集成简单。             |
| **全文检索**   | SQLite FTS5 虚拟表 + SQLAlchemy 钩子                                          | 内置支持，高效且无须额外搜索引擎。                                   |
| **打包/运行**  | `uvicorn` 启动服务，浏览器访问 `localhost:8000`                               | 无需 Electron 复杂打包，用户双击脚本即用。                           |

---

## 系统架构与模块划分

```
文献管理系统（本地 Web 应用）
├── 后端 FastAPI
│   ├── API 路由 (文献 CRUD、分类管理、查询、Agent 建议)
│   ├── 文件解析服务 (pdf/docx/txt -> 纯文本)
│   ├── Agent 服务 (调用 Ollama，提取元数据/推荐分类)
│   ├── 全文检索引擎 (FTS5 维护)
│   └── SQLite 数据库 (存储文献记录、分类、全文索引)
├── 前端 (单页风格)
│   ├── 文献列表与查询界面
│   ├── 文献添加/编辑表单 (含 Agent 建议的“采纳”按钮)
│   ├── 分类管理界面
│   └── Agent 状态显示 (是否可用)
└── 本地存储
    ├── uploads/ (原始文献文件)
    └── literature.db (数据库)
```

### 核心数据库设计

```sql
-- 分类表
categories (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT
)

-- 文献主表
literatures (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,
    year INTEGER,
    journal TEXT,
    abstract TEXT,
    file_path TEXT,                -- 原始文件存储路径
    file_name TEXT,
    content_text TEXT,             -- 提取的全文纯文本 (用于检索)
    category_id INTEGER,           -- 归属分类，外键 categories(id)
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id)
)

-- FTS5 全文搜索虚拟表 (索引标题、作者、摘要、内容)
CREATE VIRTUAL TABLE literatures_fts USING fts5(
    title, authors, abstract, content_text,
    content=literatures                       -- 关联主表
);
```

### Agent 模块设计

Agent 作为独立服务类 `AgentService`，提供两个核心方法：

1. **`suggest_metadata`**
   - 输入：文献全文文本（截取前 2000 字符）、文件名
   - 输出：建议的 `title`, `authors`, `year`, `category_suggest` (推荐分类名, 可选)
   - 实现：向 Ollama 发送 prompt，要求返回 JSON 格式。若 Ollama 不可用，降级为正则 + 规则（如从第一行提取标题，文件名去扩展名等）。

2. **`summarize_abstract`** (可选扩展)
   - 输入：全文文本
   - 输出：一段摘要 (100-200字)

**Prompt 设计示例** (中文)：

```
你是一个文献元数据提取专家。根据下面文献内容，输出 JSON 格式，包含以下字段：
- title: 文献标题（字符串）
- authors: 作者列表，如果存在多个作者用“;”分隔（字符串）
- year: 发表年份（整数，若未找到则为 null）
- category_suggest: 建议的分类名称（根据内容主题，例如“机器学习”、“自然语言处理”、“量子计算”等，字符串）
只输出 JSON，不要有其他解释。

文献内容：
{truncated_text}
```

**降级规则**：

- 标题：取正文第一个全大写或符合同行长度 >10 字符且非空的行。
- 作者：查找 "Author" / "作者" 关键词后的行。
- 年份：正则匹配 19xx 或 20xx。
- 分类：基于关键词表简单匹配（可配置默认“未分类”）。

Agent 的可用性通过检测 `http://localhost:11434/api/generate` 来判断，前端展示“智能 Agent: 在线”或“降级模式”。

---

## 项目目录结构

```
literature_manager/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # 配置 (上传目录、数据库路径)
│   │   ├── database.py          # SQLAlchemy 引擎、会话
│   │   ├── models.py            # ORM 模型 (Category, Literature)
│   │   ├── schemas.py           # Pydantic 模型 (请求/响应)
│   │   ├── api/
│   │   │   ├── literatures.py   # 文献增删改查 + 上传文件
│   │   │   ├── categories.py    # 分类 CRUD
│   │   │   ├── search.py        # 查询接口
│   │   │   └── agent.py         # Agent 建议接口
│   │   ├── services/
│   │   │   ├── file_parser.py   # PDF/DOCX/TXT 解析
│   │   │   ├── agent_service.py # Ollama 调用 + 降级规则
│   │   │   └── fts_manager.py   # FTS5 同步与搜索
│   │   └── utils.py             # 辅助函数
│   ├── uploads/                 # 上传文件存放处
│   ├── requirements.txt
│   └── run.py                   # 启动脚本 (uvicorn)
├── frontend/
│   ├── index.html               # 主界面
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js               # 前端交互 (fetch API)
├── start.bat / start.sh         # 一键启动脚本 (后台启动 Ollama + uvicorn)
└── README.md
```

---

## 各阶段开发任务及 AI 编程提示词

为了利用 AI 辅助编程（如 Copilot / Cursor / Claude Engineer），将整个项目拆分为 **6 个阶段**，每个阶段包含明确的目标和可复制到 AI 对话中的提示词。开发者可将提示词发给 AI，依次完成代码生成。

### 阶段 1：项目骨架 + 数据库 + 基础文件上传

**阶段目标**

- 创建 FastAPI 应用，连接 SQLite，定义 Category 和 Literature 模型。
- 实现上传文献文件的 API（仅保存文件到磁盘，不解析内容）。
- 实现简单的分类 CRUD（增删改查）。
- 提供基础 HTML 页面（展示文献列表、上传表单）。

**提示词**

```
你是 Python 后端与 FastAPI 专家。请为本地文献管理系统搭建阶段 1 代码：

1. 创建以下文件结构：
   backend/app/{main.py, config.py, database.py, models.py, schemas.py}
   backend/app/api/{literatures.py, categories.py}
   backend/requirements.txt (fastapi, uvicorn, sqlalchemy, aiosqlite, python-multipart)

2. 实现配置：UPLOAD_DIR = "./uploads"，数据库 URL = "sqlite:///./literature.db"

3. 定义 SQLAlchemy 模型：
   - Category: id, name (unique), description
   - Literature: id, title, authors, year, journal, abstract, file_path, file_name, content_text (可为空), category_id(FK), created_at, updated_at

4. 创建数据库引擎和依赖注入 (get_db)。

5. 实现分类 API (在 categories.py)：
   - GET /categories - 查询所有分类
   - POST /categories - 新增分类 (name, description)
   - DELETE /categories/{id} - 删除分类

6. 实现文献上传 API (在 literatures.py)：
   - POST /literatures/upload - 接收 file (文件), category_id, title 等可选元数据（若无则从文件名提取 title）。保存文件到 UPLOAD_DIR，记录到数据库，content_text 暂时留空。

7. 提供一个简单的 index.html 前端（不要求好看），包含：
   - 上传表单（文件、分类下拉、标题输入）
   - 显示已有文献列表（表格）
   - 使用 fetch 调用后端 API

8. 在 main.py 中挂载路由，并配置 CORS 和静态文件服务（/static 指向 frontend 文件夹）。

请生成完整可运行的代码，并提供启动命令（uvicorn backend.app.main:app --reload）。
```

---

### 阶段 2：文件解析与文本提取

**阶段目标**

- 识别上传的 PDF / DOCX / TXT 文件，提取纯文本内容。
- 自动填充 `content_text` 字段，用于后续检索。
- 上传后立即触发解析，并更新数据库记录。

**提示词**

```
延续阶段 1 的代码，添加文件解析服务：

1. 创建 backend/app/services/file_parser.py，实现以下函数：
   - extract_text_from_pdf(file_bytes) -> str (使用 pdfplumber)
   - extract_text_from_docx(file_bytes) -> str (使用 python-docx)
   - extract_text_from_txt(file_bytes) -> str (使用 chardet 检测编码)
   - extract_text(file_path) -> str (根据扩展名调用对应函数)

2. 修改文献上传 API (POST /literatures/upload)：
   - 保存文件后，调用 extract_text 获取全文内容。
   - 将 content_text 存入数据库。
   - 如果用户未提供 title，从文件名（去掉扩展名）或从文本前 50 个字符中提取作为临时标题。

3. 增加异常处理：解析失败时 content_text 为空，记录错误日志但不中断上传。

4. 更新 requirements.txt：增加 pdfplumber, python-docx, chardet。

5. 测试：上传一个 PDF 文件，验证 content_text 字段被正确填充。

请输出完整修改的代码（主要给出 file_parser.py 和更新后的 literatures.py 上传部分）。
```

---

### 阶段 3：分类管理与文献分配

**阶段目标**

- 前端完成分类管理独立界面（增删改）。
- 文献编辑功能：允许修改文献的分类、基本信息。
- 实现文献删除和按分类筛选。

**提示词**

```
在已有代码基础上增加分类管理前端与文献编辑功能：

1. 前端 index.html 添加“管理分类”按钮，弹窗或新区域展示分类列表，支持：
   - 添加新分类（输入 name，description）
   - 删除分类（若分类下有文献，拒绝删除或提示先移动文献）
   - 修改分类名称

2. 实现文献编辑功能：
   - 每个文献行增加“编辑”按钮，点击后弹出表单，可修改：标题、作者、年份、期刊、摘要、所属分类。
   - 提供 PUT /literatures/{id} API 更新记录。
   - 添加 DELETE /literatures/{id} API 删除文献（同时删除本地文件）。

3. 前端增加分类筛选下拉框：选择分类后仅显示该分类下的文献。

4. 修改文献列表显示内容：标题、作者、年份、分类名称。

5. 确保所有 API 都使用了数据库会话关闭机制。

请生成前后端对应的代码片段（重点：categories.py 新增 PUT 和 DELETE 路由；literatures.py 的 PUT/DELETE；前端 JavaScript 函数）。
```

---

### 阶段 4：查询功能（含全文检索）

**阶段目标**

- 实现多条件搜索（标题、作者、年份范围、分类、全文内容）。
- 使用 SQLite FTS5 提升全文搜索性能。
- 前端提供搜索框和结果高亮（可选）。

**提示词**

```
在文献管理系统中集成全文检索功能：

1. 使用 SQLAlchemy 事件，当 Literature 插入或更新 content_text、title、authors、abstract 时，同步更新 FTS5 虚拟表。
   - 创建 FTS5 虚拟表 literatures_fts，包含字段：title, authors, abstract, content_text。
   - 使用 SQLAlchemy 的 after_insert 和 after_update 事件维护同步。

2. 实现搜索 API：GET /search?q=关键词&category_id=&year_start=&year_end=
   - 利用 FTS5 的 MATCH 查询进行全文搜索，同时可以叠加 category_id 和年份范围过滤。
   - 返回文献列表。

3. 前端搜索界面：
   - 搜索框（支持模糊关键词）
   - 分类下拉、年份起止输入框
   - 点击搜索后刷新文献列表。

4. 如果用户未安装 FTS5 或不支持，回退到使用 LIKE 模糊查询（在 API 中实现 fallback）。

请提供详细的代码实现，包括：数据库模型事件绑定、search.py 路由、前端搜索函数。
```

---

### 阶段 5：人工填写表单优化 + Agent 建议接入准备

**阶段目标**

- 完善文献添加/编辑表单，使其能呈现 Agent 给出的元数据建议。
- 构建 Agent 的基础服务框架（尚未对接 LLM，先用模拟数据测试）。

**提示词**

```
为 Agent 功能做前置准备：实现 Agent API 框架和前端“建议填充”按钮。

1. 创建 backend/app/services/agent_service.py，定义 AgentService 类：
   - 方法 suggest_metadata(file_path: str, text_content: str) -> dict
     (当前先返回模拟数据：{"title": "模拟标题", "authors": "模拟作者", "year": 2024, "category_suggest": "未分类"})
   - 方法 is_available() -> bool (暂时返回 True)

2. 在 backend/app/api/agent.py 中创建路由：
   - POST /agent/suggest - 接收文献 ID（或直接传 text_content），返回建议的元数据。

3. 前端修改：
   - 在添加/编辑文献的表单旁边增加“✨ Agent 建议”按钮。
   - 点击后，若当前有已上传的文件（或选中的文献），调用 /agent/suggest API，将返回的字段自动填充到表单对应输入框。
   - 用户可修改后保存。

4. 测试模拟建议流程：上传文件，点击“Agent 建议”，表单自动填充模拟数据。

请提供 agent_service.py, agent.py 路由以及前端相关 JavaScript 代码。
```

---

### 阶段 6：集成真实 LLM Agent（Ollama 本地模型）

**阶段目标**

- 安装并配置 Ollama，拉取一个小型中文模型（如 `qwen2:1.5b` 或 `llama3.2:3b`）。
- 将 AgentService 实际调用 Ollama API 提取文献元数据。
- 实现降级策略（ollama 不可用时使用规则提取 + 提示用户）。

**提示词**

```
将 Agent 升级为真实 LLM 驱动，完全本地运行：

1. 指导用户安装 Ollama（https://ollama.com）并拉取模型：
   ollama pull qwen2:1.5b

2. 修改 agent_service.py：
   - 检测 http://localhost:11434/api/generate 是否可访问。
   - 实现 _call_ollama(prompt, model="qwen2:1.5b") 方法，发送 POST 请求，流式或非流式获取响应。
   - 设计系统提示词（如前面描述的 JSON 输出约束）。
   - 解析返回的 JSON，若失败则降级到规则提取（实现 _rule_based_extract 方法）。

3. 规则提取的备用逻辑：
   - 标题：取文本第一行非空且长度小于 200 的行。
   - 作者：搜索 "作者|Author|Authors" 后的 2 行内容。
   - 年份：正则 r'\b(19|20)\d{2}\b'。
   - 分类建议：基于常见关键词映射（如 "neural network" -> "机器学习"）。

4. 在 Agent API 中增加缓存：相同文献的 text 哈希值 5 分钟内不重复调用。

5. 前端显示 Agent 状态（通过 GET /agent/status 返回可用性和加载的模型名）。

6. 提供一键启动脚本 start.sh / start.bat，依次检查 Ollama 是否运行、启动后端服务。

请给出完整的 agent_service.py（集成 Ollama 与规则降级），以及 /agent/status 接口，并更新启动脚本说明。
```

---

## 如何使用这些提示词进行 AI 编程

1. **准备开发环境**：安装 Python 3.10，创建虚拟环境，新建项目文件夹。
2. **按顺序执行阶段**：将每个阶段的提示词复制到 AI 对话中（如 ChatGPT/Claude，或 Cursor Composer），让 AI 生成对应代码。
3. **代码整合**：将生成的文件按目录结构放置，并根据 AI 的说明安装依赖。
4. **运行与调试**：执行 `uvicorn backend.app.main:app --reload`，访问 `http://localhost:8000` 查看效果。
5. **Agent 依赖**：阶段 6 需要提前安装 Ollama，并拉取模型。若用户不想用 LLM，阶段 5 的模拟 Agent 和阶段 6 的规则降级模式依然可用。

---

## 最终交付物（用户得到）

- 一个完整、可本地运行的文献管理系统源码。
- 支持 PDF/DOCX/TXT 文件上传、全文检索、分类管理、人工元数据填写。
- 具备智能 Agent（可自动提取标题/作者/年份/推荐分类），并可在没有 Ollama 时自动降级。
- 所有数据存储在项目目录内，无任何外部依赖（除了 Python 包和可选的 Ollama）。

通过上述**结构化提示词驱动**的开发方式，即可用 AI 编程工具逐步构建出符合全部需求的本地文献管理系统。
