# 元信息

-   **项目名称**: Ming-UniAudio Gradio Demo
-   **项目描述**: 本项目是 Ming LLM 系列 UniAudio 音频模型的 Gradio-based 演示应用。

# 项目结构

-   **版本控制**: Git
-   **文档结构**: 本文档 (`GEMINI.md`) 是项目的核心章程，定义了目标、范围和协作流程。

# 技能 / Skills

**本项目的项目管理工作流，使用 `doc-todo-log-loop` 全局技能来管理。**

- 日志文档使用 `YYYY-MM-DD-hh-mm-开发日志.md` 作为文件名。
- 其余文档用 `YYYY-MM-DD-hh-mm-$文档标题.md` 作为文件名。$文档标题 部分用中文。

可以使用该 Skill 来管理项目的 TODO 列表、工作日志和迭代计划。

- 本项目使用 `deploy-folder-to-modelscope` 技能进行 ModelScope 部署。

# 核心应用与文档

-   `gradio_app/`: 核心 Gradio 应用目录，包含 `app.py` 和 `requirements.txt`。这是部署到 ModelScope 的主要内容。
-   `doc/`: 项目相关文档。
-   `doc/2026-01-13-22-00-ModelScope与AECS部署指南.md`: 应用的详细部署指南，包含 ModelScope 和内部云两种方案。
-   `GEMINI.md`: 项目章程和核心信息。

# 协作流程和规范

-   **环境规范**: 项目开发应在 `virtualenv` 创建的独立 Python 虚拟环境中进行。
-   **开发流程**: 我们将遵循上述【核心任务】中定义的三个主要步骤进行迭代开发。
-   **代码风格**: 遵循项目现有代码风格。在进行大规模重构时，我们将统一采用 `ruff` 进行格式化和 linting。
-   **分支与提交**:
    -   `main` 分支为稳定分支。
    -   所有新功能或修复应在单独的 `feature/...` 或 `fix/...` 分支中进行。
    -   提交信息应清晰、简洁，描述本次提交的主要目的。
-   **测试**: 在重构和开发过程中，将通过手动测试确保 Gradio 应用的核心功能（音频输入、API 调用、结果展示）正常。
-   **ModelScope 部署**: 如果需要部署项目特定目录到 ModelScope 平台，请使用 `deploy-folder-to-modelscope` 技能。该技能将引导您完成部署流程，包括管理 ModelScope URL 和部署目录。
