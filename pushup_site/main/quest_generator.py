from datetime import timedelta
from django.utils import timezone
import random


class QuestGenerator:
    """Генератор квестов для канонических упражнений + табата + бег."""

    def __init__(self, player):
        self.player = player

    def generate_initial_quests(self):
        quests_data = [self._create_daily_login_quest()]
        exercise_quests = [
            self._create_pushup_quest(),
            self._create_squat_quest(),
            self._create_crunch_quest(),
            self._create_pullup_quest(),
            self._create_tabata_quest(),
            self._create_run_quest(),
        ]
        quests_data.extend(random.sample(exercise_quests, 3))
        return quests_data

    def generate_daily_quests(self):
        quests_data = [self._create_daily_login_quest()]
        exercise_quests = [
            self._create_pushup_quest(),
            self._create_squat_quest(),
            self._create_crunch_quest(),
            self._create_pullup_quest(),
            self._create_tabata_quest(),
            self._create_run_quest(),
        ]
        quests_data.extend(random.sample(exercise_quests, 3))
        return quests_data

    def generate_weekly_quests(self):
        return [
            self._create_weekly_pushup_quest(),
            self._create_weekly_squat_quest(),
            self._create_weekly_pullup_quest(),
        ]

    def _create_pushup_quest(self):
        goal = random.randint(5, 15) + (self.player.level * 2)
        return {
            "title": "💪 Сила отжиманий",
            "description": f"Выполни {goal} классических отжиманий",
            "quest_type": "PUSHUP",
            "goal": goal,
            "progress": 0,
            "difficulty": 1,
            "reward_xp": goal * 5 // 2,
            "reward_currency": goal * 3,
            "reward_skill_points": 1 if goal >= 20 else 0,
            "expires_at": timezone.now() + timedelta(days=1),
            "is_daily": True,
            "is_boss_quest": False,
        }

    def _create_squat_quest(self):
        goal = random.randint(10, 20) + (self.player.level * 3)
        return {
            "title": "🦵 Выносливость ног",
            "description": f"Выполни {goal} классических приседаний",
            "quest_type": "SQUAT",
            "goal": goal,
            "progress": 0,
            "difficulty": 1,
            "reward_xp": goal * 2,
            "reward_currency": goal * 2,
            "reward_skill_points": 1 if goal >= 25 else 0,
            "expires_at": timezone.now() + timedelta(days=1),
            "is_daily": True,
            "is_boss_quest": False,
        }

    def _create_pullup_quest(self):
        goal = random.randint(3, 8) + self.player.level
        return {
            "title": "🎯 Сила хвата",
            "description": f"Выполни {goal} классических подтягиваний",
            "quest_type": "PULLUP",
            "goal": goal,
            "progress": 0,
            "difficulty": 2,
            "reward_xp": goal * 8,
            "reward_currency": goal * 4,
            "reward_skill_points": 1 if goal >= 10 else 0,
            "expires_at": timezone.now() + timedelta(days=1),
            "is_daily": True,
            "is_boss_quest": False,
        }

    def _create_crunch_quest(self):
        goal = random.randint(15, 25) + (self.player.level * 4)
        return {
            "title": "🔥 Пресс сталь",
            "description": f"Выполни {goal} классических скручиваний",
            "quest_type": "CRUNCH",
            "goal": goal,
            "progress": 0,
            "difficulty": 1,
            "reward_xp": goal * 3 // 2,
            "reward_currency": goal * 2,
            "reward_skill_points": 1 if goal >= 30 else 0,
            "expires_at": timezone.now() + timedelta(days=1),
            "is_daily": True,
            "is_boss_quest": False,
        }

    def _create_tabata_quest(self):
        return {
            "title": "⚡ Табата",
            "description": "Заверши 1 табата-тренировку",
            "quest_type": "TABATA",
            "goal": 1,
            "progress": 0,
            "difficulty": 2,
            "reward_xp": 40,
            "reward_currency": 30,
            "reward_skill_points": 1,
            "expires_at": timezone.now() + timedelta(days=1),
            "is_daily": True,
            "is_boss_quest": False,
        }

    def _create_run_quest(self):
        goal_km = 2
        return {
            "title": "🏃 Бег",
            "description": f"Пробеги {goal_km} км",
            "quest_type": "RUN",
            "goal": goal_km,
            "progress": 0,
            "difficulty": 2,
            "reward_xp": 50,
            "reward_currency": 35,
            "reward_skill_points": 1,
            "expires_at": timezone.now() + timedelta(days=1),
            "is_daily": True,
            "is_boss_quest": False,
        }

    def _create_daily_login_quest(self):
        return {
            "title": "📅 Ежедневный вход",
            "description": "Зайди в приложение чтобы получить бонус!",
            "quest_type": "DAILY_LOGIN",
            "goal": 1,
            "progress": 0,
            "difficulty": 1,
            "reward_xp": 25,
            "reward_currency": 25,
            "reward_skill_points": 0,
            "expires_at": timezone.now() + timedelta(days=1),
            "is_daily": True,
            "is_boss_quest": False,
        }

    def _create_weekly_pushup_quest(self):
        goal = 60 + (self.player.level * 10)
        return {
            "title": "🏆 Недельная сила",
            "description": f"Сделай {goal} отжиманий за неделю",
            "quest_type": "PUSHUP",
            "goal": goal,
            "progress": 0,
            "difficulty": 2,
            "reward_xp": goal * 3,
            "reward_currency": goal * 2,
            "reward_skill_points": 2,
            "expires_at": timezone.now() + timedelta(days=7),
            "is_daily": False,
            "is_boss_quest": False,
        }

    def _create_weekly_squat_quest(self):
        goal = 90 + (self.player.level * 12)
        return {
            "title": "🦵 Недельная выносливость",
            "description": f"Выполни {goal} приседаний за неделю",
            "quest_type": "SQUAT",
            "goal": goal,
            "progress": 0,
            "difficulty": 2,
            "reward_xp": goal * 2,
            "reward_currency": goal,
            "reward_skill_points": 2,
            "expires_at": timezone.now() + timedelta(days=7),
            "is_daily": False,
            "is_boss_quest": False,
        }

    def _create_weekly_pullup_quest(self):
        goal = 20 + (self.player.level * 3)
        return {
            "title": "🎯 Недельный хват",
            "description": f"Сделай {goal} подтягиваний за неделю",
            "quest_type": "PULLUP",
            "goal": goal,
            "progress": 0,
            "difficulty": 2,
            "reward_xp": goal * 5,
            "reward_currency": goal * 2,
            "reward_skill_points": 2,
            "expires_at": timezone.now() + timedelta(days=7),
            "is_daily": False,
            "is_boss_quest": False,
        }
