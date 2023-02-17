"""
当 go_subtitle 中存在 __init__.py 时整个文件夹被视为包 package

当 go_subtitle 作为模块执行 import go_subtitle 时仅会自动执行 __init__.py
其中 __init__.py 的 __name__ 与 __package__ 属性都是 "go_subtitle" 

当 go_subtitle 作为模块执行 python -m go_subtitle 时会首先执行 __init__.py 随后再执行 __main__.py
其中 __init__.py 的 __name__ 与 __package__ 属性都是 "go_subtitle"
"""

__version__ = "0.0.1"

# 定义 import go_subtitle 暴露的接口
from .weight import available_models, load_model
from .audio import load_audio, log_mel_spectrogram, pad_or_trim
from .decoding import DecodingOptions, DecodingResult, decode, detect_language
from .model import Whisper, ModelDimensions
from .shell import generate_subtitle, extract_audio, get_avpath
