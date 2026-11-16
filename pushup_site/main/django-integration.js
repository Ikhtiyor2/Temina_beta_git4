// js/django-integration-optimized.js - ВПОЛНЕ ОПТИМИЗИРОВАННАЯ ВЕРСИЯ

class OptimizedDjangoIntegration {
    constructor() {
        this.baseURL = window.location.origin;
        this.csrfToken = this.getCSRFToken();
        this.sessionId = this.generateSessionId();
        this.frameCounter = 0;
        this.lastProcessedFrame = 0;
        this.networkQuality = 'unknown';
        this.pingTimes = [];
        this.isLowBandwidthMode = false;
        
        // Адаптивные настройки
        this.settings = {
            quality: 70,
            frameRate: 20,
            width: 480,
            height: 360,
            sendEveryNFrame: 2,
            compression: true,
            batchSize: 1,
            adaptive: true
        };
        
        // Статистика
        this.stats = {
            framesSent: 0,
            framesProcessed: 0,
            totalBytesSent: 0,
            avgProcessingTime: 0,
            networkErrors: 0
        };
        
        // Кэш для повторных запросов
        this.frameCache = new Map();
        this.cacheLimit = 50;
        
        // Очередь для батч-обработки
        this.frameQueue = [];
        this.batchInterval = null;
        
        this.init();
    }

    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    getCSRFToken() {
        const cookie = document.cookie.match(/csrftoken=([^;]+)/);
        return cookie ? cookie[1] : '';
    }

    async init() {
        // Определяем устройство и получаем настройки
        await this.detectDeviceAndNetwork();
        await this.loadOptimalSettings();
        
        // Начинаем мониторинг сети
        this.startNetworkMonitoring();
        
        console.log('🚀 Оптимизированная система загружена:', {
            session: this.sessionId,
            settings: this.settings,
            device: this.deviceType
        });
    }

    async detectDeviceAndNetwork() {
        // Определение типа устройства
        const ua = navigator.userAgent.toLowerCase();
        if (/mobile|android|iphone|ipad/.test(ua)) {
            this.deviceType = 'mobile';
            this.settings.width = 320;
            this.settings.height = 240;
            this.settings.quality = 60;
        } else if (/tablet/.test(ua)) {
            this.deviceType = 'tablet';
            this.settings.width = 480;
            this.settings.height = 360;
            this.settings.quality = 70;
        } else {
            this.deviceType = 'desktop';
            this.settings.width = 640;
            this.settings.height = 480;
            this.settings.quality = 80;
        }

        // Проверка сети
        await this.checkNetworkQuality();
    }

    async checkNetworkQuality() {
        try {
            // Простой ping тест
            const start = performance.now();
            await fetch(`${this.baseURL}/api/status/`, { 
                method: 'HEAD',
                cache: 'no-cache'
            });
            const ping = performance.now() - start;
            
            this.pingTimes.push(ping);
            if (this.pingTimes.length > 10) this.pingTimes.shift();
            
            const avgPing = this.pingTimes.reduce((a, b) => a + b) / this.pingTimes.length;
            
            // Определяем качество сети
            if (avgPing > 500) {
                this.networkQuality = 'poor';
                this.isLowBandwidthMode = true;
            } else if (avgPing > 200) {
                this.networkQuality = 'medium';
                this.isLowBandwidthMode = false;
            } else {
                this.networkQuality = 'good';
                this.isLowBandwidthMode = false;
            }
            
            // Адаптируем настройки
            this.adaptToNetwork();
            
        } catch (error) {
            console.warn('Network check failed:', error);
            this.networkQuality = 'unknown';
        }
    }

    adaptToNetwork() {
        if (this.networkQuality === 'poor' || this.isLowBandwidthMode) {
            this.settings.quality = Math.max(40, this.settings.quality - 20);
            this.settings.sendEveryNFrame = 4;
            this.settings.frameRate = 10;
            this.settings.batchSize = 3;
        } else if (this.networkQuality === 'medium') {
            this.settings.quality = 60;
            this.settings.sendEveryNFrame = 3;
            this.settings.frameRate = 15;
            this.settings.batchSize = 2;
        } else {
            this.settings.quality = 80;
            this.settings.sendEveryNFrame = 2;
            this.settings.frameRate = 25;
            this.settings.batchSize = 1;
        }
    }

