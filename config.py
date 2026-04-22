import os
TOKEN = os.getenv('DISCORD_TOKEN')

# ------------------ ID каналов ------------------
WELCOME_CHANNEL_ID = 1469706687475875943          # канал для приветствий
LOG_CHANNEL_ID = 1490743373915754678               # канал для логов заходов
LEAVE_LOG_CHANNEL_ID = 1490743519403315351  # канал для логов выхода участников
REQUEST_CHANNEL_ID = 1469685743579566275           # канал для заявок (входящие)
ACCEPTED_CHANNEL_ID = 1469685873779019800          # канал для принятых заявок
REJECTED_CHANNEL_ID = 1469685977021944001          # канал для отклонённых заявок
BLACKLIST_LOG_CHANNEL_ID = 1490752403912528042     # канал для логов чёрного списка
BLACKLIST_PANEL_CHANNEL_ID = 1479504212105756955   # канал с панелью управления ЧС
APPLICATION_BUTTON_CHANNEL_ID = 1454052533654786118 # канал с кнопкой подачи заявки
PORTFOLIO_CREATION_CHANNEL_ID = 1469700666132795463 # канал с кнопкой создания портфеля
AFK_LOG_CHANNEL_ID = 1490741922766258362           # канал для логов AFK
AFK_PANEL_CHANNEL_ID = 1496491713227788348         # канал с панелью AFK
VACATION_LOG_CHANNEL_ID = 1490751284960296991      # канал для логов отпусков
VACATION_PANEL_CHANNEL_ID = 1469704346978619474    # канал с панелью отпусков
GREEN_REQUESTS_CHANNEL_ID = 1479505188678271107
GREEN_LOG_CHANNEL_ID = 1490752310325022761
LOGGING_CHANNEL_ID = 1453814215960957129  # ID канала для логов
# ------------------ ID ролей ------------------
ROLE_OZON = 1469687547981598946
ROLE_GUEST = 1453818314685022408
ROLE_FAMQ = 1453818745754484850
ROLE_ACADEMY = 1453817578626748628
INVITER_ROLE_ID = 1453817370043748443
LEADER_ROLE_ID = 1453817008826351697
DEPUTY_LEADER_ROLE_ID = 1453817087272157305
VACATION_ROLE_ID = 1469703867418542314
CURATOR_ROLE_ID = 1471533152462704876

# Роли для рангов (портфели)
ACADEMY_ROLE_ID = 1453817578626748628
REED_ROLE_ID = 1453817475828551975
MAIN_ROLE_ID = 1453817433352700067
HIGH_ROLE_ID = 1453817148433502270

# ------------------ ID категорий (портфели) ------------------
ACADEMY_CATEGORY_ID = 1496264623924449346
REED_CATEGORY_ID = 1496264623924449346
MAIN_CATEGORY_ID = 1496264623924449346
HIGH_CATEGORY_ID = 1496264623924449346

# ------------------ ID кастомных эмодзи ------------------
EMOJI_ACCEPT = 1490411149248827453
EMOJI_REJECT = 1490411135843959005
EMOJI_CALL = 1490411470926774522
# ID кастомных эмодзи для портфелей (замените на реальные ID ваших эмодзи)
EMOJI_ACADEMY = "<:Academy:1481338614959968386>"   # эмодзи для Academy
EMOJI_REED = "<:Reed:1481338714985594920>"       # эмодзи для Reed
EMOJI_MAIN = "<:Main:1481338748947140660>"       # эмодзи для Main
EMOJI_HIGH = "<:high:1481339215626240030>"       # эмодзи для High

# ------------------ Прочее ------------------
APPLICATION_BANNER_URL = "https://cdn.discordapp.com/attachments/1476263725735346179/1476995652079845447/image.png?ex=69a326e4&is=69a1d564&hm=2de1512ce783425de92c134e30b5b60f7a4844802264f5b8d571793e81573691&"
VOICE_CHANNEL_ID = 1472308376045228275


ACTIVITY_CHECK_DAYS = 4          # период неактивности в днях
ACTIVITY_CHECK_HOUR = 24         # интервал проверки в часах (например, 24 – раз в сутки)

# Роли, имеющие доступ ко всем портфелям (высокие + лидеры)
PORTFOLIO_ACCESS_ROLES = [HIGH_ROLE_ID, LEADER_ROLE_ID, DEPUTY_LEADER_ROLE_ID, ]

# ---------- Каналы для мероприятий ----------
EVENTS_CREATION_CHANNEL_ID = 1469692595260231894   # канал с кнопкой создания
EVENTS_CHANNEL_ID = 1488879747898277960            # канал, куда отправляются мероприятия
EVENTS_LOG_CHANNEL_ID = 1486411401022144825        # канал для логов мероприятий

# ---------- Роли для мероприятий ----------
# Список ролей, которые могут записываться сразу в основной состав (например, "Основной состав")
EVENT_PRIVILEGED_ROLES = [HIGH_ROLE_ID, MAIN_ROLE_ID, DEPUTY_LEADER_ROLE_ID, LEADER_ROLE_ID]  # подставьте ID
# Роли, имеющие административные права (лидер, деп-лидер)
EVENT_ADMIN_ROLES = [LEADER_ROLE_ID, DEPUTY_LEADER_ROLE_ID]

# ---------- Голосовой канал для проверки ----------
EVENT_VOICE_CHANNEL_ID = 1454074855980011762

# ------------------ Настройки логирования бота ------------------
BOT_LOG_CHANNEL_ID = 1483772224065376278   # ID канала для единого лога
LOGGING_ENABLED = True

LOG_LEVELS = {
    'commands': True,
    'events': True,
    'errors': True,
    'ui': True,
    'voice': True,
    'messages': False,
    'debug': True,
    'role_changes': True,
    'http_errors': True,
}


# Текстовые каналы для панелей управления (по одному на категорию)
KICK_PANEL_CHANNEL_ID = 1489656813287899166       # канал с кнопками для киков
WEAPONS_PANEL_CHANNEL_ID = 1489656938022043768    # канал с кнопками для оружия
EVENT_PANEL_CHANNEL_ID = 1489663807608586380      # канал с кнопками для мероприятий

# Каналы для логов (обычные текстовые каналы)
KICK_LOG_CHANNEL_ID = 1491073954729951243          # ID канала, куда отправлять логи киков
WEAPONS_LOG_CHANNEL_ID = 1491074032043430018       # ID канала, куда отправлять логи изменений оружия
EVENT_LOG_CHANNEL_ID = 1491074075815317655         # ID канала, куда отправлять логи мероприятий

# Роли, имеющие доступ к панели (хай-ранги, деп-лидеры, лидеры)
REPORT_ACCESS_ROLES = [
    HIGH_ROLE_ID,
    DEPUTY_LEADER_ROLE_ID,
    LEADER_ROLE_ID
]


# Конкурс инвайтов
CONTEST_CHANNEL_ID = 1492799248419520623          # ID канала, куда кидают скрины
CONTEST_APPROVER_ROLE_ID = 1492799522508767252    # ID роли организатора
LEADERBOARD_CHANNEL_ID = 1492799271706296450      # ID канала для топа участников

EMOJI_FIRST_PLACE = "<:123:1492808461799657542>"
EMOJI_SECOND_PLACE = "<:321:1492808489825996850>"


# ------------------ Настройки PostgreSQL ------------------
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_DATABASE = os.getenv('PG_DATABASE', 'reedguard')
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')


