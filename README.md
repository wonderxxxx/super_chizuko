# Super Chizuko|超级智子 项目

这是超级智子，一个从奇点Chat项目发展而来的山寨版本。它具有情感状态管理和记忆功能，能够理解用户情感并提供个性化的回答。

## 项目结构

```
super_chizuko/
├── backend/           # 后端代码
│   ├── ai_manager.py  # AI管理器
│   ├── app.py         # Flask应用入口
│   ├── chat_service.py # 聊天服务
│   ├── chroma_db/     # Chroma向量数据库（会被忽略）
│   ├── config.py      # 配置文件
│   ├── data.db        # SQLite数据库（会被忽略）
│   ├── database.py    # 数据库操作
│   ├── download_model.py # 模型下载脚本
│   ├── emotion_state_serv/ # 情感状态服务
│   ├── init_data.py   # 数据初始化脚本
│   ├── memory_manager.py # 记忆管理器
│   ├── models/        # 模型文件目录（会被忽略）
│   └── prompt_generator.py # 提示生成器
├── frontend/          # 前端代码
│   ├── css/           # CSS样式
│   ├── index.html     # HTML页面
│   └── js/            # JavaScript代码
└── .gitignore         # Git忽略配置
```

## 环境准备

1. 安装Python 3.8+和pip
2. 克隆仓库后进入项目目录
3. 安装依赖：

```bash
cd backend
pip install -r requirements.txt
```

## 模型下载

项目使用的语言模型需要从ModelScope下载。运行以下脚本：

```bash
cd backend
python download_model.py
```

您可以通过参数指定其他模型：

```bash
python download_model.py --model-name "Xorbits/bge-small-zh-v1.5" --save-dir ./models
```

## 数据初始化

在首次运行或在新机器上部署时，需要初始化数据库和向量数据库：

```bash
cd backend
python init_data.py
```

## 运行应用

```bash
cd backend
python app.py
```

应用将在 `http://localhost:9602` 启动。

## Git配置

### .gitignore文件

项目已配置.gitignore文件，忽略以下内容：

- Python编译缓存文件
- IDE配置文件
- 模型文件目录 `backend/models/`
- Chroma数据库目录 `backend/chroma_db/`
- SQLite数据库文件 `backend/data.db`
- 环境文件
- 日志文件

### 部署新机器流程

1. 克隆仓库：`git clone <仓库地址>`
2. 安装依赖：`pip install -r backend/requirements.txt`
3. 下载模型：`python backend/download_model.py`
4. 初始化数据：`python backend/init_data.py`
5. 运行应用：`python backend/app.py`

## 配置说明

主要配置文件为 `backend/config.py`，包含以下配置项：

- Ollama模型配置
- 记忆配置
- Flask应用配置
- 模型配置
- 情感状态机配置
- 数据库配置
- Chroma配置

## 开发说明

1. 请勿将大模型文件、数据库文件提交到Git仓库
2. 使用 `download_model.py` 下载模型
3. 使用 `init_data.py` 初始化数据
4. 遵循PEP 8编码规范

## 许可证

MIT