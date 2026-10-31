"""
海上军舰 - 卡牌强化系统
每个波次结束（进入下一波之前）出现 3 张卡牌供玩家选择，选择后永久强化属性。
触发间隔由 constants.CARD_WAVE_INTERVAL 控制。
"""
import random
import pygame
import constants as C
game_state = None

def _wrap_text_lines(font, text, max_px_width):
    """中文逐字折行，返回字符串列表，每行不超过max_px_width像素"""
    lines = []
    current = []
    cur_w = 0
    for ch in text:
        w, _ = font.size(ch)
        if cur_w + w > max_px_width and current:
            lines.append(''.join(current))
            current = [ch]
            cur_w = w
        else:
            current.append(ch)
            cur_w += w
    if current:
        lines.append(''.join(current))
    return lines

def _parse_highlight(text):
    """
    解析 **...** 标记，返回 (纯文本, 与每个字符一一对应的 is_highlight 布尔列表)。
    未闭合的 ** 视为普通字符（容错）。
    """
    out_text = []
    is_hl = []
    i = 0
    in_mark = False
    while i < len(text):
        if text[i:i+2] == '**':
            in_mark = not in_mark
            i += 2
            continue
        out_text.append(text[i])
        is_hl.append(in_mark)
        i += 1
    return ''.join(out_text), is_hl

def _wrap_text_with_highlight(font, text, max_px_width):
    """
    按字符折行，返回 list[list[(str, is_highlight)]]。
    外层 = 行列表；内层 = 该行内的若干连续段（相同高亮状态合并）。
    """
    clean_text, is_hl = _parse_highlight(text)
    lines = []
    current = []          # [(char, is_hl), ...]
    cur_w = 0
    for ch, hl in zip(clean_text, is_hl):
        w, _ = font.size(ch)
        if cur_w + w > max_px_width and current:
            lines.append(current)
            current = [(ch, hl)]
            cur_w = w
        else:
            current.append((ch, hl))
            cur_w += w
    if current:
        lines.append(current)

    # 将每行的字符压缩成段
    result = []
    for line in lines:
        segs = []
        buf = ''
        buf_hl = None
        for ch, hl in line:
            if buf and hl != buf_hl:
                segs.append((buf, buf_hl))
                buf = ch
                buf_hl = hl
            else:
                buf += ch
                buf_hl = hl
        if buf:
            segs.append((buf, buf_hl))
        result.append(segs)
    return result

# ─── 升级类型定义 ────────────────────────────────────────
class UpgradeType:
    """升级类型：定义名称、描述、效果"""
    def __init__(self, order, key, name, desc,quality, effect_fn):
        self.order = order        # 序号（用于调试面板）
        self.key = key
        self.name = name
        self.desc = desc
        self.quality = quality    # "common"绿色普通 / "rare"蓝色高级
        self.effect_fn = effect_fn  # effect_fn(player) -> None

    @property
    def icon(self):
        icons = {
            'max_dur': '[HP]',
            'bullet_dmg': '[ATK]',
            'fire_rate': '[ATKSPD]',
            'fuel_save': '[GAS]',
            'move_spd': '[SPD]',
            'armor': '[DEF]',
            'bullet_size': '[BUL]',
            'smaller_player': '[SIZE-]',
            'slow_enemy_bullets': '[SLOW]',
            'bullet_burn': '[FIRE]',
            'bullet_chain': '[LIGHT]',
            'missile_shunt': '[BOMB]',
            'counter_strike': '[RIP]',
            'lifesteal': '[BLOOD]',
            'full_hp_power': '[FULL]',
            'pierce_round': '[PIERCE]',
            'heavy_armor': '[HEAVY]',
            'collision_damage': '[SMASH]',
            'auto_aim': '[AIM]',
            'bombardment': '[BOMB+]',
            'blood_pact': '[PACT]',
            'blood_oath': '[OATH]',
            'overload_reaction': '[OVERLOAD]',
            'bombardment_mode': '[BARAGE]',
            'volley_protocol': '[VOLLEY]',
            'bloodlust': '[RAGE]',
            'shield_charge': '[CALM]',
            'revive': '[REVIVE]',
            'death_ring': '[RING]',
            'fire_breath': '[BREATH]',
        }
        return icons.get(self.key, '✨')


# ─── 升级效果函数 ────────────────────────────────────────
def _apply_max_dur(p):
    """增加最大耐久上限 +20"""
    p.max_dur_bonus += 20
    p.dur_bonus += 20
    effective_max = get_effective_max_dur()
    p.dur = min(p.dur + 20, effective_max)

def _apply_bullet_dmg(p):
    """增加子弹伤害 +2"""
    p.dmg_bonus += 2

def _apply_fire_rate(p):
    """提升射速（减少射击间隔），下限5帧，上限-16"""
    if p.fire_rate_bonus > -16:
        p.fire_rate_bonus = p.fire_rate_bonus - 1

def _apply_fuel_save(p):
    """降低燃料消耗（最多减少90%）"""
    if p.fuel_save_bonus < 90:
        p.fuel_save_bonus = min(p.fuel_save_bonus + 10, 90)

def _apply_move_spd(p):
    """提升移动速度，上限 +4"""
    if p.move_spd_bonus < 4.0:
        p.move_spd_bonus = min(p.move_spd_bonus + 0.2, 4.0)

def _apply_armor(p):
    """减少受到伤害（每次-2，无上限）"""
    p.armor_bonus -= 2

def _apply_bullet_size(p):
    """增大子弹尺寸 +3"""
    p.bullet_size_bonus += 3

def _apply_smaller_player(p):
    """缩小玩家体型，下限 r=20"""
    if p.player_size_bonus > -16:
        p.player_size_bonus = max(p.player_size_bonus - 2, -16)

