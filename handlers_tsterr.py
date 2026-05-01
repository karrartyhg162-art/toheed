import os, io, uuid
from telethon import Button
from database import DataManager
db = DataManager()

MEDIA_DIR = os.path.join("data", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# ═══════════════ القوائم ═══════════════
def ikb_main():
    return [
        [Button.inline("📝 تسطير السب", b"ts_sub")],
        [Button.inline("🔗 التسطير المتسلسل", b"ts_seq")],
        [Button.inline("⬅️ رجوع", b"main_menu")]
    ]

def ikb_sub():
    return [
        [Button.inline("👨 تسطير الذكور", b"sub_m")],
        [Button.inline("👩 تسطير الإناث", b"sub_f")],
        [Button.inline("⏱ الزمن", b"sub_t")],
        [Button.inline("⬅️ رجوع", b"super_tsterr")]
    ]

def ikb_gender(g):
    return [
        [Button.inline("🗑 حذف النص", f"gd_{g}".encode())],
        [Button.inline("➕ إضافة نص", f"ga_{g}".encode())],
        [Button.inline("📄 إضافة ملف TXT", f"gt_{g}".encode())],
        [Button.inline("🔑 اختيار كلمة تفعيل", f"gk_{g}".encode())],
        [Button.inline("📥 استلام جميع النصوص", f"ge_{g}".encode())],
        [Button.inline("⬅️ رجوع", b"ts_sub")]
    ]

def ikb_sub_time():
    s = db.get_tsterr_settings()
    m = s.get("sub_delay_mode", "gaussian")
    g = "✅" if m == "gaussian" else "⬜"
    l = "✅" if m == "length" else "⬜"
    return [
        [Button.inline(f"{g} التوزيع الغاوسي", b"stm_g")],
        [Button.inline(f"{l} حسب طول النص", b"stm_l")],
        [Button.inline("⬅️ رجوع", b"ts_sub")]
    ]

def ikb_seq():
    return [
        [Button.inline("➕ إضافة عنوان سلسلة", b"sq_add")],
        [Button.inline("📋 إدارة السلاسل", b"sq_lst")],
        [Button.inline("⏱ قسم الزمن", b"sq_t")],
        [Button.inline("⬅️ رجوع", b"super_tsterr")]
    ]

def ikb_seq_time():
    s = db.get_tsterr_settings()
    m = s.get("seq_delay_mode", "length")
    l = "✅" if m == "length" else "⬜"
    r = "✅" if m == "random_range" else "⬜"
    return [
        [Button.inline(f"{l} حسب طول النص", b"sqm_l")],
        [Button.inline(f"{r} من إلى", b"sqm_r")],
        [Button.inline("⬅️ رجوع", b"ts_seq")]
    ]

def ikb_sec_manage(title):
    t = title.encode()
    return [
        [Button.inline("➕ إضافة محتوى", b"si_a_" + t)],
        [Button.inline("📋 عرض المحتوى", b"si_v_" + t)],
        [Button.inline("🗑 حذف عنصر", b"si_d_" + t)],
        [Button.inline("❌ حذف السلسلة", b"sq_del_" + t)],
        [Button.inline("⬅️ رجوع", b"sq_lst")]
    ]

# ═══════════════ معالج الأزرار ═══════════════
async def handle_tsterr_cb(event, data, states, userbot_ref=None):
    d = data

    # ─── القائمة الرئيسية ───
    if d == b"super_tsterr":
        await event.edit("📚 **قسم التسطير**\nاختر النوع:", buttons=ikb_main())

    # ─── تسطير السب ───
    elif d == b"ts_sub":
        s = db.get_tsterr_settings()
        ml = len(db.get_random_texts("male"))
        fl = len(db.get_random_texts("female"))
        txt = (f"📝 **تسطير السب**\n━━━━━━━━━━\n"
               f"👨 نصوص الذكور: **{ml}**\n👩 نصوص الإناث: **{fl}**\n"
               f"🔑 تفعيل ذكور: `{s.get('activation_keyword_male','ذكر')}`\n"
               f"🔑 تفعيل إناث: `{s.get('activation_keyword_female','انثى')}`")
        await event.edit(txt, buttons=ikb_sub())

    elif d == b"sub_m":
        c = len(db.get_random_texts("male"))
        await event.edit(f"👨 **تسطير الذكور**\nالنصوص: **{c}**", buttons=ikb_gender("male"))
    elif d == b"sub_f":
        c = len(db.get_random_texts("female"))
        await event.edit(f"👩 **تسطير الإناث**\nالنصوص: **{c}**", buttons=ikb_gender("female"))

    # ─── أزرار الجنس (حذف/إضافة/ملف/كلمة/تصدير) ───
    elif d.startswith(b"gd_"):
        g = d[3:].decode()
        texts = db.get_random_texts(g)
        if not texts:
            await event.answer("لا توجد نصوص.", alert=True); return True
        states[event.sender_id] = f"gd_{g}"
        label = "الذكور" if g == "male" else "الإناث"
        txt = f"🗑 **حذف نصوص {label}**\n\nأرسل رقم النص أو `الكل` لحذف الجميع:\n\n"
        for i, t in enumerate(texts[:20]):
            txt += f"**{i+1}.** {t[:50]}{'...' if len(t)>50 else ''}\n"
        if len(texts) > 20:
            txt += f"\n... و {len(texts)-20} نص آخر"
        await event.edit(txt, buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])

    elif d.startswith(b"ga_"):
        g = d[3:].decode()
        states[event.sender_id] = f"ga_{g}"
        await event.edit("➕ أرسل النصوص واحداً تلو الآخر.\nأرسل `تم` عند الانتهاء:",
                         buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])

    elif d.startswith(b"gt_"):
        g = d[3:].decode()
        states[event.sender_id] = f"gt_{g}"
        await event.edit("📄 أرسل ملف TXT يحتوي على النصوص:",
                         buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])

    elif d.startswith(b"gk_"):
        g = d[3:].decode()
        states[event.sender_id] = f"gk_{g}"
        s = db.get_tsterr_settings()
        key = "activation_keyword_male" if g == "male" else "activation_keyword_female"
        await event.edit(f"🔑 الكلمة الحالية: `{s.get(key, '')}`\n\nأرسل كلمة التفعيل الجديدة:",
                         buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])

    elif d.startswith(b"ge_"):
        g = d[3:].decode()
        texts = db.get_random_texts(g)
        if not texts:
            await event.answer("لا توجد نصوص.", alert=True); return True
        label = "الذكور" if g == "male" else "الإناث"
        fp = io.BytesIO(("\n\n".join(texts)).encode('utf-8'))
        fp.name = f"texts_{g}.txt"
        await event.client.send_file(event.chat_id, fp, caption=f"📥 جميع نصوص {label} ({len(texts)} نص)")

    # ─── زمن السب ───
    elif d == b"sub_t":
        s = db.get_tsterr_settings()
        mode = "التوزيع الغاوسي" if s.get("sub_delay_mode") == "gaussian" else "حسب طول النص"
        txt = (f"⏱ **زمن تسطير السب**\n━━━━━━━━━━\n"
               f"الوضع: **{mode}**\n"
               f"النطاق: **{s.get('sub_delay_min',2)}** - **{s.get('sub_delay_max',15)}** ثانية")
        await event.edit(txt, buttons=ikb_sub_time())

    elif d == b"stm_g":
        db.update_tsterr_setting("sub_delay_mode", "gaussian")
        states[event.sender_id] = "stm_range"
        await event.edit("✅ تم اختيار التوزيع الغاوسي.\n\nأرسل النطاق بصيغة: `2-15`",
                         buttons=[[Button.inline("⬅️ رجوع", b"sub_t")]])

    elif d == b"stm_l":
        db.update_tsterr_setting("sub_delay_mode", "length")
        states[event.sender_id] = "stm_range"
        await event.edit("✅ تم اختيار حسب طول النص.\n\nأرسل النطاق (أقل-أعلى) بصيغة: `2-15`",
                         buttons=[[Button.inline("⬅️ رجوع", b"sub_t")]])

    # ─── التسطير المتسلسل ───
    elif d == b"ts_seq":
        titles = db.get_sequential_titles()
        txt = f"🔗 **التسطير المتسلسل**\nالسلاسل: **{len(titles)}**"
        if titles:
            txt += "\n━━━━━━━━━━\n"
            for t in titles:
                items = db.get_sequential_items(t)
                txt += f"📌 **{t}** ({len(items)} عنصر)\n"
        await event.edit(txt, buttons=ikb_seq())

    elif d == b"sq_add":
        states[event.sender_id] = "sq_add"
        await event.edit("➕ أرسل عنوان السلسلة الجديدة:\n\n"
                         "⚠️ العنوان هو كلمة التفعيل.\nعندما تكتبه في الخاص أو المجموعة سيتم إرسال محتويات السلسلة.",
                         buttons=[[Button.inline("⬅️ رجوع", b"ts_seq")]])

    elif d == b"sq_lst":
        titles = db.get_sequential_titles()
        if not titles:
            await event.answer("لا توجد سلاسل.", alert=True); return True
        btns = [[Button.inline(f"📌 {t}", b"sq_mg_" + t.encode())] for t in titles]
        btns.append([Button.inline("⬅️ رجوع", b"ts_seq")])
        await event.edit("📋 **اختر سلسلة لإدارتها:**", buttons=btns)

    elif d.startswith(b"sq_mg_"):
        title = d[6:].decode()
        items = db.get_sequential_items(title)
        txt = f"📌 **سلسلة: {title}**\n━━━━━━━━━━\nالعناصر: **{len(items)}**"
        await event.edit(txt, buttons=ikb_sec_manage(title))

    elif d.startswith(b"si_a_"):
        title = d[5:].decode()
        states[event.sender_id] = f"si_a_{title}"
        await event.edit(f"➕ **إضافة محتوى لسلسلة «{title}»**\n\n"
                         "أرسل أي نوع من المحتوى:\n"
                         "• نص\n• صورة\n• ملصق\n• متحرك (GIF)\n• فيديو\n• ملف\n\n"
                         "أرسل `تم` عند الانتهاء.",
                         buttons=[[Button.inline("⬅️ رجوع", b"sq_mg_" + title.encode())]])

    elif d.startswith(b"si_v_"):
        title = d[5:].decode()
        items = db.get_sequential_items(title)
        if not items:
            await event.answer("لا توجد عناصر.", alert=True); return True
        types = {"text":"📝","photo":"🖼","sticker":"🎭","animation":"🎬","video":"📹","document":"📎"}
        txt = f"📋 **محتوى «{title}»** ({len(items)} عنصر)\n━━━━━━━━━━\n"
        for i, item in enumerate(items[:25]):
            tp = types.get(item["type"], "❓")
            preview = item.get("content", item.get("file_path", ""))[:40] if item["type"] == "text" else f"[{item['type']}]"
            txt += f"{i+1}. {tp} {preview}\n"
        if len(items) > 25:
            txt += f"\n... و {len(items)-25} عنصر آخر"
        await event.edit(txt, buttons=[[Button.inline("⬅️ رجوع", b"sq_mg_" + title.encode())]])

    elif d.startswith(b"si_d_"):
        title = d[5:].decode()
        items = db.get_sequential_items(title)
        if not items:
            await event.answer("لا توجد عناصر.", alert=True); return True
        states[event.sender_id] = f"si_d_{title}"
        types = {"text":"📝","photo":"🖼","sticker":"🎭","animation":"🎬","video":"📹","document":"📎"}
        txt = f"🗑 **حذف عنصر من «{title}»**\n\nأرسل رقم العنصر:\n\n"
        for i, item in enumerate(items[:25]):
            tp = types.get(item["type"], "❓")
            preview = item.get("content", "")[:40] if item["type"] == "text" else f"[{item['type']}]"
            txt += f"{i+1}. {tp} {preview}\n"
        await event.edit(txt, buttons=[[Button.inline("⬅️ رجوع", b"sq_mg_" + title.encode())]])

    elif d.startswith(b"sq_del_"):
        title = d[7:].decode()
        db.remove_sequential_section(title)
        await event.answer(f"تم حذف سلسلة «{title}»", alert=True)
        await event.edit("🔗 **التسطير المتسلسل**", buttons=ikb_seq())

    # ─── زمن المتسلسل ───
    elif d == b"sq_t":
        s = db.get_tsterr_settings()
        mode = "حسب طول النص" if s.get("seq_delay_mode") == "length" else "من إلى (عشوائي)"
        txt = (f"⏱ **زمن التسطير المتسلسل**\n━━━━━━━━━━\n"
               f"الوضع: **{mode}**\n"
               f"النطاق: **{s.get('seq_delay_min',2)}** - **{s.get('seq_delay_max',15)}** ثانية")
        await event.edit(txt, buttons=ikb_seq_time())

    elif d == b"sqm_l":
        db.update_tsterr_setting("seq_delay_mode", "length")
        states[event.sender_id] = "sqm_range"
        await event.edit("✅ حسب طول النص.\n\nأرسل النطاق (أقل-أعلى) بصيغة: `2-15`",
                         buttons=[[Button.inline("⬅️ رجوع", b"sq_t")]])

    elif d == b"sqm_r":
        db.update_tsterr_setting("seq_delay_mode", "random_range")
        states[event.sender_id] = "sqm_range"
        await event.edit("✅ من إلى (عشوائي).\n\nأرسل النطاق بصيغة: `2-15`",
                         buttons=[[Button.inline("⬅️ رجوع", b"sq_t")]])
    else:
        return False
    return True

