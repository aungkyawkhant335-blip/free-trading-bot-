import os
import sqlite3
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import logging

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
def init_db():
    conn = sqlite3.connect('/tmp/trades.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades
                 (id INTEGER PRIMARY KEY, symbol TEXT, entry_price REAL, 
                  size REAL, strategy TEXT, status TEXT DEFAULT 'open',
                  exit_price REAL, pnl REAL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# Command handlers
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📗 FREE Trading Journal Bot\n\n"
        "Commands:\n"
        "/add SYMBOL PRICE SIZE STRATEGY\n"
        "/view - Show all trades\n"
        "/close SYMBOL EXIT_PRICE\n" 
        "/stats - Show performance\n\n"
        "Examples:\n"
        "/add BTC 35000 0.1 swing\n"
        "/close BTC 36000\n"
        "/view\n"
        "/stats"
    )

def add_trade(update: Update, context: CallbackContext):
    if len(context.args) != 4:
        update.message.reply_text("❌ Use: /add SYMBOL PRICE SIZE STRATEGY\nExample: /add BTC 35000 0.1 swing")
        return
    
    symbol, price, size, strategy = context.args
    try:
        conn = sqlite3.connect('/tmp/trades.db')
        c = conn.cursor()
        c.execute("INSERT INTO trades (symbol, entry_price, size, strategy) VALUES (?, ?, ?, ?)",
                  (symbol.upper(), float(price), float(size), strategy))
        conn.commit()
        conn.close()
        update.message.reply_text(f"✅ Trade added:\n{symbol.upper()} @ ${price}\nSize: {size}\nStrategy: {strategy}")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

def view_trades(update: Update, context: CallbackContext):
    conn = sqlite3.connect('/tmp/trades.db')
    c = conn.cursor()
    c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 10")
    trades = c.fetchall()
    conn.close()
    
    if not trades:
        update.message.reply_text("📭 No trades found")
        return
    
    response = "📋 Recent Trades:\n\n"
    for trade in trades:
        id, symbol, entry, size, strategy, status, exit_price, pnl, created_at = trade
        response += f"#{id} {symbol}: ${entry} x {size} ({strategy}) - {status}\n"
        if status == 'closed':
            response += f"  Exit: ${exit_price} | PnL: ${pnl:.2f}\n"
        response += "\n"
    
    update.message.reply_text(response)

def close_trade(update: Update, context: CallbackContext):
    if len(context.args) != 2:
        update.message.reply_text("❌ Use: /close SYMBOL EXIT_PRICE\nExample: /close BTC 36000")
        return
    
    symbol, exit_price = context.args
    try:
        conn = sqlite3.connect('/tmp/trades.db')
        c = conn.cursor()
        
        c.execute("SELECT id, entry_price, size FROM trades WHERE symbol=? AND status='open' ORDER BY id DESC LIMIT 1", 
                  (symbol.upper(),))
        trade = c.fetchone()
        
        if not trade:
            update.message.reply_text(f"❌ No open trade found for {symbol.upper()}")
            return
        
        trade_id, entry_price, size = trade
        pnl = (float(exit_price) - entry_price) * size
        
        c.execute("UPDATE trades SET status='closed', exit_price=?, pnl=? WHERE id=?", 
                  (float(exit_price), pnl, trade_id))
        conn.commit()
        conn.close()
        
        update.message.reply_text(f"✅ Trade closed:\n{symbol.upper()} @ ${exit_price}\nPnL: ${pnl:.2f}")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

def stats(update: Update, context: CallbackContext):
    conn = sqlite3.connect('/tmp/trades.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*), SUM(pnl) FROM trades WHERE status='closed'")
    total_trades, total_pnl = c.fetchone()
    total_pnl = total_pnl or 0
    
    c.execute("SELECT COUNT(*) FROM trades WHERE status='closed' AND pnl > 0")
    winning_trades = c.fetchone()[0]
    
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    c.execute("SELECT AVG(pnl) FROM trades WHERE status='closed'")
    avg_pnl = c.fetchone()[0] or 0
    
    conn.close()
    
    response = f"📊 Trading Stats:\n\n"
    response += f"Total Trades: {total_trades}\n"
    response += f"Win Rate: {win_rate:.1f}%\n"
    response += f"Total PnL: ${total_pnl:.2f}\n"
    response += f"Average PnL: ${avg_pnl:.2f}"
    
    update.message.reply_text(response)

def main():
    # Get bot token from environment
    token = os.environ.get("BOT_TOKEN")
    if not token:
        logger.error("❌ Please set BOT_TOKEN environment variable")
        return
    
    # Initialize database
    init_db()
    
    # Create bot application with compatible version
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher
    
    # Add command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add", add_trade))
    dispatcher.add_handler(CommandHandler("view", view_trades))
    dispatcher.add_handler(CommandHandler("close", close_trade))
    dispatcher.add_handler(CommandHandler("stats", stats))
    
    # Start the Bot
    updater.start_polling()
    logger.info("🚀 FREE Trading Bot is running on Render...")
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
