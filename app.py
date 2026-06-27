# -*- coding: utf-8 -*-
# app.py - Garena Web Controller App with Stateless Memory-Only Public REST APIs (Check UID & Security Bind Patched with MongoDB Integration)

import os
import sys
import json
import time
import shutil
import hmac
import hashlib
import requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from pymongo import MongoClient

# Absolute import resolution paths
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

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
app.json.order_keys = False  # JSON key ordering fix
app.secret_key = "OUT_OF_LAW_SYSTEM_KEY_902"

# ==========================================
# === MONGODB DATABASE CONFIGURATION     ===
# ==========================================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://admin:admin@cluster.mongodb.net/garena_db")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["garena_manager"]
    members_col = db["members"]
    bots_col = db["bots"]
except Exception as e:
    print(f"[*] MongoDB connection warning: {str(e)}")
    db = None
    members_col = None
    bots_col = None

# Database helper functions mapped cleanly to MongoDB Collections
def load_members():
    try:
        if members_col is None:
            return {}
        docs = members_col.find({})
        members_dict = {}
        for doc in docs:
            username = doc.get("username")
            if username:
                p = dict(doc)
                p.pop("_id", None)  # Remove internal key for JSON compatibility
                members_dict[username] = p
                
        if not members_dict:
            # Initialize default super owner profile upon database empty state
            default_data = {
                "owner": {
                    "name": "Super Owner",
                    "username": "owner",
                    "password": "123",
                    "role": "owner",
                    "limit": 999
                }
            }
            save_members(default_data)
            return default_data
        return members_dict
    except Exception as e:
        print(f"[*] MongoDB load_members error: {str(e)}")
        return {}

def save_members(data):
    try:
        if members_col is None:
            return
        for username, p in data.items():
            p["username"] = username
            members_col.update_one(
                {"username": username},
                {"$set": p},
                upsert=True
            )
    except Exception as e:
        print(f"[*] MongoDB save_members error: {str(e)}")

def get_user_dir(username):
    # Mocking folder creation to prevent any structural breaks
    return username

def get_user_profile(username):
    try:
        if members_col is None:
            return {"username": username, "password": "123", "role": "user", "limit": 5}
        doc = members_col.find_one({"username": username})
        if doc:
            doc.pop("_id", None)
            return doc
    except Exception:
        pass
    return {"username": username, "password": "123", "role": "user", "limit": 5}

def save_user_profile(username, profile):
    try:
        if members_col is None:
            return
        profile["username"] = username
        members_col.update_one(
            {"username": username},
            {"$set": profile},
            upsert=True
        )
    except Exception as e:
        print(f"[*] MongoDB save_user_profile error: {str(e)}")

def get_user_bots(username):
    try:
        if bots_col is None:
            return []
        docs = bots_col.find({"owner_username": username})
        bots_list = []
        for doc in docs:
            doc.pop("_id", None)
            bots_list.append(doc)
        return bots_list
    except Exception as e:
        print(f"[*] MongoDB get_user_bots error: {str(e)}")
        return []

def save_user_bots(username, bots):
    try:
        if bots_col is None:
            return
        # First wipe existing bots for this username to prevent duplicate keys, then insert updated bots list
        bots_col.delete_many({"owner_username": username})
        if bots:
            for b in bots:
                b["owner_username"] = username
                b.pop("_id", None)
                bots_col.insert_one(b)
    except Exception as e:
        print(f"[*] MongoDB save_user_bots error: {str(e)}")

# Initialize owner profile dynamically on start
def init_owner_profile():
    owner_profile = get_user_profile("owner")
    owner_profile["username"] = "owner"
    owner_profile["password"] = "123"
    owner_profile["role"] = "owner"
    owner_profile["limit"] = 999
    save_user_profile("owner", owner_profile)

init_owner_profile()

def render_section(template_name, **kwargs):
    try:
        return render_template(f"sections/{template_name}", **kwargs)
    except Exception as e:
        return f"<div class='p-4 text-red-500'>Section '{template_name}' Render Failure: {str(e)}</div>"

# ==================== AUTH ROUTING AND FILTERS ====================

