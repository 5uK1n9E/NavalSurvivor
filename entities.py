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

game_state = None

# ─── 导弹轰炸 ───────────────────────────────────────────────
class MissileStrike:
    """导弹轰炸区域：红圈倒计时后爆炸"""
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.radius = C.MISSILE_RADIUS
        self.state = 'countdown'  # countdown / explode / done
        self.timer = C.MISSILE_COUNTDOWN
        self.pulse = 0
        self.alive = True
        self.frame = 0
        self.boom_imgs = []
        self._load_booms()
        # 预生成半透明红色区域图片（用于透明覆盖）
        r = self.radius + 10
        self._area = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(self._area, (255, 50, 50, 60), (r, r), self.radius)

    def _load_booms(self):
        """加载boom动画帧"""
        import os
        base = get_resource_path('resource')

        for i in range(1, 7):
            path = os.path.join(base, f'boom{i}.png')
            try:
                self.boom_imgs.append(pygame.image.load(path).convert_alpha())
            except Exception:
                self.boom_imgs.append(None)

    def update(self):
        self.timer -= 1
        self.pulse += 0.15
        if self.state == 'countdown' and self.timer <= 0:
            self.state = 'explode'
            self.frame = 0
            self.timer = C.MISSILE_EXPLODE_FRAMES
        elif self.state == 'explode' and self.timer <= 0:
            self.state = 'done'
            self.alive = False

    def draw(self, surf):
        if self.state == 'done' or not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        r = self.radius
        if self.state == 'countdown':
            # 脉冲动画
            self.pulse += 0.1
            pulse = math.sin(self.pulse) * 8
            pr = int(r + pulse)
            # 透明红色填充圆（可见背景）
            rect = pygame.Rect(cx - pr, cy - pr, pr * 2, pr * 2)
            surf.blit(self._area, rect)
            # 红色边框
            pygame.draw.circle(surf, (255, 60, 60), (cx, cy), pr, 2)
            # 倒计时文字
            secs = max(1, self.timer // 60)
            t = pygame.font.SysFont('microsoftyahei', 22, bold=True).render(str(secs), True, (255, 80, 80))
            surf.blit(t, (cx - t.get_width() // 2, cy - t.get_height() // 2))
        elif self.state == 'explode':
            # 持续播放boom动画 + 红色透明圈
            boom_frame = self.frame // 15
            self.frame += 1
            # 先画boom动画帧（循环播放）
            if len(self.boom_imgs) > 0 and self.boom_imgs[boom_frame % len(self.boom_imgs)] is not None:
                img = self.boom_imgs[boom_frame % len(self.boom_imgs)]
                scale = (r * 2.5) / max(img.get_width(), img.get_height())
                if 0 < scale < 10:
                    img = pygame.transform.smoothscale(
                        img, (int(img.get_width() * scale), int(img.get_height() * scale)))
                rect = img.get_rect(center=(cx, cy))
                surf.blit(img, rect)
            # 持续画红色透明圈（即使boom动画播完也保持视觉）
            rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
            surf.blit(self._area, rect)
            # 爆炸期间持续播放boom音效（每10帧一次）
            if self.timer % 10 == 0:
                if assets.SOUND_BOOM:
                    assets.SOUND_BOOM.play()
            if self.timer <= 0:
                self.state = 'done'
                self.alive = False

    def check_damage(self, entities_list):
        """检查对实体列表的伤害，返回 True 表示造成伤害"""
        if self.state != 'explode':
            return False
        hit = False
        for e in entities_list:
            if not e.get('alive', True):
                continue
            if C.dst((e['x'], e['y']), (self.x, self.y)) < self.radius + e.get('sz', 30):
                e['hp'] -= C.MISSILE_ENEMY_DAMAGE
                if e['hp'] <= 0:
                    e['alive'] = False
                hit = True
        return hit


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
    """敌舰击毁后的爆炸动画，按序播放 boom1~boom6"""
    FRAME_COUNT = 6
    TICKS_PER_FRAME = 10   # 每帧 10 游戏刻，总时长约 1 秒

    def __init__(self, x, y, size):
        """爆炸动画：敌舰击毁后播放 boom1~boom6，半径随帧数扩大"""
        self.x, self.y = x, y
        self.max_r = int(size * 5)       # 爆炸半径 = 舰体尺寸×5
        self.r_step = max(1, self.max_r // Boom.FRAME_COUNT)
        self.frame = 0
        self.tick = 0
        self.alive = True
        self.loaded = []
        self._load_frames()

    def _load_frames(self):
        base = get_resource_path('resource')

        for i in range(1, Boom.FRAME_COUNT + 1):
            path = os.path.join(base, f'boom{i}.png')
            try:
                self.loaded.append(pygame.image.load(path).convert_alpha())
            except Exception:
                self.loaded.append(None)

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
        img = self.loaded[min(self.frame, len(self.loaded) - 1)]
        if img is None:
            return
        r = min(self.max_r, (self.frame + 1) * self.r_step)
        scale = (r * 2) / max(img.get_width(), img.get_height()) if r > 0 else 0
        if 0 < scale < 10:
            img = pygame.transform.smoothscale(
                img, (int(img.get_width() * scale), int(img.get_height() * scale)))
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
        self.brate = C.SHOOT_INT
        self.bdmg = C.BULLET_DMG
        self.bcount = 1
        self.sprinting = False
        self.invincible = 0  # 无敌帧计时器
        self.strengthen_timer = 0  # 强化剩余时间
        self.strengthen_bcount = 0  # 强化额外弹数
        # 新增强化道具状态
        self.shield_active = False      # 护盾是否激活（一次性）
        self.fire_rate_timer = 0        # 射速提升剩余时间
        self.jamming_timer = 0          # 信号干扰剩余时间

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
            spd = C.SPD_SPRINT if self.sprinting else C.SPD
            self.x += dx / n * spd
            self.y += dy / n * spd
            self.angle = math.atan2(dy, dx)
        self.x = C.clamp(self.x, self.r, C.W - self.r)
        self.y = C.clamp(self.y, self.r, C.H - self.r)
        if moving:
            rate = C.FUEL_COST_SPRINT if self.sprinting else C.FUEL_COST * 1.5
            self.fuel = max(0, self.fuel - rate)
        else:
            self.fuel = max(0, self.fuel - C.FUEL_COST)
        self.cd = max(0, self.cd - 1)
        self.invincible = max(0, self.invincible - 1)
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
        # 发射子弹
        if self.cd <= 0:
            mx, my = mouse_pos
            base = C.ang((self.x, self.y), (mx, my))
            # 射速提升：降低射击间隔
            fire_rate = self.brate
            if self.fire_rate_timer > 0:
                fire_rate = max(1, int(self.brate * C.FIRE_RATE_BOOST_MULT))
            total_bullets = self.bcount + self.strengthen_bcount
            for i in range(total_bullets):
                off = (i - (total_bullets - 1) / 2) * C.SPREAD
                game_state.bullets.append(Bullet(self.x, self.y, base + off, C.BULLET_SPD, self.bdmg))
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
            # 护盾破碎特效
            for _ in range(12):
                angle = random.uniform(0, math.tau)
                dist = random.uniform(self.r, self.r + 10)
                game_state.parts.append(Particle(
                    self.x + math.cos(angle) * dist,
                    self.y + math.sin(angle) * dist,
                    math.cos(angle) * 3, math.sin(angle) * 3,
                    25, C.C_SHIELD, 5))
            return  # 护盾吸收伤害，不受伤
        if self.invincible > 0:
            return  # 无敌帧内不受伤害
        self.dur = max(0, self.dur - dmg)
        self.invincible = C.INVINCIBLE_FRAMES
        if assets.SOUND_HIT:
            assets.SOUND_HIT.play()

    def pickup(self, drop):
        if drop.tp == 'fuel':
            self.fuel = min(C.MAX_FUEL, self.fuel + C.DROP_FUEL)
            self.score += C.SCORE_FUEL
        elif drop.tp == 'repair':
            self.dur = min(C.MAX_DUR, self.dur + C.DROP_REPAIR)
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
        # 无敌帧期间玩家贴图虚化（降低 alpha 绘制）
        if self.invincible > 0 and game_state.frame % 4 < 2:
            alpha = 128
            temp_img = assets.PLAYER_IMG.copy() if assets.PLAYER_IMG else None
            if temp_img:
                temp_img.set_alpha(alpha)
                angle_deg = math.degrees(self.angle)
                rotated = pygame.transform.rotozoom(temp_img, -angle_deg, 1.0)
                rect = rotated.get_rect(center=(cx, cy))
                surf.blit(rotated, rect)
            else:
                color = C.C_PLAYER_D if self.dur < C.MAX_DUR * 0.3 else C.C_PLAYER
                pts = [(cx, cy - 24), (cx + 18, cy), (cx, cy + 14), (cx - 18, cy)]
                pygame.draw.polygon(surf, color, pts)
                pygame.draw.polygon(surf, (30, 40, 50), pts, 2)
        elif assets.PLAYER_IMG is not None:
            angle_deg = math.degrees(self.angle)
            rotated = pygame.transform.rotozoom(assets.PLAYER_IMG, -angle_deg, 1.0)
            rect = rotated.get_rect(center=(cx, cy))
            surf.blit(rotated, rect)
        else:
            color = C.C_PLAYER_D if self.dur < C.MAX_DUR * 0.3 else C.C_PLAYER
            pts = [(cx, cy - 24), (cx + 18, cy), (cx, cy + 14), (cx - 18, cy)]
            pygame.draw.polygon(surf, color, pts)
            pygame.draw.polygon(surf, (30, 40, 50), pts, 2)


# ─── 敌人 ───────────────────────────────────────────────
def mk_enemy(x, y, etype, wave, story_mode=False, story_battle=0):
    """创建敌人字典，敌舰 HP 随波次递增；故事模式额外加成"""
    inf = C.ETYPES[etype]
    wave_mult = 1 + wave * 0.12
    if story_mode:
        wave_mult += C.STORY_HP_MULT[story_battle]
    hp = int(inf['hp'] * wave_mult)
    return {
        'x': x, 'y': y, 'type': etype,
        'hp': hp, 'mhp': hp,
        'spd': inf['spd'], 'dmg': inf['dmg'], 'rate': inf['rate'],
        'sz': inf['sz'], 'bsz': inf['bsz'], 'bspd': inf['bspd'],
        'col': inf['col'],
        'angle': 0, 'cd': random.randint(0, inf['rate']), 'alive': True,
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
            bspd = e['bspd'] * spd_mult if jam else e['bspd']
            game_state.enemy_bullets.append(Bullet(
                e['x'], e['y'], a, bspd, e['dmg'], False, e['bsz']))
            e['cd'] = e['rate']
    if d < e['sz'] + player.r:
        player.hurt(e['dmg'] * 0.2)


def hurt_enemy(e, dmg):
    """对敌人造成伤害，死亡时播放爆炸动画、音效并生成掉落"""
    e['hp'] -= dmg
    if e['hp'] <= 0:
        e['alive'] = False
        game_state.player.kills += 1
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


