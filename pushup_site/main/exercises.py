from collections import deque
import math
from typing import Tuple, List, Dict, Any
import time
from datetime import datetime
from .quest_manager import QuestManager
from .models import WorkoutSet, EXERCISE_CHOICES, Player, Quest, WorkoutSession

# Формат ошибки для ИИ: что не так + как исправить (можно добавить priority для сортировки)
def err(message: str, hint: str, priority: int = 0) -> Dict[str, Any]:
    """Ошибка с подсказкой по исправлению. priority: 1 = критично (безопасность/поза), 2 = техника."""
    return {"message": message, "hint": hint, "priority": priority}

class PoseDetectionBase:
    """Базовый класс для всех упражнений."""
    def __init__(self, title: str):
        self.title = title
        self.count = 0
        self.stage = "up"
        self.ready = False
        self.ready_buffer = deque([False] * 15, maxlen=15)
        self.start_time = None
        self.session_start_time = time.time()
        self.last_reps = 0
        self.reps_per_minute = 0
        self.calories_burned = 0
        
    def get_state(self) -> dict:
        """Returns the current state to be saved in the session."""
        return {
            'count': self.count, 
            'stage': self.stage, 
            'ready': self.ready,
            'start_time': self.start_time,
            'session_start_time': self.session_start_time
        }
        
    def load_state(self, state: dict):
        """Loads the status from the session."""
        self.count = state.get('count', 0)
        self.stage = state.get('stage', 'up')
        self.ready = state.get('ready', False)
        self.start_time = state.get('start_time')
        self.session_start_time = state.get('session_start_time', time.time())
    
    def get_hud_data(self) -> dict:
        """Возвращает данные для HUD."""
        current_time = time.time()
        session_duration = current_time - self.session_start_time
        
        # Расчет скорости (повторений в минуту)
        if session_duration > 0:
            self.reps_per_minute = (self.count / session_duration) * 60
        
        # Расчет калорий (примерная формула)
        self.calories_burned = self.count * 0.5  # ~0.5 калорий на повтор
        
        # Время тренировки
        if self.start_time:
            workout_duration = current_time - self.start_time
        else:
            workout_duration = 0
            
        return {
            'count': self.count,
            'stage': self.stage,
            'ready': self.ready,
            'workout_duration': workout_duration,
            'session_duration': session_duration,
            'reps_per_minute': self.reps_per_minute,
            'calories_burned': self.calories_burned,
            'current_time': datetime.now().strftime("%H:%M:%S")
        }
    
    def _process_pose(self, landmarks) -> Tuple[str, List[Dict[str, str]]]:
        """Метод для обработки позы - должен быть переопределен в дочерних классах.
        Возвращает (feedback, список ошибок: [{message, hint}])."""
        return "Processing...", []

class MathUtils:
    """Утилиты для расчета углов."""
    @staticmethod
    def calculate_angle(a, b, c):
        # a, b, c - списки [x, y] или объекты с атрибутами x, y
        if hasattr(a, 'x'):
            a = [a.x, a.y]
            b = [b.x, b.y]
            c = [c.x, c.y]
        ba = [a[0] - b[0], a[1] - b[1]]
        bc = [c[0] - b[0], c[1] - b[1]]
        dot_product = ba[0] * bc[0] + ba[1] * bc[1]
        mag_ba = math.sqrt(ba[0]**2 + ba[1]**2)
        mag_bc = math.sqrt(bc[0]**2 + bc[1]**2)
        if mag_ba == 0 or mag_bc == 0:
            return 0
        cosine_angle = dot_product / (mag_ba * mag_bc)
        cosine_angle = max(min(cosine_angle, 1), -1)
        return math.degrees(math.acos(cosine_angle))

    @staticmethod
    def angle_deg(a, b, c):
        """Короткий алиас для угла в градусах (b — вершина)."""
        return MathUtils.calculate_angle(a, b, c)


class AngleSmoother:
    """Сглаживание углов по последним N кадрам — уменьшает дрожание и ложные срабатывания ИИ."""
    def __init__(self, size: int = 5):
        self._q: deque = deque(maxlen=max(1, size))

    def push(self, value: float) -> None:
        self._q.append(value)

    def median(self) -> float:
        if not self._q:
            return 0.0
        s = sorted(self._q)
        n = len(s)
        return (s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2)

    def value(self) -> float:
        return self.median()


