# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bot that monitors the Madrid City Council website for "padrón" (census registration) appointment availability and sends Telegram notifications when appointments become available.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Single execution (for testing or cron)
python cita_checker.py --once

# Continuous execution (runs every CHECK_INTERVAL_MINUTES)
python cita_checker.py

# Test Telegram connection
python test_telegram.py
```

## Configuration

Copy `.env.example` to `.env` and configure:
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID
- `CHECK_INTERVAL_MINUTES` - Check frequency (default: 30)

## Architecture

Two implementations exist:

1. **`cita_checker.py`** - Monolithic script with all logic (currently in use)
2. **`src/`** - Refactored modular version:
   - `config.py` - Environment variables and logging setup
   - `browser.py` - Selenium Chrome automation (headless), screenshot handling
   - `notifier.py` - Async Telegram message/photo sending

The bot:
1. Opens the appointment page via headless Chrome
2. Selects "Padrón" category and "Altas" procedure in dropdowns
3. Analyzes page text for availability indicators
4. Sends Telegram notification only when appointments are found or errors occur

## Key Patterns

- Screenshots saved to `screenshots/` for debugging when detection fails
- Logs written to `cita_checker.log`
- The Madrid website structure may change; check screenshots when scraping breaks
- Uses `webdriver-manager` to auto-manage ChromeDriver versions

## macOS Scheduling

`com.citapadron.checker.plist` provides launchd configuration. Install with:
```bash
cp com.citapadron.checker.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.citapadron.checker.plist
```
