/**
 * PickerUI — DOM renderer for the Audio Class Filters transfer picker.
 *
 * UMD module: works as CommonJS (require) in Node/jsdom tests and as a global
 * (PickerUI) when loaded via <script> after transfer_picker.js.
 *
 * The pure state/query logic lives in transfer_picker.js (TransferPicker).
 * This module owns rendering and interaction only:
 *
 *   - both panes are rendered from TransferPicker.filterState(state), so the
 *     search box actually filters the lists (it previously never did);
 *   - the active category chip is ANDed with the search query;
 *   - group headers and label rows are SIBLINGS, not nested in a flex header;
 *   - a click anywhere on a label row toggles its checkbox, and a checkbox
 *     click stops propagation so it can never collapse the group;
 *   - optional row keyboard navigation (Arrow/Home/End + Space/Enter);
 *   - a live result count (aria-live) and a Browse / Selected phone view.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(root);
  } else {
    root.PickerUI = factory(root);
  }
})(
  typeof globalThis !== 'undefined'
    ? globalThis
    : typeof self !== 'undefined'
      ? self
      : this,
  function (root) {
    'use strict';

    function resolveTransferPicker() {
      if (root && root.TransferPicker) return root.TransferPicker;
      if (typeof require === 'function') {
        try {
          return require('./transfer_picker.js');
        } catch (error) {
          // Fall through to the explicit error below.
        }
      }
      throw new Error('PickerUI requires TransferPicker (load transfer_picker.js first)');
    }

    function el(doc, tag, className, text) {
      var node = doc.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }

    /** Collect a {labels, subgroups} node into a flat array of label names. */
    function collectLabels(node, out) {
      (node.labels || []).forEach(function (label) {
        out.push(label);
      });
      var subgroups = node.subgroups || {};
      Object.keys(subgroups).forEach(function (key) {
        collectLabels(subgroups[key], out);
      });
      return out;
    }

    /**
     * Convert a filterState() view ({group: {labels, subgroups}}) into
     * {group: [labels]}, flattening nested subgroups under their top-level
     * group (the layout groups by AudioSet top-level category).
     */
    function flattenView(view) {
      var buckets = {};
      Object.keys(view || {}).forEach(function (top) {
        var labels = collectLabels(view[top], []);
        if (labels.length) buckets[top] = labels;
      });
      return buckets;
    }

    function bucketedCount(buckets) {
      var total = 0;
      Object.keys(buckets).forEach(function (key) {
        total += buckets[key].length;
      });
      return total;
    }

    /**
     * Build a picker.
     *
     * @param {object} options
     * @param {string} options.prefix           id prefix, e.g. "include"
     * @param {string} options.title            heading text
     * @param {string[]} options.allLabels      all YAMNet display names
     * @param {object} options.groupsTree       ontology tree (top_level_groups)
     * @param {object[]} options.classGroups    [{name, classes}] for the chips
     * @param {string[]} [options.accepted]     initially accepted (lowercased ok)
     * @param {Document} [options.document]     document to build into
     * @returns {object} controller
     */
    function createPicker(options) {
      var doc =
        options.document ||
        (typeof document !== 'undefined' ? document : null);
      if (!doc) throw new Error('PickerUI.createPicker requires a document');

      var TP = resolveTransferPicker();
      var prefix = options.prefix;
      var allLabels = (options.allLabels || []).slice();
      var groupsTree = options.groupsTree || {};
      var classGroups = options.classGroups || [];
      var state = TP.createState(allLabels, groupsTree, options.accepted || []);
      var activeGroup = null;
      var view = 'browse';

      var rootEl = el(doc, 'div', 'picker');
      rootEl.id = prefix + '-picker';

      /* ---- heading ---- */
      var head = el(doc, 'div', 'picker-head');
      var h3 = el(doc, 'h3');
      h3.appendChild(el(doc, 'span', 'picker-title', options.title || 'Audio Class Filters'));
      var counter = el(doc, 'span', 'picker-counter');
      counter.id = prefix + '-counter';
      h3.appendChild(counter);
      head.appendChild(h3);
      rootEl.appendChild(head);

      /* ---- toolbar: search + phone view toggle + live count ---- */
      var toolbar = el(doc, 'div', 'picker-toolbar');

      var search = el(doc, 'input', 'picker-search');
      search.type = 'search';
      search.id = prefix + '-search';
      search.placeholder = 'Search audio classes\u2026';
      search.autocomplete = 'off';
      search.setAttribute('aria-label', (options.title || 'Filters') + ': search classes');
      toolbar.appendChild(search);

      var segmented = el(doc, 'div', 'picker-segmented');
      segmented.setAttribute('role', 'tablist');
      segmented.setAttribute('aria-label', 'Picker view');
      var browseBtn = el(doc, 'button', 'seg-btn active', 'Browse');
      browseBtn.type = 'button';
      browseBtn.id = prefix + '-tab-browse';
      browseBtn.setAttribute('role', 'tab');
      browseBtn.setAttribute('aria-selected', 'true');
      var selectedBtn = el(doc, 'button', 'seg-btn', 'Selected');
      selectedBtn.type = 'button';
      selectedBtn.id = prefix + '-tab-selected';
      selectedBtn.setAttribute('role', 'tab');
      selectedBtn.setAttribute('aria-selected', 'false');
      segmented.appendChild(browseBtn);
      segmented.appendChild(selectedBtn);
      toolbar.appendChild(segmented);

      var resultCount = el(doc, 'div', 'picker-count');
      resultCount.id = prefix + '-result-count';
      resultCount.setAttribute('aria-live', 'polite');
      toolbar.appendChild(resultCount);
      rootEl.appendChild(toolbar);

      /* ---- category chips ---- */
      var chips = el(doc, 'div', 'group-chips');
      chips.id = prefix + '-chips';
      chips.setAttribute('role', 'group');
      chips.setAttribute('aria-label', 'Filter by category');
      var allChip = el(doc, 'button', 'group-chip active', 'All categories');
      allChip.type = 'button';
      allChip.dataset.group = '';
      allChip.setAttribute('aria-pressed', 'true');
      chips.appendChild(allChip);
      classGroups.forEach(function (group) {
        var chip = el(
          doc,
          'button',
          'group-chip',
          group.name + ' (' + (group.classes || []).length + ')'
        );
        chip.type = 'button';
        chip.dataset.group = group.name;
        chip.setAttribute('aria-pressed', 'false');
        chips.appendChild(chip);
      });
      rootEl.appendChild(chips);

      /* ---- panes ---- */
      var body = el(doc, 'div', 'picker-body');
      body.id = prefix + '-body';
      body.dataset.view = view;

      function buildPane(key, label) {
        var pane = el(doc, 'section', 'pane pane-' + key);
        var header = el(doc, 'div', 'pane-header');
        var titleWrap = el(doc, 'span', 'pane-title');
        titleWrap.appendChild(doc.createTextNode(label + ' '));
        var count = el(doc, 'span', 'pane-count');
        count.id = prefix + '-' + key + '-count';
        titleWrap.appendChild(count);
        header.appendChild(titleWrap);

        var selectAll = null;
        var removeAll = null;
        if (key === 'available') {
          var actions = el(doc, 'div', 'pane-actions');
          selectAll = el(doc, 'button', 'select-all-btn', 'Select All');
          selectAll.type = 'button';
          selectAll.id = prefix + '-select-all-btn';
          removeAll = el(doc, 'button', 'remove-all-btn', 'Remove All');
          removeAll.type = 'button';
          removeAll.id = prefix + '-remove-all-btn';
          actions.appendChild(selectAll);
          actions.appendChild(removeAll);
          header.appendChild(actions);
        }

        var list = el(doc, 'div', 'pane-list');
        list.id = prefix + '-' + key;
        list.setAttribute('role', 'listbox');
        list.setAttribute('aria-multiselectable', 'true');
        list.setAttribute('aria-label', label + ' audio classes');
        list.tabIndex = 0;

        pane.appendChild(header);
        pane.appendChild(list);
        return {
          pane: pane,
          list: list,
          count: count,
          selectAll: selectAll,
          removeAll: removeAll,
        };
      }

      var avail = buildPane('available', 'Available');

      var transfer = el(doc, 'div', 'transfer-controls');
      var acceptBtn = el(doc, 'button', 'transfer-btn', '\u2192');
      acceptBtn.type = 'button';
      acceptBtn.id = prefix + '-accept-btn';
      acceptBtn.dataset.action = 'accept';
      acceptBtn.title = 'Accept selected labels';
      acceptBtn.setAttribute('aria-label', 'Accept selected labels');
      var removeBtn = el(doc, 'button', 'transfer-btn', '\u2190');
      removeBtn.type = 'button';
      removeBtn.id = prefix + '-remove-btn';
      removeBtn.dataset.action = 'remove';
      removeBtn.title = 'Remove selected labels';
      removeBtn.setAttribute('aria-label', 'Remove selected labels');
      transfer.appendChild(acceptBtn);
      transfer.appendChild(removeBtn);

      var acc = buildPane('accepted', 'Accepted');

      body.appendChild(avail.pane);
      body.appendChild(transfer);
      body.appendChild(acc.pane);
      rootEl.appendChild(body);

      /* ---- rendering ---- */

      function createLabelRow(labelName, paneKey, index) {
        var item = el(doc, 'div', 'label-item');
        item.id = prefix + '-' + paneKey + '-opt-' + index;
        item.setAttribute('role', 'option');
        item.setAttribute('aria-selected', 'false');
        item.tabIndex = -1;

        var cb = el(doc, 'input');
        cb.type = 'checkbox';
        cb.dataset.label = labelName;
        cb.tabIndex = -1;
        cb.setAttribute('aria-label', labelName);

        var span = el(doc, 'span', 'label-text', labelName);
        item.appendChild(cb);
        item.appendChild(span);

        function sync() {
          item.setAttribute('aria-selected', cb.checked ? 'true' : 'false');
          item.classList.toggle('is-checked', cb.checked);
        }

        cb.addEventListener('click', function (event) {
          // A tick must never bubble to the group header: that handler
          // toggles .collapsed, so the group used to vanish on every click.
          event.stopPropagation();
          sync();
        });

        item.addEventListener('click', function (event) {
          if (event.target === cb) return; // handled by the checkbox itself
          cb.checked = !cb.checked;
          sync();
        });

        return item;
      }

      function renderPane(list, buckets, paneKey) {
        list.innerHTML = '';
        var names = Object.keys(buckets).sort(function (a, b) {
          return a.localeCompare(b);
        });
        if (!names.length) {
          var empty = el(
            doc,
            'div',
            'empty-note',
            paneKey === 'accepted'
              ? 'No accepted classes match.'
              : 'No available classes match.'
          );
          empty.setAttribute('role', 'status');
          list.appendChild(empty);
          return 0;
        }

        var optionIndex = 0;
        names.forEach(function (groupName) {
          var labels = buckets[groupName].slice().sort(function (a, b) {
            return a.localeCompare(b);
          });

          var group = el(doc, 'div', 'group');
          var header = el(doc, 'div', 'group-header');
          header.setAttribute('aria-expanded', 'true');

          var caret = el(doc, 'span', 'group-caret', '\u25be');
          caret.setAttribute('aria-hidden', 'true');
          var title = el(
            doc,
            'span',
            'group-title',
            groupName + ' (' + labels.length + ')'
          );

          var actions = el(doc, 'div', 'group-actions');
          var btn = el(doc, 'button', 'group-btn', paneKey === 'available' ? 'Select' : 'Clear');
          btn.type = 'button';
          btn.setAttribute(
            'aria-label',
            (paneKey === 'available' ? 'Select all in ' : 'Clear all in ') + groupName
          );
          btn.addEventListener('click', function (event) {
            event.stopPropagation();
            if (paneKey === 'available') TP.accept(state, labels);
            else TP.remove(state, labels);
            render();
          });
          actions.appendChild(btn);

          header.appendChild(caret);
          header.appendChild(title);
          header.appendChild(actions);
          header.addEventListener('click', function () {
            var collapsed = group.classList.toggle('collapsed');
            header.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
          });

          var labelsDiv = el(doc, 'div', 'group-labels');
          labels.forEach(function (labelName) {
            labelsDiv.appendChild(
              createLabelRow(labelName, paneKey, optionIndex++)
            );
          });

          group.appendChild(header);
          group.appendChild(labelsDiv);
          list.appendChild(group);
        });
        return optionIndex;
      }

      function updateChips() {
        var chipNodes = chips.querySelectorAll('.group-chip');
        Array.prototype.forEach.call(chipNodes, function (chip) {
          var on = (chip.dataset.group || '') === (activeGroup || '');
          chip.classList.toggle('active', on);
          chip.setAttribute('aria-pressed', on ? 'true' : 'false');
        });
      }

      function restrict(buckets, groupName) {
        if (!groupName) return buckets;
        var out = {};
        if (buckets[groupName]) out[groupName] = buckets[groupName];
        return out;
      }

      function render() {
        // Single source of truth for "what matches": the pure module filters
        // by the search query; the active chip is then ANDed on top.
        var filtered = TP.filterState(state);
        var availBuckets = restrict(flattenView(filtered.available), activeGroup);
        var accBuckets = restrict(flattenView(filtered.accepted), activeGroup);

        var availRows = renderPane(avail.list, availBuckets, 'available');
        var accRows = renderPane(acc.list, accBuckets, 'accepted');

        avail.count.textContent = String(availRows);
        acc.count.textContent = String(accRows);
        counter.textContent = TP.getCounter(state);

        var bits = [availRows + ' available', accRows + ' selected'];
        if (state.search) bits.push('matching \u201c' + state.search + '\u201d');
        if (activeGroup) bits.push('in ' + activeGroup);
        resultCount.textContent = bits.join(' \u00b7 ');
      }

      /* ---- interaction ---- */

      search.addEventListener('input', function (event) {
        TP.setSearch(state, event.target.value);
        render();
      });

      chips.addEventListener('click', function (event) {
        var chip = event.target.closest ? event.target.closest('.group-chip') : null;
        if (!chip) return;
        activeGroup = chip.dataset.group || null;
        render();
      });

      function setView(next) {
        view = next === 'selected' ? 'selected' : 'browse';
        body.dataset.view = view;
        browseBtn.classList.toggle('active', view === 'browse');
        selectedBtn.classList.toggle('active', view === 'selected');
        browseBtn.setAttribute('aria-selected', view === 'browse' ? 'true' : 'false');
        selectedBtn.setAttribute('aria-selected', view === 'selected' ? 'true' : 'false');
      }
      browseBtn.addEventListener('click', function () {
        setView('browse');
      });
      selectedBtn.addEventListener('click', function () {
        setView('selected');
      });

      function readChecked(list) {
        return Array.prototype.slice
          .call(list.querySelectorAll('input[type=checkbox]:checked'))
          .map(function (cb) {
            return cb.dataset.label;
          });
      }

      acceptBtn.addEventListener('click', function () {
        var labels = readChecked(avail.list);
        if (!labels.length) return;
        TP.accept(state, labels);
        render();
      });

      removeBtn.addEventListener('click', function () {
        var labels = readChecked(acc.list);
        if (!labels.length) return;
        TP.remove(state, labels);
        render();
      });

      // "Select All" / "Remove All" act on what is currently visible
      // (search + chip applied), so a filtered view can't silently accept
      // hundreds of hidden labels.
      avail.selectAll.addEventListener('click', function () {
        var visible = Array.prototype.slice
          .call(avail.list.querySelectorAll('input[type=checkbox]'))
          .map(function (cb) {
            return cb.dataset.label;
          });
        if (!visible.length) return;
        TP.accept(state, visible);
        render();
      });

      avail.removeAll.addEventListener('click', function () {
        var visible = Array.prototype.slice
          .call(acc.list.querySelectorAll('input[type=checkbox]'))
          .map(function (cb) {
            return cb.dataset.label;
          });
        if (!visible.length) return;
        TP.remove(state, visible);
        render();
      });

      // Keyboard navigation: the listbox is a single tab stop; arrows move
      // between rows, Home/End jump, Space/Enter toggles.
      function wireKeyboard(list) {
        list.addEventListener('keydown', function (event) {
          var rows = Array.prototype.slice.call(list.querySelectorAll('.label-item'));
          if (!rows.length) return;
          var index = rows.indexOf(doc.activeElement);

          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            var delta = event.key === 'ArrowDown' ? 1 : -1;
            var next = index === -1 ? (delta > 0 ? 0 : rows.length - 1) : index + delta;
            if (next < 0) next = 0;
            if (next >= rows.length) next = rows.length - 1;
            rows[next].focus();
            list.setAttribute('aria-activedescendant', rows[next].id);
          } else if (event.key === 'Home' || event.key === 'End') {
            event.preventDefault();
            var target = event.key === 'Home' ? rows[0] : rows[rows.length - 1];
            target.focus();
            list.setAttribute('aria-activedescendant', target.id);
          } else if (event.key === ' ' || event.key === 'Enter') {
            if (index === -1) return;
            event.preventDefault();
            rows[index].querySelector('input[type=checkbox]').click();
          }
        });

        list.addEventListener('focus', function () {
          if (doc.activeElement !== list) return;
          var first = list.querySelector('.label-item');
          if (first) {
            first.focus();
            list.setAttribute('aria-activedescendant', first.id);
          }
        });
      }
      wireKeyboard(avail.list);
      wireKeyboard(acc.list);

      render();

      return {
        element: rootEl,
        state: state,
        render: render,
        setView: setView,
        setGroup: function (name) {
          activeGroup = name || null;
          render();
        },
        getAcceptedValues: function () {
          return TP.getAcceptedValues(state);
        },
        destroy: function () {
          if (rootEl.parentNode) rootEl.parentNode.removeChild(rootEl);
        },
      };
    }

    return {
      createPicker: createPicker,
      flattenView: flattenView,
      bucketedCount: bucketedCount,
    };
  }
);
