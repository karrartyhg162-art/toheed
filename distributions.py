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

# ─── تأخير حسب طول النص (Length-based) ───
def length_based_delay(text_length: int, min_delay: float, max_delay: float) -> float:
    """حساب التأخير بناءً على طول النص ضمن نطاق محدد
    النص الأطول = تأخير أطول، النص الأقصر = تأخير أقصر"""
    MAX_REF_LENGTH = 2000
    ratio = min(text_length / MAX_REF_LENGTH, 1.0)
    delay = min_delay + (max_delay - min_delay) * ratio
    variation = random.uniform(0.9, 1.1)
    return max(min_delay, min(delay * variation, max_delay))

# ─── دوال مساعدة ───
def gaussian_reply_delay() -> float:
    return gaussian_delay(3.0, 10.0)

def random_range_delay(min_val: float, max_val: float) -> float:
    """تأخير عشوائي بسيط ضمن نطاق"""
    return random.uniform(min_val, max_val)
