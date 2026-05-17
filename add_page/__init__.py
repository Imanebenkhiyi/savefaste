from flask import Blueprint

# إنشاء Blueprint خاص بإضافة الصفحات
add_page_bp = Blueprint(
    'add_page',                   # اسم الـ Blueprint (يستخدم في url_for وغيره)
    __name__,                     # اسم الوحدة الحالية
    template_folder='templates', # مجلد القوالب (html)
    static_folder='static'       # مجلد الملفات الثابتة (CSS, JS, صور)
)

# استيراد المسارات بعد تعريف الـ Blueprint
from . import routes
