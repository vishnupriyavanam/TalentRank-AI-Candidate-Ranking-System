import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="TalentRank AI",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 TalentRank AI")
st.subheader("AI-Powered Candidate Ranking System")

st.write(
    "This application displays the Top 100 ranked candidates generated for the given job description."
)

# Load final submission
try:
    df = pd.read_csv("final_submission.csv")

    st.success("Final ranked candidate file loaded successfully!")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Ranked Candidates", len(df))

    with col2:
        st.metric("Top Rank", int(df["rank"].min()))

    with col3:
        st.metric("Highest Score", round(df["score"].max(), 4))

    st.markdown("### Top Ranked Candidates")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Final Submission CSV",
        data=csv,
        file_name="final_submission.csv",
        mime="text/csv"
    )

except FileNotFoundError:
    st.error("final_submission.csv not found. Please place it in the same folder as app.py.")

st.markdown("---")

st.markdown("### Ranking Approach")
st.write(
    """
    The system evaluates candidates using skills match, experience, domain relevance,
    and recruiter response signals. Candidates are scored and ranked to generate the
    Top 100 recommendations with reasoning.
    """
)

st.markdown("### Submission Assets")
st.write("""
- GitHub Repository
- Final Submission CSV
- Source Code
- Project Presentation
""")