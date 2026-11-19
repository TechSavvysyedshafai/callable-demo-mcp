/* UAT Test Case Generator: engine.
 * Turns a plain-text requirement (fields + business rules) into UAT test cases
 * using standard QA techniques: happy path, boundary value analysis, equivalence
 * classes, required-field checks and decision-rule coverage (each rule fires;
 * each condition on its own stops it firing). Also lists requirement questions
 * (rules that can never fire, rules that overlap, missing ranges).
 * No AI calls: every test case can be traced back to a line of the spec.
 * Works in the browser (window.UATEngine) and in Node (module.exports).
 */
(function (root) {
  'use strict';

  var NUMBER_TYPES = { number: 1, money: 1, amount: 1, integer: 1, int: 1, decimal: 1, percent: 1 };
  var CHOICE_TYPES = { choice: 1, list: 1, dropdown: 1, option: 1, options: 1 };
  var YESNO_TYPES = { yesno: 1, 'yes/no': 1, boolean: 1, bool: 1, checkbox: 1 };
  var TEXT_TYPES = { text: 1, string: 1, 'free text': 1 };
  var NUM = /^-?\d+(?:\.\d+)?$/;

  function norm(s) { return String(s == null ? '' : s).trim().toLowerCase(); }
  function decimalsOf(step) { var p = String(step).split('.'); return p[1] ? p[1].length : 0; }

  // ---------- parsing ----------
  function parse(text) {
    var spec = { feature: '', defaultOutcome: '', fields: [], rules: [], errors: [] };
    var byName = {};
    var lines = String(text || '').split(/\r?\n/);
    var pendingRules = [];
    lines.forEach(function (raw, i) {
      var line = raw.trim();
      var n = i + 1;
      if (!line || line.charAt(0) === '#') return;
      var m;
      if ((m = line.match(/^feature\s*:\s*(.+)$/i))) { spec.feature = m[1].trim(); return; }
      if ((m = line.match(/^default\s*:\s*(.+)$/i))) { spec.defaultOutcome = m[1].trim(); return; }
      if ((m = line.match(/^field\s*:\s*(.+)$/i))) {
        var f = parseField(m[1], n, spec.errors);
        if (f) {
          if (byName[norm(f.name)]) { spec.errors.push({ line: n, message: 'Field "' + f.name + '" is defined twice.' }); return; }
          byName[norm(f.name)] = f; spec.fields.push(f);
        }
        return;
      }
      if ((m = line.match(/^rule\s+([^:]+?)\s*:\s*(.+?)\s*=>\s*(.+)$/i))) {
        pendingRules.push({ id: m[1].trim(), when: m[2], outcome: m[3].trim(), line: n });
        return;
      }
      if (/^rule\b/i.test(line)) {
        spec.errors.push({ line: n, message: 'Rule lines look like: Rule R1: Field > 10 AND Other = Yes => Outcome' });
        return;
      }
      spec.errors.push({ line: n, message: 'Not understood. Lines start with Feature:, Default:, Field: or Rule.' });
    });
    pendingRules.forEach(function (r) {
      var rule = parseRule(r, byName, spec.errors);
      if (rule) spec.rules.push(rule);
    });
    return spec;
  }

  function parseField(body, n, errors) {
    var parts = body.split('|').map(function (s) { return s.trim(); }).filter(function (s) { return s !== ''; });
    if (parts.length < 2) { errors.push({ line: n, message: 'Field needs a name and a type, e.g. Field: Driver age | number | 18..75 | required' }); return null; }
    var name = parts[0];
    var t = norm(parts[1]);
    var f = { name: name, type: null, required: false, min: null, max: null, step: 1, maxLength: null, options: [], line: n };
    if (NUMBER_TYPES[t]) { f.type = 'number'; if (t === 'decimal') f.step = 0.01; }
    else if (CHOICE_TYPES[t]) f.type = 'choice';
    else if (YESNO_TYPES[t]) { f.type = 'yesno'; f.options = ['Yes', 'No']; }
    else if (TEXT_TYPES[t]) f.type = 'text';
    else { errors.push({ line: n, message: 'Unknown type "' + parts[1] + '". Use number, choice, yesno or text.' }); return null; }
    parts.slice(2).forEach(function (p) {
      var m, lp = norm(p);
      if (lp === 'required' || lp === 'mandatory') f.required = true;
      else if (lp === 'optional') f.required = false;
      else if ((m = p.match(/^(-?\d+(?:\.\d+)?)\s*\.\.\s*(-?\d+(?:\.\d+)?)$/))) { f.min = +m[1]; f.max = +m[2]; }
      else if ((m = p.match(/^min\s+(-?\d+(?:\.\d+)?)$/i))) f.min = +m[1];
      else if ((m = p.match(/^max\s+(-?\d+(?:\.\d+)?)$/i))) { if (f.type === 'text') f.maxLength = Math.floor(+m[1]); else f.max = +m[1]; }
      else if ((m = p.match(/^step\s+(\d+(?:\.\d+)?)$/i)) && +m[1] > 0) f.step = +m[1];
      else if (f.type === 'choice') f.options = p.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
      else errors.push({ line: n, message: 'Did not understand "' + p + '" for field ' + name + '.' });
    });
    if (f.type === 'choice' && f.options.length < 2) errors.push({ line: n, message: 'Choice field ' + name + ' needs at least two options, separated by commas.' });
    if (f.type === 'number' && f.min != null && f.max != null && f.min > f.max) errors.push({ line: n, message: 'Field ' + name + ': minimum is larger than maximum.' });
    return f;
  }

  var OPS = [[/\s+is\s+not\s+/i, '!='], [/\s*>=\s*/, '>='], [/\s*<=\s*/, '<='], [/\s*!=\s*/, '!='], [/\s*>\s*/, '>'], [/\s*<\s*/, '<'], [/\s*=\s*/, '='], [/\s+is\s+/i, '=']];

  function parseRule(r, byName, errors) {
    if (/\s+or\s+/i.test(r.when)) { errors.push({ line: r.line, message: 'Rule ' + r.id + ': OR is not supported. Write it as two rules with the same outcome.' }); return null; }
    var conds = [];
    var ok = true;
    r.when.split(/\s+and\s+/i).forEach(function (c) {
      var found = null;
      for (var k = 0; k < OPS.length && !found; k++) {
        var m = c.match(OPS[k][0]);
        if (m) found = { left: c.slice(0, m.index).trim(), op: OPS[k][1], right: c.slice(m.index + m[0].length).trim() };
      }
      if (!found || !found.left || !found.right) { errors.push({ line: r.line, message: 'Rule ' + r.id + ': could not read the condition "' + c.trim() + '".' }); ok = false; return; }
      var f = byName[norm(found.left)];
      if (!f) { errors.push({ line: r.line, message: 'Rule ' + r.id + ': there is no field called "' + found.left + '".' }); ok = false; return; }
      var value = found.right;
      if (f.type === 'number') {
        if (!NUM.test(value.replace(/,/g, ''))) { errors.push({ line: r.line, message: 'Rule ' + r.id + ': ' + f.name + ' is a number, so "' + value + '" must be a number.' }); ok = false; return; }
        value = +value.replace(/,/g, '');
      } else {
        if (/^(>=|<=|>|<)$/.test(found.op)) { errors.push({ line: r.line, message: 'Rule ' + r.id + ': ' + f.name + ' is not a number, so use = or != only.' }); ok = false; return; }
        if (f.options.length) {
          var match = f.options.filter(function (o) { return norm(o) === norm(value); })[0];
          if (!match) { errors.push({ line: r.line, message: 'Rule ' + r.id + ': "' + value + '" is not one of the options for ' + f.name + ' (' + f.options.join(', ') + ').' }); ok = false; return; }
          value = match;
        }
      }
      conds.push({ field: f, op: found.op, value: value });
    });
    if (!ok) return null;
    return { id: r.id, conds: conds, outcome: r.outcome, line: r.line };
  }

  // ---------- evaluation ----------
  function condHolds(c, v) {
    if (v === '' || v == null) return false;
    if (c.field.type === 'number') {
      var x = +v; if (isNaN(x)) return false;
      switch (c.op) { case '>': return x > c.value; case '>=': return x >= c.value; case '<': return x < c.value; case '<=': return x <= c.value; case '=': return x === c.value; case '!=': return x !== c.value; }
      return false;
    }
    return c.op === '=' ? norm(v) === norm(c.value) : norm(v) !== norm(c.value);
  }

  function fmt(f, v) {
    if (v === '' || v == null) return '(blank)';
    if (f.type === 'number' && typeof v === 'number') return String(+v.toFixed(decimalsOf(f.step)));
    return String(v);
  }

  function validate(spec, record) {
    var errs = [];
    spec.fields.forEach(function (f) {
      var v = record[f.name];
      if (v === '' || v == null) { if (f.required) errs.push(f.name + ' is required'); return; }
      if (f.type === 'number') {
        if (typeof v !== 'number' && !NUM.test(String(v))) { errs.push(f.name + ' must be a number'); return; }
        var x = +v;
        if (f.min != null && f.max != null && (x < f.min || x > f.max)) errs.push(f.name + ' must be between ' + fmt(f, f.min) + ' and ' + fmt(f, f.max));
        else if (f.min != null && x < f.min) errs.push(f.name + ' must be at least ' + fmt(f, f.min));
        else if (f.max != null && x > f.max) errs.push(f.name + ' must be at most ' + fmt(f, f.max));
      } else if (f.options.length) {
        if (!f.options.some(function (o) { return norm(o) === norm(v); })) errs.push(f.name + ' must be one of: ' + f.options.join(', '));
      } else if (f.type === 'text' && f.maxLength != null && String(v).length > f.maxLength) {
        errs.push(f.name + ' must be at most ' + f.maxLength + ' characters');
      }
    });
    return errs;
  }

  function evaluate(spec, record) {
    var errors = validate(spec, record);
    if (errors.length) return { errors: errors, fired: [] };
    var fired = spec.rules.filter(function (r) { return r.conds.every(function (c) { return condHolds(c, record[c.field.name]); }); });
    return { errors: [], fired: fired };
  }

  function expectedText(spec, result) {
    if (result.errors.length) return 'Rejected at input with message: ' + result.errors.join('; ') + '. No outcome is produced.';
    if (!result.fired.length) return spec.defaultOutcome || '(No rule applies. The requirement does not say what happens: see Requirement questions.)';
    return result.fired.map(function (r) { return r.outcome + ' [' + r.id + ']'; }).join('; ');
  }

  // ---------- value choice ----------
  function inRange(f, v) { return (f.min == null || v >= f.min) && (f.max == null || v <= f.max); }
  function rnd(f, v) { return +(+v).toFixed(decimalsOf(f.step)); }
  function snap(f, v) { var base = f.min != null ? f.min : 0; return rnd(f, base + Math.round((v - base) / f.step) * f.step); }

  function candidates(spec, f) {
    if (f.type === 'number') {
      var set = [];
      var add = function (v) { v = rnd(f, v); if (inRange(f, v) && set.indexOf(v) < 0) set.push(v); };
      if (f.min != null && f.max != null) { add(snap(f, (f.min + f.max) / 2)); add(snap(f, f.min + (f.max - f.min) / 4)); add(snap(f, f.min + 3 * (f.max - f.min) / 4)); }
      if (f.min != null) add(f.min);
      if (f.max != null) add(f.max);
      spec.rules.forEach(function (r) { r.conds.forEach(function (c) { if (c.field === f) { add(c.value - f.step); add(c.value); add(c.value + f.step); } }); });
      if (!set.length) [100, 10, 1, 1000, 0].forEach(add);
      return set;
    }
    if (f.options.length) return f.options.slice();
    var vals = [];
    spec.rules.forEach(function (r) { r.conds.forEach(function (c) { if (c.field === f && vals.indexOf(c.value) < 0) vals.push(c.value); }); });
    vals.push(sampleText(f, null));
    return vals;
  }

  function sampleText(f, len) {
    var src = 'TEST0123456789ABCDEFGHJKLMNPQRSTUVWXYZ';
    if (len == null) len = f.maxLength != null ? Math.min(6, f.maxLength) : 6;
    var s = ''; while (s.length < len) s += src; return s.slice(0, len);
  }

  function condsOn(spec, f) {
    var out = [];
    spec.rules.forEach(function (r) { r.conds.forEach(function (c) { if (c.field === f) out.push(c); }); });
    return out;
  }

  function baseRecord(spec) {
    var rec = {};
    spec.fields.forEach(function (f) {
      var cs = condsOn(spec, f);
      var cands = candidates(spec, f);
      var pick = cands.filter(function (v) { return cs.every(function (c) { return !condHolds(c, v); }); })[0];
      rec[f.name] = pick != null ? pick : cands[0];
    });
    return rec;
  }

  // value for field f satisfying `must` (all true) and violating `mustNot` (all false), nearest to `near`
  function findValue(spec, f, must, mustNot, near) {
    var cands = candidates(spec, f).filter(function (v) {
      return must.every(function (c) { return condHolds(c, v); }) && mustNot.every(function (c) { return !condHolds(c, v); });
    });
    if (!cands.length) return { ok: false };
    if (f.type === 'number' && typeof near === 'number') cands.sort(function (a, b) { return Math.abs(a - near) - Math.abs(b - near); });
    return { ok: true, value: cands[0] };
  }

  // record where every condition of the rule holds (null if impossible within the allowed values)
  function ruleTrueRecord(spec, rule, base) {
    var rec = clone(base);
    var fields = uniqueFields(rule);
    for (var i = 0; i < fields.length; i++) {
      var f = fields[i];
      var must = rule.conds.filter(function (c) { return c.field === f; });
      var res = findValue(spec, f, must, [], must[0].value);
      if (!res.ok) return null;
      rec[f.name] = res.value;
    }
    return rec;
  }

  function uniqueFields(rule) {
    var out = []; rule.conds.forEach(function (c) { if (out.indexOf(c.field) < 0) out.push(c.field); }); return out;
  }
  function clone(o) { var r = {}; for (var k in o) r[k] = o[k]; return r; }

  // ---------- generation ----------
  function generate(spec) {
    var cases = [];
    var questions = [];
    var seen = {};
    var base = baseRecord(spec);
    var feature = spec.feature || 'the feature';

    function key(rec) { return spec.fields.map(function (f) { return f.name + '=' + rec[f.name]; }).join('|'); }
    function addCase(c) {
      var k = key(c.data);
      if (seen[k]) { var prev = seen[k]; if (prev.covers.indexOf(c.covers) < 0) prev.covers += '; ' + c.covers; return; }
      var result = evaluate(spec, c.data);
      c.expected = expectedText(spec, result);
      c.outcomeKind = result.errors.length ? 'reject' : (result.fired.length ? 'rule' : 'default');
      seen[k] = c;
      cases.push(c);
    }

    // 1. happy path
    addCase({ title: 'Standard valid case', technique: 'Happy path', covers: 'All fields', data: base, focus: [], priority: 'High' });

    // 2. decision rules: rule fires, and each condition on its own stops it firing
    spec.rules.forEach(function (rule) {
      var t = ruleTrueRecord(spec, rule, base);
      if (!t) {
        questions.push({ kind: 'Never applies', text: 'Rule ' + rule.id + ' can never apply with the allowed values (' + rule.conds.map(condLabel).join(' and ') + '). Is a limit or the rule wrong?' });
        return;
      }
      addCase({
        title: rule.id + ' applies: ' + rule.conds.map(function (c) { return c.field.name + ' ' + fmt(c.field, t[c.field.name]); }).join(', '),
        technique: 'Decision rule', covers: 'Rule ' + rule.id, data: t, focus: uniqueFields(rule).map(function (f) { return f.name; }), priority: 'High'
      });
      rule.conds.forEach(function (c) {
        var f = c.field;
        var others = rule.conds.filter(function (o) { return o !== c && o.field === f; });
        var res = findValue(spec, f, others, [c], c.value);
        if (!res.ok) return;
        var rec = clone(t); rec[f.name] = res.value;
        addCase({
          title: rule.id + ' does not apply when ' + f.name + ' is ' + fmt(f, res.value) + (rule.conds.length > 1 ? ' (other conditions met)' : ''),
          technique: 'Decision rule', covers: 'Rule ' + rule.id + ' (' + condLabel(c) + ')', data: rec, focus: [f.name], priority: 'High'
        });
      });
    });

    // 3. fields: boundaries, classes, required, format
    spec.fields.forEach(function (f) {
      var v = function (val) { var r = clone(base); r[f.name] = val; return r; };
      if (f.type === 'number') {
        var s = f.step;
        if (f.min != null) {
          addCase({ title: f.name + ' just below minimum (' + fmt(f, rnd(f, f.min - s)) + ') is rejected', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(rnd(f, f.min - s)), focus: [f.name], priority: 'Medium' });
          addCase({ title: f.name + ' at minimum (' + fmt(f, f.min) + ') is accepted', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(f.min), focus: [f.name], priority: 'Medium' });
          if (f.max == null || rnd(f, f.min + s) < f.max) addCase({ title: f.name + ' just above minimum (' + fmt(f, rnd(f, f.min + s)) + ') is accepted', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(rnd(f, f.min + s)), focus: [f.name], priority: 'Low' });
        }
        if (f.max != null) {
          if (f.min == null || rnd(f, f.max - s) > f.min) addCase({ title: f.name + ' just below maximum (' + fmt(f, rnd(f, f.max - s)) + ') is accepted', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(rnd(f, f.max - s)), focus: [f.name], priority: 'Low' });
          addCase({ title: f.name + ' at maximum (' + fmt(f, f.max) + ') is accepted', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(f.max), focus: [f.name], priority: 'Medium' });
          addCase({ title: f.name + ' just above maximum (' + fmt(f, rnd(f, f.max + s)) + ') is rejected', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(rnd(f, f.max + s)), focus: [f.name], priority: 'Medium' });
        }
        if (f.min == null || f.max == null) questions.push({ kind: 'Missing limit', text: 'What are the ' + (f.min == null && f.max == null ? 'minimum and maximum' : f.min == null ? 'minimum' : 'maximum') + ' allowed values for ' + f.name + '?' });
        addCase({ title: f.name + ' with letters ("abc") is rejected', technique: 'Invalid format', covers: 'Field ' + f.name, data: v('abc'), focus: [f.name], priority: 'Low' });
      } else if (f.options.length) {
        f.options.forEach(function (o) {
          addCase({ title: f.name + ' "' + o + '" is accepted', technique: 'Equivalence class', covers: 'Field ' + f.name, data: v(o), focus: [f.name], priority: 'Low' });
        });
        addCase({ title: f.name + ' with a value not in the list is rejected', technique: 'Equivalence class', covers: 'Field ' + f.name, data: v('Not a listed value'), focus: [f.name], priority: 'Medium' });
      } else if (f.type === 'text' && f.maxLength != null) {
        addCase({ title: f.name + ' at the maximum length (' + f.maxLength + ' characters) is accepted', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(sampleText(f, f.maxLength)), focus: [f.name], priority: 'Medium' });
        addCase({ title: f.name + ' one character too long (' + (f.maxLength + 1) + ') is rejected', technique: 'Boundary value', covers: 'Field ' + f.name, data: v(sampleText(f, f.maxLength + 1)), focus: [f.name], priority: 'Medium' });
      }
      if (f.required) addCase({ title: f.name + ' left blank is rejected', technique: 'Required field', covers: 'Field ' + f.name, data: v(''), focus: [f.name], priority: 'Medium' });
    });

    // 4. requirement questions: overlapping rules, missing default
    for (var i = 0; i < spec.rules.length; i++) {
      for (var j = i + 1; j < spec.rules.length; j++) {
        var a = spec.rules[i], b = spec.rules[j];
        var ex = overlapExample(spec, a, b, base);
        if (ex && norm(a.outcome) !== norm(b.outcome)) {
          questions.push({ kind: 'Overlap', text: 'Rules ' + a.id + ' and ' + b.id + ' can apply to the same case (for example ' + uniqueFields(a).concat(uniqueFields(b)).filter(function (f, k, arr) { return arr.indexOf(f) === k; }).map(function (f) { return f.name + ' ' + fmt(f, ex[f.name]); }).join(', ') + '). Should both outcomes happen, or does one win?' });
        }
      }
    }
    var nOverlap = questions.filter(function (q) { return q.kind === 'Overlap'; }).length;
    if (nOverlap >= 3) questions.unshift({ kind: 'Priority', text: nOverlap + ' pairs of rules can apply to the same case. Agree one priority order with the business (for example: Decline, then Refer, then Loading) and add it to the requirement.' });
    if (!spec.defaultOutcome) questions.push({ kind: 'Missing default', text: 'What should happen when no rule applies? Add a line like "Default: Quote issued at standard premium".' });

    cases.forEach(function (c, k) {
      c.id = 'TC-' + String(k + 1).padStart(3, '0');
      c.steps = '1. Open ' + feature + '. 2. Enter the test data. 3. Submit.';
      c.dataText = spec.fields.map(function (f) { return f.name + ' = ' + fmt(f, c.data[f.name]); }).join('; ');
    });
    return { cases: cases, questions: questions, base: base };
  }

  function overlapExample(spec, a, b, base) {
    var orders = [[a, b], [b, a]];
    for (var k = 0; k < orders.length; k++) {
      var first = ruleTrueRecord(spec, orders[k][0], base);
      if (!first) return null;
      var both = ruleTrueRecord(spec, orders[k][1], first);
      if (!both) continue;
      var fired = evaluate(spec, both).fired;
      if (fired.indexOf(a) >= 0 && fired.indexOf(b) >= 0) return both;
    }
    // combined search: satisfy both rules' conditions on shared fields together
    var rec = clone(base), conds = a.conds.concat(b.conds);
    var fields = []; conds.forEach(function (c) { if (fields.indexOf(c.field) < 0) fields.push(c.field); });
    for (var i = 0; i < fields.length; i++) {
      var f = fields[i];
      var must = conds.filter(function (c) { return c.field === f; });
      var res = findValue(spec, f, must, [], must[0].value);
      if (!res.ok) return null;
      rec[f.name] = res.value;
    }
    var fr = evaluate(spec, rec).fired;
    return fr.indexOf(a) >= 0 && fr.indexOf(b) >= 0 ? rec : null;
  }

  function condLabel(c) { return c.field.name + ' ' + c.op + ' ' + fmt(c.field, c.value); }

  // ---------- export ----------
  var COLS = ['ID', 'Title', 'Technique', 'Covers', 'Test data', 'Steps', 'Expected result', 'Priority'];
  function row(c) { return [c.id, c.title, c.technique, c.covers, c.dataText, c.steps, c.expected, c.priority]; }

  function toCSV(cases) {
    var esc = function (s) { s = String(s); return /[",\n;]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    return [COLS].concat(cases.map(row)).map(function (r) { return r.map(esc).join(','); }).join('\n');
  }
  function toTSV(cases) {
    var clean = function (s) { return String(s).replace(/[\t\n]/g, ' '); };
    return [COLS].concat(cases.map(row)).map(function (r) { return r.map(clean).join('\t'); }).join('\n');
  }
  function toMarkdown(cases) {
    var esc = function (s) { return String(s).replace(/\|/g, '\\|'); };
    var out = ['| ' + COLS.join(' | ') + ' |', '|' + COLS.map(function () { return '---'; }).join('|') + '|'];
    cases.forEach(function (c) { out.push('| ' + row(c).map(esc).join(' | ') + ' |'); });
    return out.join('\n');
  }

  var api = { parse: parse, generate: generate, evaluate: evaluate, validate: validate, toCSV: toCSV, toTSV: toTSV, toMarkdown: toMarkdown };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.UATEngine = api;
})(this);