class PushupWorkout(PoseDetectionBase):
    """Отжимания: сглаживание углов, подтверждение фаз по кадрам, подсказки «почти правильно»."""

    def __init__(self):
        super().__init__("Отжимания — TeminaFit v3.0")
        self.down_hold_frames = 0
        self.MIN_HOLD_FRAMES = 2
        self.hands_on_ground = True
        self.top_position_pose = False
        self._elbow_smooth = AngleSmoother(5)
        self._hip_smooth = AngleSmoother(5)
        self._back_smooth = AngleSmoother(5)
        self._stage_down_confirm = 0
        self._stage_up_confirm = 0
        self.STAGE_CONFIRM_NEEDED = 2
        self._hands_off_frames = 0
        self.HANDS_OFF_GRACE = 5

    def _process_pose(self, landmarks) -> Tuple[str, List[Dict[str, str]]]:
        """Отжимания: контроль каждого угла и изгиба. Конкретные подсказки по отклонениям."""
        if not landmarks:
            self.ready_buffer.append(False)
            return "Ожидание...", []

        lm = landmarks.landmark
        errors: List[Dict[str, Any]] = []

        ls, le, lw = lm[11], lm[13], lm[15]
        rs, re, rw = lm[12], lm[14], lm[16]
        lh, rh = lm[23], lm[24]
        lk, rk = lm[25], lm[26]

        # —— Все углы по отдельности ——
        left_elbow_angle = MathUtils.calculate_angle([ls.x, ls.y], [le.x, le.y], [lw.x, lw.y])
        right_elbow_angle = MathUtils.calculate_angle([rs.x, rs.y], [re.x, re.y], [rw.x, rw.y])
        elbow_angle = (left_elbow_angle + right_elbow_angle) / 2

        left_back_angle = MathUtils.calculate_angle([ls.x, ls.y], [lh.x, lh.y], [lk.x, lk.y])
        right_back_angle = MathUtils.calculate_angle([rs.x, rs.y], [rh.x, rh.y], [rk.x, rk.y])
        back_angle = (left_back_angle + right_back_angle) / 2

        left_hip_angle = MathUtils.calculate_angle([lk.x, lk.y], [lh.x, lh.y], [ls.x, ls.y])
        right_hip_angle = MathUtils.calculate_angle([rk.x, rk.y], [rh.x, rh.y], [rs.x, rs.y])
        hip_angle = (left_hip_angle + right_hip_angle) / 2

        # Сглаживание углов — меньше дрожания и ложных срабатываний
        self._elbow_smooth.push(elbow_angle)
        self._back_smooth.push(back_angle)
        self._hip_smooth.push(hip_angle)
        smooth_elbow = self._elbow_smooth.value()
        smooth_hip = self._hip_smooth.value()
        smooth_back = self._back_smooth.value()

        shoulder_width = abs(ls.x - rs.x)
        shoulder_hip_y_diff = abs(ls.y - lh.y)
        torso_length = math.hypot(ls.x - lh.x, ls.y - lh.y)
        shoulder_center = [(ls.x + rs.x) / 2, (ls.y + rs.y) / 2]
        elbow_flare_angle = MathUtils.calculate_angle([le.x, le.y], shoulder_center, [re.x, re.y])
        elbows_flared = elbow_flare_angle > 100

        # Кисти под плечами (по X)
        l_hand_under_shoulder = abs(lw.x - ls.x) < 0.12
        r_hand_under_shoulder = abs(rw.x - rs.x) < 0.12

        # Руки на полу: пороги ослаблены (камера/угол дают меньший y запястий), плюс запас по позе
        # y в MediaPipe: вниз растёт, пол = высокий y. Мягкий вариант — при явном упоре лёжа
        wrists_avg_y = (lw.y + rw.y) / 2
        wrists_min_y = min(lw.y, rw.y)
        hands_y_strict = (lw.y > 0.70 and rw.y > 0.70) or wrists_avg_y > 0.72
        # если поза явно упор лёжа (руки выпрямлены) и запястья не вверху — считаем руки на полу
        arms_extended = elbow_angle > 120
        hands_y_relaxed = arms_extended and wrists_min_y > 0.58 and wrists_avg_y > 0.62
        hands_near_floor = hands_y_strict or hands_y_relaxed

        if not hands_near_floor:
            self._hands_off_frames += 1
            if self._hands_off_frames >= self.HANDS_OFF_GRACE:
                self.hands_on_ground = False
                errors.append(err(
                    "Руки не на полу.",
                    "Опустите ладони на пол на ширине плеч, кисти строго под плечами. Убедитесь, что руки целиком в кадре — так ИИ сможет считать повторения.",
                    1
                ))
                return "Поставьте руки на пол!", errors
        else:
            self._hands_off_frames = 0
            self.hands_on_ground = True

        # Конкретные ошибки по углам при старте / в верхней точке
        if elbow_angle > 120:
            if not l_hand_under_shoulder and lw.x > ls.x + 0.05:
                errors.append(err(
                    "Левая кисть впереди плеча.",
                    "Поставьте левую ладонь строго под левым плечом (вертикальная линия вниз).",
                    2
                ))
            if not r_hand_under_shoulder and rw.x < rs.x - 0.05:
                errors.append(err(
                    "Правая кисть впереди плеча.",
                    "Поставьте правую ладонь строго под правым плечом (вертикальная линия вниз).",
                    2
                ))
            if hip_angle < 160 and elbow_angle > 150:
                errors.append(err(
                    f"Угол в тазу: {hip_angle:.0f}° — таз должен быть в одну линию с корпусом (~180°).",
                    "Напрягите ягодицы и пресс, не прогибайтесь и не поднимайте таз.",
                    2
                ))
            if back_angle < 170 and elbow_angle > 150:
                errors.append(err(
                    f"Угол спины (плечо–таз–колено): {back_angle:.0f}° — спина должна быть прямее.",
                    "Выпрямите корпус в одну линию от головы до пят. Не прогибайте поясницу.",
                    2
                ))
            if shoulder_hip_y_diff > 0.25:
                errors.append(err(
                    "Плечи и таз не в одной горизонтали — корпус наклонён.",
                    "Держите плечи и таз на одной линии (параллельно полу). Напрягите пресс.",
                    2
                ))

        start_pose = (
            smooth_elbow > 150 and smooth_hip > 135 and smooth_back > 140 and
            shoulder_width > 0.15 and torso_length > 0.10 and
            shoulder_hip_y_diff < 0.30 and self.hands_on_ground
        )
        self.ready_buffer.append(start_pose)

        if smooth_elbow > 150:
            self.top_position_pose = (
                smooth_hip > 135 and smooth_back > 140 and shoulder_width > 0.15 and
                torso_length > 0.10 and shoulder_hip_y_diff < 0.30 and self.hands_on_ground
            )

        if not self.ready:
            if sum(self.ready_buffer) >= 12:
                self.ready = True
                return "Готово. Начинайте отжимания!", errors
            return "Примите упор лёжа...", errors

        if not self.hands_on_ground:
            errors.append(err(
                "Руки оторваны от пола.",
                "Держите ладони плотно на полу на протяжении всего движения. Отрывание рук не только не засчитывается — так легко потерять равновесие.",
                1
            ))
            return "Руки подняты! Стоп.", errors

        if smooth_elbow < 90:
            self._stage_down_confirm += 1
            self._stage_up_confirm = 0
        elif smooth_elbow > 150:
            self._stage_up_confirm += 1
            self._stage_down_confirm = 0
        else:
            self._stage_down_confirm = 0
            self._stage_up_confirm = 0

        if smooth_elbow < 90 and self.stage == "up" and self._stage_down_confirm >= self.STAGE_CONFIRM_NEEDED:
            self.stage = "down"
            self.down_hold_frames = 0
            self._stage_down_confirm = 0
            return "Движение вниз...", errors

        if self.stage == "down":
            if smooth_elbow < 90:
                self.down_hold_frames += 1
                if elbows_flared:
                    errors.append(err(
                        f"Угол между локтями: {elbow_flare_angle:.0f}° — локти разведены (норма до 90–100°).",
                        "Сгибайте руки вдоль корпуса: локти направлены назад. Так нагрузка идёт в грудь и трицепс — и повтор засчитается.",
                        2
                    ))
                # Асимметрия локтей
                elbow_diff = abs(left_elbow_angle - right_elbow_angle)
                if elbow_diff > 15:
                    if left_elbow_angle < right_elbow_angle - 10:
                        errors.append(err(
                            f"Левый локоть согнут сильнее ({left_elbow_angle:.0f}° vs {right_elbow_angle:.0f}°) — асимметрия.",
                            "Опускайтесь равномерно: оба локтя сгибаются одинаково. Выравняйте нагрузку на обе руки.",
                            2
                        ))
                    else:
                        errors.append(err(
                            f"Правый локоть согнут сильнее ({right_elbow_angle:.0f}° vs {left_elbow_angle:.0f}°) — асимметрия.",
                            "Опускайтесь равномерно: оба локтя сгибаются одинаково. Выравняйте нагрузку на обе руки.",
                            2
                        ))
                # Прогиб спины в нижней точке
                if back_angle < 150:
                    errors.append(err(
                        f"Угол спины внизу: {back_angle:.0f}° — не прогибайтесь в пояснице.",
                        "Держите корпус прямой линией и в нижней точке. Напрягите пресс.",
                        2
                    ))
                if hip_angle < 120:
                    errors.append(err(
                        f"Угол в тазу внизу: {hip_angle:.0f}° — таз не поднимайте.",
                        "Таз держите в одну линию с плечами и ногами на всём движении.",
                        2
                    ))

            if smooth_elbow > 150:
                if self._stage_up_confirm >= self.STAGE_CONFIRM_NEEDED:
                    if self.down_hold_frames >= self.MIN_HOLD_FRAMES:
                        if self.top_position_pose and self.hands_on_ground:
                            self.count += 1
                            feedback = "Отжимание засчитано!"
                        else:
                            if hip_angle < 135:
                                if 128 <= hip_angle < 135:
                                    errors.append(err(
                                        f"Почти! Угол таза {hip_angle:.0f}° — выпрямите ещё чуть-чуть.",
                                        "Голова — плечи — таз — ноги в одну линию. Ещё немного напрягите пресс и ягодицы.",
                                        2
                                    ))
                                else:
                                    errors.append(err(
                                        f"В верхней точке угол таза: {hip_angle:.0f}° — выпрямите линию корпуса.",
                                        "Голова — плечи — таз — ноги в одну линию. Напрягите пресс и ягодицы.",
                                        2
                                    ))
                            if back_angle < 140:
                                errors.append(err(
                                    f"В верхней точке угол спины: {back_angle:.0f}° — не прогибайте поясницу.",
                                    "Держите спину прямой. Не поднимайте таз вверх.",
                                    2
                                ))
                            if shoulder_hip_y_diff >= 0.30:
                                errors.append(err(
                                    "В верхней точке плечи и таз не в одной линии.",
                                    "Выровняйте корпус параллельно полу. Напрягите пресс.",
                                    2
                                ))
                            if not errors:
                                errors.append(err(
                                    "Неправильная форма в верхней точке.",
                                    "Держите корпус одной прямой линией: голова — плечи — таз — ноги. Не прогибайте поясницу и не поднимайте таз.",
                                    2
                                ))
                            feedback = "Исправьте форму корпуса!"
                    else:
                        if self.down_hold_frames == 1:
                            errors.append(err(
                                "Почти! Ещё мгновение внизу — задержка почти достаточная.",
                                "В нижней точке задержитесь ещё чуть-чуть (1–2 сек), затем выжмите вверх.",
                                2
                            ))
                        else:
                            errors.append(err(
                                f"В нижней точке задержались мало кадров — нужно 1–2 сек (локти ~90°).",
                                "В нижней точке задержитесь на 1–2 секунды, затем плавно выжмите вверх.",
                                2
                            ))
                        feedback = "Задержитесь внизу!"

                    self.stage = "up"
                    self.down_hold_frames = 0
                    self._stage_up_confirm = 0
                return feedback, errors

        return "Продолжайте...", errors