@app.before_request
def require_login():
    allowed_routes = ['login', 'api_auth_login', 'static']
    
    # Bypass session auth checks for Stateless Direct Public APIs
    if request.path.startswith('/api/direct/'):
        return
        
    if 'username' not in session and request.endpoint not in allowed_routes:
        return redirect(url_for('login'))

@app.route('/login')
def login():
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data = request.json or {}
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()
    remember = data.get("remember", False)
    
    if not username or not password:
        return jsonify({"success": False, "msg": "Fields cannot be left empty."})
        
    members = load_members()
    if username in members and members[username]["password"] == password:
        session['username'] = username
        session['role'] = members[username].get("role", "user")
        if remember:
            session.permanent = True
        return jsonify({"success": True})
    return jsonify({"success": False, "msg": "Invalid Username ID or Password."})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ==================== MAIN PANEL PORTRAIT RENDERER ====================

@app.route('/')
def index():
    username = session.get('username')
    bots = get_user_bots(username)
    session_data = bot.load_session(username)

    # Redirect cleanly to bot login if Garena token is empty on load
    if not session_data.get("token"):
        return redirect(url_for('bot_login'))

    header = render_section("header.html")
    nav_bar = render_section("nav_bar.html")
    dashboard = render_section("dashboard.html")
    friend_sec = render_section("friend.html")
    bot_sec = render_section("bot.html")
    guild_sec = render_section("guild.html")
    modals = render_section("modals.html")
    
    return render_template("index.html", 
                           header=header, 
                           nav_bar=nav_bar, 
                           dashboard=dashboard, 
                           friend_sec=friend_sec, 
                           bot_sec=bot_sec, 
                           guild_sec=guild_sec, 
                           modals=modals)

@app.route('/bot-login')
def bot_login():
    return render_template("bot_login.html")

# ==================== BOT MANAGER WORKSPACE APIs ====================

