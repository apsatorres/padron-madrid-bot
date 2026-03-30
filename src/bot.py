"""Interactive Telegram bot with inline keyboard configuration."""

import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes,
)

from .config import logger, TELEGRAM_BOT_TOKEN
from .db import init_db, add_check, get_checks, remove_check, update_offices, set_active
from .browser import fetch_site_options

# Conversation states
SELECT_CATEGORY, SELECT_PROCEDURE, SELECT_OFFICES, CONFIRM = range(4)

# Cache for site options (populated on first /add)
_site_cache = {}


def _keyboard_grid(items, prefix, cols=2):
    """Build an InlineKeyboardMarkup grid from a list of items."""
    buttons = [
        InlineKeyboardButton(item, callback_data=f"{prefix}:{item}")
        for item in items
    ]
    rows = [buttons[i:i + cols] for i in range(0, len(buttons), cols)]
    return InlineKeyboardMarkup(rows)


def _office_keyboard(all_offices, selected):
    """Build a multi-select keyboard for offices."""
    buttons = []
    for office in all_offices:
        check = "✓ " if office in selected else ""
        buttons.append(
            InlineKeyboardButton(
                f"{check}{office}",
                callback_data=f"office:{office}"
            )
        )
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([
        InlineKeyboardButton("✓ Listo", callback_data="office:__done__"),
        InlineKeyboardButton("Cualquiera (sin preferencia)", callback_data="office:__any__"),
    ])
    return InlineKeyboardMarkup(rows)


async def _ensure_cache(category=None):
    """Populate the site options cache if needed."""
    if "categories" not in _site_cache:
        logger.info("Fetching categories from site...")
        data = fetch_site_options()
        _site_cache["categories"] = data.get("categories", [])

    if category and category not in _site_cache:
        logger.info(f"Fetching procedures/offices for '{category}'...")
        data = fetch_site_options(category)
        _site_cache[category] = {
            "procedures": data.get("procedures", []),
            "offices": data.get("offices", []),
        }


