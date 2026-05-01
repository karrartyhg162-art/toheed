# ══════════════════════════════════════════════════════════════
# قاعدة البيانات الموحدة - تدعم جميع وظائف المشاريع الثلاثة
# ══════════════════════════════════════════════════════════════
import json
import os
import logging
import shutil

logger = logging.getLogger(__name__)

DATA_DIR = "data"
MEDIA_DIR = os.path.join(DATA_DIR, "media")

class DataManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(MEDIA_DIR, exist_ok=True)
        self.data_dir = DATA_DIR
        account_name = os.environ.get("ACCOUNT_NAME", "unified")
        # ملفات البيانات
        self.main_file = os.path.join(DATA_DIR, f"{account_name}_main_data.json")
        self.tracked_messages_file = os.path.join(DATA_DIR, f"{account_name}_tracked_messages.json")
        self._init_files()

    def _init_files(self):
        if not os.path.exists(self.main_file):
            data = {
                # ─── مشروع النشر التلقائي ───
                "publish_groups": [],
                "publish_messages": [],
                "is_publishing": True,
                "is_auto_reply_enabled": False,
                "auto_reply_keywords": [],
                "replied_users": [],
                "publish_logs": [],
                "publish_delays": {"min": 30, "max": 90},

                # ─── مشروع التسطير ───
                "random_texts_male": [],
                "random_texts_female": [],
                "sequential_sections": {},
                "reports": [],
                "tsterr_settings": {
                    "activation_keyword_male": "ذكر",
                    "activation_keyword_female": "انثى",
                    "sub_delay_mode": "gaussian",
                    "sub_delay_min": 2.0,
                    "sub_delay_max": 15.0,
                    "seq_delay_mode": "length",
                    "seq_delay_min": 2.0,
                    "seq_delay_max": 15.0,
                },

                # ─── مشروع الكتم ───
                "dm_muted": [],
                "group_muted": {},

                # ─── حالة التشغيل ───
                "running_jobs": {},
                "emergency_stopped": False,
            }
            self._save(self.main_file, data)

        if not os.path.exists(self.tracked_messages_file):
            self._save(self.tracked_messages_file, {})

    def _load(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Corrupted JSON file: {path}, attempting backup restore")
            backup = path + ".bak"
            if os.path.exists(backup):
                try:
                    with open(backup, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    pass
            return {}
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")
            return {}

    def _save(self, path, data):
        """حفظ آمن مع نسخة احتياطية لمنع فقدان البيانات"""
        try:
            tmp_path = path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # نسخة احتياطية من الملف القديم
            if os.path.exists(path):
                shutil.copy2(path, path + ".bak")
            # استبدال الملف الأصلي بالملف المؤقت
            shutil.move(tmp_path, path)
        except Exception as e:
            logger.error(f"Error saving {path}: {e}")
            # محاولة الحفظ المباشر كخطة بديلة
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except:
                pass

    def load_data(self):
        return self._load(self.main_file)

    def save_data(self, data):
        self._save(self.main_file, data)

    # ══════════════════════════════════════
    # مشروع النشر التلقائي
    # ══════════════════════════════════════
    def get_publish_groups(self):
        return self.load_data().get("publish_groups", [])

    def get_enabled_publish_groups(self):
        return [g for g in self.get_publish_groups() if g.get("enabled", True)]

    def add_publish_group(self, group_id, group_name=""):
        data = self.load_data()
        for g in data.get("publish_groups", []):
            if str(g["group_id"]) == str(group_id):
                return False
        data.setdefault("publish_groups", []).append({"group_id": str(group_id), "group_name": group_name, "enabled": True})
        self.save_data(data)
        return True

    def toggle_publish_group(self, index):
        data = self.load_data()
        grps = data.get("publish_groups", [])
        if 0 <= index < len(grps):
            grps[index]["enabled"] = not grps[index].get("enabled", True)
            self.save_data(data)
            return grps[index]["enabled"]
        return False

    def remove_publish_group(self, group_id):
        data = self.load_data()
        data["publish_groups"] = [g for g in data.get("publish_groups", []) if str(g["group_id"]) != str(group_id)]
        self.save_data(data)

    def remove_publish_group_by_index(self, index):
        data = self.load_data()
        grps = data.get("publish_groups", [])
        if 0 <= index < len(grps):
            removed = grps.pop(index)
            self.save_data(data)
            return removed
        return None

    def toggle_publish_group(self, group_id):
        data = self.load_data()
        for g in data.get("publish_groups", []):
            if str(g["group_id"]) == str(group_id):
                g["enabled"] = not g.get("enabled", True)
                self.save_data(data)
                return g["enabled"]
        return None

    def update_group_name(self, group_id, name):
        data = self.load_data()
        for g in data.get("publish_groups", []):
            if str(g["group_id"]) == str(group_id):
                g["group_name"] = name
                self.save_data(data)
                return

    def get_publish_messages(self):
        return self.load_data().get("publish_messages", [])

    def get_active_messages(self):
        return [m for m in self.get_publish_messages() if m.get("active", True)]

    def add_publish_message(self, content):
        data = self.load_data()
        data.setdefault("publish_messages", []).append({"content": content, "active": True})
        self.save_data(data)

    def remove_publish_message_by_index(self, index):
        data = self.load_data()
        msgs = data.get("publish_messages", [])
        if 0 <= index < len(msgs):
            removed = msgs.pop(index)
            self.save_data(data)
            return removed
        return None

    def toggle_publish_message(self, index):
        data = self.load_data()
        msgs = data.get("publish_messages", [])
        if 0 <= index < len(msgs):
            msgs[index]["active"] = not msgs[index].get("active", True)
            self.save_data(data)
            return msgs[index]["active"]
        return None

    def toggle_all_messages(self, active):
        data = self.load_data()
        for m in data.get("publish_messages", []):
            m["active"] = active
        self.save_data(data)

    def clear_publish_messages(self):
        data = self.load_data()
        data["publish_messages"] = []
        self.save_data(data)

    def is_publishing_enabled(self):
        return self.load_data().get("is_publishing", True)

    def set_publishing_enabled(self, val):
        data = self.load_data()
        data["is_publishing"] = val
        self.save_data(data)

    def get_publish_state(self):
        return self.load_data().get("publish_state", {"remaining_groups": [], "current_msg_idx": 0})

    def save_publish_state(self, remaining_groups, current_msg_idx):
        data = self.load_data()
        data["publish_state"] = {"remaining_groups": remaining_groups, "current_msg_idx": current_msg_idx}
        self.save_data(data)

    def get_publish_delays(self):
        d = self.load_data().get("publish_delays", {})
        return d.get("min", 30), d.get("max", 90)

    def set_publish_delays(self, mn, mx):
        data = self.load_data()
        data["publish_delays"] = {"min": mn, "max": mx}
        self.save_data(data)

    def add_publish_log(self, group_id, group_name, message, status):
        data = self.load_data()
        from datetime import datetime
        data.setdefault("publish_logs", []).append({
            "group_id": group_id, "group_name": group_name,
            "message": message[:100], "status": status,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        # الاحتفاظ بآخر 200 سجل فقط
        if len(data["publish_logs"]) > 200:
            data["publish_logs"] = data["publish_logs"][-200:]
        self.save_data(data)

    def get_publish_logs(self):
        return self.load_data().get("publish_logs", [])

    # ─── الرد التلقائي ───
    def is_auto_reply_enabled(self):
        return self.load_data().get("is_auto_reply_enabled", False)

    def set_auto_reply_enabled(self, val):
        data = self.load_data()
        data["is_auto_reply_enabled"] = val
        self.save_data(data)

    def get_auto_reply_keywords(self):
        return self.load_data().get("auto_reply_keywords", [])

    def get_active_auto_reply_keywords(self):
        return [k for k in self.get_auto_reply_keywords() if k.get("active", True)]

    def add_auto_reply_keyword(self, keyword, reply_text):
        data = self.load_data()
        data.setdefault("auto_reply_keywords", []).append({"keyword": keyword, "reply_text": reply_text, "active": True})
        self.save_data(data)

    def remove_auto_reply_keyword(self, keyword):
        data = self.load_data()
        data["auto_reply_keywords"] = [k for k in data.get("auto_reply_keywords", []) if k["keyword"] != keyword]
        self.save_data(data)

    def remove_auto_reply_by_index(self, index):
        data = self.load_data()
        kws = data.get("auto_reply_keywords", [])
        if 0 <= index < len(kws):
            removed = kws.pop(index)
            self.save_data(data)
            return removed
        return None

    def toggle_auto_reply_keyword(self, index):
        data = self.load_data()
        kws = data.get("auto_reply_keywords", [])
        if 0 <= index < len(kws):
            kws[index]["active"] = not kws[index].get("active", True)
            self.save_data(data)
            return kws[index]["active"]
        return None

    def toggle_all_auto_reply(self, active):
        data = self.load_data()
        for k in data.get("auto_reply_keywords", []):
            k["active"] = active
        self.save_data(data)

    def is_user_replied(self, user_id, keyword):
        data = self.load_data()
        for r in data.get("replied_users", []):
            if str(r["user_id"]) == str(user_id) and r["keyword"] == keyword:
                return True
        return False

    def mark_user_replied(self, user_id, keyword, chat_id):
        data = self.load_data()
        data.setdefault("replied_users", []).append({"user_id": str(user_id), "keyword": keyword, "chat_id": str(chat_id)})
        # تحديد حد أقصى للسجلات لمنع نمو غير محدود
        if len(data["replied_users"]) > 5000:
            data["replied_users"] = data["replied_users"][-3000:]
        self.save_data(data)

    # ══════════════════════════════════════
    # مشروع التسطير - تسطير السب
    # ══════════════════════════════════════
    def get_tsterr_settings(self):
        data = self.load_data()
        settings = data.get("tsterr_settings", {})
        # ضمان وجود القيم الافتراضية
        defaults = {
            "activation_keyword_male": "ذكر",
            "activation_keyword_female": "انثى",
            "sub_delay_mode": "gaussian",
            "sub_delay_min": 2.0,
            "sub_delay_max": 15.0,
            "seq_delay_mode": "length",
            "seq_delay_min": 2.0,
            "seq_delay_max": 15.0,
        }
        for k, v in defaults.items():
            if k not in settings:
                settings[k] = v
        return settings

    def update_tsterr_setting(self, key, value):
        data = self.load_data()
        data.setdefault("tsterr_settings", {})[key] = value
        self.save_data(data)

    def get_random_texts(self, gender):
        return self.load_data().get(f"random_texts_{gender}", [])

    def add_random_texts(self, gender, texts):
        data = self.load_data()
        key = f"random_texts_{gender}"
        existing = set(data.get(key, []))
        added = 0
        for t in texts:
            if t not in existing:
                data.setdefault(key, []).append(t)
                existing.add(t)
                added += 1
        self.save_data(data)
        return added

    def remove_random_text(self, gender, index):
        data = self.load_data()
        key = f"random_texts_{gender}"
        texts = data.get(key, [])
        if 0 <= index < len(texts):
            texts.pop(index)
            data[key] = texts
            self.save_data(data)
            return True
        return False

    def clear_random_texts(self, gender):
        """حذف جميع النصوص لجنس معين"""
        data = self.load_data()
        key = f"random_texts_{gender}"
        data[key] = []
        self.save_data(data)

    # ══════════════════════════════════════
    # مشروع التسطير - التسطير المتسلسل
    # ══════════════════════════════════════
    def get_sequential_sections(self):
        return self.load_data().get("sequential_sections", {})

    def get_sequential_section(self, name):
        return self.get_sequential_sections().get(name, None)

    def add_sequential_section(self, title):
        """إنشاء سلسلة جديدة بعنوان (العنوان هو كلمة التفعيل)"""
        data = self.load_data()
        if title in data.get("sequential_sections", {}):
            return False
        data.setdefault("sequential_sections", {})[title] = {
            "items": []
        }
        self.save_data(data)
        return True

    def remove_sequential_section(self, name):
        data = self.load_data()
        if name in data.get("sequential_sections", {}):
            # حذف ملفات الوسائط المرتبطة
            section = data["sequential_sections"][name]
            items = section.get("items", [])
            for item in items:
                if item.get("type") != "text" and item.get("file_path"):
                    try:
                        os.remove(item["file_path"])
                    except OSError:
                        pass
            del data["sequential_sections"][name]
            self.save_data(data)
            return True
        return False

    def add_sequential_item(self, section_name, item):
        """إضافة عنصر (نص أو وسائط) إلى سلسلة
        item format: {"type": "text|photo|sticker|animation|video|document", "content": "...", "file_path": "..."}
        """
        data = self.load_data()
        sec = data.get("sequential_sections", {}).get(section_name)
        if not sec:
            return False
        sec.setdefault("items", []).append(item)
        self.save_data(data)
        return True

    def get_sequential_items(self, section_name):
        """الحصول على جميع عناصر سلسلة"""
        sec = self.get_sequential_section(section_name)
        if not sec:
            return []
        # دعم التوافق مع الهيكل القديم
        if "items" in sec:
            return sec["items"]
        elif "texts" in sec:
            return [{"type": "text", "content": t} for t in sec.get("texts", [])]
        return []

    def remove_sequential_item(self, section_name, index):
        data = self.load_data()
        sec = data.get("sequential_sections", {}).get(section_name)
        if not sec:
            return False
        items = sec.get("items", [])
        if 0 <= index < len(items):
            removed = items.pop(index)
            if removed.get("type") != "text" and removed.get("file_path"):
                try:
                    os.remove(removed["file_path"])
                except OSError:
                    pass
            self.save_data(data)
            return True
        return False

    def clear_sequential_items(self, section_name):
        data = self.load_data()
        sec = data.get("sequential_sections", {}).get(section_name)
        if not sec:
            return False
        for item in sec.get("items", []):
            if item.get("type") != "text" and item.get("file_path"):
                try:
                    os.remove(item["file_path"])
                except OSError:
                    pass
        sec["items"] = []
        self.save_data(data)
        return True

    def get_sequential_titles(self):
        """الحصول على جميع عناوين السلاسل"""
        return list(self.get_sequential_sections().keys())

    # ─── التقارير ───
    def get_reports(self):
        return self.load_data().get("reports", [])

    def add_report(self, report):
        data = self.load_data()
        data.setdefault("reports", []).append(report)
        if len(data["reports"]) > 50:
            data["reports"] = data["reports"][-50:]
        self.save_data(data)

    # ─── الرسائل المتتبعة ───
    def track_message(self, chat_id, msg_id):
        tracked = self._load(self.tracked_messages_file)
        key = str(chat_id)
        msgs = tracked.setdefault(key, [])
        msgs.append(msg_id)
        # تحديد حد أقصى لمنع نمو غير محدود
        if len(msgs) > 500:
            tracked[key] = msgs[-300:]
        self._save(self.tracked_messages_file, tracked)

    def get_tracked_messages(self):
        return self._load(self.tracked_messages_file)

    def clear_tracked_messages(self):
        self._save(self.tracked_messages_file, {})

    # ══════════════════════════════════════
    # مشروع الكتم
    # ══════════════════════════════════════
    def get_dm_muted(self):
        return self.load_data().get("dm_muted", [])

    def add_dm_mute(self, user_id):
        data = self.load_data()
        if user_id not in data.setdefault("dm_muted", []):
            data["dm_muted"].append(user_id)
            self.save_data(data)
            return True
        return False

    def remove_dm_mute(self, user_id):
        data = self.load_data()
        if user_id in data.get("dm_muted", []):
            data["dm_muted"].remove(user_id)
            self.save_data(data)
            return True
        return False

    def is_dm_muted(self, user_id):
        return user_id in self.load_data().get("dm_muted", [])

    def get_group_muted(self):
        return self.load_data().get("group_muted", {})

    def add_group_mute(self, group_id, user_id):
        data = self.load_data()
        key = str(group_id)
        muted = data.setdefault("group_muted", {}).setdefault(key, [])
        if user_id not in muted:
            muted.append(user_id)
            self.save_data(data)
            return True
        return False

    def remove_group_mute(self, group_id, user_id):
        data = self.load_data()
        key = str(group_id)
        muted = data.get("group_muted", {}).get(key, [])
        if user_id in muted:
            muted.remove(user_id)
            if not muted:
                del data["group_muted"][key]
            self.save_data(data)
            return True
        return False

    def is_group_muted(self, group_id, user_id):
        data = self.load_data()
        is_global = user_id in data.get("group_muted", {}).get("all", [])
        is_local = user_id in data.get("group_muted", {}).get(str(group_id), [])
        return is_global or is_local

    # ══════════════════════════════════════
    # إدارة حالة التشغيل (Job Persistence)
    # ══════════════════════════════════════
    def save_running_job(self, job_id, job_data):
        """حفظ مهمة نشطة في قاعدة البيانات"""
        data = self.load_data()
        data.setdefault("running_jobs", {})[job_id] = job_data
        self.save_data(data)

    def remove_running_job(self, job_id):
        """إزالة مهمة منتهية"""
        data = self.load_data()
        jobs = data.get("running_jobs", {})
        if job_id in jobs:
            del jobs[job_id]
            self.save_data(data)

    def get_running_jobs(self):
        """الحصول على جميع المهام المحفوظة"""
        return self.load_data().get("running_jobs", {})

    def clear_running_jobs(self):
        """مسح جميع المهام المحفوظة"""
        data = self.load_data()
        data["running_jobs"] = {}
        self.save_data(data)

    def set_emergency_stopped(self, val):
        """تعيين حالة الإيقاف الطارئ"""
        data = self.load_data()
        data["emergency_stopped"] = val
        self.save_data(data)

    def is_emergency_stopped(self):
        """التحقق من حالة الإيقاف الطارئ"""
        return self.load_data().get("emergency_stopped", False)
