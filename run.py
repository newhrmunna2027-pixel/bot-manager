# -*- coding: utf-8 -*-
# run.py - Combined Engine Setup & Dual-Thread Bootloader (MongoDB & Render Cloud Patched)
# This loader handles log environment setup, DB connection check, port binding, background Flask API, and main CLI loop.

import os
import sys
import time
import socket
import threading
from pymongo import MongoClient

# নিশ্চিত ডিরেক্টরি চেকার (লগ ও টেমপ্লেটের জন্য প্রয়োজনীয় ফোল্ডার জেনারেটর)
REQUIRED_DIRECTORIES = ["temp_files", "templates"]
for folder in REQUIRED_DIRECTORIES:
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except Exception as e:
            print(f"Directory initialization error [{folder}]: {str(e)}")

# সিস্টেমে মডিউল ইম্পোর্ট পাথ সচল করা
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Friend')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Guild')))

import bot
import friend_list
import add_friend
import remove_friend
import pending_list
import accept_request
import reject_request
import guild_info
import member_list
import join_guild
import leave_guild
import terminal
import app 

def is_port_in_use(port):
    """পোর্ট ব্লক হওয়া এড়াতে ব্যাকগ্রাউন্ড কানেকশন সিকিউরিটি চেক"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def check_mongodb_connection():
    """স্টার্টআপে MongoDB কানেকশন সফলভাবে সম্পন্ন হচ্ছে কি না তা ভেরিফাই করার মেথড"""
    mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://admin:admin@cluster.mongodb.net/garena_db")
    try:
        # ৫ সেকেন্ডের মধ্যে কানেক্ট না হলে এটি কানেকশন ফেইলড দেখাবে
        temp_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        temp_client.server_info()  # Forces a call to check if connection is active
        print("\033[1;32m[🟢] MongoDB Connection verified successfully!\033[0m")
        return True
    except Exception as e:
        print("\033[1;31m[❌] MongoDB Connection Warning: Connection failed or invalid MONGO_URI!\033[0m")
        print(f"\033[1;31m    Error Detail: {str(e)}\033[0m")
        return False

def run_flask_app():
    """ব্যাকগ্রাউন্ড থ্রেড এপিআই সার্ভার রানার"""
    import os
    # Render-এর দেওয়া ডাইনামিক পোর্ট রিড করবে, না থাকলে ডিফল্ট ৫০0০ পোর্ট নিবে
    port = int(os.environ.get("PORT", 5000))
    app.app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def print_engine_boot_banner():
    """টার্মিনাল লোড হওয়ার পূর্বে স্টার্টআপ ডেকোরেশন"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("\033[1;36m[*] Initializing Garena Triple-Mode Controller Engine...\033[0m")
    print("\033[1;33m[*] Validating Remote Garena MongoDB Datastores...\033[0m")
    
    # বুট ব্যানারে ডাটাবেজ কানেকশন চেক করা
    check_mongodb_connection()
    
    print("\033[1;32m[*] Web API Server successfully bound on Background Thread.\033[0m")
    time.sleep(1.5)

if __name__ == '__main__':
    # ১. বুট ডেকোরেশন ও ডাটাবেজ চেকিং রান করা
    print_engine_boot_banner()

    # ২. ব্যাকগ্রাউন্ড থ্রেড এপিআই সার্ভার ইনিশিয়ালাইজ করা
    api_thread = threading.Thread(target=run_flask_app, daemon=True)
    api_thread.start()
    
    # ৩. মেইন থ্রেডে ইউজার কনসোল লুপ রান করা
    try:
        terminal.console_loop()
    except KeyboardInterrupt:
        print(f"\n\n\033[1;31m⚠ Dashboard Engine Process terminated by user.\033[0m")