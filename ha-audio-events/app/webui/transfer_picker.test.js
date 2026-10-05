/**
 * Node tests for transfer_picker.js.
 * Run with: node transfer_picker.test.js
 */
'use strict';

const assert = require('assert');
const TransferPicker = require('./transfer_picker.js');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  ✓ ' + name);
  } catch (e) {
    failed++;
    console.log('  ✗ ' + name + '\n    ' + e.message);
  }
}

// Tiny groupsTree fixture: 2 top-level groups, 3 subgroups, 5 labels
const groupsTree = {
  'Sounds of things': {
    labels: ['Hammer'],
    allLabels: ['Hammer', 'Drill', 'Engine sound'],
    count: 3,
    subgroups: {
      Tools: { labels: ['Drill'], allLabels: ['Drill'], count: 1, subgroups: {} },
      Engine: { labels: ['Engine sound'], allLabels: ['Engine sound'], count: 1, subgroups: {} },
    },
  },
  Music: {
    labels: ['Music'],
    allLabels: ['Music', 'Rock guitar'],
    count: 2,
    subgroups: {
      'Rock music': { labels: ['Rock guitar'], allLabels: ['Rock guitar'], count: 1, subgroups: {} },
    },
  },
};

const allLabels = ['Hammer', 'Drill', 'Engine sound', 'Music', 'Rock guitar'];

function newState() {
  return TransferPicker.createState(allLabels, groupsTree, []);
}

/** Recursively collect every label under a {name: {labels, subgroups}} tree. */
function flattenLabels(tree) {
  const out = [];
  Object.keys(tree).forEach(function (k) {
    const node = tree[k];
    out.push.apply(out, node.labels);
    out.push.apply(out, flattenLabels(node.subgroups));
  });
  return out;
}

// --- accept / remove ---
test('accept adds label to accepted set', () => {
  const s = newState();
  TransferPicker.accept(s, 'Hammer');
  assert.ok(s.accepted.has('hammer'));
  assert.equal(s.accepted.size, 1);
});

test('accept normalises case', () => {
  const s = newState();
  TransferPicker.accept(s, 'HAmMeR');
  assert.ok(s.accepted.has('hammer'));
});

test('accept accepts a list of labels', () => {
  const s = newState();
  TransferPicker.accept(s, ['Drill', 'Music']);
  assert.equal(s.accepted.size, 2);
});

test('remove removes label from accepted set', () => {
  const s = newState();
  TransferPicker.accept(s, ['Hammer', 'Drill']);
  TransferPicker.remove(s, 'Hammer');
  assert.ok(!s.accepted.has('hammer'));
  assert.ok(s.accepted.has('drill'));
});

test('remove accepts a list of labels', () => {
  const s = newState();
  TransferPicker.accept(s, ['Hammer', 'Drill']);
  TransferPicker.remove(s, ['Hammer', 'Drill']);
  assert.equal(s.accepted.size, 0);
});

// --- selectAll / removeAll ---
test('selectAll accepts every label', () => {
  const s = newState();
  TransferPicker.selectAll(s);
  assert.equal(s.accepted.size, allLabels.length);
});

test('removeAll clears all labels', () => {
  const s = newState();
  TransferPicker.selectAll(s);
  TransferPicker.removeAll(s);
  assert.equal(s.accepted.size, 0);
});

// --- search filtering ---
test('setSearch sets the query', () => {
  const s = newState();
  TransferPicker.setSearch(s, 'Drill');
  assert.equal(s.search, 'drill');
});

test('filterState returns matching labels in the accepted pane', () => {
  const s = newState();
  TransferPicker.accept(s, ['Hammer', 'Drill', 'Music']);
  const view = TransferPicker.filterState(s);
  // "drill" in search — only drill should appear in accepted (case-insensitive)
  TransferPicker.setSearch(s, 'drill');
  const view2 = TransferPicker.filterState(s);
  const acceptedLabels = flattenLabels(view2.accepted);
  assert.ok(acceptedLabels.includes('Drill'));
  assert.ok(!acceptedLabels.includes('Hammer'));
});

test('filterState shows labels in the available pane when search matches', () => {
  const s = newState();
  const view = TransferPicker.filterState(s);
  // All 5 labels should appear (available=5, accepted=0)
  assert.equal(view.availableCount + view.acceptedCount, allLabels.length);
});

test('filterState with group name search shows all labels in that group', () => {
  const s = newState();
  TransferPicker.accept(s, ['Hammer', 'Drill', 'Engine sound']);
  // Search for "Engine" (a subgroup name) should show Engine sound
  TransferPicker.setSearch(s, 'engine');
  const view = TransferPicker.filterState(s);
  const acceptedLabels = flattenLabels(view.accepted);
  assert.ok(acceptedLabels.includes('Engine sound'));
});

// --- counter ---
test('getCounter returns N/M format', () => {
  const s = newState();
  TransferPicker.accept(s, ['Hammer', 'Drill']);
  assert.equal(TransferPicker.getCounter(s), '2/5 values accepted');
});

// --- getAcceptedValues ---
test('getAcceptedValues returns sorted lowercased values', () => {
  const s = newState();
  TransferPicker.accept(s, ['Music', 'Hammer']);
  const values = TransferPicker.getAcceptedValues(s);
  assert.deepEqual(values, ['hammer', 'music']);
});

// --- UMD browser-global regression ---
// The panel loads this file as a classic <script> (no module/exports). This
// guards the UMD wrapper's browser branch: if it ever stops assigning a global
// `TransferPicker`, the Web UI's Audio Class Filters card fails with
// "TransferPicker is not defined" before any of the logic above is reached.
test('UMD wrapper assigns a global TransferPicker in a classic-script context', () => {
  const fs = require('fs');
  const pathMod = require('path');
  const vm = require('vm');
  const src = fs.readFileSync(pathMod.join(__dirname, 'transfer_picker.js'), 'utf8');

  // Fake browser global: has globalThis/self/window, but no module or exports.
  const sandbox = {};
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  sandbox.window = sandbox;
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox, { filename: 'transfer_picker.js' });

  const TP = sandbox.TransferPicker;
  assert.equal(typeof TP, 'object', 'TransferPicker was not assigned on the global');

  ['createState', 'accept', 'remove', 'selectAll', 'removeAll', 'setSearch',
   'filterState', 'getCounter', 'getAcceptedValues'].forEach(function (name) {
    assert.equal(typeof TP[name], 'function', 'TransferPicker.' + name + ' is missing');
  });

  // The global instance must actually work, not just exist.
  const s = TP.createState(['Hammer', 'Drill'], groupsTree, []);
  TP.accept(s, 'Hammer');
  assert.equal(TP.getCounter(s), '1/2 values accepted');
});

// --- summary ---
console.log(`\n${passed + failed} tests: ${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
