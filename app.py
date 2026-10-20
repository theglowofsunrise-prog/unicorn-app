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
WEEKEND_RULES_FROM = "2026-10-17"   # weekend must-do rules start on this Saturday
WEEKEND_MUST = ["chalisa", "tidy", "exercise", "meditate", "sit1", "sit2"]   # extra must-dos on Sat & Sun
WEEKEND_CHALISA_PARTS = 2      # Chalisa parts to learn (and recite to a grown-up) every weekend
CHALISA_REPEATS = 21           # times to say each part before it can be recited to a grown-up
WEEKEND_MAX_STRETCH = 40       # weekends: most screen minutes in one go, even with more saved
QUOTE_HOURS = 1                # a new quote and health tip every hour
BEDTIME = "9:30 pm"            # bedtime for the 'in bed on time' task
PARENT_WORDS = "Amma or Appa"  # what she calls her grown-ups
PROGRESS_PATH = "progress.json"   # file in the private data repo (each child has her own)
PIN_SECRET = "PARENT_PIN"      # which Secrets entry holds this child's grown-up PIN
EMAIL_SECRET = "email"         # which Secrets section holds this child's email alerts
SHOW_TAMIL = True              # Tamil words tab
SHOW_CHALISA = True            # Hanuman Chalisa tab

# id: short code (don't change once she has progress)   minutes: screen time it earns
# required: True = must be done before ANY screen time unlocks that day
TASKS = [
    {"id": "homework", "emoji": "📒", "name": "Finish today's homework", "minutes": 10,
     "required": True, "section": "must"},
    {"id": "speak", "emoji": "🗣️", "name": f"Speak {LANGUAGE} for 10 minutes", "minutes": 10,
     "required": True, "section": "must"},
    {"id": "write1", "emoji": "✏️", "name": "English writing – piece 1 (on paper)", "minutes": 5, "section": "learn"},
    {"id": "write2", "emoji": "📝", "name": "English writing – piece 2 (on paper)", "minutes": 5, "section": "learn"},
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
    # weekend-only tasks (Saturday & Sunday)
    {"id": "chalisa", "emoji": "🙏", "name": "Hanuman Chalisa: practise this weekend's parts", "minutes": 5,
     "section": "learn", "days": "weekend"},
    {"id": "tidy", "emoji": "🧹", "name": "Tidy & organise my room, desk and play space for 20 minutes",
     "minutes": 5, "section": "body", "days": "weekend"},
    # ---- daily routines (must do, from NEW_MUSTS_FROM) ----
    {"id": "schoolnotes", "emoji": "🏫", "name": "Write in Notes (with Scribble) what I learnt at school today",
     "minutes": 2, "required": True, "section": "must", "days": "school", "from": "NEW_MUSTS"},
    {"id": "lunchbox", "emoji": "🍱", "name": "Put my lunch box from my school bag at the sink for washing",
     "minutes": 2, "required": True, "section": "must", "days": "school", "from": "NEW_MUSTS"},
    {"id": "bagpack", "emoji": "🎒", "name": "Packed my school bag last night before bed "
     "(homework book, library book and everything for today)", "minutes": 2, "required": True, "section": "must",
     "days": "school", "from": "NEW_MUSTS"},
    {"id": "paati", "emoji": "👵🏽", "name": "Maths with Paati for 10–12 minutes (work it out on paper)",
     "minutes": 2, "required": True, "section": "must", "from": "NEW_MUSTS"},
    {"id": "mindful", "emoji": "🫧", "name": "One easy mindfulness activity (try the 🧘 Calm corner)",
     "minutes": 2, "required": True, "section": "must", "from": "NEW_MUSTS"},
    {"id": "comb", "emoji": "💇‍♀️", "name": "Comb my hair nicely", "minutes": 2, "required": True,
     "section": "must", "days": "weekend", "from": "NEW_MUSTS"},
]
NEW_MUSTS_FROM = "2026-10-21"     # the daily-routine must-dos above start on this day


def _as_date(d):
    return d if isinstance(d, date) else date.fromisoformat(str(d))


def weekend_rules(d) -> bool:
    """True on Saturdays and Sundays from WEEKEND_RULES_FROM onwards."""
    if d is None:
        return False
    d = _as_date(d)
    return d.weekday() >= 5 and d.isoformat() >= WEEKEND_RULES_FROM


def task_on(t, d) -> bool:
    """Does this task apply on day d?  days: weekend / school (Mon–Fri) / none = every day."""
    if d is None:
        return not t.get("days") and not t.get("from")
    d = _as_date(d)
    if t.get("from") == "NEW_MUSTS" and d.isoformat() < NEW_MUSTS_FROM:
        return False
    days = t.get("days")
    if days == "weekend":
        return weekend_rules(d)
    if days == "school":
        return d.weekday() < 5
    return True


def tasks_for(d):
    return [t for t in TASKS if task_on(t, d)]


def required_ids(d) -> set:
    req = {t["id"] for t in TASKS if t.get("required") and task_on(t, d)}
    if weekend_rules(d):
        req |= set(WEEKEND_MUST)
    return req

SECTIONS = [
    ("must", "🦄 Must do today"),
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
     "how": f"In bed by {BEDTIME} every night for 30 nights in a row."},
    {"id": "playcentre", "emoji": "🎠", "name": "Play centre of your choice (up to $50)", "streak_task": "bed",
     "streak_len": 90, "window": 90, "needs": {},
     "how": f"In bed by {BEDTIME} every night for 3 months (90 nights) in a row."},
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

