const pushupsBtn = document.getElementById('pushups-btn');
const squatsBtn = document.getElementById('squats-btn');
const crunchesBtn = document.getElementById('crunches-btn');

const workoutContainer = document.getElementById('workout-container');
const videoElement = document.getElementById('video');
const canvasElement = document.getElementById('output');
const counterDisplay = document.getElementById('counter-display');
const canvasCtx = canvasElement.getContext('2d');

let counter = 0;
let stage = null;
let pose = null;
let camera = null;

pushupsBtn.addEventListener('click', () => {
    document.querySelector('.training-list').style.display = 'none';
    workoutContainer.classList.add('active');
    startPushups();
});

squatsBtn.addEventListener('click', () => {
    alert("Подсчёт приседаний скоро будет добавлен 💪");
});

crunchesBtn.addEventListener('click', () => {
    alert("Подсчёт скручиваний скоро будет добавлен 💪");
});

async function startPushups() {
    counter = 0;
    stage = null;
    counterDisplay.innerText = `Отжиманий: 0`;

    const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false
    });
    videoElement.srcObject = stream;

    pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
    });

    pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });

    pose.onResults(onResults);

    camera = new Camera(videoElement, {
        onFrame: async () => {
            await pose.send({ image: videoElement });
        },
        width: 640,
        height: 480
    });
    camera.start();
}

function onResults(results) {
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

    if (results.poseLandmarks) {
        const lmk = results.poseLandmarks;
        const shoulder = lmk[11];
        const elbow = lmk[13];
        const wrist = lmk[15];

        const angle = Math.abs(
            Math.atan2(wrist.y - elbow.y, wrist.x - elbow.x) -
            Math.atan2(shoulder.y - elbow.y, shoulder.x - elbow.x)
        ) * (180.0 / Math.PI);

        if (angle > 160) stage = "up";
        if (angle < 70 && stage === "up") {
            stage = "down";
            counter++;
            counterDisplay.innerText = `Отжиманий: ${counter}`;
        }

        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS,
            { color: '#00FF00', lineWidth: 4 });
        drawLandmarks(canvasCtx, results.poseLandmarks,
            { color: '#FF0000', lineWidth: 2 });
    }
    canvasCtx.restore();
}
