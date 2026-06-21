# 📈 ABD Borsa Botu

> Bireysel yatırımcılar için açık kaynaklı teknik analiz ve karar destek aracı.

---

## Sorun

Bireysel yatırımcılar, kurumsal oyuncularla aynı piyasada rekabet etmek zorunda kalır — ancak aynı araçlara sahip değildir.

- Hedge fund'lar ve yatırım bankaları, gelişmiş algoritmalar ve veri akışlarıyla saniyeler içinde karar verir.
- Bireysel yatırımcıların büyük çoğunluğu ise ya duyuma dayalı işlem yapar, ya de göstergeleri nasıl yorumlayacağını bilmez, ya da duygusal kararlar vererek sistematik hatalar tekrarlar.
- Piyasaya yeni giren biri için "strateji geliştirmek" çoğunlukla gerçek para kaybetmek anlamına gelir — çünkü pratik yapacak güvenli bir ortam yoktur.

---

## Çözüm

Bu uygulama, kurumsal düzeyde teknik analiz yöntemlerini bireysel yatırımcı için erişilebilir hale getirir.

Tek bir Streamlit uygulamasında altı farklı modül bir araya gelir:

| Sekme | Ne yapar? |
|-------|-----------|
| 📡 **Sinyal Tarayıcı** | UT Bot algoritmasıyla tüm hisse havuzunu tarar, AL/SAT sinyali üretenleri listeler |
| 🚀 **Momentum & Kırılım** | Minervini ve Qullamaggie kriterlerine göre kırılım adayı güçlü hisseleri filtreler |
| 🌍 **Piyasa Nabzı** | S&P500, VIX, faiz, dolar ve sektör ETF'lerini izleyerek genel piyasa sağlığını gösterir |
| 🔬 **Hisse Analizi** | Seçilen hisse için grafik, backtest ve işlem planı (giriş / stop-loss / hedef) üretir |
| 🐋 **Balina Radar** | RVOL, OBV, MFI ve EMA50 kombinasyonuyla kurumsal birikim sinyallerini tarar |
| 🎮 **Simülasyon** | Gerçek grafiklerde sanal para ile karar egzersizi — XP, rozet ve trade journal |

---

## Ekran Görüntüleri

