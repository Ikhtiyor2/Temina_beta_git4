const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../miniapp.js'), 'utf8');
function functionSource(name) {
  const start = source.indexOf('  async function ' + name + '(') >= 0
    ? source.indexOf('  async function ' + name + '(') : source.indexOf('  function ' + name + '(');
  assert.ok(start >= 0, name);
  const rest = source.slice(start + 1);
  const next = rest.search(/\n  (?:async )?function /);
  return next < 0 ? rest.slice(0, rest.indexOf('\n  boot();')) : rest.slice(0, next);
}
function deferred() { let resolve, reject; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
function setup(overrides = {}) {
  const nodes = new Map();
  const node = () => ({ disabled: true, hidden: true, textContent: '', classList: { add() {} }, querySelector() { return node(); }, play() { return Promise.resolve(); } });
  const state = { session: null };
  const context = vm.createContext({
    state, Date, Promise, console, setTimeout, clearTimeout, clearInterval,
    t: key => key, workoutUsesCamera: () => true,
    render: () => {}, api: async () => ({ sessionId: '42' }),
    requestCameraStream: () => new Promise(() => {}), ensurePoseLibs: () => new Promise(() => {}),
    attachWorkoutCamera: () => {},
    screen: { prepend() {}, appendChild() {} },
    document: { getElementById(id) { if (!nodes.has(id)) nodes.set(id, node()); return nodes.get(id); }, createElement: node, querySelector: () => null },
    ...overrides,
  });
  for (const name of ['stopCameraSession', 'cameraError', 'prepareWorkoutCamera', 'startWorkout']) vm.runInContext(functionSource(name), context);
  return { context, state, nodes };
}
const workout = { id: 'pushup_classic', title: 'Push-ups', parentType: 'PUSHUP' };

test('workout screen opens before pending permission, AI scripts or API complete', async () => {
  const api = deferred(); let renders = 0, requests = 0;
  const { context, state } = setup({ api: () => api.promise, render: () => { renders++; }, requestCameraStream: () => { requests++; return new Promise(() => {}); } });
  const start = context.startWorkout(workout);
  assert.equal(renders, 1);
  assert.equal(state.session.kind, 'workout');
  assert.equal(requests, 1);
  await context.startWorkout(workout);
  assert.equal(requests, 1, 'double tap must not start another stream');
  api.resolve({ sessionId: '42' }); await start;
  assert.equal(state.session.id, '42');
});

test('camera preview appears while AI libraries are still loading', async () => {
  const libs = deferred(); const stream = { getTracks: () => [] };
  const { context, state, nodes } = setup({ requestCameraStream: async () => stream, ensurePoseLibs: () => libs.promise });
  await context.startWorkout(workout);
  assert.equal(nodes.get('camVideo').srcObject, stream);
  assert.equal(state.session.id, '42');
  libs.reject(new Error('CDN unavailable'));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(state.session.camError, 'train.camMissing');
  assert.equal(nodes.get('camRetryButton').hidden, false);
});

test('denied permission exposes retry instead of leaving the exercise detail screen', async () => {
  const { context, state, nodes } = setup({ requestCameraStream: async () => { throw new Error('denied'); } });
  await context.startWorkout(workout);
  assert.equal(state.session.kind, 'workout');
  assert.equal(state.session.camError, 'train.camDenied');
  assert.equal(nodes.get('camRetryButton').hidden, false);
});

test('a late camera permission result is stopped after API failure', async () => {
  const camera = deferred(); let stopped = 0;
  const { context, state } = setup({ requestCameraStream: () => camera.promise, api: async () => { throw new Error('offline'); } });
  await context.startWorkout(workout);
  assert.equal(state.session, null);
  camera.resolve({ getTracks: () => [{ stop() { stopped++; } }] });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(stopped, 1);
});

test('stopping a camera without an AI handle releases its tracks', () => {
  let stopped = 0;
  const { context } = setup();
  const session = { stream: { getTracks: () => [{ stop() { stopped++; } }] } };
  context.stopCameraSession(session);
  assert.equal(stopped, 1); assert.equal(session.stream, null);
});

test('camera permission arriving during workout finish cannot restart the camera', async () => {
  const camera = deferred(); let stopped = 0;
  const { context, state } = setup({ requestCameraStream: () => camera.promise });
  await context.startWorkout(workout);
  state.session.finishing = true;
  camera.resolve({ getTracks: () => [{ stop() { stopped++; } }] });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(stopped, 1);
  assert.equal(state.session.stream, null);
});

test('failed result save preserves session and allows another finish attempt', async () => {
  const { context, state, nodes } = setup({ api: async () => { throw new Error('offline'); } });
  state.session = { id: '42', startedAt: Date.now(), minutes: 1, calories: 0, reps: 8 };
  vm.runInContext(functionSource('finishWorkout'), context);
  await context.finishWorkout();
  assert.equal(state.session.id, '42');
  assert.equal(state.session.reps, 8);
  assert.equal(state.session.finishing, false);
  assert.equal(nodes.get('finish').disabled, false);
});

test('onboarding completes before authentication can block startup', async () => {
  const intro = deferred(); let authCalls = 0, opened = false;
  const { context } = setup({
    window: { TeminaIntro: { show: () => intro.promise } }, tg: null,
    showGate() {}, openApp() { opened = true; },
    api: async () => { authCalls++; return { authenticated: true }; },
  });
  vm.runInContext(functionSource('boot'), context);
  const boot = context.boot();
  assert.equal(authCalls, 0); assert.equal(opened, false);
  intro.resolve(); await boot;
  assert.equal(authCalls, 1); assert.equal(opened, true);
});

test('AI reuses the granted camera stream and continues inference without Camera.start', async () => {
  const frames = new Map(); let frameId = 0, requests = 0, stopped = 0, inferences = 0;
  const statuses = [];
  const ctx = { save() {}, scale() {}, drawImage() {}, restore() {}, fillRect() {} };
  const pose = { send: async () => { inferences++; }, onResults() {} };
  const stream = { getTracks: () => [{ stop() { stopped++; } }] };
  const video = { readyState: 2, currentTime: 1, videoWidth: 640, videoHeight: 480, setAttribute() {}, play: async () => {} };
  const context = vm.createContext({
    console, Promise, performance, setTimeout, clearTimeout,
    navigator: { mediaDevices: { getUserMedia() { requests++; throw new Error('unexpected camera request'); } } },
    document: { getElementById: () => null, createElement: () => ({ getContext: () => ctx }) },
    requestAnimationFrame(callback) { const id = ++frameId; frames.set(id, callback); return id; },
    cancelAnimationFrame(id) { frames.delete(id); },
    matchMedia: () => ({ matches: true }),
    TeminaPoseClient: { getOrCreatePose: async () => pose },
    Camera: class { constructor() { throw new Error('must reuse existing stream'); } },
  });
  context.window = context;
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../temina-camera-pose.js'), 'utf8'), context);
  const handle = context.TeminaCameraPose.launch({ video, canvas: { getContext: () => ctx }, stream, onResults() {}, onStatus: phase => statuses.push(phase) });
  try {
    await new Promise(resolve => setImmediate(resolve));
    assert.ok(statuses.includes('running'));
    assert.equal(requests, 0);
    assert.equal(video.srcObject, stream);
    const warmup = inferences;
    for (const [id, callback] of [...frames]) { frames.delete(id); callback(); }
    await new Promise(resolve => setImmediate(resolve));
    assert.ok(inferences > warmup, 'live frames must reach the pose model');
  } finally { handle.cancel(); }
  assert.equal(frames.size, 0);
  assert.equal(stopped, 1);
});
