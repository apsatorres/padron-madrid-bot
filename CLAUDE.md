# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bot that monitors the Madrid City Council website for "padrón" (census registration) appointment availability and sends Telegram notifications when appointments become available.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Single execution (for testing or cron)
python run.py --once

# Continuous execution (runs every CHECK_INTERVAL_MINUTES)
python run.py

# Debug scripts
python tests/debug_connection.py      # Test page connection
python tests/debug_formulario.py      # Explore form structure
python tests/debug_verificacion.py    # Full verification with logs
python tests/test_telegram.py         # Test Telegram sending
```

## Configuration

Copy `.env.example` to `.env` and configure:
- `TELEGRAM_BOT_TOKEN` - Bot token from @BotFather
- `TELEGRAM_CHAT_ID` - Your Telegram chat ID
- `CHECK_INTERVAL_MINUTES` - Check frequency (default: 30)

## Architecture

Modular structure in `src/`:
- `config.py` - Environment variables, logging, constants
- `browser.py` - Selenium Chrome automation, jQuery UI combobox handling
- `checker.py` - Appointment checking logic and form navigation
- `notifier.py` - Async Telegram notifications
- `main.py` - Entry point and scheduling

## How it works

1. Opens https://servpub.madrid.es/GNSIS_WBCIUDADANO/tramite.do
2. Clicks "Acceso SIN Identificar"
3. Selects category "Padrón y censo" via jQuery UI combobox
4. Waits for procedure options to load
5. Selects procedure "Altas, bajas y cambio de domicilio en Padrón"
6. Clicks "consultar la oficina con cita más temprana" link
7. Analyzes page text for availability indicators
8. Sends Telegram notification only when appointments found or errors occur

## Key Technical Details

- The Madrid website uses **jQuery UI comboboxes** (autocomplete widgets), not native HTML selects
- Each combobox has a visible text input and a hidden `<select>`
- Element IDs:
  - Category input: `cpTramite_combo0`, select: `selectCategorias`
  - Procedure input: `cpTramite_combo1`, select: `selectTramites`
- The procedure dropdown options update via AJAX when category changes
- Uses `webdriver-manager` to auto-manage ChromeDriver versions

## Deployment

Primary deployment is via **GitHub Actions** (`.github/workflows/check-citas.yml`):
- Runs every 30 minutes from 7am to 10pm (Madrid time)
- Requires secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Uploads screenshots as artifacts on failure

## Troubleshooting

- Screenshots saved to `screenshots/` for debugging
- Logs written to `cita_checker.log`
- If scraping breaks, run `python tests/debug_formulario.py` to see current page structure