# --- Command handlers ---

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Cita Madrid Bot</b>\n\n"
        "Te aviso cuando haya citas disponibles.\n\n"
        "Comandos:\n"
        "/add - Añadir un trámite a vigilar\n"
        "/list - Ver tus trámites configurados\n"
        "/remove - Eliminar un trámite\n"
        "/pause - Pausar un trámite\n"
        "/resume - Reanudar un trámite pausado",
        parse_mode="HTML",
    )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    checks = get_checks(chat_id)
    if not checks:
        await update.message.reply_text("No tienes trámites configurados. Usa /add para añadir uno.")
        return

    lines = ["<b>Tus trámites:</b>\n"]
    for c in checks:
        status = "⏸ pausado" if not c["active"] else "✓ activo"
        offices = ", ".join(c["preferred_offices"]) if c["preferred_offices"] else "cualquiera"
        lines.append(
            f"<b>#{c['id']}</b> [{status}]\n"
            f"  {c['category']} / {c['procedure']}\n"
            f"  Oficinas: {offices}\n"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    checks = get_checks(chat_id)
    if not checks:
        await update.message.reply_text("No tienes trámites configurados.")
        return

    buttons = [
        [InlineKeyboardButton(
            f"#{c['id']} {c['category']} / {c['procedure']}",
            callback_data=f"rm:{c['id']}"
        )]
        for c in checks
    ]
    buttons.append([InlineKeyboardButton("Cancelar", callback_data="rm:cancel")])
    await update.message.reply_text(
        "Selecciona el trámite a eliminar:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.removeprefix("rm:")

    if data == "cancel":
        await query.edit_message_text("Cancelado.")
        return

    chat_id = update.effective_chat.id
    if remove_check(chat_id, int(data)):
        await query.edit_message_text(f"Trámite #{data} eliminado.")
    else:
        await query.edit_message_text("No se encontró ese trámite.")


async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _toggle_active(update, active=False, label="pausado")


async def cmd_resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _toggle_active(update, active=True, label="reanudado")


async def _toggle_active(update, active, label):
    chat_id = update.effective_chat.id
    checks = get_checks(chat_id)
    target = [c for c in checks if c["active"] != active]
    if not target:
        await update.message.reply_text(f"No hay trámites para {'reanudar' if active else 'pausar'}.")
        return

    buttons = [
        [InlineKeyboardButton(
            f"#{c['id']} {c['category']} / {c['procedure']}",
            callback_data=f"toggle:{c['id']}:{1 if active else 0}"
        )]
        for c in target
    ]
    buttons.append([InlineKeyboardButton("Cancelar", callback_data="toggle:cancel")])
    await update.message.reply_text(
        f"Selecciona el trámite a {'reanudar' if active else 'pausar'}:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cb_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.removeprefix("toggle:")

    if data == "cancel":
        await query.edit_message_text("Cancelado.")
        return

    parts = data.split(":")
    check_id, active_val = int(parts[0]), bool(int(parts[1]))
    chat_id = update.effective_chat.id
    label = "reanudado" if active_val else "pausado"

    if set_active(chat_id, check_id, active_val):
        await query.edit_message_text(f"Trámite #{check_id} {label}.")
    else:
        await query.edit_message_text("No se encontró ese trámite.")


# --- /add conversation ---

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cargando categorías...")
    await _ensure_cache()

    categories = _site_cache.get("categories", [])
    if not categories:
        await update.message.reply_text("No se pudieron cargar las categorías. Inténtalo más tarde.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Selecciona una <b>categoría</b>:",
        reply_markup=_keyboard_grid(categories, "cat", cols=2),
        parse_mode="HTML",
    )
    return SELECT_CATEGORY


async def add_select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.removeprefix("cat:")

    context.user_data["add_category"] = category
    await query.edit_message_text(f"Categoría: <b>{category}</b>\n\nCargando trámites...", parse_mode="HTML")

    await _ensure_cache(category)
    procedures = _site_cache.get(category, {}).get("procedures", [])

    if not procedures:
        await query.edit_message_text(f"No se encontraron trámites para '{category}'.")
        return ConversationHandler.END

    await query.edit_message_text(
        f"Categoría: <b>{category}</b>\n\nSelecciona un <b>trámite</b>:",
        reply_markup=_keyboard_grid(procedures, "proc", cols=1),
        parse_mode="HTML",
    )
    return SELECT_PROCEDURE


async def add_select_procedure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    procedure = query.data.removeprefix("proc:")

    category = context.user_data["add_category"]
    context.user_data["add_procedure"] = procedure
    context.user_data["add_offices"] = set()

    offices = _site_cache.get(category, {}).get("offices", [])
    if not offices:
        check_id = add_check(query.from_user.id, category, procedure, [])
        await query.edit_message_text(
            f"<b>Trámite añadido (#{check_id})</b>\n\n"
            f"{category} / {procedure}\n"
            f"Oficinas: cualquiera",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    await query.edit_message_text(
        f"Categoría: <b>{category}</b>\n"
        f"Trámite: <b>{procedure}</b>\n\n"
        f"Selecciona <b>oficinas preferidas</b> (puedes elegir varias):",
        reply_markup=_office_keyboard(offices, set()),
        parse_mode="HTML",
    )
    return SELECT_OFFICES


async def add_select_offices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.removeprefix("office:")

    category = context.user_data["add_category"]
    procedure = context.user_data["add_procedure"]
    selected = context.user_data["add_offices"]

    if data == "__done__":
        offices_list = sorted(selected)
        check_id = add_check(query.from_user.id, category, procedure, offices_list)
        offices_text = ", ".join(offices_list) if offices_list else "cualquiera"
        await query.edit_message_text(
            f"<b>Trámite añadido (#{check_id})</b>\n\n"
            f"{category} / {procedure}\n"
            f"Oficinas: {offices_text}",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    if data == "__any__":
        check_id = add_check(query.from_user.id, category, procedure, [])
        await query.edit_message_text(
            f"<b>Trámite añadido (#{check_id})</b>\n\n"
            f"{category} / {procedure}\n"
            f"Oficinas: cualquiera",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    # Toggle office selection
    if data in selected:
        selected.discard(data)
    else:
        selected.add(data)

    all_offices = _site_cache.get(category, {}).get("offices", [])
    await query.edit_message_reply_markup(
        reply_markup=_office_keyboard(all_offices, selected)
    )
    return SELECT_OFFICES


async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Añadir trámite cancelado.")
    return ConversationHandler.END


def create_bot():
    """Build and return the Telegram Application."""
    init_db()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Simple commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("pause", cmd_pause))
    app.add_handler(CommandHandler("resume", cmd_resume))

    # Callback queries for remove/toggle
    app.add_handler(CallbackQueryHandler(cb_remove, pattern=r"^rm:"))
    app.add_handler(CallbackQueryHandler(cb_toggle, pattern=r"^toggle:"))

    # /add conversation
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            SELECT_CATEGORY: [CallbackQueryHandler(add_select_category, pattern=r"^cat:")],
            SELECT_PROCEDURE: [CallbackQueryHandler(add_select_procedure, pattern=r"^proc:")],
            SELECT_OFFICES: [CallbackQueryHandler(add_select_offices, pattern=r"^office:")],
        },
        fallbacks=[CommandHandler("cancel", add_cancel)],
        per_message=False,
    )
    app.add_handler(add_conv)

    return app
