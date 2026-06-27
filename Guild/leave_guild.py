# -*- coding: utf-8 -*-
# Guild/leave_guild.py - Quit/Leave Clan/Guild

import requests
import bot

def quit_current_clan(token, clan_id):
    try:
        region = bot.get_server_from_token(token)
        base_url = bot.get_base_url(region)
        url = f"{base_url}QuitClan"
        
        msg_payload = bot.create_proto_sync({1: int(clan_id)})
        encrypted_bytes = bot.E_AEs(msg_payload.hex())
        
        headers = {
            "Accept-Encoding": "gzip",
            "Authorization": f"Bearer {token}",
            "Connection": "Keep-Alive",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "ReleaseVersion": "OB54",
            "X-GA": "v1 1",
            "X-Unity-Version": "2018.4.11f1"
        }
        
        resp = requests.post(url, headers=headers, data=encrypted_bytes, timeout=12, verify=False)
        return resp.status_code == 200
    except Exception:
        return False