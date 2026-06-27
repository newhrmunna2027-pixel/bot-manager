# -*- coding: utf-8 -*-
# bot.py - Central Garena Authentication, Core Protobuf Mapping & EAT-to-JWT Engine (OB54 Patched with MongoDB Integration)

import os
import re
import hmac
import hashlib
import json
import random
import requests
import jwt
import urllib3
import secrets
import base64
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from pymongo import MongoClient

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# === MONGODB DATABASE CONFIGURATION     ===
# ==========================================
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://munnadhali017_db_user:m0172326@cluster0.beetmpq.mongodb.net/?appName=Cluster0")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["garena_manager"]
    sessions_col = db["sessions"]
    profile_cache_col = db["profile_cache"]
except Exception as e:
    print(f"[*] MongoDB connection warning: {str(e)}")
    sessions_col = None
    profile_cache_col = None

# Standard Garena AES Keys
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'

DEV = {
    "os": "Android OS 13 / API-33",
    "os_ver_only": "Android 13",
    "operator": "Banglalink",
    "width": 1440,
    "height": 3216,
    "dpi": "520",
    "cpu_long": "Qualcomm Snapdragon 888 | 8 cores",
    "ram": 12288,
    "gpu": "Adreno (TM) 660",
    "opengl": "OpenGL ES 3.2 V@512.0"
}

BASE_URLS = {
    "IND": "https://client.ind.freefiremobile.com/",
    "ID": "https://clientbp.ggpolarbear.com/",
    "BR": "https://client.us.freefiremobile.com/",
    "ME": "https://clientbp.ggpolarbear.com/",
    "VN": "https://clientbp.ggpolarbear.com/",
    "TH": "https://clientbp.ggpolarbear.com/",
    "CIS": "https://clientbp.ggpolarbear.com/",
    "BD": "https://clientbp.ggpolarbear.com/",
    "PK": "https://clientbp.ggpolarbear.com/",
    "SG": "https://clientbp.ggpolarbear.com/",
    "SAC": "https://client.us.freefiremobile.com/",
    "TW": "https://clientbp.ggpolarbear.com/",
    "US": "https://client.na.freefiremobile.com/",
    "NA": "https://client.na.freefiremobile.com/"
}

# SCHEMA MAPPINGS FOR PROTOBUF TO FRIENDLY NAMED DICTIONARIES
TAG_MAPPINGS = {
    "Player": {
        1: "account_uid", 
        3: "nickname", 
        5: "region", 
        6: "level", 
        7: "experience",
        11: "banner_id",   
        12: "head_pic_id",  
        14: "br_rank",
        15: "ranking_points",
        18: "badge_count",
        21: "likes", 
        24: "last_login_ts", 
        29: "guild_name", 
        41: "guild_metadata",
        44: "create_ts",
        63: "guild_id"
    },
    "Friend": {
        1: "account_uid", 
        2: "role_status",
        3: "nickname", 
        6: "region", 
        8: "level",       
        9: "experience",  
        29: "guild_name", 
        57: "game_version",
        63: "guild_id"
    },
    "Guild": {
        1: "clan_id", 
        2: "clan_name", 
        3: "created_at_ts", 
        4: "leader_uid", 
        5: "level", 
        6: "max_members", 
        7: "total_members", 
        12: "welcome_message", 
        13: "region", 
        15: "officers_list",
        16: "past_glory",
        23: "acting_leader_uid",
        36: "total_glory", 
        37: "recent_glory"
    },
    "Duo": {
        1: "partner_uid",
        3: "score",
        4: "formed_on_ts",
        5: "active_days",
        6: "status_code"
    }
}

def map_proto_to_named(parsed_dict, schema_type):
    mapping = TAG_MAPPINGS.get(schema_type, {})
    named_dict = {}
    if not isinstance(parsed_dict, dict):
        return parsed_dict
        
    for k, v in parsed_dict.items():
        try:
            tag_num = int(k)
            field_name = mapping.get(tag_num, f"tag_{tag_num}")
            if isinstance(v, dict):
                named_dict[field_name] = map_proto_to_named(v, schema_type)
            elif isinstance(v, list):
                named_dict[field_name] = [map_proto_to_named(item, schema_type) if isinstance(item, dict) else item for item in v]
            else:
                named_dict[field_name] = v
        except:
            named_dict[str(k)] = v
    return named_dict

# Cryptography helper routines
def E_AEs(pc):
    Z = bytes.fromhex(pc)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(Z, AES.block_size))