def _apply_slow_enemy_bullets(p):
    """降低敌方子弹速度，最多 -2"""
    if p.enemy_bullet_slow_bonus < 2.0:
        p.enemy_bullet_slow_bonus = min(p.enemy_bullet_slow_bonus + 0.2, 2.0)

def _apply_bullet_burn(p):
    """蓝色高级：子弹燃烧效果；重复选择提升燃烧DPS与持续时长"""
    # 新增玩家属性，记录燃烧强化层数
    if not hasattr(p, 'bullet_burn_stack'):
        p.bullet_burn_stack = 0
    p.bullet_burn_stack += 1

def _apply_bullet_chain(p):
    p.chain_stack += 1

def _apply_missile_shunt(p):
    """蓝色稀有：爆破偏转，导弹轰炸降低自伤、提高对敌人伤害"""
    p.missile_shunt_stack +=1

def _apply_counter_strike(p):
    """蓝色稀有：反击冲击，挨打触发反击，每层+1次反击次数"""
    p.counter_strike_stack += 1

def _apply_lifesteal(p):
    """蓝色稀有：浴血击杀，击杀敌人恢复血量；每层提高回血量"""
    p.lifesteal_stack += 1

def _apply_full_hp_power(p):
    """蓝色稀有：满盈之力；满血时获得额外子弹伤害，掉血加成消失"""
    p.full_hp_power_stack +=1

def _apply_pierce_round(p):
    """紫色史诗：破甲弹；子弹伤害+12，获得穿透次数，射击间隔+4（变慢）"""
    p.pierce_stack += 1
    p.dmg_bonus += 12
    p.fire_rate_bonus += 4

def _apply_heavy_armor(p):
    """紫色史诗：重型装甲；体型变大、护甲大幅提升，但移动速度下降"""
    p.player_size_bonus += C.HEAVY_ARMOR_PLAYER_SIZE_PER_STACK
    p.armor_bonus       -= C.HEAVY_ARMOR_DEF_PER_STACK
    p.heavy_armor_spd_penalty = getattr(p, 'heavy_armor_spd_penalty', 0.0) \
                                + C.HEAVY_ARMOR_SPD_PENALTY_PER_STACK
    p.heavy_armor_stack = getattr(p, 'heavy_armor_stack', 0) + 1

def _apply_collision_damage(p):
    """紫色史诗：钢铁碰撞；受伤触发无敌帧时对接触敌人造成伤害，但护甲降低"""
    p.collision_damage_stack += 1
    p.armor_bonus += C.COLLISION_ARMOR_PENALTY_PER_STACK

def _apply_auto_aim(p):
    """紫色史诗：自动瞄准；射速大幅上升并锁定最近敌人，但伤害大幅降低"""
    p.auto_aim_stack += 1

def _apply_bombardment(p):
    """紫色史诗：强化轰炸；导弹对敌我双方伤害大幅增加，且出现更频繁"""
    p.bombardment_stack += 1

def _apply_blood_pact(p):
    """紫色史诗：血祭；最大耐久大幅提升，但选择瞬间当前耐久减半（保底20）"""
    p.blood_pact_stack += 1
    p.max_dur_bonus += C.BLOOD_PACT_MAX_DUR_PER_STACK
    # 当前耐久砍半，保底
    p.dur = max(C.BLOOD_PACT_MIN_DUR, int(p.dur * C.BLOOD_PACT_DUR_MULT))

def _apply_blood_oath(p):
    """紫色史诗：杀戮契约；选择瞬间降低伤害，击杀目标数后返还更多伤害"""
    # 已经有一层进行中的，理论上卡池不会给出，但双重保险
    if getattr(p, 'blood_oath_pending', False):
        return
    p.dmg_bonus -= C.BLOOD_OATH_DMG_PENALTY
    p.blood_oath_pending = True
    p.blood_oath_kills = 0
def process_blood_oath_kill():
    """击杀敌人时调用：推进杀戮契约进度，达成目标时发放奖励"""
    if game_state is None:
        return
    p = game_state.player
    if not getattr(p, 'blood_oath_pending', False):
        return
    p.blood_oath_kills += 1
    if p.blood_oath_kills >= C.BLOOD_OATH_KILL_TARGET:
        # 契约完成：偿还伤害并给予奖励
        p.dmg_bonus += C.BLOOD_OATH_DMG_REWARD
        p.blood_oath_pending = False
        p.blood_oath_kills = 0
        p.blood_oath_completed += 1

def _apply_overload_reaction(p):
    """金色传说：超载反应；附带闪电的子弹命中燃烧中的敌人时，本次伤害大幅提升"""
    p.overload_reaction_stack += 1

def _apply_bombardment_mode(p):
    """金色传说：轰炸协议；玩家不再发射子弹，轰炸高频率、高伤害且不伤玩家"""
    p.bombardment_mode_stack += 1

def _apply_volley_protocol(p):
    """金色传说：齐射协议；常驻双发、无限穿透、伤害大幅提升"""
    p.volley_protocol_stack += 1
    p.bcount += 1     # 常驻弹数 +1

def _apply_bloodlust(p):
    """金色传说：血怒；随生命值降低而增加子弹伤害增幅"""
    p.bloodlust_stack += 1

def _apply_shield_charge(p):
    """金色传说：静海协议；未受伤一段时间后自动获得护盾，持盾时不耗燃料"""
    p.shield_charge_stack += 1

def _apply_revive(p):
    """金色传说：不屈意志；获得一次复活机会"""
    p.revive_stack += 1

def _apply_death_ring(p):
    """金色传说：死亡回响；击杀敌人时在死亡位置释放环形弹幕"""
    p.death_ring_stack += 1

def _apply_fire_breath(p):
    """金色传说：烈焰喷射；每隔一段时间向面朝方向喷射扇形火焰"""
    p.fire_breath_stack += 1

