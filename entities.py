"""
海上军舰 - 游戏实体类
包含：粒子、爆炸动画、子弹、道具、玩家、敌人
所有实体通过 game_state（由 game.py 注入）访问游戏全局数据。
"""
import os
import math
import random
import pygame
import constants as C
import assets
from utils import get_resource_path
import ui
import upgrades as ug

game_state = None

# ─── 导弹轰炸 ───────────────────────────────────────────────
class MissileStrike:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = C.MISSILE_RADIUS
        self.state = 'countdown'
        self.timer = C.MISSILE_COUNTDOWN
        self.pulse = 0
        self.alive = True
        self.frame = 0
        r = self.radius + 10
        self._area = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(self._area, (255, 50, 50, 60), (r, r), self.radius)

    def update(self):
        self.timer -= 1
        if self.state == 'countdown':
            self.pulse += 0.15
            if self.timer <= 0:
                self.state = 'explode'
                self.frame = 0
                self.timer = C.MISSILE_EXPLODE_FRAMES
        elif self.state == 'explode':
            self.frame += 1
            if self.timer <= 0:
                self.state = 'done'
                self.alive = False

    def draw(self, surf):
        ui._ensure_fonts()
        if self.state == 'done' or not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        if self.state == 'countdown':
            pulse = math.sin(self.pulse) * 8
            pr = int(r + pulse)
            surf.blit(self._area, pygame.Rect(cx - pr, cy - pr, pr * 2, pr * 2))
            pygame.draw.circle(surf, (255, 60, 60), (cx, cy), pr, 2)
            secs = max(1, self.timer // 60)
            if ui._fontm is not None:
                t = ui._fontm.render(str(secs), True, (255, 80, 80))
                surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))
        elif self.state == 'explode':
            boom_frame = (self.frame // 15) % 6
            # 原来 scale = (r * 2.5) / max(...) → 目标直径 = r * 2.5
            diameter = int(r * 2.5)
            img = assets.get_scaled_boom(diameter, boom_frame)
            if img is not None:
                rect = img.get_rect(center=(cx, cy))
                surf.blit(img, rect)
            # 红色透明圈
            surf.blit(self._area, pygame.Rect(cx - r, cy - r, r * 2, r * 2))
            if self.timer % 10 == 0 and assets.SOUND_BOOM:
                assets.SOUND_BOOM.play()


# ─── 粒子 ───────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, vx, vy, life, col, sz=3):
        """粒子：撞击/拾取效果，颜色随寿命渐变为白色"""
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.ml = life
        self.col = col
        self.sz = sz

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.vx *= 0.96; self.vy *= 0.96
        self.life -= 1

    def draw(self, surf):
        if self.life <= 0:
            return
        a = self.life / self.ml
        c = tuple(int(v * a + 255 * (1 - a)) for v in self.col)
        pygame.draw.circle(surf, c, (int(self.x), int(self.y)), max(1, int(self.sz * a)))


# ─── 爆炸动画 ───────────────────────────────────────────
class Boom:
    FRAME_COUNT = 6
    TICKS_PER_FRAME = 10

    def __init__(self, x, y, size):
        self.x, self.y = x, y
        self.max_r = int(size * 5)
        self.r_step = max(1, self.max_r // Boom.FRAME_COUNT)
        self.frame = 0
        self.tick = 0
        self.alive = True
        # 不再加载/持有原始图，改为按帧实时查缓存

    def update(self):
        self.tick += 1
        if self.tick >= Boom.TICKS_PER_FRAME:
            self.tick = 0
            self.frame += 1
        if self.frame >= Boom.FRAME_COUNT:
            self.alive = False

    def draw(self, surf):
        if not self.alive or self.frame >= Boom.FRAME_COUNT:
            return
        # 该帧的目标半径，与原来逻辑一致
        r = min(self.max_r, (self.frame + 1) * self.r_step)
        img = assets.get_scaled_boom(r * 2, self.frame)
        if img is None:
            return
        rect = img.get_rect(center=(int(self.x), int(self.y)))
        surf.blit(img, rect)


# ─── 子弹 ───────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, angle, speed, dmg, is_player=True, sz=None):
        """子弹：玩家或敌人发射，超出屏幕或超时后失效"""
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.dmg = dmg
        self.is_player = is_player
        self.r = sz if sz is not None else (5 if is_player else 4)
        self.life = 200
        self.alive = True
        self.pierce = 0
        # 无限穿透：True 时命中敌人不销毁子弹；hit_ids 记录已命中 uid，防重复伤害
        self.infinite_pierce = False
        self.hit_ids = set()
        # 死亡回响的环形弹幕（用于避免链式生成）
        self.is_ring_bullet = False

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.life -= 1
        if self.life <= 0 or self.x < -20 or self.x > C.W + 20 or self.y < -20 or self.y > C.H + 20:
            self.alive = False

    def draw(self, surf):
        color = C.C_BULLET if self.is_player else C.C_ENEMY_B
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), self.r)


