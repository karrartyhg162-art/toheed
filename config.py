API_ID = None
API_HASH = None
BOT_TOKEN = None
OWNER_ID = None
SESSION_NAME = None
STRING_SESSION = None

def init_config(account_dict):
    global API_ID, API_HASH, BOT_TOKEN, OWNER_ID, SESSION_NAME, STRING_SESSION
    API_ID = account_dict.get("api_id")
    API_HASH = account_dict.get("api_hash")
    BOT_TOKEN = account_dict.get("bot_token")
    OWNER_ID = account_dict.get("owner_id")
    SESSION_NAME = account_dict.get("session_name")
    STRING_SESSION = account_dict.get("string_session", "")
