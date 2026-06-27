# -*- coding: utf-8 -*-
# Friend/friend_list.py - Active Friend List Parser with Tag 8 Level & Tag 28/32 Avatar Decoders

import requests
import bot

def get_active_friend_list(token):
    try:
        author_uid = bot.decode_author_uid(token)
        if not author_uid:
            return {"success": False, "message": "Failed to decode account token"}

        protobuf_data = bot.create_proto_sync({1: int(author_uid)})
        encrypted_bytes = bot.encrypt_message(protobuf_data)

        region = bot.get_server_from_token(token)
        endpoint = bot.get_base_url(region) + "GetFriend"

        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB54"
        }
        
        res = requests.post(endpoint, data=encrypted_bytes, headers=headers, timeout=15, verify=False)
        if res.status_code != 200:
            return {"success": False, "message": f"Server status code: {res.status_code}"}
            
        parsed_outer = bot.parse_proto_bytes(res.content)
        friends_list = []
        
        def parse_single_friend(item_bytes):
            try:
                if not isinstance(item_bytes, bytes):
                    return None
                
                item_parsed = bot.parse_proto_bytes(item_bytes)
                uid_val = bot.decode_field_int(item_parsed.get(1), 0)
                if not uid_val:
                    return None
                    
                # SELF-PROFILE BLOCK FILTER (বোত নিজের ইউআইডি ফ্রেন্ডলিস্টে দেখাবে না)
                if str(uid_val) == str(author_uid):
                    return None
                    
                nickname = bot.decode_field_str(item_parsed.get(3))
                reg = bot.decode_field_str(item_parsed.get(6))
                
                # Garena Friend Level is strictly stored inside Tag 8
                level_val = bot.decode_field_int(item_parsed.get(8), 1)
                
                # 🟢 Garena Active Friend Avatar ID Mapping (Tag 28 / Tag 32 Fallback)
                avatar_id = bot.decode_field_int(item_parsed.get(28), 0)
                if avatar_id == 0:
                    avatar_id = bot.decode_field_int(item_parsed.get(32), 902000003)
                
                g_name = bot.decode_field_str(item_parsed.get(29))
                guild_id_val = bot.decode_field_str(item_parsed.get(63))
                ver = bot.decode_field_str(item_parsed.get(57))
                
                return {
                    "uid": str(uid_val),
                    "nickname": nickname.strip() if nickname else "Unknown",
                    "region": reg.strip() if reg else "N/A",
                    "level": int(level_val),
                    "avatar_id": str(avatar_id), # Passed cleanly to the UI mapper
                    "guild_name": g_name.strip() if g_name.strip() else "No Guild",
                    "guild_id": str(guild_id_val).strip(),
                    "version": ver.strip()
                }
            except Exception as ex:
                print(f"[*] Parse active friend element failure: {str(ex)}")
                return None

        items_1 = parsed_outer.get(1)
        if not items_1:
            return {"success": True, "friends": [], "friends_raw_bytes": res.content}

        if isinstance(items_1, list):
            for item in items_1:
                parsed = parse_single_friend(item)
                if parsed:
                    friends_list.append(parsed)

        if len(friends_list) == 0:
            if isinstance(items_1, bytes):
                inner_1 = bot.parse_proto_bytes(items_1)
                items_2 = inner_1.get(1)
                if isinstance(items_2, list):
                    for item in items_2:
                        parsed = parse_single_friend(item)
                        if parsed:
                            friends_list.append(parsed)
                elif isinstance(items_2, bytes):
                    parsed = parse_single_friend(items_2)
                    if parsed:
                        friends_list.append(parsed)

        # Garena Response bytes passed back to REST endpoints
        return {"success": True, "friends": friends_list, "friends_raw_bytes": res.content}
    except Exception as e:
        return {"success": False, "message": str(e)}