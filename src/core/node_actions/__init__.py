from .flow import start, delay, random_delay, if_condition, random_branch, loop, end, try_catch, lock, unlock
from .profile import get_me, set_bio, set_avatar, add_contact, delete_contacts, block_user, unblock_user, get_chat, set_name, set_username, set_privacy, enable_2fa, search_contacts, import_contacts, get_common_chats, download_profile_photos
from .sending import send_message, send_photo, send_video, send_document, forward_messages, edit_message_text, delete_messages, send_sticker, send_reaction, send_story, send_voice, send_audio, send_gif, send_location, search_messages, send_dice, send_poll, save_draft
from .admin import (create_group, create_channel, set_chat_title, set_chat_description, set_chat_photo, 
                     delete_chat_photo, pin_chat_message, unpin_chat_message, restrict_chat_member, 
                     promote_chat_member, ban_chat_member, unban_chat_member, export_chat_invite_link,
                     set_chat_slow_mode, set_chat_permissions, set_chat_username,
                     get_channel_posts, approve_join_requests, edit_channel_post, delete_channel_post)
from .activity import (join_chat, leave_chat, auto_react, ai_reply, read_chat_history, 
                      archive_chats, unarchive_chats, scrape_chat_members, pin_chat, 
                      unpin_chat, download_media, comment_channel_post, forward_channel_post, 
                      react_to_post, share_post_link, view_user_stories, mute_chat)
from .bots import bot_start, bot_send_command, bot_click_inline, bot_click_keyboard, bot_open_web_app, bot_inline_query
from .premium import send_premium_message, send_premium_reaction, set_emoji_status
from .utilities import (get_post_comments, ai_prompt, string_contains, write_file, read_file, 
                      get_chat_history_messages, get_unread_dialogs, read_line, get_file_from_folder, 
                      http_request, set_global_var, increase_global_counter, get_from_resource,
                      parse_json, regex_extract, wait_for_message, execute_sub_scenario)
from .checks import (check_avatar, check_username, check_user_status, check_is_member, 
                     check_is_premium, check_bio_link, check_is_admin, check_chat_type, 
                     check_is_restricted, check_is_contact, check_is_bot, check_message_contains,
                     check_unread_count, check_chat_members_count, check_is_pinned,
                     check_profile_has_username, check_profile_phone_visible,
                     check_profile_is_scam, check_profile_stories_enabled,
                     check_profile_is_mutual, check_channel_subscription)

