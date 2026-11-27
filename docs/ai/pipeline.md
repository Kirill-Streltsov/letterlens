# AI pipeline

This document describes how LetterLens turns OCR text into verified facts and an
explanation. Code: `backend/src/letterlens/pipeline/steps.py`.

## 1. Input

The client sends a `LetterDocument`: text lines with `page`, `index`, optional
normalized bounding box and OCR confidence. Each line has the id `p{page}-l{index}`.
All facts and summary sentences refer to these ids.

## 2. Steps

### 2.1 Classify

- Model: TF-IDF + logistic regression, temperature-scaled ([ADR-0007](../architecture/adr/0007-classifier-training-and-serving.md)).
- Types: `tax`, `benefits`, `health_insurance`, `immigration`, `landlord`, `other`.
- Below confidence 0.5 the classifier abstains and returns `other`.
- The type selects the guidance block in the extraction prompt and filters retrieval.

### 2.2 Extract

1. Remove lines that look like instructions to a model (`safety/guardrail.py`, `neutralize_injections`).
2. Pseudonymize personal data (`safety/pii.py`): IBAN, e-mail, phone, tax id, tax number,
   BG number, insurance number, birth date, case references, and the recipient name and
   street in the address block. The model sees placeholders such as `[TAXNO_1]`.
3. Call the gateway with task `extract`, the prompt `extract_system(letter_type)` and the strict schema `Extraction`.
4. Put the original values back into the result (`PiiVault.restore`).
5. If the gateway fails or a budget is spent, use the rule-based extractor (`extraction/rules.py`) and mark the letter `degraded`.

### 2.3 Verify

The verifier (`grounding/verifier.py`) sets the trust state of each fact:

| Situation | State | Note shown to the reader |
|---|---|---|
| The cited line contains the date or amount | `verified` | none |
| The value is in another line | `needs_check` | "appears in the letter, but not in the quoted line" |
| The value is not in the letter | `needs_check` | "not found in the quoted line" |
| A date before the letter date | `needs_check` | "before the letter date" |
| A relative period | `needs_check`, estimated | the rule, for example "1 months; received on 2026-03-16 …" |

Reference numbers that are not in the cited line are removed.

### 2.4 Retrieve

Query: subject, sender, deadline and action descriptions, and the first 2,500
characters of the letter (German terms such as "Widerspruch" carry most signal).
Ranking: BM25 over title, German keywords and text; embeddings when an index for
the configured model exists; reciprocal rank fusion; filter by letter type; drop
passages without any lexical or dense match. Result: up to 4 passages `c1`…`c4`.

### 2.5 Explain

The model writes in English: a headline, the kind of letter, 3 to 10 summary
sentences with line ids, 1 to 4 "next steps" with passage ids, and short labels for
each deadline and amount. Then the sanitizer enforces the contract:

| Rule | Action |
|---|---|
| A sentence reads like individual legal advice | drop it |
| A sentence contains a number that is not in the letter or the verified facts | drop it |
| A next step has no valid passage id | drop it |
| A line id does not exist | remove the id |
| A URL | remove it |

Counters of dropped items go to the log (`explanation sanitized`).

### 2.6 Translate

Other languages translate the checked English explanation (task
`translate_explanation`); they are not written again from the letter. The model
returns each summary sentence and next step with its index, and each label with its
fact id. Code puts the line ids, passage ids and citations back from the English
source, so every language shows the same content with the same links.

| Rule | Action |
|---|---|
| Names and addresses | hidden again with the letter's placeholders before the call (`PiiVault.reapply`) |
| An item is missing, or an extra item appears | write the explanation directly in the target language |
| A translated item fails the advice or number check | drop it (log `translation sanitized`) |
| Amounts with a space as thousands separator ("1 092,50", uk, ru) | count as the same number |

The evaluation gate `aligned_share` (min 0.95) checks that translations keep one
sentence per English sentence.

## 3. Questions

`POST /v1/letters/{id}/questions` runs three layers:

1. **Rules** (`check_question_rules`): multilingual patterns for individual advice and injection. Free and instant.
2. **Model classifier** (task `guard`): categories general information, individual legal advice, prompt injection, off topic. If this call fails, the API refuses (fail closed).
3. **Answer** (task `answer`), then the output checks: the model's own `refused` flag, the advisory-phrase check, and the number check.

A refusal tells the reader, in their language, that a counselling service can help,
and the app offers "Talk to a counsellor".

## 4. Prompts

Prompts live in `llm/prompts.py`. Each prompt has a version string
(`extract-v5`, `explain-v6`, `translate-explanation-v1`, `answer-v2`, `guard-v2`, `backtranslate-v2`). The cost ledger and every
evaluation report record the version. Rules for prompt changes:

1. Change the prompt and its version string in the same commit.
2. Run the live evaluation (`--profile live`). All gates must pass.
3. Put the report in the pull request.

## 5. Gateway

| Function | Setting |
|---|---|
| Model per task | `LETTERLENS_LLM_MODEL_EXTRACT`, `_EXPLAIN`, `_GUARD` |
| Fallback models | `LETTERLENS_LLM_FALLBACK_MODELS` |
| Retries | 3 attempts per model, exponential backoff with jitter, for 408/409/425/429/5xx and timeouts |
| Schema | strict JSON schema (no `$ref`, `additionalProperties: false`); one repair attempt |
| Budgets | `LETTERLENS_MONTHLY_LLM_BUDGET_USD`, `LETTERLENS_USER_DAILY_TOKEN_BUDGET` |
| Ledger | table `llm_calls`: task, model, prompt version, tokens, list price, latency, attempts, fallback, error |

To answer "what did this letter cost?", call `GET /v1/admin/letters/{id}/cost`.
For totals per day, task and model with p50 and p95 latency, call `GET /v1/admin/costs`.