def encrypt_message(data_bytes):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data_bytes, AES.block_size))

def encrypt_message_hex(data_bytes):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    encrypted = cipher.encrypt(pad(data_bytes, AES.block_size))
    return encrypted.hex()

def encrypt_api(plain_text):
    plain_text = bytes.fromhex(plain_text)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    cipher_text = cipher.encrypt(pad(plain_text, AES.block_size))
    return cipher_text.hex()

def YOuR_FaThER(uid):
    n = int(uid)
    res = bytearray()
    while n >= 0x80:
        res.append((n & 0x7f) | 0x80)
        n >>= 7
    res.append(n)
    payload_bytes = b"\x08" + bytes(res)
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(payload_bytes, 16))

def UNknown(d):
    try:
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        return unpad(cipher.decrypt(d), 16)
    except:
        return d

# Protobuf Utility Encoders/Decoders
def enc_vr_sync(N):
    if N < 0: return b''
    H = []
    while True:
        byte = N & 0x7F
        N >>= 7
        if N: byte |= 0x80
        H.append(byte)
        if not N: break
    return bytes(H)

def create_variant_sync(field_number, value):
    return enc_vr_sync((field_number << 3) | 0) + enc_vr_sync(value)

def create_length_sync(field_number, value):
    encoded_value = value.encode('utf-8') if isinstance(value, str) else bytes(value)
    return enc_vr_sync((field_number << 3) | 2) + enc_vr_sync(len(encoded_value)) + encoded_value

def create_proto_sync(fields):
    packet = bytearray()
    for field in sorted(fields.keys()):
        value = fields[field]
        if isinstance(value, dict):
            nested = create_proto_sync(value)
            packet.extend(create_length_sync(field, nested))
        elif isinstance(value, int):
            packet.extend(create_variant_sync(field, value))
        elif isinstance(value, str) or isinstance(value, bytes):
            packet.extend(create_length_sync(field, value))
    return bytes(packet)

def decode_varint(buf, pos):
    result = 0
    shift = 0
    while pos < len(buf):
        byte = buf[pos]
        result |= (byte & 0x7F) << shift
        pos += 1
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos

def parse_proto_bytes(data: bytes):
    result = {}
    pos = 0
    while pos < len(data):
        try:
            tag, pos = decode_varint(data, pos)
        except IndexError:
            break
        field_number = tag >> 3
        wire_type = tag & 0x07
        
        val = None
        if wire_type == 0:
            val, pos = decode_varint(data, pos)
        elif wire_type == 1:
            val = int.from_bytes(data[pos:pos+8], 'little')
            pos += 8
        elif wire_type == 2:
            length, pos = decode_varint(data, pos)
            val = data[pos:pos+length]
            pos += length
        elif wire_type == 5:
            val = int.from_bytes(data[pos:pos+4], 'little')
            pos += 4
        else:
            break
            
        if val is not None:
            if field_number in result:
                if isinstance(result[field_number], list):
                    result[field_number].append(val)
                else:
                    result[field_number] = [result[field_number], val]
            else:
                result[field_number] = val
    return result

def get_base_url(region):
    return BASE_URLS.get(region.upper(), "https://clientbp.ggpolarbear.com/")

def decode_author_uid(token):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return str(decoded.get("account_id") or decoded.get("sub"))
    except:
        return None

def get_server_from_token(token):
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        return decoded.get("lock_region", "BD").upper()
    except:
        return "BD"

# ==========================================
# === GARENA AUTHENTICATION SERVICES     ===
# ==========================================

# 🟢 Method A: Standard Guest ID & Password Login Flow
def get_token_from_uid_password(uid, password):
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
        if oauth_response.status_code != 200:
            return None, f"OAuth failed: {oauth_response.status_code}"
            
        oauth_data = oauth_response.json()
        if oauth_data.get('code') != 0:
            return None, f"Garena API Error: {oauth_data}"

        access_token = oauth_data['data']['access_token']
        open_id = oauth_data['data'].get('open_id', '')
        
        platforms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        for platform_type in platforms:
            result = try_platform_login(open_id, access_token, platform_type)
            if result and result.get('token'):
                return result['token'], None
        
        return None, "Login successful but JWT generation failed on all platforms"
    except Exception as e:
        return None, str(e)

