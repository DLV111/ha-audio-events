/**
 * jsdom tests for the Audio Class Filters picker render path.
 *
 * Unlike transfer_picker.test.js (which exercises the pure state module),
 * these tests build the real DOM through PickerUI and assert what the user
 * actually sees and clicks: search filtering, chip AND search, row taps,
 * event bubbling, live counts, the phone view toggle and the saved payload.
 *
 * Run with: node ha-audio-events/app/webui/picker.test.js
 * Requires: npm install --no-save jsdom
 */
'use strict';

const assert = require('assert');
const { JSDOM } = require('jsdom');

const TransferPicker = require('./static/transfer_picker.js');
// PickerUI resolves TransferPicker from the global object at build time.
global.TransferPicker = TransferPicker;
const PickerUI = require('./static/picker.js');

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log('  \u2713 ' + name);
  } catch (error) {
    failed++;
    console.log('  \u2717 ' + name + '\n    ' + (error && error.stack ? error.stack : error));
  }
}

/* Same fixture shape as transfer_picker.test.js: two top-level groups. */
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
const classGroups = [
  { name: 'Sounds of things', classes: [{}, {}, {}] },
  { name: 'Music', classes: [{}, {}] },
];

function build(options) {
  const dom = new JSDOM('<!DOCTYPE html><body></body>');
  const doc = dom.window.document;
  const picker = PickerUI.createPicker(
    Object.assign(
      {
        document: doc,
        prefix: 'include',
        title: 'Include',
        allLabels,
        groupsTree,
        classGroups,
        accepted: [],
      },
      options || {}
    )
  );
  doc.body.appendChild(picker.element);
  return { dom, doc, win: dom.window, picker };
}

function paneLabels(doc, pane) {
  return Array.from(
    doc.querySelectorAll('#' + 'include-' + pane + ' .label-text')
  ).map(function (node) {
    return node.textContent;
  });
}

function typeSearch(doc, win, value) {
  const input = doc.getElementById('include-search');
  input.value = value;
  input.dispatchEvent(new win.Event('input', { bubbles: true }));
}

function clickChip(doc, group) {
  const chip = Array.from(doc.querySelectorAll('#include-chips .group-chip')).find(
    function (node) {
      return (node.dataset.group || '') === group;
    }
  );
  assert.ok(chip, 'chip for "' + group + '" not found');
  chip.click();
}

// --- initial render ---

test('renders every label in Available and an empty Accepted pane', function () {
  const { doc } = build();
  assert.deepStrictEqual(paneLabels(doc, 'available').sort(), allLabels.slice().sort());
  assert.deepStrictEqual(paneLabels(doc, 'accepted'), []);
  assert.ok(
    doc.querySelector('#include-accepted .empty-note'),
    'accepted pane should show an empty note'
  );
});

test('group header and label rows are siblings, not nested in the header', function () {
  const { doc } = build();
  const group = doc.querySelector('#include-available .group');
  assert.ok(group, 'no group rendered');
  assert.ok(group.querySelector(':scope > .group-header'), 'group header missing');
  assert.ok(group.querySelector(':scope > .group-labels'), 'label container missing');
  // The original bug nested .group-labels inside .group-header, which made
  // the header hundreds of pixels tall and squeezed labels to the right.
  assert.strictEqual(group.querySelector('.group-header .group-labels'), null);
});

// --- search (the original bug: filterState was never called) ---

test('typing a search filters the Available pane', function () {
  const { doc, win } = build();
  typeSearch(doc, win, 'ha');
  assert.deepStrictEqual(paneLabels(doc, 'available'), ['Hammer']);
});

test('search filters BOTH panes by class-name substring', function () {
  const { doc, win } = build({ accepted: ['Drill'] });
  typeSearch(doc, win, 'drill');
  assert.deepStrictEqual(paneLabels(doc, 'available'), []);
  assert.deepStrictEqual(paneLabels(doc, 'accepted'), ['Drill']);
});

test('search and category chip combine (AND)', function () {
  const { doc, win } = build();

  clickChip(doc, 'Music');
  assert.deepStrictEqual(paneLabels(doc, 'available').sort(), ['Music', 'Rock guitar']);

  typeSearch(doc, win, 'rock');
  assert.deepStrictEqual(paneLabels(doc, 'available'), ['Rock guitar']);

  // A search hit from another category is hidden by the active chip.
  typeSearch(doc, win, 'hammer');
  assert.deepStrictEqual(paneLabels(doc, 'available'), []);
  assert.ok(doc.querySelector('#include-available .empty-note'));
});

