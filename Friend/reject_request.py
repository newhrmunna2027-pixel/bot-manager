# -*- coding: utf-8 -*-
# Friend/reject_request.py - Decline Friend Request

import requests
import bot

def reject_friend_request(token, target_uid):
    try:
        author_uid = bot.decode_author_uid(token)
        if not author_uid:
            return False

        msg_fields = {
            1: int(target_uid)
        }
        
        encrypted_bytes = bot.encrypt_message(bot.create_proto_sync(msg_fields))
        region = bot.get_server_from_token(token)
        endpoint = bot.get_base_url(region) + "DeclineFriendRequest"

        headers = {
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB54"
        }
        
        res = requests.post(endpoint, data=encrypted_bytes, headers=headers, timeout=10, verify=False)
        return res.status_code == 200
    except Exception:
        return False