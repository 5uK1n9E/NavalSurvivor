"""
海上军舰 - 波次管理
负责生成敌人队列并按节奏播发。
敌人在等待期间也可继续生成（不提前 return）。
波次推进条件：当前波次敌人全部消灭且等待 3 秒。
"""
import random
import math
import constants as C
from entities import mk_enemy

game_state = None

class WaveManager:
    def __init__(self):
        self.wave = 1
        self.timer = 0
        self.queue = []
        self.stimer = 0
        self.story_mode = False
        self.story_battle = 0
        self.wave_just_started = False

    def start(self, story_mode=False, story_battle=0):
        """生成当前波次的敌人队列，敌人从屏幕四周随机位置生成"""
        if game_state is None:
            return
        self.story_mode = story_mode
        self.story_battle = story_battle
        self.wave_just_started = True  # 标记波次刚推进，供外部消费一次
        # 根据模式确定目标波次
        if story_mode:
            wins = [C.WIN_WAVES_STORY1, C.WIN_WAVES_STORY2, C.WIN_WAVES_STORY3]
            self.target_waves = wins[min(story_battle, 2)]
        else:
            self.target_waves = 9999  # 无尽模式：不设上限
        # 不重置 wave，只重置队列和计时器
        n = self._calc_enemy_count()
        self.queue = []
        for _ in range(n):
            angle = random.uniform(0, math.tau)
            radius = random.randint(350, 580)
            ex = C.clamp(
                game_state.player.x + math.cos(angle) * radius, 40, C.W - 40)
            ey = C.clamp(
                game_state.player.y + math.sin(angle) * radius, 40, C.H - 40)
            r = random.random()
            if self.story_mode:
                # 故事模式：三战难度递增
                if story_battle == 0:
                    etype = 'scout' if r < 0.7 else ('cruiser' if r < 0.9 else 'battleship')
                elif story_battle == 1:
                    etype = 'scout' if r < 0.5 else ('cruiser' if r < 0.8 else 'battleship')
                else:
                    etype = 'scout' if r < 0.3 else ('cruiser' if r < 0.65 else 'battleship')
            else:
                # 生存模式：按阶段递进
                stage = (self.wave - 1) // C.WAVE_STAGE_LENGTH
                if stage == 0:
                    # 第 1~10 波：引入期
                    if self.wave < 3:
                        etype = 'scout'
                    elif self.wave < 6:
                        etype = 'scout' if r < 0.6 else 'cruiser'
                    else:
                        etype = 'scout' if r < 0.4 else ('cruiser' if r < 0.75 else 'battleship')
                elif stage == 1:
                    # 第 11~20 波：battleship 明显增加
                    etype = 'scout' if r < 0.30 else ('cruiser' if r < 0.70 else 'battleship')
                elif stage == 2:
                    # 第 21~30 波：cruiser 主导
                    etype = 'scout' if r < 0.20 else ('cruiser' if r < 0.60 else 'battleship')
                else:
                    # 第 31 波起：精英化
                    etype = 'scout' if r < 0.15 else ('cruiser' if r < 0.55 else 'battleship')
            self.queue.append((ex, ey, etype))
        self.stimer = 0
        self.timer = 0

    def _calc_enemy_count(self):
        """根据模式计算敌人数"""
        if self.story_mode:
            return 3 + self.wave * 2
        # 生存模式：阶段内线性 + 每 10 波额外跃升
        stage = (self.wave - 1) // C.WAVE_STAGE_LENGTH
        return 3 + self.wave * C.WAVE_COUNT_PER_WAVE + stage * C.WAVE_COUNT_STAGE_BONUS

    def update(self):
        """更新波次逻辑：等待敌人清空后推进波次，同时按节奏生成敌人"""
        if game_state is None:
            return

        self.timer += 1

        # 卡牌触发点
        if not game_state.story_mode and game_state.state == 'playing' and not game_state.showing_cards:
            if not game_state.enemies and not self.queue:
                next_wave = self.wave + 1
                if (next_wave % C.CARD_WAVE_INTERVAL == 0
                        and next_wave > game_state.last_card_wave):
                    # 触发卡牌选择
                    game_state.last_card_wave = next_wave
                    self.timer = 0
                    game_state.showing_cards = True
                    game_state.state = 'card_select'
                    return  # 直接 return，本帧不再执行波次增加、生成新敌人

        if not game_state.enemies:
            if self.timer >= 180:  # >= 不是 >，确保3秒后触发
                if self.wave < self.target_waves:
                    self.wave += 1
                    self.start(self.story_mode, self.story_battle)
        # 继续检查队列，让敌人在等待期间也能生成
        if self.queue:
            self.stimer += 1
            if self.stimer >= 15:
                ex, ey, etype = self.queue.pop(0)
                game_state.enemies.append(mk_enemy(ex, ey, etype, self.wave, self.story_mode, self.story_battle))
                self.stimer = 0

