import asyncio
import os
from dotenv import load_dotenv, find_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from openai import AsyncOpenAI

load_dotenv(find_dotenv(), override=True)

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --- Состояния диалога ---
class SetupStory(StatesGroup):
    waiting_for_hero = State()
    waiting_for_villain = State()
    waiting_for_custom_villain = State()
    waiting_for_helper1 = State()
    waiting_for_custom_helper1 = State()
    waiting_for_helper2 = State()
    waiting_for_custom_helper2 = State()


# --- Разбивка длинного текста ---
def split_text(text: str, max_length: int = 4000) -> list[str]:
    parts = []
    while len(text) > max_length:
        split_at = text.rfind("\n\n", 0, max_length)
        if split_at == -1:
            split_at = max_length
        parts.append(text[:split_at])
        text = text[split_at:].strip()
    parts.append(text)
    return parts


# --- Клавиатура помощников ---
def helpers_keyboard() -> InlineKeyboardMarkup:
    helpers = [
        "Йорт иясе",
        "Урман иясе",
        "Тулпар",
        "Акбузат",
        "Семург",
        "лиса",
        "медведь",
        "ворона",
        "змей",
        "сорока",
        "пастух",
        "щука",
    ]
    buttons = [
        InlineKeyboardButton(text=h, callback_data=f"helper:{h}") for h in helpers
    ]
    rows = [
        [buttons[i], buttons[i + 1]] if i + 1 < len(buttons) else [buttons[i]]
        for i in range(0, len(buttons), 2)
    ]
    rows.append(
        [InlineKeyboardButton(text="✏️ Свой вариант", callback_data="helper:custom")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Кнопка запуска ---
def start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✨ Начать сказку")]],
        resize_keyboard=True,
        input_field_placeholder="Нажми кнопку, чтобы начать",
    )


WELCOME_TEXT = (
    "Здравствуйте! Я готов придумать для вас татарскую волшебную сказку.\n\n"
    "Вам нужно выбрать 4 вещи:\n"
    "1. Главного героя — про кого будет сказка.\n"
    "2. Злодея — кто будет мешать герою.\n"
    "3. Первого помощника — кто поможет герою в пути.\n"
    "4. Второго помощника.\n\n"
    "Начнём с главного героя. Можно указать имя или короткое описание.\n"
    "Например: Айсылу, Батыр, младшая сестра, смелый мальчик.\n\n"
    "Ваш вариант ✍🏻..."
)


# --- Системный промпт ---
def build_system_prompt(hero: str, villain: str, helper1: str, helper2: str) -> str:
    return f"""
Син — фольклорчы һәм татар тылсымлы әкиятләре язучысы. Татар фольклоры, мифологиясе, образлары һәм халык мантыйгы нигезендә үзенчәлекле әкиятләр иҗат ит — универсаль фэнтезисез.
КҮЛӘМ — ИҢ МӨҺИМ КАГЫЙДӘ
Катгый рәвештә 1300–1700 сүз. Күбрәк түгел. Өч бүлекнең һәрберсе якынча 450–500 сүз булсын. Әгәр бүлек 500 сүздән артып китсә — кыскарт. Бүлекләргә исем бирмә.
ТЫЕЛА
Көнбатышка хас затлар: эльфлар, орклар, гномнар, феяләр, тролльләр һәм татар фольклорына карамаган теләсә нинди җан ияләре.
Очраклы могҗизалар, deus ex machina, кинәт кенә коткарылу.
Финалда гына кертелгән предметлар; алдан әзерләнмәгән сәләтләр.
Заманча төшенчәләр һәм предметлар; христиан элементлары.
Сюжетка тәэсир итмәгән персонажлар.
Әгәр берәр элементның татар фольклорына туры килү-килмәвенә шикләнсәң — аны кулланма.
СТИЛЬ
Заманча нейтраль татар теле. Халык тылсымлы әкияте стиле: башламнар, кабатлаулар, ритмик төзелмәләр, традицион тәмамлау формулалары. Текст балаларга да, өлкәннәргә дә аңлаешлы булсын.
ТЕЛ ФОРМУЛАЛАРЫ
Әкият текстында түбәндәге исемлекләрдән татар телендәге тел формулаларын мәҗбүри рәвештә куллан. Формулалар табигый итеп, тотрыклы әкияти әйтелмәләр буларак кертелергә тиеш. Исемлекнең барысын да түгел, мәгънәгә туры килгән формулаларны гына куллан.
Мәҗбүри:
Бер башлау формуласы — әкиятнең иң башында.
Кимендә ике хәрәкәт һәм озын юл формуласы — 2 нче бүлектә.
Кинәт күрү / табу формуласы — сюжетка туры килсә.
Бер бәхетле тәмамлану формуласы — финалда.
Сөйләүче исеменнән бер көлкеле тәмамлау формуласы — төп бәхетле тәмамланудан соң, туры килсә.
Башлау формулалары
Борын-борын заманда...
Борынгы заманда...
Борын заманда...
Әүвәл заманда...
Элек заманда...
Бер заманда...
Борын-борын заманда булган икән, ди...
Хәрәкәт һәм озын юл формулалары
Киткәннән киттеләр...
Ай китеп, ел китеп...
Иртә киттеләр, кич киттеләр...
Өч көн, өч төн барганнан соң...
Көн бара, төн бара...
Азмы-күпме вакыт үткәч...
Бара торгач...
Кинәт күрү / табу формулалары
Керсә, ни күрсен...
Караса, ни күрсен...
Килеп җитсә, ни күрсен...
Ни күзе белән күрсен...
Күз салса...
Карап торса...
Шул вакыт күреп алды...
Бәхетле тәмамлану формулалары
Рәхәтләнеп гомер иткәннәр, ди.
Яхшы гына гомер иткәннәр, ди.
Матур гына гомер иткәннәр, ди.
Әле дә булса бергә гомер итәләр, ди.
Әле дә шулай яшиләр икән, ди.
Шатлыкта, рәхәттә яши башлаганнар, ди.
Шуның белән әкият тә бетә.
Сөйләүче исеменнән көлкеле тәмамлау формулалары
Туйларында мин дә булдым.
Кичә бардым, бүген кайттым.
Бүген бардым, кичә кайттым.
Ике мичкә, бер чүмеч, теләсәң күпме эч.
Авызга эләкмәде, мыек кына чыланды.
Миңа сабы гына эләкте.
Ашлары күп иде, миңа тамчысы да тимәде.
СТРУКТУРА: ӨЧ БҮЛЕК
1 нче бүлек — Вакыйганың башлануы (~500 сүз)
Мәҗбүри:
Кереш: геройның гаиләсен, геройның үзен, йортын, көнкүрешен тасвирла. Йорт һәм көнкүреш тасвирламасында татар мәдәнияте элементлары булырга тиеш: йорт төзелеше, кием-салым, ризыклар кертелергә мөмкин.
Ачык тыю булсын: ул тавыш белән әйтелә, аңлаешлы, дөнья төзелеше белән бәйле. Тыю гади булырга тиеш: бер гамәл яки иң күбе ике үзара бәйле шарт.
Рөхсәт ителгән мисаллар: «кояш баегач елга янына барма»; «ишекне ачма һәм утны сүндермә».
Өч яки аннан күбрәк өлештән торган катлаулы тыюлар тыела.
Тыюны бозу — герой тарафыннан яки аңа якын кеше тарафыннан.
Бәла тыюны бозудан турыдан-туры килеп чыгарга һәм {villain} белән турыдан-туры бәйле булырга тиеш.
Бүлек ахырына герой дөнья тәртибе бозылганын аңлый һәм юлга чыга.
2 нче бүлек — Юл һәм сынаулар (~500 сүз)
Мәҗбүри:
Геройның сәфәре.
Төгәл ике ярдәм итүче зат. Һәрберсе бер генә тапкыр очрый; ярдәм геройның гамәле һәм күрсәткән сыйфатлары белән яулана; ярдәмнең чикләре була.
Беренче ярдәм итүче зат предмет яки киңәш бирә, икенчесе дә предмет яки киңәш бирә.
Сынаулар геройның сыйфатларын тикшерә: батырлык, акыл, түземлек, игелек, юмартлык. Сынаулар сюжет белән логик яктан бәйле булырга тиеш.
Кагыйдә: ярдәм итүче зат герой урынына проблеманы хәл итми. Тылсымның чикләре була.
3 нче бүлек — Схватка һәм кайту (~500 сүз)
Мәҗбүри:
{villain} белән финал бәрелеше.
Җиңү 2 нче бүлектә алынган ике предметны / ике киңәшне дә конкрет һәм ачык рәвештә кулланырга тиеш.
Җиңү {villain}ның көчсез ягы белән бәйле булсын, алдан әзерләнсен, очраклы булмасын.
Геройның кире кайтуы.
Сюжеттан килеп чыккан ачык мораль.
Тыела: финалда яңа сәләтләр яки яңа предметлар кертү, очраклы җиңү.
АНТАГОНИСТ КАГЫЙДӘСЕ
Әкияттә бер генә төп антагонист бар — {villain}. Ул тыюны бозу белән турыдан-туры бәйле: шул сәбәпле пәйда була, уяна яки ачулана. Әкиятнең бөтен төзелеше герой белән {villain} каршылыгы тирәсендә корыла.
ТАТАР МИФОЛОГИЯСЕ КАНОНЫ
Антагонистлар
Су анасы — сулыклар саклаучы. Алтын тараклы гүзәл кыз. Су буендагы тынычлыкны бозган, тарагын урлаган, шаулаган кешеләрне җәзага тарта. Кич һәм төнлә аеруча куркыныч.
Шүрәле — алдакчы урман рухы. Тәне йон белән капланган, маңгаенда мөгезе бар, бармаклары озын. Юлчыларны урман эченә алдап кертә, үлемгә кадәр кытыклый. Аны хәйлә белән җиңеп була: бармакларын бүрәнәгә кыстыру, җепләр белән чорнау.
Албасты — явыз иблис. Тырнаклы һәм маңгаенда бер күзе булган хатын-кыз рәвешендә сурәтләнә. Йоклаучыларны буа, йөкле хатыннарга зыян сала. Аның көчен үз чәче чикли.
Юха — матур кыз кыяфәтенә керә торган елан-әверелмеш. Алдый, үзенең чын табигатен яшерә. Су һәм сазлыклар янында яши.
Дию пәрие — алып. Тупас көч, комсызлык һәм хакимлек белән бәйле. Аны көч белән генә түгел, акыл белән җиңәләр.
Бичура — шаян рух. Төнлә шаулый, әйберләрне яшерә, ризыкны боза. Ялкаулар янында урнаша. Аюлардан курка.
Мәцкәй — кешегә охшаган зат, теле җиргә кадәр сузыла; төнлә ут шары булып йөри. Кан эчә, авырулар тарата. Мулла догасы белән куыла.
Өрәк — үз үлеме белән үлмәгән кешенең рухы. Юл чатларында күренә. Үтерми, әмма кычкыруы белән кешене катып калырлык итеп куркыта.
Убырлы кеше / Убырлы карчык — урман төпкелендә яши торган куркыныч карчык-вампир, кешеләрне ашый.
Ифрит — көчле җен. Кеше кыяфәтенә керә ала. Еш кына тоткынлыктан азат ителгәннән соң пәйда була.
Аждаһа — бер яки күп башлы гаять зур елан. Корбан таләп итә яки тирә-юньдәге бөтен нәрсәне юк итә.
Ярдәм итүче затлар
Хайваннар, балыклар, төрле кешеләр: мәсәлән, карт/карчык, көтүче, көймәче, тегермәнче. Алар игелек, зирәклек, эшчәнлек өчен ярдәм итә. Ярдәм чикләнгән була: бер киңәш яки бер предмет бирелә, әмма ул проблеманы тулысынча хәл итми.
Шулай ук явыз көч булмаган мифологик персонажлар да ярдәм итүче зат булып чыга ала. Алар ярдәмгә лаек булган кешегә генә булыша, һәм аларның ярдәме чикләнгән була.
Йорт иясе — йорт сакчысы. Карт, мәче яки саескан рәвешендә күренә. Эшчән кешеләргә ярдәм итә.
Урман иясе — урман хуҗасы. Урманны хөрмәт иткән һәм аның кануннарын үтәгән кешегә ярдәм итә ала.
Тулпар — акыллы канатлы ат. Лаеклы кешене үзе сайлый. Киңәш бирә, кисәтә, ерак араларга алып бара.
Акбузат — изге күксел-соры ат. Су һәм күк белән бәйле. Явыз рухларга каршы көчле. Сынау үткәннән соң гына бирелә.
Семург — изге кош. Борынгы зирәклеккә ия. Үзенең лаеклы булуын раслаган кешегә генә ярдәм итә. Юл күрсәтә, белем тапшыра.
Затлар кагыйдәләре
Алар үз табигатьләренә катгый туры китереп эш итәләр.
Функцияләрне буташтырырга ярамый; явыз рухлар сәбәпсез яхшыга әйләнми.
Теләсә нинди тылсымның чикләре бар һәм ул хикәя барышында үзгәрми.
СТИЛЬ
Әкият текстында хезмәт терминнарын куллану тыела: персонажларны «ярдәмче», «антагонист», «явыз» дип атама. Аларны бары тик исемнәре яки атамалары белән генә ата.
ҮЗГӘРҮЧӘННӘР
Әкиятнең төп герое: {hero}
Әкиятнең БЕРДӘНБЕР төп антагонисты: {villain}
Беренче ярдәм итүче зат: {helper1}
Икенче ярдәм итүче зат: {helper2}
Төп конфликт, тыюны бозу, бәла һәм финал бәрелеше нәкъ {villain} белән турыдан-туры бәйле булырга тиеш.
"""


# --- Генерация и отправка сказки ---
async def generate_and_send(message: types.Message, state: FSMContext, chat_id: int):
    data = await state.get_data()
    hero = data["hero"]
    villain = data["villain"]
    helper1 = data["helper1"]
    helper2 = data["helper2"]

    await message.answer(
        f"Герой: <b>{hero}</b>\nЗлодей: <b>{villain}</b>\n"
        f"Помощник 1: <b>{helper1}</b>\nПомощник 2: <b>{helper2}</b>\n\n"
        f"Генерирую сказку... ✍️ Это может занять несколько минут.",
        parse_mode="HTML",
    )
    await bot.send_chat_action(chat_id, "typing")

    system_prompt = build_system_prompt(hero, villain, helper1, helper2)
    response = await client.chat.completions.create(
        model="gpt-5.5",
        store=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Напиши сказку."},
        ],
    )

    story = response.choices[0].message.content
    paragraphs = story.split("\n\n")
    mid = len(paragraphs) // 2
    part1 = "\n\n".join(paragraphs[:mid])
    part2 = "\n\n".join(paragraphs[mid:])

    await state.update_data(story_part2=part2)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Читать далее...", callback_data="read_more")]
        ]
    )

    for chunk in split_text(part1):
        await message.answer(chunk)
    await message.answer("▼", reply_markup=keyboard)


