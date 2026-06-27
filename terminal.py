# -*- coding: utf-8 -*-
# terminal.py - Interactive Garena Console & Dynamic Web Logs Mode

import os
import sys
import json
import time
import logging
from datetime import datetime

# Resolve dynamic paths for direct command-line execution
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

# ANSI Terminal Coloring Configurations
R = '\033[1;31m'
C = '\033[1;36m'
G = '\033[1;32m'
Y = '\033[1;33m'
W = '\033[1;37m'
D = '\033[0m'
K = '\033[90m'

FIRST_BOOT_COMPLETED = False
CURRENT_MODE = "SYSTEM"  # Modes: "SYSTEM" (Default Console) or "WEB" (Live Logs)

# 🟢 Redirection of background Flask Werkzeug logs to temporary file to keep terminal clean
if not os.path.exists("temp_files"):
    try:
        os.makedirs("temp_files")
    except:
        pass

try:
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler("temp_files/web.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s'))
    werkzeug_logger.addHandler(file_handler)
    # Prevent duplicate prints to console stdout/stderr
    werkzeug_logger.propagate = False
except Exception as e:
    print(f"[*] Warning: Logger intercept disabled: {str(e)}")

def clear_screen():
    global FIRST_BOOT_COMPLETED
    if not FIRST_BOOT_COMPLETED:
        FIRST_BOOT_COMPLETED = True
        return
    os.system('cls' if os.name == 'nt' else 'clear')

def write_temp_file(filename, data):
    try:
        if not os.path.exists("temp_files"):
            os.makedirs("temp_files")
        with open(os.path.join("temp_files", filename), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except:
        pass

def delete_temp_file(filename):
    path = os.path.join("temp_files", filename)
    if os.path.exists(path):
        try: os.remove(path)
        except: pass

def print_banner():
    clear_screen()
    banner = f"""
{R}  ==================================================
{Y}           FREE FIRE MASTER MANAGER DASHBOARD
{C}               Smooth Interactive Terminal
{R}  =================================================={D}
"""
    sys.stdout.write(banner)

def get_self_profile_and_save():
    token, error = bot.get_active_token()
    if error or not token:
        print(f" \033[1;31m✗ [DEBUG] token verification failed: {error}\033[0m")
        return None
        
    author_uid = bot.decode_author_uid(token)
    print(f" \033[1;33m[*] [DEBUG] Decoded UID from Token: {author_uid}\033[0m")
    res = bot.get_player_info_detailed(author_uid, token)
    
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
        write_temp_file("data.json", profile_data)
        return profile_data
    else:
        print(f" \033[1;31m✗ [DEBUG] Profile fetch failed! Message: {res.get('message')}\033[0m")
    return None

def render_profile_card(profile):
    if not profile:
        return
    clan_status = f"{G}{profile['clan_name']} (ID: {profile['clan_id']}){D}" if (profile.get("clan_id") and profile["clan_id"] != "0" and profile["clan_id"] != "") else f"{R}No Guild{D}"
    card = f"""
  {Y}✦{D} {W}ACTIVE BOT PROFILE:{D}
  {C}--------------------------------------------------{D}
    {C}Nickname  :{D} {profile['nickname']}
    {C}UID       :{D} {profile['uid']}
    {C}Level     :{D} {profile['level']}
    {C}Region    :{D} {profile['region']}
    {C}Guild     :{D} {clan_status}
  {C}--------------------------------------------------{D}
"""
    sys.stdout.write(card)

# Option 1: Advanced Player Information Lookup
def player_info_flow():
    print_banner()
    sys.stdout.write(f"\n {Y}✦{D} {W}ENTER TARGET PLAYER UID {K}»{D} {C}")
    target_uid = input().strip()
    sys.stdout.write(D)
    
    if not target_uid.isdigit():
        print(f" {R}⚠ Invalid UID.{D}")
        time.sleep(1.5)
        return

    print(f" {C}[*] Extracting comprehensive profiles...{D}")
    token, error = bot.get_active_token()
    if error or not token:
        print(f" {R}✗ AUTH ERROR:{D} {error}")
        time.sleep(2)
        return

    res = bot.get_player_info_detailed(target_uid, token)
    if res.get("success"):
        print_banner()
        print(f"\n  {G}✔ DETAILED PLAYER PORTRAIT:{D}")
        print(f"  {C}--------------------------------------------------{D}")
        print(f"    {C}Nickname      :{D} {res['nickname']}")
        print(f"    {C}UID           :{D} {res['uid']}")
        print(f"    {C}Level         :{D} {res['level']}")
        print(f"    {C}Likes         :{D} {res['likes']}")
        print(f"    {C}Region        :{D} {res['region']}")
        print(f"    {C}Created At    :{D} {res['created_at']}")
        print(f"    {C}Last Login    :{D} {res['last_login']}")
        print(f"    {C}Signature/Bio :{D} {res['signature']}")
        print(f"  {C}--------------------------------------------------{D}")
        
        if res['clan_id'] != "0":
            print(f"    {Y}[🏰 ASSOCIATED GUILD DATA]{D}")
            print(f"    {C}Guild Name    :{D} {res['clan_name']}")
            print(f"    {C}Guild ID      :{D} {res['clan_id']}")
            print(f"    {C}Leader UID    :{D} {res['leader_uid']}")
        else:
            print(f"    {R}[🏰 GUILD DATA]: Player is not in any Guild.{D}")
        print(f"  {C}--------------------------------------------------{D}")
    else:
        print(f" {R}✗ Fetch Failed: {res.get('message')}{D}")
        
    sys.stdout.write(f"\n{K}Press Enter to return to main menu...{D}")
    input()

def get_uid_from_command(cmd, filename):
    parts = cmd.split()
    if len(parts) < 2: return None
    param = parts[1].strip()
    if param.isdigit() and len(param) > 6: return param
    try:
        idx = int(param)
        with open(os.path.join("temp_files", filename), "r", encoding="utf-8") as f:
            list_data = json.load(f)
        if 1 <= idx <= len(list_data):
            return list_data[idx - 1]["uid"]
    except: pass
    return None

# Option 2: Friend List Manager
def friend_list_flow():
    while True:
        print_banner()
        print(f"\n {C}[*] Fetching active friend list...{D}")
        token, error = bot.get_active_token()
        if error or not token:
            print(f" {R}✗ AUTH ERROR:{D} {error}")
            time.sleep(2)
            return

        delete_temp_file("list.json")
        res = friend_list.get_active_friend_list(token)
        if not res.get("success"):
            print(f" {R}✗ FAILED:{D} {res.get('message')}")
            time.sleep(2)
            return

        friends = res["friends"]
        write_temp_file("list.json", friends)

        print_banner()
        print(f"\n{Y}====== ACTIVE FRIENDS ({len(friends)}) ======{D}\n")
        for i, fr in enumerate(friends, 1):
            print(f"  {Y}[{i}]{D} {G}{fr['nickname']}{D} {W}(UID: {fr['uid']}){D}")
            print(f"      {C}➥ Region:{D} {fr['region']} | {C}Level:{D} {fr['level']} | {C}Guild:{D} {fr['guild_name']}")
            print(f"  {K}--------------------------------------------------{D}")

        print(f"\n {W}Commands:{D}")
        print(f"   {C}delete [no/uid]{D} - Remove friend")
        print(f"   {C}back{D}           - Return to dashboard\n")
        
        sys.stdout.write(f" {Y}✦{D} {W}CHOOSE ACTION {K}»{D} {C}")
        cmd = input().strip().lower()
        sys.stdout.write(D)

        if cmd == "back" or cmd == "":
            delete_temp_file("list.json")
            break
        elif cmd.startswith("delete"):
            target_uid = get_uid_from_command(cmd, "list.json")
            if not target_uid:
                print(f" {R}⚠ Invalid index or UID.{D}")
                time.sleep(1.5)
                continue
            
            print(f" {C}[*] Deleting friend UID: {target_uid}...{D}")
            success = remove_friend.delete_active_friend(token, target_uid)
            if success:
                print(f" {G}✔ Success! Player removed from Garena Friends.{D}")
            else: print(f" {R}✗ Failed to remove friend.{D}")
            time.sleep(1.5)

# Option 3: Add Friend
def add_friend_flow():
    print_banner()
    sys.stdout.write(f"\n {Y}✦{D} {W}ENTER UID TO SEND REQUEST {K}»{D} {C}")
    target_uid = input().strip()
    sys.stdout.write(D)

    if not target_uid.isdigit():
        print(f" {R}⚠ Invalid UID.{D}")
        time.sleep(1.5)
        return

    print(f" {C}[*] Sending friend request to {target_uid}...{D}")
    token, error = bot.get_active_token()
    if error or not token:
        print(f" {R}✗ AUTH ERROR:{D} {error}")
        time.sleep(2)
        return

    success = add_friend.add_target_friend(token, target_uid)
    if success:
        print(f" {G}✔ Success! Friend request sent.{D}")
    else: print(f" {R}✗ Request failed.{D}")
    
    sys.stdout.write(f"\n{K}Press Enter to return to main menu...{D}")
    input()

# Option 4: Pending List Flow
def pending_list_flow():
    while True:
        print_banner()
        print(f"\n {C}[*] Fetching pending requests...{D}")
        token, error = bot.get_active_token()
        if error or not token:
            print(f" {R}✗ AUTH ERROR:{D} {error}")
            time.sleep(2)
            return

        delete_temp_file("list.json")
        res = pending_list.get_pending_request_list(token)
        if not res.get("success"):
            print(f" {R}✗ FAILED:{D} {res.get('message')}")
            time.sleep(2)
            return

        reqs = res["requests"]
        write_temp_file("list.json", reqs)

        print_banner()
        print(f"\n{Y}====== PENDING REQUESTS ({len(reqs)}) ======{D}\n")
        for i, rq in enumerate(reqs, 1):
            print(f"  {Y}[{i}]{D} {G}{rq['nickname']}{D} {W}(UID: {rq['uid']}){D}")
            print(f"      {C}➥ Level:{D} {rq['level']} | {C}Likes:{D} {rq['likes']} | {C}Server:{D} {rq['region']}")
            print(f"  {K}--------------------------------------------------{D}")

        print(f"\n {W}Commands:{D}")
        print(f"   {C}accept [no/uid]{D} - Confirm request")
        print(f"   {C}reject [no/uid]{D} - Decline request")
        print(f"   {C}back{D}            - Return to dashboard\n")
        
        sys.stdout.write(f" {Y}✦{D} {W}CHOOSE ACTION {K}»{D} {C}")
        cmd = input().strip().lower()
        sys.stdout.write(D)

        if cmd == "back" or cmd == "":
            delete_temp_file("list.json")
            break
        elif cmd.startswith("accept"):
            target_uid = get_uid_from_command(cmd, "list.json")
            if not target_uid:
                print(f" {R}⚠ Invalid selection.{D}")
                time.sleep(1.5)
                continue
            print(f" {C}[*] Accepting request from: {target_uid}...{D}")
            success = accept_request.accept_friend_request(token, target_uid)
            if success: print(f" {G}✔ Friend Request accepted.{D}")
            else: print(f" {R}✗ Accept execution failed.{D}")
            time.sleep(1.5)
            
        elif cmd.startswith("reject"):
            target_uid = get_uid_from_command(cmd, "list.json")
            if not target_uid:
                print(f" {R}⚠ Invalid selection.{D}")
                time.sleep(1.5)
                continue
            print(f" {C}[*] Declining request from: {target_uid}...{D}")
            success = reject_request.reject_friend_request(token, target_uid)
            if success: print(f" {G}✔ Friend Request rejected.{D}")
            else: print(f" {R}✗ Reject execution failed.{D}")
            time.sleep(1.5)

# Option 5: Bio Changer
def bio_changer_flow():
    print_banner()
    print(f"\n {Y}✦{D} {W}WRITE YOUR NEW BIO/SIGNATURE.{D}")
    print(f" {K}Type text below. Press [ENTER] twice consecutively to confirm & save:{D}\n")
    
    lines = []
    empty_streak = 0
    while True:
        line = input(f" {C}»{D} ")
        if line.strip() == "":
            empty_streak += 1
            if empty_streak >= 2: break
        else:
            empty_streak = 0
            lines.append(line)
            
    bio_text = "\n".join(lines).strip()
    if not bio_text:
        print(f" {R}⚠ Bio content is empty. Modification aborted.{D}")
        time.sleep(1.5)
        return

    print(f"\n {C}[*] Modifying signature with Garena...{D}")
    token, error = bot.get_active_token()
    if error or not token:
        print(f" {R}✗ AUTH ERROR:{D} {error}")
        time.sleep(2)
        return

    res = bot.update_bio_native(token, bio_text)
    if res.get("success"): print(f" {G}✔ Success! Bio changed successfully.{D}")
    else: print(f" {R}✗ Failed: {res.get('message')}{D}")
    
    sys.stdout.write(f"\n{K}Press Enter to return to main menu...{D}")
    input()

# Option 6: Dynamic Duo Checker
def dynamic_duo_flow():
    print_banner()
    sys.stdout.write(f"\n {Y}✦{D} {W}ENTER PLAYER UID TO CHECK DUO STATUS {K}»{D} {C}")
    target_uid = input().strip()
    sys.stdout.write(D)

    if not target_uid.isdigit():
        print(f" {R}⚠ Invalid UID.{D}")
        time.sleep(1.5)
        return

    print(f" {C}[*] Running Dynamic Duo Engine...{D}")
    token, error = bot.get_active_token()
    if error or not token:
        print(f" {R}✗ AUTH ERROR:{D} {error}")
        time.sleep(2)
        return

    res = bot.check_duo_native(token, target_uid)
    if not res.get("success"):
        print(f" {R}✗ Duo Checker: {res.get('message')}{D}")
        sys.stdout.write(f"\n{K}Press Enter to return...{D}")
        input()
        return

    partner_uid = res["partner_uid"]
    print(f" {C}[*] Fetching profiles for checked players and partners...{D}")
    p1 = bot.get_player_info_detailed(target_uid, token)
    p2 = bot.get_player_info_detailed(partner_uid, token)

    p1_name = p1.get("nickname", "Unknown Profile") if p1.get("success") else "Private Profile"
    p1_lvl = p1.get("level", "N/A") if p1.get("success") else "N/A"
    p1_likes = p1.get("likes", "N/A") if p1.get("success") else "N/A"
    p1_clan = p1.get("clan_name", "N/A") if p1.get("success") else "N/A"
    
    p2_name = p2.get("nickname", "Unknown Profile") if p2.get("success") else "Private Profile"
    p2_lvl = p2.get("level", "N/A") if p2.get("success") else "N/A"
    p2_likes = p2.get("likes", "N/A") if p2.get("success") else "N/A"
    p2_clan = p2.get("clan_name", "N/A") if p2.get("success") else "N/A"

    print_banner()
    duo_card = f"""
  {Y}💕====== DYNAMIC DUO MOOD CARD ======{D}
  {C}--------------------------------------------------{D}
    {C}Score        :{D} {res['score']} Points
    {C}Duo Level    :{D} Level {res['level']}
    {C}Formed On    :{D} {res['formed_on']}
    {C}Active Days  :{D} {res['days_active']} Days
    {C}Status       :{D} {res['status']}
  {C}--------------------------------------------------{D}
    {G}[👑 INITIATOR PLAYER PROFILE]{D}
    {C}Name / Nick  :{D} {p1_name}
    {C}UID          :{D} {target_uid}
    {C}Player Level :{D} Lvl {p1_lvl} (Likes: {p1_likes})
    {C}Guild Name   :{D} {p1_clan}
  {C}--------------------------------------------------{D}
    {G}[💝 COMPANION DUO PROFILE]{D}
    {C}Name / Nick  :{D} {p2_name}
    {C}UID          :{D} {partner_uid}
    {C}Player Level :{D} Lvl {p2_lvl} (Likes: {p2_likes})
    {C}Guild Name   :{D} {p2_clan}
  {C}--------------------------------------------------{D}
"""
    sys.stdout.write(duo_card)
    sys.stdout.write(f"\n{K}Press Enter to return to main menu...{D}")
    input()

# Option 7: Nickname Changer
def nickname_changer_flow():
    print_banner()
    sys.stdout.write(f"\n {Y}✦{D} {W}ENTER NEW NICKNAME FOR BOT {K}»{D} {C}")
    new_nick = input().strip()
    sys.stdout.write(D)

    if not new_nick:
        print(f" {R}⚠ Nickname cannot be empty.{D}")
        time.sleep(1.5)
        return

    print(f" {C}[*] Changing bot nickname...{D}")
    token, error = bot.get_active_token()
    if error or not token:
        print(f" {R}✗ AUTH ERROR:{D} {error}")
        time.sleep(2)
        return

    res = bot.change_nickname_native(token, new_nick)
    if res.get("success"):
        print(f" {G}✔ Success! Nickname modified to '{new_nick}'.{D}")
        get_self_profile_and_save()
    else: print(f" {R}✗ Failed: {res.get('message')}{D}")
        
    sys.stdout.write(f"\n{K}Press Enter to return to main menu...{D}")
    input()

# Option 8: Join Guild
def join_guild_flow():
    print_banner()
    sys.stdout.write(f"\n {Y}✦{D} {W}ENTER TARGET GUILD ID {K}»{D} {C}")
    guild_id = input().strip()
    sys.stdout.write(D)

    if not guild_id.isdigit():
        print(f" {R}⚠ Invalid Guild ID.{D}")
        time.sleep(1.5)
        return

    print(f" {C}[*] Extracting target Guild details for confirmation...{D}")
    token, error = bot.get_active_token()
    if error or not token:
        print(f" {R}✗ AUTH ERROR:{D} {error}")
        time.sleep(2)
        return

    res = guild_info.get_clan_info_by_id(token, guild_id)
    if not res.get("success"):
        print(f" {R}✗ Could not fetch Guild details: {res.get('message')}{D}")
        time.sleep(2.5)
        return

    g = res["guild_info"]
    print_banner()
    print(f"\n  {Y}[🏰 TARGET GUILD INFORMATION]{D}")
    print(f"  {C}--------------------------------------------------{D}")
    print(f"    {C}Guild Name   :{D} {g['clan_name']}")
    print(f"    {C}Guild ID     :{D} {g['clan_id']}")
    print(f"    {C}Level        :{D} {g['level']}")
    print(f"    {C}Current Slots:{D} {g['total_members']} / {g['max_members']}")
    print(f"    {C}Leader UID   :{D} {g['leader_uid']}")
    print(f"    {C}Welcome Msg  :{D} {g['welcome_message']}")
    print(f"    {C}Region       :{D} {g['region']}")
    print(f"  {C}--------------------------------------------------{D}\n")

    sys.stdout.write(f" {Y}✦{D} {W}Type '{G}join{W}' to submit request, or '{R}back{W}' to cancel {K}»{D} {C}")
    decision = input().strip().lower()
    sys.stdout.write(D)

    if decision == "join":
        print(f" {C}[*] Submitting join request...{D}")
        success = join_guild.request_join_clan(token, guild_id)
        if success:
            print(f" {G}✔ Success! Guild join request submitted successfully.{D}")
            get_self_profile_and_save()
        else: print(f" {R}✗ Join execution failed.{D}")
    else: print(f" {Y}[*] Action cancelled. Returning to main menu...{D}")
    time.sleep(2)

# Option 8/9: Manage Guild
def manage_guild_flow(clan_id):
    while True:
        print_banner()
        print(f"\n {C}[*] Extracting Guild general information...{D}")
        token, error = bot.get_active_token()
        if error or not token:
            print(f" {R}✗ AUTH ERROR:{D} {error}")
            time.sleep(2)
            return

        res = guild_info.get_clan_info_by_id(token, clan_id)
        if not res.get("success"):
            print(f" {R}✗ FAILED TO GET GUILD DETAILS: {res.get('message')}{D}")
            time.sleep(2.5)
            return

        g = res["guild_info"]
        print_banner()
        print(f"\n  {Y}[⭐ GUILD MANAGEMENT CARD]{D}")
        print(f"  {C}--------------------------------------------------{D}")
        print(f"    {C}Guild Name   :{D} {g['clan_name']}")
        print(f"    {C}Guild ID     :{D} {g['clan_id']}")
        print(f"    {C}Level        :{D} {g['level']}")
        print(f"    {C}Total Member :{D} {g['total_members']} / {g['max_members']}")
        print(f"    {C}Total Glory  :{D} {g['total_glory']}")
        print(f"    {C}Weekly Glory :{D} {g['recent_glory']}")
        print(f"    {C}Welcome Msg  :{D} {g['welcome_message']}")
        print(f"    {C}Creation Time:{D} {g['created_at']}")
        print(f"  {C}--------------------------------------------------{D}\n")

        print(f"  {W}Available Commands:{D}")
        print(f"    {C}list{D}  - Show all guild members")
        print(f"    {C}leave{D} - Exit current guild")
        print(f"    {C}back{D}  - Return to dashboard\n")

        sys.stdout.write(f" {Y}✦{D} {W}CHOOSE COMMAND {K}»{D} {C}")
        cmd = input().strip().lower()
        sys.stdout.write(D)

        if cmd == "back" or cmd == "": break
        elif cmd == "list":
            print_banner()
            print(f"\n {C}[*] Loading members registry (A to Z)...{D}")
            m_res = member_list.get_guild_member_list(token, clan_id)
            if not m_res.get("success"):
                print(f" {R}✗ Member fetch failed: {m_res.get('message')}{D}")
                time.sleep(2)
                continue
                
            print_banner()
            print(f"\n {Y}====== GUILD REGISTRY ({g['clan_name']}) ======{D}\n")
            
            officer_count = len(m_res.get("officers", []))
            if m_res.get("acting_leader") and m_res["acting_leader"] != "N/A":
                officer_count += 1
                
            print(f"    {C}Total Members  :{D} {m_res['total_members']}")
            print(f"    {C}Total Officers :{D} {officer_count + 1} (Leader + Officers)")
            print(f"  {C}--------------------------------------------------{D}\n")
            
            if m_res.get("leader"):
                l = m_res["leader"]
                print(f"  {Y}[👑 GUILD LEADER]{D} {G}{l['name']}{D} | UID: {l['uid']} | Weekly Glory: {l['weekly_glory']}")
            if m_res.get("acting_leader"):
                al = m_res["acting_leader"]
                print(f"  {Y}[⭐ ACTING LEADER]{D} {G}{al['name']}{D} | UID: {al['uid']} | Weekly Glory: {al['weekly_glory']}")
                
            if m_res.get("officers"):
                print(f"\n  {Y}[👮 GUILD OFFICERS]{D}")
                for off in m_res["officers"]:
                    print(f"    Name: {off['name'].ljust(15)} | UID: {off['uid'].ljust(12)} | Weekly Glory: {off['weekly_glory']}")
                    
            if m_res.get("members"):
                print(f"\n  {Y}[👥 GUILD MEMBERS]{D}")
                for mem in m_res["members"]:
                    print(f"    Name: {mem['name'].ljust(15)} | UID: {mem['uid'].ljust(12)} | Weekly Glory: {mem['weekly_glory']}")
            
            sys.stdout.write(f"\n{K}Press Enter to return to Guild Card...{D}")
            input()
            
        elif cmd == "leave":
            sys.stdout.write(f" {R}⚠ Are you sure you want to exit guild? (yes/no) »{D} {C}")
            conf = input().strip().lower()
            sys.stdout.write(D)
            if conf == "yes":
                print(f" {C}[*] Quitting guild...{D}")
                success = leave_guild.quit_current_clan(token, clan_id)
                if success:
                    print(f" {G}✔ Success! You left the guild.{D}")
                    get_self_profile_and_save()
                    time.sleep(2)
                    break
                else:
                    print(f" {R}✗ Failed to quit guild.{D}")
                    time.sleep(1.5)

def logout_flow():
    delete_temp_file("data.json")
    delete_temp_file("list.json")
    if os.path.exists("url.json"):
        try:
            with open("url.json", "w") as f:
                json.dump({}, f)
        except: pass
    print(f"\n {G}[*] Credentials wiped. Returning to login screen...{D}")
    time.sleep(1.5)

# 🟢 NEW MODE S3: PRINTS STATELESS DIRECT REST APIs FOR EASY CLIENT COPY
def print_direct_api_directory():
    clear_screen()
    directory_card = f"""
{C}========================================================================
                     GARENA DIRECT REST API BLUEPRINT 
{C}========================================================================{D}
  
  {Y}[+] BASE ACCESS URL »{D} {G}http://127.0.0.1:5000{D}
  
  {W}* Query inputs [uid] and [password] belong to Garena Bot accounts.*{D}

  {Y}1. profile info (Bot / Target):{D}
  {G}http://127.0.0.1:5000/api/direct/profile?uid=<bot_uid>&password=<bot_pass>&target=<target_uid>{D}
  
  {Y}2. Active friends List:{D}
  {G}http://127.0.0.1:5000/api/direct/friends?uid=<bot_uid>&password=<bot_pass>{D}
  
  {Y}3. Pending Request Inbox:{D}
  {G}http://127.0.0.1:5000/api/direct/pending?uid=<bot_uid>&password=<bot_pass>{D}
  
  {Y}4. Dynamic Duo Scraper:{D}
  {G}http://127.0.0.1:5000/api/direct/duo?uid=<bot_uid>&password=<bot_pass>&target=<target_uid>{D}
  
  {Y}5. Guild Profile details:{D}
  {G}http://127.0.0.1:5000/api/direct/guild/info?uid=<bot_uid>&password=<bot_pass>&clan_id=<guild_id>{D}
  
  {Y}6. Guild members Glory Roster:{D}
  {G}http://127.0.0.1:5000/api/direct/guild/members?uid=<bot_uid>&password=<bot_pass>&clan_id=<guild_id>{D}

{C}------------------------------------------------------------------------
                         GARENA DIRECT SYSTEM ACTIONS
{C}------------------------------------------------------------------------{D}

  {Y}7. Send Friend Request:{D}
  {G}http://127.0.0.1:5000/api/direct/friends/add?uid=<bot_uid>&password=<bot_pass>&target=<target_uid>{D}
  
  {Y}8. Delete Active Friend:{D}
  {G}http://127.0.0.1:5000/api/direct/friends/remove?uid=<bot_uid>&password=<bot_pass>&target=<target_uid>{D}
  
  {Y}9. Confirm Pending Request:{D}
  {G}http://127.0.0.1:5000/api/direct/friends/accept?uid=<bot_uid>&password=<bot_pass>&target=<target_uid>{D}
  
  {Y}10. Decline Pending Request:{D}
  {G}http://127.0.0.1:5000/api/direct/friends/reject?uid=<bot_uid>&password=<bot_pass>&target=<target_uid>{D}
  
  {Y}11. Join Target Guild:{D}
  {G}http://127.0.0.1:5000/api/direct/guild/join?uid=<bot_uid>&password=<bot_pass>&clan_id=<guild_id>{D}
  
  {Y}12. Leave current Guild:{D}
  {G}http://127.0.0.1:5000/api/direct/guild/leave?uid=<bot_uid>&password=<bot_pass>&clan_id=<guild_id>{D}
  
  {Y}13. Change Bot Nickname:{D}
  {G}http://127.0.0.1:5000/api/direct/bot/nickname?uid=<bot_uid>&password=<bot_pass>&nickname=<new_nick>{D}
  
  {Y}14. Change Bot Bio Signature:{D}
  {G}http://127.0.0.1:5000/api/direct/bot/bio?uid=<bot_uid>&password=<bot_pass>&bio=<signature>{D}

{C}========================================================================{D}
"""
    sys.stdout.write(directory_card)
    sys.stdout.write(f"\n{K}Press Enter to return to Garena Console Dashboard...{D}")
    input()

# 🟢 NEW MODE S1: LOOPS AND SHOWS FLASK LOGS STREAMED FROM LOGFILE
def view_web_logs_flow():
    clear_screen()
    print(f"{C}=================================================={D}")
    print(f"           {Y}LIVE WEB CONTROL PORT INBOX LOGS{D}        ")
    print(f"       {K}Tailed from: temp_files/web.log (Every 2s){D} ")
    print(f"   {W}Type 'S2' and press Enter to return to Dashboard{D}")
    print(f"{C}=================================================={D}\n")
    
    last_position = 0
    log_file_path = "temp_files/web.log"
    
    # Pre-render last 15 lines if exists
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-15:]:
                    sys.stdout.write(f" {G}»{D} {line}")
                last_position = f.tell()
        except: pass
        
    while True:
        # Non-blocking input fallback loop check
        sys.stdout.write(f"\n{Y}[Logs active: Press ENTER to reload, or type 'S2' to return] »{D} {C}")
        cmd = input().strip().upper()
        sys.stdout.write(D)
        
        if cmd == "S2":
            break
            
        # Refresh print changes
        clear_screen()
        print(f"{C}=================================================={D}")
        print(f"           {Y}LIVE WEB CONTROL PORT INBOX LOGS{D}        ")
        print(f"   {W}Type 'S2' and press Enter to return to Dashboard{D}")
        print(f"{C}=================================================={D}\n")
        
        if os.path.exists(log_file_path):
            try:
                with open(log_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-20:]: # show last 20 rows on manual reload
                        sys.stdout.write(f" {G}»{D} {line}")
            except Exception as ex:
                print(f" {R}✗ Error reading buffer stream: {str(ex)}{D}")
        else:
            print(f" {K}[*] No web logs received inside the buffer stream yet.{D}")

def console_loop():
    global CURRENT_MODE
    delete_temp_file("data.json")
    
    while True:
        # 🟢 If user switched mode to S1 (Web Mode), jump into the log tailer flow
        if CURRENT_MODE == "WEB":
            view_web_logs_flow()
            CURRENT_MODE = "SYSTEM" # auto reset back to system on exit
            continue
            
        session = bot.load_session()
        if not session or not session.get("uid") or not session.get("password"):
            print_banner()
            print(f"\n {Y}[⭐ NO ACTIVE SESSION FOUND]{D}")
            print(f" {K}Commands shortcut: Type 'S3' to print Stateless Garena APIs{D}\n")
            sys.stdout.write(f" {Y}✦{D} {W}ENTER YOUR GARENA GUEST UID {K}»{D} {C}")
            uid = input().strip()
            
            # Allow shortcut routing from login gate too!
            if uid.upper() == "S3":
                print_direct_api_directory()
                continue
            elif uid.upper() == "S1":
                CURRENT_MODE = "WEB"
                continue
                
            sys.stdout.write(f" {Y}✦{D} {W}ENTER YOUR ACCOUNT PASSWORD {K}»{D} {C}")
            password = input().strip()
            sys.stdout.write(D)
            
            if not uid or not password:
                print(f" {R}⚠ Credentials cannot be empty.{D}")
                time.sleep(1.5)
                continue
                
            print(f"\n {C}[*] Connecting Garena engine...{D}")
            token, error = bot.get_token_from_uid_password(uid, password)
            if error:
                print(f" {R}✗ Login failure: {error}{D}")
                time.sleep(2.5)
                continue
                
            bot.save_session({"uid": uid, "password": password, "token": token})
            print(f" {G}✔ Authenticated successfully!{D}")
            time.sleep(1)

        profile = None
        if os.path.exists(os.path.join("temp_files", "data.json")):
            try:
                with open(os.path.join("temp_files", "data.json"), "r", encoding="utf-8") as f:
                    profile = json.load(f)
            except: pass
                
        if not profile:
            profile = get_self_profile_and_save()
            if not profile:
                print(f" {R}✗ Failed to pull owner profile. Force logging out...{D}")
                logout_flow()
                continue

        print_banner()
        render_profile_card(profile)
        
        has_guild = profile["clan_id"] != "0" and profile["clan_id"] != ""

        print(f"    {C}[1]{D} {W}PLAYER INFORMATION SHOW{D}")
        print(f"    {C}[2]{D} {W}FRIEND LIST (DELETE FRIEND){D}")
        print(f"    {C}[3]{D} {W}ADD NEW FRIEND{D}")
        print(f"    {C}[4]{D} {W}PENDING FRIEND REQUESTS (ACCEPT/REJECT){D}")
        print(f"    {C}[5]{D} {W}BIO/SIGNATURE CHANGER (DOUBLE ENTER TO SAVE){D}")
        print(f"    {C}[6]{D} {W}DYNAMIC DUO CHECKER (WITH DUAL PROFILE DATA){D}")
        print(f"    {C}[7]{D} {W}BOT NICKNAME CHANGER{D}")
        
        if not has_guild:
            print(f"    {C}[8]{D} {W}JOIN GUILD{D}")
        else:
            print(f"    {C}[8]{D} {W}MANAGE GUILD (MEMBERS LIST/LEAVE){D}")
            
        print(f"    {C}[9]{D} {W}LOGOUT FROM THIS BOT{D}")
        print(f"    {C}[10]{D}{W}CLOSE DASHBOARD ENGINE{D}\n")
        
        print(f"  {Y}[📊 SWITCH MODES SPECIAL COMMANDS]{D}")
        print(f"    {C}S1{D} » {W}Web Mode (Hides Garena Menu, Shows Live Server Logs){D}")
        print(f"    {C}S3{D} » {W}Print Garena Stateless Direct Web API URLs{D}\n")
        
        sys.stdout.write(f" {Y}✦{D} {W}SELECT OPERATION {K}»{D} {C}")
        opt = input().strip()
        sys.stdout.write(D)
        
        if opt.upper() == "S1":
            CURRENT_MODE = "WEB"
        elif opt.upper() == "S2":
            CURRENT_MODE = "SYSTEM"
            showToast("System Console mode updated.")
        elif opt.upper() == "S3":
            print_direct_api_directory()
        elif opt == "1": player_info_flow()
        elif opt == "2": friend_list_flow()
        elif opt == "3": add_friend_flow()
        elif opt == "4": pending_list_flow()
        elif opt == "5": bio_changer_flow()
        elif opt == "6": dynamic_duo_flow()
        elif opt == "7": nickname_changer_flow()
        elif opt == "8" and not has_guild: join_guild_flow()
        elif opt == "8" and has_guild: manage_guild_flow(profile["clan_id"])
        elif opt == "9": logout_flow()
        elif opt == "10":
            print(f"\n {G}[*]{D} Exiting Controller Engine. Goodbye!")
            os._exit(0)
        else:
            print(f"\n {R}⚠ Invalid selection.{D}")
            time.sleep(1)