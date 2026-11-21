from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    HiddenField,
    PasswordField,
    RadioField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Regexp,
    ValidationError,
)

from models import TOPUP_METHODS, User


class RegisterForm(FlaskForm):
    username = StringField(
        "اسم المستخدم",
        validators=[DataRequired(), Length(min=3, max=64)],
    )
    email = StringField(
        "البريد الإلكتروني",
        validators=[DataRequired(), Email(), Length(max=120)],
    )
    password = PasswordField(
        "كلمة المرور",
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    confirm_password = PasswordField(
        "تأكيد كلمة المرور",
        validators=[DataRequired(), EqualTo("password", message="كلمتا المرور غير متطابقتين.")],
    )
    submit = SubmitField("إنشاء الحساب")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data.strip()).first():
            raise ValidationError("اسم المستخدم مستخدم بالفعل.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("هذا البريد الإلكتروني مسجل بالفعل.")


class LoginForm(FlaskForm):
    email = StringField("البريد الإلكتروني", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("كلمة المرور", validators=[DataRequired()])
    remember_me = BooleanField("تذكرني على هذا الجهاز")
    submit = SubmitField("تسجيل الدخول")


class TopUpForm(FlaskForm):
    amount = DecimalField(
        "المبلغ",
        places=2,
        validators=[DataRequired(), NumberRange(min=1, max=5000, message="المبلغ بين 1 و 5000.")],
    )
    method = RadioField(
        "طريقة الدفع",
        choices=list(TOPUP_METHODS.items()),
        validators=[DataRequired()],
    )
    reference = StringField(
        "رقم العملية / المرجع",
        validators=[DataRequired(), Length(min=3, max=64)],
    )
    note = TextAreaField("ملاحظات إضافية", validators=[Length(max=500)])
    submit = SubmitField("إرسال طلب الشحن")


class CheckoutForm(FlaskForm):
    package_id = HiddenField(validators=[DataRequired()])
    player_id = StringField(
        "معرّف الحساب في اللعبة",
        validators=[
            DataRequired(),
            Length(min=4, max=64),
            Regexp(r"^[A-Za-z0-9 ._\-]+$", message="معرّف غير صالح، استخدم الأحرف والأرقام فقط."),
        ],
    )
    note = TextAreaField("ملاحظات", validators=[Length(max=300)])
    submit = SubmitField("متابعة الدفع")


class PlaceOrderForm(FlaskForm):
    package_id = HiddenField(validators=[DataRequired()])
    player_id = HiddenField(
        validators=[
            DataRequired(),
            Length(min=4, max=64),
            Regexp(r"^[A-Za-z0-9 ._\-]+$"),
        ],
    )
    note = HiddenField(validators=[Length(max=300)])
    submit = SubmitField("تأكيد الشراء من المحفظة")


class GameForm(FlaskForm):
    name = StringField("اسم اللعبة", validators=[DataRequired(), Length(max=128)])
    slug = StringField(
        "الرابط (slug)",
        validators=[
            DataRequired(),
            Length(max=80),
            Regexp(r"^[a-z0-9\-]+$", message="أحرف إنجليزية صغيرة وأرقام وشرطات فقط."),
        ],
    )
    tagline = StringField("سطر تعريفي", validators=[Length(max=160)])
    description = TextAreaField("الوصف", validators=[Length(max=2000)])
    category = SelectField(
        "الفئة",
        choices=[
            ("battle_royale", "باتل رويال"),
            ("shooter", "تصويب"),
            ("sports", "رياضة"),
            ("moba", "MOBA"),
            ("rpg", "RPG"),
            ("sandbox", "عالم مفتوح"),
        ],
        validators=[DataRequired()],
    )
    currency_name = StringField("اسم العملة", validators=[DataRequired(), Length(max=32)])
    accent = StringField(
        "لون الغلاف",
        default="#7c5cff",
        validators=[DataRequired(), Regexp(r"^#[0-9A-Fa-f]{6}$", message="استخدم لوناً مثل #7c5cff")],
    )
    sort_order = DecimalField("ترتيب العرض", default=0, places=0)
    is_active = BooleanField("مفعّلة", default=True)
    submit = SubmitField("إضافة اللعبة")

    def validate_slug(self, field):
        from models import Game

        if Game.query.filter_by(slug=field.data.strip().lower()).first():
            raise ValidationError("هذا الرابط مستخدم بالفعل.")


class PackageForm(FlaskForm):
    label = StringField("اسم الباقة", validators=[DataRequired(), Length(max=64)])
    amount = StringField("الكمية", validators=[Length(max=32)])
    price = DecimalField(
        "السعر",
        places=2,
        validators=[DataRequired(), NumberRange(min=0.01, max=100000)],
    )
    bonus = StringField("مكافأة (اختياري)", validators=[Length(max=64)])
    sort_order = DecimalField("ترتيب العرض", default=0, places=0)
    is_active = BooleanField("مفعّلة", default=True)
    submit = SubmitField("إضافة الباقة")
