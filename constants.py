from os import environ

days_promocode_is_valid: int = 10

db_host = environ.get('MYSQL_HOST', '127.0.0.1')
db_user = environ.get('MYSQL_USER', 'root')
db_password = environ.get('MYSQL_PASSWORD', '')
db = environ.get('MYSQL_DATABASE', '')

server_addr = environ.get('SERVER_ADDR', "http://0.0.0.0:8090")  # change here

nginx_host = environ.get('NGINX_HOST', '127.0.0.1')  # automatically

root_chat = ('',)
admin_chats = ('', '', '',) + root_chat
weak_admin_chats = admin_chats + root_chat

default_shop_name = ""

static_data = path_to_db = homedir = ""
private_db = ""

if db_host == '127.0.0.1':
    static_data = path_to_db = homedir = ""
    private_db = ""

db_json_path = f"{static_data}collections"
ios_json = f"{db_json_path}/ios-json/ios-collections.json"
ios_banned_json = f"{db_json_path}/ios-json/ios-banned-collections.json"
android_json = f"{db_json_path}/android-json/android-collections.json"
android_banned_json = f"{db_json_path}/android-json/android-banned-collections.json"

images_dir_path = f"{static_data}images"

ads_img_dir = f"{images_dir_path}/adspromo"
ios_ads_json_path = f"{db_json_path}/ios-json/ios-ads.json"
android_ads_json_path = f"{db_json_path}/android-json/android-ads.json"

classifier = f"{private_db}/clf.pkl"
count_vectorizer = f"{private_db}/count_vect.pkl"
tf_idf_transformer = f"{private_db}/tfidf_transformer.pkl"
navec_file = f"{private_db}/navec_news_v1_1B_250K_300d_100q.tar"
ner_file = f"{private_db}/slovnet_ner_news_v1.tar"
email_read_msg = f"{private_db}/read_messages.json"
instagram_target_list_file = f"{private_db}/instagram_targets.txt"
instapy_workspace = f"{private_db}/instapy_workspace"
push_cert = f"{private_db}/Certificates-prod.pem"

# dict in this format is needed for classification
categories = {
    0: "Детские магазины",
    1: "Еда",
    2: "Кино",
    3: "Книги",
    4: "Красота и здоровье",
    5: "Маркетплейсы",
    6: "Одежда и обувь",
    7: "Техника",
    8: "Разное",
    9: "ГОРЯЧЕЕ 🔥",
    10: "Для дома"
}

# needed for short shop description
initial_form_words = {
    r"^[Сс]кидк\w{1,3}": "Скидка",
    r"^[Рр]аспродаж\w{1,2}": "Распродажа",
    r"^бесплатн": "Беспалтн",
    r"^[Хх]алявн": "Беспалтн",
    r"^выгод": "Выгод"
    }

priorities = {'zero': 0, 'default': 250, 'html': 300, 'middle': 500,
              'high': 750, 'ultra': 1000, 'mega': 5000}

# must be 400x400
default_image = "/default_images/default_icon.png"
hot_default_image = "/default_images/hot_icon.png"
food_default_image = "/default_images/food_icon.png"
movie_default_image = "/default_images/movie_icon.png"
kids_default_image = "/default_images/kids_icon.png"
books_default_image = "/default_images/books_icon.png"
cosmetics_default_image = "/default_images/cosmetics_icon.png"
clothes_default_image = "/default_images/clothes_icon.png"
marketplace_default_image = "/default_images/marketplace_icon.png"
electronics_default_image = "/default_images/electronics_icon.png"
home_default_image = "/default_images/home_icon.png"


default_images = {
    "Кино": movie_default_image,
    "Детские магазины": kids_default_image,
    "Еда": food_default_image,
    "Книги": books_default_image,
    "Красота и здоровье": cosmetics_default_image,
    "Одежда и обувь": clothes_default_image,
    "Маркетплейсы": marketplace_default_image,
    "Техника": electronics_default_image,
    "Для дома": home_default_image,
    "Разное": default_image,
    "ГОРЯЧЕЕ 🔥": hot_default_image,
}

categories_priorities = {
    "ГОРЯЧЕЕ 🔥": 1000,
    "Еда": 900,
    "Одежда и обувь": 800,
    "Красота и здоровье": 700,
    "Техника": 600,
    "Книги": 500,
    "Детские магазины": 400,
    "Маркетплейсы": 300,
    "Для дома": 200,
    "Кино": 100,
    "Разное": 0,
    "DEFAULT": 1,
}

categories_tags = {
    "Кино": ("кинотеатр", "кино",),
    "Детские магазины": ("дети", "игрушки", ),
    "Еда": ("еда",),
    "Книги": ("книги", "чтение", "литература", ),
    "Красота и здоровье": ("красота", "здоровье", ),
    "Одежда и обувь": ("одежда", "обувь", ),
    "Маркетплейсы": ("гипермаркет", "маркетплейс", ),
    "Техника": ("электроника", "техника", ),
    "Разное": ("разное", ),
    "ГОРЯЧЕЕ 🔥": ("лучшее", "топ", ),
    "Для дома": ("дом", ),
}

# {account: website_link}
# that associated with shop
instagram_accounts_website = {
    "tanuki.official": "https://tanuki.ru",
    "yakitoriya.ru": "https://yakitoriya.ru",
    "dominospizzarussia": "https://dominospizza.ru",
    "dodopizza_msk": "https://dodopizza.ru",
    "papajohnsru": "https://papajohns.ru",
    "pizzahutrussia": "https://pizzahut.ru",
    "kfcrussia": "https://kfc.ru",
    "delivery_club": "https://delivery-club.ru"
}

vk_targets = ("probnick_ru", "skidki", "halyavshiki",)