# ─── 道具 ───────────────────────────────────────────────
class Drop:
    """掉落道具：燃料/回血/强化/护盾/射速提升/信号干扰，使用贴图绘制"""
    TYPES = ('fuel', 'repair', 'upgrade', 'shield', 'fire_rate', 'jamming')
    COLS  = {
        'fuel': C.C_FUEL, 'repair': C.C_REPAIR, 'upgrade': C.C_UPGRADE,
        'shield': C.C_SHIELD, 'fire_rate': C.C_FIRE_RATE, 'jamming': C.C_JAMMING,
    }
    IMG_MAP = {
        'fuel': 'DROP_IMG_FUEL', 'repair': 'DROP_IMG_RECOVER',
        'upgrade': 'DROP_IMG_STRENGTHEN',
        'shield': 'DROP_IMG_SHIELD',
        'fire_rate': 'DROP_IMG_FIRE_RATE',
        'jamming': 'DROP_IMG_JAMMING',
    }

    def __init__(self, x, y, tp):
        """道具：燃料/修复/强化，浮动画效果"""
        self.x, self.y, self.tp = x, y, tp
        self.alive = True
        self.t = random.uniform(0, 6.28)
        self.r = 12   # 道具半径（适配贴图）

    def update(self):
        self.t += 0.07

    def draw(self, surf):
        by = math.sin(self.t) * 3
        img_attr = self.IMG_MAP.get(self.tp)
        img = getattr(assets, img_attr, None) if img_attr else None
        if img is not None:
            rect = img.get_rect(center=(int(self.x), int(self.y + by)))
            surf.blit(img, rect)
        else:
            # 贴图未加载时回退到彩色圆形
            color = self.COLS.get(self.tp, C.C_WHITE)
            pygame.draw.circle(surf, color, (int(self.x), int(self.y + by)), self.r)
            pygame.draw.circle(surf, C.C_WHITE, (int(self.x), int(self.y + by)), self.r, 2)


