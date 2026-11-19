# UAT Test Case Generator

Write a requirement's fields and business rules in plain text. The tool produces a traceable UAT pack and a list of questions to take back to the business. It makes no AI calls, so every test case traces to a line of the requirement.

## What it generates

| Technique | What you get |
|---|---|
| Happy path | One valid case where no rule applies, with the default outcome |
| Decision rule | Each rule at the exact point it starts to apply, then each of its conditions switched off on its own |
| Boundary value | Minimum and maximum, plus one step either side, for numbers and text length |
| Equivalence class | Each listed option accepted, one value not in the list rejected |
| Required field | Each required field left blank |
| Invalid format | Letters typed into a number field |

Expected results are worked out from the rules, including when a boundary value also triggers a rule. Identical test data is merged into one case, and its "Covers" column lists everything that case covers.

**Requirement questions** flag rules that can never apply within the allowed values, pairs of rules that can apply to the same case (so a priority order is needed), missing limits, and a missing default outcome.

## Requirement format

```
Feature: Motor insurance quote
Default: Quote issued at standard premium

Field: Driver age | number | 18..75 | required
Field: Vehicle value | number | 1000..150000 | step 500 | required
Field: Cover type | choice | Comprehensive, Third party only | required
Field: Smoker | yesno | required
Field: Registration number | text | max 8 | required

Rule R1: Driver age < 25 AND Cover type = Comprehensive => Apply 20% young driver loading
```

Conditions use `>`, `>=`, `<`, `<=`, `=` and `!=`, joined with AND. For OR, write two rules with the same outcome.

## Known limits

- Dates, and rules that compare two fields (such as "years licence held must be less than age minus 17"), are not supported yet.
- The tool trusts the rules as written. A wrong rule gives a wrong expected result, so review the requirement questions first.

## Files

- `engine.js`: parsing, test generation, rule evaluation and export (CSV, Excel-ready tab-separated text, Markdown). Works in the browser and in Node.
- `index.html`: the page (three insurance examples: motor quote, health claim, term life).
- `tests/test_engine.js`: run with `node business/uat_generator/tests/test_engine.js`.
