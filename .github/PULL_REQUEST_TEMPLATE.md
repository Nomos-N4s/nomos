## Description
&lt;!-- Describe the changes and the motivation. Link to relevant issues. --&gt;
Fixes # (issue)

## Type of Change
&lt;!-- Mark all that apply --&gt;
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update (book, README, API docs)
- [ ] Refactor / cleanup (no functional change)
- [ ] Formal verification (Lean proofs, predictions)

## Checklist
&lt;!-- All items must be checked before merge --&gt;
- [ ] I have read the [CONTRIBUTING.md](../CONTRIBUTING.md) guidelines
- [ ] My code follows the project's style guidelines (type hints, no comments in code, docstrings for public APIs)
- [ ] I have performed a self-review of my code
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally (`python -m pytest tests/ -v`)
- [ ] I have run the benchmark suite if this affects experiments (`python -m src.governance.runner all --baselines`)
- [ ] I have run the formal prediction suite if this affects core logic (`python -m src.governance.runner prove --all`)
- [ ] I have made corresponding changes to the documentation (book chapters, README, docstrings)
- [ ] My changes generate no new warnings
- [ ] I have updated the [CHANGELOG.md](../CHANGELOG.md) if this is a user-facing change

## Testing
&lt;!-- Describe how you tested this. Include commands, environments, and edge cases. --&gt;

## Screenshots / Output
&lt;!-- If applicable, add output, plots, or architecture diagrams. --&gt;
&lt;!-- Benchmark example (if benchmarks were run):
```
Total time: X.XXs
Total reports: 400
Analysis: N effect sizes, M hacking episodes
Generating figures...
  -> results/figures/reward_curves.png
  -> results/figures/violation_rates.png
  -> results/figures/deadlock_frequency.png
  -> results/figures/pareto_frontier.png
All figures saved to results/figures/
```
--&gt;

## Additional Notes
&lt;!-- Anything else reviewers should know? Link to theoretical foundations, review panel feedback, etc. --&gt;