# ─── 升级类型列表 ─────────────────────────────
ALL_UPGRADES = [
    UpgradeType(1, 'max_dur',    '耐久强化', '最大耐久 +20，当前耐久同步提升', C.UPGRADE_QUALITY_COMMON, _apply_max_dur),
    UpgradeType(2, 'bullet_dmg', '火力强化', '子弹伤害 +2',                   C.UPGRADE_QUALITY_COMMON, _apply_bullet_dmg),
    UpgradeType(3, 'fire_rate',  '射速强化', '射击间隔 -1帧', C.UPGRADE_QUALITY_COMMON, _apply_fire_rate),
    UpgradeType(4, 'fuel_save',  '燃料节省', '燃料消耗 -10%',      C.UPGRADE_QUALITY_COMMON, _apply_fuel_save),
    UpgradeType(5, 'move_spd',   '移动加速', '移动速度 +0.2',      C.UPGRADE_QUALITY_COMMON, _apply_move_spd),
    UpgradeType(6, 'armor',      '装甲强化', '受到伤害 -2',          C.UPGRADE_QUALITY_COMMON, _apply_armor),
    UpgradeType(7, 'bullet_size','弹道增大', '子弹尺寸 +3',                    C.UPGRADE_QUALITY_COMMON, _apply_bullet_size),
    UpgradeType(8, 'smaller_player', '目标缩小', '玩家体型 -2',   C.UPGRADE_QUALITY_COMMON, _apply_smaller_player),
    UpgradeType(9, 'slow_enemy_bullets', '减速弹道', '敌方子弹速度 -0.2', C.UPGRADE_QUALITY_COMMON, _apply_slow_enemy_bullets),
    UpgradeType(10, 'bullet_burn', '燃烧弹药', '子弹命中使敌人持续燃烧；重复选择提升燃烧伤害与持续时间',
                C.UPGRADE_QUALITY_RARE, _apply_bullet_burn),
    UpgradeType(11, 'bullet_chain', '闪电弹药', '子弹命中释放连锁闪电，电击附近敌人；重复选择提升伤害与范围',
                C.UPGRADE_QUALITY_RARE, _apply_bullet_chain),
    UpgradeType(12, 'missile_shunt', '爆破偏转', '导弹轰炸对你伤害降低，对敌人伤害提高；重复选择放大效果',
                C.UPGRADE_QUALITY_RARE, _apply_missile_shunt),
    UpgradeType(13, 'counter_strike', '反击冲击',
                '受到伤害时触发反击；每一层增加一次反击攻击次数',
                C.UPGRADE_QUALITY_RARE, _apply_counter_strike),
    UpgradeType(14, 'lifesteal', '浴血击杀',
                '击杀敌人恢复耐久；重复选择提高击杀回血量',
                C.UPGRADE_QUALITY_RARE, _apply_lifesteal),
    UpgradeType(15, 'full_hp_power', '满盈之力',
                '血量处于满血状态时获得额外子弹伤害；受伤后加成消失，重复选择提升加成',
                C.UPGRADE_QUALITY_RARE, _apply_full_hp_power),
    UpgradeType(16, 'pierce_round', '破甲弹',
                '子弹伤害大幅增加，获得穿透效果；但射击间隔增大，重复选择继续叠加伤害与穿透',
                C.UPGRADE_QUALITY_EPIC, _apply_pierce_round),
    UpgradeType(17, 'heavy_armor', '重型装甲',
                f'玩家体型 +{C.HEAVY_ARMOR_PLAYER_SIZE_PER_STACK}，'
                f'受到伤害 -{C.HEAVY_ARMOR_DEF_PER_STACK}，'
                f'移动速度 -{C.HEAVY_ARMOR_SPD_PENALTY_PER_STACK}',
                C.UPGRADE_QUALITY_EPIC, _apply_heavy_armor),
    UpgradeType(18, 'collision_damage', '钢铁碰撞',
                f'受击进入无敌帧时，对接触的敌人造成 {C.COLLISION_DAMAGE_PER_STACK} 伤害；'
                f'但受伤 +{C.COLLISION_ARMOR_PENALTY_PER_STACK}，重复选择叠加',
                C.UPGRADE_QUALITY_EPIC, _apply_collision_damage),
    UpgradeType(19, 'auto_aim', '自动瞄准',
                f'射速大幅上升（间隔最低 {int(C.SHOOT_INT * C.AUTO_AIM_FIRE_RATE_MULT_MIN)} 帧），'
                f'自动锁定最近敌人；伤害降低至 {int(C.AUTO_AIM_DMG_MULT_MIN * 100)}%，重复选择叠加',
                C.UPGRADE_QUALITY_EPIC, _apply_auto_aim),
    UpgradeType(20, 'bombardment', '强化轰炸',
                f'导弹对敌我双方伤害 +{int(C.BOMBARDMENT_DMG_MULT_PER_STACK * 100)}%/层，'
                f'出现间隔 -{int(C.BOMBARDMENT_SPACING_MULT_PER_STACK * 100)}%/层，'
                f'轰炸圈 +{C.MISSILE_COUNT_PER_STACK}/层（上限 {C.MISSILE_COUNT_CAP} 圈）；',
                C.UPGRADE_QUALITY_EPIC, _apply_bombardment),
    UpgradeType(21, 'blood_pact', '血祭',
                f'选择时：最大耐久 +{C.BLOOD_PACT_MAX_DUR_PER_STACK}，'
                f'当前耐久 -{int((1 - C.BLOOD_PACT_DUR_MULT) * 100)}%'
                f'（保底 {C.BLOOD_PACT_MIN_DUR}）；重复选择继续叠加',
                C.UPGRADE_QUALITY_EPIC, _apply_blood_pact),
    UpgradeType(22, 'blood_oath', '杀戮契约',
                f'选择时：伤害 -{C.BLOOD_OATH_DMG_PENALTY}；'
                f'击杀 {C.BLOOD_OATH_KILL_TARGET} 个敌人后伤害 '
                f'+{C.BLOOD_OATH_DMG_REWARD};未完成前不会再次出现',
                C.UPGRADE_QUALITY_EPIC, _apply_blood_oath),
    UpgradeType(23, 'overload_reaction', '超载反应',
                f'闪电子弹命中燃烧中的敌人时触发超载：'
                f'伤害×(基础{C.OVERLOAD_BASE_MULT:.1f}+闪电层×{C.OVERLOAD_CHAIN_BONUS}+燃烧层×{C.OVERLOAD_BURN_BONUS})',
                C.UPGRADE_QUALITY_GOLD, _apply_overload_reaction),
    UpgradeType(24, 'bombardment_mode', '轰炸协议',
                f'**玩家不再发射子弹**；轰炸区间固定为 {C.BOMBARDMENT_MODE_SPACING} 帧、'
                f'对敌伤害 ×{C.BOMBARDMENT_MODE_DMG_MULT:.1f}（+{C.BOMBARDMENT_MODE_COUNT_BONUS} 圈），'
                f'且不再伤害玩家',
                C.UPGRADE_QUALITY_GOLD, _apply_bombardment_mode),
    UpgradeType(25, 'volley_protocol', '齐射协议',
                f'常驻双发子弹；子弹无限穿透；'
                f'伤害 ×{C.VOLLEY_PROTOCOL_DMG_MULT:.1f}',
                C.UPGRADE_QUALITY_GOLD, _apply_volley_protocol),
    UpgradeType(26, 'bloodlust', '血怒',
                f'**血量越低伤害越高**：满血时 +{int(C.BLOODLUST_BASE_MULT * 100)}%，'
                f'生命比例降至 {int(C.BLOODLUST_TRIGGER_RATIO * 100)}% 时提升至 +{int(C.BLOODLUST_MAX_MULT * 100)}%，',
                C.UPGRADE_QUALITY_GOLD, _apply_bloodlust),
    UpgradeType(27, 'shield_charge', '静海协议',
                f'未受伤 {C.SHIELD_CHARGE_FRAMES // C.FPS} 秒后自动获得护盾；'
                f'持有护盾时不再消耗燃料',
                C.UPGRADE_QUALITY_GOLD, _apply_shield_charge),
    UpgradeType(28, 'revive', '不屈意志',
                f'耐久归零时自动复活一次：'
                f'恢复 {int(C.REVIVE_HEAL_RATIO * 100)}% 最大耐久，'
                f'并获得 {C.REVIVE_INVINCIBLE_FRAMES // C.FPS} 秒无敌',
                C.UPGRADE_QUALITY_GOLD, _apply_revive),
    UpgradeType(29, 'death_ring', '死亡回响',
                f'敌人被击杀时，在死亡位置释放 {C.DEATH_RING_BULLET_COUNT} 发环形弹幕，'
                f'每发造成玩家子弹伤害的 {int(C.DEATH_RING_DMG_RATIO * 100)}%；'
                f'环形弹幕击杀不会连锁触发',
                C.UPGRADE_QUALITY_GOLD, _apply_death_ring),
    UpgradeType(30, 'fire_breath', '烈焰喷射',
                f'每 {C.FIRE_BREATH_COOLDOWN // C.FPS} 秒向面朝方向喷射扇形火焰'
                f'（±{C.FIRE_BREATH_HALF_ANGLE}°，{C.FIRE_BREATH_RANGE}px），'
                f'造成 {C.FIRE_BREATH_DAMAGE} 点**固定伤害**',
                C.UPGRADE_QUALITY_GOLD, _apply_fire_breath),
]




