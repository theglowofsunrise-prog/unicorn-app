import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

# ---------------- SETTINGS (edit these) ----------------
STUDENT_NAME = "Andal"
DAILY_GOAL_MINUTES = 30
TIMEZONE = "Australia/Brisbane"

# Each task: what Andal has to do, how many minutes it earns,
# and whether it MUST be done before any screen time unlocks.
TASKS = [
    {"name": "Finish homework", "minutes": 10, "required": True},
    {"name": "Read a book for 20 minutes", "minutes": 10, "required": False},
    {"name": "Tidy my room", "minutes": 5, "required": False},
    {"name": "30 minutes of outdoor play or exercise", "minutes": 5, "required": False},
]
# -------------------------------------------------------

st.set_page_config(page_title=f"{STUDENT_NAME}'s Screen Time", page_icon="⭐", layout="centered")

now = datetime.now(ZoneInfo(TIMEZONE))
today = now.date().isoformat()

# Start fresh each new day
if st.session_state.get("day") != today:
    st.session_state.day = today
    st.session_state.celebrated = False
    for i in range(len(TASKS)):
        st.session_state[f"task_{i}"] = False


def reset_tasks():
    st.session_state.celebrated = False
    for i in range(len(TASKS)):
        st.session_state[f"task_{i}"] = False


st.title(f"⭐ Hi {STUDENT_NAME}!")
st.caption(now.strftime("%A, %d %B %Y"))
st.write(
    f"Complete your tasks to earn up to **{DAILY_GOAL_MINUTES} minutes** "
    "of screen time today."
)

st.subheader("Today's tasks")
for i, task in enumerate(TASKS):
    label = f"{task['name']}  (+{task['minutes']} min)"
    if task["required"]:
        label += "  · **must do**"
    st.checkbox(label, key=f"task_{i}")

done = [st.session_state[f"task_{i}"] for i in range(len(TASKS))]
required_done = all(d for d, t in zip(done, TASKS) if t["required"])
earned = min(sum(t["minutes"] for d, t in zip(done, TASKS) if d), DAILY_GOAL_MINUTES)
unlocked = earned if required_done else 0

st.divider()

col1, col2 = st.columns(2)
col1.metric("Screen time earned", f"{unlocked} min")
col2.metric("Still to earn", f"{DAILY_GOAL_MINUTES - unlocked} min")
st.progress(unlocked / DAILY_GOAL_MINUTES)

if not required_done:
    st.warning("Finish your **must do** tasks first to unlock screen time. 🔒")
elif unlocked >= DAILY_GOAL_MINUTES:
    st.success(f"Amazing work, {STUDENT_NAME}! You've earned all {DAILY_GOAL_MINUTES} minutes! 🎉")
    if not st.session_state.celebrated:
        st.balloons()
        st.session_state.celebrated = True
elif unlocked > 0:
    st.info(f"Great going! You have {unlocked} minutes so far. Keep it up! 💪")

st.button("Start over", on_click=reset_tasks)
