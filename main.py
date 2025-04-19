import io
import re
import PyPDF2
import telebot
import uuid
import firebase_admin
from firebase_admin import credentials, firestore
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

# إعداد Firebase
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

TELEGRAM_BOT_TOKEN = "1677851489:AAHwJMHtD6OR1T-Iw48CzDPtjywCd5gGzpE"
ADMIN_ID = 661135226, 6151396284  # المطور الأساسي

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# تنظيف النصوص
def clean_text(text):
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

# إزالة أي رموز Unicode غير قابلة للترميز
def safe_text(text):
    return text.encode("utf-8", "surrogatepass").decode("utf-8", "ignore")

# تحليل الأسئلة
def parse_quiz(quiz_text):
    quiz_data = []
    cleaned_text = clean_text(quiz_text)

    pattern = re.compile(
        r'(\d+)\.\s*(.*?)\s*A\)\s*(.*?)\s*B\)\s*(.*?)\s*C\)\s*(.*?)\s*D\)\s*(.*?)\s*Answer:\s*([A-D])',
        re.MULTILINE | re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(cleaned_text)
    for match in matches:
        question_number = match[0].strip()
        question_text = match[1].strip()
        options = [match[i].strip() for i in range(2, 6)]
        correct_option = match[6].strip().upper()

        if correct_option in ['A', 'B', 'C', 'D']:
            correct_option_id = ord(correct_option) - ord("A")
            quiz_data.append({
                "number": question_number,
                "question": question_text,
                "options": options,
                "correct_option": correct_option_id
            })

    return quiz_data

# القائمة الرئيسية
def main_menu(is_admin=False):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📥 إرسال كويز جديد", callback_data="new_quiz"),
        InlineKeyboardButton("📂 عرض الكويزات", callback_data="list_quizzes")
    )
    if is_admin:
        markup.add(InlineKeyboardButton("👤 إدارة المطورين", callback_data="manage_devs"))
    markup.add(InlineKeyboardButton("❌ إلغاء", callback_data="cancel"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    is_admin = message.chat.id in ADMIN_ID
    doc = db.collection("developers").document(str(message.chat.id)).get()
    is_dev = is_admin or doc.exists
    if is_dev:
        bot.send_message(message.chat.id, "مرحبًا بك! اختر من القائمة:", reply_markup=main_menu(is_admin))
    else:
        # عرض الكويزات فقط للمستخدم العادي
        quizzes = db.collection("quizzes").stream()
        markup = InlineKeyboardMarkup()
        found = False
        for doc in quizzes:
            data = doc.to_dict()
            quiz_id = doc.id
            name = data.get("name", "بدون اسم")
            markup.add(InlineKeyboardButton(f"📖 {name}", callback_data=f"user_quiz_{quiz_id}"))
            found = True
        if not found:
            bot.send_message(message.chat.id, "📂 لا توجد اختبارات حالياً.")
        else:
            bot.send_message(message.chat.id, "📂 اختر اختبارًا لبدء حلّه:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("user_quiz_"))
def send_quiz_to_user(call):
    quiz_id = call.data.split("_")[2]
    doc = db.collection("quizzes").document(quiz_id).get()
    if not doc.exists:
        bot.send_message(call.message.chat.id, "⚠️ لم يتم العثور على الكويز.")
        return
    quiz = doc.to_dict()
    questions = quiz.get("questions", [])

    # إرسال اسم الكويز أولاً
    bot.send_message(call.message.chat.id, f"{quiz.get('name', 'بدون اسم')}")

    for q in questions:
        bot.send_poll(
            chat_id=call.message.chat.id,
            question=f"{q['number']}. {q['question']}",
            options=[f"(A)   {q['options'][0]}", f"(B)   {q['options'][1]}", f"(C)   {q['options'][2]}", f"(D)   {q['options'][3]}"],
            type="quiz",
            correct_option_id=q['correct_option'],
            is_anonymous=False
        )
        time.sleep(3)

@bot.callback_query_handler(func=lambda call: call.data == "new_quiz")
def request_quiz_name(call):
    msg = bot.send_message(call.message.chat.id, "📋 أرسل اسم الكويز:")
    bot.register_next_step_handler(msg, receive_quiz_name)

def receive_quiz_name(message):
    if not message.text:
        bot.send_message(message.chat.id, "⚠️ يجب إدخال اسم نصي.")
        return
    quiz_name = safe_text(message.text.strip())
    quiz_id = str(uuid.uuid4())[:8]
    msg = bot.send_message(message.chat.id, f"📝 الآن أرسل الأسئلة بتنسيق الكويز لـ ({quiz_name}):")
    bot.register_next_step_handler(msg, lambda msg: handle_quiz_input(msg, quiz_name, quiz_id))

def handle_quiz_input(message, quiz_name, quiz_id):
    file_content = ""

    if message.document:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        if message.document.file_name.endswith(".txt"):
            file_content = downloaded_file.decode("utf-8", errors="ignore")

        elif message.document.file_name.endswith(".pdf"):
            try:
                reader = PyPDF2.PdfReader(io.BytesIO(downloaded_file))
                for page in reader.pages:
                    file_content += page.extract_text()
            except Exception as e:
                bot.send_message(message.chat.id, f"⚠️ فشل استخراج النص من ملف PDF: {e}")
                return
        else:
            bot.send_message(message.chat.id, "⚠️ الرجاء إرسال ملف بصيغة .txt أو .pdf فقط.")
            return
    elif message.text:
        file_content = safe_text(message.text)
    else:
        bot.send_message(message.chat.id, "⚠️ لم يتم العثور على نص أو ملف.")
        return

    quiz_data = parse_quiz(file_content)
    if not quiz_data:
        bot.send_message(message.chat.id, "⚠️ لم يتم التعرف على أسئلة.")
        return

    db.collection("quizzes").document(quiz_id).set({"name": quiz_name, "questions": quiz_data})
    bot.send_message(message.chat.id, f"✅ تم حفظ الكويز **{quiz_name}**.", reply_markup=main_menu(message.chat.id in ADMIN_ID))

@bot.callback_query_handler(func=lambda call: call.data == "list_quizzes")
def list_quizzes(call):
    quizzes = db.collection("quizzes").stream()
    markup = InlineKeyboardMarkup()
    found = False
    for doc in quizzes:
        data = doc.to_dict()
        quiz_id = doc.id
        name = data.get("name", "بدون اسم")
        markup.add(InlineKeyboardButton(f"📖 {name}", callback_data=f"quiz_options_{quiz_id}"))
        found = True
    if not found:
        bot.send_message(call.message.chat.id, "📂 لا توجد اختبارات حالياً.")
    else:
        bot.send_message(call.message.chat.id, "📂 اختر اختبارًا لإدارته:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("quiz_options_"))
def show_quiz_options(call):
    quiz_id = call.data.split("_")[2]
    doc = db.collection("quizzes").document(quiz_id).get()
    if not doc.exists:
        bot.send_message(call.message.chat.id, "⚠️ لم يتم العثور على هذا الاختبار.")
        return
    quiz_name = doc.to_dict().get("name", "بدون اسم")
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📨 إرسال الكويز", callback_data=f"select_quiz_{quiz_id}"),
        InlineKeyboardButton("✏️ تعديل الكويز", callback_data=f"edit_quiz_{quiz_id}"),
        InlineKeyboardButton("🗑️ حذف الكويز", callback_data=f"delete_quiz_{quiz_id}")
    )
    bot.send_message(call.message.chat.id, f"🔹 إدارة الكويز: {quiz_name}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_quiz_"))
def send_quiz_to_target(call):
    quiz_id = call.data.split("_")[2]
    msg = bot.send_message(call.message.chat.id, "🔹 أرسل معرف القناة أو المستخدم:")
    bot.register_next_step_handler(msg, lambda msg: send_quiz_to_target_final(msg, quiz_id))

def send_quiz_to_target_final(message, quiz_id):
    target = message.text.strip()
    try:
        bot.get_chat(target)
        doc = db.collection("quizzes").document(quiz_id).get()
        if not doc.exists:
            bot.send_message(message.chat.id, "⚠️ لم يتم العثور على الكويز.")
            return
        quiz = doc.to_dict()
        questions = quiz.get("questions", [])
        for q in questions:
            bot.send_poll(
                chat_id=target,
                question=f"{q['number']}. {q['question']}",
                options=[f"(A)   {q['options'][0]}", f"(B)   {q['options'][1]}", f"(C)   {q['options'][2]}", f"(D)   {q['options'][3]}"],
                type="quiz",
                correct_option_id=q['correct_option'],
                is_anonymous=True
            )
            time.sleep(5)
        bot.send_message(message.chat.id, "✅ تم إرسال الكويز.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ فشل الإرسال: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_quiz_"))
def edit_quiz(call):
    quiz_id = call.data.split("_")[2]
    msg = bot.send_message(call.message.chat.id, "✏️ أرسل الأسئلة الجديدة:")
    bot.register_next_step_handler(msg, lambda msg: update_quiz_data(msg, quiz_id))

def update_quiz_data(message, quiz_id):
    quiz_data = parse_quiz(safe_text(message.text))
    if not quiz_data:
        bot.send_message(message.chat.id, "⚠️ لم يتم التعرف على أي أسئلة.")
        return
    db.collection("quizzes").document(quiz_id).update({"questions": quiz_data})
    bot.send_message(message.chat.id, "✅ تم تحديث الأسئلة.", reply_markup=main_menu(message.chat.id in ADMIN_ID))

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_quiz_"))
def delete_quiz(call):
    quiz_id = call.data.split("_")[2]
    db.collection("quizzes").document(quiz_id).delete()
    bot.send_message(call.message.chat.id, "✅ تم حذف الكويز.", reply_markup=main_menu(call.message.chat.id in ADMIN_ID))

bot.polling(none_stop=True)