# ─── Player 初始化扩展 ───────────────────────────────────
def init_player_upgrades(p):
    """为 Player 对象添加升级相关属性"""
    p.max_dur_bonus = 0          # 额外耐久上限
    p.dur_bonus = 0              # 当前耐久加成（用于恢复时同步）
    p.dmg_bonus = 0              # 额外伤害
    p.fire_rate_bonus = 0        # 射击间隔减少量（负数=更快）
    p.fuel_save_bonus = 0        # 燃料节省百分比（0-90）
    p.move_spd_bonus = 0.0       # 移动速度加成
    p.armor_bonus = 0            # 伤害减免
    p.bullet_size_bonus = 0      # 子弹尺寸加成
    p.player_size_bonus = 0      # 玩家体型变化（负数=更小）
    p.enemy_bullet_slow_bonus = 0.0  # 敌方子弹减速
    p.upgrade_counts = {}        # {key: 已选择次数}
    p.bullet_burn_stack = 0  # 燃烧弹药强化层数，0=无燃烧效果
    p.chain_stack = 0 #闪电弹药层数
    p.missile_shunt_stack = 0  # 轰炸偏转层数
    p.counter_strike_stack = 0  # 反击冲击层数
    p.lifesteal_stack = 0  # 浴血击杀层数
    p.full_hp_power_stack = 0  # 满盈之力层数
    p.pierce_stack = 0  # 穿透层数
    p.heavy_armor_stack = 0
    p.heavy_armor_spd_penalty = 0.0
    p.collision_damage_stack = 0
    p.auto_aim_stack = 0
    p.bombardment_stack = 0
    p.blood_pact_stack = 0
    p.blood_oath_pending = False
    p.blood_oath_kills = 0
    p.blood_oath_completed = 0
    p.overload_reaction_stack = 0
    p.bombardment_mode_stack = 0
    p.volley_protocol_stack = 0
    p.bloodlust_stack = 0
    p.shield_charge_stack = 0
    p.shield_charge_timer = 0
    p.revive_stack = 0
    p.revive_used = False
    p.death_ring_stack = 0
    p.fire_breath_stack = 0

