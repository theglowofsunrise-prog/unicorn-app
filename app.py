import base64
import html as htmllib
import json
import random
import re
import uuid
from datetime import date, datetime, timedelta
from fractions import Fraction
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import streamlit as st

# ============================ SETTINGS (edit these) ============================
STUDENT_NAME = "Andal"
LANGUAGE = "Tamil"             # the language she practises speaking
DAILY_GOAL_MINUTES = 30        # most screen time she can earn from tasks in one day
TIMEZONE = "Australia/Brisbane"
MATHS_TO_SOLVE = 3             # maths problems to solve to tick the maths task
TRIES_FOR_CLUE_1 = 2           # wrong tries before clue 1 appears
TRIES_FOR_CLUE_2 = 4           # wrong tries before clue 2 appears
TRIES_BEFORE_SKIP = 3          # wrong tries before she may swap to a different problem
MIN_STORY_WORDS = 50           # words a saved story needs to tick a writing task
WORD_CHALLENGE_USES = 3        # sentences / uses of the word of the day needed
WORD_CHALLENGE_MINUTES = 5     # screen-time minutes for completing the word challenge
WORD_SENTENCE_MIN_WORDS = 6    # each word-of-the-day sentence needs at least this many words
BIG_WHEEL_STREAK = 4           # star days in a row needed for a big-wheel spin
BIG_SPINS_PER_WEEK = 2         # most big-wheel spins per week (Mon–Sun)
CARROTS_FOR_SWAP = 30          # carrots needed to swap for screen time
CARROT_SWAP_MINUTES = 30
TOY_FUND_STEP = 10             # $ added to the toy fund per win
TOY_FUND_TARGET = 30           # $ needed before the toy shop trip
RESTAURANT_GAP_DAYS = 21       # days between restaurant dinners

# id: short code (don't change once she has progress)   minutes: screen time it earns
# required: True = must be done before ANY screen time unlocks that day
TASKS = [
    {"id": "homework", "emoji": "📒", "name": "Finish today's homework", "minutes": 10,
     "required": True, "section": "must"},
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

# Big rewards (streak goals).
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
    {"id": "singing", "emoji": "🎶", "name": "Singing star: +60 screen-time minutes", "streak_task": "sing",
     "streak_len": 30, "window": 30, "needs": {}, "bonus_minutes": 60,
     "how": "Practise singing 15 minutes every day for 30 days in a row. The minutes go into your balance."},
]
# Only these prizes are shown as a "sneak peek" — the rest stay a surprise until she spins.
SMALL_TEASERS = ["milkshake", "stickers"]
BIG_TEASERS = ["timezone", "movie_night"]
STAR_DAYS_PER_DOLLAR = 14      # a "star day" = she earned the full daily screen time

# Spin-the-wheel prizes. "auto" prizes are added straight away; the rest wait in "My prizes"
# until a grown-up marks them as done.
BIG_PRIZES = [
    {"id": "movie_night", "emoji": "🎬", "name": "Choose the family movie and watch it together"},
    {"id": "outing", "emoji": "🏞️", "name": "Pick a weekend outing (park, beach, library, bike ride)"},
    {"id": "gamenight", "emoji": "🎲", "name": "Family game night where I pick the game"},
    {"id": "bake", "emoji": "🧁", "name": "Bake or cook something special together"},
    {"id": "bubblebath", "emoji": "🛁", "name": "Bubble bath with extra bubbles"},
    {"id": "timezone", "emoji": "🕹️", "name": "30 minutes at Timezone"},
    {"id": "restaurant", "emoji": "🍽️", "name": "Choose my favourite restaurant for a family dinner",
     "rules": f"No Mexican restaurants! Only if at least {RESTAURANT_GAP_DAYS // 7} weeks have passed since "
              "our last family dinner at a restaurant."},
    {"id": "toyshop", "emoji": "🧸", "name": f"Toy shop trip: +${TOY_FUND_STEP} to my Toy Fund", "auto": "toy",
     "rules": f"Save up to ${TOY_FUND_TARGET}, then go toy shopping and choose toys within the budget!"},
    {"id": "bowling", "emoji": "🎳", "name": "Bowling and ice cream day (I choose the flavour!)"},
]
SMALL_PRIZES = [
    {"id": "dessert", "emoji": "🍨", "name": "Pick a healthy dessert for dinner (as agreed by my parent)"},
    {"id": "carmusic", "emoji": "🎵", "name": "Choose the music in the car for a day"},
    {"id": "cardgame", "emoji": "🃏", "name": "A quick card or board game with a grown-up"},
    {"id": "dinner", "emoji": "🍝", "name": "Choose dinner for one evening"},
    {"id": "breakfast", "emoji": "🥞", "name": "Choose breakfast for one morning"},
    {"id": "stickers", "emoji": "🦕", "name": "Fun stickers: animals, space, dinos, favourite characters"},
    {"id": "stationery", "emoji": "✏️", "name": "Special stationery, up to $5 value"},
    {"id": "milkshake", "emoji": "🥤", "name": "Make a special milkshake together"},
    {"id": "story", "emoji": "📚", "name": "Choose a bedtime story, even a funny or unusual one"},
    {"id": "parentgame", "emoji": "🎮", "name": "A parent joins my favourite game for 30 minutes"},
    {"id": "extra30", "emoji": "⏰", "name": "30 minutes extra screen time, added straight to my balance",
     "auto": "minutes"},
    {"id": "bedpass", "emoji": "🌙", "name": "30 minutes later bedtime on Friday (bedtime pass)",
     "rules": "Ask a grown-up to mark it done the morning after. That night still counts for your bedtime streak!"},
    {"id": "carrots", "emoji": "🥕", "name": "Earn 10 carrots!", "auto": "carrots",
     "rules": f"Collect {CARROTS_FOR_SWAP} carrots to swap for {CARROT_SWAP_MINUTES} minutes of screen time "
              "(a grown-up approves the swap)."},
]

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
WORDS_OF_THE_DAY = [   # roughly Year 6 / age-11 vocabulary
    ("meticulous", "showing great attention to detail; very careful and precise",
     "She was meticulous when copying the map, checking every line twice."),
    ("resilient", "able to recover quickly from difficulties", "The resilient seedling kept growing after the storm."),
    ("eloquent", "able to speak or write in a clear, powerful way", "His eloquent speech moved the whole audience."),
    ("ominous", "giving the feeling that something bad is about to happen", "Ominous clouds gathered over the hills."),
    ("benevolent", "kind and wanting to help others", "The benevolent queen opened her gardens to everyone."),
    ("tenacious", "holding on firmly; refusing to give up", "The tenacious puppy refused to let go of the rope."),
    ("serene", "calm, peaceful and untroubled", "The lake looked serene at sunrise."),
    ("conspicuous", "easy to notice; standing out", "Her bright yellow raincoat was conspicuous in the crowd."),
    ("reluctant", "unwilling or hesitant to do something", "Tom was reluctant to jump into the icy pool."),
    ("vibrant", "full of energy and life; bright and strong (colours)", "The market was bursting with vibrant colours."),
    ("ingenious", "clever, original and inventive", "She invented an ingenious way to reach the top shelf."),
    ("melancholy", "a deep, thoughtful sadness", "A melancholy tune drifted from the old piano."),
    ("exquisite", "extremely beautiful and delicate", "The butterfly's wings had an exquisite pattern."),
    ("diligent", "working hard and carefully", "The diligent student checked every answer."),
    ("audacious", "bold and willing to take risks", "The audacious explorer sailed into unknown waters."),
    ("perplexed", "confused and puzzled", "I was perplexed by the tricky riddle."),
    ("formidable", "impressive and powerful, sometimes a little frightening", "The castle walls were formidable."),
    ("luminous", "giving off light; glowing", "Luminous jellyfish lit up the dark sea."),
    ("compassionate", "feeling and showing care for others who are suffering",
     "The compassionate nurse held the scared child's hand."),
    ("inquisitive", "curious and eager to learn", "The inquisitive kitten explored every cupboard."),
    ("dilapidated", "old, broken and falling to pieces", "They tiptoed into the dilapidated old barn."),
    ("exuberant", "full of energy, excitement and cheerfulness", "The exuberant crowd cheered for the team."),
    ("tranquil", "quiet and peaceful", "We spent a tranquil afternoon by the river."),
    ("vigilant", "watchful and alert to danger", "The vigilant meerkat kept watch for eagles."),
    ("intrepid", "fearless and adventurous", "The intrepid climbers finally reached the summit."),
    ("spontaneous", "happening suddenly, without planning", "We had a spontaneous picnic in the park."),
    ("cascade", "to fall or pour down in large amounts, like a waterfall", "Her curls cascaded over her shoulders."),
    ("gregarious", "enjoying being with other people; sociable", "Our gregarious neighbour knows everyone on the street."),
    ("immaculate", "perfectly clean and tidy", "Her bedroom was immaculate after the big clean-up."),
    ("whimsical", "playful and fanciful in an unusual way", "The book had whimsical drawings of dancing teapots."),
    ("persevere", "to keep trying even when something is difficult", "If you persevere, you will master the piano piece."),
    ("magnanimous", "generous and forgiving, especially towards a rival",
     "The magnanimous winner shook hands with every player."),
    ("labyrinth", "a complicated maze of paths or passages", "The old library felt like a labyrinth of shelves."),
    ("nonchalant", "calm and relaxed, as if not worried at all", "He gave a nonchalant shrug and kept reading."),
    ("radiant", "shining brightly; glowing with happiness", "She gave a radiant smile when she saw the puppy."),
    ("predicament", "a difficult or awkward situation", "Locked out in the rain, we were in a real predicament."),
    ("jubilant", "feeling or showing great joy, especially after success", "The jubilant team lifted the trophy."),
    ("scrutinise", "to examine something very carefully", "The detective scrutinised every clue."),
    ("ethereal", "extremely light and delicate, almost magical", "An ethereal mist floated over the valley."),
    ("ambitious", "having a strong wish to succeed or do something big",
     "She has an ambitious plan to write a whole novel."),
]
FUN_FACTS = [
    "Rabbits' teeth never stop growing — that's why they love to chew! 🐰",
    "When a rabbit is super happy, it jumps and twists in the air. This is called a 'binky'! 🐇",
    "Rabbits can see almost all the way around them without turning their heads. 👀",
    "Baby rabbits are called kits. 🍼",
    "Happy rabbits sometimes 'purr' by gently rubbing their teeth together. 😊",
    "The unicorn is the national animal of Scotland! 🦄",
    "A rainbow is really a full circle — from the ground we only see half of it. 🌈",
    "Octopuses have three hearts! 🐙",
    "Honey never goes bad. Honey thousands of years old has been found in ancient Egyptian tombs! 🍯",
    "A group of flamingos is called a 'flamboyance'. 🦩",
    "Sea otters hold hands while they sleep so they don't drift apart. 🦦",
    "Butterflies taste with their feet! 🦋",
    "A day on Venus is longer than a whole year on Venus. 🪐",
    "Koalas can sleep up to 20 hours a day. 🐨",
    "Bananas are berries, but strawberries are not! 🍌",
    "Your heart beats about 100,000 times every day. ❤️",
    "A bolt of lightning is hotter than the surface of the Sun! ⚡",
    "Jupiter is so big that all the other planets could fit inside it. 🪐",
    "Hummingbirds are the only birds that can fly backwards. 🐦",
    "Dolphins sleep with one half of their brain at a time. 🐬",
    "Platypuses are mammals that lay eggs! 🥚",
    "Male seahorses are the ones who carry the babies. 🌊",
    "Some penguins give a pebble to the penguin they like best. 🐧",
    "Wombat poo is shaped like little cubes! 🟫",
    "Koalas have fingerprints that look almost exactly like human fingerprints. 🐨",
    "A kookaburra's call sounds just like someone laughing. 😂",
    "Saturn is so light for its size that it would float in a giant bathtub! 🛁",
    "Starfish don't have a brain. ⭐",
    "Owls can't move their eyes, so they turn their whole heads instead. 🦉",
    "Polar bears have black skin under their white fur. 🐻‍❄️",
    "A shrimp's heart is in its head! 🦐",
    "Sloths can hold their breath for up to 40 minutes underwater. 🦥",
    "The Eiffel Tower grows a little taller in summer because metal expands in the heat. 🗼",
    "Snails have thousands of tiny teeth. 🐌",
    "The Moon has 'moonquakes', a bit like earthquakes. 🌙",
    "Elephants can't jump. 🐘",
    "Cows have best friends and get stressed when they are apart. 🐄",
    "There is no sound in space because there's no air to carry it. 🚀",
]

MOODS = [
    ("happy", "😄", "Happy", "Yay! Happy bunnies hop the highest! 🐰"),
    ("excited", "🤩", "Excited", "Woohoo! Tell a grown-up what you're excited about!"),
    ("calm", "😌", "Calm", "Lovely and peaceful, like a bunny in the sunshine ☀️"),
    ("tired", "😴", "Tired", "Maybe a little rest and a glass of water will help 💧"),
    ("worried", "😟", "Worried", "Telling a grown-up what's worrying you can make it feel smaller 💗"),
    ("sad", "😢", "Sad", "It's okay to feel sad. A hug from a grown-up can really help 💗"),
    ("cross", "😠", "Cross", "Big feelings are okay. Try 3 slow, deep bunny breaths 🌬️"),
]

# Pet growth by total star days
PET_STAGES = [
    (0, "egg", "A magic egg", "Earn your first star day to help it hatch!"),
    (1, "hatching", "Hatching!", "Something is wriggling inside…"),
    (3, "baby", "Baby bunny", "So tiny and fluffy!"),
    (7, "little", "Little bunny", "Growing bigger every day!"),
    (15, "big", "Big bunny", "Strong and bouncy!"),
    (30, "beautiful", "Beautiful bunny", "The most beautiful bunny in the land!"),
    (60, "magical", "Magical rainbow bunny", "Shimmering with rainbow magic! ✨"),
]

# Dress-ups. stat = which number unlocks it (see compute_stats)
ACCESSORIES = [
    {"id": "bow", "slot": "head", "emoji": "🎀", "name": "Pink bow", "stat": "star_days", "need": 3,
     "how": "3 star days"},
    {"id": "flowers", "slot": "head", "emoji": "🌸", "name": "Flower crown", "stat": "star_days", "need": 7,
     "how": "7 star days"},
    {"id": "tophat", "slot": "head", "emoji": "🎩", "name": "Fancy top hat", "stat": "maths_solved", "need": 30,
     "how": "solve 30 maths problems"},
    {"id": "crown", "slot": "head", "emoji": "👑", "name": "Princess crown", "stat": "star_days", "need": 30,
     "how": "30 star days"},
    {"id": "horn", "slot": "head", "emoji": "🦄", "name": "Unicorn horn", "stat": "star_days", "need": 45,
     "how": "45 star days"},
    {"id": "wings", "slot": "back", "emoji": "🧚", "name": "Fairy wings", "stat": "max_speak_streak", "need": 7,
     "how": "a 7-day speaking streak"},
    {"id": "cape", "slot": "back", "emoji": "🌈", "name": "Rainbow cape", "stat": "star_days", "need": 20,
     "how": "20 star days"},
    {"id": "glasses", "slot": "face", "emoji": "🕶️", "name": "Cool sunglasses", "stat": "stories", "need": 3,
     "how": "write 3 stories"},
    {"id": "scarf", "slot": "neck", "emoji": "🧣", "name": "Cosy scarf", "stat": "max_bed_streak", "need": 7,
     "how": "7 bedtimes in a row"},
    {"id": "necklace", "slot": "neck", "emoji": "💎", "name": "Sparkly necklace", "stat": "homework_days",
     "need": 10, "how": "10 homework days"},
]
SLOT_NAMES = {"head": "🎀 Head", "back": "🧚 Back", "face": "🕶️ Face", "neck": "🧣 Neck"}

THEMES = [
    {"id": "rainbow", "name": "🌈 Rainbow", "need": 0},
    {"id": "candy", "name": "🍬 Candy", "need": 3},
    {"id": "ocean", "name": "🌊 Ocean", "need": 7},
    {"id": "hearts", "name": "💗 Love hearts", "need": 14},
    {"id": "galaxy", "name": "🌌 Galaxy", "need": 21},
    {"id": "unicorn", "name": "🦄 Unicorn dream", "need": 30},
]

# Badges: stat >= need. c1/c2 = medal colours
BADGES = [
    ("first_hop", "🌱", "First Hop", "Finish your very first task", "active_days", 1, "#d9fbe0", "#7fd99a"),
    ("first_star", "⭐", "First Star", "Earn your first star day", "star_days", 1, "#fff6c9", "#ffd23f"),
    ("homework_hero", "🦸", "Homework Hero", "Do homework on 10 days", "homework_days", 10, "#ffe0ec", "#ff7fb0"),
    ("week_talker", "🔥", "7-Day Talker", "Speak your language 7 days in a row", "max_speak_streak", 7,
     "#ffe7d1", "#ff9f43"),
    ("chatterbox", "🗣️", "Chatterbox", "Speak your language on 30 days", "speak_days", 30, "#ffe3f1", "#ff79b6"),
    ("star_collector", "🌟", "Star Collector", "Earn 10 star days", "star_days", 10, "#fff1c2", "#f5c400"),
    ("superstar", "💫", "Superstar", "Earn 30 star days", "star_days", 30, "#efe3ff", "#9b6bff"),
    ("maths_magician", "🪄", "Maths Magician", "Solve 25 maths problems", "maths_solved", 25, "#e0f2ff", "#38b6ff"),
    ("fraction_fairy", "🧚", "Fraction Fairy", "Solve 10 fraction problems", "fraction_solved", 10,
     "#fde2ff", "#d36bff"),
    ("decimal_dancer", "💃", "Decimal Dancer", "Solve 10 decimal problems", "decimal_solved", 10,
     "#ffe2e2", "#ff6b6b"),
    ("story_starter", "✏️", "Story Starter", "Save your first story", "stories", 1, "#e6f9ff", "#4cc9f0"),
    ("little_author", "📖", "Little Author", "Write 10 stories", "stories", 10, "#e9e4ff", "#7b61ff"),
    ("word_wizard", "💖", "Word Wizard", "Use the word of the day 3 times", "word_wins", 1, "#ffe0f0", "#ff4fa3"),
    ("bookworm", "🐛", "Bookworm Bunny", "Read on 15 days", "read_days", 15, "#e7ffd9", "#6cc644"),
    ("sleepy_star", "🌙", "Sleepy Star", "In bed on time 7 nights in a row", "max_bed_streak", 7,
     "#e6e6ff", "#6c63ff"),
    ("dream_keeper", "🦉", "Dream Keeper", "In bed on time 30 nights in a row", "max_bed_streak", 30,
     "#e3e0ff", "#4b3a99"),
    ("songbird", "🎤", "Little Songbird", "Sing on 7 days", "sing_days", 7, "#fff0d6", "#ffb347"),
    ("calm_cloud", "☁️", "Calm Cloud", "Sit still for 2 minutes 5 times", "sit2_days", 5, "#eef6ff", "#8ab6ff"),
    ("bouncy", "🤸", "Bouncy Bunny", "Exercise on 10 days", "exercise_days", 10, "#dcfff4", "#2ec4a6"),
    ("lucky", "🎡", "Lucky Spinner", "Spin a prize wheel", "spins", 1, "#fff3e0", "#ff8a3d"),
    ("feelings", "😊", "Feelings Friend", "Share your mood 5 times", "moods", 5, "#fffbe0", "#f2c200"),
    ("chalisa_start", "🙏", "Little Devotee", "Learn your first Chalisa part", "chalisa_parts", 1, "#fff0db", "#ff9933"),
    ("chalisa_champion", "📿", "Chalisa Champion", "Learn the whole Hanuman Chalisa", "chalisa_parts", 8, "#ffe6cc", "#e66b00"),
]
# ================================================================================

TASK_BY_ID = {t["id"]: t for t in TASKS}
PRIZE_BY_ID = {p["id"]: p for p in BIG_PRIZES + SMALL_PRIZES}


def md_safe(text) -> str:
    """Stop Streamlit reading text between two $ signs as a maths formula (plain markdown)."""
    return str(text).replace("$", "\\$")


def html_safe(text) -> str:
    """Escape text placed inside HTML snippets (also stops $…$ maths)."""
    return htmllib.escape(str(text)).replace("$", "&#36;")


st.set_page_config(page_title=f"{STUDENT_NAME} Earns Stars", page_icon="🦄", layout="centered")

# ============================ HANUMAN CHALISA ============================
# The Hanuman Chalisa (by Goswami Tulsidas, 16th century) has 2 opening dohas, 40 chaupais and
# 1 closing doha. Here it is split into 8 parts of about 6 lines (3 couplets) each.
BEADS_PER_PART = 5             # 📿 beads earned for each part learned by heart
BEADS_FOR_MINUTES = 20         # every 20 beads ...
BEAD_MINUTES = 30              # ... = 30 minutes of screen time (added automatically)
CHALISA_NEEDS_PIN = True       # True = a grown-up PIN is needed to submit each part (after hearing her recite)
CHALISA_PICTURES = ["Sri1.png", "HM1.png"]   # picture files in the repo, next to app.py (names are case-sensitive)
CHALISA_OUTINGS = [
    "🎬 Watch a movie at the cinema, then ice cream 🍦",
    "🎳 Go bowling, then ice cream 🍦",
    "🍽️ Dinner at my favourite restaurant, then ice cream 🍦",
]
CHALISA_PARTS = [
    {"title": "Opening prayer (Dohas) + verses 1–2", "lines": [
        "Sri Guru Charan Saroj Raj, Nij Mann Mukuru Sudhaari.",
        "Barnaun Raghuvar Bimal Jasu, Jo Daayaku Phal Chaari.",
        "Buddhiheen Tanu Janike, Sumiraun Pawan-Kumar.",
        "Bal Buddhi Vidya Dehu Mohi, Harahu Kalesh Bikaar.",
        "Jai Hanuman Gyan Gunn Sagar. Jai Kapees Tihun Lok Ujaagar.",
        "Ramdoot Atulit Baldhama. Anjani-Putra Pawansut Naama."],
     "meaning": "With my heart made clean by my Guru's blessing, I sing the glory of Lord Rama. Knowing I still have "
                "a lot to learn, I think of Hanuman, the Son of the Wind, and ask for strength, wisdom and knowledge, "
                "and for my troubles to go away. Victory to Hanuman, an ocean of wisdom and goodness! He is Rama's "
                "messenger, mightier than anyone, the son of Mother Anjani."},
    {"title": "Verses 3–8 · Hanuman the mighty hero", "lines": [
        "Mahaveer Vikram Bajrangi. Kumati Nivaar Sumati Ke Sangi.",
        "Kanchan Baran Biraj Subesa. Kaanan Kundal Kunchit Kesa.",
        "Haath Braj Au Dhwaja Biraaje. Kaandhe Moonj Janeu Saaje.",
        "Shankar Suvan Kesarinandan. Tej Prataap Maha Jag Vandan.",
        "Vidyavaan Guni Ati Chaatur. Ram Kaaj Karibe Ko Aatur.",
        "Prabhu Charitra Sunibe Ko Rasiya. Ram Lakhan Sita Mann Basiya."],
     "meaning": "Hanuman is a brave hero, strong as a thunderbolt. He chases away bad thoughts and stays close to good "
                "ones. He shines like gold, with earrings and curly hair, holding a mace and a flag. The whole world "
                "honours him. He is wise, kind and clever, always keen to help Rama, and he loves hearing Rama's "
                "stories. Rama, Lakshmana and Sita live in his heart."},
    {"title": "Verses 9–14 · Adventures for Lord Rama", "lines": [
        "Sukshma Roop Dhari Siyanhi Dikhawa. Bikat Roop Dhari Lanka Jarawa.",
        "Bheem Roop Dhari Asura Sanghare. Ramchandra Ke Kaaj Sanware.",
        "Laaye Sanjeevan Lakhana Jiyaaye. Sri Raghuveer Harashi Urr Laaye.",
        "Raghupati Keenhi Bahut Badai. Tum Mum Priya, Bhartahi Sum Bhai.",
        "Sahas Badan Tumharo Jas Gaave. Asa Kahi Sripati Kanth Lagaave.",
        "Sankaadik Brahmadi Munisa. Narad Sarad Sahit Aheesa."],
     "meaning": "Hanuman became tiny to visit Sita, and enormous to set Lanka on fire. In a mighty form he defeated "
                "the demons and finished Rama's work. He brought the Sanjeevani herb to save Lakshmana, and Rama "
                "hugged him with joy, saying: 'You are as dear to me as my brother Bharat!' Great sages, gods and "
                "even the thousand-headed serpent sing his praises."},
    {"title": "Verses 15–20 · Nothing is too hard", "lines": [
        "Jam Kuber Digpal Jahan Te. Kabi Kobid Kahi Sake Kahan Te.",
        "Tum Upkaar Sugreevahi Keenha. Ram Milaaye Raj-Pad Deenha.",
        "Tumharo Mantra Bibhishan Maana. Lankeshwar Bhaye Sab Jag Jaana.",
        "Yug Sahastra Jojan Par Bhanu. Leelyo Taahi Madhur Phal Jaanu.",
        "Prabhu Mudrika Meli Mukh Maahi. Jaladhi Laanghi Gaye Achraj Naahi.",
        "Durgam Kaaj Jagat Ke Jete. Sugam Anugrah Tumhare Tete."],
     "meaning": "Not even gods, poets or scholars can fully describe Hanuman's greatness. He helped Sugriva meet Rama "
                "and get his kingdom back, and Vibhishana followed his advice and became King of Lanka. As a baby, "
                "Hanuman tried to swallow the faraway Sun, thinking it was a sweet fruit! Holding Rama's ring in his "
                "mouth, he leapt across the ocean. With his blessing, every hard job becomes easy."},
    {"title": "Verses 21–26 · Our brave protector", "lines": [
        "Ram Duaare Tum Rakhvare. Hott Na Aagya Binu Paisare.",
        "Sab Sukh Lahe Tumhari Sarna. Tum Rakshak Kahu Ko Dar Na.",
        "Aapan Tej Samharo Aape. Teeno Lok Haank Te Kaampe.",
        "Bhoot Pishaach Nikat Nahi Aavein. Mahaveer Jab Naam Sunaave.",
        "Naase Rog Hare Sab Peera. Japat Nirantar Hanumat Beera.",
        "Sankat Te Hanuman Churave. Mann Kram Vachan Dhyaan Jo Laave."],
     "meaning": "Hanuman guards Rama's door. Everyone who comes to him finds happiness, and with him as our protector "
                "we don't need to be afraid of anything. Only he can hold his own amazing power, and the three worlds "
                "tremble when he roars. Bad things stay away when his name is said, and pain fades for those who keep "
                "remembering him. He rescues anyone who thinks of him with their mind, words and actions."},
    {"title": "Verses 27–32 · Glory through the ages", "lines": [
        "Sab Par Ram Tapasvi Raja. Tin Ke Kaaj Sakal Tum Saaja.",
        "Aur Manorath Jo Koi Laave. Soi Amit Jivan Phal Paave.",
        "Chaaron Yug Partap Tumhara. Hai Parsidh Jagat Ujiyara.",
        "Saadhu-Sant Ke Tum Rakhvare. Asur Nikandan Ram Dulaare.",
        "Ashta Siddhi Nau Nidhi Ke Daata. As Var Deen Janaki Mata.",
        "Ram Rasayan Tumhare Paasa. Sadaa Raho Raghupati Ke Daasa."],
     "meaning": "Rama is the greatest king, and Hanuman carried out all his work. Anyone who comes to Hanuman with a "
                "sincere wish receives its fruit. His glory shines through all four ages and lights up the world. He "
                "protects good people, defeats demons and is dearly loved by Rama. Mother Sita blessed him to give "
                "eight special powers and nine treasures. He holds devotion to Rama in his heart and is always Rama's "
                "humble helper."},
    {"title": "Verses 33–38 · Blessings for everyone", "lines": [
        "Tumhare Bhajan Ram Ko Paave. Janam Janam Ke Dukh Bisraave.",
        "Antkaal Raghuvar Pur Jaayi. Jahan Janam Hari-Bhakt Kahayi.",
        "Aur Devta Chitta Na Dharai. Hanumat Sei Sarva Sukh Karai.",
        "Sankat Kate, Mite Sab Peera. Jo Sumire Hanumat Balbeera.",
        "Jai Jai Jai Hanuman Gosain. Krupa Karahu Gurudev Ki Naai.",
        "Jo Sat Baar Paath Kar Koi. Chutahi Bandhi Maha Sukh Hoyi."],
     "meaning": "By singing Hanuman's praises, people reach Rama and forget old sorrows, and are remembered as Rama's "
                "devotees. Serving Hanuman brings every kind of comfort. Troubles end and pain goes away for those "
                "who remember mighty Hanuman. Victory, victory, victory to Hanuman! Please bless us like a kind "
                "teacher. Whoever recites this a hundred times becomes free and very happy."},
    {"title": "Verses 39–40 + closing Doha", "lines": [
        "Jo Yeh Padhe Hanuman Chalisa. Hoye Siddhi Saakhi Gaurisa.",
        "Tulsidas Sada Hari Chera. Keeje Nath Hriday Mah Dera.",
        "Pawan Tanay Sankat Haran, Mangal Murti Roop.",
        "Ram Lakhan Sita Sahit, Hriday Basahu Sur Bhoop."],
     "meaning": "Whoever reads the Hanuman Chalisa will succeed, and Lord Shiva himself is the witness. Tulsidas, who "
                "wrote it, says: 'I am always the Lord's servant. Please live in my heart.' O Son of the Wind, remover "
                "of troubles, full of blessings: please live in our hearts, together with Rama, Lakshmana and Sita."},
]
CHALISA_FACTS = [
    "The Hanuman Chalisa was written by the poet-saint Goswami Tulsidas about 450 years ago, in the 1500s. 🪶",
    "'Chalisa' comes from 'chalis', which means forty. It has 40 verses called chaupais! 🔢",
    "As well as the 40 chaupais, there are 2 short verses (dohas) at the start and 1 at the end. 📜",
    "It is written in Awadhi, an old form of Hindi spoken around the city of Ayodhya. 🗣️",
    "Tulsidas also wrote the Ramcharitmanas, a famous retelling of the Ramayana. 📖",
    "One verse says baby Hanuman tried to swallow the Sun, thinking it was a sweet fruit! ☀️🍑",
    "Some people like to multiply the numbers in that Sun verse (yug × sahasra × yojan) and get close to the real "
    "distance from the Earth to the Sun! 🌍☀️",
    "'Bajrangi' means someone whose body is as strong as a thunderbolt (vajra). ⚡",
    "Hanuman is called 'Pawan-putra', the Son of the Wind god, Vayu. 🌬️",
    "In the Ramayana, Hanuman couldn't tell which herb was Sanjeevani, so he carried the whole mountain! ⛰️",
    "Many families recite the Hanuman Chalisa on Tuesdays and Saturdays, the days linked with Hanuman. 📅",
    "Millions of people around the world know the Hanuman Chalisa by heart, and recordings of it have been played "
    "billions of times online. 🌏",
    "Hanuman is loved for being strong, brave, humble, and a loyal friend who always helps. 💪💖",
    "A prayer bead string (mala) usually has 108 beads, used to count prayers. 📿",
]
ICON_JOKES = {
    "unicorn": [
        "What do you call a unicorn with no horn? A horse! 🐴",
        "Fact: The unicorn is the national animal of Scotland! 🦄",
        "Fact: Narwhals are called 'unicorns of the sea'. Their horn is really a super-long tooth! 🐋",
        "Why don't unicorns get lost? They follow their horn-pass! 🧭",
        "What's a unicorn's favourite treat? Rainbow sprinkles, of course! 🍩",
    ],
    "bunny": [
        "How do bunnies keep fit? Hare-obics! 🤸",
        "Fact: A happy bunny jumps and twists in the air. It's called a 'binky'! 🐰",
        "What's a bunny's favourite music? Hip-hop! 🎵",
        "Fact: A rabbit's teeth never stop growing! 🦷",
        "Fact: Rabbits can turn their ears to listen in different directions. 👂",
        "Why are bunnies so lucky? They have four rabbit's feet! 🍀",
    ],
    "rainbow": [
        "Fact: A rainbow is really a full circle. From the ground we only see half! 🌈",
        "Fact: You can only see a rainbow when the Sun is behind you. ☀️",
        "Fact: In a double rainbow, the second one has its colours in reverse order! 🌈🌈",
        "Rainbow colours: Red, Orange, Yellow, Green, Blue, Indigo, Violet (ROYGBIV)! 🎨",
        "Why did the rainbow go to school? To get a little brighter! 🎓",
    ],
    "star": [
        "How do you throw a space party? You planet! 🪐",
        "Fact: Our Sun is a star! ☀️",
        "Fact: Stars twinkle because their light wobbles through Earth's air. ✨",
        "Fact: There are more stars in space than grains of sand on all Earth's beaches! 🏖️",
        "Why did the star go to school? To get brighter! ⭐",
    ],
}
ANIMATED_FRIENDS = True        # friendly characters cross the screen now and then (tap them!)
# Each friend: emoji, row (pixels from the bottom), seconds per full cycle, start delay, style, sound, sayings
FRIENDS = [
    {"id": "bunny", "emoji": "🐇", "bottom": 10, "cycle": 70, "delay": 4, "move": "hop", "sound": "boing", "says": [
        "Hop hop! I'm late for a carrot party! 🥕",
        "Boing! I'm practising my binky! 🐰",
        "Did you do your homework? I ate mine… it was a carrot! 🥕",
        "Catch me if you can! 🏃‍♀️",
        "I've got 99 carrots and I want one more! 🥕"]},
    {"id": "unicorn", "emoji": "🦄", "bottom": 70, "cycle": 95, "delay": 26, "move": "gallop", "sound": "sparkle", "says": [
        "Neigh-ver give up! 🦄",
        "I'm off to find the end of the rainbow! 🌈",
        "Sparkle mode: ON ✨",
        "My horn is for scratching itchy clouds! ☁️",
        "Have you earned your star today? ⭐"]},
    {"id": "koala", "emoji": "🐨", "bottom": 30, "cycle": 110, "delay": 50, "move": "waddle", "sound": "grunt", "says": [
        "G'day, mate! 🐨",
        "Shh… I need my 20-hour nap 😴",
        "Got any gum leaves? I'm starving! 🌿",
        "I'm not a bear, I'm a marsupial! 👶",
        "Walking is hard work… time for a snooze 💤"]},
    {"id": "parrot", "emoji": "🦜", "bottom": 140, "cycle": 85, "delay": 38, "move": "fly", "sound": "tweet", "says": [
        "Squawk! Pretty bird! 🦜",
        "Tweet tweet! Have you done your maths? 🔢",
        "I'm a rainbow of feathers! 🌈",
        "Polly wants a fun fact! 🧠",
        "Say Vanakkam! Va-nak-kam! 🙏"]},
    {"id": "kangaroo", "emoji": "🦘", "bottom": 14, "cycle": 120, "delay": 75, "move": "bound", "sound": "boing", "says": [
        "Boing! Boing! Kangaroos can't hop backwards very well! 🦘",
        "Want a ride in my pouch? 👜",
        "I can jump higher than a car! 🚗",
        "Hop to it, champ! 🏆"]},
    {"id": "butterfly", "emoji": "🦋", "bottom": 190, "cycle": 100, "delay": 62, "move": "flutter", "sound": "sparkle", "says": [
        "I taste with my feet! 👣",
        "I used to be a caterpillar! 🐛",
        "Flutter flutter… you're doing great! 💖",
        "My wings are like stained glass! 🌈"]},
]

