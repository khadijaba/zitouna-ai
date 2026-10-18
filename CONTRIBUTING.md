# Contributing to Zitouna AI

Six people push to this repo for ten weeks. These rules keep `main` always demo-able and avoid losing each other's work. Read once, keep the cheat sheet at the bottom handy.

## 1. Branches

```
main      ← always works; updated only at the end of each phase (tag v0.X.0)
 └ develop  ← integration branch; every PR goes here
     ├ feat/m1-gradcam
     ├ data/m3-onagri-2015-2024
     └ fix/backend-jwt-expiry
```

- **Never commit directly to `main` or `develop`.** Everything goes through a pull request (PR).
- Create your branch from an up-to-date `develop`. Name it `<type>/<area>-<short-description>`:

| type | when |
|---|---|
| `feat/` | new feature, endpoint, screen, model |
| `fix/` | bug fix |
| `data/` | dataset extraction / cleaning scripts |
| `exp/` | experiment you may throw away (notebooks) |
| `docs/` | README, report, contract |
| `chore/` | config, dependencies, CI, Docker |

  `area` = `m1` … `m6`, `backend`, `frontend`, `infra`. Examples: `feat/m4-sarima-baseline`, `fix/frontend-login-redirect`.
- One branch = one topic. Small PRs (< ~400 changed lines) get reviewed fast; huge PRs sit for days.
- Delete the branch after merge (GitHub does it automatically if you enable it in Settings).

## 2. Commits

Use [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): what, in the imperative`.

```
feat(m1): add Grad-CAM heatmap to /predict
fix(backend): return 404 when parcel belongs to another user
data(m3): extract ONAGRI production 2015-2024 to CSV
test(m5): add 40 derja questions to intent test set
docs(report): write M2 results section
chore(infra): pin postgres to 17-alpine
```

Scopes: `m1`…`m6`, `backend`, `frontend`, `infra`, `ci`, `docs`, `report`.
Commit often on your branch; it gets squashed on merge, so messy intermediate commits are fine.

## 3. Pull requests

1. Push your branch and open a PR **into `develop`** (not `main`).
2. Fill in the template. Link the issue with `Closes #12`.
3. CI must be green (backend, frontend and AI services are built and tested automatically, only for what you changed).
4. **1 approval** required. CODEOWNERS requests the right reviewer automatically (e.g. a change in `ai-services/m4-price/` asks the M4 owner).
5. The author merges, with **Squash and merge**, once approved.

Reviewing: answer within 24 h. Check that it runs, that it does what the PR says, and that nothing secret or heavy is committed. Prefer questions ("what happens if `treeCount` is null?") over orders.

### End of a phase (every 2 weeks)

After the team review, M3 (Git owner) opens a PR `develop → main`, merges it with a **merge commit** (not squash), and tags it:

```bash
git checkout main && git pull
git tag -a v0.2.0 -m "Phase 2: baselines" && git push origin v0.2.0
```

## 4. Staying in sync

```bash
git checkout develop && git pull           # every morning
git checkout feat/m1-gradcam
git rebase develop                         # bring your branch up to date
# fix conflicts if any, then: git add <files> && git rebase --continue
git push --force-with-lease                # only on YOUR branch, never on develop/main
```

Never `git push --force` on `develop` or `main`. Never rewrite a branch someone else works on.

## 5. What must never be committed

| ❌ | ✅ instead |
|---|---|
| Datasets (`data/raw`, `data/processed`) | Shared Google Drive folder, same structure (see [data/README.md](data/README.md)) |
| Model weights (`.pt`, `.pkl`, `.joblib`, `.onnx`…) | Hugging Face model repo: `python scripts/models.py pull` / `push` (see [models/README.md](models/README.md)) |
| `.env`, passwords, API keys, the JWT secret | `.env` (git-ignored); document new variables in `.env.example` |
| Notebook outputs (images, big tables) | Strip outputs before committing (`nbstripout`, below) |
| `node_modules/`, `target/`, `.venv/` | Rebuilt by each member |

The `.gitignore` already blocks these. If you committed a secret by mistake: tell the team, **rotate it** (deleting the commit is not enough, it stays in the history).

### Recommended: pre-commit hooks

```bash
pip install pre-commit
pre-commit install        # once per clone
```

Then every commit is checked automatically: large files are refused, notebook outputs are stripped, Python is linted and formatted.

## 6. Changing the API contract

The JSON exchanged between the app, the backend and the AI services is described in [docs/api-contract.md](docs/api-contract.md) and frozen after week 2. To change it:

1. Open an issue explaining the change and who is affected.
2. In **one PR**, update together: `docs/api-contract.md`, the Python schema (`app/schemas.py`), the Java record (`…Result.java`) and the TypeScript model (`frontend/src/app/core/api/models.ts`).
3. Adding an optional field is easy. Renaming or removing one breaks the others: agree on it first.

## 7. Module owners: from notebook to service

1. Explore and train in `notebooks/mX_*/`. Log runs in MLflow (params, metric, baseline vs model).
2. Export the model to `models/mX/` and upload it: `python scripts/models.py push mX`.
3. Plug it in `ai-services/mX-*/app/predictor.py` (`load()` and `predict()`) and add the libraries to `requirements.txt`.
4. Restart the service: `/health` shows `"modelLoaded": true` and responses have `"mock": false`.

## 8. GitHub settings (repo admin, once)

- **Settings → General**: set the **default branch to `develop`** (new PRs then target it automatically); allow *Squash merging* and *Merge commits*, disable *Rebase merging*; enable *Automatically delete head branches*.
- **Settings → Branches → Add rule** (or Rules → Rulesets) for `main` and `develop`:
  - Require a pull request before merging, 1 approval, dismiss stale approvals
  - Require review from Code Owners
  - Require status checks to pass: **`ci-ok`**
  - Require conversation resolution
  - Block force pushes and deletions
- **Settings → Collaborators**: add the 5 teammates with *Write* access.
- [.github/CODEOWNERS](.github/CODEOWNERS): give each module to its owner (replace the username on its lines).
- Create labels: `type:task`, `type:bug`, `m1` … `m6`, `backend`, `frontend`, `infra`, `report`.
- Create a **Project** (board) and link it to the repo.

> Branch protection on a **private** repo needs GitHub Pro/Team. Students get Pro for free with the [GitHub Student Developer Pack](https://education.github.com/pack). Otherwise make the repo public or just follow the rules by discipline.

## Cheat sheet

```bash
# start a task
git checkout develop && git pull
git checkout -b feat/m2-prophet-baseline

# work
git add -p                                   # review what you stage
git commit -m "feat(m2): add Prophet baseline for ET0"
git push -u origin feat/m2-prophet-baseline  # then open the PR on GitHub

# update your branch with the latest develop
git fetch origin && git rebase origin/develop
git push --force-with-lease

# undo
git restore <file>             # discard local changes to a file
git restore --staged <file>    # unstage
git commit --amend             # fix the last commit (before pushing)
git revert <sha>               # undo a pushed commit safely
```