class SquatWorkout(PoseDetectionBase):
    """Приседания: сглаживание углов, контроль по каждой ноге."""

    MIN_DOWN_FRAMES = 5

    def __init__(self):
        super().__init__("Приседания — TeminaFit v3.0")
        self.ready_buffer = deque([False] * 15, maxlen=15)
        self.min_knee_angle_in_rep = 180
        self.down_hold_frames = 0
        self._knee_smooth = AngleSmoother(5)
        self._stage_down_confirm = 0
        self._stage_up_confirm = 0
        self.STAGE_CONFIRM_NEEDED = 2

    def get_state(self) -> dict:
        s = super().get_state()
        s["min_knee_angle_in_rep"] = getattr(self, "min_knee_angle_in_rep", 180)
        s["down_hold_frames"] = getattr(self, "down_hold_frames", 0)
        return s

    def load_state(self, state: dict):
        super().load_state(state)
        self.min_knee_angle_in_rep = state.get("min_knee_angle_in_rep", 180)
        self.down_hold_frames = state.get("down_hold_frames", 0)

    def _process_pose(self, landmarks) -> Tuple[str, List[Dict[str, str]]]:
        """Приседания: контроль углов в коленях, тазу, симметрия ног, наклон корпуса."""
        if not landmarks:
            self.ready_buffer.append(False)
            return "Ожидание полного тела...", []

        lm = landmarks.landmark
        errors: List[Dict[str, Any]] = []

        lhip, lknee, lankle = lm[23], lm[25], lm[27]
        rhip, rknee, rankle = lm[24], lm[26], lm[28]
        lshoulder, rshoulder = lm[11], lm[12]

        l_knee_angle = MathUtils.calculate_angle([lhip.x, lhip.y], [lknee.x, lknee.y], [lankle.x, lankle.y])
        r_knee_angle = MathUtils.calculate_angle([rhip.x, rhip.y], [rknee.x, rknee.y], [rankle.x, rankle.y])
        knee_angle = (l_knee_angle + r_knee_angle) / 2

        self._knee_smooth.push(knee_angle)
        smooth_knee = self._knee_smooth.value()

        l_hip_angle = MathUtils.calculate_angle([lknee.x, lknee.y], [lhip.x, lhip.y], [lshoulder.x, lshoulder.y])
        r_hip_angle = MathUtils.calculate_angle([rknee.x, rknee.y], [rhip.x, rhip.y], [rshoulder.x, rshoulder.y])
        hip_angle = (l_hip_angle + r_hip_angle) / 2

        left_leg_down = lankle.y > lknee.y and lknee.y > lhip.y
        right_leg_down = rankle.y > rknee.y and rknee.y > rhip.y
        body_visible = left_leg_down and right_leg_down

        # Колени вперёд за носки — по сторонам
        left_knee_over = lknee.x > lankle.x and lhip.x < lknee.x
        right_knee_over = rknee.x > rankle.x and rhip.x < rknee.x
        if left_knee_over and right_knee_over:
            errors.append(err(
                "Оба колена уходят вперёд за носки.",
                "Отводите таз назад, как при посадке на стул. Колени не должны сильно выходить вперёд за стопы — так безопаснее для суставов.",
                2
            ))
        elif left_knee_over:
            errors.append(err(
                "Левое колено уходит вперёд за носок.",
                "Отведите таз назад и следите, чтобы левое колено не заходило далеко вперёд за стопу.",
                2
            ))
        elif right_knee_over:
            errors.append(err(
                "Правое колено уходит вперёд за носок.",
                "Отведите таз назад и следите, чтобы правое колено не заходило далеко вперёд за стопу.",
                2
            ))

        # Асимметрия углов коленей
        knee_diff = abs(l_knee_angle - r_knee_angle)
        if body_visible and knee_diff > 12 and 80 < knee_angle < 175:
            if l_knee_angle < r_knee_angle - 10:
                errors.append(err(
                    f"Левое колено согнуто сильнее ({l_knee_angle:.0f}° vs {r_knee_angle:.0f}°) — приседайте симметрично.",
                    "Опускайтесь равномерно: оба колена сгибаются на одинаковый угол. Переносите вес по центру.",
                    2
                ))
            elif r_knee_angle < l_knee_angle - 10:
                errors.append(err(
                    f"Правое колено согнуто сильнее ({r_knee_angle:.0f}° vs {l_knee_angle:.0f}°) — приседайте симметрично.",
                    "Опускайтесь равномерно: оба колена сгибаются на одинаковый угол. Переносите вес по центру.",
                    2
                ))

        upright_pose = knee_angle > 170 and hip_angle > 170 and body_visible
        self.ready_buffer.append(upright_pose)

        if not self.ready:
            if sum(self.ready_buffer) >= 10:
                self.ready = True
                return "Готово. Начинайте приседания!", errors
            return "Встаньте прямо для начала", errors

        if not body_visible:
            errors.append(err(
                "Не видно полное тело.",
                "Отойдите от камеры так, чтобы в кадре были голова, корпус и обе ноги целиком. ИИ считает приседания только когда видит полное тело.",
                1
            ))
            return "Покажите всё тело, обе ноги должны быть видны", errors

        if smooth_knee < 90:
            self._stage_down_confirm += 1
            self._stage_up_confirm = 0
        elif smooth_knee > 170:
            self._stage_up_confirm += 1
            self._stage_down_confirm = 0
        else:
            self._stage_down_confirm = 0
            self._stage_up_confirm = 0

        if smooth_knee < 90 and self.stage == "up" and self._stage_down_confirm >= self.STAGE_CONFIRM_NEEDED:
            self.stage = "down"
            self.min_knee_angle_in_rep = knee_angle
            self.down_hold_frames = 0
            self._stage_down_confirm = 0
            return "Приседайте ниже...", errors

        if self.stage == "down":
            if smooth_knee < 165:
                self.down_hold_frames += 1
            if knee_angle < self.min_knee_angle_in_rep:
                self.min_knee_angle_in_rep = knee_angle
            if smooth_knee > 170:
                if self._stage_up_confirm >= self.STAGE_CONFIRM_NEEDED:
                    deep_enough = self.min_knee_angle_in_rep < 100
                    held_down_enough = self.down_hold_frames >= self.MIN_DOWN_FRAMES
                    if deep_enough and held_down_enough:
                        self.count += 1
                        feedback = "Приседание засчитано!"
                    elif not deep_enough:
                        if 92 <= self.min_knee_angle_in_rep < 100:
                            errors.append(err(
                                f"Почти! Угол в коленях {self.min_knee_angle_in_rep:.0f}° — присядьте ещё чуть глубже (нужно < 90°).",
                                "Опускайтесь до угла меньше 90° (бедро параллельно полу или ниже), затем вставайте.",
                                2
                            ))
                        else:
                            errors.append(err(
                                f"Угол в коленях внизу: {self.min_knee_angle_in_rep:.0f}° — нужно меньше 90° (глубже).",
                                "Опускайтесь до угла в колене меньше 90° (бедро хотя бы параллельно полу), затем выпрямляйтесь.",
                                2
                            ))
                        feedback = "Приседайте глубже!"
                    else:
                        errors.append(err(
                            "Слишком быстро встали из нижней точки.",
                            "Задержитесь в нижней точке приседа на 1–2 секунды, затем плавно вставайте. Так повтор будет засчитан.",
                            2
                        ))
                        feedback = "Задержитесь внизу!"
                    self.stage = "up"
                    self.min_knee_angle_in_rep = 180
                    self.down_hold_frames = 0
                    self._stage_up_confirm = 0
                    return feedback, errors

        return "Продолжайте...", errors

