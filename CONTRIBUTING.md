# Contributing

Thanks for considering contributing!

## How to contribute
1. Fork the repo
2. Create a feature branch:
   - `git checkout -b feature/<short-name>`
3. Make your changes
4. Run locally:
   - `python scanner.py --output findings.json --fail-on NONE`
5. Open a Pull Request with:
   - What you changed
   - Why you changed it
   - How you tested it

## Guidelines
- Keep changes minimal and easy to review
- Prefer small PRs over large refactors
- Do not include AWS credentials or sensitive data
- Avoid hardcoding account-specific values (use GitHub Secrets/Inputs)

## Code style
- Keep scripts readable and beginner-friendly
- Use clear variable names and comments where needed
