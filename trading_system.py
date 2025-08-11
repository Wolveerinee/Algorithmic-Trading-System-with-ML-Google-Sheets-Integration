"""
Sanitized Algorithmic Trading System (no hard-coded secrets)
Please set the following environment variables instead of storing secrets in code:
  - GOOGLE_CREDENTIALS: path to your service-account.json (DO NOT commit this file)
  - TELEGRAM_TOKEN: your Telegram bot token
  - TELEGRAM_CHAT_ID: target chat id for Telegram alerts
You can store these in a local .env file for development (and never commit .env).
"""

import os
import yfinance as yf
import pandas as pd
import numpy as np
import talib
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import logging
import schedule
import time
import requests
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_system.log'),
        logging.StreamHandler()
    ]
)

class DataFetcher:
    """Handles data ingestion from Yahoo Finance API"""
    def __init__(self, symbols, period='6mo'):
        self.symbols = symbols
        self.period = period
    
    def fetch_data(self):
        data = {}
        periods_to_try = [self.period, '3mo', '1mo', '1y']
        for i, symbol in enumerate(self.symbols):
            if i > 0:
                time.sleep(2)
            symbol_data_fetched = False
            for period in periods_to_try:
                try:
                    logging.info(f"Attempting to fetch data for {symbol} with period {period}")
                    ticker = yf.Ticker(symbol)
                    try:
                        info = ticker.info
                        if not info:
                            logging.warning(f"No info found for {symbol}")
                            continue
                        logging.info(f"Successfully retrieved info for {symbol}")
                    except Exception as info_e:
                        logging.warning(f"Could not retrieve info for {symbol}: {str(info_e)}")
                        if "429" in str(info_e) or "Too Many Requests" in str(info_e):
                            logging.info("Rate limited. Waiting 5 seconds before retry...")
                            time.sleep(5)
                            continue
                    hist = ticker.history(period=period)
                    logging.info(f"Retrieved {len(hist)} rows of data for {symbol} with period {period}")
                    if not hist.empty:
                        data[symbol] = hist
                        symbol_data_fetched = True
                        break
                    else:
                        logging.warning(f"No historical data found for {symbol} with period {period}")
                except Exception as e:
                    logging.error(f"Error fetching data for {symbol} with period {period}: {str(e)}")
                    if "429" in str(e) or "Too Many Requests" in str(e):
                        logging.info("Rate limited. Waiting 5 seconds before retry...")
                        time.sleep(5)
                        continue
                    import traceback
                    logging.error(f"Full traceback for {symbol} with period {period}: {traceback.format_exc()}")
            if not symbol_data_fetched:
                logging.error(f"Failed to fetch data for {symbol} with all attempted periods")
        if not data:
            logging.error("No data fetched for any symbols. This might be due to Yahoo Finance API issues.")
        return data

class TradingStrategy:
    """Implements RSI + Moving Average crossover strategy"""
    def __init__(self, data):
        self.data = data
        self.signals = {}
    
    def calculate_indicators(self, df):
        df['RSI'] = talib.RSI(df['Close'], timeperiod=14)
        df['20_MA'] = talib.SMA(df['Close'], timeperiod=20)
        df['50_MA'] = talib.SMA(df['Close'], timeperiod=50)
        df['MACD'], df['MACD_signal'], _ = talib.MACD(df['Close'])
        return df
    
    def generate_signals(self):
        for symbol, df in self.data.items():
            df = self.calculate_indicators(df)
            df['Signal'] = 0
            df['Position'] = 0
            buy_condition = (df['RSI'] < 30) & (df['20_MA'] > df['50_MA'])
            sell_condition = (df['RSI'] > 70) | (df['20_MA'] < df['50_MA'])
            df.loc[buy_condition, 'Signal'] = 1
            df.loc[sell_condition, 'Signal'] = -1
            df['Position'] = df['Signal'].replace(to_replace=0, value=None).ffill()
            self.signals[symbol] = df
            logging.info(f"Signals generated for {symbol}")
        return self.signals

