import os
import sqlite3
import requests
import time

# Simple Telegram bot without complex dependencies
class SimpleTradingBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.init_db()
        self.last_update_id = 0
    
    def init_db(self):
        conn = sqlite3.connect('/tmp/trades.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS trades
                     (id INTEGER PRIMARY KEY, symbol TEXT, entry_price REAL, 
                      size REAL, strategy TEXT, status TEXT DEFAULT 'open',
                      exit_price REAL, pnl REAL)''')
        conn.commit()
        conn.close()
    
    def send_message(self, chat_id, text):
        url = f"{self.base_url}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        requests.post(url, json=data)
    
    def get_updates(self):
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 30}
        response = requests.get(url, params=params)
        return response.json().get("result", [])
    
    def handle_message(self, message):
        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip()
        
        if text == "/start":
            self.send_message(chat_id, 
                "📗 FREE Trading Journal Bot\n\n"
                "Commands:\n"
                "/add SYMBOL PRICE SIZE STRATEGY\n"
                "/view - Show trades\n"
                "/close SYMBOL EXIT_PRICE\n"
                "/stats - Performance\n\n"
                "Example: /add BTC 35000 0.1 swing")
        
        elif text.startswith("/add") and len(text.split()) == 5:
            _, symbol, price, size, strategy = text.split()
            try:
                conn = sqlite3.connect('/tmp/trades.db')
                c = conn.cursor()
                c.execute("INSERT INTO trades (symbol, entry_price, size, strategy) VALUES (?, ?, ?, ?)",
                         (symbol.upper(), float(price), float(size), strategy))
                conn.commit()
                conn.close()
                self.send_message(chat_id, f"✅ Added: {symbol} @ ${price}")
            except Exception as e:
                self.send_message(chat_id, f"❌ Error: {e}")
        
        elif text == "/view":
            conn = sqlite3.connect('/tmp/trades.db')
            c = conn.cursor()
            c.execute("SELECT * FROM trades ORDER BY id DESC LIMIT 5")
            trades = c.fetchall()
            conn.close()
            
            if not trades:
                self.send_message(chat_id, "No trades found")
                return
            
            response = "📋 Trades:\n"
            for trade in trades:
                id, symbol, entry, size, strategy, status, exit_price, pnl = trade
                response += f"{symbol}: ${entry} x {size} - {status}\n"
            
            self.send_message(chat_id, response)
        
        elif text.startswith("/close") and len(text.split()) == 3:
            _, symbol, exit_price = text.split()
            try:
                conn = sqlite3.connect('/tmp/trades.db')
                c = conn.cursor()
                c.execute("SELECT id, entry_price, size FROM trades WHERE symbol=? AND status='open' LIMIT 1", 
                         (symbol.upper(),))
                trade = c.fetchone()
                
                if trade:
                    trade_id, entry_price, size = trade
                    pnl = (float(exit_price) - entry_price) * size
                    c.execute("UPDATE trades SET status='closed', exit_price=?, pnl=? WHERE id=?", 
                             (float(exit_price), pnl, trade_id))
                    conn.commit()
                    self.send_message(chat_id, f"✅ Closed: {symbol} @ ${exit_price} | PnL: ${pnl:.2f}")
                else:
                    self.send_message(chat_id, f"❌ No open trade for {symbol}")
                conn.close()
            except Exception as e:
                self.send_message(chat_id, f"❌ Error: {e}")
        
        elif text == "/stats":
            conn = sqlite3.connect('/tmp/trades.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*), SUM(pnl) FROM trades WHERE status='closed'")
            total, pnl = c.fetchone()
            pnl = pnl or 0
            conn.close()
            self.send_message(chat_id, f"📊 Stats:\nTrades: {total}\nTotal PnL: ${pnl:.2f}")
    
    def run(self):
        print("🤖 Simple Trading Bot Running...")
        while True:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.last_update_id = update["update_id"]
                    if "message" in update:
                        self.handle_message(update["message"])
                time.sleep(1)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("❌ Set BOT_TOKEN environment variable")
    else:
        bot = SimpleTradingBot(token)
        bot.run()