# Days that should count as star days even though the rules were different back then
STAR_DAY_FIXES = ["2026-10-12"]
PARENT_AUTOLOCK_MINUTES = 5   # the Grown-ups tab locks itself after this long

# Bonus maths (optional): each correct answer = 1 carrot
EXTRA_MATHS_TOPICS = [
    ("fractions", "🍕 Fractions"),
    ("mult3", "✖️ Multiplying 3-digit numbers"),
    ("compare4", "⚖️ Comparing 4-digit numbers (<, >, =)"),
    ("add4", "➕ Adding 4-digit numbers"),
    ("sub4", "➖ Subtracting 4-digit numbers"),
    ("decimals", "🔟 Decimal adding & subtracting"),
    ("div3", "➗ Dividing up to 3-digit numbers"),
]
EXTRA_MATHS_CARROTS = 1        # carrots per correct bonus answer

# ============================ ENGLISH → TAMIL WORDS ============================
# Spoken Tamil written in English letters. Format: "english": ("tamil", "optional note")
# Grown-ups can add more words from the Grown-ups tab without editing this file.
TAMIL_WORDS = {
    "👪 Family & people": {
        "mother": ("amma", ""), "mum": ("amma", ""), "father": ("appa", ""), "dad": ("appa", ""),
        "grandmother": ("paati", "also 'aaya'"), "grandma": ("paati", ""), "grandfather": ("thaatha", ""),
        "grandpa": ("thaatha", ""), "elder sister": ("akka", ""), "younger sister": ("thangachi", "also 'thangai'"),
        "elder brother": ("anna", ""), "younger brother": ("thambi", ""),
        "sister": ("akka / thangachi", "akka = older sister, thangachi = younger sister"),
        "brother": ("anna / thambi", "anna = older brother, thambi = younger brother"),
        "uncle": ("maama", "mum's brother; dad's brothers are 'periyappa' (older) / 'chithappa' (younger)"),
        "aunt": ("athai", "dad's sister; mum's sisters are 'periyamma' (older) / 'chithi' (younger)"),
        "baby": ("kuzhandhai", "also 'paapaa'"), "child": ("kuzhandhai", ""), "family": ("kudumbam", ""),
        "friend": ("nanban", "a boy friend; a girl friend is 'thozhi'"), "son": ("magan", ""), "daughter": ("magal", ""),
        "boy": ("paiyan", ""), "girl": ("ponnu", "formal: 'penn'"), "teacher": ("aasiriyar", "kids often just say 'teacher'"),
        "student": ("maanavi", "a girl student; a boy is 'maanavan'"), "people": ("makkal", ""),
        "king": ("raja", "also 'arasan'"), "queen": ("raani", ""), "doctor": ("maruththuvar", "often just 'doctor'"),
    },
    "🧍 Body": {
        "head": ("thalai", ""), "hair": ("mudi", ""), "eye": ("kann", ""), "eyes": ("kangal", ""), "ear": ("kaadhu", ""),
        "nose": ("mooku", ""), "mouth": ("vaai", ""), "tooth": ("pal", ""), "teeth": ("pal", ""), "tongue": ("naakku", ""),
        "face": ("mugam", ""), "hand": ("kai", ""), "leg": ("kaal", ""), "foot": ("paadham", "also 'kaal'"),
        "finger": ("viral", ""), "nail": ("nagam", ""), "stomach": ("vayiru", ""), "tummy": ("vayiru", ""),
        "back": ("mudhugu", ""), "neck": ("kazhuththu", ""), "shoulder": ("thol", ""), "knee": ("muzhangaal", ""),
        "heart": ("idhayam", ""), "skin": ("thol", "sounds like 'shoulder' but is a different letter in Tamil"),
        "blood": ("ratham", ""), "body": ("udambu", ""),
    },
    "🏠 Home & things": {
        "house": ("veedu", ""), "home": ("veedu", ""), "door": ("kadhavu", ""), "window": ("jannal", ""),
        "room": ("arai", ""), "kitchen": ("samaiyal arai", ""), "bed": ("padukkai", "a cot/bed frame is 'kattil'"),
        "chair": ("naarkaali", ""), "table": ("mesai", ""), "floor": ("tharai", ""), "wall": ("suvar", ""),
        "roof": ("koorai", ""), "key": ("saavi", ""), "lamp": ("vilakku", ""), "light": ("velichcham", ""),
        "clock": ("kadigaaram", ""), "book": ("puththagam", ""), "bag": ("pai", ""), "cup": ("koppai", ""),
        "plate": ("thattu", ""), "spoon": ("karandi", ""), "bowl": ("kinnam", ""), "bucket": ("vaali", ""),
        "soap": ("sopu", ""), "towel": ("thundu", ""), "pillow": ("thalaiyanai", ""), "blanket": ("porvai", ""),
        "mirror": ("kannaadi", "also means 'glasses'"), "comb": ("seepu", ""), "clothes": ("thuni", "also 'udai'"),
        "shirt": ("sattai", ""), "skirt": ("paavaadai", ""), "umbrella": ("kudai", ""), "sandals": ("seruppu", ""),
        "box": ("petti", ""), "ball": ("pandhu", ""), "toy": ("bommai", ""), "doll": ("bommai", ""),
        "money": ("panam", "also 'kaasu'"), "car": ("car", "formal: 'mahizhundhu'"), "boat": ("padagu", ""),
    },
    "🍛 Food & drink": {
        "food": ("saapaadu", "formal: 'unavu'"), "rice": ("saadham", "uncooked rice is 'arisi'"),
        "water": ("thanni", "formal: 'neer'"), "milk": ("paal", ""), "yogurt": ("thayir", ""), "curd": ("thayir", ""),
        "butter": ("vennai", ""), "ghee": ("nei", ""), "sugar": ("sakkarai", ""), "salt": ("uppu", ""),
        "egg": ("muttai", ""), "fruit": ("pazham", ""), "apple": ("aappil", "often just 'apple'"), "orange": ("aaranju", ""),
        "bread": ("rotti", ""), "tea": ("tea", "formal: 'theneer'"), "banana": ("vaazhaippazham", ""), "mango": ("maampazham", ""),
        "grapes": ("thiraatchai", ""), "coconut": ("thengaai", ""), "lemon": ("elumichai", ""),
        "jackfruit": ("palaappazham", ""), "vegetable": ("kaaikari", ""), "tomato": ("thakkaali", ""),
        "onion": ("vengaayam", ""), "potato": ("urulaikizhangu", ""), "garlic": ("poondu", ""), "ginger": ("inji", ""),
        "chilli": ("milagaai", ""), "pepper": ("milagu", ""), "coffee": ("kaapi", ""), "sweet": ("inippu", ""),
        "honey": ("then", ""), "oil": ("ennai", ""), "chicken": ("kozhi", ""), "fish": ("meen", ""),
        "breakfast": ("kaalai saapaadu", "also 'tiffin'"), "lunch": ("madhiya saapaadu", ""),
        "dinner": ("iravu saapaadu", ""), "tasty": ("rusi", "'It's tasty' = 'rusiyaa irukku'"),
    },
    "🐾 Animals": {
        "dog": ("naai", ""), "cat": ("poonai", ""), "cow": ("pasu", "also 'maadu'"), "goat": ("aadu", ""),
        "horse": ("kudhirai", ""), "elephant": ("yaanai", ""), "lion": ("singam", ""), "tiger": ("puli", ""),
        "monkey": ("kurangu", ""), "bird": ("paravai", ""), "crow": ("kaakkaa", ""), "parrot": ("kili", ""),
        "peacock": ("mayil", ""), "hen": ("kozhi", ""), "duck": ("vaaththu", ""), "snake": ("paambu", ""),
        "frog": ("thavalai", ""), "rabbit": ("muyal", ""), "bunny": ("muyal", ""), "mouse": ("eli", ""), "rat": ("eli", ""),
        "squirrel": ("anil", ""), "ant": ("erumbu", ""), "butterfly": ("pattaampoochi", ""), "bee": ("theni", ""),
        "mosquito": ("kosu", ""), "deer": ("maan", ""), "bear": ("karadi", ""), "fox": ("nari", ""),
        "donkey": ("kazhudhai", ""), "camel": ("ottagam", ""), "owl": ("aandhai", ""), "spider": ("silandhi", ""),
        "turtle": ("aamai", ""), "crocodile": ("mudhalai", ""), "lizard": ("palli", ""), "eagle": ("kazhugu", ""),
        "insect": ("poochi", ""), "animal": ("vilangu", ""),
    },
    "🌈 Colours": {
        "red": ("sivappu", ""), "blue": ("neelam", ""), "green": ("pachai", ""), "yellow": ("manjal", ""),
        "white": ("vellai", ""), "black": ("karuppu", ""), "orange (colour)": ("aaranju niram", ""),
        "pink": ("ilanchivappu", "many people just say 'pink'"), "purple": ("oodhaa", ""),
        "brown": ("pazhuppu niram", ""), "grey": ("saambal niram", ""), "gold": ("thangam", ""), "colour": ("niram", ""),
    },
    "🔢 Numbers": {
        "zero": ("poojiyam", ""), "one": ("onnu", "formal: 'ondru'"), "two": ("rendu", "formal: 'irandu'"),
        "three": ("moonu", "formal: 'moondru'"), "four": ("naalu", "formal: 'naangu'"),
        "five": ("anju", "formal: 'aindhu'"), "six": ("aaru", ""), "seven": ("ezhu", ""), "eight": ("ettu", ""),
        "nine": ("onbadhu", ""), "ten": ("paththu", ""), "eleven": ("padhinonnu", ""), "twelve": ("pannendu", ""),
        "twenty": ("irubadhu", ""), "fifty": ("aimbadhu", ""), "hundred": ("nooru", ""), "thousand": ("aayiram", ""),
    },
    "📅 Days & time": {
        "sunday": ("nyaayiru", "Sunday = 'nyaayitru kizhamai'"), "monday": ("thingal", "+ 'kizhamai' = day"),
        "tuesday": ("sevvaai", ""), "wednesday": ("pudhan", ""), "thursday": ("vyaazhan", ""),
        "friday": ("velli", ""), "saturday": ("sani", ""), "day": ("naal", ""), "week": ("vaaram", ""),
        "month": ("maadham", ""), "year": ("varusham", ""), "today": ("innaikku", "formal: 'indru'"),
        "tomorrow": ("naalaikku", "formal: 'naalai'"), "yesterday": ("nethu", "formal: 'netru'"),
        "morning": ("kaalai", ""), "afternoon": ("madhiyam", ""), "evening": ("saayangaalam", ""),
        "night": ("raaththiri", "also 'iravu'"), "time": ("neram", ""), "now": ("ippo", ""), "later": ("appuram", ""),
    },
    "🌳 Nature": {
        "sun": ("sooriyan", ""), "moon": ("nilaa", ""), "star": ("natchaththiram", ""), "sky": ("vaanam", ""),
        "cloud": ("megam", ""), "rain": ("mazhai", ""), "wind": ("kaaththu", "formal: 'kaatru'"), "tree": ("maram", ""),
        "flower": ("poo", ""), "leaf": ("ilai", ""), "grass": ("pul", ""), "river": ("aaru", ""), "sea": ("kadal", ""),
        "mountain": ("malai", ""), "stone": ("kal", ""), "sand": ("manal", ""), "fire": ("neruppu", ""),
        "soil": ("mann", ""), "world": ("ulagam", ""), "rainbow": ("vaanavil", ""), "garden": ("thottam", ""),
        "forest": ("kaadu", ""), "street": ("theru", ""), "village": ("graamam", "also 'ooru'"),
    },
    "🏫 School": {
        "school": ("palli", "most people say 'school'"), "class": ("vagupu", ""), "homework": ("veettu paadam", ""),
        "lesson": ("paadam", ""), "letter": ("ezhuththu", "a letter of the alphabet"), "word": ("vaarththai", "also 'sol'"),
        "sentence": ("vaakkiyam", ""), "story": ("kadhai", ""), "song": ("paattu", ""), "game": ("vilaiyaattu", ""),
        "question": ("kelvi", ""), "answer": ("badhil", ""), "exam": ("thervu", "also 'pareetchai'"),
        "maths": ("kanakku", ""), "picture": ("padam", ""), "name": ("peyar", "spoken: 'per'"),
        "language": ("mozhi", ""), "tamil": ("thamizh", ""),
    },
    "✨ Describing words": {
        "big": ("periya", ""), "small": ("chinna", ""), "good": ("nalla", ""), "bad": ("ketta", ""),
        "hot": ("soodu", ""), "cold": ("kulir", "cold drink/water: 'jillunu'"), "happy": ("sandhosham", ""),
        "sad": ("varuththam", ""), "beautiful": ("azhagu", ""), "pretty": ("azhagu", ""), "new": ("pudhu", ""),
        "old": ("pazhaya", "for things; an old person is 'vayasaana'"), "fast": ("vegam", ""), "slow": ("medhuvaa", ""),
        "clean": ("suththam", ""), "dirty": ("azhukku", ""), "a lot": ("niraiya", ""), "a little": ("konjam", ""),
        "very": ("romba", ""), "heavy": ("ganamaa", ""), "tired": ("kalaippu", ""), "hungry": ("pasi", ""),
        "angry": ("kobam", ""), "scared": ("bayam", ""), "sour": ("pulippu", ""), "spicy": ("kaaram", ""),
        "bitter": ("kasappu", ""), "tall": ("uyaram", ""), "short": ("kuttai", ""),
    },
    "💬 Useful phrases": {
        "hello": ("vanakkam", ""), "thank you": ("nandri", ""), "yes": ("aamaa", ""), "no": ("illa", "formal: 'illai'"),
        "please": ("thayavu seydhu", ""), "sorry": ("mannichidunga", "formal: 'mannikkavum'"),
        "good morning": ("kaalai vanakkam", ""), "how are you": ("eppadi irukkeenga?", "to a friend: 'eppadi irukka?'"),
        "i am fine": ("naan nallaa irukken", ""), "what is your name": ("unga per enna?", ""),
        "my name is": ("en per …", "e.g. 'en per Andal'"), "come here": ("inga vaa", ""), "go there": ("anga po", ""),
        "let's play": ("vilaiyaadalaam", ""), "i am hungry": ("enakku pasikkudhu", ""),
        "i am thirsty": ("enakku thaagamaa irukku", ""), "give me water": ("thanni kudunga", ""),
        "i like it": ("enakku pidikkum", ""), "i don't know": ("theriyaadhu", ""), "i know": ("theriyum", ""),
        "very good": ("romba nalla", ""), "well done": ("shabaash", ""), "what": ("enna", ""), "where": ("enga", ""),
        "when": ("eppo", ""), "why": ("yen", ""), "who": ("yaaru", ""), "how": ("eppadi", ""), "how much": ("evvalavu", ""),
        "this": ("idhu", ""), "that": ("adhu", ""), "here": ("inga", ""), "there": ("anga", ""), "i": ("naan", ""),
        "you": ("nee", "polite: 'neenga'"), "he": ("avan", "polite: 'avar'"), "she": ("ava", "polite: 'avanga'"),
        "we": ("naanga", ""), "they": ("avanga", ""), "my": ("en", ""), "your": ("un", "polite: 'unga'"),
        "and": ("um", "added to the end of words, e.g. 'ammavum appavum'"), "see you later": ("appuram paakkalaam", ""),
        "good night": ("iniya iravu", "many families just say 'good night'"),
    },
}
TAMIL_TIPS = [
    "'zh' (as in thamizh, mazhai) is a special Tamil sound — curl your tongue back and say a soft 'l/r'. 👅",
    "'th' in Tamil words (like thanni, thambi) is soft, like the 'th' in 'the'. 🗣️",
    "Double letters (like paththu, kappal) mean you hold that sound a little longer. ⏱️",
    "Adding 'nga' makes words polite for elders: 'vaa' → 'vaanga' (please come). 🙏",
    "Add 'um' to join words: 'amma' + 'appa' → 'ammavum appavum' (mum and dad). 🔗",
]

# ============================ TAMIL DOING WORDS (VERBS) ============================
# (english, english past, english past participle, tamil command, I do/am doing, I did, I will, note)
# Spoken Tamil, "I" forms. The app builds the you/he/she/we/they forms from these automatically.
TAMIL_VERBS = [
    ("eat", "ate", "eaten", "saapidu", "saapidren", "saapten", "saapiduven", ""),
    ("drink", "drank", "drunk", "kudi", "kudikkiren", "kudichen", "kudippen", ""),
    ("sleep", "slept", "slept", "thoongu", "thoongaren", "thoonginen", "thoonguven", ""),
    ("walk", "walked", "walked", "nada", "nadakkiren", "nadandhen", "nadappen", ""),
    ("run", "ran", "run", "odu", "odaren", "odinen", "oduven", ""),
    ("come", "came", "come", "vaa", "varen", "vandhen", "varuven", ""),
    ("go", "went", "gone", "po", "poren", "ponen", "poven", ""),
    ("sit", "sat", "sat", "utkaaru", "utkaaren", "utkaandhen", "utkaaruven", ""),
    ("stand", "stood", "stood", "nillu", "nikkiren", "ninnen", "nippen", ""),
    ("play", "played", "played", "vilaiyaadu", "vilaiyaadaren", "vilaiyaadinen", "vilaiyaaduven", ""),
    ("read", "read", "read", "padi", "padikkiren", "padichen", "padippen", "'padi' also means study"),
    ("study", "studied", "studied", "padi", "padikkiren", "padichen", "padippen", ""),
    ("write", "wrote", "written", "ezhudhu", "ezhudharen", "ezhudhinen", "ezhudhuven", ""),
    ("speak", "spoke", "spoken", "pesu", "pesaren", "pesinen", "pesuven", ""),
    ("talk", "talked", "talked", "pesu", "pesaren", "pesinen", "pesuven", ""),
    ("listen", "listened", "listened", "kelu", "kekkiren", "ketten", "keppen", "the same word means 'ask'"),
    ("ask", "asked", "asked", "kelu", "kekkiren", "ketten", "keppen", "the same word means 'listen'"),
    ("see", "saw", "seen", "paaru", "paakkiren", "paaththen", "paappen", ""),
    ("look", "looked", "looked", "paaru", "paakkiren", "paaththen", "paappen", ""),
    ("watch", "watched", "watched", "paaru", "paakkiren", "paaththen", "paappen", "watch TV = 'TV paaru'"),
    ("give", "gave", "given", "kodu", "kudukkiren", "kuduththen", "kuduppen", ""),
    ("take", "took", "taken", "edu", "edukkiren", "eduththen", "eduppen", ""),
    ("open", "opened", "opened", "thira", "thirakkiren", "thirandhen", "thirappen", ""),
    ("close", "closed", "closed", "moodu", "moodaren", "moodinen", "mooduven", ""),
    ("wash", "washed", "washed", "kazhuvu", "kazhuvaren", "kazhuvinen", "kazhuvuven", "wash clothes = 'thuni thovai'"),
    ("cook", "cooked", "cooked", "samai", "samaikkiren", "samaichen", "samaippen", ""),
    ("sing", "sang", "sung", "paadu", "paadaren", "paadinen", "paaduven", ""),
    ("dance", "danced", "danced", "aadu", "aadaren", "aadinen", "aaduven", ""),
    ("jump", "jumped", "jumped", "kudhi", "kudhikkiren", "kudhichen", "kudhippen", ""),
    ("laugh", "laughed", "laughed", "siri", "sirikkiren", "sirichen", "sirippen", "also means 'smile'"),
    ("smile", "smiled", "smiled", "siri", "sirikkiren", "sirichen", "sirippen", ""),
    ("cry", "cried", "cried", "azhu", "azharen", "azhudhen", "azhuven", ""),
    ("wait", "waited", "waited", "kaaththiru", "kaaththirukkiren", "kaaththirundhen", "kaaththiruppen",
     "quick 'wait!' = 'iru!'"),
    ("buy", "bought", "bought", "vaangu", "vaangaren", "vaanginen", "vaanguven", ""),
    ("think", "thought", "thought", "yosi", "yosikkiren", "yosichen", "yosippen", ""),
    ("swim", "swam", "swum", "neendhu", "neendharen", "neendhinen", "neendhuven", ""),
    ("draw", "drew", "drawn", "padam varai", "padam varaiyaren", "padam varainjen", "padam varaiven", ""),
    ("climb", "climbed", "climbed", "eru", "eraren", "erinen", "eruven", ""),
    ("learn", "learned", "learned", "kaththukko", "kaththukkaren", "kaththukitten", "kaththukkuven", ""),
    ("teach", "taught", "taught", "sollikudu", "sollikudukkiren", "sollikuduththen", "sollikuduppen", ""),
    ("bathe", "bathed", "bathed", "kuli", "kulikkiren", "kulichen", "kulippen", "have a bath/shower"),
    ("help", "helped", "helped", "udhavi pannu", "udhavi panren", "udhavi pannen", "udhavi pannuven", ""),
    ("do", "did", "done", "pannu", "panren", "pannen", "pannuven", "formal: 'sei'"),
    ("make", "made", "made", "pannu", "panren", "pannen", "pannuven", "make food = 'samai'"),
    ("say", "said", "said", "sollu", "solren", "sonnen", "solluven", ""),
    ("tell", "told", "told", "sollu", "solren", "sonnen", "solluven", ""),
    ("call", "called", "called", "koopidu", "koopidren", "koopten", "koopiduven", ""),
    ("catch", "caught", "caught", "pudi", "pudikkiren", "pudichen", "pudippen", "also 'hold'"),
    ("hold", "held", "held", "pudi", "pudikkiren", "pudichen", "pudippen", ""),
    ("throw", "threw", "thrown", "veesu", "veesaren", "veesinen", "veesuven", ""),
    ("push", "pushed", "pushed", "thallu", "thallaren", "thallinen", "thalluven", ""),
    ("pull", "pulled", "pulled", "izhu", "izhukkiren", "izhuththen", "izhuppen", ""),
    ("cut", "cut", "cut", "vettu", "vettaren", "vettinen", "vettuven", ""),
    ("break", "broke", "broken", "udai", "udaikkiren", "udaichen", "udaippen", ""),
    ("fall", "fell", "fallen", "vizhu", "vizharen", "vizhundhen", "vizhuven", ""),
    ("carry", "carried", "carried", "thookku", "thookkaren", "thookkinen", "thookkuven", "also 'lift'"),
    ("lift", "lifted", "lifted", "thookku", "thookkaren", "thookkinen", "thookkuven", ""),
    ("search", "searched", "searched", "thedu", "thedaren", "thedinen", "theduven", ""),
    ("find", "found", "found", "kandupudi", "kandupudikkiren", "kandupudichen", "kandupudippen", ""),
    ("lose", "lost", "lost", "tholai", "tholaikkiren", "tholaichen", "tholaippen", "lose a thing"),
    ("forget", "forgot", "forgotten", "maranthudu", "marakkiren", "maranthutten", "maranthuduven",
     "'Don't forget!' = 'marakkaadhe!'"),
    ("wake up", "woke up", "woken up", "ezhundhiru", "ezhundhirikkiren", "ezhundhen", "ezhundhirippen", ""),
    ("get up", "got up", "got up", "ezhundhiru", "ezhundhirikkiren", "ezhundhen", "ezhundhirippen", ""),
    ("brush teeth", "brushed teeth", "brushed teeth", "pal theyi", "pal theykkiren", "pal theychen", "pal theyppen", ""),
    ("wear", "wore", "worn", "podu", "poduren", "potten", "poduven", "e.g. 'sattai podu' = put on a shirt"),
    ("put", "put", "put", "vai", "vaikkiren", "vechen", "vaippen", ""),
    ("clean", "cleaned", "cleaned", "suththam pannu", "suththam panren", "suththam pannen", "suththam pannuven", ""),
    ("finish", "finished", "finished", "mudi", "mudikkiren", "mudichen", "mudippen", "'It's finished' = 'mudinjudhu'"),
    ("start", "started", "started", "aarambi", "aarambikkiren", "aarambichen", "aarambippen", ""),
    ("begin", "began", "begun", "aarambi", "aarambikkiren", "aarambichen", "aarambippen", ""),
    ("stop", "stopped", "stopped", "niruththu", "niruththaren", "niruththinen", "niruththuven", ""),
    ("win", "won", "won", "jeyi", "jeyikkiren", "jeyichen", "jeyippen", ""),
    ("fly", "flew", "flown", "para", "parakkiren", "parandhen", "parappen", ""),
    ("ride", "rode", "ridden", "ottu", "ottaren", "ottinen", "ottuven", "ride a bike = 'cycle ottu'"),
    ("drive", "drove", "driven", "ottu", "ottaren", "ottinen", "ottuven", ""),
    ("show", "showed", "shown", "kaattu", "kaattaren", "kaattinen", "kaattuven", ""),
    ("send", "sent", "sent", "anuppu", "anupparen", "anuppinen", "anuppuven", ""),
    ("bring", "brought", "brought", "kondu vaa", "kondu varen", "kondu vandhen", "kondu varuven", ""),
    ("count", "counted", "counted", "ennu", "ennaren", "enninen", "ennuven", ""),
    ("hug", "hugged", "hugged", "katti pudi", "katti pudikkiren", "katti pudichen", "katti pudippen", ""),
    ("kiss", "kissed", "kissed", "muththam kodu", "muththam kudukkiren", "muththam kuduththen", "muththam kuduppen", ""),
    ("stay", "stayed", "stayed", "iru", "irukken", "irundhen", "iruppen", "also means 'be'"),
    ("fight", "fought", "fought", "sandai podu", "sandai poduren", "sandai potten", "sandai poduven", ""),
    ("shout", "shouted", "shouted", "kaththu", "kaththaren", "kaththinen", "kaththuven", ""),
    ("hide", "hid", "hidden", "olinjukko", "olinjukkaren", "olinjukitten", "olinjukkuven", "hide yourself"),
    ("sell", "sold", "sold", "vil", "vikkiren", "vitthen", "vippen", ""),
    ("tie", "tied", "tied", "kattu", "kattaren", "kattinen", "kattuven", ""),
    ("fill", "filled", "filled", "nirappu", "nirapparen", "nirappinen", "nirappuven", ""),
    ("pour", "poured", "poured", "oothu", "oothaaren", "oothinen", "oothuven", ""),
    ("touch", "touched", "touched", "thodu", "thodaren", "thotten", "thoduven", ""),
    ("grow", "grew", "grown", "valar", "valaren", "valarndhen", "valaruven", ""),
    ("change", "changed", "changed", "maaththu", "maaththaren", "maaththinen", "maaththuven", ""),
    ("kick", "kicked", "kicked", "udhai", "udhaikkiren", "udhaichen", "udhaippen", ""),
    ("bite", "bit", "bitten", "kadi", "kadikkiren", "kadichen", "kadippen", ""),
    ("blow", "blew", "blown", "oodhu", "oodharen", "oodhinen", "oodhuven", "blow candles = 'mezhuguvarththi oodhu'"),
    ("turn", "turned", "turned", "thiruppu", "thirupparen", "thiruppinen", "thiruppuven", ""),
    ("dig", "dug", "dug", "thondu", "thondaren", "thondinen", "thonduven", ""),
    ("lie down", "lay down", "lain down", "padu", "padukkiren", "paduththen", "paduppen", ""),
    ("try", "tried", "tried", "try pannu", "try panren", "try pannen", "try pannuven", "formal: 'muyarchi pannu'"),
    ("pray", "prayed", "prayed", "kumbidu", "kumbidren", "kumbitten", "kumbiduven", "also 'saami kumbidu'"),
    ("practise", "practised", "practised", "practice pannu", "practice panren", "practice pannen", "practice pannuven",
     "formal: 'payirchi sei'"),
    ("tidy", "tidied", "tidied", "olungaa vai", "olungaa vaikkiren", "olungaa vechen", "olungaa vaippen", "put things neatly"),
    ("share", "shared", "shared", "share pannu", "share panren", "share pannen", "share pannuven", "formal: 'pagirndhu kodu'"),
    ("pack", "packed", "packed", "pack pannu", "pack panren", "pack pannen", "pack pannuven", ""),
    ("visit", "visited", "visited", "paakka po", "paakka poren", "paakka ponen", "paakka poven",
     "e.g. 'paatti-a paakka poren' = I'm going to visit grandma"),
    ("live", "lived", "lived", "vaazhu", "vaazhaaren", "vaazhndhen", "vaazhuven", "where I live = 'naan irukkira idam'"),
    ("feed", "fed", "fed", "saapadu kodu", "saapadu kudukkiren", "saapadu kuduththen", "saapadu kuduppen", ""),
    ("fold", "folded", "folded", "madi", "madikkiren", "madichen", "madippen", ""),
    ("paint", "painted", "painted", "colour adi", "colour adikkiren", "colour adichen", "colour adippen", ""),
    ("spill", "spilled", "spilled", "kottu", "kottaren", "kottinen", "kottuven", ""),
    ("borrow", "borrowed", "borrowed", "kadan vaangu", "kadan vaangaren", "kadan vaanginen", "kadan vaanguven", ""),
    ("hurry", "hurried", "hurried", "seekiram pannu", "seekiram panren", "seekiram pannen", "seekiram pannuven",
     "'Hurry up!' = 'seekiram!'"),
]
# Feeling verbs work differently in Tamil ("to me it is …"), so they get their own simple card.
TAMIL_SPECIAL_VERBS = [
    ("know", "knew", "known", "enakku theriyum", "enakku therinjudhu", "enakku theriyum",
     "'I don't know' = 'enakku theriyaadhu'"),
    ("like", "liked", "liked", "enakku pidikkum", "enakku pidichudhu", "enakku pidikkum",
     "'I don't like it' = 'enakku pidikkaadhu'"),
    ("want", "wanted", "wanted", "enakku venum", "enakku venum-nu irundhudhu", "enakku venum",
     "'I don't want' = 'enakku venaam'"),
    ("understand", "understood", "understood", "enakku puriyudhu", "enakku purinjudhu", "enakku puriyum",
     "'I don't understand' = 'enakku puriyala'"),
    ("remember", "remembered", "remembered", "enakku nyaabagam irukku", "enakku nyaabagam vandhudhu",
     "enakku nyaabagam irukkum", ""),
    ("feel hungry", "felt hungry", "felt hungry", "enakku pasikkudhu", "enakku pasichudhu", "enakku pasikkum", ""),
    ("feel sleepy", "felt sleepy", "felt sleepy", "enakku thookkam varudhu", "enakku thookkam vandhudhu",
     "enakku thookkam varum", ""),
    ("hurt", "hurt", "hurt", "valikkudhu", "valichudhu", "valikkum", "'My leg hurts' = 'kaal valikkudhu'"),
]
PRONOUNS = [("I", "naan", "en"), ("you", "nee", "a"), ("he", "avan", "aan"), ("she", "ava", "aa"),
            ("we", "naanga", "om"), ("they / polite you", "avanga", "aanga")]

