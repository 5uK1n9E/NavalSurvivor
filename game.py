"""
海上军舰 - 游戏主循环
负责：状态管理、碰撞检测、渲染、主循环控制。
通过注入 game_state 到各模块解决循环引用问题。
"""
import math
import random
import pygame
import constants as C
import assets
import entities
import waves
import ui
import upgrades as ug


class GameState:
    """游戏全局状态：持有所有实体列表、波次管理器、帧计数等"""
    def __init__(self):
        self.player      = entities.Player()
        self.bullets     = []
        self.enemy_bullets = []
        self.enemies     = []
        self.drops       = []
        self.parts       = []
        self.booms       = []
        self.missiles    = []   # 导弹轰炸区域
        self.wm          = waves.WaveManager()
        self.frame = 0
        self.state = 'playing'   # playing / paused / win / lose
        self.win_why = ''
        self.hint_timer = C.HINT_DUR
        self.lightning_lines = []
        # 游戏模式
        self.story_mode = False     # 是否故事模式
        self.story_battle = 0       # 当前第几战 (0/1/2)
        self.story_act_idx = 0      # 下一场要播放的幕索引
        self.story_endings = []     # 加载的结局列表
        self.missile_timer = 0      # 导弹间隔计时
        # 调试面板
        self.debug_open = False
        self.debug_pause_btn = None
        self.debug_arrow_btn = None
        self.muted = False  # 静音状态
        self.menu_mode = True  # 初始菜单状态
        # 卡牌强化系统
        self.last_card_wave = 0   # 上次出现卡牌的波次
        self.showing_cards = False  # 是否正在显示卡牌选择
        self.showing_player_panel = False  # 是否显示玩家属性面板
        self.player_panel_page = 0  # 玩家面板当前页码
        self._mouse_event_handled = False  # 本次帧是否已处理鼠标点击，防止else块重复执行

    def start(self, story_mode=False, story_battle=0, story_act_idx=0, story_endings=None):
        """重置所有状态，准备新游戏"""
        self.wm.start(story_mode, story_battle)
        self.frame = 0
        self.state = 'playing'
        self.win_why = ''
        self.hint_timer = C.HINT_DUR
        self.mouse_pos = (C.W // 2, C.H // 2)
        self.paused = False
        self.story_mode = story_mode
        self.story_battle = story_battle
        self.story_act_idx = story_act_idx
        self.story_endings = story_endings or []
        self.missile_timer = 0
        self.debug_open = False
        self.debug_pause_btn = None
        self.debug_arrow_btn = None
        self.muted = False
        self.menu_mode = True
        # 卡牌强化系统
        self.last_card_wave = 0
        self.showing_cards = False
        self.showing_player_panel = False
        self.player_panel_page = 0
        self._mouse_event_handled = False


def init_game(story_mode=False, story_battle=0, story_act_idx=0, story_endings=None):
    """重置游戏状态（重新开始用）"""
    gs.player      = entities.Player()
    ug.init_player_upgrades(gs.player)
    gs.bullets     = []; gs.enemy_bullets = []
    gs.enemies     = []; gs.drops       = []
    gs.parts       = []; gs.booms       = []; gs.missiles = []
    gs.lightning_lines = []
    gs.wm          = waves.WaveManager()
    gs.wm.start(story_mode, story_battle)
    gs.frame = 0
    gs.state = 'playing'
    gs.win_why = ''
    gs.hint_timer = C.HINT_DUR
    gs.mouse_pos = (C.W // 2, C.H // 2)
    gs.paused = False
    gs.story_mode = story_mode
    gs.story_battle = story_battle
    gs.story_act_idx = story_act_idx
    # 只在新值显式传入时才重置结局数据，保留跨模式的 story 数据
    if story_endings is not None:
        gs.story_endings = story_endings
    gs.missile_timer = 0
    gs.debug_open = False
    gs.debug_pause_btn = None
    gs.debug_arrow_btn = None
    # gs.muted = False  # 静音状态跨游戏保持，不重置
    # 卡牌强化系统
    gs.last_card_wave = 0
    gs.showing_cards = False
    gs.showing_player_panel = False
    gs.player_panel_page = 0
    gs._mouse_event_handled = False


def _handle_collisions():
    """处理所有碰撞：玩家子弹→敌人、敌弹→玩家（跳过无敌帧）、拾取道具"""
    p = gs.player

    # 敌人燃烧DoT更新
    dt = 1.0 / C.FPS
    # 仅正常游戏运行状态才更新燃烧；paused / card_select 全部冻结燃烧计时
    if gs.state == "playing":
        for e in gs.enemies:
            if not e['alive']:
                continue
            if e['burn_timer'] > 0:
                e['burn_timer'] -= dt
                e['burn_tick_acc'] += dt
                if e['burn_tick_acc'] >= C.BURN_TICK_RATE:
                    burn_dps = ug.get_burn_dps()
                    dmg = burn_dps * C.BURN_TICK_RATE
                    e['hp'] -= dmg
                    e['burn_tick_acc'] = 0.0
                    for _ in range(4):
                        angle = random.uniform(0, math.tau)
                        dist = random.uniform(0, e['sz'])
                        px = e['x'] + math.cos(angle) * dist
                        py = e['y'] + math.sin(angle) * dist
                        gs.parts.append(entities.Particle(px, py, random.uniform(-1.2, 1.2), random.uniform(-1.5, 1.0),
                                                          random.randint(12, 22), (255, 100, 30), 4))
                    if e['hp'] <= 0:
                        entities.hurt_enemy(e, 0)


    # 玩家子弹命中敌人
    for pb in gs.bullets:
        if not pb.alive:
            continue
        for e in gs.enemies:
            if not e['alive']:
                continue
            if C.dst((pb.x, pb.y), (e['x'], e['y'])) < e['sz'] + pb.r:
                # =========无限穿透：跳过已命中的敌人=========
                if e['uid'] in pb.hit_ids:
                    continue
                # =========超载反应判定=========
                final_dmg = pb.dmg
                overloaded = False
                if (ug.get_overload_reaction_stack(gs.player) > 0
                        and getattr(gs.player, 'chain_stack', 0) > 0
                        and e.get('burn_timer', 0) > 0):
                    mult = ug.get_overload_damage_mult(gs.player)
                    final_dmg = int(pb.dmg * mult)
                    overloaded = True
                entities.hurt_enemy(e, final_dmg,allow_death_ring=not getattr(pb, 'is_ring_bullet', False))
                # 超载视觉特效：以紫色为主的爆发粒子
                if overloaded:
                    cx, cy = e['x'], e['y']
                    # 主力：深紫大粒子
                    for _ in range(16):
                        ang = random.uniform(0, math.tau)
                        spd = random.uniform(2.0, 5.0)
                        gs.parts.append(entities.Particle(
                            cx, cy,
                            math.cos(ang) * spd,
                            math.sin(ang) * spd,
                            random.randint(26, 40),
                            (190, 80, 255),
                            random.randint(6, 8)))
                    # 亮紫核心
                    for _ in range(10):
                        ang = random.uniform(0, math.tau)
                        spd = random.uniform(0.8, 2.5)
                        gs.parts.append(entities.Particle(
                            cx, cy,
                            math.cos(ang) * spd,
                            math.sin(ang) * spd,
                            random.randint(20, 32),
                            (230, 150, 255),
                            6))
                    # 橙色火花
                    for _ in range(6):
                        ang = random.uniform(0, math.tau)
                        spd = random.uniform(2.5, 6.0)
                        gs.parts.append(entities.Particle(
                            cx, cy,
                            math.cos(ang) * spd,
                            math.sin(ang) * spd,
                            random.randint(14, 22),
                            (255, 180, 60),
                            5))
                # =========子弹穿透 / 销毁逻辑========
                pb.hit_ids.add(e['uid'])
                if pb.infinite_pierce:
                    pass  # 无限穿透，不销毁
                elif pb.pierce > 0:
                    pb.pierce -= 1
                else:
                    pb.alive = False
                # =========附加燃烧效果==========
                burn_dps = ug.get_burn_dps()
                if burn_dps > 0:
                    dur = ug.get_burn_duration_sec()
                    # 刷新燃烧持续时间
                    e['burn_timer'] = dur
                    e['burn_tick_acc'] = 0.0
                # ==========连锁闪电逻辑==========
                if gs.state == "playing":
                    chain_radius, chain_dmg = ug.get_chain_lightning_info(gs.player)
                    if chain_radius > 0:
                        hit_list = []
                        hit_this_frame = set()
                        hit_this_frame.add(id(e))  # 原始被击中本体标记
                        for other in gs.enemies:
                            if not other['alive']:
                                continue
                            if other is e:
                                continue
                            if id(other) in hit_this_frame:
                                continue
                            dx = other['x'] - e['x']
                            dy = other['y'] - e['y']
                            dist_sq = dx * dx + dy * dy
                            if dist_sq <= chain_radius * chain_radius:
                                hit_list.append((dist_sq, other))
                        # 由近到远排序，限制数量
                        hit_list.sort(key=lambda x: x[0])
                        hit_list = hit_list[:C.CHAIN_LIGHTNING_MAX_TARGET]

                        for _, target in hit_list:
                            hit_this_frame.add(id(target))
                            entities.hurt_enemy(target, chain_dmg)
                            # 元组：起点、终点、闪电存活帧数(12帧≈0.2秒，调大更久)
                            gs.lightning_lines.append((e['x'], e['y'], target['x'], target['y'], 12))
                            # 连锁目标生成蓝色粒子增强特效
                            for _ in range(6):
                                angle = random.uniform(0, math.tau)
                                dist = random.uniform(0, 14)
                                px = target['x'] + math.cos(angle) * dist
                                py = target['y'] + math.sin(angle) * dist
                                gs.parts.append(entities.Particle(
                                    px, py,
                                    random.uniform(-2.5, 2.5),
                                    random.uniform(-2.5, 2.5),
                                    random.randint(15, 24),
                                    (120, 180, 255),
                                    4
                                ))

                for _ in range(3):
                    gs.parts.append(entities.Particle(
                        pb.x, pb.y,
                        random.uniform(-2, 2), random.uniform(-2, 2),
                        random.randint(8, 14), (255, 220, 80), 3))
                break

    # 敌方子弹命中玩家（无敌帧内跳过碰撞）
    for eb in gs.enemy_bullets:
        if not eb.alive:
            continue
        if C.dst((eb.x, eb.y), (p.x, p.y)) < p.r + eb.r:
            if p.invincible <= 0:  # 非无敌帧才受伤，敌弹消失
                p.hurt(eb.dmg)
                eb.alive = False
            # 无敌帧内敌弹穿过玩家，不销毁（继续飞行）
            for _ in range(4):
                gs.parts.append(entities.Particle(
                    eb.x, eb.y,
                    random.uniform(-2, 2), random.uniform(-2, 2),
                    random.randint(10, 18), (255, 80, 80), 3))

    # 拾取道具
    for d in gs.drops:
        if d.alive and C.dst((d.x, d.y), (p.x, p.y)) < p.r + d.r:
            p.pickup(d)
            d.alive = False
            for _ in range(6):
                gs.parts.append(entities.Particle(
                    d.x, d.y,
                    random.uniform(-2, 2), random.uniform(-2, 2),
                    random.randint(12, 25), entities.Drop.COLS[d.tp], 4))


def _handle_missile_collisions():
    """处理导弹对玩家和敌人的伤害（爆炸期间持续伤害）"""
    p = gs.player
    # 爆破偏转（missile_shunt）：玩家受伤降低、敌人受伤提高
    p_shunt, e_shunt = ug.get_missile_shunt_multipliers(gs.player)
    # 强化轰炸（bombardment）：双方伤害等倍提升
    bomb_mult = ug.get_bombardment_damage_mult(gs.player)
    # 轰炸协议（bombardment_mode）：对敌伤害额外加成，且不伤玩家
    barrage = ug.is_bombardment_mode_active(p)
    mode_dmg_mult = C.BOMBARDMENT_MODE_DMG_MULT if barrage else 1.0
    p_mult = p_shunt * bomb_mult
    e_mult = e_shunt * bomb_mult * mode_dmg_mult
    for m in gs.missiles:
        if m.state == 'explode':
            # 对玩家造成伤害（轰炸协议激活时跳过）
            if not barrage:
                if m.timer % 10 == 0 and C.dst((m.x, m.y), (p.x, p.y)) < m.radius + p.r:
                    dmg = C.MISSILE_DAMAGE * p_mult
                    p.hurt(dmg)
            # 对敌人造成伤害（每10帧一次）
            for e in gs.enemies:
                if e['alive'] and C.dst((m.x, m.y), (e['x'], e['y'])) < m.radius + e['sz']:
                    dmg = C.MISSILE_ENEMY_DAMAGE * e_mult
                    e['hp'] -= dmg
                    if e['hp'] <= 0:
                        entities.hurt_enemy(e, 999)


def _cleanup():
    """清理所有已失效的实体（子弹、敌人、道具、粒子、爆炸、导弹）"""
    gs.bullets     = [b for b in gs.bullets     if b.alive]
    gs.enemy_bullets = [b for b in gs.enemy_bullets if b.alive]
    gs.enemies     = [e for e in gs.enemies     if e['alive']]
    gs.drops       = [d for d in gs.drops       if d.alive]
    gs.parts       = [pt for pt in gs.parts     if pt.life > 0]
    gs.booms       = [bm for bm in gs.booms    if bm.alive]
    gs.missiles    = [m for m in gs.missiles    if m.alive]


def _check_end_condition():
    """判定胜负：燃料/耐久耗尽则失败；无尽模式（生存模式）无波次终点"""
    p = gs.player
    if p.fuel <= 0:
        gs.state, gs.win_why = 'lose', '燃料耗尽'
    elif p.dur <= 0:
        #耐久归零时若仍有复活机会
        if getattr(p, 'revive_stack', 0) > 0 and not getattr(p, 'revive_used', False):
            p.revive_used = True
            p.dur = max(1, int(ug.get_effective_max_dur() * C.REVIVE_HEAL_RATIO))
            p.invincible = C.REVIVE_INVINCIBLE_FRAMES
            # 金色爆发特效
            cx, cy = p.x, p.y
            for _ in range(40):
                ang = random.uniform(0, math.tau)
                spd = random.uniform(1.5, 5.5)
                col = random.choice([(255, 215, 0), (255, 240, 120), (255, 180, 40)])
                gs.parts.append(entities.Particle(
                    cx, cy,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd,
                    random.randint(30, 50),
                    col,
                    random.randint(6, 9)))
            # 一圈金色光环粒子
            for i in range(24):
                ang = math.tau * i / 24
                dist = p.r + 60
                gs.parts.append(entities.Particle(
                    cx + math.cos(ang) * dist,
                    cy + math.sin(ang) * dist,
                    -math.cos(ang) * 3.0,
                    -math.sin(ang) * 3.0,
                    28, (255, 230, 120), 5))
            # 不改变 state，游戏继续
        else:
            gs.state, gs.win_why = 'lose', '耐久归零'
    elif gs.story_mode and gs.state != 'story_act':
        # 故事模式：第二战第3波开始时触发剧情（wave_just_started 保证只触发一次）
        if gs.story_battle == 1 and gs.wm.wave == 3 and gs.wm.wave_just_started:
            gs.state = 'story_act'
            gs.win_why = 'story_act_3'
            gs.wm.wave_just_started = False  # 已消费，防止重复触发
        # 判断当前战是否完成（wave 到达目标且无剩余敌人）
        elif gs.wm.wave >= gs.wm.target_waves and not gs.wm.queue and not gs.enemies:
            gs.state = 'win'
            gs.win_why = f'第 {gs.story_battle + 1} 战胜利'
    # 无尽模式：不再限制 WIN_WAVES 波次，燃料或耐久耗尽才失败
    # 注：卡牌触发已移至游戏主循环中 wm.update() 之前，此处不再重复检查


def _check_missile_spawn():
    """生成导弹轰炸区：生存模式第6波后，故事模式第三战；轰炸协议激活时无视门槛"""
    barrage = ug.is_bombardment_mode_active(gs.player)
    # 门槛判断：轰炸协议激活时跳过波次/故事战门槛
    if not barrage:
        if gs.story_mode:
            if gs.story_battle != 2:
                return
        else:
            if gs.wm.wave < 6:
                return
    gs.missile_timer += 1
    # 间隔：轰炸协议使用专属固定间隔
    if barrage:
        spacing = C.BOMBARDMENT_MODE_SPACING
    else:
        spacing = ug.get_effective_missile_spacing()
    if gs.missile_timer < spacing:
        return
    gs.missile_timer = 0
    lo, hi = ug.get_effective_missile_count_range()
    if barrage:
        lo += C.BOMBARDMENT_MODE_COUNT_BONUS
        hi += C.BOMBARDMENT_MODE_COUNT_BONUS
    count = random.randint(lo, hi)
    for _ in range(count):
        x = random.randint(C.MISSILE_RADIUS + 20, C.W - C.MISSILE_RADIUS - 20)
        y = random.randint(C.MISSILE_RADIUS + 20, C.H - C.MISSILE_RADIUS - 20)
        gs.missiles.append(entities.MissileStrike(x, y))
        if assets.SOUND_MISSILE:
            assets.SOUND_MISSILE.play()


def _handle_debug_actions():
    """处理调试面板触发的动作（固定耐久/燃料）"""
    # 固定耐久/燃料只在面板打开时生效
    if gs.debug_open and gs.state == 'playing':
        if getattr(gs, '_debug_fixed_dur', False):
            gs.player.dur = ug.get_effective_max_dur()
        if getattr(gs, '_debug_fixed_fuel', False):
            gs.player.fuel = C.MAX_FUEL


def _toggle_pause():
    """切换暂停状态（win/lose 状态下禁用）"""
    if gs.state in ('win', 'lose'):
        return
    if gs.state == 'playing':
        gs.state = 'paused'
    elif gs.state == 'paused':
        gs.state = 'playing'


def _render_base(screen):
    """渲染一帧的基础画面（不含 HUD 和暂停层，供暂停时复用）"""
    # 背景图（assets.prepare() 加载后为有效值）
    bg = assets.BACKGROUND_IMG
    if bg is not None:
        screen.blit(bg, (0, 0))
    else:
        screen.fill(C.C_SEA)   # 兜底：背景图未加载时填充纯色
    # 动态海浪叠加
    t = gs.frame * 0.025
    for i in range(8):
        wx = ((i * 197 + t * 18) % (C.W + 160)) - 80
        wy = ((i * 311 + math.sin(t + i) * 22) % (C.H + 160)) - 80
        if 0 < wx < C.W and 0 < wy < C.H:
            pygame.draw.circle(screen, (*C.C_WAVE[:3], 10),
                               (int(wx), int(wy)), 18 + (i % 4) * 7)

    # 绘制顺序：道具 → 敌人 → 玩家 → 子弹 → 粒子 → 爆炸
    for d  in gs.drops:       d.draw(screen)
    for e  in gs.enemies:     entities.draw_enemy(e, screen)
    gs.player.draw(screen)
    for b  in gs.bullets:     b.draw(screen)
    for b  in gs.enemy_bullets: b.draw(screen)
    for pt in gs.parts:       pt.draw(screen)
    for bm in gs.booms:       bm.draw(screen)
    for m  in gs.missiles:    m.draw(screen)

    # ---------------- 连锁闪电绘制 ----------------
    def draw_zigzag_lightning(surf, x1, y1, x2, y2):
        subdiv = 6
        pts = [(x1, y1)]
        for i in range(1, subdiv):
            t = i / subdiv
            nx = x1 * (1 - t) + x2 * t
            ny = y1 * (1 - t) + y2 * t
            off = 14
            nx += random.uniform(-off, off)
            ny += random.uniform(-off, off)
            pts.append((nx, ny))
        pts.append((x2, y2))
        # 多层线条，外粗亮白，中层浅蓝，内层细亮蓝
        pygame.draw.lines(surf, (240, 248, 255), False, pts, 5)
        pygame.draw.lines(surf, (160, 200, 255), False, pts, 3)
        pygame.draw.lines(surf, (200, 230, 255), False, pts, 1)

    # 更新闪电生命周期，绘制还活着的闪电
    new_lightning = []
    for item in gs.lightning_lines:
        x1, y1, x2, y2, life = item
        if life > 0:
            draw_zigzag_lightning(screen, x1, y1, x2, y2)
            new_lightning.append((x1, y1, x2, y2, life - 1))
    gs.lightning_lines = new_lightning
    # ----------------------------------------------------------------
    ui.draw_hud(screen)
    gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn, gs.panel_btn = ui.draw_pause_button(screen)

    # 十字准星
    mx, my = gs.mouse_pos
    cs = 8
    pygame.draw.line(screen, (255, 255, 255), (mx - cs, my), (mx + cs, my), 1)
    pygame.draw.line(screen, (255, 255, 255), (mx, my - cs), (mx, my + cs), 1)

    # 操作提示
    if gs.hint_timer > 0:
        ui.draw_hint(screen)

    # 焦点提示
    if not pygame.display.get_active() and gs.state == 'playing':
        overlay = pygame.Surface((C.W, C.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        screen.blit(overlay, (0, 0))
        t = ui._fontb.render('请点击游戏窗口', True, (255, 220, 70))
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 25))
        t = ui._font.render('点击窗口后 WASD 即可控制移动', True, C.C_DIM)
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 + 20))
        t = ui._font.render('鼠标瞄准方向射击，空格冲刺', True, C.C_DIM)
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 + 42))


