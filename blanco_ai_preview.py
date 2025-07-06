import streamlit as st

# Sample today's games slate
games = {
    "Mets @ Yankees": {
        "pitchers": "Carlos Rodón vs Frankie Montas",
        "score": "Yankees 5 – Mets 4",
        "win_prob": "Yankees 60% vs Mets 40%",
        "total": "Under 9.5 Runs (70% Confidence)",
        "props": [
            "Aaron Judge Over 1.5 TB (80%)",
            "Brandon Nimmo Over 1.5 TB (82%)"
        ]
    },
    "Orioles @ Braves": {
        "pitchers": "Trevor Rogers vs Grant Holmes",
        "score": "Braves 6 – Orioles 4",
        "win_prob": "Braves 58% vs Orioles 42%",
        "total": "Over 9 Runs (65% Confidence)",
        "props": [
            "Ronald Acuña Jr. Over 0.5 Hits (78%)",
            "Tyler O'Neill Over 1.5 TB (82%)"
        ]
    }
}

st.set_page_config(page_title="Blanco AI Preview", layout="centered")
st.title("⚾ Blanco AI Live Preview")

choice = st.selectbox("Select Today's Game", list(games.keys()))
data = games[choice]

st.subheader(choice)
st.markdown(f"**Pitchers:** {data['pitchers']}")
st.markdown(f"**Score Prediction:** {data['score']}")
st.markdown(f"**Win Prob:** {data['win_prob']}")
st.markdown(f"**Total Pick:** {data['total']}")

st.header("Prop Bets (80%+)")
for prop in data["props"]:
    st.markdown(f"- {prop}")

st.markdown("---")
st.markdown("🚀 Powered by **Blanco AI™**")