    async loadOptimalSettings() {
        try {
            const response = await fetch(`${this.baseURL}/api/camera/settings/`, {
                headers: { 'X-CSRFToken': this.csrfToken }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.recommendations) {
                    // Объединяем с нашими настройками
                    Object.assign(this.settings, data.recommendations);
                    console.log('📊 Загружены серверные настройки:', data.recommendations);
                }
            }
        } catch (error) {
            console.warn('Не удалось загрузить настройки с сервера:', error);
        }
    }

    startNetworkMonitoring() {
        // Периодическая проверка сети
        setInterval(() => {
            this.checkNetworkQuality().catch(() => {});
        }, 30000); // Каждые 30 секунд
        
        // Мониторинг онлайн/оффлайн
        window.addEventListener('online', () => {
            console.log('🌐 Сеть восстановлена');
            this.isLowBandwidthMode = false;
            this.adaptToNetwork();
        });
        
        window.addEventListener('offline', () => {
            console.warn('📵 Нет сети, переходим в оффлайн режим');
            this.isLowBandwidthMode = true;
            this.settings.sendEveryNFrame = 5;
            this.settings.quality = 30;
        });
    }

    // ОСНОВНОЙ МЕТОД ОБРАБОТКИ КАДРОВ
    async processVideoFrame(videoElement, exerciseType) {
        if (!videoElement || !videoElement.videoWidth) {
            return null;
        }

        this.frameCounter++;
        
        // ПРОПУСК КАДРОВ для экономии
        if (this.frameCounter % this.settings.sendEveryNFrame !== 0) {
            return null;
        }

        // ПОДГОТОВКА КАНВАСА ДЛЯ СЖАТИЯ
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        // Устанавливаем размеры для сжатия
        canvas.width = this.settings.width;
        canvas.height = Math.round(
            (videoElement.videoHeight / videoElement.videoWidth) * this.settings.width
        );
        
        // РИСУЕМ И СЖИМАЕМ
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        // КОМПРЕССИЯ JPEG с настройкой качества
        const compressedDataUrl = canvas.toDataURL('image/jpeg', this.settings.quality / 100);
        
        // ПРОВЕРКА КЭША (избегаем отправки одинаковых кадров)
        const frameHash = this.hashFrame(compressedDataUrl);
        if (this.frameCache.has(frameHash)) {
            const cached = this.frameCache.get(frameHash);
            this.frameCache.set(frameHash, { ...cached, lastUsed: Date.now() });
            return cached.result;
        }
        
        // ПОДГОТОВКА ДАННЫХ ДЛЯ ОТПРАВКИ
        const frameData = {
            frame: compressedDataUrl,
            exercise_type: exerciseType,
            frame_number: this.frameCounter,
            session_id: this.sessionId,
            client_settings: {
                quality: this.settings.quality,
                width: canvas.width,
                height: canvas.height,
                device_type: this.deviceType,
                network_quality: this.networkQuality
            },
            timestamp: Date.now()
        };
        
        // РАЗМЕР КАДРА (для статистики)
        const frameSize = compressedDataUrl.length;
        this.stats.totalBytesSent += frameSize;
        
        // ОТПРАВКА НА СЕРВЕР
        try {
            const startTime = performance.now();
            
            const response = await fetch(`${this.baseURL}/api/ai/process-optimized/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify(frameData),
                signal: AbortSignal.timeout(5000) // Таймаут 5 секунд
            });
            
            const processingTime = performance.now() - startTime;
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            // ОБНОВЛЯЕМ СТАТИСТИКУ
            this.stats.framesSent++;
            this.stats.framesProcessed++;
            this.stats.avgProcessingTime = 
                (this.stats.avgProcessingTime * (this.stats.framesProcessed - 1) + processingTime) 
                / this.stats.framesProcessed;
            
            // КЭШИРУЕМ РЕЗУЛЬТАТ
            if (result.success && !result.cached) {
                this.frameCache.set(frameHash, {
                    result: result,
                    lastUsed: Date.now(),
                    size: frameSize
                });
                
                // Очистка старых записей
                if (this.frameCache.size > this.cacheLimit) {
                    const oldest = Array.from(this.frameCache.entries())
                        .sort((a, b) => a[1].lastUsed - b[1].lastUsed)[0];
                    this.frameCache.delete(oldest[0]);
                }
            }
            
            // АДАПТАЦИЯ НА ОСНОВЕ РЕЗУЛЬТАТОВ
            if (result.processing_time_ms > 300) {
                // Сервер медленно обрабатывает - уменьшаем нагрузку
                this.settings.sendEveryNFrame = Math.min(5, this.settings.sendEveryNFrame + 1);
                this.settings.quality = Math.max(40, this.settings.quality - 10);
            }
            
            return result;
            
        } catch (error) {
            console.error('Ошибка обработки кадра:', error);
            this.stats.networkErrors++;
            
            // АВТОМАТИЧЕСКАЯ ДЕГРАДАЦИЯ ПРИ ОШИБКАХ
            if (this.stats.networkErrors > 3) {
                this.degradeQuality();
            }
            
            return {
                success: false,
                error: error.name === 'AbortError' ? 'timeout' : 'network',
                feedback: 'Сеть: проблемы с соединением',
                fallback: true
            };
        }
    }

    // БАТЧ-ОБРАБОТКА (для еще большей оптимизации)
    startBatchProcessing(videoElement, exerciseType) {
        if (this.batchInterval) {
            clearInterval(this.batchInterval);
        }
        
        this.batchInterval = setInterval(async () => {
            if (this.frameQueue.length >= this.settings.batchSize) {
                await this.processBatch(exerciseType);
            }
        }, 1000 / this.settings.frameRate);
        
        // Собираем кадры в очередь
        const frameInterval = setInterval(() => {
            if (!videoElement.videoWidth) return;
            
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            canvas.width = this.settings.width;
            canvas.height = Math.round(
                (videoElement.videoHeight / videoElement.videoWidth) * this.settings.width
            );
            
            ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
            const dataUrl = canvas.toDataURL('image/jpeg', this.settings.quality / 100);
            
            this.frameQueue.push({
                frame: dataUrl,
                timestamp: Date.now()
            });
            
            // Ограничиваем размер очереди
            if (this.frameQueue.length > 10) {
                this.frameQueue.shift();
            }
        }, 1000 / this.settings.frameRate);
        
        return () => {
            clearInterval(this.batchInterval);
            clearInterval(frameInterval);
            this.frameQueue = [];
        };
    }

    async processBatch(exerciseType) {
        if (this.frameQueue.length === 0) return;
        
        const frames = this.frameQueue.map((item, index) => ({
            frame: item.frame,
            frame_number: this.frameCounter + index
        }));
        
        this.frameCounter += frames.length;
        
        try {
            const response = await fetch(`${this.baseURL}/api/ai/process-batch/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    frames: frames,
                    exercise_type: exerciseType,
                    batch_size: frames.length,
                    session_id: this.sessionId
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Обрабатываем результаты батча
                this.frameQueue = []; // Очищаем очередь
                
                // Берем последний результат (самый актуальный)
                const lastResult = result.results[result.results.length - 1];
                return lastResult;
            }
            
        } catch (error) {
            console.error('Batch processing error:', error);
            this.frameQueue = []; // Очищаем при ошибке
        }
        
        return null;
    }

