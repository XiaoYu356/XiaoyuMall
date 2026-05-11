# 智能百货平台

基于Spring Cloud Alibaba的智能百货平台微服务架构,集成商品管理、优惠券系统、订单交易等核心功能,预留AI智能服务接口。

## 📋 项目介绍

智能百货平台是一个基于微服务架构的电商系统,采用Spring Cloud Alibaba技术栈,实现了商品管理、优惠券系统、订单交易等核心电商功能,并预留了AI智能服务接口,支持后续集成智能客服、智能推荐等AI能力。

## 🏗️ 技术架构

### 后端技术栈

| 技术 | 版本 | 说明 |
|-----|------|------|
| Spring Boot | 3.2.2 | 应用开发框架 |
| Spring Cloud | 2023.0.0 | 微服务框架 |
| Spring Cloud Alibaba | 2023.0.0-RC1 | 微服务组件 |
| Sa-Token | 1.37.0 | 权限认证框架 |
| Nacos | 2.3.0 | 服务注册与配置中心 |
| MySQL | 8.0 | 关系型数据库 |
| Redis | 7.2 | 分布式缓存 |
| MyBatis-Plus | 3.5.5 | ORM框架 |
| MinIO | RELEASE.2024-01 | 对象存储 |
| RocketMQ | 5.1.0 | 消息队列 |

### 前端技术栈

| 技术 | 版本 | 说明 |
|-----|------|------|
| Vue | 3.4.0 | 渐进式JavaScript框架 |
| Vue Router | 4.2.5 | 官方路由管理器 |
| Pinia | 2.1.7 | 新一代状态管理工具 |
| Element Plus | 2.5.0 | Vue 3组件库 |
| Axios | 1.6.5 | HTTP客户端 |
| Vite | 5.0.10 | 下一代前端构建工具 |

### 项目结构

```
smart-mall
├── backend/                    # 后端代码
│   ├── mall-common/           # 公共模块
│   ├── mall-gateway/          # 网关服务
│   ├── user-service/          # 用户服务
│   ├── product-service/       # 商品服务
│   ├── coupon-service/        # 优惠券服务
│   ├── order-service/         # 订单服务
│   ├── sql/                   # 数据库脚本
│   ├── docker-compose.yaml    # Docker编排配置
│   └── pom.xml                # Maven父项目配置
├── frontend/                   # 前端代码
│   └── mall-admin/            # 管理后台
│       ├── src/               # 源代码
│       ├── package.json       # NPM配置
│       └── vite.config.js     # Vite配置
├── 智能百货平台架构设计.md      # 架构设计文档
├── 权限管理实现说明.md          # 权限管理文档
└── README.md                   # 项目说明
```

## 🚀 快速开始

### 环境要求

**后端环境**:
- JDK 17+
- Maven 3.6+
- MySQL 8.0+
- Redis 7.0+
- Nacos 2.3.0+
- MinIO (可选)

**前端环境**:
- Node.js 18+
- npm 9+

### 后端启动步骤

1. **进入后端目录**
```bash
cd backend
```

2. **启动基础设施**
```bash
docker-compose up -d
```

3. **初始化数据库**
```bash
# 执行数据库初始化脚本
mysql -uroot -proot < sql/init.sql
mysql -uroot -proot < sql/permission.sql
```

4. **编译项目**
```bash
mvn clean install
```

5. **启动服务**

按以下顺序启动:
```bash
# 1. 启动网关服务
cd mall-gateway
mvn spring-boot:run

# 2. 启动用户服务
cd ../user-service
mvn spring-boot:run

# 3. 启动商品服务
cd ../product-service
mvn spring-boot:run

# 4. 启动优惠券服务
cd ../coupon-service
mvn spring-boot:run

# 5. 启动订单服务
cd ../order-service
mvn spring-boot:run
```

### 前端启动步骤

1. **进入前端目录**
```bash
cd frontend/mall-admin
```

2. **安装依赖**
```bash
npm install
```

3. **启动开发服务器**
```bash
npm run dev
```

4. **访问应用**
```
打开浏览器访问: http://localhost:3000
默认账号: admin / 123456
```

## 📖 API文档

启动服务后,访问以下地址查看API文档:

- **网关聚合文档**: http://localhost:8080/doc.html
- **用户服务**: http://localhost:8081/doc.html
- **商品服务**: http://localhost:8082/doc.html
- **优惠券服务**: http://localhost:8083/doc.html
- **订单服务**: http://localhost:8084/doc.html

## 🔧 配置说明

### Nacos配置

配置文件位于各服务的 `application.yaml` 中,主要配置项:

```yaml
spring:
  cloud:
    nacos:
      discovery:
        server-addr: localhost:8848
      config:
        server-addr: localhost:8848
        file-extension: yaml
```

### MinIO配置

```yaml
minio:
  endpoint: http://localhost:9000
  access-key: admin
  secret-key: admin123456
  bucket-name: mall-products
```

## 📦 服务端口

| 服务 | 端口 | 说明 |
|-----|------|------|
| mall-gateway | 8080 | API网关 |
| user-service | 8081 | 用户服务 |
| product-service | 8082 | 商品服务 |
| coupon-service | 8083 | 优惠券服务 |
| order-service | 8084 | 订单服务 |

## 🎯 功能特性

### 已实现功能

- ✅ 用户注册登录
- ✅ 商品管理
- ✅ 商品分类
- ✅ 库存管理
- ✅ 优惠券发放与核销
- ✅ 订单创建与支付
- ✅ 文件上传(MinIO)
- ✅ API网关路由

### 预留功能(AI集成)

- 🔜 智能客服
- 🔜 智能推荐
- 🔜 智能搜索
- 🔜 RAG检索增强

## 📝 开发指南

### 代码规范

- 遵循阿里巴巴Java开发规范
- 使用Lombok简化代码
- 统一异常处理
- 统一返回结果格式

### 分支管理

- `master`: 主分支,稳定版本
- `develop`: 开发分支
- `feature/*`: 功能分支
- `hotfix/*`: 热修复分支

## 📄 许可证

本项目采用 Apache License 2.0 许可证

## 👥 联系方式

如有问题或建议,请提交Issue或Pull Request
