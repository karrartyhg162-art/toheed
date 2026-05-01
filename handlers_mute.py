from telethon import Button
from database import DataManager

db = DataManager()

def ikb_mute_main():
    return [
        [Button.inline("📋 عرض المكتومين", b"mute_list")],
        [Button.inline("➕ إضافة كتم", b"mute_add")],
        [Button.inline("⬅️ رجوع", b"main_menu")]
    ]

async def handle_mute_cb(event, data, states):
    if data == b"super_mute":
        await event.edit("🔇 **قسم الكتم**\nاختر من القائمة:", buttons=ikb_mute_main())
        return True
        
    elif data == b"mute_list":
        await show_mute_list(event)
        return True
        
    elif data == b"mute_add":
        states[event.sender_id] = "mute_add_id"
        await event.edit("أرسل معرف (Username) أو آيدي (ID) الشخص المراد كتمه:", buttons=[[Button.inline("رجوع", b"super_mute")]])
        return True
        
    elif data.startswith(b"mute_type_"):
        state_val = states.get(event.sender_id, "")
        if not state_val.startswith("mute_add_type_"):
            await event.answer("انتهت الجلسة", alert=True)
            return True
        
        target = state_val.replace("mute_add_type_", "")
        m_type = data.decode().replace("mute_type_", "")
        
        from userbot import userbot
        try:
            if target.isdigit() or (target.startswith('-') and target[1:].isdigit()):
                uid = int(target)
            else:
                ent = await userbot.get_entity(target)
                uid = ent.id
        except Exception:
            await event.edit("❌ تعذر العثور على الشخص. تأكد من الآيدي أو المعرف.", buttons=[[Button.inline("رجوع", b"super_mute")]])
            states[event.sender_id] = None
            return True

        if m_type == "dm":
            db.add_dm_mute(uid)
            await event.edit(f"🔇 تم كتم `{uid}` في الخاص بنجاح.", buttons=[[Button.inline("رجوع", b"super_mute")]])
        elif m_type == "all_gp":
            db.add_group_mute("all", uid)
            await event.edit(f"🔇 تم كتم `{uid}` في جميع المجموعات بنجاح.", buttons=[[Button.inline("رجوع", b"super_mute")]])
            
        states[event.sender_id] = None
        return True
        
    elif data.startswith(b"unmute_"):
        parts = data.decode().split('_')
        m_type = parts[1]
        
        if m_type == "dm":
            uid = int(parts[2])
            db.remove_dm_mute(uid)
            await event.answer("تم إلغاء الكتم في الخاص", alert=False)
            await show_mute_list(event)
        elif m_type == "gp":
            gid = parts[2]
            uid = int(parts[3])
            db.remove_group_mute(gid, uid)
            await event.answer("تم إلغاء الكتم في المجموعة", alert=False)
            await show_mute_list(event)
        return True
        
    return False

async def show_mute_list(event):
    dm_muted = db.get_dm_muted()
    group_muted = db.get_group_muted()
    
    buttons = []
    text = "📋 **قائمة المكتومين:**\n\n"
    
    if not dm_muted and not group_muted:
        text += "لا يوجد أشخاص مكتومين حالياً."
    
    if dm_muted:
        text += "**في الخاص:**\n"
        for uid in dm_muted:
            text += f"• `{uid}`\n"
            buttons.append([Button.inline(f"إلغاء كتم {uid} (خاص)", f"unmute_dm_{uid}".encode())])
            
    if group_muted:
        text += "\n**في المجموعات:**\n"
        for gid, uids in group_muted.items():
            g_name = "جميع المجموعات" if gid == "all" else f"مجموعة {gid}"
            for uid in uids:
                text += f"• `{uid}` ({g_name})\n"
                buttons.append([Button.inline(f"إلغاء كتم {uid} ({g_name})", f"unmute_gp_{gid}_{uid}".encode())])
                
    buttons.append([Button.inline("⬅️ رجوع", b"super_mute")])
    await event.edit(text, buttons=buttons)

async def handle_mute_msg(event, state, states):
    if state == "mute_add_id":
        target = event.text.strip()
        states[event.sender_id] = f"mute_add_type_{target}"
        
        buttons = [
            [Button.inline("في الخاص", b"mute_type_dm")],
            [Button.inline("في جميع المجموعات", b"mute_type_all_gp")],
            [Button.inline("إلغاء", b"super_mute")]
        ]
        await event.reply(f"كيف تريد كتم الهدف `{target}`؟", buttons=buttons)
        return True
    return False
