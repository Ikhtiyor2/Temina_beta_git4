from django.utils import timezone
from .models import Quest, WorkoutSession
from .quest_generator import QuestGenerator
import logging

logger = logging.getLogger(__name__)

class QuestManager:
    """Исправленный менеджер квестов"""

    def __init__(self, player):
        self.player = player

    def create_initial_quests(self):
        """Создает начальные квесты для нового игрока"""
        print("🆕 Создаем начальные квесты...")
        
        # Очищаем старые квесты (на всякий случай)
        Quest.objects.filter(player=self.player).delete()
        
        generator = QuestGenerator(self.player)
        quests_data = generator.generate_initial_quests()
        
        created_quests = []
        for quest_data in quests_data:
            quest = Quest.objects.create(player=self.player, **quest_data)
            created_quests.append(quest)
            print(f"✅ Создан квест: {quest.title}")
        
        return created_quests

    def generate_daily_quests(self):
        """Генерирует ежедневные квесты — всего 4 в день."""
        print("🔄 Генерация ежедневных квестов...")
        
        # Удаляем старые ежедневные: завершённые и просроченные
        from django.db.models import Q
        Quest.objects.filter(
            player=self.player,
            is_daily=True,
        ).filter(
            Q(completed=True) | Q(expires_at__lte=timezone.now())
        ).delete()
        
        # Проверяем, есть ли активные ежедневные квесты (не просрочены)
        active_daily_quests = Quest.objects.filter(
            player=self.player,
            is_daily=True,
            completed=False,
            expires_at__gt=timezone.now()
        )
        
        if active_daily_quests.exists():
            print("📊 Активные ежедневные квесты уже существуют")
            return list(active_daily_quests)
        
        # Создаем новые ежедневные квесты
        generator = QuestGenerator(self.player)
        quests_data = generator.generate_daily_quests()
        
        created_quests = []
        for quest_data in quests_data:
            quest = Quest.objects.create(player=self.player, **quest_data)
            created_quests.append(quest)
            print(f"✅ Создан ежедневный квест: {quest.title}")
        
        return created_quests

    def generate_weekly_quests(self):
        """Генерирует недельные квесты, если активного недельного набора ещё нет."""
        print("🔄 Генерация недельных квестов...")

        from django.db.models import Q
        Quest.objects.filter(
            player=self.player,
            is_daily=False,
        ).filter(
            Q(completed=True) | Q(expires_at__lte=timezone.now())
        ).delete()

        active_weekly_quests = Quest.objects.filter(
            player=self.player,
            is_daily=False,
            completed=False,
            expires_at__gt=timezone.now()
        )

        if active_weekly_quests.exists():
            print("📊 Активные недельные квесты уже существуют")
            return list(active_weekly_quests)

        generator = QuestGenerator(self.player)
        quests_data = generator.generate_weekly_quests()

        created_quests = []
        for quest_data in quests_data:
            quest = Quest.objects.create(player=self.player, **quest_data)
            created_quests.append(quest)
            print(f"✅ Создан недельный квест: {quest.title}")

        return created_quests

    def update_quest_progress(self, exercise_type, count):
        """Обновляет прогресс квестов на основе выполненного упражнения"""
        logger.debug("Quest progress update: %s +%s", exercise_type, count)
        
        active_quests = Quest.objects.filter(
            player=self.player,
            completed=False,
            expires_at__gt=timezone.now()
        )
        
        completed_quests = []
        
        for quest in active_quests:
            print(f"🔍 Проверка квеста: {quest.title} (тип: {quest.quest_type})")
            
            if quest.quest_type == exercise_type:
                if quest.quest_type == "RUN":
                    quest.progress = min(quest.goal, quest.progress + max(1, count // 1000))
                elif quest.quest_type == "TABATA":
                    quest.progress = min(quest.goal, quest.progress + 1)
                else:
                    quest.progress += count
                quest.save()
                
                print(f"📊 Прогресс квеста '{quest.title}': {quest.progress}/{quest.goal}")
                
                if quest.progress >= quest.goal and not quest.completed:
                    quest.complete_quest()
                    completed_quests.append(quest)
                    print(f"🎉 Квест завершен: {quest.title}")
            
            elif quest.quest_type == 'COMBO' and quest.combo_data:
                # Для комбо-квестов
                if exercise_type in quest.combo_data:
                    # Здесь нужно доработать логику для комбо-квестов
                    # Пока просто увеличиваем общий прогресс
                    quest.progress = min(quest.progress + 1, quest.goal)
                    quest.save()
                    
                    if quest.progress >= quest.goal and not quest.completed:
                        quest.complete_quest()
                        completed_quests.append(quest)
        
        return completed_quests

    def complete_daily_login(self):
        """Отмечает выполнение ежедневного входа"""
        daily_login_quests = Quest.objects.filter(
            player=self.player,
            quest_type='DAILY_LOGIN',
            completed=False,
            expires_at__gt=timezone.now()
        )
        
        for quest in daily_login_quests:
            quest.progress = 1
            if quest.check_completion():
                quest.complete_quest()
                return True
        
        return False

    def get_active_quests(self):
        """Возвращает активные квесты"""
        return Quest.objects.filter(
            player=self.player,
            completed=False,
            expires_at__gt=timezone.now()
        ).order_by('difficulty', 'expires_at')

    def get_completed_quests(self):
        """Возвращает завершенные квесты"""
        return Quest.objects.filter(
            player=self.player,
            completed=True
        ).order_by('-expires_at')

    def cleanup_expired_quests(self):
        """Очищает просроченные квесты"""
        expired_count = Quest.objects.filter(
            player=self.player,
            completed=False,
            expires_at__lte=timezone.now()
        ).delete()[0]
        
        print(f"🗑️ Удалено {expired_count} просроченных квестов")
        return expired_count

    def get_quests_for_api(self):
        """Форматирует квесты для API"""
        quests = Quest.objects.filter(player=self.player)
        quests_data = []
        
        for quest in quests:
            quests_data.append({
                'id': quest.id,
                'title': quest.title,
                'description': quest.description,
                'quest_type': quest.quest_type,
                'goal': quest.goal,
                'progress': quest.progress,
                'progress_percent': quest.get_progress_percent(),
                'reward_xp': quest.reward_xp,
                'reward_currency': quest.reward_currency,
                'reward_skill_points': quest.reward_skill_points,
                'difficulty': quest.difficulty,
                'completed': quest.completed,
                'is_expired': quest.is_expired(),
                'expires_at': quest.expires_at.isoformat() if quest.expires_at else None,
            })
        
        return quests_data