    degradeQuality() {
        console.warn('⚠️ Degrading quality due to network issues');
        
        this.settings.quality = Math.max(30, this.settings.quality - 20);
        this.settings.sendEveryNFrame = Math.min(6, this.settings.sendEveryNFrame + 1);
        this.settings.frameRate = Math.max(5, this.settings.frameRate - 5);
        this.settings.batchSize = Math.min(4, this.settings.batchSize + 1);
        
        // Уведомляем сервер о проблемах
        this.reportNetworkIssue();
    }

    async reportNetworkIssue() {
        try {
            await fetch(`${this.baseURL}/api/network/quality/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    quality: 'poor',
                    ping: this.pingTimes.slice(-1)[0] || 500,
                    session_id: this.sessionId
                })
            });
        } catch (error) {
            // Игнорируем ошибку отчета
        }
    }

    hashFrame(frameData) {
        // Быстрый хэш для сравнения кадров
        let hash = 0;
        const str = frameData.substring(0, 200); // Берем только начало
        for (let i = 0; i < str.length; i++) {
            hash = ((hash << 5) - hash) + str.charCodeAt(i);
            hash = hash & hash;
        }
        return hash.toString(36);
    }

    // ОПТИМИЗИРОВАННЫЙ HUD
    async getOptimizedHUD(exerciseType = 'PUSHUP') {
        try {
            const cacheKey = `hud_${exerciseType}_${Math.floor(Date.now() / 1000)}`; // Кэш на секунду
            
            if (sessionStorage.getItem(cacheKey)) {
                return JSON.parse(sessionStorage.getItem(cacheKey));
            }
            
            const response = await fetch(
                `${this.baseURL}/api/hud/optimized/?exercise=${exerciseType}&_=${Date.now()}`,
                {
                    headers: { 'X-CSRFToken': this.csrfToken },
                    signal: AbortSignal.timeout(2000)
                }
            );
            
            if (!response.ok) throw new Error('HUD request failed');
            
            const data = await response.json();
            
            // Кэшируем на 1 секунду
            sessionStorage.setItem(cacheKey, JSON.stringify(data));
            setTimeout(() => sessionStorage.removeItem(cacheKey), 1000);
            
            return data;
            
        } catch (error) {
            console.warn('HUD request failed, using fallback:', error);
            return {
                success: false,
                count: 0,
                quality: 92.0,
                errors: 0,
                fallback: true,
                cached: false
            };
        }
    }

    // СТАТИСТИКА И МОНИТОРИНГ
    getStats() {
        return {
            ...this.stats,
            settings: this.settings,
            networkQuality: this.networkQuality,
            deviceType: this.deviceType,
            cacheSize: this.frameCache.size,
            frameQueue: this.frameQueue.length,
            efficiency: this.stats.framesProcessed / Math.max(1, this.stats.framesSent)
        };
    }

    resetStats() {
        this.stats = {
            framesSent: 0,
            framesProcessed: 0,
            totalBytesSent: 0,
            avgProcessingTime: 0,
            networkErrors: 0
        };
        this.frameCache.clear();
    }

    // ОЧИСТКА РЕСУРСОВ
    cleanup() {
        if (this.batchInterval) {
            clearInterval(this.batchInterval);
            this.batchInterval = null;
        }
        this.frameCache.clear();
        this.frameQueue = [];
        
        // Уведомляем сервер о завершении сессии
        this.notifySessionEnd();
    }

    async notifySessionEnd() {
        try {
            await fetch(`${this.baseURL}/api/session/end/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    stats: this.getStats()
                })
            });
        } catch (error) {
            // Игнорируем ошибку
        }
    }
}

