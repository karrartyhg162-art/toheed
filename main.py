import os
import sys
import asyncio

# Ensure we are in the same directory as main.py
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import logging
import json
import config

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S", handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bot.log", encoding="utf-8")])
logging.getLogger("telethon").setLevel(logging.ERROR)

import subprocess

ACCOUNTS_FILE = "data/accounts.json"

def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_accounts(accounts):
    os.makedirs("data", exist_ok=True)
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(accounts, f, ensure_ascii=False, indent=4)

async def run_account(account):
    os.environ["ACCOUNT_NAME"] = account["name"]
    config.init_config(account)

    # Import bots after config is initialized
    from userbot import start_userbot, userbot
    from control_bot import start_bot, bot, set_userbot_ref
    import userbot as ub_module
    
    print(f"\n[{account['name']}] 🚀 Starting Userbot...")
    await start_userbot()
    set_userbot_ref(ub_module)
    print(f"[{account['name']}] 🤖 Starting Control Bot...")
    await start_bot()

    print(f"\n🟢 [{account['name']}] Ready! Send /start to the Control Bot.")
    
    try:
        await asyncio.gather(userbot.run_until_disconnected(), bot.run_until_disconnected())
    except KeyboardInterrupt:
        pass
    finally:
        await userbot.disconnect()
        await bot.disconnect()

def main_menu():
    print("══════════════════════════════════════")
    print("   🚀 Unified Telegram Bot 3-in-1")
    print("══════════════════════════════════════")

    accounts = load_accounts()
    print("1. Run all added accounts")
    print("2. Add a new account")
    
    choice = input("Choose (1/2): ").strip()

    if choice == "2":
        name = input("Account Name (Identifier): ")
        api_id = int(input("API_ID: "))
        api_hash = input("API_HASH: ")
        bot_token = input("BOT_TOKEN: ")
        string_session = input("STRING_SESSION (Leave empty to login via phone number): ")
        owner_id = int(input("OWNER_ID: "))
        
        account = {
            "name": name,
            "api_id": api_id,
            "api_hash": api_hash,
            "bot_token": bot_token,
            "string_session": string_session,
            "owner_id": owner_id,
            "session_name": f"data/{name}_user"
        }
        accounts.append(account)
        save_accounts(accounts)
        print("\n✅ Account added successfully!")
        
        # Re-run menu
        main_menu()
        return

    elif choice == "1":
        if not accounts:
            print("❌ No accounts found. Please add a new account first.")
            return
            
        print("\n🚀 Launching all accounts...")
        processes = []
        for acc in accounts:
            print(f"➡️ Starting process for account: {acc['name']}")
            # Start a separate process for each account
            p = subprocess.Popen([sys.executable, sys.argv[0], "--run-account", acc["name"]])
            processes.append(p)
            
        print("\n🟢 All accounts are running!")
        print("🛑 Press Ctrl+C to stop all accounts.\n")
        
        try:
            for p in processes:
                p.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping all accounts...")
            for p in processes:
                p.terminate()
            print("✅ All accounts stopped.")
    else:
        print("❌ Invalid choice.")

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--run-account":
        # Worker process execution
        acc_name = sys.argv[2]
        accounts = load_accounts()
        target_account = next((a for a in accounts if a["name"] == acc_name), None)
        if target_account:
            asyncio.run(run_account(target_account))
        else:
            print(f"❌ Account {acc_name} not found.")
    else:
        # Main menu execution
        try:
            main_menu()
        except KeyboardInterrupt:
            print("\n🛑 Exiting...")
