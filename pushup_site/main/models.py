from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json
import secrets
import string
import uuid
from django.db.models import Sum, Max, Count, Q  # Убедитесь, что эти импорты есть
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models.manager import Manager

class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    level = models.IntegerField(default=1)
    exp = models.FloatField(default=0)
    exp_to_level = models.FloatField(default=100)
    skill_points = models.IntegerField(default=0)
    strength = models.IntegerField(default=1)
    stamina = models.IntegerField(default=1)
    agility = models.IntegerField(default=1)
    technique = models.IntegerField(default=1)
    currency = models.IntegerField(default=0)
    fatigue = models.FloatField(default=0)
    last_login_date = models.DateField(auto_now=True)
    login_streak = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    display_name = models.CharField(max_length=120, blank=True, default="")
    avatar_url = models.URLField(max_length=512, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    region = models.CharField(max_length=120, blank=True, default="")
    faculty = models.CharField(max_length=200, blank=True, default="")
    course = models.PositiveSmallIntegerField(null=True, blank=True)
    institution_custom = models.CharField(max_length=200, blank=True, default="")
    invite_code = models.CharField(max_length=12, unique=True, null=True, blank=True)
    season_title = models.CharField(max_length=200, blank=True, default="")
    xp_escrow = models.IntegerField(default=0)
    institution = models.ForeignKey(
        "Institution",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="students",
    )
    school_institution = models.ForeignKey(
        "Institution",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="school_students",
    )
    # Soft email verification: app/web usable without confirm; flag tracks opt-in verify.
    email_verified = models.BooleanField(default=False)
    # Telegram Mini App identity. Empty for email/password accounts.
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_username = models.CharField(max_length=64, blank=True, default="")

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = self._generate_invite_code()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_invite_code() -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(8))
            if not Player.objects.filter(invite_code=code).exists():
                return code
        return uuid.uuid4().hex[:8].upper()

    def skill_cap(self) -> int:
        return max(1, int(self.level or 1) // 2)

    def add_exp(self, amount):
        self.exp += amount
        leveled_up = False
        while self.exp >= self.exp_to_level:
            self.exp -= self.exp_to_level
            self.level += 1
            self.skill_points += 1
            self.exp_to_level = self.level * 100
            leveled_up = True
        return leveled_up

    def deduct_exp(self, amount: int) -> int:
        """Remove up to `amount` XP; returns amount actually removed."""
        amount = max(0, int(amount))
        if amount <= 0:
            return 0
        total = int(100 * int(self.level or 1) * (int(self.level or 1) - 1) / 2 + float(self.exp or 0))
        actual = min(amount, total)
        new_total = total - actual
        level = 1
        while True:
            next_threshold = 100 * (level + 1) * level // 2
            if new_total < next_threshold:
                self.level = level
                self.exp = float(new_total - 100 * level * (level - 1) // 2)
                self.exp_to_level = float(level * 100)
                return actual
            level += 1
    
    def upgrade_skill(self, skill_name):
        valid_skills = ['strength', 'stamina', 'agility', 'technique']
        if skill_name in valid_skills and self.skill_points > 0:
            current_value = getattr(self, skill_name)
            if current_value >= self.skill_cap():
                return False
            setattr(self, skill_name, current_value + 1)
            self.skill_points -= 1
            return True
        return False
    
    def add_fatigue(self, amount):
        self.fatigue = min(100, self.fatigue + amount)
    
    def reduce_fatigue(self, amount):
        self.fatigue = max(0, self.fatigue - amount)
    
    def update_login_streak(self):
        today = timezone.now().date()
        if self.last_login_date == today:
            return
        if self.last_login_date == today - timedelta(days=1):
            self.login_streak += 1
        else:
            self.login_streak = 1
        self.last_login_date = today
    
    def __str__(self):
        return f"{self.user.username} - Level {self.level}"

class Quest(models.Model):
    QUEST_TYPES = [
        ('PUSHUP', 'Отжимания'),
        ('SQUAT', 'Приседания'), 
        ('PULLUP', 'Подтягивания'),
        ('CRUNCH', 'Скручивания'),
        ('PLANK', 'Планка'),
        ('COMBO', 'Комбо-упражнения'),
        ('STREAK', 'Серия тренировок'),
        ('PERFECT_FORM', 'Идеальная техника'),
        ('DAILY_LOGIN', 'Ежедневный вход'),
        ('REST', 'Отдых'),
        ('BOSS', 'Босс-квест'),
        ('TABATA', 'Табата'),
        ('RUN', 'Бег'),
    ]
    
    DIFFICULTY_CHOICES = [
        (1, 'Легкий'),
        (2, 'Средний'),
        (3, 'Сложный'),
        (4, 'Эксперт'),
        (5, 'Легендарный'),
    ]
    
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='quests')
    title = models.CharField(max_length=200)
    description = models.TextField()
    quest_type = models.CharField(max_length=20, choices=QUEST_TYPES)
    goal = models.IntegerField(default=0)
    progress = models.IntegerField(default=0)
    reward_xp = models.IntegerField(default=0)
    reward_currency = models.IntegerField(default=0)
    reward_skill_points = models.IntegerField(default=0)
    difficulty = models.IntegerField(choices=DIFFICULTY_CHOICES, default=1)
    time_limit = models.IntegerField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_boss_quest = models.BooleanField(default=False)
    is_daily = models.BooleanField(default=True)
    
    # Для сложных квестов
    combo_data = models.JSONField(null=True, blank=True)
    required_exercises = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        status = "✅" if self.completed else "🔄"
        return f"{status} {self.title} - {self.player.user.username}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['player', 'completed']),
            models.Index(fields=['expires_at']),
        ]
    
    def get_progress_percent(self):
        """Возвращает процент выполнения квеста"""
        if self.goal == 0:
            return 0
        return min(100, int((self.progress / self.goal) * 100))
    
    def is_expired(self):
        """Проверяет истек ли срок квеста"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def check_completion(self):
        """Проверяет выполнен ли квест"""
        if self.completed:
            return True
            
        if self.quest_type == 'COMBO' and self.combo_data:
            return self._check_combo_completion()
        elif self.quest_type == 'PERFECT_FORM':
            return self.progress >= self.goal
        elif self.quest_type == 'DAILY_LOGIN':
            return self.player.login_streak >= self.goal
        elif self.quest_type == 'REST':
            return self.player.fatigue <= 20
        else:
            return self.progress >= self.goal
    
    def _check_combo_completion(self):
        """Проверяет выполнение комбо-квеста"""
        if not self.combo_data:
            return False
        
        for exercise, required in self.combo_data.items():
            # Здесь должна быть логика проверки прогресса по каждому упражнению
            current_progress = getattr(self, f'progress_{exercise}', 0)
            if current_progress < required:
                return False
        return True
    
    def add_progress(self, exercise_type, amount=1, perfect_rep=False):
        """Добавляет прогресс к квесту"""
        if self.completed:
            return False
            
        progress_added = False
        
        if self.quest_type == exercise_type:
            self.progress += amount
            progress_added = True
        elif self.quest_type == 'COMBO' and self.combo_data:
            if exercise_type in self.combo_data:
                # Для комбо-квестов нужна отдельная логика хранения прогресса
                pass
        elif self.quest_type == 'PERFECT_FORM' and perfect_rep:
            self.progress += amount
            progress_added = True
            
        if progress_added:
            self.save()
            return self.check_completion()
        
        return False
    
    def complete_quest(self):
        """Завершает квест и выдает награды"""
        if not self.completed:
            self.completed = True
            self.save()
            
            # Выдаем награды игроку
            self.player.add_exp(self.reward_xp)
            self.player.currency += self.reward_currency
            self.player.skill_points += self.reward_skill_points
            self.player.save()
            return True
        return False

class WorkoutSession(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='workout_sessions')
    exercise_type = models.CharField(max_length=20)
    reps_count = models.IntegerField(default=0)
    errors_count = models.IntegerField(default=0)
    duration_seconds = models.IntegerField(default=0)
    calories_burned = models.FloatField(default=0)
    date = models.DateTimeField(auto_now_add=True)
    quest = models.ForeignKey(Quest, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.player.user.username} - {self.exercise_type} - {self.reps_count} reps"
    
    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['player', 'date']),
        ]

class WorkoutSet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workout_sets')
    exercise_type = models.CharField(max_length=20, choices=[
        ('PUSHUP', 'Отжимания'),
        ('SQUAT', 'Приседания'),
        ('PULLUP', 'Подтягивания'),
        ('CRUNCH', 'Скручивания'),
        ('PLANK', 'Планка'),
    ])
    repetitions = models.IntegerField()
    date_completed = models.DateTimeField(auto_now_add=True)
    quality_score = models.FloatField(default=1.0)
    
    def __str__(self):
        return f"{self.user.username} - {self.exercise_type} - {self.repetitions} reps"
    
    class Meta:
        ordering = ['-date_completed']

class EXERCISE_CHOICES:
    CHOICES = [
        ('PUSHUP', 'Отжимания'),
        ('SQUAT', 'Приседания'),
        ('PULLUP', 'Подтягивания'),
        ('CRUNCH', 'Скручивания'),
        ('PLANK', 'Планка'),
    ]
    
    @classmethod
    def get_display_name(cls, exercise_type):
        return dict(cls.CHOICES).get(exercise_type, exercise_type)
# Добавьте в models.py после существующих моделей

# Добавьте в models.py после существующих моделей

class PlayerStats(models.Model):
    """Расширенная статистика игрока"""
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name='stats')
    
    # Общая статистика
    total_workouts = models.IntegerField(default=0)
    total_reps = models.IntegerField(default=0)
    total_calories = models.FloatField(default=0)
    total_workout_time = models.IntegerField(default=0)  # в секундах
    
    # Статистика по упражнениям
    pushups_total = models.IntegerField(default=0)
    squats_total = models.IntegerField(default=0)
    pullups_total = models.IntegerField(default=0)
    crunches_total = models.IntegerField(default=0)
    planks_total = models.IntegerField(default=0)  # секунды в планке всего
    
    # Рекорды
    max_pushups_set = models.IntegerField(default=0)
    max_squats_set = models.IntegerField(default=0)
    max_pullups_set = models.IntegerField(default=0)
    max_crunches_set = models.IntegerField(default=0)
    max_plank_hold_seconds = models.IntegerField(default=0)  # лучший результат планки (сек)
    
    # Время и даты
    current_streak = models.IntegerField(default=0)  # текущая серия дней с тренировками
    max_streak = models.IntegerField(default=0)     # максимальная серия
    last_workout_date = models.DateTimeField(null=True, blank=True)
    
    # Достижения
    perfect_workouts = models.IntegerField(default=0)  # тренировки без ошибок
    quests_completed = models.IntegerField(default=0)
    
    # Ежедневная статистика
    today_reps = models.IntegerField(default=0)
    today_workouts = models.IntegerField(default=0)
    today_calories = models.FloatField(default=0)
    last_updated = models.DateField(auto_now=True)
    
    def __str__(self):
        return f"Статистика {self.player.user.username}"
    
    def update_daily_stats(self, reps, calories=0):
        """Обновляет ежедневную статистику"""
        today = timezone.now().date()
        
        # Сбрасываем ежедневную статистику если это новый день
        if self.last_updated != today:
            self.today_reps = 0
            self.today_workouts = 0
            self.today_calories = 0
            self.last_updated = today
        
        self.today_reps += reps
        self.today_calories += calories
        self.today_workouts += 1
        
        # Обновляем общую статистику
        self.total_reps += reps
        self.total_calories += calories
        self.total_workouts += 1
        
        # Обновляем серию тренировок
        self._update_streak()
        
        self.save()
    
    def update_exercise_stats(self, exercise_type, reps, is_record=False):
        """Обновляет статистику по конкретному упражнению"""
        exercise_field_map = {
            'PUSHUP': 'pushups_total',
            'SQUAT': 'squats_total', 
            'PULLUP': 'pullups_total',
            'CRUNCH': 'crunches_total',
            'PLANK': 'planks_total',
        }
        
        max_field_map = {
            'PUSHUP': 'max_pushups_set',
            'SQUAT': 'max_squats_set',
            'PULLUP': 'max_pullups_set', 
            'CRUNCH': 'max_crunches_set',
            'PLANK': 'max_plank_hold_seconds',
        }
        
        field = exercise_field_map.get(exercise_type)
        max_field = max_field_map.get(exercise_type)
        
        if field:
            current_total = getattr(self, field)
            setattr(self, field, current_total + reps)
            
        if max_field and is_record:
            current_max = getattr(self, max_field)
            if reps > current_max:
                setattr(self, max_field, reps)
    
    def _update_streak(self):
        """Обновляет серию тренировок"""
        today = timezone.now().date()
        
        if not self.last_workout_date:
            self.current_streak = 1
        else:
            last_date = self.last_workout_date.date()
            if last_date == today:
                # Уже обновляли сегодня
                return
            elif last_date == today - timedelta(days=1):
                # Подряд идущие дни
                self.current_streak += 1
            else:
                # Серия прервана
                self.current_streak = 1
        
        # Обновляем максимальную серию
        if self.current_streak > self.max_streak:
            self.max_streak = self.current_streak
            
        self.last_workout_date = timezone.now()
    
    def get_weekly_stats(self):
        """Возвращает статистику за последние 7 дней"""
        week_ago = timezone.now() - timedelta(days=7)
        
        workouts = WorkoutSession.objects.filter(
            player=self.player,
            date__gte=week_ago
        )
        
        weekly_stats = workouts.aggregate(
            total_workouts=Count('id'),
            total_reps=Sum('reps_count'),
            total_calories=Sum('calories_burned')
        )
        
        return {
            'workouts': weekly_stats['total_workouts'] or 0,
            'reps': weekly_stats['total_reps'] or 0,
            'calories': weekly_stats['total_calories'] or 0
        }
    
    def get_monthly_stats(self):
        """Возвращает статистику за последние 30 дней"""
        month_ago = timezone.now() - timedelta(days=30)
        
        workouts = WorkoutSession.objects.filter(
            player=self.player,
            date__gte=month_ago
        )
        
        monthly_stats = workouts.aggregate(
            total_workouts=Count('id'),
            total_reps=Sum('reps_count'),
            total_calories=Sum('calories_burned')
        )
        
        return {
            'workouts': monthly_stats['total_workouts'] or 0,
            'reps': monthly_stats['total_reps'] or 0,
            'calories': monthly_stats['total_calories'] or 0
        }

class Achievement(models.Model):
    """Достижения игрока"""
    ACHIEVEMENT_TYPES = [
        ('REPS', 'По повторениям'),
        ('STREAK', 'По сериям'),
        ('WORKOUTS', 'По тренировкам'),
        ('QUEST', 'По квестам'),
        ('RECORD', 'По рекордам'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    requirement = models.IntegerField()  # Требуемое значение для получения
    reward_xp = models.IntegerField(default=0)
    reward_currency = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, default='🏆')  # Emoji иконка
    
    def __str__(self):
        return self.name

class PlayerAchievement(models.Model):
    """Достижения, полученные игроком"""
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    date_earned = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(default=0)  # Текущий прогресс (для прогрессивных достижений)
    
    class Meta:
        unique_together = ['player', 'achievement']
    
    def __str__(self):
        return f"{self.player.user.username} - {self.achievement.name}"
    
# Добавьте в models.py после существующих моделей

class ActiveWorkout(models.Model):
    """
    Активная тренировка пользователя в реальном времени.
    Теперь: 1 игрок может иметь несколько активных тренировок (по упражнениям).
    """

    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='active_workouts'
    )

    exercise_type = models.CharField(
        max_length=20,
        choices=[
            ('PUSHUP', 'Отжимания'),
            ('SQUAT', 'Приседания'),
            ('PULLUP', 'Подтягивания'),
            ('CRUNCH', 'Скручивания'),
            ('PLANK', 'Планка'),
        ],
        default='PUSHUP'
    )

    # Состояние счетчика
    count = models.IntegerField(default=0)
    stage = models.CharField(max_length=20, default="up")
    ready = models.BooleanField(default=False)

    # Временные метки
    start_time = models.DateTimeField(auto_now_add=True)
    last_frame_time = models.DateTimeField(auto_now=True)
    last_update = models.DateTimeField(auto_now=True)

    # Дополнительные данные для кэширования
    frame_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Кэшированные данные последнего кадра"
    )

    # Флаги состояния
    is_active = models.BooleanField(default=True)
    was_completed = models.BooleanField(default=False)

    # Метрики производительности
    total_frames_processed = models.IntegerField(default=0)
    avg_processing_time_ms = models.FloatField(default=0)

    class Meta:
        db_table = 'active_workouts'
        verbose_name = 'Активная тренировка'
        verbose_name_plural = 'Активные тренировки'

        indexes = [
            models.Index(fields=['player', 'exercise_type']),
            models.Index(fields=['last_frame_time']),
            models.Index(fields=['is_active']),
        ]

        constraints = [
            models.UniqueConstraint(
                fields=['player', 'exercise_type'],
                name='unique_active_workout_per_player'
            )
        ]

    def __str__(self):
        status = "✅ Активна" if self.is_active else "❌ Завершена"
        return f"{status} {self.get_exercise_type_display()}: {self.count} повторений"

    def save(self, *args, **kwargs):
        """Обновляем время при каждом сохранении"""
        if not self.start_time:
            self.start_time = timezone.now()
        self.last_update = timezone.now()
        super().save(*args, **kwargs)

    def update_frame_data(self, ai_result):
        """
        Обновляет кэшированные данные кадра.
        Сохраняет также доп. поля (напр. min_knee_angle_in_rep для приседаний).
        """
        self.frame_data = {
            'count': ai_result.get('count', 0),
            'stage': ai_result.get('stage', 'up'),
            'ready': ai_result.get('ready', False),
            'feedback': ai_result.get('feedback', ''),
            'errors': ai_result.get('errors', []),
            'pose_detected': ai_result.get('pose_detected', False),
            'processing_time': ai_result.get('processing_time_ms', 0),
            'timestamp': timezone.now().isoformat(),
        }
        if 'min_knee_angle_in_rep' in ai_result:
            self.frame_data['min_knee_angle_in_rep'] = ai_result['min_knee_angle_in_rep']

        # Обновляем метрики
        self.total_frames_processed += 1

        current_time = ai_result.get('processing_time_ms', 0)
        if self.total_frames_processed > 1:
            self.avg_processing_time_ms = (
                (self.avg_processing_time_ms * (self.total_frames_processed - 1)) + current_time
            ) / self.total_frames_processed
        else:
            self.avg_processing_time_ms = current_time

        self.last_frame_time = timezone.now()
        self.save(update_fields=[
            'frame_data',
            'last_frame_time',
            'total_frames_processed',
            'avg_processing_time_ms'
        ])

    def is_expired(self):
        """
        Проверяет, истекла ли тренировка (нет кадров 30 секунд)
        """
        if not self.is_active:
            return True

        time_since_last_frame = timezone.now() - self.last_frame_time
        return time_since_last_frame.total_seconds() > 30

    def mark_completed(self):
        """
        Помечает тренировку как завершенную
        """
        self.is_active = False
        self.was_completed = True
        self.save(update_fields=['is_active', 'was_completed', 'last_update'])

    def reset(self):
        """
        Сбрасывает тренировку к начальному состоянию
        """
        self.count = 0
        self.stage = "up"
        self.ready = False
        self.frame_data = {}
        self.total_frames_processed = 0
        self.avg_processing_time_ms = 0
        self.start_time = timezone.now()
        self.last_frame_time = timezone.now()
        self.is_active = True
        self.was_completed = False
        self.save()

    def get_duration_seconds(self):
        """
        Возвращает длительность тренировки в секундах
        """
        if not self.is_active:
            return 0

        duration = timezone.now() - self.start_time
        return int(duration.total_seconds())

    def to_json(self):
        """
        Возвращает данные тренировки для API
        """
        return {
            'id': self.id,
            'exercise_type': self.exercise_type,
            'exercise_display': self.get_exercise_type_display(),
            'count': self.count,
            'stage': self.stage,
            'ready': self.ready,
            'is_active': self.is_active,
            'was_completed': self.was_completed,
            'start_time': self.start_time.isoformat(),
            'last_frame_time': self.last_frame_time.isoformat(),
            'duration_seconds': self.get_duration_seconds(),
            'total_frames_processed': self.total_frames_processed,
            'avg_processing_time_ms': round(self.avg_processing_time_ms, 2),
            'frame_data': self.frame_data,
        }

    @classmethod
    def cleanup_expired(cls):
        """
        Удаляет истекшие тренировки
        """
        expired = cls.objects.filter(is_active=True)
        expired_ids = []

        for workout in expired:
            if workout.is_expired():
                expired_ids.append(workout.id)
                workout.delete()

        return expired_ids

    @classmethod
    def get_or_create_active(cls, player, exercise_type='PUSHUP'):
        """
        Теперь логика правильная:
        один игрок может иметь отдельную ActiveWorkout на каждое упражнение.
        """
        exercise_type = (exercise_type or "PUSHUP").upper()

        workout, created = cls.objects.get_or_create(
            player=player,
            exercise_type=exercise_type,
            defaults={
                "start_time": timezone.now(),
                "last_frame_time": timezone.now(),
                "is_active": True,
                "was_completed": False,
                "count": 0,
                "stage": "up",
                "ready": False,
                "frame_data": {},
                "total_frames_processed": 0,
                "avg_processing_time_ms": 0,
            }
        )

        # если истекла — сбрасываем
        if workout.is_expired():
            workout.reset()

        # всегда активируем
        if not workout.is_active:
            workout.is_active = True
            workout.was_completed = False
            workout.save(update_fields=['is_active', 'was_completed', 'last_update'])

        return workout, created


class FitnessProfile(models.Model):
    """
    Профиль пользователя для ИИ-тренера: цели, здоровье, оборудование, уровень.
    Заполняется при онбординге или в настройках; используется для генерации плана тренировок.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fitness_profile')

    # Основной профиль
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    height_cm = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    target_weight_kg = models.FloatField(null=True, blank=True)

    # Цели (множественный выбор): build_muscle, lose_weight, stay_in_shape, look_better
    goals = models.JSONField(default=list, blank=True)  # e.g. ["build_muscle", "look_better"]

    # Фокус мышц: chest, back, arms, shoulders, abs, full_body
    muscle_focus = models.JSONField(default=list, blank=True)

    # Ограничения по здоровью: back, knee, hip_joints, shoulders, no_jumps
    health_limits = models.JSONField(default=list, blank=True)

    # Оборудование: bodyweight, gym, barbell, dumbbell, machine
    equipment = models.JSONField(default=list, blank=True)

    # Уровень: beginner, intermediate, advanced
    fitness_level = models.CharField(
        max_length=20,
        choices=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        default='beginner',
        blank=True,
    )

    # Уровень активности: sedentary, light, moderate, active, very_active
    activity_level = models.CharField(
        max_length=20,
        choices=[
            ('sedentary', 'Sedentary'),
            ('light', 'Light'),
            ('moderate', 'Moderate'),
            ('active', 'Active'),
            ('very_active', 'Very Active'),
        ],
        default='moderate',
        blank=True,
    )

    # Тренировок в неделю (1–7)
    workouts_per_week = models.PositiveSmallIntegerField(default=3, null=True, blank=True)

    # Мотивация: health, appearance, stress_relief, social, enjoyment
    motivation = models.JSONField(default=list, blank=True)

    # Доп. заметки для ИИ (ментальное/физическое здоровье, предпочтения)
    notes = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fitness profile'
        verbose_name_plural = 'Fitness profiles'

    def __str__(self):
        return f"Fitness profile: {self.user.username}"

    def is_complete(self):
        """Минимально заполнен для генерации плана: возраст, цель, уровень."""
        return bool(
            self.age
            and (self.goals or self.fitness_level)
        )


