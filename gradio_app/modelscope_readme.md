---
# 详细文档见https://modelscope.cn/docs/%E5%88%9B%E7%A9%BA%E9%97%B4%E5%8D%A1%E7%89%87
domain: #领域：cv/nlp/audio/multi-modal/AutoML
  - multi-modal
tags: #自定义标签
  - audio
  - tts
  - text-to-speech
datasets: #关联数据集
  evaluation:
  #- iic/ICDAR13_HCTR_Dataset
  test:
  #- iic/MTWI
  train:
  #- iic/SIBR
models: #关联模型
  - inclusionAI/Ming-omni-tts-16.8B-A3B
  - inclusionAI/Ming-omni-tts-0.5B
  - inclusionAI/Ming-omni-tts-tokenizer-12Hz
 
## 启动文件(若SDK为Gradio/Streamlit，默认为app.py, 若为Static HTML, 默认为index.html)
deployspec:
  entry_file: app.py
license: Apache License 2.0
---

# Ming UniAudio Demo

Ling LLM 系列 Ming-omni-tts 音频模型的演示应用。

这是一个基于 Gradio 的 Ming UniAudio 模型演示应用。

## 相关模型 / Related Models

### ModelScope Models
- [Ming-omni-tts-16.8B-A3B](https://modelscope.cn/models/inclusionAI/Ming-omni-tts-16.8B-A3B)
- [Ming-omni-tts-0.5B](https://modelscope.cn/models/inclusionAI/Ming-omni-tts-0.5B)
- [Ming-omni-tts-tokenizer-12Hz](https://modelscope.cn/models/inclusionAI/Ming-omni-tts-tokenizer-12Hz)

### HuggingFace Models
- [Ming-flash-omni-2.0](https://huggingface.co/inclusionAI/Ming-flash-omni-2.0)
- [Ming-omni-tts-16.8B-A3B](https://huggingface.co/inclusionAI/Ming-omni-tts-16.8B-A3B)
- [Ming-omni-tts-0.5B](https://huggingface.co/inclusionAI/Ming-omni-tts-0.5B)
- [Ming-omni-tts-tokenizer-12Hz](https://huggingface.co/inclusionAI/Ming-omni-tts-tokenizer-12Hz)