class CrunchesWorkout(PoseDetectionBase):
    """Crunches exercise detection and counting - FIXED VERSION"""
    
    def __init__(self):
        super().__init__("Скручивания — TeminaFit v3.0")
        self.start_shoulder_y = None
        self.start_hip_y = None
        self.ready_buffer = deque([False] * 15, maxlen=15)
        self.stable_reference_points = deque(maxlen=10)
        self.camera_movement_threshold = 0.03
        self.crunch_down_frames = 0
        
    def _check_camera_stability(self) -> bool:
        """Проверяет стабильность камеры по реперным точкам"""
        if len(self.stable_reference_points) < 5:
            return True
            
        # Вычисляем максимальное движение за последние кадры
        max_movement = 0
        for i in range(1, len(self.stable_reference_points)):
            dx = abs(self.stable_reference_points[i][0] - self.stable_reference_points[i-1][0])
            dy = abs(self.stable_reference_points[i][1] - self.stable_reference_points[i-1][1])
            movement = math.sqrt(dx*dx + dy*dy)
            max_movement = max(max_movement, movement)
        
        return max_movement < 0.02
        
    def _process_pose(self, landmarks) -> Tuple[str, List[Dict[str, str]]]:
        """Скручивания: считаются только правильные повторения. Ошибки с подсказками."""
        if not landmarks:
            self.ready_buffer.append(False)
            return "Ожидание полного тела...", []

        lm = landmarks.landmark
        errors: List[Dict[str, str]] = []

        l_shoulder, r_shoulder = lm[11], lm[12]
        l_hip, r_hip = lm[23], lm[24]
        l_knee, r_knee = lm[25], lm[26]
        nose = lm[0]

        shoulder_pt = ((l_shoulder.x + r_shoulder.x)/2, (l_shoulder.y + r_shoulder.y)/2)
        hip_pt = ((l_hip.x + r_hip.x)/2, (l_hip.y + r_hip.y)/2)
        knee_pt = ((l_knee.x + r_knee.x)/2, (l_knee.y + r_knee.y)/2)
        nose_pt = (nose.x, nose.y)

        current_reference = (nose.x, nose.y)
        self.stable_reference_points.append(current_reference)
        camera_stable = self._check_camera_stability()

        torso_angle = MathUtils.calculate_angle(knee_pt, hip_pt, shoulder_pt)

        # Стартовая поза: человек полностью в кадре, лёжа боком (вид сбоку)
        min_x = min(nose_pt[0], shoulder_pt[0], hip_pt[0], knee_pt[0])
        max_x = max(nose_pt[0], shoulder_pt[0], hip_pt[0], knee_pt[0])
        min_y = min(nose_pt[1], shoulder_pt[1], hip_pt[1], knee_pt[1])
        max_y = max(nose_pt[1], shoulder_pt[1], hip_pt[1], knee_pt[1])
        in_frame = (0.06 <= min_x and max_x <= 0.94 and 0.06 <= min_y and max_y <= 0.94)
        body_span = math.hypot(shoulder_pt[0] - knee_pt[0], shoulder_pt[1] - knee_pt[1])
        full_body_visible = in_frame and body_span > 0.22
        flat_lying = torso_angle > 168
        shoulder_spread_x = abs(l_shoulder.x - r_shoulder.x)
        side_view = shoulder_spread_x < 0.2

        if not self.ready:
            calibration_pose = full_body_visible and flat_lying and camera_stable and side_view
            if calibration_pose:
                self.start_shoulder_y = shoulder_pt[1]
                self.start_hip_y = hip_pt[1]
                self.ready_buffer.append(True)
            else:
                self.ready_buffer.append(False)
                if not camera_stable:
                    errors.append(err(
                        "Камера двигается.",
                        "Зафиксируйте телефон или камеру неподвижно (например, прислоните к стене или поставьте на штатив). Так ИИ сможет корректно считать повторения.",
                        1
                    ))
                elif not full_body_visible:
                    errors.append(err(
                        "Тело не полностью в кадре.",
                        "Лягте на спину боком к камере так, чтобы в кадре были видны голова, корпус и ноги целиком (вид сбоку).",
                        1
                    ))
                elif not side_view:
                    errors.append(err(
                        "Камера видит вас не сбоку.",
                        "Полностью повернитесь боком к камере: лёжа на спине, боком к объективу. Тогда скручивания будут правильно распознаваться.",
                        1
                    ))
                elif not flat_lying:
                    errors.append(err(
                        "Стартовая поза не выпрямлена.",
                        "Лягте на спину, ноги согнуты в коленях. Выпрямите корпус в одну линию (угол плечи–таз–колени около 180°), затем начинайте скручивания.",
                        2
                    ))
            if sum(self.ready_buffer) >= 12:
                self.ready = True
                self.crunch_down_frames = 0
                return "Готово. Начинайте скручивания!", errors
            return "Примите стартовую позицию: лёжа боком к камере, всё тело в кадре.", errors

        if not camera_stable:
            errors.append(err(
                "Камера двигается во время упражнения.",
                "Держите камеру неподвижно на протяжении всего подхода — иначе подсчёт может сбиться.",
                1
            ))
        hip_y_diff = abs(self.start_hip_y - hip_pt[1])
        if hip_y_diff > 0.06:
            errors.append(err(
                "Таз отрывается или смещается.",
                "Работайте только верхней частью корпуса: поднимайте плечи к коленям. Таз и поясница должны оставаться на полу — так скручивание засчитается и нагрузка пойдёт в пресс.",
                2
            ))

        if torso_angle <= 118 and self.stage == "up":
            self.stage = "down"
            self.crunch_down_frames = 0
            return "Скручивание...", errors

        if self.stage == "down":
            if torso_angle < 165:
                self.crunch_down_frames += 1
            # Угол шеи: подбородок не к груди (избегаем перегрузки шеи)
            nose_pt = (nose.x, nose.y)
            neck_angle = MathUtils.calculate_angle(knee_pt, shoulder_pt, nose_pt)
            if 50 < neck_angle < 95 and torso_angle < 140:
                errors.append(err(
                    "Подбородок слишком близко к груди — лишняя нагрузка на шею.",
                    "Держите голову в нейтральном положении: взгляд в потолок или вперёд, не тяните подбородок к груди.",
                    2
                ))
            if torso_angle >= 165:
                counted = self.crunch_down_frames >= 2
                if counted:
                    self.count += 1
                feedback = "Повтор засчитан!" if (counted and len(errors) == 0) else ("Держите скручивание чуть дольше" if not counted else "Исправьте форму!")
                self.stage = "up"
                self.crunch_down_frames = 0
                return feedback, errors

        return "Продолжайте...", errors

