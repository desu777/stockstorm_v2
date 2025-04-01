import logging
import random
import string
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.contrib.auth.models import User
from home.models import TelegramConfig, UserProfile
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ContextTypes
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

def generate_verification_code(length=6):
    """Generate a random verification code"""
    letters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(letters) for _ in range(length))

class Command(BaseCommand):
    help = 'Runs the Telegram bot for crypto price alerts'

    def handle(self, *args, **options):
        self.stdout.write('Starting Telegram bot...')
        
        if not hasattr(settings, 'TELEGRAM_BOT_TOKEN'):
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN is not configured in settings'))
            return
        
        # Create the Application
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Add error handler
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Log the error and send a message to the user."""
            # Log the error
            logger.error(f"Exception while handling an update: {context.error}")
            
            # Send error message to console
            self.stdout.write(self.style.ERROR(f"Error: {context.error}"))
            
            # Try to notify the user
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "Sorry, something went wrong. The error has been logged and we'll fix it as soon as possible."
                )

        # Register the error handler
        application.add_error_handler(error_handler)
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("register", self.register_command))
        application.add_handler(CommandHandler("verify", self.verify_command))
        application.add_handler(CommandHandler("status", self.status_command))
        # Nowe, krótsze komendy dla botów
        application.add_handler(CommandHandler("51015rei", self.bnb_list_command))
        application.add_handler(CommandHandler("51015", self.bnb_list_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Start the Bot
        self.stdout.write('Bot started. Press Ctrl+C to stop.')
        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to start bot: {e}"))
            logger.error(f"Failed to start Telegram bot: {e}", exc_info=True)
            raise
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /start is issued."""
        await update.message.reply_html(
            f"👋 <b>Welcome to STOCKstorm Crypto Alerts Bot!</b>\n\n"
            f"I'll send you notifications when your cryptocurrency price alerts are triggered.\n\n"
            f"To get started, please use the /register command followed by your STOCKstorm username.\n"
            f"Example: <code>/register john_doe</code>\n\n"
            f"Use /help to see all available commands."
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        await update.message.reply_html(
            f"📚 <b>STOCKstorm Bot Commands:</b>\n\n"
            f"• <code>/start</code> - Start interacting with the bot\n"
            f"• <code>/help</code> - Show this help message\n"
            f"• <code>/register username</code> - Register your Telegram with STOCKstorm\n"
            f"• <code>/verify CODE</code> - Verify your account with the code from STOCKstorm\n"
            f"• <code>/status</code> - Check your registration status\n"
            f"• <code>/51015rei botname</code> - Show trades from your bot with reinvestment\n"
            f"• <code>/51015 botname</code> - Show trades from your bot without reinvestment\n\n"
            f"After registration, you'll receive alert notifications automatically when price thresholds are met."
        )
    
    @sync_to_async
    def get_user_by_username(self, username):
        """Get user by username in sync context"""
        return User.objects.filter(username=username).first()
        
    @sync_to_async
    def save_telegram_config(self, user, chat_id, verification_code):
        """Save telegram config in sync context"""
        chat_id_str = str(chat_id)  # Ensure chat_id is a string
        logger.info(f"Saving telegram config for user: {user.username}, chat_id: {chat_id_str}")
        
        with transaction.atomic():
            # First delete any existing unverified configs for this chat_id
            # This allows users to start over if they didn't complete verification
            TelegramConfig.objects.filter(chat_id=chat_id_str, is_verified=False).delete()
            
            # Check if user already has a verified config with a different chat_id
            existing_verified = TelegramConfig.objects.filter(user=user, is_verified=True).first()
            if existing_verified:
                logger.info(f"User {user.username} already has a verified config with chat_id: {existing_verified.chat_id}")
                # Update the verified config with the new chat_id and reset verification
                existing_verified.chat_id = chat_id_str
                existing_verified.verification_code = verification_code
                existing_verified.is_verified = False
                existing_verified.save()
                telegram_config = existing_verified
            else:
                # Create new config or update existing one for this chat_id
                telegram_config, created = TelegramConfig.objects.update_or_create(
                    user=user,
                    defaults={
                        'chat_id': chat_id_str,
                        'verification_code': verification_code,
                        'is_verified': False
                    }
                )
                action = "Created" if created else "Updated"
                logger.info(f"{action} telegram config for user: {user.username}")
            
            # Make sure profile has Telegram notifications enabled
            profile, created = UserProfile.objects.get_or_create(user=user)
            if not profile.telegram_notifications_enabled:
                profile.telegram_notifications_enabled = True
                profile.save()
                logger.info(f"Enabled telegram notifications for user: {user.username}")
                
        return telegram_config
    
    @sync_to_async
    def find_and_verify_telegram_config(self, chat_id, verification_code):
        """Find and verify telegram config in sync context"""
        chat_id_str = str(chat_id)  # Ensure chat_id is a string
        logger.info(f"Searching for config with chat_id: {chat_id_str}, code: {verification_code}")
        
        # First check if user already has a verified config
        existing_verified = TelegramConfig.objects.filter(
            chat_id=chat_id_str,
            is_verified=True
        ).first()
        
        if existing_verified:
            logger.info(f"User already has verified config: {existing_verified.user.username}")
            return None
            
        # Find config waiting for verification
        telegram_config = TelegramConfig.objects.filter(
            chat_id=chat_id_str,
            verification_code=verification_code,
            is_verified=False
        ).first()
        
        if not telegram_config:
            logger.warning(f"No matching config found for chat_id: {chat_id_str}, code: {verification_code}")
            return None
            
        logger.info(f"Found config for user: {telegram_config.user.username}, verifying...")
        telegram_config.is_verified = True
        telegram_config.verification_code = None  # Reset verification code after successful verification
        telegram_config.save()
        logger.info(f"Config verified successfully for user: {telegram_config.user.username}")
            
        return telegram_config
    
    @sync_to_async
    def get_telegram_config_by_chat_id(self, chat_id):
        """Get telegram config by chat_id in sync context"""
        # Ensure chat_id is a string
        chat_id_str = str(chat_id)
        logger.info(f"Looking for TelegramConfig with chat_id: {chat_id_str}")
        
        config = TelegramConfig.objects.filter(chat_id=chat_id_str).first()
        if config:
            logger.info(f"Found TelegramConfig for user: {config.user.username}, is_verified: {config.is_verified}")
        else:
            logger.warning(f"No TelegramConfig found for chat_id: {chat_id_str}")
            
        return config
    
    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Register the user's Telegram account with their STOCKstorm account."""
        args = context.args
        if not args or len(args) != 1:
            await update.message.reply_html(
                "⚠️ Please provide your STOCKstorm username.\n"
                "Example: <code>/register john_doe</code>"
            )
            return
        
        username = args[0]
        chat_id = update.effective_chat.id
        logger.info(f"Registration attempt for username: {username}, from chat_id: {chat_id}")
        
        try:
            # Check if this chat_id is already registered
            existing_config = await self.get_telegram_config_by_chat_id(chat_id)
            if existing_config and existing_config.is_verified:
                # Already verified
                await update.message.reply_html(
                    f"ℹ️ This Telegram account is already registered and verified for user <b>{existing_config.user.username}</b>.\n\n"
                    f"If you want to register a different account, you need to reset your Telegram connection in STOCKstorm settings first."
                )
                return
            
            # Look up the username
            user = await self.get_user_by_username(username)
            if not user:
                await update.message.reply_text(
                    f"❌ User '{username}' not found. Please check the username and try again."
                )
                return
            
            # Generate a verification code
            verification_code = generate_verification_code()
            
            # Save or update the TelegramConfig
            telegram_config = await self.save_telegram_config(user, chat_id, verification_code)
            
            await update.message.reply_html(
                f"✅ Registration initiated for user <b>{username}</b>!\n\n"
                f"Your verification code is: <code>{verification_code}</code>\n\n"
                f"Log in to your STOCKstorm account and enter this code in the Telegram verification section.\n"
                f"Then, use <code>/verify {verification_code}</code> to complete the registration."
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error during register command: {error_msg}")
            await update.message.reply_text(
                f"❌ An error occurred during registration: {error_msg}. Please try again later."
            )
    
    async def verify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Verify the user's account with the provided code."""
        args = context.args
        if not args or len(args) != 1:
            await update.message.reply_html(
                "⚠️ Please provide your verification code.\n"
                "Example: <code>/verify ABC123</code>"
            )
            return
        
        verification_code = args[0].upper()
        chat_id = str(update.effective_chat.id)
        logger.info(f"Verification attempt from chat_id: {chat_id} with code: {verification_code}")
        
        try:
            # Check if user is already verified
            existing_config = await self.get_telegram_config_by_chat_id(chat_id)
            if existing_config and existing_config.is_verified:
                logger.info(f"User already verified: {existing_config.user.username}")
                await update.message.reply_html(
                    f"✅ <b>Already Verified</b>\n\n"
                    f"Your Telegram account is already linked to <b>{existing_config.user.username}</b>.\n"
                    f"You will receive notifications when your crypto price alerts are triggered."
                )
                return
            
            # Find the TelegramConfig for this chat_id and code
            telegram_config = await self.find_and_verify_telegram_config(chat_id, verification_code)
            
            if not telegram_config:
                logger.warning(f"Verification failed for chat_id: {chat_id} with code: {verification_code}")
                if existing_config:
                    await update.message.reply_html(
                        f"❌ <b>Verification failed.</b>\n\n"
                        f"Invalid code. Your current verification code is <code>{existing_config.verification_code or 'MISSING'}</code>.\n"
                        f"Please try again with the correct code."
                    )
                else:
                    await update.message.reply_text(
                        "❌ Verification failed. Invalid code or your registration has expired.\n\n"
                        "Please start again with /register command."
                    )
                return
            
            username = telegram_config.user.username
            logger.info(f"Verification successful for user: {username}")
            
            await update.message.reply_html(
                f"🎉 <b>Verification successful!</b>\n\n"
                f"Your Telegram account is now linked to <b>{username}</b>.\n"
                f"You will receive notifications when your crypto price alerts are triggered.\n\n"
                f"Use /status to check your registration status at any time."
            )
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error during verify command: {error_message}")
            await update.message.reply_text(
                f"❌ An error occurred during verification: {error_message}. Please try again later."
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check the status of the user's Telegram registration."""
        chat_id = str(update.effective_chat.id)
        logger.info(f"Status command received from chat_id: {chat_id}")
        
        try:
            # Find the TelegramConfig for this chat_id
            telegram_config = await self.get_telegram_config_by_chat_id(chat_id)
            
            if not telegram_config:
                logger.info(f"No TelegramConfig found for chat_id: {chat_id}")
                await update.message.reply_html(
                    "❓ <b>Status: Not Registered</b>\n\n"
                    "You haven't registered your Telegram account yet.\n"
                    "Use <code>/register username</code> to link your STOCKstorm account."
                )
                return
            
            username = telegram_config.user.username
            verified = telegram_config.is_verified
            logger.info(f"TelegramConfig found for user: {username}, is_verified: {verified}")
            
            if verified:
                await update.message.reply_html(
                    f"✅ <b>Status: Verified</b>\n\n"
                    f"Your Telegram account is linked to <b>{username}</b>.\n"
                    f"You will receive notifications when your crypto price alerts are triggered."
                )
            else:
                verification_code = telegram_config.verification_code or "CODE_MISSING"
                await update.message.reply_html(
                    f"⏳ <b>Status: Pending Verification</b>\n\n"
                    f"Your Telegram account is linked to <b>{username}</b> but not verified yet.\n"
                    f"Use <code>/verify {verification_code}</code> to complete registration."
                )
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Error during status command: {error_message}")
            await update.message.reply_text(
                f"❌ An error occurred while checking your status: {error_message}. Please try again later."
            )
    
    @sync_to_async
    def get_user_bots(self, user_id):
        """Get a list of BNB bots for a user"""
        from django.contrib.auth.models import User
        from home.models import Bot
        
        user = User.objects.filter(id=user_id).first()
        if not user:
            return []
            
        # Get all BNB bots for the user
        return list(Bot.objects.filter(user=user, broker_type='BNB').values('id', 'name', 'instrument', 'status', 'microservice_bot_id'))
    
    @sync_to_async
    def get_bot_by_name(self, user_id, bot_name):
        """Get a BNB bot by name for a user"""
        from django.contrib.auth.models import User
        from home.models import Bot
        
        user = User.objects.filter(id=user_id).first()
        if not user:
            return None
            
        # Find the bot by name (case-insensitive)
        return Bot.objects.filter(user=user, broker_type='BNB', name__iexact=bot_name).first()
    
    @sync_to_async
    def get_bot_trades(self, bot_id, microservice_bot_id, user_id):
        """Get trades for a BNB bot"""
        from django.conf import settings
        import requests
        import io
        import csv
        from home.views import get_token
        
        # Get token for microservice
        microservice_token = get_token(user_id)
        if not microservice_token:
            return None, "Couldn't authenticate with microservice. Please check your settings."
            
        # Build URL to microservice
        url = f"{settings.BNB_MICROSERVICE_URL}/export_bnb_trades_csv/{microservice_bot_id}/"
        
        # Set authorization header
        headers = {
            "Authorization": f"Token {microservice_token}"
        }
        
        try:
            # Query microservice
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Process CSV data
                content = response.content.decode('utf-8')
                
                # Determine the delimiter - could be ; or ,
                if ';' in content.split('\n')[0]:
                    delimiter = ';'
                else:
                    delimiter = ','
                    
                logger.info(f"Using delimiter '{delimiter}' for BNB CSV")
                
                csv_data = io.StringIO(content)
                csv_reader = csv.reader(csv_data, delimiter=delimiter)
                
                # Extract data from CSV
                rows = list(csv_reader)
                if len(rows) < 2:  # Check if there's at least a header and one data row
                    return [], "No trades found for this bot."
                    
                header = rows[0]
                trades = rows[1:]  # Skip header
                
                # Dodajemy logging dla debugowania
                logger.info(f"CSV Header for BNB bot: {header}")
                if trades:
                    logger.info(f"First trade row example: {trades[0]}")
                
                # Find column indexes - sprawdźmy dokładnie nagłówki
                logger.info(f"Headers from CSV: {header}")
                
                # Użyj nowej funkcji do odgadnięcia indeksów kolumn
                column_indexes = self.guess_column_indexes(header, trades)
                
                logger.info(f"Mapped column indexes: {column_indexes}")
                
                return trades, header
            else:
                return None, f"Error from microservice ({url}): {response.status_code} {response.text}"
        except Exception as e:
            return None, f"Error fetching trades from {url}: {str(e)}"
    
    async def bnb_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trades from a BNB bot"""
        chat_id = update.effective_chat.id
        args = context.args
        
        try:
            # Check if user is authenticated
            telegram_config = await self.get_telegram_config_by_chat_id(chat_id)
            if not telegram_config or not telegram_config.is_verified:
                await update.message.reply_html(
                    "❌ <b>Not Authenticated</b>\n\n"
                    "You need to register and verify your account first.\n"
                    "Use <code>/register username</code> to get started."
                )
                return
                
            user_id = telegram_config.user.id
            user_name = telegram_config.user.username
            
            # No arguments - show list of bots
            if not args:
                bots = await self.get_user_bots(user_id)
                if not bots:
                    await update.message.reply_html(
                        "❌ <b>No BNB Bots Found</b>\n\n"
                        "You don't have any BNB bots set up yet."
                    )
                    return
                    
                # Format list of bots
                bot_list = "\n".join([
                    f"• <b>{bot['name']}</b> ({bot['instrument']}) - <i>{bot['status']}</i>"
                    for bot in bots
                ])
                
                await update.message.reply_html(
                    f"📊 <b>Your BNB Bots:</b>\n\n"
                    f"{bot_list}\n\n"
                    f"To see trades for a specific bot, use:\n"
                    f"<code>/bnb_list botname</code>"
                )
                return
                
            # Get bot by name
            bot_name = args[0]
            bot = await self.get_bot_by_name(user_id, bot_name)
            
            if not bot:
                await update.message.reply_html(
                    f"❌ <b>Bot Not Found</b>\n\n"
                    f"Couldn't find a BNB bot named '<b>{bot_name}</b>'.\n"
                    f"Use <code>/bnb_list</code> to see all your bots."
                )
                return
                
            if not bot.microservice_bot_id:
                await update.message.reply_html(
                    f"❌ <b>Bot Error</b>\n\n"
                    f"Bot '<b>{bot.name}</b>' doesn't have a valid microservice ID."
                )
                return
                
            # Get trades for bot
            trades, header = await self.get_bot_trades(bot.id, bot.microservice_bot_id, user_id)
            
            if trades is None:
                await update.message.reply_html(
                    f"❌ <b>Error</b>\n\n"
                    f"Failed to get trades: {header}"
                )
                return
                
            if not trades:
                await update.message.reply_html(
                    f"ℹ️ <b>No Trades</b>\n\n"
                    f"Bot '<b>{bot.name}</b>' doesn't have any trades yet."
                )
                return
                
            # Calculate total profit
            total_profit = 0
            try:
                profit_index = header.index("Profit")
                for trade in trades:
                    if len(trade) > profit_index:
                        profit_str = trade[profit_index].replace(',', '.')
                        if profit_str:  # Check if not empty
                            try:
                                profit_value = float(profit_str)
                                total_profit += profit_value
                            except ValueError:
                                logger.warning(f"Could not convert profit to float: {profit_str}")
                                # Skip this trade for total profit calculation
            except (ValueError, IndexError) as e:
                # If profit can't be calculated, just continue without it
                logger.warning(f"Error calculating total profit: {str(e)}")
                
            # Format trades for display (limit to 10 latest)
            latest_trades = trades[-10:] if len(trades) > 10 else trades
            
            # Find column indexes - sprawdźmy dokładnie nagłówki
            logger.info(f"Headers from CSV: {header}")
            
            # Użyj nowej funkcji do odgadnięcia indeksów kolumn
            column_indexes = self.guess_column_indexes(header, trades)
            
            logger.info(f"Mapped column indexes: {column_indexes}")
            
            # Jeśli nie możemy znaleźć podstawowych kolumn, użyjmy domyślnych indeksów
            level_idx = column_indexes.get('level', 0)
            price_idx = column_indexes.get('open_price', 1)
            close_price_idx = column_indexes.get('close_price', 2)
            profit_idx = column_indexes.get('profit', 3)
            status_idx = column_indexes.get('status', 6)
            open_time_idx = column_indexes.get('open_time', 4)
            close_time_idx = column_indexes.get('close_time', 5)
            side_idx = column_indexes.get('side', -1)  # -1 if not found
            
            # Format trades nicely
            trades_text = ""
            for i, trade in enumerate(reversed(latest_trades)):  # Show newest first
                try:
                    # Log the raw trade data for debugging
                    logger.info(f"Processing trade row: {trade}")
                    
                    if len(trade) <= max(filter(lambda x: x >= 0, [level_idx, price_idx, close_price_idx, profit_idx, status_idx, open_time_idx, close_time_idx, side_idx])):
                        logger.warning(f"Trade has insufficient columns: {len(trade)} vs needed: {max(filter(lambda x: x >= 0, [level_idx, price_idx, close_price_idx, profit_idx, status_idx, open_time_idx, close_time_idx, side_idx]))}")
                        continue  # Skip trades with incomplete data
                        
                    level = trade[level_idx] if level_idx < len(trade) else "?"
                    side = trade[side_idx] if side_idx >= 0 and side_idx < len(trade) else ""
                    
                    # Bezpieczne pobranie ceny otwarcia
                    price = "N/A"
                    if price_idx < len(trade) and trade[price_idx]:
                        price = trade[price_idx].replace(',', '.')
                    
                    # Bezpieczne pobranie ceny zamknięcia
                    close_price = "N/A"
                    if close_price_idx < len(trade) and trade[close_price_idx]:
                        close_price = trade[close_price_idx].replace(',', '.')
                    
                    # Bezpieczne pobranie zysku
                    profit = "0"
                    profit_float = 0
                    if profit_idx < len(trade) and trade[profit_idx]:
                        profit = trade[profit_idx].replace(',', '.')
                        try:
                            profit_float = float(profit)
                        except ValueError:
                            pass
                    
                    # Bezpieczne pobranie statusu
                    status = "?"
                    if status_idx < len(trade) and trade[status_idx]:
                        status = trade[status_idx]
                    
                    # Bezpieczne pobranie czasu otwarcia
                    open_time = "?"
                    if open_time_idx < len(trade) and trade[open_time_idx]:
                        open_time = trade[open_time_idx]
                    
                    # Bezpieczne pobranie czasu zamknięcia
                    close_time = "-"
                    if close_time_idx < len(trade) and trade[close_time_idx]:
                        close_time = trade[close_time_idx]
                    
                    # Format trade line - prostszy format zgodny z CSV
                    trades_text += (
                        f"{i+1}. <b>{level}</b>\n"
                        f"   Open Price: <b>{price}</b>\n"
                    )
                    
                    # Dodaj cenę zamknięcia tylko jeśli dostępna
                    if close_price != "N/A":
                        trades_text += f"   Close Price: <b>{close_price}</b>\n"
                    else:
                        trades_text += f"   Close Price: -\n"
                    
                    # Dodaj profit
                    if profit_float != 0:
                        trades_text += f"   Profit: <b>{profit}</b>\n"
                    else:
                        trades_text += f"   Profit: -\n"
                    
                    # Czas otwarcia i zamknięcia
                    trades_text += f"   Open Time: <i>{open_time}</i>\n"
                    trades_text += f"   Close Time: <i>{close_time}</i>\n"
                    
                    # Status
                    trades_text += f"   Status: <b>{status}</b>\n\n"
                    
                except Exception as e:
                    logger.error(f"Error formatting trade: {str(e)}")
                    # Skip this trade in display
            
            # Format response
            response = (
                f"📊 <b>Trades for {bot.name} ({bot.instrument})</b>\n\n"
                f"Status: <b>{bot.status}</b>\n"
                f"Total trades: <b>{len(trades)}</b>\n"
            )
            
            if total_profit != 0:
                profit_emoji = "✅" if total_profit > 0 else "❌"
                response += f"Total profit: <b>{profit_emoji} {total_profit:.2f}</b>\n"
                
            response += f"\n<b>Latest trades:</b>\n\n{trades_text}"
            
            if len(trades) > 10:
                response += f"Showing 10 of {len(trades)} trades...\n"
                
            # Add link to web interface
            response += (
                f"\nTo see complete details and download CSV, visit your dashboard at:\n"
                f"<a href='https://stockstorm.pl/bnb/{bot.id}/'>STOCKstorm Dashboard</a>"
            )
            
            await update.message.reply_html(response)
            
        except Exception as e:
            logger.error(f"Error in bnb_list_command: {str(e)}")
            await update.message.reply_html(
                f"❌ <b>Error</b>\n\n"
                f"Something went wrong: {str(e)}\n"
                f"Please try again later."
            )
    
    @sync_to_async
    def get_user_xtb_bots(self, user_id):
        """Get list of XTB bots for a user"""
        from home.models import Bot
        bots = Bot.objects.filter(user_id=user_id, broker_type='XTB').values(
            'id', 'name', 'instrument', 'status', 'microservice_bot_id'
        )
        return list(bots)

    @sync_to_async
    def get_xtb_bot_by_name(self, user_id, bot_name):
        """Get XTB bot by name"""
        from home.models import Bot, User
        
        user = User.objects.filter(id=user_id).first()
        if not user:
            return None
            
        # Find the bot by name (case-insensitive)
        return Bot.objects.filter(user=user, broker_type='XTB', name__iexact=bot_name).first()
    
    def guess_column_indexes(self, header, rows):
        """Helper function to guess column indexes based on data patterns"""
        # Słownik na indeksy kolumn
        column_indexes = {}
        
        # Najpierw sprawdź nazwy kolumn w nagłówku
        for i, col_name in enumerate(header):
            if not col_name:
                continue
                
            col_name_lower = col_name.lower().strip()
            if 'level' in col_name_lower:
                column_indexes['level'] = i
            elif 'open' in col_name_lower and 'price' in col_name_lower:
                column_indexes['open_price'] = i
            elif 'close' in col_name_lower and 'price' in col_name_lower:
                column_indexes['close_price'] = i
            elif 'profit' in col_name_lower:
                column_indexes['profit'] = i
            elif 'status' in col_name_lower:
                column_indexes['status'] = i
            elif 'open' in col_name_lower and 'time' in col_name_lower:
                column_indexes['open_time'] = i
            elif 'close' in col_name_lower and 'time' in col_name_lower:
                column_indexes['close_time'] = i
            elif 'side' in col_name_lower:
                column_indexes['side'] = i
        
        # Jeśli nie znaleziono kolumn po nazwach, spróbuj odgadnąć na podstawie danych
        if not column_indexes and len(rows) > 0:
            first_row = rows[0]
            # Sprawdź wzorce charakterystyczne dla poszczególnych kolumn
            for i, value in enumerate(first_row):
                if not value:
                    continue
                    
                value_lower = value.lower().strip()
                # Poziom często zaczyna się od "lv"
                if value_lower.startswith('lv'):
                    column_indexes['level'] = i
                    
                # Ceny zwykle mają format liczbowy (z przecinkiem lub kropką)
                elif any(c.isdigit() for c in value) and (',' in value or '.' in value):
                    # Jeśli nie mamy jeszcze open_price, to to będzie pierwsza kolumna z liczbą
                    if 'open_price' not in column_indexes:
                        column_indexes['open_price'] = i
                    # Druga kolumna z liczbą to prawdopodobnie close_price
                    elif 'close_price' not in column_indexes:
                        column_indexes['close_price'] = i
                    # Trzecia kolumna z liczbą to prawdopodobnie profit
                    elif 'profit' not in column_indexes:
                        column_indexes['profit'] = i
                        
                # Daty często mają format z kropkami lub myślnikami i zawierają cyfry
                elif any(c.isdigit() for c in value) and ('.' in value or '-' in value or ':' in value):
                    # Pierwsza data to prawdopodobnie open_time
                    if 'open_time' not in column_indexes:
                        column_indexes['open_time'] = i
                    # Druga data to prawdopodobnie close_time
                    elif 'close_time' not in column_indexes:
                        column_indexes['close_time'] = i
                        
                # Status często zawiera słowa jak "OPEN", "CLOSED", itp.
                elif value_lower in ['open', 'closed', 'pending', 'cancelled', 'executed']:
                    column_indexes['status'] = i
                    
                # Side często zawiera "BUY" lub "SELL"
                elif value_lower in ['buy', 'sell']:
                    column_indexes['side'] = i
        
        logger.info(f"Guessed column indexes: {column_indexes}")
        return column_indexes
        
    @sync_to_async
    def get_xtb_bot_trades(self, bot_id, microservice_bot_id, user_id):
        """Get trades for a XTB bot"""
        from django.conf import settings
        import requests
        import io
        import csv
        from home.views import get_token
        
        # Get token for microservice
        microservice_token = get_token(user_id)
        if not microservice_token:
            return None, "Couldn't authenticate with microservice. Please check your settings."
            
        # Build URL to microservice - używamy poprawnego URL jak w funkcji export_bot_trades
        url = f"{settings.MICROSERVICE_URL2}/export_bot_trades_csv/{microservice_bot_id}/"
        
        # Set authorization header
        headers = {
            "Authorization": f"Token {microservice_token}"
        }
        
        try:
            # Query microservice
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Process CSV data
                content = response.content.decode('utf-8')
                
                # Determine the delimiter - could be ; or ,
                if ';' in content.split('\n')[0]:
                    delimiter = ';'
                else:
                    delimiter = ','
                    
                logger.info(f"Using delimiter '{delimiter}' for XTB CSV")
                
                csv_data = io.StringIO(content)
                csv_reader = csv.reader(csv_data, delimiter=delimiter)
                
                # Extract data from CSV
                rows = list(csv_reader)
                if len(rows) < 2:  # Check if there's at least a header and one data row
                    return [], "No trades found for this bot."
                    
                header = rows[0]
                trades = rows[1:]  # Skip header
                
                # Dodajemy logging dla debugowania
                logger.info(f"CSV Header for XTB bot: {header}")
                if trades:
                    logger.info(f"First trade row example: {trades[0]}")
                
                # Find column indexes - sprawdźmy dokładnie nagłówki
                logger.info(f"Headers from CSV: {header}")
                
                # Użyj nowej funkcji do odgadnięcia indeksów kolumn
                column_indexes = self.guess_column_indexes(header, trades)
                
                logger.info(f"Mapped column indexes: {column_indexes}")
                
                return trades, header
            else:
                return None, f"Error from microservice ({url}): {response.status_code} {response.text}"
        except Exception as e:
            return None, f"Error fetching trades from {url}: {str(e)}"
    
    async def xtb_list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show trades from a XTB bot"""
        chat_id = update.effective_chat.id
        args = context.args
        
        try:
            logger.info(f"XTB list command received from chat_id: {chat_id}, args: {args}")
            
            # Check if user is authenticated
            telegram_config = await self.get_telegram_config_by_chat_id(chat_id)
            if not telegram_config or not telegram_config.is_verified:
                logger.warning(f"User not authenticated, chat_id: {chat_id}")
                await update.message.reply_html(
                    "❌ <b>Not Authenticated</b>\n\n"
                    "You need to register and verify your account first.\n"
                    "Use <code>/register username</code> to get started."
                )
                return
                
            user_id = telegram_config.user.id
            user_name = telegram_config.user.username
            logger.info(f"User authenticated: {user_name} (ID: {user_id})")
            
            # No arguments - show list of bots
            if not args:
                logger.info(f"Getting XTB bots list for user: {user_name}")
                bots = await self.get_user_xtb_bots(user_id)
                logger.info(f"Found {len(bots)} XTB bots for user: {user_name}")
                
                if not bots:
                    await update.message.reply_html(
                        "❌ <b>No XTB Bots Found</b>\n\n"
                        "You don't have any XTB bots set up yet."
                    )
                    return
                    
                # Format list of bots
                bot_list = "\n".join([
                    f"• <b>{bot['name']}</b> ({bot['instrument']}) - <i>{bot['status']}</i>"
                    for bot in bots
                ])
                
                await update.message.reply_html(
                    f"📊 <b>Your XTB Bots:</b>\n\n"
                    f"{bot_list}\n\n"
                    f"To see trades for a specific bot, use:\n"
                    f"<code>/51015xtb_list botname</code>"
                )
                return
                
            # Get bot by name
            bot_name = args[0]
            logger.info(f"Getting XTB bot by name: '{bot_name}' for user: {user_name}")
            bot = await self.get_xtb_bot_by_name(user_id, bot_name)
            
            if not bot:
                logger.warning(f"XTB bot not found: '{bot_name}' for user: {user_name}")
                await update.message.reply_html(
                    f"❌ <b>Bot Not Found</b>\n\n"
                    f"Couldn't find a XTB bot named '<b>{bot_name}</b>'.\n"
                    f"Use <code>/51015xtb_list</code> to see all your bots."
                )
                return
                
            logger.info(f"Found XTB bot: {bot.name} (ID: {bot.id}, Microservice ID: {bot.microservice_bot_id})")
            
            if not bot.microservice_bot_id:
                logger.warning(f"XTB bot missing microservice ID: '{bot_name}' (ID: {bot.id})")
                await update.message.reply_html(
                    f"❌ <b>Bot Error</b>\n\n"
                    f"Bot '<b>{bot.name}</b>' doesn't have a valid microservice ID."
                )
                return
                
            # Get trades for bot
            logger.info(f"Getting trades for XTB bot: {bot.name} (Microservice ID: {bot.microservice_bot_id})")
            trades, header = await self.get_xtb_bot_trades(bot.id, bot.microservice_bot_id, user_id)
            
            if trades is None:
                logger.error(f"Error getting trades for XTB bot: {bot.name}, error: {header}")
                await update.message.reply_html(
                    f"❌ <b>Error</b>\n\n"
                    f"Failed to get trades: {header}"
                )
                return
                
            logger.info(f"Retrieved {len(trades)} trades for XTB bot: {bot.name}")
                
            if not trades:
                await update.message.reply_html(
                    f"ℹ️ <b>No Trades</b>\n\n"
                    f"Bot '<b>{bot.name}</b>' doesn't have any trades yet."
                )
                return
                
            # Calculate total profit
            total_profit = 0
            try:
                profit_index = header.index("Profit")
                for trade in trades:
                    if len(trade) > profit_index:
                        profit_str = trade[profit_index].replace(',', '.')
                        if profit_str:  # Check if not empty
                            try:
                                profit_value = float(profit_str)
                                total_profit += profit_value
                            except ValueError:
                                logger.warning(f"Could not convert profit to float: {profit_str}")
                                # Skip this trade for total profit calculation
            except (ValueError, IndexError) as e:
                # If profit can't be calculated, just continue without it
                logger.warning(f"Error calculating total profit: {str(e)}")
                
            # Format trades for display (limit to 10 latest)
            latest_trades = trades[-10:] if len(trades) > 10 else trades
            
            # Find column indexes - sprawdźmy dokładnie nagłówki
            logger.info(f"Headers from CSV: {header}")
            
            # Użyj nowej funkcji do odgadnięcia indeksów kolumn
            column_indexes = self.guess_column_indexes(header, trades)
            
            logger.info(f"Mapped column indexes: {column_indexes}")
            
            # Jeśli nie możemy znaleźć podstawowych kolumn, użyjmy domyślnych indeksów
            level_idx = column_indexes.get('level', 0)
            price_idx = column_indexes.get('open_price', 1)
            close_price_idx = column_indexes.get('close_price', 2)
            profit_idx = column_indexes.get('profit', 3)
            status_idx = column_indexes.get('status', 6)
            open_time_idx = column_indexes.get('open_time', 4)
            close_time_idx = column_indexes.get('close_time', 5)
            side_idx = column_indexes.get('side', -1)  # -1 if not found
            
            # Format trades nicely
            trades_text = ""
            for i, trade in enumerate(reversed(latest_trades)):  # Show newest first
                try:
                    # Log the raw trade data for debugging
                    logger.info(f"Processing trade row: {trade}")
                    
                    if len(trade) <= max(filter(lambda x: x >= 0, [level_idx, price_idx, close_price_idx, profit_idx, status_idx, open_time_idx, close_time_idx, side_idx])):
                        logger.warning(f"Trade has insufficient columns: {len(trade)} vs needed: {max(filter(lambda x: x >= 0, [level_idx, price_idx, close_price_idx, profit_idx, status_idx, open_time_idx, close_time_idx, side_idx]))}")
                        continue  # Skip trades with incomplete data
                        
                    level = trade[level_idx] if level_idx < len(trade) else "?"
                    side = trade[side_idx] if side_idx >= 0 and side_idx < len(trade) else ""
                    
                    # Bezpieczne pobranie ceny otwarcia
                    price = "N/A"
                    if price_idx < len(trade) and trade[price_idx]:
                        price = trade[price_idx].replace(',', '.')
                    
                    # Bezpieczne pobranie ceny zamknięcia
                    close_price = "N/A"
                    if close_price_idx < len(trade) and trade[close_price_idx]:
                        close_price = trade[close_price_idx].replace(',', '.')
                    
                    # Bezpieczne pobranie zysku
                    profit = "0"
                    profit_float = 0
                    if profit_idx < len(trade) and trade[profit_idx]:
                        profit = trade[profit_idx].replace(',', '.')
                        try:
                            profit_float = float(profit)
                        except ValueError:
                            pass
                    
                    # Bezpieczne pobranie statusu
                    status = "?"
                    if status_idx < len(trade) and trade[status_idx]:
                        status = trade[status_idx]
                    
                    # Bezpieczne pobranie czasu otwarcia
                    open_time = "?"
                    if open_time_idx < len(trade) and trade[open_time_idx]:
                        open_time = trade[open_time_idx]
                    
                    # Bezpieczne pobranie czasu zamknięcia
                    close_time = "-"
                    if close_time_idx < len(trade) and trade[close_time_idx]:
                        close_time = trade[close_time_idx]
                    
                    # Format trade line - prostszy format zgodny z CSV
                    trades_text += (
                        f"{i+1}. <b>{level}</b>\n"
                        f"   Open Price: <b>{price}</b>\n"
                    )
                    
                    # Dodaj cenę zamknięcia tylko jeśli dostępna
                    if close_price != "N/A":
                        trades_text += f"   Close Price: <b>{close_price}</b>\n"
                    else:
                        trades_text += f"   Close Price: -\n"
                    
                    # Dodaj profit
                    if profit_float != 0:
                        trades_text += f"   Profit: <b>{profit}</b>\n"
                    else:
                        trades_text += f"   Profit: -\n"
                    
                    # Czas otwarcia i zamknięcia
                    trades_text += f"   Open Time: <i>{open_time}</i>\n"
                    trades_text += f"   Close Time: <i>{close_time}</i>\n"
                    
                    # Status
                    trades_text += f"   Status: <b>{status}</b>\n\n"
                    
                except Exception as e:
                    logger.error(f"Error formatting trade: {str(e)}")
                    # Skip this trade in display
            
            # Format response
            response = (
                f"📊 <b>Trades for {bot.name} ({bot.instrument})</b>\n\n"
                f"Status: <b>{bot.status}</b>\n"
                f"Total trades: <b>{len(trades)}</b>\n"
            )
            
            if total_profit != 0:
                profit_emoji = "✅" if total_profit > 0 else "❌"
                response += f"Total profit: <b>{profit_emoji} {total_profit:.2f}</b>\n"
                
            response += f"\n<b>Latest trades:</b>\n\n{trades_text}"
            
            if len(trades) > 10:
                response += f"Showing 10 of {len(trades)} trades...\n"
                
            # Add link to web interface
            response += (
                f"\nTo see complete details and download CSV, visit your dashboard at:\n"
                f"<a href='https://stockstorm.pl/bot/{bot.id}/'>STOCKstorm Dashboard</a>"
            )
            
            await update.message.reply_html(response)
            
        except Exception as e:
            logger.error(f"Error in xtb_list_command: {str(e)}")
            await update.message.reply_html(
                f"❌ <b>Error</b>\n\n"
                f"Something went wrong: {str(e)}\n"
                f"Please try again later."
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Echo the user message - default handler for text messages."""
        await update.message.reply_text(
            "I only respond to commands. Type /help to see available commands."
        ) 