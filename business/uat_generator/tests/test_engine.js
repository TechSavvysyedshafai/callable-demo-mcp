// Run with: node business/uat_generator/tests/test_engine.js
const assert = require('assert');
const E = require('../engine.js');

const MOTOR = `Feature: Motor insurance quote
Default: Quote issued at standard premium

Field: Driver age | number | 18..75 | required
Field: Years licence held | number | 0..57 | required
Field: Vehicle value | number | 1000..150000 | step 500 | required
Field: Claims in last 3 years | number | 0..10 | required
Field: Cover type | choice | Comprehensive, Third party fire and theft, Third party only | required
Field: Registration number | text | max 8 | required

Rule R1: Claims in last 3 years > 2 => Decline: claims history outside appetite
Rule R2: Driver age < 25 AND Cover type = Comprehensive => Apply 20% young driver loading
Rule R3: Vehicle value >= 100000 => Refer to underwriter: high value vehicle
Rule R4: Years licence held < 1 => Refer to underwriter: new driver`;

const HEALTH = `Feature: Health claim submission
Default: Claim accepted for assessment
Field: Claim amount | number | 1..500000 | required
Field: Days since treatment | number | 0..365 | required
Field: Policy status | choice | Active, Lapsed, Cancelled | required
Field: Pre-authorisation obtained | yesno | required
Rule C1: Policy status != Active => Reject: policy not in force
Rule C2: Days since treatment > 90 => Reject: submitted after 90-day deadline
Rule C3: Claim amount > 50000 AND Pre-authorisation obtained = No => Refer: pre-authorisation required above 50,000`;

let n = 0;
function test(name, fn) { fn(); n++; console.log('ok  ' + name); }

test('parses the motor spec without errors', () => {
  const s = E.parse(MOTOR);
  assert.deepStrictEqual(s.errors, []);
  assert.strictEqual(s.fields.length, 6);
  assert.strictEqual(s.rules.length, 4);
  assert.strictEqual(s.fields[2].step, 500);
});

test('standard case fires no rule and gets the default outcome', () => {
  const s = E.parse(MOTOR);
  const g = E.generate(s);
  const happy = g.cases[0];
  assert.strictEqual(happy.technique, 'Happy path');
  assert.strictEqual(happy.expected, 'Quote issued at standard premium');
  assert.deepStrictEqual(E.evaluate(s, g.base).fired, []);
});

test('boundary values for driver age are 17, 18, 19, 74, 75, 76', () => {
  const g = E.generate(E.parse(MOTOR));
  const ages = g.cases.filter(c => c.technique === 'Boundary value' && c.covers.startsWith('Field Driver age')).map(c => c.data['Driver age']);
  assert.deepStrictEqual(ages.sort((a, b) => a - b), [17, 18, 19, 74, 75, 76]);
  const below = g.cases.find(c => c.data['Driver age'] === 17);
  assert.match(below.expected, /Driver age must be between 18 and 75/);
});

test('step is respected for vehicle value boundaries', () => {
  const g = E.generate(E.parse(MOTOR));
  const vals = g.cases.filter(c => c.covers.startsWith('Field Vehicle value') && c.technique === 'Boundary value').map(c => c.data['Vehicle value']);
  assert.ok(vals.includes(500) && vals.includes(1000) && vals.includes(1500) && vals.includes(150500));
});

test('each rule gets a "fires" case at the edge and a "does not fire" case per condition', () => {
  const g = E.generate(E.parse(MOTOR));
  const r2 = g.cases.filter(c => c.covers.includes('Rule R2'));
  const fires = r2.find(c => c.title.startsWith('R2 applies'));
  assert.ok(fires, 'R2 fires case');
  assert.strictEqual(fires.data['Driver age'], 24);
  assert.strictEqual(fires.data['Cover type'], 'Comprehensive');
  assert.match(fires.expected, /young driver loading \[R2\]/);
  const ageOff = r2.find(c => c.title.includes('Driver age is 25'));
  assert.ok(ageOff, 'age 25 stops R2');
  assert.doesNotMatch(ageOff.expected, /\[R2\]/);
  const coverOff = r2.find(c => c.title.includes('does not apply when Cover type'));
  assert.ok(coverOff, 'other cover stops R2');
  const r1 = g.cases.find(c => c.title.startsWith('R1 applies'));
  assert.strictEqual(r1.data['Claims in last 3 years'], 3);
});

