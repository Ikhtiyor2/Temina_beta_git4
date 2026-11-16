const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
function detector() {
  const context = vm.createContext({ Date, Math });
  context.window = context;
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../temina-exercise-detector.js'), 'utf8'), context);
  return context.TeminaExerciseDetector.create('PUSHUP', 'ru');
}
function pose(offset = 0, down = false) {
  const lm = Array.from({ length: 33 }, () => ({ x: 0, y: 0, visibility: 1 }));
  const y = down ? 0.45 : 0.3;
  for (const [s, e, w, h, k, x] of [[11,13,15,23,25,0.3], [12,14,16,24,26,0.5]]) {
    lm[s] = { x, y: y + offset };
    lm[e] = { x: x + (down ? 0.12 : 0), y: (down ? 0.48 : 0.4) + offset };
    lm[w] = { x, y: 0.5 + offset };
    lm[h] = { x: x + 0.2, y: y + 0.02 + offset };
    lm[k] = { x: x + 0.4, y: y + 0.04 + offset };
  }
  return lm;
}
test('hands higher in the image still allow setup and a complete push-up', () => {
  for (const offset of [-0.18, 0, 0.24]) {
    const d = detector();
    let out;
    for (let i = 0; i < 15; i++) out = d.process(pose(offset));
    assert.equal(out.errors.length, 0);
    for (let i = 0; i < 4; i++) d.process(pose(offset, true));
    d.process(pose(offset));
    assert.equal(d.getCount(), 1, 'count must not depend on vertical framing');
  }
});
test('sustained raised hands still block setup and repetitions', () => {
  const d = detector(); const lm = pose();
  lm[15].y = lm[16].y = 0.1;
  let out;
  for (let i = 0; i < 12; i++) out = d.process(lm);
  assert.match(out.feedback, /руки на пол/);
  assert.equal(d.getCount(), 0);
});
test('brief landmark jitter does not interrupt a ready pose', () => {
  const d = detector();
  for (let i = 0; i < 15; i++) d.process(pose());
  const jitter = pose(); jitter[15].y = jitter[16].y = 0.1;
  for (let i = 0; i < 6; i++) assert.equal(d.process(jitter).errors.length, 0);
  assert.equal(d.process(pose()).errors.length, 0);
  for (let i = 0; i < 4; i++) d.process(pose(0, true));
  d.process(pose());
  assert.equal(d.getCount(), 1);
});

function ready(d) { for (let i = 0; i < 15; i++) d.process(pose()); }
function cycle(d, bottom) {
  let out;
  for (let i = 0; i < 5; i++) out = d.process(bottom);
  return d.process(pose());
}
test('elbow-only bending with stationary shoulders and hips does not count', () => {
  const d = detector(); ready(d);
  const fake = pose();
  fake[13].x += 0.12; fake[14].x += 0.12;
  const result = cycle(d, fake);
  assert.equal(d.getCount(), 0);
  assert.match(result.feedback, /корпус/);
});
test('kneeling hand-to-shoulder imitation is rejected, then a normal rep can count', () => {
  const d = detector(); ready(d);
  const fake = pose();
  for (const [e, w] of [[13,15], [14,16]]) {
    fake[e].x += 0.12;
    fake[w].y = 0.34;
  }
  for (let rep = 0; rep < 3; rep++) cycle(d, fake);
  assert.equal(d.getCount(), 0);
  cycle(d, pose(0, true));
  assert.equal(d.getCount(), 1);
});
test('moving the shoulders without lowering the hips is not a full-body repetition', () => {
  const d = detector(); ready(d);
  const fake = pose(0, true), top = pose();
  for (const i of [23,24,25,26]) fake[i] = top[i];
  cycle(d, fake);
  assert.equal(d.getCount(), 0);
});
test('sustained wrist displacement invalidates an otherwise complete body movement', () => {
  const d = detector(); ready(d);
  d.process(pose(0, true));
  const shifted = pose(0, true);
  shifted[15].x += 0.09; shifted[16].x += 0.09;
  for (let i = 0; i < 4; i++) d.process(shifted);
  for (let i = 0; i < 4; i++) d.process(pose(0, true));
  d.process(pose());
  assert.equal(d.getCount(), 0);
});
test('small wrist jitter is tolerated and consecutive genuine repetitions count', () => {
  const d = detector(); ready(d);
  const bottom = pose(0, true);
  bottom[15].x += 0.012; bottom[16].x -= 0.012;
  for (let rep = 0; rep < 3; rep++) cycle(d, bottom);
  assert.equal(d.getCount(), 3);
});
test('uncertain pose landmarks cannot create a counted repetition', () => {
  const d = detector(); ready(d);
  const bottom = pose(0, true); bottom[23].visibility = 0.1;
  cycle(d, bottom);
  assert.equal(d.getCount(), 0);
});
test('reset clears partial repetition and its movement reference', () => {
  const d = detector(); ready(d);
  for (let i = 0; i < 5; i++) d.process(pose(0, true));
  d.reset(); ready(d);
  assert.equal(d.getCount(), 0);
  cycle(d, pose(0, true));
  assert.equal(d.getCount(), 1);
});

function relaxedPose(down = false) {
  const lm = pose();
  for (const [s,e,h,k] of [[11,13,23,25],[12,14,24,26]]) {
    if (down) {
      lm[s].y = 0.38; lm[h].y = 0.40; lm[k].y = 0.42;
      lm[e].x += 0.05; lm[e].y = 0.44; // ~100 degrees, rather than strictly below 90.
    } else lm[e].x += 0.03; // ~147 degrees: slightly bent arms at the top.
  }
  return lm;
}
test('relaxed angles count a smooth rep without a deliberate bottom hold', () => {
  const d = detector();
  for (let i = 0; i < 10; i++) d.process(relaxedPose());
  d.process(relaxedPose(true)); d.process(relaxedPose(true));
  d.process(relaxedPose());
  assert.equal(d.getCount(), 1);
});
test('narrow shoulder projection from a side angle does not block setup', () => {
  const d = detector();
  function side(down) {
    const lm = relaxedPose(down);
    for (const i of [12,14,16,24,26]) lm[i].x -= 0.14;
    return lm;
  }
  for (let i = 0; i < 10; i++) d.process(side(false));
  d.process(side(true)); d.process(side(true)); d.process(side(false));
  assert.equal(d.getCount(), 1);
});
test('more tolerant setup still rejects an upright body', () => {
  const d = detector(); const standing = pose();
  for (const [s,e,w,h,k] of [[11,13,15,23,25],[12,14,16,24,26]]) {
    standing[s].y=0.2; standing[e].y=0.35; standing[w].y=0.5;
    standing[h]={x:standing[s].x,y:0.45};
    standing[k]={x:standing[s].x,y:0.7};
  }
  for(let i=0;i<15;i++) d.process(standing);
  cycle(d, pose(0,true));
  assert.equal(d.getCount(),0);
});
