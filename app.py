import base64
import json
import random
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# ============================ SETTINGS (edit these) ============================
STUDENT_NAME = "Andal"
LANGUAGE = "your language"     # e.g. replace with the name of the language
DAILY_GOAL_MINUTES = 30        # most screen time she can earn from tasks in one day
TIMEZONE = "Australia/Brisbane"
MATHS_TO_SOLVE = 3             # maths problems to solve to tick the maths task
TRIES_FOR_CLUE_1 = 2           # wrong tries before clue 1 appears
TRIES_FOR_CLUE_2 = 4           # wrong tries before clue 2 appears
TRIES_BEFORE_SKIP = 3          # wrong tries before she may swap to a different problem

# id: short code (don't change once she has progress)   minutes: screen time it earns
# required: True = must be done before ANY screen time unlocks that day
# section: where it shows on the Today tab
TASKS = [
    {"id": "speak", "emoji": "🗣️", "name": f"Speak {LANGUAGE} for 10 minutes", "minutes": 10,
     "required": True, "section": "must"},
    {"id": "write1", "emoji": "✏️", "name": "English writing – piece 1", "minutes": 5, "section": "learn"},
    {"id": "write2", "emoji": "📝", "name": "English writing – piece 2", "minutes": 5, "section": "learn"},
    {"id": "maths", "emoji": "🔢", "name": f"Solve {MATHS_TO_SOLVE} maths problems", "minutes": 5,
     "section": "learn", "auto": True},
    {"id": "read", "emoji": "📚", "name": "Read a book for 20 minutes", "minutes": 5, "section": "learn"},
    {"id": "exercise", "emoji": "🤸", "name": "Exercise or active play for 20 minutes", "minutes": 5,
     "section": "body"},
    {"id": "meditate", "emoji": "🧘", "name": "Quiet meditation for 5 minutes", "minutes": 5, "section": "body"},
    {"id": "sit1", "emoji": "🪷", "name": "Sit perfectly still for 1 minute", "minutes": 3, "section": "body"},
    {"id": "sit2", "emoji": "🦢", "name": "Sit perfectly still for 2 minutes", "minutes": 5, "section": "body"},
    {"id": "sing", "emoji": "🎤", "name": "Practise singing for 15 minutes", "minutes": 5, "section": "habits"},
    {"id": "bed", "emoji": "🌙", "name": "Was in bed by 9:30 pm last night", "minutes": 0, "section": "habits"},
]

SECTIONS = [
    ("must", "🦄 Must do every day"),
    ("learn", "🐰 Learning tasks"),
    ("body", "🌈 Body & calm"),
    ("habits", "🌙 Singing & sleep"),
]

# Big rewards.
#   streak_task / streak_len: that task must be done this many days IN A ROW
#   window / needs: inside the last `window` days, these tasks need at least this many days
#   bonus_minutes: instead of a treat, adds extra screen-time minutes to her bonus bank
REWARDS = [
    {"id": "burrito", "emoji": "🌯", "name": "Burrito treat", "streak_task": "speak", "streak_len": 7,
     "window": 7, "needs": {"exercise": 4, "meditate": 4, "read": 4},
     "how": f"Speak {LANGUAGE} 7 days in a row, and that week exercise, meditate and read on at least 4 days each."},
    {"id": "movie", "emoji": "🎬", "name": "Movie at the cinema", "streak_task": "speak", "streak_len": 21,
     "window": 30, "needs": {"exercise": 20, "read": 20},
     "how": f"Speak {LANGUAGE} 21 days in a row (no breaks!), and over the month exercise and read on at least 20 days each."},
    {"id": "icecream", "emoji": "🍦", "name": "Choose your own ice cream", "streak_task": "bed", "streak_len": 30,
     "window": 30, "needs": {},
     "how": "In bed by 9:30 pm every night for 30 nights in a row."},
    {"id": "playcentre", "emoji": "🎠", "name": "Play centre of your choice (up to $50)", "streak_task": "bed",
     "streak_len": 90, "window": 90, "needs": {},
     "how": "In bed by 9:30 pm every night for 3 months (90 nights) in a row."},
    {"id": "singing", "emoji": "🎶", "name": "Singing star: +60 bonus screen-time minutes", "streak_task": "sing",
     "streak_len": 30, "window": 30, "needs": {}, "bonus_minutes": 60,
     "how": "Practise singing 15 minutes every day for 30 days in a row. The minutes go into your bonus bank."},
]
STAR_DAYS_PER_DOLLAR = 14      # a "star day" = she earned the full daily screen time
BONUS_SPEND_STEP = 10          # bonus-bank minutes used per tap

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