def apply_upgrade(p, upgrade):
    """应用升级效果并记录计数"""
    upgrade.effect_fn(p)
    p.upgrade_counts[upgrade.key] = p.upgrade_counts.get(upgrade.key, 0) + 1


# ─── 查询函数 ────────────────────────────────────────────
def get_used_upgrade_keys():
    """获取玩家已选择的升级类型集合"""
    if game_state is None:
        return set()
    return set(getattr(game_state.player, 'upgrade_counts', {}).keys())

def get_available_upgrades():
    """返回当前可用的升级类型列表：实时读取player属性，过滤已经叠到上限的强化"""
    if game_state is None:
        return list(ALL_UPGRADES)
    p = game_state.player
    avail = []
    for upg in ALL_UPGRADES:
        if not is_upgrade_reached_max(p, upg.key):
            avail.append(upg)
    return avail


def get_upgrade_counts():
    """获取各升级的选择次数字典 {key: count}"""
    if game_state is None:
        return {}
    return getattr(game_state.player, 'upgrade_counts', {})

def get_upgrade_history():
    """获取已选择升级的完整历史（含序号、名称、次数）"""
    if game_state is None:
        return []
    counts = get_upgrade_counts()
    result = []
    for u in ALL_UPGRADES:
        if u.key in counts:
            result.append({
                'order': u.order,
                'key': u.key,
                'name': u.name,
                'icon': u.icon,
                'count': counts[u.key],
            })
    return result

def get_effective_max_dur():
    """获取有效最大耐久"""
    if game_state is None:
        return C.MAX_DUR
    base = C.MAX_DUR
    bonus = game_state.player.max_dur_bonus if hasattr(game_state.player, 'max_dur_bonus') else 0
    return base + bonus

def get_effective_bullet_dmg():
    """获取有效子弹伤害（自动瞄准会按乘数降低）"""
    if game_state is None:
        return C.BULLET_DMG
    base = C.BULLET_DMG
    bonus = game_state.player.dmg_bonus if hasattr(game_state.player, 'dmg_bonus') else 0
    _, full_hp_bonus = get_full_hp_bonus_info(game_state.player)
    dmg = base + bonus + full_hp_bonus
    # 自动瞄准：伤害乘数
    stack = getattr(game_state.player, 'auto_aim_stack', 0)
    if stack > 0:
        mult = max(C.AUTO_AIM_DMG_MULT_MIN,
                   1.0 - stack * C.AUTO_AIM_DMG_MULT_PER_STACK)
        dmg = int(dmg * mult)
    # 齐射协议：伤害大幅提升乘数
    if getattr(game_state.player, 'volley_protocol_stack', 0) > 0:
        dmg = int(dmg * C.VOLLEY_PROTOCOL_DMG_MULT)
    if getattr(game_state.player, 'bloodlust_stack', 0) > 0:
        dmg = int(dmg * get_bloodlust_damage_mult(game_state.player))
    return max(1, dmg)   # 保证至少 1 点伤害

def get_effective_shoot_interval():
    """获取有效射击间隔（自动瞄准可突破 5 帧下限）"""
    if game_state is None:
        return C.SHOOT_INT
    base = C.SHOOT_INT
    bonus = game_state.player.fire_rate_bonus if hasattr(game_state.player, 'fire_rate_bonus') else 0
    interval = base + bonus
    # 自动瞄准：射速乘数
    stack = getattr(game_state.player, 'auto_aim_stack', 0)
    if stack > 0:
        mult = max(C.AUTO_AIM_FIRE_RATE_MULT_MIN,
                   1.0 - stack * C.AUTO_AIM_FIRE_RATE_MULT_PER_STACK)
        interval = int(interval * mult)
        return max(2, interval)   # 自动瞄准允许最低 2 帧
    return max(5, interval)       # 无自动瞄准仍保持原 5 帧下限

def get_effective_fuel_cost(rate_type='normal'):
    """获取有效燃料消耗"""
    if game_state is None:
        if rate_type == 'normal':
            return C.FUEL_COST
        else:
            return C.FUEL_COST_SPRINT
    base = C.FUEL_COST if rate_type == 'normal' else C.FUEL_COST_SPRINT
    save = game_state.player.fuel_save_bonus if hasattr(game_state.player, 'fuel_save_bonus') else 0
    return base * (1 - save / 100.0)

def get_effective_speed():
    """获取有效移动速度"""
    if game_state is None:
        return C.SPD
    base = C.SPD
    bonus = game_state.player.move_spd_bonus if hasattr(game_state.player, 'move_spd_bonus') else 0
    penalty = getattr(game_state.player, 'heavy_armor_spd_penalty', 0.0)
    return max(0.5, base + bonus - penalty)

def get_effective_sprint_speed():
    """获取有效冲刺速度"""
    if game_state is None:
        return C.SPD_SPRINT
    base = C.SPD_SPRINT
    bonus = game_state.player.move_spd_bonus if hasattr(game_state.player, 'move_spd_bonus') else 0
    penalty = getattr(game_state.player, 'heavy_armor_spd_penalty', 0.0)
    return max(0.5, base + bonus * 1.5 - penalty * 1.5)

def get_effective_player_radius():
    """获取有效玩家半径（重型装甲无层数上限，但半径设物理上限防止玩家卡死）"""
    if game_state is None:
        return 36
    base = 36
    bonus = game_state.player.player_size_bonus if hasattr(game_state.player, 'player_size_bonus') else 0
    # 下限 20；上限 200，保证玩家仍能在屏幕内移动
    return min(200, max(20, base + bonus))

