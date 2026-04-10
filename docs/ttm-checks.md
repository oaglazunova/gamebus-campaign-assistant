# TTM checks

This document explains the current **TTM structure checks** used by GameBus Campaign Assistant.

## What is TTM in this context?

TTM stands for the **Transtheoretical Model** of behavior change.

In the current campaign setup, TTM is represented through a level structure that reflects progression through stages, plus fallback / relapse behavior when users do not meet the required conditions.

The assistant does not evaluate the psychology of a campaign directly. Instead, it checks whether the configured level structure matches the **expected TTM-style progression pattern**.

## Expected progression structure

The current checker assumes this sequence of main levels:

- Newbie
- Rookie
- Amateur
- Proficient
- Skilled
- Expert
- Master
- Grandmaster

In addition, the current campaigns may contain **at-risk / relapse levels** around:

- Skilled
- Expert
- Master

These levels are used to represent setbacks or maintenance states.

## What the TTM checker tries to verify

The checker looks at the configured level transitions and tries to detect whether the campaign follows the expected TTM structure.

In plain language, it checks things such as:

- whether the level progression goes forward in the expected order
- whether fallback / failure transitions go to the correct level
- whether relapse / at-risk levels are placed where they are expected
- whether the overall progression graph is structurally consistent

## What a TTM issue usually means

If the assistant reports a TTM issue, it usually means one of the following:

- a level points to the wrong next level
- a failure path points to the wrong fallback level
- an at-risk level is missing or connected incorrectly
- the expected progression order is broken
- a terminal level or relapse-related transition is inconsistent

## Typical examples

### Example 1 — wrong forward progression
A level should lead to the next stage, but instead points to some other level.

Example idea:
- `Rookie` should progress to `Amateur`
- but it is configured to jump directly to `Proficient`

### Example 2 — wrong relapse target
A failure transition should lead to a specific at-risk level or previous level, but it points somewhere else.

Example idea:
- `Expert` failure should lead to `Expert At Risk`
- but it goes directly back to `Amateur`

### Example 3 — broken maintenance path
A relapse or maintenance level exists, but it does not return to the intended “main path” correctly.

## What to inspect when a TTM issue is reported

When you see a TTM issue, inspect:

1. the current level
2. its success transition
3. its failure transition
4. whether it belongs to the main path or an at-risk path
5. whether the target level matches the intended progression structure

If available, also compare the level to:
- your campaign design template
- the TTM structure diagram
- the expected level sequence for that campaign family

## What the checker does **not** guarantee

The TTM check does **not** guarantee that:

- the task content is psychologically appropriate
- the incentives are well designed
- the domain content fits the intended stage
- the campaign is clinically or behaviorally optimal

It only checks whether the **configured structure** matches the expected TTM-style level progression.

## Current assumption

At the moment, the checker assumes **one known TTM structure**, based on the current project setup.

In the future, campaigns may:
- have a different valid TTM structure
- use no TTM structure at all
- or require configurable TTM validation rules

If that happens, this part of the checker will likely need to become more flexible.

## Relationship to the chat assistant

When the chat assistant says things like:

- `Show TTM issues`
- `Explain TTM`

it uses the results of the current TTM structure check plus a plain-language explanation based on this expected model.

## Summary

In short:

- TTM checks validate the **structure of level progression**
- they focus on main-path and relapse/fallback transitions
- they help detect incorrect connections in the campaign graph
- they do not replace expert review of content or behavioral design