def md_safe(text) -> str:
    """Stop Streamlit reading text between two $ signs as a maths formula (plain markdown)."""
    return str(text).replace("$", "\\$")


def html_safe(text) -> str:
    """Same, for text placed inside HTML snippets."""
    return str(text).replace("$", "&#36;")

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
.block-container { max-width: 800px; padding-top: 2rem; }
.hero { position: relative; text-align: center; padding: 30px 16px 22px; border-radius: 28px;
  background: rgba(255,255,255,.75); border: 3px solid #ffd1e8;
  box-shadow: 0 8px 30px rgba(255,105,180,.18); margin-bottom: 16px; overflow: hidden; }
.hero .title { display: inline-block; font-size: 2.7rem; font-weight: 700; line-height: 1.15;
  background: linear-gradient(90deg,#ff4fa3,#ff9f43,#f5c400,#3fbf5a,#38b6ff,#9b6bff);
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero .sub { color: #8a5a8a; font-size: 1.05rem; margin-top: 4px; }
.hero .badge { display: inline-block; margin: 10px 4px 0; padding: 4px 14px; border-radius: 999px;
  font-weight: 600; font-size: .95rem; }
.badge.fire { background: #fff0d6; color: #b35c00; }
.badge.moon { background: #ece6ff; color: #4b3a99; }
.badge.money { background: #e3f8e7; color: #1f7a37; }
.badge.bank { background: #ffe3f1; color: #a3236b; }
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
.reward-head { font-size: 1.35rem; font-weight: 700; color: #5a2d66; }
.how { color: #7a5a80; margin: 2px 0 8px; }
.pill { display: inline-block; padding: 3px 12px; border-radius: 999px; margin: 3px 4px 3px 0;
  font-size: .95rem; background: #f3e8ff; color: #5a2d66; }
.pill.ok { background: #dcf8e2; color: #1f7a37; }
.topic { display: inline-block; padding: 3px 12px; border-radius: 999px; background: #e0f2ff; color: #1d5f8a;
  font-weight: 600; font-size: .9rem; }
.question { font-size: 2rem; font-weight: 700; color: #3b2350; margin: 10px 0 6px; line-height: 1.3; }
.locked { background: #f6f0fa; border: 2px dashed #d9c4e6; border-radius: 14px; padding: 10px 14px;
  color: #8a6a96; margin: 6px 0; }
.clue { background: #fffbe6; border: 2px solid #ffe28a; border-radius: 14px; padding: 10px 14px;
  color: #6b4e00; margin: 6px 0; }
.scroll { overflow-x: auto; }
table.week { border-collapse: collapse; width: 100%; font-size: .95rem; background: rgba(255,255,255,.8); }
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
    return {"days": {}, "claims": {}, "dollars_paid": 0, "history": [],
            "maths": {}, "bonus_bank": 0, "bonus_used": {}}


def done_on(data, d: date) -> set:
    return set(data["days"].get(d.isoformat(), []))


def task_minutes(done: set) -> int:
    if not all(t["id"] in done for t in TASKS if t.get("required")):
        return 0
    return min(sum(TASK_BY_ID[t]["minutes"] for t in done if t in TASK_BY_ID), DAILY_GOAL_MINUTES)


def is_star_day(done: set) -> bool:
    return task_minutes(done) >= DAILY_GOAL_MINUTES


def counts_for(data, reward_id, d: date) -> bool:
    """Days on or before the last time this reward was given don't count again."""
    last = data["claims"].get(reward_id)
    return last is None or d > date.fromisoformat(last)


def status_at(data, r, end: date):
    streak, d = 0, end
    while counts_for(data, r["id"], d) and r["streak_task"] in done_on(data, d):
        streak += 1
        d -= timedelta(days=1)
    window = [end - timedelta(days=i) for i in range(r["window"])]
    window = [x for x in window if counts_for(data, r["id"], x)]
    counts = {tid: sum(tid in done_on(data, x) for x in window) for tid in r["needs"]}
    ok = streak >= r["streak_len"] and all(counts[t] >= n for t, n in r["needs"].items())
    return {"streak": streak, "counts": counts, "ok": ok}


def reward_status(data, r, today: date):
    """Check ending today, or ending yesterday (so a streak isn't 0 before today's task is done)."""
    s_today = status_at(data, r, today)
    if s_today["ok"] or r["streak_task"] in done_on(data, today):
        return s_today
    return status_at(data, r, today - timedelta(days=1))


def task_streak(data, today: date, tid: str) -> int:
    d = today if tid in done_on(data, today) else today - timedelta(days=1)
    n = 0
    while tid in done_on(data, d):
        n += 1
        d -= timedelta(days=1)
    return n


def dollar_status(data):
    stars = sum(is_star_day(set(v)) for v in data["days"].values())
    earned = stars // STAR_DAYS_PER_DOLLAR
    return {"owed": earned - data.get("dollars_paid", 0),
            "toward_next": stars % STAR_DAYS_PER_DOLLAR, "paid": data.get("dollars_paid", 0)}


# ------------------------------ Year 4 maths bank ------------------------------
def _frac(n, d):
    return f"{n}/{d}"


def _dec(tenths_or_hund, places=1):
    return f"{tenths_or_hund / (10 ** places):.{places}f}"


def make_problem(day: date, index: int):
    """Returns dict(topic, question, answer: Fraction, clues: [str, str]). Same day+index = same problem."""
    rng = random.Random(day.toordinal() * 1000 + index)
    kind = rng.choice([
        "frac_add", "frac_sub", "frac_of", "equiv", "dec_add", "dec_sub", "dec_hund",
        "times", "mult_2x1", "divide", "money", "add_3d", "sub_3d",
    ])
    if kind == "frac_add":
        d = rng.choice([4, 5, 6, 8, 10, 12])
        a = rng.randint(1, d - 2)
        b = rng.randint(1, d - 1 - a)
        return dict(topic="Fractions ➕", question=f"{_frac(a, d)} + {_frac(b, d)} = ?",
                    answer=Fraction(a + b, d), hint="Write your answer as a fraction, like 3/8",
                    clues=["When the bottom numbers (denominators) are the same, they stay the same in the answer.",
                           f"Add only the top numbers: {a} + {b}. The bottom number stays {d}."])
    if kind == "frac_sub":
        d = rng.choice([4, 5, 6, 8, 10, 12])
        a = rng.randint(2, d - 1)
        b = rng.randint(1, a - 1)
        return dict(topic="Fractions ➖", question=f"{_frac(a, d)} − {_frac(b, d)} = ?",
                    answer=Fraction(a - b, d), hint="Write your answer as a fraction, like 2/5",
                    clues=["Same bottom numbers? Then the bottom number doesn't change.",
                           f"Take away the top numbers: {a} − {b}. Keep {d} on the bottom."])
    if kind == "frac_of":
        d = rng.choice([2, 3, 4, 5, 10])
        a = rng.randint(1, d - 1)
        n = d * rng.randint(2, 10)
        return dict(topic="Fraction of a number 🍕", question=f"What is {_frac(a, d)} of {n}?",
                    answer=Fraction(a * n, d), hint="Type a whole number",
                    clues=[f"First share {n} into {d} equal groups. How many are in ONE group?",
                           f"One group is {n} ÷ {d}. You need {a} of those groups, so multiply by {a}."])
    if kind == "equiv":
        d = rng.choice([2, 3, 4, 5])
        a = rng.randint(1, d - 1)
        m = rng.choice([2, 3, 4, 5])
        return dict(topic="Equivalent fractions 🟰", question=f"{_frac(a, d)} = ?/{d * m}",
                    answer=Fraction(a * m), hint="Type the missing top number",
                    clues=[f"What do you multiply {d} by to get {d * m}?",
                           f"Whatever you did to the bottom ({d} × {m}), do the same to the top: {a} × {m}."])
    if kind == "dec_add":
        a, b = rng.randint(1, 49), rng.randint(1, 49)
        return dict(topic="Decimals ➕", question=f"{_dec(a)} + {_dec(b)} = ?", answer=Fraction(a + b, 10),
                    hint="Type a decimal, like 3.4",
                    clues=["Line up the decimal points, like stacking ones and tenths in columns.",
                           "Add the tenths first. If you get 10 or more tenths, that makes 1 whole — carry it over."])
    if kind == "dec_sub":
        a = rng.randint(20, 99)
        b = rng.randint(1, a - 1)
        return dict(topic="Decimals ➖", question=f"{_dec(a)} − {_dec(b)} = ?", answer=Fraction(a - b, 10),
                    hint="Type a decimal, like 2.6",
                    clues=["Line up the decimal points first.",
                           "Subtract the tenths first. Not enough tenths? Swap 1 whole for 10 tenths."])
    if kind == "dec_hund":
        a, b = rng.randint(101, 499), rng.randint(5, 95)
        return dict(topic="Decimals (hundredths) 💯", question=f"{_dec(a, 2)} + {_dec(b, 2)} = ?",
                    answer=Fraction(a + b, 100), hint="Type a decimal, like 3.45",
                    clues=["Both numbers have 2 digits after the point. Line up the points.",
                           "Add hundredths, then tenths, then ones — carry when a column makes 10."])
    if kind == "times":
        a, b = rng.randint(3, 10), rng.randint(3, 10)
        return dict(topic="Times tables ✖️", question=f"{a} × {b} = ?", answer=Fraction(a * b),
                    hint="Type a whole number",
                    clues=[f"Think of it as {b} groups of {a}.",
                           f"Skip-count by {a}: {a}, {2 * a}, {3 * a}… keep going until you've said {b} numbers."])
    if kind == "mult_2x1":
        n, m = rng.randint(12, 49), rng.randint(3, 9)
        tens, ones = n - n % 10, n % 10
        return dict(topic="Multiplication ✖️", question=f"{n} × {m} = ?", answer=Fraction(n * m),
                    hint="Type a whole number",
                    clues=[f"Split {n} into tens and ones: {tens} + {ones}.",
                           f"Work out {tens} × {m} and {ones} × {m}, then add the two answers together."])
    if kind == "divide":
        dv, q = rng.randint(3, 10), rng.randint(3, 10)
        return dict(topic="Division ➗", question=f"{dv * q} ÷ {dv} = ?", answer=Fraction(q),
                    hint="Type a whole number",
                    clues=[f"How many groups of {dv} fit into {dv * q}?",
                           f"Turn it around: {dv} × ? = {dv * q}. Which times-table fact helps?"])
    if kind == "money":
        have = rng.choice([5, 10, 20])
        cost = rng.randint(105, have * 100 - 25)
        cost -= cost % 5
        item = rng.choice(["a pencil case", "a book", "some stickers", "a toy bunny", "a smoothie"])
        return dict(topic="Money 💵",
                    question=f"{STUDENT_NAME} pays for {item} costing ${cost / 100:.2f} with a ${have} note. "
                             f"How much change does she get?",
                    answer=Fraction(have * 100 - cost, 100), hint="Type dollars and cents, like 3.45",
                    clues=["Change = the money you gave − the price.",
                           f"Count up from ${cost / 100:.2f}: first to the next whole dollar, then up to ${have}."])
    if kind == "add_3d":
        a, b = rng.randint(125, 699), rng.randint(125, 299)
        return dict(topic="Adding big numbers ➕", question=f"{a} + {b} = ?", answer=Fraction(a + b),
                    hint="Type a whole number",
                    clues=["Add the ones first, then the tens, then the hundreds.",
                           "If a column adds up to 10 or more, carry 1 to the next column."])
    a = rng.randint(400, 999)
    b = rng.randint(101, a - 50)
    return dict(topic="Subtracting big numbers ➖", question=f"{a} − {b} = ?", answer=Fraction(a - b),
                hint="Type a whole number",
                clues=["Start with the ones column, then tens, then hundreds.",
                       "Top digit smaller than the bottom one? Borrow 1 from the next column (it becomes 10)."])


def parse_answer(text: str):
    s = str(text).strip().replace("$", "").replace(",", "").replace(" ", " ")
    if not s:
        return None
    try:
        parts = s.split()
        if len(parts) == 2 and "/" in parts[1]:   # mixed number like 1 1/2
            whole = Fraction(parts[0])
            return whole + Fraction(parts[1]) * (1 if whole >= 0 else -1)
        return Fraction(s.replace(" ", ""))
    except (ValueError, ZeroDivisionError):
        return None


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
        except Exception as e:
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
    st.error(f"😿 Progress couldn't be saved. Ask a grown-up to check the Grown-ups tab. ({err})")
if flash := st.session_state.pop("flash", None):
    st.success(flash)
    st.balloons()

# ------------------------------------ hero -----------------------------------
dollars = dollar_status(data)
bank = data.get("bonus_bank", 0)
badges = (f'<span class="badge fire">🔥 {task_streak(data, today, "speak")}-day speaking streak</span>'
          f'<span class="badge moon">🌙 {task_streak(data, today, "bed")}-night bedtime streak</span>')
if bank:
    badges += f'<span class="badge bank">🎶 {bank} bonus minutes saved</span>'
if dollars["paid"] or dollars["owed"]:
    badges += f'<span class="badge money">💵 &#36;{dollars["paid"]} earned so far</span>'
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

tab_today, tab_maths, tab_rewards, tab_week, tab_parent = st.tabs(
    ["🌈 Today", "🧮 Maths & clues", "🏆 Big rewards", "📅 My fortnight", "🔐 Grown-ups"]
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


def task_label(t):
    reward = f"  **+{t['minutes']} min**" if t["minutes"] else "  *(counts toward big rewards)*"
    return f"{t['emoji']} {t['name']}{reward}"


def task_box(t, tip=None):
    if t.get("auto"):
        is_done = t["id"] in done_today
        st.checkbox(task_label(t), value=is_done, disabled=True, key=f"view_{TODAY_KEY}_{t['id']}_{is_done}")
    else:
        key = f"{TODAY_KEY}_{t['id']}"
        if key not in st.session_state:
            st.session_state[key] = t["id"] in done_today
        st.checkbox(task_label(t), key=key, on_change=toggle, args=(t["id"], key))
    if tip:
        st.markdown(f'<div class="tip">{tip}</div>', unsafe_allow_html=True)


def spend_bonus():
    def change(d):
        step = min(BONUS_SPEND_STEP, d.get("bonus_bank", 0))
        d["bonus_bank"] = d.get("bonus_bank", 0) - step
        d.setdefault("bonus_used", {})[TODAY_KEY] = d.get("bonus_used", {}).get(TODAY_KEY, 0) + step

    update(change)


def next_idea():
    st.session_state.idea_shift = st.session_state.get("idea_shift", 0) + 1


SIT_TIMER = """
<div style="font-family:'Fredoka',sans-serif;text-align:center;padding:10px;border-radius:16px;
  background:#f6f0ff;border:2px solid #d9c4f6">
  <div id="t" style="font-size:2.4rem;font-weight:700;color:#5a2d66">🦢 Ready?</div>
  <div style="margin-top:6px">
    <button onclick="go(60)" style="font-size:1rem;padding:6px 14px;border-radius:999px;border:0;
      background:#ff7fbf;color:white;margin:3px;cursor:pointer">Start 1 minute</button>
    <button onclick="go(120)" style="font-size:1rem;padding:6px 14px;border-radius:999px;border:0;
      background:#9b6bff;color:white;margin:3px;cursor:pointer">Start 2 minutes</button>
  </div>
</div>
<script>
let iv = null;
function beep(){ try { const c = new (window.AudioContext||window.webkitAudioContext)();
  [0,0.25,0.5].forEach(s=>{const o=c.createOscillator();o.frequency.value=880;o.connect(c.destination);
  o.start(c.currentTime+s);o.stop(c.currentTime+s+0.15);}); } catch(e){} }
function go(sec){ clearInterval(iv); let left = sec; const t = document.getElementById('t');
  const show = () => { t.textContent = '🤫 ' + Math.floor(left/60) + ':' + String(left%60).padStart(2,'0'); };
  show(); iv = setInterval(()=>{ left--; if(left<=0){ clearInterval(iv);
    t.textContent='🎉 Done! Show your grown-up'; beep(); } else show(); }, 1000); }
</script>
"""

with tab_today:
    task_mins = task_minutes(done_today)
    bonus_today = data.get("bonus_used", {}).get(TODAY_KEY, 0)
    pct = int(100 * task_mins / DAILY_GOAL_MINUTES)
    extra = f" + 🎶 {bonus_today} bonus" if bonus_today else ""
    st.markdown(
        f'<div class="minutes"><span>⭐ {task_mins} min earned{extra}</span>'
        f'<span>🎯 goal {DAILY_GOAL_MINUTES} min</span></div>'
        f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
        unsafe_allow_html=True,
    )
    required_left = [t for t in TASKS if t.get("required") and t["id"] not in done_today]
    if required_left:
        st.warning("🔒 Do your **must do** task first to unlock screen time!")
    elif task_mins >= DAILY_GOAL_MINUTES:
        st.success(f"🦄 WOW {STUDENT_NAME}! You earned all {DAILY_GOAL_MINUTES} minutes today — it's a ⭐ star day!")
        if st.session_state.get("celebrated") != TODAY_KEY:
            st.balloons()
            st.session_state.celebrated = TODAY_KEY
    else:
        st.info(f"🐰 Hop hop! {DAILY_GOAL_MINUTES - task_mins} more minutes to earn. You can do it!")

    if bonus_today:
        st.markdown(f"**Total screen time today: {task_mins + bonus_today} minutes** 🎉")
    if bank > 0:
        with st.container(border=True):
            st.markdown(f"🎶 **Bonus bank: {bank} minutes** — extra screen time you earned by singing!")
            st.button(f"Use {min(BONUS_SPEND_STEP, bank)} bonus minutes today", on_click=spend_bonus,
                      disabled=bool(required_left),
                      help="Finish your must-do task first" if required_left else None)

    idea_n = today.toordinal() + st.session_state.get("idea_shift", 0)
    write_n = today.toordinal()
    tips = {
        "speak": f"💡 <b>Idea for today:</b> {SPEAKING_IDEAS[idea_n % len(SPEAKING_IDEAS)]}",
        "write1": f"✨ Write about: <b>{WRITING_PROMPTS[write_n % len(WRITING_PROMPTS)]}</b>",
        "write2": f"✨ Write about: <b>{WRITING_PROMPTS[(write_n + 5) % len(WRITING_PROMPTS)]}</b>",
        "maths": f"🧮 Go to the <b>Maths & clues</b> tab. This ticks itself when you solve {MATHS_TO_SOLVE} problems "
                 f"(solved today: {data.get('maths', {}).get(TODAY_KEY, {}).get('solved', 0)}).",
        "sit1": "📣 <b>Call a grown-up to watch you first!</b> Sit cross-legged, hands resting on your knees, "
                "back tall, eyes soft. No talking, no wiggling, no giggling. Use the timer below.",
        "sit2": "📣 <b>Call a grown-up to watch.</b> Same as the 1-minute challenge, but twice as long! "
                "Tip: breathe slowly and count your breaths.",
        "sing": "🎶 Sing for 15 minutes every day for 30 days in a row to win 60 bonus minutes!",
        "bed": "🌙 Tick this in the morning if you were in bed by 9:30 pm last night. "
               "30 nights in a row = 🍦 ice cream. 90 nights = 🎠 play centre!",
    }
    for sec_id, sec_title in SECTIONS:
        sec_tasks = [t for t in TASKS if t.get("section", "learn") == sec_id]
        if not sec_tasks:
            continue
        st.markdown(f"### {sec_title}")
        with st.container(border=True):
            for t in sec_tasks:
                task_box(t, tips.get(t["id"]))
                if t["id"] == "speak":
                    st.button("🎲 Give me a different idea", on_click=next_idea)
            if sec_id == "body" and any(t["id"] in ("sit1", "sit2") for t in sec_tasks):
                if hasattr(st, "iframe"):
                    st.iframe(SIT_TIMER, height=130)
                else:  # older Streamlit versions
                    import streamlit.components.v1 as components
                    components.html(SIT_TIMER, height=130)


# ------------------------------------ MATHS ----------------------------------
def maths_state(d):
    return d.setdefault("maths", {}).setdefault(TODAY_KEY, {"index": 0, "solved": 0, "tries": 0, "log": []})


def check_answer():
    given = parse_answer(st.session_state.get("maths_answer", ""))
    if given is None:
        st.session_state.maths_msg = ("warn", "Hmm, I can't read that. Try a number like 12, 3.4 or 5/8.")
        return
    outcome = {}

    def change(d):
        m = maths_state(d)
        prob = make_problem(today, m["index"])
        if given == prob["answer"]:
            m["solved"] += 1
            m["log"].append(prob["question"])
            m["index"] += 1
            m["tries"] = 0
            outcome["right"] = True
            if m["solved"] >= MATHS_TO_SOLVE:
                s = set(d["days"].get(TODAY_KEY, []))
                s.add("maths")
                d["days"][TODAY_KEY] = sorted(s)
        else:
            m["tries"] += 1
            outcome["right"] = False

    if update(change):
        st.session_state.maths_answer = ""
        if outcome["right"]:
            cheers = ["🎉 Brilliant!", "🦄 Magical!", "🌟 Superstar!", "🐰 Hop-tastic!", "🌈 You got it!"]
            st.session_state.maths_msg = ("ok", random.choice(cheers) + " That's correct!")
            st.session_state.maths_party = True
        else:
            st.session_state.maths_msg = ("bad", "Not quite — check your working and try again! 💪")


def skip_problem():
    def change(d):
        m = maths_state(d)
        m["index"] += 1
        m["tries"] = 0

    if update(change):
        st.session_state.maths_answer = ""
        st.session_state.maths_msg = ("info", "Here's a different problem. You've got this!")


with tab_maths:
    m = data.get("maths", {}).get(TODAY_KEY, {"index": 0, "solved": 0, "tries": 0, "log": []})
    st.markdown("### 🧮 Year 4 maths challenge")
    solved = m["solved"]
    pct = int(100 * min(solved, MATHS_TO_SOLVE) / MATHS_TO_SOLVE)
    st.markdown(
        f'<div class="minutes"><span>✅ Solved today: {solved}</span>'
        f'<span>🎯 {MATHS_TO_SOLVE} to tick your maths task</span></div>'
        f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
        unsafe_allow_html=True,
    )
    if solved >= MATHS_TO_SOLVE:
        st.success("🌟 Maths task done for today! Keep going for extra practice if you like.")

    prob = make_problem(today, m["index"])
    tries = m["tries"]
    with st.container(border=True):
        st.markdown(f'<span class="topic">{prob["topic"]}</span>'
                    f'<div class="question">{html_safe(prob["question"])}</div>', unsafe_allow_html=True)
        with st.form("maths_form", border=False):
            c1, c2 = st.columns([3, 1])
            c1.text_input("Your answer", key="maths_answer", placeholder=prob["hint"],
                          label_visibility="collapsed")
            c2.form_submit_button("Check ✔️", on_click=check_answer, use_container_width=True)
        st.caption(f"Tries on this problem: {tries}")

        msg = st.session_state.pop("maths_msg", None)
        if msg:
            {"ok": st.success, "bad": st.error, "warn": st.warning, "info": st.info}[msg[0]](msg[1])
        if st.session_state.pop("maths_party", False):
            st.balloons()

        st.markdown("#### 🔍 Clues")
        for n, need in ((1, TRIES_FOR_CLUE_1), (2, TRIES_FOR_CLUE_2)):
            if tries >= need:
                st.markdown(f'<div class="clue">💡 <b>Clue {n}:</b> {html_safe(prob["clues"][n - 1])}</div>',
                            unsafe_allow_html=True)
            else:
                left = need - tries
                st.markdown(f'<div class="locked">🔒 Clue {n} unlocks after {left} more '
                            f'{"try" if left == 1 else "tries"}. Have a go first!</div>', unsafe_allow_html=True)
        if tries >= TRIES_FOR_CLUE_2:
            st.info("🙋 Still stuck? Ask a grown-up to sit with you and work through the clues together.")
        if tries >= TRIES_BEFORE_SKIP:
            st.button("🔄 Try a different problem", on_click=skip_problem)

    if m.get("log"):
        with st.expander(f"⭐ Problems you solved today ({len(m['log'])})"):
            for q in m["log"]:
                st.markdown(f"✅ {md_safe(q)}")


# ----------------------------------- REWARDS ---------------------------------
def give_reward(reward_id, pin_key):
    if str(st.session_state.get(pin_key, "")).strip() != parent_pin():
        st.session_state[pin_key + "_bad"] = True
        return
    r = next((x for x in REWARDS if x["id"] == reward_id), None)

    def change(d):
        if reward_id == "dollar":
            d["dollars_paid"] = d.get("dollars_paid", 0) + 1
        else:
            d["claims"][reward_id] = TODAY_KEY
            if r and r.get("bonus_minutes"):
                d["bonus_bank"] = d.get("bonus_bank", 0) + r["bonus_minutes"]
        d["history"].append({"reward": reward_id, "date": TODAY_KEY})

    if update(change):
        name = "$1" if reward_id == "dollar" else r["name"]
        st.session_state.flash = f"🎁 Reward given: {md_safe(name)}! Well done {STUDENT_NAME}!"


def claim_box(reward_id, button="Give reward 🎁"):
    pin_key = f"pin_{reward_id}"
    with st.form(f"claim_{reward_id}", border=False):
        c1, c2 = st.columns([2, 1])
        c1.text_input("Grown-up PIN to hand over the reward", type="password", key=pin_key)
        c2.write("")
        c2.form_submit_button(button, on_click=give_reward, args=(reward_id, pin_key))
    if st.session_state.pop(pin_key + "_bad", False):
        st.error("That PIN isn't right.")


STREAK_WORDS = {"speak": "🗣️ speaking", "bed": "🌙 bedtime", "sing": "🎤 singing"}

with tab_rewards:
    st.markdown("### 🏆 Big rewards")
    for r in REWARDS:
        s = reward_status(data, r, today)
        parts = [min(s["streak"], r["streak_len"]) / r["streak_len"]]
        parts += [min(s["counts"][t], n) / n for t, n in r["needs"].items()]
        pct = int(100 * sum(parts) / len(parts))
        with st.container(border=True):
            st.markdown(f'<div class="reward-head">{r["emoji"]} {html_safe(r["name"])}</div>'
                        f'<div class="how">{r["how"]}</div>', unsafe_allow_html=True)
            word = STREAK_WORDS.get(r["streak_task"], r["streak_task"])
            pills = [f'<span class="pill {"ok" if s["streak"] >= r["streak_len"] else ""}">'
                     f'{word} in a row {min(s["streak"], r["streak_len"])}/{r["streak_len"]}</span>']
            for tid, n in r["needs"].items():
                t = TASK_BY_ID[tid]
                pills.append(f'<span class="pill {"ok" if s["counts"][tid] >= n else ""}">'
                             f'{t["emoji"]} {tid} {min(s["counts"][tid], n)}/{n} days</span>')
            st.markdown("".join(pills), unsafe_allow_html=True)
            st.markdown(f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
                        unsafe_allow_html=True)
            if s["ok"]:
                st.success(f"🎉 UNLOCKED! {STUDENT_NAME} has earned: {md_safe(r['name'])}!")
                claim_box(r["id"], "Add to bank 🎶" if r.get("bonus_minutes") else "Give reward 🎁")
            elif s["streak"] == 0:
                st.caption("🌱 Start your streak today — every day counts!")

    with st.container(border=True):
        st.markdown(f'<div class="reward-head">💵 Earn a dollar</div>'
                    f'<div class="how">Every {STAR_DAYS_PER_DOLLAR} ⭐ star days (days you earn the full '
                    f'{DAILY_GOAL_MINUTES} minutes) = &#36;1. They don\'t have to be in a row.</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<span class="pill">⭐ {dollars["toward_next"]}/{STAR_DAYS_PER_DOLLAR} star days toward the next &#36;1</span>'
                    f'<span class="pill ok">💵 &#36;{dollars["paid"]} given so far</span>', unsafe_allow_html=True)
        pct = int(100 * dollars["toward_next"] / STAR_DAYS_PER_DOLLAR)
        st.markdown(f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
                    unsafe_allow_html=True)
        if dollars["owed"] > 0:
            st.success(f"🎉 {STUDENT_NAME} has earned \\${dollars['owed']} that hasn't been handed over yet!")
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
    mins_row = "".join(
        f"<td>{(task_minutes(done_on(data, d)) + data.get('bonus_used', {}).get(d.isoformat(), 0)) or ''}</td>"
        for d in days)
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
                if not t.get("auto"):
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

        st.markdown("#### 🎶 Bonus bank")
        st.write(f"{bank} minutes saved. Used today: {data.get('bonus_used', {}).get(TODAY_KEY, 0)} minutes.")

        st.markdown("#### 🎁 Rewards handed over")
        if data["history"]:
            for h in reversed(data["history"][-20:]):
                name = "$1" if h["reward"] == "dollar" else next(
                    (f"{r['emoji']} {r['name']}" for r in REWARDS if r["id"] == h["reward"]), h["reward"])
                st.markdown(f"• {date.fromisoformat(h['date']).strftime('%d %b %Y')} — {md_safe(name)}")
        else:
            st.caption("None yet.")

        with st.expander("⚠️ Reset everything"):
            confirm = st.checkbox(f"Yes, delete all of {STUDENT_NAME}'s progress")
            st.button("Reset all progress", on_click=reset_all, disabled=not confirm)

        if st.button("🔒 Lock"):
            st.session_state.parent_ok = False
            st.rerun()
