# شامو ستور — متجر شحن الألعاب الإلكترونية

متجر عربي (RTL) لشحن الألعاب: ببجي موبايل، فري فاير، eFootball، Call of Duty Mobile، جينشين،
روبوكس، موبايل ليجندز، فورتنايت. يشمل تسجيل دخول بالبريد الإلكتروني وكلمة المرور، ومحفظة
رصيد داخلية، وطلبات شحن تُدار من لوحة تحكم.

مبني بـ Flask وFlask-SQLAlchemy وFlask-Login وFlask-WTF (حماية CSRF)، وقاعدة بيانات
SQLite افتراضية قابلة للاستبدال بأي قاعدة عبر `DATABASE_URL`.

## المزايا

**للعميل**
- إنشاء حساب باسم مستخدم وبريد وكلمة مرور (تشفير كلمات المرور عبر Werkzeug).
- تسجيل الدخول بالبريد وكلمة المرور، مع خيار «تذكرني».
- محفظة برصيد وحركات مسجّلة (شحن، شراء، استرداد، تعديل إداري) وسجل كامل للحركات.
- طلب شحن رصيد بطرق دفع محلية (زين كاش، آسياسيل، فاست باي، تحويل بنكي، USDT) مع رقم عملية التحويل.
- شراء الباقات من الرصيد عبر خطوة تأكيد، ثم متابعة حالة الطلب (بانتظار المراجعة → قيد التنفيذ → مكتمل).
- سجل الطلبات وتفاصيل كل طلب مع معرّف حساب اللعبة والحالة.

**للمسؤول**
- نظرة عامة على الإيرادات وأرصدة المحافظ والطلبات المعلّقة والأكثر مبيعاً.
- إضافة الألعاب وتعديل الباقات والأسعار وإخفاء/تفعيل أي عنصر.
- إدارة الطلبات وتغيير حالتها، ورفض الطلب يعيد المبلغ تلقائياً إلى محفظة العميل.
- مراجعة طلبات شحن الرصيد (قبول يضيف الرصيد، رفض لا يضيف).
- البحث عن المستخدمين وتعديل أرصدتهم مع تسجيل سبب التعديل في الحركات.

## التشغيل

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env            # ثم عدّل SECRET_KEY وبيانات المسؤول
.venv/bin/flask --app app init-db      # الجداول + كتالوج الألعاب + حساب المسؤول
.venv/bin/flask --app app seed-demo   # اختياري: عميل تجريبي برصيد وسجل طلبات
.venv/bin/python wsgi.py
```

الموقع على `http://localhost:5000`. للإنتاج:

```bash
.venv/bin/gunicorn -c gunicorn.conf.py wsgi:application
```

### الحسابات الافتراضية

| الدور | البريد | كلمة المرور |
| --- | --- | --- |
| مسؤول | `admin@shamostore.com` | `Admin@12345` |
| عميل تجريبي (بعد `seed-demo` فقط) | `player@shamostore.com` | `Player@12345` |

على خادم عام اضبط `ADMIN_PASSWORD` دائماً: الإعداد الافتراضي في `Dockerfile` و`render.yaml`
يرفض كلمة المرور الافتراضية (`ALLOW_DEFAULT_ADMIN=false`) ويفشل الإقلاع برسالة واضحة بدلاً من
إنشاء مسؤول بكلمة مرور معروفة.

`init-db` لا ينشئ أي حساب عميل ممول، حتى لا يحصل تثبيت إنتاجي على دخول تجريبي معروف.
الحساب التجريبي وطلباته تأتي من أمر `seed-demo` المنفصل، ويمكن تعطيله بـ
`ENABLE_DEMO_ACCOUNT=false`.

غيّر كلمة مرور المسؤول قبل أي استخدام حقيقي (`flask --app app create-admin` يحدّثها من
`ADMIN_PASSWORD`).

## النشر

المشروع تطبيق Flask، لذلك يحتاج خادماً يشغّل Python. Netlify أو GitHub Pages (استضافة ثابتة)
لا تستطيع تشغيله، وتحويلها إليه مباشرة يعطي صفحة «Page not found».

