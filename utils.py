import os
import sys

def get_resource_path(relative_path):
    """兼容 开发环境 / PyInstaller打包后 的资源路径"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后临时解压目录
        base_path = sys._MEIPASS
    else:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