# ─── 玩家 ───────────────────────────────────────────────
class Player:
    def __init__(self):
        """玩家：WASD/方向键移动，空格冲刺，鼠标瞄准射击"""
        self.x, self.y = C.W // 2, C.H // 2
        self.r, self.angle = 36, -math.pi / 2
        self.fuel = C.MAX_FUEL
        self.dur = C.MAX_DUR
        self.kills = 0
        self.score = 0
        self.cd = 0
        self.bdmg = 0
        self.bcount = 1
        self.sprinting = False
        self.invincible = 0  # 无敌帧计时器
        self.strengthen_timer = 0  # 强化剩余时间
        self.strengthen_bcount = 0  # 强化额外弹数
        # 新增强化道具状态
        self.shield_active = False      # 护盾是否激活（一次性）
        self.fire_rate_timer = 0        # 射速提升剩余时间
        self.jamming_timer = 0          # 信号干扰剩余时间
        # 卡牌强化属性
        self.max_dur_bonus = 0          # 额外耐久上限
        self.dur_bonus = 0              # 当前耐久加成
        self.dmg_bonus = 0              # 额外伤害
        self.fire_rate_bonus = 0        # 射击间隔减少（负数=更快）
        self.fuel_save_bonus = 0        # 燃料节省百分比
        self.move_spd_bonus = 0.0       # 移动速度加成
        self.armor_bonus = 0            # 伤害减免
        self.bullet_size_bonus = 0      # 子弹尺寸加成
        self.player_size_bonus = 0      # 玩家体型变化
        self.enemy_bullet_slow_bonus = 0.0  # 敌方子弹减速
        self.heavy_armor_stack = 0      # 重型装甲
        self.heavy_armor_spd_penalty = 0.0
        self.collision_damage_stack = 0 # 钢铁碰撞强化
        self.auto_aim_stack = 0         # 自动瞄准强化
        self.blood_pact_stack = 0       # 血祭强化
        # 杀戮契约强化
        self.blood_oath_pending = False   # 是否有进行中的契约
        self.blood_oath_kills = 0         # 当前契约的击杀进度
        self.blood_oath_completed = 0     # 已完成契约层数
        self.bombardment_mode_stack = 0   # 轰炸协议强化
        self.volley_protocol_stack = 0    # 齐射协议强化
        self.bloodlust_stack = 0          # 血怒强化
        # 静海协议强化
        self.shield_charge_stack = 0     # 层数（0/1）
        self.shield_charge_timer = 0     # 未受伤累计计时器（帧）
        self.revive_stack = 0          # 不屈意志强化层数（0/1）
        self.revive_used = False       # 本局是否已使用过复活
        self.death_ring_stack = 0       # 死亡回响强化层数（0/1）
        # 烈焰喷射强化
        self.fire_breath_stack = 0            # 层数（0/1）
        self.fire_breath_cd = 0               # 冷却剩余帧数
        self.fire_breath_visual_timer = 0     # 视觉火焰持续帧数
        self.fire_breath_vis_angle = 0.0      # 视觉火焰朝向
        self.fire_breath_vis_x = 0.0          # 视觉火焰起始 x
        self.fire_breath_vis_y = 0.0          # 视觉火焰起始 y

    def update(self, keys, mouse_pos):
        dx, dy = 0, 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:   dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:   dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:  dx += 1
        moving = dx != 0 or dy != 0
        self.sprinting = keys[pygame.K_SPACE] and moving
        if moving:
            n = math.hypot(dx, dy)
            # 卡牌强化：移动速度加成
            spd = ug.get_effective_sprint_speed() if self.sprinting else ug.get_effective_speed()
            self.x += dx / n * spd
            self.y += dy / n * spd
            self.angle = math.atan2(dy, dx)
        # 卡牌强化：玩家半径
        self.r = ug.get_effective_player_radius()
        self.x = C.clamp(self.x, self.r, C.W - self.r)
        self.y = C.clamp(self.y, self.r, C.H - self.r)
        # 静海协议：持有护盾时不消耗燃料（含冲刺）
        fuel_free = self.shield_active and self.shield_charge_stack > 0
        if not fuel_free:
            if moving:
                rate = ug.get_effective_fuel_cost('sprint' if self.sprinting else 'normal')
                self.fuel = max(0, self.fuel - rate)
            else:
                self.fuel = max(0, self.fuel - ug.get_effective_fuel_cost('normal'))
        self.cd = max(0, self.cd - 1)
        self.invincible = max(0, self.invincible - 1)
        # 静海协议：未受伤时累计，满帧数获得护盾
        if self.shield_charge_stack > 0:
            if self.shield_active:
                # 已有护盾计时归零
                self.shield_charge_timer = 0
            else:
                self.shield_charge_timer += 1
                if self.shield_charge_timer >= C.SHIELD_CHARGE_FRAMES:
                    # 充能完成：获得护盾 + 蓝色粒子
                    self.shield_active = True
                    self.shield_charge_timer = 0
                    for _ in range(24):
                        ang = random.uniform(0, math.tau)
                        dist = self.r + random.uniform(8, 22)
                        game_state.parts.append(Particle(
                            self.x + math.cos(ang) * dist,
                            self.y + math.sin(ang) * dist,
                            -math.cos(ang) * 2.0,
                            -math.sin(ang) * 2.0,
                            random.randint(20, 30),
                            C.C_SHIELD,
                            random.randint(4, 6)))
        # 强化计时
        if self.strengthen_timer > 0:
            self.strengthen_timer -= 1
            if self.strengthen_timer <= 0:
                self.strengthen_bcount = 0
        # 射速提升计时
        if self.fire_rate_timer > 0:
            self.fire_rate_timer -= 1
        # 信号干扰计时
        if self.jamming_timer > 0:
            self.jamming_timer -= 1
        # 烈焰喷射：冷却计时 + 视觉持续 + 触发
        if self.fire_breath_cd > 0:
            self.fire_breath_cd -= 1
        if self.fire_breath_visual_timer > 0:
            self.fire_breath_visual_timer -= 1
            # 每帧生成几个火焰粒子延续视觉
            for _ in range(8):
                _spawn_fire_breath_particle(
                    self.fire_breath_vis_x,
                    self.fire_breath_vis_y,
                    self.fire_breath_vis_angle)
        if self.fire_breath_stack > 0 and self.fire_breath_cd <= 0:
            # 仅在存在存活敌人时触发（避免空放）
            if any(e['alive'] for e in game_state.enemies):
                _trigger_fire_breath(self)
        # 发射子弹
        if self.cd <= 0:
            # 轰炸协议：不再发射子弹
            if self.bombardment_mode_stack > 0:
                self.cd = ug.get_effective_shoot_interval()
            else:
                mx, my = mouse_pos
                # 自动瞄准：优先锁定最近的存活敌人
                target = None
                if self.auto_aim_stack > 0:
                    target = ug.get_nearest_enemy_to_player()
                if target is not None:
                    base = C.ang((self.x, self.y), (target['x'], target['y']))
                else:
                    base = C.ang((self.x, self.y), (mx, my))
                fire_rate = ug.get_effective_shoot_interval()
                total_bullets = self.bcount + self.strengthen_bcount
                dmg = ug.get_effective_bullet_dmg() + self.bdmg
                pierce_cnt = ug.get_bullet_pierce(self)
                has_infinite = self.volley_protocol_stack > 0
                for i in range(total_bullets):
                    off = (i - (total_bullets - 1) / 2) * C.SPREAD
                    bsize = ug.get_effective_bullet_radius()
                    bullet = Bullet(self.x, self.y, base + off, C.BULLET_SPD, dmg, sz=bsize)
                    bullet.pierce = pierce_cnt
                    bullet.infinite_pierce = has_infinite
                    game_state.bullets.append(bullet)
                self.cd = fire_rate

            # 强化期间每帧生成紫色粒子
            if self.strengthen_timer > 0:
                for _ in range(3):
                    angle = random.uniform(0, math.tau)
                    dist = random.uniform(self.r, self.r + 15)
                    game_state.parts.append(Particle(
                        self.x + math.cos(angle) * dist,
                        self.y + math.sin(angle) * dist,
                        math.cos(angle) * 0.5,
                        math.sin(angle) * 0.5,
                        20,
                        C.C_UPGRADE,
                        4))
            # 射速提升期间每帧生成黄色电弧粒子
            if self.fire_rate_timer > 0:
                for _ in range(3):
                    angle = random.uniform(0, math.tau)
                    dist = random.uniform(self.r + 2, self.r + 18)
                    game_state.parts.append(Particle(
                        self.x + math.cos(angle) * dist,
                        self.y + math.sin(angle) * dist,
                        math.cos(angle) * 1.5 + random.uniform(-0.5, 0.5),
                        math.sin(angle) * 1.5 + random.uniform(-0.5, 0.5),
                        18,
                        C.C_FIRE_RATE,
                        3))

    def hurt(self, dmg):
        """受到攻击时：护盾优先吸收，否则触发无敌帧并播放音效"""
        if self.shield_active:
            self.shield_active = False
            self.shield_charge_timer = 0
            # 护盾破碎特效
            for _ in range(12):
                angle = random.uniform(0, math.tau)
                dist = random.uniform(self.r, self.r + 10)
                game_state.parts.append(Particle(
                    self.x + math.cos(angle) * dist,
                    self.y + math.sin(angle) * dist,
                    math.cos(angle) * 3, math.sin(angle) * 3,
                    25, C.C_SHIELD, 5))
            return  # 护盾吸收伤害，不受伤，不触发反击
        if self.invincible > 0:
            return  # 无敌帧内不受伤害，不触发反击
        # 卡牌强化：伤害减免
        reduction = ug.get_damage_reduction()
        final_dmg = max(1, dmg + reduction)
        self.dur = max(0, self.dur - final_dmg)
        self.shield_charge_timer = 0
        self.invincible = C.INVINCIBLE_FRAMES
        if assets.SOUND_HIT:
            assets.SOUND_HIT.play()
        # 反击冲击逻辑
        stack = ug.get_counter_strike_stack(self)
        if stack > 0 and game_state.state == "playing":
            for _ in range(stack):
                alive_enemies = [e for e in game_state.enemies if e['alive']]
                if not alive_enemies:
                    break
                target = random.choice(alive_enemies)
                hurt_enemy(target, C.COUNTER_STRIKE_DAMAGE)
                # 生成白色连线特效：玩家 → 目标敌人，复用闪电渲染逻辑
                game_state.lightning_lines.append(
                    (self.x, self.y, target['x'], target['y'], 8)
                )

    def pickup(self, drop):
        if drop.tp == 'fuel':
            self.fuel = min(C.MAX_FUEL, self.fuel + C.DROP_FUEL)
            self.score += C.SCORE_FUEL
        elif drop.tp == 'repair':
            max_dur = ug.get_effective_max_dur()
            self.dur = min(max_dur, self.dur + C.DROP_REPAIR)
            self.score += C.SCORE_REPAIR
        elif drop.tp == 'upgrade':
            self.strengthen_timer = C.STRENGTHEN_DURATION
            self.strengthen_bcount = 1  # 双发弹药
            self.score += C.SCORE_UPGRADE
        elif drop.tp == 'shield':
            self.shield_active = True
            self.score += C.SCORE_UPGRADE
        elif drop.tp == 'fire_rate':
            self.fire_rate_timer = C.FIRE_RATE_BOOST_DURATION
            self.score += C.SCORE_UPGRADE
        elif drop.tp == 'jamming':
            self.jamming_timer = C.SIGNAL_JAMMING_DURATION
            self.score += C.SCORE_UPGRADE

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        # 绘制护盾（蓝色透明球壳，在玩家贴图下方）
        if self.shield_active:
            shield_r = int(self.r + 14)
            shield_surf = pygame.Surface((shield_r * 2, shield_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(shield_surf, (*C.C_SHIELD[:3], 80), (shield_r, shield_r), shield_r)
            pygame.draw.circle(shield_surf, (*C.C_SHIELD[:3], 180), (shield_r, shield_r), shield_r, 2)
            surf.blit(shield_surf, (cx - shield_r, cy - shield_r))

        angle_deg = math.degrees(self.angle)
        if assets.PLAYER_IMG is not None:
            scale = ug.get_player_scale_bonus()
            rotated = pygame.transform.rotozoom(assets.PLAYER_IMG, -angle_deg, scale)
            if self.invincible > 0 and game_state.frame % 4 < 2:
                rotated.set_alpha(128)
            rect = rotated.get_rect(center=(cx, cy))
            surf.blit(rotated, rect)
        else:
            # 兜底多边形
            color = C.C_PLAYER_D if self.dur < C.MAX_DUR * 0.3 else C.C_PLAYER
            s = self.r / 36.0
            pts = [(cx, cy - int(24 * s)),
                   (cx + int(18 * s), cy),
                   (cx, cy + int(14 * s)),
                   (cx - int(18 * s), cy)]
            pygame.draw.polygon(surf, color, pts)
            pygame.draw.polygon(surf, (30, 40, 50), pts, 2)

        # DEBUG模式绘制红色碰撞圈！用来肉眼看缩小效果
        if C.DEBUG:
            pygame.draw.circle(surf, (255, 40, 40), (cx, cy), self.r, 2)

# ─── 敌人唯一 ID 计数器（用于子弹无限穿透去重）────────────
_enemy_uid_counter = 0

def _next_enemy_uid():
    global _enemy_uid_counter
    _enemy_uid_counter += 1
    return _enemy_uid_counter

# ─── 敌人 ───────────────────────────────────────────────
def mk_enemy(x, y, etype, wave, story_mode=False, story_battle=0):
    """创建敌人字典，敌舰 HP 随波次递增；故事模式额外加成"""
    inf = C.ETYPES[etype]
    if story_mode:
        # 故事模式：保留原线性逻辑 + 故事战加成
        wave_mult = 1 + wave * 0.12 + C.STORY_HP_MULT[story_battle]
    else:
        # 生存模式：阶段内线性增长 + 每 10 波额外跃升
        stage = (wave - 1) // C.WAVE_STAGE_LENGTH
        wave_mult = 1.0 + wave * C.WAVE_HP_PER_WAVE + stage * C.WAVE_HP_STAGE_BONUS
    hp = int(inf['hp'] * wave_mult)
    return {
        'x': x, 'y': y, 'type': etype,
        'hp': hp, 'mhp': hp,
        'spd': inf['spd'], 'dmg': inf['dmg'], 'rate': inf['rate'],
        'sz': inf['sz'], 'bsz': inf['bsz'], 'bspd': inf['bspd'],
        'col': inf['col'],
        'angle': 0, 'cd': random.randint(0, inf['rate']), 'alive': True,
        # 燃烧状态
        'burn_timer': 0.0,      # 燃烧剩余时间（秒）
        'burn_tick_acc':0.0,    # tick累积计时器
        # 唯一 ID（供无限穿透子弹去重）
        'uid': _next_enemy_uid(),
    }



def update_enemy(e, player):
    """更新单个敌人：朝向玩家移动，进入 300px 范围后发射子弹，接触造成伤害"""
    if not e['alive']:
        return
    # 信号干扰减速
    jam = game_state.player.jamming_timer > 0
    spd_mult = C.JAMMING_SPEED_MULT if jam else 1.0
    a = C.ang((e['x'], e['y']), (player.x, player.y))
    e['angle'] = a
    e['x'] += math.cos(a) * e['spd'] * spd_mult
    e['y'] += math.sin(a) * e['spd'] * spd_mult
    e['x'] = C.clamp(e['x'], e['sz'], C.W - e['sz'])
    e['y'] = C.clamp(e['y'], e['sz'], C.H - e['sz'])
    d = C.dst((e['x'], e['y']), (player.x, player.y))
    if d < 300:
        e['cd'] -= 1
        if e['cd'] <= 0:
            base_bspd = e['bspd'] * spd_mult
            bspd = ug.get_effective_enemy_bullet_speed(base_bspd)
            game_state.enemy_bullets.append(Bullet(
                e['x'], e['y'], a, bspd, e['dmg'], False, e['bsz']))
            e['cd'] = e['rate']
    if d < e['sz'] + player.r:
        prev_inv = player.invincible
        player.hurt(e['dmg'] * 0.2)
        if prev_inv <= 0 and player.invincible > 0 and player.collision_damage_stack > 0:
            cdm = C.COLLISION_DAMAGE_PER_STACK * player.collision_damage_stack
            for other in game_state.enemies:
                if not other['alive']:
                    continue
                if C.dst((other['x'], other['y']), (player.x, player.y)) < other['sz'] + player.r:
                    hurt_enemy(other, cdm)
                    # 紫红色撞击粒子
                    for _ in range(6):
                        angle = random.uniform(0, math.tau)
                        dist = random.uniform(other['sz'] * 0.4, other['sz'] * 1.3)
                        px = other['x'] + math.cos(angle) * dist
                        py = other['y'] + math.sin(angle) * dist
                        game_state.parts.append(Particle(
                            px, py,
                            random.uniform(-2.5, 2.5),
                            random.uniform(-2.5, 2.5),
                            random.randint(12, 22),
                            (200, 90, 220),
                            4))
def _spawn_death_ring(x, y):
    """在 (x, y) 位置生成一圈死亡回响弹幕（玩家阵营）"""
    if game_state is None:
        return
    p = game_state.player
    base_dmg = ug.get_effective_bullet_dmg()
    ring_dmg = max(1, int(base_dmg * C.DEATH_RING_DMG_RATIO))
    n = C.DEATH_RING_BULLET_COUNT
    for i in range(n):
        ang = math.tau * i / n
        b = Bullet(
            x, y, ang,
            C.DEATH_RING_BULLET_SPEED,
            ring_dmg,
            is_player=True,
            sz=C.DEATH_RING_BULLET_RADIUS)
        b.is_ring_bullet = True
        game_state.bullets.append(b)
    # 金色爆发粒子
    for _ in range(16):
        ang = random.uniform(0, math.tau)
        spd = random.uniform(2.0, 4.5)
        game_state.parts.append(Particle(
            x, y,
            math.cos(ang) * spd,
            math.sin(ang) * spd,
            random.randint(18, 30),
            (255, 220, 100),
            4))

def _spawn_fire_breath_particle(origin_x, origin_y, angle):
    """在扇形内随机位置生成一个火焰视觉粒子"""
    if game_state is None:
        return
    half_rad = math.radians(C.FIRE_BREATH_HALF_ANGLE)
    ang = angle + random.uniform(-half_rad, half_rad)
    dist = random.uniform(20, C.FIRE_BREATH_RANGE)
    px = origin_x + math.cos(ang) * dist
    py = origin_y + math.sin(ang) * dist
    game_state.parts.append(Particle(
        px, py,
        math.cos(ang) * random.uniform(0.5, 2.0),
        math.sin(ang) * random.uniform(0.5, 2.0),
        random.randint(12, 20),
        random.choice([(255, 120, 40), (255, 180, 80), (255, 220, 120)]),
        random.randint(3, 6)))


def _trigger_fire_breath(p):
    """触发烈焰喷射：对扇形内所有存活敌人造成固定伤害 + 爆发火焰粒子"""
    if game_state is None:
        return
    p.fire_breath_cd = C.FIRE_BREATH_COOLDOWN
    p.fire_breath_visual_timer = C.FIRE_BREATH_VISUAL_FRAMES
    p.fire_breath_vis_angle = p.angle
    p.fire_breath_vis_x = p.x
    p.fire_breath_vis_y = p.y

    half_rad = math.radians(C.FIRE_BREATH_HALF_ANGLE)
    # ===== 伤害判定：扇形内所有敌人 =====
    for e in game_state.enemies:
        if not e['alive']:
            continue
        dx = e['x'] - p.x
        dy = e['y'] - p.y
        dist = math.hypot(dx, dy)
        if dist > C.FIRE_BREATH_RANGE + e['sz']:
            continue
        enemy_ang = math.atan2(dy, dx)
        diff = enemy_ang - p.angle
        # 规范化到 [-pi, pi]
        while diff > math.pi:
            diff -= math.tau
        while diff < -math.pi:
            diff += math.tau
        if abs(diff) <= half_rad:
            hurt_enemy(e, C.FIRE_BREATH_DAMAGE, allow_death_ring=True)

    # ===== 爆发粒子：扇形内大范围喷涌 =====
    for _ in range(50):
        ang = p.angle + random.uniform(-half_rad, half_rad)
        dist = random.uniform(20, C.FIRE_BREATH_RANGE)
        px = p.x + math.cos(ang) * dist
        py = p.y + math.sin(ang) * dist
        game_state.parts.append(Particle(
            px, py,
            math.cos(ang) * random.uniform(1.5, 3.5),
            math.sin(ang) * random.uniform(1.5, 3.5),
            random.randint(18, 32),
            random.choice([(255, 100, 30), (255, 180, 60), (255, 220, 100)]),
            random.randint(5, 8)))

def hurt_enemy(e, dmg, allow_death_ring=True):
    """对敌人造成伤害，死亡时播放爆炸动画、音效并生成掉落"""
    e['hp'] -= dmg
    if e['hp'] <= 0:
        e['alive'] = False
        game_state.player.kills += 1
        # 杀戮契约进度推进
        ug.process_blood_oath_kill()
        # 死亡回响：非环形弹幕击杀才生成环形弹幕
        if (allow_death_ring and getattr(game_state.player, 'death_ring_stack', 0) > 0):
            _spawn_death_ring(e['x'], e['y'])
        # 浴血击杀回血逻辑
        heal_val = ug.get_lifesteal_heal(game_state.player)
        if heal_val > 0 and game_state.state == "playing":
            max_hp = ug.get_effective_max_dur()
            game_state.player.dur = min(game_state.player.dur + heal_val, max_hp)
            # 回血红色小粒子特效
            for _ in range(12):
                angle = random.uniform(0, math.tau)
                dist = random.uniform(e['sz'] * 0.3, e['sz'] * 1.1)
                px = e['x'] + math.cos(angle) * dist
                py = e['y'] + math.sin(angle) * dist
                game_state.parts.append(
                    Particle(px, py,
                             (game_state.player.x - px) * 0.08,
                             (game_state.player.y - py) * 0.08,
                             34, (255, 60, 60), 6)
                )

        # 根据敌舰类型给分
        if e['type'] == 'battleship':
            game_state.player.score += C.SCORE_BOSS
        else:
            game_state.player.score += C.SCORE_ENEMY
        # 爆炸动画 + 音效
        game_state.booms.append(Boom(e['x'], e['y'], e['sz']))
        if assets.SOUND_BOOM:
            assets.SOUND_BOOM.play()
        # 掉落
        r = random.random() * 100
        fuel_drop_rate = 25 if e['type'] == 'battleship' else C.DROP_REP_P + C.DROP_UP
        jamming_active = game_state.player.jamming_timer > 0
        # 信号干扰激活时额外概率掉落 jamming
        if jamming_active and r < 12:
            game_state.drops.append(Drop(e['x'], e['y'], 'jamming'))
        # 正常模式四种强化道具掉落（各自独立概率，互不干扰）
        elif r < C.DROP_SHIELD_P:
            game_state.drops.append(Drop(e['x'], e['y'], 'shield'))
        elif r < C.DROP_SHIELD_P + C.DROP_FIRE_RATE_P:
            game_state.drops.append(Drop(e['x'], e['y'], 'fire_rate'))
        elif r < C.DROP_SHIELD_P + C.DROP_FIRE_RATE_P + C.DROP_JAMMING_P:
            game_state.drops.append(Drop(e['x'], e['y'], 'jamming'))
        elif r < C.DROP_SHIELD_P + C.DROP_FIRE_RATE_P + C.DROP_JAMMING_P + C.DROP_UP:
            game_state.drops.append(Drop(e['x'], e['y'], 'upgrade'))
        elif r < C.DROP_SHIELD_P + C.DROP_FIRE_RATE_P + C.DROP_JAMMING_P + C.DROP_UP + C.DROP_REP_P:
            game_state.drops.append(Drop(e['x'], e['y'], 'repair'))
        elif r < fuel_drop_rate:
            game_state.drops.append(Drop(e['x'], e['y'], 'fuel'))
        else:
            game_state.drops.append(Drop(e['x'], e['y'], 'fuel'))


def draw_enemy(e, surf):
    """绘制单个敌人：根据类型加载贴图并旋转，不在视野内时跳过"""
    if not e['alive']:
        return
    cx, cy = int(e['x']), int(e['y'])
    type_to_img = {'scout': assets.ENEMY_IMG_SMALL,
                   'cruiser': assets.ENEMY_IMG_MED,
                   'battleship': assets.ENEMY_IMG_LARGE}
    img = type_to_img.get(e['type'])
    if img is not None:
        angle_deg = math.degrees(e['angle'])
        rotated = pygame.transform.rotozoom(img, -angle_deg, 1.0)
        rect = rotated.get_rect(center=(cx, cy))
        surf.blit(rotated, rect)
    else:
        pts = [(cx + int(math.cos(e['angle'] + i * 2.094) * e['sz']),
                cy + int(math.sin(e['angle'] + i * 2.094) * e['sz'])) for i in range(3)]
        pygame.draw.polygon(surf, e['col'], pts)
        pygame.draw.polygon(surf, (0, 0, 0, 90), pts, 2)
    # 血条
    if e['hp'] < e['mhp']:
        bw, bh = e['sz'] * 2, 4
        hy = cy - e['sz'] - 8
        pygame.draw.rect(surf, (50, 0, 0), (cx - bw // 2, hy, bw, bh))
        pygame.draw.rect(surf, (210, 50, 50),
                         (cx - bw // 2, hy, bw * e['hp'] / e['mhp'], bh))
    # 信号干扰蓝色电弧特效
    if game_state.player.jamming_timer > 0 and game_state.frame % 4 < 2:
        for _ in range(2):
            angle = random.uniform(0, math.tau)
            dist = random.uniform(e['sz'] * 0.5, e['sz'] * 1.2)
            px = cx + math.cos(angle) * dist
            py = cy + math.sin(angle) * dist
            vx = math.cos(angle + 1.5) * 2
            vy = math.sin(angle + 1.5) * 2
            game_state.parts.append(Particle(px, py, vx, vy, 15, C.C_JAMMING, 3))

#   ==========敌人燃烧简单视觉提示==========
    # ==========敌人燃烧视觉提示：纯图形绘制，无任何文字==========
    if e.get('burn_timer', 0) > 0:
        # 敌人头顶位置
        tri_y = cy - e['sz'] - 16
        # 外层大火焰三角（橙红色）
        tri_points_outer = [
            (cx, tri_y - 12),
            (cx - 10, tri_y + 8),
            (cx + 10, tri_y + 8),
        ]
        pygame.draw.polygon(surf, (255, 110, 40), tri_points_outer)
        # 内层小火焰三角（亮黄色）
        tri_points_inner = [
            (cx, tri_y - 6),
            (cx - 5, tri_y + 4),
            (cx + 5, tri_y + 4),
        ]
        pygame.draw.polygon(surf, (255, 180, 30), tri_points_inner)
