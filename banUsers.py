import asyncio
import random
import time
from telethon import TelegramClient
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsRecent
from telethon.errors import FloodWaitError, SlowModeWaitError
from datetime import datetime, timedelta, timezone

# Your API credentials (get from https://my.telegram.org)
API_ID = 'YOUR_API_ID'  # Replace with your actual API ID
API_HASH = 'YOUR_API_HASH'  # Replace with your actual API hash
PHONE_NUMBER = '+YOUR_PHONE'  # Replace with your phone in international format

# Configuration - NOW USING UTC TIMES
CHAT_ID = '@your_group'  # Your group/channel username or ID
SPAM_START_TIME = datetime(2025, 7, 9, 8, 15, tzinfo=timezone.utc)  # UTC time YYYY,DD,MM,HH,MM
SPAM_END_TIME = datetime(2025, 7, 9, 8, 22, tzinfo=timezone.utc)    # UTC time YYYY,DD,MM,HH,MM
DRY_RUN = False  # Set to False to actually ban users

def make_aware(dt):
    """Ensure datetime is timezone-aware (convert naive to UTC)"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

async def main():
    # Initialize the client
    client = TelegramClient('session_name', API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)
    
    try:
        # Get the chat entity
        chat = await client.get_entity(CHAT_ID)
        print(f"✅ Processing chat: {chat.title} (ID: {chat.id})")
        
        # Get ALL participants with proper rate limit handling
        print("🔄 Fetching ALL participants (this may take time for large groups)...")
        all_participants = []
        offset = 0
        limit = 200
        total = None
        page = 1
        
        while True:
            try:
                # CRITICAL FIX: MUST USE ChannelParticipantsRecent() to get join dates
                result = await client(GetParticipantsRequest(
                    channel=chat,
                    filter=ChannelParticipantsRecent(),  # ESSENTIAL FOR JOIN DATES
                    offset=offset,
                    limit=limit,
                    hash=0
                ))
                
                if not result.participants:
                    print("📭 No more participants found")
                    break
                
                # Process participants with their join dates
                valid_count = 0
                for participant in result.participants:
                    if hasattr(participant, 'date') and participant.date:
                        # Extract user_id based on participant type
                        user_id = None
                        
                        # Most participant types have user_id directly
                        if hasattr(participant, 'user_id'):
                            user_id = participant.user_id
                        # ChannelParticipantBanned has peer.user_id instead
                        elif hasattr(participant, 'peer') and hasattr(participant.peer, 'user_id'):
                            user_id = participant.peer.user_id
                        
                        # Skip if we couldn't determine user_id
                        if user_id is None:
                            continue
                        
                        # Find corresponding user
                        user = next((u for u in result.users if u.id == user_id), None)
                        if user:
                            all_participants.append({
                                'user': user,
                                'join_date': participant.date,
                                'username': user.username or 'No username',
                                'name': f"{user.first_name or ''} {user.last_name or ''}".strip()
                            })
                            valid_count += 1
                
                print(f"📄 Page {page}: Found {valid_count} participants with join dates (Total so far: {len(all_participants)})")
                
                offset += len(result.participants)
                if total is None:
                    total = result.count
                    print(f"📊 Total participants in channel: {total}")
                
                # Check if we've fetched all participants
                if len(result.participants) < limit:
                    print("📭 Reached end of participant list")
                    break
                
                # Progressive delay to avoid rate limits
                delay = min(3.0, 1.0 + (page * 0.05))
                print(f"⏳ Waiting {delay:.1f}s before next request...")
                await asyncio.sleep(delay)
                
                page += 1
                
            except FloodWaitError as e:
                wait_time = e.seconds + 10
                print(f"⚠️ RATE LIMIT HIT! Required wait: {wait_time} seconds - pausing participant fetching")
                await asyncio.sleep(wait_time)
            except SlowModeWaitError as e:
                wait_time = e.seconds + 5
                print(f"⚠️ SLOW MODE ACTIVE! Waiting {wait_time} seconds")
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f"❌ Critical error fetching participants: {str(e)}")
                break
        
        print(f"\n📊 FINAL COUNT: Found {len(all_participants)} participants with join dates out of {total} total members")
        
        # Filter users who joined during spam period
        spam_users = []
        
        for participant in all_participants:
            # CRITICAL FIX: Convert to timezone-aware UTC
            join_date = make_aware(participant['join_date'])
            
            if SPAM_START_TIME <= join_date <= SPAM_END_TIME:
                spam_users.append(participant)
        
        print(f"🚨 Found {len(spam_users)} users who joined during spam period")
        
        # Display first 5 spam users for verification
        print("\n🔍 First 5 spam users found:")
        for spam_user in spam_users[:5]:
            join_date_utc = make_aware(spam_user['join_date'])
            print(f"- {spam_user['name']} (@{spam_user['username']}) - Joined: {join_date_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        if len(spam_users) < 100 and len(spam_users) > 3:
            print("\n⚠️ WARNING: Found fewer than 100 spam users - double check your time window")
        elif not spam_users:
            print("❌ No spam users found in the specified time range - verify your SPAM_START_TIME and SPAM_END_TIME")
            return
        
        # Display full list if in dry run
        if DRY_RUN and len(spam_users) <= 50:
            print("\n📋 Full list of spam users:")
            for i, spam_user in enumerate(spam_users, 1):
                join_date_utc = make_aware(spam_user['join_date'])
                print(f"{i}. {spam_user['name']} (@{spam_user['username']}) - {join_date_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        # Confirm before banning
        if not DRY_RUN:
            confirm = input(f"\n⚠️ WARNING: About to BAN {len(spam_users)} users. Proceed? (yes/no): ")
            if confirm.lower() != 'yes':
                print("🛑 Operation cancelled")
                return
     
        # BAN USERS WITH OPTIMIZED RATE LIMIT HANDLING
        banned_count = 0
        failed_users = []
        start_time = datetime.now(timezone.utc)
        success_streak = 0
        current_delay = 2.0  # Start aggressive
        last_rate_limit = None
        rate_limit_recovery = False

        print(f"\n{'='*50}")
        print(f"⚡ Starting ban operation at {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"💡 DRY_RUN = {DRY_RUN}")
        print(f"💡 Total spam users: {len(spam_users)}")
        print(f"💡 Using scientifically optimized rate limiting")
        print(f"💡 Estimated time: {len(spam_users)*3.5/60:.1f} minutes (vs {len(spam_users)*25/60:.1f} with old method)")
        print(f"{'='*50}\n")

        for i, spam_user in enumerate(spam_users, 1):
            attempt = 1
            max_attempts = 2  # Reduced from 3 - be decisive
            
            while attempt <= max_attempts:
                try:
                    if DRY_RUN:
                        print(f"[DRY RUN] ({i}/{len(spam_users)}) Would ban: {spam_user['name']} (@{spam_user['username']})")
                    else:
                        start_op = time.time()
                        await client.edit_permissions(
                            chat,
                            spam_user['user'],
                            view_messages=False
                        )
                        op_time = time.time() - start_op
                        
                        print(f"✅ Banned ({i}/{len(spam_users)}): {spam_user['name']} (@{spam_user['username']}) [API: {op_time:.2f}s]")
                        banned_count += 1
                        success_streak += 1
                        rate_limit_recovery = False
                    
                    # DYNAMIC DELAY CALCULATION - THE KEY IMPROVEMENT
                    if success_streak < 50:
                        # Phase 1: Aggressive (first 50 bans)
                        current_delay = max(1.8, 2.2 - (success_streak * 0.01))
                    elif success_streak < 200:
                        # Phase 2: Moderate (bans 50-200)
                        current_delay = 2.5 + min(1.5, (success_streak - 50) * 0.02)
                    else:
                        # Phase 3: Conservative (after 200 bans)
                        current_delay = 3.5 + min(2.0, (success_streak - 200) * 0.005)
                    
                    # Special recovery mode after rate limit
                    if rate_limit_recovery:
                        current_delay = max(2.5, current_delay * 0.7)
                    
                    # Cap at reasonable maximum (8s instead of 45s)
                    current_delay = min(8.0, current_delay)
                    
                    # Add minimal jitter (only 5% variation)
                    jitter = random.uniform(0.95, 1.05)
                    actual_delay = current_delay * jitter
                    
                    if not DRY_RUN and i < len(spam_users):
                        remaining_time = (len(spam_users) - i) * current_delay
                        completion_time = datetime.now(timezone.utc) + timedelta(seconds=remaining_time)
                        print(f"⏳ Waiting {actual_delay:.2f}s (streak: {success_streak}) | Est. complete: {completion_time:%H:%M}")
                        await asyncio.sleep(actual_delay)
                    
                    break  # Exit retry loop on success
                    
                except FloodWaitError as e:
                    wait_time = e.seconds + 2  # Minimal buffer (Telegram is accurate)
                    print(f"⚠️ RATE LIMIT: {wait_time}s required (streak: {success_streak})")
                    
                    # CRITICAL: Use Telegram's EXACT timing
                    start_wait = time.time()
                    await asyncio.sleep(wait_time)
                    wait_actual = time.time() - start_wait
                    
                    # Record rate limit event
                    last_rate_limit = {
                        'streak': success_streak,
                        'required': wait_time,
                        'actual': wait_actual
                    }
                    success_streak = 0
                    rate_limit_recovery = True
                    
                    # IMPORTANT: Don't increment attempt counter for FloodWait
                    # We'll try this user again immediately after waiting
                    continue
                    
                except Exception as e:
                    error_msg = str(e)
                    if "USER_ADMIN_INVALID" in error_msg or "CHAT_ADMIN_REQUIRED" in error_msg:
                        print(f"🛑 CRITICAL: Lost admin privileges - stopping operation")
                        return
                    elif "USER_KICKED" in error_msg or "USER_BANNED_IN_CHANNEL" in error_msg:
                        print(f"ℹ️ User {spam_user['name']} already banned")
                        banned_count += 1
                    else:
                        print(f"❌ Error banning {spam_user['name']}: {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}")
                        failed_users.append(spam_user)
                    break
            
            # Progressive reset after sustained success
            if success_streak > 0 and success_streak % 100 == 0:
                print(f"🔄 Sustained success! Resetting delay to base value (streak: {success_streak})")
                current_delay = 2.0
        
        # Operation summary
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Remove microseconds
        total_seconds = duration.total_seconds()
        avg_time_per_ban = total_seconds / banned_count if banned_count > 0 else 0
        
        print(f"\n{'='*50}")
        print(f"⚡ Ban operation completed at {end_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"⏱️ Total duration: {duration_str}")
        print(f"📊 Processed: {len(spam_users)}/{len(spam_users)} spam users")
        print(f"✅ Successfully banned: {banned_count}")
        print(f"⏱️ Average time per ban: {avg_time_per_ban:.2f} seconds")
        print(f"❌ Failed bans: {len(failed_users)}")
        
        if failed_users:
            print("\n📋 Failed users:")
            for user in failed_users[:5]:  # Show first 5
                print(f"- {user['name']} (@{user['username']})")
            if len(failed_users) > 5:
                print(f"... and {len(failed_users)-5} more")
        
        if DRY_RUN:
            print("\nℹ️ This was a DRY RUN - no actual bans were performed")
            print(f"💡 To run actual bans, set DRY_RUN = False and rerun")
        else:
            print("\n✅ Operation completed successfully")
            print(f"💡 Performance: Processed {banned_count} bans at {60/avg_time_per_ban:.1f} bans/minute")
        
    finally:
        await client.disconnect()
        print("\n🔌 Client disconnected")

if __name__ == "__main__":
    print("🚀 Starting Telegram spam cleaner")
    print("ℹ️ Make sure you've authorized the session first!")
    print("-" * 50)
    asyncio.run(main())
