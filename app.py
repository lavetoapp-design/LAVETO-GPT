import streamlit as st
import pandas as pd
from groq import Groq
import openpyxl
import warnings
warnings.filterwarnings('ignore')

# إعدادات واجهة التطبيق
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

uploaded_file = st.file_uploader("ارفع ملف إكسيل المصنع (تقرير مبيعات المصنع مفصل)", type=["xlsx"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("اسأل عن إجمالي المبيعات، أكبر عميل، المخزون، أو الموديلات..."):
    if not api_key:
        st.error("يرجى إدخال Groq API Key أولاً في القائمة الجانبية.")
    elif uploaded_file is None:
        st.warning("يرجى رفع ملف الإكسيل أولاً للبدء.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            # 1. قراءة القيم الجاهزة والمباشرة من شيت Dashboard باستخدام openpyxl
            wb = openpyxl.load_workbook(uploaded_file, data_only=True)
            dashboard_data = {}
            
            # البحث عن شيت Dashboard
            dash_sheet_name = None
            for name in wb.sheetnames:
                if 'dash' in name.lower() and 'chart' not in name.lower():
                    dash_sheet_name = name
                    break
            
            if dash_sheet_name:
                ws_dash = wb[dash_sheet_name]
                # استخراج القيم الثابتة من خلايا الداشبورد
                dashboard_data['أكبر عميل سحباً'] = ws_dash['P43'].value
                dashboard_data['إجمالي صافي المبيعات الكلي للمصنع'] = ws_dash['K50'].value
                dashboard_data['إجمالي القطع المرتجعة الكلي'] = ws_dash['K57'].value
                dashboard_data['إجمالي الإنتاج والإضافات بالمصنع'] = ws_dash['P58'].value
                dashboard_data['الموديل الأكثر مبيعاً'] = ws_dash['N45'].value
                dashboard_data['أعلى موديل به مرتجعات'] = ws_dash['M47'].value

            # تحويل بيانات الداشبورد لنص مباشر
            dashboard_text = "\n".join([f"- {k}: {v}" for k, v in dashboard_data.items() if v is not None])

            # 2. قراءة الجداول التفصيلية في حال السؤال عن تفاصيل عميل أو صنف محدد
            xls = pd.ExcelFile(uploaded_file)
            df_clients = pd.read_excel(xls, sheet_name='Clients') if 'Clients' in xls.sheet_names else pd.DataFrame()
            
            clients_summary = ""
            if not df_clients.empty and 'العميل' in df_clients.columns:
                clean_c = df_clients[~df_clients['العميل'].astype(str).str.contains('الاجمالي|Unnamed', na=False)].dropna(subset=['العميل'])
                clients_summary = clean_c[['العميل', 'المبيعات', 'المرتجعات', 'صافي المبيعات']].to_string(index=False)

            system_instruction = f"""
            أنت مساعد ذكي لإدارة مصنع ملابس لافيتو (Laveto).
            
            قاعدة أساسية وصارمة:
            الأرقام الإجمالية العامة (مثل أكبر عميل، إجمالي المبيعات، إجمالي المرتجعات، إجمالي الإنتاج، أعلى موديل مبيعاً أو مرتجعاً) تأخذها مباشرة وبشكل قطعي من شيت Dashboard المسجل أدناه، دون إجراء أي عمليات حسابية أو تخمين:
            
            === بيانات شيت Dashboard المعتمدة الرسمية ===
            {dashboard_text}
            =============================================

            إذا كان السؤال عن تفاصيل عميل محدد بالاسم، ارجع لجدول العملاء أدناه:
            {clients_summary}
            
            أجب باختصار ودقة وبالأرقام المذكورة في الداشبورد فقط.
            """

            client = Groq(api_key=api_key)

            with st.chat_message("assistant"):
                with st.spinner("جاري قراءة الأرقام من شيت Dashboard..."):
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
            st.error(f"حدث خطأ أثناء قراءة الملف: {e}")
