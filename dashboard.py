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
    try:
        # Try to get credentials from Streamlit secrets
        return psycopg2.connect(
            host=st.secrets["connections"]["postgresql"]["host"],
            database=st.secrets["connections"]["postgresql"]["database"],
            user=st.secrets["connections"]["postgresql"]["user"],
            password=st.secrets["connections"]["postgresql"]["password"],
            port=st.secrets["connections"]["postgresql"].get("port", 5432)
        )
    except Exception as e:
        # Fallback for local development (if .streamlit/secrets.toml exists locally)
        st.error(f"Erro ao conectar: {e}")
        st.info("Configure os secrets no Streamlit Cloud: Settings → Secrets")
        raise

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

    # DEBUG: Mostrar estatísticas dos dados
    st.sidebar.markdown("---")
    st.sidebar.subheader("Debug Info")
    st.sidebar.write(f"Total de tarefas: {len(df_tasks)}")
    st.sidebar.write(f"Tarefas com assignee: {df_tasks['assignee_name'].notna().sum()}")
    st.sidebar.write(f"Assignees únicos: {df_tasks['assignee_name'].nunique()}")

    # Mostrar alguns assignee_names
    if df_tasks['assignee_name'].notna().any():
        st.sidebar.write("Funcionários encontrados:")
        st.sidebar.write(df_tasks['assignee_name'].value_counts().head(5))

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

# Employee analytics section
st.header("📈 Análise por Funcionário")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Tarefas por Funcionário")
    # Filter out null assignees
    df_with_assignee = df_filtered[df_filtered['assignee_name'].notna()]
    if not df_with_assignee.empty:
        employee_counts = df_with_assignee['assignee_name'].value_counts().reset_index()
        employee_counts.columns = ['Funcionário', 'Total de Tarefas']
        fig_employee = px.bar(
            employee_counts.head(10),
            x='Funcionário',
            y='Total de Tarefas',
            color='Total de Tarefas',
            color_continuous_scale='Blues',
            text='Total de Tarefas'
        )
        fig_employee.update_traces(textposition='outside')
        fig_employee.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_employee, use_container_width=True)
    else:
        st.info("Sem dados de funcionários disponíveis")

with col2:
    st.subheader("Taxa de Conclusão por Funcionário")
    if not df_with_assignee.empty:
        employee_completion = df_with_assignee.groupby('assignee_name').agg({
            'done': ['sum', 'count']
        }).reset_index()
        employee_completion.columns = ['Funcionário', 'Concluídas', 'Total']
        employee_completion['Taxa (%)'] = (employee_completion['Concluídas'] / employee_completion['Total'] * 100).round(1)
        employee_completion = employee_completion.sort_values('Taxa (%)', ascending=True).head(10)

        fig_completion = px.bar(
            employee_completion,
            y='Funcionário',
            x='Taxa (%)',
            orientation='h',
            color='Taxa (%)',
            color_continuous_scale='Greens',
            text='Taxa (%)'
        )
        fig_completion.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig_completion.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_completion, use_container_width=True)
    else:
        st.info("Sem dados de conclusão disponíveis")

st.markdown("---")

# Employee status breakdown
st.subheader("Status das Tarefas por Funcionário")
if not df_with_assignee.empty:
    employee_status = df_with_assignee.groupby(['assignee_name', 'status']).size().reset_index(name='Quantidade')

    # Get top 10 employees by total tasks
    top_employees = df_with_assignee['assignee_name'].value_counts().head(10).index.tolist()
    employee_status_filtered = employee_status[employee_status['assignee_name'].isin(top_employees)]

    if not employee_status_filtered.empty:
        fig_status_employee = px.bar(
            employee_status_filtered,
            x='assignee_name',
            y='Quantidade',
            color='status',
            title='Distribuição de Status (Top 10 Funcionários)',
            labels={'assignee_name': 'Funcionário', 'Quantidade': 'Número de Tarefas'},
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_status_employee.update_layout(height=400)
        st.plotly_chart(fig_status_employee, use_container_width=True)
    else:
        st.info("Sem dados de status por funcionário disponíveis")
else:
    st.info("Sem dados de funcionários disponíveis")

st.markdown("---")

# Ranking table
st.subheader("🏆 Ranking de Produtividade")
if not df_with_assignee.empty:
    ranking = df_with_assignee.groupby('assignee_name').agg({
        'task_id': 'count',
        'done': 'sum'
    }).reset_index()
    ranking.columns = ['Funcionário', 'Total de Tarefas', 'Tarefas Concluídas']
    ranking['Pendentes'] = ranking['Total de Tarefas'] - ranking['Tarefas Concluídas']
    ranking['Taxa de Conclusão (%)'] = (ranking['Tarefas Concluídas'] / ranking['Total de Tarefas'] * 100).round(1)
    ranking = ranking.sort_values('Tarefas Concluídas', ascending=False)

    # Add ranking position
    ranking.insert(0, 'Posição', range(1, len(ranking) + 1))

    st.dataframe(
        ranking,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Sem dados de funcionários disponíveis")

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
