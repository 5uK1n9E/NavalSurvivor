"""
海上军舰 - 资源加载与预处理
所有贴图/音效在 pygame.init() 之后调用 prepare() 加载。
本模块负责从 resource/ 目录读取资源并预缩放，避免游戏循环中重复 I/O。
"""
import os
import pygame
import constants as C
from utils import get_resource_path

_ASSET_DIR = get_resource_path('resource')

# ─── 贴图变量（延迟初始化） ─────────────────────────────
PLAYER_IMG        = None
ENEMY_IMG_SMALL   = None
ENEMY_IMG_MED     = None
ENEMY_IMG_LARGE   = None
BACKGROUND_IMG    = None   # 游戏背景（全屏静态）

# ─── 道具贴图（延迟初始化） ─────────────────────────────
DROP_IMG_FUEL     = None   # 燃料道具贴图
DROP_IMG_RECOVER  = None   # 回血道具贴图
DROP_IMG_STRENGTHEN = None  # 强化道具贴图
DROP_IMG_SHIELD   = None   # 护盾道具贴图
DROP_IMG_FIRE_RATE = None  # 射速提升道具贴图
DROP_IMG_JAMMING  = None   # 信号干扰道具贴图

# ─── 剧情贴图（延迟初始化） ─────────────────────────────
PLOT_CG    = [None] * 4  # cg1~cg4，对应四幕剧情
PLOT_ENDING = None       # 结局 CG
PLOT_WIN    = None       # 胜利 CG

# ─── 音效变量（延迟初始化） ─────────────────────────────
SOUND_HIT  = None  # 玩家受击金属音效
SOUND_BOOM = None  # 敌舰爆炸音效
SOUND_MISSILE = None  # 导弹爆炸音效


# ─── 工具函数 ───────────────────────────────────────────
def _load_img(name):
    """加载贴图，失败返回 None"""
    try:
        img = pygame.image.load(os.path.join(_ASSET_DIR, name)).convert_alpha()
        return img
    except Exception:
        return None

def _rotate90_ccw(img):
    """逆时针旋转 90°（舰首朝上 → 舰首朝右），与鼠标角度坐标系对齐"""
    return pygame.transform.rotate(img, 90)

def _scale_to(img, target_size):
    """缩放到目标尺寸，保持长宽比；接近 1:1 时跳过缩放以节省开销"""
    iw, ih = img.get_width(), img.get_height()
    scale = target_size / max(iw, ih)
    if 0.99 <= scale <= 1.01:
        return img
    return pygame.transform.smoothscale(img, (int(iw * scale), int(ih * scale)))


# ─── 加载入口 ───────────────────────────────────────────
def prepare(muted=False):
    """
    在 pygame.init() 之后调用一次，加载并预处理所有贴图/音效。
    每次重新开始游戏都会重新调用此函数（应对资源未就绪的情况）。
    将图片缩放到合适的游戏尺寸，背景图缩放到全屏。
    muted：是否静音，静音时所有音效加载后音量设为0。
    """
    global PLAYER_IMG, ENEMY_IMG_SMALL, ENEMY_IMG_MED, ENEMY_IMG_LARGE, BACKGROUND_IMG
    global DROP_IMG_FUEL, DROP_IMG_RECOVER, DROP_IMG_STRENGTHEN
    global DROP_IMG_SHIELD, DROP_IMG_FIRE_RATE, DROP_IMG_JAMMING
    global PLOT_CG, PLOT_ENDING, PLOT_WIN
    global SOUND_HIT, SOUND_BOOM, SOUND_MISSILE

    PLAYER_IMG        = _scale_to(_rotate90_ccw(_load_img('player.png')),   C.PLAYER_SIZE)
    ENEMY_IMG_SMALL   = _scale_to(_rotate90_ccw(_load_img('enemy1.png')), 85)   # scout - 轻型驱逐舰
    ENEMY_IMG_MED     = _scale_to(_rotate90_ccw(_load_img('enemy2.png')), 110)  # cruiser - 巡洋舰
    ENEMY_IMG_LARGE   = _scale_to(_rotate90_ccw(_load_img('enemy3.png')), 145) # battleship - 战列舰
    # 背景图缩放到全屏尺寸
    bg = _load_img('background.png')
    BACKGROUND_IMG = pygame.transform.smoothscale(bg, (C.W, C.H)) if bg else None

    # 加载道具贴图（缩放到合适尺寸）
    DROP_IMG_FUEL     = _scale_to(_load_img('fuel.png'), 24)
    DROP_IMG_RECOVER  = _scale_to(_load_img('recover.png'), 24)
    DROP_IMG_STRENGTHEN = _scale_to(_load_img('strengthen.png'), 24)
    DROP_IMG_SHIELD   = _scale_to(_load_img('shield.png'), 24)
    DROP_IMG_FIRE_RATE = _scale_to(_load_img('firingRate.png'), 24)
    DROP_IMG_JAMMING  = _scale_to(_load_img('slow.png'), 24)

    # 加载剧情 CG（缩放到全屏）
    import os as _os
    plot_dir = _os.path.join(_ASSET_DIR, 'plot')
    for i in range(4):
        try:
            PLOT_CG[i] = pygame.transform.smoothscale(
                pygame.image.load(_os.path.join(plot_dir, f'cg{i+1}.png')).convert_alpha(),
                (C.W, C.H))
        except Exception:
            PLOT_CG[i] = None
    try:
        PLOT_ENDING = pygame.transform.smoothscale(
            pygame.image.load(_os.path.join(plot_dir, 'ending.png')).convert_alpha(),
            (C.W, C.H))
    except Exception:
        PLOT_ENDING = None
    try:
        PLOT_WIN = pygame.transform.smoothscale(
            pygame.image.load(_os.path.join(plot_dir, 'win.png')).convert_alpha(),
            (C.W, C.H))
    except Exception:
        PLOT_WIN = None
    SOUND_HIT  = _load_sound('sounds/hit.mp3')
    SOUND_BOOM = _load_sound('sounds/destroy.mp3')
    SOUND_MISSILE = _load_sound('sounds/missile.mp3')  # 可能不存在，返回 None
    # 若当前静音，刚加载的音效也设为静音
    if muted:
        for s in (SOUND_HIT, SOUND_BOOM, SOUND_MISSILE):
            if s: s.set_volume(0)


def _load_sound(name):
    """加载音效文件，失败返回 None"""
    try:
        return pygame.mixer.Sound(os.path.join(_ASSET_DIR, name))
    except Exception:
        return None
