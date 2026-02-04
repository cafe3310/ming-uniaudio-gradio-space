# 项目待办事项 (TODO)

## 当前迭代：UniAudio V4 MOE 接入

### 文档与规范
- [x] 同步项目管理与文档命名规范 (`GEMINI.md`) @2026-02-04
- [x] 整理并重命名历史文档 (`doc/`) @2026-02-04
- [x] 归档旧版 Gradio Demo 代码 @2026-02-04
- [x] 编写 Gradio Demo 代码结构与功能分析文档 @2026-02-04
- [x] 编写 UniAudio V4 MOE 接口对接方案文档 @2026-02-04

### 代码开发 (Gradio App)
- [x] **实现模块化 Demo Tab (`tab_uniaudio_demo.py`)** @2026-02-04
- [x] **集成到主应用 (`app.py`)** @2026-02-04
- [ ] **接入音频代理下载**:
    - [ ] 修改 `tab_uniaudio_demo.py` 中的下载逻辑。
    - [ ] 不再直接 `requests.get` OSS URL。
    - [ ] 解析 OSS URL 参数，调用后端新增的 `get_audio` 代理接口。
- [ ] **迁移静态数据**:
    - [ ] 将 `DROPDOWN_CHOICES` 和 `IP_DICT` 提取为独立配置文件或常量模块。
- [ ] **UI 适配**:
    - [ ] 更新 `app.py` 的事件处理函数，对接新的 `UniAudioV4Client`。
    - [ ] 移除旧的 `Pai-Plus` 相关代码和环境变量。
- [ ] **环境配置**:
    - [ ] 更新 `.env.example`，添加 `API_KEY`, `WEBGW_URL`, `APP_ID` 等配置项。

### 测试与发布
- [ ] **联调测试**:
    - [ ] 针对预发环境 (Pre) 进行 6 个功能 Tab 的冒烟测试。
    - [ ] 验证长音频生成的轮询超时机制。
- [ ] **ModelScope 部署**:
    - [ ] 验证 `deploy-folder-to-modelscope` 技能的有效性。
    - [ ] 更新 ModelScope 上的 `app.py` 和依赖。

---

## 历史归档

### 新语音模型 Demo 整合 (Legacy)
- [x] 分析 `inbox` 中的代码块 (001-005)，理解依赖关系和 UI 逻辑。
- [x] 创建独立的标签页模块 `gradio_app/tab_audio_instruct.py`。
- [x] 在 `gradio_app/app.py` 中引入并整合 `AudioInstructTab` 作为第二个标签页。
- [x] 扩展 `SpeechService` 以支持可控 TTS 的新参数 (`caption`, `seed` 等)。
- [x] 完善 `AudioInstructTab` 中的示例数据 (Examples)。
- [x] 验证功能 (需用户协助测试)。