# ═══════════════ معالج الرسائل ═══════════════
async def handle_tsterr_msg(event, state, states):
    text = event.text or ""

    # ─── حذف نص (ذكور/إناث) ───
    if state and state.startswith("gd_"):
        g = state[3:]
        if text.strip() == "الكل":
            db.clear_random_texts(g)
            states[event.sender_id] = None
            await event.reply("✅ تم حذف جميع النصوص.", buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])
        else:
            try:
                idx = int(text.strip()) - 1
                if db.remove_random_text(g, idx):
                    states[event.sender_id] = None
                    await event.reply("✅ تم الحذف.", buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])
                else:
                    await event.reply("❌ رقم غير صحيح.")
            except:
                await event.reply("❌ أرسل رقماً أو `الكل`.")
        return True

    # ─── إضافة نص يدوي ───
    elif state and state.startswith("ga_"):
        g = state[3:]
        if text.strip() == "تم":
            states[event.sender_id] = None
            total = len(db.get_random_texts(g))
            await event.reply(f"✅ تم الانتهاء. المجموع: {total}", buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])
        else:
            added = db.add_random_texts(g, [text])
            total = len(db.get_random_texts(g))
            if added:
                await event.reply(f"✅ نص رقم {total}")
            else:
                await event.reply("❌ نص مكرر.")
        return True

    # ─── إضافة ملف TXT ───
    elif state and state.startswith("gt_"):
        g = state[3:]
        if event.message.document:
            try:
                data = await event.client.download_media(event.message, bytes)
                content = data.decode('utf-8')
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                added = db.add_random_texts(g, lines)
                total = len(db.get_random_texts(g))
                states[event.sender_id] = None
                await event.reply(f"✅ تم إضافة **{added}** نص من الملف.\nالمجموع: **{total}**",
                                  buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])
            except Exception as e:
                await event.reply(f"❌ خطأ في قراءة الملف: {e}")
        else:
            await event.reply("❌ أرسل ملف TXT فقط.")
        return True

    # ─── اختيار كلمة تفعيل ───
    elif state and state.startswith("gk_"):
        g = state[3:]
        key = "activation_keyword_male" if g == "male" else "activation_keyword_female"
        db.update_tsterr_setting(key, text.strip())
        states[event.sender_id] = None
        await event.reply(f"✅ كلمة التفعيل: **{text.strip()}**",
                          buttons=[[Button.inline("⬅️ رجوع", f"sub_{'m' if g=='male' else 'f'}".encode())]])
        return True

    # ─── نطاق زمن السب ───
    elif state == "stm_range":
        try:
            p = text.replace(" ", "").split("-")
            mn, mx = float(p[0]), float(p[1])
            if mn <= 0 or mx <= 0 or mn >= mx:
                await event.reply("❌ قيم غير صحيحة."); return True
            db.update_tsterr_setting("sub_delay_min", mn)
            db.update_tsterr_setting("sub_delay_max", mx)
            states[event.sender_id] = None
            await event.reply(f"✅ النطاق: {mn}s - {mx}s", buttons=[[Button.inline("⬅️ رجوع", b"sub_t")]])
        except:
            await event.reply("❌ صيغة خاطئة. مثال: `2-15`")
        return True

    # ─── إضافة عنوان سلسلة ───
    elif state == "sq_add":
        title = text.strip()
        if not title:
            await event.reply("❌ العنوان فارغ."); return True
        if db.add_sequential_section(title):
            states[event.sender_id] = None
            await event.reply(f"✅ تم إنشاء سلسلة «{title}»\n🔑 كلمة التفعيل: `{title}`",
                              buttons=[[Button.inline("➕ إضافة محتوى", b"si_a_" + title.encode()),
                                        Button.inline("⬅️ رجوع", b"ts_seq")]])
        else:
            await event.reply("❌ السلسلة موجودة مسبقاً.")
        return True

    # ─── إضافة محتوى للسلسلة ───
    elif state and state.startswith("si_a_"):
        title = state[5:]
        if text.strip() == "تم":
            states[event.sender_id] = None
            items = db.get_sequential_items(title)
            await event.reply(f"✅ تم. العناصر: {len(items)}", buttons=[[Button.inline("⬅️ رجوع", b"sq_mg_" + title.encode())]])
            return True

        msg = event.message
        item = None

        if msg.photo:
            path = await event.client.download_media(msg, MEDIA_DIR)
            item = {"type": "photo", "file_path": path}
        elif msg.sticker:
            path = await event.client.download_media(msg, MEDIA_DIR)
            item = {"type": "sticker", "file_path": path}
        elif msg.gif:
            path = await event.client.download_media(msg, MEDIA_DIR)
            item = {"type": "animation", "file_path": path}
        elif msg.video:
            path = await event.client.download_media(msg, MEDIA_DIR)
            item = {"type": "video", "file_path": path}
        elif msg.document and not msg.sticker and not msg.gif and not msg.video:
            path = await event.client.download_media(msg, MEDIA_DIR)
            item = {"type": "document", "file_path": path}
        elif text:
            item = {"type": "text", "content": text}

        if item:
            db.add_sequential_item(title, item)
            count = len(db.get_sequential_items(title))
            types = {"text":"📝","photo":"🖼","sticker":"🎭","animation":"🎬","video":"📹","document":"📎"}
            await event.reply(f"✅ {types.get(item['type'],'❓')} عنصر رقم {count}")
        else:
            await event.reply("❌ نوع غير مدعوم.")
        return True

    # ─── حذف عنصر من سلسلة ───
    elif state and state.startswith("si_d_"):
        title = state[5:]
        try:
            idx = int(text.strip()) - 1
            if db.remove_sequential_item(title, idx):
                states[event.sender_id] = None
                await event.reply("✅ تم الحذف.", buttons=[[Button.inline("⬅️ رجوع", b"sq_mg_" + title.encode())]])
            else:
                await event.reply("❌ رقم غير صحيح.")
        except:
            await event.reply("❌ أرسل رقماً.")
        return True

    # ─── نطاق زمن المتسلسل ───
    elif state == "sqm_range":
        try:
            p = text.replace(" ", "").split("-")
            mn, mx = float(p[0]), float(p[1])
            if mn <= 0 or mx <= 0 or mn >= mx:
                await event.reply("❌ قيم غير صحيحة."); return True
            db.update_tsterr_setting("seq_delay_min", mn)
            db.update_tsterr_setting("seq_delay_max", mx)
            states[event.sender_id] = None
            await event.reply(f"✅ النطاق: {mn}s - {mx}s", buttons=[[Button.inline("⬅️ رجوع", b"sq_t")]])
        except:
            await event.reply("❌ صيغة خاطئة. مثال: `2-15`")
        return True

    return False