// КЛАСС ДЛЯ УПРАВЛЕНИЯ КАМЕРОЙ
class OptimizedCameraManager {
    constructor(videoElementId, options = {}) {
        this.video = document.getElementById(videoElementId);
        this.stream = null;
        this.isMirrored = true;
        this.constraints = {
            video: {
                width: { ideal: options.width || 640 },
                height: { ideal: options.height || 480 },
                facingMode: 'user',
                frameRate: { ideal: options.frameRate || 30 }
            },
            audio: false
        };
    }

    async start() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Камера не поддерживается');
            }
            
            this.stream = await navigator.mediaDevices.getUserMedia(this.constraints);
            
            if (this.video) {
                this.video.srcObject = this.stream;
                this.video.play();
                
                if (this.isMirrored) {
                    this.video.style.transform = 'scaleX(-1)';
                }
                
                console.log('📷 Камера запущена');
                return true;
            }
            
            return false;
            
        } catch (error) {
            console.error('❌ Ошибка камеры:', error);
            
            // Fallback: создаем тестовое видео для демо
            this.createTestVideo();
            return false;
        }
    }

    createTestVideo() {
        if (!this.video) return;
        
        // Создаем тестовый canvas с анимацией
        const canvas = document.createElement('canvas');
        canvas.width = 640;
        canvas.height = 480;
        const ctx = canvas.getContext('2d');
        
        let frame = 0;
        const drawTestFrame = () => {
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Рисуем тестовую анимацию
            ctx.fillStyle = '#8b5cf6';
            ctx.beginPath();
            ctx.arc(
                canvas.width / 2 + Math.sin(frame * 0.1) * 50,
                canvas.height / 2 + Math.cos(frame * 0.1) * 50,
                30, 0, Math.PI * 2
            );
            ctx.fill();
            
            ctx.fillStyle = '#ffffff';
            ctx.font = '20px Arial';
            ctx.textAlign = 'center';
            ctx.fillText('📷 Демо-режим', canvas.width / 2, 50);
            ctx.fillText('Камера недоступна', canvas.width / 2, 80);
            
            frame++;
            
            // Конвертируем в video stream
            const stream = canvas.captureStream(20);
            this.video.srcObject = stream;
            this.video.play();
            
            requestAnimationFrame(drawTestFrame);
        };
        
        drawTestFrame();
    }

    stop() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
    }

    getResolution() {
        if (this.video && this.video.videoWidth) {
            return {
                width: this.video.videoWidth,
                height: this.video.videoHeight,
                aspectRatio: this.video.videoWidth / this.video.videoHeight
            };
        }
        return null;
    }

    toggleMirror() {
        this.isMirrored = !this.isMirrored;
        if (this.video) {
            this.video.style.transform = this.isMirrored ? 'scaleX(-1)' : 'scaleX(1)';
        }
    }
}

