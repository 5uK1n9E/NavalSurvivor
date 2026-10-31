"""
海上军舰 - 界面绘制
负责：启动封面、HUD（血条/燃料/波次/得分）、操作提示、结束界面、暂停菜单。
通过 game_state（由 game.py 注入）访问游戏全局数据。
"""
import ctypes
import pygame
import constants as C
import os
import upgrades as ug
game_state = None

# ─── 玩家属性面板 ────────────────────────────────────────
_PLAYER_PANEL_W = 340
_PLAYER_PANEL_X = 20
_PLAYER_PANEL_Y = 60
_PLAYER_PANEL_H = 520
_PANEL_LINE_H = 22
_PAGE_MAX_LINES = 16  # 每页最大行数（含标题行）


def _draw_panel_row(surf, panel, y, label, value, color, line_h):
    """绘制面板一行：左侧标签 + 右侧值"""
    lbl = _font.render(label, True, C.C_DIM)
    val = _font.render(value, True, color)
    surf.blit(lbl, (panel.left + 10, y))
    surf.blit(val, (panel.right - val.get_width() - 10, y))
    return y + line_h


def draw_player_panel(surf, page=0):
    """绘制玩家属性面板：page0基础属性；page1强化效果；page2强化历史，←→翻页，共3页"""
    _ensure_fonts()
    panel = pygame.Rect(_PLAYER_PANEL_X, _PLAYER_PANEL_Y, _PLAYER_PANEL_W, _PLAYER_PANEL_H)
    pygame.draw.rect(surf, (15, 25, 45, 225), panel, border_radius=8)
    pygame.draw.rect(surf, (60, 100, 160), panel, 2, border_radius=8)
    p = game_state.player
    y = panel.top + 12
    lh = _PANEL_LINE_H
    col_dim = C.C_DIM
    col_white = C.C_WHITE
    col_green = (80, 215, 90)
    col_blue  = (80, 160, 255)
    col_orange = (255, 180, 60)
    col_red   = (255, 90, 90)

    def draw_title(y, text, color):
        t = _font.render(text, True, color)
        surf.blit(t, (panel.left + 10, y))
        return y + lh

    def draw_sep(y):
        pygame.draw.line(surf, (60, 100, 160),
                         (panel.left + 8, y), (panel.right - 8, y))
        return y + lh

    # ── page0：基础属性 ──
    if page == 0:
        t = _fontb.render('玩 家 属 性', True, col_white)
        surf.blit(t, (panel.left + 10, y))
        y += lh + 4
        y = draw_sep(y)
        y = _draw_panel_row(surf, panel, y, '耐久',
                            f'{int(p.dur)} / {int(ug.get_effective_max_dur())}', col_green, lh)
        y = _draw_panel_row(surf, panel, y, '燃料',
                            f'{int(p.fuel)} / {int(C.MAX_FUEL)}', col_orange, lh)
        y += 4
        y = draw_title(y, '── 战斗属性 ──', col_blue)
        y = _draw_panel_row(surf, panel, y, '子弹伤害',
                            f'{ug.get_effective_bullet_dmg()} (+{p.dmg_bonus})', col_blue, lh)
        y = _draw_panel_row(surf, panel, y, '射击间隔',
                            f'{ug.get_effective_shoot_interval()}帧 (基{C.SHOOT_INT})', col_blue, lh)
        y = _draw_panel_row(surf, panel, y, '子弹速度', f'{C.BULLET_SPD}', col_blue, lh)
        y = _draw_panel_row(surf, panel, y, '子弹尺寸',
                            f'r={ug.get_effective_bullet_radius()} (+{p.bullet_size_bonus})', col_blue, lh)
        y += 4
        y = draw_title(y, '── 移动属性 ──', col_blue)
        spd_pen = getattr(p, 'heavy_armor_spd_penalty', 0.0)
        if spd_pen > 0:
            spd_detail = f'+{p.move_spd_bonus:.1f}/-{spd_pen:.1f}'
        else:
            spd_detail = f'+{p.move_spd_bonus:.1f}'
        y = _draw_panel_row(surf, panel, y, '移动速度',
                            f'{ug.get_effective_speed():.1f} ({spd_detail})', col_blue, lh)
        y = _draw_panel_row(surf, panel, y, '冲刺速度',
                            f'{ug.get_effective_sprint_speed():.1f}', col_blue, lh)
        y = _draw_panel_row(surf, panel, y, '玩家半径',
                            f'r={ug.get_effective_player_radius()} (基36, {p.player_size_bonus:+d})', col_blue, lh)
        y = _draw_panel_row(surf, panel, y, '燃料消耗',
                            f'{ug.get_effective_fuel_cost("normal"):.4f}/帧 (基{C.FUEL_COST})',
                            col_green if p.fuel_save_bonus > 0 else col_blue, lh)
        y += 4
        y = draw_title(y, '── 防御属性 ──', col_blue)
        y = _draw_panel_row(surf, panel, y, '最大耐久',
                            f'{ug.get_effective_max_dur()} (+{p.max_dur_bonus})', col_green, lh)
        reduction = ug.get_damage_reduction()
        if reduction < 0:
            y = _draw_panel_row(surf, panel, y, '伤害减免',
                                f'-{abs(reduction)} ({p.armor_bonus:+d})', col_green, lh)
        elif reduction > 0:
            y = _draw_panel_row(surf, panel, y, '伤害惩罚',
                                f'+{reduction} ({p.armor_bonus:+d})', col_red, lh)
        else:
            y = _draw_panel_row(surf, panel, y, '伤害减免',
                                f'0 ({p.armor_bonus:+d})', col_dim, lh)

    # ── page1：强化实时状态 + 敌人削弱 ──
    elif page == 1:
        t = _fontb.render('强化效果', True, col_white)
        surf.blit(t, (panel.left + 10, y))
        y += lh +4
        y = draw_sep(y)

        burn_stack = getattr(p, "bullet_burn_stack", 0)
        if burn_stack > 0:
            burn_dps = ug.get_burn_dps()
            burn_dur = ug.get_burn_duration_sec()
            y = _draw_panel_row(surf, panel, y, '燃烧弹药',
                                f"{burn_dps:.1f}/秒 持续{burn_dur:.1f}s ×{burn_stack}层", (255, 120, 40), lh)

        chain_stack = getattr(p, "chain_stack", 0)
        if chain_stack > 0:
            chain_r, chain_d = ug.get_chain_lightning_info(p)
            y = _draw_panel_row(surf, panel, y, '闪电弹药',
                                f"范围{chain_r:.0f} 伤害{chain_d:.0f} ×{chain_stack}层", (100, 180, 255), lh)

        shunt_stack = getattr(p, "missile_shunt_stack",0)
        if shunt_stack > 0:
            p_mul,e_mul = ug.get_missile_shunt_multipliers(p)
            y = _draw_panel_row(surf, panel, y, '爆破偏转',
                                f"自伤×{p_mul:.2f} 敌伤×{e_mul:.2f} ×{shunt_stack}层", (255,140,70), lh)

        counter_stack = getattr(p, "counter_strike_stack", 0)
        if counter_stack > 0:
            y = _draw_panel_row(surf, panel, y, '反击冲击',
                                f"挨打反击次数×{counter_stack} 单次伤害{C.COUNTER_STRIKE_DAMAGE}", (220, 120, 220), lh)

        lifesteal_stack = getattr(p, "lifesteal_stack",0)
        if lifesteal_stack >0:
            heal_per = ug.get_lifesteal_heal(p)
            y = _draw_panel_row(surf, panel, y, '浴血击杀',
                                f"击杀回复{heal_per}耐久 ×{lifesteal_stack}层", (210,70,70), lh)

        full_stack = getattr(p, "full_hp_power_stack",0)
        if full_stack >0:
            is_full, dmg_bonus = ug.get_full_hp_bonus_info(p)
            status_text = "[满血激活]" if is_full else "[未满血失效]"
            y = _draw_panel_row(surf, panel, y, '满盈之力',
                                f"+{C.FULL_HP_BONUS_DMG_PER_STACK*full_stack}子弹伤害 {status_text}", (100,220,220), lh)

        pierce_stack = getattr(p, "pierce_stack", 0)
        if pierce_stack > 0:
            y = _draw_panel_row(surf, panel, y, '破甲弹',
                                f"穿透次数{pierce_stack} 伤害+{pierce_stack * 12} 射速惩罚+{pierce_stack * 4}",
                                (180, 80, 220), lh)
        heavy_stack = getattr(p, "heavy_armor_stack", 0)
        if heavy_stack > 0:
            y = _draw_panel_row(surf, panel, y, '重型装甲',
                                f"减伤{C.HEAVY_ARMOR_DEF_PER_STACK*heavy_stack} "
                                f"速度-{p.heavy_armor_spd_penalty:.1f} "
                                f"×{heavy_stack}层",
                                (200, 140, 255), lh)
        collision_stack = getattr(p, "collision_damage_stack", 0)
        if collision_stack > 0:
            cdmg = C.COLLISION_DAMAGE_PER_STACK * collision_stack
            cpen = C.COLLISION_ARMOR_PENALTY_PER_STACK * collision_stack
            y = _draw_panel_row(surf, panel, y, '钢铁碰撞',
                                f"碰撞{cdmg} 受伤+{cpen} ×{collision_stack}层",
                                (220, 100, 220), lh)
        auto_aim_stack = getattr(p, "auto_aim_stack", 0)
        if auto_aim_stack > 0:
            interval = ug.get_effective_shoot_interval()
            dmg = ug.get_effective_bullet_dmg()
            y = _draw_panel_row(surf, panel, y, '自动瞄准',
                                f"射速{interval}帧 伤害{dmg} ×{auto_aim_stack}层",
                                (100, 220, 255), lh)
        bombardment_stack = getattr(p, "bombardment_stack", 0)
        if bombardment_stack > 0:
            bmult = ug.get_bombardment_damage_mult(p)
            spacing = ug.get_effective_missile_spacing()
            cnt_lo, cnt_hi = ug.get_effective_missile_count_range()
            count_text = f"{cnt_lo}~{cnt_hi}圈" if cnt_lo != cnt_hi else f"{cnt_lo}圈"
            y = _draw_panel_row(surf, panel, y, '强化轰炸',
                                f"伤害×{bmult:.2f} 间隔{spacing}帧",
                                (255, 140, 60), lh)
            y = _draw_panel_row(surf, panel, y, '　└ 轰炸圈',
                                f"{count_text} ×{bombardment_stack}层",
                                (255, 140, 60), lh)
        blood_pact_stack = getattr(p, "blood_pact_stack", 0)
        if blood_pact_stack > 0:
            bonus = C.BLOOD_PACT_MAX_DUR_PER_STACK * blood_pact_stack
            pct = int((1 - C.BLOOD_PACT_DUR_MULT) * 100)
            y = _draw_panel_row(surf, panel, y, '血祭',
                                f"上限+{bonus} 选择时血量-{pct}% ×{blood_pact_stack}层",
                                (220, 60, 120), lh)
        blood_oath_pending = getattr(p, 'blood_oath_pending', False)
        blood_oath_completed = getattr(p, 'blood_oath_completed', 0)
        if blood_oath_pending or blood_oath_completed > 0:
            if blood_oath_pending:
                prog = getattr(p, 'blood_oath_kills', 0)
                # 已完成层数作为附加信息
                suffix = f" 已完成{blood_oath_completed}层" if blood_oath_completed > 0 else ""
                y = _draw_panel_row(surf, panel, y, '杀戮契约',
                                    f"进度 {prog}/{C.BLOOD_OATH_KILL_TARGET}{suffix}",
                                    (220, 70, 70), lh)
            else:
                y = _draw_panel_row(surf, panel, y, '杀戮契约',
                                    f"已完成 {blood_oath_completed} 层",
                                    (220, 70, 70), lh)
        overload_stack = getattr(p, 'overload_reaction_stack', 0)
        if overload_stack > 0:
            chain = getattr(p, 'chain_stack', 0)
            burn = getattr(p, 'bullet_burn_stack', 0)
            mult = ug.get_overload_damage_mult(p)
            if chain > 0 and burn > 0:
                # 已具备完整触发条件
                detail = f"闪电{chain}×燃烧{burn} 伤害×{mult:.2f}"
                color = (255, 215, 0)
            elif chain == 0:
                # 缺闪电，无法触发
                detail = f"需闪电层数 (当前×{mult:.2f})"
                color = (140, 120, 60)
            else:
                # 有闪电但燃烧层为0，无法触发
                detail = f"需燃烧层数 (当前×{mult:.2f})"
                color = (140, 120, 60)
            y = _draw_panel_row(surf, panel, y, '超载反应', detail, color, lh)
        barrage_stack = getattr(p, 'bombardment_mode_stack', 0)
        if barrage_stack > 0:
            lo, hi = ug.get_effective_missile_count_range()
            lo += C.BOMBARDMENT_MODE_COUNT_BONUS
            hi += C.BOMBARDMENT_MODE_COUNT_BONUS
            count_text = f"{lo}~{hi}圈" if lo != hi else f"{lo}圈"
            y = _draw_panel_row(surf, panel, y, '轰炸协议',
                                f"无子弹 {C.BOMBARDMENT_MODE_SPACING}帧/{count_text} 敌伤×{C.BOMBARDMENT_MODE_DMG_MULT:.1f}",
                                (255, 215, 0), lh)
        volley_stack = getattr(p, 'volley_protocol_stack', 0)
        if volley_stack > 0:
            cur_bcount = p.bcount + p.strengthen_bcount
            y = _draw_panel_row(surf, panel, y, '齐射协议',
                                f"当前{cur_bcount}发 无限穿透 伤害×{C.VOLLEY_PROTOCOL_DMG_MULT:.1f}",
                                (255, 215, 0), lh)
        bloodlust_stack = getattr(p, 'bloodlust_stack', 0)
        if bloodlust_stack > 0:
            max_dur = ug.get_effective_max_dur()
            hp_pct = int(p.dur / max_dur * 100) if max_dur > 0 else 0
            mult = ug.get_bloodlust_damage_mult(p)
            # 血量越低颜色越红（30% 以下深红，50% 以下橙红，其余橙色）
            if hp_pct <= 30:
                color = (255, 60, 60)
            elif hp_pct <= 50:
                color = (255, 130, 80)
            else:
                color = (255, 180, 100)
            y = _draw_panel_row(surf, panel, y, '血怒',
                                f"HP{hp_pct}% 伤害×{mult:.2f}",
                                color, lh)
        shield_charge_stack = getattr(p, 'shield_charge_stack', 0)
        if shield_charge_stack > 0:
            if p.shield_active:
                detail = "护盾激活 · 无耗油"
                color = (100, 220, 255)
            else:
                frames = getattr(p, 'shield_charge_timer', 0)
                sec = frames / C.FPS
                total_sec = C.SHIELD_CHARGE_FRAMES / C.FPS
                detail = f"充能中 {sec:.1f}/{total_sec:.0f}s"
                color = (80, 180, 240)
            y = _draw_panel_row(surf, panel, y, '静海协议', detail, color, lh)
        revive_stack = getattr(p, 'revive_stack', 0)
        if revive_stack > 0:
            if getattr(p, 'revive_used', False):
                detail = "已用尽"
                color = (150, 130, 80)
            else:
                detail = f"待触发 回复{int(C.REVIVE_HEAL_RATIO * 100)}% 无敌{C.REVIVE_INVINCIBLE_FRAMES // C.FPS}s"
                color = (255, 215, 0)
            y = _draw_panel_row(surf, panel, y, '不屈意志', detail, color, lh)
        death_ring_stack = getattr(p, 'death_ring_stack', 0)
        if death_ring_stack > 0:
            ring_dmg = max(1, int(ug.get_effective_bullet_dmg() * C.DEATH_RING_DMG_RATIO))
            y = _draw_panel_row(surf, panel, y, '死亡回响',
                                f"击杀{ C.DEATH_RING_BULLET_COUNT}发弹幕 单发{ring_dmg}",
                                (255, 215, 0), lh)
        fire_breath_stack = getattr(p, 'fire_breath_stack', 0)
        if fire_breath_stack > 0:
            cd = getattr(p, 'fire_breath_cd', 0)
            if cd <= 0:
                detail = f"就绪 · {C.FIRE_BREATH_DAMAGE}伤 扇形{C.FIRE_BREATH_HALF_ANGLE*2}°"
                color = (255, 120, 40)
            else:
                cd_sec = cd / C.FPS
                detail = f"冷却 {cd_sec:.1f}s · {C.FIRE_BREATH_DAMAGE}伤"
                color = (180, 100, 60)
            y = _draw_panel_row(surf, panel, y, '烈焰喷射', detail, color, lh)

        y += 4
        y = draw_title(y, '── 对敌人削弱 ──', col_red)
        slow_bonus = p.enemy_bullet_slow_bonus
        if slow_bonus > 0:
            y = _draw_panel_row(surf, panel, y, '敌方子弹速度',
                                f'-{slow_bonus:.1f}', col_red, lh)
        else:
            y = _draw_panel_row(surf, panel, y, '敌方子弹速度', '无削弱', col_dim, lh)

        fuel_save = p.fuel_save_bonus
        if fuel_save > 0:
            y = _draw_panel_row(surf, panel, y, '燃料节省', f'{fuel_save}%', col_green, lh)
        else:
            y = _draw_panel_row(surf, panel, y, '燃料消耗', '无节省', col_dim, lh)

    # ── page2：已获取强化列表 ──
    elif page == 2:
        t = _fontb.render('已获取强化列表', True, col_white)
        surf.blit(t, (panel.left + 10, y))
        y += lh +4
        y = draw_sep(y)

        history = ug.get_upgrade_history()
        if not history:
            t = _font.render('（暂无强化）', True, col_dim)
            surf.blit(t, (panel.left + 10, y))
        else:
            for item in history:
                count_text = f'×{item["count"]}' if item["count"] > 1 else ''
                label = f'{item["icon"]} {item["name"]}'
                if count_text:
                    label += f'  {count_text}'
                t = _font.render(label, True, col_green)
                surf.blit(t, (panel.left + 10, y))
                y += lh

    # 翻页提示：一共3页
    page_hint = f'按 ← → 翻页 (第{page+1}/3页)'
    hint = _font.render(page_hint, True, (80, 100, 130))
    surf.blit(hint, (panel.left + 10, panel.bottom - 28))


