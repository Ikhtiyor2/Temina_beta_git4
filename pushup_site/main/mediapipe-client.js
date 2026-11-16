// static/js/mediapipe-client.js

class MediaPipePoseDetector {
    constructor(videoElementId, canvasElementId, onResultsCallback) {
        this.videoElement = document.getElementById(videoElementId);
        this.canvasElement = document.getElementById(canvasElementId);
        this.onResultsCallback = onResultsCallback;
        this.pose = null;
        this.camera = null;
        this.isRunning = false;
    }

    async initialize() {
        console.log('🔄 Инициализация MediaPipe Pose...');
        
        // Создаем экземпляр Pose
        this.pose = new Pose({
            locateFile: (file) => {
                console.log(`Загрузка MediaPipe файла: ${file}`);
                return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
            }
        });

        // Настройки
        this.pose.setOptions({
            modelComplexity: 1,  // 0=легкий, 1=полный, 2=тяжелый
            smoothLandmarks: true,
            enableSegmentation: false,
            smoothSegmentation: false,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });

        // Обработка результатов
        this.pose.onResults((results) => {
            if (this.onResultsCallback) {
                this.onResultsCallback(results);
            }
            
            // Отрисовка на canvas
            this.drawResults(results);
        });

        // Настройка камеры
        this.camera = new Camera(this.videoElement, {
            onFrame: async () => {
                if (this.isRunning && this.pose) {
                    await this.pose.send({image: this.videoElement});
                }
            },
            width: 640,
            height: 480
        });

        console.log('✅ MediaPipe инициализирован');
    }

    async start() {
        console.log('🎥 Запуск камеры...');
        
        if (!this.pose) {
            await this.initialize();
        }
        
        this.isRunning = true;
        await this.camera.start();
        console.log('✅ Камера запущена');
    }

    stop() {
        console.log('🛑 Остановка камеры...');
        this.isRunning = false;
        if (this.camera) {
            this.camera.stop();
        }
        console.log('✅ Камера остановлена');
    }

    drawResults(results) {
        if (!this.canvasElement || !results) return;
        
        const canvasCtx = this.canvasElement.getContext('2d');
        const canvasWidth = this.canvasElement.width;
        const canvasHeight = this.canvasElement.height;
        
        // Очистка canvas
        canvasCtx.save();
        canvasCtx.clearRect(0, 0, canvasWidth, canvasHeight);
        
        // Отрисовка позы если есть
        if (results.poseLandmarks) {
            this.drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {
                color: '#00FF00',
                lineWidth: 2
            });
            this.drawLandmarks(canvasCtx, results.poseLandmarks, {
                color: '#FF0000',
                lineWidth: 1,
                radius: 3
            });
        }
        
        canvasCtx.restore();
    }

    drawLandmarks(ctx, landmarks, style) {
        ctx.fillStyle = style.color;
        ctx.strokeStyle = style.color;
        ctx.lineWidth = style.lineWidth || 1;
        
        for (const landmark of landmarks) {
            const x = landmark.x * ctx.canvas.width;
            const y = landmark.y * ctx.canvas.height;
            
            ctx.beginPath();
            ctx.arc(x, y, style.radius || 3, 0, 2 * Math.PI);
            ctx.fill();
        }
    }

    drawConnectors(ctx, landmarks, connections, style) {
        ctx.strokeStyle = style.color;
        ctx.lineWidth = style.lineWidth || 2;
        
        for (const [start, end] of connections) {
            const startPoint = landmarks[start];
            const endPoint = landmarks[end];
            
            if (startPoint && endPoint) {
                const startX = startPoint.x * ctx.canvas.width;
                const startY = startPoint.y * ctx.canvas.height;
                const endX = endPoint.x * ctx.canvas.width;
                const endY = endPoint.y * ctx.canvas.height;
                
                ctx.beginPath();
                ctx.moveTo(startX, startY);
                ctx.lineTo(endX, endY);
                ctx.stroke();
            }
        }
    }
}

// MediaPipe соединения для позы
const POSE_CONNECTIONS = [
    [0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8], [9, 10],
    [11, 12], [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
    [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20], [11, 23],
    [12, 24], [23, 24], [23, 25], [24, 26], [25, 27], [26, 28], [27, 29],
    [28, 30], [29, 31], [30, 32], [27, 31], [28, 32]
];