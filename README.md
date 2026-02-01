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
poetry run game-bot
```

## Project Structure

```
src/
├── config.py          # Configuration loader
├── main.py            # Entry point (module: src.main)
├── core/
│   ├── bot.py         # Main bot logic
│   └── model/         # Data models
├── driver_adapter/    # Browser driver wrapper
└── scan_adapter/      # Scanning functionality
```

## Configuration

Create a `config.yaml` file in the project root with your game credentials and settings.

## License

This project is for educational purposes only.

## Running with Docker

The repository includes a `Dockerfile` configured to install Python 3.14, Poetry, the project package, and Playwright browsers. The image's default command runs the module directly (`python -m src.main`). Below are recommended commands for building and running the image and how to pass credentials and the server URL via environment variables.

Note: This README assumes the application ultimately reads the configuration from `config.yaml` (the app loads that file by default). `src/config.py` supports substituting environment variables inside `config.yaml` (e.g. use `${SERVER_URL}` in `config.yaml`) and `load_config` calls `load_dotenv()` so a `.env` file is also supported. In short, either:

- Provide a `config.yaml` file in the container (mount or COPY) with values or placeholders such as `${SERVER_URL}` that will be replaced from environment variables at runtime; or
- Create a `.env` file (or set env vars) and ensure `config.yaml` uses placeholders for those values, or generate `config.yaml` before running.

The expected environment variable names used in examples below are:
- `SERVER_URL` (or `server_url` inside `config.yaml`)
- `USER_LOGIN` (or `user_login` inside `config.yaml`)
- `USER_PASSWORD` (or `user_password` inside `config.yaml`)

Build the image:

```bash
docker build -t game-bot:latest .
```

Run the container and pass credentials inline (the container will execute `python -m src.main`):

```bash
docker run --rm -it \
  -e SERVER_URL="https://example.com" \
  -e USER_LOGIN="player1" \
  -e USER_PASSWORD="s3cr3t" \
  game-bot:latest
```

Use an env-file (recommended to avoid leaking credentials in shell history). Create a file named `.env` with:

```text
SERVER_URL=https://example.com
USER_LOGIN=player1
USER_PASSWORD=s3cr3t
```

Then run:

```bash
docker run --rm -it --env-file .env game-bot:latest
```

If you prefer to run the installed console script instead of the module, you can override the container command (the project is installed during image build):

```bash
# run the console script via Poetry shim inside the container
docker run --rm -it --env-file .env game-bot:latest poetry run game-bot
```
