# Bot de Citas Padron Madrid

Bot que verifica la disponibilidad de citas para empadronamiento en Madrid y te notifica por Telegram.

## Instalacion rapida

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar Telegram (ver abajo)
cp .env.example .env
# Edita .env con tu token y chat_id

# 3. Probar que funciona
python run.py --once

# 4. Ejecutar en modo continuo
python run.py
```

## Configurar Telegram

### Paso 1: Crear bot
1. Abre Telegram y busca `@BotFather`
2. Envia `/newbot`
3. Sigue las instrucciones para nombrar tu bot
4. Copia el **token** que te da (algo como `123456789:ABCdefGHIjklMNO...`)

### Paso 2: Obtener tu Chat ID
1. Busca tu bot en Telegram y enviale cualquier mensaje
2. Visita en el navegador:
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
3. Busca `"chat":{"id":XXXXXXXX}` - ese numero es tu `CHAT_ID`

### Paso 3: Configurar .env
```bash
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNO...
TELEGRAM_CHAT_ID=987654321
CHECK_INTERVAL_MINUTES=30
```

## Modos de ejecucion

### Ejecucion continua (recomendado)
```bash
python run.py
```
Se ejecuta cada X minutos (configurable en `.env`).

### Ejecucion unica (para cron)
```bash
python run.py --once
```

### Con cron (cada 30 min de 7am a 10pm)
```bash
crontab -e
```
Agregar:
```cron
*/30 7-22 * * * cd /Users/satorrea/PycharmProjects/cita-padron-madrid && /Users/satorrea/PycharmProjects/cita-padron-madrid/.venv/bin/python run.py --once >> cron.log 2>&1
```

### Con launchd en Mac (mas confiable que cron)
Ver archivo `com.citapadron.checker.plist` incluido.

## Troubleshooting

- **Screenshots**: Se guardan en la carpeta `screenshots/` para debugging
- **Logs**: Ver `cita_checker.log`
- **Test Telegram**: `python test_telegram.py`

## Notas

- El bot solo notifica cuando **hay citas disponibles** o si hay un error
- Si no hay citas, solo se registra en el log (no te molesta)
- La pagina del Ayuntamiento puede cambiar; si deja de funcionar, revisa los screenshots
