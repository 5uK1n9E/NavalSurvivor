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
        self.muted = False  # 静音状态（在 start() 中不重置，跨游戏保持）
        self.menu_mode = True  # 初始菜单状态

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
        # self.muted = False  # 静音状态跨游戏保持，不重置
        # 清空所有实体
        self.bullets = []; self.enemy_bullets = []
        self.enemies = []; self.drops = []
        self.parts = []; self.booms = []; self.missiles = []


def init_game(story_mode=False, story_battle=0, story_act_idx=0, story_endings=None):
    """重置游戏状态（重新开始用）"""
    gs.player      = entities.Player()
    gs.bullets     = []; gs.enemy_bullets = []
    gs.enemies     = []; gs.drops       = []
    gs.parts       = []; gs.booms       = []; gs.missiles = []
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


def _handle_collisions():
    """处理所有碰撞：玩家子弹→敌人、敌弹→玩家（跳过无敌帧）、拾取道具"""
    p = gs.player

    # 玩家子弹命中敌人
    for pb in gs.bullets:
        if not pb.alive:
            continue
        for e in gs.enemies:
            if not e['alive']:
                continue
            if C.dst((pb.x, pb.y), (e['x'], e['y'])) < e['sz'] + pb.r:
                entities.hurt_enemy(e, pb.dmg)
                pb.alive = False
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
    for m in gs.missiles:
        if m.state == 'explode':
            # 对玩家造成伤害（每10帧一次）
            if m.timer % 10 == 0 and C.dst((m.x, m.y), (p.x, p.y)) < m.radius + p.r:
                p.hurt(C.MISSILE_DAMAGE)
            # 对敌人造成伤害（每10帧一次）
            for e in gs.enemies:
                if e['alive'] and C.dst((m.x, m.y), (e['x'], e['y'])) < m.radius + e['sz']:
                    e['hp'] -= C.MISSILE_ENEMY_DAMAGE
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
    """判定胜负：燃料/耐久耗尽则失败，完成 WIN_WAVES 波次则胜利；中途触发剧情"""
    p = gs.player
    if p.fuel <= 0:
        gs.state, gs.win_why = 'lose', '燃料耗尽'
    elif p.dur <= 0:
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
    elif gs.wm.wave >= C.WIN_WAVES and not gs.wm.queue and not gs.enemies:
        gs.state, gs.win_why = 'win', f'坚守阵地成功！最终得分：{p.score}'
    elif gs.wm.wave >= C.WIN_WAVES and not gs.wm.queue and not gs.enemies:
        gs.state, gs.win_why = 'win', f'坚守阵地成功！最终得分：{p.score}'


def _check_missile_spawn():
    """生成导弹轰炸区：生存模式第6波后，故事模式第三战"""
    if gs.story_mode:
        if gs.story_battle != 2:
            return
    else:
        if gs.wm.wave < 6:
            return
    gs.missile_timer += 1
    if gs.missile_timer < C.MISSILE_MIN_SPACING:
        return
    gs.missile_timer = 0
    count = random.randint(C.MISSILE_COUNT_MIN, C.MISSILE_COUNT_MAX)
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
            gs.player.dur = C.MAX_DUR
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

    ui.draw_hud(screen)
    gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn = ui.draw_pause_button(screen)

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
        screen.fill((0, 0, 0, 165))
        t = ui._fontb.render('请点击游戏窗口', True, (255, 220, 70))
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 25))
        t = ui._font.render('点击窗口后 WASD 即可控制移动', True, C.C_DIM)
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 + 20))
        t = ui._font.render('鼠标瞄准方向射击，空格冲刺', True, C.C_DIM)
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 + 42))