def _render(screen):
    """渲染一帧：背景 + 海浪 + 所有实体 + HUD + 准星 + 提示（不含按钮/面板）"""
    _render_base(screen)

    # 玩家属性面板
    if gs.showing_player_panel and gs.state in ('playing', 'paused'):
        ui.draw_player_panel(screen, gs.player_panel_page)

    # 结束画面（包含 story_act 中途剧情）
    if gs.state in ('win', 'lose', 'story_act'):
        # 故事模式：根据结果跳转对应剧情
        if gs.story_mode:
            _handle_story_end(screen, gs.story_acts)
            return
        # 生存模式：显示结束界面
        end_result = ui.draw_end_screen(screen, gs.clock, gs.state == 'win')
        if end_result == 'menu':
            gs.menu_mode = True
        elif end_result == 'restart':
            assets.prepare(gs.muted)
            init_game()
        return

    # 注意：不在这里调用 display.flip()，让调用方统一刷新


# ─── 故事模式辅助类 ────────────────────────────────────────
class StoryActWrapper:
    """包装 story 模块的 StoryAct，使其兼容显示接口"""
    def __init__(self, title, scene_desc, lines, cg_index=0):
        self.title = title
        self.scene_desc = scene_desc
        self.lines = lines
        self.cg_index = cg_index


