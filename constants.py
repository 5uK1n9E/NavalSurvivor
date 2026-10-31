"""
海上军舰 - 常量与配置
集中管理所有游戏参数、颜色、按钮配置和工具函数。
其他模块通过 import constants as C 使用。
"""
DEBUG = False
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
BTN_MENU    = (30, 55, 80)
BTN_MENU_H  = (42, 78, 110)
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
# ─── 生存模式敌军成长（每 10 波为阶段分界）──────────────
WAVE_STAGE_LENGTH = 10              # 每 10 波为一个阶段
WAVE_HP_PER_WAVE = 0.10             # 阶段内：每波血量倍率增加量
WAVE_HP_STAGE_BONUS = 0.80          # 跨阶段：血量倍率额外一次性增加
WAVE_COUNT_PER_WAVE = 2             # 阶段内：每波敌人数量增加
WAVE_COUNT_STAGE_BONUS = 5          # 跨阶段：敌人数量额外一次性增加
# 卡牌触发间隔（波次）。1 = 每波触发一次；2 = 每两波触发一次
CARD_WAVE_INTERVAL = 1
# -----强化品质概率配置-----
UPGRADE_QUALITY_COMMON = "common"    # 绿色普通
UPGRADE_QUALITY_RARE = "rare"       # 蓝色高级
UPGRADE_QUALITY_EPIC = "epic"       # 紫色史诗
UPGRADE_QUALITY_GOLD = "gold"       # 金色传说（每个只能获取一次）
# 蓝色概率20%，紫色史诗8%，金色传说3%
UPGRADE_RARE_CHANCE = 0.20
UPGRADE_EPIC_CHANCE = 0.08
UPGRADE_GOLD_CHANCE = 0.03