TAMIL_WORDS.update({
    "🧩 Describing words from verbs": {
        "broken": ("udainja", "e.g. 'udainja bommai' = broken toy"), "cooked": ("samaicha", ""),
        "boiled": ("kodhicha", "boiled water = 'kodhicha thanni'"), "frozen": ("urainja", ""),
        "lost": ("tholanja", "a lost toy = 'tholanja bommai'"), "washed": ("thovaicha", "for clothes"),
        "fallen": ("vizhundha", ""), "written": ("ezhudhina", ""), "spoken": ("pesina", ""),
        "closed": ("moodina", ""), "opened": ("thirandha", ""), "burnt": ("karinja", ""), "torn": ("kizhinja", ""),
        "dried": ("kaanja", ""), "wet": ("nanainja", ""), "folded": ("madicha", ""), "fried": ("poricha", ""),
        "grown": ("valarndha", ""), "finished": ("mudinja", ""), "started": ("aarambicha", ""),
        "filled": ("nirambina", ""), "painted": ("colour adicha", ""), "tied": ("kattina", ""),
        "bought": ("vaangina", "e.g. 'vaangina dress' = the dress I bought"), "sleeping": ("thoongara", ""),
        "running": ("odara", ""), "crying": ("azhara", "e.g. 'azhara paapaa' = crying baby"),
        "smiling": ("sirikkira", ""), "flying": ("parakkira", ""), "boiling": ("kodhikkira", ""),
        "shining": ("minnara", ""), "melting": ("urugara", ""), "spinning": ("sutthara", ""),
        "tired": ("kalaippaana", "'I'm tired' = 'kalaippaa irukku'"),
        "excited": ("aarvamaana", "'I'm excited!' = 'romba aarvamaa irukku!'"),
        "scared": ("bayandha", "'I'm scared' = 'bayamaa irukku'"),
        "surprised": ("aachariyamaana", ""), "bored": ("bore adikkira", "'I'm bored' = 'bore adikkudhu'"),
        "interesting": ("suvaarasyamaana", ""), "amazing": ("arumaiyaana", "also 'super'"),
        "boring": ("bore-aana", ""), "loving": ("anbaana", ""), "caring": ("akkaraiyaana", ""),
        "missing": ("kaanaama pona", "something you can't find"), "worried": ("kavalaiyaana", ""),
    },
    "😊 Feelings & health": {
        "feelings": ("unarvugal", ""), "fun": ("jolly", "also 'sandhosham'"), "love": ("anbu", "also 'paasam'"),
        "proud": ("perumai", ""), "shy": ("vetkam", ""), "jealous": ("poraamai", ""), "worry": ("kavalai", ""),
        "surprise": ("aachariyam", ""), "calm": ("amaidhi", ""), "brave": ("dhairiyam", ""), "fear": ("bayam", ""),
        "lonely": ("thanimai", ""), "pain": ("vali", ""), "sick": ("udambu sariyilla", "'I'm sick' = 'enakku udambu sariyilla'"),
        "fever": ("kaaychal", ""), "cough": ("irumal", ""), "a cold": ("jaladhosham", ""), "headache": ("thalai vali", ""),
        "stomach ache": ("vayiru vali", ""), "medicine": ("marundhu", ""), "hospital": ("aaspathiri", ""),
        "injury": ("adi", "'I got hurt' = 'adi pattudhu'"), "sleepy": ("thookkam", ""), "thirsty": ("thaagam", ""),
    },
    "🎒 School & stationery": {
        "pencil": ("pencil", ""), "eraser": ("rubber", ""), "ruler": ("scale", ""), "notebook": ("notebook", "formal: 'kuripedu'"),
        "paper": ("kaagidham", "also 'paper'"), "scissors": ("kaththarikkol", ""), "glue": ("pasai", ""),
        "blackboard": ("karumbalagai", ""), "bell": ("mani", ""), "playground": ("vilaiyaattu maidhaanam", ""),
        "library": ("noolagam", ""), "prize": ("parisu", ""), "holiday": ("vidumurai", "also 'leave'"),
        "bus": ("bus", "formal: 'perundhu'"), "lunchbox": ("tiffin box", ""), "uniform": ("seerudai", "also 'uniform'"),
        "marks": ("madhippen", "kids say 'mark'"), "friendship": ("natpu", ""),
    },
    "👗 Clothes & getting ready": {
        "dress": ("frock", "also 'gown'"), "socks": ("socks", ""), "shoes": ("shoe", ""), "hat": ("thoppi", ""),
        "glasses": ("kannaadi", ""), "bangles": ("valaiyal", ""), "earrings": ("kammal", ""), "necklace": ("maalai", "also 'chain'"),
        "bindi": ("pottu", ""), "saree": ("pudavai", "also 'saree'"), "ribbon": ("ribbon", ""), "pocket": ("pai", "also 'pocket'"),
        "button": ("button", ""), "jacket": ("jacket", ""), "pyjamas": ("night dress", ""),
    },
    "🏡 More at home": {
        "stove": ("aduppu", ""), "pot": ("paanai", ""), "knife": ("kaththi", ""), "glass (cup)": ("tumbler", ""),
        "rubbish": ("kuppai", ""), "bin": ("kuppai thotti", ""), "broom": ("vilakkumaaru", ""), "stairs": ("padi", ""),
        "entrance": ("vaasal", ""), "toilet": ("toilet", "formal: 'kazhivarai'"), "bathroom": ("bathroom", ""),
        "photo": ("photo", "formal: 'pugaipadam'"), "god's room / prayer room": ("saami arai", ""),
        "rangoli / kolam": ("kolam", ""), "swing": ("oonjal", ""), "garden plant": ("chedi", ""), "pet": ("chella praani", ""),
    },
    "📍 Places": {
        "shop": ("kadai", ""), "market": ("sandhai", "also 'market'"), "temple": ("kovil", ""), "park": ("poonga", "also 'park'"),
        "beach": ("kadarkarai", "also 'beach'"), "city": ("nagaram", ""), "country": ("naadu", ""), "india": ("Indhiyaa", ""),
        "hometown": ("ooru", ""), "bridge": ("paalam", ""), "zoo": ("mirugakkaatchi saalai", "kids say 'zoo'"),
        "house of grandparents": ("paatti veedu", ""), "airport": ("vimaana nilaiyam", "also 'airport'"),
        "aeroplane": ("vimaanam", "also 'flight'"), "train": ("rayil", ""), "bicycle": ("cycle", ""),
    },
    "🍛 More food": {
        "idli": ("idli", ""), "dosa": ("dosai", ""), "sambar": ("saambaar", ""), "rasam": ("rasam", ""),
        "chutney": ("chutney", ""), "curry": ("kuzhambu", "dry vegetable dish = 'poriyal'"), "pickle": ("oorugaai", ""),
        "sweets": ("inippu", "also 'sweet'"), "laddu": ("laddu", ""), "payasam": ("paayasam", ""),
        "ice cream": ("ice cream", ""), "chocolate": ("chocolate", ""), "cake": ("cake", ""), "juice": ("juice", ""),
        "snacks": ("thinpandam", "kids say 'snacks'"), "lentils": ("paruppu", ""), "spinach": ("keerai", ""),
        "peanuts": ("verkadalai", ""), "cucumber": ("vellarikkaai", ""), "pumpkin": ("poosanikkaai", ""),
        "brinjal": ("kaththarikkaai", ""), "beans": ("beans", ""), "corn": ("cholam", ""), "papaya": ("pappaali", ""),
        "pomegranate": ("maadhulai", ""), "guava": ("koyyaa", ""), "watermelon": ("tharpoosani", ""),
        "strawberry": ("strawberry", ""), "pineapple": ("annaasi", ""),
    },
    "🦘 More animals": {
        "puppy": ("naaikutti", ""), "kitten": ("poonaikutti", ""), "calf": ("kannukutti", ""), "chick": ("kozhikunju", ""),
        "lamb": ("aattukutti", ""), "nest": ("koodu", ""), "feather": ("iragu", "also means 'wing'"), "tail": ("vaal", ""),
        "horn": ("kombu", ""), "sparrow": ("kuruvi", ""), "pigeon": ("puraa", ""), "bat": ("vavvaal", ""),
        "whale": ("thimingalam", ""), "dolphin": ("dolphin", "formal: 'oongil'"), "shark": ("sura", ""),
        "cockroach": ("karappaan poochi", ""), "worm": ("puzhu", ""), "snail": ("naththai", ""), "kangaroo": ("kangaroo", ""),
        "koala": ("koala", ""), "penguin": ("penguin", ""), "zebra": ("varikkudhirai", ""), "giraffe": ("ottagachivingi", ""),
    },
    "🌍 More nature & weather": {
        "earth": ("bhoomi", ""), "planet": ("graham", ""), "wave": ("alai", ""), "island": ("theevu", ""),
        "lake": ("yeri", ""), "pond": ("kulam", ""), "well": ("kinaru", ""), "seed": ("vidhai", ""), "root": ("ver", ""),
        "branch": ("kilai", ""), "rock": ("paarai", ""), "ice": ("ice", "also 'panikkatti'"), "smoke": ("pugai", ""),
        "shadow": ("nizhal", ""), "sunshine": ("veyil", ""), "summer": ("kodaikaalam", ""), "winter": ("kulirkaalam", ""),
        "storm": ("puyal", ""), "thunder": ("idi", ""), "lightning": ("minnal", ""), "fog": ("pani", "also dew/snow"),
    },
    "🧭 Where & when": {
        "up": ("mela", ""), "down": ("keezha", ""), "inside": ("ulla", ""), "outside": ("veliya", ""),
        "near": ("pakkaththula", "also 'next to'"), "far": ("dhooram", ""), "front": ("munnaadi", "also 'before'"),
        "behind": ("pinnaadi", ""), "left": ("idadhu", ""), "right (side)": ("valadhu", ""), "middle": ("naduvula", ""),
        "always": ("eppavum", ""), "sometimes": ("sila neram", ""), "never": ("eppavume illa", ""), "again": ("thirumba", ""),
        "soon": ("seekiram", "also 'quickly' / 'early'"), "late": ("lettu", "formal: 'thaamadham'"), "first": ("mudhal", ""),
        "last": ("kadaisi", ""), "after": ("appuram", ""), "before": ("munnaadi", ""), "together": ("onnaa", "also 'serndhu'"),
        "alone": ("thaniyaa", ""), "everyone": ("ellaarum", ""), "everything": ("ellaam", ""), "nothing": ("onnum illa", ""),
        "something": ("edhaavadhu", ""), "but": ("aanaa", ""), "because": ("yennaa", ""), "so": ("adhanaala", ""),
        "or": ("illa", "also 'alladhu'"), "also": ("kooda", ""), "only": ("mattum", ""),
    },
    "🔁 Opposites": {
        "full": ("niraiya", ""), "empty": ("kaali", ""), "light (weight)": ("lesaa", ""), "dark": ("iruttu", ""),
        "bright": ("velichchamaa", ""), "loud": ("saththamaa", ""), "quiet": ("amaidhiyaa", ""), "soft": ("medhuvaana", ""),
        "hard": ("kadinamaana", ""), "easy": ("sulabam", ""), "difficult": ("kashtam", ""), "right (correct)": ("sari", ""),
        "wrong": ("thappu", ""), "true": ("unmai", ""), "lie": ("poi", ""), "same": ("ore maadhiri", ""),
        "different": ("vera", ""), "rich": ("panakkaaran", ""), "poor": ("ezhai", ""), "dry": ("kaanja", ""),
        "sharp": ("koormaiyaana", ""), "round": ("vattamaana", ""), "long": ("neelamaana", ""), "thick": ("thadimana", ""),
        "thin": ("olliyaana", ""), "strong": ("balamaana", ""), "weak": ("balaveenamaana", ""), "young": ("chinna vayasu", ""),
    },
    "🔢 More numbers": {
        "thirteen": ("padhimoonu", ""), "fourteen": ("padhinaalu", ""), "fifteen": ("padhinanju", ""),
        "sixteen": ("padhinaaru", ""), "seventeen": ("padhinezhu", ""), "eighteen": ("padhinettu", ""),
        "nineteen": ("paththonbadhu", ""), "thirty": ("muppadhu", ""), "forty": ("naarpadhu", ""), "sixty": ("arubadhu", ""),
        "seventy": ("ezhubadhu", ""), "eighty": ("embadhu", ""), "ninety": ("thonnooru", ""), "half": ("paadhi", ""),
        "second (2nd)": ("rendaavadhu", ""), "third (3rd)": ("moonaavadhu", ""), "first (1st)": ("mudhalaavadhu", ""),
    },
    "💬 Everyday sentences": {
        "i'm coming": ("naan varen", ""), "wait a minute": ("oru nimisham iru", ""), "come quickly": ("seekiram vaa", ""),
        "i'm done": ("mudinjudhu", ""), "let's go": ("polaam", ""), "i'm bored": ("bore adikkudhu", ""),
        "i'm sleepy": ("thookkam varudhu", ""), "i'm tired": ("kalaippaa irukku", ""), "it hurts": ("valikkudhu", ""),
        "i'm scared": ("bayamaa irukku", ""), "i want water": ("enakku thanni venum", ""), "i don't want": ("enakku venaam", ""),
        "it's okay": ("paravaayilla", ""), "good job": ("shabaash", ""), "happy birthday": ("piranthanaal vaazhthukkal", ""),
        "happy deepavali": ("Deepavali vaazhthukkal", ""), "happy pongal": ("Pongal vaazhthukkal", ""),
        "how old are you": ("unakku enna vayasu?", ""), "i am nine years old": ("enakku onbadhu vayasu", ""),
        "where are you going": ("enga pora?", ""), "what are you doing": ("enna panra?", ""), "did you eat": ("saaptiyaa?", ""),
        "very tasty": ("romba rusiyaa irukku", ""), "can i play": ("naan vilaiyaadalaamaa?", ""),
        "can i have it": ("enakku kidaikkumaa?", ""), "i miss you": ("unna miss panren", "'Paatti, unga nyaabagamaa irukku'"),
        "i love you": ("enakku unga mela romba paasam", "a warm way to say it to family"), "come and eat": ("saapida vaa", ""),
        "what happened": ("enna aachu?", ""), "nothing happened": ("onnum aagala", ""), "is it true": ("unmaiyaa?", ""),
        "of course": ("kandippaa", ""), "no problem": ("prachanai illa", ""), "be careful": ("jaakkiradhaiyaa iru", ""),
        "well done amma": ("super amma!", ""), "good night": ("iniya iravu", ""), "bless me": ("aasirvaadham pannunga", "said to elders"),
    },
})

# ===================== YEAR 5 VOCABULARY (spoken Tamil, English letters) =====================
TAMIL_WORDS.update({
    "📘 School subjects & learning": {
        "science": ("ariviyal", ""), "history": ("varalaaru", ""), "geography": ("puviyiyal", ""),
        "art": ("oviyam", "also 'kalai'"), "music": ("isai", ""), "sport": ("vilaiyaattu", ""), "computer": ("kanini", "most say 'computer'"),
        "english (language)": ("aangilam", ""), "subject": ("paadam", ""), "principal": ("thalaimai aasiriyar", ""),
        "classroom": ("vagupparai", ""), "map": ("varaipadam", "also 'map'"), "dictionary": ("agaraadhi", ""),
        "page": ("pakkam", ""), "chapter": ("adhiyaayam", ""), "poem": ("kavidhai", ""), "essay": ("katturai", ""),
        "example": ("udhaaranam", ""), "meaning": ("artham", ""), "practice": ("payirchi", ""), "mistake": ("thappu", ""),
        "result": ("mudivu", ""), "sports day": ("vilaiyaattu dhinam", ""), "project": ("project", ""), "test": ("test", "also 'thervu'"),
        "knowledge": ("arivu", ""), "idea": ("yosanai", ""), "rule": ("vidhi", ""), "team": ("anni", "also 'team'"),
        "line (queue)": ("varisai", ""), "drawing": ("padam", ""), "colouring": ("colour adikkaradhu", ""),
        "reading": ("vaasippu", ""), "spelling": ("ezhuththu kootal", ""), "grammar": ("ilakkanam", ""),
    },
    "🔬 Science & space": {
        "air": ("kaaththu", "formal: 'kaatru'"), "plant": ("chedi", ""), "energy": ("aatral", ""), "heat": ("veppam", ""),
        "sound": ("oli", "also 'saththam'"), "electricity": ("minsaaram", "also 'current'"), "magnet": ("kaandham", ""),
        "machine": ("iyandhiram", ""), "experiment": ("sodhanai", ""), "scientist": ("vinjaani", ""), "brain": ("moolai", ""),
        "bone": ("elumbu", ""), "lungs": ("nurai eeral", ""), "muscle": ("thasai", ""), "germ": ("kirumi", ""),
        "health": ("aarokkiyam", ""), "space": ("vinveli", ""), "rocket": ("rocket", ""), "astronaut": ("vinveli veerar", ""),
        "volcano": ("erimalai", ""), "earthquake": ("nilanadukkam", ""), "flood": ("vellam", "also means jaggery!"),
        "desert": ("paalaivanam", ""), "ocean": ("samudhram", "also 'kadal'"), "dinosaur": ("dinosaur", ""),
        "gold (metal)": ("thangam", ""), "silver": ("velli", ""), "iron": ("irumbu", ""), "glass": ("kannaadi", ""),
        "wood": ("maram", "also 'kattai'"), "plastic": ("plastic", ""), "water drop": ("thuli", ""),
        "temperature": ("vepanilai", ""), "shadow puppet": ("nizhal bommai", ""),
    },
    "🧍 More body words": {
        "lips": ("udhadu", ""), "cheek": ("kannam", ""), "eyebrow": ("puruvam", ""), "eyelash": ("imai", ""),
        "chin": ("thaadai", ""), "elbow": ("muzhangai", ""), "wrist": ("manikkattu", ""), "ankle": ("kanukkaal", ""),
        "heel": ("kudhikaal", ""), "toe": ("kaal viral", ""), "thumb": ("kattai viral", ""), "palm": ("ullangai", ""),
        "chest": ("nenju", ""), "waist": ("idupu", ""), "sweat": ("viyarvai", ""), "tears": ("kanneer", ""),
        "breath": ("moochu", ""), "voice": ("kural", ""),
    },
    "👨‍👩‍👧 More family & people": {
        "relatives": ("sondhakkaaranga", ""), "guest": ("virundhaali", ""), "neighbour": ("pakkaththu veettukaaranga", ""),
        "twins": ("irattaiyar", ""), "grandson": ("peran", ""), "granddaughter": ("peththi", ""), "parents": ("petror", "also 'amma appa'"),
        "husband": ("kanavan", ""), "wife": ("manaivi", ""), "elders": ("periyavanga", ""), "everybody": ("ellaarum", ""),
        "stranger": ("theriyaadhavanga", ""), "classmate": ("kooda padikkaravanga", ""), "best friend": ("nerungiya thozhi", "for a boy: 'nerungiya nanban'"),
    },
    "🛁 Daily routine": {
        "toothbrush": ("pal brush", ""), "toothpaste": ("pal paste", ""), "shampoo": ("shampoo", ""), "bath": ("kuliyal", ""),
        "water bottle": ("thanni bottle", ""), "school bag": ("school pai", ""), "rest": ("oyvu", ""), "nap": ("kutti thookkam", ""),
        "bedtime": ("thoongara neram", ""), "story time": ("kadhai neram", ""), "alarm": ("alarm", ""),
        "morning prayer": ("kaalai praarththanai", ""), "screen time": ("screen time", ""), "chores": ("veettu velai", ""),
        "homework time": ("padikkira neram", ""), "dinner time": ("saapadu neram", ""),
    },
    "🍳 Kitchen & cooking": {
        "rice cooker": ("rice cooker", ""), "pressure cooker": ("cooker", ""), "frying pan": ("vaanali", ""),
        "dosa pan": ("dosai kal", ""), "mixer": ("mixie", ""), "flour": ("maavu", "also 'batter'"), "rice flour": ("arisi maavu", ""),
        "wheat": ("godhumai", ""), "spices": ("masaala", ""), "turmeric": ("manjal", ""), "cumin": ("seeragam", ""),
        "mustard seeds": ("kadugu", ""), "curry leaves": ("kariveppilai", ""), "coriander": ("koththamalli", ""),
        "mint": ("pudhinaa", ""), "tamarind": ("puli", "also means 'tiger'!"), "jaggery": ("vellam", ""),
        "coconut milk": ("thengaai paal", ""), "smell (nice)": ("vaasanai", ""), "recipe": ("seimurai", ""),
        "fridge": ("fridge", ""), "oven": ("oven", ""), "lid": ("moodi", ""), "tray": ("thattu", ""),
    },
    "🪔 Festivals & culture": {
        "festival": ("pandigai", ""), "deepavali": ("Deepavali", "also 'Diwali'"), "pongal": ("Pongal", ""),
        "navarathri": ("Navaraathiri", ""), "karthigai deepam": ("Karththigai Deepam", ""), "vinayagar chathurthi": ("Vinaayagar Chathurththi", ""),
        "tamil new year": ("Thamizh puththaandu", ""), "prayer": ("praarththanai", ""), "god": ("kadavul", "also 'saami'"),
        "garland": ("maalai", ""), "new clothes": ("pudhu dhuni", ""), "crackers": ("pattaasu", ""), "gift": ("parisu", ""),
        "celebration": ("kondaattam", ""), "wedding": ("kalyaanam", ""), "birthday": ("piranthanaal", ""), "function": ("vizhaa", "also 'function'"),
        "blessing": ("aasirvaadham", ""), "dance (classical)": ("Bharathanaattiyam", ""), "drum": ("melam", ""),
        "veena": ("veenai", ""), "flute": ("pullaankuzhal", ""), "sugarcane": ("karumbu", ""), "oil lamp": ("agal vilakku", ""),
        "tamil months": ("Chiththirai, Vaigaasi, Aani, Aadi, Aavani, Purattaasi, Aippasi, Karththigai, Maargazhi, Thai, Maasi, Panguni",
                         "Chiththirai starts in mid-April"),
    },
    "🛍️ Shopping & money": {
        "coin": ("kaasu", ""), "rupee": ("rooba", ""), "dollar": ("dollar", ""), "price": ("vilai", ""), "cheap": ("malivu", ""),
        "expensive": ("vilai adhigam", ""), "customer": ("vaadikkaiyaalar", ""), "change (money)": ("chillarai", ""),
        "bill": ("bill", ""), "discount": ("thallupadi", ""), "queue": ("varisai", ""), "trolley": ("trolley", ""),
        "how much is this": ("idhu evvalavu?", ""), "too expensive": ("romba vilai", ""),
    },
    "🚌 Travel & transport": {
        "motorbike": ("bike", ""), "auto rickshaw": ("auto", ""), "ticket": ("ticket", "formal: 'cheetu'"),
        "station": ("station", "formal: 'nilaiyam'"), "traffic": ("traffic", ""), "journey": ("payanam", ""), "trip": ("suttrula", "also 'trip'"),
        "suitcase": ("petti", ""), "passport": ("passport", ""), "driver": ("driver", "formal: 'ottunar'"), "seatbelt": ("seatbelt", ""),
        "boat ride": ("padagu savaari", ""), "ship": ("kappal", ""), "helicopter": ("helicopter", ""), "road trip": ("car payanam", ""),
    },
    "⚽ Sports & games": {
        "bat": ("bat", ""), "cricket": ("cricket", ""), "football": ("football", "also 'kaalpandhu'"), "race": ("ottappandhayam", ""),
        "score": ("score", ""), "goal": ("goal", "a dream/aim is 'ilakku'"), "slide": ("sarukku maram", "kids say 'slide'"),
        "hide and seek": ("kannaamoochi", ""), "skipping": ("skipping", ""), "chess": ("chadhurangam", ""), "carrom": ("carrom", ""),
        "puzzle": ("pudhir", ""), "kite": ("pattam", ""), "swimming": ("neechal", ""), "dance class": ("dance class", ""),
        "winner": ("vetriyaalar", ""), "loser": ("thotravanga", ""), "turn (my turn)": ("murai", "'en murai' = my turn"),
        "rules (game)": ("vilaiyaattu vidhigal", ""), "medal": ("padhakkam", ""), "trophy": ("kopai", ""),
    },
    "💛 Character & values": {
        "respect": ("mariyaadhai", ""), "kindness": ("irakkam", "also 'anbu'"), "patience": ("porumai", ""), "honesty": ("nermai", ""),
        "discipline": ("ozhukkam", ""), "hard work": ("uzhaippu", ""), "success": ("vetri", ""), "failure": ("thoalvi", ""),
        "dream": ("kanavu", ""), "aim": ("ilakku", ""), "wisdom": ("gnaanam", ""), "confidence": ("thannambikkai", ""),
        "helpful": ("udhavi seiyara", ""), "polite": ("mariyaadhaiyaana", ""), "lazy": ("somberi", ""), "clever": ("puththisaali", ""),
        "naughty": ("settai", ""), "careful": ("jaakkiradhai", ""), "nervous": ("padhattam", ""), "embarrassed": ("vetkamaa", ""),
        "grateful": ("nandriyulla", ""), "upset": ("manasu sariyilla", ""), "generous": ("thaaraala", ""), "brave girl": ("dhairiyamaana ponnu", ""),
        "truthful": ("unmaiyaana", ""), "forgiveness": ("mannippu", ""), "teamwork": ("koottu muyarchi", ""),
    },
    "🗣️ Conversation (Year 5)": {
        "can you help me": ("enakku udhavi panreengalaa?", ""), "i need help": ("enakku help venum", ""),
        "what does this mean": ("idhukku enna artham?", ""), "how do you say it in tamil": ("Thamizhla eppadi solradhu?", ""),
        "please say it again": ("thirumba sollunga", ""), "please speak slowly": ("medhuvaa pesunga", ""), "let me try": ("naan try panren", ""),
        "my turn": ("en murai", ""), "your turn": ("un murai", "polite: 'unga murai'"), "who is it": ("yaaru adhu?", ""),
        "wait for me": ("enakkaaga kaaththiru", ""), "hurry up": ("seekiram", ""), "be quiet": ("amaidhiyaa iru", ""),
        "sit down": ("utkaaru", ""), "stand up": ("ezhundhiru", ""), "can i go to the toilet": ("naan toilet polaamaa?", ""),
        "i finished my homework": ("naan homework mudichitten", ""), "i got good marks": ("enakku nalla mark kidaichudhu", ""),
        "i love tamil": ("enakku Thamizh romba pidikkum", ""), "thank you very much": ("romba nandri", ""),
        "see you tomorrow": ("naalaikku paakkalaam", ""), "take care": ("paaththukko", "to an elder: 'paaththukkonga'"),
        "get well soon": ("seekiram gunamaagu", ""), "congratulations": ("vaazhthukkal", ""), "happy new year": ("puththaandu vaazhthukkal", ""),
        "what time is it": ("mani enna?", ""), "what day is it today": ("innaikku enna kizhamai?", ""), "what is this": ("idhu enna?", ""),
        "where is my bag": ("en bag enga?", ""), "i lost my pencil": ("en pencil tholanjudhu", ""), "can i watch tv": ("naan TV paakkalaamaa?", ""),
        "come and play": ("vilaiyaada vaa", ""), "i am ready": ("naan ready", ""), "i'm busy": ("naan busy-aa irukken", ""),
        "is it okay": ("sariyaa?", ""), "that's right": ("adhu sari", ""), "that's wrong": ("adhu thappu", ""),
        "i forgot": ("naan maranthutten", ""), "i remember": ("enakku nyaabagam irukku", ""), "tell me a story": ("oru kadhai sollunga", ""),
        "i'm full": ("vayiru niranjudhu", ""), "one more please": ("innum onnu kudunga", ""), "it's my birthday": ("innaikku en piranthanaal", ""),
        "i'm sorry": ("mannichidunga", "to a friend: 'sorry'"), "it's raining": ("mazhai peyyudhu", ""), "it's hot": ("veyil adikkudhu", ""),
        "it's cold": ("kulirudhu", ""), "where do you live": ("neenga enga irukkeenga?", ""), "i live in brisbane": ("naan Brisbane-la irukken", ""),
        "what is your favourite": ("unakku enna romba pidikkum?", ""), "my favourite colour is pink": ("enakku pink niram romba pidikkum", ""),
    },
    "⏰ Time": {
        "o'clock": ("mani", "e.g. 'moonu mani' = 3 o'clock"), "minute": ("nimisham", ""), "second (time)": ("vinaadi", ""),
        "hour": ("mani neram", ""), "calendar": ("naatkaatti", ""), "date": ("thedhi", ""), "midnight": ("nalliravu", ""),
        "noon": ("madhiyam", ""), "weekend": ("vaara iruthi", "also 'weekend'"), "every day": ("dhinamum", ""), "tonight": ("innaikku raaththiri", ""),
        "this week": ("indha vaaram", ""), "next week": ("adutha vaaram", ""), "last week": ("pona vaaram", ""),
        "next year": ("adutha varusham", ""), "last year": ("pona varusham", ""), "early": ("seekiram", ""), "on time": ("sariyaana neraththula", ""),
    },
    "📐 Maths words": {
        "circle": ("vattam", ""), "square": ("sadhuram", ""), "triangle": ("mukkonam", ""), "rectangle": ("neel sadhuram", ""),
        "line": ("kodu", ""), "dot": ("pulli", ""), "number": ("en", ""), "add": ("koottu", ""), "subtract": ("kazhi", ""),
        "multiply": ("perukku", ""), "divide": ("vagu", ""), "equal": ("samam", ""), "plus": ("koottal", ""), "minus": ("kazhiththal", ""),
        "quarter": ("kaal", "also means 'leg'!"), "double": ("rendu madangu", ""), "total": ("mottham", ""), "more": ("adhigam", ""),
        "less": ("kuraivu", ""), "length": ("neelam", ""), "weight": ("edai", ""), "height": ("uyaram", ""), "measure": ("alavu", ""),
        "even number": ("iratta padai en", ""), "odd number": ("otrai padai en", ""), "fraction": ("bin", ""), "answer (maths)": ("vidai", ""),
    },
    "💼 Jobs": {
        "farmer": ("vivasaayi", ""), "nurse": ("nurse", "formal: 'sevilier'"), "police officer": ("police", "formal: 'kaavalar'"),
        "firefighter": ("theeyanaippu veerar", ""), "cook": ("samaiyalkaarar", ""), "shopkeeper": ("kadaikkaarar", ""),
        "tailor": ("thaiyalkaarar", ""), "carpenter": ("thachchar", ""), "engineer": ("engineer", "formal: 'poriyaalar'"),
        "artist": ("oviyar", ""), "singer": ("paadagar", ""), "dancer": ("nadanakkalaignar", ""), "pilot": ("vimaani", "also 'pilot'"),
        "soldier": ("raanuva veerar", ""), "priest": ("poosaari", ""), "postman": ("thabaalkaarar", ""), "fisherman": ("meenavar", ""),
        "builder": ("kattida thozhilaali", ""), "vet": ("kaalnadai maruththuvar", ""), "dentist": ("pal doctor", ""), "writer": ("ezhuththaalar", ""),
    },
    "🏙️ More places": {
        "living room": ("hall", ""), "bedroom": ("padukkai arai", ""), "balcony": ("balcony", ""), "post office": ("anjal nilaiyam", "also 'post office'"),
        "police station": ("kaaval nilaiyam", ""), "bank": ("vangi", "also 'bank'"), "restaurant": ("unavagam", "people often say 'hotel'"),
        "bakery": ("bakery", ""), "cinema": ("thiraiyarangam", "also 'theatre'"), "museum": ("arungaatchiyagam", ""),
        "swimming pool": ("neechal kulam", ""), "farm": ("pannai", ""), "factory": ("thozhirsaalai", ""), "office": ("aluvalagam", "also 'office'"),
        "church": ("church", ""), "mosque": ("pallivaasal", ""), "village fair": ("thiruvizhaa", ""), "playground": ("vilaiyaattu maidhaanam", ""),
    },
    "🐘 More animals": {
        "rooster": ("seval", ""), "ox": ("maadu", ""), "buffalo": ("erumai", ""), "sheep": ("semmari aadu", ""), "wolf": ("onaai", ""),
        "cheetah": ("sivingi", ""), "leopard": ("siruththai", ""), "rhinoceros": ("kaandaamirugam", ""), "hippopotamus": ("neeryaanai", ""),
        "crab": ("nandu", ""), "prawn": ("iraal", ""), "starfish": ("natchathira meen", ""), "seahorse": ("kadal kudhirai", ""),
        "swan": ("annam", ""), "kingfisher": ("meenkoththi", ""), "woodpecker": ("marangoththi", ""), "cuckoo": ("kuyil", ""),
        "dragonfly": ("thumbi", ""), "grasshopper": ("vettukkili", ""), "firefly": ("minminippoochi", ""), "caterpillar": ("kambalippoochi", ""),
        "scorpion": ("thel", ""), "beetle": ("vandu", ""), "cobra": ("naagappaambu", ""), "python": ("malaippaambu", ""),
    },
    "🌸 Plants & flowers": {
        "neem tree": ("vembu", ""), "banyan tree": ("aalamaram", ""), "coconut tree": ("thennai maram", ""), "palm tree": ("panai maram", ""),
        "rose": ("roja", ""), "jasmine": ("malligai", "spoken: 'malli poo'"), "lotus": ("thaamarai", ""), "sunflower": ("sooriyagaandhi", ""),
        "tulsi": ("thulasi", ""), "banana leaf": ("vaazhai ilai", ""), "thorn": ("mul", ""), "bud": ("mottu", ""), "petal": ("idhazh", ""),
    },
    "🥦 More vegetables & dishes": {
        "okra": ("vendaikkaai", ""), "bitter gourd": ("paavakkaai", ""), "drumstick": ("murungaikkaai", ""), "cabbage": ("muttaikose", ""),
        "cauliflower": ("cauliflower", ""), "radish": ("mullangi", ""), "beetroot": ("beetroot", ""), "peas": ("pattaani", ""),
        "capsicum": ("kudai milagaai", ""), "mushroom": ("kaalaan", ""), "sweet potato": ("sakkaraivalli kizhangu", ""),
        "raw banana": ("vaazhaikkaai", ""), "upma": ("uppumaa", ""), "chapati": ("chappaaththi", ""), "parotta": ("parotta", ""),
        "biryani": ("biriyaani", ""), "curd rice": ("thayir saadham", ""), "lemon rice": ("elumichai saadham", ""),
        "tamarind rice": ("puliyodharai", ""), "vada": ("vadai", ""), "kesari": ("kesari", ""), "halwa": ("halwa", ""),
        "murukku": ("murukku", ""), "appalam": ("appalam", ""), "buttermilk": ("mor", ""), "porridge": ("kanji", ""),
        "pongal (dish)": ("pongal", ""), "poori": ("poori", ""), "noodles": ("noodles", ""),
    },
    "👕 More clothes & things": {
        "dhoti": ("vesti", ""), "half saree": ("dhaavani", ""), "kurta": ("kurta", ""), "shorts": ("shorts", ""), "trousers": ("pant", ""),
        "t-shirt": ("t-shirt", ""), "sweater": ("sweater", ""), "raincoat": ("mazhai coat", ""), "slippers": ("seruppu", ""),
        "watch": ("kai kadigaaram", ""), "anklet": ("kolusu", ""), "ring": ("modhiram", ""), "hair band": ("hair band", ""),
        "flowers for hair": ("poo", ""), "handkerchief": ("kaikkuttai", ""),
    },
    "✨ More describing words": {
        "noisy": ("saththamaana", ""), "messy": ("olungillaadha", ""), "crowded": ("kootamaana", ""), "famous": ("prabalamaana", ""),
        "important": ("mukkiyamaana", ""), "special": ("sirappaana", ""), "dangerous": ("aabaththaana", ""), "safe": ("paadhugaappaana", ""),
        "healthy": ("aarokkiyamaana", ""), "delicious": ("rusiyaana", ""), "fresh": ("fresh-aana", ""), "ripe": ("pazhutha", ""),
        "raw": ("pachchai", ""), "colourful": ("pala niramaana", ""), "shiny": ("palapalappaana", ""), "smooth": ("vazhuvazhuppaana", ""),
        "sticky": ("pisupisuppaana", ""), "terrible": ("mosamaana", ""), "strange": ("vinodhamaana", ""), "funny": ("vedikkaiyaana", ""),
        "cute": ("azhagaana", "kids also say 'cute'"), "smart": ("puththisaali", ""), "busy": ("busy", ""), "ready": ("ready", "formal: 'thayaar'"),
        "sure": ("nichayam", ""), "possible": ("mudiyum", "'I can' = 'ennaala mudiyum'"), "impossible": ("mudiyaadhu", "'I can't' = 'ennaala mudiyaadhu'"),
    },
    "🔢 Big numbers": {
        "twenty-one": ("irubaththonnu", ""), "twenty-five": ("irubaththanju", ""), "two hundred": ("irunooru", ""),
        "five hundred": ("ainooru", ""), "ten thousand": ("paththaayiram", ""), "lakh": ("latcham", "100,000"), "crore": ("kodi", "10 million"),
        "million": ("paththu latcham", ""),
    },
})

