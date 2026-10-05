"""
海上军舰 - 常量与配置
集中管理所有游戏参数、颜色、按钮配置和工具函数。
其他模块通过 import constants as C 使用。
"""

# ─── 屏幕 ───────────────────────────────────────────────
W          = 1200
H          = 800
FPS        = 60

# ─── 颜色 ───────────────────────────────────────────────
C_SEA       = (8, 35, 75)
C_WAVE      = (18, 65, 115)
C_PLAYER    = (70, 90, 110)
C_PLAYER_D  = (155, 55, 55)
C_FUEL      = (240, 200, 40)
C_REPAIR    = (40, 215, 90)
C_UPGRADE   = (200, 75, 240)
C_SHIELD    = (60, 140, 255)     # 护盾道具颜色（蓝色）
C_FIRE_RATE = (255, 220, 50)     # 射速提升道具颜色（金黄色）
C_JAMMING   = (60, 180, 255)     # 信号干扰道具颜色（青色）
C_BULLET    = (255, 240, 70)
C_ENEMY_B   = (255, 90, 90)
C_WHITE     = (255, 255, 255)
C_DIM       = (150, 150, 150)
C_DARK      = (15, 28, 50)

# ─── 按钮颜色（深海军装风） ──────────────────────────────
BTN_START   = (25, 65, 90)
BTN_START_H = (35, 90, 120)
BTN_EXIT    = (55, 35, 35)
BTN_EXIT_H  = (80, 45, 45)
BTN_MUNE    = (30, 55, 80)
BTN_MUNE_H  = (42, 78, 110)
BTN_RESTART = (30, 70, 50)
BTN_RESTART_H = (42, 100, 70)
BTN_PAUSE   = (40, 40, 60)
BTN_PAUSE_H = (60, 60, 90)

# ─── 游戏参数 ───────────────────────────────────────────
# 资源管理
MAX_FUEL    = 100.0    # 燃料上限
FUEL_COST   = 0.04     # 每帧静止燃料消耗
MAX_DUR     = 100      # 耐久度上限
WIN_WAVES   = 10       # 生存模式胜利所需波次
WIN_WAVES_STORY1 = 3   # 故事模式第一战波次
WIN_WAVES_STORY2 = 3   # 故事模式第二战波次
WIN_WAVES_STORY3 = 5   # 故事模式第三战波次
STORY_HP_MULT  = [0.15, 0.30, 0.45]  # 三战敌舰HP加成(第1/2/3战)
# 导弹轰炸（仅第三战）
MISSILE_MIN_SPACING = 900   # 两次轰炸最小间隔(帧)
MISSILE_COUNT_MIN = 2       # 最少轰炸区数量
MISSILE_COUNT_MAX = 3       # 最多轰炸区数量
MISSILE_COUNTDOWN = 120     # 预警倒计时帧数(2秒)
MISSILE_EXPLODE_FRAMES = 180  # 爆炸持续帧数(3秒)
MISSILE_RADIUS = 80         # 轰炸半径
MISSILE_DAMAGE = 25         # 对玩家伤害（更高）
MISSILE_ENEMY_DAMAGE = 10   # 对敌人伤害（更低）
# 道具掉落（故事模式提高）
DROP_FUEL   = 18       # 拾取燃料恢复量
DROP_REPAIR = 12       # 拾取修复恢复量
DROP_UP     = 5        # 强化道具掉落概率(百分比)
DROP_REP_P  = 35       # 修复道具掉落概率(累计≤40%)
# 新增强化道具掉落概率（正常模式，四者一致）
DROP_SHIELD_P      = 5  # 护盾掉落概率(百分比)
DROP_FIRE_RATE_P   = 5  # 射速提升掉落概率(百分比)
DROP_JAMMING_P     = 5  # 信号干扰掉落概率(百分比)
# 得分配置
SCORE_ENEMY  = 10      # 击杀普通敌人得分
SCORE_BOSS   = 50      # 击杀战列舰得分
SCORE_FUEL   = 5       # 拾取燃料得分
SCORE_REPAIR = 8       # 拾取修复道具得分
SCORE_UPGRADE= 15      # 拾取强化道具得分
# 战斗参数
SPD         = 3.5      # 玩家移动速度
SPD_SPRINT  = 6.3      # 玩家冲刺速度（SPD × 1.8）
SHOOT_INT   = 13       # 射击间隔(帧)
BULLET_DMG  = 10       # 玩家子弹伤害
BULLET_SPD  = 8        # 玩家子弹速度
SPREAD      = 0.15     # 多发射弹扩散角度
RANGE       = 380      # 攻击范围
HINT_DUR    = 180      # 操作提示帧数（3秒）
# 无敌帧
INVINCIBLE_FRAMES = 45  # 受击后无敌帧数
# 强化道具
STRENGTHEN_DURATION = 600  # 强化持续时间（帧），约10秒

# ─── 冲刺 ───────────────────────────────────────────────
FUEL_COST_SPRINT = 0.08  # 冲刺时每帧燃料消耗速率

# ─── 贴图尺寸 ───────────────────────────────────────────
PLAYER_SIZE = 80

# ─── 强化道具（正常模式新增强化） ────────────────────────
# 护盾：一次性能抵挡伤害，蓝色透明球壳
SHIELD_DUR = 0          # 护盾为一次性，无持续时间
# 射速提升：15秒内提升射速（将射击间隔除以该系数）
FIRE_RATE_BOOST_DURATION = 900  # 15秒 × 60fps
FIRE_RATE_BOOST_MULT = 0.6      # 射击间隔 × 该值（越小越快），0.6 → 射速提升约1.7倍
# 信号干扰：使敌人与弹幕减速，蓝色电弧特效
SIGNAL_JAMMING_DURATION = 360   # 6秒 × 60fps
JAMMING_SPEED_MULT = 0.45       # 敌人/敌弹速度 × 该值

# ─── 敌舰配置 ───────────────────────────────────────────
ETYPES = {
    'scout':     {'hp':18,  'spd':1.5, 'dmg':5,   'rate':100, 'sz':26,  'bsz':8,  'bspd':3,  'col':(175,55,55)},
    'cruiser':   {'hp':45,  'spd':0.9, 'dmg':10,  'rate':80,  'sz':40,  'bsz':12, 'bspd':3,  'col':(150,45,45)},
    'battleship':{'hp':110, 'spd':0.5, 'dmg':22,  'rate':55,  'sz':56,  'bsz':16, 'bspd':4,  'col':(130,38,38)},
}

# ─── 工具函数 ───────────────────────────────────────────
import math

def clamp(v, lo, hi): return max(lo, min(hi, v))   # 限制值在 [lo, hi] 范围内
def dst(a, b): return math.hypot(a[0]-b[0], a[1]-b[1])  # 两点间距离
def ang(a, b): return math.atan2(b[1]-a[1], b[0]-a[0])  # 从 a 到 b 的角度（弧度）
