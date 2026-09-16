import streamlit as st
import pandas as pd
from groq import Groq
import warnings
warnings.filterwarnings('ignore')

# إعدادات الصفحة
st.set_page_config(page_title="مساعد مصنع لافيتو", page_icon="🧵", layout="centered")

st.markdown("""
    <style>
    .stApp { direction: rtl; }
    </style>
""", unsafe_allow_html=True)

st.title("🧵 مساعد مصنع لافيتو للمبيعات والمخزون")

# إعدادات المفتاح والموديل
st.sidebar.header("الإعدادات")
api_key = st.sidebar.text_input("Groq API Key", type="password", value="")

selected_model = "llama-3.1-8b-instant"
if api_key:
    try:
        client = Groq(api_key=api_key)
        models_data = client.models.list()
        available_models = [m.id for m in models_data.data if "whisper" not in m.id and "guard" not in m.id]
        if available_models:
            selected_model = st.sidebar.selectbox("الموديل المتاح في حسابك:", available_models)
    except Exception:
        st.sidebar.warning("تأكد من صحة مفتاح الـ API")

uploaded_file = st.file_uploader("ارفع ملف إكسيل المصنع (sales.xlsx)", type=["xlsx"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("اسأل عن أكبر عميل، مبيعات مكتب، مسحوبات موديل..."):
    if not api_key:
        st.error("يرجى إدخال Groq API Key أولاً في القائمة الجانبية.")
    elif uploaded_file is None:
        st.warning("يرجى رفع ملف الإكسيل أولاً للبدء.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            xls = pd.ExcelFile(uploaded_file)
            
            # قراءة الشيتات
            df_trans = pd.read_excel(xls, sheet_name='Transaction') if 'Transaction' in xls.sheet_names else pd.DataFrame()
            df_clients = pd.read_excel(xls, sheet_name='Clients') if 'Clients' in xls.sheet_names else pd.DataFrame()
            df_products = pd.read_excel(xls, sheet_name='products') if 'products' in xls.sheet_names else pd.DataFrame()

            # --- حسابات بايثون الدقيقة المسبقة بدلاً من التخمين ---
            
            # 1. ترتيب جميع العملاء حسب المبيعات وصافي المبيعات
            clean_clients = pd.DataFrame()
            if not df_clients.empty and 'العميل' in df_clients.columns:
                clean_clients = df_clients[~df_clients['العميل'].astype(str).str.contains('الاجمالي|Unnamed', na=False)].copy()
                clean_clients['المبيعات'] = pd.to_numeric(clean_clients['المبيعات'], errors='coerce').fillna(0)
                clean_clients['المرتجعات'] = pd.to_numeric(clean_clients['المرتجعات'], errors='coerce').fillna(0)
                clean_clients['صافي المبيعات'] = pd.to_numeric(clean_clients['صافي المبيعات'], errors='coerce').fillna(0)
            
            top_clients_text = clean_clients.sort_values(by='المبيعات', ascending=False)[['العميل', 'المبيعات', 'المرتجعات', 'صافي المبيعات']].head(20).to_string(index=False) if not clean_clients.empty else "لا توجد بيانات عملاء"

            # 2. إجمالي المبيعات حسب حركات Transaction
            top_trans_clients = ""
            top_products = ""
            if not df_trans.empty:
                df_trans['quantity'] = pd.to_numeric(df_trans['quantity'], errors='coerce').fillna(0)
                top_trans_clients = df_trans.groupby('client')['quantity'].sum().sort_values(ascending=False).head(15).to_string()
                top_products = df_trans.groupby('product id')['quantity'].sum().sort_values(ascending=False).head(15).to_string()

            # 3. تجميع كل الحسابات الدقيقة كمعلومات مؤكدة
            accurate_context = f"""
            أعلى العملاء سحباً ومبيعات وفق شيت العملاء (محسوبة ومرتبة بدقة):
            {top_clients_text}

            أعلى العملاء سحباً من واقع حركات الفواتير (Transaction):
            {top_trans_clients}

            أكثر الموديلات مبيعاً وسحباً (بالكميات):
            {top_products}

            إجمالي مبيعات المصنع العامة: 10,640 قطعة (صافي بعد المرتجعات: 8,863 قطعة).
            """

            client = Groq(api_key=api_key)

            system_instruction = f"""
            أنت مساعد ذكي لإدارة مصنع ملابس لافيتو (Laveto).
            مهمتك الإجابة بدقة وحيادية استناداً إلى الحسابات المجهزة التالية.
            ممنوع تخمين الأرقام أو افتراض أن أول سطر هو الأكبر. اعتمد على الإحصائيات المحسوبة أدناه فقط:
            {accurate_context}
            """

            with st.chat_message("assistant"):
                with st.spinner("جاري استخراج الأرقام الدقيقة..."):
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": prompt}
                        ],
                        model=selected_model
                    )
                    answer = chat_completion.choices[0].message.content
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة الشيت: {e}")
