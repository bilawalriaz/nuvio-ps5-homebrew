# Writing

## Project rules

Use short, direct English for instructions and explanations. Use one term for
each component or action, and take the terms from [Glossary](GLOSSARY.md). Keep
technical identifiers exact.

Use these rules for procedures:

- Start each action with a direct verb.
- Give one instruction per sentence.
- Keep instruction sentences within 20 words when possible.
- Put conditions before the actions they restrict.
- Use numbered steps for an ordered procedure.
- State the expected response and the next action after a failure.

Keep descriptive sentences within 25 words when possible. Keep each paragraph on
one topic. Use active voice when you can name the actor. Prefer simple tenses and
ordinary verbs. Cut sales claims, filler, staged introductions and repeated
conclusions. Avoid semicolons and decorative emphasis.

Keep supported uncertainty intact. For example, a possible source failure must
stay possible after an edit. Preserve firmware limits, private-state rules and
required preconditions. When a shorter sentence loses precision, keep the
precise sentence.

## House style

- Use commas, colons or parentheses instead of em dashes and en dashes.
- Use straight quotes, not curly quotes.
- Prefer `is` and `has` to `serves as`, `boasts` and `features`.
- Cut `It is worth noting`, `Importantly` and `Notably`. Let the sentence stand.
- Avoid `It is not just X, it is Y` and other forced contrasts.
- Name the source when you cite one. Drop vague claims about experts or reports.

## Applied guides

The documentation uses the structural rules from the
[ASD-STE100 skill](https://github.com/danyuchn/asd-ste100-skill/tree/7d4a135a199a5d7447c4886bcd7ffe742a627bc9).
Procedures use its strict approach, and reference pages use its simplified prose
approach.

The final prose review also uses
[Humanizer](https://github.com/blader/humanizer/tree/225a6f39ac85f76ee48dbad772ea4abe4ed6c9d8).
Technical documentation keeps a neutral voice and supported facts. The review
removes unnecessary contrasts, repeated closers and generic claims.

Both references use fixed revisions retrieved on 2026-10-01. The guides do not
replace project policy or implementation evidence. This project does not
reproduce the official ASD dictionary and does not claim certified ASD-STE100
compliance.

## Checks and review

`make docs-check` checks local links and the required pages. It also runs the
pinned structural STE linter, which checks a 25-word sentence limit for
descriptions. The linter cannot classify procedure sentences reliably, so review
the 20-word procedure limit by hand.

The checker disables the synonym heuristic because it conflates different
technical actions. For example, service startup and app launch differ here, and a
TV observation differs from a file check. Review term consistency by hand.

Review every advisory finding for meaning and grammar. A technical code name can
resemble an ordinary verb to the linter. Code blocks and exact interface labels
keep their spelling. A clean linter result does not establish technical accuracy
or complete vocabulary compliance.