class FitnessAssessment(models.Model):
    """
    Полная анкета Assessment (schemaVersion 1).
    Каноника: height_cm, weight_kg, age_years; payload — сырой JSON клиента.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="fitness_assessments",
        null=True,
        blank=True,
    )
    profile_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    schema_version = models.PositiveSmallIntegerField(default=1)

    gender = models.CharField(max_length=32, blank=True)
    age_years = models.PositiveSmallIntegerField(null=True, blank=True)
    height_cm = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)

    primary_goal = models.CharField(max_length=32, blank=True)
    fitness_level = models.PositiveSmallIntegerField(null=True, blank=True)
    workouts_per_week = models.PositiveSmallIntegerField(null=True, blank=True)
    preferred_session_minutes = models.PositiveSmallIntegerField(null=True, blank=True)

    has_chronic_conditions = models.BooleanField(default=False)
    body_scan_consent = models.BooleanField(default=False)
    body_scan_skipped = models.BooleanField(default=False)
    assessment_confirmed = models.BooleanField(default=False)

    payload = models.JSONField(default=dict, blank=True)
    assessment_completed_at = models.DateTimeField(auto_now_add=True)

    next_recommended_program_id = models.CharField(max_length=64, null=True, blank=True)
    generated_plan_version = models.CharField(max_length=32, blank=True, default="")

    class Meta:
        ordering = ["-assessment_completed_at"]
        indexes = [
            models.Index(fields=["user", "-assessment_completed_at"], name="main_fitnes_user_id_bcd372_idx"),
        ]

    def __str__(self):
        return f"Assessment {self.profile_id} v{self.schema_version}"


class RunSession(models.Model):
    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"
    STATUS_FINISHED = "finished"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_FINISHED, "Finished"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="run_sessions")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    started_at = models.DateTimeField(default=timezone.now)
    paused_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    distance_km = models.FloatField(default=0)
    duration_sec = models.PositiveIntegerField(default=0)
    pace_min_per_km = models.FloatField(default=0)
    avg_speed = models.FloatField(default=0)
    calories_estimate = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "-started_at"], name="main_runses_user_id_d3e0b9_idx"),
            models.Index(fields=["status"], name="main_runses_status_f8a809_idx"),
        ]

    def __str__(self):
        return f"Run {self.id} {self.user.username} {self.status}"


class RunTrackPoint(models.Model):
    run_session = models.ForeignKey(RunSession, on_delete=models.CASCADE, related_name="points")
    lat = models.FloatField()
    lng = models.FloatField()
    timestamp = models.DateTimeField()
    accuracy = models.FloatField(null=True, blank=True)
    speed_mps = models.FloatField(null=True, blank=True)
    sequence = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sequence", "timestamp", "id"]
        indexes = [
            models.Index(fields=["run_session", "sequence"], name="main_runtra_run_ses_02db70_idx"),
            models.Index(fields=["timestamp"], name="main_runtra_timesta_6c2b85_idx"),
        ]

    def __str__(self):
        return f"RunPoint {self.run_session_id} #{self.sequence}"


class WeeklyPlan(models.Model):
    """Недельный план тренировок (id упражнений из WORKOUT_CATALOG / counterProfile)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="weekly_plans")
    week_start = models.DateField(db_index=True)
    difficulty_tier = models.PositiveSmallIntegerField(default=1)
    assessment = models.ForeignKey(
        "FitnessAssessment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="weekly_plans",
    )
    source = models.CharField(max_length=32, default="assessment")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-week_start"]
        constraints = [
            models.UniqueConstraint(fields=["user", "week_start"], name="uniq_weekly_plan_user_week"),
        ]

    def __str__(self):
        return f"WeeklyPlan {self.user_id} {self.week_start} tier={self.difficulty_tier}"


