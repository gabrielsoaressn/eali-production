import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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

@st.cache_data(ttl=300)
def load_deployments():
    conn = get_connection()
    query = """
        SELECT
            project_key, commit_sha, commit_timestamp, deployment_timestamp,
            environment, status, branch, lead_time_minutes
        FROM dora_deployments
        ORDER BY deployment_timestamp DESC
    """
    return pd.read_sql(query, conn)

@st.cache_data(ttl=300)
def load_sonarcloud():
    conn = get_connection()
    query = """
        SELECT
            project_key, timestamp, bugs, reliability_rating, vulnerabilities,
            security_rating, code_smells, technical_debt, debt_ratio,
            maintainability_rating, coverage_overall, coverage_new,
            duplication_density, lines_of_code, complexity, overall_rating,
            technical_debt_minutes
        FROM sonarcloud_metrics
        ORDER BY timestamp DESC
    """
    return pd.read_sql(query, conn)

# Title
st.title("📊 EALI - Dashboard de Produtividade")
st.markdown("---")

# Load data
try:
    df_tasks = load_tasks()
    df_deployments = load_deployments()
    df_sonarcloud = load_sonarcloud()
except Exception as e:
    st.error(f"Erro ao conectar ao banco de dados: {e}")
    st.stop()

# Sidebar filters
st.sidebar.header("Filtros")

# Project filter for SonarCloud
projects = df_sonarcloud['project_key'].unique().tolist()
selected_project = st.sidebar.selectbox(
    "Projeto (SonarCloud)",
    options=["Todos"] + projects
)

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Tarefas", "🚀 Deployments (DORA)", "🔍 Qualidade de Código"])

# Tab 1: Tasks
with tab1:
    st.header("Métricas de Tarefas")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)

    total_tasks = len(df_tasks)
    completed_tasks = df_tasks['done'].sum()
    pending_tasks = len(df_tasks[df_tasks['done'] == False])
    archived_tasks = df_tasks['archived'].sum()

    with col1:
        st.metric("Total de Tarefas", total_tasks)
    with col2:
        st.metric("Concluídas", int(completed_tasks))
    with col3:
        st.metric("Pendentes", pending_tasks)
    with col4:
        st.metric("Arquivadas", int(archived_tasks))

    st.markdown("---")

    # Task status distribution
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Distribuição por Status")
        status_counts = df_tasks['status'].value_counts().reset_index()
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
        df_tasks['created_at'] = pd.to_datetime(df_tasks['created_at'])
        df_tasks['month'] = df_tasks['created_at'].dt.to_period('M').astype(str)
        monthly_tasks = df_tasks.groupby('month').size().reset_index(name='Quantidade')
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