def get_effective_bullet_radius():
    """获取有效子弹半径"""
    if game_state is None:
        return 6
    base = 6
    bonus = game_state.player.bullet_size_bonus if hasattr(game_state.player, 'bullet_size_bonus') else 0
    return base + bonus

def get_effective_enemy_bullet_speed(base_spd):
    """获取有效敌方子弹速度"""
    if game_state is None:
        return base_spd
    slow = game_state.player.enemy_bullet_slow_bonus if hasattr(game_state.player, 'enemy_bullet_slow_bonus') else 0
    return max(1.0, base_spd - slow)  # 最低1.0，不能静止

def get_damage_reduction():
    """获取伤害减免量"""
    if game_state is None:
        return 0
    return game_state.player.armor_bonus if hasattr(game_state.player, 'armor_bonus') else 0

def get_player_scale_bonus():
    """根据有效玩家半径计算贴图缩放比例，保证视觉尺寸与碰撞半径一致"""
    if not game_state:
        return 1.0
    return get_effective_player_radius() / 36.0

def get_burn_dps():
    """获取燃烧每秒伤害"""
    if not game_state:
        return 0
    p = game_state.player
    stack = getattr(p, "bullet_burn_stack", 0)
    if stack <= 0:
        return 0
    return C.BURN_BASE_DPS + stack * C.BURN_DPS_PER_STACK

def get_burn_duration_sec():
    """获取燃烧持续时间（秒）"""
    if not game_state:
        return 0
    p = game_state.player
    stack = getattr(p, "bullet_burn_stack",0)
    if stack <=0:
        return 0
    return C.BURN_BASE_DURATION + stack * C.BURN_DUR_PER_STACK

def get_chain_lightning_info(p):
    """返回当前层数对应的 半径，伤害。stack=0返回0，关闭闪电效果"""
    stack = getattr(p, "chain_stack", 0)
    if stack <= 0:
        # 没有闪电强化，半径伤害全部返回0，直接关闭全部逻辑
        return 0, 0
    r = C.CHAIN_LIGHTNING_BASE_RADIUS + stack * C.CHAIN_LIGHTNING_RADIUS_PER_STACK
    dmg = C.CHAIN_LIGHTNING_BASE_DAMAGE + stack * C.CHAIN_LIGHTNING_DMG_PER_STACK
    return r, dmg

def get_missile_shunt_multipliers(p):
    """返回导弹伤害倍率 (玩家受伤倍率，敌人受伤倍率)"""
    stack = getattr(p, "missile_shunt_stack", 0)
    if stack <= 0:
        return 1.0, 1.0
    p_mult = 1.0 - stack * C.MISSILE_SHUNT_PLAYER_DAMAGE_REDUCE_PER_STACK
    e_mult = 1.0 + stack * C.MISSILE_SHUNT_ENEMY_DAMAGE_BONUS_PER_STACK
    # 玩家保留下限保护，敌人不设置上限，可以无限增长
    p_mult = max(p_mult, C.MISSILE_SHUNT_PLAYER_MIN_MULT)
    return p_mult, e_mult

def get_bombardment_damage_mult(p):
    """获取强化轰炸伤害倍率（敌我双方共用）。无层数时返回 1.0。"""
    stack = getattr(p, 'bombardment_stack', 0)
    if stack <= 0:
        return 1.0
    return 1.0 + stack * C.BOMBARDMENT_DMG_MULT_PER_STACK

def get_effective_missile_spacing():
    """获取有效导弹轰炸间隔（帧）。强化轰炸会缩短间隔，下限 180 帧（3 秒）。"""
    if game_state is None:
        return C.MISSILE_MIN_SPACING
    stack = getattr(game_state.player, 'bombardment_stack', 0)
    if stack <= 0:
        return C.MISSILE_MIN_SPACING
    mult = max(C.BOMBARDMENT_SPACING_MULT_MIN,
               1.0 - stack * C.BOMBARDMENT_SPACING_MULT_PER_STACK)
    return max(C.BOMBARDMENT_SPACING_FLOOR, int(C.MISSILE_MIN_SPACING * mult))

def get_effective_missile_count_range():
    """
    获取有效轰炸圈数范围 (min, max)。
    强化轰炸每层使 min/max 各 +MISSILE_COUNT_PER_STACK，两者最终封顶于 MISSILE_COUNT_CAP。
    无强化时回退到原始 (C.MISSILE_COUNT_MIN, C.MISSILE_COUNT_MAX)。
    """
    if game_state is None:
        return C.MISSILE_COUNT_MIN, C.MISSILE_COUNT_MAX
    stack = getattr(game_state.player, 'bombardment_stack', 0)
    cap = C.MISSILE_COUNT_CAP
    add = stack * C.MISSILE_COUNT_PER_STACK
    lo = min(C.MISSILE_COUNT_MIN + add, cap)
    hi = min(C.MISSILE_COUNT_MAX + add, cap)
    if lo > hi:
        lo = hi
    return lo, hi

def get_counter_strike_stack(p):
    """获取反击冲击层数，0代表无效果"""
    return getattr(p, "counter_strike_stack", 0)

def get_lifesteal_heal(p):
    """获取击杀单个敌人的回血量，0=无吸血效果"""
    stack = getattr(p, "lifesteal_stack",0)
    if stack <=0:
        return 0
    return C.LIFESTEAL_BASE_HEAL + stack * C.LIFESTEAL_PER_STACK

def get_full_hp_bonus_info(p):
    """满盈之力：返回(是否满血,额外伤害)，非满血返回0加成"""
    stack = getattr(p, "full_hp_power_stack",0)
    if stack <= 0:
        return False, 0
    max_hp = get_effective_max_dur()
    is_full = (p.dur >= max_hp)
    bonus = stack * C.FULL_HP_BONUS_DMG_PER_STACK if is_full else 0
    return is_full, bonus

