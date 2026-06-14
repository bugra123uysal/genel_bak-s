# 📈 ABD Borsası Al/Sat Botu — UT Bot Alerts + Simülasyon

Gerçek ABD hisse senedi verisi üzerinde **UT Bot Alerts** indikatörü ile çalışan,
tek dosyalık bir Streamlit uygulaması. Hisseleri tarar, AL/SAT sinyallerini
listeler, backtest yapar ve bir trading simülasyon oyunu sunar.

> ⚠️ **Bu uygulama yatırım tavsiyesi değildir. Gerçek emir göndermez.
> Yalnızca eğitim ve simülasyon amaçlıdır. Kâr garantisi vermez.**

---

## Özellikler

| Sekme | Açıklama |
|---|---|
| 📡 **Piyasa Tarayıcı** | Tüm hisse havuzunu UT Bot mantığıyla tarar; AL/SAT sinyali verenleri en üstte listeler. Skor, RSI ve günlük değişimi gösterir. |
| 🤖 **Detaylı Analiz** | Seçilen hisse için UT Bot grafiği (ATR trailing stop + AL/SAT okları), backtest (strateji vs Al&Tut), kazanma oranı, max drawdown ve teknik skor/formasyon analizi. |
| 🎮 **Simülasyon** | $100 sanal bakiyeyle eğitim oyunu. Gerçek veya sentetik grafik, XP, seviye, rozet ve hedef sistemi. |

İndikatör: TradingView **UT Bot Alerts** (ATR trailing stop) Pine Script mantığının
birebir Python uyarlaması. `Key Value` (hassasiyet) ve `ATR Period` arayüzden ayarlanabilir.

---

## Kurulum

```bash
git clone https://github.com/<kullanici-adin>/<repo-adi>.git
cd <repo-adi>
pip install -r requirements.txt
streamlit run trading_app.py
```

Tarayıcıda otomatik açılır (genellikle `http://localhost:8501`).

---

## Streamlit Cloud'a Deploy

1. Bu repoyu GitHub'a push edin.
2. [share.streamlit.io](https://share.streamlit.io) → **New app** → repoyu seçin.
3. Main file path: `trading_app.py` → Deploy.

API anahtarı gerektirmez; veri `yfinance` üzerinden ücretsiz çekilir.

---

## Kullanılan Teknolojiler

- [Streamlit](https://streamlit.io) — arayüz
- [yfinance](https://github.com/ranaroussi/yfinance) — hisse verisi
- [Plotly](https://plotly.com/python/) — grafikler
- pandas / numpy — hesaplama

---

## Lisans

Eğitim amaçlı, serbestçe kullanılabilir. UT Bot Alerts indikatörü orijinal
TradingView topluluk script'ine dayanır.