def _render(screen):
    """渲染一帧：背景 + 海浪 + 所有实体 + HUD + 准星 + 提示（不含按钮/面板）"""
    _render_base(screen)

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
    gs = GameState()
    entities.game_state = gs
    waves.game_state = gs
    ui.game_state = gs
    gs.start()
    # 手动触发字体初始化（保险）
    ui._ensure_fonts()
    """主循环：菜单 → 游戏 → 暂停/结束 → 菜单，支持生存和故事两种模式"""
    screen = pygame.display.set_mode((C.W, C.H))
    pygame.display.set_caption("海上军舰 - Naval Survivor")
    gs.clock = pygame.time.Clock()
    gs.menu_mode = True   # 初始在菜单状态
    gs.mouse_pos = (C.W // 2, C.H // 2)
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
                elif ev.type == pygame.MOUSEMOTION:
                    gs.mouse_pos = ev.pos
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    pos = pygame.mouse.get_pos()

                    if gs.state == 'paused':
                        # 暂停时：先检测调试面板，再检测暂停菜单
                        if gs.debug_open and getattr(gs, '_debug_btns', []):
                            for action, btn in gs._debug_btns:
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
                                    elif action == 'dmg_up':
                                        gs.player.bdmg += 10
                                    elif action == 'clear':
                                        gs.enemies = []
                                        gs.wm.queue = []
                                    elif action == 'die':
                                        gs.player.dur = 0
                                    break
                            else:
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
                            continue
                        # 暂停菜单按钮
                        if gs.debug_arrow_btn and gs.debug_arrow_btn.collidepoint(pos):
                            gs.debug_open = not gs.debug_open
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
                            init_game()
                            continue
                        if menu_btn.collidepoint(pos):
                            gs.menu_mode = True
                            break
                    else:
                        # 游戏中：先检测调试面板，再检测其他按钮
                        if gs.debug_open and getattr(gs, '_debug_btns', []):
                            for action, btn in gs._debug_btns:
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
                                    elif action == 'dmg_up':
                                        gs.player.bdmg += 10
                                    elif action == 'clear':
                                        gs.enemies = []
                                        gs.wm.queue = []
                                    elif action == 'die':
                                        gs.player.dur = 0
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

                if gs.state in ('playing', 'story_act'):
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

                # 所有非暂停状态都渲染（含 win/lose 用于触发结束画面）
                if gs.state not in ('paused',):
                    _render(screen)
                    # 绘制按钮和调试面板
                    gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn = ui.draw_pause_button(screen)
                    if gs.debug_open:
                        gs._debug_btns = ui.draw_debug_panel(screen, gs.debug_open, gs.player)
                    # 所有渲染完成后统一刷新
                    pygame.display.flip()
                    gs.frame += 1
                    gs.clock.tick(C.FPS)
                elif gs.state == 'paused':
                    # 暂停：停止一切更新，仅渲染暂停菜单
                    # 先渲染基础画面 + 按钮 + 调试面板
                    _render_base(screen)
                    gs.debug_pause_btn, gs.debug_arrow_btn, gs.mute_btn = ui.draw_pause_button(screen)
                    if gs.debug_open:
                        gs._debug_btns = ui.draw_debug_panel(screen, gs.debug_open, gs.player)
                    # 显示暂停菜单（非阻塞）+ 获取按钮
                    pause_btns = ui.draw_pause_menu(screen, gs.clock)
                    pygame.display.flip()
                    if not (gs.debug_open and getattr(gs, '_debug_btns', [])):
                        for btn in pause_btns:
                            if btn.collidepoint(pos):
                                if btn == pause_btns[0]:  # continue
                                    gs.state = 'playing'
                                elif btn == pause_btns[1]:  # restart
                                    assets.prepare(gs.muted)
                                    init_game()
                                elif btn == pause_btns[2]:  # menu
                                    gs.menu_mode = True
                                break
                else:
                    # 等待 _render 中的结束画面处理
                    pass
                continue  # 跳过 break，继续游戏循环

        # ESC 跳出游戏循环，回到菜单
        if gs.menu_mode:
            continue