def get_bullet_pierce(p):
    """获取子弹穿透剩余次数，0无穿透"""
    return getattr(p, "pierce_stack",0)

def get_nearest_enemy_to_player():
    """返回距玩家最近的存活敌人（dict），没有则返回 None。供自动瞄准使用。"""
    if game_state is None or not game_state.enemies:
        return None
    p = game_state.player
    nearest = None
    best_d_sq = float('inf')
    for e in game_state.enemies:
        if not e['alive']:
            continue
        dx = e['x'] - p.x
        dy = e['y'] - p.y
        d_sq = dx * dx + dy * dy
        if d_sq < best_d_sq:
            best_d_sq = d_sq
            nearest = e
    return nearest

def get_overload_reaction_stack(p):
    """获取超载反应强化层数（实际 0 或 1，因为金色只能获取一次）"""
    return getattr(p, 'overload_reaction_stack', 0)

def get_overload_damage_mult(p):
    """
    计算超载反应倍率：基于玩家闪电层数 + 燃烧层数。
    公式：BASE + chain_stack × CHAIN_BONUS + burn_stack × BURN_BONUS
    未获取超载反应时返回 1.0（无加成）。
    """
    if getattr(p, 'overload_reaction_stack', 0) <= 0:
        return 1.0
    chain = getattr(p, 'chain_stack', 0)
    burn = getattr(p, 'bullet_burn_stack', 0)
    return (C.OVERLOAD_BASE_MULT
            + chain * C.OVERLOAD_CHAIN_BONUS
            + burn * C.OVERLOAD_BURN_BONUS)

def is_bombardment_mode_active(p):
    """是否已拥有轰炸协议强化"""
    return getattr(p, 'bombardment_mode_stack', 0) > 0

def get_bloodlust_damage_mult(p):
    """
    血怒伤害乘数：1.0 = 无增幅，2.0 = +100%。
    未获取血怒时返回 1.0。
    满血 → 1+BASE；HP <= TRIGGER_RATIO → 1+MAX；中间线性插值。
    """
    if getattr(p, 'bloodlust_stack', 0) <= 0:
        return 1.0
    max_dur = get_effective_max_dur()
    if max_dur <= 0:
        return 1.0 + C.BLOODLUST_MAX_MULT
    hp_ratio = max(0.0, min(1.0, p.dur / max_dur))
    trigger = C.BLOODLUST_TRIGGER_RATIO
    if hp_ratio <= trigger:
        bonus = C.BLOODLUST_MAX_MULT
    else:
        t = (1.0 - hp_ratio) / (1.0 - trigger)     # HP 从 1.0 → trigger 时 t 从 0 → 1
        bonus = C.BLOODLUST_BASE_MULT + t * (C.BLOODLUST_MAX_MULT - C.BLOODLUST_BASE_MULT)
    return 1.0 + bonus

def get_death_ring_stack(p):
    """获取死亡回响强化层数（0 或 1）"""
    return getattr(p, 'death_ring_stack', 0)


def is_upgrade_reached_max(p, key):
    """判断该强化是否已经达到上限，True=已满，卡牌池过滤"""
    if key == "fire_rate":
        # fire_rate_bonus最大 -16
        return p.fire_rate_bonus <= -16
    elif key == "fuel_save":
        return p.fuel_save_bonus >= 90
    elif key == "move_spd":
        return p.move_spd_bonus >= 4.0
    elif key == "smaller_player":
        return p.player_size_bonus <= -16
    elif key == "slow_enemy_bullets":
        return p.enemy_bullet_slow_bonus >= 2.0
    elif key == "blood_oath":
        # 有进行中的契约时，卡池不显示（"未完成前不再出现"）
        return getattr(p, 'blood_oath_pending', False)
    elif key == "overload_reaction":
        # 金色强化：只能获取一次
        return getattr(p, 'overload_reaction_stack', 0) >= 1
    elif key == "bombardment_mode":
        # 金色强化：只能获取一次
        return getattr(p, 'bombardment_mode_stack', 0) >= 1
    elif key == "volley_protocol":
        # 金色强化：只能获取一次
        return getattr(p, 'volley_protocol_stack', 0) >= 1
    elif key == "bloodlust":
        # 金色强化：只能获取一次
        return getattr(p, 'bloodlust_stack', 0) >= 1
    elif key == "shield_charge":
        # 金色强化：只能获取一次
        return getattr(p, 'shield_charge_stack', 0) >= 1
    elif key == "revive":
        # 金色强化：只能获取一次（无论是否已使用）
        return getattr(p, 'revive_stack', 0) >= 1
    elif key == "death_ring":
        # 金色强化：只能获取一次
        return getattr(p, 'death_ring_stack', 0) >= 1
    elif key == "fire_breath":
        # 金色强化：只能获取一次
        return getattr(p, 'fire_breath_stack', 0) >= 1
    # 其余强化无上限，永远允许出现卡牌
    return False




# ─── 卡牌选择界面 ────────────────────────────────────────
_CARD_W, _CARD_H = 260, 260
_CARD_SPACING = 300
_CARD_Y = C.H - _CARD_H - 30


