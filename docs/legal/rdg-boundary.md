# The legal-advice boundary (RDG)

> Not legal advice. This document describes how the product implements a boundary.
> A lawyer must review the boundary before launch.

## 1. The rule

Under § 2 (1) of the Legal Services Act (Rechtsdienstleistungsgesetz, RDG), a
legal service is any activity in a concrete matter of another person that needs a
legal examination of the individual case. Only persons that a law permits may
provide it (§ 3 RDG), for example lawyers or recognized counselling bodies.

## 2. What LetterLens does and does not do

| Allowed (information) | Not allowed (individual assessment) |
|---|---|
| Say what the letter says, in plain language | Say whether the decision is correct or lawful |
| Show the dates and amounts that the letter names | Recommend to object, to pay, to sign or not |
| Explain what a term or a procedure means in general, with sources | Predict the outcome of an objection or a lawsuit |
| Estimate a period end with the general rule, marked "please check" | Write an objection for the reader |
| Name free counselling services and hand the letter over with consent | Act for the reader towards the authority |

## 3. Implementation

| Layer | Mechanism | Code |
|---|---|---|
| Prompt | The explanation and answer prompts forbid individual assessments and predictions | `llm/prompts.py` |
| Input check, layer 1 | Multilingual patterns for advice requests | `safety/guardrail.py` |
| Input check, layer 2 | Model classifier; if it is not available, the API refuses | `services/letters.py::ask` |
| Output check | Advisory phrases are removed from explanations; an advisory answer is replaced with the refusal | `pipeline/steps.py::sanitize_explanation` |
| Hand-over | The refusal offers "Talk to a counsellor"; sharing needs explicit consent | clients, `services/sharing.py` |
| Corpus | General information with a primary source (mostly the law text) and a check date | `backend/corpus/` |

## 4. Measurement

The red-team set has 54 advice requests and 34 normal questions in 6 languages.
Current results (rules layer only): 85.2 % of advice requests caught, 0 % of
normal questions blocked, 100 % of injection attempts caught. The live profile
adds the model layer. Gate: at least 95 % caught and at most 10 % false
positives with the model layer.

## 5. Questions for the legal review

1. Is the estimated period end (with the rule shown and the state "please check") information or a legal service?
2. Is the summary of "what people usually do next", with sources, general information?
3. Does the hand-over to a counselling service need a contract between the operator and the service?
4. Which disclaimer wording is necessary in each language?
