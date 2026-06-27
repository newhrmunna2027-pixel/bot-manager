# -*- coding: utf-8 -*-
# Friend/remove_friend.py - Delete Active Friend

import requests
import bot

def delete_active_friend(token, target_uid):
    try:
        author_uid = bot.decode_author_uid(token)
        if not author_uid:
            return False

        msg_fields = {
            1: int(author_uid),
            2: int(target_uid)
        }
        
        encrypted_bytes = bot.encrypt_message(bot.create_proto_sync(msg_fields))
        region = bot.get_server_from_token(token)
        endpoint = bot.get_base_url(region) + "RemoveFriend"

        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB53"
        }
        
        res = requests.post(endpoint, data=encrypted_bytes, headers=headers, timeout=10, verify=False)
        return res.status_code == 200
    except Exception:
        return False