// ГЛАВНЫЙ КЛАСС ДЛЯ ИНТЕГРАЦИИ
class OptimizedGameSystem {
    constructor() {
        this.integration = new OptimizedDjangoIntegration();
        this.camera = null;
        this.exerciseTracker = null;
        this.currentExercise = null;
        this.isTraining = false;
        this.processInterval = null;
        this.hudUpdateInterval = null;
        
        // UI элементы
        this.ui = {
            repCounter: document.getElementById('live-rep-counter'),
            feedback: document.getElementById('ai-feedback'),
            qualityIndicator: document.getElementById('quality-indicator'),
            statsPanel: document.getElementById('stats-panel'),
            networkStatus: document.getElementById('network-status')
        };
        
        this.init();
    }

    async init() {
        try {
            // Загружаем начальные данные
            await this.loadInitialData();
            
            // Настраиваем UI
            this.setupUI();
            
            // Стартуем периодические обновления
            this.startPeriodicUpdates();
            
            console.log('🎮 Оптимизированная игровая система готова');
            
        } catch (error) {
            console.error('Ошибка инициализации:', error);
            this.showNotification('Ошибка загрузки системы', 'error');
        }
    }

    async loadInitialData() {
        // Загружаем данные игрока, квесты и т.д.
        // Можно добавить параллельную загрузку
        const [playerData, questsData] = await Promise.allSettled([
            this.integration.getPlayerData(),
            this.integration.getQuests()
        ]);
        
        this.player = playerData.status === 'fulfilled' ? playerData.value : null;
        this.quests = questsData.status === 'fulfilled' ? questsData.value : [];
    }

    setupUI() {
        // Настраиваем UI элементы
        this.updateNetworkStatus();
        
        // Добавляем обработчики
        this.addEventListeners();
    }

    updateNetworkStatus() {
        if (this.ui.networkStatus) {
            const stats = this.integration.getStats();
            const quality = stats.networkQuality;
            
            let text = '🌐 Сеть: ';
            let color = '#4CAF50';
            
            if (quality === 'poor') {
                text += 'Плохо';
                color = '#F44336';
            } else if (quality === 'medium') {
                text += 'Нормально';
                color = '#FF9800';
            } else {
                text += 'Хорошо';
                color = '#4CAF50';
            }
            
            this.ui.networkStatus.textContent = text;
            this.ui.networkStatus.style.color = color;
        }
    }