# "free": True = always available (not a reward). "icons" = the 4 tappable hero icons (emoji, joke key)
THEMES = [
    {"id": "icepalace", "name": "❄️ Ice Palace", "need": 0, "free": True,
     "icons": [("❄️", "snow"), ("👑", "crown"), ("⛄", "snowman"), ("✨", "star")]},
    {"id": "springprincess", "name": "🌷 Spring Princess", "need": 0, "free": True,
     "icons": [("🌷", "flower"), ("👑", "crown"), ("🦌", "reindeer"), ("🍫", "chocolate")]},
    {"id": "snowyfun", "name": "⛄ Snowy Fun", "need": 0, "free": True,
     "icons": [("⛄", "snowman"), ("🥕", "carrot"), ("🦌", "reindeer"), ("❄️", "snow")]},
    {"id": "planetpals", "name": "🪐 Planet Pals", "need": 0, "free": True,
     "icons": [("☀️", "sun"), ("🪐", "planet"), ("🌍", "earth"), ("🌙", "moon")]},
    {"id": "sunnysolar", "name": "☀️ Sunny Solar", "need": 0, "free": True,
     "icons": [("☀️", "sun"), ("☄️", "comet"), ("🚀", "rocket"), ("⭐", "star")]},
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
ICON_JOKES.update({
    "snow": [
        "Fact: Every snowflake has six sides (or six points)! ❄️",
        "Fact: Snow looks white, but each little ice crystal is actually clear like glass! 🧊",
        "What do snowflakes like to do on holiday? Chill out! 😎",
        "Fact: The biggest snowflake ever reported was said to be as wide as a dinner plate! 🍽️",
    ],
    "crown": [
        "Why did the princess bring a ladder to the ball? To reach the high notes! 🎶",
        "Fact: Some royal crowns have more than 2,000 diamonds! 💎",
        "What's a queen's favourite weather? Reign! 🌧️👑",
    ],
    "snowman": [
        "What do snowmen eat for breakfast? Frosted flakes! 🥣",
        "Where do snowmen keep their money? In a snow bank! 🏦",
        "What do you call a snowman in summer? A puddle! 💧",
        "What do snowmen like to do at parties? Chill! 🎉",
    ],
    "reindeer": [
        "Fact: Reindeer are the only deer where the girls grow antlers too! 🦌",
        "Fact: Reindeer eyes change colour — golden in summer and blue in winter! 👀",
        "Why did the reindeer get a ticket? It was caught speeding through the snow! 🚓",
    ],
    "flower": [
        "Fact: Tulips can keep growing about 2 cm after they're cut and put in a vase! 🌷",
        "What did the big flower say to the little flower? Hi, bud! 🌱",
        "Fact: Sunflowers turn to follow the Sun when they're young! 🌻",
    ],
    "chocolate": [
        "Fact: Chocolate comes from cocoa beans that grow in pods on trees! 🍫",
        "Fact: Long ago, cocoa beans were used as money in Central America! 🪙",
        "Why did the chocolate bar go to school? To become a smarty! 🎓",
    ],
    "carrot": [
        "Fact: Long ago, carrots were purple and yellow — orange ones came later! 🥕",
        "What's a carrot's favourite game? Root-ball! ⚽",
    ],
    "sun": [
        "Fact: About 1.3 million Earths could fit inside the Sun! ☀️",
        "Fact: Sunlight takes about 8 minutes to reach Earth! ⏱️",
        "Why did the Sun go to school? To get brighter! 🎓",
        "Fact: The Sun is so big it holds almost all the mass of our solar system! 🌞",
    ],
    "planet": [
        "Fact: Saturn is so light that it would float in a giant bathtub! 🛁🪐",
        "Fact: Jupiter is the biggest planet — more than 1,300 Earths could fit inside! 🟠",
        "Fact: A day on Venus is longer than its whole year! 🤯",
        "How do you throw a space party? You planet! 🎉",
        "Fact: Neptune has the fastest winds in the solar system! 💨",
        "Fact: Mars has the tallest volcano we know of, Olympus Mons! 🌋",
    ],
    "earth": [
        "Fact: Earth is the only planet not named after a god or goddess! 🌍",
        "Fact: About 71% of Earth is covered by water! 🌊",
        "Fact: Earth spins at about 1,600 km per hour at the equator! 🌀",
    ],
    "moon": [
        "Fact: The Moon is slowly moving away from Earth — about 4 cm every year! 🌙",
        "Fact: Footprints on the Moon can last for millions of years, because there's no wind! 👣",
        "Why did the cow jump over the Moon? To get to the Milky Way! 🐄🥛",
    ],
    "comet": [
        "Fact: Comets are giant dirty snowballs made of ice, dust and rock! ☄️",
        "Fact: A comet's tail always points away from the Sun! ➡️",
    ],
    "rocket": [
        "Fact: Astronauts grow a little taller in space! 📏🚀",
        "Fact: In space, astronauts can't cry tears that fall — they float as little balls! 💧",
        "What do astronauts eat their lunch on? Satellite dishes! 🍽️",
    ],
})

# Inspiring quotes: (quote, who said it, who they were, what it means). A new one every QUOTE_HOURS hours.
QUOTES = [
    ("I have no special talents. I am only passionately curious.", "Albert Einstein", "scientist",
     "Being curious and asking lots of questions is a superpower."),
    ("Imagination is more important than knowledge.", "Albert Einstein", "scientist",
     "Dreaming up new ideas helps us discover things nobody knows yet."),
    ("Life is like riding a bicycle. To keep your balance, you must keep moving.", "Albert Einstein",
     "scientist, in a letter to his son", "Keep going, even when things wobble!"),
    ("Nothing in life is to be feared, it is only to be understood.", "Marie Curie",
     "scientist who won two Nobel Prizes", "When something feels scary, learning about it makes it smaller."),
    ("If I have seen further, it is by standing on the shoulders of giants.", "Isaac Newton", "scientist",
     "We learn so much from the people who came before us — teachers, parents and books."),
    ("Genius is one percent inspiration and ninety-nine percent perspiration.", "Thomas Edison", "inventor",
     "Great work is mostly hard work. (Perspiration means sweat!)"),
    ("Chance favours the prepared mind.", "Louis Pasteur", "scientist",
     "Good luck comes most often to people who have practised and prepared."),
    ("Give me a place to stand, and I will move the Earth.", "Archimedes", "Greek mathematician",
     "With a clever idea (like a lever!), you can do enormous things."),
    ("Remember to look up at the stars and not down at your feet.", "Stephen Hawking", "scientist",
     "Stay curious about the big, amazing universe."),
    ("However difficult life may seem, there is always something you can do and succeed at.", "Stephen Hawking",
     "scientist", "Even on hard days, there is always something you can do well."),
    ("What you do makes a difference, and you have to decide what kind of difference you want to make.",
     "Jane Goodall", "scientist who studied chimpanzees", "Every choice you make changes the world a little bit."),
    ("Like what you do, and then you will do your best.", "Katherine Johnson", "NASA mathematician",
     "When you enjoy something, you put your best into it."),
    ("That's one small step for a man, one giant leap for mankind.", "Neil Armstrong",
     "the first person to walk on the Moon", "Small steps can be part of something giant."),
    ("Ask the right questions, and nature will open the doors to her secrets.", "C. V. Raman",
     "Indian scientist who won the Nobel Prize", "Good questions are the key to big discoveries."),
    ("Dream, dream, dream. Dreams transform into thoughts, and thoughts result in action.", "Dr A. P. J. Abdul Kalam",
     "scientist and President of India, from Tamil Nadu", "Big dreams turn into plans, and plans turn into doing."),
    ("If you want to shine like a sun, first burn like a sun.", "Dr A. P. J. Abdul Kalam",
     "scientist and President of India, from Tamil Nadu", "To shine brightly, you have to put in the hard work first."),
    ("Great things are done by a series of small things brought together.", "Vincent van Gogh", "painter",
     "Lots of little efforts add up to something great."),
    ("All truths are easy to understand once they are discovered; the point is to discover them.",
     "Galileo Galilei", "scientist and astronomer", "Exploring and finding things out is the exciting part!"),
    ("The most effective way to do it, is to do it.", "Amelia Earhart",
     "first woman to fly solo across the Atlantic Ocean", "Stop waiting — just start!"),
    ("A journey of a thousand miles begins with a single step.", "Lao Tzu", "Chinese philosopher",
     "Every big goal starts with one small step."),
    ("When I walk along with two others, they may serve me as my teachers.", "Confucius", "Chinese philosopher",
     "You can learn something from everyone around you."),
    ("To know what you know and to know what you do not know — that is true knowledge.", "Confucius",
     "Chinese philosopher", "It's smart to say 'I don't know yet' — then you can learn it."),
    ("While we teach, we learn.", "Seneca", "Roman philosopher",
     "Explaining something to someone else helps you understand it better."),
    ("Well begun is half done.", "Aristotle", "Greek philosopher",
     "A good start makes the rest much easier."),
    ("We are what we repeatedly do. Excellence, then, is not an act, but a habit.", "Will Durant",
     "writer, explaining the ideas of Aristotle", "Doing something again and again (like 21 times!) makes you great at it."),
    ("Waste no more time arguing about what a good man should be. Be one.", "Marcus Aurelius",
     "Roman emperor and philosopher", "Don't just talk about being good — be good!"),
    ("The mind is not a vessel to be filled, but a fire to be kindled.", "Plutarch", "Greek writer",
     "Learning isn't just filling your head with facts — it's lighting up your curiosity."),
    ("Wonder is the beginning of wisdom.", "Socrates", "Greek philosopher",
     "Wondering 'why?' is how wisdom starts."),
    ("Arise, awake, and stop not till the goal is reached.", "Swami Vivekananda", "Indian thinker and teacher",
     "Get up, get going, and don't stop until you reach your goal."),
    ("Do your work with your whole heart, and don't worry about the reward.", "Bhagavad Gita",
     "the simple meaning of verse 2.47", "Focus on doing your best; good things follow."),
    ("We are what we think.", "The Buddha", "teacher, from the Dhammapada",
     "Happy, kind thoughts help make a happy, kind you."),
    ("It is not the mountain we conquer, but ourselves.", "Sir Edmund Hillary",
     "one of the first two people to climb Mount Everest", "The biggest win is beating your own fears and doubts."),
    ("How wonderful it is that nobody need wait a single moment before starting to improve the world.", "Anne Frank",
     "young writer", "You can start making the world better right now — even today!"),
    ("One child, one teacher, one book, one pen can change the world.", "Malala Yousafzai",
     "youngest-ever Nobel Peace Prize winner", "Learning is powerful — and you have it!"),
    ("Alone we can do so little; together we can do so much.", "Helen Keller",
     "author who was deaf and blind", "Teamwork makes big things possible."),
    ("The best and most beautiful things in the world cannot be seen or even touched — they must be felt with the heart.",
     "Helen Keller", "author who was deaf and blind", "Love, kindness and friendship are the real treasures."),
    ("You must do the thing you think you cannot do.", "Eleanor Roosevelt", "writer and leader",
     "Try the thing that feels too hard — you might surprise yourself!"),
    ("Do what you can, with what you have, where you are.", "Theodore Roosevelt", "President of the USA",
     "You don't need everything to be perfect to start."),
    ("If you can't fly, then run. If you can't run, then walk. If you can't walk, then crawl. But whatever you do, "
     "you have to keep moving forward.", "Martin Luther King Jr.", "leader who fought for fairness",
     "Keep going forward, even if it's slowly."),
    ("Try to be a rainbow in someone's cloud.", "Maya Angelou", "poet and writer",
     "Brighten someone's day when they are feeling sad."),
    ("Well done is better than well said.", "Benjamin Franklin", "inventor and writer",
     "Doing something is better than just talking about it."),
    ("Lost time is never found again.", "Benjamin Franklin", "inventor and writer",
     "Use your time wisely — you can't get it back."),
    ("Whether you think you can, or you think you can't — you're right.", "Henry Ford", "car maker",
     "Believing in yourself is the first step."),
    ("Katrathu kai mann alavu, kallaathathu ulagalavu — what we have learned is a handful of sand; what we haven't "
     "learned is as big as the world.", "Avvaiyar", "great Tamil poet", "There is always so much more to learn!"),
    ("Ookkamathu kaividel — never give up your enthusiasm.", "Avvaiyar", "great Tamil poet, from Aathichoodi",
     "Keep your energy and excitement, even when it's hard."),
    ("Enn ezhuthu igazhel — never look down on numbers and letters.", "Avvaiyar",
     "great Tamil poet, from Aathichoodi", "Maths and reading are treasures — treat them with respect!"),
    ("Aram seya virumbu — love to do good deeds.", "Avvaiyar", "great Tamil poet, from Aathichoodi",
     "Enjoy helping others and doing what's right."),
    ("Learn well what you should learn, and then live by what you have learned.", "Thiruvalluvar",
     "Tamil poet, Thirukkural 391", "Learning is best when you use it in your life."),
    ("The deeper you dig a well in the sand, the more water flows; the more you learn, the more knowledge flows.",
     "Thiruvalluvar", "Tamil poet, Thirukkural 396", "Keep learning and your knowledge keeps growing."),
    ("Even when luck isn't on your side, hard work always brings its reward.", "Thiruvalluvar",
     "Tamil poet, Thirukkural 619", "Effort always pays off."),
    ("Saying harsh words when kind words are there is like picking an unripe fruit when a ripe one is right there.",
     "Thiruvalluvar", "Tamil poet, Thirukkural 100", "Always choose the kind words."),
    ("A lotus stem grows as tall as the water is deep; a person rises as high as their spirit.", "Thiruvalluvar",
     "Tamil poet, Thirukkural 595", "Big hopes and a strong heart help you rise high."),
    ("Odi vilaiyaadu paappa — run and play, little one; don't sit around being lazy!", "Subramania Bharati",
     "great Tamil poet", "Move your body, play and stay active!"),
    ("The more that you read, the more things you will know. The more that you learn, the more places you'll go.",
     "Dr. Seuss", "children's author", "Reading opens doors to the whole world."),
    ("Today you are You, that is truer than true. There is no one alive who is Youer than You.", "Dr. Seuss",
     "children's author", "There is only one you — and that's wonderful!"),
    ("If you have good thoughts they will shine out of your face like sunbeams and you will always look lovely.",
     "Roald Dahl", "children's author, from The Twits", "Kind thoughts make you shine on the outside too."),
    ("A little Consideration, a little Thought for Others, makes all the difference.", "A. A. Milne",
     "author of Winnie-the-Pooh (said by Eeyore)", "Small acts of kindness matter a lot."),
    ("No act of kindness, no matter how small, is ever wasted.", "Aesop", "storyteller, from The Lion and the Mouse",
     "Even tiny kind acts can make a big difference."),
    ("Slow and steady wins the race.", "Aesop", "storyteller, from The Tortoise and the Hare",
     "Keep going steadily — you'll get there!"),
    ("Fall seven times, stand up eight.", "Japanese proverb", "a wise saying from Japan",
     "However many times you fall, get up one more time."),
    ("I've failed over and over and over again in my life. And that is why I succeed.", "Michael Jordan",
     "basketball champion", "Mistakes help you learn and get better."),
    ("You miss 100% of the shots you don't take.", "Wayne Gretzky", "ice hockey champion",
     "You have to try to have a chance of winning."),
    ("Don't let what you cannot do interfere with what you can do.", "John Wooden", "famous basketball coach",
     "Focus on all the things you CAN do."),
    ("Success is no accident. It is hard work, perseverance, learning, studying, sacrifice and most of all, "
     "love of what you are doing.", "Pelé", "football champion", "Success comes from hard work and loving what you do."),
    ("Chase your dreams, because dreams do come true.", "Sachin Tendulkar", "cricket champion",
     "Keep working toward your dreams."),
    ("Don't count the days, make the days count.", "Muhammad Ali", "boxing champion",
     "Make every day a good one!"),
    ("I think a champion is defined not by their wins, but by how they can recover when they fall.",
     "Serena Williams", "tennis champion", "Champions get back up after they fall."),
    ("We all have dreams. But in order to make dreams come into reality, it takes an awful lot of determination, "
     "dedication, self-discipline, and effort.", "Jesse Owens", "Olympic running champion",
     "Dreams come true with effort and practice."),
    ("I don't think limits.", "Usain Bolt", "fastest runner in the world",
     "Don't decide what you can't do before you try."),
    ("I'd rather regret the risks that didn't work out than the chances I didn't take at all.", "Simone Biles",
     "Olympic gymnastics champion", "It's better to try and miss than never try at all."),
]
ANIMATED_FRIENDS = True        # friendly characters visit the screen now and then (tap them!)
VISIT_EVERY_SECONDS = (120, 120)   # a new visitor every 2 minutes
# Each friend: emoji, how it moves, sound when tapped, sayings (one pops up when it visits)
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

FRIENDS += [
    {"id": "twinkle", "emoji": "🌟", "move": "twinkle", "sound": "sparkle", "says": [
        "Twinkle twinkle! Stars are giant balls of glowing gas! ✨",
        "Our Sun is a star — the closest one to Earth! ☀️",
        "Starlight can take thousands of years to reach your eyes! 👀",
        "You're a star when you try your best! ⭐"]},
    {"id": "trex", "emoji": "🦖", "move": "stomp", "sound": "grunt", "says": [
        "RAWR! I'm a T. rex — my teeth were as long as bananas! 🍌",
        "Dinosaurs lived millions of years before people! 🕰️",
        "Birds are living relatives of dinosaurs! 🐦",
        "My arms are tiny, but my brain says: never give up! 💪"]},
    {"id": "dino", "emoji": "🦕", "move": "stomp", "sound": "grunt", "says": [
        "Long-neck dinosaurs ate plants — like a giant salad! 🥗",
        "Some long-neck dinosaurs were longer than 3 buses! 🚌🚌🚌",
        "Fossils help scientists learn about dinosaurs! 🦴",
        "Slow and steady — that's my style! 🐢"]},
    {"id": "croc", "emoji": "🐊", "move": "swim", "sound": "grunt", "says": [
        "Snap snap! Crocodiles have been around since the dinosaurs! 🦖",
        "Saltwater crocodiles live in northern Australia! 🇦🇺",
        "I can hold my breath underwater for a very long time! 🫧",
        "Brush your teeth twice a day — I have about 60 of them! 🪥"]},
    {"id": "dolphin", "emoji": "🐬", "move": "swim", "sound": "tweet", "says": [
        "Dolphins call each other with special whistles — like names! 📣",
        "Dolphins sleep with half their brain at a time! 😴",
        "I'm a mammal, not a fish — I breathe air! 💨",
        "Splash! Drink some water — stay hydrated! 💧"]},
    {"id": "octopus", "emoji": "🐙", "move": "swim", "sound": "pop", "says": [
        "I have three hearts and blue blood! 💙",
        "Octopuses can change colour to hide! 🎨",
        "Eight arms — perfect for doing homework AND maths! 📚",
        "I squirt ink to escape! 🖋️"]},
    {"id": "turtle", "emoji": "🐢", "move": "swim", "sound": "pop", "says": [
        "Sea turtles can travel thousands of kilometres! 🌊",
        "Slow and steady wins the race! 🏁",
        "Please don't drop plastic — it hurts sea turtles! ♻️",
        "Baby turtles race to the sea when they hatch! 🏃"]},
    {"id": "whale", "emoji": "🐳", "move": "swim", "sound": "grunt", "says": [
        "The blue whale is the biggest animal that ever lived! 🐋",
        "Humpback whales sing songs that travel across the ocean! 🎶",
        "Whales swim past the Queensland coast every winter! 🌊",
        "Take a deep breath… and relax! 🧘"]},
    {"id": "shark", "emoji": "🦈", "move": "swim", "sound": "boing", "says": [
        "Sharks were around even before the dinosaurs! 🦖",
        "Sharks have no bones — their skeleton is cartilage, like your ears! 👂",
        "Some sharks lose thousands of teeth in their life — and grow new ones! 🦷",
        "Keep swimming, keep learning! 🏊"]},
    {"id": "crab", "emoji": "🦀", "move": "waddle", "sound": "pop", "says": [
        "I walk sideways! Can you? ↔️",
        "Crabs wear their skeleton on the outside! 🦴",
        "Pinch pinch! Time to tidy up? 🧹",
        "Don't be crabby — smile! 😄"]},
    {"id": "owl", "emoji": "🦉", "move": "fly", "sound": "tweet", "says": [
        "Hoo hoo! Owls can turn their heads really far around! 🔄",
        "Wise owl tip: read a little every day! 📚",
        "Owls fly almost silently! 🤫",
        "Bedtime by 9:30 helps your brain grow! 🌙"]},
    {"id": "bee", "emoji": "🐝", "move": "flutter", "sound": "tweet", "says": [
        "Buzz! Bees do a waggle dance to tell friends where flowers are! 💃",
        "Bees help plants grow fruit and veggies! 🍎",
        "Be busy as a bee — finish your tasks! ✅",
        "One bee makes only a tiny bit of honey in its whole life! 🍯"]},
    {"id": "penguin", "emoji": "🐧", "move": "waddle", "sound": "boing", "says": [
        "Penguins can't fly, but they're super swimmers! 🏊",
        "Little penguins live in southern Australia! 🇦🇺",
        "Emperor penguin dads keep the egg warm on their feet! 🥚",
        "Waddle waddle… exercise time! 🤸"]},
    {"id": "elephant", "emoji": "🐘", "move": "stomp", "sound": "grunt", "says": [
        "Elephants never forget… well, they have amazing memories! 🧠",
        "An elephant's trunk has thousands of muscles! 💪",
        "Elephants greet friends by twisting trunks together! 🤝",
        "Practise 21 times and you'll remember like an elephant! 🙏"]},
    {"id": "rocket", "emoji": "🚀", "move": "fly", "sound": "sparkle", "says": [
        "3… 2… 1… blast off! 🚀",
        "It takes about 3 days to fly to the Moon! 🌙",
        "Astronauts exercise every day in space to stay strong! 💪",
        "Aim for the stars! ⭐"]},
    {"id": "fairy", "emoji": "🧚", "move": "flutter", "sound": "sparkle", "says": [
        "Sprinkle sprinkle! A kind word is real magic! ✨",
        "Every time you try, you get a little stronger! 💖",
        "Make your bed — it's a magic start to the day! 🛏️",
        "Believe in yourself! 🌈"]},
    {"id": "dragon", "emoji": "🐉", "move": "fly", "sound": "grunt", "says": [
        "Real Komodo dragons live in Indonesia — they're giant lizards! 🦎",
        "Breathe in like a dragon… and out slowly! 🧘",
        "Brave like a dragon — try the hard maths problem! 🔢",
        "Dragons guard treasure — your treasure is learning! 💎"]},
    {"id": "robot", "emoji": "🤖", "move": "stomp", "sound": "tick", "says": [
        "Beep boop! Robots help build cars and explore Mars! 🚗",
        "Robots follow instructions called code! 💻",
        "Practice makes progress! Beep! 🔁",
        "Charging… done! Ready to learn! 🔋"]},
]

FRIENDS += [
    {"id": "elyssa", "name": "Elyssa", "emoji": "👧🏼", "move": "hop", "sound": "sparkle", "says": [
        "Hi Andal! I finished my spelling homework — high five! ✋",
        "In class today we learned about volcanoes! 🌋 What did you learn?",
        "Homework first, then we can play! 📚➡️⚽",
        "Camping tip: pack a torch and spare batteries! 🔦",
        "Camping tip: always tell a grown-up before you go exploring! 🏕️",
        "Camping tip: wear a hat and sunscreen, even when it's cloudy! 🧢",
        "I'm SO excited for camp! Are you? ⛺"]},
    {"id": "priya", "name": "Priya", "emoji": "👧🏽", "move": "hop", "sound": "tweet", "says": [
        "Hi! I practised my times tables in the car today! ✖️",
        "I'm going to dance class after school! 💃",
        "Let's both read one chapter before bed tonight! 📖",
        "Camping tip: bring a water bottle and drink often! 💧",
        "Camping tip: shake your shoes before you put them on — bugs love hiding there! 👟",
        "Camping tip: leave the campsite cleaner than you found it! ♻️"]},
    {"id": "mia", "name": "Mia", "emoji": "👧🏻", "move": "hop", "sound": "pop", "says": [
        "Art class was so fun — I painted a rainbow! 🎨",
        "My homework trick: do the hardest bit first! 💪",
        "Swimming lessons today — I can float on my back now! 🏊‍♀️",
        "Camping tip: pack warm pyjamas — nights at camp get chilly! 🧦",
        "Camping tip: stay with your buddy the whole time! 👭",
        "Camping tip: pack a raincoat, just in case! 🌧️"]},
    {"id": "panda", "emoji": "🐼", "move": "waddle", "sound": "grunt", "says": [
        "Giant pandas spend about 12 hours a day eating bamboo! 🎋",
        "A newborn panda is about the size of a stick of butter! 🧈",
        "Pandas are great tree climbers! 🌳"]},
    {"id": "giraffe", "emoji": "🦒", "move": "stomp", "sound": "boing", "says": [
        "Giraffes sleep very little — but YOU need 9–12 hours! 😴",
        "My tongue is about 50 cm long! 👅",
        "Every giraffe has its own special pattern of spots — just like you're one of a kind! 🌟"]},
    {"id": "flamingo", "emoji": "🦩", "move": "fly", "sound": "tweet", "says": [
        "Flamingos are pink because of the food they eat! 🦐",
        "Can you balance on one leg like me? Try for 10 seconds! 🦵"]},
    {"id": "ladybird", "emoji": "🐞", "move": "flutter", "sound": "pop", "says": [
        "Ladybirds help gardens by eating tiny pests called aphids! 🌱",
        "My spots warn birds that I taste yucky! 🔴"]},
    {"id": "comet", "emoji": "☄️", "move": "fly", "sound": "sparkle", "says": [
        "Halley's Comet visits about every 76 years — next time in 2061! 🔭",
        "Comets are icy, dusty space snowballs! ❄️"]},
]
for _f in FRIENDS:                      # friends with names say who they are
    if _f.get("name"):
        _f["says"] = [f"{_f['name']}: {_x}" for _x in _f["says"]]

# Mindfulness, meditation, health and exercise quotes (shown every other hour). (quote, who, who they were, meaning)
MINDFUL_QUOTES = [
    ("Breath is the bridge which connects life to consciousness, which unites your body to your thoughts.",
     "Thich Nhat Hanh", "Zen teacher and mindfulness writer", "Noticing your breathing helps your body and mind feel calm together."),
    ("Feelings come and go like clouds in a windy sky. Conscious breathing is my anchor.", "Thich Nhat Hanh",
     "Zen teacher and mindfulness writer", "Big feelings pass. Slow breaths keep you steady."),
    ("Walk as if you are kissing the Earth with your feet.", "Thich Nhat Hanh", "Zen teacher and mindfulness writer",
     "Walk gently and notice each step."),
    ("Smile, breathe and go slowly.", "Thich Nhat Hanh", "Zen teacher and mindfulness writer",
     "Slowing down helps you enjoy things more."),
    ("The present moment is filled with joy and happiness. If you are attentive, you will see it.", "Thich Nhat Hanh",
     "Zen teacher and mindfulness writer", "Look around — there's something good happening right now."),
    ("Nothing can bring you peace but yourself.", "Ralph Waldo Emerson", "American writer and thinker",
     "Calm comes from inside you."),
    ("Adopt the pace of nature: her secret is patience.", "Ralph Waldo Emerson", "American writer and thinker",
     "Trees grow slowly — be patient with yourself too."),
    ("Look deep into nature, and then you will understand everything better.", "Albert Einstein", "scientist",
     "Time in nature helps your mind."),
    ("Calmness is the cradle of power.", "Josiah Gilbert Holland", "American writer", "A calm mind is a strong mind."),
    ("You can't stop the waves, but you can learn to surf.", "Jon Kabat-Zinn", "mindfulness teacher",
     "You can't stop every problem, but you can learn to handle it."),
    ("Wherever you go, there you are.", "Jon Kabat-Zinn", "mindfulness teacher", "Be here, in this moment."),
    ("Almost everything will work again if you unplug it for a few minutes, including you.", "Anne Lamott", "writer",
     "Short breaks — even from screens — help you recharge."),
    ("Lack of activity destroys the good condition of every human being, while movement and methodical physical "
     "exercise save it and preserve it.", "Plato", "Greek philosopher", "Moving your body every day keeps it strong."),
    ("Take care of your body. It's the only place you have to live.", "Jim Rohn", "writer and speaker",
     "Look after your body: eat well, move and sleep."),
    ("An early-morning walk is a blessing for the whole day.", "Henry David Thoreau", "writer who loved nature",
     "A morning walk makes the whole day better."),
    ("Practice and all is coming.", "Sri K. Pattabhi Jois", "yoga teacher from India", "Keep practising — good things come."),
    ("Health is a state of complete harmony of the body, mind and spirit.", "B. K. S. Iyengar",
     "famous yoga teacher from India", "Being healthy means your body AND your mind feel good."),
    ("In the midst of movement and chaos, keep stillness inside of you.", "Deepak Chopra", "writer on health and meditation",
     "Even on busy days, find a calm spot inside."),
    ("Exercise is king. Nutrition is queen. Put them together and you've got a kingdom.", "Jack LaLanne",
     "fitness pioneer", "Moving + healthy food = super you!"),
    ("He who has health has hope; and he who has hope has everything.", "Arabian proverb", "a wise old saying",
     "Good health gives you hope for everything else."),
    ("A good laugh and a long sleep are the best cures in the doctor's book.", "Irish proverb", "a wise old saying",
     "Laughing and sleeping well are great medicine."),
    ("Sleep is the golden chain that ties health and our bodies together.", "Thomas Dekker", "English writer",
     "Sleep keeps you healthy and strong."),
    ("No medicine is needed for the body if you eat only after your last meal has been digested.", "Thiruvalluvar",
     "Tamil poet, Thirukkural 942", "Don't overeat — give your tummy a rest between meals."),
    ("Kaalai ezhunthavudan padippu… maalai muzhuthum vilaiyaattu — study after you wake up, and play all evening!",
     "Subramania Bharati", "great Tamil poet", "Balance learning and play every day."),
    ("Happiness depends upon ourselves.", "Aristotle", "Greek philosopher", "You can choose things that make you happy."),
    ("Yoga is the journey of the self, through the self, to the self.", "The Bhagavad Gita", "ancient Indian wisdom",
     "Yoga helps you understand yourself."),
    ("Take rest; a field that has rested gives a bountiful crop.", "Ovid", "Roman poet",
     "Resting helps you grow and do your best."),
    ("When you arise in the morning, think of what a precious privilege it is to be alive — to breathe, to think, "
     "to enjoy, to love.", "Marcus Aurelius", "Roman emperor and philosopher", "Start each day feeling thankful."),
    ("Very little is needed to make a happy life.", "Marcus Aurelius", "Roman emperor and philosopher",
     "Happiness often comes from simple things."),
]

# Health tips (a new one every hour)
HEALTH_TIPS = [
    "💧 Drink water through the day — keep a bottle nearby!",
    "🌈 Eat a rainbow: different coloured fruits and veggies give you different vitamins.",
    "🏃‍♀️ Kids need about 60 minutes of active play every day.",
    "😴 Children your age need about 9–12 hours of sleep each night.",
    "🪥 Brush your teeth twice a day, for 2 minutes each time.",
    "🧼 Wash your hands with soap for 20 seconds — that's 'Happy Birthday' sung twice!",
    "👀 The 20-20-20 rule: every 20 minutes of screen time, look at something 6 metres away for 20 seconds.",
    "🧢 Going outside? Slip, slop, slap, seek, slide: shirt, sunscreen, hat, shade and sunnies!",
    "🌳 Playing outside in daylight is good for your eyes.",
    "🍳 Eat breakfast — it gives your brain energy for learning.",
    "🥛 Choose water or milk instead of sugary drinks.",
    "🧘 Feeling upset? Take 5 slow belly breaths: in through your nose, out through your mouth.",
    "🪑 Sit up tall when you read or write — your back will thank you.",
    "🍎 Pick fruit or yoghurt for snacks instead of lollies.",
    "🤧 Sneeze or cough into your elbow to keep germs away.",
    "📵 Put screens away an hour before bed to sleep better.",
    "🤸 Stretch for a couple of minutes when you wake up.",
    "🥕 Crunchy veggies like carrots and cucumber make great snacks.",
    "🚶 Sitting for a long time? Take a short walk or dance break!",
    "😊 Laughing and playing with friends is good for your heart and mind.",
    "💅 Keep your nails short and clean to stop germs.",
    "🎒 Carry your school bag on both shoulders.",
    "🌙 Go to bed at the same time every night — your body loves a routine.",
    "🍽️ Eat slowly and stop when your tummy feels comfortably full.",
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


# ================================ CALM CORNER & ANGELS (Andal only) ================================
SHOW_MINDFUL = True                  # the 🧘 Calm corner page
ANGELS_ON = True                     # angels fly in with kind words
ANGEL_EVERY_SECONDS = (240, 360)     # an angel visits every 4–6 minutes
ANGEL_FIRST_SECONDS = 45             # first angel about 45 seconds after opening

# {name} becomes the student's name
ANGEL_WORDS = [
    "{name}, you are so brilliant! Your clever brain can solve anything you set your mind to. ✨",
    "{name}, you are so kind. The way you care for others makes the whole world brighter. 💖",
    "{name}, you can do so much more than you think you can. Never put a fence around your dreams! 🌈",
    "Don't limit yourself, {name}. You are capable of amazing, big, wonderful things! 🚀",
    "{name}, you are too good! The angels are so proud of you. 👼",
    "{name}, you are so strong — strong in your body, strong in your mind, and strong in your heart. 💪",
    "{name}, you are so disciplined. Doing your tasks every day is a real superpower! 🌟",
    "{name}, you listen so well and you follow the rules so nicely. That makes your family so proud. 🤍",
    "When something feels hard, {name}, remember: hard means you are growing! 🌱",
    "{name}, you are braver than you believe and smarter than you think. 🦁",
    "{name}, your heart is full of light. Keep shining! ☀️",
    "{name}, every time you try, you get stronger. Trying is the bravest thing of all! ⭐",
    "{name}, you have a beautiful mind and a beautiful heart. 💫",
    "{name}, you are a superstar learner! Every page, every sum, every word makes you shine brighter. 📚",
    "The sky is not your limit, {name} — it's only the beginning! 🌌",
    "{name}, you are a wonderful daughter, a caring friend and a fantastic student. 💝",
    "{name}, you finish what you start. That is what champions do! 🏆",
    "{name}, mistakes are just stepping stones. You are learning and growing every single day. 🪜",
    "{name}, you are calm, you are focused, and you can do this! 🧘",
    "Believe in yourself, {name}. The angels already believe in you, one hundred percent! 💯",
    "{name}, your kindness is a gift to everyone you meet. 🎁",
    "{name}, you are so obedient and respectful — such a lovely way to be. 🌸",
    "{name}, you have the power to learn anything. Your brain grows every time you practise! 🧠",
    "{name}, you are a bright, bright star — and stars never stop shining. 🌠",
    "{name}, you are stronger than any challenge. You've got this! ⚡",
    "{name}, you make good choices, even when they're not the easy ones. That's real strength. 🌿",
    "{name}, you are more capable than you know. Aim high — higher than the clouds! ☁️",
    "{name}, being disciplined today makes your dreams come true tomorrow. 🗝️",
    "{name}, your smile can light up a whole room. 😊",
    "{name}, you are gentle, wise and wonderful. 🦋",
    "{name}, you never give up. That's what makes you so special. 🌈",
    "{name}, don't ever think 'I can't'. Think 'I can't YET' — and then you will! 🌟",
    "{name}, you are doing such a great job. Keep going, little champion! 🥇",
    "{name}, you have a heart of gold and a mind like a shining star. 💛",
    "{name}, your effort today is planting seeds for a beautiful tomorrow. 🌻",
    "{name}, you are loved, you are clever, and you are enough — just as you are. 💗",
    "{name}, you can climb any mountain, one little step at a time. ⛰️",
    "{name}, you have so much more inside you than you can imagine. Let it shine! ✨",
    "{name}, you are strong like Hanuman — brave, devoted and full of power! 🙏",
    "{name}, being kind is your superpower — and you use it every day. 🦸‍♀️",
]

# A calm idea for each day (rotates)
CALM_TIPS = [
    ("🎈 Balloon breathing", "Put your hands on your tummy. Breathe in and fill your tummy like a balloon. "
     "Breathe out slowly and let the balloon go down. Do it 5 times."),
    ("🌸 Smell the flower, blow the candle", "Breathe in through your nose like you're smelling a flower. "
     "Breathe out through your mouth like you're gently blowing out a birthday candle."),
    ("⭐ Star hand breathing", "Spread your fingers like a star. Trace up each finger while you breathe in, "
     "and down each finger while you breathe out."),
    ("🐢 Turtle time", "Pretend you're a turtle going into its shell. Curl up, close your eyes and count 10 slow breaths. "
     "Then come out slowly, feeling calm."),
    ("👂 Listening game", "Close your eyes for one minute. How many different sounds can you hear? Count them on your fingers."),
    ("🌈 Rainbow walk", "Look around the room and find something red, orange, yellow, green, blue and purple."),
    ("🧊 Melting snowman", "Stand tall and stiff like a snowman. Then slowly melt down to the floor, relaxing every part of you."),
    ("🌳 Strong tree", "Stand with your feet planted like roots. Reach your arms up like branches. "
     "Sway gently in the wind and breathe slowly."),
    ("🍫 Mindful snack", "Eat one small piece of fruit really slowly. Notice the colour, the smell, the taste and the crunch."),
    ("🦋 Butterfly hug", "Cross your arms over your chest and tap your shoulders slowly, left then right, like butterfly wings."),
    ("☁️ Cloud thoughts", "Imagine your thoughts are clouds floating across the sky. Watch them drift past — you don't have to chase them."),
    ("🐝 Bee breathing", "Breathe in, then hum like a bee as you breathe out: hmmmmm. Feel the buzz! Do it 5 times."),
    ("💗 Heart listening", "Put your hand on your heart. Can you feel it beating? Breathe slowly and feel it get calmer."),
    ("🧸 Teddy breathing", "Lie down with a teddy on your tummy. Breathe slowly and watch teddy ride up and down."),
]

GRATITUDE_PROMPTS = [
    "a person who made me smile today", "something yummy I ate", "something in nature I love",
    "something my body can do", "a friend I'm glad to have", "something that made me laugh",
    "something cosy in my home", "something I learned today", "someone who helped me",
    "a toy or book I love", "something beautiful I saw", "a happy memory",
]

KIND_IDEAS = [
    "Give someone in your family a big hug. 🤗", "Say thank you to your teacher today. 🍎",
    "Help set the table for dinner. 🍽️", "Draw a picture for someone you love. 🎨",
    "Tell a friend one thing you like about them. 💬", "Share a toy or a snack with someone. 🍪",
    "Help tidy up without being asked. 🧹", "Make someone laugh today. 😂",
    "Water a plant or help in the garden. 🌱", "Say something kind to yourself in the mirror. 🪞",
    "Ask a grown-up 'How was your day?' 💗", "Help someone who looks a bit sad. 🫶",
    "Write a little thank-you note. 💌", "Be patient and wait your turn nicely. ⏳",
]

I_AM = [
    "I am brave 🦁", "I am kind 💖", "I am clever 🧠", "I am strong 💪", "I am loved 💗", "I am calm 🧘",
    "I am a good friend 🤝", "I can do hard things ⛰️", "I am disciplined 🗓️", "I am honest 🌟",
    "I am a great learner 📚", "I am creative 🎨", "I am patient 🐢", "I am helpful 🙌", "I believe in myself ✨",
    "I am grateful 🙏", "I am focused 🎯", "I am gentle 🦋", "I make good choices 🌿", "I never give up 🌈",
]

# What to try for each feeling (uses the ids in MOODS)
FEELING_HELP = {
    "happy": ["Share your happy feeling — tell someone what made you smile!", "Do a happy dance for 30 seconds 💃",
              "Put a note in your gratitude jar 🫙"],
    "excited": ["Take 3 big breaths so your excitement doesn't bounce away 🎈", "Draw what you're excited about 🎨",
                "Tell a grown-up all about it!"],
    "calm": ["Enjoy it! Notice how your body feels when it's calm 🌿", "Read a book quietly 📚",
             "Try the breathing bubble below to stay calm"],
    "tired": ["Drink a glass of water 💧", "Stretch up high like a tall tree 🌳",
              "If it's late, it might be time for bed 🌙"],
    "worried": ["Tell a grown-up what's worrying you — sharing makes it smaller 💗",
                "Try 5 slow balloon breaths 🎈", "Do the 5-4-3-2-1 senses game below 👀"],
    "sad": ["Ask for a hug 🤗", "It's okay to cry — tears help feelings come out 💧",
            "Hug a teddy and do butterfly taps 🦋"],
    "cross": ["Stop, and take 3 bee breaths — hmmmm 🐝", "Squeeze your hands tight, then let go. Do it 3 times ✊",
              "Walk away and come back when you feel calmer 🚶‍♀️"],
}

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
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;500;600;700&family=Nunito:wght@500;700;800&display=swap');
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
.quote { position: relative; background: linear-gradient(135deg,#fffdf3,#f4efff); border: 2px solid #e6d6ff;
  border-radius: 22px; padding: 16px 20px 14px 54px; margin: 6px 0 14px; color: #3b2350; }
.quote .qmark { position: absolute; left: 14px; top: -6px; font-size: 4.2rem; line-height: 1; color: #c9a8ff;
  font-family: Georgia, serif; }
.quote .qtext { font-size: 1.22rem; font-weight: 600; line-height: 1.4; }
.quote .qwho { margin-top: 6px; color: #6b3f73; font-weight: 600; }
.quote .qwho span { font-weight: 400; color: #8a6a96; }
.quote .qmean { margin-top: 6px; color: #5a4300; background: #fff6cc; border-radius: 12px; padding: 4px 10px;
  display: inline-block; font-size: .95rem; }
.critter { position: fixed; left: 0; z-index: 4; pointer-events: none; font-size: 36px; will-change: transform; }
.critter span { display: inline-block; }
.critter.bunny { bottom: 10px; animation: run-across 38s linear 5s infinite; transform: translateX(110vw); }
.critter.bunny span { animation: hop-small .45s ease-in-out infinite; }
.critter.unicorn { bottom: 64px; font-size: 40px; animation: run-across 55s linear 26s infinite; transform: translateX(110vw); }
.critter.unicorn span { animation: hop-big .8s ease-in-out infinite; }
@keyframes run-across { 0% { transform: translateX(110vw); } 16% { transform: translateX(-80px); } 100% { transform: translateX(-80px); } }
@keyframes hop-small { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-12px); } }
@keyframes hop-big { 0%,100% { transform: translateY(0) rotate(0); } 50% { transform: translateY(-26px) rotate(-8deg); } }
/* ===================== polish (Oct 2026) ===================== */
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp span, .stApp div, .stApp button, .stApp input, .stApp textarea,
.stApp [data-testid="stMarkdownContainer"] { font-family: 'Fredoka', 'Nunito', system-ui, -apple-system, sans-serif !important; }
.stApp { -webkit-font-smoothing: antialiased; color: #2f1d40; }
.stApp p, .stApp li { font-size: 1.06rem; line-height: 1.5; }
.stApp [data-testid="stIconMaterial"], .stApp .material-symbols-rounded { font-family: 'Material Symbols Rounded' !important; }
.stAppDeployButton, [data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; }
.block-container { max-width: 860px; padding-top: 1.2rem !important; }
.hero { border-width: 0 !important; background: rgba(255,255,255,.92) !important;
  box-shadow: 0 2px 0 rgba(255,255,255,.9) inset, 0 14px 40px rgba(120,60,160,.16) !important; }
.hero .title { font-size: 2.9rem; letter-spacing: .01em; }
.balance { font-size: 1.45rem; padding: 10px 24px; box-shadow: 0 8px 22px rgba(155,107,255,.42); }
[data-testid="stVerticalBlockBorderWrapper"] { background: rgba(255,255,255,.93) !important;
  box-shadow: 0 10px 30px rgba(120,60,160,.10); border-width: 2px !important; }
.card, .quote, .fact, .msg { box-shadow: 0 8px 24px rgba(120,60,160,.09); }
h3, h4 { font-weight: 700 !important; letter-spacing: .01em; }
.stButton > button, .stFormSubmitButton > button { border-radius: 16px !important; font-weight: 600 !important;
  min-height: 46px; font-size: 1.02rem !important; border-width: 2px !important; transition: transform .12s, box-shadow .12s; }
.stButton > button:hover, .stFormSubmitButton > button:hover { transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(155,107,255,.25); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: linear-gradient(90deg,#ff5fa2,#9b6bff) !important; border: 0 !important; color: #fff !important; }
.stTextInput input, .stNumberInput input, .stTextArea textarea { border-radius: 14px !important; font-size: 1.05rem !important; }
[data-testid="stExpander"] details { border-radius: 18px !important; background: rgba(255,255,255,.9); }
[data-testid="stExpander"] summary p { font-weight: 600; font-size: 1.05rem; }

/* ---- big category buttons ---- */
.st-key-navbar { position: sticky; top: 0; z-index: 50; padding: 8px 6px; margin: 4px 0 6px; border-radius: 24px;
  background: rgba(255,255,255,.88); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 8px 26px rgba(120,60,160,.14); }
.st-key-navbar [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: 6px !important; }
.st-key-navbar [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }
.st-key-navbar button { min-height: 62px !important; border-radius: 20px !important; padding: 4px 6px !important;
  background: #f7f1ff !important; border: 2px solid transparent !important; color: #4a2a63 !important; }
.st-key-navbar button p { font-size: 1.08rem !important; font-weight: 700 !important; line-height: 1.15; white-space: normal; }
.st-key-navbar button[kind="primary"] { background: linear-gradient(135deg,#ff5fa2,#9b6bff) !important; color: #fff !important;
  box-shadow: 0 8px 18px rgba(155,107,255,.40); }
.st-key-navbar button[kind="primary"] p { color: #fff !important; }
.st-key-navhidden { display: none !important; }
.st-key-call_angel button { background: linear-gradient(90deg,#ffe9a8,#ffd1e8) !important; border: 2px solid #ffd36b !important;
  color: #5a3d00 !important; }
.st-key-call_angel button p { font-size: 1.12rem !important; font-weight: 700 !important; }
@media (max-width: 560px) { .st-key-navbar button p { font-size: .86rem !important; }
  .st-key-navbar button { min-height: 58px !important; padding: 2px !important; } .hero .title { font-size: 2.2rem; } }

/* ---- sub-tabs as pills that wrap (no sideways scrolling) ---- */
[role="tablist"] { flex-wrap: wrap !important; gap: 8px !important; padding: 4px 0 8px; border: 0 !important;
  overflow: visible !important; }
[role="tablist"]::after, .react-aria-SelectionIndicator { display: none !important; }
[data-testid="stTab"], [role="tab"] { background: rgba(255,255,255,.92) !important; border-radius: 999px !important;
  padding: 8px 18px !important; border: 2px solid #eadcf7 !important; height: auto !important; margin: 0 !important;
  box-shadow: 0 3px 10px rgba(120,60,160,.06); }
[data-testid="stTab"] p, [role="tab"] p { font-size: 1.06rem !important; font-weight: 600 !important; color: #5a2d66 !important; }
[data-testid="stTab"][aria-selected="true"], [role="tab"][aria-selected="true"] { background: linear-gradient(135deg,#fff0f8,#f3ecff) !important;
  border-color: #ff7fbf !important; box-shadow: 0 6px 16px rgba(255,95,162,.25); }
[data-testid="stTab"][aria-selected="true"] p, [role="tab"][aria-selected="true"] p { color: #d6337f !important; }
/* bordered boxes (each st.container(border=True) gets a "card" key automatically) */
[class*="st-key-card"] { background: rgba(255,255,255,.94) !important; border-radius: 24px !important;
  border: 2px solid #f1dcf0 !important; box-shadow: 0 10px 30px rgba(120,60,160,.10); padding: 16px 18px !important; }

/* ---- calm corner ---- */
.calm-hero { text-align: center; padding: 20px 14px 16px; border-radius: 26px; margin: 4px 0 12px;
  background: linear-gradient(135deg,#e9fbf3 0%,#eef4ff 50%,#fdf0ff 100%); box-shadow: 0 10px 30px rgba(90,160,150,.15); }
.ch-title { font-size: 1.9rem; font-weight: 700; color: #2f6f68; }
.ch-sub { color: #5d7a86; font-size: 1.05rem; margin-top: 2px; }
.angel-card { position: relative; text-align: center; padding: 18px 18px 16px; margin: 0 0 8px; border-radius: 26px;
  background: linear-gradient(160deg,#fffdf3 0%,#fff1f8 55%,#f3ecff 100%); border: 3px solid #ffd36b;
  box-shadow: 0 0 26px rgba(255,207,90,.55); }
.ac-wing { font-size: 2.6rem; line-height: 1; filter: drop-shadow(0 0 10px rgba(255,214,90,.9)); }
.ac-head { font-size: .82rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #b58a00; margin: 6px 0 4px; }
.ac-text { font-size: 1.3rem; font-weight: 600; color: #3b2350; line-height: 1.4; }
.calm-h { font-size: 1.3rem; font-weight: 700; color: #4a2a63; }
.calm-s { color: #7a6386; margin: 2px 0 8px; }
.feel-card { display: flex; gap: 14px; align-items: flex-start; background: #f2fbf7; border: 2px solid #bfe9d6;
  border-radius: 20px; padding: 12px 16px; margin-top: 8px; color: #24514a; }
.feel-card .fc-big { font-size: 3rem; line-height: 1; }
.feel-card ul { margin: 6px 0 0 0; padding-left: 18px; }
.gjar { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 8px; }
.gnote { width: 150px; min-height: 70px; padding: 10px 12px; border-radius: 6px 6px 18px 6px; font-weight: 500; color: #3b2350;
  box-shadow: 0 6px 14px rgba(0,0,0,.08); font-size: .98rem; line-height: 1.3; }
.gnote span { display: block; margin-top: 6px; font-size: .75rem; color: #8a6a96; }
.iam-row { display: flex; flex-wrap: wrap; gap: 10px; margin: 4px 0 8px; }
.iam { flex: 1 1 150px; text-align: center; font-size: 1.3rem; font-weight: 700; color: #fff; padding: 16px 10px;
  border-radius: 20px; background: linear-gradient(135deg,#ff7fbf,#9b6bff); box-shadow: 0 8px 18px rgba(155,107,255,.3); }
.iam:nth-child(2) { background: linear-gradient(135deg,#4cc3ff,#7a7bff); }
.iam:nth-child(3) { background: linear-gradient(135deg,#ffb347,#ff6f91); }
.calm-grid { display: flex; flex-wrap: wrap; gap: 12px; margin: 6px 0 10px; }
.cg { flex: 1 1 260px; border-radius: 22px; padding: 14px 16px; box-shadow: 0 8px 22px rgba(120,60,160,.08); }
.cg1 { background: #ecfbf1; border: 2px solid #bfe9cc; color: #24514a; }
.cg2 { background: #fff8e1; border: 2px solid #ffe28a; color: #5a4300; }
.cg-h { font-weight: 700; font-size: 1.12rem; margin-bottom: 4px; }
.cg-t { font-size: 1.04rem; line-height: 1.45; }
.char-prev { display: flex; align-items: center; justify-content: center; min-height: 140px; border-radius: 20px; margin: 4px 0 10px;
  background-color: #fff; background-image: radial-gradient(#ece3f6 1.2px, transparent 1.2px); background-size: 18px 18px;
  box-shadow: inset 0 0 0 2px #f1e4f7; }
.char-prev img { max-width: 220px; max-height: 200px; filter: drop-shadow(0 6px 10px rgba(0,0,0,.15)); }
.char-prev.small { min-height: 110px; } .char-prev.small img { max-width: 120px; max-height: 120px; }
.char-say { background: #fff3fa; border-radius: 14px; padding: 4px 10px; margin: 4px 0; color: #5a2d66; font-size: .98rem; }
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

SNOW_SVG = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='90' height='90'%3E"
            "%3Cg stroke='%23ffffff' stroke-width='2.2' stroke-linecap='round' opacity='.85' transform='translate(45 45)'%3E"
            "%3Cpath d='M0-16V16M-14-8L14 8M-14 8L14-8M0-16l-4-4M0-16l4-4M0 16l-4 4M0 16l4 4'/%3E%3C/g%3E%3C/svg%3E")
THEME_CSS.update({
    "icepalace": f""".stApp {{ background-color: #dff3ff; background-image: url("{SNOW_SVG}"),
        radial-gradient(circle at 15% 10%, rgba(255,255,255,.9) 0, transparent 35%),
        radial-gradient(circle at 85% 30%, rgba(196,170,255,.45) 0, transparent 40%),
        linear-gradient(180deg, #e9f7ff 0%, #bfe6ff 55%, #a9d4f5 100%);
        background-size: 90px 90px, 100% 100%, 100% 100%, 100% 100%; }}
        .hero .title {{ background: linear-gradient(90deg,#3a8dde,#7fd3ff,#b18cff,#3a8dde); -webkit-background-clip: text;
        background-clip: text; color: transparent; }}
        .balance {{ background: linear-gradient(90deg,#4aa8ff,#9b7bff); }}
        .hero, [data-testid="stVerticalBlockBorderWrapper"], .card {{ border-color: #b9e2ff !important; }}
        h3 {{ color: #24518a !important; }}""",
    "springprincess": """.stApp { background:
        radial-gradient(circle at 10% 12%, rgba(255,160,205,.55) 0, transparent 32%),
        radial-gradient(circle at 90% 20%, rgba(120,215,200,.5) 0, transparent 34%),
        radial-gradient(circle at 20% 90%, rgba(170,225,150,.5) 0, transparent 34%),
        radial-gradient(circle at 85% 88%, rgba(255,205,140,.5) 0, transparent 30%),
        linear-gradient(180deg, #fff2f8 0%, #f2fff8 100%); }
        .hero .title { background: linear-gradient(90deg,#d6337f,#ff7fb6,#2fb5a0,#d6337f); -webkit-background-clip: text;
        background-clip: text; color: transparent; }
        .balance { background: linear-gradient(90deg,#e0458f,#2fb5a0); }
        .hero, [data-testid="stVerticalBlockBorderWrapper"], .card { border-color: #ffc4de !important; }
        h3 { color: #8a1f55 !important; }""",
    "snowyfun": f""".stApp {{ background-color: #f4fbff; background-image: url("{SNOW_SVG}"),
        radial-gradient(ellipse at 50% 110%, #ffffff 0, #ffffff 30%, transparent 31%),
        linear-gradient(180deg, #cfeeff 0%, #e8f7ff 60%, #ffffff 100%);
        background-size: 70px 70px, 100% 100%, 100% 100%; }}
        .hero .title {{ background: linear-gradient(90deg,#ff8a1f,#ffb347,#38a8f5,#ff8a1f); -webkit-background-clip: text;
        background-clip: text; color: transparent; }}
        .balance {{ background: linear-gradient(90deg,#ff8a1f,#38a8f5); }}
        .hero, [data-testid="stVerticalBlockBorderWrapper"], .card {{ border-color: #c6e8ff !important; }}
        h3 {{ color: #1f5c8a !important; }}""",
    "planetpals": """.stApp { background:
        radial-gradient(2px 2px at 20px 30px, #ffffff, transparent),
        radial-gradient(2px 2px at 110px 140px, #fff7c2, transparent),
        radial-gradient(1.5px 1.5px at 170px 60px, #ffffff, transparent),
        radial-gradient(circle at 4% 6%, #fff3a0 0, #ffc21a 7%, #ff9a1f 10%, rgba(255,154,31,.35) 13%, transparent 20%),
        radial-gradient(circle at 95% 12%, #9fe0ff 0, #3a9be8 3.2%, #2a7a3a 4.4%, #2f8fe0 4.8%, transparent 5%),
        radial-gradient(circle at 96% 46%, #ffc4a3 0, #e2603a 3.2%, transparent 3.4%),
        radial-gradient(ellipse 9% 1.6% at 5% 62%, transparent 55%, rgba(255,226,160,.95) 62%, transparent 72%),
        radial-gradient(circle at 5% 62%, #ffe9b8 0, #e0aa5c 4%, transparent 4.2%),
        repeating-linear-gradient(0deg, transparent 0 6px, rgba(160,90,40,.35) 6px 10px),
        linear-gradient(180deg, #3b3f9e 0%, #5a56c4 45%, #7c6fd6 100%);
        background-size: 200px 200px, 200px 200px, 200px 200px, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 0 0, 100% 100%;
        background-attachment: fixed; }
        .stApp::after { content: ""; position: fixed; right: 3%; bottom: 4%; width: 110px; height: 110px; border-radius: 50%;
        background: repeating-linear-gradient(170deg, #f4c58a 0 10px, #d98a4a 10px 18px, #fbe3c0 18px 24px);
        box-shadow: inset -14px -10px 0 rgba(0,0,0,.12); pointer-events: none; z-index: 0; opacity: .95; }
        .hero .title { background: linear-gradient(90deg,#ffb020,#e2603a,#2f8fe0,#7a5cff,#ffb020); -webkit-background-clip: text;
        background-clip: text; color: transparent; }
        .balance { background: linear-gradient(90deg,#ff9a1f,#3a6cf0); }
        .hero, .card { border-color: #c9d4ff !important; }
        [data-testid="stVerticalBlockBorderWrapper"] { background: rgba(255,255,255,.93); border-color: #c9d4ff !important; }
        h3 { color: #22307a !important; }
        .block-container { position: relative; z-index: 1; background: rgba(255,255,255,.80); border-radius: 28px;
        padding: 1.5rem 1.4rem 2rem !important; margin-top: 1.2rem; }
        [data-testid="stHeader"] { background: transparent; }""",
    "sunnysolar": """.stApp { background:
        radial-gradient(circle at 50% -10%, #fff6b0 0, #ffd23f 12%, rgba(255,160,40,.55) 22%, transparent 45%),
        radial-gradient(circle at 50% -10%, transparent 0 52%, rgba(255,150,60,.35) 52.4%, transparent 53%),
        radial-gradient(circle at 50% -10%, transparent 0 68%, rgba(255,120,80,.3) 68.4%, transparent 69%),
        radial-gradient(circle at 50% -10%, transparent 0 84%, rgba(230,90,120,.25) 84.4%, transparent 85%),
        linear-gradient(180deg, #fff4d6 0%, #ffe3c4 50%, #ffd6d6 100%);
        background-attachment: fixed; }
        .hero .title { background: linear-gradient(90deg,#ff7a00,#ffc400,#ff4f6d,#ff7a00); -webkit-background-clip: text;
        background-clip: text; color: transparent; }
        .balance { background: linear-gradient(90deg,#ff8a00,#ff4f6d); }
        .hero, [data-testid="stVerticalBlockBorderWrapper"], .card { border-color: #ffd59a !important; }
        h3 { color: #8a3a00 !important; }""",
})
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
            "messages": [], "facts": {}, "chalisa": {}, "bead_rewards_given": 0, "chalisa_reward": None,
            "kid_messages": [], "task_feedback": []}


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


class DaySet(set):
    """A set of task ids that also remembers which day it belongs to (weekends have extra must-dos)."""
    key = None


def day_set(items, key):
    s = DaySet(items)
    s.key = key
    return s


def counted_set(data, key: str) -> set:
    """Tasks that COUNT for rewards: ticked AND approved (grown-up or auto-checked). Older days count as ticked."""
    ticked = set(data["days"].get(key, []))
    start = data.get("approval_start")
    if not start or key < start:
        return day_set(ticked, key)
    ok = set(data.get("approved", {}).get(key, []))
    return day_set((ticked & ok) | ({"star"} & ticked), key)


def counted_days(data) -> dict:
    return {k: counted_set(data, k) for k in data["days"]}


def done_on(data, d: date) -> set:
    return counted_set(data, d.isoformat())


def ticked_on(data, d: date) -> set:
    return set(data["days"].get(d.isoformat(), []))


def pending_on(data, d: date) -> set:
    return (ticked_on(data, d) - done_on(data, d)) & set(TASK_BY_ID)


def task_minutes(done: set, key=None) -> int:
    if "star" in done:          # a day a grown-up marked as a star day
        return DAILY_GOAL_MINUTES
    key = key or getattr(done, "key", None)
    if not required_ids(key) <= set(done):
        return 0
    return min(sum(TASK_BY_ID[t]["minutes"] for t in done if t in TASK_BY_ID), DAILY_GOAL_MINUTES)


def is_star_day(done: set, key=None) -> bool:
    if "star" in done:
        return True
    return task_minutes(done, key) >= DAILY_GOAL_MINUTES


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
        "star_days": sum(is_star_day(v) for v in days.values()),
        "speak_days": count("speak"), "read_days": count("read"), "sing_days": count("sing"), "music_days": count("music"),
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


def weekend_start(d: date):
    """The Saturday of this weekend (or None on a weekday)."""
    if d.weekday() == 5:
        return d
    if d.weekday() == 6:
        return d - timedelta(days=1)
    return None


def weekend_chalisa(d, today: date):
    """This weekend's Chalisa goal: learn the next 2 parts (or revise 2 once all are learned)."""
    sat = weekend_start(today)
    if sat is None:
        return None
    days_ = {sat.isoformat(), (sat + timedelta(days=1)).isoformat()}
    ch = d.get("chalisa", {})
    before = {int(k) for k, v in ch.items() if v < sat.isoformat()}
    remaining = [i for i in range(len(CHALISA_PARTS)) if i not in before]
    learned_now = sorted(int(k) for k, v in ch.items() if v in days_)
    revised = sorted({int(x) for x in d.get("chalisa_revise", {}).get(sat.isoformat(), [])})
    if remaining:
        targets = remaining[:WEEKEND_CHALISA_PARTS]
        done = [i for i in targets if i in learned_now]
        need = len(targets)
        mode = "learn"
    else:
        targets = []
        done = revised
        need = WEEKEND_CHALISA_PARTS
        mode = "revise"
    return {"sat": sat.isoformat(), "mode": mode, "targets": targets, "done": done, "need": need,
            "complete": len(done) >= need}


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
def local_file():
    return Path(PROGRESS_PATH.replace(".json", "_local.json"))


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def storage_cfg():
    s = secret("storage")
    if s and s.get("github_token") and s.get("repo"):
        path = PROGRESS_PATH if PROGRESS_PATH != "progress.json" else s.get("path", "progress.json")
        return {"token": s["github_token"], "repo": s["repo"], "path": path}
    return None


def parent_pin() -> str:
    return str(secret(PIN_SECRET, "1234"))


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
    if local_file().exists():
        return migrate({**default_data(), **json.loads(local_file().read_text())}, today_local()), None
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
    local_file().write_text(text)
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


VISITOR_ENGINE = r"""
(function(){
  if (window.__andalVisitors) return; window.__andalVisitors = true;
  var F = __FRIENDS__, MIN = __MIN__, MAX = __MAX__, MOVES = __MOVES__, last = -1;
  function rnd(a, b){ return a + Math.random() * (b - a); }
  function pick(list){ return list[Math.floor(Math.random() * list.length)]; }
  function edgePoint(e, W, H){
    if (e === 'L') return [-70, rnd(.15, .8) * H];
    if (e === 'R') return [W + 20, rnd(.15, .8) * H];
    if (e === 'T') return [rnd(.1, .85) * W, -70];
    return [rnd(.1, .85) * W, H + 20];
  }
  function say(el, text){
    var old = document.getElementById('andal-vbubble'); if (old) old.remove();
    var r = el.getBoundingClientRect(), b = document.createElement('div'); b.id = 'andal-vbubble';
    b.textContent = text;
    b.style.cssText = 'position:fixed;z-index:99998;max-width:250px;padding:10px 14px;border-radius:18px;pointer-events:none;'
      + 'background:#fff;border:3px solid #9b6bff;color:#3b2350;font:600 15px Fredoka,system-ui,sans-serif;'
      + 'box-shadow:0 8px 24px rgba(155,107,255,.3);transition:opacity .3s, transform .3s;opacity:0;transform:scale(.6)';
    document.body.appendChild(b);
    var left = Math.min(Math.max(8, r.left + r.width / 2 - 125), window.innerWidth - 266);
    var top = r.top > 140 ? r.top - b.offsetHeight - 10 : r.bottom + 10;
    b.style.left = left + 'px'; b.style.top = Math.max(8, top) + 'px';
    requestAnimationFrame(function(){ b.style.opacity = '1'; b.style.transform = 'scale(1)'; });
    setTimeout(function(){ b.style.opacity = '0'; setTimeout(function(){ b.remove(); }, 350); }, 4200);
  }
  function visit(){
    if (document.hidden || !F.length) { schedule(); return; }
    var i; do { i = Math.floor(Math.random() * F.length); } while (F.length > 1 && i === last); last = i;
    var f = F[i], W = window.innerWidth, H = window.innerHeight;
    var edges = ['L', 'R', 'T', 'B'], a = pick(edges), b;
    do { b = pick(edges); } while (b === a);
    var p0 = edgePoint(a, W, H), p2 = edgePoint(b, W, H), pm = [rnd(.32, .6) * W, rnd(.3, .55) * H];
    var wrap = document.createElement('div');
    wrap.style.cssText = 'position:fixed;left:0;top:0;z-index:99990;pointer-events:none;will-change:transform';
    var flip = document.createElement('span'); flip.style.cssText = 'display:inline-block;'
      + (p2[0] > p0[0] ? 'transform:scaleX(-1)' : '');
    var em = document.createElement('span');
    em.textContent = f.emoji; em.title = 'Tap me!';
    em.setAttribute('data-joke', f.id); em.setAttribute('data-sound', f.sound || 'pop');
    em.style.cssText = 'display:inline-block;font-size:46px;padding:6px;cursor:pointer;pointer-events:auto;'
      + 'user-select:none;-webkit-tap-highlight-color:transparent;filter:drop-shadow(0 4px 6px rgba(0,0,0,.18))';
    flip.appendChild(em); wrap.appendChild(flip); document.body.appendChild(wrap);
    var mv = MOVES[f.move] || MOVES.hop;
    try { em.animate(mv[0], {duration: mv[1], iterations: Infinity, easing: 'ease-in-out'}); } catch (e) {}
    var T = 15000;
    var anim = wrap.animate([
      {transform: 'translate(' + p0[0] + 'px,' + p0[1] + 'px)'},
      {transform: 'translate(' + pm[0] + 'px,' + pm[1] + 'px)', offset: .35},
      {transform: 'translate(' + pm[0] + 'px,' + pm[1] + 'px)', offset: .65},
      {transform: 'translate(' + p2[0] + 'px,' + p2[1] + 'px)'}], {duration: T, easing: 'ease-in-out'});
    setTimeout(function(){
      var h = new Date().getHours(), todo = (window.__andalTodo || []).filter(function(r){ return h >= r[1] && h < r[2]; });
      if (todo.length && Math.random() < .5) say(em, pick(todo)[0]);
      else if (f.says && f.says.length) say(em, pick(f.says));
    }, T * .37);
    anim.onfinish = function(){ wrap.remove(); schedule(); };
  }
  function schedule(){ setTimeout(visit, rnd(MIN, MAX) * 1000); }
  setTimeout(visit, 20000);   // the first visitor pops in about 20 seconds after opening
})();
"""

VISITOR_MOVES = {
    "hop": ([{"transform": "translateY(0)"}, {"transform": "translateY(-14px)"}, {"transform": "translateY(0)"}], 450),
    "gallop": ([{"transform": "translateY(0) rotate(0)"}, {"transform": "translateY(-22px) rotate(-8deg)"},
                {"transform": "translateY(0) rotate(0)"}], 800),
    "waddle": ([{"transform": "rotate(-9deg)"}, {"transform": "rotate(9deg) translateY(-3px)"},
                {"transform": "rotate(-9deg)"}], 700),
    "fly": ([{"transform": "translateY(0) rotate(-4deg)"}, {"transform": "translateY(-26px) rotate(4deg)"},
             {"transform": "translateY(0) rotate(-4deg)"}], 1400),
    "bound": ([{"transform": "translateY(0) scaleY(1)"}, {"transform": "translateY(-34px) scaleY(1.05)"},
               {"transform": "translateY(0) scaleY(.92)"}, {"transform": "translateY(0) scaleY(1)"}], 900),
    "flutter": ([{"transform": "translateY(0) scale(1)"}, {"transform": "translateY(-18px) scale(.9)"},
                 {"transform": "translateY(-6px) scale(1)"}, {"transform": "translateY(-22px) scale(.9)"},
                 {"transform": "translateY(0) scale(1)"}], 650),
    "swim": ([{"transform": "translateY(0) rotate(-5deg)"}, {"transform": "translateY(-12px) rotate(5deg)"},
              {"transform": "translateY(0) rotate(-5deg)"}], 1600),
    "twinkle": ([{"transform": "scale(1) rotate(0)"}, {"transform": "scale(1.25) rotate(20deg)"},
                 {"transform": "scale(1) rotate(0)"}], 1200),
    "stomp": ([{"transform": "translateY(0) rotate(-3deg)"}, {"transform": "translateY(-6px) rotate(3deg)"},
               {"transform": "translateY(0) rotate(-3deg)"}], 900),
}


def install_visitors():
    friends = [{"id": f["id"], "emoji": f["emoji"], "move": f["move"], "sound": f.get("sound", "pop"),
                "says": f["says"]} for f in FRIENDS]
    code = (VISITOR_ENGINE.replace("__FRIENDS__", json.dumps(friends))
            .replace("__MIN__", str(VISIT_EVERY_SECONDS[0])).replace("__MAX__", str(VISIT_EVERY_SECONDS[1]))
            .replace("__MOVES__", json.dumps(VISITOR_MOVES)))
    _embed("<script>try{var P=window.parent;if(!P.__andalVisitors){var s=P.document.createElement('script');"
           f"s.textContent={json.dumps(code)};P.document.head.appendChild(s);}}}}catch(e){{}}</script>", 1)


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


# ------------------------------- angels (Andal only) -------------------------------
ANGEL_ENGINE = r"""
(function(){
  if (window.__andalAngels) return; window.__andalAngels = true;
  var WORDS = __WORDS__, MIN = __MIN__, MAX = __MAX__, FIRST = __FIRST__, last = -1, busy = false;
  function rnd(a, b){ return a + Math.random() * (b - a); }
  function pick(l){ return l[Math.floor(Math.random() * l.length)]; }
  var css = document.createElement('style');
  css.textContent = '@keyframes angelGlow{0%,100%{box-shadow:0 0 22px rgba(255,207,90,.55),0 10px 30px rgba(155,107,255,.25)}'
    + '50%{box-shadow:0 0 42px rgba(255,207,90,.95),0 10px 30px rgba(155,107,255,.35)}}'
    + '#andal-angel-card{position:fixed;left:50%;z-index:99996;width:min(380px,88vw);padding:16px 20px 14px;border-radius:26px;'
    + 'text-align:center;cursor:pointer;background:linear-gradient(160deg,#fffdf3 0%,#fff1f8 55%,#f3ecff 100%);'
    + 'border:3px solid #ffd36b;color:#3b2350;font-family:Fredoka,Nunito,system-ui,sans-serif;animation:angelGlow 2.2s ease-in-out infinite;'
    + 'transition:opacity .45s, transform .45s;opacity:0;transform:translate(-50%,10px) scale(.8)}'
    + '#andal-angel-card .ah{font-size:13px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:#b58a00;margin-bottom:6px}'
    + '#andal-angel-card .am{font-size:21px;font-weight:600;line-height:1.35}'
    + '#andal-angel-card .ax{font-size:12px;color:#9a7aa6;margin-top:8px}';
  document.head.appendChild(css);
  function sparkle(x, y){
    var s = document.createElement('div'); s.textContent = pick(['✨','⭐','💫','🌟','💖','✨']);
    s.style.cssText = 'position:fixed;left:' + x + 'px;top:' + y + 'px;z-index:99993;pointer-events:none;font-size:'
      + Math.round(rnd(13, 24)) + 'px';
    document.body.appendChild(s);
    var a = s.animate([{opacity: 1, transform: 'translate(0,0) scale(1)'},
      {opacity: 0, transform: 'translate(' + rnd(-24, 24) + 'px,' + rnd(24, 60) + 'px) scale(.3) rotate(' + rnd(-90, 90) + 'deg)'}],
      {duration: 1500, easing: 'ease-out'});
    a.onfinish = function(){ s.remove(); };
  }
  function angel(size, delay, dx, dy, path, T){
    var wrap = document.createElement('div');
    wrap.style.cssText = 'position:fixed;left:0;top:0;z-index:99995;pointer-events:none;will-change:transform';
    var em = document.createElement('div'); em.textContent = '👼';
    em.style.cssText = 'font-size:' + size + 'px;filter:drop-shadow(0 0 14px rgba(255,214,90,.95)) drop-shadow(0 4px 6px rgba(0,0,0,.15))';
    wrap.appendChild(em); document.body.appendChild(wrap);
    try { em.animate([{transform: 'translateY(0) rotate(-6deg) scale(1)'}, {transform: 'translateY(-14px) rotate(6deg) scale(1.06)'},
      {transform: 'translateY(0) rotate(-6deg) scale(1)'}], {duration: 1300, iterations: Infinity, easing: 'ease-in-out'}); } catch (e) {}
    var kf = path.map(function(p){ var o = {transform: 'translate(' + (p[0] + dx) + 'px,' + (p[1] + dy) + 'px)'};
      if (p[2] !== undefined) o.offset = p[2]; return o; });
    var anim = wrap.animate(kf, {duration: T, delay: delay, easing: 'ease-in-out', fill: 'both'});
    var timer = setInterval(function(){ var r = wrap.getBoundingClientRect();
      if (r.left > -60 && r.left < innerWidth && r.top > -60 && r.top < innerHeight) sparkle(r.left + size * .4 + rnd(-10, 10), r.top + size * .7); }, 110);
    anim.onfinish = function(){ clearInterval(timer); wrap.remove(); };
    return anim;
  }
  function showCard(text, top, ms){
    var old = document.getElementById('andal-angel-card'); if (old) old.remove();
    var c = document.createElement('div'); c.id = 'andal-angel-card';
    c.innerHTML = '<div class="ah">✨ A message from the angels ✨</div><div class="am"></div><div class="ax">tap to close</div>';
    c.querySelector('.am').textContent = text; c.style.top = top + 'px';
    document.body.appendChild(c);
    requestAnimationFrame(function(){ c.style.opacity = '1'; c.style.transform = 'translate(-50%,0) scale(1)'; });
    function close(){ c.style.opacity = '0'; c.style.transform = 'translate(-50%,-10px) scale(.9)'; setTimeout(function(){ c.remove(); }, 500); }
    c.onclick = close; setTimeout(close, ms);
  }
  function fly(manual){
    if (busy || (!manual && document.hidden)) { if (!manual) schedule(); return; }
    busy = true;
    var W = innerWidth, H = innerHeight, left = Math.random() < .5, T = 16000;
    var i; do { i = Math.floor(Math.random() * WORDS.length); } while (WORDS.length > 1 && i === last); last = i;
    var hy = Math.max(70, H * .14), hx = W / 2 - 34;
    var path = [[left ? -100 : W + 30, rnd(.35, .6) * H], [hx, hy, .3], [hx, hy, .72], [left ? W + 40 : -120, -120]];
    var lead = angel(64, 0, 0, 0, path, T);
    if (Math.random() < .4) { angel(40, 350, -70, 34, path, T); angel(40, 650, 74, 30, path, T); }
    setTimeout(function(){ try { window.__andalPlay && window.__andalPlay('chime'); } catch (e) {} showCard(WORDS[i], hy + 86, T * .4); }, T * .3);
    lead.onfinish = function(){ busy = false; if (!manual) schedule(); };
  }
  function schedule(){ setTimeout(function(){ fly(false); }, rnd(MIN, MAX) * 1000); }
  window.__andalAngel = function(){ fly(true); };
  setTimeout(function(){ fly(false); }, FIRST * 1000);
})();
"""


def install_angels(words):
    code = (ANGEL_ENGINE.replace("__WORDS__", json.dumps(words, ensure_ascii=False))
            .replace("__MIN__", str(ANGEL_EVERY_SECONDS[0])).replace("__MAX__", str(ANGEL_EVERY_SECONDS[1]))
            .replace("__FIRST__", str(ANGEL_FIRST_SECONDS)))
    _embed("<script>try{var P=window.parent;if(!P.__andalAngels){var s=P.document.createElement('script');"
           f"s.textContent={json.dumps(code)};P.document.head.appendChild(s);}}}}catch(e){{}}</script>", 1)


def call_angel_now():
    _embed(f"<script>/*{random.random()}*/setTimeout(function(){{try{{window.parent.__andalAngel()}}catch(e){{}}}},300);"
           "</script>", 1)


# ------------------------------- breathing bubble -------------------------------
BREATH_HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
body{margin:0;font-family:Fredoka,Nunito,system-ui,-apple-system,sans-serif;text-align:center;background:transparent;color:#3b2350}
.stage{position:relative;height:250px;display:flex;align-items:center;justify-content:center}
.ring{position:absolute;width:230px;height:230px;border-radius:50%;border:3px dashed rgba(155,107,255,.35)}
.bub{width:90px;height:90px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:38px;
 background:radial-gradient(circle at 35% 30%,#fff 0,__C1__ 30%,__C2__ 100%);box-shadow:0 0 40px __C1__;
 transition:width __IN__s ease-in-out,height __IN__s ease-in-out}
.bub.big{width:220px;height:220px}
.say{font-size:24px;font-weight:600;min-height:34px;margin-top:4px}
.count{font-size:14px;color:#8a6a96;margin-top:2px}
button{margin-top:10px;font:600 18px Fredoka,Nunito,system-ui,sans-serif;padding:10px 26px;border-radius:999px;border:0;
 color:#fff;background:linear-gradient(90deg,#ff5fa2,#9b6bff);box-shadow:0 6px 16px rgba(155,107,255,.35);cursor:pointer}
</style></head><body>
<div class="stage"><div class="ring"></div><div class="bub" id="b">__EMOJI__</div></div>
<div class="say" id="s">Press start when you're ready</div><div class="count" id="c"></div>
<button id="go">▶ Start</button>
<script>
var IN=__IN__, HOLD=__HOLD__, OUT=__OUT__, N=__N__, b=document.getElementById('b'), s=document.getElementById('s'),
    c=document.getElementById('c'), go=document.getElementById('go'), running=false, timers=[];
function later(f,ms){ timers.push(setTimeout(f,ms)); }
function stop(msg){ timers.forEach(clearTimeout); timers=[]; running=false; b.classList.remove('big'); s.textContent=msg; go.textContent='▶ Again'; }
function round(i){
  if(i>=N){ stop('Well done! You are calm and strong ✨'); c.textContent=''; return; }
  c.textContent='Breath '+(i+1)+' of '+N;
  b.style.transition='width '+IN+'s ease-in-out,height '+IN+'s ease-in-out'; b.classList.add('big'); s.textContent='__SAYIN__';
  later(function(){ s.textContent='Hold… '; }, IN*1000);
  later(function(){ b.style.transition='width '+OUT+'s ease-in-out,height '+OUT+'s ease-in-out'; b.classList.remove('big');
    s.textContent='__SAYOUT__'; }, (IN+HOLD)*1000);
  later(function(){ round(i+1); }, (IN+HOLD+OUT)*1000+400);
}
go.onclick=function(){ if(running){ stop('Paused — press start again'); return; } running=true; go.textContent='⏸ Pause'; round(0); };
</script></body></html>"""

BREATH_STYLES = {
    "🎈 Balloon": dict(EMOJI="🎈", SAYIN="Breathe in… fill your balloon", SAYOUT="Breathe out… let it go slowly",
                      C1="#ff9fcf", C2="#ff5fa2", IN=4, HOLD=1, OUT=5, N=5),
    "🌸 Flower & candle": dict(EMOJI="🌸", SAYIN="Smell the flower… 🌸", SAYOUT="Blow out the candle… 🕯️",
                              C1="#ffc2dc", C2="#f78fb3", IN=4, HOLD=1, OUT=4, N=5),
    "⭐ Star": dict(EMOJI="⭐", SAYIN="Breathe in… up the star", SAYOUT="Breathe out… down the star",
                   C1="#ffe28a", C2="#f5b700", IN=3, HOLD=1, OUT=3, N=5),
    "🐝 Bee hum": dict(EMOJI="🐝", SAYIN="Breathe in through your nose…", SAYOUT="Hummmm like a bee… 🐝",
                      C1="#fff0a8", C2="#f2c200", IN=4, HOLD=1, OUT=6, N=5),
    "🌊 Ocean wave": dict(EMOJI="🌊", SAYIN="The wave comes in…", SAYOUT="The wave goes out…",
                         C1="#9fdcff", C2="#38a0e8", IN=5, HOLD=1, OUT=5, N=5),
}


def breath_html(style):
    h = BREATH_HTML
    for k, v in BREATH_STYLES[style].items():
        h = h.replace(f"__{k}__", str(v))
    return h


# ================================ LOGINS & PROFILES ================================
# Logins live in the app's Secrets:
#   [logins]
#   andal = "her password"          andal_parent = "grown-up password"
#   elyssa = "her password"         elyssa_parent = "grown-up password"
# With no [logins] section the app works like before (Andal only, no login, no chat).
import hashlib
import hmac

# Every bordered box gets a "card" style key so the stylesheet can make it look nice.
_st_container = st.container
_card_no = [0]


def _card_container(*args, **kwargs):
    if kwargs.get("border") and not kwargs.get("key"):
        _card_no[0] += 1
        kwargs["key"] = f"card{_card_no[0]}"
    return _st_container(*args, **kwargs)


st.container = _card_container


KIDS = {"andal": "Andal", "elyssa": "Elyssa"}

ELYSSA_TASKS = [
    {"id": "homework", "emoji": "📒", "name": "Finish today's homework", "minutes": 10, "required": True,
     "section": "must"},
    {"id": "exercise", "emoji": "⚽", "name": "Physical activity or sport for 30 minutes", "minutes": 10,
     "required": True, "section": "must"},
    {"id": "bed", "emoji": "🌙", "name": "Was in bed by 9:00 pm last night", "minutes": 0, "required": True,
     "section": "must"},
    {"id": "speak", "emoji": "🗣️", "name": "Speak Chinese for 10 minutes", "minutes": 5, "section": "learn"},
    {"id": "write1", "emoji": "✏️", "name": "English writing – piece 1 (on paper)", "minutes": 5, "section": "learn"},
    {"id": "write2", "emoji": "📝", "name": "English writing – piece 2 (on paper)", "minutes": 5, "section": "learn"},
    {"id": "maths", "emoji": "🔢", "name": f"Solve {MATHS_TO_SOLVE} maths problems", "minutes": 5,
     "section": "learn", "auto": True},
    {"id": "read", "emoji": "📚", "name": "Read a book for 20 minutes", "minutes": 5, "section": "learn"},
    {"id": "veggies", "emoji": "🥦", "name": "Ate fruit and veggies today", "minutes": 3, "section": "body"},
    {"id": "chore", "emoji": "🧹", "name": "Help at home or tidy my room for 15 minutes", "minutes": 5,
     "section": "habits"},
    {"id": "music", "emoji": "🎹", "name": "Practise music or my instrument for 15 minutes", "minutes": 5,
     "section": "habits"},
]
ELYSSA_SECTIONS = [("must", "🦄 Must do today"), ("learn", "🐰 Learning tasks"), ("body", "🌈 Healthy me"),
                   ("habits", "🎵 Home & music")]
ELYSSA_REWARDS = [
    {"id": "book", "emoji": "📚", "name": "A new book of your choice", "streak_task": "read", "streak_len": 7,
     "window": 7, "needs": {"homework": 5},
     "how": "Read 7 days in a row, and do your homework on at least 5 of those days."},
    {"id": "movie", "emoji": "🎬", "name": "Movie at the cinema", "streak_task": "exercise", "streak_len": 21,
     "window": 30, "needs": {"read": 15},
     "how": "Be active 21 days in a row (no breaks!), and read on at least 15 days that month."},
    {"id": "icecream", "emoji": "🍦", "name": "Choose your own ice cream", "streak_task": "bed", "streak_len": 30,
     "window": 30, "needs": {}, "how": "In bed by 9:00 pm every night for 30 nights in a row."},
    {"id": "playcentre", "emoji": "🎠", "name": "Play centre of your choice (up to $50)", "streak_task": "bed",
     "streak_len": 90, "window": 90, "needs": {},
     "how": "In bed by 9:00 pm every night for 3 months (90 nights) in a row."},
    {"id": "music_star", "emoji": "🎶", "name": "Music star: +60 screen-time minutes", "streak_task": "music",
     "streak_len": 30, "window": 30, "needs": {}, "bonus_minutes": 60,
     "how": "Practise music 15 minutes every day for 30 days in a row. The minutes go into your balance."},
]


def apply_profile(profile):
    """Switch every child-specific setting before the app draws anything."""
    global STUDENT_NAME, LANGUAGE, TASKS, TASK_BY_ID, SECTIONS, REWARDS, BEDTIME, PARENT_WORDS, PROGRESS_PATH
    global PIN_SECRET, EMAIL_SECRET, SHOW_TAMIL, SHOW_CHALISA, WEEKEND_RULES_FROM, STAR_DAY_FIXES, BADGES
    global BIG_PRIZES, PRIZE_BY_ID, FRIENDS, SHOW_MINDFUL, ANGELS_ON
    if profile != "elyssa":
        return
    STUDENT_NAME, LANGUAGE, BEDTIME, PARENT_WORDS = "Elyssa", "Chinese", "9:00 pm", "Mum or Dad"
    TASKS, SECTIONS, REWARDS = ELYSSA_TASKS, ELYSSA_SECTIONS, ELYSSA_REWARDS
    TASK_BY_ID = {t["id"]: t for t in TASKS}
    PROGRESS_PATH, PIN_SECRET, EMAIL_SECRET = "progress_elyssa.json", "ELYSSA_PARENT_PIN", "email_elyssa"
    SHOW_TAMIL = SHOW_CHALISA = False
    SHOW_MINDFUL = ANGELS_ON = False          # Calm corner and angels are just for Andal
    WEEKEND_RULES_FROM = "9999-12-31"          # Andal's weekend rules don't apply
    STAR_DAY_FIXES = []
    BADGES = [b for b in BADGES if b[4] not in ("chalisa_parts", "sit2_days", "sing_days")] + [
        ("music_maker", "🎹", "Music Maker", "Practise music on 10 days", "music_days", 10, "#e8f0ff", "#5b7cff")]
    BIG_PRIZES = [dict(p, rules=f"Only if at least {RESTAURANT_GAP_DAYS // 7} weeks have passed since our last "
                       "family dinner at a restaurant.") if p["id"] == "restaurant" else p for p in BIG_PRIZES]
    PRIZE_BY_ID = {p["id"]: p for p in BIG_PRIZES + SMALL_PRIZES}
    # the friendly visitor 'Elyssa' becomes 'Andal' when Elyssa is using the app
    swapped = []
    for f in FRIENDS:
        if f["id"] == "elyssa":
            f = dict(f, name="Andal", emoji="👧🏽",
                     says=[x.replace("Elyssa:", "Andal:").replace("Hi Andal", "Hi Elyssa") for x in f["says"]])
        swapped.append(f)
    FRIENDS = swapped


def login_table():
    t = secret("logins")
    return {str(k).lower(): str(v) for k, v in dict(t).items()} if t else {}


def _token(user, pw):
    return hmac.new(pw.encode(), f"earn-stars:{user}".encode(), hashlib.sha256).hexdigest()[:24]


def who(user):
    profile = user.replace("_parent", "")
    return {"user": user, "profile": profile, "role": "parent" if user.endswith("_parent") else "kid"}


def do_login():
    u = str(st.session_state.get("li_user", "")).strip().lower()
    pw = str(st.session_state.get("li_pw", ""))
    table = login_table()
    if u in table and hmac.compare_digest(pw, table[u]) and u.replace("_parent", "") in KIDS:
        st.session_state.auth = who(u)
        st.session_state.li_pw = ""
        if st.session_state.get("li_keep"):
            st.query_params["u"] = u
            st.query_params["k"] = _token(u, table[u])
    else:
        st.session_state.li_err = "That name or password isn't right. Try again! 🔐"


def do_logout():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.query_params.clear()


LOGINS = login_table()
CHAT_ON = bool(LOGINS)
if not LOGINS:
    AUTH = {"user": "andal", "profile": "andal", "role": "kid", "legacy": True}
else:
    AUTH = st.session_state.get("auth")
    if not AUTH:
        qu, qk = st.query_params.get("u", ""), st.query_params.get("k", "")
        if qu in LOGINS and qk and hmac.compare_digest(qk, _token(qu, LOGINS[qu])):
            AUTH = st.session_state.auth = who(qu)
    if not AUTH:
        st.markdown(BASE_CSS + "<style>" + THEME_CSS["rainbow"] + "</style>", unsafe_allow_html=True)
        st.markdown('<div class="hero"><div class="title">⭐ Earn Stars ⭐</div>'
                    '<div class="sub">Sign in to see your stars, tasks and rewards</div></div>', unsafe_allow_html=True)
        with st.container(border=True):
            with st.form("login", border=False):
                st.text_input("Your name", key="li_user", placeholder="e.g. andal or elyssa")
                st.text_input("Password", key="li_pw", type="password")
                st.checkbox("Keep me signed in on this device", key="li_keep", value=True)
                st.form_submit_button("Sign in ✨", on_click=do_login, type="primary", use_container_width=True)
            if err := st.session_state.pop("li_err", None):
                st.error(err)
            st.caption("Grown-ups: sign in with your child's name followed by _parent (for example andal_parent).")
        st.stop()
apply_profile(AUTH["profile"])
IS_PARENT = AUTH["role"] == "parent"
CHAT_FRIEND = next((n for k, n in KIDS.items() if k != AUTH["profile"]), "")


# ------------------------------------ chat ------------------------------------
CHAT_PATH = "chat.json"
CHAT_MAX = 300          # characters per message
CHAT_KEEP = 400         # messages kept in the file


def _chat_cfg():
    cfg = storage_cfg()
    return dict(cfg, path=CHAT_PATH) if cfg else None


def chat_load():
    cfg = _chat_cfg()
    if cfg:
        url, headers = _gh(cfg)
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 404:
            return [], None
        r.raise_for_status()
        body = r.json()
        return json.loads(base64.b64decode(body["content"]).decode()), body["sha"]
    f = Path("chat_local.json")
    return (json.loads(f.read_text()) if f.exists() else []), None


def chat_change(change) -> bool:
    for attempt in range(3):
        try:
            msgs, sha = chat_load()
            if change(msgs) is False:
                return False
            msgs = msgs[-CHAT_KEEP:]
            text = json.dumps(msgs, ensure_ascii=False, indent=0)
            cfg = _chat_cfg()
            if cfg:
                url, headers = _gh(cfg)
                payload = {"message": "chat", "content": base64.b64encode(text.encode()).decode()}
                if sha:
                    payload["sha"] = sha
                r = requests.put(url, headers=headers, json=payload, timeout=15)
                r.raise_for_status()
            else:
                Path("chat_local.json").write_text(text)
            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (409, 422) and attempt < 2:
                continue
            st.session_state.chat_err = "The chat couldn't be saved just now — try again."
            return False
        except Exception:
            st.session_state.chat_err = "The chat couldn't be saved just now — try again."
            return False
    return False


def chat_send():
    text = " ".join(str(st.session_state.get("chat_in", "")).split())[:CHAT_MAX]
    if not text:
        return
    msg = {"id": uuid.uuid4().hex[:10], "from": AUTH["profile"], "name": STUDENT_NAME, "text": text,
           "time": datetime.now(ZoneInfo(TIMEZONE)).isoformat(timespec="seconds")}

    def change(msgs):
        msgs.append(msg)
    if chat_change(change):
        st.session_state.chat_in = ""
        st.session_state.sound_next = "pop"


def chat_delete(mid):
    def change(msgs):
        keep = [m for m in msgs if m["id"] != mid]
        if len(keep) == len(msgs):
            return False
        msgs[:] = keep
    chat_change(change)


def chat_view():
    try:
        msgs, _ = chat_load()
    except Exception:
        st.warning("The chat couldn't be loaded just now. 🔄")
        return
    if not msgs:
        st.caption(f"No messages yet — say hi to {CHAT_FRIEND}! 👋")
    html_rows = []
    for m in msgs[-50:]:
        mine = m["from"] == AUTH["profile"]
        when = datetime.fromisoformat(m["time"]).strftime("%a %I:%M %p")
        html_rows.append(f'<div class="cb {"me" if mine else "them"}"><div class="cn">{html_safe(m["name"])} · {when}</div>'
                         f'{html_safe(m["text"])}</div>')
    st.markdown('<div class="chatbox">' + "".join(html_rows) + "</div>", unsafe_allow_html=True)


# ================================ MY CHARACTERS (draw → comes alive) ================================
import os
import tempfile
import streamlit.components.v1 as _components

DRAW_HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<style>
html,body{margin:0;padding:0;background:transparent;font-family:Fredoka,Nunito,system-ui,-apple-system,sans-serif;
 user-select:none;-webkit-user-select:none;-webkit-touch-callout:none;color:#3b2350}
.bar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:0 0 8px}
.sw{width:32px;height:32px;border-radius:50%;border:3px solid #fff;box-shadow:0 0 0 2px #e4d8ef;cursor:pointer;padding:0}
.sw.on{box-shadow:0 0 0 3px #9b6bff;transform:scale(1.12)}
.b{font:600 15px Fredoka,Nunito,system-ui,sans-serif;padding:7px 12px;border-radius:14px;border:2px solid #eadcf7;
 background:#fff;color:#4a2a63;cursor:pointer;-webkit-tap-highlight-color:transparent}
.b.on{background:#f3ecff;border-color:#9b6bff}
.dot{display:inline-block;border-radius:50%;background:#4a2a63;vertical-align:middle}
.go{background:linear-gradient(90deg,#ff5fa2,#9b6bff);color:#fff;border:0;font-size:17px;padding:10px 20px;
 box-shadow:0 6px 16px rgba(155,107,255,.35)}
#wrap{position:relative;border-radius:22px;overflow:hidden;background-color:#fff;box-shadow:inset 0 0 0 2px #eadcf7;
 background-image:radial-gradient(#ece3f6 1.2px,transparent 1.2px);background-size:22px 22px}
canvas{display:block;width:100%;touch-action:none;cursor:crosshair}
.hint{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#c2b0d3;font-size:20px;
 pointer-events:none;text-align:center;padding:20px}
.msg{font-size:15px;color:#7a6386;margin-left:6px}
</style></head><body>
<div class="bar" id="cols"></div>
<div class="bar" id="tools"></div>
<div id="wrap"><canvas id="c"></canvas><div class="hint" id="hint">✏️ Draw your character here with your Apple Pencil<br>(a big, colourful drawing works best!)</div></div>
<div class="bar" style="margin-top:10px"><button class="b go" id="use">✅ Use this drawing</button><span class="msg" id="msg"></span></div>
<script>
var COLS=['#222222','#ff4fa3','#ff8a00','#f5c400','#2fbf5a','#16b5c9','#3a7bff','#8b5cf6','#a0522d','#ffffff','#ffc8a8','#9aa0a6'];
var SIZES=[['S',3],['M',7],['L',14],['XL',26]];
var H=__HEIGHT__, cv=document.getElementById('c'), ctx=cv.getContext('2d'), wrap=document.getElementById('wrap');
var strokes=[], cur=null, colour='#222222', size=7, eraser=false, fingerOK=true, sawPen=false, dpr=window.devicePixelRatio||1;
function post(type,extra){ var m={isStreamlitMessage:true,type:type}; for(var k in extra) m[k]=extra[k]; window.parent.postMessage(m,'*'); }
function height(){ post('streamlit:setFrameHeight',{height:document.body.scrollHeight+4}); }
function setup(){ var w=wrap.clientWidth; cv.width=Math.round(w*dpr); cv.height=Math.round(H*dpr); cv.style.height=H+'px';
  ctx.setTransform(dpr,0,0,dpr,0,0); redraw(); height(); }
function drawStroke(s){
  ctx.save(); ctx.globalCompositeOperation=s.erase?'destination-out':'source-over'; ctx.strokeStyle=s.c; ctx.fillStyle=s.c;
  ctx.lineCap='round'; ctx.lineJoin='round'; var p=s.p;
  if(p.length===1){ ctx.beginPath(); ctx.arc(p[0][0],p[0][1],s.w*p[0][2]/2,0,7); ctx.fill(); ctx.restore(); return; }
  for(var i=1;i<p.length;i++){ var a=p[i-1], b=p[i]; ctx.lineWidth=s.w*(a[2]+b[2])/2; ctx.beginPath();
    var mx=(a[0]+b[0])/2, my=(a[1]+b[1])/2;
    if(i>1){ var z=p[i-2]; ctx.moveTo((z[0]+a[0])/2,(z[1]+a[1])/2); ctx.quadraticCurveTo(a[0],a[1],mx,my); }
    else { ctx.moveTo(a[0],a[1]); ctx.lineTo(mx,my); }
    ctx.stroke(); }
  ctx.restore(); }
function redraw(){ ctx.clearRect(0,0,cv.width,cv.height); strokes.forEach(drawStroke);
  document.getElementById('hint').style.display=strokes.length?'none':'flex'; }
function pt(e){ var r=cv.getBoundingClientRect(); var pr=(e.pointerType==='pen'&&e.pressure>0)?(0.35+e.pressure*1.3):1;
  return [e.clientX-r.left,e.clientY-r.top,pr]; }
cv.addEventListener('pointerdown',function(e){
  if(e.pointerType==='pen') sawPen=true;
  if(e.pointerType==='touch' && (sawPen || !fingerOK)) return;      // palm rejection
  e.preventDefault(); cv.setPointerCapture(e.pointerId);
  cur={c:colour,w:eraser?size*2.2:size,erase:eraser,p:[pt(e)],id:e.pointerId}; strokes.push(cur); redraw(); });
cv.addEventListener('pointermove',function(e){ if(!cur||e.pointerId!==cur.id) return; e.preventDefault();
  var ev=e.getCoalescedEvents?e.getCoalescedEvents():[e]; if(!ev.length) ev=[e];
  ev.forEach(function(x){ cur.p.push(pt(x)); }); redraw(); });
function end(e){ if(cur&&e.pointerId===cur.id) cur=null; }
cv.addEventListener('pointerup',end); cv.addEventListener('pointercancel',end);
document.addEventListener('touchmove',function(e){ if(e.target===cv) e.preventDefault(); },{passive:false});
var cols=document.getElementById('cols');
COLS.forEach(function(c){ var b=document.createElement('button'); b.className='sw'+(c===colour?' on':''); b.style.background=c;
  b.onclick=function(){ colour=c; eraser=false; [].forEach.call(cols.children,function(x){x.classList.remove('on');}); b.classList.add('on'); tools(); };
  cols.appendChild(b); });
var tb=document.getElementById('tools');
function tools(){ tb.innerHTML='';
  SIZES.forEach(function(s){ var b=document.createElement('button'); b.className='b'+(size===s[1]?' on':'');
    var d=Math.min(s[1],22); b.innerHTML='<span class="dot" style="width:'+d+'px;height:'+d+'px"></span> '+s[0];
    b.onclick=function(){ size=s[1]; tools(); }; tb.appendChild(b); });
  var er=document.createElement('button'); er.className='b'+(eraser?' on':''); er.textContent='🧽 Eraser';
  er.onclick=function(){ eraser=!eraser; tools(); }; tb.appendChild(er);
  var un=document.createElement('button'); un.className='b'; un.textContent='↩️ Undo';
  un.onclick=function(){ strokes.pop(); redraw(); }; tb.appendChild(un);
  var cl=document.createElement('button'); cl.className='b'; cl.textContent='🗑️ Clear';
  cl.onclick=function(){ if(!strokes.length||confirm('Clear the whole drawing?')){ strokes=[]; redraw(); } }; tb.appendChild(cl);
  var fg=document.createElement('button'); fg.className='b'+(fingerOK&&!sawPen?' on':''); fg.textContent=sawPen?'✏️ Pencil only':(fingerOK?'👆 Finger: on':'👆 Finger: off');
  fg.onclick=function(){ if(sawPen){ sawPen=false; fingerOK=true; } else fingerOK=!fingerOK; tools(); }; tb.appendChild(fg);
}
tools();
document.getElementById('use').onclick=function(){
  var msg=document.getElementById('msg');
  var d=ctx.getImageData(0,0,cv.width,cv.height).data, W=cv.width, Hh=cv.height, x0=W, y0=Hh, x1=-1, y1=-1;
  for(var y=0;y<Hh;y+=2){ for(var x=0;x<W;x+=2){ if(d[(y*W+x)*4+3]>16){ if(x<x0)x0=x; if(x>x1)x1=x; if(y<y0)y0=y; if(y>y1)y1=y; } } }
  if(x1<0){ msg.textContent='Draw something first! ✏️'; return; }
  var pad=6*dpr; x0=Math.max(0,x0-pad); y0=Math.max(0,y0-pad); x1=Math.min(W,x1+pad); y1=Math.min(Hh,y1+pad);
  var w=x1-x0, h=y1-y0, sc=Math.min(1,__MAXPX__/Math.max(w,h)), o=document.createElement('canvas');
  o.width=Math.max(1,Math.round(w*sc)); o.height=Math.max(1,Math.round(h*sc));
  o.getContext('2d').drawImage(cv,x0,y0,w,h,0,0,o.width,o.height);
  post('streamlit:setComponentValue',{value:{img:o.toDataURL('image/png'),w:o.width,h:o.height,n:Date.now()},dataType:'json'});
  msg.textContent='Got it! Now give your character a name below 👇';
};
window.addEventListener('message',function(e){ if(e.data&&e.data.type==='streamlit:render'){ if(!cv.width) setup(); } });
window.addEventListener('resize',function(){ setup(); });
post('streamlit:componentReady',{apiVersion:1});
setTimeout(setup,60);
</script></body></html>"""

_DRAW_DIR = os.path.join(tempfile.gettempdir(), "earn_stars_drawpad_v1")


def draw_pad(key, height=420):
    html = DRAW_HTML.replace("__HEIGHT__", str(int(height))).replace("__MAXPX__", "260")
    d = f"{_DRAW_DIR}_{int(height)}"
    os.makedirs(d, exist_ok=True)
    f = os.path.join(d, "index.html")
    if not os.path.exists(f) or open(f, encoding="utf-8").read() != html:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(html)
    comp = _components.declare_component(f"earn_stars_drawpad_{int(height)}", path=d)
    return comp(key=key, default=None)


# ---------------------------- saving characters ----------------------------
CHARS_MAX = 8
CHAR_MOVES = {"hop": "🐰 Hop", "fly": "🕊️ Float", "spin": "🌀 Spin", "wiggle": "🪱 Wiggle", "bounce": "🏀 Bounce",
              "zoom": "🚀 Zoom"}
CHAR_VOICES = {"squeaky": ("🐭 Squeaky", 1.9, 1.1), "sweet": ("🧚 Sweet", 1.45, 1.0), "normal": ("🙂 Normal", 1.0, 1.0),
               "deep": ("🐻 Deep", 0.55, 0.9), "robot": ("🤖 Robot", 0.25, 0.85)}


def chars_path():
    return f"characters_{AUTH['profile']}.json"


def _chars_cfg():
    cfg = storage_cfg()
    return dict(cfg, path=chars_path()) if cfg else None


def chars_load(force=False):
    cache = st.session_state.get("_chars_cache")
    if cache is not None and not force:
        return cache
    try:
        cfg = _chars_cfg()
        if cfg:
            url, headers = _gh(cfg)
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 404:
                chars = []
            else:
                r.raise_for_status()
                chars = json.loads(base64.b64decode(r.json()["content"]).decode())
        else:
            f = Path(chars_path().replace(".json", "_local.json"))
            chars = json.loads(f.read_text()) if f.exists() else []
    except Exception:
        chars = []
    st.session_state._chars_cache = chars
    return chars


def chars_change(change) -> bool:
    for attempt in range(3):
        try:
            cfg = _chars_cfg()
            sha = None
            if cfg:
                url, headers = _gh(cfg)
                r = requests.get(url, headers=headers, timeout=15)
                if r.status_code == 404:
                    chars = []
                else:
                    r.raise_for_status()
                    body = r.json()
                    chars, sha = json.loads(base64.b64decode(body["content"]).decode()), body["sha"]
            else:
                f = Path(chars_path().replace(".json", "_local.json"))
                chars = json.loads(f.read_text()) if f.exists() else []
            if change(chars) is False:
                return False
            text = json.dumps(chars, ensure_ascii=False)
            if cfg:
                payload = {"message": "characters", "content": base64.b64encode(text.encode()).decode()}
                if sha:
                    payload["sha"] = sha
                requests.put(url, headers=headers, json=payload, timeout=20).raise_for_status()
            else:
                f.write_text(text)
            st.session_state._chars_cache = chars
            return True
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (409, 422) and attempt < 2:
                continue
            st.session_state.char_err = "Your character couldn't be saved just now — please try again."
            return False
        except Exception:
            st.session_state.char_err = "Your character couldn't be saved just now — please try again."
            return False
    return False


# ---------------------------- reminders from the floating friends ----------------------------
REMIND_TEXT = {
    "homework": "Have you finished today's homework? 📒",
    "speak": f"Let's speak {LANGUAGE} for 10 minutes today! 🗣️",
    "schoolnotes": "Write in Notes what you learnt at school today! 🏫✏️",
    "lunchbox": "Lunch box out of your school bag and onto the sink, please! 🍱",
    "bagpack": "Did you pack your school bag last night? Tick it in your must-do list! 🎒",
    "paati": "Time for 10 minutes of maths with Paati — on paper! 👵🏽",
    "mindful": "Take a calm minute in the Calm corner! 🫧",
    "comb": "Don't forget to comb your hair nicely! 💇‍♀️",
    "exercise": "Let's get moving and do some exercise! 🤸",
    "meditate": "Time for a quiet meditation! 🧘",
    "sit1": "Can you sit perfectly still for 1 minute? 🪷",
    "sit2": "Can you sit perfectly still for 2 minutes? 🦢",
    "chalisa": "Practise your Hanuman Chalisa parts today! 🙏",
    "tidy": "20 minutes of tidy-up time! 🧹",
    "bed": "Did you get to bed on time last night? Tick it! 🌙",
}
REMIND_HOURS = {"lunchbox": (15, 21), "schoolnotes": (15, 21), "bagpack": (6, 12), "bed": (6, 12)}


def build_reminders(today_d, ticked: set, required: set):
    """[text, from_hour, to_hour] — the browser only uses the ones that fit the current hour."""
    out = []
    for tid in sorted(required - ticked):
        t = TASK_BY_ID.get(tid)
        if not t:
            continue
        txt = REMIND_TEXT.get(tid) or f"Don't forget your must-do: {t['emoji']} {t['name']}!"
        h0, h1 = REMIND_HOURS.get(tid, (6, 21))
        out.append([f"{STUDENT_NAME}, {txt[0].lower() + txt[1:]}", h0, h1])
    if "bagpack" in TASK_BY_ID and today_d.weekday() in (6, 0, 1, 2, 3):
        out.append([f"{STUDENT_NAME}, pack your school bag tonight before bed: homework book, library book… 🎒", 18, 22])
    out.append([f"{STUDENT_NAME}, bedtime is {BEDTIME} — time to get ready for bed! 🌙", 20, 22])
    return out


# ---------------------------- the drawn characters come alive ----------------------------
CHAR_ENGINE = r"""
(function(){
  if (window.__andalChars) return; window.__andalChars = true;
  var MIN = __MIN__, MAX = __MAX__, last = -1, busy = false;
  function rnd(a, b){ return a + Math.random() * (b - a); }
  function pick(l){ return l[Math.floor(Math.random() * l.length)]; }
  var MV = {
    hop: [[{transform:'translateY(0)'},{transform:'translateY(-26px)'},{transform:'translateY(0)'}], 520],
    fly: [[{transform:'translateY(0) rotate(-5deg)'},{transform:'translateY(-22px) rotate(5deg)'},{transform:'translateY(0) rotate(-5deg)'}], 1500],
    spin: [[{transform:'rotate(0)'},{transform:'rotate(360deg)'}], 1400],
    wiggle: [[{transform:'rotate(-12deg)'},{transform:'rotate(12deg)'},{transform:'rotate(-12deg)'}], 600],
    bounce: [[{transform:'translateY(0) scale(1.1,.9)'},{transform:'translateY(-40px) scale(.95,1.05)'},{transform:'translateY(0) scale(1.1,.9)'}], 800],
    zoom: [[{transform:'scale(1)'},{transform:'scale(1.25)'},{transform:'scale(1)'}], 900]
  };
  var unlocked = false;
  function unlock(){ if (unlocked) return; unlocked = true;
    try { var u = new SpeechSynthesisUtterance(' '); u.volume = 0; speechSynthesis.speak(u); } catch (e) {} }
  document.addEventListener('pointerdown', unlock, {once: true, capture: true});
  function voice(){ try { var v = speechSynthesis.getVoices().filter(function(x){ return /^en/i.test(x.lang); });
    return v.find(function(x){ return /en-AU/i.test(x.lang); }) || v.find(function(x){ return /en-GB/i.test(x.lang); }) || v[0]; } catch (e) { return null; } }
  function talk(text, c){
    if (!window.__andalCharVoice) return;
    try { var clean = text.replace(/[\u{1F000}-\u{1FFFF}\u{2600}-\u{27BF}\u{FE0F}\u{200D}]/gu, '').trim(); if (!clean) return;
      var u = new SpeechSynthesisUtterance(clean); u.pitch = c.pitch || 1.4; u.rate = c.rate || 1; var v = voice(); if (v) u.voice = v;
      speechSynthesis.cancel(); speechSynthesis.speak(u); } catch (e) {}
  }
  function say(el, name, text){
    var old = document.getElementById('andal-cbubble'); if (old) old.remove();
    var r = el.getBoundingClientRect(), b = document.createElement('div'); b.id = 'andal-cbubble';
    b.innerHTML = '<div style="font-size:12px;color:#9b6bff;font-weight:700;margin-bottom:2px"></div><div></div>';
    b.children[0].textContent = name; b.children[1].textContent = text;
    b.style.cssText = 'position:fixed;z-index:99998;max-width:260px;padding:10px 14px;border-radius:18px;pointer-events:none;'
      + 'background:#fff;border:3px solid #ff7fbf;color:#3b2350;font:600 16px Fredoka,Nunito,system-ui,sans-serif;'
      + 'box-shadow:0 10px 26px rgba(255,95,162,.3);transition:opacity .3s, transform .3s;opacity:0;transform:scale(.6)';
    document.body.appendChild(b);
    var left = Math.min(Math.max(8, r.left + r.width / 2 - 130), innerWidth - 276);
    var top = r.top > 150 ? r.top - b.offsetHeight - 10 : r.bottom + 10;
    b.style.left = left + 'px'; b.style.top = Math.max(8, top) + 'px';
    requestAnimationFrame(function(){ b.style.opacity = '1'; b.style.transform = 'scale(1)'; });
    setTimeout(function(){ b.style.opacity = '0'; setTimeout(function(){ b.remove(); }, 350); }, 5200);
  }
  function edge(e, W, H){ if (e === 'L') return [-180, rnd(.2, .7) * H]; if (e === 'R') return [W + 30, rnd(.2, .7) * H];
    if (e === 'T') return [rnd(.1, .8) * W, -180]; return [rnd(.1, .8) * W, H + 30]; }
  function visit(manual){
    var isManual = manual !== false && manual !== undefined;
    var C = (window.__andalCharList || []).filter(function(c){ return c.show !== false || isManual; });
    if (!C.length || busy || (!isManual && document.hidden)) { if (!isManual) schedule(); return; }
    busy = true;
    var i = (typeof manual === 'number') ? Math.min(manual, C.length - 1) : (function(){ var k; do { k = Math.floor(Math.random() * C.length); } while (C.length > 1 && k === last); return k; })();
    last = i; var c = C[i], W = innerWidth, H = innerHeight;
    var E = ['L', 'R', 'T', 'B'], a = pick(E), b; do { b = pick(E); } while (b === a);
    var p0 = edge(a, W, H), p2 = edge(b, W, H), sz = Math.min(150, W * .34), pm = [rnd(.28, .55) * W, rnd(.28, .5) * H];
    var wrap = document.createElement('div'); wrap.style.cssText = 'position:fixed;left:0;top:0;z-index:99991;pointer-events:none;will-change:transform';
    var img = document.createElement('img'); img.src = c.img; img.alt = c.name;
    img.style.cssText = 'display:block;width:' + sz + 'px;height:auto;max-height:' + sz + 'px;object-fit:contain;'
      + 'filter:drop-shadow(0 6px 10px rgba(0,0,0,.18));' + (p2[0] > p0[0] ? '' : 'transform:scaleX(1)');
    var inner = document.createElement('div'); inner.appendChild(img); wrap.appendChild(inner); document.body.appendChild(wrap);
    var mv = MV[c.move] || MV.hop; try { inner.animate(mv[0], {duration: mv[1], iterations: Infinity, easing: 'ease-in-out'}); } catch (e) {}
    var T = 16000, anim = wrap.animate([
      {transform: 'translate(' + p0[0] + 'px,' + p0[1] + 'px)'},
      {transform: 'translate(' + pm[0] + 'px,' + pm[1] + 'px)', offset: .33},
      {transform: 'translate(' + pm[0] + 'px,' + pm[1] + 'px)', offset: .68},
      {transform: 'translate(' + p2[0] + 'px,' + p2[1] + 'px)'}], {duration: T, easing: 'ease-in-out'});
    setTimeout(function(){
      var h = new Date().getHours(), todo = (window.__andalTodo || []).filter(function(r){ return h >= r[1] && h < r[2]; });
      var text = (todo.length && Math.random() < .55) ? pick(todo)[0] : (c.says && c.says.length ? pick(c.says) : 'Hello!');
      say(img, c.name, text); talk(text, c);
    }, T * .36);
    anim.onfinish = function(){ wrap.remove(); busy = false; if (!isManual) schedule(); };
  }
  function schedule(){ setTimeout(function(){ visit(false); }, rnd(MIN, MAX) * 1000); }
  window.__andalCharVisit = function(i){ visit(typeof i === 'number' ? i : true); };
  setTimeout(function(){ visit(false); }, 90000);
})();
"""
CHAR_EVERY_SECONDS = (180, 300)


def sync_floaters(chars, reminders, voice_on, send_chars):
    """Keeps the browser's list of drawn characters and today's reminders up to date (characters only when changed)."""
    code = (CHAR_ENGINE.replace("__MIN__", str(CHAR_EVERY_SECONDS[0])).replace("__MAX__", str(CHAR_EVERY_SECONDS[1])))
    parts = ["var P=window.parent;",
             f"P.__andalTodo={json.dumps(reminders, ensure_ascii=False)};",
             f"P.__andalCharVoice={'true' if voice_on else 'false'};"]
    if send_chars:
        lst = [{"name": c["name"], "img": c["img"], "says": c.get("says", []), "move": c.get("move", "hop"),
                "pitch": CHAR_VOICES.get(c.get("voice", "sweet"), CHAR_VOICES["sweet"])[1],
                "rate": CHAR_VOICES.get(c.get("voice", "sweet"), CHAR_VOICES["sweet"])[2], "show": c.get("show", True)}
               for c in chars]
        parts.append(f"P.__andalCharList={json.dumps(lst, ensure_ascii=False)};")
    parts.append(f"if(!P.__andalChars){{var s=P.document.createElement('script');s.textContent={json.dumps(code)};"
                 "P.document.head.appendChild(s);}")
    _embed("<script>try{" + "".join(parts) + "}catch(e){}</script>", 1)


def char_visit_now(i):
    _embed(f"<script>/*{random.random()}*/setTimeout(function(){{try{{window.parent.__andalCharVisit({int(i)})}}catch(e){{}}}},400);"
           "</script>", 1)


# ---------------------------- beautiful new-badge pop-up ----------------------------
BADGE_ENGINE = r"""
(function(){
  if (window.__andalBadge) return;
  var q = [], open = false;
  var css = document.createElement('style');
  css.textContent = '@keyframes bdgSpin{to{transform:rotate(360deg)}}@keyframes bdgPop{0%{transform:scale(.3) rotate(-12deg);opacity:0}'
   + '60%{transform:scale(1.08) rotate(3deg);opacity:1}100%{transform:scale(1) rotate(0)}}'
   + '@keyframes bdgFall{0%{transform:translateY(-10vh) rotate(0)}100%{transform:translateY(110vh) rotate(720deg)}}'
   + '@keyframes bdgShine{0%,100%{filter:drop-shadow(0 0 0 rgba(255,215,90,0))}50%{filter:drop-shadow(0 0 22px rgba(255,215,90,.95))}}'
   + '#bdg-ov{position:fixed;inset:0;z-index:100000;display:flex;align-items:center;justify-content:center;'
   + 'background:rgba(45,20,70,.45);backdrop-filter:blur(5px);-webkit-backdrop-filter:blur(5px);transition:opacity .4s;opacity:0}'
   + '#bdg-card{position:relative;width:min(340px,86vw);padding:26px 22px 22px;border-radius:30px;text-align:center;'
   + 'background:linear-gradient(165deg,#fffdf4,#fff0f8 60%,#f1ebff);box-shadow:0 24px 60px rgba(60,20,90,.35);'
   + 'font-family:Fredoka,Nunito,system-ui,sans-serif;color:#3b2350;animation:bdgPop .7s cubic-bezier(.2,.9,.3,1.3) both}'
   + '#bdg-card .rays{position:absolute;left:50%;top:92px;width:300px;height:300px;margin:-150px 0 0 -150px;border-radius:50%;'
   + 'background:repeating-conic-gradient(rgba(255,215,90,.35) 0 10deg,transparent 10deg 20deg);animation:bdgSpin 9s linear infinite;'
   + '-webkit-mask:radial-gradient(circle,#000 30%,transparent 70%);mask:radial-gradient(circle,#000 30%,transparent 70%)}'
   + '#bdg-card .top{position:relative;font-size:14px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#d6337f}'
   + '#bdg-card .medal{position:relative;width:120px;height:120px;margin:14px auto 10px;border-radius:50%;display:flex;'
   + 'align-items:center;justify-content:center;font-size:62px;border:6px solid #fff;animation:bdgShine 2s ease-in-out infinite}'
   + '#bdg-card .nm{position:relative;font-size:26px;font-weight:700;margin-top:6px}'
   + '#bdg-card .ds{position:relative;font-size:16px;color:#7a6386;margin:4px 0 16px}'
   + '#bdg-card button{position:relative;font:700 18px Fredoka,Nunito,system-ui,sans-serif;color:#fff;border:0;border-radius:999px;'
   + 'padding:12px 30px;background:linear-gradient(90deg,#ff5fa2,#9b6bff);box-shadow:0 8px 20px rgba(155,107,255,.4);cursor:pointer}'
   + '.bdg-cf{position:fixed;top:0;z-index:100001;pointer-events:none;width:10px;height:16px;border-radius:3px;animation:bdgFall linear forwards}';
  document.head.appendChild(css);
  function confetti(){ var C = ['#ff4fa3','#ffb800','#2fbf5a','#38b6ff','#9b6bff','#ff7a45','#ffe14d'];
    for (var i = 0; i < 90; i++) { var p = document.createElement('div'); p.className = 'bdg-cf';
      p.style.left = (Math.random() * 100) + 'vw'; p.style.background = C[i % C.length];
      p.style.animationDuration = (2.4 + Math.random() * 2.2) + 's'; p.style.animationDelay = (Math.random() * .7) + 's';
      p.style.width = (6 + Math.random() * 8) + 'px'; document.body.appendChild(p);
      setTimeout(function(x){ return function(){ x.remove(); }; }(p), 5600); } }
  function next(){
    if (open || !q.length) return; open = true; var b = q.shift();
    var ov = document.createElement('div'); ov.id = 'bdg-ov';
    ov.innerHTML = '<div id="bdg-card"><div class="rays"></div><div class="top">🎉 New badge earned! 🎉</div>'
      + '<div class="medal"></div><div class="nm"></div><div class="ds"></div><button>Yay! 💖</button></div>';
    var m = ov.querySelector('.medal'); m.textContent = b.emoji;
    m.style.background = 'radial-gradient(circle at 35% 30%,#fff 0,' + b.c1 + ' 40%,' + b.c2 + ' 100%)';
    m.style.boxShadow = '0 0 0 5px ' + b.c2 + ',0 12px 26px rgba(0,0,0,.18)';
    ov.querySelector('.nm').textContent = b.name; ov.querySelector('.ds').textContent = b.desc;
    document.body.appendChild(ov); requestAnimationFrame(function(){ ov.style.opacity = '1'; });
    confetti(); try { window.__andalPlay && window.__andalPlay('fanfare'); } catch (e) {}
    function close(){ ov.style.opacity = '0'; setTimeout(function(){ ov.remove(); open = false; next(); }, 420); }
    ov.querySelector('button').onclick = close; ov.onclick = function(e){ if (e.target === ov) close(); };
    setTimeout(function(){ if (document.body.contains(ov)) close(); }, 12000);
  }
  window.__andalBadge = function(list){ list.forEach(function(b){ q.push(b); }); next(); };
})();
"""


def badge_popup(badges):
    """badges: list of BADGES rows (id, emoji, name, desc, stat, need, c1, c2)."""
    lst = [{"emoji": b[1], "name": b[2], "desc": b[3], "c1": b[6], "c2": b[7]} for b in badges]
    _embed(f"<script>/*{random.random()}*/try{{var P=window.parent;if(!P.__andalBadge){{var s=P.document.createElement('script');"
           f"s.textContent={json.dumps(BADGE_ENGINE)};P.document.head.appendChild(s);}}"
           f"setTimeout(function(){{P.__andalBadge({json.dumps(lst, ensure_ascii=False)});}},350);}}catch(e){{}}</script>", 1)


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
if not AUTH.get("legacy"):
    _sb1, _sb2 = st.columns([4, 1])
    _sb1.caption(f"👋 Signed in as **{STUDENT_NAME}'s grown-up**" if IS_PARENT else f"👋 Signed in as **{STUDENT_NAME}**")
    _sb2.button("Sign out", on_click=do_logout, key="signout", use_container_width=True)
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


FB_STARS = {0: "", 1: "⭐", 2: "⭐⭐", 3: "⭐⭐⭐"}
FB_TASKS = [(t["id"], f"{t['emoji']} {t['name']}") for t in TASKS] + [
    ("chalisa_recite", "🙏 Hanuman Chalisa recitation"), ("story", "📖 Story / writing"),
    ("bonus_maths", "⭐ Bonus maths"), ("general", "💬 General / the whole day")]
FB_TASK_NAME = dict(FB_TASKS)
new_feedback = [f for f in data.get("task_feedback", []) if not f.get("seen")]
if new_feedback:
    with alerts:
        st.markdown(f'<div class="msg">💬 <b>You have {len(new_feedback)} new note{"s" if len(new_feedback) != 1 else ""} '
                    'from a grown-up about your tasks!</b><br>Scroll down on the 🌈 Today tab to '
                    '“Notes from my grown-ups”.</div>', unsafe_allow_html=True)


def save_task_feedback(prefix, day_key, need_pin):
    if need_pin and not pin_ok(f"{prefix}_pin"):
        st.session_state[f"{prefix}_msg"] = ("bad", "That PIN isn't right.")
        return
    text = str(st.session_state.get(f"{prefix}_text", "")).strip()
    task = st.session_state.get(f"{prefix}_task", "general")
    stars = int(st.session_state.get(f"{prefix}_stars", 0) or 0)
    if not text and not stars:
        st.session_state[f"{prefix}_msg"] = ("bad", "Write a note or choose stars first.")
        return

    def change(d):
        d.setdefault("task_feedback", []).append({
            "id": uuid.uuid4().hex[:8], "date": day_key, "task": task, "text": text, "stars": stars,
            "time": datetime.now(ZoneInfo(TIMEZONE)).strftime("%d %b %H:%M"), "seen": False})

    if need_pin:
        st.session_state[f"{prefix}_pin"] = ""
    if update(change):
        st.session_state[f"{prefix}_text"] = ""
        st.session_state[f"{prefix}_stars"] = 0
        st.session_state[f"{prefix}_msg"] = ("ok", f"💬 Feedback saved — {STUDENT_NAME} will see it on her Today page.")


def feedback_form(prefix, day_key, need_pin, task_ids=None):
    opts = [k for k, _ in FB_TASKS if task_ids is None or k in task_ids or k in ("chalisa_recite", "story",
                                                                                   "bonus_maths", "general")]
    with st.form(f"{prefix}_form", border=False):
        st.selectbox("Which task?", opts, key=f"{prefix}_task", format_func=lambda k: FB_TASK_NAME.get(k, k))
        st.text_area("Your feedback", key=f"{prefix}_text", height=80,
                     placeholder="Lovely clear Tamil today! Try to say 'naan' a little slower. 💖")
        st.radio("Stars (optional)", [0, 1, 2, 3], key=f"{prefix}_stars", horizontal=True,
                 format_func=lambda n: FB_STARS[n] or "none")
        if need_pin:
            st.text_input("Grown-up PIN", type="password", key=f"{prefix}_pin")
        st.form_submit_button("💾 Save feedback", on_click=save_task_feedback, args=(prefix, day_key, need_pin))
    fmsg = st.session_state.pop(f"{prefix}_msg", None)
    if fmsg:
        (st.success if fmsg[0] == "ok" else st.error)(fmsg[1])


def mark_feedback_seen():
    def change(d):
        for f in d.get("task_feedback", []):
            f["seen"] = True
    update(change)


def email_cfg():
    e = secret(EMAIL_SECRET)
    if e and e.get("sender") and e.get("app_password") and e.get("to"):
        to = e["to"] if isinstance(e["to"], list) else [x.strip() for x in str(e["to"]).split(",") if x.strip()]
        return {"sender": e["sender"], "password": str(e["app_password"]).replace(" ", ""), "to": to}
    return None


def send_email(subject, body):
    """Email the grown-ups (Gmail + App Password from Secrets). Returns True/False; never crashes the app."""
    cfg = email_cfg()
    if not cfg:
        return False
    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, cfg["sender"], ", ".join(cfg["to"])
        msg.set_content(body)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as smtp:
            smtp.login(cfg["sender"], cfg["password"])
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.session_state.email_error = str(e)[:200]
        return False


def send_test_email():
    ok = send_email(f"⭐ Test from {STUDENT_NAME}'s app", f"Email alerts are working! Messages from {STUDENT_NAME} "
                    "will arrive here.")
    st.session_state.parent_note = ("📧 Test email sent — check your inbox (and spam folder)." if ok else
                                    f"📧 Couldn't send: {st.session_state.pop('email_error', 'email is not set up')}")


def send_kid_message():
    text = str(st.session_state.get("kid_msg", "")).strip()
    if not text:
        st.session_state.kid_msg_note = ("bad", "Type your message first! ✏️")
        return

    def change(d):
        d.setdefault("kid_messages", []).append({
            "id": uuid.uuid4().hex[:8], "date": TODAY_KEY, "time": datetime.now(ZoneInfo(TIMEZONE)).strftime("%H:%M"),
            "text": text[:1000], "read": False, "reply": ""})

    if update(change):
        st.session_state.kid_msg = ""
        now = datetime.now(ZoneInfo(TIMEZONE)).strftime("%A %d %b, %I:%M %p")
        emailed = send_email(f"💌 New message from {STUDENT_NAME}",
                             f"{STUDENT_NAME} sent you a message ({now}):\n\n{text}\n\n"
                             "Reply in the 🔐 Grown-ups tab of the app: https://andal-earns-stars.streamlit.app (sign in as "
                             f"{AUTH['profile']}_parent)")
        st.session_state.kid_msg_note = ("ok", "💌 Sent! Your grown-up will see it" +
                                         (" in their email too. 📧" if emailed else " in the 🔐 Grown-ups tab."))


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
_th = next((t for t in THEMES if t["id"] == theme_id), {})
_icons = _th.get("icons") or [("🦄", "unicorn"), ("🐰", "bunny"), ("🌈", "rainbow"), ("✨", "star")]
_floats = "".join(f'<div class="float f{i + 1}" data-joke="{k}" title="Tap me!">{e}</div>' for i, (e, k) in enumerate(_icons))
st.markdown(
    f"""<div class="hero">{_floats}
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
    badge_popup([b for bid in party for b in BADGES if b[0] == bid])

# ------------------------------ navigation ------------------------------
# Big, simple category buttons; each category shows only its own few tabs.
NAV = [
    ("day", "🌈", "My Day", ["🌈 Today"] + (["🧘 Calm corner"] if SHOW_MINDFUL else [])),
    ("learn", "📚", "Learn", ["🧮 Maths", "✍️ Stories"] + (["🗣️ Tamil words"] if SHOW_TAMIL else [])
     + (["🙏 Chalisa"] if SHOW_CHALISA else [])),
    ("fun", "🎉", "Fun", ["🎡 Spin", "🏆 Rewards", "🐰 Bunny & badges", "🎨 My characters", "📅 My weeks"]),
    ("friends", "💬", "Chat", ["💬 Chat"] if CHAT_ON else []),
    ("grown", "🔐", "Grown-ups", ["🔐 Grown-ups"]),
]
NAV = [n for n in NAV if n[3]]
if st.session_state.get("nav") not in [n[0] for n in NAV]:
    st.session_state.nav = "grown" if IS_PARENT else "day"


def go_nav(cid):
    st.session_state.nav = cid


with st.container(key="navbar"):
    _ncols = st.columns(len(NAV))
    for _col, (_cid, _emo, _label, _names) in zip(_ncols, NAV):
        _dot = " ✨" if _cid == "fun" and (small_ws["ok"] or big_ws["ok"]) else ""
        _col.button(f"{_emo} {_label}{_dot}", key=f"nav_{_cid}", on_click=go_nav, args=(_cid,),
                    type="primary" if _cid == st.session_state.nav else "secondary", use_container_width=True)
_hidden = st.container(key="navhidden")      # pages that aren't open are kept here, out of sight
_TABS = {}
for _cid, _emo, _label, _names in NAV:
    if _cid == st.session_state.nav:
        if len(_names) == 1:
            _TABS[_names[0]] = st.container()
        else:
            _TABS.update(zip(_names, st.tabs(_names, key=f"tabs_{_cid}")))
    else:
        for _n in _names:
            _TABS[_n] = _hidden.container()
(tab_today, tab_maths, tab_write, tab_spin, tab_rewards, tab_pet, tab_weeks, tab_parent) = (
    _TABS["🌈 Today"], _TABS["🧮 Maths"], _TABS["✍️ Stories"], _TABS["🎡 Spin"], _TABS["🏆 Rewards"],
    _TABS["🐰 Bunny & badges"], _TABS["📅 My weeks"], _TABS["🔐 Grown-ups"])
tab_tamil, tab_chalisa, tab_chat = _TABS.get("🗣️ Tamil words"), _TABS.get("🙏 Chalisa"), _TABS.get("💬 Chat")
tab_calm = _TABS.get("🧘 Calm corner")
tab_chars = _TABS["🎨 My characters"]


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


REQ_TODAY = required_ids(today)
TASKS_TODAY = tasks_for(today)
WEEKEND = weekend_rules(today)


def task_label(t):
    reward = f"  **+{t['minutes']} min**" if t["minutes"] else "  *(counts toward big rewards)*"
    must = "  · **must do**" if t["id"] in REQ_TODAY else ""
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
    for f in data.get("task_feedback", []):
        if f["date"] == TODAY_KEY and f["task"] == tid:
            st.markdown(f'<div class="note">💬 <b>Grown-up says:</b> {FB_STARS.get(f.get("stars", 0), "")} '
                        f'{html_safe(f.get("text", ""))}</div>', unsafe_allow_html=True)


def approve_tasks(day_key, tids, pin_key=None):
    if pin_key and not pin_ok(pin_key):
        st.session_state.approve_msg = ("bad", "That PIN isn't right.")
        return
    n = {}

    def change(d):
        ticked = set(d["days"].get(day_key, []))
        ok = d.setdefault("approved", {}).setdefault(day_key, [])
        new = [t for t in tids if t in ticked and t not in ok]
        dk = date.fromisoformat(day_key)
        if "chalisa" in new and weekend_rules(dk) and dk.weekday() == 6:
            wc = weekend_chalisa(d, dk)
            if wc and not wc["complete"]:
                new.remove("chalisa")
                n["held"] = True
        ok.extend(new)
        n["n"] = len(new)
        if day_key != TODAY_KEY:
            d.setdefault("earned", {})[day_key] = task_minutes(counted_set(d, day_key))

    if pin_key:
        st.session_state[pin_key] = ""
    if update(change):
        st.session_state.parent_ok = False if pin_key else st.session_state.get("parent_ok")
        st.session_state.flash = f"✅ {n['n']} task{'s' if n['n'] != 1 else ''} approved — rewards unlocked!"
        if n.get("held"):
            st.session_state.approve_note = (f"🙏 The Chalisa task can be approved on Sunday once this weekend's "
                                             f"{WEEKEND_CHALISA_PARTS} parts have been recited to a grown-up "
                                             "(🙏 Chalisa tab).")


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

    if WEEKEND and mins > WEEKEND_MAX_STRETCH:
        st.session_state.use_msg = ("bad", f"Weekend rule: at most {WEEKEND_MAX_STRETCH} minutes in one go. "
                                           "Take a break, then use more later. 🌞")
        st.session_state.use_pin = ""
        return

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
    if WEEKEND:
        st.markdown(f'<div class="fact">🌞 <b>Weekend must-dos!</b> On Saturdays and Sundays, these are must-do too: '
                    f'🙏 Hanuman Chalisa practice, 🧹 tidy-up (20 min), 🤸 exercise, 🧘 meditation and both 🪷🦢 '
                    f'sit-still challenges. Screen time: at most <b>{WEEKEND_MAX_STRETCH} minutes</b> in one go.</div>',
                    unsafe_allow_html=True)
    required_left = [t for t in TASKS_TODAY if t["id"] in REQ_TODAY and t["id"] not in done_today]
    if required_left:
        def _low(n):
            return n if n.split()[0] in ("Hanuman", "English") else n[0].lower() + n[1:]
        names = ", ".join(f"{t['emoji']} {_low(t['name'])}" for t in required_left[:-1])
        names = (names + " and " if names else "") + f"{required_left[-1]['emoji']} {_low(required_left[-1]['name'])}"
        if len(required_left) > 4:
            st.warning(f"🔒 **{len(required_left)} must-do tasks** to finish before screen time unlocks: "
                       + "  ".join(t["emoji"] for t in required_left) + "  — they're in the 🦄 Must do list below.")
        else:
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
            anote = st.session_state.pop("approve_note", None)
            if anote:
                st.warning(anote)
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
                    '<div style="color:#8a6a96;font-size:.9rem">Unused minutes are saved for another day 💾</div>'
                    + (f'<div style="margin-top:8px;padding:8px 10px;border-radius:12px;background:#fff3d6;color:#7a4a00;'
                       f'font-size:.95rem">🌞 <b>Weekend rule:</b> even if you have more minutes saved, use the screen '
                       f'for <b>{WEEKEND_MAX_STRETCH} minutes at most</b> at a time. Then take a break! 🧘</div>'
                       if WEEKEND else ""),
                    unsafe_allow_html=True)
        with c2:
            if bal["balance"] > 0:
                st.markdown("**🧑‍🍼 Grown-up: record minutes used**")
                st.text_input("Grown-up PIN", type="password", key="use_pin")
                quick = min(DAILY_GOAL_MINUTES, bal["balance"])
                st.markdown(f"**Option 1** · used the full {quick} minutes")
                st.toggle(f"Slide ➡️ {quick} minutes used", key="use_toggle", on_change=use_quick)
                most = min(bal["balance"], WEEKEND_MAX_STRETCH) if WEEKEND else bal["balance"]
                st.markdown("**Option 2** · used fewer minutes" if not WEEKEND else
                            f"**Option 2** · enter minutes used (up to {most})")
                if st.session_state.get("use_mins", 0) > most or "use_mins" not in st.session_state:
                    st.session_state.use_mins = min(15, most)
                oc1, oc2 = st.columns([3, 2])
                oc1.number_input("Minutes used", min_value=1, max_value=most, step=5, key="use_mins",
                                 label_visibility="collapsed")
                oc2.button("💾 Save", on_click=use_custom, use_container_width=True)
            else:
                st.caption("No minutes to use yet — finish some tasks! 🐰")
        msg = st.session_state.pop("use_msg", None)
        if msg:
            (st.success if msg[0] == "ok" else st.error)(msg[1])

    # ---- inspiring quote + health tip (new ones every hour; mindfulness/health quotes every other hour) ----
    _qslot = today.toordinal() * (24 // QUOTE_HOURS) + datetime.now(ZoneInfo(TIMEZONE)).hour // QUOTE_HOURS
    _qlist = MINDFUL_QUOTES if _qslot % 2 == 0 else QUOTES
    _qorder = list(range(len(_qlist)))
    random.Random(2026).shuffle(_qorder)
    _q = _qlist[_qorder[(_qslot // 2) % len(_qlist)]]
    _horder = list(range(len(HEALTH_TIPS)))
    random.Random(7).shuffle(_horder)
    st.markdown(f'<div class="fact">🍏 <b>Health tip:</b> {html_safe(HEALTH_TIPS[_horder[_qslot % len(HEALTH_TIPS)]])}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="quote"><div class="qmark">“</div><div class="qtext">{html_safe(_q[0])}</div>'
                f'<div class="qwho">— {html_safe(_q[1])}, <span>{html_safe(_q[2])}</span></div>'
                f'<div class="qmean">💡 {html_safe(_q[3])}</div></div>', unsafe_allow_html=True)

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
                 + ("· Need a word? Look it up in the <b>🗣️ Tamil words</b> tab!" if SHOW_TAMIL else ""),
        "write1": f"📄 <b>Write it on paper first</b> — in your notebook or on a separate sheet. "
                  f"Idea: <b>{WRITING_PROMPTS[write_n % len(WRITING_PROMPTS)]}</b>. Try to use the word "
                  f"<b>{html_safe(wotd['word'])}</b>. Then tick this and show your writing to a grown-up. "
                  "🎙️ If you like, read it out loud and record it in the <b>✍️ Stories</b> tab.",
        "write2": f"📄 <b>Paper first!</b> Write your second piece in your notebook or on paper. "
                  f"Idea: <b>{WRITING_PROMPTS[(write_n + 5) % len(WRITING_PROMPTS)]}</b>. Then tick this and show "
                  "a grown-up. 🎙️ You can read it aloud and record it in the <b>✍️ Stories</b> tab.",
        "tidy": "🧹 Set a 20-minute timer. Put toys away, clear and wipe your desk, sort books and pencils, "
                "make your bed and pick up clothes. Then show a grown-up your tidy space! ✨",
        "maths": f"🧮 Go to the <b>Maths</b> tab. This ticks itself when you solve {MATHS_TO_SOLVE} problems "
                 f"(solved today: {data.get('maths', {}).get(TODAY_KEY, {}).get('solved', 0)}).",
        "sit1": "📣 <b>Call a grown-up to watch you first!</b> Sit cross-legged, hands resting on your knees, "
                "back tall, eyes soft. No talking, no wiggling, no giggling. Use the timer below.",
        "sit2": "📣 <b>Call a grown-up to watch.</b> Same as the 1-minute challenge, but twice as long! "
                "Tip: breathe slowly and count your breaths.",
        "sing": "🎶 Sing for 15 minutes every day for 30 days in a row to win 60 bonus minutes!",
        "veggies": "🥦 Did you eat fruit at snack time and veggies at dinner? A rainbow on your plate! 🌈",
        "chore": "🧹 Ideas: make your bed, tidy your desk, set the table, fold washing, feed a pet.",
        "music": "🎹 Practise your instrument or singing for 15 minutes. 30 days in a row = 60 bonus minutes!",
        "bed": f"🌙 Tick this in the morning if you were in bed by {BEDTIME} last night. "
               "30 nights in a row = 🍦 ice cream. 90 nights = 🎠 play centre!",
    }
    wc_today = weekend_chalisa(data, today) if WEEKEND else None
    if wc_today:
        if wc_today["mode"] == "learn":
            parts_txt = " and ".join(f"Part {i + 1}" for i in wc_today["targets"])
            goal = f"learn <b>{parts_txt}</b> by heart"
        else:
            goal = f"revise any <b>{WEEKEND_CHALISA_PARTS} parts</b>"
        tips["chalisa"] = (f"🙏 This weekend: {goal}. Say each part at least <b>{CHALISA_REPEATS} times</b> (count them "
                           f"in the 🙏 Chalisa tab). On Saturday or Sunday, recite the parts to a grown-up "
                           f"<b>without looking and without help</b>. Recited so far: <b>{len(wc_today['done'])}/"
                           f"{wc_today['need']}</b>{' ✅' if wc_today['complete'] else ''}. Tick this each day after "
                           "practising; a grown-up approves it (on Sunday, once the parts are recited).")
    tips.update({
        "schoolnotes": "📝 Open the <b>Notes</b> app, write today's date, and use your Apple Pencil (Scribble) to write "
                       "<b>3 things you learnt at school today</b>. Show a grown-up, then tick this.",
        "lunchbox": "🍱 As soon as you get home, take your lunch box out of your school bag and put it at the sink.",
        "bagpack": "🎒 Tick this in the morning if you packed your bag <b>last night before bed</b>: homework book, "
                   "library book on library day, and anything else you need for today.",
        "paati": "👵🏽 Ask Paati for 10–12 minutes of maths. Work it out <b>on paper</b>, then show Paati your page.",
        "mindful": "🫧 Do one easy calm activity: the breathing bubble, a feelings check-in or your gratitude jar in the "
                   "<b>🧘 Calm corner</b> (in 🌈 My Day).",
        "comb": "💇‍♀️ Comb your hair nicely, all the way through. Ask a grown-up to help with tangles.",
    })
    for sec_id, sec_title in SECTIONS:
        sec_tasks = [t for t in TASKS_TODAY
                     if ("must" if t["id"] in REQ_TODAY else t.get("section", "learn")) == sec_id]
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

    # ---- notes (feedback) from grown-ups ----
    recent_fb = [f for f in data.get("task_feedback", [])
                 if f["date"] >= (today - timedelta(days=14)).isoformat()]
    st.markdown("### 💬 Notes from my grown-ups")
    with st.container(border=True):
        if not recent_fb:
            st.caption("When a grown-up gives you feedback on a task, it will appear here. 🌟")
        for f in reversed(recent_fb[-12:]):
            st.markdown(f'<div class="note">{"🆕 " if not f.get("seen") else ""}<b>{html_safe(FB_TASK_NAME.get(f["task"], f["task"]))}</b>'
                        f' · {date.fromisoformat(f["date"]).strftime("%a %d %b")} {FB_STARS.get(f.get("stars", 0), "")}'
                        f'<br>{html_safe(f.get("text", ""))}</div>', unsafe_allow_html=True)
        if any(not f.get("seen") for f in recent_fb):
            st.button("👍 Got it — thank you!", on_click=mark_feedback_seen, key="fb_seen_btn")

    # ---- message to a grown-up ----
    st.markdown("### 💌 Send a message to my grown-up")
    with st.container(border=True):
        st.text_area("My message", key="kid_msg", height=80, max_chars=1000, label_visibility="collapsed",
                     placeholder=f"Type a message for {PARENT_WORDS}… 💖")
        st.button("📨 Send", on_click=send_kid_message, key="kid_send", type="primary")
        knote = st.session_state.pop("kid_msg_note", None)
        if knote:
            (st.success if knote[0] == "ok" else st.warning)(knote[1])
        my_msgs = data.get("kid_messages", [])
        if my_msgs:
            with st.expander(f"📬 My messages ({len(my_msgs)})"):
                for km in reversed(my_msgs[-10:]):
                    st.markdown(f"• {km['date'][5:]} {km.get('time', '')}: {md_safe(km['text'])} "
                                f"{'👀 read' if km.get('read') else '🕒 not read yet'}"
                                + (f"  \n  ↪️ **Reply:** {md_safe(km['reply'])}" if km.get("reply") else ""))

    # ---- quick feedback while listening (grown-up PIN) ----
    with st.expander("🧑‍🏫 Grown-up: give feedback on a task (needs PIN)"):
        feedback_form("qfb", TODAY_KEY, True, {t["id"] for t in TASKS_TODAY})

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
        # Writing tasks are done on PAPER and approved by a grown-up, so typing here doesn't tick them.
        award_word_win(d, TODAY_KEY, w["word"], info)

    if update(change):
        st.session_state.story_title = ""
        st.session_state.story_text = ""
        parts = [f"📖 Story saved! ({words} words)"]
        if info.get("tick"):
            parts.append(f"Your writing task {'1' if info['tick'] == 'write1' else '2'} is ticked! ✅")
            st.session_state.celebrate = {"fact": info.get("fact"), "task": info["tick"]}
        elif info.get("problem"):
            parts = [f"📖 Saved, but: {info['problem']}"]
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

    st.markdown("### 📄 English writing: paper first!")
    with st.container(border=True):
        st.markdown(f'<div class="tip" style="margin-left:0;font-size:1.05rem">✏️ <b>Step 1:</b> write BOTH English '
                    f'pieces on paper — in your notebook or on a separate sheet.<br>'
                    f'💡 Ideas: <b>{html_safe(WRITING_PROMPTS[write_n % len(WRITING_PROMPTS)])}</b> and '
                    f'<b>{html_safe(WRITING_PROMPTS[(write_n + 5) % len(WRITING_PROMPTS)])}</b><br>'
                    '✅ <b>Step 2:</b> tick “English writing” on the 🌈 Today tab and show your paper to a grown-up.<br>'
                    '🎙️ <b>Step 3 (if you like):</b> read your story out loud and record it below!</div>',
                    unsafe_allow_html=True)
        if hasattr(st, "audio_input"):
            st.audio_input("🎙️ Read my story aloud (tap to record, then play it back)", key="story_rec")
            st.caption("Recordings are for listening back now (and playing to a grown-up) — they aren't saved.")

    st.markdown("### ⌨️ Type a story (optional)")
    st.caption("Typing a story here is extra practice — it helps with the word-of-the-day challenge and badges. "
               "Your writing tasks are still done on paper. 📄")
    with st.container(border=True):
        st.text_input("Title", key="story_title", placeholder="My amazing story")
        st.text_area("Your story", key="story_text", height=260,
                     placeholder="Once upon a time, a curious little bunny…")
        draft = str(st.session_state.get("story_text", ""))
        n_words = count_words(draft)
        st.markdown(f'<div class="minutes"><span>📝 {n_words} words</span><span>🎯 aim for {MIN_STORY_WORDS}+ words'
                    f'</span></div><div class="rbar"><div class="rfill" style="width:'
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


if tab_tamil is not None:
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
        if d.get("chalisa_reps", {}).get(str(i), 0) < CHALISA_REPEATS:
            info["reps"] = True
            return False
        ch[str(i)] = TODAY_KEY
        bs = bead_status(d)
        while d.get("bead_rewards_given", 0) < bs["rewards_due"]:
            d["bead_rewards_given"] = d.get("bead_rewards_given", 0) + 1
            d.setdefault("credits", []).append({"date": TODAY_KEY, "minutes": BEAD_MINUTES,
                                                "reason": f"{BEADS_FOR_MINUTES} prayer beads 📿"})
            info["minutes"] = info.get("minutes", 0) + BEAD_MINUTES
        info["all"] = bs["all_done"]

    ok = update(change)
    st.session_state[f"ch_pin_{i}"] = ""
    if info.get("reps"):
        st.session_state.ch_msg = ("bad", f"Say this part {CHALISA_REPEATS} times first (use the counter). 🔁")
    if ok:
        parts = [f"🙏 Wonderful! Part {i + 1} learned: +{BEADS_PER_PART} 📿 beads!"]
        if info.get("minutes"):
            parts.append(f"You reached {BEADS_FOR_MINUTES} beads: +{info['minutes']} minutes of screen time! ⏳")
        if info.get("all"):
            parts.append("🎉 You learned the WHOLE Hanuman Chalisa! Choose your special outing below!")
        st.session_state.ch_msg = ("ok", " ".join(parts))
        st.session_state.celebrate = {"fact": None, "task": "chalisa"}
        st.session_state[f"ch_ready_{i}"] = False


def add_rep(i, step=1):
    def change(d):
        reps = d.setdefault("chalisa_reps", {})
        reps[str(i)] = max(0, reps.get(str(i), 0) + step)
    if update(change) and step > 0:
        n = st.session_state.data.get("chalisa_reps", {}).get(str(i), 0)
        if n == CHALISA_REPEATS:
            st.session_state.ch_msg = ("ok", f"🎉 {CHALISA_REPEATS} times! Part {i + 1} is ready to recite to a grown-up.")
            st.session_state.celebrate = {"fact": None, "task": "chalisa"}


def revise_part(i):
    if not pin_ok(f"rv_pin_{i}"):
        st.session_state.ch_msg = ("bad", "That PIN isn't right. Ask a grown-up! 🔐")
        return
    sat = weekend_start(today)

    def change(d):
        if sat is None:
            return False
        lst = d.setdefault("chalisa_revise", {}).setdefault(sat.isoformat(), [])
        if i in lst:
            return False
        lst.append(i)

    st.session_state[f"rv_pin_{i}"] = ""
    if update(change):
        st.session_state.ch_msg = ("ok", f"🙏 Super! Part {i + 1} recited from memory this weekend.")
        st.session_state.celebrate = {"fact": None, "task": "chalisa"}


def reps_box(i):
    n = data.get("chalisa_reps", {}).get(str(i), 0)
    shown = min(n, CHALISA_REPEATS)
    dots = "".join(f'<span class="bead{" on" if j < shown else ""}" style="width:14px;height:14px"></span>'
                   for j in range(CHALISA_REPEATS))
    st.markdown(f'<div style="text-align:center"><div class="chalisa-head">🔁 Said it {n} time{"s" if n != 1 else ""}'
                f'{" ✅" if n >= CHALISA_REPEATS else f" · {CHALISA_REPEATS - n} to go"}</div>'
                f'<div class="beads">{dots}</div></div>', unsafe_allow_html=True)
    r1, r2 = st.columns([3, 1])
    r1.button("➕ I said the whole part once more", key=f"rep_add_{i}", on_click=add_rep, args=(i, 1),
              use_container_width=True, type="primary")
    r2.button("↩️ Undo", key=f"rep_undo_{i}", on_click=add_rep, args=(i, -1), use_container_width=True,
              disabled=n == 0)
    return n


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


if tab_chalisa is not None:
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
        wc = weekend_chalisa(data, today) if WEEKEND else None
        with st.container(border=True):
            st.markdown('<div class="reward-head">🌞 Weekend Chalisa goal</div>', unsafe_allow_html=True)
            if wc:
                if wc["mode"] == "learn":
                    names = " and ".join(f"<b>Part {i + 1}</b>" for i in wc["targets"])
                    st.markdown(f'<div class="how">This weekend, learn {names} by heart. It\'s a <b>must-do</b> on Saturday '
                                f'and Sunday!</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="how">You know the whole Chalisa! 🏆 This weekend, revise any '
                                f'<b>{WEEKEND_CHALISA_PARTS} parts</b> and recite them to a grown-up.</div>',
                                unsafe_allow_html=True)
                pills = "".join(f'<span class="pill {"ok" if j < len(wc["done"]) else "no"}">'
                                f'{"✅" if j < len(wc["done"]) else "⬜"} recited {j + 1}</span>' for j in range(wc["need"]))
                st.markdown(pills, unsafe_allow_html=True)
            else:
                nxt_parts = [i for i in range(len(CHALISA_PARTS)) if str(i) not in data.get("chalisa", {})]
                if nxt_parts:
                    st.markdown(f'<div class="how">Every Saturday & Sunday: learn <b>{WEEKEND_CHALISA_PARTS} parts</b>. '
                                f'Next weekend: ' + " and ".join(f"<b>Part {i + 1}</b>" for i in nxt_parts[:WEEKEND_CHALISA_PARTS])
                                + '. You can start practising now!</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="how">Every weekend: revise any {WEEKEND_CHALISA_PARTS} parts.</div>',
                                unsafe_allow_html=True)
            st.markdown(f'<div class="tip" style="margin-left:0">🔁 <b>The rule:</b> say every part at least '
                        f'<b>{CHALISA_REPEATS} times</b> (tap the counter each time). Then recite it to a grown-up '
                        '<b>without looking and without any help</b>. The grown-up approves with the PIN. 🙏</div>',
                        unsafe_allow_html=True)
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
                    if wc and wc["mode"] == "revise":
                        if i in wc["done"]:
                            st.info("🙏 Recited from memory this weekend ✅")
                        else:
                            reps_box(i)
                            with st.form(f"rv_form_{i}", border=False):
                                v1, v2 = st.columns([2, 1])
                                v1.text_input("Grown-up PIN: recited without looking or help", type="password",
                                              key=f"rv_pin_{i}")
                                v2.write("")
                                v2.form_submit_button("Recited ✅", on_click=revise_part, args=(i,))
                    continue
                n_reps = reps_box(i)
                if hasattr(st, "audio_input"):
                    st.audio_input("🎙️ Practice recorder (optional: tap to record, then play it back)", key=f"ch_rec_{i}")
                ready_ok = n_reps >= CHALISA_REPEATS
                if not ready_ok:
                    st.caption(f"🔒 Say this part {CHALISA_REPEATS} times first, then you can recite it to a grown-up.")
                st.checkbox(f"I recited all {len(part['lines'])} lines to a grown-up — without looking and without any help",
                            key=f"ch_ready_{i}", disabled=not ready_ok)
                if CHALISA_NEEDS_PIN:
                    st.text_input("Grown-up PIN", type="password", key=f"ch_pin_{i}")
                st.button(f"🙏 I've learned Part {i + 1}! (+{BEADS_PER_PART} 📿)", key=f"ch_submit_{i}", type="primary",
                          on_click=learn_part, args=(i,),
                          disabled=not (ready_ok and st.session_state.get(f"ch_ready_{i}")))


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
        st.markdown("**✨ Pick any time**")
        fcols = st.columns(3)
        for i, th in enumerate([t for t in THEMES if t.get("free")]):
            fcols[i % 3].button(th["name"] + (" ✔️" if th["id"] == theme_id else ""), key=f"theme_{th['id']}",
                                disabled=th["id"] == theme_id, on_click=set_theme, args=(th["id"],),
                                use_container_width=True)
        st.markdown("**⭐ Star-day themes**")
        tcols = st.columns(3)
        for i, th in enumerate([t for t in THEMES if not t.get("free")]):
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
        cells = "".join(f"<td>{'✅' if t['id'] in done_on(data, d_) else ('⏳' if t['id'] in ticked_on(data, d_) else ('·' if task_on(t, d_) else ''))}</td>"
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
        d.setdefault("earned", {})[d_iso] = task_minutes(new, d_iso)

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


def kid_msg_read(mid):
    def change(d):
        for km in d.get("kid_messages", []):
            if km["id"] == mid:
                km["read"] = True
    update(change)


def kid_msg_reply(mid):
    text = str(st.session_state.get(f"kreply_{mid}", "")).strip()
    if not text:
        return

    def change(d):
        for km in d.get("kid_messages", []):
            if km["id"] == mid:
                km["read"] = True
                km["reply"] = text
        d.setdefault("messages", []).append({"id": uuid.uuid4().hex[:8], "date": TODAY_KEY,
                                             "text": f"↪️ Reply to your message: {text}", "seen": False})

    if update(change):
        st.session_state[f"kreply_{mid}"] = ""
        st.session_state.parent_note = f"↪️ Reply sent — {STUDENT_NAME} will see it as a message."


def delete_feedback(fid):
    def change(d):
        d["task_feedback"] = [f for f in d.get("task_feedback", []) if f["id"] != fid]
    if update(change):
        st.session_state.parent_note = "🗑️ Feedback removed."


def reset_all():
    def change(d):
        d.clear()
        d.update(migrate(default_data(), today))

    if update(change):
        for k in list(st.session_state.keys()):
            if k.startswith(TODAY_KEY) or k.startswith("wear_"):
                del st.session_state[k]
        st.session_state.flash = "All progress reset."


if IS_PARENT:
    st.session_state.parent_ok = True          # signed in as the grown-up: no PIN needed
    st.session_state.parent_ok_at = datetime.now().timestamp()
elif st.session_state.get("parent_ok") and \
        datetime.now().timestamp() - st.session_state.get("parent_ok_at", 0) > PARENT_AUTOLOCK_MINUTES * 60:
    st.session_state.parent_ok = False     # auto-lock

with tab_parent:
    unread_kid = [km for km in data.get("kid_messages", []) if not km.get("read")]
    if not st.session_state.get("parent_ok"):
        if unread_kid:
            st.info(f"📨 {len(unread_kid)} new message{'s' if len(unread_kid) != 1 else ''} from {STUDENT_NAME} — "
                    "enter the PIN to read.")
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
        if not IS_PARENT:
            st.caption(f"🔒 This page locks itself after {PARENT_AUTOLOCK_MINUTES} minutes.")

        kms = data.get("kid_messages", [])
        st.markdown(f"#### 📨 Messages from {STUDENT_NAME}" + (f" ({len(unread_kid)} new)" if unread_kid else ""))
        ecfg = email_cfg()
        if ecfg:
            ec1, ec2 = st.columns([3, 1])
            ec1.caption(f"📧 Email alerts are ON — new messages are emailed to {', '.join(ecfg['to'])}.")
            ec2.button("Send test 📧", on_click=send_test_email, key="email_test")
        else:
            st.caption("📧 Email alerts are off. Add an [email] section to the app's Secrets to get messages by email.")
        if not kms:
            st.caption(f"No messages yet. {STUDENT_NAME} can send one from the bottom of her Today page.")
        for km in reversed(kms[-10:]):
            with st.container(border=True):
                st.markdown(f"{'🆕 ' if not km.get('read') else ''}**{km['date']} {km.get('time', '')}** — {md_safe(km['text'])}")
                if km.get("reply"):
                    st.caption(f"↪️ You replied: {km['reply']}")
                else:
                    r1, r2 = st.columns([3, 1])
                    r1.text_input("Reply", key=f"kreply_{km['id']}", label_visibility="collapsed",
                                  placeholder="Write a reply…")
                    r2.button("Reply ↪️", key=f"kreply_btn_{km['id']}", on_click=kid_msg_reply, args=(km["id"],))
                    if not km.get("read"):
                        st.button("Mark as read 👀", key=f"kread_{km['id']}", on_click=kid_msg_read, args=(km["id"],))

        st.markdown("#### 💬 Give feedback on a task")
        fb_days = [today - timedelta(days=i) for i in range(8)]
        st.selectbox("Day", fb_days, key="gfb_day", format_func=lambda x: x.strftime("%A %d %b"))
        feedback_form("gfb", st.session_state.get("gfb_day", today).isoformat(), False)
        fbs = data.get("task_feedback", [])
        if fbs:
            with st.expander(f"Feedback given ({len(fbs)})"):
                for f in reversed(fbs[-20:]):
                    c1, c2 = st.columns([5, 1])
                    c1.markdown(f"• {f['date']} · {FB_TASK_NAME.get(f['task'], f['task'])} {FB_STARS.get(f.get('stars', 0), '')}: "
                                f"{md_safe(f.get('text', ''))} {'✅ seen' if f.get('seen') else '🕒 not seen yet'}")
                    c2.button("🗑️", key=f"fbdel_{f['id']}", on_click=delete_feedback, args=(f["id"],))

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
        st.text_area("Message", key="parent_msg", placeholder=f"So proud of your maths today, {STUDENT_NAME}! 💖", height=80)
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

        chd = data.get("chalisa", {})
        if SHOW_CHALISA:
            st.markdown("#### 🙏 Hanuman Chalisa")
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
        if SHOW_MINDFUL:
            st.markdown("#### 🫙 Gratitude jar")
            _gl = data.get("gratitude", [])
            if _gl:
                for g in reversed(_gl[-15:]):
                    st.write(f"🙏 {date.fromisoformat(g['date']).strftime('%a %d %b')}: {md_safe(g['text'])}")
            else:
                st.caption("No thankful notes yet — they're written in the 🧘 Calm corner.")

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

        if SHOW_TAMIL:
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

        if CHAT_ON:
            st.markdown("#### 💬 The girls' chat")
            st.caption(f"Everything {STUDENT_NAME} and {CHAT_FRIEND} write to each other. Both families' grown-ups "
                       "can read it and remove a message if needed.")
            try:
                _cm, _ = chat_load()
            except Exception:
                _cm = []
            if not _cm:
                st.caption("No chat messages yet.")
            for m in reversed(_cm[-40:]):
                c1, c2 = st.columns([6, 1])
                c1.markdown(f"**{md_safe(m['name'])}** · {m['time'][5:16].replace('T', ' ')} — {md_safe(m['text'])}")
                c2.button("🗑️", key=f"chdel_{m['id']}", on_click=chat_delete, args=(m["id"],), help="Remove this message")
        if not IS_PARENT and st.button("🔒 Lock"):
            st.session_state.parent_ok = False
            st.rerun()


# ==================================== CHAT ====================================
if tab_chat is not None:
    with tab_chat:
        st.markdown(f"### 💬 Chat with {CHAT_FRIEND}" if not IS_PARENT else "### 💬 The girls' chat")
        st.markdown('<style>.chatbox{display:flex;flex-direction:column;gap:6px;max-height:420px;overflow-y:auto;'
                    'padding:8px;background:rgba(255,255,255,.85);border-radius:18px;border:2px solid #ffd1e8}'
                    '.cb{max-width:78%;padding:8px 12px;border-radius:16px;font-size:1.02rem;color:#3b2350;line-height:1.35}'
                    '.cb.me{align-self:flex-end;background:#ffe0f0;border-bottom-right-radius:4px}'
                    '.cb.them{align-self:flex-start;background:#e6f3ff;border-bottom-left-radius:4px}'
                    '.cn{font-size:.75rem;color:#8a6a96;margin-bottom:2px}</style>', unsafe_allow_html=True)
        if IS_PARENT:
            st.caption("Grown-ups can read the chat here. To remove a message, use the 💬 section in the 🔐 Grown-ups tab.")
        else:
            st.markdown(f'<div class="tip" style="margin-left:0">💖 Chat about homework, school, books and fun stuff. '
                        f'Be kind — grown-ups from both families can read this chat.</div>', unsafe_allow_html=True)
        if hasattr(st, "fragment"):
            st.fragment(run_every=15)(chat_view)()     # refreshes by itself every 15 seconds
        else:
            chat_view()
        if not IS_PARENT:
            with st.form("chat_form", clear_on_submit=False, border=False):
                cc1, cc2 = st.columns([5, 1])
                cc1.text_input("Message", key="chat_in", max_chars=CHAT_MAX, label_visibility="collapsed",
                               placeholder=f"Write to {CHAT_FRIEND}…")
                cc2.form_submit_button("Send 📨", on_click=chat_send, use_container_width=True)
        if err := st.session_state.pop("chat_err", None):
            st.error(err)
        st.button("🔄 Refresh chat", key="chat_refresh")




# ================================== MY CHARACTERS ==================================
def adopt_drawing(val):
    if val and isinstance(val, dict) and val.get("img") and val.get("n") != st.session_state.get("char_draft_n"):
        st.session_state.char_draft_n = val["n"]
        if len(val["img"]) > 400_000:
            st.session_state.char_note = ("warn", "That drawing is too big to save — try a smaller drawing. 🙏")
        else:
            st.session_state.char_draft = val


def save_character():
    draft = st.session_state.get("char_draft")
    name = " ".join(str(st.session_state.get("ch_name", "")).split())[:24]
    says = [" ".join(x.split())[:90] for x in str(st.session_state.get("ch_says", "")).splitlines() if x.strip()][:6]
    if not draft:
        st.session_state.char_note = ("warn", "First draw your character and press ✅ Use this drawing.")
        return
    if not name:
        st.session_state.char_note = ("warn", "Give your character a name! ✨")
        return
    if not says:
        says = [f"Hi {STUDENT_NAME}! I'm {name}! 👋"]
    ch = {"id": uuid.uuid4().hex[:8], "name": name, "img": draft["img"], "says": says,
          "move": st.session_state.get("ch_move", "hop"), "voice": st.session_state.get("ch_voice", "sweet"),
          "show": True, "made": TODAY_KEY}
    pos = {}

    def change(chars):
        if len(chars) >= CHARS_MAX:
            st.session_state.char_err = f"You can have up to {CHARS_MAX} characters. Delete one to make room. 🙂"
            return False
        chars.append(ch)
        pos["i"] = len(chars) - 1
    if chars_change(change):
        st.session_state.char_note = ("ok", f"🎉 {name} is alive! Watch — {name} is coming to say hello!")
        st.session_state.char_visit = pos["i"]
        st.session_state.pop("char_draft", None)
        st.session_state.pad_gen = st.session_state.get("pad_gen", 0) + 1
        st.session_state.ch_name = ""
        st.session_state.ch_says = ""
        st.session_state.sound_next = "chime"


def char_toggle(cid):
    def change(chars):
        for c in chars:
            if c["id"] == cid:
                c["show"] = not c.get("show", True)
    chars_change(change)


def char_delete(cid):
    def change(chars):
        chars[:] = [c for c in chars if c["id"] != cid]
    chars_change(change)


def char_visit(i):
    st.session_state.char_visit = i


def set_char_voice():
    on = bool(st.session_state.get("char_voice_on", True))

    def change(d):
        d["char_voice"] = on
    update(change)


with tab_chars:
    st.markdown('<div class="calm-hero" style="background:linear-gradient(135deg,#fff2e0,#ffe6f3 50%,#ecf0ff)">'
                '<div class="ch-title" style="color:#c2410c">🎨 My Characters</div>'
                '<div class="ch-sub">Draw a character with your Apple Pencil — it will come alive, fly around and talk to you!'
                '</div></div>', unsafe_allow_html=True)
    if err := st.session_state.pop("char_err", None):
        st.error(err)
    if note := st.session_state.pop("char_note", None):
        (st.success if note[0] == "ok" else st.warning)(note[1])
    _chars = chars_load()
    with st.container(border=True):
        st.markdown('<div class="calm-h">✏️ 1. Draw your character</div>'
                    '<div class="calm-s">Fill the space with a big, colourful drawing. Then press <b>✅ Use this drawing</b>.'
                    '</div>', unsafe_allow_html=True)
        adopt_drawing(draw_pad(f"drawpad_{st.session_state.get('pad_gen', 0)}"))
    with st.container(border=True):
        st.markdown('<div class="calm-h">💬 2. Bring it to life</div>', unsafe_allow_html=True)
        _draft = st.session_state.get("char_draft")
        if _draft:
            st.markdown(f'<div class="char-prev"><img src="{_draft["img"]}"></div>', unsafe_allow_html=True)
        else:
            st.caption("Your drawing will appear here after you press ✅ Use this drawing.")
        st.text_input("Name", key="ch_name", max_chars=24, placeholder="e.g. Sparkle the Star")
        st.text_area("Things it says (one per line)", key="ch_says", height=110,
                     placeholder=f"Hi {STUDENT_NAME}! You're amazing!\nLet's do some maths!\nI love rainbows! 🌈")
        _c1, _c2 = st.columns(2)
        _c1.selectbox("How it moves", list(CHAR_MOVES), format_func=CHAR_MOVES.get, key="ch_move")
        _c2.selectbox("Its voice", list(CHAR_VOICES), format_func=lambda k: CHAR_VOICES[k][0], key="ch_voice", index=1)
        st.button("✨ Make it come alive!", key="char_save", on_click=save_character, type="primary",
                  use_container_width=True, disabled=len(_chars) >= CHARS_MAX)

    st.markdown(f"### 🧸 My characters ({len(_chars)}/{CHARS_MAX})")
    st.checkbox("🔊 My characters talk out loud", key="char_voice_on", value=data.get("char_voice", True),
                on_change=set_char_voice)
    if not _chars:
        st.caption("No characters yet — draw your first one above! 🎨")
    for _i, _c in enumerate(_chars):
        with st.container(border=True):
            _a, _b = st.columns([1, 2])
            _a.markdown(f'<div class="char-prev small"><img src="{_c["img"]}"></div>', unsafe_allow_html=True)
            with _b:
                st.markdown(f'<div class="calm-h">{html_safe(_c["name"])}{"" if _c.get("show", True) else " 🙈"}</div>'
                            f'<div class="calm-s">{CHAR_MOVES.get(_c.get("move"), "")} · '
                            f'{CHAR_VOICES.get(_c.get("voice"), CHAR_VOICES["sweet"])[0]} voice</div>'
                            + "".join(f'<div class="char-say">💬 {html_safe(x)}</div>' for x in _c.get("says", [])),
                            unsafe_allow_html=True)
                _x1, _x2, _x3 = st.columns(3)
                _x1.button("👋 Visit now", key=f"cv_{_c['id']}", on_click=char_visit, args=(_i,), use_container_width=True)
                _x2.button("🙈 Hide" if _c.get("show", True) else "👀 Show", key=f"ct_{_c['id']}", on_click=char_toggle,
                           args=(_c["id"],), use_container_width=True)
                with _x3.popover("🗑️ Delete", use_container_width=True):
                    st.write(f"Delete **{md_safe(_c['name'])}**?")
                    st.button("Yes, delete", key=f"cd_{_c['id']}", on_click=char_delete, args=(_c["id"],))

# ================================== CALM CORNER (Andal only) ==================================
def calm_mood(mid):
    def change(d):
        d.setdefault("moods", []).append({"date": TODAY_KEY, "time": datetime.now(ZoneInfo(TIMEZONE)).strftime("%H:%M"),
                                          "mood": mid})
    if update(change):
        st.session_state.calm_mood_reply = mid


def save_gratitude():
    items = [" ".join(str(st.session_state.get(f"gr_{i}", "")).split())[:140] for i in range(3)]
    items = [x for x in items if x]
    if not items:
        st.session_state.gr_note = ("warn", "Write at least one thing you're thankful for 💗")
        return

    def change(d):
        d.setdefault("gratitude", []).extend({"date": TODAY_KEY, "text": x} for x in items)
        d["gratitude"] = d["gratitude"][-400:]
    if update(change):
        st.session_state.gr_note = ("ok", f"🫙 {len(items)} thankful note{'s' if len(items) > 1 else ''} "
                                          "went into your jar! A thankful heart is a happy heart 💖")
        st.session_state.sound_next = "chime"


def angel_now():
    st.session_state.angel_now = True


def more_i_am():
    st.session_state.i_am_shift = st.session_state.get("i_am_shift", 0) + 3


if tab_calm is not None:
    with tab_calm:
        _d = today.toordinal()
        st.markdown(f'<div class="calm-hero"><div class="ch-title">🧘 {html_safe(STUDENT_NAME)}\'s Calm Corner</div>'
                    '<div class="ch-sub">A quiet, cosy place to breathe, notice your feelings and say thank you 💗</div>'
                    '</div>', unsafe_allow_html=True)

        # ---- angel message of the day ----
        _aw = ANGEL_WORDS[(_d * 7) % len(ANGEL_WORDS)].format(name=STUDENT_NAME)
        st.markdown(f'<div class="angel-card"><div class="ac-wing">👼</div><div class="ac-head">Today\'s angel message'
                    f'</div><div class="ac-text">{html_safe(_aw)}</div></div>', unsafe_allow_html=True)
        st.button("👼 Call an angel to visit me", key="call_angel", on_click=angel_now, use_container_width=True)
        if st.session_state.pop("angel_now", False) and ANGELS_ON:
            call_angel_now()

        # ---- feelings ----
        with st.container(border=True):
            st.markdown('<div class="calm-h">💗 How am I feeling?</div>'
                        '<div class="calm-s">All feelings are okay. Tap the one that fits you right now.</div>',
                        unsafe_allow_html=True)
            _fc = st.columns(4)
            for _i, (mid, emo, label, _r) in enumerate(MOODS):
                _fc[_i % 4].button(f"{emo} {label}", key=f"calm_mood_{mid}", on_click=calm_mood, args=(mid,),
                                   use_container_width=True)
            _fr = st.session_state.pop("calm_mood_reply", None)
            if _fr:
                _m = next(m for m in MOODS if m[0] == _fr)
                _tips = "".join(f"<li>{html_safe(t)}</li>" for t in FEELING_HELP.get(_fr, []))
                st.markdown(f'<div class="feel-card"><div class="fc-big">{_m[1]}</div><div><b>You feel '
                            f'{_m[2].lower()}.</b> {html_safe(_m[3])}<ul>{_tips}</ul></div></div>',
                            unsafe_allow_html=True)

        # ---- breathing bubble ----
        with st.container(border=True):
            st.markdown('<div class="calm-h">🫧 Breathe with me</div>'
                        '<div class="calm-s">Pick a breath, press start, and follow the bubble.</div>',
                        unsafe_allow_html=True)
            _bs = st.radio("Breathing style", list(BREATH_STYLES), horizontal=True, key="breath_style",
                           label_visibility="collapsed")
            _embed(breath_html(_bs), 360)

        # ---- gratitude jar ----
        with st.container(border=True):
            st.markdown('<div class="calm-h">🫙 My gratitude jar</div>'
                        '<div class="calm-s">Write up to 3 things you are thankful for today.</div>',
                        unsafe_allow_html=True)
            _gp = [GRATITUDE_PROMPTS[(_d + k * 5) % len(GRATITUDE_PROMPTS)] for k in range(3)]
            with st.form("gratitude", clear_on_submit=True, border=False):
                for _i in range(3):
                    st.text_input(f"Thankful {_i + 1}", key=f"gr_{_i}", max_chars=140, label_visibility="collapsed",
                                  placeholder=f"🙏 I'm thankful for {_gp[_i]}…")
                st.form_submit_button("💖 Put them in my jar", on_click=save_gratitude, use_container_width=True)
            if _gn := st.session_state.pop("gr_note", None):
                (st.success if _gn[0] == "ok" else st.warning)(_gn[1])
            _grat = data.get("gratitude", [])
            if _grat:
                _cols = ["#ffe3f1", "#e8e1ff", "#dff4ff", "#fff3c4", "#dcf8e2", "#ffe6d6"]
                _notes = "".join(
                    f'<div class="gnote" style="background:{_cols[k % len(_cols)]};transform:rotate({(k % 5) - 2}deg)">'
                    f'{html_safe(g["text"])}<span>{date.fromisoformat(g["date"]).strftime("%d %b")}</span></div>'
                    for k, g in enumerate(reversed(_grat[-12:])))
                st.markdown(f'<div class="calm-s" style="margin-top:6px">✨ <b>{len(_grat)}</b> thankful note{"" if len(_grat) == 1 else "s"} '
                            f'in your jar so far!</div><div class="gjar">{_notes}</div>', unsafe_allow_html=True)

        # ---- I am... ----
        with st.container(border=True):
            st.markdown('<div class="calm-h">🌟 Say it out loud: I am…</div>'
                        '<div class="calm-s">Read each one in a strong, proud voice.</div>', unsafe_allow_html=True)
            _sh = st.session_state.get("i_am_shift", 0)
            _ia = [I_AM[(_d * 3 + _sh + k) % len(I_AM)] for k in range(3)]
            st.markdown('<div class="iam-row">' + "".join(f'<div class="iam">{html_safe(x)}</div>' for x in _ia)
                        + '</div>', unsafe_allow_html=True)
            st.button("🔄 Show me 3 more", key="iam_more", on_click=more_i_am)

        # ---- calm idea + mindful quote + kindness mission ----
        _ct = CALM_TIPS[_d % len(CALM_TIPS)]
        _mq = MINDFUL_QUOTES[(_d * 5) % len(MINDFUL_QUOTES)]
        st.markdown(
            f'<div class="calm-grid"><div class="cg cg1"><div class="cg-h">🌿 Calm idea for today</div>'
            f'<div class="cg-t"><b>{html_safe(_ct[0])}</b><br>{html_safe(_ct[1])}</div></div>'
            f'<div class="cg cg2"><div class="cg-h">💛 Kindness mission</div>'
            f'<div class="cg-t">{html_safe(KIND_IDEAS[_d % len(KIND_IDEAS)])}</div></div></div>'
            f'<div class="quote"><div class="qmark">“</div><div class="qtext">{html_safe(_mq[0])}</div>'
            f'<div class="qwho">— {html_safe(_mq[1])}, <span>{html_safe(_mq[2])}</span></div>'
            f'<div class="qmean">💡 {html_safe(_mq[3])}</div></div>', unsafe_allow_html=True)

        with st.expander("👀 The 5-4-3-2-1 senses game (for worried or busy feelings)"):
            st.markdown("Look around you and find:\n\n"
                        "- 👀 **5** things you can **see**\n- ✋ **4** things you can **touch**\n"
                        "- 👂 **3** things you can **hear**\n- 👃 **2** things you can **smell**\n"
                        "- 👅 **1** thing you can **taste**\n\nWell done — you brought your mind back to right now. 🌈")
        with st.expander("🧰 My calm-down toolbox"):
            st.markdown("When feelings get really big, try one of these:\n\n"
                        + "\n".join(f"- **{t[0]}** — {t[1]}" for t in CALM_TIPS[:8]))

# ---- hopping friends (purely decorative, never block taps) ----
if ANIMATED_FRIENDS:
    install_visitors()
if _snd := st.session_state.pop("sound_next", None):
    play_sound(_snd)
# ---- my drawn characters + must-do reminders (kids only) ----
if not IS_PARENT:
    _chars_all = chars_load()
    _chash = hashlib.md5(json.dumps([[c["id"], c["name"], c.get("show", True), c.get("move"), c.get("voice"),
                                      c.get("says")] for c in _chars_all]).encode()).hexdigest()
    sync_floaters(_chars_all, build_reminders(today, set(data["days"].get(TODAY_KEY, [])), REQ_TODAY),
                  data.get("char_voice", True), st.session_state.get("chars_sent") != _chash)
    st.session_state.chars_sent = _chash
if (_cv := st.session_state.pop("char_visit", None)) is not None:
    char_visit_now(_cv)
# ---- angels with kind words (Andal only) ----
if ANGELS_ON and not IS_PARENT:
    install_angels([w.format(name=STUDENT_NAME) for w in ANGEL_WORDS])