class WeeklyPlanDay(models.Model):
    plan = models.ForeignKey(WeeklyPlan, on_delete=models.CASCADE, related_name="days")
    day_index = models.PositiveSmallIntegerField()
    is_rest = models.BooleanField(default=False)
    counter_profile_id = models.CharField(max_length=64, blank=True, default="")
    display_title = models.CharField(max_length=160, blank=True, default="")
    target_sets = models.PositiveSmallIntegerField(default=0)
    target_reps = models.PositiveSmallIntegerField(default=0)
    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    focus_note = models.CharField(max_length=256, blank=True, default="")
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["day_index"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "day_index"], name="uniq_weekly_plan_day_index"),
        ]

    def __str__(self):
        return f"Day {self.day_index} plan={self.plan_id}"

    def refresh_completed_from_exercises(self) -> None:
        if self.is_rest:
            return
        ex_qs = self.exercises.all()
        if not ex_qs.exists():
            return
        all_done = not ex_qs.filter(completed=False).exists()
        if self.completed != all_done:
            self.completed = all_done
            self.save(update_fields=["completed"])


class WeeklyPlanDayExercise(models.Model):
    """Одно упражнение в комплексе тренировочного дня."""

    day = models.ForeignKey(WeeklyPlanDay, on_delete=models.CASCADE, related_name="exercises")
    sort_order = models.PositiveSmallIntegerField(default=0)
    counter_profile_id = models.CharField(max_length=64)
    display_title = models.CharField(max_length=160, blank=True, default="")
    target_sets = models.PositiveSmallIntegerField(default=3)
    target_reps = models.PositiveSmallIntegerField(default=0)
    duration_sec = models.PositiveIntegerField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["day", "sort_order"],
                name="uniq_weekly_plan_day_exercise_order",
            ),
        ]

    def __str__(self):
        return f"DayEx {self.counter_profile_id} day={self.day_id}"