ACTION_HANDLERS = {
    "parse_json": parse_json,
    "regex_extract": regex_extract,
    "wait_for_message": wait_for_message,
    "execute_sub_scenario": execute_sub_scenario,

    # 1. Flow Control / Управление
    "start": start,
    "end": end,
    "delay": delay,
    "random_delay": random_delay,
    "if_condition": if_condition,
    "random_branch": random_branch,
    "loop": loop,
    "try_catch": try_catch,
    "lock": lock,
    "unlock": unlock,
    
    # 2. Profile & Contacts / Профиль и Контакты
    "get_me": get_me,
    "set_bio": set_bio,
    "set_avatar": set_avatar,
    "set_name": set_name,
    "set_username": set_username,
    "set_privacy": set_privacy,
    "enable_2fa": enable_2fa,
    "search_contacts": search_contacts,
    "import_contacts": import_contacts,
    "get_common_chats": get_common_chats,
    "download_profile_photos": download_profile_photos,

    "add_contact": add_contact,
    "delete_contacts": delete_contacts,
    "block_user": block_user,
    "unblock_user": unblock_user,
    "get_chat": get_chat,
    
    # 3. Sending / Отправка
    "send_message": send_message,
    "send_photo": send_photo,
    "send_video": send_video,
    "send_document": send_document,
    "forward_messages": forward_messages,
    "edit_message_text": edit_message_text,
    "delete_messages": delete_messages,
    "send_sticker": send_sticker,
    "send_reaction": send_reaction,
    "send_story": send_story,
    "send_voice": send_voice,
    "send_audio": send_audio,
    "send_gif": send_gif,
    "send_location": send_location,
    "search_messages": search_messages,
    "send_dice": send_dice,
    
    # 4. Chat Admin / Управление чатами
    "create_group": create_group,
    "create_channel": create_channel,
    "set_chat_title": set_chat_title,
    "set_chat_description": set_chat_description,
    "set_chat_username": set_chat_username,
    "set_chat_photo": set_chat_photo,
    "delete_chat_photo": delete_chat_photo,
    "pin_chat_message": pin_chat_message,
    "unpin_chat_message": unpin_chat_message,
    "restrict_chat_member": restrict_chat_member,
    "promote_chat_member": promote_chat_member,
    "ban_chat_member": ban_chat_member,
    "unban_chat_member": unban_chat_member,
    "export_chat_invite_link": export_chat_invite_link,
    "set_chat_slow_mode": set_chat_slow_mode,
    "set_chat_permissions": set_chat_permissions,
    "get_channel_posts": get_channel_posts,
    "approve_join_requests": approve_join_requests,
    "edit_channel_post": edit_channel_post,
    "delete_channel_post": delete_channel_post,
    
    # 5. Activity / Ативность
    "join_chat": join_chat,
    "leave_chat": leave_chat,
    "auto_react": auto_react,
    "ai_reply": ai_reply,
    "read_chat_history": read_chat_history,
    "archive_chats": archive_chats,
    "unarchive_chats": unarchive_chats,
    "scrape_chat_members": scrape_chat_members,
    "pin_chat": pin_chat,
    "unpin_chat": unpin_chat,
    "download_media": download_media,
    "comment_channel_post": comment_channel_post,
    "forward_channel_post": forward_channel_post,
    "react_to_post": react_to_post,
    "share_post_link": share_post_link,
    "view_user_stories": view_user_stories,
    
    # 6. Bots / Взаимодействие с ботами
    "bot_start": bot_start,
    "bot_send_command": bot_send_command,
    "bot_click_inline": bot_click_inline,
    "bot_click_keyboard": bot_click_keyboard,
    "bot_open_web_app": bot_open_web_app,
    "bot_inline_query": bot_inline_query,
    
    # 7. Premium / Премиум-функции
    "send_premium_message": send_premium_message,
    "send_premium_reaction": send_premium_reaction,
    "set_emoji_status": set_emoji_status,
    "send_poll": send_poll,
    "save_draft": save_draft,
    
    # 8. Utilities / Утилиты
    "get_post_comments": get_post_comments,
    "ai_prompt": ai_prompt,
    "string_contains": string_contains,
    "write_file": write_file,
    "read_file": read_file,
    "get_chat_history_messages": get_chat_history_messages,
    "get_unread_dialogs": get_unread_dialogs,
    "read_line": read_line,
    "get_file_from_folder": get_file_from_folder,

    # 9. Network & Global Data / Сеть и Данные
    "http_request": http_request,
    "set_global_var": set_global_var,
    "increase_global_counter": increase_global_counter,
    "get_from_resource": get_from_resource,
    
    # 10. Checks / Проверки
    "check_avatar": check_avatar,
    "check_username": check_username,
    "check_user_status": check_user_status,
    "check_is_member": check_is_member,
    "check_is_premium": check_is_premium,
    "check_bio_link": check_bio_link,
    "check_is_admin": check_is_admin,
    "check_chat_type": check_chat_type,
    "check_is_restricted": check_is_restricted,
    "check_is_contact": check_is_contact,
    "check_is_bot": check_is_bot,
    "check_message_contains": check_message_contains,
    "check_unread_count": check_unread_count,
    "check_chat_members_count": check_chat_members_count,
    "check_is_pinned": check_is_pinned,
    "check_profile_has_username": check_profile_has_username,
    "check_profile_phone_visible": check_profile_phone_visible,
    "check_profile_is_scam": check_profile_is_scam,
    "check_profile_stories_enabled": check_profile_stories_enabled,
    "check_profile_is_mutual": check_profile_is_mutual,
    "check_channel_subscription": check_channel_subscription,
    "mute_chat": mute_chat
}

# Dynamically merge custom action handlers
try:
    from src.core.managers import plugin_manager
    ACTION_HANDLERS.update(plugin_manager.custom_handlers)
except Exception as e:
    print(f"Error merging custom action handlers: {e}")