class PlankWorkout(PoseDetectionBase):
    """
    Планка: учёт времени удержания в правильной позе.
    count = секунды в правильной планке.
    Античит: проверка видимости, выравнивания тела (плечи–таз–лодыжки),
    стабильности (нет резких скачков — человек не ушёл из кадра и не мошенничает).
    """

    SECONDS_PER_COUNT = 1  # 1 count = 1 second
    FRAMES_PER_SECOND = 10  # ожидаемый FPS при отправке кадров
    GOOD_FRAMES_NEEDED = 8  # подряд хороших кадров для засчёта 1 сек
    MIN_VISIBILITY_AVG = 0.5  # минимальная средняя видимость ключевых точек
    MAX_HIP_SAG_DEG = 25  # макс. "провисание" таза (угол от прямой линии) в градусах
    MAX_HIP_PIKE_DEG = 25  # макс. "пик" таза вверх
    STABILITY_THRESHOLD = 0.08  # макс. смещение центра тела между кадрами (античит)
    READY_BUFFER_LEN = 12  # кадров в стартовой позе для ready

    def __init__(self):
        super().__init__("Планка — TeminaFit")
        self.ready_buffer = deque([False] * self.READY_BUFFER_LEN, maxlen=self.READY_BUFFER_LEN)
        self.good_hold_frames = 0
        self.last_center = None
        self.hold_start_time = None
        self.max_hold_seconds = 0
        self.current_hold_seconds = 0

    def get_state(self) -> dict:
        s = super().get_state()
        s["max_hold_seconds"] = getattr(self, "max_hold_seconds", 0)
        s["current_hold_seconds"] = getattr(self, "current_hold_seconds", 0)
        return s

    def load_state(self, state: dict):
        super().load_state(state)
        self.max_hold_seconds = state.get("max_hold_seconds", 0)
        self.current_hold_seconds = state.get("current_hold_seconds", 0)

    def _process_pose(self, landmarks) -> Tuple[str, List[Dict[str, str]]]:
        if not landmarks:
            self.ready_buffer.append(False)
            self.good_hold_frames = 0
            return "Ожидание... Встаньте в кадр.", []

        lm = landmarks.landmark
        errors: List[Dict[str, str]] = []

        # Ключевые точки для планки (вид сбоку: плечи, таз, лодыжки)
        ls, rs = lm[11], lm[12]
        lh, rh = lm[23], lm[24]
        la, ra = lm[27], lm[28]
        le, re = lm[13], lm[14]
        lw, rw = lm[15], lm[16]

        # Центр тела (для античита — стабильность)
        center_x = (ls.x + rs.x + lh.x + rh.x) / 4
        center_y = (ls.y + rs.y + lh.y + rh.y) / 4
        if self.last_center is not None:
            dx = abs(center_x - self.last_center[0])
            dy = abs(center_y - self.last_center[1])
            if math.sqrt(dx*dx + dy*dy) > self.STABILITY_THRESHOLD:
                self.good_hold_frames = 0
                errors.append(err(
                    "Резкое движение.",
                    "Держите планку статично: не сдвигайтесь по полу и не двигайте камеру во время удержания. Секунды считаются только при стабильной позе.",
                    1
                ))
                self.last_center = (center_x, center_y)
                return "Держите позу стабильно!", errors
        self.last_center = (center_x, center_y)

        # Видимость (античит: человек должен быть в кадре)
        vis = [ls.visibility, rs.visibility, lh.visibility, rh.visibility, la.visibility, ra.visibility]
        avg_vis = sum(vis) / len(vis) if vis else 0
        if avg_vis < self.MIN_VISIBILITY_AVG:
            self.good_hold_frames = 0
            errors.append(err(
                "Не видно тело целиком.",
                "Расположите камеру сбоку так, чтобы были видны плечи, таз и ноги. Тогда ИИ сможет проверить прямую линию и засчитать секунды.",
                1
            ))
            return "Покажите тело в кадре.", errors

        # Средние точки
        shoulder_pt = ((ls.x + rs.x) / 2, (ls.y + rs.y) / 2)
        hip_pt = ((lh.x + rh.x) / 2, (lh.y + rh.y) / 2)
        ankle_pt = ((la.x + ra.x) / 2, (la.y + ra.y) / 2)

        # Угол линия плечи-таз-лодыжки (в идеале ~180° — прямая линия)
        torso_angle = MathUtils.calculate_angle(shoulder_pt, hip_pt, ankle_pt)
        body_straight = (180 - self.MAX_HIP_SAG_DEG) <= torso_angle <= (180 + self.MAX_HIP_PIKE_DEG)

        # Руки/локти: локти под плечами
        elbow_shoulder_ok = (abs(le.x - ls.x) < 0.15 and abs(re.x - rs.x) < 0.15) or \
                           (abs(lw.x - ls.x) < 0.15 and abs(rw.x - rs.x) < 0.15)
        if not elbow_shoulder_ok:
            errors.append(err(
                "Локти или кисти не под плечами.",
                "Поставьте предплечья или ладони строго под плечами. Так нагрузка распределяется правильно и поза засчитывается.",
                2
            ))

        if not body_straight:
            if torso_angle < 180 - self.MAX_HIP_SAG_DEG:
                errors.append(err(
                    f"Угол линия плечи–таз–лодыжки: {torso_angle:.0f}° — таз провисает (норма ~180°).",
                    "Поддерживайте прямую линию: голова — плечи — таз — ноги. Напрягите пресс и ягодицы, не прогибайтесь в пояснице.",
                    2
                ))
            else:
                errors.append(err(
                    f"Угол линия плечи–таз–лодыжки: {torso_angle:.0f}° — таз поднят слишком высоко (норма ~180°).",
                    "Опустите таз в одну линию с плечами и ногами. Не поднимайте ягодицы вверх — «домиком» планка не засчитывается.",
                    2
                ))

        good_pose = body_straight and elbow_shoulder_ok and avg_vis >= self.MIN_VISIBILITY_AVG
        self.ready_buffer.append(good_pose)

        if not self.ready:
            if sum(self.ready_buffer) >= 10:
                self.ready = True
                self.hold_start_time = time.time()
                return "Готово. Держите планку!", errors
            return "Примите упор на предплечьях/ладонах, тело в одну линию.", errors

        if not good_pose:
            self.good_hold_frames = 0
            if errors:
                return "Исправьте позу.", errors
            return "Держите прямую линию корпуса.", errors

        self.good_hold_frames += 1
        if self.good_hold_frames >= self.GOOD_FRAMES_NEEDED:
            self.good_hold_frames = 0
            self.count += 1
            self.current_hold_seconds = self.count
            if self.current_hold_seconds > self.max_hold_seconds:
                self.max_hold_seconds = self.current_hold_seconds
            return f"Отлично! {self.count} сек.", errors

        return f"Держите! {self.count} сек.", errors