class WeeklyPlanSessionLog(models.Model):
    plan = models.ForeignKey(WeeklyPlan, on_delete=models.CASCADE, related_name="session_logs")
    day = models.ForeignKey(WeeklyPlanDay, on_delete=models.CASCADE, related_name="session_logs")
    exercise = models.ForeignKey(
        WeeklyPlanDayExercise,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="session_logs",
    )
    counter_profile_id = models.CharField(max_length=64)
    reps = models.PositiveIntegerField(default=0)
    duration_sec = models.PositiveIntegerField(default=0)
    quality_score = models.FloatField(null=True, blank=True)
    errors_json = models.JSONField(default=list, blank=True)
    ai_feedback = models.TextField(blank=True, default="")
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at"]

    def __str__(self):
        return f"WeekLog plan={self.plan_id} day={self.day_id}"


class Subscription(models.Model):
    """
    Состояние подписки пользователя (источник правды — бэкенд).
    Обновляется вебхуком RevenueCat + сверкой через REST API GET /subscribers.
    Клиент только читает статус, сам решать «активна ли подписка» он не может.
    """

    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELED = "canceled"       # отменена, но ещё действует до конца периода
    STATUS_GRACE = "grace_period"      # проблема с оплатой, доступ ещё есть
    STATUS_PAUSED = "paused"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELED, "Canceled"),
        (STATUS_GRACE, "Grace period"),
        (STATUS_PAUSED, "Paused"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    platform = models.CharField(max_length=20, default="revenuecat")

    # Идентификатор пользователя в RevenueCat (App User ID). Используем User.pk.
    app_user_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    # entitlement (напр. "pro") + конкретный продукт стора
    entitlement_id = models.CharField(max_length=120, blank=True, default="")
    product_id = models.CharField(max_length=160, blank=True, default="")
    store = models.CharField(max_length=40, blank=True, default="")  # play_store / app_store / ...

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_EXPIRED)
    current_period_end = models.DateTimeField(null=True, blank=True)
    auto_renewing = models.BooleanField(default=False)

    # Идемпотентность вебхуков: id последнего обработанного события RevenueCat.
    last_event_id = models.CharField(max_length=128, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.user.username} · {self.entitlement_id or '—'} · {self.status}"

    def is_active(self) -> bool:
        """Подписка даёт доступ, если статус «живой» и период ещё не истёк."""
        if self.status in (self.STATUS_ACTIVE, self.STATUS_CANCELED, self.STATUS_GRACE):
            return bool(self.current_period_end and self.current_period_end > timezone.now())
        return False


