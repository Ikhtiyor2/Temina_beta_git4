/**
 * TeminaFit: клиентский ИИ-счётчик (форма + античит) с /training/.
 * TeminaExerciseDetector.create(exerciseType, lang) → { process, getCount, reset, getIntegrity }
 */
(function (global) {
  "use strict";

  function create(exerciseType, lang) {
    var TRAIN_EN = lang === "en";
    var EX = String(exerciseType || "PUSHUP").toUpperCase();
    var startedAt = Date.now();
    var audit = { frames: 0, poseFrames: 0, critical: 0 };

    function err(message, hint) {
      return { message: message, hint: hint };
    }
    function e(mRu, hRu, mEn, hEn) {
      return err(TRAIN_EN ? mEn : mRu, TRAIN_EN ? hEn : hRu);
    }
    function fb(ru, en) {
      return TRAIN_EN ? en : ru;
    }

    function angle(a, b, c) {
      var ba = [a.x - b.x, a.y - b.y];
      var bc = [c.x - b.x, c.y - b.y];
      var dot = ba[0] * bc[0] + ba[1] * bc[1];
      var magBa = Math.sqrt(ba[0] * ba[0] + ba[1] * ba[1]);
      var magBc = Math.sqrt(bc[0] * bc[0] + bc[1] * bc[1]);
      if (magBa === 0 || magBc === 0) return 0;
      var cos = Math.max(-1, Math.min(1, dot / (magBa * magBc)));
      return (Math.acos(cos) * 180) / Math.PI;
    }

    var state = {
      count: 0,
      stage: "up",
      ready: false,
      readyBuffer: [],
      downHoldFrames: 0,
      handsOnGround: true,
      topPositionPose: false,
      minKneeAngleInRep: 180,
      goodHoldFrames: 0,
      lastCenter: null,
      stableRef: [],
      holdStartTime: null,
      startHipY: null,
      handsOffFrames: 0,
      crunchDownFrames: 0,
      pushupRef: null,
    };
    var READY_BUF_LEN = 15;
    var SQUAT_MIN_DOWN_FRAMES = 5;
    var HANDS_OFF_GRACE = 10;
    // Tolerant push-up profile; stationary support and torso motion remain mandatory.
    var PUSHUP_TOP_ANGLE = 140;
    var PUSHUP_DOWN_ANGLE = 105;
    var PUSHUP_SHOULDER_TRAVEL = 0.09;
    var PUSHUP_HIP_TRAVEL = 0.035;

    function pushupReference(ls, rs, lh, rh, lw, rw, scale) {
      var shoulder = { x: (ls.x + rs.x) / 2, y: (ls.y + rs.y) / 2 };
      var dx = (lw.x + rw.x) / 2 - shoulder.x;
      var dy = (lw.y + rw.y) / 2 - shoulder.y;
      var length = Math.hypot(dx, dy) || 1;
      return {
        shoulder: shoulder, hip: { x: (lh.x + rh.x) / 2, y: (lh.y + rh.y) / 2 },
        leftWrist: { x: lw.x, y: lw.y }, rightWrist: { x: rw.x, y: rw.y },
        axis: { x: dx / length, y: dy / length }, scale: Math.max(0.1, scale),
        shoulderTravel: 0, hipTravel: 0, movingFrames: 0, invalid: false,
      };
    }

    function pushup(lm) {
      var ls = lm[11],
        le = lm[13],
        lw = lm[15],
        rs = lm[12],
        re = lm[14],
        rw = lm[16];
      var lh = lm[23],
        rh = lm[24],
        lk = lm[25],
        rk = lm[26];
      // Uncertain landmarks must neither count a movement nor create a form violation.
      if ([ls, le, lw, rs, re, rw, lh, rh, lk, rk].some(function (point) {
        return !point || !Number.isFinite(point.x) || !Number.isFinite(point.y) ||
          (typeof point.visibility === "number" && point.visibility < 0.35);
      })) return { feedback: fb("Покажите руки и корпус в кадре", "Keep arms and torso in frame"), errors: [] };
      var elbowAngle = (angle(ls, le, lw) + angle(rs, re, rw)) / 2;
      var backAngle = (angle(ls, lh, lk) + angle(rs, rh, rk)) / 2;
      var hipAngle = (angle(lk, lh, ls) + angle(rk, rh, rs)) / 2;
      var shoulderWidth = Math.abs(ls.x - rs.x);
      var torsoLen = Math.hypot(ls.x - lh.x, ls.y - lh.y);
      var shoulderHipY = Math.abs(ls.y - lh.y);
      var wristsAvgY = (lw.y + rw.y) / 2;
      // Image height cannot locate the floor: camera tilt and distance move the
      // entire pose. Compare wrists with shoulders instead, including at the
      // bottom of a rep, with a small allowance for landmark jitter.
      var shouldersAvgY = (ls.y + rs.y) / 2;
      var wristTolerance = Math.max(0.025, Math.min(0.06, torsoLen * 0.15));
      var handsNearFloor =
        lw.y >= ls.y - wristTolerance && rw.y >= rs.y - wristTolerance &&
        wristsAvgY >= shouldersAvgY - wristTolerance * 0.5;
      if (!handsNearFloor) {
        state.handsOffFrames++;
        if (state.handsOffFrames >= HANDS_OFF_GRACE) {
          state.handsOnGround = false;
          state.stage = "up";
          state.downHoldFrames = 0;
          state.pushupRef = null;
          return {
            feedback: fb("Поставьте руки на пол!", "Put your hands on the floor!"),
            errors: [
              e(
                "Руки не на полу.",
                "Опустите ладони на пол на ширине плеч, кисти строго под плечами. Убедитесь, что руки целиком в кадре.",
                "Hands not on the floor.",
                "Place palms on the floor shoulder-width apart, wrists under shoulders. Keep your whole arms in frame."
              ),
            ],
          };
        }
        // Ignore uncertain wrist frames instead of treating their changing
        // elbow angles as a downward movement and counting a false rep.
        return { feedback: fb("Проверяю положение кистей...", "Checking hand position..."), errors: [] };
      } else {
        state.handsOffFrames = 0;
        state.handsOnGround = true;
      }
      var topForm = hipAngle > 130 && backAngle > 135 && shoulderWidth > 0.035 &&
        torsoLen > 0.08 && shoulderHipY < Math.max(0.08, torsoLen * 0.9);
      var startPose = elbowAngle > PUSHUP_TOP_ANGLE && topForm;
      state.readyBuffer.push(startPose);
      if (state.readyBuffer.length > READY_BUF_LEN) state.readyBuffer.shift();
      if (elbowAngle > PUSHUP_TOP_ANGLE) state.topPositionPose = topForm;
      if (!state.ready) {
        if (startPose && state.readyBuffer.filter(Boolean).length >= 8) {
          state.ready = true;
          state.pushupRef = pushupReference(ls, rs, lh, rh, lw, rw, torsoLen);
          return { feedback: fb("Готово. Начинайте отжимания!", "Ready. Start push-ups!"), errors: [] };
        }
        return { feedback: fb("Примите упор лёжа...", "Get into plank position..."), errors: [] };
      }
      if (!state.handsOnGround) {
        return {
          feedback: fb("Руки подняты! Стоп.", "Hands up! Stop."),
          errors: [
            e(
              "Руки оторваны от пола.",
              "Держите ладони плотно на полу на протяжении всего движения. Отрывание рук не засчитывается.",
              "Hands off the floor.",
              "Keep palms firmly on the floor throughout the movement. Lifting hands does not count."
            ),
          ],
        };
      }
      if (!state.pushupRef && elbowAngle <= PUSHUP_TOP_ANGLE) {
        return { feedback: fb("Вернитесь в верхнюю точку", "Return to the top position"), errors: [] };
      }
      if (!state.pushupRef || (state.stage === "up" && elbowAngle > PUSHUP_TOP_ANGLE)) {
        state.pushupRef = pushupReference(ls, rs, lh, rh, lw, rw, torsoLen);
      }
      var ref = state.pushupRef;
      var wristMovement = Math.max(
        Math.hypot(lw.x - ref.leftWrist.x, lw.y - ref.leftWrist.y),
        Math.hypot(rw.x - ref.rightWrist.x, rw.y - ref.rightWrist.y)
      );
      if (wristMovement > Math.max(0.022, ref.scale * 0.35)) {
        ref.movingFrames++;
        if (ref.movingFrames >= 4) ref.invalid = true;
        // Do not turn a jumping wrist landmark into a false elbow movement.
        return {
          feedback: fb("Оставьте ладони на месте, опускайте корпус", "Keep palms in place and lower your torso"),
          errors: ref.invalid ? [e(
            "Опора смещается.", "Ладони остаются на месте, плечи и корпус опускаются и поднимаются.",
            "Hand support is moving.", "Keep palms in place while shoulders and torso move down and up."
          )] : [],
        };
      }
      ref.movingFrames = 0;
      var shoulderTravel = ((ls.x + rs.x) / 2 - ref.shoulder.x) * ref.axis.x +
        ((ls.y + rs.y) / 2 - ref.shoulder.y) * ref.axis.y;
      var hipTravel = ((lh.x + rh.x) / 2 - ref.hip.x) * ref.axis.x +
        ((lh.y + rh.y) / 2 - ref.hip.y) * ref.axis.y;
      // Both displacements must occur together with bent elbows and stable wrists.
      if (elbowAngle < 115 && shoulderTravel > ref.scale * PUSHUP_SHOULDER_TRAVEL && hipTravel > ref.scale * PUSHUP_HIP_TRAVEL) {
        ref.shoulderTravel = Math.max(ref.shoulderTravel, shoulderTravel);
        ref.hipTravel = Math.max(ref.hipTravel, hipTravel);
      }
      if (elbowAngle < PUSHUP_DOWN_ANGLE && state.stage === "up") {
        state.stage = "down";
        state.downHoldFrames = 0;
        return { feedback: fb("Движение вниз...", "Going down..."), errors: [] };
      }
      if (state.stage === "down") {
        if (elbowAngle < PUSHUP_DOWN_ANGLE) {
          state.downHoldFrames++;
          var center = { x: (ls.x + rs.x) / 2, y: (ls.y + rs.y) / 2 };
          var elbowFlareAngle = angle(le, center, re);
          if (elbowFlareAngle > 100) {
            return {
              feedback: fb("Локти ближе к корпусу!", "Elbows closer to your body!"),
              errors: [
                e(
                  "Локти разведены в стороны.",
                  "Сгибайте руки вдоль корпуса: локти направлены назад, угол между локтями не больше 90–100°. Так нагрузка идёт в грудь и трицепс — и повтор засчитается.",
                  "Elbows flared out.",
                  "Tuck elbows along your body, pointing back. Angle between elbows under 90–100°. That loads chest and triceps and counts the rep."
                ),
              ],
            };
          }
        }
        if (elbowAngle > PUSHUP_TOP_ANGLE) {
          var wasHoldEnough = state.downHoldFrames >= 1;
          var bodyMoved = ref.shoulderTravel > ref.scale * PUSHUP_SHOULDER_TRAVEL && ref.hipTravel > ref.scale * PUSHUP_HIP_TRAVEL;
          var returnedUp = shoulderTravel < ref.scale * 0.2 && hipTravel < ref.scale * 0.2;
          var supportedMovement = !ref.invalid && bodyMoved && returnedUp;
          var counted = wasHoldEnough && state.topPositionPose && supportedMovement;
          var errs = [];
          if (!supportedMovement) errs.push(e(
            "Повтор не засчитан: двигайте корпус, а не руки.",
            "Оставьте ладони на месте. Опустите плечи и корпус к полу, затем поднимитесь обратно.",
            "Rep not counted: move your torso, not your hands.",
            "Keep palms in place. Lower shoulders and torso toward the floor, then push back up."
          ));
          if (!counted && !wasHoldEnough)
            errs.push(
              e(
                "Повтор не засчитан: слишком быстро внизу.",
                "Опускайтесь и поднимайтесь плавно, чтобы камера успела распознать нижнюю точку. Специально задерживаться на 1–2 секунды не нужно.",
                "Rep not counted: too fast at the bottom.",
                "Move down and up smoothly so the camera can recognize the bottom position. A deliberate 1–2 second hold is not required."
              )
            );
          if (!counted && wasHoldEnough && !state.topPositionPose)
            errs.push(
              e(
                "Неправильная форма в верхней точке.",
                "Держите корпус одной прямой линией: голова — плечи — таз — ноги. Не прогибайте поясницу и не поднимайте таз. Напрягите пресс.",
                "Wrong form at the top.",
                "Keep body in one straight line: head — shoulders — hips — legs. Don't arch your lower back or lift your hips. Engage your core."
              )
            );
          state.stage = "up";
          if (counted) state.count++;
          state.downHoldFrames = 0;
          state.pushupRef = pushupReference(ls, rs, lh, rh, lw, rw, torsoLen);
          var feedbackMsg = counted
            ? fb("Отжимание засчитано!", "Push-up counted!")
            : !supportedMovement
              ? fb("Ладони на месте — опускайте и поднимайте корпус", "Keep palms still — lower and raise your torso")
            : wasHoldEnough
              ? fb("Исправьте форму корпуса!", "Fix your body form!")
              : fb("Задержитесь внизу!", "Hold at the bottom!");
          return { feedback: feedbackMsg, errors: errs };
        }
      }
      return { feedback: fb("Продолжайте...", "Keep going..."), errors: [] };
    }

    function squat(lm) {
      var lhip = lm[23],
        lknee = lm[25],
        lankle = lm[27],
        rhip = lm[24],
        rknee = lm[26],
        rankle = lm[28];
      var lsh = lm[11],
        rsh = lm[12];
      var kneeAngle = (angle(lhip, lknee, lankle) + angle(rhip, rknee, rankle)) / 2;
      var hipAngle = (angle(lknee, lhip, lsh) + angle(rknee, rhip, rsh)) / 2;
      var bodyVisible = lankle.y > lknee.y && lknee.y > lhip.y && rankle.y > rknee.y && rknee.y > rhip.y;
      var kneesOverToes = (lknee.x > lankle.x && lhip.x < lknee.x) || (rknee.x > rankle.x && rhip.x < rknee.x);
      var errs = [];
      if (kneesOverToes)
        errs.push(
          e(
            "Колени уходят вперёд за носки.",
            "Следите, чтобы колени не выходили далеко вперёд за стопы. Отводите таз назад, как при посадке на стул.",
            "Knees going past toes.",
            "Keep knees from going far past your feet. Sit back as if into a chair."
          )
        );
      var upright = kneeAngle > 170 && hipAngle > 170 && bodyVisible;
      state.readyBuffer.push(upright);
      if (state.readyBuffer.length > READY_BUF_LEN) state.readyBuffer.shift();
      if (!state.ready) {
        if (state.readyBuffer.filter(Boolean).length >= 10) {
          state.ready = true;
          return { feedback: fb("Готово. Начинайте приседания!", "Ready. Start squats!"), errors: [] };
        }
        return { feedback: fb("Встаньте прямо для начала", "Stand straight to begin"), errors: errs };
      }
      if (!bodyVisible) {
        errs.push(
          e(
            "Не видно полное тело.",
            "Отойдите от камеры так, чтобы в кадре были голова, корпус и обе ноги целиком.",
            "Full body not visible.",
            "Step back so the camera sees your head, torso and both legs fully."
          )
        );
        return { feedback: fb("Покажите всё тело, обе ноги должны быть видны", "Show your full body, both legs must be visible"), errors: errs };
      }
      if (kneeAngle < 90 && state.stage === "up") {
        state.stage = "down";
        state.minKneeAngleInRep = kneeAngle;
        state.downHoldFrames = 0;
        return { feedback: fb("Приседайте ниже...", "Squat lower..."), errors: errs };
      }
      if (state.stage === "down") {
        if (kneeAngle < 165) state.downHoldFrames++;
        if (kneeAngle < state.minKneeAngleInRep) state.minKneeAngleInRep = kneeAngle;
        if (kneeAngle > 170) {
          var deepEnough = state.minKneeAngleInRep < 100;
          var heldDownEnough = state.downHoldFrames >= SQUAT_MIN_DOWN_FRAMES;
          if (!deepEnough)
            errs.push(
              e(
                "Недостаточная глубина приседа.",
                "Опускайтесь до угла в колене меньше 90° (бедро хотя бы параллельно полу), затем выпрямляйтесь.",
                "Squat not deep enough.",
                "Lower until knee angle is under 90° (thigh at least parallel to the floor), then stand up."
              )
            );
          if (!heldDownEnough && deepEnough)
            errs.push(
              e(
                "Слишком быстро встали.",
                "Задержитесь в нижней точке приседа на мгновение.",
                "Stood up too fast.",
                "Hold briefly at the bottom of the squat."
              )
            );
          if (deepEnough && heldDownEnough) state.count++;
          state.stage = "up";
          state.minKneeAngleInRep = 180;
          state.downHoldFrames = 0;
          return {
            feedback:
              deepEnough && heldDownEnough
                ? fb("Приседание засчитано!", "Squat counted!")
                : deepEnough
                  ? fb("Задержитесь внизу!", "Hold at the bottom!")
                  : fb("Приседайте глубже!", "Squat deeper!"),
            errors: errs,
          };
        }
      }
      return { feedback: fb("Продолжайте...", "Keep going..."), errors: errs };
    }

    function crunch(lm) {
      var nose = { x: lm[0].x, y: lm[0].y };
      var shoulder = { x: (lm[11].x + lm[12].x) / 2, y: (lm[11].y + lm[12].y) / 2 };
      var hip = { x: (lm[23].x + lm[24].x) / 2, y: (lm[23].y + lm[24].y) / 2 };
      var knee = { x: (lm[25].x + lm[26].x) / 2, y: (lm[25].y + lm[26].y) / 2 };
      var torsoAngle = angle(knee, hip, shoulder);
      var errs = [];
      if (!state.ready) {
        var minX = Math.min(nose.x, shoulder.x, hip.x, knee.x),
          maxX = Math.max(nose.x, shoulder.x, hip.x, knee.x);
        var minY = Math.min(nose.y, shoulder.y, hip.y, knee.y),
          maxY = Math.max(nose.y, shoulder.y, hip.y, knee.y);
        var inFrame = minX >= 0.06 && maxX <= 0.94 && minY >= 0.06 && maxY <= 0.94;
        var bodySpan = Math.hypot(shoulder.x - knee.x, shoulder.y - knee.y);
        var fullBodyVisible = inFrame && bodySpan > 0.22;
        var flatLying = torsoAngle > 168;
        var shoulderSpreadX = Math.abs(lm[11].x - lm[12].x);
        var sideView = shoulderSpreadX < 0.2;
        var startPoseOk = fullBodyVisible && flatLying && sideView;
        if (startPoseOk) state.readyBuffer.push(true);
        else {
          state.readyBuffer.push(false);
          if (!fullBodyVisible)
            errs.push(
              e(
                "Тело не полностью в кадре.",
                "Встаньте боком к камере: лягте на спину так, чтобы в кадре были видны голова, корпус и ноги целиком (вид сбоку).",
                "Body not fully in frame.",
                "Lie on your back sideways to the camera so head, torso and legs are fully visible (side view)."
              )
            );
          else if (!sideView)
            errs.push(
              e(
                "Камера видит вас не сбоку.",
                "Полностью повернитесь боком к камере: лёжа на спине, боком к объективу, чтобы считались скручивания.",
                "Camera not seeing you from the side.",
                "Turn fully sideways to the camera: on your back, side facing the lens, for crunches to count."
              )
            );
          else if (!flatLying)
            errs.push(
              e(
                "Стартовая поза не выпрямлена.",
                "Лягте на спину, ноги согнуты, выпрямите корпус (угол плечи–таз–колени почти 180°), затем начните.",
                "Start pose not straight.",
                "Lie on your back, knees bent, straighten your torso (shoulders–hips–knees angle nearly 180°), then start."
              )
            );
        }
        if (state.readyBuffer.length > READY_BUF_LEN) state.readyBuffer.shift();
        if (state.readyBuffer.filter(Boolean).length >= 12) {
          state.ready = true;
          state.startHipY = hip.y;
          state.crunchDownFrames = 0;
          return { feedback: fb("Готово. Начинайте скручивания!", "Ready. Start crunches!"), errors: [] };
        }
        return {
          feedback: fb(
            "Примите стартовую позицию: лёжа боком к камере, всё тело в кадре.",
            "Get in start position: on your back, sideways to the camera, full body in frame."
          ),
          errors: errs,
        };
      }
      if (state.startHipY != null && Math.abs(hip.y - state.startHipY) > 0.06) {
        errs.push(
          e(
            "Таз отрывается или смещается.",
            "Работайте только верхней частью корпуса. Таз и поясница должны оставаться на полу.",
            "Hips lifting or shifting.",
            "Work only the upper body. Hips and lower back should stay on the floor."
          )
        );
      }
      if (torsoAngle <= 118 && state.stage === "up") {
        state.stage = "down";
        state.crunchDownFrames = 0;
        return { feedback: fb("Скручивание...", "Crunching..."), errors: errs };
      }
      if (state.stage === "down") {
        if (torsoAngle < 165) state.crunchDownFrames++;
        if (torsoAngle >= 165) {
          var counted = state.crunchDownFrames >= 2;
          if (counted) state.count++;
          state.stage = "up";
          state.crunchDownFrames = 0;
          return {
            feedback: counted
              ? errs.length
                ? fb("Исправьте форму!", "Fix your form!")
                : fb("Повтор засчитан!", "Rep counted!")
              : fb("Держите скручивание чуть дольше", "Hold the crunch a bit longer"),
            errors: errs,
          };
        }
      }
      return { feedback: fb("Продолжайте...", "Keep going..."), errors: errs };
    }

    function plank(lm) {
      var ls = lm[11],
        rs = lm[12],
        lh = lm[23],
        rh = lm[24],
        la = lm[27],
        ra = lm[28],
        le = lm[13],
        re = lm[14],
        lw = lm[15],
        rw = lm[16];
      var cx = (ls.x + rs.x + lh.x + rh.x) / 4,
        cy = (ls.y + rs.y + lh.y + rh.y) / 4;
      var errs = [];
      if (state.lastCenter) {
        var dx = Math.abs(cx - state.lastCenter.x),
          dy = Math.abs(cy - state.lastCenter.y);
        if (Math.sqrt(dx * dx + dy * dy) > 0.08) {
          state.holdStartTime = null;
          state.lastCenter = { x: cx, y: cy };
          errs.push(
            e(
              "Резкое движение.",
              "Держите планку статично. Не сдвигайтесь и не подстраивайте камеру во время удержания.",
              "Sudden movement.",
              "Hold the plank still. Don't shift or adjust the camera during the hold."
            )
          );
          return { feedback: fb("Держите позу стабильно!", "Keep the pose stable!"), errors: errs };
        }
      }
      state.lastCenter = { x: cx, y: cy };
      var shoulder = { x: (ls.x + rs.x) / 2, y: (ls.y + rs.y) / 2 },
        hip = { x: (lh.x + rh.x) / 2, y: (lh.y + rh.y) / 2 },
        ankle = { x: (la.x + ra.x) / 2, y: (la.y + ra.y) / 2 };
      var torsoAngle = angle(shoulder, hip, ankle);
      var bodyStraight = torsoAngle >= 155 && torsoAngle <= 205;
      var elbowOk =
        (Math.abs(le.x - ls.x) < 0.15 && Math.abs(re.x - rs.x) < 0.15) ||
        (Math.abs(lw.x - ls.x) < 0.15 && Math.abs(rw.x - rs.x) < 0.15);
      if (!elbowOk)
        errs.push(
          e(
            "Локти/кисти не под плечами.",
            "Поставьте предплечья или ладони строго под плечами.",
            "Elbows/wrists not under shoulders.",
            "Place forearms or palms directly under your shoulders."
          )
        );
      if (!bodyStraight) {
        if (torsoAngle < 155)
          errs.push(
            e(
              "Таз провисает вниз.",
              "Поддерживайте прямую линию: голова–плечи–таз–ноги. Напрягите пресс и ягодицы.",
              "Hips sagging.",
              "Keep a straight line: head–shoulders–hips–legs. Engage core and glutes."
            )
          );
        else
          errs.push(
            e(
              "Таз поднят слишком высоко.",
              "Опустите таз в одну линию с плечами и ногами, не поднимайте ягодицы вверх.",
              "Hips too high.",
              "Lower your hips in line with shoulders and legs; don't lift your glutes up."
            )
          );
      }
      var goodPose = bodyStraight && elbowOk;
      state.readyBuffer.push(goodPose);
      if (state.readyBuffer.length > READY_BUF_LEN) state.readyBuffer.shift();
      if (!state.ready) {
        if (state.readyBuffer.filter(Boolean).length >= 10) {
          state.ready = true;
          state.holdStartTime = null;
          return { feedback: fb("Готово. Держите планку!", "Ready. Hold the plank!"), errors: [] };
        }
        return {
          feedback: fb("Примите упор на предплечьях/ладонах, тело в одну линию.", "Get into forearm or palm plank, body in one line."),
          errors: errs,
        };
      }
      if (!goodPose) {
        state.holdStartTime = null;
        return {
          feedback: errs.length ? fb("Исправьте позу.", "Fix your pose.") : fb("Держите прямую линию корпуса.", "Keep a straight body line."),
          errors: errs,
        };
      }
      state.holdStartTime = state.holdStartTime || Date.now();
      state.count = Math.floor((Date.now() - state.holdStartTime) / 1000);
      return {
        feedback: state.count
          ? TRAIN_EN
            ? "Great! " + state.count + " sec."
            : "Отлично! " + state.count + " сек."
          : TRAIN_EN
            ? "Hold! " + state.count + " sec."
            : "Держите! " + state.count + " сек.",
        errors: [],
      };
    }

    function pullup(lm) {
      var ls = lm[11],
        le = lm[13],
        lw = lm[15],
        rs = lm[12],
        re = lm[14],
        rw = lm[16];
      var lh = lm[23],
        rh = lm[24];
      var elbowAngle = (angle(ls, le, lw) + angle(rs, re, rw)) / 2;
      var wristsAbove = lw.y < ls.y - 0.02 && rw.y < rs.y - 0.02;
      var torsoLen = Math.hypot(ls.x - lh.x, ls.y - lh.y);
      var errs = [];
      if (!wristsAbove)
        errs.push(
          e(
            "Кисти не над плечами.",
            "Встань к перекладине так, чтобы кисти были выше плеч и обе руки были в кадре.",
            "Wrists not above shoulders.",
            "Hang from the bar so both wrists are above the shoulders and in frame."
          )
        );
      if (torsoLen < 0.08)
        errs.push(
          e(
            "Корпус не в кадре.",
            "Отойди, чтобы камера видела руки, плечи и таз.",
            "Torso not in frame.",
            "Step back so the camera sees arms, shoulders and hips."
          )
        );
      var hang = elbowAngle > 150 && wristsAbove && torsoLen > 0.08;
      state.readyBuffer.push(hang);
      if (state.readyBuffer.length > READY_BUF_LEN) state.readyBuffer.shift();
      if (!state.ready) {
        if (state.readyBuffer.filter(Boolean).length >= 10) {
          state.ready = true;
          state.stage = "hang";
          return { feedback: fb("Готово. Начинайте подтягивания!", "Ready. Start pull-ups!"), errors: [] };
        }
        return { feedback: fb("Повисни на перекладине, руки прямые...", "Hang from the bar, arms straight..."), errors: errs };
      }
      if (!wristsAbove) {
        return { feedback: fb("Верни руки на перекладину.", "Get your hands back on the bar."), errors: errs };
      }
      if (elbowAngle < 70 && state.stage === "hang") {
        state.stage = "up";
        state.downHoldFrames = 0;
        return { feedback: fb("Подбородок к перекладине...", "Chin to the bar..."), errors: errs };
      }
      if (state.stage === "up") {
        if (elbowAngle < 80) state.downHoldFrames++;
        if (elbowAngle > 150) {
          var counted = state.downHoldFrames >= 2;
          if (!counted)
            errs.push(
              e(
                "Повтор не засчитан: слишком быстро.",
                "Подтянись до сгиба локтя меньше 70° и задержись, затем опустись в вис.",
                "Rep not counted: too fast.",
                "Pull until elbows are under 70°, hold briefly, then lower to a hang."
              )
            );
          if (counted) state.count++;
          state.stage = "hang";
          state.downHoldFrames = 0;
          return {
            feedback: counted ? fb("Подтягивание засчитано!", "Pull-up counted!") : fb("Подтянись выше и задержись!", "Pull higher and hold!"),
            errors: errs,
          };
        }
      }
      return { feedback: fb("Продолжайте...", "Keep going..."), errors: errs };
    }

    function processLandmarksClient(landmarks) {
      if (!landmarks || landmarks.length < 28) return { count: state.count, feedback: fb("Ожидание...", "Waiting..."), errors: [] };
      var out;
      if (EX === "PUSHUP") out = pushup(landmarks);
      else if (EX === "SQUAT") out = squat(landmarks);
      else if (EX === "CRUNCH") out = crunch(landmarks);
      else if (EX === "PLANK") out = plank(landmarks);
      else if (EX === "PULLUP") out = pullup(landmarks);
      else out = { feedback: fb("Продолжайте...", "Keep going..."), errors: [] };
      return { count: state.count, feedback: out.feedback || fb("Продолжайте...", "Keep going..."), errors: out.errors || [] };
    }

    function getClientCount() {
      return state.count;
    }

    function resetClientState() {
      state.count = 0;
      state.stage = EX === "PULLUP" ? "hang" : "up";
      state.ready = false;
      state.readyBuffer = [];
      state.downHoldFrames = 0;
      state.minKneeAngleInRep = 180;
      state.goodHoldFrames = 0;
      state.lastCenter = null;
      state.holdStartTime = null;
      state.startHipY = null;
      state.stableRef = [];
      state.crunchDownFrames = 0;
      state.handsOffFrames = 0;
      state.handsOnGround = true;
      state.topPositionPose = false;
      state.pushupRef = null;
      startedAt = Date.now();
      audit = { frames: 0, poseFrames: 0, critical: 0 };
    }

    function process(landmarks) {
      audit.frames++;
      if (landmarks && landmarks.length >= 28) audit.poseFrames++;
      var out = processLandmarksClient(landmarks);
      if (out.errors && out.errors.length) audit.critical += 1;
      return out;
    }

    function getIntegrity() {
      var minutes = Math.max(1 / 60, (Date.now() - startedAt) / 60000);
      var rpm = Math.round(state.count / minutes);
      var ratio = audit.frames ? audit.poseFrames / audit.frames : 1;
      var flags = [];
      if (rpm > 45) flags.push("REP_RATE_EXCEEDED");
      if (ratio < 0.5) flags.push("LOW_TRACKED_RATIO");
      if (audit.critical > 12) flags.push("FORM_VIOLATIONS");
      return {
        tracked_reps: state.count,
        client_reps: state.count,
        valid_pose_ratio: Math.round(ratio * 1000) / 1000,
        max_reps_per_minute: rpm,
        flags: flags,
        critical_violations: audit.critical,
      };
    }

    return {
      process: process,
      getCount: getClientCount,
      reset: resetClientState,
      getIntegrity: getIntegrity,
    };
  }

  global.TeminaExerciseDetector = { create: create };
})(typeof window !== "undefined" ? window : this);
