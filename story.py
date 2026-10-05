"""
海上军舰 - 故事模式对话系统
负责从 text.txt 解析剧情、显示 Galgame 风格对话。
对话按角色分段显示，点击或按空格继续。
"""
import re
import pygame
import constants as C
from utils import get_resource_path

# ─── 对话数据结构 ────────────────────────────────────────
class DialogueLine:
    """一行对话或叙述"""
    def __init__(self, speaker, text, is_narration=False):
        self.speaker = speaker     # '玩家'/'老周'/'邓世昌'/'丁汝昌'/None(叙述)
        self.text = text
        self.is_narration = is_narration


class StoryAct:
    """一场剧情演出（含多行对话）"""
    def __init__(self, title, scene_desc, lines, cg_index=0):
        self.title = title
        self.scene_desc = scene_desc
        self.lines = lines  # list of DialogueLine
        self.cg_index = cg_index  # 0-3 对应 cg1~cg4，-1 无背景


# ─── 字体（延迟初始化） ────────────────────────────────────
_dialog_font  = None
_dialog_name  = None
_act_title    = None
_scene_font   = None


def _ensure_fonts():
    """确保 pygame 已初始化并创建字体"""
    global _dialog_font, _dialog_name, _act_title, _scene_font
    if _dialog_font is None:
        _dialog_font  = pygame.font.SysFont('microsoftyahei', 20)
        _dialog_name  = pygame.font.SysFont('microsoftyahei', 22, bold=True)
        _act_title    = pygame.font.SysFont('microsoftyahei', 32, bold=True)
        _scene_font   = pygame.font.SysFont('microsoftyahei', 18)


