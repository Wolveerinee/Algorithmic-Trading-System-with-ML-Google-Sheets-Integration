# 📈 Algorithmic Trading System with ML & Google Sheets Integration

## Overview
This project is an **Automated Trading System** built in Python that:

- Fetches stock data from Yahoo Finance.
- Applies technical indicators like RSI, Moving Averages, and MACD.
- Generates buy/sell signals based on a strategy.
- Trains a Machine Learning model to predict price movements.
- Logs trade data and portfolio summaries into Google Sheets for easy monitoring.

## ✨ Features
- **Data Fetching**: Pulls historical stock data from Yahoo Finance (`yfinance`).
- **Technical Indicators**: Uses `TA-Lib` for RSI, SMA, and MACD calculations.
- **Trading Strategy**: RSI + Moving Average crossover rules.
- **Machine Learning**: Decision Tree model for next-day price prediction.
- **Google Sheets Logging**: Trade logs, ML predictions, and portfolio summaries automatically updated.
- **Error Handling**: Handles API rate limits, connection issues, and invalid tickers.
- **Automation**: Can be scheduled to run periodically with the `schedule` library.

## 📂 Project Structure
```
.
├── trading_system.py           # Main trading system logic
├── trading_system.log          # Log file with runtime details
├── test_google_sheets.py       # Script to test Google Sheets connection
├── service-account.json        # Google API credentials (DO NOT share publicly)
├── README.md                   # Project documentation
```

## 🛠 Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/algo-trading-system.git
cd algo-trading-system
```

### 2. Install dependencies
Make sure you have **Python 3.10+** installed.  
Then install the required packages:
```bash
pip install -r requirements.txt
```
If `TA-Lib` fails to install, follow [TA-Lib installation instructions](https://mrjbq7.github.io/ta-lib/install.html) for your OS.

### 3. Set up Google Sheets API
- Go to [Google Cloud Console](https://console.cloud.google.com/).
- Create a **Service Account** and enable the **Google Sheets API**.
- Download the `service-account.json` credentials file and place it in the project root.
- Share your Google Sheet (e.g., `"AlgoTradingSystem"`) with the `client_email` from `service-account.json`.

## ⚙️ Configuration
In `trading_system.py`, set the stock symbols you want to track:
```python
symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]
```
Also ensure your Google Sheet contains these worksheets:
- **Trade_Log**
- **ML_Predictions**
- **Portfolio_Summary**

## ▶️ Usage

### 1. Run the trading system
```bash
python trading_system.py
```

### 2. Test Google Sheets connection
```bash
python test_google_sheets.py
```

## 📊 Example Output in Google Sheets

### **Trade_Log**
| Timestamp           | Symbol  | Signal | Close Price | RSI  | 20_MA | 50_MA |
|--------------------|---------|--------|-------------|------|-------|-------|
| 2025-08-11 10:30   | INFY.NS | 1      | 1450.25     | 28.5 | 1435.2| 1420.1 |

### **ML_Predictions**
| Timestamp           | Symbol  | Prediction | Accuracy |
|--------------------|---------|------------|----------|
| 2025-08-11 10:30   | INFY.NS | 1          | 0.82     |

### **Portfolio_Summary**
| Timestamp           | Total Symbols | Buy Signals | Sell Signals | Hold Signals | Avg Accuracy | Portfolio Value | Daily Change | Daily Change % |
|--------------------|---------------|-------------|--------------|--------------|--------------|-----------------|--------------|----------------|
| 2025-08-11 10:30   | 5             | 2           | 1            | 2            | 81.25%       | 7450.50         | 150.20       | 2.05%          |

## 🔍 Troubleshooting
1. **Yahoo Finance API Issues**
   - Error `429 Too Many Requests`: Wait a few minutes or use a VPN.
   - Check ticker validity on Yahoo Finance.

2. **TA-Lib Installation**
   - Requires native C libraries. Follow OS-specific installation guides.

3. **Google Sheets Logging Fails**
   - Ensure your sheet name matches exactly.
   - Check that the service account email has **Editor** access.