**Docker**

```bash
docker build -t shamostore .
docker run -p 8000:8000 \
  -e SECRET_KEY="مفتاح-طويل-عشوائي" \
  -e ADMIN_EMAIL="you@example.com" \
  -e ADMIN_PASSWORD="كلمة-مرور-قوية" \
  shamostore
```

**Render** (موصى به لنطاق دائم)

1. ارفع المستودع إلى GitHub ثم أنشئ Blueprint من ملف `render.yaml`.
2. أدخل `ADMIN_EMAIL` و`ADMIN_PASSWORD` عند الطلب؛ يُولّد `SECRET_KEY` تلقائياً.
3. المنصة تنشئ PostgreSQL وتمرر `DATABASE_URL`، والتطبيق يحوّل `postgres://` تلقائياً.

**خادم خاص (VPS)**

```bash
python3 -m venv /opt/shamostore/.venv
/opt/shamostore/.venv/bin/pip install -r requirements.txt
/opt/shamostore/.venv/bin/gunicorn -c gunicorn.conf.py wsgi:application
```

ثم ضع Nginx أمام المنفذ 8000 مع شهادة HTTPS (Certbot)، واضبط `SESSION_COOKIE_SECURE = True`.

## الاختبارات

```bash
.venv/bin/python -m pytest
```

تغطي الاختبارات: التسجيل وتكرار البريد، تسجيل الدخول الصحيح والخاطئ، صلاحيات المسؤول،
طلب شحن الرصيد وقبوله أو رفضه، الشراء من المحفظة، منع الشراء عند نقص الرصيد، واسترداد
المبلغ عند رفض الطلب، وتعديل الرصيد إدارياً.

## متغيرات البيئة

| المتغير | الوصف |
| --- | --- |
| `SECRET_KEY` | مفتاح الجلسات، إلزامي في الإنتاج |
| `DATABASE_URL` | رابط قاعدة البيانات، افتراضياً SQLite داخل `instance/` |
| `STORE_NAME` | اسم المتجر الظاهر في الواجهة |
| `CURRENCY_SYMBOL` | رمز العملة، افتراضياً `$` |
| `ADMIN_USERNAME` / `ADMIN_EMAIL` / `ADMIN_PASSWORD` | حساب المسؤول الذي ينشئه `init-db` |
| `ENABLE_DEMO_ACCOUNT` | `false` يمنع أمر `seed-demo` من إنشاء الحساب التجريبي |

## هيكل المشروع

```
app.py                 مصنع التطبيق، الفلاتر، أوامر CLI، معالجات الأخطاء
config.py              الإعدادات ونسخة الاختبار
extensions.py          db / login_manager / csrf
models.py              المستخدم، المحفظة وحركاتها، طلبات الشحن، الألعاب، الباقات، الطلبات
services.py            قواعد العمل: الشراء، تغيير حالة الطلب، مراجعة الشحن، ضبط الرصيد
forms.py               نماذج التحقق
blueprints/            shop، auth، wallet، orders، admin
templates/             واجهات Jinja بالعربية RTL
static/                CSS وJS والأيقونة
seed.py                تهيئة قاعدة البيانات والكتالوج والحسابات الافتراضية
tests/                 اختبارات pytest
```

## ملاحظات قبل الإطلاق

- لا تشغّل `seed-demo` على الإنتاج، فهو ينشئ عميلاً برصيد مجاني.
- ادفع طرق الدفع إلى بوابة حقيقية (مثل Stripe أو بوابة محلية) بدل التحويل اليدوي:
  نقطة التجريد جاهزة في `services.approve_topup` ولا تحتاج تغيير الواجهات.
- فعّل HTTPS، واضبط `SESSION_COOKIE_SECURE = True` في `config.py`.
- نقل بيانات حساب الدفع في `TOPUP_INSTRUCTIONS` داخل `models.py` إلى الإعدادات قبل النشر العام.
