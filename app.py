import streamlit as st
import pandas as pd
from groq import Groq
import warnings
warnings.filterwarnings('ignore')

# إعدادات واجهة التطبيق
st.set_page_config(page_title="مساعد مصنع لافيتو", page_icon="🧵", layout="centered")

# ضبط اتجاه الكتابة للغة العربية
st.markdown("""
    <style>
    .stApp { direction: rtl; }
    </style>
""", unsafe_allow_html=True)

st.title("🧵 مساعد مصنع لافيتو للمبيعات والمخزون")

# إعدادات المفتاح والموديل بالقائمة الجانبية
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

# رفع ملف الإكسيل
uploaded_file = st.file_uploader("ارفع ملف إكسيل المصنع (تقرير مبيعات المصنع مفصل)", type=["xlsx"])

# إدارة سجل المحادثة
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# استقبال السؤال
if prompt := st.chat_input("اسأل عن المخزون، مبيعات عميل، المرتجعات، أو كود موديل..."):
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
            
            # قراءة الشيتات الخاصة بالمصنع
            df_trans = pd.read_excel(xls, sheet_name='Transaction') if 'Transaction' in xls.sheet_names else pd.DataFrame()
            df_clients = pd.read_excel(xls, sheet_name='Clients') if 'Clients' in xls.sheet_names else pd.DataFrame()
            df_add = pd.read_excel(xls, sheet_name='ADD') if 'ADD' in xls.sheet_names else pd.DataFrame()
            df_returns = pd.read_excel(xls, sheet_name='Returns') if 'Returns' in xls.sheet_names else pd.DataFrame()

            # 1. حساب المخزون الدقيق بالمعادلة: (الإنتاج + المرتجعات) - المبيعات
            stock_summary = []
            if not df_add.empty and not df_trans.empty:
                df_add['quantity'] = pd.to_numeric(df_add['quantity'], errors='coerce').fillna(0)
                df_trans['quantity'] = pd.to_numeric(df_trans['quantity'], errors='coerce').fillna(0)
                
                # تجميع الإضافات (الإنتاج)
                add_grouped = df_add.groupby('product id')['quantity'].sum()
                # تجميع المبيعات
                trans_grouped = df_trans.groupby('product id')['quantity'].sum()
                
                # تجميع المرتجعات
                ret_grouped = pd.Series(dtype=float)
                if not df_returns.empty and 'product' in df_returns.columns and 'عدد القطع' in df_returns.columns:
                    df_returns['عدد القطع'] = pd.to_numeric(df_returns['عدد القطع'], errors='coerce').fillna(0)
                    ret_grouped = df_returns.groupby('product')['عدد القطع'].sum()

                # دمج كل الموديلات وحساب المخزون بالمعادلة الدقيقة
                all_pids = set(add_grouped.index).union(set(trans_grouped.index)).union(set(ret_grouped.index))
                for pid in all_pids:
                    try:
                        pid_int = int(pid)
                    except Exception:
                        continue
                    in_qty = add_grouped.get(pid, 0)
                    out_qty = trans_grouped.get(pid, 0)
                    ret_qty = ret_grouped.get(pid, 0)
                    
                    # المعادلة: الوارد (إنتاج + مرتجع) - المنصرف (مبيعات)
                    actual_stock = (in_qty + ret_qty) - out_qty
                    
                    stock_summary.append({
                        'كود الموديل': pid_int,
                        'الإنتاج (إضافة)': int(in_qty),
                        'المرتجع للمصنع': int(ret_qty),
                        'إجمالي الوارد': int(in_qty + ret_qty),
                        'المبيعات': int(out_qty),
                        'المخزون الفعلي الحالي': int(actual_stock)
                    })

            df_actual_stock = pd.DataFrame(stock_summary)

            # 2. تجهيز جدول العملاء وترتيبهم تنازلياً وفق صافي المبيعات
            clean_clients = pd.DataFrame()
            if not df_clients.empty and 'العميل' in df_clients.columns:
                clean_clients = df_clients[~df_clients['العميل'].astype(str).str.contains('الاجمالي|Unnamed', na=False)].copy()
                clean_clients['المبيعات'] = pd.to_numeric(clean_clients['المبيعات'], errors='coerce').fillna(0)
                clean_clients['المرتجعات'] = pd.to_numeric(clean_clients['المرتجعات'], errors='coerce').fillna(0)
                clean_clients['صافي المبيعات'] = pd.to_numeric(clean_clients['صافي المبيعات'], errors='coerce').fillna(0)
            
            top_clients_text = clean_clients.sort_values(by='صافي المبيعات', ascending=False)[['العميل', 'المبيعات', 'المرتجعات', 'صافي المبيعات']].head(20).to_string(index=False) if not clean_clients.empty else ""

            # 3. تجهيز بيانات المخزون المسبقة للأعلى رصيداً
            stock_preview = df_actual_stock.sort_values(by='المخزون الفعلي الحالي', ascending=False).to_string(index=False) if not df_actual_stock.empty else ""

            # تجهيز السياق الدقيق
            accurate_context = f"""
            المعادلة المعتمدة في حساب مخزون مصنع لافيتو:
            المخزون الفعلي الحالي = (الإنتاج + المرتجعات) - المبيعات.
            (المرتجعات بضاعة رجعت للمصنع وتضاف للرصيد، بينما المبيعات تخرج من الرصيد).

            جدول المخزون المحسوب بدقة لكل الموديلات:
            {stock_preview}

            جدول العملاء مرتبين تنازلياً حسب صافي المبيعات (المبيعات - المرتجعات):
            {top_clients_text}
            """

            client = Groq(api_key=api_key)

            system_instruction = f"""
            أنت مساعد ذكي لإدارة مصنع ملابس لافيتو (Laveto).
            مهمتك تقديم إجابات مباشرة ودقيقة باللغة العربية بناءً على البيانات المحسوبة مسبقاً.
            القاعدة الحسابية: المخزون الفعلي = (الإنتاج + المرتجعات) - المبيعات.
            لا تقم بتأليف أو تخمين أي أرقام من عندك، واعتمد كلياً على الجداول المرفقة أدناه:
            {accurate_context}
            """

            with st.chat_message("assistant"):
                with st.spinner("جاري تدقيق الحسابات والرد..."):
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
            st.error(f"حدث خطأ أثناء فحص البيانات: {e}")
