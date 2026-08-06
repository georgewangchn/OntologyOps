# 贡献指南

感谢您考虑为 OntologyOps 做出贡献！

## 提交贡献前

### 1. 阅读 CLA

请先阅读 [CLA.md](CLA.md)。当您提交 Pull Request 时，即表示您同意 CLA 的全部条款。

> CLA 是保护项目出版链路的关键：它确保作者可以将社区贡献纳入商业出版书，而不会被 CC BY-NC-SA 4.0 的 SA 条款锁定。

### 2. 确认贡献类型

| 贡献类型 | 文件范围 | 适用协议 | 注意事项 |
|---------|---------|---------|---------|
| 代码贡献 | `labs/*.py`, `astro/src/pages/`, `astro/src/components/` | MIT | 确保不引入与 MIT 不兼容的依赖 |
| 内容贡献 | `astro/src/content/blog/*.mdx` | CC BY-NC-SA 4.0 | 通过 CLA 授权商用再许可 |
| 协议贡献 | `ontologyops/` | CC BY 4.0 | 协议变更需充分讨论 |

### 3. 代码风格

- Python：遵循 PEP 8，使用中文类名/变量名时确保 UTF-8 编码
- Markdown：使用 ATX 标题（`#`），代码块标注语言
- 提交信息：简洁描述修改内容，关联相关 Issue

## 提交流程

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/your-feature`
3. 提交修改：`git commit -m "feat: 添加 XXX 功能"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建 Pull Request，描述修改内容和动机

## 行为准则

- 尊重所有参与者
- 聚焦技术讨论，避免人身攻击
- 欢迎不同水平的贡献者
- 提供建设性反馈