# Tab 2: DORA Metrics
with tab2:
    st.header("Métricas DORA - Deployments")

    if len(df_deployments) > 0:
        # KPIs
        col1, col2, col3, col4 = st.columns(4)

        total_deployments = len(df_deployments)
        successful_deployments = len(df_deployments[df_deployments['status'] == 'success'])
        avg_lead_time = df_deployments['lead_time_minutes'].mean()
        success_rate = (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0

        with col1:
            st.metric("Total Deployments", total_deployments)
        with col2:
            st.metric("Deployments com Sucesso", successful_deployments)
        with col3:
            st.metric("Lead Time Médio", f"{avg_lead_time:.1f} min")
        with col4:
            st.metric("Taxa de Sucesso", f"{success_rate:.1f}%")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Lead Time por Deployment")
            df_deployments['deployment_timestamp'] = pd.to_datetime(df_deployments['deployment_timestamp'])
            fig_lead = px.line(
                df_deployments.sort_values('deployment_timestamp'),
                x='deployment_timestamp',
                y='lead_time_minutes',
                markers=True,
                labels={'deployment_timestamp': 'Data', 'lead_time_minutes': 'Lead Time (min)'},
                color_discrete_sequence=['#2ecc71']
            )
            fig_lead.update_layout(height=350)
            st.plotly_chart(fig_lead, use_container_width=True)

        with col2:
            st.subheader("Status dos Deployments")
            status_deploy = df_deployments['status'].value_counts().reset_index()
            status_deploy.columns = ['Status', 'Quantidade']
            fig_deploy_status = px.pie(
                status_deploy,
                values='Quantidade',
                names='Status',
                color_discrete_sequence=['#2ecc71', '#e74c3c']
            )
            fig_deploy_status.update_layout(height=350)
            st.plotly_chart(fig_deploy_status, use_container_width=True)

        # Recent deployments table
        st.subheader("Deployments Recentes")
        recent_deployments = df_deployments[['project_key', 'deployment_timestamp', 'status', 'branch', 'lead_time_minutes']].head(10)
        recent_deployments.columns = ['Projeto', 'Data', 'Status', 'Branch', 'Lead Time (min)']
        st.dataframe(recent_deployments, use_container_width=True)
    else:
        st.info("Nenhum deployment registrado")

# Tab 3: Code Quality
with tab3:
    st.header("Métricas de Qualidade - SonarCloud")

    # Filter by project
    if selected_project != "Todos":
        df_filtered = df_sonarcloud[df_sonarcloud['project_key'] == selected_project]
    else:
        df_filtered = df_sonarcloud

    if len(df_filtered) > 0:
        # Get latest metrics per project
        df_latest = df_filtered.sort_values('timestamp').groupby('project_key').last().reset_index()

        # KPIs
        col1, col2, col3, col4 = st.columns(4)

        total_bugs = df_latest['bugs'].sum()
        total_vulnerabilities = df_latest['vulnerabilities'].sum()
        total_code_smells = df_latest['code_smells'].sum()
        avg_coverage = df_latest['coverage_overall'].mean()

        with col1:
            st.metric("Bugs", int(total_bugs))
        with col2:
            st.metric("Vulnerabilidades", int(total_vulnerabilities))
        with col3:
            st.metric("Code Smells", int(total_code_smells))
        with col4:
            st.metric("Cobertura Média", f"{avg_coverage:.1f}%")

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Rating por Projeto")
            rating_order = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
            df_latest['rating_value'] = df_latest['overall_rating'].map(rating_order)
            fig_rating = px.bar(
                df_latest,
                x='project_key',
                y='rating_value',
                color='overall_rating',
                labels={'project_key': 'Projeto', 'rating_value': 'Rating', 'overall_rating': 'Rating'},
                color_discrete_map={'A': '#2ecc71', 'B': '#27ae60', 'C': '#f1c40f', 'D': '#e67e22', 'E': '#e74c3c'}
            )
            fig_rating.update_layout(height=350, yaxis_tickvals=[1,2,3,4,5], yaxis_ticktext=['E','D','C','B','A'])
            st.plotly_chart(fig_rating, use_container_width=True)

        with col2:
            st.subheader("Cobertura de Código por Projeto")
            fig_coverage = px.bar(
                df_latest,
                x='project_key',
                y='coverage_overall',
                labels={'project_key': 'Projeto', 'coverage_overall': 'Cobertura (%)'},
                color_discrete_sequence=['#3498db']
            )
            fig_coverage.update_layout(height=350)
            st.plotly_chart(fig_coverage, use_container_width=True)

        # Technical debt
        st.subheader("Dívida Técnica")
        col1, col2 = st.columns(2)

        with col1:
            fig_debt = px.bar(
                df_latest,
                x='project_key',
                y='technical_debt_minutes',
                labels={'project_key': 'Projeto', 'technical_debt_minutes': 'Dívida Técnica (min)'},
                color_discrete_sequence=['#e74c3c']
            )
            fig_debt.update_layout(height=300)
            st.plotly_chart(fig_debt, use_container_width=True)

        with col2:
            # Convert to hours/days for better readability
            df_latest['debt_hours'] = df_latest['technical_debt_minutes'] / 60
            st.markdown("### Resumo da Dívida Técnica")
            for _, row in df_latest.iterrows():
                hours = row['debt_hours']
                if hours >= 24:
                    debt_str = f"{hours/24:.1f} dias"
                else:
                    debt_str = f"{hours:.1f} horas"
                st.write(f"**{row['project_key']}**: {debt_str}")

        # Code quality evolution
        st.subheader("Evolução da Qualidade do Código")
        df_filtered['timestamp'] = pd.to_datetime(df_filtered['timestamp'])
        fig_evolution = px.line(
            df_filtered.sort_values('timestamp'),
            x='timestamp',
            y='bugs',
            color='project_key',
            markers=True,
            labels={'timestamp': 'Data', 'bugs': 'Bugs', 'project_key': 'Projeto'}
        )
        fig_evolution.update_layout(height=400)
        st.plotly_chart(fig_evolution, use_container_width=True)

        # Lines of code
        st.subheader("Linhas de Código por Projeto")
        fig_loc = px.bar(
            df_latest,
            x='project_key',
            y='lines_of_code',
            labels={'project_key': 'Projeto', 'lines_of_code': 'Linhas de Código'},
            color_discrete_sequence=['#9b59b6']
        )
        fig_loc.update_layout(height=300)
        st.plotly_chart(fig_loc, use_container_width=True)
    else:
        st.info("Nenhuma métrica de qualidade disponível")

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