class Institution(models.Model):
    TYPE_UNIVERSITY = "university"
    TYPE_SCHOOL = "school"
    TYPE_CHOICES = [
        (TYPE_UNIVERSITY, "University"),
        (TYPE_SCHOOL, "School"),
    ]

    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_UNIVERSITY)
    name = models.CharField(max_length=200)
    name_en = models.CharField(max_length=200, blank=True, default="")
    name_uz = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    region = models.CharField(max_length=120, blank=True, default="")
    country = models.CharField(max_length=80, default="UZ")
    is_verified = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="submitted_institutions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["type", "city", "region"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.city})"


class Friendship(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_BLOCKED = "blocked"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_BLOCKED, "Blocked"),
    ]

    from_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="friendships_sent")
    to_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="friendships_received")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["from_player", "to_player"], name="uniq_friendship_pair"),
        ]
        indexes = [
            models.Index(fields=["from_player", "status"]),
            models.Index(fields=["to_player", "status"]),
        ]

    def __str__(self):
        return f"{self.from_player_id} -> {self.to_player_id} ({self.status})"


class Challenge(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    ]
    METRIC_REPS = "reps"
    METRIC_DISTANCE_KM = "distance_km"
    METRIC_DURATION_SEC = "duration_sec"
    METRIC_CHOICES = [
        (METRIC_REPS, "Reps"),
        (METRIC_DISTANCE_KM, "Distance km"),
        (METRIC_DURATION_SEC, "Duration sec"),
    ]

    challenger = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="challenges_sent")
    opponent = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="challenges_received")
    exercise_type = models.CharField(max_length=20)
    goal_metric = models.CharField(max_length=20, choices=METRIC_CHOICES, default=METRIC_REPS)
    goal_value = models.IntegerField(default=0)
    wager_xp = models.IntegerField(default=10)
    deadline = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    challenger_result = models.IntegerField(default=0)
    opponent_result = models.IntegerField(default=0)
    winner = models.ForeignKey(
        Player,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="challenges_won",
    )
    session_challenger_id = models.IntegerField(null=True, blank=True)
    session_opponent_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["challenger", "status"]),
            models.Index(fields=["opponent", "status"]),
            models.Index(fields=["deadline"]),
        ]

    def __str__(self):
        return f"Challenge {self.id} {self.challenger_id} vs {self.opponent_id}"