# 🟢 Method B: Garena EAT Token Authentication, Inspection & Conversion Flow
def get_tokens_from_eat_inspect(eat_token):
    try:
        callback_url = f"https://api-otrss.garena.com/support/callback/?access_token={eat_token}"
        headers = {
            "Host": "api-otrss.garena.com",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }
        
        response = requests.get(callback_url, headers=headers, verify=False, timeout=10, allow_redirects=False)
        
        access_token = None
        redirect_url = response.headers.get('Location', '')
        match = re.search(r'access_token=([^&]+)', redirect_url)
        if match:
            access_token = match.group(1)
            
        if not access_token and response.status_code == 200:
            match_body = re.search(r'["\']access_token["\']\s*:\s*["\']([^"\']+)["\']', response.text.replace('\\"', '"'))
            if match_body:
                access_token = match_body.group(1)
                
        if not access_token:
            return None, None, "Could not extract OAuth Access Token from Garena Callback."

        inspect_url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
        inspect_response = requests.get(inspect_url, verify=False, timeout=10)
        
        if inspect_response.status_code == 200:
            data = inspect_response.json()
            if 'open_id' in data:
                return access_token, str(data['open_id']), None
            else:
                return None, None, "Open ID not found in Garena token registry."
        else:
            return None, None, f"Garena token inspect failed with status code: {inspect_response.status_code}"
    except Exception as e:
        return None, None, f"Inspection error: {str(e)}"

def get_token_from_eat_flow(eat_token):
    access_token, open_id, error = get_tokens_from_eat_inspect(eat_token)
    if error or not access_token or not open_id:
        return None, None, None, None, error
        
    try:
        platforms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        for platform_type in platforms:
            result = try_platform_login(open_id, access_token, platform_type)
            if result and result.get('token'):
                jwt_token = result['token']
                uid = decode_author_uid(jwt_token)
                return jwt_token, access_token, open_id, uid, None
                
        return None, None, None, None, "EAT Token inspect successful, but Game JWT session generation failed."
    except Exception as e:
        return None, None, None, None, f"Decryption session exception: {str(e)}"

