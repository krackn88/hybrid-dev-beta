# Changelog

## [Unreleased]

## [1.0.0] - 2025-03-29
### Added
- Initial setup of GitHub Actions workflows:
  - CI workflow to run tests on push and pull requests.
  - Release workflow to create releases when tags are pushed.
  - Webhook Manager workflow to manage GitHub webhooks via workflow dispatch.
- Python script for automating repo updates using the `gh` CLI.
- Updated `CHANGELOG.md` and `TODO.md` to reflect ongoing tasks and changes.
- Integrated GitHub Actions setup script (`setup_github_actions.sh`).
- Added `start_webhook.sh` to start the webhook handler.
- Set up a test webhook in GitHub.
- Triggered the webhook for testing.
