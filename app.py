 try:
        # قراءة الإكسيل وتجهيز عينة للذكاء الاصطناعي
        df = pd.read_excel(uploaded_file)
        
        # استخراج ملخص للأعمدة وعينة أسطر
        columns_list = list(df.columns)
        total_records = len(df)
        data_sample = df.head(15).to_string(index=False)
        
        # صياغة التعليمات البرمجية للوكيل
        system_instruction = f"""
        أنت مساعد ذكي ومتخصص في تحليل البيانات لمصنع ملابس لافيتو (Laveto).
        مهمتك الإجابة بدقة، احترافية، وباللغة العربية على أسئلة الإدارة.
        
        معلومات الشيت:
        - إجمالي الحركات/الصفوف: {total_records}
        - الأعمدة المتوفرة: {columns_list}
        
        عينة من البيانات الفعلية:
        {data_sample}
        
        تعليمات هامة:
        - التزم بالبيانات والأرقام المذكورة بدقة دون افتراض أرقام غير موجودة.
        - إذا لم تكن المعلومة متوفرة في العينة، وضّح ذلك باختصار واذكر أسماء الأعمدة المتاحة للمساعدة.
        """

        # الاتصال بـ Groq API
        client = Groq(api_key=api_key)

        with st.chat_message("assistant"):
            with st.spinner("جاري فحص الشيت وتحليل البيانات..."):
                chat_completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    # استخدام موديل قوي وسريع معتمد رسمياً في Groq
                    model="llama-3.3-70b-versatile",
                )
                answer = chat_completion.choices[0].message.content
                st.markdown(answer)
                
                # حفظ الرد في سجل الشات
                st.session_state.messages.append({"role": "assistant", "content": answer})

    except Exception as e:
        st.error(f"حدث خطأ أثناء معالجة الطلب: {e}")
