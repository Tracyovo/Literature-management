# Literature Manager

Local-first literature manager with a FastAPI backend and a lightweight HTML/JS frontend.

## 产品功能

- 本地文件存储与上传（PDF/DOCX/TXT），自动抽取文本。
- 文献元数据管理（标题、作者、年份、期刊、摘要、引用）。
- 分类管理、列表浏览、分页与排序。
- 关键词检索与全文检索（SQLite FTS5 + 降级 like）。
- 导入/导出（CSV、BibTeX）。
- Agent 辅助建议（接入外部 API，失败自动规则降级）。

### Agent API 接入说明

环境变量配置：

- AI_PROVIDER=api (等价于 custom)
- AI_CUSTOM_ENDPOINT=https://your-host/your-endpoint
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

## 开发进度

- 已完成：文献 CRUD、上传与解析、分类管理、全文检索、导入/导出、Agent API 接入与规则降级、Storage Root 配置。
- 已完成：前端编辑页显示 Agent 模式与模型名（/agent/status）。
- 已完成：前端搜索结果渲染与后端返回结构对齐。
- 已完成：后端标题校验、上传路径安全校验、导入结果统计与错误输出。
- 运行方式：进入 Backend 安装依赖后，使用 `python run.py` 或 `start.bat` 启动服务。

## 桌面版（独立窗口，解压即用）

使用 Electron 将前端打包为桌面窗口，并内置后端 exe：

```powershell
cd DesktopApp
npm install
npm run dist
```

产物在 `DesktopApp\dist`（zip 解压即用）。

## 桌面一键打包脚本

在支持 Bash 的环境（如 Git Bash）执行：

```bash
./scripts/build_fullstack.sh
```

或使用 PowerShell：

```powershell
scripts\build_fullstack.ps1
```

输出：

- `DesktopApp/dist`（桌面 zip 包）
