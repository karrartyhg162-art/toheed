from telethon import Button
from database import DataManager
db = DataManager()

# ══════════════════════════════════════
# القائمة الرئيسية للنشر التلقائي - 5 أزرار
# ══════════════════════════════════════
def format_arabic_time(dt_str):
    from datetime import datetime
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
        minute = dt.minute
        ampm = "صباحاً" if hour < 12 else "مساءً"
        h12 = hour % 12
        if h12 == 0: h12 = 12
        return f"{h12}:{minute:02d} {ampm}"
    except:
        return dt_str

def ikb_publish_main():
    is_pub = db.is_publishing_enabled()
    pub_btn = Button.inline("⏹ إيقاف النشر", b"pub_toggle") if is_pub else Button.inline("▶️ بدء النشر", b"pub_toggle")
    return [
        [pub_btn],
        [Button.inline("📂 المجموعات", b"pub_groups")],
        [Button.inline("📝 الرسائل", b"pub_messages")],
        [Button.inline("🔑 الرد التلقائي", b"pub_autoreply")],
        [Button.inline("⏱ الزمن", b"pub_time")],
        [Button.inline("📊 سجل النشر", b"pub_history")],
        [Button.inline("⬅️ رجوع للقائمة الرئيسية", b"main_menu")]
    ]

# ─── أزرار قسم المجموعات ───
def ikb_groups_menu():
    return [
        [Button.inline("➕ إضافة مجموعات", b"pg_add")],
        [Button.inline("➖ حذف مجموعات", b"pg_del")],
        [Button.inline("📋 عرض المجموعات", b"pg_list")],
        [Button.inline("⬅️ رجوع", b"super_publish")]
    ]

# ─── أزرار قسم الرسائل ───
def ikb_messages_menu():
    return [
        [Button.inline("➕ إضافة رسالة", b"pm_add")],
        [Button.inline("➖ حذف رسالة", b"pm_del")],
        [Button.inline("📋 عرض الرسائل", b"pm_list")],
        [Button.inline("⬅️ رجوع", b"super_publish")]
    ]

# ─── أزرار قسم الرد التلقائي ───
def ikb_autoreply_menu():
    is_ar = db.is_auto_reply_enabled()
    ar_btn = Button.inline("⏹ إيقاف الرد التلقائي", b"ar_toggle") if is_ar else Button.inline("▶️ تشغيل الرد التلقائي", b"ar_toggle")
    return [
        [ar_btn],
        [Button.inline("➕ إضافة نص للرد", b"ar_add")],
        [Button.inline("➖ حذف نص", b"ar_del")],
        [Button.inline("📋 اختيار النصوص", b"ar_list")],
        [Button.inline("⬅️ رجوع", b"super_publish")]
    ]

