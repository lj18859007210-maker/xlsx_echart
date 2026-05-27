# Frontend

`frontend/` 是 `xlsx_echart` 的前端工程目录，当前使用 `React + Vite + TypeScript`。

## 当前内容

- `src/main.tsx`：前端入口
- `src/App.tsx`：应用根组件
- `src/pages/HomePage.tsx`：初始化首页
- `src/modules/`：按功能拆分的模块目录
- `tests/`：前端测试预留目录

## 环境要求

- Node.js `24+`
- npm `11+`

## 安装依赖

在 `frontend/` 目录执行：

```powershell
npm install
```

## 启动开发服务

在 `frontend/` 目录执行：

```powershell
npm run dev
```

默认地址：

- `http://localhost:5173`

## 常用命令

```powershell
npm run lint
npm run build
npm run preview
```

## 配置说明

- 环境变量示例：`../.env.example`
- 前端 API 地址变量：`VITE_API_BASE_URL`
- 构建工具配置：`vite.config.ts`
- 代码检查配置：`eslint.config.js`

## 当前阶段

当前只完成了工程初始化和基础页面，后续会在这里继续补上传页、Gate 1 结构确认页、结果页和图表面板。
