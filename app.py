import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, date, timedelta
from streamlit_calendar import calendar

# --- КОНФИГУРАЦИЯ ---
st.set_page_config(page_title="WORK & CASH PRO", layout="wide", page_icon="📈")

# Стилизация (Dark Mode Friendly)
st.markdown("""
    <style>
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #3e4255; }
    .status-warning { color: #ff4b4b; font-weight: bold; }
    .status-ok { color: #00cc96; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- DB SETUP ---
conn = sqlite3.connect('finance_pro.sqlite', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY, date TEXT, type TEXT, income REAL, hours REAL)')
c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, note TEXT)')
conn.commit()

# --- SIDEBAR ---
st.sidebar.title("💎 WORK & CASH")
menu = st.sidebar.selectbox("Меню", ["Dashboard", "Календарь смен", "Ввод данных", "Цели 🎯", "История"])

# --- ЛОГИКА ---
df_s = pd.read_sql_query("SELECT * FROM shifts", conn)
df_e = pd.read_sql_query("SELECT * FROM expenses", conn)

if menu == "Dashboard":
    st.title("🚀 Твой финансовый статус")
    
    if not df_s.empty:
        # Метрики
        t_inc = df_s['income'].sum()
        t_exp = df_e['amount'].sum()
        balance = t_inc - t_exp
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Заработано всего", f"{t_inc:,.0} ₽")
        c2.metric("Потрачено", f"{t_exp:,.0} ₽", delta=f"-{t_exp:,.0}", delta_color="inverse")
        c3.metric("Чистый капитал", f"{balance:,.0} ₽")

        # --- УМНЫЕ УВЕДОМЛЕНИЯ ---
        st.markdown("---")
        st.subheader("🤖 Советы от ИИ")
        
        # Считаем средний расход в день за неделю
        last_week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent_exp = df_e[df_e['date'] >= last_week]['amount'].sum() / 7
        
        if recent_exp > (t_inc / 30): # Если тратим в день больше, чем 1/30 дохода
            st.error(f"⚠️ Внимание! Ваши средние траты ({recent_exp:.0f}₽/день) выше нормы. Цель может быть отложена.")
        else:
            st.success("✅ Отличный темп! Вы тратите меньше, чем зарабатываете.")

        # Графики
        col_left, col_right = st.columns(2)
        with col_left:
            fig1 = px.line(df_s, x='date', y='income', title="Динамика доходов", markers=True)
            st.plotly_chart(fig1, use_container_width=True)
        with col_right:
            fig2 = px.bar(df_e.groupby('category')['amount'].sum().reset_index(), 
                          x='category', y='amount', title="Траты по категориям", color='category')
            st.plotly_chart(fig2, use_container_width=True)

elif menu == "Календарь смен":
    st.title("📅 График работы")
    calendar_events = []
    for i, row in df_s.iterrows():
        calendar_events.append({
            "title": f"💰 {row['income']}₽",
            "start": row['date'],
            "end": row['date'],
            "backgroundColor": "#00cc96" if row['type'] == "Основная" else "#ffbb00"
        })
    
    calendar(events=calendar_events, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"}})

elif menu == "Ввод данных":
    tab1, tab2 = st.tabs(["Добавить Смену", "Добавить Расход"])
    with tab1:
        with st.form("s_form"):
            d = st.date_input("Дата")
            tp = st.selectbox("Тип", ["Основная", "Ночная", "Подработка"])
            inc = st.number_input("Доход", min_value=0)
            hr = st.number_input("Часы", 1, 24, 8)
            if st.form_submit_button("Сохранить"):
                c.execute("INSERT INTO shifts (date, type, income, hours) VALUES (?,?,?,?)", (d, tp, inc, hr))
                conn.commit()
                st.rerun()
    with tab2:
        with st.form("e_form"):
            d_e = st.date_input("Дата")
            cat = st.selectbox("Категория", ["Еда", "Транспорт", "Жилье", "Развлечения", "Шоппинг"])
            am = st.number_input("Сумма", min_value=0)
            if st.form_submit_button("Записать"):
                c.execute("INSERT INTO expenses (date, category, amount) VALUES (?,?,?)", (d_e, cat, am))
                conn.commit()
                st.rerun()

elif menu == "Цели 🎯":
    st.title("🎯 Твои мечты")
    target = st.text_input("Название цели", "Новый ноутбук")
    price = st.number_input("Стоимость", min_value=0, value=100000)
    
    current_savings = df_s['income'].sum() - df_e['amount'].sum()
    progress = min(1.0, max(0.0, current_savings / price))
    
    st.progress(progress)
    st.subheader(f"Выполнено на {progress*100:.1f}%")
    
    if progress < 1:
        avg_shift = df_s['income'].mean() if not df_s.empty else 1
        needed = (price - current_savings) / avg_shift
        st.info(f"Осталось накопить {price - current_savings:,.0f} ₽. Это примерно **{int(needed)+1}** рабочих смен.")

elif menu == "История":
    st.subheader("Последние записи")
    st.write("Смены")
    st.table(df_s.tail(10))
    st.write("Расходы")
    st.table(df_e.tail(10))