# -----燃烧子弹DoT参数-----
BURN_BASE_DPS = 2          # 基础每秒燃烧伤害
BURN_BASE_DURATION = 3.0   # 基础持续秒
BURN_DPS_PER_STACK = 1     # 每选一次蓝色燃烧强化，每秒伤害+1
BURN_DUR_PER_STACK = 0.8   # 每选一次，持续时间 +0.8秒
BURN_TICK_RATE = 0.5       # 每0.5秒结算一次燃烧伤害
# 连锁闪电基础
CHAIN_LIGHTNING_BASE_RADIUS = 120
CHAIN_LIGHTNING_BASE_DAMAGE = 6
CHAIN_LIGHTNING_RADIUS_PER_STACK = 25
CHAIN_LIGHTNING_DMG_PER_STACK = 3
CHAIN_LIGHTNING_MAX_TARGET = 4   # 一次闪电最多连锁几个额外敌人
# 导弹偏转强化
MISSILE_SHUNT_PLAYER_DAMAGE_REDUCE_PER_STACK = 0.15   # 每层减少15%所受导弹伤害
MISSILE_SHUNT_ENEMY_DAMAGE_BONUS_PER_STACK = 0.20     # 每层敌人导弹伤害+20%
MISSILE_SHUNT_PLAYER_MIN_MULT = 0.10                  # 玩家最低倍率，不能低于0.1
# 反击冲击强化
COUNTER_STRIKE_DAMAGE = 18      # 每次反击固定伤害
# 浴血击杀强化（击杀敌人回血）
LIFESTEAL_BASE_HEAL = 3
LIFESTEAL_PER_STACK = 2
# 满盈之力强化：满血获得额外子弹伤害
FULL_HP_BONUS_DMG_PER_STACK = 4
# 重型装甲强化（紫色史诗）
HEAVY_ARMOR_PLAYER_SIZE_PER_STACK = 6        # 每层玩家半径 +6
HEAVY_ARMOR_DEF_PER_STACK = 8                # 每层受到伤害 -8
HEAVY_ARMOR_SPD_PENALTY_PER_STACK = 0.4      # 每层移动速度 -0.4
# 钢铁碰撞强化（紫色史诗）
COLLISION_DAMAGE_PER_STACK = 10          # 每层碰撞伤害
COLLISION_ARMOR_PENALTY_PER_STACK = 3    # 每层护甲惩罚（正值=受伤增加）
# 自动瞄准强化（紫色史诗）
AUTO_AIM_FIRE_RATE_MULT_PER_STACK = 0.20    # 每层射击间隔 ×(1 - 0.20×层)
AUTO_AIM_FIRE_RATE_MULT_MIN = 0.30          # 射速乘数下限（13 → 约 4 帧）
AUTO_AIM_DMG_MULT_PER_STACK = 0.12          # 每层伤害 ×(1 - 0.12×层)
AUTO_AIM_DMG_MULT_MIN = 0.40                # 伤害乘数下限（40%）
# 强化轰炸（紫色史诗）
BOMBARDMENT_DMG_MULT_PER_STACK = 0.30      # 每层双方伤害 ×(1 + 0.30×层)
BOMBARDMENT_SPACING_MULT_PER_STACK = 0.15  # 每层间隔 ×(1 - 0.15×层)
BOMBARDMENT_SPACING_MULT_MIN = 0.20        # 间隔乘数下限（900×0.20 = 180 帧 = 3 秒）
BOMBARDMENT_SPACING_FLOOR = 180            # 间隔硬底（帧）
MISSILE_COUNT_PER_STACK = 1                # 每层强化，轰炸圈数 +1
MISSILE_COUNT_CAP       = 12               # 轰炸圈总数硬上限
# 血祭强化（紫色史诗）
BLOOD_PACT_MAX_DUR_PER_STACK = 50       # 每层最大耐久 +50
BLOOD_PACT_DUR_MULT = 0.7               # 每次选择当前耐久 ×0.5
BLOOD_PACT_MIN_DUR = 20                 # 当前耐久保底
# 杀戮契约强化（紫色史诗）
BLOOD_OATH_DMG_PENALTY = 8         # 选择瞬间伤害降低
BLOOD_OATH_KILL_TARGET = 15        # 每层击杀目标
BLOOD_OATH_DMG_REWARD = 20         # 完成后伤害增加
# 超载反应强化（金色传说）
# 超载倍率 = BASE + 闪电层数 × CHAIN_BONUS + 燃烧层数 × BURN_BONUS
OVERLOAD_BASE_MULT = 1.5            # 触发超载时基础倍率
OVERLOAD_CHAIN_BONUS = 0.2          # 每层闪电强化的额外加成
OVERLOAD_BURN_BONUS = 0.2           # 每层燃烧强化的额外加成
# 轰炸协议强化（金色传说）
BOMBARDMENT_MODE_SPACING = 450           # 该强化专属轰炸间隔（帧，= 1 秒），优先级高于其他间隔算法
BOMBARDMENT_MODE_DMG_MULT = 3.0         # 对敌人伤害额外倍率（仅敌人，不影响玩家）
BOMBARDMENT_MODE_COUNT_BONUS = 5        # 该强化额外增加的轰炸圈数量
# 齐射协议强化（金色传说）
VOLLEY_PROTOCOL_DMG_MULT = 1.8      # 伤害大幅提升乘数
# 血怒强化（金色传说）
# 增幅 = BASE + clamp((1 - hp_ratio) / (1 - TRIGGER_RATIO), 0, 1) × (MAX - BASE)
BLOODLUST_BASE_MULT = 0.10       # 满血时的基础增幅（+10%）
BLOODLUST_MAX_MULT = 1.00        # 最高增幅（+100%，即 ×2.0）
BLOODLUST_TRIGGER_RATIO = 0.10   # 生命比例降到该值时达到最高增幅
# 静海协议强化（金色传说）
# 未受伤累计满该帧数后自动获得护盾（8 秒 = 480 帧）
SHIELD_CHARGE_FRAMES = 480
# 不屈意志强化（金色传说）
REVIVE_HEAL_RATIO = 0.5             # 复活后恢复的最大耐久比例（50%）
REVIVE_INVINCIBLE_FRAMES = 120      # 复活后的无敌帧数（2 秒）
# 死亡回响强化（金色传说）
DEATH_RING_BULLET_COUNT = 12       # 环形弹幕数量
DEATH_RING_DMG_RATIO = 0.5          # 伤害比例（相对玩家子弹伤害）
DEATH_RING_BULLET_SPEED = 6.0       # 环形弹幕飞行速度
DEATH_RING_BULLET_RADIUS = 4        # 环形弹幕半径
# 烈焰喷射强化（金色传说）
FIRE_BREATH_COOLDOWN = 180             # 喷射冷却帧数（3 秒）
FIRE_BREATH_DAMAGE = 100                # 单次喷射固定伤害（不受子弹伤害加成影响）
FIRE_BREATH_RANGE = 280                # 喷射射程（像素）
FIRE_BREATH_HALF_ANGLE = 35            # 扇形半角（度），总角度 = 半角 × 2 = 70°
FIRE_BREATH_VISUAL_FRAMES = 24         # 喷射视觉持续帧数（仅视觉，不影响伤害判定）


# ─── 工具函数 ───────────────────────────────────────────
import math

def clamp(v, lo, hi): return max(lo, min(hi, v))   # 限制值在 [lo, hi] 范围内
def dst(a, b): return math.hypot(a[0]-b[0], a[1]-b[1])  # 两点间距离
def ang(a, b): return math.atan2(b[1]-a[1], b[0]-a[0])  # 从 a 到 b 的角度（弧度）