> _(Katkı sağlamak isteyenler buraya ekran görüntüsü PR'ı açabilir)_

---

## Kurulum

### Gereksinimler

- Python 3.9+
- pip

### Adımlar

```bash
# 1. Repoyu klonla
git clone https://github.com/bugra123uysal/deneme_al_sat_bot.git
cd deneme_al_sat_bot

# 2. Bağımlılıkları kur
pip install -r requirements.txt

# 3. Uygulamayı başlat
python -m streamlit run trading_app.py
```

Tarayıcıda otomatik açılır: `http://localhost:8501`

---

## Kullanılan Teknolojiler

- [Streamlit](https://streamlit.io/) — Web arayüzü
- [yfinance](https://github.com/ranaroussi/yfinance) — Borsa verisi
- [Pandas](https://pandas.pydata.org/) & [NumPy](https://numpy.org/) — Veri işleme
- [Plotly](https://plotly.com/) — İnteraktif grafikler

---

## Teknik Yöntemler

- **UT Bot Alerts** — ATR tabanlı trailing stop ile AL/SAT sinyali (TradingView uyarlaması)
- **Minervini Trend Template** — 7 kriterli trend filtresi
- **Qullamaggie Momentum** — EMA bulutu + ADR% + göreli güç (RS Rating)
- **Wyckoff Hacim Analizi** — OBV, MFI, RVOL ile kurumsal iz tespiti
- **Backtest Motoru** — Sinyal geçmişine göre win rate ve ortalama getiri hesabı

---
## Uygulama içi görseller

<img width="753" height="214" alt="Ekran görüntüsü 2026-06-22 020635" src="https://github.com/user-attachments/assets/136d7ff4-ed2d-41cc-86d6-a5c1e1fa0d6e" />
<img width="1653" height="677" alt="Ekran görüntüsü 2026-06-22 020625" src="https://github.com/user-attachments/assets/f8236747-b786-4b89-baa6-fde1b93571ea" />
<img width="1685" height="599" alt="Ekran görüntüsü 2026-06-22 020608" src="https://github.com/user-attachments/assets/d30395ea-1235-4f7c-af20-028de45c3e9e" />
<img width="1911" height="768" alt="Ekran görüntüsü 2026-06-22 020549" src="https://github.com/user-attachments/assets/5a310e3b-f35c-425d-b81d-2478e05def5c" />
<img width="1917" height="688" alt="Ekran görüntüsü 2026-06-22 020521" src="https://github.com/user-attachments/assets/0a6a121c-63ac-47b6-ad05-b2906805d1d9" />
<img width="1909" height="788" alt="Ekran görüntüsü 2026-06-22 020502" src="https://github.com/user-attachments/assets/af4addeb-dd73-4367-b5e3-d79fe01c93e0" />
<img width="1872" height="737" alt="Ekran görüntüsü 2026-06-22 020658" src="https://github.com/user-attachments/assets/b3cbfb49-a420-4fd2-acd3-87302f19fc47" />
<img width="1914" height="724" alt="Ekran görüntüsü 2026-06-22 020404" src="https://github.com/user-attachments/assets/38d63340-ec97-41a7-b015-cc63285f491f" />
<img width="1895" height="738" alt="Ekran görüntüsü 2026-06-22 020309" src="https://github.com/user-attachments/assets/77d8e416-b2e4-4ea8-9f07-a553e100218a" />
<img width="1880" height="663" alt="Ekran görüntüsü 2026-06-22 020233" src="https://github.com/user-attachments/assets/7461ceee-4a92-4143-aaf1-f36bebed0c32" />
<img width="1919" height="792" alt="Ekran görüntüsü 2026-06-22 020146" src="https://github.com/user-attachments/assets/bf1873f2-57d2-42c4-9079-86b22cb7c85d" />
<img width="1635" height="497" alt="Ekran görüntüsü 2026-06-22 020417" src="https://github.com/user-attachments/assets/49e34b82-43a2-4946-b8e6-acf93e06609d" />




## Önemli Uyarı

> Bu uygulama **yalnızca eğitim amaçlıdır.**
> Gerçek emir göndermez. Yatırım tavsiyesi niteliği taşımaz.
> Tüm veriler Yahoo Finance üzerinden alınmaktadır ve gecikmeli olabilir.

---

## Katkı Sağlamak (Contributing)

Bu proje açık kaynaklıdır ve her türlü katkıya açıktır. Yeni fikrin mi var? Bir hata mı buldun? Yeni bir sekme veya gösterge eklemek mi istiyorsun? Aşağıdaki adımları izle:

### 1. Repoyu Fork'la

Sağ üst köşedeki **Fork** butonuna tıkla — projenin bir kopyası kendi GitHub hesabına oluşur.

### 2. Kendi Branch'ini Oluştur

```bash
git checkout -b ozellik/yeni-gosterge
```

Branch ismi ne olduğunu açıklasın: `ozellik/`, `duzeltme/`, `tasarim/` gibi ön ekler kullan.

### 3. Değişikliklerini Yap ve Commit At

```bash
git add .
git commit -m "feat: MACD göstergesi Hisse Analizi sekmesine eklendi"
```

Commit mesajları İngilizce veya Türkçe olabilir ama ne yaptığını net açıklamalı.

### 4. Fork'una Push Et

```bash
git push origin ozellik/yeni-gosterge
```

### 5. Pull Request Aç

GitHub'da kendi fork'una git → **Compare & pull request** butonuna tıkla → Ne yaptığını kısaca açıkla → Gönder.

---



## Lisans

MIT License — istediğin gibi kullanabilir, değiştirebilir ve dağıtabilirsin.

---

<p align="center">
  Geliştiren: <a href="https://github.com/bugra123uysal">bugra123uysal</a> &nbsp;·&nbsp;
  Katkıda bulunmak için <a href="https://github.com/bugra123uysal/deneme_al_sat_bot/fork">Fork'la

  </a>

</p>
  linkedin: <a href="https://www.linkedin.com/in/mesut-bu%C4%9Fra-uysal-16a1bb288/"> linkedin