# ══════════════════════════════════════
# معالج أحداث الأزرار
# ══════════════════════════════════════
async def handle_publish_cb(event, data, states):
    # ─── القائمة الرئيسية للنشر ───
    if data == b"super_publish":
        g = len(db.get_publish_groups())
        m = len(db.get_publish_messages())
        am = len(db.get_active_messages())
        ar = len(db.get_auto_reply_keywords())
        mn, mx = db.get_publish_delays()
        txt = (
            "📢 **النشر التلقائي**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"📂 المجموعات: **{g}**\n"
            f"📝 الرسائل: **{m}** (مفعّلة: **{am}**)\n"
            f"🔑 نصوص الرد التلقائي: **{ar}**\n"
            f"⏱ الزمن: **{mn}** - **{mx}** ثانية\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        await event.edit(txt, buttons=ikb_publish_main())

    elif data == b"pub_toggle":
        is_pub = db.is_publishing_enabled()
        if not is_pub:
            # التحقق من وجود مجموعات ورسائل
            if not db.get_enabled_publish_groups() or not db.get_active_messages():
                await event.answer("❌ لا يمكن بدء النشر. تأكد من وجود مجموعات ورسائل مفعّلة.", alert=True)
                return True
        db.set_publishing_enabled(not is_pub)
        # تحديث القائمة
        await handle_publish_cb(event, b"super_publish", states)

    elif data == b"pub_history":
        logs = [log for log in db.get_publish_logs() if log.get("status") == "success"]
        if not logs:
            await event.answer("لا يوجد سجل نشر حتى الآن.", alert=True)
            return True
        
        txt = "📊 **سجل النشر الأخير:**\n━━━━━━━━━━━━━━━━━━\n\n"
        # جلب آخر 10 سجلات ناجحة وعكس الترتيب ليكون الأحدث في الأعلى
        recent_logs = logs[-10:]
        recent_logs.reverse()
        
        for i, log in enumerate(recent_logs):
            g_name = log.get("group_name") or log.get("group_id")
            if len(g_name) > 25: g_name = g_name[:22] + "..."
            msg_prev = log.get("message", "")[:40].replace("\n", " ")
            time_str = format_arabic_time(log.get("time", ""))
            
            txt += f"**{i+1}. {g_name}**\n"
            txt += f"💬 `{msg_prev}...`\n"
            txt += f"🕒 {time_str}\n\n"
            
        await event.edit(txt, buttons=[[Button.inline("⬅️ رجوع", b"super_publish")]])

    # ══════════════════════════════════════
    # قسم المجموعات
    # ══════════════════════════════════════
    elif data == b"pub_groups":
        g = len(db.get_publish_groups())
        await event.edit(f"📂 **إدارة المجموعات**\nالعدد الحالي: **{g}**", buttons=ikb_groups_menu())

    elif data == b"pg_add":
        states[event.sender_id] = "pg_add"
        await event.edit(
            "➕ **إضافة مجموعات**\n\n"
            "أرسل آيدي أو رابط المجموعة.\n"
            "يمكنك إرسال عدة مجموعات، كل مجموعة في سطر.\n\n"
            "مثال:\n`-1001234567890`\n`https://t.me/groupname`",
            buttons=[[Button.inline("⬅️ رجوع", b"pub_groups")]]
        )

    elif data == b"pg_del":
        grps = db.get_publish_groups()
        if not grps:
            await event.answer("لا توجد مجموعات للحذف.", alert=True)
            return True
        states[event.sender_id] = "pg_del"
        txt = "➖ **حذف مجموعات**\n\nأرسل أرقام المجموعات المراد حذفها (مفصولة بفاصلة):\n\n"
        for i, g in enumerate(grps):
            name = g.get("group_name") or g["group_id"]
            txt += f"**{i+1}.** {name}\n"
        txt += "\nمثال: `1,3,5` أو `2`"
        await event.edit(txt, buttons=[[Button.inline("⬅️ رجوع", b"pub_groups")]])

    elif data == b"pg_list":
        grps = db.get_publish_groups()
        if not grps:
            await event.answer("لا توجد مجموعات مضافة.", alert=True)
            return True
        btns = []
        for i, g in enumerate(grps):
            name = g.get("group_name") or g["group_id"]
            if len(name) > 30: name = name[:27] + "..."
            s = "✅" if g.get("enabled", True) else "⬜"
            btns.append([Button.inline(f"{s} {name}", f"pg_tog_{i}".encode())])
        btns.append([Button.inline("✅ تفعيل الكل", b"pg_all_on"), Button.inline("⬜ تعطيل الكل", b"pg_all_off")])
        btns.append([Button.inline("⬅️ رجوع", b"pub_groups")])
        await event.edit("📋 **المجموعات المضافة:**\nاضغط على المجموعة للتبديل بين التفعيل والتعطيل:", buttons=btns)

    elif data.startswith(b"pg_tog_"):
        idx = int(data.decode().replace("pg_tog_", ""))
        db.toggle_publish_group(idx)
        await handle_publish_cb(event, b"pg_list", states)

    elif data == b"pg_all_on":
        data_dict = db.load_data()
        for g in data_dict.get("publish_groups", []): g["enabled"] = True
        db.save_data(data_dict)
        await handle_publish_cb(event, b"pg_list", states)

    elif data == b"pg_all_off":
        data_dict = db.load_data()
        for g in data_dict.get("publish_groups", []): g["enabled"] = False
        db.save_data(data_dict)
        await handle_publish_cb(event, b"pg_list", states)

    # ══════════════════════════════════════
    # قسم الرسائل
    # ══════════════════════════════════════
    elif data == b"pub_messages":
        m = len(db.get_publish_messages())
        am = len(db.get_active_messages())
        await event.edit(
            f"📝 **إدارة الرسائل**\n"
            f"الإجمالي: **{m}** | المفعّلة: **{am}**",
            buttons=ikb_messages_menu()
        )

    elif data == b"pm_add":
        states[event.sender_id] = "pm_add"
        await event.edit(
            "➕ **إضافة رسالة**\n\n"
            "أرسل نص الرسالة المراد إضافتها.\n"
            "يمكنك إرسال عدة رسائل واحدة تلو الأخرى.\n\n"
            "أرسل `تم` عند الانتهاء.",
            buttons=[[Button.inline("⬅️ رجوع", b"pub_messages")]]
        )

    elif data == b"pm_del":
        msgs = db.get_publish_messages()
        if not msgs:
            await event.answer("لا توجد رسائل للحذف.", alert=True)
            return True
        states[event.sender_id] = "pm_del"
        txt = "➖ **حذف رسائل**\n\nأرسل أرقام الرسائل المراد حذفها (مفصولة بفاصلة):\n\n"
        for i, m in enumerate(msgs):
            preview = m["content"][:80].replace("\n", " ")
            s = "🟢" if m.get("active", True) else "🔴"
            txt += f"{s} **{i+1}.** {preview}{'...' if len(m['content'])>80 else ''}\n"
        txt += "\nمثال: `1,3` أو `2`"
        await event.edit(txt, buttons=[[Button.inline("⬅️ رجوع", b"pub_messages")]])

    elif data == b"pm_list":
        msgs = db.get_publish_messages()
        if not msgs:
            await event.answer("لا توجد رسائل.", alert=True)
            return True
        # عرض الرسائل مع أزرار التحديد
        btns = []
        for i, m in enumerate(msgs):
            s = "✅" if m.get("active", True) else "⬜"
            preview = m["content"][:35].replace("\n", " ")
            btns.append([
                Button.inline(f"{s} {i+1}. {preview}{'…' if len(m['content'])>35 else ''}", f"pm_tog_{i}".encode()),
                Button.inline("👁", f"pm_view_{i}".encode())
            ])
        btns.append([Button.inline("✅ تحديد الكل", b"pm_all_on"), Button.inline("⬜ إلغاء الكل", b"pm_all_off")])
        btns.append([Button.inline("⬅️ رجوع", b"pub_messages")])
        await event.edit("📋 **الرسائل المحفوظة:**\nاضغط للتبديل | 👁 لعرض النص كاملاً", buttons=btns)

    elif data.startswith(b"pm_tog_"):
        idx = int(data.decode().replace("pm_tog_", ""))
        result = db.toggle_publish_message(idx)
        if result is not None:
            # إعادة عرض القائمة
            msgs = db.get_publish_messages()
            btns = []
            for i, m in enumerate(msgs):
                s = "✅" if m.get("active", True) else "⬜"
                preview = m["content"][:35].replace("\n", " ")
                btns.append([
                    Button.inline(f"{s} {i+1}. {preview}{'…' if len(m['content'])>35 else ''}", f"pm_tog_{i}".encode()),
                    Button.inline("👁", f"pm_view_{i}".encode())
                ])
            btns.append([Button.inline("✅ تحديد الكل", b"pm_all_on"), Button.inline("⬜ إلغاء الكل", b"pm_all_off")])
            btns.append([Button.inline("⬅️ رجوع", b"pub_messages")])
            st = "مفعّلة ✅" if result else "معطّلة ⬜"
            await event.edit(f"📋 **الرسائل المحفوظة:**\nالرسالة {idx+1}: {st}", buttons=btns)

    elif data.startswith(b"pm_view_"):
        idx = int(data.decode().replace("pm_view_", ""))
        msgs = db.get_publish_messages()
        if 0 <= idx < len(msgs):
            content = msgs[idx]["content"]
            s = "✅ مفعّلة" if msgs[idx].get("active", True) else "⬜ معطّلة"
            txt = f"📝 **الرسالة رقم {idx+1}** ({s})\n━━━━━━━━━━━━━━━━━━\n\n{content}"
            await event.edit(txt, buttons=[
                [Button.inline("📤 إرسال للمراجعة", f"pm_send_{idx}".encode())],
                [Button.inline("⬅️ رجوع", b"pm_list")]
            ])

    elif data.startswith(b"pm_send_"):
        idx = int(data.decode().replace("pm_send_", ""))
        msgs = db.get_publish_messages()
        if 0 <= idx < len(msgs):
            await event.respond(msgs[idx]["content"])
            await event.answer("تم إرسال النص للمراجعة ✅", alert=True)

    elif data == b"pm_all_on":
        db.toggle_all_messages(True)
        await event.answer("تم تفعيل جميع الرسائل ✅", alert=True)
        msgs = db.get_publish_messages()
        btns = []
        for i, m in enumerate(msgs):
            s = "✅"
            preview = m["content"][:35].replace("\n", " ")
            btns.append([
                Button.inline(f"{s} {i+1}. {preview}{'…' if len(m['content'])>35 else ''}", f"pm_tog_{i}".encode()),
                Button.inline("👁", f"pm_view_{i}".encode())
            ])
        btns.append([Button.inline("✅ تحديد الكل", b"pm_all_on"), Button.inline("⬜ إلغاء الكل", b"pm_all_off")])
        btns.append([Button.inline("⬅️ رجوع", b"pub_messages")])
        await event.edit("📋 **الرسائل المحفوظة:**\nتم تفعيل الكل ✅", buttons=btns)

    elif data == b"pm_all_off":
        db.toggle_all_messages(False)
        await event.answer("تم إلغاء تفعيل جميع الرسائل ⬜", alert=True)
        msgs = db.get_publish_messages()
        btns = []
        for i, m in enumerate(msgs):
            s = "⬜"
            preview = m["content"][:35].replace("\n", " ")
            btns.append([
                Button.inline(f"{s} {i+1}. {preview}{'…' if len(m['content'])>35 else ''}", f"pm_tog_{i}".encode()),
                Button.inline("👁", f"pm_view_{i}".encode())
            ])
        btns.append([Button.inline("✅ تحديد الكل", b"pm_all_on"), Button.inline("⬜ إلغاء الكل", b"pm_all_off")])
        btns.append([Button.inline("⬅️ رجوع", b"pub_messages")])
        await event.edit("📋 **الرسائل المحفوظة:**\nتم إلغاء تفعيل الكل ⬜", buttons=btns)

    # ══════════════════════════════════════
    # قسم الرد التلقائي
    # ══════════════════════════════════════
    elif data == b"pub_autoreply":
        kws = db.get_auto_reply_keywords()
        active = len([k for k in kws if k.get("active", True)])
        await event.edit(
            f"🔑 **الرد التلقائي**\n"
            f"النصوص: **{len(kws)}** | المفعّلة: **{active}**\n\n"
            "⚠️ الردود تعمل فقط داخل المجموعات المحددة.",
            buttons=ikb_autoreply_menu()
        )

    elif data == b"ar_toggle":
        is_ar = db.is_auto_reply_enabled()
        db.set_auto_reply_enabled(not is_ar)
        await handle_publish_cb(event, b"pub_autoreply", states)

    elif data == b"ar_add":
        states[event.sender_id] = "ar_add_kw"
        await event.edit(
            "➕ **إضافة نص للرد التلقائي**\n\n"
            "أرسل الكلمة أو الجملة التي تريد الرد عليها تلقائياً:",
            buttons=[[Button.inline("⬅️ رجوع", b"pub_autoreply")]]
        )

    elif data == b"ar_del":
        kws = db.get_auto_reply_keywords()
        if not kws:
            await event.answer("لا توجد نصوص للحذف.", alert=True)
            return True
        states[event.sender_id] = "ar_del"
        txt = "➖ **حذف نصوص الرد التلقائي**\n\nأرسل أرقام النصوص المراد حذفها (مفصولة بفاصلة):\n\n"
        for i, k in enumerate(kws):
            txt += f"**{i+1}.** {k['keyword']}\n"
        txt += "\nمثال: `1,3` أو `2`"
        await event.edit(txt, buttons=[[Button.inline("⬅️ رجوع", b"pub_autoreply")]])

    elif data == b"ar_list":
        kws = db.get_auto_reply_keywords()
        if not kws:
            await event.answer("لا توجد نصوص مضافة.", alert=True)
            return True
        btns = []
        for i, k in enumerate(kws):
            s = "✅" if k.get("active", True) else "⬜"
            preview = k["keyword"][:30]
            btns.append([
                Button.inline(f"{s} {i+1}. {preview}{'…' if len(k['keyword'])>30 else ''}", f"ar_tog_{i}".encode()),
                Button.inline("👁", f"ar_view_{i}".encode())
            ])
        btns.append([Button.inline("✅ تحديد الكل", b"ar_all_on"), Button.inline("⬜ إلغاء الكل", b"ar_all_off")])
        btns.append([Button.inline("⬅️ رجوع", b"pub_autoreply")])
        await event.edit("🔑 **نصوص الرد التلقائي:**\nاضغط للتبديل | 👁 لعرض التفاصيل", buttons=btns)

    elif data.startswith(b"ar_tog_"):
        idx = int(data.decode().replace("ar_tog_", ""))
        result = db.toggle_auto_reply_keyword(idx)
        if result is not None:
            kws = db.get_auto_reply_keywords()
            btns = []
            for i, k in enumerate(kws):
                s = "✅" if k.get("active", True) else "⬜"
                preview = k["keyword"][:30]
                btns.append([
                    Button.inline(f"{s} {i+1}. {preview}{'…' if len(k['keyword'])>30 else ''}", f"ar_tog_{i}".encode()),
                    Button.inline("👁", f"ar_view_{i}".encode())
                ])
            btns.append([Button.inline("✅ تحديد الكل", b"ar_all_on"), Button.inline("⬜ إلغاء الكل", b"ar_all_off")])
            btns.append([Button.inline("⬅️ رجوع", b"pub_autoreply")])
            st = "مفعّل ✅" if result else "معطّل ⬜"
            await event.edit(f"🔑 **نصوص الرد التلقائي:**\nالنص {idx+1}: {st}", buttons=btns)

    elif data.startswith(b"ar_view_"):
        idx = int(data.decode().replace("ar_view_", ""))
        kws = db.get_auto_reply_keywords()
        if 0 <= idx < len(kws):
            k = kws[idx]
            s = "✅ مفعّل" if k.get("active", True) else "⬜ معطّل"
            txt = (
                f"🔑 **النص رقم {idx+1}** ({s})\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"**الكلمة/الجملة:**\n{k['keyword']}\n\n"
                f"**نص الرد:**\n{k['reply_text']}"
            )
            await event.edit(txt, buttons=[
                [Button.inline("📤 إرسال للمراجعة", f"ar_send_{idx}".encode())],
                [Button.inline("⬅️ رجوع", b"ar_list")]
            ])

    elif data.startswith(b"ar_send_"):
        idx = int(data.decode().replace("ar_send_", ""))
        kws = db.get_auto_reply_keywords()
        if 0 <= idx < len(kws):
            k = kws[idx]
            await event.respond(f"🔑 **الكلمة:** {k['keyword']}\n\n📝 **الرد:**\n{k['reply_text']}")
            await event.answer("تم إرسال النص للمراجعة ✅", alert=True)

    elif data == b"ar_all_on":
        db.toggle_all_auto_reply(True)
        await event.answer("تم تفعيل جميع النصوص ✅", alert=True)
        kws = db.get_auto_reply_keywords()
        btns = []
        for i, k in enumerate(kws):
            preview = k["keyword"][:30]
            btns.append([
                Button.inline(f"✅ {i+1}. {preview}{'…' if len(k['keyword'])>30 else ''}", f"ar_tog_{i}".encode()),
                Button.inline("👁", f"ar_view_{i}".encode())
            ])
        btns.append([Button.inline("✅ تحديد الكل", b"ar_all_on"), Button.inline("⬜ إلغاء الكل", b"ar_all_off")])
        btns.append([Button.inline("⬅️ رجوع", b"pub_autoreply")])
        await event.edit("🔑 **نصوص الرد التلقائي:**\nتم تفعيل الكل ✅", buttons=btns)

    elif data == b"ar_all_off":
        db.toggle_all_auto_reply(False)
        await event.answer("تم إلغاء تفعيل جميع النصوص ⬜", alert=True)
        kws = db.get_auto_reply_keywords()
        btns = []
        for i, k in enumerate(kws):
            preview = k["keyword"][:30]
            btns.append([
                Button.inline(f"⬜ {i+1}. {preview}{'…' if len(k['keyword'])>30 else ''}", f"ar_tog_{i}".encode()),
                Button.inline("👁", f"ar_view_{i}".encode())
            ])
        btns.append([Button.inline("✅ تحديد الكل", b"ar_all_on"), Button.inline("⬜ إلغاء الكل", b"ar_all_off")])
        btns.append([Button.inline("⬅️ رجوع", b"pub_autoreply")])
        await event.edit("🔑 **نصوص الرد التلقائي:**\nتم إلغاء تفعيل الكل ⬜", buttons=btns)

    # ══════════════════════════════════════
    # قسم الزمن
    # ══════════════════════════════════════
    elif data == b"pub_time":
        mn, mx = db.get_publish_delays()
        await event.edit(
            "⏱ **إعدادات الزمن**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"الإعدادات الحالية:\n"
            f"⏱ **من:** {mn} ثانية\n"
            f"⏱ **إلى:** {mx} ثانية\n\n"
            "يتم اختيار وقت عشوائي متغير داخل هذا النطاق\n"
            "بين كل عملية نشر وأخرى.\n\n"
            "لتغيير القيم اضغط تعديل.",
            buttons=[
                [Button.inline("✏️ تعديل الزمن", b"pt_edit")],
                [Button.inline("⬅️ رجوع", b"super_publish")]
            ]
        )

    elif data == b"pt_edit":
        states[event.sender_id] = "pt_edit"
        await event.edit(
            "⏱ **تعديل الزمن**\n\n"
            "أرسل القيم بالصيغة التالية:\n"
            "`من-إلى`\n\n"
            "أمثلة:\n"
            "• `30-120` (من 30 إلى 120 ثانية)\n"
            "• `60-300` (من دقيقة إلى 5 دقائق)\n"
            "• `120-600` (من دقيقتين إلى 10 دقائق)",
            buttons=[[Button.inline("⬅️ رجوع", b"pub_time")]]
        )

    else:
        return False
    return True

# ══════════════════════════════════════
# معالج الرسائل النصية
# ══════════════════════════════════════
async def handle_publish_msg(event, state, states):
    text = event.text

    # ─── إضافة مجموعات ───
    if state == "pg_add":
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        added = 0
        for line in lines:
            if db.add_publish_group(line):
                added += 1
        if added > 0:
            await event.reply(
                f"✅ تم إضافة **{added}** مجموعة بنجاح.\n"
                "أرسل المزيد أو اضغط رجوع.",
                buttons=[[Button.inline("⬅️ رجوع", b"pub_groups")]]
            )
        else:
            await event.reply("⚠️ المجموعات موجودة مسبقاً أو لم يتم إدخال بيانات.", buttons=[[Button.inline("⬅️ رجوع", b"pub_groups")]])

    # ─── حذف مجموعات ───
    elif state == "pg_del":
        try:
            indices = sorted([int(x.strip()) - 1 for x in text.split(",")], reverse=True)
            removed = 0
            for idx in indices:
                if db.remove_publish_group_by_index(idx):
                    removed += 1
            states[event.sender_id] = None
            await event.reply(f"🗑 تم حذف **{removed}** مجموعة.", buttons=[[Button.inline("⬅️ رجوع", b"pub_groups")]])
        except:
            await event.reply("❌ صيغة خاطئة. أرسل الأرقام مفصولة بفاصلة.\nمثال: `1,3,5`")

    # ─── إضافة رسائل ───
    elif state == "pm_add":
        if text.strip() == "تم":
            states[event.sender_id] = None
            await event.reply("✅ تم الانتهاء من إضافة الرسائل.", buttons=[[Button.inline("⬅️ رجوع", b"pub_messages")]])
        else:
            db.add_publish_message(text)
            total = len(db.get_publish_messages())
            await event.reply(f"✅ تم إضافة الرسالة رقم **{total}**.\nأرسل رسالة أخرى أو اكتب `تم`.")

    # ─── حذف رسائل ───
    elif state == "pm_del":
        try:
            indices = sorted([int(x.strip()) - 1 for x in text.split(",")], reverse=True)
            removed = 0
            for idx in indices:
                if db.remove_publish_message_by_index(idx):
                    removed += 1
            states[event.sender_id] = None
            await event.reply(f"🗑 تم حذف **{removed}** رسالة.", buttons=[[Button.inline("⬅️ رجوع", b"pub_messages")]])
        except:
            await event.reply("❌ صيغة خاطئة. أرسل الأرقام مفصولة بفاصلة.\nمثال: `1,3`")

    # ─── إضافة كلمة رد تلقائي ───
    elif state == "ar_add_kw":
        states[event.sender_id] = "ar_add_reply"
        states["_ar_kw"] = text
        await event.reply(f"✅ الكلمة: **{text}**\n\nالآن أرسل نص الرد التلقائي:")

    elif state == "ar_add_reply":
        kw = states.pop("_ar_kw", "")
        db.add_auto_reply_keyword(kw, text)
        states[event.sender_id] = None
        await event.reply(
            f"✅ تم إضافة الرد التلقائي:\n"
            f"🔑 الكلمة: **{kw}**\n"
            f"📝 الرد: {text[:100]}{'...' if len(text)>100 else ''}",
            buttons=[[Button.inline("➕ إضافة نص آخر", b"ar_add"), Button.inline("⬅️ رجوع", b"pub_autoreply")]]
        )

    # ─── تعديل الزمن ───
    elif state == "pt_edit":
        try:
            parts = text.replace(" ", "").split("-")
            mn_val = float(parts[0])
            mx_val = float(parts[1])
            if mn_val <= 0 or mx_val <= 0:
                await event.reply("❌ القيم يجب أن تكون أكبر من صفر.")
                return True
            if mn_val >= mx_val:
                await event.reply("❌ قيمة (من) يجب أن تكون أقل من قيمة (إلى).")
                return True
            db.set_publish_delays(mn_val, mx_val)
            states[event.sender_id] = None
            await event.reply(
                f"✅ تم حفظ إعدادات الزمن:\n"
                f"⏱ **من:** {mn_val} ثانية\n"
                f"⏱ **إلى:** {mx_val} ثانية",
                buttons=[[Button.inline("⬅️ رجوع", b"pub_time")]]
            )
        except (ValueError, IndexError):
            await event.reply("❌ صيغة خاطئة.\nأرسل بالصيغة: `30-120`")
        return True

    # ─── حذف نصوص رد تلقائي ───
    elif state == "ar_del":
        try:
            indices = sorted([int(x.strip()) - 1 for x in text.split(",")], reverse=True)
            removed = 0
            for idx in indices:
                if db.remove_auto_reply_by_index(idx):
                    removed += 1
            states[event.sender_id] = None
            await event.reply(f"🗑 تم حذف **{removed}** نص.", buttons=[[Button.inline("⬅️ رجوع", b"pub_autoreply")]])
        except:
            await event.reply("❌ صيغة خاطئة. أرسل الأرقام مفصولة بفاصلة.\nمثال: `1,3`")

    else:
        return False
    return True