test('live result count reflects the filtered view', function () {
  const { doc, win } = build();
  const count = doc.getElementById('include-result-count');
  assert.ok(/5 available/.test(count.textContent), count.textContent);
  assert.ok(/0 selected/.test(count.textContent), count.textContent);

  typeSearch(doc, win, 'ha');
  assert.ok(/1 available/.test(count.textContent), count.textContent);
  assert.ok(/matching/.test(count.textContent), count.textContent);

  clickChip(doc, 'Music');
  assert.ok(/0 available/.test(count.textContent), count.textContent);
  assert.ok(/in Music/.test(count.textContent), count.textContent);
});

// --- row interaction / event bubbling ---

test('clicking the row text toggles the checkbox (whole row is a tap target)', function () {
  const { doc } = build();
  const row = doc.querySelector('#include-available .label-item');
  const checkbox = row.querySelector('input[type=checkbox]');
  row.querySelector('.label-text').click();
  assert.strictEqual(checkbox.checked, true);
  assert.strictEqual(row.getAttribute('aria-selected'), 'true');
});

test('ticking a checkbox does NOT collapse its group (bubbling regression)', function () {
  const { doc } = build();
  const group = doc.querySelector('#include-available .group');
  const checkbox = group.querySelector('input[type=checkbox]');

  checkbox.click();

  assert.strictEqual(checkbox.checked, true);
  assert.strictEqual(group.classList.contains('collapsed'), false);
  assert.strictEqual(
    group.querySelector('.group-header').getAttribute('aria-expanded'),
    'true'
  );
  // The label rows are still visible.
  assert.notStrictEqual(
    group.querySelector('.group-labels').style.display,
    'none'
  );
});

test('clicking a group header collapses it and a second click expands it', function () {
  const { doc } = build();
  const group = doc.querySelector('#include-available .group');
  const header = group.querySelector('.group-header');
  header.click();
  assert.strictEqual(group.classList.contains('collapsed'), true);
  header.click();
  assert.strictEqual(group.classList.contains('collapsed'), false);
});

// --- transfer + saved payload ---

test('accept button moves ticked labels into Accepted', function () {
  const { doc } = build();
  const row = Array.from(doc.querySelectorAll('#include-available .label-item')).find(
    function (node) {
      return node.querySelector('.label-text').textContent === 'Hammer';
    }
  );
  row.click();
  doc.getElementById('include-accept-btn').click();

  assert.deepStrictEqual(paneLabels(doc, 'accepted'), ['Hammer']);
  assert.strictEqual(paneLabels(doc, 'available').includes('Hammer'), false);
});

test('saved payload keeps the {include, exclude} lowercased array contract', function () {
  const { picker } = build({ accepted: ['Music', 'Hammer'] });
  assert.deepStrictEqual(picker.getAcceptedValues(), ['hammer', 'music']);
  assert.strictEqual(
    JSON.stringify({ include: picker.getAcceptedValues(), exclude: [] }),
    '{"include":["hammer","music"],"exclude":[]}'
  );
});

// --- phone view toggle ---

test('Browse / Selected toggle switches the body view and aria state', function () {
  const { doc } = build();
  const body = doc.getElementById('include-body');
  assert.strictEqual(body.dataset.view, 'browse');

  doc.getElementById('include-tab-selected').click();
  assert.strictEqual(body.dataset.view, 'selected');
  assert.strictEqual(
    doc.getElementById('include-tab-selected').getAttribute('aria-selected'),
    'true'
  );
  assert.strictEqual(
    doc.getElementById('include-tab-browse').getAttribute('aria-selected'),
    'false'
  );

  doc.getElementById('include-tab-browse').click();
  assert.strictEqual(body.dataset.view, 'browse');
});

// --- keyboard navigation ---

test('arrow keys move between rows and Space toggles the focused row', function () {
  const { doc, win } = build();
  const list = doc.getElementById('include-available');
  list.focus();

  const first = doc.activeElement;
  assert.ok(first.classList.contains('label-item'), 'focus did not land on a row');

  first.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
  const second = doc.activeElement;
  assert.notStrictEqual(second, first);
  assert.ok(second.classList.contains('label-item'));

  second.dispatchEvent(new win.KeyboardEvent('keydown', { key: ' ', bubbles: true }));
  assert.strictEqual(second.querySelector('input[type=checkbox]').checked, true);
});

// --- summary ---

console.log('\n' + (passed + failed) + ' tests: ' + passed + ' passed, ' + failed + ' failed');
process.exit(failed > 0 ? 1 : 0);
