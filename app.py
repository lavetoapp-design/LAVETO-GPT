import streamlit as st
import pandas as pd
from groq import Groq

st.set_page_config(page_title="تطبيق لافيتو", page_icon="🧵", layout="centered")

st.markdown("""
    <style>
    .stApp { direction: rtl; }
    </style>
""", unsafe_allow_html=True)

st.title("🧵 مساعد مصنع لافيتو")

# إدخال المفتاح في الجانب أو تثبيته برمجياً
api_key = st.sidebar.text_input("Groq API Key", type="password", value="")

# رفع ملف الإكسيل
uploaded_file = st.file_uploader("ارفع ملف إكسيل المصنع (sales.xlsx)", type=["xlsx"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("اسأل عن مبيعات، كميات، أو موديل..."):
    if not api_key:
        st.error("يرجى إدخال Groq API Key أولاً في القائمة الجانبية.")
    elif uploaded_file is None:
        st.warning("يرجى رفع ملف الإكسيل أولاً للبدء.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # قراءة البيانات
        df = pd.read_excel(uploaded_file)
        data_preview = df.head(15).to_string(index=False)
        
        client = Groq(api_key=api_key)
        
        system_instruction = f"""
        أنت مساعد ذكي لإدارة مصنع ملابس لافيتو.
        أجب على استفسارات المبيعات والكميات بدقة واختصار استناداً لبيانات الشيت.
        أعمدة الشيت: {list(df.columns)}
        عينة من البيانات:
        {data_preview}
        """

        with st.chat_message("assistant"):
            with st.spinner("جاري مراجعة الشيت..."):
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    model="qwen-2.5-32b", # موديل سريع ومجاني
                )
                answer = chat_completion.choices[0].message.content
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
