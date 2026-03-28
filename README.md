# Bot de Citas Padron Madrid

Bot que verifica automaticamente la disponibilidad de citas para empadronamiento en el Ayuntamiento de Madrid y te notifica por Telegram cuando hay citas disponibles.

## Como funciona

1. El bot navega a la pagina de citas del Ayuntamiento de Madrid
2. Selecciona categoria "Padron y censo" y tramite "Altas, bajas y cambio de domicilio"
3. Busca disponibilidad haciendo click en "consultar oficina con cita mas temprana"
4. Si hay citas disponibles, te envia una notificacion por Telegram

## Configuracion inicial

### 1. Crear bot de Telegram

1. Abre Telegram y busca `@BotFather`
2. Envia `/newbot`
3. Sigue las instrucciones para nombrar tu bot
4. Copia el **token** que te da (ej: `123456789:ABCdefGHIjklMNO...`)

### 2. Obtener tu Chat ID

1. Busca tu bot en Telegram y enviale cualquier mensaje (ej: "hola")
2. Visita en el navegador:
   ```
   https://api.telegram.org/bot<TU_TOKEN>/getUpdates
   ```
3. Busca `"chat":{"id":XXXXXXXX}` - ese numero es tu `CHAT_ID`

### 3. Configurar GitHub Actions (recomendado)

Esta es la forma mas facil - el bot corre en los servidores de GitHub automaticamente, sin necesidad de tener tu computadora encendida.

1. Haz fork de este repositorio o subelo a tu cuenta de GitHub
2. Ve a **Settings > Secrets and variables > Actions**
3. Agrega estos secrets:
   - `TELEGRAM_BOT_TOKEN` = tu token del bot
   - `TELEGRAM_CHAT_ID` = tu chat ID
4. Ve a **Actions** y habilita los workflows
5. El bot se ejecutara automaticamente cada 30 minutos de 7am a 10pm (hora Madrid)

Para ejecutar manualmente: **Actions > Verificar Citas Padron Madrid > Run workflow**

## Modos de ejecucion

### GitHub Actions (recomendado)
- Se ejecuta automaticamente en la nube
- Configurable via `.github/workflows/check-citas.yml`

### Ejecucion local (para testing)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu token y chat_id

# Ejecutar una vez
python run.py --once

# Ejecutar en modo continuo (cada 30 min)
python run.py
```

## Scripts de debug

Para diagnosticar problemas con la pagina del Ayuntamiento:

```bash
# Probar conexion a la pagina
python tests/debug_connection.py

# Explorar el formulario y sus opciones
python tests/debug_form.py

# Ejecutar verificacion completa con logs detallados
python tests/debug_verificacion.py

# Probar envio de mensajes por Telegram
python tests/test_telegram.py
```

## Estructura del proyecto

```
src/
  config.py      # Configuracion y variables de entorno
  browser.py     # Automatizacion del navegador (Selenium)
  checker.py     # Logica de verificacion de citas
  notifier.py    # Envio de notificaciones por Telegram
  main.py        # Punto de entrada y orquestacion

tests/
  debug_*.py     # Scripts de debug

.github/workflows/
  check-citas.yml  # Configuracion de GitHub Actions
```

## Troubleshooting

- **Screenshots**: Se guardan en `screenshots/` cuando hay errores
- **Logs**: Ver `cita_checker.log`
- **La pagina cambio**: Si deja de funcionar, ejecuta `python tests/debug_formulario.py` para ver la estructura actual de la pagina

## Notas

- El bot solo notifica cuando **hay citas disponibles** o si ocurre un error
- Si no hay citas, solo se registra en el log (no te molesta con notificaciones)
- La pagina del Ayuntamiento usa widgets jQuery UI para los selectores

## Links utiles

- Pagina de citas: https://servpub.madrid.es/GNSIS_WBCIUDADANO/tramite.do
- Crear bot Telegram: https://t.me/BotFather
