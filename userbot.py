import os
import asyncio
import random
import logging
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError, ChatWriteForbiddenError, UserBannedInChannelError,
    ChannelPrivateError, MessageDeleteForbiddenError
)
from telethon.errors.rpcerrorlist import RPCError
from telethon.sessions import StringSession
from telethon.tl.types import (
    DocumentAttributeSticker, InputStickerSetEmpty,
    DocumentAttributeVideo, DocumentAttributeFilename
)
from config import API_ID, API_HASH, SESSION_NAME, STRING_SESSION, OWNER_ID
from database import DataManager
from distributions import (gaussian_delay, gaussian_pick_index, weighted_pick_index,
                           weibull_delay, weibull_security_delay, weibull_retry_delay,
                           length_based_delay, random_range_delay, smart_content_delay)

logger = logging.getLogger(__name__)
db = DataManager()

userbot = None
if STRING_SESSION and len(STRING_SESSION) > 50:
    try:
        userbot = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    except ValueError:
        logger.warning("Invalid STRING_SESSION provided. Falling back to SQLite session.")
        userbot = TelegramClient(SESSION_NAME, API_ID, API_HASH)
else:
    userbot = TelegramClient(SESSION_NAME, API_ID, API_HASH)


emergency_stop_flag = False
active_tasks = {}
latest_user_msgs = {}
_publish_task = None

# تخزين مؤقت لمعلومات الحساب لتجنب استدعاء API متكرر
_me_cache = None

# الحد الأقصى للمهام المتزامنة
MAX_CONCURRENT_TASKS = 5
# الحد الأقصى لتتبع الرسائل في الذاكرة
MAX_TRACKED_CHATS = 200
MAX_USERS_PER_CHAT = 100

async def get_me_cached():
    """الحصول على معلومات الحساب مع تخزين مؤقت"""
    global _me_cache
    if _me_cache is None:
        _me_cache = await userbot.get_me()
    return _me_cache