def draw_card(surf, card, hover_idx, card_idx):
    """绘制单张卡牌"""
    import ui
    ui._ensure_fonts()
    _font_small = ui._font
    _font_big = ui._fontb

    x = (C.W - _CARD_SPACING * 3) // 2 + card_idx * _CARD_SPACING + 20
    y = _CARD_Y
    is_hover = hover_idx == card_idx

    # =====品质颜色=====
    if card.quality == C.UPGRADE_QUALITY_GOLD:
        # 金色传说品质
        if is_hover:
            border_col = (255, 240, 140)
            bg_col = (60, 45, 15)
        else:
            border_col = (230, 180, 50)
            bg_col = (42, 30, 8)
    elif card.quality == C.UPGRADE_QUALITY_EPIC:
        # 紫色史诗品质
        if is_hover:
            border_col = (200, 100, 255)
            bg_col = (35, 20, 50)
        else:
            border_col = (140, 60, 200)
            bg_col = (22, 12, 35)
    elif card.quality == C.UPGRADE_QUALITY_RARE:
        # 蓝色高级品质
        if is_hover:
            border_col = (100, 200, 255)
            bg_col = (20, 40, 60)
        else:
            border_col = (60, 140, 220)
            bg_col = (12, 25, 45)
    else:
        # 绿色普通品质
        if is_hover:
            border_col = (255, 220, 50)
            bg_col = (30, 55, 30)
        else:
            border_col = (100, 130, 170)
            bg_col = (20, 40, 20)

    # 卡牌背景
    pygame.draw.rect(surf, bg_col, (x, y, _CARD_W, _CARD_H), border_radius=8)
    pygame.draw.rect(surf, border_col, (x, y, _CARD_W, _CARD_H), 2, border_radius=8)
    # 序号标签
    order_surf = _font_small.render(str(card.order), True, (255, 240, 150))
    surf.blit(order_surf, (x + 8, y + 8))
    # 图标
    icon_surf = _font_big.render(card.icon, True, (255, 220, 100))
    surf.blit(icon_surf, (x + _CARD_W // 2 - icon_surf.get_width() // 2, y + 15))
    # 名称
    name_surf = _font_small.render(card.name, True, (255, 255, 255))
    surf.blit(name_surf, (x + _CARD_W // 2 - name_surf.get_width() // 2, y + 55))
    # 描述文字：自动折行 + 支持 **...** 标红
    desc_lines = _wrap_text_with_highlight(_font_small, card.desc, _CARD_W - 20)
    desc_y = y + 90
    for segs in desc_lines:
        cur_x = x + 10
        for seg_text, is_hl in segs:
            col = (255, 90, 90) if is_hl else (180, 200, 180)
            seg_surf = _font_small.render(seg_text, True, col)
            surf.blit(seg_surf, (cur_x, desc_y))
            cur_x += seg_surf.get_width()
        desc_y += 22
    # 提示
    hint_surf = _font_small.render('点击选择', True, (120, 140, 120))
    surf.blit(hint_surf, (x + _CARD_W // 2 - hint_surf.get_width() // 2, y + _CARD_H - 30))


def show_card_selection(clock):
    """显示卡牌选择界面（阻塞式）"""
    import ui
    ui._ensure_fonts()
    available = get_available_upgrades()
    # 兜底保护
    if len(available) <= 0:
        available = list(ALL_UPGRADES)

    cards = []
    # 生成3张key互不重复的卡牌
    while len(cards) < 3:
        r = random.random()
        # 预先取出各类可用列表（从高到低）
        gold_list   = [u for u in available if u.quality == C.UPGRADE_QUALITY_GOLD]
        epic_list   = [u for u in available if u.quality == C.UPGRADE_QUALITY_EPIC]
        rare_list   = [u for u in available if u.quality == C.UPGRADE_QUALITY_RARE]
        common_list = [u for u in available if u.quality == C.UPGRADE_QUALITY_COMMON]

        selected_pool = None
        if r < C.UPGRADE_GOLD_CHANCE:
            selected_pool = gold_list
        elif r < C.UPGRADE_GOLD_CHANCE + C.UPGRADE_EPIC_CHANCE:
            selected_pool = epic_list
        elif r < C.UPGRADE_GOLD_CHANCE + C.UPGRADE_EPIC_CHANCE + C.UPGRADE_RARE_CHANCE:
            selected_pool = rare_list
        else:
            selected_pool = common_list

        # ==========降级兜底==========（金色→紫→蓝→绿）
        if not selected_pool:
            if selected_pool is gold_list:
                selected_pool = epic_list
            if not selected_pool:
                selected_pool = rare_list
            if not selected_pool:
                selected_pool = common_list

        pick = random.choice(selected_pool)

        if not any(c.key == pick.key for c in cards):
            cards.append(pick)

    hover_idx = -1
    while True:
        # 清屏并绘制基础画面
        import assets
        bg = assets.BACKGROUND_IMG
        if bg:
            game_state.screen.blit(bg, (0, 0))
        else:
            game_state.screen.fill(C.C_SEA)
        # 绘制"选择强化"标题
        import ui
        ui._ensure_fonts()
        title = ui._fontb.render('选择一项强化', True, (255, 220, 100))
        game_state.screen.blit(title, (C.W // 2 - title.get_width() // 2, 30))
        # 绘制3张卡牌
        for i, card in enumerate(cards):
            draw_card(game_state.screen, card, hover_idx, i)
        pygame.display.flip()
        clock.tick(C.FPS)
        # 处理事件
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); __import__('sys').exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = pygame.mouse.get_pos()
                for i, card in enumerate(cards):
                    x = (C.W - _CARD_SPACING * 3) // 2 + i * _CARD_SPACING + 20
                    y = _CARD_Y
                    rect = pygame.Rect(x, y, _CARD_W, _CARD_H)
                    if rect.collidepoint(pos):
                        # 应用升级效果（通过新增的 apply_upgrade 记录计数）
                        apply_upgrade(game_state.player, card)
                        return  # 返回继续游戏
            if ev.type == pygame.MOUSEMOTION:
                pos = pygame.mouse.get_pos()
                hover_idx = -1
                for i, card in enumerate(cards):
                    x = (C.W - _CARD_SPACING * 3) // 2 + i * _CARD_SPACING + 20
                    y = _CARD_Y
                    rect = pygame.Rect(x, y, _CARD_W, _CARD_H)
                    if rect.collidepoint(pos):
                        hover_idx = i
                        break