def _handle_story_end(screen, story_acts):
    """故事模式结束处理：播放幕间剧情或结局"""
    acts = [
        StoryActWrapper(a.title, a.scene_desc, a.lines, a.cg_index)
        for a in story_acts
    ]

    if gs.state == 'lose':
        # 选择结局：根据失败原因
        if '燃料' in gs.win_why:
            ending = next((e for e in gs.story_endings if '燃料' in e['title'] or '不足' in e['title']),
                          gs.story_endings[0] if gs.story_endings else None)
        else:  # 耐久归零
            ending = next((e for e in gs.story_endings if '耐久' in e['title'] or '归零' in e['title']),
                          gs.story_endings[0] if gs.story_endings else None)
        if ending:
            import story as story_module
            story_module.show_ending(screen, gs.clock, ending)
        gs.menu_mode = True

    elif gs.state == 'story_act':
        # 剧情中断：播放幕间剧情后继续战斗
        import story as story_module
        act_idx = gs.story_act_idx
        if act_idx < len(acts):
            story_module.show_dialogue(screen, gs.clock, acts[act_idx])
            gs.story_act_idx = act_idx + 1
        gs.state = 'playing'

    elif gs.state == 'win':
        if gs.story_battle == 0:
            # 第1战胜利 → 播放第2幕 → 开始第2战
            import story as story_module
            act_idx = gs.story_act_idx
            if act_idx < len(acts):
                story_module.show_dialogue(screen, gs.clock, acts[act_idx])
                gs.story_act_idx = act_idx + 1
            gs.story_battle += 1
            assets.prepare(gs.muted)
            init_game(
                story_mode=True,
                story_battle=gs.story_battle,
                story_act_idx=gs.story_act_idx,
                story_endings=gs.story_endings,
            )
        elif gs.story_battle == 1:
            # 第2战胜利 → 播放第4幕 → 开始第3战
            import story as story_module
            act_idx = gs.story_act_idx
            if act_idx < len(acts):
                story_module.show_dialogue(screen, gs.clock, acts[act_idx])
                gs.story_act_idx = act_idx + 1
            gs.story_battle += 1
            assets.prepare(gs.muted)
            init_game(
                story_mode=True,
                story_battle=gs.story_battle,
                story_act_idx=gs.story_act_idx,
                story_endings=gs.story_endings,
            )
        else:
            # 第三战胜利，播放最终结局
            ending = next((e for e in gs.story_endings if '胜利' in e['title']),
                          gs.story_endings[-1] if gs.story_endings else None)
            if ending:
                import story as story_module
                story_module.show_ending(screen, gs.clock, ending)
            gs.menu_mode = True