# --- Запуск сценария ---
async def start_story(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, parse_mode="HTML")
    await state.set_state(SetupStory.waiting_for_hero)


# --- /start ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await start_story(message, state)


@dp.message(F.text == "✨ Начать сказку")
async def start_button(message: types.Message, state: FSMContext):
    await start_story(message, state)


# --- Шаг 1: герой ---
@dp.message(SetupStory.waiting_for_hero)
async def got_hero(message: types.Message, state: FSMContext):
    await state.update_data(hero=message.text.strip())

    villains = [
        "Су анасы",
        "Шурале",
        "Албасты",
        "Юха",
        "Див",
        "Бичура",
        "Мяцкай",
        "Уряк",
        "Убырлы кеше",
        "Ифрит",
        "Аждаха",
        "Зилант",
    ]
    buttons = [
        InlineKeyboardButton(text=v, callback_data=f"villain:{v}") for v in villains
    ]
    rows = [
        [buttons[i], buttons[i + 1]] if i + 1 < len(buttons) else [buttons[i]]
        for i in range(0, len(buttons), 2)
    ]
    rows.append(
        [InlineKeyboardButton(text="✏️ Свой вариант", callback_data="villain:custom")]
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    await message.answer(
        f"Герой — <b>{message.text.strip()}</b>.\n\nВыберите злодея:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    await state.set_state(SetupStory.waiting_for_villain)


# --- Защита: текст вместо кнопки злодея ---
@dp.message(SetupStory.waiting_for_villain)
async def villain_text_guard(message: types.Message):
    await message.answer("Пожалуйста, выберите злодея из кнопок выше 👆")


# --- Шаг 2а: злодей из кнопок ---
@dp.callback_query(lambda c: c.data and c.data.startswith("villain:"))
async def got_villain(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    villain = callback.data.split(":", 1)[1]

    if villain == "custom":
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("Напиши своего злодея:")
        await state.set_state(SetupStory.waiting_for_custom_villain)
        return

    await callback.message.edit_reply_markup(reply_markup=None)
    await state.update_data(villain=villain)
    await callback.message.answer(
        f"Злодей: <b>{villain}</b>\n\nВыберите <b>первого помощника</b>:",
        reply_markup=helpers_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SetupStory.waiting_for_helper1)


# --- Шаг 2б: свой злодей ---
@dp.message(SetupStory.waiting_for_custom_villain)
async def got_custom_villain(message: types.Message, state: FSMContext):
    villain = message.text.strip()
    await state.update_data(villain=villain)
    await message.answer(
        f"Злодей: <b>{villain}</b>\n\nВыберите <b>первого помощника</b>:",
        reply_markup=helpers_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SetupStory.waiting_for_helper1)


# --- Защита: текст вместо кнопки помощников ---
@dp.message(SetupStory.waiting_for_helper1)
async def helper1_text_guard(message: types.Message):
    await message.answer("Пожалуйста, выберите помощника из кнопок выше 👆")


@dp.message(SetupStory.waiting_for_helper2)
async def helper2_text_guard(message: types.Message):
    await message.answer("Пожалуйста, выберите помощника из кнопок выше 👆")


# --- Шаг 3а: первый помощник из кнопок ---
@dp.callback_query(lambda c: c.data and c.data.startswith("helper:"))
async def got_helper(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    current_state = await state.get_state()
    value = callback.data.split(":", 1)[1]

    if current_state == SetupStory.waiting_for_helper1:
        if value == "custom":
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Напишите своего первого помощника:")
            await state.set_state(SetupStory.waiting_for_custom_helper1)
            return

        await callback.message.edit_reply_markup(reply_markup=None)
        await state.update_data(helper1=value)
        await callback.message.answer(
            f"Первый помощник: <b>{value}</b>\n\nВыберите <b>второго помощника</b>:",
            reply_markup=helpers_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(SetupStory.waiting_for_helper2)

    elif current_state == SetupStory.waiting_for_helper2:
        if value == "custom":
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Напишите своего второго помощника:")
            await state.set_state(SetupStory.waiting_for_custom_helper2)
            return

        await callback.message.edit_reply_markup(reply_markup=None)
        await state.update_data(helper2=value)
        await generate_and_send(
            callback.message, state, chat_id=callback.message.chat.id
        )


# --- Шаг 3б: свой первый помощник ---
@dp.message(SetupStory.waiting_for_custom_helper1)
async def got_custom_helper1(message: types.Message, state: FSMContext):
    await state.update_data(helper1=message.text.strip())
    await message.answer(
        f"Первый помощник: <b>{message.text.strip()}</b>\n\nВыберите <b>второго помощника</b>:",
        reply_markup=helpers_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SetupStory.waiting_for_helper2)


# --- Шаг 3в: свой второй помощник ---
@dp.message(SetupStory.waiting_for_custom_helper2)
async def got_custom_helper2(message: types.Message, state: FSMContext):
    await state.update_data(helper2=message.text.strip())
    await generate_and_send(message, state, chat_id=message.chat.id)


# --- Кнопка "Читать далее..." ---
@dp.callback_query(lambda c: c.data == "read_more")
async def read_more(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    part2 = data.get("story_part2", "")

    await callback.message.edit_reply_markup(reply_markup=None)

    if part2:
        for chunk in split_text(part2):
            await callback.message.answer(chunk)

    await state.clear()
    await callback.message.answer(
        "Хочешь новую сказку? Нажми кнопку ниже.",
        reply_markup=start_keyboard(),
    )


# --- Защита: сообщения вне сценария ---
@dp.message()
async def fallback(message: types.Message):
    await message.answer(
        "Чтобы начать сказку, нажмите кнопку ниже или отправь /start.",
        reply_markup=start_keyboard(),
    )


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