# ─── 解析 text.txt ───────────────────────────────────────
def _parse_story(path):
    """从 text.txt 解析出 4 幕剧情 + 3 个结局"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return [], []

    acts = []
    endings = []

    # 分割段落：### 标记新幕，"结局X" 标记结局
    # 同时支持 "### 结局X" 和纯 "结局X" 两种格式
    sections = re.split(r'(?=### |\n结局[一二三]：)', content)
    act_counter = 0  # 用于为每幕分配 cg_index
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 检测是否结局
        ending_match = re.match(r'(?:###\s*)?结局[一二三]：\s*(.*)', section)
        if ending_match:
            ending_title = ending_match.group(1).strip()
            lines = _extract_dialogue(section)
            # 结局根据标题决定 CG
            if '胜利' in ending_title:
                cg = 'win'
            else:
                cg = 'ending'
            endings.append({'title': ending_title, 'lines': lines, 'cg': cg})
            continue

        # 检测是否幕
        act_match = re.match(r'###\s*(第.*?幕.*?)(?=\n|$)', section)
        if act_match:
            title = act_match.group(1).strip()
            lines = _extract_dialogue(section)
            # 提取场景描述
            scene_match = re.search(r'\*\*场景\*\*：(.*?)\n', section, re.DOTALL)
            scene_desc = scene_match.group(1).strip() if scene_match else ''
            # 按顺序分配 cg_index (0-3)
            cg_idx = min(act_counter, 3)
            act_counter += 1
            acts.append(StoryAct(title, scene_desc, lines, cg_index=cg_idx))

    return acts, endings


def _extract_dialogue(section):
    """从一段剧情文本中提取对话行和叙述行"""
    lines = []

    for raw_line in section.split('\n'):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        # 跳过标题行和分隔线
        if raw_line.startswith('###') or raw_line.startswith('##') or raw_line == '---':
            continue
        # 跳过 **对话** 标记行
        if raw_line in ('**场景**', '**对话**', '**核心走向**'):
            continue

        # 检测对话：角色（动作）：内容 或 角色：内容
        dm = re.match(r'(玩家|老周|邓世昌|丁汝昌)[（(].*?[）)]：(.+)', raw_line)
        if dm:
            speaker = dm.group(1)
            text = dm.group(2).strip()
            lines.append(DialogueLine(speaker, text))
            continue

        # 检测对话：角色：内容（无括号动作）
        dm2 = re.match(r'(玩家|老周|邓世昌|丁汝昌)：(.+)', raw_line)
        if dm2:
            speaker = dm2.group(1)
            text = dm2.group(2).strip()
            lines.append(DialogueLine(speaker, text))
            continue

        # 处理加粗段落：**场景**：xxx → 提取xxx作为旁白
        bold_match = re.match(r'^\*\*(.+?)\*\*：(.+)$', raw_line)
        if bold_match:
            text = bold_match.group(2).strip()
            lines.append(DialogueLine(None, text, is_narration=True))
            continue

        # 去掉行内 **...** 标记
        cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', raw_line)
        cleaned = cleaned.strip()
        if cleaned:
            lines.append(DialogueLine(None, cleaned, is_narration=True))

    return lines


# ─── Galgame 对话渲染 ────────────────────────────────────
def show_dialogue(screen, clock, act, skip_callback=None):
    """
    显示一场剧情对话，Galgame 风格。
    背景为对应 CG 图（如有），对话框在底部。
    无幕标题，旁白直接居中显示。
    """
    _ensure_fonts()
    lines = act.lines
    if not lines:
        return True

    # 加载 CG 背景
    import assets
    cg = None
    cg_idx = getattr(act, 'cg_index', None)
    if cg_idx is not None and 0 <= cg_idx < 4:
        cg = assets.PLOT_CG[cg_idx]

    # 角色颜色
    SPEAKER_COLORS = {
        '玩家':    (220, 230, 255),
        '老周':    (200, 180, 140),
        '邓世昌':  (255, 200, 150),
        '丁汝昌':  (180, 200, 220),
    }

    # 淡入黑幕
    for alpha in range(0, 256, 16):
        overlay = pygame.Surface((C.W, C.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        clock.tick(C.FPS)

    # 对话框位置（底部，增加高度以容纳更多行）
    DIALOG_X = 40
    DIALOG_Y = C.H - 180
    DIALOG_W = C.W - 80
    DIALOG_H = 140

    for line_idx, line in enumerate(lines):
        done = False
        # 按对话框高度自动分割超长文本
        display_lines = _split_dialogue_line(line, DIALOG_H, DIALOG_W)
        for dl in display_lines:
            while not done:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit(); __import__('sys').exit()
                    if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                        if ev.type == pygame.KEYDOWN and ev.key not in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                            continue
                        done = True
                        if skip_callback and ev.type == pygame.MOUSEBUTTONDOWN:
                            skip_callback()
                        break

                # 绘制 CG 背景（如有）
                if cg is not None:
                    screen.blit(cg, (0, 0))
                else:
                    screen.fill(C.C_SEA)
                # 绘制对话框
                _draw_dialogue_box(screen, dl, DIALOG_X, DIALOG_Y, DIALOG_W, DIALOG_H, SPEAKER_COLORS)
                pygame.display.flip()
                clock.tick(C.FPS)

    return True


def _draw_dialogue_box(screen, line, x, y, w, h, speaker_colors):
    """绘制 Galgame 风格对话框（半透明底 + 角色名 + 对话文字）"""
    # 底部半透明对话框背景
    box = pygame.Surface((w, h), pygame.SRCALPHA)
    box.fill((10, 15, 30, 200))
    screen.blit(box, (x, y))
    # 边框
    pygame.draw.rect(screen, (100, 130, 170), (x, y, w, h), 2, border_radius=6)

    if line.is_narration:
        # 旁白：居中，淡色，小字体
        wrapped = _wrap_text(line.text, w - 40, _dialog_font)
        for i, para in enumerate(wrapped):
            t = _dialog_font.render(para, True, (180, 180, 180))
            screen.blit(t, (x + w // 2 - t.get_width() // 2, y + h // 2 - 10 + i * 24))
    else:
        # 角色对话
        color = speaker_colors.get(line.speaker, C.C_WHITE)
        # 角色名（左上角）
        name_t = _dialog_name.render(line.speaker, True, color)
        screen.blit(name_t, (x + 10, y + 10))
        # 对话内容
        wrapped = _wrap_text(line.text, w - 20, _dialog_font)
        for i, para in enumerate(wrapped):
            t = _dialog_font.render(para, True, C.C_WHITE)
            screen.blit(t, (x + 10, y + 40 + i * 24))

    # 提示
    t = _dialog_font.render('按空格或点击继续', True, (120, 120, 120))
    screen.blit(t, (x + w - t.get_width() - 8, y + h - 28))


def _split_dialogue_line(line, dialog_h, dialog_w):
    """如果文本折行超出对话框高度则分段，返回需要依次显示的 DialogueLine 列表"""
    _ensure_fonts()
    max_rows = (dialog_h - 40) // 24  # 角色名行(22px) + 提示行(20px) 约40px
    # 估算折行后的行数（与 _draw_dialogue_box 中一致）
    wrapped = _wrap_text(line.text, dialog_w - 20, _dialog_font)
    if len(wrapped) <= max_rows:
        return [line]
    # 超出行数：将文本分段，每段最多 max_rows 行
    parts = []
    for i in range(0, len(wrapped), max_rows):
        chunk = wrapped[i:i + max_rows]
        parts.append(DialogueLine(line.speaker, '\n'.join(chunk),
                                  is_narration=line.is_narration))
    return parts


def _wrap_text(text, max_width, font):
    """将长文本按最大宽度折行"""
    words = list(text)
    wrapped = []
    current = []
    current_w = 0
    for w in words:
        tw = font.size(w)[0]
        if current_w + tw > max_width and current:
            wrapped.append(''.join(current))
            current = [w]
            current_w = tw
        else:
            current.append(w)
            current_w += tw
    if current:
        wrapped.append(''.join(current))
    return wrapped


def show_ending(screen, clock, ending, skip_callback=None):
    """显示结局对话（Galgame风格，底部对话框）"""
    _ensure_fonts()
    lines = ending['lines']
    if not lines:
        return True

    # 加载 CG 背景
    import assets
    cg_key = ending.get('cg', 'ending')
    if cg_key == 'win':
        cg = assets.PLOT_WIN
    else:
        cg = assets.PLOT_ENDING

    # 淡入黑幕
    for alpha in range(0, 256, 16):
        overlay = pygame.Surface((C.W, C.H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        screen.blit(overlay, (0, 0))
        pygame.display.flip()
        clock.tick(C.FPS)

    SPEAKER_COLORS = {
        '玩家':    (220, 230, 255),
        '老周':    (200, 180, 140),
        '邓世昌':  (255, 200, 150),
        '丁汝昌':  (180, 200, 220),
    }

    DIALOG_X = 40
    DIALOG_Y = C.H - 150
    DIALOG_W = C.W - 80
    DIALOG_H = 160  # 结局对话更长，增加对话框高度

    # 显示结局标题（半屏提示）
    screen.fill((*C.C_DARK[:3], 220))
    t = _act_title.render(ending['title'], True, (255, 100, 100))
    screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 80))
    t = _dialog_font.render('历史将无法改变……', True, (150, 150, 150))
    screen.blit(t, (C.W // 2 - t.get_width() // 2, C.H // 2 - 30))
    pygame.display.flip()
    clock.tick(C.FPS)
    _wait_for_continue(screen, clock)

    # 逐行显示结局对话
    for line in lines:
        done = False
        # 按对话框高度自动分割超长文本
        display_lines = _split_dialogue_line(line, DIALOG_H, DIALOG_W)
        for dl in display_lines:
            while not done:
                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit(); __import__('sys').exit()
                    if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                        if ev.type == pygame.KEYDOWN and ev.key not in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                            continue
                        done = True
                        if skip_callback and ev.type == pygame.MOUSEBUTTONDOWN:
                            skip_callback()
                        break
                # 绘制 CG 背景（如有）
                if cg is not None:
                    screen.blit(cg, (0, 0))
                else:
                    screen.fill(C.C_DARK)
                _draw_dialogue_box(screen, dl, DIALOG_X, DIALOG_Y, DIALOG_W, DIALOG_H, SPEAKER_COLORS)
                pygame.display.flip()
                clock.tick(C.FPS)

    return True


def _wait_for_continue(screen, clock):
    """等待用户确认继续"""
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); __import__('sys').exit()
            if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                if ev.type == pygame.KEYDOWN and ev.key not in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                    continue
                return


# ─── 初始化 ───────────────────────────────────────────────
def load_story():
    """加载故事数据，返回 (acts, endings)"""
    path = get_resource_path("text.txt")
    return _parse_story(path)
