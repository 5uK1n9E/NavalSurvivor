"""
海上军舰 - Naval Survivor
吸血鬼幸存者风格的2D海上军舰生存游戏
入口文件：禁用中文输入法、初始化 pygame、启动游戏主循环。
"""
import os
import sys
# 禁用中文输入法（IME），防止 WASD 等按键被输入法拦截
os.environ['SDL_IM_MODULE'] = 'none'
import pygame
pygame.init()
pygame.mixer.init()
from game import run
run()
