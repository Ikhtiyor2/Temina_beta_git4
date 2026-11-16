# test_mediapipe.py
import unittest

raise unittest.SkipTest("Manual MediaPipe smoke test; excluded from Django test discovery.")

import sys
import os

# Добавьте путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pushup_site.settings')

import django
django.setup()

print("=" * 50)
print("🔍 ТЕСТ MEDIAPIPE И POSE MANAGER")
print("=" * 50)

# Тест 1: Проверка импортов
try:
    import mediapipe as mp
    print(f"✅ MediaPipe импортирован, версия: {mp.__version__}")
except ImportError as e:
    print(f"❌ MediaPipe НЕ установлен: {e}")
    sys.exit(1)

# Тест 2: Проверка OpenCV
try:
    import cv2
    print(f"✅ OpenCV импортирован, версия: {cv2.__version__}")
except ImportError as e:
    print(f"❌ OpenCV НЕ установлен: {e}")

# Тест 3: Проверка PoseManager
try:
    from main.pose_manager import PoseManager
    print("✅ PoseManager импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта PoseManager: {e}")
    sys.exit(1)

# Тест 4: Создаем тестовое изображение
import numpy as np
print("\n🔧 Создаю тестовое изображение...")
test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

# Тест 5: Запускаем PoseManager
print("🤖 Тестирую PoseManager...")
try:
    with PoseManager(device_type='desktop') as pose_manager:
        print("✅ PoseManager создан успешно")
        
        # Конвертируем в RGB (нужно для MediaPipe)
        import cv2
        image_rgb = cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB)
        
        # Обрабатываем изображение
        import time
        start_time = time.time()
        results = pose_manager.process(image_rgb)
        processing_time = (time.time() - start_time) * 1000
        
        if results:
            if results.pose_landmarks:
                landmarks_count = len(results.pose_landmarks.landmark)
                print(f"✅ Pose обнаружен! Landmarks: {landmarks_count}")
                print(f"⏱ Время обработки: {processing_time:.1f}мс")
            else:
                print("⚠️ Pose НЕ обнаружен (ожидаемо для случайного изображения)")
        else:
            print("❌ Нет результатов от PoseManager")
            
    print("✅ PoseManager закрыт корректно")
    
except Exception as e:
    print(f"❌ Ошибка при тесте PoseManager: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("📊 ИТОГ ТЕСТА MEDIAPIPE:")
print("=" * 50)

# Заключительная проверка
try:
    # Прямой тест MediaPipe
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    # Тест на черном изображении
    black_image = np.zeros((480, 640, 3), dtype=np.uint8)
    black_image_rgb = cv2.cvtColor(black_image, cv2.COLOR_BGR2RGB)
    results = pose.process(black_image_rgb)
    
    if results.pose_landmarks:
        print("❌ Странно: на черном изображении обнаружен pose")
    else:
        print("✅ Ожидаемо: на черном изображении pose не обнаружен")
    
    pose.close()
    print("✅ MediaPipe Pose работает корректно")
    
except Exception as e:
    print(f"❌ Ошибка в прямом тесте MediaPipe: {e}")

print("\n✅ ТЕСТ ЗАВЕРШЕН!")