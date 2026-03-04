# 文档开发指南

## GitHub 文档使用方式

### GitHub 平台内容
- **GitHub Wiki**
  - 简单、免费
  - 适合小型项目文档
  - 支持 Markdown

- **GitHub Pages**
  - 支持 Jekyll/Markdown
  - 可自定义域名
  - 适合静态网站文档

- **Docsify/MDX**
  - 轻量级文档站点生成器
  - 官方推荐

### 个人开发者推荐平台

- **Vercel/Netlify**
  - 免费托管
  - 支持自定义域名
  - 适合静态网站

- **GitBook**
  - 专业文档平台
  - 免费版平均个人使用
  - 完整的文档管理功能

- **Notion**
  - 快速搭建
  - 不需代码
  - 适合快速创建文档

- **Sphinx**
  - Python 项目专用
  - 生成精美文档
  - 适合技术项目

### 选择建议
- 简单需求：GitHub Wiki
- 专业文档：GitBook
- 快速搭建：Notion
- 自定义需求：Vercel + Docsify

---

## GitHub Actions 自动发布目标

### 代码存储平台
- GitHub Pages
- GitLab Pages
- Bitbucket

### 云服务
- **AWS**
  - S3
  - Lambda
  - EC2

- **Google Cloud**
  - Cloud Run
  - Cloud Functions

- **Azure**
  - Blob Storage
  - Functions

- **Vercel**
- **Netlify**
- **Heroku**

### 容器平台
- Docker Hub
- AWS ECR
- Google Container Registry
- Azure Container Registry

### 应用商店
- npm (Node.js)
- PyPI (Python)
- RubyGems
- Maven Central
- Homebrew

### CI/CD 平台
- Jenkins
- CircleCI
- Travis CI

### 其他部署
- FTP/SFTP 服务器
- API 部署
- 自定义脚本部署

### 选择建议
根据项目类型选择合适的部署目标，考虑性能、安全性和维护性。