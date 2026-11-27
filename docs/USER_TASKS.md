# Your hands-on checklist
- Install Git, Python 3.12, Docker Desktop and VS Code; create your own free GitHub account/repository.
- Extract this package and run the commands in README. Check Docker output and troubleshoot errors. Run lint, mypy and tests on your machine; run GitHub Actions after push.
- Download source datasets, validate licensing/schema, choose a region, manually label about 200 pairs with evidence. Record real data profile and evaluation; tune thresholds on separate data.
- Run PostgreSQL/ElasticMQ integration and retry experiments. Run Locust using `locust -f locustfile.py --headless -u 20 -r 5 -t 60s --host http://localhost:8000 --csv results/load` (create results directory first). Increase users only if machine permits; replace query with representative real search terms.
- Fill result and incident templates with observed outcomes. Improve coverage to target and fix defects.
- Review each source file, understand SQL transactions and blocking complexity, implement at least a few improvements yourself and record honest commits. Do not fake commit history or claim sole authorship.
- Record your own demo video and personalize resume bullets with real results. Share repo with recruiter yourself.

## Git first push
Create an EMPTY public repository (no auto README). In extracted folder: `git init -b main`, `git add .`, `git commit -m "Initial generated project baseline"`, `git remote add origin YOUR_REPO_URL`, `git push -u origin main`. Inspect `git status` before committing and ensure raw data and secrets are excluded.
