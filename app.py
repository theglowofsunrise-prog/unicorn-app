import base64
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# ============================ SETTINGS (edit these) ============================
STUDENT_NAME = "Andal"
LANGUAGE = "your language"     # e.g. replace with the name of the language
DAILY_GOAL_MINUTES = 30        # most screen time she can earn in one day
TIMEZONE = "Australia/Brisbane"
MATHS_LEVEL = "medium"         # "easy", "medium" or "hard"

# id: short code (don't change once she has progress)  minutes: screen time it earns
# required: True = must be done before ANY screen time unlocks that day
TASKS = [
    {"id": "speak", "emoji": "🗣️", "name": f"Speak {LANGUAGE} for 10 minutes", "minutes": 10, "required": True},
    {"id": "write1", "emoji": "✏️", "name": "English writing – piece 1", "minutes": 5},
    {"id": "write2", "emoji": "📝", "name": "English writing – piece 2", "minutes": 5},
    {"id": "maths", "emoji": "🔢", "name": "Solve a maths problem", "minutes": 5},
    {"id": "read", "emoji": "📚", "name": "Read a book for 20 minutes", "minutes": 5},
    {"id": "exercise", "emoji": "🤸", "name": "Exercise or active play for 20 minutes", "minutes": 5},
    {"id": "meditate", "emoji": "🧘", "name": "Quiet meditation for 5 minutes", "minutes": 5},
]

# Big rewards. streak_len = days IN A ROW of speaking needed.
# needs = how many days each task must be done inside the window.
REWARDS = [
    {
        "id": "burrito", "emoji": "🌯", "name": "Burrito treat",
        "window": 7, "streak_len": 7,
        "needs": {"exercise": 4, "meditate": 4, "read": 4},
        "how": f"Speak {LANGUAGE} 7 days in a row, and in that week exercise, meditate and read on at least 4 days each.",
    },
    {
        "id": "movie", "emoji": "🎬", "name": "Movie at the cinema",
        "window": 30, "streak_len": 21,
        "needs": {"exercise": 20, "read": 20},
        "how": f"Speak {LANGUAGE} 21 days in a row (3 weeks, no breaks!), and in the month exercise and read on at least 20 days each.",
    },
]
STAR_DAYS_PER_DOLLAR = 14   # a "star day" = she earned the full daily screen time

SPEAKING_IDEAS = [
    "Tell a story about your favourite animal 🐰",
    "Describe everything you did today, from waking up to now",
    "Explain how to make your favourite food, step by step",
    "Tell a grown-up about your best friend and why you like them",
    "Retell a story from a book you have read",
    "Pretend you are a unicorn 🦄 and talk about your magical day",
    "Name 20 things in this room and say what colour they are",
    "Talk about where you would go if you could fly anywhere",
    "Tell a funny story — real or made up!",
    "Interview a family member: ask them 5 questions and listen",
    "Describe your dream birthday party",
    "Teach someone a game, explaining all the rules",
]
WRITING_PROMPTS = [
    "My perfect weekend",
    "A letter to a bunny who lives in the garden",
    "If I had a pet unicorn…",
    "The best day of my life",
    "Describe a rainbow to someone who has never seen one",
    "What I want to be when I grow up, and why",
    "A day in the life of a burrito 🌯",
    "My favourite book and why I love it",
    "If I were invisible for one day",
    "Three things that make me happy",
    "A story that starts with 'The door creaked open…'",
    "How to be a good friend",
]
# ================================================================================

TASK_BY_ID = {t["id"]: t for t in TASKS}

