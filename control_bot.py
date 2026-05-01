import os
from telethon import TelegramClient, events, Button
from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommand, BotCommandScopeDefault
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_ID
from handlers_publish import handle_publish_cb, handle_publish_msg
from handlers_tsterr import handle_tsterr_cb, handle_tsterr_msg
from handlers_mute import handle_mute_cb, handle_mute_msg

account_name = os.environ.get("ACCOUNT_NAME", "unified")
bot = TelegramClient(f"data/{account_name}_control_bot.session", API_ID, API_HASH)
user_states = {}
userbot_ref = None

def set_userbot_ref(ref):
    global userbot_ref
    userbot_ref = ref

def ikb_main():
    return [
        [Button.inline("📢 مشروع النشر التلقائي", b"super_publish")],
        [Button.inline("📚 مشروع التسطير (الردود)", b"super_tsterr")],
        [Button.inline("🔇 مشروع الكتم والحماية", b"super_mute")],
        [Button.inline("🛑 إيقاف جميع العمليات", b"stop_all")]
    ]

@bot.on(events.NewMessage(pattern=r'(?i)^(/start|Start)$'))
async def cmd_start(event):
    if event.sender_id != OWNER_ID: return
    user_states[event.sender_id] = None
    # إرسال رسالة مخفية لحذف الكيبورد الثابت (الأشياء المحددة بالأحمر)
    msg = await event.respond("جاري إزالة الكيبورد القديم...", buttons=Button.clear())
    await msg.delete()
    
    await event.reply("🤖 **أهلاً بك في نظام البوت الموحد**\nاختر المشروع:", buttons=ikb_main())

@bot.on(events.CallbackQuery())
async def on_callback(event):
    if event.sender_id != OWNER_ID: return
    d = event.data
    if d == b"main_menu":
        user_states[event.sender_id] = None
        await event.edit("🤖 **القائمة الرئيسية**", buttons=ikb_main())
        return
    if d == b"stop_all":
        await event.edit("⏳ **جاري إيقاف جميع العمليات...**")
        try:
            stopped = await userbot_ref.stop_all_operations()
            await event.edit(
                f"🛑 **تم إيقاف جميع العمليات بنجاح**\n\n"
                f"العمليات التي تم إيقافها: **{stopped}**\n\n"
                "⚠️ لن يتم استرجاع أي مهام تلقائياً حتى تقوم بتشغيلها يدوياً.",
                buttons=[[Button.inline("⬅️ رجوع للقائمة الرئيسية", b"main_menu")]]
            )
        except Exception as e:
            await event.edit(f"❌ خطأ أثناء الإيقاف: {e}", buttons=[[Button.inline("⬅️ رجوع", b"main_menu")]])
        return
    if await handle_publish_cb(event, d, user_states): return
    if await handle_tsterr_cb(event, d, user_states, userbot_ref): return
    if await handle_mute_cb(event, d, user_states): return

@bot.on(events.NewMessage())
async def on_message(event):
    if event.sender_id != OWNER_ID: return
    state = user_states.get(event.sender_id)
    if not state: return
    if await handle_publish_msg(event, state, user_states): return
    if await handle_tsterr_msg(event, state, user_states): return
    if await handle_mute_msg(event, state, user_states): return

async def start_bot():
    print("🤖 جاري تشغيل بوت التحكم...")
    await bot.start(bot_token=BOT_TOKEN)
    
    # استرجاع أيقونة القائمة الزرقاء التي تحتوي على أمر /start
    try:
        cmd = [BotCommand(command="start", description="رسالة البدء")]
        await bot(SetBotCommandsRequest(
            scope=BotCommandScopeDefault(),
            lang_code='',
            commands=cmd
        ))
    except Exception as e:
        print(f"⚠️ تعذر إعداد زر القائمة: {e}")
        
    print("✅ بوت التحكم يعمل بكامل المميزات!")
