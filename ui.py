"""
海上军舰 - 界面绘制
负责：启动封面、HUD（血条/燃料/波次/得分）、操作提示、结束界面、暂停菜单。
通过 game_state（由 game.py 注入）访问游戏全局数据。
"""
import ctypes
import pygame
import constants as C
import os

game_state = None


# ─── 字体（延迟初始化） ────────────────────────────────────
_font  = None
_fontb = None
_fontm = None


def _ensure_fonts():
    """确保 pygame 已初始化并创建字体"""
    global _font, _fontb, _fontm
    if _font is None:
        try:
            _font = pygame.font.SysFont('microsoftyahei', 18)
            _fontb = pygame.font.SysFont('microsoftyahei', 42, bold=True)
            _fontm = pygame.font.SysFont('microsoftyahei', 26)
        except:
            # 找不到雅黑，使用系统默认字体兜底
            _font = pygame.font.SysFont('', 18)
            _fontb = pygame.font.SysFont('', 42, bold=True)
            _fontm = pygame.font.SysFont('', 26)

# ─── 辅助绘制 ────────────────────────────────────────────
def draw_bar(surf, x, y, w, h, ratio, col, bg, label):
    """绘制进度条：背景 + 填充 + 边框 + 右侧文字标签"""
    _ensure_fonts()
    pygame.draw.rect(surf, bg, (x, y, w, h))
    pygame.draw.rect(surf, col, (x, y, int(w * max(0, ratio)), h))
    pygame.draw.rect(surf, C.C_DARK, (x, y, w, h), 1)
    t = _font.render(label, True, C.C_WHITE)
    # 文字放在条形图右侧，避免遮挡
    surf.blit(t, (x + w + 4, y - 2))