class MLModel:
    """Machine learning model for predicting price movements"""
    def __init__(self, signals):
        self.signals = signals
        self.models = {}
        self.accuracies = {}
    
    def prepare_data(self, df):
        df['Target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
        df.dropna(inplace=True)
        features = ['RSI', 'MACD', 'Volume', '20_MA', '50_MA']
        X = df[features].copy().fillna(0)
        y = df['Target']
        return X, y
    
    def train_models(self):
        for symbol, df in self.signals.items():
            X, y = self.prepare_data(df.copy())
            if X.empty or y.empty:
                logging.warning(f"Not enough data to train model for {symbol}")
                continue
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            model = DecisionTreeClassifier(max_depth=5)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            self.models[symbol] = model
            self.accuracies[symbol] = accuracy
            logging.info(f"ML model trained for {symbol} with accuracy: {accuracy:.2f}")
        return self.models, self.accuracies

class GoogleSheetsLogger:
    """Handles logging to Google Sheets. Will safely skip if credentials are missing."""
    def __init__(self, credentials_file):
        self.sheet = None
        try:
            if not credentials_file or not os.path.exists(credentials_file):
                logging.warning("Google credentials file not found. Skipping Sheets logging.")
                return
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            client = gspread.authorize(creds)
            self.sheet = client.open("AlgoTradingSystem")
        except Exception as e:
            logging.error(f"Failed to initialize Google Sheets client: {e}")
            self.sheet = None
    
    def log_trades(self, signals, models, accuracies):
        if not self.sheet:
            logging.info("Sheets client not initialized - skipping trade logging.")
            return
        try:
            trade_sheet = self.sheet.worksheet("Trade_Log")
            trade_data = []
            for symbol, df in signals.items():
                last_signal = df.iloc[-1]
                trade_data.append([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    symbol,
                    int(last_signal['Signal']),
                    float(last_signal['Close']),
                    float(last_signal['RSI']) if not np.isnan(last_signal['RSI']) else 0,
                    float(last_signal['20_MA']) if not np.isnan(last_signal['20_MA']) else 0,
                    float(last_signal['50_MA']) if not np.isnan(last_signal['50_MA']) else 0
                ])
            trade_sheet.append_rows(trade_data)
            logging.info("Trade data logged to Google Sheets")
        except Exception as e:
            logging.error(f"Error logging to Google Sheets: {str(e)}")
    
    def log_portfolio(self, signals, models, accuracies):
        if not self.sheet:
            logging.info("Sheets client not initialized - skipping portfolio logging.")
            return
        try:
            portfolio_sheet = self.sheet.worksheet("Portfolio_Summary")
            previous_value = 0
            try:
                all_values = portfolio_sheet.get_all_values()
                if len(all_values) > 1:
                    previous_value = float(all_values[-1][6])
            except:
                pass
            total_symbols = len(signals)
            buy_signals = sum(1 for df in signals.values() if df.iloc[-1]['Signal'] == 1)
            sell_signals = sum(1 for df in signals.values() if df.iloc[-1]['Signal'] == -1)
            hold_signals = total_symbols - buy_signals - sell_signals
            avg_accuracy = sum(accuracies.values()) / len(accuracies) if accuracies else 0
            portfolio_value = sum(df.iloc[-1]['Close'] for df in signals.values())
            daily_change = portfolio_value - previous_value
            daily_change_pct = (daily_change / previous_value) * 100 if previous_value else 0
            summary_data = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                total_symbols,
                buy_signals,
                sell_signals,
                hold_signals,
                f"{avg_accuracy:.2%}",
                f"{portfolio_value:.2f}",
                f"{daily_change:.2f}",
                f"{daily_change_pct:.2f}%"
            ]
            if not portfolio_sheet.get_all_values():
                headers = ["Timestamp", "Total Symbols", "Buy Signals", "Sell Signals", "Hold Signals", "Avg Accuracy", "Portfolio Value", "Daily Change", "Daily Change %"]
                portfolio_sheet.append_row(headers)
            portfolio_sheet.append_row(summary_data)
            logging.info("Portfolio summary logged to Google Sheets")
        except Exception as e:
            logging.error(f"Error logging portfolio summary: {str(e)}")

class TelegramNotifier:
    """Handles Telegram notifications safely (no hard-coded token)."""
    def __init__(self, bot_token=None, chat_id=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = None
        if bot_token:
            self.base_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    def send_alert(self, message):
        if not self.base_url or not self.chat_id:
            logging.warning("Telegram token or chat id not provided - skipping alert.")
            return
        try:
            payload = {'chat_id': self.chat_id, 'text': message, 'parse_mode': 'Markdown'}
            response = requests.post(self.base_url, json=payload, timeout=10)
            if response.status_code == 200:
                logging.info("Telegram alert sent successfully")
            else:
                logging.error(f"Failed to send Telegram alert: {response.text}")
        except Exception as e:
            logging.error(f"Error sending Telegram alert: {str(e)}")

class TradingSystem:
    """Main trading system orchestrator (sanitized)."""
    def __init__(self):
        # Configuration - use environment variables instead of hard-coded secrets
        self.symbols = os.getenv('SYMBOLS', 'RELIANCE.NS,INFY.NS,ICICIBANK.NS').split(',')
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS', 'service-account.json')
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        # Initialize components
        self.data_fetcher = DataFetcher(self.symbols)
        self.strategy = TradingStrategy({})
        self.ml_model = MLModel({})
        self.sheets_logger = GoogleSheetsLogger(self.credentials_file)
        self.telegram_notifier = TelegramNotifier(self.telegram_token, self.telegram_chat_id)
    
    def run_system(self):
        logging.info("Starting trading system execution")
        data = self.data_fetcher.fetch_data()
        if not data:
            logging.error("No data fetched for any symbol. Aborting execution.")
            return
        logging.info(f"Successfully fetched data for symbols: {list(data.keys())}")
        self.strategy.data = data
        signals = self.strategy.generate_signals()
        self.ml_model.signals = signals
        models, accuracies = self.ml_model.train_models()
        self.sheets_logger.log_trades(signals, models, accuracies)
        self.sheets_logger.log_portfolio(signals, models, accuracies)
        alert_msg = "*Trading System Update*\n\n"
        for symbol in signals.keys():
            last_signal = signals[symbol].iloc[-1]
            alert_msg += f\"*{symbol}*: Signal={last_signal['Signal']}, Close={last_signal['Close']:.2f}\n\"
            if symbol in accuracies:
                alert_msg += f\"ML Accuracy: {accuracies[symbol]:.2f}\n\"
        self.telegram_notifier.send_alert(alert_msg)
        logging.info("Trading system execution completed")
    
    def schedule_execution(self):
        schedule.every().day.at("09:30").do(self.run_system)
        logging.info("Trading system scheduled to run daily at 09:30")
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    system = TradingSystem()
    # Immediate execution (only if env vars are configured)
    system.run_system()
    # For scheduled execution (comment above line and uncomment below)
    # system.schedule_execution()
