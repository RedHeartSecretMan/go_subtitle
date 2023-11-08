"""
当 subtitler 中存在 __main__.py 时整个文件夹是 python 可执行文件即模块 module（最小的模块就是一个单独的 python 文件）

1. python -m <module_or_package> 的形式执行命令
将 subtitler 作为模块执行 python -m subtitler 时会在执行 __init__.py 后继续执行 __main__.py
其中 __main__.py 的 __name__ 属性是 "__main__" 而 __package__ 属性是 "subtitler"

2. python <filename_or_dirname> 的形式执行命令
将 subtitler 作为文件执行 python subtitler 时仅会自动执行 __main__.py
其中 __main__.py 的 __name__ 属性是 "__main__" 而 __package__ 属性是 "" 空字符串
"""

from .app import main


if __name__ == "__main__":
    main()