class Season(models.Model):
    SCOPE_GLOBAL = "global"
    SCOPE_CITY = "city"
    SCOPE_REGION = "region"
    SCOPE_UNIVERSITY = "university"
    SCOPE_SCHOOL = "school"
    SCOPE_CHOICES = [
        (SCOPE_GLOBAL, "Global"),
        (SCOPE_CITY, "City"),
        (SCOPE_REGION, "Region"),
        (SCOPE_UNIVERSITY, "University"),
        (SCOPE_SCHOOL, "School"),
    ]

    name = models.CharField(max_length=200)
    scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, default=SCOPE_GLOBAL)
    scope_key = models.CharField(max_length=200, blank=True, default="")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    prize_description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class SeasonRanking(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="rankings")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="season_rankings")
    rank = models.PositiveIntegerField()
    total_xp = models.IntegerField(default=0)
    snapshot_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["season", "player"], name="uniq_season_player_rank"),
        ]
        ordering = ["rank"]

    def __str__(self):
        return f"Season {self.season_id} #{self.rank} player={self.player_id}"


class PlayerBadge(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="badges")
    season = models.ForeignKey("Season", null=True, blank=True, on_delete=models.SET_NULL, related_name="badges")
    label = models.CharField(max_length=120)
    icon = models.CharField(max_length=32, blank=True, default="")
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-earned_at"]

    def __str__(self):
        return f"Badge {self.label} player={self.player_id}"