st.set_page_config(page_title=f"{STUDENT_NAME} Earns Stars", page_icon="🦄", layout="centered")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&display=swap');
.stApp {
  background:
    radial-gradient(circle at 8% 8%, rgba(255,182,217,.55) 0, transparent 32%),
    radial-gradient(circle at 92% 18%, rgba(196,170,255,.45) 0, transparent 34%),
    radial-gradient(circle at 15% 92%, rgba(160,220,255,.45) 0, transparent 34%),
    radial-gradient(circle at 88% 85%, rgba(255,236,150,.45) 0, transparent 30%),
    linear-gradient(180deg, #fff3fa 0%, #fdf0ff 50%, #eef8ff 100%);
}
h1, h2, h3, p, label, li, input, .stMarkdown, [data-baseweb="tab"] p { font-family: 'Fredoka', sans-serif !important; }
h3 { color: #5a2d66 !important; }
.block-container { max-width: 780px; padding-top: 2rem; }
.hero { position: relative; text-align: center; padding: 30px 16px 22px; border-radius: 28px;
  background: rgba(255,255,255,.75); border: 3px solid #ffd1e8;
  box-shadow: 0 8px 30px rgba(255,105,180,.18); margin-bottom: 16px; overflow: hidden; }
.hero .title { display: inline-block; font-size: 2.7rem; font-weight: 700; line-height: 1.15;
  background: linear-gradient(90deg,#ff4fa3,#ff9f43,#f5c400,#3fbf5a,#38b6ff,#9b6bff);
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero .sub { color: #8a5a8a; font-size: 1.05rem; margin-top: 4px; }
.hero .badge { display: inline-block; margin: 10px 4px 0; padding: 4px 14px; border-radius: 999px;
  font-weight: 600; font-size: .98rem; }
.badge.fire { background: #fff0d6; color: #b35c00; }
.badge.money { background: #e3f8e7; color: #1f7a37; }
.float { position: absolute; font-size: 2rem; animation: bob 3s ease-in-out infinite; }
.f1 { left: 16px; top: 14px; } .f2 { right: 18px; top: 16px; animation-delay: .6s; }
.f3 { left: 30px; bottom: 10px; animation-delay: 1.2s; } .f4 { right: 32px; bottom: 12px; animation-delay: 1.8s; }
@keyframes bob { 0%,100% { transform: translateY(0) rotate(-5deg); } 50% { transform: translateY(-8px) rotate(5deg); } }
.minutes { display: flex; justify-content: space-between; font-weight: 600; color: #6b3f73;
  margin: 2px 4px 6px; font-size: 1.1rem; }
.rbar { height: 22px; border-radius: 999px; background: #f3e6f7; overflow: hidden; border: 2px solid #ffd1e8; }
.rfill { height: 100%; border-radius: 999px;
  background: linear-gradient(90deg,#ff4fa3,#ff9f43,#f5c400,#3fbf5a,#38b6ff,#9b6bff,#ff4fa3);
  background-size: 300% 100%; animation: slide 6s linear infinite; }
@keyframes slide { 0% { background-position: 0% 50%; } 100% { background-position: 100% 50%; } }
[data-testid="stVerticalBlockBorderWrapper"] { background: rgba(255,255,255,.8);
  border-radius: 22px !important; border: 2px solid #ffd1e8 !important; }
[data-testid="stCheckbox"] label p { font-size: 1.12rem; font-weight: 500; }
.tip { background: #fff6fb; border-left: 5px solid #ff9ccc; border-radius: 12px; padding: 8px 12px;
  color: #6b3f73; margin: 0 0 6px 30px; font-size: .98rem; }
.reward-head { font-size: 1.4rem; font-weight: 700; color: #5a2d66; }
.how { color: #7a5a80; margin: 2px 0 8px; }
.pill { display: inline-block; padding: 3px 12px; border-radius: 999px; margin: 3px 4px 3px 0;
  font-size: .95rem; background: #f3e8ff; color: #5a2d66; }
.pill.ok { background: #dcf8e2; color: #1f7a37; }
.scroll { overflow-x: auto; }
table.week { border-collapse: collapse; width: 100%; font-size: .95rem; background: rgba(255,255,255,.8); border-radius: 16px; }
table.week th, table.week td { text-align: center; padding: 6px 5px; border-bottom: 1px solid #f6d6ea; }
table.week th { color: #6b3f73; font-weight: 600; }
table.week td.name { text-align: left; white-space: nowrap; }
table.week tr.star td { font-weight: 600; background: #fffbe6; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ------------------------------- dates & rules -------------------------------
def today_local() -> date:
    return datetime.now(ZoneInfo(TIMEZONE)).date()


def default_data():
    return {"days": {}, "claims": {}, "dollars_paid": 0, "history": []}


def done_on(data, d: date) -> set:
    return set(data["days"].get(d.isoformat(), []))


def unlocked_minutes(done: set) -> int:
    if not all(t["id"] in done for t in TASKS if t.get("required")):
        return 0
    return min(sum(TASK_BY_ID[t]["minutes"] for t in done if t in TASK_BY_ID), DAILY_GOAL_MINUTES)


def is_star_day(done: set) -> bool:
    return unlocked_minutes(done) >= DAILY_GOAL_MINUTES


def counts_for(data, reward_id, d: date) -> bool:
    """Days on or before the last time this reward was given don't count again."""
    last = data["claims"].get(reward_id)
    return last is None or d > date.fromisoformat(last)


def status_at(data, r, end: date):
    streak, d = 0, end
    while counts_for(data, r["id"], d) and "speak" in done_on(data, d):
        streak += 1
        d -= timedelta(days=1)
    window = [end - timedelta(days=i) for i in range(r["window"])]
    window = [x for x in window if counts_for(data, r["id"], x)]
    counts = {tid: sum(tid in done_on(data, x) for x in window) for tid in r["needs"]}
    ok = streak >= r["streak_len"] and all(counts[t] >= n for t, n in r["needs"].items())
    return {"streak": streak, "counts": counts, "ok": ok}


def reward_status(data, r, today: date):
    """Check ending today, or ending yesterday (so the streak isn't 0 before she speaks today)."""
    s_today = status_at(data, r, today)
    s_yday = status_at(data, r, today - timedelta(days=1))
    if s_today["ok"] or "speak" in done_on(data, today):
        return s_today
    return s_yday


def speaking_streak(data, today: date) -> int:
    d = today if "speak" in done_on(data, today) else today - timedelta(days=1)
    n = 0
    while "speak" in done_on(data, d):
        n += 1
        d -= timedelta(days=1)
    return n


def dollar_status(data):
    stars = sum(is_star_day(set(v)) for v in data["days"].values())
    earned = stars // STAR_DAYS_PER_DOLLAR
    return {"stars": stars, "owed": earned - data.get("dollars_paid", 0),
            "toward_next": stars % STAR_DAYS_PER_DOLLAR, "paid": data.get("dollars_paid", 0)}


def maths_problem(day: date, extra: int, level: str):
    rng = random.Random(day.toordinal() * 100 + extra)
    if level == "easy":
        a, b = rng.randint(1, 10), rng.randint(1, 10)
        op = rng.choice("+-")
    elif level == "hard":
        op = rng.choice(["+", "-", "×", "÷"])
        if op in "+-":
            a, b = rng.randint(100, 999), rng.randint(100, 999)
        else:
            a, b = rng.randint(3, 12), rng.randint(3, 12)
    else:
        op = rng.choice(["+", "-", "×"])
        if op in "+-":
            a, b = rng.randint(10, 99), rng.randint(10, 99)
        else:
            a, b = rng.randint(2, 10), rng.randint(2, 10)
    if op == "-" and b > a:
        a, b = b, a
    if op == "÷":
        a = a * b  # always divides exactly
    answer = {"+": a + b, "-": a - b, "×": a * b, "÷": a // b if b else 0}[op]
    return f"{a} {op} {b} = ?", answer


# --------------------------------- storage -----------------------------------
LOCAL_FILE = Path("progress_local.json")


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def storage_cfg():
    s = secret("storage")
    if s and s.get("github_token") and s.get("repo"):
        return {"token": s["github_token"], "repo": s["repo"], "path": s.get("path", "progress.json")}
    return None


def parent_pin() -> str:
    return str(secret("PARENT_PIN", "1234"))


def _gh(cfg):
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['path']}"
    headers = {"Authorization": f"Bearer {cfg['token']}", "Accept": "application/vnd.github+json",
               "Cache-Control": "no-cache"}
    return url, headers


def load_data():
    cfg = storage_cfg()
    if cfg:
        url, headers = _gh(cfg)
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 404:
            return default_data(), None
        r.raise_for_status()
        body = r.json()
        data = json.loads(base64.b64decode(body["content"]).decode())
        return {**default_data(), **data}, body["sha"]
    if LOCAL_FILE.exists():
        return {**default_data(), **json.loads(LOCAL_FILE.read_text())}, None
    return default_data(), None


def save_data(data, sha):
    text = json.dumps(data, indent=1, sort_keys=True)
    cfg = storage_cfg()
    if cfg:
        url, headers = _gh(cfg)
        payload = {"message": f"Progress update {today_local()}",
                   "content": base64.b64encode(text.encode()).decode()}
        if sha:
            payload["sha"] = sha
        r = requests.put(url, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        return r.json()["content"]["sha"]
    LOCAL_FILE.write_text(text)
    return None


def update(change) -> bool:
    """Re-read the latest saved progress, apply the change, save it back."""
    for attempt in range(2):
        try:
            data, sha = load_data()
            change(data)
            sha = save_data(data, sha)
            st.session_state.data, st.session_state.sha = data, sha
            return True
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if attempt == 0 and code in (409, 422):
                continue  # someone saved at the same moment — try again
            st.session_state.save_error = f"GitHub said {code}. The token may have expired or lost access."
            return False
        except Exception as e:  # network trouble etc.
            st.session_state.save_error = str(e)
            return False
    return False


if "data" not in st.session_state:
    try:
        st.session_state.data, st.session_state.sha = load_data()
    except Exception as e:
        st.session_state.data, st.session_state.sha = default_data(), None
        st.session_state.save_error = f"Couldn't load saved progress ({e})."

data = st.session_state.data
today = today_local()
TODAY_KEY = today.isoformat()
done_today = done_on(data, today)

# ------------------------------ messages on top ------------------------------
if err := st.session_state.pop("save_error", None):
    st.error(f"😿 Progress couldn't be saved. Ask a grown-up to check the Parent corner. ({err})")
if flash := st.session_state.pop("flash", None):
    st.success(flash)
    st.balloons()

# ------------------------------------ hero -----------------------------------
streak = speaking_streak(data, today)
dollars = dollar_status(data)
badges = f'<span class="badge fire">🔥 {streak}-day speaking streak</span>'
if dollars["paid"] or dollars["owed"]:
    badges += f'<span class="badge money">💵 ${dollars["paid"]} earned so far</span>'
st.markdown(
    f"""
<div class="hero">
  <div class="float f1">🦄</div><div class="float f2">🐰</div>
  <div class="float f3">🌈</div><div class="float f4">✨</div>
  <div class="title">Hi {STUDENT_NAME}!</div>
  <div class="sub">{today.strftime("%A, %d %B %Y")}</div>
  {badges}
</div>
""",
    unsafe_allow_html=True,
)

tab_today, tab_rewards, tab_week, tab_parent = st.tabs(
    ["🌈 Today", "🏆 Big rewards", "📅 My fortnight", "🔐 Grown-ups"]
)


# ------------------------------------ TODAY ----------------------------------
def toggle(tid, key):
    checked = st.session_state[key]

    def change(d):
        s = set(d["days"].get(TODAY_KEY, []))
        (s.add if checked else s.discard)(tid)
        d["days"][TODAY_KEY] = sorted(s)

    if not update(change):
        st.session_state[key] = not checked  # put the tick back how it was


def task_box(t, tip=None):
    key = f"{TODAY_KEY}_{t['id']}"
    if key not in st.session_state:
        st.session_state[key] = t["id"] in done_today
    st.checkbox(f"{t['emoji']} {t['name']}  **+{t['minutes']} min**", key=key,
                on_change=toggle, args=(t["id"], key))
    if tip:
        st.markdown(f'<div class="tip">{tip}</div>', unsafe_allow_html=True)


def check_maths(answer):
    raw = str(st.session_state.get("maths_answer", "")).strip()
    try:
        right = int(raw) == answer
    except ValueError:
        right = False
    st.session_state.maths_result = "right" if right else "wrong"
    if right:
        key = f"{TODAY_KEY}_maths"
        if not st.session_state.get(key):
            st.session_state[key] = True
            toggle("maths", key)


def new_problem():
    st.session_state.maths_shift = st.session_state.get("maths_shift", 0) + 1
    st.session_state.maths_result = None
    st.session_state.maths_answer = ""


with tab_today:
    mins = unlocked_minutes(done_today)
    pct = int(100 * mins / DAILY_GOAL_MINUTES)
    st.markdown(
        f'<div class="minutes"><span>⭐ {mins} min earned</span><span>🎯 goal {DAILY_GOAL_MINUTES} min</span></div>'
        f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
        unsafe_allow_html=True,
    )
    required_left = [t for t in TASKS if t.get("required") and t["id"] not in done_today]
    if required_left:
        st.warning("🔒 Do your **must do** task first to unlock screen time!")
    elif mins >= DAILY_GOAL_MINUTES:
        st.success(f"🦄 WOW {STUDENT_NAME}! You earned all {DAILY_GOAL_MINUTES} minutes today — it's a ⭐ star day!")
        if st.session_state.get("celebrated") != TODAY_KEY:
            st.balloons()
            st.session_state.celebrated = TODAY_KEY
    else:
        st.info(f"🐰 Hop hop! {DAILY_GOAL_MINUTES - mins} more minutes to earn. You can do it!")

    idea_n = today.toordinal() + st.session_state.get("idea_shift", 0)
    st.markdown("### 🦄 Must do every day")
    with st.container(border=True):
        for t in TASKS:
            if not t.get("required"):
                continue
            tip = None
            if t["id"] == "speak":
                tip = f"💡 <b>Idea for today:</b> {SPEAKING_IDEAS[idea_n % len(SPEAKING_IDEAS)]}"
            task_box(t, tip)
        if any(t["id"] == "speak" and t.get("required") for t in TASKS):
            if st.button("🎲 Give me a different idea"):
                st.session_state.idea_shift = st.session_state.get("idea_shift", 0) + 1
                st.rerun()

    st.markdown("### 🐰 Bonus tasks — earn more minutes")
    with st.container(border=True):
        for t in TASKS:
            if t.get("required"):
                continue
            tip = None
            if t["id"] == "write1":
                tip = f"✨ Write about: <b>{WRITING_PROMPTS[today.toordinal() % len(WRITING_PROMPTS)]}</b>"
            elif t["id"] == "write2":
                tip = f"✨ Write about: <b>{WRITING_PROMPTS[(today.toordinal() + 5) % len(WRITING_PROMPTS)]}</b>"
            task_box(t, tip)
            if t["id"] == "maths":
                shift = st.session_state.get("maths_shift", 0)
                question, answer = maths_problem(today, shift, MATHS_LEVEL)
                with st.form("maths_form", clear_on_submit=False, border=False):
                    c1, c2 = st.columns([2, 1])
                    c1.text_input(f"🧮 Problem of the day:  **{question}**", key="maths_answer",
                                  placeholder="Type your answer")
                    c2.write("")
                    c2.form_submit_button("Check ✔️", on_click=check_maths, args=(answer,))
                result = st.session_state.get("maths_result")
                if result == "right":
                    st.success("🎉 Correct! Maths ticked off.")
                elif result == "wrong":
                    st.error("Not quite — have another go! 💪")
                st.button("🔄 New problem", on_click=new_problem)


# ----------------------------------- REWARDS ---------------------------------
def give_reward(reward_id, pin_key):
    if str(st.session_state.get(pin_key, "")).strip() != parent_pin():
        st.session_state[pin_key + "_bad"] = True
        return

    def change(d):
        if reward_id == "dollar":
            d["dollars_paid"] = d.get("dollars_paid", 0) + 1
        else:
            d["claims"][reward_id] = TODAY_KEY
        d["history"].append({"reward": reward_id, "date": TODAY_KEY})

    if update(change):
        name = "$1" if reward_id == "dollar" else next(r["name"] for r in REWARDS if r["id"] == reward_id)
        st.session_state.flash = f"🎁 Reward given: {name}! Well done {STUDENT_NAME}!"


def claim_box(reward_id):
    pin_key = f"pin_{reward_id}"
    with st.form(f"claim_{reward_id}", border=False):
        c1, c2 = st.columns([2, 1])
        c1.text_input("Grown-up PIN to hand over the reward", type="password", key=pin_key)
        c2.write("")
        c2.form_submit_button("Give reward 🎁", on_click=give_reward, args=(reward_id, pin_key))
    if st.session_state.pop(pin_key + "_bad", False):
        st.error("That PIN isn't right.")


with tab_rewards:
    st.markdown("### 🏆 Big rewards")
    for r in REWARDS:
        s = reward_status(data, r, today)
        parts = [min(s["streak"], r["streak_len"]) / r["streak_len"]]
        parts += [min(s["counts"][t], n) / n for t, n in r["needs"].items()]
        pct = int(100 * sum(parts) / len(parts))
        with st.container(border=True):
            st.markdown(f'<div class="reward-head">{r["emoji"]} {r["name"]}</div>'
                        f'<div class="how">{r["how"]}</div>', unsafe_allow_html=True)
            pills = [f'<span class="pill {"ok" if s["streak"] >= r["streak_len"] else ""}">'
                     f'🗣️ speaking in a row {min(s["streak"], r["streak_len"])}/{r["streak_len"]}</span>']
            for tid, n in r["needs"].items():
                t = TASK_BY_ID[tid]
                pills.append(f'<span class="pill {"ok" if s["counts"][tid] >= n else ""}">'
                             f'{t["emoji"]} {tid} {min(s["counts"][tid], n)}/{n} days</span>')
            st.markdown("".join(pills), unsafe_allow_html=True)
            st.markdown(f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
                        unsafe_allow_html=True)
            if s["ok"]:
                st.success(f"🎉 UNLOCKED! {STUDENT_NAME} has earned a {r['name'].lower()}!")
                claim_box(r["id"])
            elif s["streak"] == 0 and r["streak_len"] > 1:
                st.caption("🌱 Start your speaking streak today — every day counts!")

    with st.container(border=True):
        st.markdown(f'<div class="reward-head">💵 Earn a dollar</div>'
                    f'<div class="how">Every {STAR_DAYS_PER_DOLLAR} ⭐ star days (days you earn the full '
                    f'{DAILY_GOAL_MINUTES} minutes) = $1. They don\'t have to be in a row.</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<span class="pill">⭐ {dollars["toward_next"]}/{STAR_DAYS_PER_DOLLAR} star days toward the next $1</span>'
                    f'<span class="pill ok">💵 ${dollars["paid"]} given so far</span>', unsafe_allow_html=True)
        pct = int(100 * dollars["toward_next"] / STAR_DAYS_PER_DOLLAR)
        st.markdown(f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
                    unsafe_allow_html=True)
        if dollars["owed"] > 0:
            st.success(f"🎉 {STUDENT_NAME} has earned ${dollars['owed']} that hasn't been handed over yet!")
            claim_box("dollar")


# ------------------------------------ WEEK -----------------------------------
with tab_week:
    st.markdown("### 📅 The last 14 days")
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    head = "".join(f"<th>{d.strftime('%a')}<br>{d.day}</th>" for d in days)
    rows = ""
    for t in TASKS:
        cells = "".join(f"<td>{'✅' if t['id'] in done_on(data, d) else '·'}</td>" for d in days)
        rows += f"<tr><td class='name'>{t['emoji']} {t['id']}</td>{cells}</tr>"
    stars = "".join(f"<td>{'⭐' if is_star_day(done_on(data, d)) else ''}</td>" for d in days)
    mins_row = "".join(f"<td>{unlocked_minutes(done_on(data, d)) or ''}</td>" for d in days)
    rows += f"<tr class='star'><td class='name'>⭐ star day</td>{stars}</tr>"
    rows += f"<tr><td class='name'>⏱️ minutes</td>{mins_row}</tr>"
    st.markdown(f"<div class='scroll'><table class='week'><tr><th></th>{head}</tr>{rows}</table></div>",
                unsafe_allow_html=True)


# ----------------------------------- PARENT ----------------------------------
def save_edit():
    d_iso = st.session_state.edit_date.isoformat()
    chosen = st.session_state[f"edit_tasks_{d_iso}"]

    def change(d):
        d["days"][d_iso] = sorted(chosen)

    if update(change):
        if d_iso == TODAY_KEY:
            for t in TASKS:
                st.session_state[f"{TODAY_KEY}_{t['id']}"] = t["id"] in chosen
        st.session_state.flash = "Saved ✔️"


def reset_all():
    def change(d):
        d.clear()
        d.update(default_data())

    if update(change):
        for k in list(st.session_state.keys()):
            if k.startswith(TODAY_KEY):
                del st.session_state[k]
        st.session_state.flash = "All progress reset."


with tab_parent:
    if not st.session_state.get("parent_ok"):
        st.markdown("### 🔐 Grown-ups only")
        with st.form("parent_login", border=False):
            pin = st.text_input("PIN", type="password")
            if st.form_submit_button("Open"):
                if pin.strip() == parent_pin():
                    st.session_state.parent_ok = True
                    st.rerun()
                else:
                    st.error("That PIN isn't right.")
    else:
        if storage_cfg():
            st.success(f"✅ Progress is saved to GitHub ({storage_cfg()['repo']}).")
        else:
            st.warning("⚠️ Permanent saving isn't set up yet, so progress can be lost when the app "
                       "restarts or goes to sleep. Add the [storage] secrets to fix this.")
        if parent_pin() == "1234":
            st.info("Tip: the PIN is still the default 1234. Set PARENT_PIN in the app's Secrets.")

        st.markdown("#### ✏️ Fix a day")
        st.caption("Forgot to tick something on a past day? Correct it here — streaks update automatically.")
        st.date_input("Day", value=today, max_value=today, key="edit_date", format="DD/MM/YYYY")
        d_iso = st.session_state.edit_date.isoformat()
        st.multiselect("Tasks done that day", options=[t["id"] for t in TASKS],
                       default=sorted(done_on(data, st.session_state.edit_date) & set(TASK_BY_ID)),
                       format_func=lambda tid: f"{TASK_BY_ID[tid]['emoji']} {TASK_BY_ID[tid]['name']}",
                       key=f"edit_tasks_{d_iso}")
        st.button("Save this day", on_click=save_edit)

        st.markdown("#### 🎁 Rewards handed over")
        if data["history"]:
            for h in reversed(data["history"][-20:]):
                name = "$1" if h["reward"] == "dollar" else next(
                    (f"{r['emoji']} {r['name']}" for r in REWARDS if r["id"] == h["reward"]), h["reward"])
                st.write(f"• {date.fromisoformat(h['date']).strftime('%d %b %Y')} — {name}")
        else:
            st.caption("None yet.")

        with st.expander("⚠️ Reset everything"):
            confirm = st.checkbox(f"Yes, delete all of {STUDENT_NAME}'s progress")
            st.button("Reset all progress", on_click=reset_all, disabled=not confirm)

        if st.button("🔒 Lock"):
            st.session_state.parent_ok = False
            st.rerun()