TAMIL_VERBS.extend([
    ("sneeze", "sneezed", "sneezed", "thummu", "thummaren", "thumminen", "thummuven", ""),
    ("cough", "coughed", "coughed", "irumu", "irumaren", "iruminen", "irumuven", ""),
    ("yawn", "yawned", "yawned", "kottaavi vidu", "kottaavi vidaren", "kottaavi vitten", "kottaavi viduven", ""),
    ("smell", "smelled", "smelled", "vaasanai paaru", "vaasanai paakkiren", "vaasanai paaththen", "vaasanai paappen", ""),
    ("taste", "tasted", "tasted", "rusi paaru", "rusi paakkiren", "rusi paaththen", "rusi paappen", ""),
    ("agree", "agreed", "agreed", "othukko", "othukkaren", "othukkitten", "othukkuven", ""),
    ("decide", "decided", "decided", "mudivu pannu", "mudivu panren", "mudivu pannen", "mudivu pannuven", ""),
    ("explain", "explained", "explained", "vilakku", "vilakkaren", "vilakkinen", "vilakkuven", ""),
    ("answer", "answered", "answered", "badhil sollu", "badhil solren", "badhil sonnen", "badhil solluven", ""),
    ("repeat", "repeated", "repeated", "thirumba sollu", "thirumba solren", "thirumba sonnen", "thirumba solluven", ""),
    ("collect", "collected", "collected", "sekari", "sekarikkiren", "sekarichen", "sekarippen", ""),
    ("arrange", "arranged", "arranged", "adukku", "adukkaren", "adukkinen", "adukkuven", ""),
    ("build", "built", "built", "kattu", "kattaren", "kattinen", "kattuven", "same word as 'tie'"),
    ("plant", "planted", "planted", "nadu", "nadaren", "natten", "naduven", ""),
    ("water the plants", "watered the plants", "watered the plants", "chedikku thanni oothu", "chedikku thanni oothaaren",
     "chedikku thanni oothinen", "chedikku thanni oothuven", ""),
    ("save", "saved", "saved", "semi", "semikkiren", "semichen", "semippen", "save money"),
    ("spend", "spent", "spent", "selavu pannu", "selavu panren", "selavu pannen", "selavu pannuven", ""),
    ("pay", "paid", "paid", "panam kodu", "panam kudukkiren", "panam kuduththen", "panam kuduppen", ""),
    ("celebrate", "celebrated", "celebrated", "kondaadu", "kondaadaren", "kondaadinen", "kondaaduven", ""),
    ("invite", "invited", "invited", "azhai", "azhaikkiren", "azhaichen", "azhaippen", ""),
    ("travel", "travelled", "travelled", "payanam pannu", "payanam panren", "payanam pannen", "payanam pannuven", ""),
    ("enjoy", "enjoyed", "enjoyed", "enjoy pannu", "enjoy panren", "enjoy pannen", "enjoy pannuven", ""),
    ("rest", "rested", "rested", "oyvu edu", "oyvu edukkiren", "oyvu eduththen", "oyvu eduppen", ""),
    ("worry", "worried", "worried", "kavalaippadu", "kavalaippadaren", "kavalaippatten", "kavalaippaduven", ""),
    ("believe", "believed", "believed", "nambu", "nambaren", "nambinen", "nambuven", "also 'trust'"),
    ("trust", "trusted", "trusted", "nambu", "nambaren", "nambinen", "nambuven", ""),
    ("whisper", "whispered", "whispered", "mella pesu", "mella pesaren", "mella pesinen", "mella pesuven", ""),
    ("apologise", "apologised", "apologised", "mannippu kelu", "mannippu kekkiren", "mannippu ketten", "mannippu keppen", ""),
    ("forgive", "forgave", "forgiven", "mannichidu", "mannikkiren", "mannichitten", "mannichiduven", ""),
    ("thank", "thanked", "thanked", "nandri sollu", "nandri solren", "nandri sonnen", "nandri solluven", ""),
    ("protect", "protected", "protected", "kaappaaththu", "kaappaaththaren", "kaappaaththinen", "kaappaaththuven", ""),
    ("get dressed", "got dressed", "got dressed", "dress pannikko", "dress pannikkaren", "dress pannikitten", "dress pannikkuven", ""),
    ("comb hair", "combed hair", "combed hair", "thalai vaaru", "thalai vaaraaren", "thalai vaarinen", "thalai vaaruven", ""),
    ("knock", "knocked", "knocked", "thattu", "thattaren", "thattinen", "thattuven", ""),
    ("shake", "shook", "shaken", "aattu", "aattaren", "aattinen", "aattuven", ""),
    ("wave", "waved", "waved", "kai aattu", "kai aattaren", "kai aattinen", "kai aattuven", "wave your hand"),
    ("wipe", "wiped", "wiped", "thudai", "thudaikkiren", "thudaichen", "thudaippen", ""),
    ("sweep", "swept", "swept", "perukku", "perukkaren", "perukkinen", "perukkuven", ""),
    ("sew", "sewed", "sewn", "thai", "thaikkiren", "thaichen", "thaippen", ""),
    ("lock", "locked", "locked", "poottu", "poottaren", "poottinen", "poottuven", ""),
    ("switch on", "switched on", "switched on", "on pannu", "on panren", "on pannen", "on pannuven", ""),
    ("switch off", "switched off", "switched off", "off pannu", "off panren", "off pannen", "off pannuven", ""),
    ("meet", "met", "met", "santhi", "santhikkiren", "santhichen", "santhippen", ""),
    ("leave", "left", "left", "kilambu", "kilambaren", "kilambinen", "kilambuven", "leave / set off"),
    ("come back", "came back", "come back", "thirumbi vaa", "thirumbi varen", "thirumbi vandhen", "thirumbi varuven", ""),
    ("arrive", "arrived", "arrived", "poi seru", "poi seraren", "poi serndhen", "poi seruven", ""),
    ("choose", "chose", "chosen", "therndhedu", "therndhedukkiren", "therndheduththen", "therndheduppen", ""),
    ("lend", "lent", "lent", "kadan kodu", "kadan kudukkiren", "kadan kuduththen", "kadan kuduppen", ""),
    ("guess", "guessed", "guessed", "yoogi", "yoogikkiren", "yoogichen", "yoogippen", ""),
    ("imagine", "imagined", "imagined", "karpanai pannu", "karpanai panren", "karpanai pannen", "karpanai pannuven", ""),
    ("dream", "dreamed", "dreamed", "kanavu kaanu", "kanavu kaanaren", "kanavu kanden", "kanavu kaanuven", ""),
    ("shine", "shone", "shone", "minnu", "minnaren", "minninen", "minnuven", ""),
    ("melt", "melted", "melted", "urugu", "urugaren", "uruginen", "uruguven", ""),
    ("wake someone up", "woke someone up", "woken someone up", "ezhuppu", "ezhupparen", "ezhuppinen", "ezhuppuven", ""),
    ("obey", "obeyed", "obeyed", "solradha kelu", "solradha kekkiren", "sonnadha ketten", "solradha keppen", "listen to what you're told"),
    ("greet", "greeted", "greeted", "vanakkam sollu", "vanakkam solren", "vanakkam sonnen", "vanakkam solluven", ""),
])

