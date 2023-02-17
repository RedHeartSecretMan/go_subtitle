"""
当 go_subtitle 中存在 __main__.py 时整个文件夹是可执行文件夹即模块 module

当 go_subtitle 作为模块执行 python -m go_subtitle 时会在执行 __init__.py 后继续执行 __main__.py
其中 __main__.py 的 __name__ 属性是 "__main__" 而 __package__ 属性是 "go_subtitle"

当 go_subtitle 作为文件执行 python go_subtitle 时仅会自动执行 __main__.py
其中 __main__.py 的 __name__ 属性是 "__main__" 而 __package__ 属性是 "" 空字符串
"""

from .shell import main


main()
