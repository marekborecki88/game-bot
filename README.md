# Game Bot

A Python-based game automation bot built with Playwright.

## Description

This project provides automated gameplay functionality using web automation. It uses Playwright for browser automation and includes features for account management, village management, and automated scanning.

## Requirements

- Python ^3.14
- Poetry (for dependency management)

## Installation

1. Clone the repository
2. Install dependencies:

```bash
poetry install
```

3. Install Playwright browsers:

```bash
poetry run playwright install
```

4. Configure your settings in `config.yaml`

## Usage

Run the bot using:

```bash
poetry run python -m app.main
```

Alternatively, you can use the Poetry script:

```bash
poetry run game-bot
```

## Project Structure

```
app/
├── config.py          # Configuration loader
├── main.py           # Entry point
├── core/
│   ├── bot.py        # Main bot logic
│   └── model/        # Data models
├── driver_adapter/   # Browser driver wrapper
└── scan_adapter/     # Scanning functionality
```

## Configuration

Create a `config.yaml` file in the project root with your game credentials and settings.

## License

This project is for educational purposes only.

