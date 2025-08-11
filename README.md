# Telegram Ban Spam Users

A practical script to identify and ban mass spam users from Telegram groups/channels. This tool handles Telegram's API limitations correctly to efficiently process large numbers of bans while respecting rate limits.

## How It Works

1. **Fetches participants** with their join dates using Telegram's API
2. **Filters users** who joined during a specific time window you define
3. **Bans users** with an optimized delay algorithm that adapts to Telegram's rate limits
4. **Provides detailed reporting** of success/failure rates and performance metrics

## Installation

### Prerequisites
- Python
- Telegram API credentials ([get from my.telegram.org](https://my.telegram.org))

### Steps

1. Install required library:
```bash
# Clone the repository
git clone https://github.com/your-username/telegram-bulk-banUsers.git
cd telegram-bulk-banUsers

# Install dependencies
pip install telethon
```

2. Get API credentials:
   - Go to https://my.telegram.org
   - Log in with your phone number
   - Create a new application to get API_ID and API_HASH


## Configuration

Edit `banUsers.py` with your settings:

```python
# Your API credentials (get from https://my.telegram.org)
API_ID = 'YOUR_API_ID'  # Replace with your actual API ID
API_HASH = 'YOUR_API_HASH'  # Replace with your actual API hash
PHONE_NUMBER = '+YOUR_PHONE'  # Replace with your phone in international format

# Configuration
CHAT_ID = '@your_group'  # Your group/channel username or ID
SPAM_START_TIME = datetime(2023, 10, 5, 14, 30, tzinfo=timezone.utc)  # UTC time YYYY,DD,MM,HH,MM
SPAM_END_TIME = datetime(2023, 10, 5, 14, 45, tzinfo=timezone.utc)  # UTC time YYYY,DD,MM,HH,MM
DRY_RUN = True  # Set to False to actually ban users
```

### Critical Timezone Note
- **All times must be in UTC** - Telegram stores all join dates in UTC
- Example: If spam happened at 9:30 AM EST (UTC-4), set:
  ```python
  SPAM_START_TIME = datetime(2023, 10, 5, 13, 30, tzinfo=timezone.utc)
  ```

## Usage

1. **First run with DRY_RUN = True** to verify it finds the correct users:
   ```bash
   python banUsers.py
   ```
   
2. **Review the output** - check the first 5 spam users to confirm timing is correct

3. **Set DRY_RUN = False** and run again to execute bans

4. **Confirm** when prompted:
   ```
   WARNING: About to BAN 2845 users. Proceed? (yes/no):
   ```

### Performance Expectations
| Spam Users | Estimated Time |
|------------|----------------|
| 500        | ~45-60 minutes |
| 1,000      | ~1.5-2 hours   |
| 3,000      | ~2.5-3.5 hours |
| 5,000      | ~4-5 hours     |

*Note: Actual performance depends on your account's standing with Telegram*

## Important Considerations

1. **Account Restrictions**:
   - After mass banning, Telegram may temporarily restrict your account
   - Wait 24-48 hours before running again if you encounter issues

2. **Time Window Accuracy**:
   - Incorrect UTC timing is the most common issue
   - If finding 0 users, expand your time window by 5 minutes on both ends

3. **Rate Limit Behavior**:
   - The script automatically handles rate limits, but may need to slow down
   - If consistently hitting rate limits, stop and wait 24 hours

4. **Admin Permissions**:
   - You must have "Ban Users" permission
   - The account must be able to access participant join dates

## Troubleshooting

### "Found 0 users who joined during spam period"
- Verify your time window is in **UTC**, not local time
- Expand your time window by 5-10 minutes on both ends
- Confirm spam actually occurred in that window

### Rate limit errors during participant fetching
- Wait 24-48 hours before trying again
- Consider using a different admin account
- Reduce `limit = 100` (from 200) in the participant fetching section

### Only finding a small number of users (e.g., 3-50)
- Telegram is likely rate-limiting your participant requests
- Wait 24 hours and try again
- Your account may be temporarily restricted for admin operations

### Bans taking too long (30+ seconds per ban)
- Your account has likely been flagged from previous operations
- Wait 48-72 hours for limits to reset
- Consider using a different admin account for future operations

## Disclaimer

This tool is intended for legitimate spam cleanup in groups you administer.

- Use responsibly and ethically
- Respect Telegram's [Terms of Service](https://core.telegram.org/api/terms)
- The authors are not responsible for misuse or account restrictions

> **WARNING**: Improper use of this tool could result in your Telegram account being restricted. Always verify spam users before banning and respect Telegram's rate limits.

---

