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

- **Team attack set** (written by the team): 69 training, 38 hold-out (techniques not in training)
  and 14 paraphrased prompts, labelled with the five basic attacks of Liu et al. and with technique
  names, and 84 benign documents (42 for tuning, 42 for reporting; 30 hard negatives).
- **Public data, split by source.** Some sources are used to tune the layers, the others are kept for
  a single final run:
  - *Tune* (12,328 items): `deepset/prompt-injections`, `Lakera/gandalf_ignore_instructions`,
    `jackhhao/jailbreak-classification`, BIPIA (payloads in carrier documents), Mirror, SPML, a
    Vietnamese translation of deepset, and the attack e-mails of phase 1 of LLMail-Inject plus half of
    its benign e-mails.
  - *Hold-out*: the attack e-mails of phase 2 of LLMail-Inject that were not used before (200 run
    end to end, 600 for detection only) and the other half of its benign e-mails (80). This is the only
    public hold-out that no tuning has seen.

Public sets are lists of single prompts. They have no carrier document, no Vietnamese task, no
per-run secret and, except LLMail-Inject, no success check that runs on the model output, which an
end-to-end ASR needs. So the ASR is computed on the team prompts and on the LLMail-Inject e-mails
(a `send_email` call whose arguments contain the attacker's address); the other sources are used to
tune and to measure detection only.

## Protocol and main results

The protocol was written down before the hold-out was run: tune the layers on the tune data, freeze the
configuration (tag `freeze-v2`), and run the hold-out exactly once. ASR is per prompt with a 95% bootstrap
interval over prompts (Wilson interval over runs for the e-mails).

| ASR (%) | No defense | + L1 | + L2 | + L3 | + L4 |
|---|---|---|---|---|---|
| Team hold-out (38 prompts) | 34.2 [19.7, 48.7] | 14.5 | 5.3 | 1.3 | 3.9 |
| LLMail-Inject phase 2 (200 e-mails) | 51.5 [44.6, 58.3] | 22.0 | 14.5 | 0.0 [0.0, 1.9] | 0.0 |

- On the team hold-out, the reductions of L1 (+19.7 points [+7.9, +32.9]) and L2 (+9.2 [+1.3, +18.4])
  exclude zero, the one of L3 (+3.9 [0.0, +10.5]) touches zero, and L4 does not help (the 3.9% against
  1.3% is sampling noise: L4 blocks no run). Without defense the ASR on the 69 training prompts is
  15.9% [7.2, 24.6].
- On the e-mails, L1 removes the most (+29.5 points), then L3 (+14.5) and L2 (+7.5); L4 changes nothing.
  Part of the L1 gain comes from patterns chosen on phase 1 of the same competition, which has the same goal.
- On the 42 untouched benign documents of the team, the false-refusal rate goes 0, 2.4, 4.8, 4.8 and 14.3%
  along the chain, and the mean latency is 0.98, 0.96, 1.62 and 2.74 times the baseline. L4 stops no
  further attack: with our implementation it is a negative result, not a statement about MELON itself.
- On the 600 phase-2 e-mails used for detection, L1 detects 47.0%, L2 37.3% and both together 59.7%,
  with no false positive on 80 benign e-mails.
- Tuning L1 on public data raised its detection rate on those data from 38.9% to 51.3% but did not change
  what it blocks among the team hold-out prompts (57.9% in both designs).
- A zero is an observation, not a guarantee: 0 successes in 200 e-mails correspond to an upper bound of 1.9%.
- Limitations: small data partly written by us, a hold-out that is only partly unseen, reduced sample
  sizes to finish in time, one model, one static task, non-adaptive attacks.

An earlier design (public data used zero-shot only, never for tuning) gave similar numbers on the
team prompts; its results are kept in `results/final/`, and the v2 runs and the tuning log are in `results/v2/`.

## Repository layout

```
analysis/        statistics: Wilson and cluster-bootstrap intervals, result tables
attack_prompts/  attack and benign data, external data (build scripts, provenance), validation script, reference list
baseline_agent/  the target system (no defense)
defenses/        L1-L4, the evaluation harness, detection experiments
results/         runs of the earlier design (results/final), of the final design (results/v2) and tuning evidence
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