_font = None
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
    eff_max_dur = ug.get_effective_max_dur()
    draw_bar(surf, m, m,            bar_w, 14, p.dur / eff_max_dur,
             (40, 185, 80), (18, 55, 28), f'耐久 {int(p.dur)}/{int(eff_max_dur)}')
    draw_bar(surf, m, m + 18,       bar_w, 14, p.fuel / C.MAX_FUEL,
             (225, 185, 40), (75, 55, 10), f'燃料 {int(p.fuel)}')

    if game_state.story_mode:
        # 故事模式：显示当前波次/目标
        t = _font.render(f'波次 {game_state.wm.wave}/{game_state.wm.target_waves}', True, (255, 220, 120))
        surf.blit(t, (C.W // 2 - t.get_width() // 2, m))
    else:
        # 生存模式（无尽）：显示波次、阶段和得分
        wave = game_state.wm.wave
        stage_idx = (wave - 1) // C.WAVE_STAGE_LENGTH + 1  # 1-based 阶段号
        roman = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
        stage_label = roman[stage_idx - 1] if stage_idx <= len(roman) else str(stage_idx)
        stage_color = (255, 180, 60) if stage_idx > 1 else C.C_WHITE
        wave_txt = _font.render(f'波次 {wave} (阶段 {stage_label})', True, stage_color)
        surf.blit(wave_txt, (C.W // 2 - wave_txt.get_width() // 2, m))
        score_txt = _font.render(f'得分 {p.score}', True, C.C_DIM)
        surf.blit(score_txt, (C.W // 2 - score_txt.get_width() // 2, m + 22))

def draw_pause_button(surf):
    """绘制右上角：面板按钮 + 暂停按钮 + 静音按钮 + 右侧调试三角箭头"""
    _ensure_fonts()
    btn_h, btn_w = 28, 36
    # 面板按钮（最右）
    panel_btn = pygame.Rect(C.W - 56, 14, btn_w, btn_h)
    hover_p = panel_btn.collidepoint(pygame.mouse.get_pos())
    col_p = (60, 95, 55) if hover_p else (40, 65, 38)
    pygame.draw.rect(surf, col_p, panel_btn, border_radius=4)
    pygame.draw.rect(surf, C.C_WHITE, panel_btn, 1, border_radius=4)
    # 小人图标（两条线代表面板）
    cx, cy = panel_btn.centerx, panel_btn.centery
    pygame.draw.line(surf, C.C_WHITE, (cx - 6, cy - 6), (cx + 6, cy - 6), 2)
    pygame.draw.line(surf, C.C_WHITE, (cx - 6, cy + 6), (cx + 6, cy + 6), 2)
    pygame.draw.line(surf, C.C_WHITE, (cx - 3, cy - 6), (cx - 3, cy + 6), 2)

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
    return btn, dbg, mute_btn, panel_btn


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
    draw_btn(screen, menu_btn,      '返  回  菜  单', C.BTN_MENU,    C.BTN_MENU_H,   _fontb)
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

    _DEBUG_W = 260
    _DEBUG_X = C.W - _DEBUG_W - 20
    panel = pygame.Rect(_DEBUG_X, 50, _DEBUG_W, C.H - 100)
    pygame.draw.rect(screen, (15, 20, 35, 230), panel, border_radius=8)
    pygame.draw.rect(screen, (80, 100, 140), panel, 2, border_radius=8)

    # 标题
    t = _fontb.render('调  试  面  板', True, (200, 200, 255))
    screen.blit(t, (panel.centerx - t.get_width() // 2, panel.top + 10))

    y = panel.top + 45
    line_h = 26
    btn_h = 28
    btn_w = 110
    buttons = []

    # =========【移除：耐久/燃料/伤害状态文本，不再绘制】========

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
    t = _font.render('跳到下一波', True, C.C_WHITE)
    screen.blit(t, (btn_next.centerx - t.get_width() // 2, btn_next.centery - 8))
    buttons.append(('next_wave', btn_next))
    y += btn_h + 6

    # 伤害+10
    btn_up = pygame.Rect(panel.left + 8, y, btn_w, btn_h)
    hover_up = btn_up.collidepoint(pygame.mouse.get_pos())
    c_up = (100, 40, 40) if hover_up else (70, 25, 25)
    pygame.draw.rect(screen, c_up, btn_up, border_radius=4)
    t = _font.render('+伤害', True, C.C_WHITE)
    screen.blit(t, (btn_up.centerx - t.get_width() // 2, btn_up.centery - 8))
    buttons.append(('dmg_up', btn_up))

    # 清除敌军
    btn_clear = pygame.Rect(panel.left + 8 + btn_w + 6, y, btn_w, btn_h)
    hover_clear = btn_clear.collidepoint(pygame.mouse.get_pos())
    c_clear = (100, 60, 40) if hover_clear else (70, 40, 25)
    pygame.draw.rect(screen, c_clear, btn_clear, border_radius=4)
    t = _font.render('清除敌军', True, C.C_WHITE)
    screen.blit(t, (btn_clear.centerx - t.get_width() // 2, btn_clear.centery - 8))
    buttons.append(('clear', btn_clear))
    y += btn_h + 6

    # 触发死亡
    btn_die = pygame.Rect(panel.left + 8, y, btn_w * 2 + 14, btn_h)
    hover_die = btn_die.collidepoint(pygame.mouse.get_pos())
    c_die = (80, 25, 25) if hover_die else (55, 18, 18)
    pygame.draw.rect(screen, c_die, btn_die, border_radius=4)
    t = _font.render('触发死亡结局', True, (200, 80, 80))
    screen.blit(t, (btn_die.centerx - t.get_width() // 2, btn_die.centery - 8))
    buttons.append(('die', btn_die))
    y += btn_h + 10

    # 分割线
    y += 2
    pygame.draw.line(screen, (60, 100, 160),
                     (panel.left + 8, y), (panel.right - 8, y))
    y += line_h

    t = _font.render('强 化 测 试', True, (100, 200, 100))
    screen.blit(t, (panel.left + 10, y))
    y += line_h

    import upgrades as ug
    btn_w2 = 74
    btn_h2 = 24
    col_up = (25, 60, 35)
    col_up_h = (40, 95, 50)
    gap_x = 6
    per_row = 3

    # 循环生成强化按钮，严格限定在panel内部
    for idx, upg in enumerate(ug.ALL_UPGRADES):
        col_idx = idx % per_row
        row_idx = idx // per_row
        bx = panel.left + 8 + col_idx * (btn_w2 + gap_x)
        by = y + row_idx * (btn_h2 + 4)
        btn = pygame.Rect(bx, by, btn_w2, btn_h2)
        hover = btn.collidepoint(pygame.mouse.get_pos())
        is_maxed = ug.is_upgrade_reached_max(player, upg.key)

        if is_maxed:
            btn_color = (45, 45, 45)
            text_color = (90, 90, 90)
        else:
            btn_color = col_up_h if hover else col_up
            text_color = C.C_WHITE

        pygame.draw.rect(screen, btn_color, btn, border_radius=4)
        label = f'{upg.order}'
        t = _font.render(label, True, text_color)
        screen.blit(t, (btn.centerx - t.get_width() // 2, btn.centery - 7))
        # ✅强化按钮：三元组
        buttons.append((f'upgrade_{upg.key}', btn, is_maxed))

    # 计算强化按钮区域总高度，移动y到强化按钮下方
    total_rows = (len(ug.ALL_UPGRADES) + per_row -1) // per_row
    y = y + total_rows * (btn_h2 +4) + 8

    # 底部提示
    t = _font.render('点击右侧箭头关闭', True, (80, 80, 100))
    screen.blit(t, (panel.centerx - t.get_width() // 2, panel.bottom - 30))

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
        draw_btn(screen, menu_btn,    '返回主菜单',  C.BTN_MENU,    C.BTN_MENU_H,  _fontb)
        pygame.display.flip()
        clock.tick(C.FPS)
