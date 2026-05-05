# analytics_enhanced.py - FINAL FIX
import os
import json
import pandas as pd
import streamlit as st
from datetime import datetime
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go

# --- Page config ---
st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")
st.title("📊 AI ChatOps Assistant - Analytics Dashboard")
st.caption("Comprehensive monitoring of user queries, bot performance, and knowledge gaps")

# --- Log file names ---
LOG_JSONL = "chat_log.jsonl"
LOG_CSV = "chat_log.csv"
UNKNOWN_RESPONSE_PHRASE = "I do not have that information in the knowledge base"


def parse_iso(dt_str):
    """Parse ISO timestamp strings robustly"""
    if pd.isna(dt_str) or dt_str is None or dt_str == "":
        return pd.NaT
    
    if isinstance(dt_str, (pd.Timestamp, datetime)):
        return pd.to_datetime(dt_str)
    
    dt_str = str(dt_str).strip()
    
    try:
        return pd.to_datetime(dt_str, format='ISO8601', errors='coerce')
    except:
        try:
            return pd.to_datetime(dt_str, errors='coerce')
        except:
            return pd.NaT


def load_data():
    """Load chat log data from JSONL or CSV"""
    
    # Try JSONL first
    if os.path.exists(LOG_JSONL):
        rows = []
        try:
            with open(LOG_JSONL, "r", encoding="utf8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        rows.append(obj)
                    except:
                        continue
            
            if rows:
                df = pd.DataFrame(rows)
                if "timestamp" in df.columns:
                    df["timestamp"] = df["timestamp"].apply(parse_iso)
                return df
                
        except Exception as e:
            st.error(f"Error loading JSONL: {e}")
    
    # Fallback to CSV
    if os.path.exists(LOG_CSV):
        try:
            df = pd.read_csv(LOG_CSV, quotechar='"', skipinitialspace=True)
            if "timestamp" in df.columns:
                df["timestamp"] = df["timestamp"].apply(parse_iso)
            return df
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
    
    return pd.DataFrame(columns=["timestamp", "user", "query", "response", "feedback"])


# --- Main App ---
data = load_data()

if data is None or data.empty:
    st.warning("📭 No chat data found. Start asking questions in the chat app!")
    st.stop()

st.success(f"📈 Analyzing {len(data)} logged interactions")

# --- Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", 
    "🔍 Knowledge Gaps", 
    "👥 User Activity", 
    "📈 Query Patterns",
    "📋 Raw Data"
])

