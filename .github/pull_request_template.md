## What does this PR do?

<!-- One or two sentences. Link the issue: "Closes #12" closes it automatically on merge. -->

Closes #

## Area

- [ ] M1 · Disease  - [ ] M2 · Irrigation  - [ ] M3 · Yield  - [ ] M4 · Price  - [ ] M5 · Assistant  - [ ] M6 · Trees
- [ ] Backend  - [ ] Frontend  - [ ] Infra / Docker / CI  - [ ] Docs / report

## How to test it

<!-- Commands to run, page to open, request to send. Screenshot or GIF for UI changes. -->

## Checklist

- [ ] The branch is up to date with `develop` and CI is green
- [ ] I ran the tests of the part I changed (`./mvnw verify`, `npx ng test`, `python -m pytest`)
- [ ] No secrets, datasets or model weights are committed
- [ ] Notebook outputs are stripped
- [ ] If an API request/response changed: `docs/api-contract.md`, the Java record and the TS model are updated, and the backend + frontend owners are reviewers
- [ ] For a model change: the metric vs the baseline is in the description (and logged in MLflow)