    addEventListeners() {
        // Добавляем глобальные обработчики
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    // 🎬 ЗАПУСК ТРЕНИРОВКИ
    async startTraining(exerciseType) {
        if (this.isTraining) {
            this.showNotification('Тренировка уже идет!', 'warning');
            return;
        }
        
        try {
            this.currentExercise = exerciseType;
            this.isTraining = true;
            
            // 1. Инициализируем камеру
            this.camera = new OptimizedCameraManager('ai-video-feed', {
                width: this.integration.settings.width,
                height: this.integration.settings.height,
                frameRate: this.integration.settings.frameRate
            });
            
            const cameraStarted = await this.camera.start();
            
            if (!cameraStarted) {
                this.showNotification('⚠️ Используется демо-режим', 'warning');
            }
            
            // 2. Показываем интерфейс тренировки
            this.showTrainingUI();
            
            // 3. Запускаем обработку кадров
            this.startFrameProcessing();
            
            // 4. Запускаем обновление HUD
            this.startHUDUpdates();
            
            this.showNotification(`🚀 ${this.getExerciseName(exerciseType)} начаты!`, 'success');
            
        } catch (error) {
            console.error('Ошибка запуска тренировки:', error);
            this.showNotification('❌ Ошибка запуска', 'error');
            this.isTraining = false;
        }
    }

    getExerciseName(type) {
        const names = {
            'PUSHUP': 'Отжимания',
            'SQUAT': 'Приседания',
            'PULLUP': 'Подтягивания',
            'CRUNCH': 'Скручивания'
        };
        return names[type] || 'Тренировка';
    }

    showTrainingUI() {
        // Показываем блок тренировки
        const setupSection = document.getElementById('training-setup');
        const sessionSection = document.getElementById('current-session');
        
        if (setupSection) setupSection.style.display = 'none';
        if (sessionSection) sessionSection.style.display = 'block';
        
        // Обновляем название упражнения
        const title = document.getElementById('exercise-title');
        if (title && this.currentExercise) {
            title.textContent = this.getExerciseName(this.currentExercise);
        }
    }

    startFrameProcessing() {
        if (this.processInterval) {
            clearInterval(this.processInterval);
        }
        
        // Используем адаптивный интервал на основе FPS
        const interval = 1000 / this.integration.settings.frameRate;
        
        this.processInterval = setInterval(async () => {
            if (!this.isTraining || !this.camera || !this.camera.video) {
                return;
            }
            
            const result = await this.integration.processVideoFrame(
                this.camera.video,
                this.currentExercise
            );
            
            if (result) {
                this.handleAIResult(result);
            }
            
        }, interval);
    }

    handleAIResult(result) {
        if (!result.success) {
            // Обработка ошибок
            if (result.error === 'timeout') {
                this.showNotification('AI: Таймаут обработки', 'warning');
            }
            return;
        }
        
        // Обновляем счетчик
        if (this.ui.repCounter && result.count !== undefined) {
            this.ui.repCounter.textContent = result.count;
            
            // Анимация при изменении
            if (parseInt(this.ui.repCounter.textContent) < result.count) {
                this.ui.repCounter.classList.add('pulse');
                setTimeout(() => this.ui.repCounter.classList.remove('pulse'), 300);
            }
        }
        
        // Обновляем фидбэк: текст + при ошибках — какая ошибка и как исправить
        if (this.ui.feedback) {
            let text = result.feedback || '';
            if (result.errors && result.errors.length > 0) {
                const parts = result.errors.map(function(e) {
                    const msg = (typeof e === 'object' && e.message != null) ? e.message : String(e);
                    const hint = (typeof e === 'object' && e.hint != null) ? e.hint : '';
                    return '❌ ' + msg + (hint ? '\n💡 Как исправить: ' + hint : '');
                });
                text = text + '\n\n' + parts.join('\n\n');
            }
            this.ui.feedback.textContent = text;
            this.ui.feedback.style.whiteSpace = 'pre-line';
            if (result.errors && result.errors.length > 0) {
                this.ui.feedback.style.color = '#FF9800';
            } else if (result.pose_detected) {
                this.ui.feedback.style.color = '#4CAF50';
            } else {
                this.ui.feedback.style.color = '#2196F3';
            }
        }
        
        // Обновляем индикатор качества
        if (this.ui.qualityIndicator) {
            const quality = result.pose_quality || 'unknown';
            const colors = {
                'good': '#4CAF50',
                'needs_improvement': '#FF9800',
                'no_pose': '#9E9E9E',
                'unknown': '#2196F3'
            };
            this.ui.qualityIndicator.style.backgroundColor = colors[quality] || '#2196F3';
        }
        
        // Обновляем статистику
        if (result.processing_time_ms) {
            this.updateProcessingStats(result.processing_time_ms);
        }
    }

    updateProcessingStats(processingTime) {
        if (this.ui.statsPanel) {
            const stats = this.integration.getStats();
            this.ui.statsPanel.innerHTML = `
                <div>FPS: ${Math.round(1000 / processingTime)}</div>
                <div>Задержка: ${Math.round(processingTime)}ms</div>
                <div>Кадров: ${stats.framesProcessed}</div>
            `;
        }
    }

    startHUDUpdates() {
        if (this.hudUpdateInterval) {
            clearInterval(this.hudUpdateInterval);
        }
        
        // HUD обновляем реже, чем кадры (раз в 2 секунды)
        this.hudUpdateInterval = setInterval(async () => {
            if (!this.isTraining || !this.currentExercise) return;
            
            const hudData = await this.integration.getOptimizedHUD(this.currentExercise);
            if (hudData.success) {
                this.updateHUD(hudData);
            }
            
            // Обновляем статус сети
            this.updateNetworkStatus();
            
        }, 2000);
    }

    updateHUD(hudData) {
        // Обновляем различные элементы HUD
        // Можно добавить анимации и визуализацию
    }

    // 🏁 ЗАВЕРШЕНИЕ ТРЕНИРОВКИ
    async finishTraining() {
        if (!this.isTraining) return;
        
        try {
            this.isTraining = false;
            
            // Останавливаем все интервалы
            if (this.processInterval) {
                clearInterval(this.processInterval);
                this.processInterval = null;
            }
            
            if (this.hudUpdateInterval) {
                clearInterval(this.hudUpdateInterval);
                this.hudUpdateInterval = null;
            }
            
            // Останавливаем камеру
            if (this.camera) {
                this.camera.stop();
                this.camera = null;
            }
            
            // Скрываем UI тренировки
            this.hideTrainingUI();
            
            // Показываем результаты
            this.showResults();
            
            // Очищаем интеграцию
            this.integration.cleanup();
            
            this.showNotification('🏁 Тренировка завершена!', 'success');
            
        } catch (error) {
            console.error('Ошибка завершения:', error);
            this.showNotification('❌ Ошибка завершения', 'error');
        }
    }

    hideTrainingUI() {
        const setupSection = document.getElementById('training-setup');
        const sessionSection = document.getElementById('current-session');
        
        if (setupSection) setupSection.style.display = 'block';
        if (sessionSection) sessionSection.style.display = 'none';
    }

    async showResults() {
        // Показываем статистику тренировки
        const stats = this.integration.getStats();
        
        // Можно показать модальное окно с результатами
        console.log('Результаты тренировки:', stats);
    }

    // ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    showNotification(message, type = 'info') {
        console.log(`[${type}] ${message}`);
        
        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: ${type === 'success' ? '#4CAF50' : 
                        type === 'warning' ? '#FF9800' : 
                        type === 'error' ? '#F44336' : '#2196F3'};
            color: white;
            border-radius: 8px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
            max-width: 300px;
        `;
        
        document.body.appendChild(notification);
        
        // Автоматическое скрытие
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    startPeriodicUpdates() {
        // Периодически обновляем данные
        setInterval(() => {
            this.updateNetworkStatus();
        }, 10000);
    }

    cleanup() {
        if (this.isTraining) {
            this.finishTraining();
        }
        
        if (this.integration) {
            this.integration.cleanup();
        }
        
        // Очищаем интервалы
        if (this.processInterval) clearInterval(this.processInterval);
        if (this.hudUpdateInterval) clearInterval(this.hudUpdateInterval);
    }
}

// ГЛОБАЛЬНЫЙ ДОСТУП
let gameSystem = null;

document.addEventListener('DOMContentLoaded', () => {
    gameSystem = new OptimizedGameSystem();
    
    // Экспортируем функции для глобального доступа
    window.startOptimizedTraining = (type) => gameSystem.startTraining(type);
    window.endOptimizedTraining = () => gameSystem.finishTraining();
    window.getTrainingStats = () => gameSystem.integration.getStats();
    
    // Добавляем стили для анимаций
    const styles = document.createElement('style');
    styles.textContent = `
        .pulse {
            animation: pulse 0.3s ease;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        
        .camera-container {
            margin: 20px auto;
            max-width: 640px;
            position: relative;
        }
        
        .camera-wrapper {
            position: relative;
            width: 100%;
            height: 480px;
            border-radius: 12px;
            overflow: hidden;
            border: 2px solid #8b5cf6;
            background: #1a1a2e;
        }
        
        #ai-video-feed {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        
        .network-status {
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10;
        }
        
        .stats-panel {
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 11px;
            z-index: 10;
            display: grid;
            grid-template-columns: repeat(3, auto);
            gap: 5px;
        }
    `;
    document.head.appendChild(styles);
});