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

    def start(self, story_mode=False, story_battle=0):
        """生成当前波次的敌人队列，敌人从屏幕四周随机位置生成"""
        self.story_mode = story_mode
        self.story_battle = story_battle
        self.wave_just_started = True  # 标记波次刚推进，供外部消费一次
        # 根据模式确定目标波次
        if story_mode:
            wins = [C.WIN_WAVES_STORY1, C.WIN_WAVES_STORY2, C.WIN_WAVES_STORY3]
            self.target_waves = wins[min(story_battle, 2)]
        else:
            self.target_waves = C.WIN_WAVES
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
                # 生存模式
                if self.wave < 3:
                    etype = 'scout'
                elif self.wave < 6:
                    etype = 'scout' if r < 0.6 else 'cruiser'
                else:
                    if r < 0.4:
                        etype = 'scout'
                    elif r < 0.75:
                        etype = 'cruiser'
                    else:
                        etype = 'battleship'
            self.queue.append((ex, ey, etype))
        self.stimer = 0
        self.timer = 0

    def _calc_enemy_count(self):
        """根据模式计算敌人数"""
        if self.story_mode:
            return 3 + self.wave * 2
        return 3 + self.wave * 2

    def update(self):
        """更新波次逻辑：等待敌人清空后推进波次，同时按节奏生成敌人"""
        self.timer += 1
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