def _cleanup_latest_msgs():
    """تنظيف ذاكرة تتبع الرسائل لمنع النمو غير المحدود"""
    global latest_user_msgs
    if len(latest_user_msgs) > MAX_TRACKED_CHATS:
        # الاحتفاظ بآخر النصف فقط
        keys = list(latest_user_msgs.keys())
        for k in keys[:len(keys) // 2]:
            del latest_user_msgs[k]
    # تنظيف المستخدمين داخل كل مجموعة
    for cid in latest_user_msgs:
        if len(latest_user_msgs[cid]) > MAX_USERS_PER_CHAT:
            items = list(latest_user_msgs[cid].items())
            latest_user_msgs[cid] = dict(items[-(MAX_USERS_PER_CHAT // 2):])

# ═══════════════════════════════════════
# دالة إظهار "جاري الكتابة" وإرسال
# ═══════════════════════════════════════
def _get_sticker_send_kwargs(file_path):
    """بناء معاملات الإرسال الصحيحة للملصقات حسب نوع الملف
    .webp = ملصق ثابت
    .webm = ملصق فيديو (يحتاج DocumentAttributeVideo)
    .tgs  = ملصق متحرك (يحتاج mime_type خاص)
    يُرجع None إذا لم يكن الملف ملصقاً
    """
    if not file_path:
        return None
    ext = os.path.splitext(file_path)[1].lower()
    
    sticker_attr = DocumentAttributeSticker(
        alt='⭐',
        stickerset=InputStickerSetEmpty()
    )
    
    if ext == '.webp':
        # ملصق ثابت (Static Sticker)
        return {
            'attributes': [sticker_attr],
            'force_document': False
        }
    elif ext == '.webm':
        # ملصق فيديو (Video Sticker) - يحتاج أبعاد 512x512
        video_attr = DocumentAttributeVideo(
            duration=0,
            w=512,
            h=512,
            round_message=False,
            supports_streaming=False
        )
        return {
            'attributes': [sticker_attr, video_attr],
            'force_document': False,
            'mime_type': 'video/webm'
        }
    elif ext == '.tgs':
        # ملصق متحرك (Animated Sticker)
        return {
            'attributes': [
                sticker_attr,
                DocumentAttributeFilename(file_name='sticker.tgs')
            ],
            'force_document': False,
            'mime_type': 'application/x-tgsticker'
        }
    return None

async def send_with_typing(client, chat_id, delay, reply_to=None, text=None, file_path=None, item_type=None):
    """إرسال مع إظهار Typing... للطرف الآخر مع إعادة المحاولة"""
    MAX_RETRIES = 3
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            # إظهار جاري الكتابة أثناء التأخير (فقط في المحاولة الأولى)
            if attempt == 0:
                action_type = 'typing' if text else 'document'
                remaining = delay
                while remaining > 0:
                    if emergency_stop_flag:
                        raise asyncio.CancelledError()
                    chunk = min(remaining, 4.0)
                    try:
                        async with client.action(chat_id, action_type):
                            await asyncio.sleep(chunk)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        await asyncio.sleep(chunk)
                    remaining -= chunk
            else:
                # انتظار قصير قبل إعادة المحاولة
                await asyncio.sleep(random.uniform(2, 5))

            # إرسال المحتوى
            if file_path:
                sticker_kwargs = _get_sticker_send_kwargs(file_path)
                is_sticker = (item_type == "sticker") or (sticker_kwargs is not None)
                
                if is_sticker and sticker_kwargs:
                    # إرسال كملصق حقيقي مع الخصائص الصحيحة لكل نوع
                    msg = await client.send_file(
                        chat_id, file_path,
                        reply_to=reply_to,
                        **sticker_kwargs
                    )
                else:
                    msg = await client.send_file(chat_id, file_path, reply_to=reply_to)
            elif text:
                msg = await client.send_message(chat_id, text, reply_to=reply_to)
            else:
                return None
            return msg
        except FloodWaitError as e:
            logger.warning(f"FloodWait in send_with_typing: {e.seconds}s (attempt {attempt+1})")
            await asyncio.sleep(e.seconds + random.uniform(2, 5))
            last_error = e
            continue
        except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError) as e:
            logger.warning(f"Permission error: {e}")
            return None  # لا فائدة من إعادة المحاولة
        except ConnectionError as e:
            logger.error(f"Connection lost during send (attempt {attempt+1})")
            last_error = e
            await asyncio.sleep(random.uniform(5, 15))
            continue
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Send error (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            last_error = e
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(random.uniform(2, 5))
                continue
    
    logger.error(f"Send failed after {MAX_RETRIES} attempts: {last_error}")
    return None

def calc_sub_delay(text, settings):
    """حساب التأخير لتسطير السب"""
    mode = settings.get("sub_delay_mode", "gaussian")
    mn = settings.get("sub_delay_min", 2.0)
    mx = settings.get("sub_delay_max", 15.0)
    if mode == "length":
        return length_based_delay(len(text), mn, mx)
    else:  # gaussian
        return gaussian_delay(mn, mx)

def calc_seq_delay(item_type, content_len, settings):
    """حساب التأخير للتسطير المتسلسل بناءً على نوع المحتوى وطوله"""
    mode = settings.get("seq_delay_mode", "length")
    mn = settings.get("seq_delay_min", 2.0)
    mx = settings.get("seq_delay_max", 15.0)
    if mode == "length":
        return smart_content_delay(item_type, content_len, mn, mx)
    else:  # random_range
        return random_range_delay(mn, mx)

# ══════════════════════════════════════
# 1. مشروع الكتم - حذف رسائل المكتومين
# ══════════════════════════════════════
@userbot.on(events.NewMessage(incoming=True))
async def handle_mute_messages(event):
    if getattr(event, 'out', False): return
    if not event.sender_id or event.sender_id == OWNER_ID: return
    
    if event.is_private:
        if db.is_dm_muted(event.sender_id):
            try: await event.delete()
            except Exception: pass
            raise events.StopPropagation
    elif event.is_group or getattr(event, 'is_channel', False):
        if db.is_group_muted(event.chat_id, event.sender_id):
            try: await event.delete()
            except Exception: pass
            raise events.StopPropagation

@userbot.on(events.NewMessage(outgoing=True, pattern=r'^\.كتم$'))
async def cmd_mute_new(event):
    if event.is_group or getattr(event, 'is_channel', False):
        if not event.is_reply: 
            try: await event.delete()
            except Exception: pass
            return
        replied = await event.get_reply_message()
        if not replied or not replied.sender_id or replied.sender_id == OWNER_ID: 
            try: await event.delete()
            except Exception: pass
            return
            
        chat = await event.get_chat()
        can_delete = False
        if getattr(chat, 'creator', False):
            can_delete = True
        else:
            try:
                p = await event.client.get_permissions(event.chat_id, 'me')
                can_delete = getattr(p, 'delete_messages', False) or getattr(p, 'is_creator', False)
            except Exception:
                can_delete = False
                
        if not can_delete:
            try:
                await event.edit("❌ لا أملك صلاحية حذف الرسائل في هذه المجموعة.")
                await asyncio.sleep(2)
                await event.delete()
            except Exception: pass
            return

        db.add_group_mute(event.chat_id, replied.sender_id)
        try: await event.delete()
        except Exception: pass
        
    elif event.is_private:
        target_id = event.chat_id
        if target_id == OWNER_ID: 
            try: await event.delete()
            except Exception: pass
            return
        db.add_dm_mute(target_id)
        try: await event.delete()
        except Exception: pass

@userbot.on(events.NewMessage(outgoing=True, pattern=r'^\.رف$'))
async def cmd_unmute_new(event):
    if event.is_group or getattr(event, 'is_channel', False):
        if not event.is_reply: 
            try: await event.delete()
            except Exception: pass
            return
        replied = await event.get_reply_message()
        if not replied or not replied.sender_id: 
            try: await event.delete()
            except Exception: pass
            return
        db.remove_group_mute(event.chat_id, replied.sender_id)
        db.remove_group_mute("all", replied.sender_id)
        try: await event.delete()
        except Exception: pass
        
    elif event.is_private:
        target_id = event.chat_id
        db.remove_dm_mute(target_id)
        try: await event.delete()
        except Exception: pass

@userbot.on(events.NewMessage(outgoing=True, pattern=r'^هخ$'))
async def cmd_emergency_stop(event):
    """إيقاف فوري لجميع مهام التسطير النشطة"""
    global emergency_stop_flag
    emergency_stop_flag = True
    for tid, task in list(active_tasks.items()):
        if not task.done():
            task.cancel()
    active_tasks.clear()
    db.clear_running_jobs()
    # إعادة تعيين العلم بعد الإيقاف
    await asyncio.sleep(1)
    emergency_stop_flag = False

async def stop_all_operations():
    """إيقاف جميع العمليات - يُستدعى من بوت التحكم"""
    global emergency_stop_flag, _publish_task
    emergency_stop_flag = True
    stopped_count = 0
    # إيقاف التسطير
    for tid, task in list(active_tasks.items()):
        if not task.done():
            task.cancel()
            stopped_count += 1
    active_tasks.clear()
    # إيقاف النشر
    if db.is_publishing_enabled():
        db.set_publishing_enabled(False)
        stopped_count += 1
    # مسح المهام المحفوظة ووضع علامة الإيقاف
    db.clear_running_jobs()
    db.set_emergency_stopped(True)
    await asyncio.sleep(1)
    emergency_stop_flag = False
    return stopped_count

# ══════════════════════════════════════
# 2. مشروع التسطير - تسطير السب + المتسلسل
# ══════════════════════════════════════
@userbot.on(events.NewMessage(func=lambda e: (e.is_group or e.is_channel) and not e.out))
async def track_user_msgs(event):
    if not event.sender_id: return
    cid = event.chat_id
    uid = event.sender_id
    if cid not in latest_user_msgs: latest_user_msgs[cid] = {}
    latest_user_msgs[cid][uid] = event.id
    # تنظيف دوري
    _cleanup_latest_msgs()

@userbot.on(events.NewMessage(outgoing=True))
async def handle_tsterr_commands(event):
    global emergency_stop_flag
    if not event.text: return
    text = event.text.strip()
    
    # تجنب التعارض مع أوامر أخرى
    if text in ('.كتم', '.رف', 'هخ'):
        return
    
    settings = db.get_tsterr_settings()

    # ─── تحديد الهدف ───
    target_uid = None
    reply_to_id = None
    if event.is_group or getattr(event, 'is_channel', False):
        if event.is_reply:
            replied = await event.get_reply_message()
            if replied and replied.sender_id:
                target_uid = replied.sender_id
                reply_to_id = replied.id
    elif event.is_private:
        target_uid = event.chat_id

    # ─── التحقق من الحد الأقصى للمهام ───
    running_tasks = sum(1 for t in active_tasks.values() if not t.done())
    if running_tasks >= MAX_CONCURRENT_TASKS:
        # لا نبدأ مهام جديدة إذا وصلنا للحد
        return

    # ─── كلمات تسطير السب ───
    kw_male = settings.get("activation_keyword_male", "")
    kw_female = settings.get("activation_keyword_female", "")

    if text == kw_male and target_uid:
        tid = f"random_male_{target_uid}_{event.chat_id}"
        if tid in active_tasks and not active_tasks[tid].done():
            active_tasks[tid].cancel()
            return
        db.set_emergency_stopped(False)
        db.save_running_job(tid, {"type":"random","gender":"male","chat_id":event.chat_id,"target_uid":target_uid})
        task = asyncio.create_task(_run_random(event.client, event.chat_id, target_uid, reply_to_id, tid, "male"))
        active_tasks[tid] = task
        return

    if text == kw_female and target_uid:
        tid = f"random_female_{target_uid}_{event.chat_id}"
        if tid in active_tasks and not active_tasks[tid].done():
            active_tasks[tid].cancel()
            return
        db.set_emergency_stopped(False)
        db.save_running_job(tid, {"type":"random","gender":"female","chat_id":event.chat_id,"target_uid":target_uid})
        task = asyncio.create_task(_run_random(event.client, event.chat_id, target_uid, reply_to_id, tid, "female"))
        active_tasks[tid] = task
        return

    # ─── كلمات التسطير المتسلسل (العنوان = كلمة التفعيل) ───
    titles = db.get_sequential_titles()
    if text in titles:
        chat_target = target_uid or event.chat_id
        tid = f"seq_{text}_{chat_target}_{event.chat_id}"
        if tid in active_tasks and not active_tasks[tid].done():
            active_tasks[tid].cancel()
            return
        db.set_emergency_stopped(False)
        db.save_running_job(tid, {"type":"sequential","section_name":text,"chat_id":event.chat_id,"target_uid":chat_target})
        task = asyncio.create_task(_run_sequential(event.client, event.chat_id, chat_target, reply_to_id, text, tid))
        active_tasks[tid] = task
        return


async def _run_random(client, chat_id, target_uid, reply_to_id, task_id, gender):
    """تشغيل تسطير السب (عشوائي) مع حماية الحساب"""
    global emergency_stop_flag
    start = datetime.now()
    count = 0
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 3
    try:
        while not emergency_stop_flag:
            texts = [t for t in db.get_random_texts(gender) if t.strip()]
            if not texts: break
            chosen = random.choice(texts)
            s = db.get_tsterr_settings()
            delay = calc_sub_delay(chosen, s)
            rid = latest_user_msgs.get(chat_id, {}).get(target_uid, reply_to_id)
            
            try:
                msg = await send_with_typing(client, chat_id, delay, reply_to=rid, text=chosen)
                if msg:
                    db.track_message(chat_id, msg.id)
                    count += 1
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
            except FloodWaitError as e:
                logger.warning(f"FloodWait in random tsterr: {e.seconds}s - stopping task")
                await asyncio.sleep(e.seconds + random.uniform(5, 15))
                break  # إيقاف المهمة بعد FloodWait
            except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError):
                logger.warning(f"Permission lost in chat {chat_id} - stopping task")
                break
            except ConnectionError:
                logger.error("Connection error in random tsterr")
                await asyncio.sleep(random.uniform(10, 30))
                consecutive_errors += 1
            except Exception as e:
                logger.error(f"Error in random tsterr: {e}")
                consecutive_errors += 1
            
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.warning(f"Too many consecutive errors ({consecutive_errors}) - stopping task {task_id}")
                break
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Random tsterr fatal error: {e}")
    finally:
        if count > 0:
            label = "ذكور" if gender == "male" else "إناث"
            db.add_report({"username": str(target_uid), "start_time": start.strftime("%I:%M %p"),
                           "end_time": datetime.now().strftime("%I:%M %p"), "count": count, "type": f"تسطير سب ({label})"})
        active_tasks.pop(task_id, None)
        db.remove_running_job(task_id)


async def _run_sequential(client, chat_id, target_uid, reply_to_id, section_name, task_id):
    """تشغيل التسطير المتسلسل مع حماية الحساب وإعادة المحاولة"""
    global emergency_stop_flag
    start = datetime.now()
    count = 0
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 5
    try:
        items = db.get_sequential_items(section_name)
        for idx, item in enumerate(items):
            if emergency_stop_flag: break
            s = db.get_tsterr_settings()
            content_len = len(item.get("content", "")) if item["type"] == "text" else 0
            delay = calc_seq_delay(item["type"], content_len, s)
            rid = latest_user_msgs.get(chat_id, {}).get(target_uid, reply_to_id)

            try:
                msg = None
                if item["type"] == "text":
                    msg = await send_with_typing(client, chat_id, delay, reply_to=rid, text=item["content"])
                else:
                    fp = item.get("file_path", "")
                    if fp and os.path.exists(fp):
                        msg = await send_with_typing(client, chat_id, delay, reply_to=rid, file_path=fp, item_type=item["type"])
                    else:
                        logger.warning(f"Sequential item {idx+1}: file not found: {fp}")
                        continue  # تخطي الملف المفقود بدلاً من احتسابه كخطأ

                if msg:
                    db.track_message(chat_id, msg.id)
                    count += 1
                    consecutive_errors = 0
                    logger.info(f"Sequential [{section_name}] item {idx+1}/{len(items)} sent OK")
                else:
                    consecutive_errors += 1
                    logger.warning(f"Sequential [{section_name}] item {idx+1}/{len(items)} returned None")
            except FloodWaitError as e:
                logger.warning(f"FloodWait in sequential tsterr: {e.seconds}s - waiting then continuing")
                await asyncio.sleep(e.seconds + random.uniform(5, 15))
                consecutive_errors += 1
                continue  # استكمال بدلاً من التوقف
            except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError):
                logger.warning(f"Permission lost in chat {chat_id} - stopping sequential")
                break
            except ConnectionError:
                logger.error(f"Connection error in sequential item {idx+1} - waiting then continuing")
                await asyncio.sleep(random.uniform(10, 30))
                consecutive_errors += 1
                continue  # استكمال بدلاً من التوقف
            except Exception as e:
                logger.error(f"Sequential item {idx+1} error: {e}")
                consecutive_errors += 1
                
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                logger.warning(f"Too many consecutive errors ({consecutive_errors}) - stopping sequential {task_id}")
                break
                
                
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Sequential tsterr fatal error: {e}")
    finally:
        if count > 0:
            db.add_report({"username": str(target_uid), "start_time": start.strftime("%I:%M %p"),
                           "end_time": datetime.now().strftime("%I:%M %p"), "count": count, "type": f"متسلسل ({section_name})"})
        active_tasks.pop(task_id, None)
        db.remove_running_job(task_id)

# ══════════════════════════════════════
# 3. مشروع النشر التلقائي - توزيعات ذكية
# ══════════════════════════════════════
_group_publish_history = {}

async def publish_loop():
    """حلقة النشر التلقائي مع استعادة الحالة بعد الانقطاع وحماية شاملة"""
    consecutive_cycle_errors = 0
    
    while True:
        try:
            if not db.is_publishing_enabled():
                await asyncio.sleep(5)
                consecutive_cycle_errors = 0
                continue
                
            groups = db.get_enabled_publish_groups()
            messages = db.get_active_messages()
            if not groups or not messages:
                # انتظار بصمت دون إيقاف البوت حتى يتم إضافة محتوى
                await asyncio.sleep(10)
                continue
                
            mn, mx = db.get_publish_delays()
            mn = max(mn, 15.0)
            mx = max(mx, mn + 10.0)

            # ─── استرجاع الحالة ───
            state = db.get_publish_state()
            remaining_groups = state.get("remaining_groups", [])
            current_msg_idx = state.get("current_msg_idx", 0)

            # تصفية المجموعات المحذوفة أو المعطلة
            valid_gids = [str(g["group_id"]) for g in groups]
            remaining_groups = [gid for gid in remaining_groups if gid in valid_gids]

            # بدء دورة جديدة إذا انتهت الدورة الحالية
            if not remaining_groups:
                remaining_groups = valid_gids.copy()
                random.shuffle(remaining_groups)
                db.save_publish_state(remaining_groups, current_msg_idx)

            while remaining_groups:
                if not db.is_publishing_enabled(): break

                current_gid = remaining_groups[0]
                g = next((g for g in groups if str(g["group_id"]) == current_gid), None)
                if not g:
                    remaining_groups.pop(0)
                    db.save_publish_state(remaining_groups, current_msg_idx)
                    continue

                if current_msg_idx >= len(messages):
                    current_msg_idx = 0
                
                msg = messages[current_msg_idx]["content"]

                try:
                    gid = int(g["group_id"]) if g["group_id"].lstrip('-').isdigit() else g["group_id"]
                    typing_duration = random.uniform(1.5, 4.0)
                    try:
                        async with userbot.action(gid, 'typing'):
                            await asyncio.sleep(typing_duration)
                    except (RPCError, ConnectionError):
                        await asyncio.sleep(typing_duration)
                    
                    await userbot.send_message(gid, msg)
                    db.add_publish_log(g["group_id"], g.get("group_name",""), msg[:100], "success")
                    logger.info(f"✅ نشر في: {g.get('group_name') or g['group_id']}")
                    consecutive_cycle_errors = 0
                    
                    # حفظ الحالة بعد النشر بنجاح للانتقال للمجموعة التالية والرسالة التالية
                    remaining_groups.pop(0)
                    current_msg_idx = (current_msg_idx + 1) % len(messages)
                    db.save_publish_state(remaining_groups, current_msg_idx)
                    
                except FloodWaitError as e:
                    wait = e.seconds + random.uniform(10, 30)
                    logger.warning(f"⚠️ FloodWait {e.seconds}s - انتظار: {wait:.1f}s للاستكمال")
                    await asyncio.sleep(wait)
                    continue
                except (ChatWriteForbiddenError, UserBannedInChannelError, ChannelPrivateError) as e:
                    db.add_publish_log(g["group_id"], g.get("group_name",""), msg[:100], "forbidden")
                    logger.warning(f"⛔ ممنوع من الإرسال في {g['group_id']}")
                    remaining_groups.pop(0)
                    db.save_publish_state(remaining_groups, current_msg_idx)
                    await asyncio.sleep(random.uniform(2, 5))
                    continue
                except ConnectionError:
                    logger.error("❌ فقدان الاتصال أثناء النشر، سيتم الاستكمال لاحقاً")
                    await asyncio.sleep(random.uniform(15, 45))
                    consecutive_cycle_errors += 1
                    break
                except Exception as e:
                    db.add_publish_log(g["group_id"], g.get("group_name",""), msg[:100], "failed")
                    logger.error(f"❌ فشل: {g['group_id']}: {e}")
                    remaining_groups.pop(0)
                    db.save_publish_state(remaining_groups, current_msg_idx)
                    await asyncio.sleep(weibull_security_delay(3.0, 12.0))

                # تأخير آمن بين المجموعات
                delay = max(mn, weibull_delay(float(mn), float(mx), shape=1.5) + random.uniform(-2.0, 5.0))
                await asyncio.sleep(delay)

            if not remaining_groups and db.is_publishing_enabled():
                await asyncio.sleep(weibull_security_delay(8.0, 25.0))
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Publish loop error: {e}")
            consecutive_cycle_errors += 1
            await asyncio.sleep(min(30 * consecutive_cycle_errors, 300))
            if consecutive_cycle_errors >= 10:
                consecutive_cycle_errors = 0

# ─── الرد التلقائي على الكلمات المفتاحية ───
@userbot.on(events.NewMessage(incoming=True, func=lambda e: not e.is_private))
async def handle_auto_reply(event):
    if not db.is_auto_reply_enabled(): return
    if not event.message or not event.message.text: return
    # استخدام cache بدلاً من استدعاء API كل مرة
    me = await get_me_cached()
    if me and event.sender_id == me.id: return
    enabled_groups = db.get_enabled_publish_groups()
    if not enabled_groups: return
    chat_id_str = str(event.chat_id)
    group_ids = [str(g["group_id"]) for g in enabled_groups]
    if chat_id_str not in group_ids: return
    keywords = db.get_active_auto_reply_keywords()
    if not keywords: return
    msg_text = event.message.text.lower()
    for kw in keywords:
        if kw["keyword"].lower() in msg_text:
            uid = str(event.sender_id)
            if db.is_user_replied(uid, kw["keyword"]): continue
            try:
                # Typing قبل الرد بتأخير طبيعي
                typing_delay = weibull_delay(3.0, 10.0, shape=1.5)
                try:
                    async with userbot.action(event.chat_id, 'typing'):
                        await asyncio.sleep(typing_delay)
                except (RPCError, ConnectionError):
                    await asyncio.sleep(typing_delay)
                await event.reply(kw["reply_text"])
                db.mark_user_replied(uid, kw["keyword"], str(event.chat_id))
            except FloodWaitError as e:
                logger.warning(f"FloodWait in auto_reply: {e.seconds}s")
                await asyncio.sleep(e.seconds + random.uniform(5, 10))
            except (ChatWriteForbiddenError, UserBannedInChannelError):
                logger.warning(f"Cannot reply in {event.chat_id}")
            except Exception as e:
                logger.error(f"Auto reply error: {e}")
            break

async def resume_saved_jobs():
    """استرجاع المهام المحفوظة بعد إعادة التشغيل"""
    if db.is_emergency_stopped():
        logger.info("⏸ الإيقاف الطارئ مفعّل - لن يتم استرجاع المهام")
        return
    jobs = db.get_running_jobs()
    if not jobs:
        return
    logger.info(f"🔄 استرجاع {len(jobs)} مهمة محفوظة...")
    for job_id, job_data in jobs.items():
        if job_id in active_tasks and not active_tasks[job_id].done():
            continue
        try:
            if job_data["type"] == "random":
                task = asyncio.create_task(_run_random(
                    userbot, job_data["chat_id"], job_data["target_uid"],
                    None, job_id, job_data["gender"]
                ))
                active_tasks[job_id] = task
                logger.info(f"  ✅ استرجاع: {job_id}")
            elif job_data["type"] == "sequential":
                task = asyncio.create_task(_run_sequential(
                    userbot, job_data["chat_id"], job_data["target_uid"],
                    None, job_data["section_name"], job_id
                ))
                active_tasks[job_id] = task
                logger.info(f"  ✅ استرجاع: {job_id}")
        except Exception as e:
            logger.error(f"  ❌ فشل استرجاع {job_id}: {e}")
            db.remove_running_job(job_id)

async def start_userbot():
    global _me_cache, _publish_task
    print("🚀 جاري تشغيل اليوزربوت...")
    await userbot.start()
    me = await userbot.get_me()
    _me_cache = me
    print(f"✅ اليوزربوت: {me.first_name} (@{me.username or ''})")
    _publish_task = asyncio.create_task(publish_loop())
    # استرجاع المهام المحفوظة بعد تأخير قصير
    await asyncio.sleep(2)
    await resume_saved_jobs()
    print("✅ اليوزربوت جاهز بالكامل.")
