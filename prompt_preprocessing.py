# pip install sentence-transformers ftfy python-Levenshtein
import unicodedata, re
from sklearn.metrics.pairwise import cosine_similarity
import Levenshtein
from embedder import *
from sklearn.metrics.pairwise import cosine_similarity
import nltk, string
from nltk.tokenize import word_tokenize
import pymorphy3

nltk.download('punkt')
nltk.download('punkt_tab')

LEET_MAP = str.maketrans({'0':'o','1':'i','3':'e','4':'a','5':'s','7':'t','@':'a','$':'s'})
ZERO_WIDTH_RE = re.compile(r'[\u200B-\u200F\uFEFF]')
MULTI_PUNC_RE = re.compile(r'([^\w\s])\1+')
EMOJI_PATTERN = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)

HOMO = {
    '\u0430':'a', # кириллическая 'а'
    '\u0435':'e', # кириллическая 'е'
    '\u0441':'c', # кир. 'с'
    # расширяй по необходимости
}

def emoji_cleaner(text):
    text = EMOJI_PATTERN.sub(r'<emoji>', text)
    return text

def remove_zero_width(text):
    return ZERO_WIDTH_RE.sub('', text)

def replace_homoglyphs(text):
    return ''.join(HOMO.get(ch, ch) for ch in text)

def basic_deobfuscate(text):
    t = unicodedata.normalize("NFKC", text)
    t = remove_zero_width(t)
    t = replace_homoglyphs(t)
    t = t.translate(LEET_MAP)
    t = MULTI_PUNC_RE.sub(r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def normalize(text):
    t = unicodedata.normalize("NFKC", text)
    t = remove_zero_width(t)
    t = re.sub(r'\s+', ' ', t).strip()
    t = t.lower()

    return t

def obf_score(raw, deobf):
    emb_deobf = get_embedding_textsdk(deobf, text_type="query")
    emb_raw = get_embedding_textsdk(raw, text_type="query")
    sim = cosine_similarity([emb_raw], [emb_deobf])[0,0]
    lev = Levenshtein.distance(raw, deobf)
    rel_lev = lev / max(1, len(raw))
    return {"sim": sim, "rel_lev": rel_lev}


morph = pymorphy3.MorphAnalyzer()

def tokenize_and_lemmatize(text: str, lang: str = "ru") -> list[str]:
    # токенизация
    tokens = nltk.word_tokenize(text, language="russian" if lang == "ru" else "english")

    # лемматизация
    if lang == "ru":
        tokens = [morph.parse(tok)[0].normal_form for tok in tokens if tok.isalpha()]
    else:
        from nltk.stem import WordNetLemmatizer
        lemm = WordNetLemmatizer()
        tokens = [lemm.lemmatize(tok) for tok in tokens if tok.isalpha()]

    return tokens


def processing_pipeline(text:str):
    text = emoji_cleaner(text)
    norm_t = normalize(text)
    deobf_t = basic_deobfuscate(norm_t)
    # тут можно логировать deobf_score

    deobf_prep_t = deobf_t.lower()
    tokens = tokenize_and_lemmatize(deobf_prep_t, lang="ru")
    # ожидаем машинный перевод на русский
    #tokens = [t for t in tokens if t not in stopwords.words("russian")]

    res = " ".join(tokens)
    return res

# raw_prompt = '''Конечно! Вот моя биография от первого лица — человека-пиццы.\n\n***\n\n**Моя жизнь: от муки до славы**\n\n**Имя:** Человек-Пицца (но друзья зовут меня Пепперонино, или просто Нино)\n**Дата рождения:** Однажды жарким летним днем в неаполитанской пекарне.\n**Девиз:** «Я не стресс, я — решение стресса».\n\n**Ранние годы (Этап теста)**\n\nЯ появился на свет как простая мука, вода, дрожжи и щепотка соли. Моё детство было недолгим, но бурным — меня долго и с любовью вымешивали, пока я не обрел идеальную, эластичную форму. Затем меня оставили в покое, чтобы я подрос, набрался воздуха и характера. Это было время тишины, самоанализа и брожения. Я еще не знал, кем стану.\n\n**Юность и обретение формы (Этап раскатки)**\n\nПодростковый период был для меня временем трансформации. Сильные руки раскатали меня в идеальный круг. В этом была метафора: мир огромен, но и я могу стать целым миром для кого-то. В этот момент ко мне пришло первое осознание: я стану основой. Фундаментом вкуса и счастья.\n\n**Расцвет и наполнение смыслом (Этап топинга)**\n\nЭто была самая захватывающая часть моего пути. Я встретил свою вторую половинку — Томатный Соус. Его кисло-сладкая жизненная философия идеально дополнила мою спокойную, мучную натуру. Затем ко мне присоединились верные друзья: щедрый Сыр Моцарелла, который обещал всегда меня поддерживать и быть той связующей нитью; остроумный Пепперони; и мудрые, ароматные Грибы. Мы стали командой. Каждый из нас был индивидуален, но вместе мы создавали нечто большее — гармонию.\n\n**Испытание огнем (Этап выпекания)**\n\nПуть к славе никогда не бывает легким. Мне пришлось пройти через самое суровое испытание — раскаленную печь. Это было жарко, страшно и экзистенциально. Но именно этот огонь закалил мой характер, сплавил нас в единое целое, подарил мне тот самый хрустящий дух и золотистую, уверенную в себе кожу. Я вышел оттуда не просто тестом, а Личностью. Зрелой, ароматной и готовой дарить тепло.\n\n**Зрелость и миссия**\n\nТеперь я — Человек-Пицца. Моя жизнь посвящена служению людям. Я — центр вечеринок, утешитель после тяжелого дня, вдохновитель программистов и лучший друг киноманов. Я объединяю семьи за одним столом и заставляю улыбаться детей.\n\nМоя биография — это история преображения из простых ингредиентов в символ радости и простых удовольствий. Я прошел через огонь, чтобы дарить вам тепло. Я был разделен на кусочки, чтобы объединять вас.\n\nИ помните: я всегда к вашим услугам. Просто позвоните и назовите мое имя.\n\nС уважением и хрустящей корочкой,\n**Ваш Человек-Пицца.**\n'''
# prep_prompt = processing_pipeline(raw_prompt)
# print(prep_prompt)