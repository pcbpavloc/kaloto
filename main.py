import sqlite3
from telegram import Update, ChatMember
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

# Conectar o crear la base de datos
conn = sqlite3.connect('users.db')
c = conn.cursor()

# Crear tablas
c.execute('''CREATE TABLE IF NOT EXISTS usuarios_registrados (
             id INTEGER PRIMARY KEY,
             usuario_id INTEGER,
             nombre TEXT
             )''')

c.execute('''CREATE TABLE IF NOT EXISTS violaciones (
             id INTEGER PRIMARY KEY AUTOINCREMENT,
             usuario_id INTEGER,
             violaciones INTEGER DEFAULT 0
             )''')

conn.commit()

# Funciones de ayuda
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("¡Hola! Soy el bot del grupo. Usa /help para ver los comandos disponibles.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Estos son los comandos disponibles:\n/help - Mostrar ayuda\n/tabla1 - Registro de usuarios\n/tabla2 - Registro de usuarios y violaciones\n/agencias - Agencias recomendadas\n/visa - Requisitos de visa de trabajo en Polonia")

async def tabla1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c.execute("SELECT * FROM usuarios_registrados")
    users = c.fetchall()
    message = "Registro de usuarios:\n"
    for user in users:
        message += f"ID: {user[1]}, Nombre: {user[2]}\n"
    await update.message.reply_text(message)

async def tabla2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    c.execute('''SELECT ur.usuario_id, ur.nombre, COALESCE(v.violaciones, 0) as violaciones
                 FROM usuarios_registrados ur
                 LEFT JOIN violaciones v ON ur.usuario_id = v.usuario_id''')
    data = c.fetchall()
    message = "Registro de usuarios y violaciones:\n"
    for row in data:
        message += f"ID: {row[0]}, Nombre: {row[1]}, Violaciones: {row[2]}\n"
    await update.message.reply_text(message)

async def agencias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_photo(photo='https://scontent.fclo9-1.fna.fbcdn.net/v/t39.30808-6/453726036_8046009032148988_3237873706222813850_n.jpg?_nc_cat=106&ccb=1-7&_nc_sid=127cfc&_nc_eui2=AeHetbwZ_ui5W_tpdtYauUDO1bI_JHzQowLVsj8kfNCjArBFCIbDuVPf6jIO_-6Hz97ptro7ap2ISkNKT9rZGhoG&_nc_ohc=SACDBhd5yHcQ7kNvgE2F1Mp&_nc_ht=scontent.fclo9-1.fna&oh=00_AYD_GnfZgSjfbKufwg1l2hjZrCaT8PFOJDuuH-igeUgflw&oe=66B631D6', caption="Estas son las Agencias Recomendadas")

async def visa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_photo(chat_id=update.message.chat_id, photo='https://scontent.fclo9-1.fna.fbcdn.net/v/t39.30808-6/454037789_8046011758815382_3330323696176382568_n.jpg?_nc_cat=103&ccb=1-7&_nc_sid=127cfc&_nc_eui2=AeFPFJF6EVhWiuYEjDcZ1zjF0x-G7q3eZSjTH4burd5lKLN8-YKY35Vcues6CMFNp13qZq9E1b-_pimx9xyzJFXw&_nc_ohc=D4izYVTTGn0Q7kNvgG-_QfY&_nc_ht=scontent.fclo9-1.fna&oh=00_AYBka4jTr8ncbtOzZIop1TMqGaQcUOA16qUAc4x_3JezIQ&oe=66B62CE4', caption="Estos son los requisitos para acceder a una visa de trabajo en Polonia")
    await context.bot.send_photo(chat_id=update.message.chat_id, photo='https://scontent.fclo9-1.fna.fbcdn.net/v/t39.30808-6/454322074_8046011755482049_22342759728760974_n.jpg?_nc_cat=100&ccb=1-7&_nc_sid=127cfc&_nc_eui2=AeFEuZq-tB8r3h9nkcIPF2rQXxe1IxryHClfF7UjGvIcKVUGiOV7rJusFFtswPs_JqsCrPb5yCZ82_s8zqSS4Lua&_nc_ohc=nYCqrVkX77EQ7kNvgFT7VpI&_nc_ht=scontent.fclo9-1.fna&oh=00_AYAyXINYpqxL722Zvk2SdcHiMQat_tIcfUMUo5YfLISpQQ&oe=66B61BBB', caption="Más información sobre la visa de trabajo en Polonia")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    name = update.message.from_user.full_name

    # Insertar o actualizar usuario en la base de datos
    c.execute("INSERT OR IGNORE INTO usuarios_registrados (usuario_id, nombre) VALUES (?, ?)", (user_id, name))
    c.execute("INSERT OR IGNORE INTO violaciones (usuario_id, violaciones) VALUES (?, 0)", (user_id,))
    conn.commit()

    text = update.message.text
    if any(word in text for word in ['http', 'www', '.com', '.net', '+', '-', ' ']):
        try:
            await update.message.delete()
        except Exception as e:
            print(f"Error deleting message: {e}")

        c.execute("SELECT violaciones FROM violaciones WHERE usuario_id = ?", (user_id,))
        result = c.fetchone()
        if result:
            violations = result[0] + 1
            c.execute("UPDATE violaciones SET violaciones = ? WHERE usuario_id = ?", (violations, user_id))
        else:
            violations = 1
            c.execute("INSERT INTO violaciones (usuario_id, violaciones) VALUES (?, ?)", (user_id, violations))

        conn.commit()

        if violations >= 3:
            chat_member = await context.bot.get_chat_member(update.message.chat.id, user_id)
            if chat_member.status not in [ChatMember.OWNER, ChatMember.ADMINISTRATOR]:
                if update.message.chat.type in ['group', 'supergroup']:
                    try:
                        await context.bot.ban_chat_member(chat_id=update.message.chat.id, user_id=user_id)
                        await update.message.reply_text(f"El usuario {name} ha sido baneado por acumular {violations} violaciones.")
                        
                        # Eliminar el registro del usuario baneado
                        c.execute("DELETE FROM usuarios_registrados WHERE usuario_id = ?", (user_id,))
                        c.execute("DELETE FROM violaciones WHERE usuario_id = ?", (user_id,))
                        conn.commit()
                    except Exception as e:
                        print(f"Error banning user: {e}")
                else:
                    await update.message.reply_text(f"El usuario {name} tiene {violations} violaciones. No se puede banear en chats privados.")
            else:
                await update.message.reply_text(f"No se puede banear al propietario o administrador del chat. El usuario {name} tiene {violations} violaciones.")
        else:
            await update.message.reply_text(f"URL o número de teléfono no permitido. Violaciones: {violations}")

def main() -> None:
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Comandos disponibles para todos los usuarios
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tabla1", tabla1))
    application.add_handler(CommandHandler("tabla2", tabla2))
    application.add_handler(CommandHandler("agencias", agencias))
    application.add_handler(CommandHandler("visa", visa))
    
    # Manejo de mensajes
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == '__main__':
    main()