class SeasonPrizeTier(models.Model):
    PRIZE_VIRTUAL = "virtual"
    PRIZE_PHYSICAL = "physical"
    PRIZE_TYPE_CHOICES = [
        (PRIZE_VIRTUAL, "Virtual"),
        (PRIZE_PHYSICAL, "Physical"),
    ]
    FULFILLMENT_PENDING = "pending"
    FULFILLMENT_CLAIMED = "claimed"
    FULFILLMENT_SHIPPED = "shipped"
    FULFILLMENT_CHOICES = [
        (FULFILLMENT_PENDING, "Pending"),
        (FULFILLMENT_CLAIMED, "Claimed"),
        (FULFILLMENT_SHIPPED, "Shipped"),
    ]

    season = models.ForeignKey("Season", on_delete=models.CASCADE, related_name="prize_tiers")
    rank_from = models.PositiveIntegerField()
    rank_to = models.PositiveIntegerField()
    prize_type = models.CharField(max_length=16, choices=PRIZE_TYPE_CHOICES, default=PRIZE_VIRTUAL)
    description = models.TextField(blank=True, default="")
    fulfillment_status = models.CharField(
        max_length=16, choices=FULFILLMENT_CHOICES, default=FULFILLMENT_PENDING
    )

    def __str__(self):
        return f"Prize {self.season_id} ranks {self.rank_from}-{self.rank_to}"