gs: GameState | None = None
# 注入全局游戏状态，切断循环引用
ui.game_state = gs
entities.game_state = gs
waves.game_state = gs

def run():
    global gs
    import upgrades
    gs = GameState()
    entities.game_state = gs
    waves.game_state = gs
    ui.game_state = gs
    upgrades.game_state = gs
    gs.start()
    # 手动触发字体初始化（保险）
    ui._ensure_fonts()
    """主循环：菜单 → 游戏 → 暂停/结束 → 菜单，支持生存和故事两种模式"""
    screen = pygame.display.set_mode((C.W, C.H))
    pygame.display.set_caption("海上军舰 - Naval Survivor")
    gs.clock = pygame.time.Clock()
    gs.menu_mode = True   # 初始在菜单状态
    gs.mouse_pos = (C.W // 2, C.H // 2)
    gs.screen = screen   # 将 screen 存入 gs，供 upgrades 等模块使用
    # 加载故事数据（仅故事模式需要）
    import story
    gs.story_acts, gs.story_endings = story.load_story()

    while True:
        # ── 主菜单循环 ─────────────────────────────────
        while gs.menu_mode:
            result = ui.show_start_screen(screen, gs.clock)
            if result == 'menu':
                pygame.quit(); __import__('sys').exit()
            elif result == 'start':
                # 生存模式
                gs.menu_mode = False
                assets.prepare(gs.muted)
                init_game(story_mode=False)
                break
            elif result == 'story':
                # 故事模式：先播放第一幕，再开始第一战
                gs.menu_mode = False
                assets.prepare(gs.muted)
                import story as story_module
                # 播放第一幕（索引0）
                story_module.show_dialogue(screen, gs.clock,
                    type('Act', (), {
                        'title': gs.story_acts[0].title if gs.story_acts else '第一幕',
                        'scene_desc': gs.story_acts[0].scene_desc if gs.story_acts else '',
                        'lines': gs.story_acts[0].lines if gs.story_acts else [],
                        'cg_index': gs.story_acts[0].cg_index if gs.story_acts else 0,
                    })())
                # 开始第一战
                gs.story_act_idx = 1
                init_game(
                    story_mode=True,
                    story_battle=0,
                    story_act_idx=1,
                    story_endings=gs.story_endings,
                )
                break

        # ── 游戏循环 ───────────────────────────────────
        while not gs.menu_mode:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); __import__('sys').exit()
                elif ev.type == pygame.KEYDOWN:
                    # win/lose 状态下只允许返回主菜单，禁用暂停和ESC
                    if gs.state in ('win', 'lose'):
                        if ev.key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
                            gs.menu_mode = True
                        # 注意：不能 break，否则 _render 不会执行，结局 CG 无法播放
                        continue
                    if ev.key == pygame.K_ESCAPE:
                        if gs.state == 'playing' or gs.state == 'paused':
                            _toggle_pause()
                        break
                    # 翻页处理（仅玩家面板开启时）
                    if gs.showing_player_panel:
                        if ev.key in (pygame.K_LEFT, pygame.K_PAGEUP):
                            gs.player_panel_page = max(0, gs.player_panel_page - 1)
                            break
                        if ev.key in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
                            gs.player_panel_page = min(2, gs.player_panel_page + 1)
                            break
                elif ev.type == pygame.MOUSEMOTION:
                    gs.mouse_pos = ev.pos
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    pos = pygame.mouse.get_pos()
                    gs._mouse_event_handled = True

                    if gs.state == 'paused':
                        # 调试面板边界矩形
                        _DEBUG_W = 260
                        debug_panel_rect = pygame.Rect(C.W - _DEBUG_W - 20, 50, _DEBUG_W, C.H - 100)
                        # 只有点击落在调试面板内，才处理调试面板按钮
                        if gs.debug_open and getattr(gs, '_debug_btns', []) and debug_panel_rect.collidepoint(pos):
                            for entry in gs._debug_btns:
                                action, btn, *rest = entry
                                is_maxed = rest[0] if rest else False

                                if btn.collidepoint(pos):
                                    if action == 'fixed_dur':
                                        gs._debug_fixed_dur = not getattr(gs, '_debug_fixed_dur', False)
                                    elif action == 'fixed_fuel':
                                        gs._debug_fixed_fuel = not getattr(gs, '_debug_fixed_fuel', False)
                                    elif action == 'next_wave':
                                        gs.wm.wave = min(gs.wm.wave + 1, gs.wm.target_waves)
                                        gs.wm.queue = []
                                        gs.wm.timer = 0
                                        gs.wm.stimer = 0
                                        gs.last_card_wave = gs.wm.wave
                                        gs.showing_cards = False
                                        gs.state = 'playing'
                                    elif action == 'dmg_up':
                                        gs.player.bdmg += 10
                                    elif action == 'clear':
                                        gs.enemies = []
                                        gs.wm.queue = []
                                        gs.last_card_wave = gs.wm.wave
                                        gs.showing_cards = False
                                        gs.state = 'playing'
                                    elif action == 'die':
                                        gs.player.dur = 0
                                    elif action.startswith('upgrade_'):
                                        if is_maxed:
                                            break
                                        key = action.replace('upgrade_', '')
                                        upg = next((u for u in ug.ALL_UPGRADES if u.key == key), None)
                                        if upg:
                                            ug.apply_upgrade(gs.player, upg)
                                        break

                            else:
                                # 点击在调试面板框内，但没有点任何调试按钮：处理箭头、静音
                                if gs.debug_arrow_btn and gs.debug_arrow_btn.collidepoint(pos):
                                    gs.debug_open = not gs.debug_open
                                elif getattr(gs, 'mute_btn', None) and gs.mute_btn.collidepoint(pos):
                                    gs.muted = not gs.muted
                                    if gs.muted:
                                        pygame.mixer.music.set_volume(0)
                                        for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                            if s: s.set_volume(0)
                                    else:
                                        pygame.mixer.music.set_volume(1)
                                        for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                            if s: s.set_volume(1)
                        # 暂停菜单按钮
                        else:
                            # 点击不在调试面板区域：处理箭头、面板、静音按钮（不在调试面板框，但是右上角小图标）
                            if gs.debug_arrow_btn and gs.debug_arrow_btn.collidepoint(pos):
                                gs.debug_open = not gs.debug_open
                                continue
                            if getattr(gs, 'panel_btn', None) and gs.panel_btn.collidepoint(pos):
                                gs.showing_player_panel = not gs.showing_player_panel
                                if gs.showing_player_panel:
                                    gs.state = 'paused'
                                else:
                                    gs.state = 'playing'
                                continue
                            if getattr(gs, 'mute_btn', None) and gs.mute_btn.collidepoint(pos):
                                gs.muted = not gs.muted
                                if gs.muted:
                                    pygame.mixer.music.set_volume(0)
                                    for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                        if s: s.set_volume(0)
                                else:
                                    pygame.mixer.music.set_volume(1)
                                    for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                        if s: s.set_volume(1)
                                continue
                        # 继续/重新开始/返回菜单
                        btn_w, btn_h = 280, 52
                        y_offset = C.H // 2 - 96
                        continue_btn = pygame.Rect(C.W // 2 - btn_w // 2, y_offset, btn_w, btn_h)
                        restart_btn  = pygame.Rect(C.W // 2 - btn_w // 2, y_offset + 64, btn_w, btn_h)
                        menu_btn     = pygame.Rect(C.W // 2 - btn_w // 2, y_offset + 128, btn_w, btn_h)
                        if continue_btn.collidepoint(pos):
                            gs.state = 'playing'
                            continue
                        if restart_btn.collidepoint(pos):
                            assets.prepare(gs.muted)
                            init_game(
                                story_mode=gs.story_mode,
                                story_battle=gs.story_battle,
                                story_act_idx=gs.story_act_idx,
                                story_endings=gs.story_endings,
                            )
                            continue
                        if menu_btn.collidepoint(pos):
                            gs.menu_mode = True
                            break
                    else:
                        # 游戏中：先检测调试面板，再检测其他按钮
                        if gs.debug_open and getattr(gs, '_debug_btns', []):
                            for entry in gs._debug_btns:
                                action, btn, *rest = entry
                                is_maxed = rest[0] if rest else False

                                if btn.collidepoint(pos):
                                    if action == 'fixed_dur':
                                        gs._debug_fixed_dur = not getattr(gs, '_debug_fixed_dur', False)
                                    elif action == 'fixed_fuel':
                                        gs._debug_fixed_fuel = not getattr(gs, '_debug_fixed_fuel', False)
                                    elif action == 'next_wave':
                                        gs.wm.wave = min(gs.wm.wave + 1, gs.wm.target_waves)
                                        gs.wm.queue = []
                                        gs.wm.timer = 0
                                        gs.wm.stimer = 0
                                        gs.last_card_wave = gs.wm.wave
                                        gs.showing_cards = False
                                        gs.state = 'playing'
                                    elif action == 'dmg_up':
                                        gs.player.bdmg += 10
                                    elif action == 'clear':
                                        gs.enemies = []
                                        gs.wm.queue = []
                                        gs.last_card_wave = gs.wm.wave
                                        gs.showing_cards = False
                                        gs.state = 'playing'
                                    elif action == 'die':
                                        gs.player.dur = 0
                                    elif action.startswith('upgrade_'):
                                        if is_maxed:
                                            break
                                        key = action.replace('upgrade_', '')
                                        upg = next((u for u in ug.ALL_UPGRADES if u.key == key), None)
                                        if upg:
                                            ug.apply_upgrade(gs.player, upg)
                                    break

                            else:
                                if gs.debug_arrow_btn and gs.debug_arrow_btn.collidepoint(pos):
                                    gs.debug_open = not gs.debug_open
                                elif gs.debug_pause_btn and gs.debug_pause_btn.collidepoint(pos):
                                    _toggle_pause()
                                elif getattr(gs, 'mute_btn', None) and gs.mute_btn.collidepoint(pos):
                                    gs.muted = not gs.muted
                                    if gs.muted:
                                        pygame.mixer.music.set_volume(0)
                                        for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                            if s: s.set_volume(0)
                                    else:
                                        pygame.mixer.music.set_volume(1)
                                        for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                            if s: s.set_volume(1)
                            continue
                        if gs.debug_arrow_btn and gs.debug_arrow_btn.collidepoint(pos):
                            gs.debug_open = not gs.debug_open
                            continue
                        if getattr(gs, 'panel_btn', None) and gs.panel_btn.collidepoint(pos):
                            gs.showing_player_panel = not gs.showing_player_panel
                            if gs.showing_player_panel:
                                gs.state = 'paused'
                            else:
                                gs.state = 'playing'
                            continue
                        if gs.debug_pause_btn and gs.debug_pause_btn.collidepoint(pos):
                            _toggle_pause()
                        elif getattr(gs, 'mute_btn', None) and gs.mute_btn.collidepoint(pos):
                            gs.muted = not gs.muted
                            if gs.muted:
                                pygame.mixer.music.set_volume(0)
                                for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                    if s: s.set_volume(0)
                            else:
                                pygame.mixer.music.set_volume(1)
                                for s in (assets.SOUND_HIT, assets.SOUND_BOOM, assets.SOUND_MISSILE):
                                    if s: s.set_volume(1)
            else:  # 仅当事件循环没有 break 时才执行
                keys = pygame.key.get_pressed()

                if not gs._mouse_event_handled:
                    if gs.state in ('playing', 'story_act', 'card_select'):
                        # 操作提示计时
                        if gs.hint_timer > 0:
                            gs.hint_timer -= 1

                        # 更新
                        gs.player.update(keys, gs.mouse_pos)
                        for b   in gs.bullets:      b.update()
                        for b   in gs.enemy_bullets: b.update()
                        for e   in gs.enemies:      entities.update_enemy(e, gs.player)
                        for d   in gs.drops:        d.update()
                        for pt  in gs.parts:        pt.update()
                        for bm  in gs.booms:        bm.update()
                        for m   in gs.missiles:     m.update()

                        _handle_collisions()
                        _handle_missile_collisions()
                        _handle_debug_actions()
                        _cleanup()
                        gs.wm.update()
                        _check_missile_spawn()
                        _check_end_condition()

                # 渲染分支
                if gs.state == 'card_select':
                    ug.show_card_selection(gs.clock)
                    gs.showing_cards = False
                    gs.state = 'playing'
                    gs.frame += 1
                    gs.clock.tick(C.FPS)
                    continue
                elif gs.state == 'paused':
                    if gs.debug_open and gs.showing_player_panel:
                        _render_base(screen)
                        gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn, gs.panel_btn = ui.draw_pause_button(screen)
                        gs._debug_btns = ui.draw_debug_panel(screen, gs.debug_open, gs.player)
                        ui.draw_player_panel(screen, gs.player_panel_page)
                        pygame.display.flip()
                    elif gs.debug_open:
                        _render_base(screen)
                        gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn, gs.panel_btn = ui.draw_pause_button(screen)
                        gs._debug_btns = ui.draw_debug_panel(screen, gs.debug_open, gs.player)
                        pygame.display.flip()
                    elif gs.showing_player_panel:
                        _render_base(screen)
                        gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn, gs.panel_btn = ui.draw_pause_button(screen)
                        ui.draw_player_panel(screen, gs.player_panel_page)
                        pygame.display.flip()
                    else:
                        _render_base(screen)
                        gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn, gs.panel_btn = ui.draw_pause_button(screen)
                        pause_btns = ui.draw_pause_menu(screen, gs.clock)
                        if gs.debug_arrow_btn and gs.debug_arrow_btn.collidepoint(pygame.mouse.get_pos()):
                            gs.debug_open = True
                            gs._debug_btns = ui.draw_debug_panel(screen, True, gs.player)
                else:
                    _render(screen)
                    gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn, gs.panel_btn = ui.draw_pause_button(screen)
                    if gs.debug_open:
                        gs._debug_btns = ui.draw_debug_panel(screen, gs.debug_open, gs.player)
                    pygame.display.flip()
                    gs.frame += 1
                    gs.clock.tick(C.FPS)
                gs._mouse_event_handled = False
                continue  # 跳过 break，继续游戏循环

        # ESC 跳出游戏循环，回到菜单
        if gs.menu_mode:
            continue



