"""
当 subtitler 中存在 __init__.py 时整个文件夹被视为包 package（包就是一个或多个 python 模块的集合）
 
将 subtitler 作为包导入 import subtitler 时仅会自动执行 __init__.py
其中 __init__.py 的 __name__ 与 __package__ 属性都是 "subtitler" 

当 subtitler 作为模块执行 python -m subtitler 时会首先执行 __init__.py 随后再执行 __main__.py
其中 __init__.py 的 __name__ 与 __package__ 属性都是 "subtitler"
"""

# 定义 import subtitler 暴露的接口
from .weight import available_models, load_model
from .audio import load_audio, log_mel_spectrogram, pad_or_trim
from .decoding import DecodingOptions, DecodingResult, decode, detect_language
from .model import Whisper, ModelDimensions
from .app import generate_subtitle, extract_audio, get_avpath