class IntegrityFlag(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="integrity_flags")
    session_id = models.IntegerField(null=True, blank=True)
    flags = models.JSONField(default=list, blank=True)
    sanitized_reps = models.IntegerField(default=0)
    raw_reps = models.IntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["player", "-created_at"]),
        ]

    def __str__(self):
        return f"IntegrityFlag player={self.player_id} session={self.session_id}"


class SupportThread(models.Model):
    STATUS_OPEN = "open"
    STATUS_WAITING_STAFF = "waiting_staff"
    STATUS_WAITING_USER = "waiting_user"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_WAITING_STAFF, "Waiting staff"),
        (STATUS_WAITING_USER, "Waiting user"),
        (STATUS_CLOSED, "Closed"),
    ]

    CATEGORY_GENERAL = "general"
    CATEGORY_TECHNICAL = "technical"
    CATEGORY_BILLING = "billing"
    CATEGORY_ACCOUNT = "account"
    CATEGORY_CHOICES = [
        (CATEGORY_GENERAL, "General"),
        (CATEGORY_TECHNICAL, "Technical"),
        (CATEGORY_BILLING, "Billing"),
        (CATEGORY_ACCOUNT, "Account"),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="support_threads")
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_GENERAL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_WAITING_STAFF)
    unread_by_user = models.PositiveIntegerField(default=0)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["player", "-last_message_at"]),
            models.Index(fields=["status", "-updated_at"]),
        ]
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        return f"SupportThread {self.id} ({self.status}) player={self.player_id}"


class SupportMessage(models.Model):
    SENDER_USER = "user"
    SENDER_STAFF = "staff"
    SENDER_SYSTEM = "system"
    SENDER_CHOICES = [
        (SENDER_USER, "User"),
        (SENDER_STAFF, "Staff"),
        (SENDER_SYSTEM, "System"),
    ]

    thread = models.ForeignKey(SupportThread, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=16, choices=SENDER_CHOICES, default=SENDER_USER)
    sender_user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="support_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["thread", "created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"SupportMessage {self.id} thread={self.thread_id} ({self.sender_type})"

