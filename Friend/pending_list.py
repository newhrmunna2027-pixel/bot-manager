# -*- coding: utf-8 -*-
# Friend/pending_list.py - Get Pending Friend Request List with Avatar ID

import requests
from datetime import datetime
import bot

def get_pending_request_list(token):
    try:
        author_uid = bot.decode_author_uid(token)
        if not author_uid:
            return {"success": False, "message": "Failed to decode account token"}

        protobuf_data = bot.create_proto_sync({1: int(author_uid)})
        encrypted_bytes = bot.encrypt_message(protobuf_data)

        region = bot.get_server_from_token(token)
        endpoint = bot.get_base_url(region) + "GetFriendRequestList"

        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB54"
        }
        
        res = requests.post(endpoint, data=encrypted_bytes, headers=headers, timeout=15, verify=False)
        if res.status_code != 200:
            return {"success": False, "message": f"Server status: {res.status_code}"}
            
        parsed_outer = bot.parse_proto_bytes(res.content)
        outer_1 = parsed_outer.get(1)
        if not outer_1:
            return {"success": True, "requests": [], "pending_raw_bytes": res.content}

        if isinstance(outer_1, bytes):
            inner_1 = bot.parse_proto_bytes(outer_1)
        elif isinstance(outer_1, list):
            inner_1 = bot.parse_proto_bytes(outer_1[0])
        else:
            return {"success": True, "requests": [], "pending_raw_bytes": res.content}
            
        pending_items = inner_1.get(1)
        if not pending_items:
            return {"success": True, "requests": [], "pending_raw_bytes": res.content}

        requests_list = []

        def safe_date_convert(ts):
            try:
                if not ts or ts == 0: return "N/A"
                return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %I:%M %p')
            except:
                return "N/A"

        def parse_single_request(item_bytes):
            try:
                if not isinstance(item_bytes, bytes):
                    return None
                    
                item_parsed = bot.parse_proto_bytes(item_bytes)
                uid_val = bot.decode_field_int(item_parsed.get(1), 0)
                if not uid_val:
                    return None
                    
                nickname = bot.decode_field_str(item_parsed.get(3))
                reg = bot.decode_field_str(item_parsed.get(5))
                
                # 🟢 Garena Correction: Tag 6 is the real Level for pending request items
                level_val = bot.decode_field_int(item_parsed.get(6), 1)
                
                # Garena Pending Avatar/HeadPic ID (Tag 12) Mapping
                avatar_id = bot.decode_field_int(item_parsed.get(12), 902000003)
                
                exp_val = bot.decode_field_int(item_parsed.get(7), 0)
                br_rank_val = bot.decode_field_int(item_parsed.get(14), 0)
                ranking_points_val = bot.decode_field_int(item_parsed.get(15), 0)
                badge_cnt_val = bot.decode_field_int(item_parsed.get(18), 0)
                liked_val = bot.decode_field_int(item_parsed.get(21), 0)
                
                request_ts = bot.decode_field_int(item_parsed.get(24), 0)
                cs_rank_val = bot.decode_field_int(item_parsed.get(30), 0)
                max_rank_val = bot.decode_field_int(item_parsed.get(35), 0)
                cs_max_rank_val = bot.decode_field_int(item_parsed.get(36), 0)
                create_ts = bot.decode_field_int(item_parsed.get(44), 0)
                version_bytes = item_parsed.get(50, b"N/A")
                
                # Garena Guild name extraction (Strict Tag 29, fallback bypass)
                guild_name = bot.decode_field_str(item_parsed.get(29)).strip()
                if not guild_name or guild_name == "No Guild" or guild_name == "":
                    tag_41_bytes = item_parsed.get(41)
                    if isinstance(tag_41_bytes, bytes):
                        tag_41_parsed = bot.parse_proto_bytes(tag_41_bytes)
                        g_bytes = tag_41_parsed.get(5, b"No Guild")
                        guild_name = g_bytes.decode('utf-8', errors='ignore') if isinstance(g_bytes, bytes) else str(g_bytes)

                version = version_bytes.decode('utf-8', errors='ignore') if isinstance(version_bytes, bytes) else str(version_bytes)

                return {
                    "uid": str(uid_val),
                    "nickname": nickname.strip() if nickname else "Unknown",
                    "region": reg.strip() if reg else "N/A",
                    "level": int(level_val),
                    "avatar_id": str(avatar_id),
                    "exp": int(exp_val),
                    "br_rank": int(br_rank_val),
                    "br_points": int(ranking_points_val),
                    "badge_count": int(badge_cnt_val),
                    "likes": int(liked_val),
                    "request_time": safe_date_convert(request_ts),
                    "last_login_time": safe_date_convert(request_ts),
                    "cs_rank": int(cs_rank_val),
                    "max_rank": int(max_rank_val),
                    "cs_max_rank": int(cs_max_rank_val),
                    "created_time": safe_date_convert(create_ts),
                    "version": version.strip(),
                    "guild_name": guild_name.strip() if guild_name else "No Guild"
                }
            except Exception as ex:
                print(f"[*] Parse pending friend request failure: {str(ex)}")
                return None

        if isinstance(pending_items, list):
            for item in pending_items:
                res_obj = parse_single_request(item)
                if res_obj:
                    requests_list.append(res_obj)
        elif isinstance(pending_items, bytes):
            res_obj = parse_single_request(pending_items)
            if res_obj:
                requests_list.append(res_obj)

        # Garena Response bytes passed back to REST endpoints
        return {"success": True, "requests": requests_list, "pending_raw_bytes": res.content}
    except Exception as e:
        return {"success": False, "message": str(e)}