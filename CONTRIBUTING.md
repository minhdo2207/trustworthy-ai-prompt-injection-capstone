# Working rules for this repository

These rules apply to the whole team: Minh, Thanh, Ngoc, Huong, Nam.

## 1. The `main` branch is protected

- **Do not push directly to `main`.** Every change goes through a pull request (PR).
- An approval is not required, but **ask someone to look at the PR before you merge it**, especially if it touches `defenses/` or `attack_prompts/`.
- All comments in a PR must be resolved before merging.
- Do not force-push to `main` and do not delete it.

## 2. Workflow for a change

```bash
git checkout main
git pull
git checkout -b <name>/<type>-<short-description>     # e.g. ngoc/feat-l1-unicode-filter
# ... edit, test ...
git add <specific files>                              # do not use git add .
git commit -m "feat(defenses): add L1 Unicode normalisation"
git push -u origin <branch-name>
```

Then open a PR into `main` on GitHub, assign a reviewer, and tell the team in the group chat.
If you edit directly on the GitHub web page, choose **"Create a new branch for this commit and start a pull request"**; never commit straight to `main`.

## 3. Branch names

Use `<name>/<type>-<short-description>`: lower case, no diacritics, words joined with hyphens.

Examples: `huong/data-benign-set`, `thanh/feat-harness`, `nam/fix-l3-delimiter`, `minh/docs-related-work`.

## 4. Commit format

```
<type>(<scope>): <short description, in the imperative mood>

<more explanation if needed: why, and what it affects>
```

**Type (`<type>`):**

| Type | Use when |
|---|---|
| `feat` | Adding a feature or a new defense layer |
| `fix` | Fixing a bug |
| `data` | Adding or changing the prompt sets or the benign set |
| `docs` | Documentation, report, README |
| `exp` | Experimental results, CSV files, tables |
| `refactor` | Reorganising code without changing its behaviour |
| `chore` | Configuration, `requirements.txt`, `.gitignore` |

**Scope (`<scope>`):** `attack_prompts`, `baseline_agent`, `defenses`, `docs`, or a layer name such as `l1`, `l2`, `l3`, `l4`, `harness`.

**Rules:**

1. The first line is **at most 72 characters** and does not end with a full stop.
2. Each commit does **one thing**. Do not mix a code change and a data change in one commit.
3. Do not use messages such as `Update`, `fix`, `abc` or `Add files via upload`. The message must tell others what changed.
4. Commit with **your own GitHub account** (check `git config user.name` and `git config user.email`).
5. Write in Vietnamese or in English, but keep one language within a PR.

Good examples:

```
data(attack_prompts): add 4 Fake Completion prompts to the hold-out
exp(harness): record the Qwen3-8B baseline ASR on train and hold-out
fix(l2): correct the Prompt Guard threshold chosen wrongly on the hold-out
```

## 5. Pull request rules

- The **PR title** follows the same format as a commit.
- The **PR description** says what was done, why, how to check it, and links the issue (`Closes #<number>`).
- Keep PRs small, with one purpose, so that they are easy to review. Avoid PRs with dozens of files.
- The reviewer checks: does it run, does it touch the hold-out data, are there stray files, do the references have correct links and sources.
- Use **Squash and merge** to keep the history of `main` short, one commit per PR.
- Delete the branch after merging.

## 6. Rules specific to this project

1. **Never tune thresholds, keywords or system prompts on the hold-out.** Tune only on the tune data (the training prompts, the tuning half of the benign set and the public sources marked as tune in the report). The hold-out is run once, for the final frozen configuration.
2. Every prompt that comes from an external source must record its `source` (paper or data set name, link, licence).
3. Experimental results must be reproducible from a script. Do not edit result CSV files by hand.
4. Do not change `attack_prompts/holdout_prompts.json` after the hold-out has been measured without telling the whole team.

## 7. This is a public repository: do not commit these

- **API keys, tokens and passwords** (OpenRouter, Hugging Face, ...). Keep them in `.env` (already in `.gitignore`); commit only `.env.example` with dummy values.
- Large model files, `venv` folders and caches.
- Anyone's personal data.

If you commit a secret key to a branch by mistake: **revoke the key at once** on the provider's page and tell the team lead. Deleting the commit is not enough, because the key has already been exposed.

## 8. When there is a conflict

Update your own branch from `main`; never edit `main` yourself:

```bash
git fetch origin
git rebase origin/main      # or: git merge origin/main
# resolve the conflicts, then:
git push --force-with-lease   # only on your own branch
```

If you are not sure, ask the team lead before you force-push.
