# pose_manager.py (ИСПРАВЛЕННАЯ ВЕРСИЯ БЕЗ SINGLETON)
"""
Менеджер для работы с MediaPipe Pose.
Каждый запрос создает свой экземпляр Pose для thread-safe работы.
"""
import logging
import time
from typing import Optional, Dict, Any
import mediapipe as mp

logger = logging.getLogger(__name__)


class PoseManager:
    """
    Контекстный менеджер для работы с MediaPipe Pose.
    Автоматически создает и закрывает ресурсы.
    """
    
    # Конфигурации для разных типов устройств
    CONFIGURATIONS = {
        'desktop': {
            'model_complexity': 2,
            'min_detection_confidence': 0.5,
            'min_tracking_confidence': 0.5,
        },
        'mobile': {
            'model_complexity': 1,
            'min_detection_confidence': 0.5,
            'min_tracking_confidence': 0.5,
        },
        'low_power': {
            'model_complexity': 0,
            'min_detection_confidence': 0.5,
            'min_tracking_confidence': 0.5,
        }
    }
    
    def __init__(self, 
                 static_image_mode: bool = False,
                 model_complexity: int = 1,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 device_type: str = 'desktop'):
        """
        Инициализация менеджера поз.
        
        Args:
            static_image_mode: Если True, обрабатывает каждое изображение независимо
            model_complexity: Сложность модели (0, 1, 2)
            min_detection_confidence: Минимальная уверенность для детекции
            min_tracking_confidence: Минимальная уверенность для отслеживания
            device_type: Тип устройства для оптимизации
        """
        self.static_image_mode = static_image_mode
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.device_type = device_type
        
        # Загружаем MediaPipe только при первом использовании
        self.mp_pose = None
        self.pose = None
        self.is_initialized = False
        
        # Статистика использования
        self.created_at = time.time()
        self.frames_processed = 0
        self.total_processing_time = 0
        
        # Применяем конфигурацию для устройства
        self._apply_device_configuration()
    
    def _apply_device_configuration(self):
        """Применяет оптимальную конфигурацию для типа устройства"""
        config = self.CONFIGURATIONS.get(self.device_type, self.CONFIGURATIONS['desktop'])
        
        if self.device_type == 'mobile':
            self.model_complexity = min(self.model_complexity, 1)
        elif self.device_type == 'low_power':
            self.model_complexity = 0
        
        # Обновляем настройки из конфигурации
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def _initialize(self):
        """Ленивая инициализация MediaPipe"""
        if self.is_initialized:
            return
        
        try:
            # Импортируем mediapipe только когда нужно
            if self.mp_pose is None:
                self.mp_pose = mp.solutions.pose
            
            # Создаем экземпляр Pose
            self.pose = self.mp_pose.Pose(
                static_image_mode=self.static_image_mode,
                model_complexity=self.model_complexity,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_tracking_confidence,
                smooth_landmarks=True,
                enable_segmentation=False,
                smooth_segmentation=True,
            )
            
            self.is_initialized = True
            logger.debug(f"PoseManager инициализирован для {self.device_type}")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации PoseManager: {e}")
            raise
    
    def __enter__(self):
        """Вход в контекстный менеджер"""
        self._initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера - закрываем ресурсы"""
        self.close()
    
    def process(self, image, calculate_metrics: bool = False) -> Optional[Any]:
        """
        Обрабатывает изображение и возвращает результаты.
        
        Args:
            image: RGB изображение (numpy array)
            calculate_metrics: Если True, считает метрики производительности
            
        Returns:
            Результаты MediaPipe Pose или None
        """
        if not self.is_initialized or self.pose is None:
            self._initialize()
        
        start_time = time.time()
        
        try:
            # Конвертируем в RGB если нужно
            if len(image.shape) == 3 and image.shape[2] == 3:
                # Уже RGB
                pass
            elif len(image.shape) == 3 and image.shape[2] == 4:
                # RGBA → RGB
                import cv2
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)
            elif len(image.shape) == 2:
                # Grayscale → RGB
                import cv2
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
            # Обрабатываем изображение
            results = self.pose.process(image)
            
            # Считаем метрики если нужно
            if calculate_metrics:
                processing_time = time.time() - start_time
                self.frames_processed += 1
                self.total_processing_time += processing_time
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка обработки изображения: {e}")
            return None
    
    def close(self):
        """Закрывает ресурсы MediaPipe"""
        if self.pose is not None:
            try:
                self.pose.close()
                self.pose = None
                self.is_initialized = False
                logger.debug(f"PoseManager закрыт, обработано {self.frames_processed} кадров")
            except Exception as e:
                logger.error(f"Ошибка закрытия PoseManager: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику использования"""
        avg_time = (self.total_processing_time / self.frames_processed 
                   if self.frames_processed > 0 else 0)
        
        return {
            'frames_processed': self.frames_processed,
            'total_processing_time': self.total_processing_time,
            'avg_processing_time': avg_time,
            'created_at': self.created_at,
            'device_type': self.device_type,
            'is_initialized': self.is_initialized,
        }
    
    def reset_stats(self):
        """Сбрасывает статистику"""
        self.frames_processed = 0
        self.total_processing_time = 0
    
    @classmethod
    def create_for_device(cls, user_agent: str = "") -> 'PoseManager':
        """
        Создает оптимизированный PoseManager для устройства
        
        Args:
            user_agent: User-Agent строка для определения типа устройства
            
        Returns:
            Оптимизированный PoseManager
        """
        user_agent = user_agent.lower()
        
        if any(mobile in user_agent for mobile in ['mobile', 'android', 'iphone', 'ipad']):
            device_type = 'mobile'
        elif any(tablet in user_agent for tablet in ['tablet', 'ipad']):
            device_type = 'mobile'  # Используем mobile настройки для планшетов
        else:
            device_type = 'desktop'
        
        logger.info(f"Создание PoseManager для {device_type} (User-Agent: {user_agent[:50]})")
        
        return cls(device_type=device_type)


# 🔴 УДАЛЯЕМ старый singleton код!
# Больше нет глобальных переменных или singleton'ов
# Каждый запрос создает свой PoseManager

# Пример использования:
def example_usage():
    """Пример использования исправленного PoseManager"""
    import cv2
    
    # Способ 1: Использование как контекстный менеджер (рекомендуется)
    with PoseManager(device_type='desktop') as pose_manager:
        # Загружаем изображение
        image = cv2.imread('test.jpg')
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Обрабатываем
        results = pose_manager.process(image_rgb)
        
        if results.pose_landmarks:
            print(f"Обнаружено поз: {len(results.pose_landmarks.landmark)}")
        
        # Получаем статистику
        stats = pose_manager.get_stats()
        print(f"Статистика: {stats}")
    
    # Способ 2: Ручное управление
    pose_manager = PoseManager(device_type='mobile')
    try:
        image = cv2.imread('test.jpg')
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        results = pose_manager.process(image_rgb)
        
        if results and results.pose_landmarks:
            # Работаем с результатами
            pass
            
    finally:
        pose_manager.close()


# 🔴 УДАЛЯЕМ старый singleton класс!
# Если был класс типа PoseSingleton - удаляем его полностью

if __name__ == "__main__":
    # Тестируем работу
    print("✅ PoseManager готов к работе (без singleton!)")