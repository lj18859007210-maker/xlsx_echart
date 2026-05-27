# Backend

`backend/` 是 `xlsx_echart` 的后端服务目录，当前使用 `FastAPI` 作为 Web 框架。

## 当前内容

- `app/main.py`：FastAPI 应用入口
- `app/core/config.py`：环境变量和默认配置
- `app/api/`：基础路由骨架
- `tests/`：后端测试目录

## 环境要求

- Python `3.11+`

## 安装依赖

在仓库根目录执行：

```powershell
python -m pip install -e ./backend[dev]
```

## 启动开发服务

在仓库根目录执行：

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- 健康检查：`http://localhost:8000/health`
- API 前缀：`http://localhost:8000/api`

## 运行测试

在仓库根目录执行：

```powershell
python -m pytest backend/tests -q
```

## 运行迁移

在 `backend/` 目录执行：

```powershell
python -m alembic upgrade head
```

## 配置说明

- 环境变量示例：`../.env.example`
- 实际配置读取：`app/core/config.py`
- 默认数据库：`SQLite`
- 默认上传目录：仓库根目录下的 `uploads/`

## 当前阶段

当前还是项目初始化阶段，路由和目录已建好，但业务接口、数据库模型和迁移还没有开始实现。
