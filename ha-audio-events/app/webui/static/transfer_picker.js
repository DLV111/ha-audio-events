/**
 * TransferPicker — pure transfer-picker logic for the HA Audio Events WebUI.
 *
 * UMD module: works as CommonJS (require) in Node tests and as a global
 * (TransferPicker) when loaded via <script> in the browser.
 *
 * State shape:
 *   { accepted: Set<string>, allLabels: string[], groupsTree: {...} }
 *
 * All functions are pure (mutate state in place, return no value).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.TransferPicker = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Create picker state for a single picker (include or exclude).
   * @param {string[]} allLabels - all 521 YAMNet display names
   * @param {object} groupsTree - top_level_groups from yamnet_groups.json
   * @param {string[]} accepted - currently accepted label names (lowercased)
   * @returns {object} state
   */
  function createState(allLabels, groupsTree, accepted) {
    return {
      accepted: new Set((accepted || []).map(function (l) { return l.toLowerCase(); })),
      allLabels: allLabels.slice().sort(),
      groupsTree: groupsTree || {},
      search: '',
    };
  }

  /** Move selected available labels into accepted. */
  function accept(state, labels) {
    var list = Array.isArray(labels) ? labels : [labels];
    list.forEach(function (l) { state.accepted.add(l.toLowerCase()); });
  }

  /** Remove selected accepted labels from accepted. */
  function remove(state, labels) {
    var list = Array.isArray(labels) ? labels : [labels];
    list.forEach(function (l) { state.accepted.delete(l.toLowerCase()); });
  }

  /** Accept every label. */
  function selectAll(state) {
    state.allLabels.forEach(function (l) { state.accepted.add(l.toLowerCase()); });
  }

  /** Deselect everything. */
  function removeAll(state) {
    state.accepted.clear();
  }

  /** Set the search query (lowercased). */
  function setSearch(state, query) {
    state.search = (query || '').toLowerCase();
  }

  /** Flatten groupsTree into a Set of group display names (ancestors + leaf group names). */
  function _groupNames(tree) {
    var names = {};
    function walk(node, path) {
      var p = path.slice();
      // The node itself is a group; its labels live directly under it.
      // We don't have the group's own name here — it's the key in the parent.
      Object.keys(node.subgroups || {}).forEach(function (k) {
        walk(node.subgroups[k], p.concat([k]));
      });
      // Every key encountered as a group name is searchable.
      // `path` holds ancestor group names; the leaf group name is `name`.
    }
    // Collect all group names: walk top_level_groups.
    function collect(tree) {
      Object.keys(tree).forEach(function (k) {
        names[k] = true;
        _walkSub(tree[k].subgroups, k);
      });
    }
    function _walkSub(sub, prefix) {
      Object.keys(sub).forEach(function (k) {
        names[prefix + ' > ' + k] = true;
        _walkSub(sub[k].subgroups, prefix + ' > ' + k);
      });
    }
    collect(tree);
    return Object.keys(names);
  }

  /** Check whether `query` matches a label or any of its ancestor group names. */
  function _matches(labelName, groupNames, query) {
    if (!query) return true;
    var low = labelName.toLowerCase();
    if (low.indexOf(query) !== -1) return true;
    return groupNames.some(function (g) { return g.toLowerCase().indexOf(query) !== -1; });
  }

  /**
   * Build the filtered view for rendering.
   * @returns {{available: object, accepted: object, availableCount: number, acceptedCount: number}}
   *   available/accepted are {groupName: [labels]} nested by top-level group.
   */
  function filterState(state) {
    var accepted = state.accepted;
    var query = state.search;
    var tree = state.groupsTree;

    // Build label -> top-level group name mapping from the tree.
    var labelGroup = {};
    function walk(tree, pathPrefix) {
      Object.keys(tree).forEach(function (k) {
        var node = tree[k];
        // Direct labels of this group belong under group `k`.
        node.labels.forEach(function (l) { labelGroup[l.toLowerCase()] = pathPrefix || k; });
        // Subgroups
        walk(node.subgroups, (pathPrefix ? pathPrefix + ' > ' : '') + k);
        // Labels nested deeper in subgroups — they still show under their direct group.
        // The recursive walk handles this naturally via pathPrefix.
      });
    }
    walk(tree, '');

    // All group names for search matching
    var allGroupNames = _groupNames(tree);

    function buildFiltered(set) {
      var result = {};
      var count = 0;
      Object.keys(tree).forEach(function (top) {
        var node = tree[top];
        var labels = node.labels.filter(function (l) {
          return set.has(l.toLowerCase()) && _matches(l, [top], query);
        });
        var subgroups = _filterSub(node.subgroups, set, query);
        if (labels.length > 0 || Object.keys(subgroups).length > 0) {
          result[top] = { labels: labels, subgroups: subgroups };
          count += labels.length + _countSub(subgroups);
        }
      });
      return { groups: result, count: count };
    }

    var availableSet = new Set(state.allLabels.map(function (l) { return l.toLowerCase(); }));
    accepted.forEach(function (l) { availableSet.delete(l); });

    var available = buildFiltered(availableSet);
    var acceptedFiltered = buildFiltered(accepted);
    return {
      available: available.groups,
      accepted: acceptedFiltered.groups,
      availableCount: available.count,
      acceptedCount: acceptedFiltered.count,
    };
  }

  function _filterSub(subgroups, set, query) {
    var result = {};
    Object.keys(subgroups).forEach(function (k) {
      var node = subgroups[k];
      var labels = node.labels.filter(function (l) {
        return set.has(l.toLowerCase()) && _matches(l, [], query);
      });
      var deeper = _filterSub(node.subgroups, set, query);
      if (labels.length > 0 || Object.keys(deeper).length > 0) {
        result[k] = { labels: labels, subgroups: deeper };
      }
    });
    return result;
  }

  function _countSub(subgroups) {
    var n = 0;
    Object.keys(subgroups).forEach(function (k) {
      n += subgroups[k].labels.length + _countSub(subgroups[k].subgroups);
    });
    return n;
  }

  /** "N/M values accepted" counter string. */
  function getCounter(state) {
    return state.accepted.size + '/' + state.allLabels.length + ' values accepted';
  }

  /** Accepted values sorted (source of truth for saving). */
  function getAcceptedValues(state) {
    return Array.from(state.accepted).sort();
  }

  return {
    createState: createState,
    accept: accept,
    remove: remove,
    selectAll: selectAll,
    removeAll: removeAll,
    setSearch: setSearch,
    filterState: filterState,
    getCounter: getCounter,
    getAcceptedValues: getAcceptedValues,
  };
});