# --- TAB 1: Overview ---
with tab1:
    st.header("📊 Key Metrics Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_queries = len(data)
    unique_queries = data["query"].nunique() if "query" in data.columns else 0
    unique_users = data["user"].nunique() if "user" in data.columns else 0
    
    # Calculate success rate
    if "response" in data.columns:
        unknown_count = data[data["response"].str.contains(UNKNOWN_RESPONSE_PHRASE, case=False, na=False)].shape[0]
        success_rate = ((total_queries - unknown_count) / total_queries * 100) if total_queries > 0 else 0
    else:
        success_rate = 0
        unknown_count = 0
    
    col1.metric("Total Queries", total_queries)
    col2.metric("Unique Queries", unique_queries)
    col3.metric("Active Users", unique_users)
    col4.metric("Success Rate", f"{success_rate:.1f}%")
    
    # --- FIXED: Timeline Chart with Hourly Granularity ---
    st.subheader("📅 Query Timeline")
    
    if "timestamp" in data.columns:
        timeline_data = data[data["timestamp"].notna()].copy()
        
        if len(timeline_data) > 0:
            # Check if all data is from same day
            timeline_data["date"] = timeline_data["timestamp"].dt.date
            unique_dates = timeline_data["date"].nunique()
            
            if unique_dates == 1:
                # All queries on same day - use HOURLY view
                st.info(f"📅 All queries from: {timeline_data['date'].iloc[0]}")
                
                timeline_data["hour"] = timeline_data["timestamp"].dt.floor('H')
                hourly_counts = timeline_data.groupby("hour").size().reset_index(name="queries")
                hourly_counts = hourly_counts.sort_values("hour")
                
                # Format hour for display
                hourly_counts["hour_label"] = hourly_counts["hour"].dt.strftime("%H:%M")
                
                fig = px.bar(
                    hourly_counts,
                    x="hour_label",
                    y="queries",
                    title="Hourly Query Volume (Today)",
                    labels={"hour_label": "Hour", "queries": "Number of Queries"}
                )
                
                fig.update_traces(marker_color='#3498db')
                fig.update_layout(
                    xaxis_title="Hour of Day",
                    yaxis_title="Number of Queries",
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📊 Showing {len(timeline_data)} queries across {len(hourly_counts)} hour(s)")
                
            else:
                # Multiple days - use DAILY view
                daily_counts = timeline_data.groupby("date").size().reset_index(name="queries")
                daily_counts = daily_counts.sort_values("date")
                
                fig = px.line(
                    daily_counts,
                    x="date",
                    y="queries",
                    title="Daily Query Volume",
                    markers=True
                )
                
                fig.update_traces(
                    line_color='#1f77b4',
                    line_width=2,
                    marker=dict(size=8)
                )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Number of Queries",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                st.caption(f"📊 Data range: {daily_counts['date'].min()} to {daily_counts['date'].max()}")
        else:
            st.warning("⚠️ No valid timestamps available")
    else:
        st.info("ℹ️ No timestamp data found")
    
    # --- User Distribution ---
    st.subheader("👥 Queries by User")
    if "user" in data.columns:
        user_counts = data["user"].value_counts().head(10)
        
        fig = px.bar(
            x=user_counts.index,
            y=user_counts.values,
            title="Top 10 Most Active Users",
            labels={"x": "User", "y": "Number of Queries"}
        )
        fig.update_traces(marker_color='#2ecc71')
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: Knowledge Gaps ---
with tab2:
    st.header("🔍 Knowledge Gap Analysis")
    
    if "response" in data.columns:
        unknown_df = data[data["response"].str.contains(UNKNOWN_RESPONSE_PHRASE, case=False, na=False)]
    else:
        unknown_df = pd.DataFrame()
    
    col1, col2 = st.columns(2)
    col1.metric("Unanswered Queries", len(unknown_df))
    col2.metric("Gap Rate", f"{(len(unknown_df)/len(data)*100):.1f}%")
    
    if unknown_df.empty:
        st.success("🎉 Excellent! The bot successfully answered all queries!")
    else:
        st.warning(f"⚠️ Found {len(unknown_df)} queries the bot couldn't answer")
        
        # Show top unanswered queries
        st.subheader("🔝 Top Unanswered Questions")
        if "query" in unknown_df.columns:
            top_unknown = unknown_df["query"].value_counts().head(10)
            
            fig = px.bar(
                x=top_unknown.values,
                y=top_unknown.index,
                orientation='h',
                title="Most Frequent Unanswered Queries",
                labels={"x": "Occurrences", "y": "Query"}
            )
            fig.update_traces(marker_color='#e74c3c')
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.subheader("📋 Detailed Unanswered Queries")
        display_cols = ["timestamp", "user", "query"]
        available_cols = [col for col in display_cols if col in unknown_df.columns]
        
        if "timestamp" in available_cols and unknown_df["timestamp"].notna().any():
            display_df = unknown_df[available_cols].sort_values(by="timestamp", ascending=False)
        else:
            display_df = unknown_df[available_cols]
        
        st.dataframe(display_df, use_container_width=True)

# --- TAB 3: User Activity ---
with tab3:
    st.header("👥 User Activity Analysis")
    
    if "user" in data.columns:
        # User engagement heatmap
        st.subheader("🔥 User Engagement Heatmap")
        
        if "timestamp" in data.columns:
            heatmap_data = data[data["timestamp"].notna()].copy()
            
            if len(heatmap_data) > 0:
                heatmap_data["hour"] = heatmap_data["timestamp"].dt.hour
                heatmap_data["day"] = heatmap_data["timestamp"].dt.day_name()
                
                pivot = heatmap_data.groupby(["day", "hour"]).size().reset_index(name="queries")
                pivot_table = pivot.pivot(index="day", columns="hour", values="queries").fillna(0)
                
                if not pivot_table.empty:
                    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                    pivot_table = pivot_table.reindex([d for d in day_order if d in pivot_table.index])
                    
                    fig = px.imshow(
                        pivot_table,
                        labels=dict(x="Hour of Day", y="Day of Week", color="Queries"),
                        title="Query Activity Heatmap",
                        aspect="auto",
                        color_continuous_scale="Blues"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Not enough data for heatmap")
            else:
                st.warning("⚠️ No valid timestamps")
        else:
            st.info("No timestamp data available")
        
        # User role distribution
        st.subheader("🎭 Queries by User Role")
        user_query_counts = data["user"].value_counts()
        
        fig = px.pie(
            values=user_query_counts.values, 
            names=user_query_counts.index,
            title="Query Distribution by User"
        )
        st.plotly_chart(fig, use_container_width=True)

# --- TAB 4: Query Patterns ---
with tab4:
    st.header("📈 Query Pattern Analysis")
    
    if "query" in data.columns and not data["query"].empty:
        st.subheader("🔝 Top Query Patterns")
        top_queries = data["query"].value_counts().head(15)
        
        fig = px.bar(
            x=top_queries.values,
            y=top_queries.index,
            orientation='h',
            title="Top 15 Most Common Queries",
            labels={"x": "Count", "y": "Query"}
        )
        fig.update_traces(marker_color='#3498db')
        st.plotly_chart(fig, use_container_width=True)
        
        # Query length analysis
        st.subheader("📏 Query Length Distribution")
        query_lengths = data["query"].str.len()
        
        fig = px.histogram(
            query_lengths, 
            nbins=30,
            title="Distribution of Query Lengths",
            labels={"value": "Query Length (characters)", "count": "Frequency"}
        )
        fig.update_traces(marker_color='#9b59b6')
        st.plotly_chart(fig, use_container_width=True)
        
        # Word cloud data
        st.subheader("☁️ Most Common Query Keywords")
        all_words = " ".join(data["query"].str.lower()).split()
        
        stop_words = {"what", "is", "the", "a", "an", "how", "do", "i", "to", "of", "in", "on", "for", "my", "you", "can", "get"}
        filtered_words = [word for word in all_words if word not in stop_words and len(word) > 3]
        word_counts = Counter(filtered_words).most_common(20)
        
        if word_counts:
            words_df = pd.DataFrame(word_counts, columns=["word", "count"])
            fig = px.bar(
                words_df, 
                x="word", 
                y="count",
                title="Top 20 Keywords in Queries",
                labels={"word": "Keyword", "count": "Frequency"}
            )
            fig.update_traces(marker_color='#f39c12')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data to analyze keywords")
    else:
        st.info("No queries to analyze.")

# --- TAB 5: Raw Data ---
with tab5:
    st.header("📋 Raw Chat Log Data")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        if "user" in data.columns:
            users = ["All"] + sorted(list(data["user"].unique()))
            selected_user = st.selectbox("Filter by User", users)
        else:
            selected_user = "All"
    
    with col2:
        if "response" in data.columns:
            response_types = ["All", "Successful", "Unanswered"]
            selected_type = st.selectbox("Filter by Response Type", response_types)
        else:
            selected_type = "All"
    
    # Apply filters
    filtered_data = data.copy()
    
    if selected_user != "All":
        filtered_data = filtered_data[filtered_data["user"] == selected_user]
    
    if "response" in data.columns:
        if selected_type == "Successful":
            filtered_data = filtered_data[~filtered_data["response"].str.contains(UNKNOWN_RESPONSE_PHRASE, case=False, na=False)]
        elif selected_type == "Unanswered":
            filtered_data = filtered_data[filtered_data["response"].str.contains(UNKNOWN_RESPONSE_PHRASE, case=False, na=False)]
    
    st.info(f"Showing {len(filtered_data)} of {len(data)} interactions")
    
    # Display data
    if "timestamp" in filtered_data.columns and filtered_data["timestamp"].notna().any():
        st.dataframe(
            filtered_data.sort_values(by="timestamp", ascending=False),
            use_container_width=True,
            height=600
        )
    else:
        st.dataframe(filtered_data, use_container_width=True, height=600)
    
    # Download button
    csv = filtered_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name=f"chat_log_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

# --- Footer ---
st.markdown("---")
st.caption("💡 **Tip**: Use this dashboard to identify knowledge gaps and improve your knowledge base content!")
st.caption("🔄 **Refresh**: Reload this page to see updated analytics after new queries")