# ===================== MORE TOPICS (space, science, sea, plants, food, relationships) =====================
TAMIL_WORDS.update({
    "🪐 Space & planets": {
        "universe": ("pirapanjam", ""), "galaxy": ("vinmeen thiral", ""), "milky way": ("aagaaya gangai", ""),
        "solar system": ("sooriya kudumbam", ""), "mercury (planet)": ("Budhan", ""), "venus": ("Velli", "also 'Sukkiran'"),
        "mars": ("Sevvaai", ""), "jupiter": ("Viyaazhan", "also 'Guru'"), "saturn": ("Sani", ""), "uranus": ("Uranus", ""),
        "neptune": ("Neptune", ""), "pluto": ("Pluto", "a dwarf planet"), "comet": ("vaal natchaththiram", ""),
        "meteor": ("eri natchaththiram", "also 'shooting star'"), "shooting star": ("eri natchaththiram", ""),
        "asteroid": ("sirukol", ""), "orbit": ("suttrupaadhai", ""), "gravity": ("eerppu visai", ""), "telescope": ("tholainokki", ""),
        "satellite": ("seyarkaikkol", "the Moon is Earth's natural satellite"), "spaceship": ("vinkalam", ""),
        "space station": ("vinveli nilaiyam", ""), "alien": ("vetrukiraga vaasi", ""), "black hole": ("karunthulai", ""),
        "constellation": ("natchaththira koottam", ""), "eclipse": ("grahanam", ""), "solar eclipse": ("sooriya grahanam", ""),
        "lunar eclipse": ("chandhira grahanam", ""), "full moon": ("pournami", ""), "new moon": ("amaavaasai", ""),
        "crescent moon": ("pirai", ""), "sunrise": ("sooriya udhayam", ""), "sunset": ("sooriya asthamanam", ""),
        "atmosphere": ("valimandalam", ""), "crater": ("pallam", ""), "light year": ("oli aandu", ""),
        "north star": ("dhuruva natchaththiram", ""), "planet earth": ("bhoomi graham", ""), "astronomy": ("vaaniyal", ""),
    },
    "🧪 Year 5 science (school Tamil)": {
        "solid": ("thinmam", "formal school word"), "liquid": ("thiravam", "formal school word"), "gas": ("vaayu", ""),
        "evaporation": ("aaviyaadhal", "formal school word"), "melting": ("urugudhal", ""), "freezing": ("uraidhal", ""),
        "boiling": ("kodhiththal", ""), "water cycle": ("neer suzharchi", ""), "force": ("visai", ""), "friction": ("uraaivu", ""),
        "circuit": ("minsutru", ""), "battery": ("battery", "formal: 'minkalam'"), "reflection": ("prathibhalippu", ""),
        "vibration": ("athirvu", ""), "thermometer": ("vepamaani", ""), "oxygen": ("pranavaayu", "also 'oxygen'"),
        "carbon dioxide": ("carbon dioxide", ""), "photosynthesis": ("olicherkkai", "formal school word"),
        "food chain": ("unavu sangili", ""), "habitat": ("vaazhvidam", ""), "life cycle": ("vaazhkkai suzharchi", ""),
        "germination": ("mulaiththal", ""), "pollination": ("magarandha serkkai", ""), "stem": ("thandu", ""),
        "skeleton": ("elumbukkoodu", ""), "digestion": ("seeranam", ""), "senses": ("pulangal", ""), "nutrition": ("oottachaththu", ""),
        "vitamin": ("vitamin", ""), "mammal": ("paaloottigal", "formal school word"), "reptile": ("oorvana", ""),
        "amphibian": ("iruvaazhvi", ""), "predator": ("vettaiyaadum vilangu", ""), "prey": ("irai", ""),
        "extinct": ("azhindhu pona", ""), "fossil": ("puthaipadivam", ""), "mineral": ("kanimam", ""), "erosion": ("arippu", ""),
        "pollution": ("maasu", ""), "recycle": ("marusuzharchi", ""), "environment": ("suttruchoozhal", ""),
        "climate": ("kaalanilai", ""), "weather": ("vaanilai", ""), "experiment result": ("sodhanai mudivu", ""),
    },
    "🌊 Sea & sea creatures": {
        "seashell": ("kilinjal", ""), "conch shell": ("sangu", ""), "coral": ("pavazham", ""), "seaweed": ("kadal paasi", ""),
        "lighthouse": ("kalangarai vilakkam", ""), "harbour": ("thuraimugam", ""), "sea turtle": ("kadal aamai", ""),
        "octopus": ("octopus", ""), "jellyfish": ("jellyfish", ""), "lobster": ("lobster", ""), "eel": ("vilaangu meen", ""),
        "squid": ("kanavaai", ""), "oyster": ("sippi", ""), "pearl": ("muththu", ""), "stingray": ("thirukkai meen", ""),
        "seal (animal)": ("seal", ""), "sailor": ("maalumi", ""), "diver": ("diver", ""), "fishing net": ("valai", ""),
        "anchor": ("nangooram", ""), "sail": ("paai", ""), "deep": ("aazham", ""), "salt water": ("uppu thanni", ""),
        "beach sand": ("kadarkarai manal", ""), "sandcastle": ("manal veedu", ""), "fish tank": ("meen thotti", ""),
        "clownfish": ("clownfish", ""), "sea creatures": ("kadal uyirinangal", ""), "underwater": ("thanneerukku adiyil", ""),
    },
    "🌳 Plants & trees": {
        "tree trunk": ("adimaram", ""), "bark": ("maraththoal", ""), "bush": ("pudhar", ""), "creeper": ("kodi", "also 'vine'"),
        "mango tree": ("maamaram", ""), "tamarind tree": ("puliyamaram", ""), "jackfruit tree": ("palaamaram", ""),
        "banana tree": ("vaazhai maram", ""), "peepal tree": ("arasamaram", ""), "bamboo": ("moongil", ""), "teak": ("thekku", ""),
        "sandalwood": ("santhanam", ""), "eucalyptus": ("thaila maram", "koalas love it!"), "cactus": ("kalli", ""),
        "moss": ("paasi", ""), "herb": ("mooligai", ""), "vegetable garden": ("kaaikari thottam", ""), "flower pot": ("chedi thotti", ""),
        "sunlight": ("sooriya oli", ""), "dry leaves": ("sarugu", ""), "seedling": ("naaththu", ""), "grass field": ("pulvelli", ""),
        "pine tree": ("pine maram", ""), "apple tree": ("apple maram", ""), "lemon tree": ("elumichai maram", ""),
    },
    "👨‍👩‍👧‍👦 Relationships": {
        "mother's brother": ("maama", ""), "mother's brother's wife": ("maami", ""), "father's sister": ("athai", ""),
        "father's sister's husband": ("maama", "same word as mother's brother"),
        "father's elder brother": ("periyappa", ""), "father's elder brother's wife": ("periyamma", ""),
        "father's younger brother": ("chithappa", ""), "father's younger brother's wife": ("chithi", ""),
        "mother's elder sister": ("periyamma", ""), "mother's younger sister": ("chithi", ""),
        "cousin (periyappa/chithappa's child)": ("anna / akka / thambi / thangachi", "these cousins are called like brothers and sisters"),
        "cousin (maama/athai's son)": ("maama paiyan", "also 'machaan'"), "cousin (maama/athai's daughter)": ("maama ponnu", "also 'athai ponnu'"),
        "elder brother's wife": ("anni", ""), "mother-in-law": ("maamiyaar", ""), "father-in-law": ("maamanaar", ""),
        "nephew": ("marumagan", ""), "niece": ("marumagal", ""), "great grandmother": ("kollu paatti", ""),
        "great grandfather": ("kollu thaatha", ""), "family tree": ("kudumba maram", ""), "relationship": ("uravu", ""),
        "only child": ("ore kuzhandhai", ""), "older": ("periya", "older sister = 'periya akka'"), "younger": ("chinna", ""),
    },
    "🍲 Even more food": {
        "idiyappam": ("idiyappam", ""), "appam": ("aappam", ""), "kozhukattai": ("kozhukattai", ""), "sundal": ("sundal", ""),
        "kootu": ("koottu", ""), "aviyal": ("aviyal", ""), "poriyal": ("poriyal", ""), "bonda": ("bonda", ""), "bajji": ("bajji", ""),
        "samosa": ("samosa", ""), "mysore pak": ("mysore paagu", ""), "jalebi": ("jilebi", ""), "gulab jamun": ("gulaab jaamun", ""),
        "dates": ("perichampazham", ""), "fig": ("aththippazham", ""), "custard apple": ("seethaappazham", ""),
        "sweet lime": ("saaththukudi", ""), "pear": ("berikkaai", ""), "coconut water": ("ilaneer", ""),
        "sugarcane juice": ("karumbu juice", ""), "cashew": ("mundhiri", ""), "almond": ("baadhaam", ""), "pistachio": ("pista", ""),
        "raisins": ("ularndha thiraatchai", ""), "millet": ("sirudhaaniyam", ""), "ragi": ("kezhvaragu", ""), "oats": ("oats", ""),
        "cheese": ("cheese", ""), "paneer": ("paneer", ""), "cream": ("cream", ""), "chips": ("chips", ""), "popcorn": ("popcorn", ""),
        "sandwich": ("sandwich", ""), "pizza": ("pizza", ""), "pasta": ("pasta", ""), "soup": ("soup", ""), "sauce": ("sauce", ""),
        "lunch box food": ("tiffin", ""), "leftovers": ("meedhi saapaadu", ""), "hungry tummy": ("pasi vayiru", ""),
    },
})

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&display=swap');
h1, h2, h3, p, label, li, input, textarea, .stMarkdown, [data-baseweb="tab"] p { font-family: 'Fredoka', sans-serif !important; }
h3 { color: #5a2d66 !important; }
.block-container { max-width: 820px; padding-top: 2rem; }
.hero { position: relative; text-align: center; padding: 28px 16px 20px; border-radius: 28px;
  background: rgba(255,255,255,.82); border: 3px solid #ffd1e8;
  box-shadow: 0 8px 30px rgba(255,105,180,.18); margin-bottom: 14px; overflow: hidden; }
.hero .title { display: inline-block; font-size: 2.6rem; font-weight: 700; line-height: 1.15;
  background: linear-gradient(90deg,#ff4fa3,#ff9f43,#f5c400,#3fbf5a,#38b6ff,#9b6bff);
  -webkit-background-clip: text; background-clip: text; color: transparent; }
.hero .sub { color: #8a5a8a; font-size: 1.05rem; margin-top: 2px; }
.balance { display: inline-block; margin-top: 10px; padding: 8px 20px; border-radius: 999px; font-weight: 700;
  font-size: 1.35rem; color: #fff; background: linear-gradient(90deg,#ff5fa2,#9b6bff);
  box-shadow: 0 4px 14px rgba(155,107,255,.35); }
.hero .badge { display: inline-block; margin: 8px 3px 0; padding: 4px 12px; border-radius: 999px;
  font-weight: 600; font-size: .92rem; }
.badge.fire { background: #fff0d6; color: #b35c00; }
.badge.moon { background: #ece6ff; color: #4b3a99; }
.badge.money { background: #e3f8e7; color: #1f7a37; }
.badge.carrot { background: #ffe9d6; color: #b34d00; }
.badge.toy { background: #e0f2ff; color: #1d5f8a; }
.badge.spin { background: #fff3a8; color: #8a6500; animation: wiggle 1.2s ease-in-out infinite; }
@keyframes wiggle { 0%,100% { transform: rotate(-3deg); } 50% { transform: rotate(3deg); } }
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
[data-testid="stVerticalBlockBorderWrapper"] { background: rgba(255,255,255,.84);
  border-radius: 22px !important; border: 2px solid #ffd1e8 !important; }
[data-testid="stCheckbox"] label p { font-size: 1.12rem; font-weight: 500; }
.tip { background: #fff6fb; border-left: 5px solid #ff9ccc; border-radius: 12px; padding: 8px 12px;
  color: #6b3f73; margin: 0 0 6px 30px; font-size: .98rem; }
.card { background: rgba(255,255,255,.9); border: 2px solid #ffd1e8; border-radius: 20px; padding: 14px 16px;
  margin: 6px 0 10px; color: #3b2350; }
.msg { background: linear-gradient(135deg,#ffe3f1,#efe3ff); border: 3px solid #ff9ccc; border-radius: 24px;
  padding: 16px 18px; font-size: 1.2rem; color: #5a2d66; text-align: center; margin-bottom: 8px; }
.fact { background: #fffbe6; border: 2px solid #ffe28a; border-radius: 18px; padding: 10px 14px; color: #5a4300;
  margin: 6px 0 10px; }
.reward-head { font-size: 1.3rem; font-weight: 700; color: #5a2d66; }
.how { color: #7a5a80; margin: 2px 0 8px; }
.pill { display: inline-block; padding: 3px 12px; border-radius: 999px; margin: 3px 4px 3px 0;
  font-size: .95rem; background: #f3e8ff; color: #5a2d66; }
.pill.ok { background: #dcf8e2; color: #1f7a37; }
.pill.no { background: #f1eef3; color: #9a8aa3; }
.topic { display: inline-block; padding: 3px 12px; border-radius: 999px; background: #e0f2ff; color: #1d5f8a;
  font-weight: 600; font-size: .9rem; }
.question { font-size: 2rem; font-weight: 700; color: #3b2350; margin: 10px 0 6px; line-height: 1.3; }
.locked { background: #f6f0fa; border: 2px dashed #d9c4e6; border-radius: 14px; padding: 10px 14px;
  color: #8a6a96; margin: 6px 0; }
.clue { background: #fffbe6; border: 2px solid #ffe28a; border-radius: 14px; padding: 10px 14px;
  color: #6b4e00; margin: 6px 0; }
.scroll { overflow-x: auto; }
table.week { border-collapse: collapse; width: 100%; font-size: .92rem; background: rgba(255,255,255,.9); }
table.week th, table.week td { text-align: center; padding: 5px 4px; border-bottom: 1px solid #f6d6ea; }
table.week th { color: #6b3f73; font-weight: 600; }
table.week td.name { text-align: left; white-space: nowrap; }
table.week tr.star td { font-weight: 600; background: #fffbe6; }
.badge-grid { display: flex; flex-wrap: wrap; gap: 14px; justify-content: center; }
.bdg { width: 112px; text-align: center; }
.medal { position: relative; width: 84px; height: 84px; margin: 0 auto; border-radius: 50%; display: flex;
  align-items: center; justify-content: center; font-size: 40px; border: 4px solid #fff;
  box-shadow: 0 0 0 3px var(--c2), 0 6px 14px rgba(0,0,0,.12); }
.medal::before, .medal::after { content: ""; position: absolute; bottom: -16px; width: 16px; height: 24px;
  background: var(--c2); z-index: -1; clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 75%, 0 100%); }
.medal::before { left: 18px; transform: rotate(14deg); } .medal::after { right: 18px; transform: rotate(-14deg); }
.medal .shine { position: absolute; top: 8px; left: 14px; width: 18px; height: 10px; border-radius: 50%;
  background: rgba(255,255,255,.75); transform: rotate(-30deg); }
.bname { font-weight: 700; color: #5a2d66; margin-top: 14px; font-size: .95rem; line-height: 1.15; }
.bdesc { color: #8a6a96; font-size: .78rem; line-height: 1.2; margin-top: 2px; }
.bdg.bdg-off .medal { filter: grayscale(1); opacity: .45; }
.bdg.bdg-off .bname { color: #a99bb0; }
.bdg.small { width: 86px; } .bdg.small .medal { width: 58px; height: 58px; font-size: 28px; }
.bdg.small .medal::before, .bdg.small .medal::after { width: 12px; height: 18px; bottom: -12px; }
.bdg.small .medal::before { left: 12px; } .bdg.small .medal::after { right: 12px; }
.bdg.small .bname { font-size: .8rem; margin-top: 10px; }
.pet-wrap { text-align: center; }
.pet-wrap svg { max-width: 100%; height: auto; }
.pet-hop { animation: hop 2.2s ease-in-out infinite; transform-origin: 50% 100%; }
.pet-sleep { animation: breathe 4s ease-in-out infinite; transform-origin: 50% 100%; }
@keyframes hop { 0%,100% { transform: translateY(0); } 45% { transform: translateY(-10px) scaleY(1.03); } 60% { transform: translateY(0) scaleY(.97); } }
@keyframes breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.02, .985); } }
.pet-name { font-size: 1.5rem; font-weight: 700; color: #5a2d66; }
.wotd { font-size: 2.2rem; font-weight: 700; color: #ff4fa3; }
.story { background: #fffefb; border: 2px solid #f6e3b5; border-radius: 16px; padding: 12px 16px;
  color: #3b2350; line-height: 1.6; font-size: 1.05rem; }
.note { background: #e9fbef; border-left: 5px solid #5cc97f; border-radius: 12px; padding: 8px 12px;
  color: #1f5c33; margin-top: 8px; }
.celebrate { position: fixed; inset: 0; display: flex; flex-direction: column; align-items: center;
  justify-content: center; pointer-events: none; z-index: 99999; animation: fadeaway 2.4s forwards; }
.celebrate .thumb { font-size: 130px; animation: popin .55s cubic-bezier(.2,1.6,.4,1); filter: drop-shadow(0 8px 16px rgba(0,0,0,.2)); }
.celebrate .burst { font-size: 46px; letter-spacing: 6px; animation: popin .8s ease-out; }
.celebrate .word { font-size: 2.4rem; font-weight: 700; color: #ff4fa3; text-shadow: 0 3px 0 #fff, 0 6px 12px rgba(0,0,0,.15); }
@keyframes popin { 0% { transform: scale(.2) rotate(-20deg); opacity: 0; } 100% { transform: scale(1) rotate(0); opacity: 1; } }
@keyframes fadeaway { 0%, 70% { opacity: 1; } 100% { opacity: 0; visibility: hidden; } }
.float { cursor: pointer; z-index: 3; user-select: none; -webkit-tap-highlight-color: transparent; }
.chalisa { background: linear-gradient(135deg,#fff7ec,#ffefd9); border: 2px solid #ffc98a; border-radius: 18px;
  padding: 14px 18px; color: #5a2d00; font-size: 1.12rem; line-height: 1.85; }
.chalisa .ln { display: block; }
.chalisa .ln b { color: #c25400; }
.chalisa-head { font-size: 1.15rem; font-weight: 700; color: #a34700; }
.beads { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; justify-content: center; margin: 6px 0; }
.bead { width: 20px; height: 20px; border-radius: 50%; background: #f1e6da; border: 2px solid #e5d3bf; }
.bead.on { background: radial-gradient(circle at 35% 30%, #ffd9a8, #e07b1f 60%, #a94f00);
  border-color: #a94f00; box-shadow: 0 2px 4px rgba(169,79,0,.35); }
.friend { position: fixed; left: 0; z-index: 6; pointer-events: none; font-size: 38px; transform: translateX(110vw); }
.friend span { display: inline-block; pointer-events: auto; cursor: pointer; padding: 6px;
  -webkit-tap-highlight-color: transparent; user-select: none; }
.critter { position: fixed; left: 0; z-index: 4; pointer-events: none; font-size: 36px; will-change: transform; }
.critter span { display: inline-block; }
.critter.bunny { bottom: 10px; animation: run-across 38s linear 5s infinite; transform: translateX(110vw); }
.critter.bunny span { animation: hop-small .45s ease-in-out infinite; }
.critter.unicorn { bottom: 64px; font-size: 40px; animation: run-across 55s linear 26s infinite; transform: translateX(110vw); }
.critter.unicorn span { animation: hop-big .8s ease-in-out infinite; }
@keyframes run-across { 0% { transform: translateX(110vw); } 16% { transform: translateX(-80px); } 100% { transform: translateX(-80px); } }
@keyframes hop-small { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-12px); } }
@keyframes hop-big { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-26px) rotate(-8deg); } }
</style>
"""

HEART_SVG = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='70' height='70'%3E"
             "%3Cpath d='M35 58 C 8 40, 8 14, 24 14 C 30 14, 35 19, 35 23 C 35 19, 40 14, 46 14 C 62 14, 62 40, 35 58 Z'"
             " fill='%23ff8fc7' fill-opacity='0.28'/%3E%3C/svg%3E")
THEME_CSS = {
    "rainbow": """.stApp { background:
        radial-gradient(circle at 8% 8%, rgba(255,182,217,.55) 0, transparent 32%),
        radial-gradient(circle at 92% 18%, rgba(196,170,255,.45) 0, transparent 34%),
        radial-gradient(circle at 15% 92%, rgba(160,220,255,.45) 0, transparent 34%),
        radial-gradient(circle at 88% 85%, rgba(255,236,150,.45) 0, transparent 30%),
        linear-gradient(180deg, #fff3fa 0%, #fdf0ff 50%, #eef8ff 100%); }""",
    "candy": """.stApp { background:
        repeating-linear-gradient(45deg, rgba(255,214,234,.75) 0 34px, rgba(214,255,240,.75) 34px 68px,
        rgba(255,246,200,.75) 68px 102px), #fff; }""",
    "ocean": """.stApp { background:
        radial-gradient(circle at 12% 20%, rgba(255,255,255,.7) 0 10px, transparent 11px),
        radial-gradient(circle at 85% 35%, rgba(255,255,255,.6) 0 14px, transparent 15px),
        radial-gradient(circle at 30% 75%, rgba(255,255,255,.55) 0 8px, transparent 9px),
        radial-gradient(circle at 70% 88%, rgba(255,255,255,.6) 0 12px, transparent 13px),
        linear-gradient(180deg, #e3f8ff 0%, #b8ecff 45%, #8fd8f7 100%); }""",
    "hearts": f""".stApp {{ background-color: #fff0f7; background-image: url("{HEART_SVG}"),
        linear-gradient(180deg, #fff0f7, #ffe0ef); background-size: 70px 70px, 100% 100%; }}""",
    "galaxy": """.stApp { background:
        radial-gradient(1.5px 1.5px at 20px 30px, #fff, transparent),
        radial-gradient(1.5px 1.5px at 90px 120px, #fff, transparent),
        radial-gradient(2px 2px at 160px 60px, #ffe9a8, transparent),
        radial-gradient(1px 1px at 130px 170px, #fff, transparent),
        radial-gradient(1.5px 1.5px at 60px 190px, #cbd8ff, transparent),
        radial-gradient(circle at 20% 20%, rgba(155,107,255,.55) 0, transparent 40%),
        radial-gradient(circle at 85% 70%, rgba(255,79,163,.45) 0, transparent 40%),
        linear-gradient(180deg, #1b1240 0%, #2a1b5e 50%, #120c2c 100%);
        background-size: 200px 200px, 200px 200px, 200px 200px, 200px 200px, 200px 200px, 100% 100%, 100% 100%, 100% 100%; }
        .block-container { background: rgba(255,255,255,.84); border-radius: 28px; padding: 1.5rem 1.4rem 2rem !important;
        margin-top: 1.2rem; }
        [data-testid="stHeader"] { background: transparent; }""",
    "unicorn": """.stApp { background:
        radial-gradient(circle at 15% 15%, rgba(255,214,165,.7) 0, transparent 35%),
        radial-gradient(circle at 85% 25%, rgba(202,180,255,.7) 0, transparent 38%),
        radial-gradient(circle at 50% 95%, rgba(160,255,230,.6) 0, transparent 40%),
        linear-gradient(160deg, #ffe6f2 0%, #f1e4ff 50%, #e1f7ff 100%); }""",
}
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


# ----------------------- bonus maths (optional, earns carrots) -----------------------
def make_extra_problem(topic: str, day: date, index: int):
    """dict(question, answer (Fraction or '<'/'>'/'='), hint, clue). Same topic+day+index = same problem."""
    rng = random.Random(f"{day.isoformat()}-{topic}-{index}")
    if topic == "fractions":
        kind = rng.choice(["add", "sub", "of", "equiv", "bigger"])
        if kind == "add":
            d = rng.choice([4, 5, 6, 8, 10, 12]); a = rng.randint(1, d - 2); b = rng.randint(1, d - 1 - a)
            return dict(question=f"{a}/{d} + {b}/{d} = ?", answer=Fraction(a + b, d), hint="Type a fraction, like 3/8",
                        clue=f"Same bottom number? Keep {d} and add the tops: {a} + {b}.")
        if kind == "sub":
            d = rng.choice([4, 5, 6, 8, 10, 12]); a = rng.randint(2, d - 1); b = rng.randint(1, a - 1)
            return dict(question=f"{a}/{d} − {b}/{d} = ?", answer=Fraction(a - b, d), hint="Type a fraction, like 2/5",
                        clue=f"Keep {d} on the bottom and take away the tops: {a} − {b}.")
        if kind == "of":
            d = rng.choice([2, 3, 4, 5, 8, 10]); a = rng.randint(1, d - 1); n = d * rng.randint(3, 12)
            return dict(question=f"What is {a}/{d} of {n}?", answer=Fraction(a * n, d), hint="Type a whole number",
                        clue=f"Find 1/{d} first: {n} ÷ {d}. Then multiply by {a}.")
        if kind == "equiv":
            d = rng.choice([2, 3, 4, 5, 6]); a = rng.randint(1, d - 1); m = rng.choice([2, 3, 4, 5])
            return dict(question=f"{a}/{d} = ?/{d * m}", answer=Fraction(a * m), hint="Type the missing top number",
                        clue=f"{d} × {m} = {d * m}, so do the same to the top: {a} × {m}.")
        d = rng.choice([5, 6, 8, 10, 12]); a, b = rng.sample(range(1, d), 2)
        return dict(question=f"Which is bigger: {a}/{d} or {b}/{d}?", answer=Fraction(max(a, b), d),
                    hint="Type the bigger fraction", clue="Same bottom number? The bigger top number is the bigger fraction.")
    if topic == "mult3":
        n, m = rng.randint(102, 499), rng.randint(2, 9)
        h, t, o = n // 100 * 100, n // 10 % 10 * 10, n % 10
        return dict(question=f"{n} × {m} = ?", answer=Fraction(n * m), hint="Type a whole number",
                    clue=f"Split {n} into {h} + {t} + {o}. Multiply each by {m}, then add them up.")
    if topic == "compare4":
        a = rng.randint(1000, 9999)
        style = rng.random()
        if style < .15:
            b = a
        elif style < .6:   # close numbers to make it tricky
            b = a + rng.choice([-1, 1]) * rng.choice([1, 9, 10, 90, 100, 900])
            b = min(max(b, 1000), 9999)
            if b == a:
                b = a + 1 if a < 9999 else a - 1
        else:
            b = rng.randint(1000, 9999)
        ans = "=" if a == b else (">" if a > b else "<")
        return dict(question=f"{a:,}  ☐  {b:,}", answer=ans, hint="Choose <, > or =",
                    clue="Compare the thousands first. If they're the same, compare the hundreds, then tens, then ones.")
    if topic == "add4":
        a, b = rng.randint(1000, 6999), rng.randint(1000, 2999)
        return dict(question=f"{a:,} + {b:,} = ?", answer=Fraction(a + b), hint="Type a whole number",
                    clue="Add ones, then tens, then hundreds, then thousands. Carry 1 when a column makes 10 or more.")
    if topic == "sub4":
        a = rng.randint(3000, 9999); b = rng.randint(1000, a - 500)
        return dict(question=f"{a:,} − {b:,} = ?", answer=Fraction(a - b), hint="Type a whole number",
                    clue="Start with the ones. If the top digit is smaller, borrow 1 from the next column.")
    if topic == "decimals":
        kind = rng.choice(["add1", "sub1", "add2", "sub2"])
        places = 1 if kind.endswith("1") else 2
        scale = 10 ** places
        if kind.startswith("add"):
            a, b = rng.randint(11, 9 * scale), rng.randint(11, 9 * scale)
            q, ans = f"{a / scale:.{places}f} + {b / scale:.{places}f} = ?", Fraction(a + b, scale)
        else:
            a = rng.randint(2 * scale, 15 * scale); b = rng.randint(1, a - 1)
            q, ans = f"{a / scale:.{places}f} − {b / scale:.{places}f} = ?", Fraction(a - b, scale)
        return dict(question=q, answer=ans, hint=f"Type a decimal, like {'3.4' if places == 1 else '3.45'}",
                    clue="Line up the decimal points, then add or subtract column by column, just like whole numbers.")
    # div3: up to 3-digit ÷ 1-digit, always exact
    dv = rng.randint(2, 9); q = rng.randint(12, 999 // dv)
    return dict(question=f"{dv * q} ÷ {dv} = ?", answer=Fraction(q), hint="Type a whole number",
                clue=f"How many {dv}s fit into {dv * q}? Try dividing the hundreds first, then tens, then ones.")


# ------------------------------- dates & rules -------------------------------
def today_local() -> date:
    return datetime.now(ZoneInfo(TIMEZONE)).date()


def default_data():
    return {"days": {}, "claims": {}, "dollars_paid": 0, "history": [], "maths": {},
            "credits": [], "used": [], "balance_start": None, "spins": [], "carrots": 0, "toy_fund": 0,
            "last_restaurant": None, "pet": {"name": "Bunnicorn", "wear": {}}, "theme": "rainbow",
            "badges_earned": {}, "stories": [], "wotd_custom": {}, "word_wins": [], "moods": [],
            "messages": [], "facts": {}, "chalisa": {}, "bead_rewards_given": 0, "chalisa_reward": None}


def migrate(data, today: date):
    """Bring older saved progress up to date (safe to run every time)."""
    if not data.get("balance_start"):
        data["balance_start"] = today.isoformat()
        if data.get("bonus_bank"):
            data["credits"].append({"date": today.isoformat(), "minutes": int(data["bonus_bank"]),
                                    "reason": "Singing bonus minutes moved into balance"})
    data.pop("bonus_bank", None)
    data.pop("bonus_used", None)
    # One-time: carry forward unused minutes earned before the balance started (old rules: only
    # speaking was a must-do back then). Grown-ups can still adjust the balance by hand if needed.
    if not data.get("carried_over"):
        start = data["balance_start"]
        for k in sorted(data["days"]):
            if k < start:
                done = set(data["days"][k])
                old_mins = min(sum(TASK_BY_ID[t]["minutes"] for t in done if t in TASK_BY_ID and t != "homework"),
                               DAILY_GOAL_MINUTES) if "speak" in done else 0
                if old_mins:
                    data["credits"].append({"date": k, "minutes": old_mins,
                                            "reason": f"Unused minutes carried over from {k}"})
        data["carried_over"] = True
    data.setdefault("earned", {})
    if not data.get("approval_start"):
        data["approval_start"] = today.isoformat()
        data.setdefault("approved", {})[today.isoformat()] = list(data["days"].get(today.isoformat(), []))
    data.setdefault("approved", {})
    # One-time: days that must count as star days (e.g. the first day, before the rules changed)
    fixed = data.setdefault("star_fixes_done", [])
    for k in STAR_DAY_FIXES:
        if k not in fixed:
            day = set(data["days"].get(k, []))
            day.add("star")
            data["days"][k] = sorted(day)
            fixed.append(k)
    data.setdefault("pet", {}).setdefault("wear", {})
    data["pet"].setdefault("name", "Bunnicorn")
    return data


def counted_set(data, key: str) -> set:
    """Tasks that COUNT for rewards: ticked AND approved (grown-up or auto-checked). Older days count as ticked."""
    ticked = set(data["days"].get(key, []))
    start = data.get("approval_start")
    if not start or key < start:
        return ticked
    ok = set(data.get("approved", {}).get(key, []))
    return (ticked & ok) | ({"star"} & ticked)


def counted_days(data) -> dict:
    return {k: counted_set(data, k) for k in data["days"]}


def done_on(data, d: date) -> set:
    return counted_set(data, d.isoformat())


def ticked_on(data, d: date) -> set:
    return set(data["days"].get(d.isoformat(), []))


def pending_on(data, d: date) -> set:
    return (ticked_on(data, d) - done_on(data, d)) & set(TASK_BY_ID)


def task_minutes(done: set) -> int:
    if "star" in done:          # a day a grown-up marked as a star day
        return DAILY_GOAL_MINUTES
    if not all(t["id"] in done for t in TASKS if t.get("required")):
        return 0
    return min(sum(TASK_BY_ID[t]["minutes"] for t in done if t in TASK_BY_ID), DAILY_GOAL_MINUTES)


def is_star_day(done: set) -> bool:
    if "star" in done:
        return True
    return task_minutes(done) >= DAILY_GOAL_MINUTES


def balance_info(data):
    start = data.get("balance_start") or "0000"
    locked = data.get("earned", {})   # each day's minutes are locked in, so later rule changes don't alter them
    earned = sum(locked.get(k, task_minutes(v)) for k, v in counted_days(data).items() if k >= start)
    credits = sum(int(c["minutes"]) for c in data.get("credits", []))
    used = sum(int(u["minutes"]) for u in data.get("used", []))
    return {"earned": earned, "credits": credits, "used": used, "balance": max(earned + credits - used, 0)}


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


def max_streak(data, tid: str) -> int:
    days = sorted(date.fromisoformat(k) for k, v in counted_days(data).items() if tid in v)
    best = cur = 0
    prev = None
    for d in days:
        cur = cur + 1 if prev and d - prev == timedelta(days=1) else 1
        best, prev = max(best, cur), d
    return best


def dollar_status(data):
    stars = sum(is_star_day(v) for v in counted_days(data).values())
    earned = stars // STAR_DAYS_PER_DOLLAR
    return {"owed": earned - data.get("dollars_paid", 0),
            "toward_next": stars % STAR_DAYS_PER_DOLLAR, "paid": data.get("dollars_paid", 0)}


def star_run_ending(data, end: date, after=None) -> int:
    n, d = 0, end
    while is_star_day(done_on(data, d)) and (after is None or d > after):
        n += 1
        d -= timedelta(days=1)
    return n


def small_wheel_status(data, today: date):
    t = today.isoformat()
    if any(s["wheel"] == "small" and s["date"] == t for s in data.get("spins", [])):
        return {"ok": False, "why": "You've had today's small spin. Earn another star day tomorrow! 🌟"}
    if not is_star_day(done_on(data, today)):
        return {"ok": False, "why": f"Earn all {DAILY_GOAL_MINUTES} minutes today (a ⭐ star day) to spin!"}
    return {"ok": True, "why": ""}


def big_wheel_status(data, today: date):
    t = today.isoformat()
    bigs = [s for s in data.get("spins", []) if s["wheel"] == "big"]
    week_start = today - timedelta(days=today.weekday())
    this_week = [s for s in bigs if date.fromisoformat(s["date"]) >= week_start]
    last = max((date.fromisoformat(s["date"]) for s in bigs), default=None)
    run_end = today if is_star_day(done_on(data, today)) else today - timedelta(days=1)
    run = star_run_ending(data, run_end, after=last)
    info = {"run": min(run, BIG_WHEEL_STREAK), "week_used": len(this_week)}
    if any(s["date"] == t for s in bigs):
        return {**info, "ok": False, "why": "You've had a big spin today! 🦄"}
    if len(this_week) >= BIG_SPINS_PER_WEEK:
        return {**info, "ok": False,
                "why": f"You've used both big spins this week. New spins from Monday! 🗓️"}
    if not is_star_day(done_on(data, today)) or run < BIG_WHEEL_STREAK:
        return {**info, "ok": False,
                "why": f"Get {BIG_WHEEL_STREAK} ⭐ star days in a row to unlock a big spin "
                       f"({min(run, BIG_WHEEL_STREAK)}/{BIG_WHEEL_STREAK} so far)."}
    return {**info, "ok": True, "why": ""}


def restaurant_ready_from(data):
    last = data.get("last_restaurant")
    return date.fromisoformat(last) + timedelta(days=RESTAURANT_GAP_DAYS) if last else None


FRACTION_RE = re.compile(r"\d/\d|\bof\b")
DECIMAL_RE = re.compile(r"\d\.\d")


def compute_stats(data):
    days = counted_days(data)
    logs = [q for m in data.get("maths", {}).values() for q in m.get("log", [])]

    def count(tid):
        return sum(tid in v for v in days.values())

    return {
        "active_days": sum(1 for v in days.values() if v),
        "star_days": sum(is_star_day(set(v)) for v in days.values()),
        "speak_days": count("speak"), "read_days": count("read"), "sing_days": count("sing"),
        "sit2_days": count("sit2"), "exercise_days": count("exercise"), "homework_days": count("homework"),
        "max_speak_streak": max_streak(data, "speak"), "max_bed_streak": max_streak(data, "bed"),
        "maths_solved": len(logs),
        "fraction_solved": sum(1 for q in logs if FRACTION_RE.search(q)),
        "decimal_solved": sum(1 for q in logs if DECIMAL_RE.search(q) and "$" not in q),
        "stories": len(data.get("stories", [])), "word_wins": len(data.get("word_wins", [])),
        "spins": len(data.get("spins", [])), "moods": len(data.get("moods", [])),
        "chalisa_parts": len(data.get("chalisa", {})),
    }


def pet_stage(star_days):
    stage = PET_STAGES[0]
    for s in PET_STAGES:
        if star_days >= s[0]:
            stage = s
    nxt = next((s for s in PET_STAGES if s[0] > star_days), None)
    return stage, nxt


def last_star_day(data):
    stars = [k for k, v in counted_days(data).items() if is_star_day(v)]
    return date.fromisoformat(max(stars)) if stars else None


def word_of_the_day(data, day: date):
    custom = data.get("wotd_custom", {}).get(day.isoformat())
    if custom:
        return custom
    w, meaning, example = WORDS_OF_THE_DAY[day.toordinal() % len(WORDS_OF_THE_DAY)]
    return {"word": w, "meaning": meaning, "example": example}


def count_word(text: str, word: str) -> int:
    if not word:
        return 0
    return len(re.findall(r"\b" + re.escape(word.lower()) + r"\w*", text.lower()))


def bead_status(d):
    beads = BEADS_PER_PART * len(d.get("chalisa", {}))
    return {"beads": beads, "toward": beads % BEADS_FOR_MINUTES, "rewards_due": beads // BEADS_FOR_MINUTES,
            "all_done": len(d.get("chalisa", {})) >= len(CHALISA_PARTS)}


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def story_problem(text: str, earlier_texts=()):
    """Returns a friendly reason if a story looks copied, repeated or made up of nonsense; otherwise None."""
    words = re.findall(r"[a-z']+", text.lower())
    if len(words) < 10:
        return None
    if len(set(words)) / len(words) < 0.4:
        return "Lots of the same words over and over. Write your own new sentences! ✏️"
    if any(words[i] == words[i + 1] == words[i + 2] for i in range(len(words) - 2)):
        return "The same word three times in a row? Make your sentences make sense! ✏️"
    sentences = [_norm(x) for x in re.split(r"[.!?\n]+", text) if len(_norm(x).split()) >= 3]
    if len(sentences) != len(set(sentences)):
        return "Some sentences are copied more than once. Every sentence should be new! ✏️"
    no_vowel = sum(1 for w in words if len(w) > 2 and not re.search(r"[aeiouy]", w))
    if no_vowel / len(words) > 0.25:
        return "Some of those don't look like real words. Write a real story! ✏️"
    import difflib
    me = _norm(text)
    for old in earlier_texts:
        if difflib.SequenceMatcher(None, me, _norm(old)).ratio() > 0.8:
            return "This looks like a story you've already written. Write a brand-new one! ✏️"
    return None


def good_sentence(sentence: str, word: str) -> bool:
    return count_word(sentence, word) > 0 and count_words(sentence) >= WORD_SENTENCE_MIN_WORDS \
        and story_problem(sentence) is None


def wotd_uses(d, day_key: str, word: str) -> int:
    """Uses of the word today: different good sentences in the word box + uses in today's genuine stories."""
    sents = d.get("wotd_sentences", {}).get(day_key, [])
    seen, in_sentences = set(), 0
    for x in sents:
        n = _norm(x)
        if good_sentence(x, word) and n not in seen:
            seen.add(n)
            in_sentences += 1
    in_stories = sum(count_word(x["text"], word) for x in d.get("stories", [])
                     if x["date"] == day_key and x.get("ok", True))
    return in_sentences + in_stories


def award_word_win(d, day_key: str, word: str, info: dict):
    if wotd_uses(d, day_key, word) >= WORD_CHALLENGE_USES and day_key not in d.setdefault("word_wins", []):
        d["word_wins"].append(day_key)
        d.setdefault("credits", []).append({"date": day_key, "minutes": WORD_CHALLENGE_MINUTES,
                                            "reason": f"Word of the day challenge: {word}"})
        info["word_win"] = True


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def add_fact(d, today_key, info):
    seen = d.setdefault("facts", {}).setdefault(today_key, [])
    pool = [i for i in range(len(FUN_FACTS)) if i not in seen] or list(range(len(FUN_FACTS)))
    i = random.choice(pool)
    seen.append(i)
    info["fact"] = i


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
            return migrate(default_data(), today_local()), None
        r.raise_for_status()
        body = r.json()
        data = json.loads(base64.b64decode(body["content"]).decode())
        return migrate({**default_data(), **data}, today_local()), body["sha"]
    if LOCAL_FILE.exists():
        return migrate({**default_data(), **json.loads(LOCAL_FILE.read_text())}, today_local()), None
    return migrate(default_data(), today_local()), None


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
            if change(data) is False:      # the change decided not to save
                st.session_state.data, st.session_state.sha = data, sha
                return False
            tk = today_local().isoformat()
            data.setdefault("earned", {})[tk] = task_minutes(counted_set(data, tk))
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


def pin_ok(key) -> bool:
    return str(st.session_state.get(key, "")).strip() == parent_pin()


# ------------------------------- bunny drawing -------------------------------
def _bunny_parts(stage, sleepy, wear):
    fur, line = "#ffffff", "#efc3dc"
    if stage == "beautiful":
        fur = "#fff4fb"
    if stage == "magical":
        fur = "#fdf3ff"
    p = []
    # back accessories (behind the body)
    if wear.get("back") == "wings":
        p.append('<g opacity=".85"><ellipse cx="52" cy="140" rx="30" ry="46" transform="rotate(-28 52 140)" '
                 'fill="#d9f1ff" stroke="#9fd6ff" stroke-width="3"/><ellipse cx="148" cy="140" rx="30" ry="46" '
                 'transform="rotate(28 148 140)" fill="#ffe0f3" stroke="#ffa6d6" stroke-width="3"/>'
                 '<ellipse cx="62" cy="182" rx="18" ry="26" transform="rotate(-50 62 182)" fill="#fff3c4" '
                 'stroke="#ffd96b" stroke-width="3"/><ellipse cx="138" cy="182" rx="18" ry="26" '
                 'transform="rotate(50 138 182)" fill="#e4dcff" stroke="#b9a6ff" stroke-width="3"/></g>')
    if wear.get("back") == "cape":
        p.append('<path d="M66 128 Q100 120 134 128 L160 214 Q100 226 40 214 Z" fill="url(#rainbowcape)" '
                 'stroke="#fff" stroke-width="2"/>')
    # ears
    for cx, rot in ((78, -12), (122, 12)):
        p.append(f'<ellipse cx="{cx}" cy="40" rx="15" ry="40" transform="rotate({rot} {cx} 80)" fill="{fur}" '
                 f'stroke="{line}" stroke-width="3"/>')
        p.append(f'<ellipse cx="{cx}" cy="44" rx="7" ry="28" transform="rotate({rot} {cx} 80)" fill="#ffc4dd"/>')
    # body, feet, arms
    p.append(f'<ellipse cx="100" cy="172" rx="52" ry="45" fill="{fur}" stroke="{line}" stroke-width="3"/>')
    p.append('<ellipse cx="100" cy="182" rx="30" ry="28" fill="#fff7fb"/>')
    for cx in (72, 128):
        p.append(f'<ellipse cx="{cx}" cy="212" rx="19" ry="10" fill="{fur}" stroke="{line}" stroke-width="3"/>')
        p.append(f'<ellipse cx="{cx}" cy="212" rx="8" ry="4" fill="#ffd3e6"/>')
    p.append(f'<ellipse cx="70" cy="166" rx="10" ry="15" transform="rotate(20 70 166)" fill="{fur}" '
             f'stroke="{line}" stroke-width="3"/>')
    p.append(f'<ellipse cx="130" cy="166" rx="10" ry="15" transform="rotate(-20 130 166)" fill="{fur}" '
             f'stroke="{line}" stroke-width="3"/>')
    # neck accessories
    if wear.get("neck") == "scarf":
        p.append('<rect x="64" y="132" width="72" height="15" rx="7.5" fill="#ff6fa8"/>'
                 '<rect x="106" y="138" width="14" height="32" rx="6" transform="rotate(12 113 138)" fill="#ff8fbd"/>'
                 '<path d="M72 135 v9 M84 135 v9 M96 135 v9 M108 135 v9 M120 135 v9" stroke="#fff" '
                 'stroke-width="2" opacity=".7"/>')
    if wear.get("neck") == "necklace":
        p.append('<path d="M70 132 Q100 156 130 132" fill="none" stroke="#ffd23f" stroke-width="3"/>'
                 '<circle cx="80" cy="141" r="3.5" fill="#9b6bff"/><circle cx="90" cy="146" r="3.5" fill="#38b6ff"/>'
                 '<circle cx="110" cy="146" r="3.5" fill="#3fbf5a"/><circle cx="120" cy="141" r="3.5" fill="#ff9f43"/>'
                 '<path d="M100 146 l7 7 l-7 9 l-7 -9 z" fill="#ff4fa3" stroke="#fff" stroke-width="1.5"/>')
    # head
    p.append(f'<circle cx="100" cy="100" r="46" fill="{fur}" stroke="{line}" stroke-width="3"/>')
    for cx in (75, 125):
        p.append(f'<ellipse cx="{cx}" cy="113" rx="9" ry="6" fill="#ffb3d1" opacity=".85"/>')
    if sleepy:
        p.append('<path d="M75 98 Q83 105 91 98" stroke="#3b2350" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
                 '<path d="M109 98 Q117 105 125 98" stroke="#3b2350" stroke-width="3.5" fill="none" stroke-linecap="round"/>')
    else:
        for cx in (83, 117):
            p.append(f'<ellipse cx="{cx}" cy="96" rx="7.5" ry="9.5" fill="#3b2350"/>'
                     f'<circle cx="{cx + 2.5}" cy="92" r="3" fill="#fff"/><circle cx="{cx - 2}" cy="100" r="1.4" fill="#fff"/>')
        if stage in ("beautiful", "magical"):
            p.append('<path d="M74 89 l-5 -4 M77 86 l-3 -5 M126 89 l5 -4 M123 86 l3 -5" stroke="#3b2350" '
                     'stroke-width="2.2" stroke-linecap="round"/>')
    p.append('<path d="M95 107 Q100 103 105 107 Q100 113 95 107 Z" fill="#ff7fb0"/>')
    p.append('<path d="M91 115 Q95.5 120 100 115 Q104.5 120 109 115" stroke="#3b2350" stroke-width="2.4" '
             'fill="none" stroke-linecap="round"/>')
    # face accessories
    if wear.get("face") == "glasses" and not sleepy:
        p.append('<rect x="70" y="86" width="26" height="18" rx="7" fill="#3b2350" opacity=".92"/>'
                 '<rect x="104" y="86" width="26" height="18" rx="7" fill="#3b2350" opacity=".92"/>'
                 '<path d="M96 93 Q100 90 104 93" stroke="#3b2350" stroke-width="3" fill="none"/>'
                 '<path d="M74 90 l6 0" stroke="#fff" stroke-width="2" opacity=".7"/>'
                 '<path d="M108 90 l6 0" stroke="#fff" stroke-width="2" opacity=".7"/>')
    # head accessories
    head = wear.get("head")
    if head == "bow":
        p.append('<path d="M134 62 L117 50 L119 74 Z" fill="#ff5fa2"/><path d="M134 62 L151 50 L149 74 Z" fill="#ff5fa2"/>'
                 '<circle cx="134" cy="62" r="6" fill="#ff8fc0"/>')
    elif head == "flowers":
        cols = ["#ff8fc0", "#ffd23f", "#9b6bff", "#5cc97f", "#38b6ff", "#ff9f43"]
        for i, x in enumerate((66, 79, 93, 107, 121, 134)):
            y = 64 - (6 if 79 <= x <= 121 else 0) - (3 if 93 <= x <= 107 else 0)
            p.append(f'<circle cx="{x}" cy="{y}" r="7.5" fill="{cols[i]}"/><circle cx="{x}" cy="{y}" r="2.8" fill="#fff6c9"/>')
    elif head == "tophat":
        p.append('<rect x="70" y="50" width="60" height="9" rx="4.5" fill="#4b2a6b"/>'
                 '<rect x="81" y="16" width="38" height="38" rx="4" fill="#5b3480"/>'
                 '<rect x="81" y="42" width="38" height="7" fill="#ff6fa8"/><circle cx="112" cy="45" r="4" fill="#ffd23f"/>')
    elif head == "crown":
        p.append('<path d="M72 60 L76 30 L89 46 L100 22 L111 46 L124 30 L128 60 Z" fill="#ffd23f" stroke="#e0a800" '
                 'stroke-width="2.5" stroke-linejoin="round"/><circle cx="100" cy="47" r="5" fill="#ff4fa3"/>'
                 '<circle cx="85" cy="52" r="3.5" fill="#38b6ff"/><circle cx="115" cy="52" r="3.5" fill="#3fbf5a"/>')
    elif head == "horn":
        p.append('<path d="M100 6 L89 58 L111 58 Z" fill="url(#horngold)" stroke="#e0a800" stroke-width="2"/>'
                 '<path d="M92 46 L107 40 M94 34 L104 30 M96 22 L102 19" stroke="#fff" stroke-width="2.5" '
                 'stroke-linecap="round" opacity=".8"/>')
    if stage in ("beautiful", "magical"):
        for x, y, s in ((30, 60, 1), (170, 70, .8), (160, 190, .9), (35, 175, .7)):
            p.append(f'<path transform="translate({x} {y}) scale({s})" d="M0 -9 L2.5 -2.5 L9 0 L2.5 2.5 L0 9 '
                     f'L-2.5 2.5 L-9 0 L-2.5 -2.5 Z" fill="#ffd23f"/>')
    return p


def pet_svg(stage_id, sleepy=False, wear=None, size=200):
    wear = wear or {}
    defs = ('<defs><linearGradient id="rainbowcape" x1="0" x2="1"><stop offset="0" stop-color="#ff7fb0"/>'
            '<stop offset=".25" stop-color="#ffb35c"/><stop offset=".5" stop-color="#ffe066"/>'
            '<stop offset=".75" stop-color="#7fd99a"/><stop offset="1" stop-color="#7fb8ff"/></linearGradient>'
            '<linearGradient id="horngold" x1="0" x2="1"><stop offset="0" stop-color="#fff3b0"/>'
            '<stop offset="1" stop-color="#ffc93c"/></linearGradient>'
            '<radialGradient id="aura"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".7" stop-color="#e7c6ff" stop-opacity=".55"/><stop offset="1" stop-color="#ffd0ea" '
            'stop-opacity="0"/></radialGradient></defs>')
    parts = []
    if stage_id in ("egg", "hatching"):
        spots = ('<circle cx="78" cy="110" r="9" fill="#ffd0e6"/><circle cx="122" cy="96" r="7" fill="#d9ccff"/>'
                 '<circle cx="118" cy="160" r="10" fill="#c9f0ff"/><circle cx="74" cy="168" r="7" fill="#fff0a8"/>'
                 '<circle cx="100" cy="130" r="5" fill="#c7f5d9"/>')
        if stage_id == "egg":
            parts.append('<path d="M100 36 C 142 36, 164 120, 160 160 C 156 200, 130 220, 100 220 C 70 220, 44 200, '
                         '40 160 C 36 120, 58 36, 100 36 Z" fill="#fff6fb" stroke="#f3c6e0" stroke-width="4"/>' + spots)
        else:
            parts.append('<g transform="rotate(-6 100 120)">')
            for cx, rot in ((84, -14), (116, 14)):
                parts.append(f'<ellipse cx="{cx}" cy="58" rx="11" ry="28" transform="rotate({rot} {cx} 86)" '
                             'fill="#fff" stroke="#efc3dc" stroke-width="3"/>'
                             f'<ellipse cx="{cx}" cy="62" rx="5" ry="18" transform="rotate({rot} {cx} 86)" fill="#ffc4dd"/>')
            parts.append('<circle cx="100" cy="112" r="34" fill="#fff" stroke="#efc3dc" stroke-width="3"/>'
                         '<ellipse cx="88" cy="108" rx="5.5" ry="7" fill="#3b2350"/><ellipse cx="112" cy="108" rx="5.5" '
                         'ry="7" fill="#3b2350"/><circle cx="90" cy="105" r="2" fill="#fff"/><circle cx="114" cy="105" '
                         'r="2" fill="#fff"/><path d="M96 117 Q100 114 104 117 Q100 121 96 117 Z" fill="#ff7fb0"/></g>')
            parts.append('<path d="M42 130 L56 118 L70 132 L84 116 L100 132 L116 116 L130 132 L144 118 L158 130 '
                         'C 162 170, 140 220, 100 220 C 60 220, 38 170, 42 130 Z" fill="#fff6fb" stroke="#f3c6e0" '
                         'stroke-width="4" stroke-linejoin="round"/>'
                         '<circle cx="118" cy="170" r="10" fill="#c9f0ff"/><circle cx="76" cy="178" r="7" fill="#fff0a8"/>'
                         '<circle cx="98" cy="196" r="6" fill="#ffd0e6"/>')
        body = "".join(parts)
        anim = "pet-hop" if stage_id == "hatching" else "pet-sleep"
    else:
        scale = {"baby": .72, "little": .84, "big": .95, "beautiful": 1, "magical": 1}.get(stage_id, 1)
        if stage_id == "magical":
            parts.append('<circle cx="100" cy="128" r="100" fill="url(#aura)"/>')
        parts.append(f'<g transform="translate(100 224) scale({scale}) translate(-100 -224)">')
        parts.extend(_bunny_parts(stage_id, sleepy, wear))
        parts.append("</g>")
        if sleepy:
            parts.append('<text x="150" y="44" font-size="22" font-weight="700" fill="#8a7bb0">z</text>'
                         '<text x="164" y="28" font-size="28" font-weight="700" fill="#8a7bb0">Z</text>'
                         '<text x="182" y="14" font-size="18" font-weight="700" fill="#8a7bb0">z</text>')
        body = "".join(parts)
        anim = "pet-sleep" if sleepy else "pet-hop"
    return (f'<div class="pet-wrap"><svg class="{anim}" width="{size}" height="{int(size * 1.15)}" '
            f'viewBox="0 0 200 230" xmlns="http://www.w3.org/2000/svg">{defs}{body}</svg></div>')


# ---------------------------------- badges -----------------------------------
def badge_html(b, earned=True, small=False, show_desc=True):
    bid, emoji, name, desc, _stat, _need, c1, c2 = b
    if not earned:   # keep it a surprise: no name or picture until it's earned
        emoji, name = "❓", "Mystery badge"
    cls = "bdg" + ("" if earned else " bdg-off") + (" small" if small else "")
    desc_html = f'<div class="bdesc">{html_safe(desc)}</div>' if show_desc else ""
    return (f'<div class="{cls}"><div class="medal" style="--c2:{c2};background:radial-gradient(circle at 32% 28%, '
            f'#ffffff 0, {c1} 45%, {c2} 100%)"><span class="shine"></span>{emoji}</div>'
            f'<div class="bname">{html_safe(name)}</div>{desc_html}</div>')


# ------------------------------ sounds (Web Audio) ------------------------------
SOUND_ENGINE = r"""
(function(){
  if (window.__andalSound) return; window.__andalSound = true;
  var ctx = null;
  function ensure(){ if(!ctx){ try{ ctx = new (window.AudioContext||window.webkitAudioContext)(); }catch(e){ return null; } }
    if (ctx.state === 'suspended') { ctx.resume(); } return ctx; }
  function unlock(){ var c = ensure(); if(!c) return; try{ var b=c.createBuffer(1,1,22050), s=c.createBufferSource();
    s.buffer=b; s.connect(c.destination); s.start(0);}catch(e){} }
  ['pointerdown','touchend','click','keydown'].forEach(function(ev){ document.addEventListener(ev, unlock, {capture:true, passive:true}); });
  function note(c,f,t,d,type,vol){ var o=c.createOscillator(), g=c.createGain(); o.type=type||'sine'; o.frequency.value=f;
    g.gain.setValueAtTime(0.0001,t); g.gain.exponentialRampToValueAtTime(vol||0.25,t+0.02);
    g.gain.exponentialRampToValueAtTime(0.0001,t+d); o.connect(g); g.connect(c.destination); o.start(t); o.stop(t+d+0.05); }
  var SONGS = {
    chime:   [[659,0,.25],[784,.09,.25],[1047,.18,.3],[1319,.3,.45]],
    fanfare: [[523,0,.18],[659,.14,.18],[784,.28,.18],[1047,.44,.5],[784,.62,.15],[1047,.76,.6]],
    win:     [[784,0,.15],[988,.1,.15],[1175,.2,.15],[1568,.32,.55],[1319,.5,.2],[1568,.62,.7]],
    tick:    [[1800,0,.03]],
    pop:     [[880,0,.08],[1320,.05,.12]],
    sparkle: [[1568,0,.08],[1976,.07,.08],[2349,.14,.08],[3136,.21,.25]],
    tweet:   [[2600,0,.05],[3200,.07,.05],[2600,.16,.05],[3400,.23,.08]],
    grunt:   [[180,0,.18],[150,.2,.25]]
  };
  function slide(c, f1, f2, t, d, type, vol){ var o=c.createOscillator(), g=c.createGain(); o.type=type;
    o.frequency.setValueAtTime(f1,t); o.frequency.exponentialRampToValueAtTime(f2,t+d);
    g.gain.setValueAtTime(0.0001,t); g.gain.exponentialRampToValueAtTime(vol,t+0.02);
    g.gain.exponentialRampToValueAtTime(0.0001,t+d); o.connect(g); g.connect(c.destination); o.start(t); o.stop(t+d+0.05); }
  var JOKES = __JOKES__;
  document.addEventListener('click', function(e){
    var f = e.target && e.target.closest ? e.target.closest('[data-joke]') : null; if(!f) return;
    var list = JOKES[f.getAttribute('data-joke')] || []; if(!list.length) return;
    var old = document.getElementById('andal-bubble'); if(old) old.remove();
    var r = f.getBoundingClientRect(), b = document.createElement('div'); b.id = 'andal-bubble';
    b.textContent = list[Math.floor(Math.random()*list.length)];
    b.style.cssText = 'position:fixed;z-index:100000;max-width:260px;padding:12px 16px;border-radius:18px;'
      + 'background:#fff;border:3px solid #ff9ccc;color:#5a2d66;font:600 16px Fredoka,system-ui,sans-serif;'
      + 'box-shadow:0 8px 24px rgba(255,105,180,.3);transition:opacity .3s, transform .3s;opacity:0;transform:scale(.6)';
    document.body.appendChild(b);
    var left = Math.min(Math.max(8, r.left + r.width/2 - 130), window.innerWidth - 276);
    b.style.left = left + 'px'; b.style.top = Math.min(r.bottom + 8, window.innerHeight - 120) + 'px';
    requestAnimationFrame(function(){ b.style.opacity = '1'; b.style.transform = 'scale(1)'; });
    try { window.__andalPlay(f.getAttribute('data-sound') || 'pop'); } catch(err) {}
    setTimeout(function(){ b.style.opacity = '0'; b.style.transform = 'scale(.8)'; setTimeout(function(){ b.remove(); }, 350); }, 4500);
  }, true);
  window.__andalPlay = function(kind){ var c = ensure(); if(!c) return; var t = c.currentTime + 0.03;
    if (kind === 'boing') { slide(c, 220, 880, t, .18, 'sine', .3); slide(c, 330, 990, t+.2, .15, 'sine', .22); return; }
    (SONGS[kind]||SONGS.chime).forEach(function(n){ note(c, n[0], t+n[1], n[2], kind==='tick'?'square':'triangle', kind==='tick'?0.08:0.22); }); };
})();
"""


def _embed(html_doc, height):
    if hasattr(st, "iframe"):
        st.iframe(html_doc, height=height)
    else:  # older Streamlit versions
        import streamlit.components.v1 as components
        components.html(html_doc, height=height)


def install_sound_engine():
    jokes = dict(ICON_JOKES, **{f["id"]: f["says"] for f in FRIENDS})
    code = json.dumps(SOUND_ENGINE.replace("__JOKES__", json.dumps(jokes)))
    _embed("<script>try{var P=window.parent;if(!P.__andalSound){var s=P.document.createElement('script');"
           f"s.textContent={code};P.document.head.appendChild(s);}}}}catch(e){{}}</script>", 1)


def play_sound(kind):
    _embed(f"<script>/*{random.random()}*/setTimeout(function(){{try{{window.parent.__andalPlay('{kind}')}}"
           "catch(e){}}, 60);</script>", 1)


# ------------------------------------ wheel ------------------------------------
WHEEL_COLOURS = ["#ffd0e6", "#d9ccff", "#c9f0ff", "#fff0a8", "#c7f5d9", "#ffd9c2", "#f3d1ff", "#d1e8ff"]
WHEEL_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:'Fredoka',system-ui,-apple-system,sans-serif;text-align:center;background:transparent;overflow:hidden}
.wrap{position:relative;width:290px;height:290px;margin:8px auto 0}
#w{width:290px;height:290px;transform-origin:50% 50%;filter:drop-shadow(0 6px 14px rgba(255,105,180,.35))}
.pointer{position:absolute;top:-10px;left:50%;transform:translateX(-50%);font-size:36px;z-index:3}
.hub{position:absolute;top:50%;left:50%;width:64px;height:64px;margin:-32px 0 0 -32px;border-radius:50%;background:#fff;
 border:4px solid #ff8cc6;display:flex;align-items:center;justify-content:center;font-size:32px;z-index:2}
#res{min-height:64px;margin-top:10px;font-size:19px;font-weight:700;color:#5a2d66;padding:0 10px;line-height:1.35}
.conf{position:fixed;top:-40px;font-size:26px;animation:fall 2.8s linear forwards}
@keyframes fall{to{transform:translateY(520px) rotate(360deg);opacity:.2}}
@keyframes pop{0%{transform:scale(.3)}70%{transform:scale(1.15)}100%{transform:scale(1)}}
.prize{display:inline-block;animation:pop .6s;background:#fff3a8;border-radius:16px;padding:6px 12px;margin-top:4px}
</style></head><body>
<div class="wrap"><div class="pointer">🔻</div><svg id="w" viewBox="-110 -110 220 220">__SEGS__</svg><div class="hub">__HUB__</div></div>
<div id="res">__IDLE__</div>
<script>
var target=__TARGET__, n=__N__, prize=__PRIZE__;
function play(k){try{window.parent.__andalPlay&&window.parent.__andalPlay(k)}catch(e){}}
var w=document.getElementById('w'), res=document.getElementById('res');
if(target>=0){
  var seg=360/n, finalA=360*6+(360-(target*seg+seg/2)), last=-1, running=true;
  function angle(){var m=getComputedStyle(w).transform; if(!m||m==='none')return 0; var v=m.match(/matrix\\(([^)]+)\\)/);
    if(!v)return 0; var p=v[1].split(',').map(parseFloat); return (Math.atan2(p[1],p[0])*180/Math.PI+360)%360;}
  function watch(){ if(!running)return; var s=Math.floor(angle()/seg); if(s!==last){ if(last!==-1) play('tick'); last=s; } requestAnimationFrame(watch); }
  res.innerHTML='Spinning… 🌀';
  setTimeout(function(){ w.style.transition='transform 5s cubic-bezier(.12,.75,.15,1)'; w.style.transform='rotate('+finalA+'deg)'; watch(); },150);
  setTimeout(function(){ running=false; res.innerHTML='🎉 You won! 🎉<br><span class="prize">'+prize+'</span>'; play('win');
    var em=['🎉','✨','🦄','🐰','🌈','💖','⭐'];
    for(var i=0;i<26;i++){var c=document.createElement('div');c.className='conf';c.textContent=em[i%7];
      c.style.left=(Math.random()*100)+'%';c.style.animationDelay=(Math.random()*0.8)+'s';document.body.appendChild(c);} },5300);
}
</script></body></html>"""


def wheel_html(prizes, target=-1, hub="🎡", idle="", mystery=True):
    import math
    n = len(prizes)
    seg = 360 / n
    segs = []
    for i, p in enumerate(prizes):
        a0, a1 = math.radians(i * seg), math.radians((i + 1) * seg)
        x0, y0 = 100 * math.sin(a0), -100 * math.cos(a0)
        x1, y1 = 100 * math.sin(a1), -100 * math.cos(a1)
        large = 1 if seg > 180 else 0
        col = WHEEL_COLOURS[i % len(WHEEL_COLOURS)]
        segs.append(f'<path d="M0 0 L{x0:.2f} {y0:.2f} A100 100 0 {large} 1 {x1:.2f} {y1:.2f} Z" fill="{col}" '
                    f'stroke="#fff" stroke-width="2"/>')
        mid = (i + .5) * seg
        tx, ty = 70 * math.sin(math.radians(mid)), -70 * math.cos(math.radians(mid))
        segs.append(f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="19" text-anchor="middle" dominant-baseline="central" '
                    f'transform="rotate({mid:.1f} {tx:.2f} {ty:.2f})">{("🎁" if i % 2 == 0 else "❓") if mystery else p["emoji"]}</text>')
    segs.append('<circle r="104" fill="none" stroke="#ff8cc6" stroke-width="7"/>')
    prize_text = html_safe(f'{prizes[target]["emoji"]} {prizes[target]["name"]}') if target >= 0 else ""
    return (WHEEL_HTML.replace("__SEGS__", "".join(segs)).replace("__HUB__", hub)
            .replace("__IDLE__", html_safe(idle)).replace("__TARGET__", str(target)).replace("__N__", str(n))
            .replace("__PRIZE__", json.dumps(prize_text)))


SIT_TIMER = """
<div style="font-family:'Fredoka',system-ui,sans-serif;text-align:center;padding:10px;border-radius:16px;
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
var iv = null;
function play(k){ try { window.parent.__andalPlay && window.parent.__andalPlay(k); } catch(e){} }
function go(sec){ clearInterval(iv); var left = sec; var t = document.getElementById('t'); play('pop');
  var show = function(){ t.textContent = '🤫 ' + Math.floor(left/60) + ':' + String(left%60).padStart(2,'0'); };
  show(); iv = setInterval(function(){ left--; if(left<=0){ clearInterval(iv);
    t.textContent='🎉 Done! Show your grown-up'; play('fanfare'); } else show(); }, 1000); }
</script>
"""


# -------------------------------- certificates --------------------------------
def certificate_html(title, name, week_label, stats_pills, badges, standalone=False):
    pills = "".join(f'<span style="display:inline-block;margin:4px;padding:6px 12px;border-radius:999px;'
                    f'background:#fff;border:2px solid #ffd1e8;font-size:15px">{p}</span>' for p in stats_pills)
    bdg = ""
    if badges:
        bdg = ('<div style="margin-top:10px;font-size:15px;color:#7a5a80">New badges this week:</div>'
               f'<div style="font-size:30px;margin-top:2px">{" ".join(badges)}</div>')
    body = (f'<div style="max-width:640px;margin:10px auto;padding:26px 22px;border-radius:26px;text-align:center;'
            f'background:linear-gradient(135deg,#fff6fb,#f3ecff);border:7px double #ff9ccc;color:#3b2350;'
            f'font-family:Fredoka,system-ui,sans-serif;box-shadow:0 8px 24px rgba(255,105,180,.2)">'
            f'<div style="font-size:40px">🦄 🏆 🐰</div>'
            f'<div style="font-size:28px;font-weight:700;color:#a3236b;margin-top:4px">{title}</div>'
            f'<div style="font-size:16px;margin-top:8px">This certificate is proudly presented to</div>'
            f'<div style="font-size:44px;font-weight:700;color:#ff4fa3;margin:2px 0">{html_safe(name)}</div>'
            f'<div style="font-size:16px">for a wonderful week · {week_label}</div>'
            f'<div style="margin-top:12px">{pills}</div>{bdg}'
            f'<div style="margin-top:18px;font-size:15px;color:#7a5a80">Signed: ____________________ (Grown-up)</div>'
            f'<div style="font-size:26px;margin-top:6px">🌈 ⭐ 💖 ⭐ 🌈</div></div>')
    if not standalone:
        return body
    return ('<!doctype html><html><head><meta charset="utf-8"><title>Certificate</title>'
            '<link href="https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600;700&display=swap" rel="stylesheet">'
            '<style>body{background:#fff;margin:30px}@media print{body{margin:0}}</style></head><body>'
            f'{body}</body></html>')


FRIEND_MOVES = {
    "hop": "0%,100%{transform:translateY(0)}50%{transform:translateY(-12px)}",
    "gallop": "0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-24px) rotate(-8deg)}",
    "waddle": "0%,100%{transform:rotate(-8deg)}50%{transform:rotate(8deg) translateY(-3px)}",
    "fly": "0%,100%{transform:translateY(0) rotate(-4deg)}50%{transform:translateY(-30px) rotate(4deg)}",
    "bound": "0%,100%{transform:translateY(0) scaleY(1)}40%{transform:translateY(-36px) scaleY(1.05)}80%{transform:translateY(0) scaleY(.92)}",
    "flutter": "0%,100%{transform:translateY(0) scale(1)}25%{transform:translateY(-18px) scale(.9)}50%{transform:translateY(-6px) scale(1)}75%{transform:translateY(-24px) scale(.9)}",
}
MOVE_SPEED = {"hop": .45, "gallop": .8, "waddle": .7, "fly": 1.4, "bound": .9, "flutter": .6}


def friends_html():
    css, divs = [], []
    for f in FRIENDS:
        cross = 9.0  # seconds to cross the screen
        pct = max(2.0, min(60.0, 100 * cross / f["cycle"]))
        css.append(f"@keyframes run-{f['id']}{{0%{{transform:translateX(110vw)}}{pct:.2f}%{{transform:translateX(-90px)}}"
                   f"100%{{transform:translateX(-90px)}}}}@keyframes mv-{f['id']}{{{FRIEND_MOVES[f['move']]}}}"
                   f".fr-{f['id']}{{bottom:{f['bottom']}px;animation:run-{f['id']} {f['cycle']}s linear {f['delay']}s infinite}}"
                   f".fr-{f['id']} span{{animation:mv-{f['id']} {MOVE_SPEED[f['move']]}s ease-in-out infinite}}")
        divs.append(f'<div class="friend fr-{f["id"]}"><span data-joke="{f["id"]}" data-sound="{f["sound"]}" '
                    f'title="Tap me!">{f["emoji"]}</span></div>')
    return "<style>" + "".join(css) + "</style>" + "".join(divs)


# --------------------------- Tamil pronunciation ---------------------------
# Converts our English-letter Tamil (e.g. "veedu") into Tamil script (வீடு) so a Tamil voice can read it.
_TA_VOWELS = [("aa", "ஆ", "ா"), ("ai", "ஐ", "ை"), ("au", "ஔ", "ௌ"), ("ee", "ஈ", "ீ"), ("ii", "ஈ", "ீ"),
              ("oo", "ஊ", "ூ"), ("uu", "ஊ", "ூ"), ("ae", "ஏ", "ே"), ("a", "அ", ""), ("i", "இ", "ி"),
              ("u", "உ", "ு"), ("e", "எ", "ெ"), ("o", "ஒ", "ொ")]
_TA_CONS = [("ndr", ["ன", "ற"]), ("tr", ["ற", "ற"]), ("ndh", ["ந", "த"]), ("nth", ["ந", "த"]), ("ng", ["ங", "க"]), ("nj", ["ஞ", "ச"]), ("nd", ["ண", "ட"]),
            ("zh", ["ழ"]), ("th", ["த"]), ("dh", ["த"]), ("ch", ["ச"]), ("sh", ["ஷ"]), ("k", ["க"]), ("g", ["க"]),
            ("c", ["க"]), ("q", ["க"]), ("j", ["ஜ"]), ("s", ["ச"]), ("t", ["ட"]), ("d", ["ட"]), ("p", ["ப"]),
            ("b", ["ப"]), ("f", ["ஃப"]), ("v", ["வ"]), ("w", ["வ"]), ("m", ["ம"]), ("y", ["ய"]), ("r", ["ர"]),
            ("l", ["ல"]), ("h", ["ஹ"]), ("z", ["ஜ"]), ("x", ["க", "ஸ"])]
_PULLI = "்"
_ROMAN_VOWELS = "aeiou"
_HARD = {"k", "t", "p", "ch", "th", "c"}   # these sound hard in the middle of a word only when doubled in Tamil


def tamil_script(roman: str) -> str:
    out = []
    for word in re.split(r"(\W+)", roman.lower()):
        if not word or not re.match(r"[a-z]", word):
            out.append(word)
            continue
        if len(word) > 3 and word.endswith("en"):
            word = word[:-2] + "aen"          # spoken verb endings are long: vandhen -> வந்தேன்
        i, res, pending = 0, "", None   # pending = consonant waiting for its vowel
        while i < len(word):
            for v, ind, sign in _TA_VOWELS:
                if word.startswith(v, i):
                    if pending:
                        res += pending + sign
                        pending = None
                    else:
                        res += ind
                    i += len(v)
                    break
            else:
                cons = None
                for c, letters in _TA_CONS:
                    if word.startswith(c, i):
                        cons = (c, letters)
                        break
                if cons is None and word[i] == "n":
                    cons = ("n", ["ந"] if i == 0 else ["ன"])
                if cons is None:
                    i += 1
                    continue
                if pending:
                    res += pending + _PULLI
                after = i + len(cons[0])
                if (cons[0] in _HARD and len(cons[1]) == 1 and i > 0 and word[i - 1] in _ROMAN_VOWELS
                        and after < len(word) and word[after] in _ROMAN_VOWELS):
                    cons = (cons[0], cons[1] * 2)    # paati -> பாட்டி, saapidu -> சாப்பிடு
                for L in cons[1][:-1]:
                    res += L + _PULLI
                pending = cons[1][-1]
                i += len(cons[0])
        if pending:
            res += pending + _PULLI
        out.append(res)
    return "".join(out)


@st.cache_data(show_spinner=False, max_entries=2000)
def _gtts_b64(script: str):
    """Google Tamil voice via gTTS (needs internet). Raises on failure so failures aren't remembered."""
    from io import BytesIO
    from gtts import gTTS
    buf = BytesIO()
    gTTS(text=script, lang="ta", slow=False, timeout=5).write_to_fp(buf)
    return base64.b64encode(buf.getvalue()).decode()


def tamil_audio_b64(text: str, is_script=False):
    if st.session_state.get("tts_off"):
        return None
    try:
        return _gtts_b64(text if is_script else tamil_script(text))
    except Exception:
        st.session_state.tts_off = True   # use the iPad's own voice for the rest of this visit
        return None


SAY_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:Fredoka,system-ui,sans-serif;background:transparent}
.row{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;padding:4px}
button{font:600 15px Fredoka,system-ui,sans-serif;border:0;border-radius:999px;padding:9px 14px;cursor:pointer;
 background:linear-gradient(90deg,#ff7fbf,#9b6bff);color:#fff;box-shadow:0 3px 8px rgba(155,107,255,.3)}
button.slow{background:#f3e8ff;color:#5a2d66;box-shadow:none}
</style></head><body><div class="row">__BUTTONS__</div>
<script>
var ITEMS = __ITEMS__;
function voice(){ var vs = speechSynthesis.getVoices();
  return vs.find(function(x){return x.lang && x.lang.toLowerCase().indexOf('ta') === 0;}); }
function say(i, rate){
  var it = ITEMS[i];
  if (it.b64) { var a = new Audio('data:audio/mp3;base64,' + it.b64); a.playbackRate = rate; a.play().catch(function(){ speak(it, rate); }); return; }
  speak(it, rate);
}
function speak(it, rate){
  try { speechSynthesis.cancel(); var v = voice(), u;
    if (v) { u = new SpeechSynthesisUtterance(it.ta); u.voice = v; u.lang = v.lang; }
    else { u = new SpeechSynthesisUtterance(it.roman); u.lang = 'en-IN'; }
    u.rate = 0.85 * rate; speechSynthesis.speak(u); } catch(e) {}
}
if (window.speechSynthesis) speechSynthesis.getVoices();
</script></body></html>"""


def say_buttons(items, height=56):
    """items: list of (label, roman). Shows 🔊 buttons that pronounce the Tamil."""
    data_items, buttons = [], []
    for n, item in enumerate(items):
        label, roman = item[0], item[1]
        script = item[2] if len(item) > 2 and item[2] else tamil_script(roman)
        data_items.append({"roman": roman, "ta": script, "b64": tamil_audio_b64(script, is_script=True)})
        buttons.append(f'<button onclick="say({n},1)">🔊 {html_safe(label)}</button>')
    buttons.append(f'<button class="slow" onclick="say({len(items) - 1 if len(items) == 1 else 0},0.7)">🐢 Slowly</button>')
    _embed(SAY_HTML.replace("__BUTTONS__", "".join(buttons)).replace("__ITEMS__", json.dumps(data_items)), height)


# ------------------- Tamil script -> English letters (for online look-ups) -------------------
_T_VOW = {"அ": "a", "ஆ": "aa", "இ": "i", "ஈ": "ee", "உ": "u", "ஊ": "oo", "எ": "e", "ஏ": "e", "ஐ": "ai",
          "ஒ": "o", "ஓ": "o", "ஔ": "au"}
_T_SIGN = {"ா": "aa", "ி": "i", "ீ": "ee", "ு": "u", "ூ": "oo", "ெ": "e", "ே": "e", "ை": "ai", "ொ": "o", "ோ": "o",
           "ௌ": "au"}
_T_CON = {"க": "k", "ங": "ng", "ச": "s", "ஞ": "nj", "ட": "d", "ண": "n", "த": "th", "ந": "n", "ப": "p", "ம": "m",
          "ய": "y", "ர": "r", "ல": "l", "வ": "v", "ழ": "zh", "ள": "l", "ற": "r", "ன": "n", "ஜ": "j", "ஷ": "sh",
          "ஸ": "s", "ஹ": "h"}


def roman_from_tamil(text: str) -> str:
    """Readable English letters for Tamil script, e.g. தண்ணீர் -> thanneer."""
    out = []
    for word in re.split(r"(\s+)", text):
        sylls, i = [], 0   # list of (consonant or None, vowel_text or "" for pulli)
        while i < len(word):
            ch = word[i]
            if ch in _T_VOW:
                sylls.append((None, _T_VOW[ch])); i += 1
            elif ch in _T_CON:
                nxt = word[i + 1] if i + 1 < len(word) else ""
                if nxt == "்":
                    sylls.append((ch, "")); i += 2
                elif nxt in _T_SIGN:
                    sylls.append((ch, _T_SIGN[nxt])); i += 2
                else:
                    sylls.append((ch, "a")); i += 1
            else:
                sylls.append((None, ch if ch.isascii() else "")); i += 1
        res = ""
        for n, (c, v) in enumerate(sylls):
            if c is None:
                res += v
                continue
            prev = sylls[n - 1] if n > 0 else (None, " ")
            nxt = sylls[n + 1] if n + 1 < len(sylls) else (None, " ")
            prev_pulli = prev[0] is not None and prev[1] == ""
            first_half = v == "" and nxt[0] == c          # first part of a double letter, e.g. ட் in ட்ட
            second_half = prev_pulli and prev[0] == c
            sound = _T_CON[c]
            if first_half:
                sound = {"க": "k", "ட": "t", "த": "th", "ப": "p", "ச": "", "ற": "t"}.get(c, sound)
            elif second_half:
                sound = {"க": "k", "ட": "t", "த": "th", "ப": "p", "ச": "ch", "ற": "r"}.get(c, sound)
            elif v == "" and c in ("க", "ட", "ப") and nxt[0] is not None:
                sound = {"க": "k", "ட": "t", "ப": "p"}[c]           # e.g. ஆக்டோபஸ் -> aaktopas
            elif c == "க":
                sound = "k" if n == 0 or (prev_pulli and prev[0] != "ங") else "g"
            elif c == "ச":
                sound = ("j" if prev_pulli and prev[0] == "ஞ" else
                         "ch" if prev_pulli and prev[0] in ("ட", "ற") else "s")
            elif c == "த":
                sound = "th" if n == 0 or (prev_pulli and prev[0] != "ந") else "dh"
            elif c == "ப":
                sound = "b" if prev_pulli and prev[0] == "ம" else "p"
            elif c == "ட" and prev_pulli and prev[0] not in ("ண",):
                sound = "t"
            elif c == "ற":
                sound = "dr" if prev_pulli and prev[0] == "ன" else "r"
            elif c == "ட" and v == "" and nxt[0] in ("ச",):
                sound = "t"
            if v == "" and ((c == "ஞ" and nxt[0] == "ச") or (c == "ங" and nxt[0] == "க")):
                sound = "n"
            res += sound + v
        res = re.sub(r"aay$", "aai", res)
        out.append(res)
    return "".join(out)


TAMIL_RE = re.compile("[\u0B80-\u0BFF]")
ONLINE_NOTE = "🌐 From an online dictionary: usually written (formal) Tamil — check with a grown-up how your family says it."


def _translate_google(q: str):
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source="en", target="ta").translate(q)


def _translate_mymemory(q: str):
    r = requests.get("https://api.mymemory.translated.net/get", params={"q": q, "langpair": "en|ta"}, timeout=6)
    r.raise_for_status()
    return r.json()["responseData"]["translatedText"]


@st.cache_data(show_spinner=False, max_entries=5000, ttl=60 * 60 * 24 * 7)
def _online_tamil_cached(q: str):
    import concurrent.futures as cf
    answered = False
    for fn in (_translate_google, _translate_mymemory):
        try:
            with cf.ThreadPoolExecutor(max_workers=1) as ex:
                ta = ex.submit(fn, q).result(timeout=7)
            answered = True
            if ta and TAMIL_RE.search(ta):
                return ta.strip()
        except Exception:
            continue
    if answered:
        return None                      # the dictionary replied but had no Tamil for it
    raise ConnectionError("online dictionary not reachable")


def online_tamil(q: str):
    """Tamil script for an English word/phrase from an online dictionary, or None (never remembers failures)."""
    import time
    if time.time() < st.session_state.get("online_pause_until", 0):
        return None
    try:
        return _online_tamil_cached(q.strip().lower())
    except ConnectionError:
        st.session_state.online_pause_until = time.time() + 30   # internet trouble: short pause, then try again
        return None
    except Exception:
        return None


# =================================== APP ===================================
if "data" not in st.session_state:
    try:
        st.session_state.data, st.session_state.sha = load_data()
    except Exception as e:
        st.session_state.data, st.session_state.sha = migrate(default_data(), today_local()), None
        st.session_state.save_error = f"Couldn't load saved progress ({e})."

today = today_local()
TODAY_KEY = today.isoformat()
data = st.session_state.data

# ---- new badges? record + celebrate ----
stats = compute_stats(data)
earned_ids = {b[0] for b in BADGES if stats.get(b[4], 0) >= b[5]}
new_badges = earned_ids - set(data.get("badges_earned", {}))
if new_badges and not st.session_state.get("badge_save_failed"):
    def _record(d):
        be = d.setdefault("badges_earned", {})
        for bid in new_badges:
            be.setdefault(bid, TODAY_KEY)
    if update(_record):
        st.session_state.new_badge_party = sorted(new_badges)
    else:
        st.session_state.badge_save_failed = True
    data = st.session_state.data

theme_id = data.get("theme", "rainbow")
st.markdown(BASE_CSS + "<style>" + THEME_CSS.get(theme_id, THEME_CSS["rainbow"]) + "</style>",
            unsafe_allow_html=True)
install_sound_engine()
alerts = st.container()   # fixed holders, so the tabs below never move (moving resets the open tab)

done_today = done_on(data, today)          # tasks that COUNT (approved or auto-checked)
ticked_today = ticked_on(data, today)      # everything she ticked
pending_today = pending_on(data, today)    # ticked, waiting for a grown-up
bal = balance_info(data)
small_ws = small_wheel_status(data, today)
big_ws = big_wheel_status(data, today)
star_days = stats["star_days"]
earned_badges = data.get("badges_earned", {})

# ------------------------------ messages on top ------------------------------
with alerts:
    if err := st.session_state.pop("save_error", None):
        st.error(f"😿 Progress couldn't be saved. Ask a grown-up to check the Grown-ups tab. ({err})")
    if flash := st.session_state.pop("flash", None):
        st.success(flash)
        st.balloons()
        play_sound("fanfare")


def dismiss_message(mid):
    def change(d):
        for m in d.get("messages", []):
            if m["id"] == mid:
                m["seen"] = True
    update(change)


unseen = [m for m in data.get("messages", []) if not m.get("seen")]
if unseen:
    with alerts:
        m = unseen[-1]
        st.markdown(f'<div class="msg">💌 <b>A message for you!</b><br>{html_safe(m["text"])}</div>',
                    unsafe_allow_html=True)
        st.button("💖 Thank you!", key=f"seen_{m['id']}", on_click=dismiss_message, args=(m["id"],))

# ------------------------------------ hero -----------------------------------
dollars = dollar_status(data)
pills = (f'<span class="badge fire">🔥 {task_streak(data, today, "speak")}-day speaking streak</span>'
         f'<span class="badge moon">🌙 {task_streak(data, today, "bed")}-night bedtime streak</span>'
         f'<span class="badge carrot">🥕 {data.get("carrots", 0)} carrots</span>')
if data.get("toy_fund"):
    pills += f'<span class="badge toy">🧸 Toy Fund &#36;{data["toy_fund"]}</span>'
if dollars["paid"] or dollars["owed"]:
    pills += f'<span class="badge money">💵 &#36;{dollars["paid"]} earned</span>'
if small_ws["ok"] or big_ws["ok"]:
    pills += '<span class="badge spin">🎡 Spin waiting!</span>'
st.markdown(
    f"""<div class="hero"><div class="float f1" data-joke="unicorn" title="Tap me!">🦄</div>
<div class="float f2" data-joke="bunny" title="Tap me!">🐰</div>
<div class="float f3" data-joke="rainbow" title="Tap me!">🌈</div><div class="float f4" data-joke="star" title="Tap me!">✨</div>
<div class="title">Hi {html_safe(STUDENT_NAME)}!</div>
<div class="sub">{today.strftime("%A, %d %B %Y")}</div>
<div class="balance">⏳ {bal["balance"]} min screen time left</div><br>{pills}</div>""",
    unsafe_allow_html=True,
)

# ---- celebrations queued by callbacks ----
fx = st.container()
celebration = st.session_state.pop("celebrate", None)
if celebration:
  with fx:
    st.markdown('<div class="celebrate"><div class="thumb">👍</div><div class="burst">🎉🦄🌈⭐💖</div>'
                f'<div class="word">{random.choice(["Great job!", "Amazing!", "Hop-tastic!", "Well done!", "Super!"])}'
                '</div></div>', unsafe_allow_html=True)
    play_sound("chime")
    if celebration.get("fact") is not None:
        st.toast(f"🧠 Fun fact: {FUN_FACTS[celebration['fact']]}", icon="👍")
party = st.session_state.pop("new_badge_party", None)
if party:
  with fx:
    names = ", ".join(next(f"{b[1]} {b[2]}" for b in BADGES if b[0] == bid) for bid in party)
    st.success(f"🏅 NEW BADGE{'S' if len(party) > 1 else ''}! {names}")
    st.balloons()
    play_sound("fanfare")

(tab_today, tab_maths, tab_write, tab_tamil, tab_chalisa, tab_spin, tab_rewards, tab_pet, tab_weeks,
 tab_parent) = st.tabs(["🌈 Today", "🧮 Maths", "✍️ Stories", "🗣️ Tamil words", "🙏 Chalisa", "🎡 Spin",
                        "🏆 Rewards", "🐰 Bunny & badges", "📅 My weeks", "🔐 Grown-ups"])


# ================================== TODAY ==================================
def toggle(tid, key):
    checked = st.session_state[key]
    info = {}

    def change(d):
        s = set(d["days"].get(TODAY_KEY, []))
        (s.add if checked else s.discard)(tid)
        d["days"][TODAY_KEY] = sorted(s)
        if checked:
            add_fact(d, TODAY_KEY, info)

    if update(change):
        if checked:
            st.session_state.celebrate = {"fact": info.get("fact"), "task": tid}
    else:
        st.session_state[key] = not checked  # put the tick back how it was


def task_label(t):
    reward = f"  **+{t['minutes']} min**" if t["minutes"] else "  *(counts toward big rewards)*"
    must = "  · **must do**" if t.get("required") else ""
    return f"{t['emoji']} {t['name']}{reward}{must}"


def task_box(t, tip=None):
    tid = t["id"]
    if t.get("auto"):
        is_done = tid in done_today
        st.checkbox(task_label(t) + ("  ✅" if is_done else ""), value=is_done, disabled=True,
                    key=f"view_{TODAY_KEY}_{tid}_{is_done}")
    elif tid in done_today:   # approved: locked so it can't be unticked
        st.checkbox(task_label(t) + "  ✅ *approved*", value=True, disabled=True, key=f"locked_{TODAY_KEY}_{tid}")
    else:
        key = f"{TODAY_KEY}_{tid}"
        if key not in st.session_state:
            st.session_state[key] = tid in ticked_today
        label = task_label(t) + ("  ⏳ *waiting for a grown-up*" if tid in pending_today else "")
        st.checkbox(label, key=key, on_change=toggle, args=(tid, key))
    if tip:
        st.markdown(f'<div class="tip">{tip}</div>', unsafe_allow_html=True)


def approve_tasks(day_key, tids, pin_key=None):
    if pin_key and not pin_ok(pin_key):
        st.session_state.approve_msg = ("bad", "That PIN isn't right.")
        return
    n = {}

    def change(d):
        ticked = set(d["days"].get(day_key, []))
        ok = d.setdefault("approved", {}).setdefault(day_key, [])
        new = [t for t in tids if t in ticked and t not in ok]
        ok.extend(new)
        n["n"] = len(new)
        if day_key != TODAY_KEY:
            d.setdefault("earned", {})[day_key] = task_minutes(counted_set(d, day_key))

    if pin_key:
        st.session_state[pin_key] = ""
    if update(change):
        st.session_state.parent_ok = False if pin_key else st.session_state.get("parent_ok")
        st.session_state.flash = f"✅ {n['n']} task{'s' if n['n'] != 1 else ''} approved — rewards unlocked!"


def approve_today_from_box():
    approve_tasks(TODAY_KEY, list(st.session_state.get("approve_pick", [])), pin_key="approve_pin")


def next_idea():
    st.session_state.idea_shift = st.session_state.get("idea_shift", 0) + 1


def record_used(mins):
    """Take minutes off the balance (needs the grown-up PIN)."""
    if not pin_ok("use_pin"):
        st.session_state.use_msg = ("bad", "That PIN isn't right. Ask a grown-up! 🔐")
        return
    result = {}

    def change(d):
        left = balance_info(d)["balance"]
        if mins <= 0 or mins > left:
            result["bad"] = left
            return False
        d.setdefault("used", []).append({"date": TODAY_KEY, "minutes": mins,
                                         "time": datetime.now(ZoneInfo(TIMEZONE)).strftime("%H:%M")})
        result["left"] = left - mins

    ok = update(change)
    st.session_state.use_pin = ""
    if ok:
        st.session_state.use_msg = ("ok", f"✅ {mins} minutes used. {result['left']} minutes left, saved for later! 💾")
    elif "bad" in result:
        st.session_state.use_msg = ("bad", f"Only {result['bad']} minutes are left.")


def use_quick():
    """Option 1: slide switch."""
    if not st.session_state.get("use_toggle"):
        return
    st.session_state.use_toggle = False
    record_used(min(DAILY_GOAL_MINUTES, balance_info(st.session_state.data)["balance"]))


def use_custom():
    """Option 2: typed number of minutes."""
    record_used(int(st.session_state.get("use_mins", 0) or 0))


def add_mood(mid):
    def change(d):
        d.setdefault("moods", []).append({"date": TODAY_KEY, "time": datetime.now(ZoneInfo(TIMEZONE)).strftime("%H:%M"),
                                          "mood": mid})
    if update(change):
        st.session_state.mood_reply = mid


with tab_today:
    task_mins = task_minutes(done_today)
    pct = int(100 * task_mins / DAILY_GOAL_MINUTES)
    st.markdown(
        f'<div class="minutes"><span>⭐ {task_mins} min earned today</span><span>🎯 goal {DAILY_GOAL_MINUTES} min</span></div>'
        f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
        unsafe_allow_html=True,
    )
    required_left = [t for t in TASKS if t.get("required") and t["id"] not in done_today]
    if required_left:
        names = " and ".join(f"{t['emoji']} {t['name'][0].lower() + t['name'][1:]}" for t in required_left)
        st.warning(f"🔒 Do your **must do** tasks first to unlock screen time: {names}")
    elif task_mins >= DAILY_GOAL_MINUTES:
        st.success(f"🦄 WOW {STUDENT_NAME}! You earned all {DAILY_GOAL_MINUTES} minutes today — it's a ⭐ star day!")
    else:
        st.info(f"🐰 Hop hop! {DAILY_GOAL_MINUTES - task_mins} more minutes to earn. You can do it!")
    if pending_today:
        with st.container(border=True):
            st.markdown(f"**⏳ Waiting for a grown-up to check ({len(pending_today)})** — your stars, minutes and "
                        "surprises unlock once a grown-up says they're done! 🎁")
            with st.form("approve_form", border=False):
                st.multiselect("Grown-up: which tasks are really done?", sorted(pending_today), default=sorted(pending_today),
                               key="approve_pick",
                               format_func=lambda x: f"{TASK_BY_ID[x]['emoji']} {TASK_BY_ID[x]['name']}")
                a1, a2 = st.columns([2, 1])
                a1.text_input("Grown-up PIN", type="password", key="approve_pin")
                a2.write("")
                a2.form_submit_button("Approve ✅", on_click=approve_today_from_box)
            amsg = st.session_state.pop("approve_msg", None)
            if amsg:
                st.error(amsg[1])
    if small_ws["ok"] or big_ws["ok"]:
        which = "big 🦄 AND small 🌈" if small_ws["ok"] and big_ws["ok"] else ("big 🦄" if big_ws["ok"] else "small 🌈")
        st.markdown(f'<div class="fact">🎡 <b>You have a {which} wheel spin waiting!</b> '
                    'Open the <b>🎡 Spin</b> tab.</div>', unsafe_allow_html=True)
    if celebration and celebration.get("fact") is not None:
        st.markdown(f'<div class="fact">🧠 <b>Fun fact unlocked!</b> {html_safe(FUN_FACTS[celebration["fact"]])}</div>',
                    unsafe_allow_html=True)

    # ---- screen-time balance ----
    with st.container(border=True):
        c1, c2 = st.columns([1, 1])
        c1.markdown(f'<div style="font-size:1.1rem;color:#6b3f73;font-weight:600">⏳ Screen time balance</div>'
                    f'<div style="font-size:2.6rem;font-weight:700;color:#ff4fa3;line-height:1.1">{bal["balance"]} min</div>'
                    '<div style="color:#8a6a96;font-size:.9rem">Unused minutes are saved for another day 💾</div>',
                    unsafe_allow_html=True)
        with c2:
            if bal["balance"] > 0:
                st.markdown("**🧑‍🍼 Grown-up: record minutes used**")
                st.text_input("Grown-up PIN", type="password", key="use_pin")
                quick = min(DAILY_GOAL_MINUTES, bal["balance"])
                st.markdown(f"**Option 1** · used the full {quick} minutes")
                st.toggle(f"Slide ➡️ {quick} minutes used", key="use_toggle", on_change=use_quick)
                st.markdown("**Option 2** · used fewer minutes")
                if st.session_state.get("use_mins", 0) > bal["balance"] or "use_mins" not in st.session_state:
                    st.session_state.use_mins = min(15, bal["balance"])
                oc1, oc2 = st.columns([3, 2])
                oc1.number_input("Minutes used", min_value=1, max_value=bal["balance"], step=5, key="use_mins",
                                 label_visibility="collapsed")
                oc2.button("💾 Save", on_click=use_custom, use_container_width=True)
            else:
                st.caption("No minutes to use yet — finish some tasks! 🐰")
        msg = st.session_state.pop("use_msg", None)
        if msg:
            (st.success if msg[0] == "ok" else st.error)(msg[1])

    # ---- bunny + newest badges + mood ----
    with st.container(border=True):
        stage, nxt = pet_stage(star_days)
        ls = last_star_day(data)
        sleepy = stage[1] not in ("egg", "hatching") and ls is not None and (today - ls).days >= 2 \
            and not is_star_day(done_today)
        pc1, pc2 = st.columns([1, 2])
        pc1.markdown(pet_svg(stage[1], sleepy, data.get("pet", {}).get("wear", {}), size=150), unsafe_allow_html=True)
        with pc2:
            pet_name = data.get("pet", {}).get("name", "Bunnicorn")
            st.markdown(f'<div class="pet-name">{html_safe(pet_name)}</div><div style="color:#8a6a96">'
                        f'{stage[2]} · {"😴 Sleepy — earn a star day to wake me up!" if sleepy else stage[3]}</div>',
                        unsafe_allow_html=True)
            newest = sorted(reversed(list(earned_badges.items())), key=lambda kv: kv[1], reverse=True)[:2]
            if newest:
                st.markdown('<div style="margin-top:8px;color:#6b3f73;font-weight:600">🏅 My newest badges</div>'
                            '<div class="badge-grid" style="justify-content:flex-start">'
                            + "".join(badge_html(next(b for b in BADGES if b[0] == bid), small=True, show_desc=False)
                                      for bid, _ in newest if any(b[0] == bid for b in BADGES)) + '</div>',
                            unsafe_allow_html=True)
        st.markdown("**How are you feeling right now?**")
        mcols = st.columns(len(MOODS))
        for col, (mid, emo, label, _reply) in zip(mcols, MOODS):
            col.button(emo, key=f"mood_{mid}", help=label, on_click=add_mood, args=(mid,), use_container_width=True)
        reply = st.session_state.pop("mood_reply", None)
        if reply:
            mood = next(m for m in MOODS if m[0] == reply)
            st.success(f"{mood[1]} You're feeling **{mood[2].lower()}**. {mood[3]}")
        else:
            todays = [m for m in data.get("moods", []) if m["date"] == TODAY_KEY]
            if todays:
                mood = next((m for m in MOODS if m[0] == todays[-1]["mood"]), None)
                if mood:
                    st.caption(f"Last check-in today: {mood[1]} {mood[2]} at {todays[-1]['time']}")

    idea_n = today.toordinal() + st.session_state.get("idea_shift", 0)
    write_n = today.toordinal()
    wotd = word_of_the_day(data, today)
    tips = {
        "homework": "📒 Do today's homework from school. <b>No homework today?</b> Ask a grown-up for a 15-minute "
                    "learning task instead, then tick this.",
        "speak": f"💡 <b>Idea for today:</b> {SPEAKING_IDEAS[idea_n % len(SPEAKING_IDEAS)]} "
                 "· Need a word? Look it up in the <b>🗣️ Tamil words</b> tab!",
        "write1": f"✨ Write about: <b>{WRITING_PROMPTS[write_n % len(WRITING_PROMPTS)]}</b> — write it in the "
                  f"<b>My Stories</b> tab (50+ words ticks this for you!). Try to use the word <b>{html_safe(wotd['word'])}</b>.",
        "write2": f"✨ Write about: <b>{WRITING_PROMPTS[(write_n + 5) % len(WRITING_PROMPTS)]}</b>",
        "maths": f"🧮 Go to the <b>Maths</b> tab. This ticks itself when you solve {MATHS_TO_SOLVE} problems "
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
                _embed(SIT_TIMER, 130)

    facts_today = data.get("facts", {}).get(TODAY_KEY, [])
    if facts_today:
        with st.expander(f"🧠 Fun facts you unlocked today ({len(facts_today)})"):
            for i in facts_today:
                st.markdown(f"• {md_safe(FUN_FACTS[i])}")


# ================================== MATHS ==================================
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
                if "maths" not in s:
                    s.add("maths")
                    d["days"][TODAY_KEY] = sorted(s)
                    d.setdefault("approved", {}).setdefault(TODAY_KEY, []).append("maths")   # checked by the app
                    add_fact(d, TODAY_KEY, outcome)
        else:
            m["tries"] += 1
            outcome["right"] = False

    if update(change):
        st.session_state.maths_answer = ""
        if outcome["right"]:
            cheers = ["🎉 Brilliant!", "🦄 Magical!", "🌟 Superstar!", "🐰 Hop-tastic!", "🌈 You got it!"]
            st.session_state.maths_msg = ("ok", random.choice(cheers) + " That's correct!")
            st.session_state.celebrate = {"fact": outcome.get("fact"), "task": "maths"}
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


def _xm_state(d, topic):
    return d.setdefault("extra_maths", {}).setdefault(TODAY_KEY, {}).setdefault(
        topic, {"index": 0, "tries": 0, "correct": 0})


def check_extra(topic, symbol):
    if symbol is None:
        given = parse_answer(st.session_state.get("xm_answer", ""))
        if given is None:
            st.session_state.xm_msg = ("warn", "Hmm, I can't read that. Try a number like 1234, 3.4 or 5/8.")
            return
    else:
        given = symbol
    out = {}

    def change(d):
        xs = _xm_state(d, topic)
        prob = make_extra_problem(topic, today, xs["index"])
        if given == prob["answer"]:
            first_try = xs["tries"] == 0
            xs["index"] += 1
            xs["tries"] = 0
            xs["correct"] += 1
            if first_try:      # no carrot for guessing until it's right
                d["carrots"] = d.get("carrots", 0) + EXTRA_MATHS_CARROTS
            out["right"] = True
            out["first"] = first_try
            out["carrots"] = d.get("carrots", 0)
        else:
            xs["tries"] += 1
            out["right"] = False

    if update(change):
        st.session_state.xm_answer = ""
        if out["right"] and not out["first"]:
            st.session_state.xm_msg = ("ok", "✅ That's right! Carrots are only for first-try answers, so take your time "
                                             "and think before you answer. 🥕")
        elif out["right"]:
            extra = (f" You have {out['carrots']} carrots — ask a grown-up to swap them for "
                     f"{CARROT_SWAP_MINUTES} minutes! 🎉" if out["carrots"] >= CARROTS_FOR_SWAP else "")
            st.session_state.xm_msg = ("ok", f"🥕 Correct first time! +{EXTRA_MATHS_CARROTS} carrot.{extra}")
            st.session_state.celebrate = {"fact": None, "task": "bonus"}
        else:
            st.session_state.xm_msg = ("bad", "Not quite — have another go! 💪")


def skip_extra(topic):
    def change(d):
        xs = _xm_state(d, topic)
        xs["index"] += 1
        xs["tries"] = 0

    if update(change):
        st.session_state.xm_answer = ""


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
            c1.text_input("Your answer", key="maths_answer", placeholder=prob["hint"], label_visibility="collapsed")
            c2.form_submit_button("Check ✔️", on_click=check_answer, use_container_width=True)
        st.caption(f"Tries on this problem: {tries}")

        msg = st.session_state.pop("maths_msg", None)
        if msg:
            {"ok": st.success, "bad": st.error, "warn": st.warning, "info": st.info}[msg[0]](msg[1])

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

    # ---------------- bonus maths (optional) ----------------
    st.markdown("### ⭐ Bonus maths challenges")
    st.caption(f"Optional extra practice! Every correct answer = {EXTRA_MATHS_CARROTS} 🥕 carrot. "
               f"{CARROTS_FOR_SWAP} carrots = {CARROT_SWAP_MINUTES} minutes of screen time (a grown-up approves the swap "
               "in the 🎡 Spin tab).")
    with st.container(border=True):
        topic_ids = [t for t, _ in EXTRA_MATHS_TOPICS]
        topic_names = dict(EXTRA_MATHS_TOPICS)
        st.selectbox("Choose a topic", topic_ids, key="xm_topic", format_func=lambda t: topic_names[t])
        topic = st.session_state.xm_topic
        xs = data.get("extra_maths", {}).get(TODAY_KEY, {}).get(topic, {"index": 0, "tries": 0, "correct": 0})
        carrots_now = data.get("carrots", 0)
        today_correct = sum(v.get("correct", 0) for v in data.get("extra_maths", {}).get(TODAY_KEY, {}).values())
        st.markdown(f'<div class="minutes"><span>🥕 {carrots_now} carrots</span>'
                    f'<span>✅ {today_correct} bonus answers right today</span></div>'
                    f'<div class="rbar"><div class="rfill" style="width:'
                    f'{max(3, min(100, int(100 * carrots_now / CARROTS_FOR_SWAP)))}%"></div></div>', unsafe_allow_html=True)
        xp = make_extra_problem(topic, today, xs["index"])
        st.markdown(f'<span class="topic">{topic_names[topic]}</span>'
                    f'<div class="question">{html_safe(xp["question"])}</div>', unsafe_allow_html=True)
        if topic == "compare4":
            bc = st.columns(3)
            for col, sym in zip(bc, ["<", "=", ">"]):
                col.button(f"  {sym}  ", key=f"xm_cmp_{sym}", on_click=check_extra, args=(topic, sym),
                           use_container_width=True)
        else:
            with st.form("xm_form", border=False):
                f1, f2 = st.columns([3, 1])
                f1.text_input("Answer", key="xm_answer", placeholder=xp["hint"], label_visibility="collapsed")
                f2.form_submit_button("Check ✔️", on_click=check_extra, args=(topic, None), use_container_width=True)
        xmsg = st.session_state.pop("xm_msg", None)
        if xmsg:
            {"ok": st.success, "bad": st.error, "warn": st.warning}[xmsg[0]](xmsg[1])
        if xs["tries"] >= 2:
            st.markdown(f'<div class="clue">💡 <b>Clue:</b> {html_safe(xp["clue"])}</div>', unsafe_allow_html=True)
        st.button("⏭️ Skip to a new question", key="xm_skip", on_click=skip_extra, args=(topic,))


# ================================ MY STORIES ================================
def save_story():
    title = str(st.session_state.get("story_title", "")).strip() or "My story"
    text = str(st.session_state.get("story_text", "")).strip()
    words = count_words(text)
    if words == 0:
        st.session_state.story_msg = ("warn", "Write something first! ✏️")
        return
    info = {}

    def change(d):
        w = word_of_the_day(d, today)
        stories = d.setdefault("stories", [])
        problem = story_problem(text, [x["text"] for x in stories])
        info["problem"] = problem
        stories.append({"id": uuid.uuid4().hex[:8], "date": TODAY_KEY, "title": title, "text": text, "words": words,
                        "ok": problem is None,
                        "wotd": w["word"], "wotd_count": count_word(text, w["word"]), "feedback": ""})
        if words >= MIN_STORY_WORDS and problem is None:
            s = set(d["days"].get(TODAY_KEY, []))
            for tid in ("write1", "write2"):
                if tid not in s or tid not in d.get("approved", {}).get(TODAY_KEY, []):
                    s.add(tid)
                    info["tick"] = tid
                    d.setdefault("approved", {}).setdefault(TODAY_KEY, []).append(tid)   # checked by the app
                    break
            d["days"][TODAY_KEY] = sorted(s)
            if info.get("tick"):
                add_fact(d, TODAY_KEY, info)
        award_word_win(d, TODAY_KEY, w["word"], info)

    if update(change):
        st.session_state.story_title = ""
        st.session_state.story_text = ""
        parts = [f"📖 Story saved! ({words} words)"]
        if info.get("tick"):
            parts.append(f"Your writing task {'1' if info['tick'] == 'write1' else '2'} is ticked! ✅")
            st.session_state.celebrate = {"fact": info.get("fact"), "task": info["tick"]}
        elif info.get("problem"):
            parts = [f"📖 Saved, but it can't tick your writing task: {info['problem']}"]
        elif words < MIN_STORY_WORDS:
            parts.append(f"Write at least {MIN_STORY_WORDS} words in a story to tick a writing task.")
        if info.get("word_win"):
            parts.append(f"💖 WORD WIZARD! You used the word of the day {WORD_CHALLENGE_USES} times: "
                         f"+{WORD_CHALLENGE_MINUTES} minutes!")
        st.session_state.story_msg = ("ok", " ".join(parts))


def save_sentences():
    sents = [str(st.session_state.get(f"wsent_{i}", "")).strip() for i in range(WORD_CHALLENGE_USES)]
    if not any(sents):
        st.session_state.sent_msg = ("warn", "Write at least one sentence first! ✏️")
        return
    info = {}

    def change(d):
        w = word_of_the_day(d, today)
        d.setdefault("wotd_sentences", {})[TODAY_KEY] = sents
        award_word_win(d, TODAY_KEY, w["word"], info)
        info["word"] = w["word"]

    if update(change):
        good = len({_norm(x) for x in sents if good_sentence(x, info["word"])})
        if info.get("word_win"):
            st.session_state.sent_msg = ("ok", f"💖 WORD WIZARD! Brilliant sentences — +{WORD_CHALLENGE_MINUTES} minutes!")
            st.session_state.celebrate = {"fact": None, "task": "wotd"}
        else:
            st.session_state.sent_msg = ("ok", f"💾 Saved! {good} of {WORD_CHALLENGE_USES} sentences use the word.")


with tab_write:
    wotd = word_of_the_day(data, today)
    uses = wotd_uses(data, TODAY_KEY, wotd["word"])
    won = TODAY_KEY in data.get("word_wins", [])
    stars = "".join("💖" if i < min(uses, WORD_CHALLENGE_USES) else "🤍" for i in range(WORD_CHALLENGE_USES))
    st.markdown(
        f'<div class="card" style="text-align:center"><div style="color:#8a6a96;font-weight:600">✨ Word of the day ✨</div>'
        f'<div class="wotd">{html_safe(wotd["word"])}</div><div style="color:#5a2d66"><i>{html_safe(wotd["meaning"])}</i></div>'
        f'<div style="color:#8a6a96;margin-top:4px">e.g. “{html_safe(wotd.get("example", ""))}”</div>'
        f'<div style="margin-top:10px;font-size:1.05rem"><b>Challenge:</b> write {WORD_CHALLENGE_USES} different sentences ({WORD_SENTENCE_MIN_WORDS}+ words each) using '
        f'this word (or use it in your stories) for +{WORD_CHALLENGE_MINUTES} minutes!</div>'
        f'<div style="font-size:1.8rem">{stars}</div>'
        f'<div style="color:#1f7a37;font-weight:600">{"🎉 Challenge complete!" if won else ""}</div></div>',
        unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(f"**✏️ My {WORD_CHALLENGE_USES} sentences using “{md_safe(wotd['word'])}”**")
        st.markdown('<div class="tip" style="margin-left:0">📖 <b>Tip:</b> use your dictionary to explore the meaning. '
                    'Look for similar words (synonyms), opposites, and other forms of the word, '
                    'like <i>-ly</i>, <i>-ness</i> or <i>-ed</i>.</div>', unsafe_allow_html=True)
        saved = data.get("wotd_sentences", {}).get(TODAY_KEY, [])
        for i in range(WORD_CHALLENGE_USES):
            key = f"wsent_{i}"
            if key not in st.session_state:
                st.session_state[key] = saved[i] if i < len(saved) else ""
            val = str(st.session_state[key]).strip()
            mark = ""
            if val:
                if count_word(val, wotd["word"]) == 0:
                    mark = f"  ❌ use the word “{wotd['word']}”"
                elif count_words(val) < WORD_SENTENCE_MIN_WORDS:
                    mark = f"  ❌ use at least {WORD_SENTENCE_MIN_WORDS} words"
                elif story_problem(val) is not None:
                    mark = "  ❌ make it a real sentence"
                elif any(_norm(val) == _norm(str(st.session_state.get(f"wsent_{j}", ""))) for j in range(i)):
                    mark = "  ❌ write a different sentence"
                else:
                    mark = "  ✅"
            st.text_input(f"Sentence {i + 1}{md_safe(mark)}", key=key,
                          placeholder=f"Write a sentence with “{wotd['word']}”…")
        st.button("💾 Save my sentences", on_click=save_sentences)
        smsg = st.session_state.pop("sent_msg", None)
        if smsg:
            (st.success if smsg[0] == "ok" else st.warning)(smsg[1])

    st.markdown("### ✍️ Write a story")
    st.caption(f"Ideas: **{md_safe(WRITING_PROMPTS[write_n % len(WRITING_PROMPTS)])}** or "
               f"**{md_safe(WRITING_PROMPTS[(write_n + 5) % len(WRITING_PROMPTS)])}**")
    with st.container(border=True):
        st.text_input("Title", key="story_title", placeholder="My amazing story")
        st.text_area("Your story", key="story_text", height=260,
                     placeholder="Once upon a time, a curious little bunny…")
        draft = str(st.session_state.get("story_text", ""))
        n_words = count_words(draft)
        st.markdown(f'<div class="minutes"><span>📝 {n_words} words</span><span>🎯 {MIN_STORY_WORDS} words ticks a '
                    f'writing task</span></div><div class="rbar"><div class="rfill" style="width:'
                    f'{max(3, min(100, int(100 * n_words / MIN_STORY_WORDS)))}%"></div></div>', unsafe_allow_html=True)
        st.caption("Tap outside the box to update the word count.")
        st.button("💾 Save my story", on_click=save_story, type="primary")
        msg = st.session_state.pop("story_msg", None)
        if msg:
            (st.success if msg[0] == "ok" else st.warning)(msg[1])

    stories = list(reversed(data.get("stories", [])))
    st.markdown(f"### 📚 My Stories ({len(stories)})")
    if not stories:
        st.caption("Your stories will appear here. Grown-ups can read them and leave you a note! 💌")
    for s in stories[:30]:
        label = f"{'💌 ' if s.get('feedback') else ''}{s['title']} · {date.fromisoformat(s['date']).strftime('%d %b')} · {s['words']} words"
        with st.expander(md_safe(label)):
            st.markdown(f'<div class="story">{html_safe(s["text"]).replace(chr(10), "<br>")}</div>',
                        unsafe_allow_html=True)
            if s.get("feedback"):
                st.markdown(f'<div class="note">💌 <b>Note from your grown-up:</b> {html_safe(s["feedback"])}</div>',
                            unsafe_allow_html=True)


# ============================== TAMIL WORDS ==============================
DOUBLE_ING = {"run", "swim", "sit", "cut", "put", "stop", "dig", "hug", "win", "begin", "get", "shop", "hit", "spin"}


def ing_form(phrase):
    w, *rest = phrase.split(" ")
    if w.endswith("ie"):
        g = w[:-2] + "ying"
    elif w in DOUBLE_ING:
        g = w + w[-1] + "ing"
    elif w.endswith("e") and not w.endswith("ee"):
        g = w[:-1] + "ing"
    else:
        g = w + "ing"
    return " ".join([g] + rest)


def s_form(phrase):
    w, *rest = phrase.split(" ")
    if w.endswith(("s", "sh", "ch", "x", "o")):
        g = w + "es"
    elif w.endswith("y") and w[-2] not in "aeiou":
        g = w[:-1] + "ies"
    else:
        g = w + "s"
    return " ".join([g] + rest)


@st.cache_data(show_spinner=False)
def verb_index():
    idx = {}
    for kind, table in (("verb", TAMIL_VERBS), ("special", TAMIL_SPECIAL_VERBS)):
        for i, v in enumerate(table):
            base, past, part = v[0], v[1], v[2]
            for form, label in ((base, "base"), (past, "past"), (part, "past"), (ing_form(base), "now"),
                                (s_form(base), "now")):
                idx.setdefault(form.lower(), (kind, i, label))
    return idx


def all_tamil_words(d):
    words = {}
    for cat, items in TAMIL_WORDS.items():
        for en, (ta, note) in items.items():
            words.setdefault(en.lower(), (ta, note, cat))   # first entry wins if a word appears twice
    for v in TAMIL_VERBS:
        words.setdefault(v[0], (v[3], v[7], "🏃 Doing words"))
    for en, v in d.get("tamil_online", {}).items():
        words.setdefault(en.lower(), (v.get("tamil", ""), ONLINE_NOTE, "🌐 Looked up online"))
    for en, v in d.get("tamil_custom", {}).items():
        words[en.lower()] = (v.get("tamil", ""), v.get("note", ""), "⭐ Added by a grown-up")
    return words


def lookup_tamil(query, words):
    """Returns (results, suggestions). result = ('word', en, ta, note, cat) or ('verb'/'special', i, label)."""
    q = re.sub(r"[^a-z' ]", " ", query.lower()).strip()
    q = re.sub(r"\s+", " ", q)
    if not q:
        return [], []
    vidx = verb_index()
    if q in words and q not in vidx:
        return [("word", q, *words[q])], []
    stripped = re.sub(r"^(to|i|i'll|i will|will|you|he|she|we|they|am|is|are|was|were|i am|i'm|did) ", "", q)
    stripped = re.sub(r"^(will|am|is|are|was|were) ", "", stripped)
    stripped = re.sub(r"^(going to|gonna) ", "", stripped)
    out = []
    future = re.match(r"^(i will|i.ll|will|you will|he will|she will|we will|they will|going to|i.m going to|i am going to|gonna) ", q) is not None
    for cand in (q, stripped):
        if cand in vidx:
            kind, i, label = vidx[cand]
            out.append((kind, i, "future" if future else label))
            if cand in words and words[cand][2] != "🏃 Doing words":
                out.append(("word", cand, *words[cand]))
            return out, []
    for cand in (q.rstrip("s"), q[:-2] if q.endswith("es") else None, stripped):
        if cand and cand in words:
            return [("word", cand, *words[cand])], []
    out.append(("split",))   # marker: found word-by-word, not as a whole phrase
    for w in q.split():
        if w in vidx:
            out.append(vidx[w])
            continue
        for cand in (w, w.rstrip("s")):
            if cand in words:
                out.append(("word", cand, *words[cand]))
                break
    if len(out) > 1:
        return out, []
    out = []
    import difflib
    return [], difflib.get_close_matches(q, list(words) + list(vidx), n=5, cutoff=.72)


def pronoun_forms(i_form):
    """Spoken Tamil: swap the 'I' ending (-en) for the other people."""
    if not i_form.endswith("en"):
        return [(p[0], f"{p[1]} {i_form}") for p in PRONOUNS]
    stem = i_form[:-2]
    return [(p[0], f"{p[1]} {stem}{p[2]}") for p in PRONOUNS]


def verb_card(kind, i, label):
    if kind == "special":
        en, past, _p, now, did, will, note = TAMIL_SPECIAL_VERBS[i]
        rows = [("Now / every day", f"I {en}", now), ("Before (past)", f"I {past}", did), ("Later (future)", f"I will {en}", will)]
        pick = {"past": "Before (past)", "future": "Later (future)"}.get(label, "Now / every day")
        body = "".join(f'<tr{" class=star" if lbl == pick else ""}>'
                       f'<td class="name">{lbl}</td><td>{html_safe(e)}</td><td><b>{html_safe(t)}</b></td></tr>' for lbl, e, t in rows)
        st.markdown(f'<div class="card"><div style="color:#8a6a96">{html_safe(en)} · {html_safe(past)}</div>'
                    f'<div class="scroll"><table class="week">{body}</table></div>'
                    f'{"<div class=note>" + html_safe(note) + "</div>" if note else ""}</div>', unsafe_allow_html=True)
        say_buttons([("Now", now), ("Past", did), ("Future", will)])
        return
    en, past, part, cmd, now, did, will, note = TAMIL_VERBS[i]
    head = (f'<div style="color:#8a6a96">{html_safe(en)} · {html_safe(past)} · {html_safe(part)} · {html_safe(ing_form(en))}</div>'
            f'<div class="wotd">{html_safe(cmd)}!</div><div style="color:#5a2d66">= “{html_safe(en)}!” (to a friend) · '
            f'to an elder: <b>{html_safe(cmd)}nga</b></div>')
    sel = {"now": 0, "base": 0, "past": 1, "future": 2}.get(label, 0)
    cols = [("Now / every day", now), ("Before (past)", did), ("Later (future)", will)]
    head_row = "<tr><th></th>" + "".join(f"<th>{c}</th>" for c, _ in cols) + "</tr>"
    forms = [pronoun_forms(f) for _, f in cols]
    rows = ""
    for r, (who, _ta, _end) in enumerate(PRONOUNS):
        rows += f"<tr{' class=star' if r == 0 else ''}><td class='name'>{who}</td>" + "".join(
            f"<td>{'<b>' if c == sel else ''}{html_safe(forms[c][r][1])}{'</b>' if c == sel else ''}</td>"
            for c in range(3)) + "</tr>"
    eng = (f'<div style="margin-top:6px;color:#6b3f73">I {html_safe(en)} → '
           f'<b>{html_safe(now)}</b> · I {html_safe(past)} → <b>{html_safe(did)}</b> · I will {html_safe(en)} → '
           f'<b>{html_safe(will)}</b></div>')
    st.markdown(f'<div class="card">{head}<div class="scroll" style="margin-top:8px"><table class="week">{head_row}{rows}'
                f'</table></div>{eng}{"<div class=note>💡 " + html_safe(note) + "</div>" if note else ""}</div>',
                unsafe_allow_html=True)
    say_buttons([(f"{cmd}!", cmd), ("I do", f"naan {now}"), ("I did", f"naan {did}"), ("I will", f"naan {will}")], height=96)


def save_online_word(en, roman, script):
    def change(d):
        d.setdefault("tamil_online", {})[en] = {"tamil": roman, "script": script}
        lst = d.setdefault("tamil_saved", [])
        if en not in lst:
            lst.append(en)
    update(change)


def save_my_word(en):
    def change(d):
        lst = d.setdefault("tamil_saved", [])
        if en not in lst:
            lst.append(en)
    update(change)


with tab_tamil:
    words = all_tamil_words(data)
    st.markdown("### 🗣️ English → Tamil words")
    st.caption(f"Type an English word or short sentence to find it in Tamil, written in English letters. Try a doing "
               f"word like 'eat', 'ate' or 'will eat' to see all its forms! ({len(words) + len(TAMIL_SPECIAL_VERBS)}+ words)")
    with st.container(border=True):
        q = st.text_input("English word", key="tamil_q", placeholder="e.g. house, went, I'm tired, broken")
        if q.strip():
            found, sugg = lookup_tamil(q, words)
            if found and found[0] == ("split",):
                found = found[1:]
                qq = re.sub(r"\s+", " ", q.strip().lower())
                with st.spinner("Looking up the whole sentence… 🌐"):
                    script = online_tamil(qq) if len(qq) <= 60 else None
                if script:
                    roman = roman_from_tamil(script)
                    st.markdown(f'<div class="card" style="text-align:center"><div style="color:#8a6a96">{html_safe(qq)}</div>'
                                f'<div class="wotd">{html_safe(roman)}</div>'
                                f'<div style="color:#5a2d66;font-size:1.2rem">{html_safe(script)}</div>'
                                f'<div style="color:#a99bb0;font-size:.85rem;margin-top:4px">{html_safe(ONLINE_NOTE)}</div></div>',
                                unsafe_allow_html=True)
                    say_buttons([("Say it", roman, script)])
                    st.button(f"⭐ Save '{qq}' to My Tamil words", key=f"tsave_on_{qq}", on_click=save_online_word,
                              args=(qq, roman, script))
                st.markdown("**Word by word:**")
            if found:
                for res in found:
                    if res[0] == "word":
                        _k, en, ta, note, cat = res
                        st.markdown(f'<div class="card" style="text-align:center"><div style="color:#8a6a96">{html_safe(en)}</div>'
                                    f'<div class="wotd">{html_safe(ta)}</div>'
                                    f'{"<div style=color:#5a2d66><i>" + html_safe(note) + "</i></div>" if note else ""}'
                                    f'<div style="color:#a99bb0;font-size:.85rem">{html_safe(cat)}</div></div>',
                                    unsafe_allow_html=True)
                        say_buttons([("Say it", ta.split(" / ")[0].replace("…", "").strip())])
                        st.button(f"⭐ Save '{en}' to My Tamil words", key=f"tsave_{en}", on_click=save_my_word, args=(en,))
                    else:
                        verb_card(*res)
                        base = (TAMIL_VERBS if res[0] == "verb" else TAMIL_SPECIAL_VERBS)[res[1]][0]
                        if res[0] == "verb":
                            st.button(f"⭐ Save '{base}' to My Tamil words", key=f"tsave_v_{base}", on_click=save_my_word,
                                      args=(base,))
            else:
                qq = re.sub(r"\s+", " ", q.strip().lower())
                with st.spinner("Looking it up in the online dictionary… 🌐"):
                    script = online_tamil(qq) if len(qq) <= 60 else None
                if script:
                    roman = roman_from_tamil(script)
                    st.markdown(f'<div class="card" style="text-align:center"><div style="color:#8a6a96">{html_safe(qq)}</div>'
                                f'<div class="wotd">{html_safe(roman)}</div>'
                                f'<div style="color:#5a2d66;font-size:1.2rem">{html_safe(script)}</div>'
                                f'<div style="color:#a99bb0;font-size:.85rem;margin-top:4px">{html_safe(ONLINE_NOTE)}</div></div>',
                                unsafe_allow_html=True)
                    say_buttons([("Say it", roman, script)])
                    st.button(f"⭐ Save '{qq}' to My Tamil words", key=f"tsave_on_{qq}", on_click=save_online_word,
                              args=(qq, roman, script))
                else:
                    st.warning(f"I don't know “{q.strip()}” yet. Ask a grown-up — they can add it in the Grown-ups tab! 🙋")
                if sugg:
                    st.markdown("Did you mean: " + ", ".join(f"**{md_safe(s_)}**" for s_ in sugg) + "?")
    tip_i = today.toordinal() % len(TAMIL_TIPS)
    st.markdown(f'<div class="fact">🗣️ <b>Speaking tip:</b> {html_safe(TAMIL_TIPS[tip_i])}</div>', unsafe_allow_html=True)
    saved = [w for w in data.get("tamil_saved", []) if w in words]
    if saved:
        st.markdown("### ⭐ My Tamil words")
        st.markdown("".join(f'<span class="pill">{html_safe(w)} → <b>{html_safe(words[w][0])}</b></span>' for w in saved),
                    unsafe_allow_html=True)
    st.markdown("### 📚 Browse words by topic")
    cats = (["🏃 Doing words (verb table)", "💛 Feeling words (I know, I like…)"] + list(TAMIL_WORDS)
            + (["⭐ Added by a grown-up"] if data.get("tamil_custom") else [])
            + (["🌐 Looked up online"] if data.get("tamil_online") else []))
    cat = st.selectbox("Topic", cats, key="tamil_cat")
    if cat.startswith("🏃"):
        rows = "".join(f"<tr><td class='name'>{html_safe(v[0])}</td><td>{html_safe(v[3])}</td><td>{html_safe(v[4])}</td>"
                       f"<td>{html_safe(v[5])}</td><td>{html_safe(v[6])}</td></tr>" for v in sorted(TAMIL_VERBS))
        st.markdown("<div class='scroll'><table class='week'><tr><th>English</th><th>Command</th><th>I do / am doing</th>"
                    f"<th>I did</th><th>I will</th></tr>{rows}</table></div>", unsafe_allow_html=True)
        st.caption("💡 Swap the ending for other people: -en (I) → -a (you), -aan (he), -aa (she), -om (we), -aanga (they). "
                   "e.g. saapten (I ate) → ava saaptaa (she ate).")
    elif cat.startswith("💛"):
        rows = "".join(f"<tr><td class='name'>{html_safe(v[0])}</td><td>{html_safe(v[3])}</td><td>{html_safe(v[4])}</td>"
                       f"<td>{html_safe(v[5])}</td></tr>" for v in TAMIL_SPECIAL_VERBS)
        st.markdown("<div class='scroll'><table class='week'><tr><th>English</th><th>Now</th><th>Past</th><th>Future</th></tr>"
                    f"{rows}</table></div>", unsafe_allow_html=True)
        st.caption("These start with 'enakku' (= to me) because in Tamil you say 'to me it is known', 'to me it is liked'.")
    else:
        rows = [(en, ta) for en, (ta, _n, c) in sorted(words.items()) if c == cat]
        st.markdown("".join(f'<span class="pill">{html_safe(en)} → <b>{html_safe(ta)}</b></span>' for en, ta in rows),
                    unsafe_allow_html=True)
    st.caption("Spoken Tamil can be a little different in each family — check with a grown-up how your family says it. 💗")


# ============================== HANUMAN CHALISA ==============================
def learn_part(i):
    if CHALISA_NEEDS_PIN and not pin_ok(f"ch_pin_{i}"):
        st.session_state.ch_msg = ("bad", "That PIN isn't right. Ask a grown-up! 🔐")
        return
    info = {}

    def change(d):
        ch = d.setdefault("chalisa", {})
        if str(i) in ch or (i > 0 and str(i - 1) not in ch):
            return False
        ch[str(i)] = TODAY_KEY
        bs = bead_status(d)
        while d.get("bead_rewards_given", 0) < bs["rewards_due"]:
            d["bead_rewards_given"] = d.get("bead_rewards_given", 0) + 1
            d.setdefault("credits", []).append({"date": TODAY_KEY, "minutes": BEAD_MINUTES,
                                                "reason": f"{BEADS_FOR_MINUTES} prayer beads 📿"})
            info["minutes"] = info.get("minutes", 0) + BEAD_MINUTES
        info["all"] = bs["all_done"]

    if update(change):
        parts = [f"🙏 Wonderful! Part {i + 1} learned: +{BEADS_PER_PART} 📿 beads!"]
        if info.get("minutes"):
            parts.append(f"You reached {BEADS_FOR_MINUTES} beads: +{info['minutes']} minutes of screen time! ⏳")
        if info.get("all"):
            parts.append("🎉 You learned the WHOLE Hanuman Chalisa! Choose your special outing below!")
        st.session_state.ch_msg = ("ok", " ".join(parts))
        st.session_state.celebrate = {"fact": None, "task": "chalisa"}
        st.session_state[f"ch_ready_{i}"] = False


def choose_outing():
    choice = st.session_state.get("outing_pick")

    def change(d):
        if not bead_status(d)["all_done"]:
            return False
        d["chalisa_reward"] = {"choice": choice, "status": "chosen", "date": TODAY_KEY}

    if update(change):
        st.session_state.ch_msg = ("ok", f"✨ Great choice! A grown-up will plan: {choice}")


def give_outing():
    if not pin_ok("outing_pin"):
        st.session_state.ch_msg = ("bad", "That PIN isn't right.")
        return

    def change(d):
        r = d.get("chalisa_reward")
        if not r:
            return False
        r["status"] = "done"
        r["done_date"] = TODAY_KEY
        d.setdefault("history", []).append({"reward": "chalisa_outing", "date": TODAY_KEY})

    st.session_state.outing_pin = ""
    if update(change):
        st.session_state.flash = "🎉 Chalisa outing enjoyed! So proud of you!"


def next_ch_fact():
    st.session_state.ch_fact = st.session_state.get("ch_fact", 0) + 1


@st.cache_data(show_spinner=False)
def picture_b64(name):
    f = Path(__file__).parent / name
    return base64.b64encode(f.read_bytes()).decode() if f.exists() else None


with tab_chalisa:
    pics = [(n, picture_b64(n)) for n in CHALISA_PICTURES]
    pics = [(n, b) for n, b in pics if b]
    if pics:
        imgs = "".join(f'<img src="data:image/png;base64,{b}" alt="{html_safe(n)}" style="height:min(42vh,340px);'
                       'width:auto;max-width:48%;object-fit:contain;border-radius:16px;border:3px solid #ffc98a;'
                       'box-shadow:0 6px 18px rgba(169,79,0,.18);background:#fff">' for n, b in pics)
        st.markdown(f'<div style="display:flex;gap:12px;justify-content:center;align-items:center;margin:4px 0 10px">'
                    f'{imgs}</div>', unsafe_allow_html=True)
    ch_done = data.get("chalisa", {})
    bs = bead_status(data)
    if "ch_fact" not in st.session_state:
        st.session_state.ch_fact = random.randrange(len(CHALISA_FACTS))
    st.markdown(f'<div class="fact">🌟 <b>Did you know?</b> {html_safe(CHALISA_FACTS[st.session_state.ch_fact % len(CHALISA_FACTS)])}</div>',
                unsafe_allow_html=True)
    st.button("✨ Another fact", on_click=next_ch_fact, key="ch_fact_btn")

    st.markdown("### 🙏 Learn the Hanuman Chalisa")
    with st.container(border=True):
        beads_html = "".join(f'<span class="bead{" on" if j < bs["toward"] else ""}"></span>' for j in range(BEADS_FOR_MINUTES))
        st.markdown(f'<div style="text-align:center"><div class="chalisa-head">📿 My prayer beads: {bs["beads"]}</div>'
                    f'<div class="beads">{beads_html}</div><div class="how">{bs["toward"]}/{BEADS_FOR_MINUTES} beads toward '
                    f'+{BEAD_MINUTES} minutes of screen time · Parts learned: {len(ch_done)}/{len(CHALISA_PARTS)}</div></div>',
                    unsafe_allow_html=True)
        pct = int(100 * len(ch_done) / len(CHALISA_PARTS))
        st.markdown(f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>', unsafe_allow_html=True)
        st.caption(f"Each part you learn by heart = {BEADS_PER_PART} 📿 beads. Every {BEADS_FOR_MINUTES} beads = "
                   f"{BEAD_MINUTES} minutes. Learn ALL {len(CHALISA_PARTS)} parts for a special weekend outing! 🎉")
    msg = st.session_state.pop("ch_msg", None)
    if msg:
        (st.success if msg[0] == "ok" else st.error)(msg[1])

    # ---- big reward ----
    reward = data.get("chalisa_reward")
    if bs["all_done"]:
        with st.container(border=True):
            st.markdown('<div class="reward-head">🏆 Chalisa Champion! Choose your weekend outing</div>', unsafe_allow_html=True)
            if reward and reward.get("status") == "done":
                st.success(f"🎉 Enjoyed on {reward.get('done_date')}: {md_safe(reward['choice'])}")
            else:
                if reward:
                    st.info(f"Your choice: **{md_safe(reward['choice'])}** — a grown-up will plan it! You can still change it.")
                st.radio("Pick one:", CHALISA_OUTINGS, key="outing_pick",
                         index=CHALISA_OUTINGS.index(reward["choice"]) if reward and reward["choice"] in CHALISA_OUTINGS else 0)
                st.button("💖 This is my choice", on_click=choose_outing)
                if reward:
                    with st.form("outing_form", border=False):
                        oc1, oc2 = st.columns([2, 1])
                        oc1.text_input("Grown-up PIN after the outing", type="password", key="outing_pin")
                        oc2.write("")
                        oc2.form_submit_button("We went! ✅", on_click=give_outing)

    # ---- the parts ----
    next_part = next((i for i in range(len(CHALISA_PARTS)) if str(i) not in ch_done), None)
    for i, part in enumerate(CHALISA_PARTS):
        learned = str(i) in ch_done
        locked = not learned and i != next_part
        icon = "✅" if learned else ("🔒" if locked else "📿")
        label = f"{icon} Part {i + 1} of {len(CHALISA_PARTS)} · {part['title']}"
        if learned:
            label += f" · learned {date.fromisoformat(ch_done[str(i)]).strftime('%d %b')}"
        with st.expander(label, expanded=(i == next_part)):
            if locked:
                st.caption(f"🔒 Learn Part {i} first, then this part unlocks.")
                continue
            hide = st.toggle("🙈 Hide the words to test myself", key=f"ch_hide_{i}")
            lines_html = ""
            for ln in part["lines"]:
                if hide:
                    first = ln.split()[0]
                    lines_html += f'<span class="ln"><b>{html_safe(first)}</b> …</span>'
                else:
                    lines_html += f'<span class="ln">{html_safe(ln)}</span>'
            st.markdown(f'<div class="chalisa">{lines_html}</div>', unsafe_allow_html=True)
            with st.expander("💡 What does it mean?"):
                st.markdown(md_safe(part["meaning"]))
            if learned:
                st.success(f"✅ You learned this part! +{BEADS_PER_PART} 📿")
                continue
            st.markdown(f'<div class="tip" style="margin-left:0">🎙️ <b>Before you submit:</b> record yourself saying all '
                        f'{len(part["lines"])} lines from memory (use the recorder below or the iPad\'s Voice Memos app), '
                        'then play the recording to a grown-up.</div>', unsafe_allow_html=True)
            if hasattr(st, "audio_input"):
                st.audio_input("🎙️ Practice recorder (tap to record, then play it back)", key=f"ch_rec_{i}")
            st.checkbox(f"I said all {len(part['lines'])} lines from memory, recorded it and played it to a grown-up",
                        key=f"ch_ready_{i}")
            if CHALISA_NEEDS_PIN:
                st.text_input("Grown-up PIN", type="password", key=f"ch_pin_{i}")
            st.button(f"🙏 I've learned Part {i + 1}! (+{BEADS_PER_PART} 📿)", key=f"ch_submit_{i}", type="primary",
                      on_click=learn_part, args=(i,), disabled=not st.session_state.get(f"ch_ready_{i}"))


# ============================ SPIN & REWARDS ============================
def do_spin(wheel):
    prizes = BIG_PRIZES if wheel == "big" else SMALL_PRIZES
    result = {}

    def change(d):
        status = (big_wheel_status if wheel == "big" else small_wheel_status)(d, today)
        if not status["ok"]:
            return False
        idx = random.randrange(len(prizes))
        p = prizes[idx]
        spin = {"id": uuid.uuid4().hex[:8], "date": TODAY_KEY, "wheel": wheel, "prize_id": p["id"],
                "name": p["name"], "emoji": p["emoji"], "status": "waiting"}
        if p.get("auto") == "minutes":
            d.setdefault("credits", []).append({"date": TODAY_KEY, "minutes": 30, "reason": "Wheel prize"})
            spin["status"] = "auto"
        elif p.get("auto") == "carrots":
            d["carrots"] = d.get("carrots", 0) + 10
            spin["status"] = "auto"
        elif p.get("auto") == "toy":
            d["toy_fund"] = d.get("toy_fund", 0) + TOY_FUND_STEP
            spin["status"] = "auto"
        d.setdefault("spins", []).append(spin)
        result["idx"] = idx

    if update(change):
        st.session_state.spin_show = {"wheel": wheel, "idx": result["idx"], "n": random.random()}


def mark_prize():
    if not pin_ok("prize_pin"):
        st.session_state.prize_msg = ("bad", "That PIN isn't right.")
        return
    sid = st.session_state.get("prize_pick")
    result = {}

    def change(d):
        spin = next((s for s in d.get("spins", []) if s["id"] == sid and s["status"] == "waiting"), None)
        if not spin:
            return False
        if spin["prize_id"] == "restaurant":
            ready = restaurant_ready_from(d)
            if ready and today < ready:
                result["wait"] = ready
                return False
            d["last_restaurant"] = TODAY_KEY
        if spin["prize_id"] == "bedpass":
            s = set(d["days"].get(TODAY_KEY, []))
            s.add("bed")
            d["days"][TODAY_KEY] = sorted(s)
            d.setdefault("approved", {}).setdefault(TODAY_KEY, []).append("bed")   # grown-up used the PIN
            result["bed"] = True
        spin["status"] = "done"
        spin["done_date"] = TODAY_KEY
        result["name"] = f"{spin['emoji']} {spin['name']}"

    st.session_state.prize_pin = ""
    if update(change):
        st.session_state.flash = f"🎁 Prize enjoyed: {md_safe(result['name'])}!"
        if result.get("bed"):
            st.session_state[f"{TODAY_KEY}_bed"] = True
    elif "wait" in result:
        st.session_state.prize_msg = ("bad", f"🍽️ The restaurant prize can be used from "
                                             f"{result['wait'].strftime('%A %d %B')} (3 weeks after the last one).")


def swap_carrots():
    if not pin_ok("carrot_pin"):
        st.session_state.prize_msg = ("bad", "That PIN isn't right.")
        return

    def change(d):
        if d.get("carrots", 0) < CARROTS_FOR_SWAP:
            return False
        d["carrots"] -= CARROTS_FOR_SWAP
        d.setdefault("credits", []).append({"date": TODAY_KEY, "minutes": CARROT_SWAP_MINUTES, "reason": "Carrot swap"})

    st.session_state.carrot_pin = ""
    if update(change):
        st.session_state.flash = f"🥕 {CARROTS_FOR_SWAP} carrots swapped for {CARROT_SWAP_MINUTES} minutes of screen time!"


def toy_trip():
    if not pin_ok("toy_pin"):
        st.session_state.prize_msg = ("bad", "That PIN isn't right.")
        return

    def change(d):
        if d.get("toy_fund", 0) < TOY_FUND_TARGET:
            return False
        d["toy_fund"] -= TOY_FUND_TARGET
        d.setdefault("history", []).append({"reward": "toyshop", "date": TODAY_KEY})

    st.session_state.toy_pin = ""
    if update(change):
        st.session_state.flash = "🧸 Toy shop trip done! Enjoy your new toys!"


def give_reward(reward_id, pin_key):
    if not pin_ok(pin_key):
        st.session_state[pin_key + "_bad"] = True
        return
    r = next((x for x in REWARDS if x["id"] == reward_id), None)

    def change(d):
        if reward_id == "dollar":
            d["dollars_paid"] = d.get("dollars_paid", 0) + 1
        else:
            d["claims"][reward_id] = TODAY_KEY
            if r and r.get("bonus_minutes"):
                d.setdefault("credits", []).append({"date": TODAY_KEY, "minutes": r["bonus_minutes"],
                                                    "reason": r["name"]})
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

with tab_spin:
    show = st.session_state.pop("spin_show", None)
    msg = st.session_state.pop("prize_msg", None)
    if msg:
        st.error(msg[1])
    st.markdown("### 🎡 Spin the wheel!")
    wc1, wc2 = st.columns(2)
    for col, wheel, prizes, ws, title in ((wc1, "small", SMALL_PRIZES, small_ws, "🌈 Small wheel"),
                                         (wc2, "big", BIG_PRIZES, big_ws, "🦄 Big wheel")):
        with col:
            with st.container(border=True):
                st.markdown(f'<div class="reward-head" style="text-align:center">{title}</div>', unsafe_allow_html=True)
                if wheel == "small":
                    st.caption("One spin on every ⭐ star day.")
                else:
                    st.caption(f"Unlocks after {BIG_WHEEL_STREAK} star days in a row · up to {BIG_SPINS_PER_WEEK} "
                               f"spins a week (used this week: {big_ws['week_used']}/{BIG_SPINS_PER_WEEK}).")
                spinning = show and show["wheel"] == wheel
                idle = "" if spinning else ("Tap SPIN! 👇" if ws["ok"] else ws["why"])
                _embed(wheel_html(prizes, show["idx"] if spinning else -1,
                                  hub="🌈" if wheel == "small" else "🦄", idle=idle), 400)
                st.button("🎡 SPIN!", key=f"spin_{wheel}", on_click=do_spin, args=(wheel,), disabled=not ws["ok"],
                          type="primary", use_container_width=True)
                teasers = [PRIZE_BY_ID[t] for t in (SMALL_TEASERS if wheel == "small" else BIG_TEASERS) if t in PRIZE_BY_ID]
                st.markdown(f'<div class="tip" style="margin-left:0">👀 <b>Sneak peek:</b> {html_safe(" · ".join(p["emoji"] + " " + p["name"] for p in teasers))} '
                            f'… and {len(prizes) - len(teasers)} more <b>secret surprises</b>! 🤫</div>',
                            unsafe_allow_html=True)

    # ---- my prizes ----
    waiting = [s for s in data.get("spins", []) if s["status"] == "waiting"]
    st.markdown(f"### 🎁 My prizes waiting ({len(waiting)})")
    with st.container(border=True):
        if not waiting:
            st.caption("Prizes you win that need a grown-up will wait here until you enjoy them.")
        for s in waiting:
            extra = ""
            if s["prize_id"] == "restaurant":
                ready = restaurant_ready_from(data)
                extra = (f" · ⏳ can use from {ready.strftime('%d %b')}" if ready and today < ready
                         else " · ✅ ready to use (no Mexican!)")
            st.markdown(f"{s['emoji']} **{md_safe(s['name'])}** · won {date.fromisoformat(s['date']).strftime('%d %b')}"
                        f"{'' if s['wheel'] == 'small' else ' · 🦄 big'}{extra}")
        if waiting:
            with st.form("prize_form", border=False):
                st.selectbox("Grown-up: which prize was enjoyed?", options=[s["id"] for s in waiting], key="prize_pick",
                             format_func=lambda sid: next(f"{s['emoji']} {s['name']}" for s in waiting if s["id"] == sid))
                pc1, pc2 = st.columns([2, 1])
                pc1.text_input("Grown-up PIN", type="password", key="prize_pin")
                pc2.write("")
                pc2.form_submit_button("Mark as done ✅", on_click=mark_prize)

    # ---- carrots & toy fund ----
    cc1, cc2 = st.columns(2)
    with cc1:
        with st.container(border=True):
            carrots = data.get("carrots", 0)
            st.markdown(f'<div class="reward-head">🥕 Carrot collection</div><div style="font-size:1.6rem">'
                        f'{"🥕" * min(carrots // 10, 6)}{"" if carrots else "—"}</div>'
                        f'<div class="how"><b>{carrots}</b> carrots · {CARROTS_FOR_SWAP} carrots = '
                        f'{CARROT_SWAP_MINUTES} min screen time</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rbar"><div class="rfill" style="width:'
                        f'{max(3, min(100, int(100 * carrots / CARROTS_FOR_SWAP)))}%"></div></div>', unsafe_allow_html=True)
            if carrots >= CARROTS_FOR_SWAP:
                with st.form("carrot_form", border=False):
                    st.text_input("Grown-up PIN to approve the swap", type="password", key="carrot_pin")
                    st.form_submit_button(f"Swap {CARROTS_FOR_SWAP} 🥕 for {CARROT_SWAP_MINUTES} min", on_click=swap_carrots)
    with cc2:
        with st.container(border=True):
            fund = data.get("toy_fund", 0)
            st.markdown(f'<div class="reward-head">🧸 Toy Fund</div><div style="font-size:1.6rem;font-weight:700;'
                        f'color:#1d5f8a">&#36;{fund} <span style="font-size:1rem;color:#8a6a96">of &#36;{TOY_FUND_TARGET}'
                        f'</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="rbar"><div class="rfill" style="width:'
                        f'{max(3, min(100, int(100 * fund / TOY_FUND_TARGET)))}%"></div></div>', unsafe_allow_html=True)
            if fund >= TOY_FUND_TARGET:
                st.success("🎉 Ready to go toy shopping!")
                with st.form("toy_form", border=False):
                    st.text_input("Grown-up PIN after the trip", type="password", key="toy_pin")
                    st.form_submit_button("We went toy shopping 🛍️", on_click=toy_trip)
            else:
                st.caption("Win 🧸 on the big wheel to add $10.".replace("$", "\\$"))


with tab_rewards:
    st.markdown("### 🏆 Big rewards")
    for r in REWARDS:
        s = reward_status(data, r, today)
        parts = [min(s["streak"], r["streak_len"]) / r["streak_len"]]
        parts += [min(s["counts"][t], n) / n for t, n in r["needs"].items()]
        pct = int(100 * sum(parts) / len(parts))
        with st.container(border=True):
            st.markdown(f'<div class="reward-head">{r["emoji"]} {html_safe(r["name"])}</div>'
                        f'<div class="how">{html_safe(r["how"])}</div>', unsafe_allow_html=True)
            word = STREAK_WORDS.get(r["streak_task"], r["streak_task"])
            rp = [f'<span class="pill {"ok" if s["streak"] >= r["streak_len"] else ""}">'
                  f'{word} in a row {min(s["streak"], r["streak_len"])}/{r["streak_len"]}</span>']
            for tid, n in r["needs"].items():
                t = TASK_BY_ID[tid]
                rp.append(f'<span class="pill {"ok" if s["counts"][tid] >= n else ""}">'
                          f'{t["emoji"]} {tid} {min(s["counts"][tid], n)}/{n} days</span>')
            st.markdown("".join(rp), unsafe_allow_html=True)
            st.markdown(f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
                        unsafe_allow_html=True)
            if s["ok"]:
                st.success(f"🎉 UNLOCKED! {STUDENT_NAME} has earned: {md_safe(r['name'])}!")
                claim_box(r["id"], "Add minutes ⏳" if r.get("bonus_minutes") else "Give reward 🎁")
            elif s["streak"] == 0:
                st.caption("🌱 Start your streak today — every day counts!")

    with st.container(border=True):
        st.markdown(f'<div class="reward-head">💵 Earn a dollar</div>'
                    f'<div class="how">Every {STAR_DAYS_PER_DOLLAR} ⭐ star days = &#36;1. They don\'t have to be in a row.</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<span class="pill">⭐ {dollars["toward_next"]}/{STAR_DAYS_PER_DOLLAR} star days toward the next &#36;1</span>'
                    f'<span class="pill ok">💵 &#36;{dollars["paid"]} given so far</span>', unsafe_allow_html=True)
        pct = int(100 * dollars["toward_next"] / STAR_DAYS_PER_DOLLAR)
        st.markdown(f'<div class="rbar"><div class="rfill" style="width:{max(pct, 3)}%"></div></div>',
                    unsafe_allow_html=True)
        if dollars["owed"] > 0:
            st.success(f"🎉 {STUDENT_NAME} has earned \\${dollars['owed']} that hasn't been handed over yet!")
            claim_box("dollar")


# ============================ BUNNY & BADGES ============================
def save_pet():
    name = str(st.session_state.get("pet_name_in", "")).strip()[:20] or "Bunnicorn"
    wear = {slot: st.session_state.get(f"wear_{slot}") for slot in SLOT_NAMES}
    wear = {k: v for k, v in wear.items() if v and v != "none"}

    def change(d):
        d.setdefault("pet", {})["name"] = name
        d["pet"]["wear"] = wear

    update(change)


def set_theme(tid):
    def change(d):
        d["theme"] = tid
    update(change)


with tab_pet:
    stage, nxt = pet_stage(star_days)
    ls = last_star_day(data)
    sleepy = stage[1] not in ("egg", "hatching") and ls is not None and (today - ls).days >= 2 \
        and not is_star_day(done_today)
    pet = data.get("pet", {})
    with st.container(border=True):
        bc1, bc2 = st.columns([1, 1])
        bc1.markdown(pet_svg(stage[1], sleepy, pet.get("wear", {}), size=230), unsafe_allow_html=True)
        with bc2:
            st.markdown(f'<div class="pet-name">{html_safe(pet.get("name", "Bunnicorn"))}</div>'
                        f'<div style="font-size:1.1rem;color:#5a2d66"><b>{stage[2]}</b></div>'
                        f'<div style="color:#8a6a96">{"😴 I missed you! Earn a ⭐ star day to wake me up." if sleepy else stage[3]}</div>',
                        unsafe_allow_html=True)
            if nxt:
                need = nxt[0] - star_days
                frac = (star_days - stage[0]) / (nxt[0] - stage[0])
                st.markdown(f'<div style="margin-top:10px;color:#6b3f73">⭐ {need} more star day{"s" if need != 1 else ""} '
                            f'until your bunny grows… <b>✨ it’s a surprise!</b></div><div class="rbar"><div class="rfill" style="width:'
                            f'{max(3, int(100 * frac))}%"></div></div>', unsafe_allow_html=True)
            else:
                st.markdown("🌈 Fully grown and magical!")
            st.caption(f"⭐ Total star days: {star_days}")

    st.markdown("### 👗 Dress-ups")
    with st.container(border=True):
        unlocked = [a for a in ACCESSORIES if stats.get(a["stat"], 0) >= a["need"]]
        if stage[1] in ("egg", "hatching"):
            st.caption("Dress-ups can be worn once your bunny has hatched! 🥚")
        st.text_input("My bunny's name", value=pet.get("name", "Bunnicorn"), key="pet_name_in", max_chars=20)
        dcols = st.columns(len(SLOT_NAMES))
        for col, (slot, slot_label) in zip(dcols, SLOT_NAMES.items()):
            opts = ["none"] + [a["id"] for a in unlocked if a["slot"] == slot]
            cur = pet.get("wear", {}).get(slot, "none")
            if f"wear_{slot}" not in st.session_state:
                st.session_state[f"wear_{slot}"] = cur if cur in opts else "none"
            col.selectbox(slot_label, opts, key=f"wear_{slot}",
                          format_func=lambda a: "— nothing —" if a == "none" else
                          next(f"{x['emoji']} {x['name']}" for x in ACCESSORIES if x["id"] == a))
        st.button("✨ Save my bunny", on_click=save_pet, type="primary")
        chips = []
        for a in ACCESSORIES:
            ok = a in unlocked
            chips.append(f'<span class="pill {"ok" if ok else "no"}">{a["emoji"] + " " + html_safe(a["name"]) if ok else "🎁 Surprise"}'
                         f'{"" if ok else " · unlock with " + html_safe(a["how"])}</span>')
        st.markdown("".join(chips), unsafe_allow_html=True)

    st.markdown("### 🎨 My themes")
    with st.container(border=True):
        tcols = st.columns(3)
        for i, th in enumerate(THEMES):
            ok = star_days >= th["need"]
            label = (th["name"] if ok else "🎁 Mystery theme") + (" ✔️" if th["id"] == theme_id else "") + ("" if ok else f" 🔒 {th['need']}⭐")
            tcols[i % 3].button(label, key=f"theme_{th['id']}", disabled=not ok or th["id"] == theme_id,
                                on_click=set_theme, args=(th["id"],), use_container_width=True)
        st.caption("Unlock new themes by collecting ⭐ star days.")

    st.markdown(f"### 🏅 My badges ({len(earned_badges)}/{len(BADGES)})")
    with st.container(border=True):
        got = [b for b in BADGES if b[0] in earned_badges]
        locked = [b for b in BADGES if b[0] not in earned_badges]
        if got:
            st.markdown('<div class="badge-grid">' + "".join(badge_html(b) for b in got) + "</div>",
                        unsafe_allow_html=True)
        if locked:
            st.markdown('<div style="text-align:center;color:#8a6a96;margin:16px 0 8px">🔒 Still to earn</div>'
                        '<div class="badge-grid">' + "".join(badge_html(b, earned=False) for b in locked) + "</div>",
                        unsafe_allow_html=True)


# ================================ MY WEEKS ================================
def week_summary(d, monday: date):
    days = [monday + timedelta(days=i) for i in range(7)]
    keys = {x.isoformat() for x in days}
    star = sum(is_star_day(done_on(d, x)) for x in days)
    tasks = sum(len(done_on(d, x)) for x in days)
    maths = sum(len(d.get("maths", {}).get(k, {}).get("log", [])) for k in keys)
    stories = sum(1 for s in d.get("stories", []) if s["date"] in keys)
    speak = sum("speak" in done_on(d, x) for x in days)
    badges = [next(b[1] for b in BADGES if b[0] == bid) for bid, dt in d.get("badges_earned", {}).items()
              if dt in keys and any(b[0] == bid for b in BADGES)]
    return {"star": star, "tasks": tasks, "maths": maths, "stories": stories, "speak": speak, "badges": badges}


def cert_title(star):
    if star >= 5:
        return "🌟 Superstar of the Week 🌟"
    if star >= 3:
        return "⭐ Shining Star Award ⭐"
    return "🌱 Rising Star Award 🌱"


with tab_weeks:
    st.markdown("### 🏆 My weekly certificates")
    this_monday = today - timedelta(days=today.weekday())
    first_day = min((date.fromisoformat(k) for k, v in data["days"].items() if v), default=today)
    shown = 0
    for w in range(0, 12):
        monday = this_monday - timedelta(weeks=w)
        if monday + timedelta(days=6) < first_day:
            break
        ws = week_summary(data, monday)
        label = f"{monday.strftime('%d %b')} – {(monday + timedelta(days=6)).strftime('%d %b %Y')}"
        pills_ = [f"⭐ {ws['star']} star days", f"✅ {ws['tasks']} tasks", f"🗣️ {ws['speak']} speaking days",
                  f"🧮 {ws['maths']} maths problems", f"📖 {ws['stories']} stories"]
        if w == 0:
            st.markdown(f"**This week so far** ({label}) — finishes on Sunday")
            st.markdown(" · ".join(pills_))
            continue
        if ws["star"] == 0 and ws["tasks"] == 0:
            continue
        shown += 1
        if ws["star"] == 0:
            st.caption(f"{label}: {ws['tasks']} tasks done — earn a star day to get a certificate next week! 💪")
            continue
        with st.expander(f"📜 {cert_title(ws['star'])} · {label}", expanded=(shown == 1)):
            st.markdown(certificate_html(cert_title(ws["star"]), STUDENT_NAME, label, pills_, ws["badges"]),
                        unsafe_allow_html=True)
            st.download_button("🖨️ Download to print", data=certificate_html(
                cert_title(ws["star"]), STUDENT_NAME, label, pills_, ws["badges"], standalone=True),
                file_name=f"certificate_{monday.isoformat()}.html", mime="text/html", key=f"cert_{monday}")
    if shown == 0:
        st.caption("Your first certificate appears after your first full week. Keep going! 🐰")

    st.markdown("### 📅 The last 14 days")
    days14 = [today - timedelta(days=i) for i in range(13, -1, -1)]
    head = "".join(f"<th>{d_.strftime('%a')}<br>{d_.day}</th>" for d_ in days14)
    rows = ""
    for t in TASKS:
        cells = "".join(f"<td>{'✅' if t['id'] in done_on(data, d_) else ('⏳' if t['id'] in ticked_on(data, d_) else '·')}</td>"
                        for d_ in days14)
        rows += f"<tr><td class='name'>{t['emoji']} {t['id']}</td>{cells}</tr>"
    stars_row = "".join(f"<td>{'⭐' if is_star_day(done_on(data, d_)) else ''}</td>" for d_ in days14)
    mins_row = "".join(f"<td>{task_minutes(done_on(data, d_)) or ''}</td>" for d_ in days14)
    rows += f"<tr class='star'><td class='name'>⭐ star day</td>{stars_row}</tr>"
    rows += f"<tr><td class='name'>⏱️ minutes</td>{mins_row}</tr>"
    st.markdown(f"<div class='scroll'><table class='week'><tr><th></th>{head}</tr>{rows}</table></div>",
                unsafe_allow_html=True)


# ================================ GROWN-UPS ================================
def save_edit():
    d_iso = st.session_state.edit_date.isoformat()
    chosen = st.session_state[f"edit_tasks_{d_iso}"]

    star = st.session_state.get(f"edit_star_{d_iso}", False)

    def change(d):
        new = set(chosen) | ({"star"} if star else set())
        d["days"][d_iso] = sorted(new)
        d.setdefault("approved", {})[d_iso] = sorted(chosen)   # a grown-up chose these, so they count
        d.setdefault("earned", {})[d_iso] = task_minutes(new)

    if update(change):
        if d_iso == TODAY_KEY:
            for t in TASKS:
                if not t.get("auto"):
                    st.session_state.pop(f"{TODAY_KEY}_{t['id']}", None)
        st.session_state.flash = "Saved ✔️"


def add_tamil_word():
    en = str(st.session_state.get("tw_en", "")).strip().lower()
    ta = str(st.session_state.get("tw_ta", "")).strip()
    if not en or not ta:
        return

    def change(d):
        d.setdefault("tamil_custom", {})[en] = {"tamil": ta, "note": str(st.session_state.get("tw_note", "")).strip()}

    if update(change):
        st.session_state.tw_en = st.session_state.tw_ta = st.session_state.tw_note = ""
        st.session_state.parent_note = f"🗣️ Added: {en} → {ta}"


def add_tamil_bulk():
    added = {}
    for line in str(st.session_state.get("tw_bulk", "")).splitlines():
        if "=" not in line:
            continue
        en, rest = line.split("=", 1)
        ta, _, note = rest.partition("|")
        en, ta = en.strip().lower(), ta.strip()
        if en and ta:
            added[en] = {"tamil": ta, "note": note.strip()}
    if not added:
        st.session_state.parent_note = "Nothing to add — use the format: english = tamil"
        return

    def change(d):
        d.setdefault("tamil_custom", {}).update(added)

    if update(change):
        st.session_state.tw_bulk = ""
        st.session_state.parent_note = f"🗣️ Added {len(added)} Tamil word{'s' if len(added) != 1 else ''}."


def send_message():
    text = str(st.session_state.get("parent_msg", "")).strip()
    if not text:
        return

    def change(d):
        d.setdefault("messages", []).append({"id": uuid.uuid4().hex[:8], "date": TODAY_KEY, "text": text, "seen": False})

    if update(change):
        st.session_state.parent_msg = ""
        st.session_state.parent_note = f"💌 Message sent! {STUDENT_NAME} will see it next time she opens the app."


def save_feedback(story_id):
    text = str(st.session_state.get(f"fb_{story_id}", "")).strip()

    def change(d):
        for s in d.get("stories", []):
            if s["id"] == story_id:
                s["feedback"] = text

    if update(change):
        st.session_state.parent_note = "📝 Note saved on the story."


def set_wotd():
    w = str(st.session_state.get("wotd_word", "")).strip()
    meaning = str(st.session_state.get("wotd_meaning", "")).strip()

    def change(d):
        if w:
            d.setdefault("wotd_custom", {})[TODAY_KEY] = {"word": w, "meaning": meaning or "", "example": ""}
        else:
            d.setdefault("wotd_custom", {}).pop(TODAY_KEY, None)

    if update(change):
        st.session_state.parent_note = "✨ Word of the day updated."


def adjust_balance():
    mins = int(st.session_state.get("adj_mins", 0) or 0)
    reason = str(st.session_state.get("adj_reason", "")).strip() or "Grown-up adjustment"
    if mins == 0:
        return

    def change(d):
        d.setdefault("credits", []).append({"date": TODAY_KEY, "minutes": mins, "reason": reason})

    if update(change):
        st.session_state.parent_note = f"⏳ Balance {'increased' if mins > 0 else 'reduced'} by {abs(mins)} minutes."


def ate_out():
    def change(d):
        d["last_restaurant"] = TODAY_KEY

    if update(change):
        st.session_state.parent_note = "🍽️ Noted — restaurant prize can be used again in 3 weeks."


def undo_part(i):
    def change(d):
        d.get("chalisa", {}).pop(str(i), None)

    if update(change):
        st.session_state.parent_note = f"↩️ Part {i + 1} marked as not learned yet. (Minutes already given stay.)"


def reset_all():
    def change(d):
        d.clear()
        d.update(migrate(default_data(), today))

    if update(change):
        for k in list(st.session_state.keys()):
            if k.startswith(TODAY_KEY) or k.startswith("wear_"):
                del st.session_state[k]
        st.session_state.flash = "All progress reset."


if st.session_state.get("parent_ok") and \
        datetime.now().timestamp() - st.session_state.get("parent_ok_at", 0) > PARENT_AUTOLOCK_MINUTES * 60:
    st.session_state.parent_ok = False     # auto-lock

with tab_parent:
    if not st.session_state.get("parent_ok"):
        st.markdown("### 🔐 Grown-ups only")
        with st.form("parent_login", border=False):
            pin = st.text_input("PIN", type="password")
            if st.form_submit_button("Open"):
                if pin.strip() == parent_pin():
                    st.session_state.parent_ok = True
                    st.session_state.parent_ok_at = datetime.now().timestamp()
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
        note = st.session_state.pop("parent_note", None)
        if note:
            st.success(note)
        st.caption(f"🔒 This page locks itself after {PARENT_AUTOLOCK_MINUTES} minutes.")

        st.markdown("#### ✅ Approve ticked tasks")
        any_pending = False
        for back in range(0, 8):
            dd = today - timedelta(days=back)
            pend = sorted(pending_on(data, dd))
            if not pend:
                continue
            any_pending = True
            st.markdown(f"**{dd.strftime('%A %d %b')}**")
            st.multiselect("Really done:", pend, default=pend, key=f"gp_pick_{dd}",
                           format_func=lambda x: f"{TASK_BY_ID[x]['emoji']} {TASK_BY_ID[x]['name']}")
            st.button(f"Approve {dd.strftime('%d %b')}", key=f"gp_btn_{dd}",
                      on_click=lambda k=dd.isoformat(), kk=f"gp_pick_{dd}": approve_tasks(k, list(st.session_state.get(kk, [])))) 
        if not any_pending:
            st.caption("Nothing waiting. 🎉")

        st.markdown("#### 💌 Send a message")
        st.text_area("Message", key="parent_msg", placeholder="So proud of your maths today, Andal! 💖", height=80)
        st.button("Send 💌", on_click=send_message)
        msgs = data.get("messages", [])
        if msgs:
            with st.expander(f"Messages sent ({len(msgs)})"):
                for mm in reversed(msgs[-15:]):
                    st.markdown(f"• {mm['date']}: {md_safe(mm['text'])} {'✅ seen' if mm.get('seen') else '🕒 not seen yet'}")

        st.markdown("#### 📖 Stories")
        all_stories = list(reversed(data.get("stories", [])))
        if not all_stories:
            st.caption("No stories yet.")
        for s in all_stories[:15]:
            with st.expander(md_safe(f"{s['title']} · {s['date']} · {s['words']} words · "
                                     f"word of the day used {s.get('wotd_count', 0)}×")):
                st.markdown(f'<div class="story">{html_safe(s["text"]).replace(chr(10), "<br>")}</div>',
                            unsafe_allow_html=True)
                st.text_area("Your note or suggestion", value=s.get("feedback", ""), key=f"fb_{s['id']}", height=70)
                st.button("Save note", key=f"fbsave_{s['id']}", on_click=save_feedback, args=(s["id"],))

        st.markdown("#### ✨ Word of the day")
        cur = word_of_the_day(data, today)
        st.caption(f"Today's word: **{md_safe(cur['word'])}**. Type your own to replace it for today "
                   "(leave the word empty and save to go back to the automatic one).")
        wc1, wc2 = st.columns(2)
        wc1.text_input("Word", key="wotd_word")
        wc2.text_input("Meaning", key="wotd_meaning")
        st.button("Set word of the day", on_click=set_wotd)
        sents = [x for x in data.get("wotd_sentences", {}).get(TODAY_KEY, []) if x]
        if sents:
            st.markdown(f"**{STUDENT_NAME}'s sentences today:**")
            for x in sents:
                st.markdown(f"• {md_safe(x)}")

        st.markdown("#### 🙏 Hanuman Chalisa")
        chd = data.get("chalisa", {})
        bsx = bead_status(data)
        st.write(f"Parts learned: **{len(chd)}/{len(CHALISA_PARTS)}** · beads: **{bsx['beads']}** · "
                 f"screen-time rewards given: {data.get('bead_rewards_given', 0)} × {BEAD_MINUTES} min")
        if data.get("chalisa_reward"):
            r_ = data["chalisa_reward"]
            st.write(f"Outing choice: {md_safe(r_['choice'])} ({r_['status']})")
        if chd:
            last_i = max(int(k) for k in chd)
            st.button(f"↩️ Undo Part {last_i + 1} (needs more practice)", on_click=undo_part, args=(last_i,))

        st.markdown("#### 😊 Mood check-ins")
        moods = data.get("moods", [])
        if moods:
            st.write("  ".join(f"{next((m[1] for m in MOODS if m[0] == x['mood']), '?')} "
                               f"{date.fromisoformat(x['date']).strftime('%d %b')} {x['time']}"
                               for x in reversed(moods[-20:])))
        else:
            st.caption("No check-ins yet.")

        st.markdown("#### ⏳ Screen-time balance")
        st.write(f"Balance **{bal['balance']} min** = earned from tasks {bal['earned']} + extras {bal['credits']} "
                 f"− used {bal['used']}.")
        used = data.get("used", [])
        if used:
            with st.expander("Recent minutes used"):
                for u in reversed(used[-15:]):
                    st.write(f"• {u['date']} {u.get('time', '')}: {u['minutes']} min")
        ac1, ac2 = st.columns(2)
        ac1.number_input("Add (+) or remove (−) minutes", step=5, value=0, key="adj_mins")
        ac2.text_input("Reason", key="adj_reason", placeholder="e.g. extra chores")
        st.button("Adjust balance", on_click=adjust_balance)

        st.markdown("#### 🍽️ Restaurant dinners")
        last = data.get("last_restaurant")
        st.caption(f"Last family restaurant dinner: {last or 'not recorded'}. The 🍽️ wheel prize needs "
                   f"{RESTAURANT_GAP_DAYS // 7} weeks between dinners.")
        st.button("We had a family restaurant dinner today", on_click=ate_out)

        st.markdown("#### ✏️ Fix a day")
        st.caption("Forgot to tick something on a past day? Correct it here — streaks update automatically.")
        st.date_input("Day", value=today, max_value=today, key="edit_date", format="DD/MM/YYYY")
        d_iso = st.session_state.edit_date.isoformat()
        st.multiselect("Tasks done that day", options=[t["id"] for t in TASKS],
                       default=sorted(ticked_on(data, st.session_state.edit_date) & set(TASK_BY_ID)),
                       format_func=lambda tid: f"{TASK_BY_ID[tid]['emoji']} {TASK_BY_ID[tid]['name']}",
                       key=f"edit_tasks_{d_iso}")
        st.checkbox("⭐ Count this day as a star day (even if not every task is ticked)",
                    value="star" in done_on(data, st.session_state.edit_date), key=f"edit_star_{d_iso}")
        st.button("Save this day", on_click=save_edit)

        st.markdown("#### 🗣️ Add a Tamil word")
        st.caption("Add words she looks up that aren't in the list yet (or change how your family says one).")
        tc1, tc2, tc3 = st.columns(3)
        tc1.text_input("English", key="tw_en")
        tc2.text_input("Tamil (in English letters)", key="tw_ta")
        tc3.text_input("Note (optional)", key="tw_note")
        st.button("Add word", on_click=add_tamil_word)
        with st.expander("➕ Add many words at once"):
            st.caption("One word per line: english = tamil   (optionally add  | note). Example:\n"
                       "rainbow = vaanavil\nkite = pattam | also 'paattam'")
            st.text_area("Words", key="tw_bulk", height=140, placeholder="rainbow = vaanavil\nkite = pattam")
            st.button("Add all", on_click=add_tamil_bulk)
        if data.get("tamil_custom"):
            st.caption("Added: " + ", ".join(f"{k} → {v['tamil']}" for k, v in data["tamil_custom"].items()))

        st.markdown("#### 🎁 Rewards & prizes history")
        hist = [(h["date"], "$1" if h["reward"] == "dollar" else next(
            (f"{r['emoji']} {r['name']}" for r in REWARDS if r["id"] == h["reward"]),
            "🧸 Toy shop trip" if h["reward"] == "toyshop" else
            ("🙏 Chalisa outing" if h["reward"] == "chalisa_outing" else h["reward"]))) for h in data["history"]]
        hist += [(s.get("done_date", s["date"]), f"{s['emoji']} {s['name']} ({s['wheel']} wheel)")
                 for s in data.get("spins", []) if s["status"] != "waiting"]
        if hist:
            for dt, name in sorted(hist, reverse=True)[:25]:
                st.markdown(f"• {date.fromisoformat(dt).strftime('%d %b %Y')} — {md_safe(name)}")
        else:
            st.caption("None yet.")

        with st.expander("⚠️ Reset everything"):
            confirm = st.checkbox(f"Yes, delete all of {STUDENT_NAME}'s progress")
            st.button("Reset all progress", on_click=reset_all, disabled=not confirm)

        if st.button("🔒 Lock"):
            st.session_state.parent_ok = False
            st.rerun()


# ---- hopping friends (purely decorative, never block taps) ----
if ANIMATED_FRIENDS:
    st.markdown(friends_html(), unsafe_allow_html=True)
