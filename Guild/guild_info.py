# -*- coding: utf-8 -*-
# Guild/guild_info.py - Fetch Guild General Details via Confirmed Garena Mappings

import requests
import gzip
from datetime import datetime
import bot

def get_clan_info_by_id(token, clan_id):
    try:
        region = bot.get_server_from_token(token)
        base_url = bot.get_base_url(region)
        
        serialized = bot.create_proto_sync({1: int(clan_id), 2: 1})
        encrypted = bot.E_AEs(serialized.hex())
        url = base_url + "GetClanInfoByClanID"
        
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
        
        resp_http = requests.post(url, headers=headers, data=encrypted, timeout=15, verify=False)
        if resp_http.status_code != 200:
            return {"success": False, "message": f"HTTP Response Status: {resp_http.status_code}"}
            
        content = resp_http.content
        if content.startswith(b'\x1f\x8b'):
            content = gzip.decompress(content)
            
        parsed = bot.parse_proto_bytes(content)
        
        # ১০০% কনফার্মড ফিল্ড ডিকোডিং (ইউজার ভ্যালিডেটেড)
        id_val = bot.decode_field_int(parsed.get(1))
        name_val = bot.decode_field_str(parsed.get(2))
        ts_created = bot.decode_field_int(parsed.get(3))
        leader_uid = bot.decode_field_str(parsed.get(4))
        level_val = bot.decode_field_int(parsed.get(5))
        max_members = bot.decode_field_int(parsed.get(6))
        total_members = bot.decode_field_int(parsed.get(7))
        welcome_msg = bot.decode_field_str(parsed.get(12))
        region_val = bot.decode_field_str(parsed.get(13))
        
        # Officers UID parsing (Tag 15)
        officers_list = []
        off_val = parsed.get(15)
        if isinstance(off_val, list):
            for o in off_val:
                officers_list.append(str(o))
        elif off_val:
            officers_list.append(str(off_val))
            
        past_glory = bot.decode_field_int(parsed.get(16))
        acting_leader = bot.decode_field_str(parsed.get(23))
        total_glory = bot.decode_field_int(parsed.get(36))
        recent_glory = bot.decode_field_int(parsed.get(37))
        
        def format_ts(x):
            try:
                if not x: return "N/A"
                return datetime.fromtimestamp(int(x)).strftime('%Y-%m-%d %H:%M:%S')
            except:
                return "N/A"
                
        info_dict = {
            "clan_id": str(id_val),
            "clan_name": name_val.strip(),
            "created_at": format_ts(ts_created),
            "leader_uid": leader_uid if leader_uid else "N/A",
            "level": level_val,
            "max_members": max_members,
            "total_members": total_members,
            "welcome_message": welcome_msg.strip(),
            "region": region_val.strip() if region_val else region,
            "officer_uids": officers_list,
            "past_glory": past_glory,
            "acting_leader_uid": acting_leader if acting_leader else "N/A",
            "total_glory": total_glory,
            "recent_glory": recent_glory
        }
        return {
            "success": True, 
            "guild_info": info_dict
        }
    except Exception as e:
        return {"success": False, "message": str(e)}