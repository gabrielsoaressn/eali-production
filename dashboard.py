import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="EALI - Dashboard de Produtividade",
    page_icon="📊",
    layout="wide"
)

# Database connection
@st.cache_resource
def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="metricsdb",
        user="metricsuser",
        password="metricspass"
    )

@st.cache_data(ttl=300)
def load_tasks():
    conn = get_connection()
    query = """
        SELECT
            task_id, title, assignee_name, project_name, status, done,
            archived, started_at, due_at, completed_at, created_at,
            updated_at, comment_count
        FROM blue_tasks
    """
    return pd.read_sql(query, conn)

# Title
st.title("📊 EALI - Dashboard de Produtividade")
st.markdown("---")

# Load data
try:
    df_tasks = load_tasks()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    st.stop()

# Convert dates
df_tasks['created_at'] = pd.to_datetime(df_tasks['created_at'])
df_tasks['completed_at'] = pd.to_datetime(df_tasks['completed_at'])

# Sidebar filters
st.sidebar.header("Filtros")

# Status filter
all_statuses = df_tasks['status'].dropna().unique().tolist()
selected_statuses = st.sidebar.multiselect(
    "Status",
    options=all_statuses,
    default=all_statuses
)

# Date filter
min_date = df_tasks['created_at'].min().date()
max_date = df_tasks['created_at'].max().date()
date_range = st.sidebar.date_input(
    "Período",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Apply filters
df_filtered = df_tasks.copy()
if selected_statuses:
    df_filtered = df_filtered[df_filtered['status'].isin(selected_statuses)]
if len(date_range) == 2:
    df_filtered = df_filtered[
        (df_filtered['created_at'].dt.date >= date_range[0]) &
        (df_filtered['created_at'].dt.date <= date_range[1])
    ]

# KPIs
st.header("Visão Geral")
col1, col2, col3, col4 = st.columns(4)

total_tasks = len(df_filtered)
completed_tasks = df_filtered['done'].sum()
pending_tasks = len(df_filtered[df_filtered['done'] == False])
archived_tasks = df_filtered['archived'].sum()

with col1:
    st.metric("Total de Tarefas", total_tasks)
with col2:
    st.metric("Concluídas", int(completed_tasks))
with col3:
    st.metric("Pendentes", pending_tasks)
with col4:
    st.metric("Arquivadas", int(archived_tasks))

st.markdown("---")

# Charts row 1
col1, col2 = st.columns(2)

with col1:
    st.subheader("Distribuição por Status")
    status_counts = df_filtered['status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Quantidade']
    if not status_counts.empty:
        fig_status = px.pie(
            status_counts,
            values='Quantidade',
            names='Status',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status.update_layout(height=350)
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("Sem dados de status disponíveis")

with col2:
    st.subheader("Tarefas Criadas por Mês")
    df_filtered['month'] = df_filtered['created_at'].dt.to_period('M').astype(str)
    monthly_tasks = df_filtered.groupby('month').size().reset_index(name='Quantidade')
    if not monthly_tasks.empty:
        fig_monthly = px.bar(
            monthly_tasks,
            x='month',
            y='Quantidade',
            labels={'month': 'Mês', 'Quantidade': 'Tarefas'},
            color_discrete_sequence=['#3498db']
        )
        fig_monthly.update_layout(height=350)
        st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.info("Sem dados mensais disponíveis")

# Completion rate
if total_tasks > 0:
    completion_rate = (completed_tasks / total_tasks) * 100
    st.subheader("Taxa de Conclusão")
    st.progress(completion_rate / 100)
    st.write(f"**{completion_rate:.1f}%** das tarefas foram concluídas")

st.markdown("---")

# Charts row 2
col1, col2 = st.columns(2)

with col1:
    st.subheader("Tarefas Concluídas por Mês")
    df_completed = df_filtered[df_filtered['done'] == True].copy()
    if not df_completed.empty and df_completed['completed_at'].notna().any():
        df_completed['completed_month'] = df_completed['completed_at'].dt.to_period('M').astype(str)
        completed_monthly = df_completed.groupby('completed_month').size().reset_index(name='Quantidade')
        fig_completed = px.bar(
            completed_monthly,
            x='completed_month',
            y='Quantidade',
            labels={'completed_month': 'Mês', 'Quantidade': 'Concluídas'},
            color_discrete_sequence=['#2ecc71']
        )
        fig_completed.update_layout(height=350)
        st.plotly_chart(fig_completed, use_container_width=True)
    else:
        st.info("Sem dados de conclusão disponíveis")

with col2:
    st.subheader("Tarefas por Dia da Semana")
    df_filtered['weekday'] = df_filtered['created_at'].dt.day_name()
    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_pt = {
        'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
        'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df_filtered['weekday_pt'] = df_filtered['weekday'].map(weekday_pt)
    weekday_counts = df_filtered['weekday'].value_counts().reindex(weekday_order).reset_index()
    weekday_counts.columns = ['Dia', 'Quantidade']
    weekday_counts['Dia'] = weekday_counts['Dia'].map(weekday_pt)
    if not weekday_counts.empty:
        fig_weekday = px.bar(
            weekday_counts,
            x='Dia',
            y='Quantidade',
            color_discrete_sequence=['#9b59b6']
        )
        fig_weekday.update_layout(height=350)
        st.plotly_chart(fig_weekday, use_container_width=True)
    else:
        st.info("Sem dados disponíveis")

st.markdown("---")

# Recent tasks table
st.subheader("Tarefas Recentes")
recent_tasks = df_filtered[['title', 'status', 'done', 'created_at']].sort_values('created_at', ascending=False).head(15)
recent_tasks.columns = ['Título', 'Status', 'Concluída', 'Criada em']
recent_tasks['Concluída'] = recent_tasks['Concluída'].map({True: 'Sim', False: 'Não'})
st.dataframe(recent_tasks, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>EALI - Dashboard de Produtividade | Atualizado automaticamente a cada 5 minutos</p>
    </div>
    """,
    unsafe_allow_html=True
)
