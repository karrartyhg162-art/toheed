# ══════════════════════════════════════════════════════════════
# التوزيعات الاحتمالية الذكية لمحاكاة السلوك البشري
# ══════════════════════════════════════════════════════════════
import random
import math

# ─── التوزيع الغاوسي (Gaussian) ───
def gaussian_delay(min_val: float, max_val: float) -> float:
    """تأخير بتوزيع غاوسي - يركّز على الوسط مع تباين طبيعي"""
    mean = (min_val + max_val) / 2
    std_dev = (max_val - min_val) / 4
    delay = random.gauss(mean, std_dev)
    return max(min_val, min(delay, max_val))

def gaussian_pick_index(count: int) -> int:
    """اختيار فهرس بتوزيع غاوسي - للرسائل"""
    if count <= 0:
        return 0
    if count == 1:
        return 0
    mean = (count - 1) / 2.0
    std_dev = (count - 1) / 4.0
    idx = int(round(random.gauss(mean, std_dev)))
    return max(0, min(count - 1, idx))

# ─── التوزيع المرجّح (Weighted) ───
def weighted_pick_index(count: int, history: dict = None) -> int:
    """اختيار فهرس بتوزيع مرجّح - للمجموعات"""
    if count <= 0:
        return 0
    if count == 1:
        return 0
    weights = []
    for i in range(count):
        base_weight = 1.0
        if history and i in history:
            uses = history[i]
            base_weight = 1.0 / (1.0 + uses * 0.5)
        noise = random.uniform(0.8, 1.2)
        weights.append(base_weight * noise)
    total = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0
    for i, w in enumerate(weights):
        cumulative += w
        if r <= cumulative:
            return i
    return count - 1

# ─── توزيع وايبل (Weibull) ───
def weibull_delay(min_val: float, max_val: float, shape: float = 1.5) -> float:
    """تأخير بتوزيع وايبل"""
    scale = (max_val - min_val) / math.pow(math.log(2), 1.0 / shape)
    sample = min_val + random.weibullvariate(scale, shape)
    return max(min_val, min(sample, max_val))

def weibull_security_delay(base: float = 2.0, max_delay: float = 30.0) -> float:
    return weibull_delay(base, max_delay, shape=1.8)

def weibull_retry_delay(attempt: int, base: float = 3.0) -> float:
    min_d = base * (1.5 ** attempt)
    max_d = min_d * 3
    return weibull_delay(min_d, min(max_d, 120.0), shape=2.0)

# ─── تأخير حسب طول النص (Length-based) - محاكاة كتابة بشرية ───
def length_based_delay(text_length: int, min_delay: float, max_delay: float) -> float:
    """حساب التأخير بناءً على طول النص بمحاكاة سلوك الكتابة البشرية
    
    المنطق:
    - أقل من 20 حرف → 2 إلى 4 ثواني (رسالة قصيرة جداً)
    - من 20 إلى 100 حرف → 4 إلى 8 ثواني (رسالة متوسطة)
    - أكثر من 100 حرف → 8 إلى 15 ثانية (رسالة طويلة)
    
    يتم إضافة تفاوت عشوائي طبيعي (±15%) لمحاكاة التغير البشري
    """
    # سرعة كتابة بشرية تقريبية: 4-7 أحرف في الثانية
    # مع وقت تفكير قبل الكتابة: 1-2 ثانية
    
    think_time = random.uniform(0.8, 2.0)  # وقت التفكير قبل البدء بالكتابة
    
    if text_length <= 0:
        # ملصقات ووسائط - تأخير بسيط
        base_delay = random.uniform(1.5, 3.5)
    elif text_length < 20:
        # رسالة قصيرة جداً (كلمة أو كلمتين)
        typing_speed = random.uniform(5.0, 7.0)  # أحرف/ثانية (سريع لأن النص قصير)
        base_delay = think_time + (text_length / typing_speed)
        base_delay = max(2.0, min(base_delay, 4.0))
    elif text_length < 100:
        # رسالة متوسطة
        typing_speed = random.uniform(3.5, 5.5)  # أحرف/ثانية
        base_delay = think_time + (text_length / typing_speed)
        base_delay = max(4.0, min(base_delay, 8.0))
    else:
        # رسالة طويلة
        typing_speed = random.uniform(3.0, 5.0)  # أحرف/ثانية
        base_delay = think_time + (text_length / typing_speed)
        base_delay = max(8.0, min(base_delay, 15.0))
    
    # تفاوت عشوائي طبيعي (±15%) - البشر لا يكتبون بنفس السرعة دائماً
    human_variation = random.uniform(0.85, 1.15)
    final_delay = base_delay * human_variation
    
    # ضمان البقاء ضمن النطاق المحدد من المستخدم
    return max(min_delay, min(final_delay, max_delay))

# ─── تأخير ذكي حسب نوع المحتوى ───
def smart_content_delay(content_type: str, text_length: int = 0, min_delay: float = 2.0, max_delay: float = 15.0) -> float:
    """حساب التأخير بناءً على نوع المحتوى وطوله
    يحاكي السلوك البشري الطبيعي عند إرسال أنواع مختلفة من المحتوى
    """
    if content_type == "text":
        return length_based_delay(text_length, min_delay, max_delay)
    elif content_type == "sticker":
        # الملصقات سريعة الإرسال - الشخص يختار ملصق ويرسله
        delay = random.uniform(1.5, 4.0)
        return max(min_delay, min(delay, max_delay))
    elif content_type in ("photo", "animation"):
        # الصور والصور المتحركة - وقت اختيار أطول قليلاً
        delay = random.uniform(2.0, 5.0)
        return max(min_delay, min(delay, max_delay))
    elif content_type in ("video", "document"):
        # الفيديو والملفات - وقت تحميل + اختيار
        delay = random.uniform(3.0, 7.0)
        return max(min_delay, min(delay, max_delay))
    else:
        # نوع غير معروف - تأخير متوسط
        return random.uniform(min_delay, min(min_delay + 5.0, max_delay))

# ─── دوال مساعدة ───
def gaussian_reply_delay() -> float:
    return gaussian_delay(3.0, 10.0)

def random_range_delay(min_val: float, max_val: float) -> float:
    """تأخير عشوائي بسيط ضمن نطاق"""
    return random.uniform(min_val, max_val)