def draw_btn(surf, btn, text, col, hover_col, font, text_col=C.C_WHITE):
    """绘制圆角按钮，返回悬停状态；高亮时切换颜色"""
    _ensure_fonts()
    hover = btn.collidepoint(pygame.mouse.get_pos())
    color = hover_col if hover else col
    pygame.draw.rect(surf, color, btn, border_radius=8)
    pygame.draw.rect(surf, (255, 255, 255, 70), btn, 2, border_radius=8)
    pygame.draw.line(surf, (0, 0, 0, 80),
                     (btn.left + 4, btn.bottom - 1),
                     (btn.right - 4, btn.bottom - 1))
    t = font.render(text, True, text_col)
    surf.blit(t, (btn.centerx - t.get_width() // 2,
                  btn.centery - t.get_height() // 2))
    return hover


# ─── 启动界面 ────────────────────────────────────────────
def show_start_screen(screen, clock):
    """显示启动封面，返回 'start' 或 'menu'；窗口失去焦点时自动提权"""
    _ensure_fonts()
    try:
        hwnd = pygame.display.get_wm_info()['window']
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

    from utils import get_resource_path
    cover_path = get_resource_path(os.path.join('resource', 'cover.png'))

    try:
        cover_img = pygame.image.load(cover_path)
        cover_img = pygame.transform.scale(cover_img, (C.W, C.H))
    except Exception:
        cover_img = None

    btn_w, btn_h = 280, 58
    start_btn = pygame.Rect(C.W // 2 - btn_w // 2, C.H // 2 + 30, btn_w, btn_h)
    story_btn = pygame.Rect(C.W // 2 - btn_w // 2, C.H // 2 + 100, btn_w, btn_h)
    exit_btn  = pygame.Rect(C.W // 2 - btn_w // 2, C.H // 2 + 170, btn_w, btn_h)

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); __import__('sys').exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = pygame.mouse.get_pos()
                if start_btn.collidepoint(pos): return 'start'
                if story_btn.collidepoint(pos): return 'story'
                if exit_btn.collidepoint(pos):  pygame.quit(); __import__('sys').exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE): return 'start'
                elif ev.key == pygame.K_ESCAPE:
                    pygame.quit(); __import__('sys').exit()

        if cover_img:
            screen.blit(cover_img, (0, 0))
        else:
            screen.fill(C.C_SEA)

        t = _fontb.render('海上军舰 - Naval Survivor', True, C.C_WHITE)
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 180))
        draw_btn(screen, start_btn, '开  始  游  戏', C.BTN_START, C.BTN_START_H, _fontb)
        draw_btn(screen, story_btn, '故  事  模  式', C.BTN_RESTART, C.BTN_RESTART_H, _fontb)
        draw_btn(screen, exit_btn,  '退  出  游  戏', C.BTN_EXIT,  C.BTN_EXIT_H,  _fontb)

        pygame.display.flip()
        clock.tick(C.FPS)


# ─── HUD ────────────────────────────────────────────────
def draw_hud(surf):
    """绘制 HUD：左上角耐久/燃料条，顶部中央波次和得分（故事模式显示战斗进度）"""
    _ensure_fonts()
    p = game_state.player
    m = 14
    bar_w = 160

    # 左上角：耐久/燃料条（标签移至右侧避免遮挡）
    draw_bar(surf, m, m,            bar_w, 14, p.dur / C.MAX_DUR,
             (40, 185, 80), (18, 55, 28), f'耐久 {int(p.dur)}')
    draw_bar(surf, m, m + 18,       bar_w, 14, p.fuel / C.MAX_FUEL,
             (225, 185, 40), (75, 55, 10), f'燃料 {int(p.fuel)}')

    if game_state.story_mode:
        # 故事模式：显示当前波次/目标
        t = _font.render(f'波次 {game_state.wm.wave}/{game_state.wm.target_waves}', True, (255, 220, 120))
        surf.blit(t, (C.W // 2 - t.get_width() // 2, m))
    else:
        # 生存模式：显示波次和得分
        wave_txt = _font.render(f'波次 {game_state.wm.wave}/{C.WIN_WAVES}', True, C.C_WHITE)
        surf.blit(wave_txt, (C.W // 2 - wave_txt.get_width() // 2, m))

        score_txt = _font.render(f'得分 {p.score}', True, C.C_DIM)
        surf.blit(score_txt, (C.W // 2 - score_txt.get_width() // 2, m + 22))


def draw_pause_button(surf):
    """绘制右上角暂停按钮 + 静音按钮 + 右侧调试三角箭头"""
    _ensure_fonts()
    # 暂停按钮
    btn = pygame.Rect(C.W - 116, 14, 46, 28)
    hover = btn.collidepoint(pygame.mouse.get_pos())
    color = C.BTN_PAUSE_H if hover else C.BTN_PAUSE
    pygame.draw.rect(surf, color, btn, border_radius=4)
    pygame.draw.rect(surf, C.C_WHITE, btn, 1, border_radius=4)
    cx, cy = btn.centerx, btn.centery
    pygame.draw.rect(surf, C.C_WHITE, (cx - 8, cy - 5, 3, 10))
    pygame.draw.rect(surf, C.C_WHITE, (cx + 5, cy - 5, 3, 10))

    # 静音按钮（暂停按钮左侧）
    mute_btn = pygame.Rect(C.W - 162, 14, 42, 28)
    hover_m = mute_btn.collidepoint(pygame.mouse.get_pos())
    mute_color = C.BTN_PAUSE_H if hover_m else C.BTN_PAUSE
    pygame.draw.rect(surf, mute_color, mute_btn, border_radius=4)
    pygame.draw.rect(surf, C.C_WHITE, mute_btn, 1, border_radius=4)
    # 扬声器图标
    mx, my = mute_btn.centerx, mute_btn.centery
    if game_state.muted:
        # 静音图标：三角形 + 叉号
        pygame.draw.polygon(surf, C.C_WHITE, [
            (mx - 8, my - 5), (mx - 2, my - 5),
            (mx - 2, my + 5), (mx - 8, my + 5)])
        pygame.draw.line(surf, (255, 80, 80), (mx + 1, my - 6), (mx + 7, my + 6), 2)
        pygame.draw.line(surf, (255, 80, 80), (mx + 7, my - 6), (mx + 1, my + 6), 2)
    else:
        # 扬声器图标：三角形 + 声波
        pygame.draw.polygon(surf, C.C_WHITE, [
            (mx - 8, my - 5), (mx - 2, my - 5),
            (mx - 2, my + 5), (mx - 8, my + 5)])
        pygame.draw.arc(surf, C.C_WHITE,
                        (mx - 1, my - 7, 10, 14), -0.8, 0.8, 1)
        pygame.draw.arc(surf, C.C_WHITE,
                        (mx + 2, my - 9, 14, 18), -0.6, 0.6, 1)

    # 调试三角箭头（右侧边缘）
    dbg = pygame.Rect(C.W - 18, C.H // 2 - 14, 18, 28)
    dbg_hover = dbg.collidepoint(pygame.mouse.get_pos())
    dbg_color = (80, 80, 120) if dbg_hover else (40, 40, 60)
    pts = [(C.W, dbg.centery), (C.W - 14, dbg.top + 4), (C.W - 14, dbg.bottom - 4)]
    pygame.draw.polygon(surf, dbg_color, pts)
    pygame.draw.line(surf, (100, 100, 140), (C.W - 14, dbg.top + 4), (C.W - 14, dbg.bottom - 4), 1)
    return btn, dbg, mute_btn


def draw_hint(surf):
    """操作提示：前3秒淡入，后1秒淡出，底部居中显示"""
    _ensure_fonts()
    if game_state.hint_timer <= 0:
        return
    alpha = 200
    if game_state.hint_timer < 60:
        alpha = int(200 * game_state.hint_timer / 60)
    elif game_state.hint_timer > C.HINT_DUR - 60:
        alpha = int(200 * (C.HINT_DUR - game_state.hint_timer) / 60)

    overlay = pygame.Surface((C.W, C.H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha // 3))
    surf.blit(overlay, (0, 0))

    box = pygame.Rect(C.W // 2 - 220, C.H - 125, 440, 90)
    pygame.draw.rect(surf, (*C.C_DARK[:3], alpha), box, border_radius=6)
    pygame.draw.rect(surf, (*C.C_WAVE[:3], alpha), box, 2, border_radius=6)
    lines = [('WASD / 方向键 移动', (200, 210, 230)),
             ('按住空格 冲刺（加速但加速耗油）', (200, 210, 230)),
             ('鼠标瞄准方向自动射击',   (160, 170, 190))]
    for i, (txt, col) in enumerate(lines):
        t = _font.render(txt, True, col)
        surf.blit(t, (box.centerx - t.get_width() // 2,
                      box.top + 14 + i * 22))


def draw_pause_menu(screen, clock):
    """暂停菜单显示（非阻塞）。返回暂停菜单按钮列表。"""
    _ensure_fonts()
    btn_w, btn_h = 280, 52
    y_offset = C.H // 2 - 96
    continue_btn    = pygame.Rect(C.W // 2 - btn_w // 2, y_offset,           btn_w, btn_h)
    restart_btn     = pygame.Rect(C.W // 2 - btn_w // 2, y_offset + 64,     btn_w, btn_h)
    menu_btn        = pygame.Rect(C.W // 2 - btn_w // 2, y_offset + 128,    btn_w, btn_h)

    # 绘制
    t = _fontb.render('暂  停', True, C.C_WHITE)
    screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 148))
    draw_btn(screen, continue_btn,  '继  续  游  戏', C.BTN_START,   C.BTN_START_H,  _fontb)
    draw_btn(screen, restart_btn,   '重  新  开  始', C.BTN_RESTART, C.BTN_RESTART_H, _fontb)
    draw_btn(screen, menu_btn,      '返  回  菜  单', C.BTN_MNUE,    C.BTN_MNUE_H,   _fontb)
    pygame.display.flip()
    clock.tick(C.FPS)

    # 返回按钮供外部事件循环检测
    return [continue_btn, restart_btn, menu_btn]


# ─── 调试面板 ────────────────────────────────────────────
_DEBUG_W = 260
_DEBUG_X = C.W - _DEBUG_W - 20


def draw_debug_panel(screen, is_open, player):
    """绘制调试面板，返回按钮矩形列表供事件检测"""
    _ensure_fonts()
    if not is_open:
        return []

    panel = pygame.Rect(_DEBUG_X, 50, _DEBUG_W, C.H - 100)
    pygame.draw.rect(screen, (15, 20, 35, 230), panel, border_radius=8)
    pygame.draw.rect(screen, (80, 100, 140), panel, 2, border_radius=8)

    # 标题
    t = _fontb.render('调  试  面  板', True, (200, 200, 255))
    screen.blit(t, (panel.centerx - t.get_width() // 2, panel.top + 10))

    y = panel.top + 50
    line_h = 26
    btn_h = 28
    btn_w = 110
    buttons = []  # 收集所有可点击按钮

    # 当前波次
    t = _font.render(f'波次: {game_state.wm.wave}/{game_state.wm.target_waves}', True, C.C_DIM)
    screen.blit(t, (panel.left + 10, y)); y += line_h

    # 玩家属性
    t = _font.render(f'耐久: {int(player.dur)}/{C.MAX_DUR}', True, (40, 215, 90))
    screen.blit(t, (panel.left + 10, y)); y += line_h
    t = _font.render(f'燃料: {int(player.fuel)}/{int(C.MAX_FUEL)}', True, (240, 200, 40))
    screen.blit(t, (panel.left + 10, y)); y += line_h
    t = _font.render(f'伤害:{player.bdmg} 射速:{player.brate} 弹数:{player.bcount}', True, C.C_DIM)
    screen.blit(t, (panel.left + 10, y)); y += line_h + 4

    # 固定耐久（toggle）
    btn1 = pygame.Rect(panel.left + 8, y, btn_w, btn_h)
    hover1 = btn1.collidepoint(pygame.mouse.get_pos())
    c1 = (40, 100, 60) if hover1 else (25, 65, 40)
    pygame.draw.rect(screen, c1, btn1, border_radius=4)
    t = _font.render('固定耐久', True, C.C_WHITE)
    screen.blit(t, (btn1.centerx - t.get_width() // 2, btn1.centery - 8))
    if getattr(game_state, '_debug_fixed_dur', False):
        pygame.draw.rect(screen, (40, 215, 90), btn1, 2, border_radius=4)
    buttons.append(('fixed_dur', btn1))
    y += btn_h + 6

    # 固定燃料（toggle）
    btn2 = pygame.Rect(panel.left + 8, y, btn_w, btn_h)
    hover2 = btn2.collidepoint(pygame.mouse.get_pos())
    c2 = (100, 80, 40) if hover2 else (65, 50, 25)
    pygame.draw.rect(screen, c2, btn2, border_radius=4)
    t = _font.render('固定燃料', True, C.C_WHITE)
    screen.blit(t, (btn2.centerx - t.get_width() // 2, btn2.centery - 8))
    if getattr(game_state, '_debug_fixed_fuel', False):
        pygame.draw.rect(screen, (240, 200, 40), btn2, 2, border_radius=4)
    buttons.append(('fixed_fuel', btn2))
    y += btn_h + 12

    # 跳波次
    btn_next = pygame.Rect(panel.left + 8, y, btn_w * 2 + 14, btn_h)
    hover_next = btn_next.collidepoint(pygame.mouse.get_pos())
    c_next = (40, 60, 100) if hover_next else (25, 40, 70)
    pygame.draw.rect(screen, c_next, btn_next, border_radius=4)
    t = _font.render('跳 到 下 一 波', True, C.C_WHITE)
    screen.blit(t, (btn_next.centerx - t.get_width() // 2, btn_next.centery - 8))
    buttons.append(('next_wave', btn_next))
    y += btn_h + 8

    # 伤害+10
    btn_up = pygame.Rect(panel.left + 8, y, btn_w, btn_h)
    hover_up = btn_up.collidepoint(pygame.mouse.get_pos())
    c_up = (100, 40, 40) if hover_up else (70, 25, 25)
    pygame.draw.rect(screen, c_up, btn_up, border_radius=4)
    t = _font.render(f'+伤害({player.bdmg})', True, C.C_WHITE)
    screen.blit(t, (btn_up.centerx - t.get_width() // 2, btn_up.centery - 8))
    buttons.append(('dmg_up', btn_up))
    y += btn_h + 8

    # 清除敌军
    btn_clear = pygame.Rect(panel.left + 8 + btn_w + 6, y, btn_w, btn_h)
    hover_clear = btn_clear.collidepoint(pygame.mouse.get_pos())
    c_clear = (100, 60, 40) if hover_clear else (70, 40, 25)
    pygame.draw.rect(screen, c_clear, btn_clear, border_radius=4)
    t = _font.render('清 除 军', True, C.C_WHITE)
    screen.blit(t, (btn_clear.centerx - t.get_width() // 2, btn_clear.centery - 8))
    buttons.append(('clear', btn_clear))
    y += btn_h + 12

    # 触发死亡
    btn_die = pygame.Rect(panel.left + 8, y, btn_w * 2 + 14, btn_h)
    hover_die = btn_die.collidepoint(pygame.mouse.get_pos())
    c_die = (80, 25, 25) if hover_die else (55, 18, 18)
    pygame.draw.rect(screen, c_die, btn_die, border_radius=4)
    t = _font.render('触 发 死 亡 结 局', True, (200, 80, 80))
    screen.blit(t, (btn_die.centerx - t.get_width() // 2, btn_die.centery - 8))
    buttons.append(('die', btn_die))
    y += btn_h + 12

    # 关闭提示
    t = _font.render('点击右侧箭头关闭', True, (80, 80, 100))
    screen.blit(t, (panel.centerx - t.get_width() // 2, C.H - 60))

    return buttons


# ─── 结束界面 ────────────────────────────────────────────
def draw_end_screen(screen, clock, is_win):
    """显示结束界面，返回 'menu' 或 'restart'；窗口失去焦点时自动提权"""
    _ensure_fonts()
    try:
        hwnd = pygame.display.get_wm_info()['window']
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

    btn_w, btn_h = 260, 54
    menu_btn    = pygame.Rect(C.W // 2 - btn_w // 2, C.H // 2 + 60,  btn_w, btn_h)
    restart_btn = pygame.Rect(C.W // 2 - btn_w // 2, C.H // 2 + 130, btn_w, btn_h)

    title = 'MISSION COMPLETE' if is_win else 'GAME OVER'
    sub   = game_state.win_why
    stat  = f'击杀: {game_state.player.kills}  波次: {game_state.wm.wave}'

    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); __import__('sys').exit()
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = pygame.mouse.get_pos()
                if menu_btn.collidepoint(pos):    return 'menu'
                if restart_btn.collidepoint(pos): return 'restart'
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_SPACE): return 'restart'
                elif ev.key == pygame.K_ESCAPE: return 'menu'

        screen.fill((*C.C_DARK[:3], 175))
        t = _fontb.render(title, True, (255, 220, 70))
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 70))
        t = _fontm.render(sub, True, C.C_WHITE)
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 20))
        t = _font.render(stat, True, C.C_DIM)
        screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 + 15))
        draw_btn(screen, restart_btn, '再 来 一 局', C.BTN_RESTART, C.BTN_RESTART_H, _fontb)
        draw_btn(screen, menu_btn,    '返回主菜单',  C.BTN_MNUE,    C.BTN_MNUE_H,  _fontb)
        pygame.display.flip()
        clock.tick(C.FPS)
