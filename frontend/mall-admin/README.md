# 智能百货平台管理后台

基于 Vue 3 + Element Plus 的管理后台系统

## 技术栈

- Vue 3.4
- Vue Router 4.2
- Pinia 2.1
- Element Plus 2.5
- Axios 1.6
- Vite 5.0

## 功能模块

- ✅ 用户登录/登出
- ✅ 用户管理
- ✅ 商品管理
- ✅ 优惠券管理
- ✅ 订单管理
- ✅ 数据统计

## 快速开始

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

## 项目结构

```
mall-admin/
├── src/
│   ├── api/              # API接口
│   ├── components/       # 公共组件
│   ├── layout/           # 布局组件
│   ├── router/           # 路由配置
│   ├── views/            # 页面组件
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── index.html            # HTML模板
├── vite.config.js        # Vite配置
└── package.json          # 项目配置
```

## 默认账号

- 用户名: admin
- 密码: 123456

## 注意事项

1. 确保后端服务已启动
2. 后端API地址默认为 http://localhost:8080
3. 需要在后端配置跨域支持