@app.route('/api/bot/login', methods=['POST'])
def api_bot_login():
    username = session.get('username')
    data = request.json or {}
    uid = str(data.get("uid", "")).strip()
    password = data.get("password", "").strip()
    
    if not uid or not password:
        return jsonify({"success": False, "msg": "Missing bot credentials."})
        
    token, err = bot.get_token_from_uid_password(uid, password)
    if err:
        return jsonify({"success": False, "msg": f"Garena Login Failure: {err}"})
        
    profile = bot.refresh_self_profile_cache(token, username)
    if not profile:
        return jsonify({"success": False, "msg": "Garena handshake successful, profile extraction timeout."})
        
    bots = get_user_bots(username)
    bot_exists = False
    for b in bots:
        if b["uid"] == uid:
            b["password"] = password
            b["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            bot_exists = True
            break
    if not bot_exists:
        bots.append({
            "uid": uid,
            "password": password,
            "nickname": profile["nickname"],
            "level": profile["level"],
            "last_login": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    save_user_bots(username, bots)
    
    session_data = {"uid": uid, "password": password, "token": token}
    bot.save_session(session_data, username)
    
    return jsonify({"success": True})

# 🟢 Authenticate and Register Bot using Garena EAT Token Flow
@app.route('/api/bot/login_eat', methods=['POST'])
def api_bot_login_eat():
    username = session.get('username')
    data = request.json or {}
    eat_token = data.get("eat_token", "").strip()
    
    if not eat_token:
        return jsonify({"success": False, "msg": "Please supply a valid EAT token."})
        
    jwt_token, access_token, open_id, decoded_uid, err = bot.get_token_from_eat_flow(eat_token)
    if err:
        return jsonify({"success": False, "msg": f"EAT Session error: {err}"})
        
    profile = bot.refresh_self_profile_cache(jwt_token, username)
    if not profile:
        return jsonify({"success": False, "msg": "Garena EAT Handshake successful, but profile caching timed out."})
        
    bots = get_user_bots(username)
    bot_exists = False
    for b in bots:
        if b["uid"] == decoded_uid:
            b["password"] = ""  # No password saved for EAT-only profiles
            b["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            b["nickname"] = profile["nickname"]
            b["level"] = profile["level"]
            bot_exists = True
            break
    if not bot_exists:
        bots.append({
            "uid": decoded_uid,
            "password": "",
            "nickname": profile["nickname"],
            "level": profile["level"],
            "last_login": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    save_user_bots(username, bots)
    
    session_data = {
        "uid": decoded_uid, 
        "password": "", 
        "token": jwt_token, 
        "access_token": access_token, 
        "open_id": open_id, 
        "eat_token": eat_token
    }
    bot.save_session(session_data, username)
    return jsonify({"success": True})

@app.route('/api/bot/list')
def api_bot_list():
    username = session.get('username')
    bots = get_user_bots(username)
    return jsonify({"success": True, "bots": bots})

@app.route('/api/bot/switch', methods=['POST'])
def api_bot_switch():
    username = session.get('username')
    data = request.json or {}
    uid = str(data.get("uid", "")).strip()
    
    bots = get_user_bots(username)
    target_bot = None
    for b in bots:
        if b["uid"] == uid:
            target_bot = b
            break
            
    if not target_bot:
        return jsonify({"success": False, "msg": "Selected Garena bot is not registered."})
        
    if target_bot.get("password"):
        token, err = bot.get_token_from_uid_password(uid, target_bot["password"])
        if err:
            return jsonify({"success": False, "msg": f"Switch login failed: {err}"})
        session_data = {"uid": uid, "password": target_bot["password"], "token": token}
    else:
        local_sess = bot.load_session(username)
        eat_token = local_sess.get("eat_token")
        if not eat_token:
            return jsonify({"success": False, "msg": "Stored EAT token session is missing. Please re-authenticate."})
            
        token, access_token, open_id, decoded_uid, err = bot.get_token_from_eat_flow(eat_token)
        if err:
            return jsonify({"success": False, "msg": f"Switch EAT handshake failed: {err}"})
        session_data = {
            "uid": uid, 
            "password": "", 
            "token": token, 
            "access_token": access_token, 
            "open_id": open_id, 
            "eat_token": eat_token
        }
        
    profile = bot.refresh_self_profile_cache(token, username)
    if not profile:
        return jsonify({"success": False, "msg": "Switch success, caching timeout."})
        
    bot.save_session(session_data, username)
    return jsonify({"success": True, "msg": f"Switched Garena session to {profile['nickname']}!"})

@app.route('/api/bot/delete', methods=['POST'])
def api_bot_delete():
    username = session.get('username')
    data = request.json or {}
    uid = str(data.get("uid", "")).strip()
    
    bots = get_user_bots(username)
    updated_bots = [b for b in bots if b["uid"] != uid]
    save_user_bots(username, updated_bots)
    
    session_data = bot.load_session(username)
    if session_data.get("uid") == uid:
        bot.save_session({}, username)
        if db is not None:
            try:
                db["profile_cache"].delete_one({"username": username})
            except Exception: pass
            
    return jsonify({"success": True, "msg": "Bot records cleared."})

# ==================== ISOLATED CONTROLLER 3-LAYER APIs ====================

@app.route('/api/check_uid/<uid>')
def api_check_uid(uid):
    username = session.get('username')
    token, err = bot.get_active_token(username)
    if err:
        return jsonify({"success": False, "msg": f"Authentication Failure: {err}"}), 401
    
    res = bot.get_player_info_detailed(uid, token)
    return jsonify(res)

@app.route('/api/bot/profile')
def api_bot_profile():
    username = session.get('username')
    
    token, err = bot.get_active_token(username)
    if err:
        return jsonify({"success": False, "msg": f"Authentication Failure: {err}"}), 401
    
    author_uid = bot.decode_author_uid(token)
    res_raw = bot.get_player_info_detailed(author_uid, token)
    
    if res_raw.get("success"):
        return jsonify({
            "success": True,
            "profile": {
                "uid": res_raw["uid"],
                "nickname": res_raw["nickname"],
                "level": res_raw["level"],
                "clan_id": res_raw["clan_id"],
                "clan_name": res_raw["clan_name"],
                "region": res_raw["region"],
                "likes": res_raw["likes"],
                "signature": res_raw["signature"],
                "last_login": res_raw["last_login"],
                "created_at": res_raw["created_at"]
            },
            "json_data": res_raw["json_data"],
            "name_json_data": res_raw["name_json_data"]
        })
    return jsonify({"success": False, "msg": "Failed to sync Garena Bot Profile."})

@app.route('/api/bot/refresh', methods=['POST'])
def api_bot_refresh():
    username = session.get('username')
    token, err = bot.get_active_token(username)
    if err:
        return jsonify({"success": False, "msg": f"Auth token failed: {err}"}), 401
        
    author_uid = bot.decode_author_uid(token)
    res_raw = bot.get_player_info_detailed(author_uid, token)
    
    if res_raw.get("success"):
        bot.refresh_self_profile_cache(token, username)
        return jsonify({
            "success": True,
            "profile": {
                "uid": res_raw["uid"],
                "nickname": res_raw["nickname"],
                "level": res_raw["level"],
                "clan_id": res_raw["clan_id"],
                "clan_name": res_raw["clan_name"],
                "region": res_raw["region"],
                "likes": res_raw["likes"],
                "signature": res_raw["signature"],
                "last_login": res_raw["last_login"],
                "created_at": res_raw["created_at"]
            },
            "json_data": res_raw["json_data"],
            "name_json_data": res_raw["name_json_data"],
            "msg": "Bot portrait refreshed dynamically!"
        })
    return jsonify({"success": False, "msg": "Live Garena Gateway handshake timeout."})

@app.route('/api/friends/list')
def api_friends_list():
    username = session.get('username')
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    
    res = friend_list.get_active_friend_list(token)
    if res.get("success"):
        raw_proto_parsed = bot.parse_proto_bytes(res.get("friends_raw_bytes", b""))
        serializable_json = bot.make_serializable(raw_proto_parsed)
        return jsonify({
            "success": True,
            "friends": res["friends"],
            "json_data": serializable_json,
            "name_json_data": bot.map_proto_to_named(serializable_json, "Friend")
        })
    return jsonify(res)

@app.route('/api/friends/pending')
def api_friends_pending():
    username = session.get('username')
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    
    res = pending_list.get_pending_request_list(token)
    if res.get("success"):
        enriched_requests = []
        for r in res["requests"]:
            p_res = bot.get_player_info_detailed(r["uid"], token)
            if p_res.get("success"):
                r["guild_name"] = p_res.get("clan_name", "No Guild")
                r["level"] = p_res.get("level", r["level"])
                avatar_id = p_res["json_data"]["1"]["12"] if (p_res.get("json_data") and "1" in p_res["json_data"]) else "902000003"
                r["avatar_id"] = str(avatar_id)
            enriched_requests.append(r)

        raw_proto_parsed = bot.parse_proto_bytes(res.get("pending_raw_bytes", b""))
        serializable_json = bot.make_serializable(raw_proto_parsed)
        return jsonify({
            "success": True,
            "requests": enriched_requests,
            "json_data": serializable_json,
            "name_json_data": bot.map_proto_to_named(serializable_json, "Player")
        })
    return jsonify(res)

@app.route('/api/friends/add', methods=['POST'])
def api_friends_add():
    username = session.get('username')
    uid = request.json.get("uid")
    if not uid: return jsonify({"success": False, "msg": "Missing UID"}), 400
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    success = add_friend.add_target_friend(token, uid)
    return jsonify({"success": success, "msg": "Friend Request successfully queued!" if success else "Handshake rejected."})

@app.route('/api/friends/remove', methods=['POST'])
def api_friends_remove():
    username = session.get('username')
    uid = request.json.get("uid")
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    success = remove_friend.delete_active_friend(token, uid)
    return jsonify({"success": success})

@app.route('/api/friends/accept', methods=['POST'])
def api_friends_accept():
    username = session.get('username')
    uid = request.json.get("uid")
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    success = accept_request.accept_friend_request(token, uid)
    return jsonify({"success": success})

@app.route('/api/friends/reject', methods=['POST'])
def api_friends_reject():
    username = session.get('username')
    uid = request.json.get("uid")
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    success = reject_request.reject_friend_request(token, uid)
    return jsonify({"success": success})

@app.route('/api/guild/info/<clan_id>')
def api_guild_info(clan_id):
    username = session.get('username')
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    
    res = guild_info.get_clan_info_by_id(token, clan_id)
    return jsonify(res)

@app.route('/api/guild/members/<clan_id>')
def api_guild_members(clan_id):
    username = session.get('username')
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    
    res = member_list.get_guild_member_list(token, clan_id)
    
    if res.get("success"):
        safe_res = {
            "success": True,
            "leader": res.get("leader"),
            "acting_leader": res.get("acting_leader"),
            "officers": res.get("officers"),
            "members": res.get("members"),
            "total_members": res.get("total_members")
        }
        raw_proto_parsed = bot.parse_proto_bytes(res.get("members_raw_bytes", b""))
        serializable_json = bot.make_serializable(raw_proto_parsed)
        safe_res["json_data"] = serializable_json
        safe_res["name_json_data"] = bot.map_proto_to_named(serializable_json, "Guild")

        return jsonify(safe_res)
        
    return jsonify(res)

@app.route('/api/guild/join', methods=['POST'])
def api_guild_join():
    username = session.get('username')
    clan_id = request.json.get("clan_id")
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    success = join_guild.request_join_clan(token, clan_id)
    return jsonify({"success": success})

@app.route('/api/guild/leave', methods=['POST'])
def api_guild_leave():
    username = session.get('username')
    clan_id = request.json.get("clan_id")
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    success = leave_guild.quit_current_clan(token, clan_id)
    return jsonify({"success": success})

@app.route('/api/bot/nickname', methods=['POST'])
def api_bot_nickname():
    username = session.get('username')
    new_nick = request.json.get("nickname")
    if not new_nick: return jsonify({"success": False, "msg": "Nickname required."}), 400
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    res = bot.change_nickname_native(token, new_nick)
    return jsonify(res)

@app.route('/api/bot/bio', methods=['POST'])
def api_bot_bio():
    username = session.get('username')
    new_bio = request.json.get("bio")
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    res = bot.update_bio_native(token, new_bio)
    return jsonify(res)

@app.route('/api/bot/duo', methods=['POST'])
def api_bot_duo():
    username = session.get('username')
    uid = request.json.get("uid")
    token, err = bot.get_active_token(username)
    if err: return jsonify({"success": False, "msg": err}), 401
    
    res = bot.check_duo_native(token, uid)
    if res.get("success"):
        partner_uid = res.get("partner_uid")
        
        target_profile = bot.get_player_info_detailed(uid, token)
        partner_profile = bot.get_player_info_detailed(partner_uid, token) if partner_uid else None
        
        res_data = {
            "success": True,
            "partner_uid": partner_uid,
            "level": res.get("level"),
            "score": res.get("score"),
            "days_active": res.get("days_active"),
            "formed_on": res.get("formed_on"),
            "status": res.get("status"),
            
            "target_profile": target_profile,
            "partner_profile": partner_profile
        }
        
        return jsonify(res_data)
    return jsonify(res)

@app.route('/api/bot/logout', methods=['POST'])
def api_bot_logout():
    username = session.get('username')
    try:
        if db is not None:
            db["sessions"].delete_one({"username": username})
            db["profile_cache"].delete_one({"username": username})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "msg": str(e)})

# 🟢 Fetch Account Bind/Security Info (Owner Only Guarded Endpoint)
@app.route('/api/bot/check_bind')
def api_bot_check_bind():
    if session.get("role") != "owner":
        return jsonify({"success": False, "msg": "Unauthorized access. Only owners are allowed to check account bind information."}), 403
        
    username = session.get('username')
    session_data = bot.load_session(username)
    access_token = session_data.get("access_token")
    
    if not access_token:
        uid = session_data.get("uid")
        password = session_data.get("password")
        if uid and password:
            try:
                oauth_url = "https://100067.connect.garena.com/api/v2/oauth/guest/token:grant"
                parsed_uid = int(uid) if str(uid).isdigit() else uid
                payload = {
                    "client_id": 100067,
                    "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
                    "client_type": 2,
                    "password": password,
                    "response_type": "token",
                    "uid": parsed_uid
                }
                body_json = json.dumps(payload, separators=(',', ':'))
                key_bytes = bytes.fromhex("2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3")
                signature = hmac.new(key_bytes, body_json.encode('utf-8'), hashlib.sha256).hexdigest()

                headers = {
                    "Authorization": f"Signature {signature}",
                    "Content-Type": "application/json; charset=utf-8",
                    "Accept": "application/json",
                    "Connection": "Keep-Alive",
                    "Host": "100067.connect.garena.com"
                }
                oauth_response = requests.post(oauth_url, data=body_json, headers=headers, timeout=10, verify=False)
                if oauth_response.status_code == 200:
                    oauth_data = oauth_response.json()
                    if oauth_data.get('code') == 0:
                        access_token = oauth_data['data']['access_token']
                        session_data["access_token"] = access_token
                        bot.save_session(session_data, username)
            except Exception:
                pass
                
    if not access_token:
        return jsonify({"success": False, "msg": "Could not retrieve Garena OAuth Access Token for validation."})
        
    res = bot.check_bind_info_native(access_token)
    return jsonify(res)

# ==================== STATELESS PUBLIC DIRECT GET APIs ====================

def authenticate_direct_bot():
    """Helper to stateless-authenticate and return valid Garena token from URL params"""
    uid = request.args.get("uid", "").strip()
    password = request.args.get("password", "").strip()
    
    if not uid or not password:
        return None, "Error: Missing bot query parameters. 'uid' and 'password' must be defined."
        
    token, err = bot.get_token_from_uid_password(uid, password)
    if err:
        return None, f"Garena Login Failure: {err}"
    return token, None

@app.route('/api/direct/profile')
def api_direct_profile():
    token, err = authenticate_direct_bot()
    if err:
        return jsonify({"success": False, "msg": err}), 401
        
    target_uid = request.args.get("target", "").strip()
    if not target_uid:
        target_uid = bot.decode_author_uid(token)
        
    res = bot.get_player_info_detailed(target_uid, token)
    return jsonify({
        "success": res.get("success", False),
        
        "profile": {
            "uid": res.get("uid"),
            "nickname": res.get("nickname"),
            "level": res.get("level"),
            "clan_id": res.get("clan_id"),
            "clan_name": res.get("clan_name"),
            "region": res.get("region"),
            "likes": res.get("likes"),
            "signature": res.get("signature"),
            "last_login": res.get("last_login"),
            "created_at": res.get("created_at")
        } if res.get("success") else None,
        
        "json_data": res.get("json_data"),
        "name_json_data": res.get("name_json_data")
    })

@app.route('/api/direct/friends')
def api_direct_friends():
    token, err = authenticate_direct_bot()
    if err:
        return jsonify({"success": False, "msg": err}), 401
        
    res = friend_list.get_active_friend_list(token)
    if res.get("success"):
        raw_proto_parsed = bot.parse_proto_bytes(res.get("friends_raw_bytes", b""))
        serializable_json = bot.make_serializable(raw_proto_parsed)
        return jsonify({
            "success": True,
            "friends": res["friends"],
            "json_data": serializable_json,
            "name_json_data": bot.map_proto_to_named(serializable_json, "Friend")
        })
    return jsonify(res)

@app.route('/api/direct/pending')
def api_direct_pending():
    token, err = authenticate_direct_bot()
    if err:
        return jsonify({"success": False, "msg": err}), 401
        
    res = pending_list.get_pending_request_list(token)
    if res.get("success"):
        enriched_requests = []
        for r in res["requests"]:
            p_res = bot.get_player_info_detailed(r["uid"], token)
            if p_res.get("success"):
                r["guild_name"] = p_res.get("clan_name", "No Guild")
                r["level"] = p_res.get("level", r["level"])
                avatar_id = p_res["json_data"]["1"]["12"] if (p_res.get("json_data") and "1" in p_res["json_data"]) else "902000003"
                r["avatar_id"] = str(avatar_id)
            enriched_requests.append(r)

        raw_proto_parsed = bot.parse_proto_bytes(res.get("pending_raw_bytes", b""))
        serializable_json = bot.make_serializable(raw_proto_parsed)
        return jsonify({
            "success": True,
            "requests": enriched_requests,
            "json_data": serializable_json,
            "name_json_data": bot.map_proto_to_named(serializable_json, "Player")
        })
    return jsonify(res)

@app.route('/api/direct/duo')
def api_direct_duo():
    token, err = authenticate_direct_bot()
    if err:
        return jsonify({"success": False, "msg": err}), 401
        
    target_uid = request.args.get("target", "").strip()
    if not target_uid:
        return jsonify({"success": False, "msg": "Missing query parameter 'target' UID."}), 400
        
    res = bot.check_duo_native(token, target_uid)
    if res.get("success"):
        partner_uid = res.get("partner_uid")
        
        target_profile = bot.get_player_info_detailed(target_uid, token)
        partner_profile = bot.get_player_info_detailed(partner_uid, token) if partner_uid else None
        
        res_data = {
            "success": True,
            
            "duo_info": {
                "Level": res.get("level"),
                "Score": res.get("score"),
                "Active Days": res.get("days_active"),
                "Formed On": res.get("formed_on"),
                "Status": res.get("status"),
                "Partner UID": partner_uid
            },
            
            "target_profile": target_profile,
            "partner_profile": partner_profile,
            "json_data": res.get("json_data"),
            "name_json_data": res.get("name_json_data")
        }
        
        return jsonify(res_data)
    return jsonify(res)

@app.route('/api/direct/guild/info')
def api_direct_guild_info():
    token, err = authenticate_direct_bot()
    if err:
        return jsonify({"success": False, "msg": err}), 401
        
    clan_id = request.args.get("clan_id", "").strip()
    if not clan_id:
        return jsonify({"success": False, "msg": "Missing parameter 'clan_id'."}), 400
        
    res_raw = guild_info.get_clan_info_by_id(token, clan_id)
    return jsonify(res_raw)

@app.route('/api/direct/guild/members')
def api_direct_guild_members():
    token, err = authenticate_direct_bot()
    if err:
        return jsonify({"success": False, "msg": err}), 401
        
    clan_id = request.args.get("clan_id", "").strip()
    if not clan_id:
        return jsonify({"success": False, "msg": "Missing parameter 'clan_id'."}), 400
        
    res = member_list.get_guild_member_list(token, clan_id)
    if res.get("success"):
        safe_res = {
            "success": True,
            "leader": res.get("leader"),
            "acting_leader": res.get("acting_leader"),
            "officers": res.get("officers"),
            "members": res.get("members"),
            "total_members": res.get("total_members")
        }
        raw_proto_parsed = bot.parse_proto_bytes(res.get("members_raw_bytes", b""))
        serializable_json = bot.make_serializable(raw_proto_parsed)
        safe_res["json_data"] = serializable_json
        safe_res["name_json_data"] = bot.map_proto_to_named(serializable_json, "Guild")
        
        return jsonify(safe_res)
    return jsonify(res)

# ==================== PUBLIC ACTION DIRECT APIs ====================

@app.route('/api/direct/friends/add')
def api_direct_friends_add():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    target = request.args.get("target", "").strip()
    if not target: return jsonify({"success": False, "msg": "Query parameter 'target' UID is required."}), 400
    success = add_friend.add_target_friend(token, target)
    return jsonify({"success": success, "msg": "Friend request sent." if success else "Action failed."})

@app.route('/api/direct/friends/remove')
def api_direct_friends_remove():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    target = request.args.get("target", "").strip()
    if not target: return jsonify({"success": False, "msg": "Query parameter 'target' UID is required."}), 400
    success = remove_friend.delete_active_friend(token, target)
    return jsonify({"success": success, "msg": "Friend deleted." if success else "Action failed."})

@app.route('/api/direct/friends/accept')
def api_direct_friends_accept():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    target = request.args.get("target", "").strip()
    if not target: return jsonify({"success": False, "msg": "Query parameter 'target' UID is required."}), 400
    success = accept_request.accept_friend_request(token, target)
    return jsonify({"success": success, "msg": "Request accepted." if success else "Action failed."})

@app.route('/api/direct/friends/reject')
def api_direct_friends_reject():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    target = request.args.get("target", "").strip()
    if not target: return jsonify({"success": False, "msg": "Query parameter 'target' UID is required."}), 400
    success = reject_request.reject_friend_request(token, target)
    return jsonify({"success": success, "msg": "Request rejected." if success else "Action failed."})

@app.route('/api/direct/guild/join')
def api_direct_guild_join():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    clan_id = request.args.get("clan_id", "").strip()
    if not clan_id: return jsonify({"success": False, "msg": "Query parameter 'clan_id' is required."}), 400
    success = join_guild.request_join_clan(token, clan_id)
    return jsonify({"success": success, "msg": "Join request submitted." if success else "Action failed."})

@app.route('/api/direct/guild/leave')
def api_direct_guild_leave():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    clan_id = request.args.get("clan_id", "").strip()
    if not clan_id: return jsonify({"success": False, "msg": "Query parameter 'clan_id' is required."}), 400
    success = leave_guild.quit_current_clan(token, clan_id)
    return jsonify({"success": success, "msg": "Successfully left the guild." if success else "Action failed."})

@app.route('/api/direct/bot/nickname')
def api_direct_bot_nickname():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    nickname = request.args.get("nickname", "").strip()
    if not nickname: return jsonify({"success": False, "msg": "Query parameter 'nickname' is required."}), 400
    res = bot.change_nickname_native(token, nickname)
    return jsonify(res)

@app.route('/api/direct/bot/bio')
def api_direct_bot_bio():
    token, err = authenticate_direct_bot()
    if err: return jsonify({"success": False, "msg": err}), 401
    bio = request.args.get("bio", "").strip()
    if not bio: return jsonify({"success": False, "msg": "Query parameter 'bio' is required."}), 400
    res = bot.update_bio_native(token, bio)
    return jsonify(res)

# ==================== USER MANAGEMENT OWNER CORE PANEL ====================

@app.route('/api/users/list')
def api_users_list():
    if session.get("role") != "owner":
        return jsonify({"success": False, "msg": "Unauthorized access."}), 403
    
    members = load_members()
    users = []
    for username, p in members.items():
        bots = get_user_bots(username)
        users.append({
            "name": p.get("name", "Operator"),
            "username": username,
            "password": p.get("password", ""),
            "role": p.get("role", "user"),
            "limit": p.get("limit", 5),
            "bots_count": len(bots)
        })
    return jsonify({"success": True, "users": users})

@app.route('/api/users/add', methods=['POST'])
def api_users_add():
    if session.get("role") != "owner":
        return jsonify({"success": False, "msg": "Unauthorized."}), 403
        
    data = request.json or {}
    name = str(data.get("name", "Operator")).strip()
    u = str(data.get("username", "")).strip().lower()
    p = str(data.get("password", "")).strip()
    r = str(data.get("role", "user")).strip()
    l = int(data.get("limit", 5))
    
    if not u or not p:
        return jsonify({"success": False, "msg": "Credentials missing."})
        
    members = load_members()
    members[u] = {
        "name": name,
        "username": u,
        "password": p,
        "role": r,
        "limit": l
    }
    save_members(members)
    get_user_dir(u)
    return jsonify({"success": True, "msg": f"Account {u} saved!"})

@app.route('/api/users/delete', methods=['POST'])
def api_users_delete():
    if session.get("role") != "owner":
         return jsonify({"success": False, "msg": "Unauthorized."}), 403
         
    data = request.json or {}
    u = str(data.get("username", "")).strip().lower()
    
    if u == session.get("username"):
        return jsonify({"success": False, "msg": "Self-deletion is write-protected!"})
        
    try:
        if members_col is not None:
            members_col.delete_one({"username": u})
        if bots_col is not None:
            bots_col.delete_many({"owner_username": u})
        if db is not None:
            db["sessions"].delete_many({"username": u})
            db["profile_cache"].delete_many({"username": u})
            
        return jsonify({"success": True, "msg": f"User account and all database records for {u} wiped."})
    except Exception as e:
        return jsonify({"success": False, "msg": f"Database wipe failed: {str(e)}"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=30284, debug=False, threaded=True)