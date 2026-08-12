# AH BINARY TRADER BOT

Python + Streamlit dashboard for 1-minute technical-analysis signals.

## Run

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

## Access

Password:

`AH BINARY TRADER BOT`

Developer contacts:

- @TraderMishal11 — https://t.me/TraderMishal11
- @amir_trader02 — https://t.me/amir_trader02

## Telegram

1. Create/configure a Telegram bot and add it to the target group/channel.
2. Put the Bot Token and Group/Channel Chat ID in the sidebar.
3. Turn **Telegram Signal ON**.
4. Choose **AUTO SIGNAL** to scan the configured market universe, or **MANUAL SIGNAL** to select a market and generate a signal.
5. Telegram sends a chart-only PNG with the reference candle and CALL/PUT arrow; it does not send a full dashboard screenshot.

## Important

The signal engine is probabilistic technical analysis. Confidence is not a guarantee of the next candle. WIN/LOSS is only shown after the one-minute expiry is evaluated from the API data.

The chart screenshot feature uses Kaleido, included in requirements.txt.
