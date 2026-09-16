import streamlit as st
import pandas as pd
from groq import Groq

# إعدادات الصفحة
st.set_page_config(page_title="تطبيق لافيتو", page_icon="🧵", layout="centered")

# ضبط اتجاه الكتابة للغة العربية
st.markdown("""
    <style>
    .stApp { direction: rtl; }
    </style>
""", unsafe_allow_html=True)

st.title("🧵 مساعد مصنع لافيتو")

# القائمة الجانبية: إدخال المفتاح واختيار الموديل
st.sidebar.header("الإعدادات")
api_key = st.sidebar.text_input("Groq API Key", type="password", value="")

selected_model = None

if api_key:
    try:
        client = Groq(api_key=api_key)
        # جلب قائمة الموديلات المفعلة لحسابك مباشرة
        models_data = client.models.list()
        available_models = [m.id for m in models_data.data if "whisper" not in m.id and "guard" not in m.id]
        if available_models:
            selected_model = st.sidebar.selectbox("الموديل المتاح في حسابك:", available_models)
        else:
            selected_model = st.sidebar.text_input("اسم الموديل", value="openai/gpt-oss-20b")
    except Exception as e:
        st.sidebar.warning("تأكد من صحة مفتاح الـ API")
        selected_model = "openai/gpt-oss-20b"
else:
    st.sidebar.info("أدخل مفتاح Groq API لتفعيل الموديل.")

# رفع ملف الإكسيل
uploaded_file = st.file_uploader("ارفع ملف إكسيل المصنع (sales.xlsx)", type=["xlsx"])

# ذاكرة المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل السابقة
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال سؤال المستخدم
if prompt := st.chat_input("اسأل عن مبيعات، كميات، أو موديل..."):
    if not api_key:
        st.error("يرجى إدخال Groq API Key أولاً في القائمة الجانبية.")
    elif uploaded_file is None:
        st.warning("يرجى رفع ملف الإكسيل أولاً للبدء.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            # قراءة الإكسيل
            df = pd.read_excel(uploaded_file)
            data_preview = df.head(15).to_string(index=False)

            client = Groq(api_key=api_key)

            system_instruction = f"""
            أنت مساعد ذكي لإدارة مصنع ملابس لافيتو.
            أجب على استفسارات المبيعات والكميات بدقة واختصار استناداً لبيانات الشيت.
            أعمدة الشيت المتاحة: {list(df.columns)}
            عينة من البيانات:
            {data_preview}
            """

            with st.chat_message("assistant"):
                with st.spinner("جاري مراجعة الشيت والرد..."):
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        model=selected_model if selected_model else "openai/gpt-oss-20b"
                    )
                    answer = chat_completion.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            st.error(f"حدث خطأ: {e}")
