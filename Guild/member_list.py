# -*- coding: utf-8 -*-
# Guild/member_list.py - Fetch Guild Full Member List with Fixed Glory Mapping & Raw Bytes pass-through

import requests
import bot

def get_guild_member_list(token, clan_id):
    try:
        region = bot.get_server_from_token(token)
        base_url = bot.get_base_url(region)
        
        req_bytes = bot.create_proto_sync({1: int(clan_id)})
        encrypted = bot.E_AEs(req_bytes.hex())
        url = base_url + "GetClanMembers"

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Unity-Version": "2022.3.47f1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "Host": base_url.split("//")[1].rstrip("/"),
            "Accept-Encoding": "gzip, deflate",
            "X-GA": "v1 1",
        }

        resp = requests.post(url, headers=headers, data=encrypted, timeout=15, verify=False)
        if resp.status_code != 200:
            return {"success": False, "message": f"HTTP Status: {resp.status_code}"}

        parsed = bot.parse_proto_bytes(resp.content)
        entries_list = parsed.get(1, [])
        if not isinstance(entries_list, list):
            entries_list = [entries_list]
            
        leader = None
        acting_leader = None
        officers = []
        members = []
        
        def decode_str(b_data):
            if isinstance(b_data, bytes):
                return b_data.decode('utf-8', errors='ignore')
            return str(b_data)

        for entry_bytes in entries_list:
            if not isinstance(entry_bytes, bytes): continue
            entry = bot.parse_proto_bytes(entry_bytes)
            
            info_bytes = entry.get(1)
            if not info_bytes or not isinstance(info_bytes, bytes): continue
            info = bot.parse_proto_bytes(info_bytes)
            
            uid_val = info.get(1, 0)
            name_val = decode_str(info.get(3, b"Unknown"))
            
            # 🟢 Correct Member Garena Level (Tag 6) & Avatar (Tag 12) Mapping
            lvl_val = bot.decode_field_int(info.get(6), 1)
            avatar_id = bot.decode_field_int(info.get(12), 902000003)
            
            role_code = entry.get(4, 0)
            
            # 🟢 Fixed Glory Mapping: Tag 10 is Weekly Glory, Tag 11 is Total Glory
            total_glory = entry.get(11, 0)
            weekly_glory = entry.get(10, 0)
            
            member_data = {
                "uid": str(uid_val),
                "name": name_val.strip(),
                "level": int(lvl_val),
                "avatar_id": str(avatar_id),
                "total_glory": int(total_glory),
                "weekly_glory": int(weekly_glory),
                "role_code": int(role_code)
            }
            
            if role_code == 3:
                leader = member_data
            elif role_code == 4:
                acting_leader = member_data
            elif role_code == 2:
                officers.append(member_data)
            else:
                members.append(member_data)
                
        # Garena Response bytes passed back to REST endpoints
        return {
            "success": True,
            "leader": leader,
            "acting_leader": acting_leader,
            "officers": officers,
            "members": members,
            "total_members": len(entries_list),
            "members_raw_bytes": resp.content
        }
    except Exception as e:
        return {"success": False, "message": str(e)}