# Prompt-Injection Red-Teaming and a Layered Defense for an LLM

Trustworthy AI course project, Hanoi University of Science and Technology (HUST), Group 4:
Minh, Thanh, Ngoc, Huong, Nam.

## Introduction

More and more applications let a large language model (LLM) read text that somebody else wrote: an
assistant that summarises an e-mail, a question-answering tool over internal documents, a support bot
that reads tickets. The context window then holds two kinds of text. One is the instruction of the
developer and the user, which the application trusts. The other is external data, which it does not
control. The model gets both as a single token sequence and nothing forces it to obey only the first.
Anyone who can write into the document can plant an instruction and hope that the model follows it
instead of the user's request. This is *indirect prompt injection* (Greshake et al., 2023).

We study a small case that can be measured end to end. One LLM (not a multi-component agent) is asked
to summarise or answer questions about a document it should not trust. The documents are mostly
Vietnamese, with some English. The system prompt contains a secret canary that changes at every run
and a policy to keep it confidential, and two mock tools (`send_email`, `delete_file`) are declared but
never executed. An attack counts as successful when a rule-based check on the output fires: the canary
leaks, a string chosen by the attacker appears, or a mock tool is called with the attacker's arguments.

The attack side follows the framework of Liu et al. (2024), *Formalizing and Benchmarking Prompt
Injection Attacks and Defenses*: the attacker replaces the clean data `x_t` by contaminated data
`x~ = A(x_t, s_e, x_e)`, and the model receives `f(s_t + x~)`.

The work is empirical. **We do not propose a new defense.**

## Research questions

- **RQ1 (vulnerability).** How often does the undefended model follow injected instructions, and how
  does this depend on the attack type and on the attacker's goal?
- **RQ2 (effect and cost of each layer).** How much does each of four training-free layers reduce the
  attack success rate (ASR), when stacked and when used alone? What does it cost in false refusals on
  clean documents, in task utility and in latency?
- **RQ3 (generalisation).** Do the numbers measured on the prompts used to design the defenses carry
  over to a hold-out split with unseen techniques, and to public external data?

## System under test

Target model: Qwen3-8B served locally with Ollama (thinking off, temperature 0.7). Four defense layers
are applied in the order L1, L2, L3, model, L4, and each can be switched on or off:

| Layer | Mechanism |
|---|---|
| L1 | Input filtering: Unicode normalisation, removal of invisible characters, recursive decoding (Base64, hex, URL, ROT13, ...), and multilingual rule patterns scored by noisy-OR. No model call. |
| L2 | A small-LLM classifier (Qwen2.5-3B) that judges windows of the document and blocks above a threshold. |
| L3 | Instruction/data separation by prompting, with no training: datamarking (Spotlighting), a privilege hierarchy in the system prompt, a reminder after the document, and few-shot examples. It never blocks. |
| L4 | A consistency check adapted from MELON: re-run the model with the user task masked and block when the two responses are too similar (nomic-embed-text cosine). |

Instruction Hierarchy, StruQ and SecAlign train the model and are not reproduced here.

## Data

- **Team attack set** (schema v2, written by the team): 69 training, 38 hold-out (techniques not in
  training) and 14 paraphrased prompts, labelled with the five basic attacks of Liu et al. and with
  technique names, and 84 benign documents (42 for tuning, 42 for reporting; 30 hard negatives).
- **Public external data**, used zero-shot and never for tuning, in two sets:
  - *Set A* (stage 2): `deepset/prompt-injections`, `Lakera/gandalf_ignore_instructions`,
    `jackhhao/jailbreak-classification` and BIPIA contexts (2,021 attack and 1,729 benign items for detection;
    120 + 120 end to end).
  - *Set B* (stage 3, run once after the freeze): Mirror (Apache-2.0), SPML (MIT) and LLMail-Inject phase 2 (MIT),
    10,047 items after deduplication (9,385 independent plus 662 items of a Vietnamese translation of deepset);
    240 attack and 120 benign LLMail e-mails are also run end to end.

Public sets are lists of single prompts. They have no carrier document, no Vietnamese task, no
per-run secret and no success check that runs on the model output, which an end-to-end ASR needs, so
the main measurement uses the team set and the public sets serve as a second, zero-shot test.

## Protocol and main results

Thresholds are tuned on the training prompts and half of the benign set only. The configuration is
then frozen, and the hold-out and external splits are run exactly once. ASR is per prompt with a 95%
bootstrap interval over prompts.

| | Train | Hold-out |
|---|---|---|
| ASR without defense | 15.9% [8.7, 23.7] | 32.9% [19.7, 47.4] |
| + L1 | 0.0% | 15.8% |
| + L2 | 0.0% | 7.9% |
| + L3 | 0.0% | 0.0% |
| + L4 | 0.0% | 0.0% |

- Only the marginal gains of L1 (+17.1 points [+7.9, +28.9]) and L3 (+7.9 [+1.3, +17.1]) have intervals
  that exclude zero on hold-out. The 0 successes in 76 hold-out runs correspond to a Wilson upper bound
  of 4.8%, so this is not a guarantee.
- On untouched benign documents, the false-refusal rate goes 0, 2.4, 4.8, 4.8 and 15.9% along the chain,
  and mean latency (all 84 benign documents) reaches 1.69 times the baseline with L3 and 2.78 times with
  L4. L4 stops no further attack.
- L1, tuned most by hand, blocks 98.6% of the training attack runs but 37.6% [35.6, 39.8] of 2,021
  external attacks zero-shot.
- On external set B (run once after the freeze), L1 and L2 detect 17.3% and 39.3% of 6,875 independent
  attacks. End to end on 240 LLMail-Inject e-mails the undefended model calls the attacker's tool in 52.1%
  [45.8, 58.3] of the cases; the chain brings this to 0.4% [0.1, 2.3] (L3 is the largest step, L4 has no effect).
- Limitations: small data written by us, one model, one static task, non-adaptive attacks.

The full write-up (method, metrics, all tables) is in the report; its LaTeX source is under `report/`.

## Repository layout

```
analysis/        statistics: Wilson and cluster-bootstrap intervals, result tables
attack_prompts/  attack and benign data, external data (build scripts, provenance), validation script, reference list
baseline_agent/  the target system (no defense)
defenses/        L1-L4, the evaluation harness, detection experiments
report/          LaTeX sources of the report and slides
results/         final runs (results/final) and tuning evidence (results/dev_tuning)
tests/           offline tests (Ollama is mocked)
```

## Running

Python 3.13 with the standard library, `pandas` and `pytest`; Ollama with `qwen3:8b`,
`qwen2.5:3b` and `nomic-embed-text`. API keys, if any, go in `.env`, which is git-ignored.

```bash
python3 -m pytest tests -q                    # offline tests
python3 attack_prompts/validate.py            # data checks
export CAPSTONE_MODEL=qwen3:8b
python3 defenses/eval_asr.py --configs baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4 \
    --splits train,benign --samples 3 --out results/dev/example
python3 -m analysis.stats results/final/merged/results.csv --out /tmp/analysis \
    --benign-meta attack_prompts/benign_prompts.json
```

The hold-out and external splits are refused unless the final-run confirmation flag is given. See
`CONTRIBUTING.md` for commit and branch rules.
