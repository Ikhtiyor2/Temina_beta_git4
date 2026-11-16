/**
 * TeminaFit: единый клиент MediaPipe Pose.
 * - getOrCreatePose() создаёт Pose один раз и переиспользует (мгновенный старт при повторном использовании в той же вкладке).
 * - Загружать после скриптов: pose.js, drawing_utils.js, camera_utils.js
 */
(function () {
  'use strict';

  var _pose = null;
  var _posePromise = null;

  function getOrCreatePose(options) {
    if (_pose) return Promise.resolve(_pose);
    if (_posePromise) return _posePromise;
    _posePromise = new Promise(function (resolve, reject) {
      try {
        if (typeof Pose === 'undefined') {
          reject(new Error('MediaPipe Pose не загружен'));
          return;
        }
        var pose = new Pose({
          locateFile: function (f) {
            return 'https://cdn.jsdelivr.net/npm/@mediapipe/pose/' + f;
          }
        });
        var opts = options || {};
        pose.setOptions({
          modelComplexity: opts.modelComplexity !== undefined ? opts.modelComplexity : 1,
          smoothLandmarks: opts.smoothLandmarks !== undefined ? opts.smoothLandmarks : true,
          minDetectionConfidence: opts.minDetectionConfidence !== undefined ? opts.minDetectionConfidence : 0.5,
          minTrackingConfidence: opts.minTrackingConfidence !== undefined ? opts.minTrackingConfidence : 0.5
        });
        _pose = pose;
        resolve(pose);
      } catch (e) {
        reject(e);
      }
    });
    return _posePromise;
  }

  window.TeminaPoseClient = {
    getOrCreatePose: getOrCreatePose
  };
})();
