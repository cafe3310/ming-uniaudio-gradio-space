---
title: Ming-omni-tts Gradio Demo
emoji: 🎵
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.1
app_file: gradio_app/app.py
pinned: false
models:
  - inclusionAI/Ming-flash-omni-2.0
  - inclusionAI/Ming-omni-tts-16.8B-A3B
  - inclusionAI/Ming-omni-tts-0.5B
  - inclusionAI/Ming-omni-tts-tokenizer-12Hz
---

# Ming-omni-tts Gradio Demo

Ling LLM 系列 Ming-omni-tts 音频模型的演示应用。

[Ming-v2 模型系列](https://huggingface.co/collections/inclusionAI/ming-v2)

## 相关模型 / Related Models

### HuggingFace Models
- [Ming-flash-omni-2.0](https://huggingface.co/inclusionAI/Ming-flash-omni-2.0)
- [Ming-omni-tts-16.8B-A3B](https://huggingface.co/inclusionAI/Ming-omni-tts-16.8B-A3B)
- [Ming-omni-tts-0.5B](https://huggingface.co/inclusionAI/Ming-omni-tts-0.5B)
- [Ming-omni-tts-tokenizer-12Hz](https://huggingface.co/inclusionAI/Ming-omni-tts-tokenizer-12Hz)

### ModelScope Models
- [Ming-omni-tts-16.8B-A3B](https://modelscope.cn/models/inclusionAI/Ming-omni-tts-16.8B-A3B)
- [Ming-omni-tts-0.5B](https://modelscope.cn/models/inclusionAI/Ming-omni-tts-0.5B)
- [Ming-omni-tts-tokenizer-12Hz](https://modelscope.cn/models/inclusionAI/Ming-omni-tts-tokenizer-12Hz)

## tips

1. 备忘录 `doc` submodule 指向内部 doc 仓库。`AGENTS.md` 也在此仓库中。
2. Push to GitHub `main` 后，Workflow 会将应用同步到 HuggingFace Space 和 ModelScope Space。
3. 使用仓库时，最好用多次 `git remote set-url --add --push origin <remote>` 的方式，给 origin 这个 remote 设置多个 push url。可以一次 push 到多个远端 repo 的。
