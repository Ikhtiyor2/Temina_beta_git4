/**
 * TeminaFit: единый запуск камеры + MediaPipe Pose.
 * — Параллельно: getUserMedia и загрузка/прогрев Pose (WASM).
 * — Превью зеркального видео на canvas, пока ИИ не готов.
 * — Лёгкая модель на узких экранах; ограничение разрешения камеры.
 * Зависимости: pose.js, camera_utils.js, опционально mediapipe-client.js
 */
(function (global) {
  'use strict';

  var RETRY_WRAP_ID = 'temina-cp-retry-wrap';

  function isCoarseMobile() {
    return typeof global.matchMedia === 'function' && global.matchMedia('(max-width: 768px)').matches;
  }

  function defaultStringsRu() {
    return {
      starting: 'Запуск камеры и ИИ… Первый раз может занять до 30 сек.',
      cameraPrompt: 'Разрешите доступ к камере, если браузер спросит.',
      cameraReady: 'Камера включена. Загружаем нейросеть…',
      ready: 'Готово',
      timeout: 'Слишком долго. Проверьте интернет или Wi‑Fi и нажмите «Повторить».',
      permissionDenied: 'Камера недоступна: разрешите доступ в настройках браузера.',
      noCamera: 'Камера не найдена.',
      notSupported: 'Браузер не поддерживает доступ к камере.',
      notLoaded: 'Скрипты ИИ не загрузились. Обновите страницу.',
      genericError: 'Не удалось запустить камеру или ИИ.',
      retryLabel: 'Повторить',
      overlayLoadTitle: 'Загрузка ИИ',
      overlayAiTitle: 'Загружаем нейросеть…',
      overlayErrorTitle: 'Не удалось запустить'
    };
  }

  function syncLoadingOverlay(overlayEl, phase, detail, S) {
    if (!overlayEl) return;
    var titleEl = overlayEl.querySelector('.temina-cp-overlay-title');
    var subEl = overlayEl.querySelector('.temina-cp-overlay-sub');
    var spinWrap = overlayEl.querySelector('.temina-cp-spinner-wrap');

    function hide() {
      overlayEl.classList.remove('temina-cp-overlay--visible', 'temina-cp-overlay--error');
      overlayEl.setAttribute('aria-hidden', 'true');
    }

    function show(title, sub, isError) {
      overlayEl.classList.add('temina-cp-overlay--visible');
      overlayEl.classList.toggle('temina-cp-overlay--error', !!isError);
      overlayEl.setAttribute('aria-hidden', 'false');
      if (titleEl) titleEl.textContent = title || '';
      if (subEl) subEl.textContent = sub || '';
      if (spinWrap) spinWrap.style.display = isError ? 'none' : '';
    }

    if (phase === 'running') {
      hide();
      return;
    }
    if (phase === 'error') {
      var errSub = (detail && detail.message) || '';
      show(S('overlayErrorTitle'), errSub, true);
      return;
    }
    var title = phase === 'camera_live' ? S('overlayAiTitle') : S('overlayLoadTitle');
    var sub = (detail && detail.message) || '';
    show(title, sub, false);
  }

  function videoConstraints() {
    return {
      video: {
        facingMode: 'user',
        width: { max: 640 },
        height: { max: 480 }
      }
    };
  }

  function removeRetryBar() {
    var el = document.getElementById(RETRY_WRAP_ID);
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function showRetryBar(container, label, onRetry) {
    if (!container || typeof onRetry !== 'function') return;
    removeRetryBar();
    var wrap = document.createElement('div');
    wrap.id = RETRY_WRAP_ID;
    wrap.setAttribute('role', 'region');
    wrap.setAttribute('aria-label', 'Camera retry');
    wrap.style.cssText = 'margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = label;
    btn.style.cssText =
      'padding:10px 18px;border-radius:10px;border:1px solid rgba(168,85,247,0.55);' +
      'background:rgba(168,85,247,0.22);color:#f1f5f9;font-weight:600;cursor:pointer;font-size:0.95rem;';
    btn.addEventListener('click', onRetry);
    wrap.appendChild(btn);
    container.appendChild(wrap);
  }

  function createPosePromise(poseOptions) {
    function warmupPose(pose) {
      var w = document.createElement('canvas');
      w.width = 64;
      w.height = 64;
      w.getContext('2d').fillRect(0, 0, 64, 64);
      return pose.send({ image: w }).then(
        function () {
          return pose;
        },
        function () {
          return pose;
        }
      );
    }

    if (global.TeminaPoseClient && typeof global.TeminaPoseClient.getOrCreatePose === 'function') {
      return global.TeminaPoseClient.getOrCreatePose(poseOptions).then(warmupPose);
    }
    if (typeof global.Pose === 'undefined') {
      return Promise.reject({ code: 'NOT_LOADED', message: 'notLoaded' });
    }
    var p = new global.Pose({
      locateFile: function (f) {
        return 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/' + f;
      }
    });
    p.setOptions(poseOptions);
    return warmupPose(p);
  }

  /**
   * @param {object} opts
   * @param {HTMLVideoElement} opts.video
   * @param {HTMLCanvasElement} opts.canvas
   * @param {function} opts.onResults — MediaPipe onResults callback
   * @param {object} [opts.poseOptions] — опции Pose (modelComplexity и т.д.)
   * @param {number} [opts.modelComplexity] — если задано, перекрывает авто mobile/desktop
   * @param {number} [opts.loadTimeoutMs=50000]
   * @param {object} [opts.strings] — подписи (ключи как в defaultStringsRu; значения готовые строки)
   * @param {function} [opts.onStatus(phase, detail)] — phase: starting | camera_opening | camera_live | running | error
   * @param {function} [opts.onReady({ pose, mpCamera, aiLoadMs })]
   * @param {function} [opts.onError({ code, message, original })]
   * @param {HTMLElement} [opts.retryAnchor] — куда вставить кнопку «Повторить»
   * @param {function} [opts.onRetryRequest] — вызывается по клику; если нет — location.reload()
   * @param {HTMLElement} [opts.loadingOverlay] — блок .temina-cp-overlay на области камеры (спиннер + текст)
   */
  function launch(opts) {
    if (!opts || !opts.video || !opts.canvas || typeof opts.onResults !== 'function') {
      throw new Error('TeminaCameraPose.launch: video, canvas, onResults required');
    }

    var video = opts.video;
    var canvas = opts.canvas;
    var onResults = opts.onResults;
    var baseStrings = defaultStringsRu();
    var strings = Object.assign({}, baseStrings, opts.strings || {});

    function S(key) {
      return strings[key] || baseStrings[key] || key;
    }

    var poseOpt = {
      modelComplexity: typeof opts.modelComplexity === 'number' ? opts.modelComplexity : isCoarseMobile() ? 0 : 1,
      smoothLandmarks: true,
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5
    };
    if (opts.poseOptions && typeof opts.poseOptions === 'object') {
      Object.assign(poseOpt, opts.poseOptions);
    }

    var loadTimeoutMs = typeof opts.loadTimeoutMs === 'number' ? opts.loadTimeoutMs : 50000;
    var onStatus = typeof opts.onStatus === 'function' ? opts.onStatus : function () {};
    var onReady = typeof opts.onReady === 'function' ? opts.onReady : function () {};
    var onErrorCb = typeof opts.onError === 'function' ? opts.onError : function () {};
    var loadingOverlayEl = opts.loadingOverlay || null;

    function emit(phase, detail) {
      onStatus(phase, detail);
      syncLoadingOverlay(loadingOverlayEl, phase, detail, S);
    }

    var ctx = canvas.getContext('2d');
    var poseReadyFlag = false;
    var rafId = null;
    var inferenceRafId = null;
    var mediaStream = null;
    var mpCamera = null;
    var poseInstance = null;
    var cancelled = false;
    var timeoutId = null;

    function stopPreview() {
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
    }

    function drawVideoOnly() {
      if (poseReadyFlag || cancelled) return;
      if (canvas.width && canvas.height && video.readyState >= 2) {
        ctx.save();
        ctx.scale(-1, 1);
        ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
        ctx.restore();
      }
      rafId = requestAnimationFrame(drawVideoOnly);
    }

    function cleanupFailed() {
      cancelled = true;
      poseReadyFlag = true;
      stopPreview();
      if (inferenceRafId) { cancelAnimationFrame(inferenceRafId); inferenceRafId = null; }
      if (mediaStream) {
        mediaStream.getTracks().forEach(function (t) {
          t.stop();
        });
        mediaStream = null;
      }
      try {
        video.srcObject = null;
      } catch (e) {}
      if (mpCamera && typeof mpCamera.stop === 'function') {
        try {
          mpCamera.stop();
        } catch (e2) {}
      }
      mpCamera = null;
    }

    function handleError(info) {
      cleanupFailed();
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      var code = info.code || 'UNKNOWN';
      var msgKey = info.message;
      var msg =
        typeof msgKey === 'string' && msgKey in strings
          ? S(msgKey)
          : typeof msgKey === 'string'
            ? msgKey
            : S('genericError');
      emit('error', { code: code, message: msg });
      onErrorCb({ code: code, message: msg, original: info.original });

      var anchor = opts.retryAnchor;
      var retryCodes = { TIMEOUT: 1, NOT_LOADED: 1, UNKNOWN: 1, PERMISSION: 1, POSE_ERROR: 1 };
      if (anchor && retryCodes[code]) {
        showRetryBar(anchor, S('retryLabel'), function () {
          removeRetryBar();
          if (typeof opts.onRetryRequest === 'function') opts.onRetryRequest();
          else global.location.reload();
        });
      }
    }

    var existingStream = opts.stream || null;
    if (!existingStream && (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia)) {
      handleError({ code: 'NOT_SUPPORTED', message: 'notSupported' });
      return { cancel: function () {}, getMpCamera: function () { return null } };
    }

    emit('starting', { message: S('starting') });
    emit('camera_opening', { message: S('cameraPrompt') });

    var aiLoadStartMs = performance.now();

    function afterStream(stream) {
      if (cancelled) {
        stream.getTracks().forEach(function (t) {
          t.stop();
        });
        return Promise.reject({ code: 'CANCELLED', message: 'genericError' });
      }
      mediaStream = stream;
      video.setAttribute('playsinline', 'true');
      video.setAttribute('webkit-playsinline', 'true');
      video.muted = true;
      video.srcObject = stream;
      return video.play();
    }

    function afterPlay() {
      return new Promise(function (resolve) {
        if (video.videoWidth > 0) resolve();
        else
          video.addEventListener(
            'loadedmetadata',
            function () {
              resolve();
            },
            { once: true }
          );
      });
    }

    function afterMeta() {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      drawVideoOnly();
      emit('camera_live', {
        width: canvas.width,
        height: canvas.height,
        message: S('cameraReady')
      });
    }

    var streamPromise;
    if (existingStream) {
      streamPromise = Promise.resolve()
        .then(function () {
          return afterStream(existingStream);
        })
        .then(afterPlay)
        .then(afterMeta);
    } else {
      streamPromise = navigator.mediaDevices
        .getUserMedia(videoConstraints())
        .catch(function (e) {
          var code = 'UNKNOWN';
          var msg = 'genericError';
          if (e && (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError')) {
            code = 'PERMISSION';
            msg = 'permissionDenied';
          } else if (e && e.name === 'NotFoundError') {
            msg = 'noCamera';
          }
          return Promise.reject({ code: code, message: msg, original: e });
        })
        .then(afterStream)
        .then(afterPlay)
        .then(afterMeta);
    }

    var posePromise = createPosePromise(poseOpt).catch(function (e) {
      if (e && e.code === 'NOT_LOADED') {
        return Promise.reject({ code: 'NOT_LOADED', message: 'notLoaded', original: e });
      }
      return Promise.reject({ code: 'POSE_ERROR', message: 'genericError', original: e });
    });

    var readyPromise = Promise.all([streamPromise, posePromise]).then(function (results) {
      if (cancelled) return Promise.reject({ code: 'ABORT', message: 'genericError' });
      poseInstance = results[1];
      poseReadyFlag = true;
      stopPreview();
      removeRetryBar();

      poseInstance.onResults(onResults);
      if (!existingStream && typeof global.Camera === 'undefined') {
        return Promise.reject({ code: 'NOT_LOADED', message: 'notLoaded' });
      }
      if (existingStream) {
        // Reuse the stream granted by the Mini App tap. Camera.start() would
        // request a second camera stream and can fail on mobile WebViews.
        var lastVideoTime = -1;
        function inferFrame() {
          if (cancelled) return;
          if (video.readyState < 2 || video.currentTime === lastVideoTime) {
            inferenceRafId = requestAnimationFrame(inferFrame);
            return;
          }
          lastVideoTime = video.currentTime;
          Promise.resolve().then(function () {
            if (!cancelled) return poseInstance.send({ image: video });
          }).then(function () {
            if (!cancelled) inferenceRafId = requestAnimationFrame(inferFrame);
          }, function (error) {
            if (!cancelled) handleError({ code: 'POSE_ERROR', message: 'genericError', original: error });
          });
        }
        inferenceRafId = requestAnimationFrame(inferFrame);
      } else {
        mpCamera = new global.Camera(video, {
          onFrame: function () {
            return poseInstance.send({ image: video });
          },
          width: canvas.width,
          height: canvas.height
        });
        return Promise.resolve(mpCamera.start()).then(markRunning);
      }

      return markRunning();
      function markRunning() {
        if (cancelled) return Promise.reject({ code: 'ABORT', message: 'genericError' });
        var aiLoadMs = Math.round(performance.now() - aiLoadStartMs);
        emit('running', { aiLoadMs: aiLoadMs, message: S('ready') });
        var payload = { pose: poseInstance, mpCamera: mpCamera, aiLoadMs: aiLoadMs };
        onReady(payload);
        return payload;
      }
    });

    timeoutId = setTimeout(function () {
      handleError({ code: 'TIMEOUT', message: 'timeout' });
    }, loadTimeoutMs);

    readyPromise.then(
      function () {
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
      },
      function (err) {
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        if (err && err.code === 'ABORT') return;
        if (cancelled) return;
        handleError(
          err && err.code
            ? err
            : { code: 'UNKNOWN', message: 'genericError', original: err }
        );
      }
    );

    return {
      cancel: function () {
        if (timeoutId) {
          clearTimeout(timeoutId);
          timeoutId = null;
        }
        cleanupFailed();
        removeRetryBar();
        syncLoadingOverlay(loadingOverlayEl, 'running', {}, S);
      },
      getMpCamera: function () {
        return mpCamera;
      }
    };
  }

  global.TeminaCameraPose = {
    launch: launch,
    isCoarseMobile: isCoarseMobile,
    removeRetryBar: removeRetryBar,
    showRetryBar: showRetryBar
  };
})(typeof window !== 'undefined' ? window : this);