# Garena Game Server Platforms Bridge Endpoint
def try_platform_login(open_id, access_token, platform_type):
    try:
        fields = {
            3: "2024-12-05 18:15:32",
            4: "free fire",
            5: 1,
            7: "1.126.1",
            8: f"{DEV['os']} ({DEV['os_ver_only']})",
            9: "Handheld",
            10: DEV["operator"],
            11: "WIFI",
            12: DEV["width"],
            13: DEV["height"],
            14: DEV["dpi"],
            15: DEV["cpu_long"],
            16: DEV["ram"],
            17: DEV["gpu"],
            18: DEV["opengl"],
            19: f"Google|{random.randint(10000000, 99999999)}-a7d5-4cb6-8d7e-3b0e448a0c57",
            20: "223.191.51.89",
            21: "en",
            22: open_id,
            29: access_token,
            24: int(platform_type),
            99: str(platform_type),
            100: str(platform_type)
        }
        
        serialized_data = create_proto_sync(fields)
        encrypted_data = E_AEs(serialized_data.hex())

        url = "https://loginbp.ggpolarbear.com/MajorLogin"
        headers = {
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54"
        }
        
        response = requests.post(url, data=encrypted_data, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            parsed_res = parse_proto_bytes(response.content)
            token_bytes = parsed_res.get(8)
            if token_bytes:
                token_value = token_bytes.decode('utf-8', errors='ignore') if isinstance(token_bytes, bytes) else str(token_bytes)
                return {"token": token_value}
        return None
    except Exception:
        return None

# ====================================================
# === SESSION LOADER & STATE MANAGEMENT (MONGO DB) ===
# ====================================================

def load_session(username=None):
    user_key = username if username else "default_global_user"
    if sessions_col is None:
        return {}
    try:
        doc = sessions_col.find_one({"username": user_key})
        if doc:
            doc.pop("_id", None)  # Removing MongoDB internal key for compatibility
            return doc
    except Exception as e:
        print(f"[*] MongoDB load_session fault: {str(e)}")
    return {}

def save_session(data, username=None):
    user_key = username if username else "default_global_user"
    if sessions_col is None:
        return
    try:
        data_to_save = dict(data)
        data_to_save["username"] = user_key
        sessions_col.update_one(
            {"username": user_key},
            {"$set": data_to_save},
            upsert=True
        )
    except Exception as e:
        print(f"[*] MongoDB save_session fault: {str(e)}")

def get_active_token(username=None):
    session_data = load_session(username)
    uid = session_data.get("uid")
    password = session_data.get("password")
    token = session_data.get("token")
    eat_token = session_data.get("eat_token")
    
    if token:
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp = decoded.get("exp", 0)
            if exp > datetime.utcnow().timestamp() + 300:
                return token, None
        except:
            pass
            
    if eat_token:
        new_token, access_token, open_id, decoded_uid, error = get_token_from_eat_flow(eat_token)
        if not error:
            session_data["token"] = new_token
            session_data["access_token"] = access_token
            session_data["open_id"] = open_id
            session_data["uid"] = str(decoded_uid)
            save_session(session_data, username)
            return new_token, None
            
    if uid and password:
        new_token, error = get_token_from_uid_password(uid, password)
        if error:
            return None, f"Dynamic credentials renewal failed: {error}"
            
        session_data["token"] = new_token
        session_data["uid"] = str(uid)
        save_session(session_data, username)
        return new_token, None
        
    return None, "Owner token context expired. Please re-authorize Garena credentials."

# ==========================================
# === FIELD DECODERS & HELPER FUNCTIONS ===
# ==========================================

def safe_get_bytes(val):
    if not val: return None
    if isinstance(val, list):
        for item in val:
            if isinstance(item, bytes): return item
    if isinstance(val, bytes): return val
    return None

def decode_field_str(val):
    if isinstance(val, bytes):
        return val.decode('utf-8', errors='ignore')
    if isinstance(val, list) and len(val) > 0:
        first = val[0]
        return first.decode('utf-8', errors='ignore') if isinstance(first, bytes) else str(first)
    return str(val) if val is not None else ""

def decode_field_int(val, default=0):
    if isinstance(val, int): return val
    if isinstance(val, list) and len(val) > 0:
        first = val[0]
        try: return int(first)
        except: return default
    try: return int(val)
    except: return default

def is_printable_text(b):
    try:
        if len(b) < 150:
            decoded = b.decode('utf-8')
            printable_count = sum(1 for c in decoded if c.isprintable() or c in "\r\n\t")
            if printable_count / len(decoded) > 0.75:
                return True
    except: pass
    return False

def make_serializable(d):
    if isinstance(d, dict):
        return {str(k): make_serializable(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [make_serializable(x) for x in d]
    elif isinstance(d, bytes):
        if is_printable_text(d):
            return d.decode('utf-8', errors='ignore')
        try:
            parsed = parse_proto_bytes(d)
            if parsed: return make_serializable(parsed)
        except: pass
        try: return d.decode('utf-8', errors='ignore')
        except: return d.hex()
    return d

# ==========================================
# === CORE GARENA API GAME ACTIONS       ===
# ==========================================

def get_clan_name_direct(token, clan_id):
    try:
        import gzip
        region = get_server_from_token(token)
        base_url = get_base_url(region)
        url = base_url + "GetClanInfoByClanID"
        
        serialized = create_proto_sync({1: int(clan_id), 2: 1})
        encrypted = E_AEs(serialized.hex())
        
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/octet-stream",
            "Host": base_url.split("//")[1].rstrip("/"),
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        
        resp = requests.post(url, headers=headers, data=encrypted, timeout=10, verify=False)
        if resp.status_code == 200:
            content = resp.content
            if content.startswith(b'\x1f\x8b'):
                content = gzip.decompress(content)
            parsed = parse_proto_bytes(content)
            clan_name_bytes = parsed.get(2)
            if clan_name_bytes:
                return decode_field_str(clan_name_bytes).strip()
    except: pass
    return "N/A"

def get_player_info_detailed(target_uid, token):
    try:
        region = get_server_from_token(token)
        endpoint = get_base_url(region) + "GetPlayerPersonalShow"
        
        protobuf_data = create_proto_sync({1: int(target_uid), 2: 1})
        encrypted_data = encrypt_message_hex(protobuf_data)

        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB54"
        }
        
        res = requests.post(endpoint, data=bytes.fromhex(encrypted_data), headers=headers, timeout=12, verify=False)
        if res.status_code != 200:
            return {"success": False, "message": f"HTTP Status {res.status_code}"}
            
        parsed_outer = parse_proto_bytes(res.content)
        basic_bytes = safe_get_bytes(parsed_outer.get(1))
        if not basic_bytes:
            return {"success": False, "message": "Player basic info segment not found."}
            
        parsed_basic = parse_proto_bytes(basic_bytes)
        
        uid_val = parsed_basic.get(1, 0)
        name_val = decode_field_str(parsed_basic.get(3))
        lvl_val = decode_field_int(parsed_basic.get(6), 1)
        
        guild_name = decode_field_str(parsed_basic.get(29)).strip()
        if not guild_name or guild_name == "No Guild" or guild_name == "":
            tag_41_bytes = parsed_basic.get(41)
            if isinstance(tag_41_bytes, bytes):
                tag_41_parsed = parse_proto_bytes(tag_41_bytes)
                g_bytes = tag_41_parsed.get(5, b"No Guild")
                guild_name = g_bytes.decode('utf-8', errors='ignore') if isinstance(g_bytes, bytes) else str(g_bytes)

        likes_val = decode_field_int(parsed_basic.get(21))
        last_login_ts = decode_field_str(parsed_basic.get(24))
        create_ts = decode_field_str(parsed_basic.get(44))
        region_str = decode_field_str(parsed_basic.get(5))

        clan_id = "0"
        leader_uid = "N/A"
        
        clan_bytes = safe_get_bytes(parsed_outer.get(6))
        if clan_bytes:
            parsed_clan = parse_proto_bytes(clan_bytes)
            clan_id = decode_field_str(parsed_clan.get(1))
            guild_name = decode_field_str(parsed_clan.get(2))
            leader_uid = decode_field_str(parsed_clan.get(3))
            if not clan_id or clan_id == "": clan_id = "0"

        signature = "No Signature"
        social_bytes = safe_get_bytes(parsed_outer.get(9))
        if social_bytes:
            parsed_social = parse_proto_bytes(social_bytes)
            signature = decode_field_str(parsed_social.get(9))

        def format_unix(ts):
            try:
                if not ts or ts == "0" or ts == "": return "N/A"
                return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
            except: return "N/A"

        created_time = format_unix(create_ts)
        last_login_time = format_unix(last_login_ts)

        if clan_id != "0" and (guild_name == "N/A" or guild_name == "" or guild_name == "No Guild"):
            guild_name = get_clan_name_direct(token, clan_id)

        raw_json_tree = make_serializable(parsed_outer)

        return {
            "success": True,
            "uid": str(uid_val),
            "nickname": name_val.strip(),
            "level": int(lvl_val),
            "likes": int(likes_val),
            "region": region_str.strip(),
            "clan_id": clan_id,
            "clan_name": guild_name.strip() if guild_name else "No Guild",
            "leader_uid": leader_uid if leader_uid else "N/A",
            "signature": signature.strip() if signature else "No Signature",
            "created_at": created_time,
            "last_login": last_login_time,
            "raw_data": res.content.hex(), 
            "json_data": raw_json_tree,
            "name_json_data": map_proto_to_named(raw_json_tree, "Player")
        }
    except Exception as e:
        return {"success": False, "message": str(e)}

def update_bio_native(token, bio_text):
    try:
        region = get_server_from_token(token)
        base_url = get_base_url(region)
        url = f"{base_url}UpdateSocialBasicInfo"
        
        bio_bytes = bio_text.encode('utf-8')
        bio_len = len(bio_bytes)
        
        field_2 = b'\x10\x11'
        field_5 = b'\x2A\x00'
        field_6 = b'\x32\x00'
        field_8 = b'\x42' + enc_vr_sync(bio_len) + bio_bytes
        field_9 = b'\x48\x01'
        field_11 = b'\x5A\x00'
        field_12 = b'\x62\x00'
        
        proto_data = field_2 + field_5 + field_6 + field_8 + field_9 + field_11 + field_12
        encrypted = E_AEs(proto_data.hex())
        
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        
        res = requests.post(url, headers=headers, data=encrypted, timeout=12, verify=False)
        if res.status_code == 200:
            return {"success": True, "message": "Signature changed successfully!"}
        return {"success": False, "message": f"Server status: {res.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def check_duo_native(token, target_uid):
    try:
        region = get_server_from_token(token)
        base_url = get_base_url(region)
        url = f"{base_url}GetSpecialFriendList"
        
        payload = YOuR_FaThER(target_uid)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Connection": "Keep-Alive"
        }
        
        res = requests.post(url, headers=headers, data=payload, timeout=12, verify=False)
        if res.status_code == 200:
            decrypted = UNknown(res.content)
            parsed_outer = parse_proto_bytes(decrypted)
            
            duo_bytes = parsed_outer.get(1)
            if not duo_bytes or not isinstance(duo_bytes, bytes):
                return {"success": False, "message": "No Dynamic Duo info found for this player."}
                
            duo_parsed = parse_proto_bytes(duo_bytes)
            partner_uid = duo_parsed.get(1, 0)
            score = duo_parsed.get(3, 0)
            creation_ts = duo_parsed.get(4, 0)
            days_active = duo_parsed.get(5, 0)
            status_code = duo_parsed.get(6, 0)
            
            lvl = 1
            if score >= 1201: lvl = 6
            elif score >= 801: lvl = 5
            elif score >= 501: lvl = 4
            elif score >= 301: lvl = 3
            elif score >= 101: lvl = 2
            
            status_str = "Active" if status_code == 2 else "Inactive"
            creation_time = datetime.fromtimestamp(creation_ts).strftime('%B %d, %Y')
            
            raw_tree = make_serializable(duo_parsed)
            
            return {
                "success": True,
                "partner_uid": str(partner_uid),
                "level": lvl,
                "score": score,
                "days_active": days_active,
                "formed_on": creation_time,
                "status": status_str,
                "raw_data": decrypted.hex(),
                "json_data": raw_tree,
                "name_json_data": map_proto_to_named(raw_tree, "Duo")
            }
        elif res.status_code == 500:
            return {"success": False, "message": "Private profile or invalid player UID."}
        return {"success": False, "message": f"Server returned error code: {res.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def change_nickname_native(token, new_name):
    try:
        nickname_bytes = new_name.encode('utf-8')
        serialized = b''
        serialized += bytes([(1 << 3) | 2])
        serialized += enc_vr_sync(len(nickname_bytes))
        serialized += nickname_bytes
        serialized += bytes([(2 << 3) | 0])
        serialized += enc_vr_sync(random.randint(10000000, 99999999))
        
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        encrypted = cipher.encrypt(pad(serialized, AES.block_size))
        
        url = "https://loginbp.ggblueshark.com/MajorModifyNickname"
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Content-Type': "application/octet-stream",
            'Authorization': f"Bearer {token}",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB54"
        }
        
        res = requests.post(url, data=encrypted, headers=headers, timeout=12, verify=False)
        if res.status_code == 200:
            return {"success": True, "message": f"Nickname successfully modified to '{new_name}'"}
        else:
            try:
                err_msg = res.content.decode('utf-8').strip()
                return {"success": False, "message": err_msg if err_msg else f"HTTP Status: {res.status_code}"}
            except:
                return {"success": False, "message": f"HTTP Error {res.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def refresh_self_profile_cache(token, username=None):
    try:
        author_uid = decode_author_uid(token)
        if not author_uid: return None
        res = get_player_info_detailed(author_uid, token)
        if res.get("success"):
            profile_data = {
                "uid": res["uid"],
                "nickname": res["nickname"],
                "level": res["level"],
                "clan_id": res["clan_id"],
                "clan_name": res["clan_name"],
                "region": res["region"],
                "likes": res["likes"],
                "signature": res["signature"],
                "last_login": res["last_login"],
                "created_at": res["created_at"]
            }
            user_key = username if username else "default_global_user"
            if profile_cache_col is not None:
                try:
                    profile_data["username"] = user_key
                    profile_cache_col.update_one(
                        {"username": user_key},
                        {"$set": profile_data},
                        upsert=True
                    )
                except Exception as db_err:
                    print(f"[*] MongoDB profile_cache save error: {str(db_err)}")
            return profile_data
    except Exception as e:
        print(f"[*] Profile caching fault: {str(e)}")
    return None

# ==========================================================
# === OWNER-ONLY SECURE GARENA SECURITY BIND CHECKER     ===
# ==========================================================

def check_bind_info_native(access_token):
    url = "https://100067.connect.garena.com/game/account_security/bind:get_bind_info"
    
    payload = {
        'app_id': "100067", 
        'access_token': access_token
    }
    
    headers = {
        'Host': "100067.connect.garena.com",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'X-Device-OS': DEV["os"],
        'X-Device-Operator': DEV["operator"],
        'ReleaseVersion': "OB54",
        'X-GA': "v1 1",
        'X-Unity-Version': "2018.4.11f1"
    }
    
    try:
        response = requests.get(url, params=payload, headers=headers, verify=False, timeout=15)
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "email": data.get("email", ""),
                "email_to_be": data.get("email_to_be", ""),
                "countdown": data.get("request_exec_countdown", 0)
            }
        else:
            return {"success": False, "msg": f"Garena Server responded with status code: {response.status_code}"}
    except Exception as e:
        return {"success": False, "msg": f"Network Gateway timeout: {str(e)}"}