test('overlapping rules become requirement questions', () => {
  const g = E.generate(E.parse(MOTOR));
  const overlaps = g.questions.filter(q => q.kind === 'Overlap').map(q => q.text);
  assert.ok(overlaps.some(t => t.includes('R1 and R3')), 'decline vs refer');
  assert.ok(overlaps.some(t => t.includes('R2 and R4')), 'young driver vs new driver');
  assert.strictEqual(g.questions[0].kind, 'Priority', 'many overlaps get one priority question first');
});

test('a rule outside the allowed range is reported as never applying', () => {
  const s = E.parse(MOTOR + '\nRule R5: Claims in last 3 years > 10 => Decline');
  const g = E.generate(s);
  assert.ok(g.questions.some(q => q.kind === 'Never applies' && q.text.includes('R5')));
  assert.ok(!g.cases.some(c => c.covers.includes('Rule R5')));
});

test('health spec: != on choice, yes/no fields, three-way rule coverage', () => {
  const s = E.parse(HEALTH);
  assert.deepStrictEqual(s.errors, []);
  const g = E.generate(s);
  assert.strictEqual(g.base['Policy status'], 'Active');
  assert.strictEqual(g.cases[0].expected, 'Claim accepted for assessment');
  const c3 = g.cases.filter(c => c.covers.includes('Rule C3'));
  assert.ok(c3.length >= 3, 'fires + two conditions off');
  const fires = c3.find(c => c.title.startsWith('C3 applies'));
  assert.strictEqual(fires.data['Claim amount'], 50001);
  assert.strictEqual(fires.data['Pre-authorisation obtained'], 'No');
  const c1 = g.cases.find(c => c.title.startsWith('C1 applies'));
  assert.notStrictEqual(c1.data['Policy status'], 'Active');
});

test('parse errors are clear and do not stop generation', () => {
  const s = E.parse('Feature: X\nField: Age | numbr | 1..5\nField: Plan | choice | Gold, Silver\nRule P1: Plan = Bronze => Upgrade\nRule P2: Age > 1 OR Plan = Gold => Y\nhello');
  const msgs = s.errors.map(e => e.message).join('\n');
  assert.match(msgs, /Unknown type "numbr"/);
  assert.match(msgs, /"Bronze" is not one of the options/);
  assert.match(msgs, /OR is not supported/);
  assert.match(msgs, /Not understood/);
  const g = E.generate(s);
  assert.ok(g.cases.length > 0);
  assert.ok(g.questions.some(q => q.kind === 'Missing default'));
});

test('text max length gives accept and reject cases', () => {
  const g = E.generate(E.parse(MOTOR));
  const reg = g.cases.filter(c => c.covers.startsWith('Field Registration number') && c.technique === 'Boundary value');
  assert.deepStrictEqual(reg.map(c => c.data['Registration number'].length).sort(), [8, 9]);
  assert.match(reg.find(c => c.data['Registration number'].length === 9).expected, /at most 8 characters/);
});

test('exports escape quotes, commas and pipes', () => {
  const cases = [{ id: 'TC-001', title: 'A "quoted", title', technique: 'x', covers: 'a|b', dataText: 'k = v; k2 = v2', steps: 's', expected: 'e', priority: 'High' }];
  const csv = E.toCSV(cases).split('\n')[1];
  assert.ok(csv.startsWith('TC-001,"A ""quoted"", title"'));
  assert.ok(E.toMarkdown(cases).includes('a\\|b'));
  assert.strictEqual(E.toTSV(cases).split('\n')[1].split('\t').length, 8);
});

test('ids are sequential and test data is unique', () => {
  const g = E.generate(E.parse(MOTOR));
  g.cases.forEach((c, i) => assert.strictEqual(c.id, 'TC-' + String(i + 1).padStart(3, '0')));
  const keys = new Set(g.cases.map(c => c.dataText));
  assert.strictEqual(keys.size, g.cases.length);
});

console.log(`\n${n} tests passed`);
