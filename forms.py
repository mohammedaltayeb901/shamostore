from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, FloatField, SelectField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo, Length, NumberRange
from models import User

class LoginForm(FlaskForm):
    email = StringField("البريد الإلكتروني", validators=[DataRequired(), Email()])
    password = PasswordField("كلمة المرور", validators=[DataRequired()])
    remember_me = BooleanField("تذكرني")
    submit = SubmitField("تسجيل الدخول")

class RegistrationForm(FlaskForm):
    username = StringField("اسم المستخدم", validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField("البريد الإلكتروني", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("كلمة المرور", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "تأكيد كلمة المرور", validators=[DataRequired(), EqualTo("password", message="يجب أن تتطابق كلمات المرور.")])
    submit = SubmitField("إنشاء حساب")

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("اسم المستخدم هذا مستخدم بالفعل.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("هذا البريد الإلكتروني مستخدم بالفعل.")

# Add other forms as needed (e.g., GameForm, CheckoutForm, etc.)
class GameForm(FlaskForm):
    name = StringField("اسم اللعبة", validators=[DataRequired(), Length(max=128)])
    description = TextAreaField("الوصف")
    price = FloatField("السعر", validators=[DataRequired(), NumberRange(min=0)])
    image_url = StringField("رابط الصورة", validators=[Length(max=256)])
    category = StringField("الفئة", validators=[Length(max=64)])
    game_type = StringField("نوع اللعبة", validators=[DataRequired(), Length(max=64)])
    region = StringField("المنطقة", validators=[Length(max=64)])
    stock = IntegerField("المخزون", validators=[DataRequired(), NumberRange(min=0)])
    is_active = BooleanField("نشط", default=True)
    submit = SubmitField("حفظ اللعبة")

class CheckoutForm(FlaskForm):
    # Add fields for shipping/billing address if needed for physical goods, 
    # but for digital goods, we might only need payment details.
    payment_method = SelectField("طريقة الدفع", choices=[("credit_card", "بطاقة ائتمان"), ("paypal", "PayPal")], validators=[DataRequired()])
    # Add fields for credit card details if implementing directly (not recommended for production)
    # Example: card_number, expiry_date, cvv
    submit = SubmitField("إتمام الشراء")

class GameSearchForm(FlaskForm):
    query = StringField("بحث", validators=[DataRequired()])
    submit = SubmitField("بحث")