class PullupWorkout(PoseDetectionBase):
    """Pull-up exercise detection and counting"""
    
    def __init__(self):
        super().__init__("Подтягивания — TeminaFit v3.0")
        self.ready_buffer = deque([False] * 15, maxlen=15)

    def _process_pose(self, landmarks) -> Tuple[str, List[Dict[str, str]]]:
        """Подтягивания: детекция и подсчёт. Ошибки с подсказками."""
        if not landmarks:
            self.ready_buffer.append(False)
            return "Ожидание полного тела...", []

        lm = landmarks.landmark
        errors: List[Dict[str, str]] = []

        l_shoulder, r_shoulder = lm[11], lm[12]
        l_elbow, r_elbow = lm[13], lm[14]
        l_wrist, r_wrist = lm[15], lm[16]
        l_hip, r_hip = lm[23], lm[24]

        left_elbow_angle = MathUtils.calculate_angle([l_shoulder.x, l_shoulder.y], [l_elbow.x, l_elbow.y], [l_wrist.x, l_wrist.y])
        right_elbow_angle = MathUtils.calculate_angle([r_shoulder.x, r_shoulder.y], [r_elbow.x, r_elbow.y], [r_wrist.x, r_wrist.y])
        elbow_angle = (left_elbow_angle + right_elbow_angle) / 2

        hands_above_shoulders = (l_wrist.y < l_shoulder.y and r_wrist.y < r_shoulder.y)
        body_straight = abs(l_shoulder.y - l_hip.y) < 0.2

        # Асимметрия рук при подтягивании
        elbow_diff = abs(left_elbow_angle - right_elbow_angle)
        if elbow_diff > 15 and 50 < elbow_angle < 160:
            if left_elbow_angle < right_elbow_angle - 10:
                errors.append(err(
                    f"Левый локоть согнут сильнее ({left_elbow_angle:.0f}° vs {right_elbow_angle:.0f}°) — подтягивайтесь симметрично.",
                    "Подтягивайтесь равномерно: оба локтя сгибаются одинаково. Не тяните одной стороной сильнее.",
                    2
                ))
            elif right_elbow_angle < left_elbow_angle - 10:
                errors.append(err(
                    f"Правый локоть согнут сильнее ({right_elbow_angle:.0f}° vs {left_elbow_angle:.0f}°) — подтягивайтесь симметрично.",
                    "Подтягивайтесь равномерно: оба локтя сгибаются одинаково. Не тяните одной стороной сильнее.",
                    2
                ))

        start_pose = hands_above_shoulders and body_straight
        self.ready_buffer.append(start_pose)

        if not self.ready:
            if sum(self.ready_buffer) >= 10:
                self.ready = True
                return "Готово. Начинайте подтягивания!", errors
            if not hands_above_shoulders:
                errors.append(err(
                    "Руки не выше плеч в старте.",
                    "В стартовой позиции кисти должны быть выше плеч — полное разгибание рук на перекладине. Тогда повтор будет корректно засчитан.",
                    1
                ))
            if not body_straight:
                errors.append(err(
                    "Корпус не выпрямлен.",
                    "Держите тело вертикально: голова, плечи, таз и ноги в одну линию, без раскачки. Так техника чище и ИИ точнее считает.",
                    2
                ))
            return "Повисните на перекладине...", errors

        if elbow_angle < 90 and self.stage == "down":
            self.stage = "up"
            return "Подтягивайтесь...", errors
        if elbow_angle > 160 and self.stage == "up":
            self.count += 1
            self.stage = "down"
            return "Подтягивание засчитано!", errors

        return "Продолжайте...", errors
    # В exercises.py (дополнение к классам упражнений)
def complete_workout(self, count, errors=0):
    """Завершает тренировку и обновляет квесты"""
    # Сохраняем подход
    workout_data = {
        'count': count,
        'errors': errors,
        'exercise_type': self.exercise_type
    }
    
    # Обновляем квесты
    if self.request.user.is_authenticated:
        player, created = Player.objects.get_or_create(user=self.request.user)
        quest_manager = QuestManager(player)
        completed_quests = quest_manager.update_quest_progress(
            self.exercise_type, count, errors
        )
        
        # Увеличиваем усталость
        player.add_fatigue(count * 0.5)
        player.save()
        
        return {
            'completed_quests': completed_quests,
            'workout_data': workout_data
        }
    
    return {'workout_data': workout_data}