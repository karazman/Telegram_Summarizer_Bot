# Azure Portal Setup - Schritt für Schritt

Visuelle Anleitung für das Azure Portal zum Deployen des Telegram Bots.

## 📋 Übersicht

Wir erstellen in dieser Reihenfolge:
1. **Storage Account** - für die Nachrichtenspeicherung
2. **Function App** - für den Bot Code
3. **App Settings** - Konfiguration
4. **Deployment** - Code hochladen

---

## 🔐 Vorbereitung: Azure Portal öffnen

1. Gehe zu https://portal.azure.com
2. Melde dich mit deinem Microsoft Account an
3. Du solltest das Azure Dashboard sehen

---

## 📁 Schritt 1: Resource Group erstellen

**Was:** Container für alle deine Azure Ressourcen

1. **Oben links** → "Create a resource" anklicken
   ![Create Resource](https://i.imgur.com/placeholder.png)

2. Suche nach **"Resource Group"** → anklicken

3. Fülle folgendes aus:
   ```
   Subscription: (dein Account)
   Resource Group Name: telegram-bot-rg
   Region: West Europe (oder deine Region)
   ```

4. Klicke **"Review + create"** → **"Create"**

5. Warten bis grünes Häkchen erscheint ✓

---

## 💾 Schritt 2: Storage Account erstellen

**Was:** Speicher für deine Telegram Nachrichten

### 2.1 Storage Account
1. Portal oben links → **"Create a resource"**

2. Suche nach **"Storage Account"** → anklicken

3. Konfiguriere:
   ```
   Subscription: (dein Account)
   Resource Group: telegram-bot-rg  ← die gerade erstellte
   Storage Account Name: tgbotstore123  (MUSS eindeutig sein!)
   Region: West Europe
   Performance: Standard
   Redundancy: Locally-redundant storage (LRS)
   ```

4. Klicke **"Review"** → **"Create"**

### 2.2 Container erstellen

Sobald Storage erstellt ist:

1. Gehe zu **"Storage Accounts"** (oben in der Suchleiste suchen)

2. Klicke auf dein Storage Account: **tgbotstore123**

3. Links im Menü: **"Containers"** anklicken

4. Klicke **"+ Container"**
   ```
   Name: telegram-messages
   Public Access Level: Private
   ```

5. Klicke **"Create"**

### 2.3 Connection String kopieren

1. Im Storage Account oben → **"Access keys"**

2. Unter **"connection string"** das Icon klicken zum kopieren 📋

3. **Speichern! Du brauchst das später!**

   Sieht so aus:
   ```
   DefaultEndpointsProtocol=https;AccountName=tgbotstore123;AccountKey=...;EndpointSuffix=core.windows.net
   ```

---

## ⚙️ Schritt 3: Function App erstellen

**Was:** Der Server der deinen Bot-Code ausführt

1. Portal oben links → **"Create a resource"**

2. Suche nach **"Function App"** → anklicken

3. Konfiguriere:
   ```
   Subscription: (dein Account)
   Resource Group: telegram-bot-rg
   Function App Name: test-function123
   Runtime Stack: Python
   Version: 3.11
   Region: West Europe
   ```

4. Klicke **"Review + create"** → **"Create"**

5. Warten bis Deployment abgeschlossen ist ✓

---

## 🔧 Schritt 4: App Settings konfigurieren

**Was:** Hier speicherst du deine Bot-Konfiguration (Token, Chat-ID, etc.)

1. Gehe zur soeben erstellten Function App: **"test-function123"**

2. Links im Menü: **"Environment variables"** (oder **"Settings"** → **"Configuration"**)

3. Klicke **"New Application Setting"** und füge folgende nacheinander hinzu:

   **Setting 1: Telegram Bot Token**
   ```
   Name: TELEGRAM_BOT_TOKEN
   Value: 123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh
   (dein Token von @BotFather)
   ```
   Klicke OK

   **Setting 2: Storage Connection**
   ```
   Name: AZURE_STORAGE_CONNECTION_STRING
   Value: (den vorhin kopierten String einfügen)
   DefaultEndpointsProtocol=https;...
   ```
   Klicke OK

   **Setting 3: Target Chat**
   ```
   Name: TARGET_CHAT
   Value: @jkbofewugfh98ewgfvbwoeitfhow
   (deine Gruppen-Username)
   ```
   Klicke OK

   **Setting 4: Target Chat ID**
   ```
   Name: TARGET_CHAT_ID
   Value: 1234567890
   (die numerische ID der Gruppe - findest du mit Bot)
   ```
   Klicke OK

   **Setting 5: Priority Username**
   ```
   Name: PRIORITY_USERNAME
   Value: michael_schredl
   (dein Telegram Username ohne @)
   ```
   Klicke OK

   **Setting 6: Timezone**
   ```
   Name: TIMEZONE
   Value: Europe/Vienna
   (deine Zeitzone)
   ```
   Klicke OK

   **Setting 7: Admin Token**
   ```
   Name: ADMIN_AUTH_TOKEN
   Value: super_secret_token_12345
   (beliebiger sicherer String für manuelle Trigger)
   ```
   Klicke OK

   **Setting 8: Max Messages**
   ```
   Name: MAX_DAILY_MESSAGES
   Value: 500
   (Maximal zu summarisierende Nachrichten)
   ```
   Klicke OK

4. Oben klicke **"Save"** um alle Settings zu speichern

5. Wenn gefragt → **"Continue"** bestätigen

---

## 📤 Schritt 5: Code Deployen

**Was:** Lädt deinen Bot-Code in die Function App hoch

### Option A: Mit GitHub (Empfohlen - Automatisch)

1. In der Function App → **"Deployment Center"** (links im Menü)

2. Wähle:
   ```
   Source: GitHub
   ```

3. Klicke **"Authorize"** und logge dich in GitHub ein

4. Wähle:
   ```
   Organization: karazman (oder dein Account)
   Repository: Telegram_Summarizer_Bot
   Branch: main
   ```

5. Klicke **"Save"**

6. **Warten** - der Code wird automatisch deployed! (~5-10 min)

7. Wenn alles grün ist ✓, ist der Code deployed!

### Option B: Mit VS Code / Azure CLI

Oder führe aus (in PowerShell/Terminal):

```powershell
cd c:\Users\micha\Desktop\FunctionTGbot
func azure functionapp publish telegram-summarizer-bot
```

---

## ✅ Schritt 6: Telegram Webhook registrieren

**Was:** Sagt Telegram, dass dein Bot auf dieser URL läuft

1. Öffne eine neue PowerShell/Terminal

2. Führe aus (ERSETZE `YOUR_BOT_TOKEN`):
   ```powershell
   $token = "YOUR_BOT_TOKEN"
   $url = "https://test-function123-ducjf0dfbtfnagee.westeurope-01.azurewebsites.net/api/telegram"
   
   curl -X POST "https://api.telegram.org/bot$token/setWebhook" `
     -H "Content-Type: application/json" `
     -d "{`"url`": `"$url`"}"
   ```

3. Du solltest sehen:
   ```
   {"ok":true,"result":true,"description":"Webhook was set"}
   ```

---

## 🧪 Schritt 7: Testen

### Test 1: Health Check
```powershell
curl https://test-function123-ducjf0dfbtfnagee.westeurope-01.azurewebsites.net/api/health
```

Sollte antworten:
```json
{"status":"healthy","timestamp":"2024-01-01T12:00:00"}
```

### Test 2: Manuelle Summary
```powershell
curl -X POST https://test-function123-ducjf0dfbtfnagee.westeurope-01.azurewebsites.net/api/trigger-summary `
  -H "Content-Type: application/json" `
  -d '{"auth_token":"super_secret_token_12345"}'
```

### Test 3: Real Test in Telegram
1. Schreibe Nachrichten in deine Telegramgruppe
2. Beobachte die Logs (siehe unten)

---

## 📊 Logs überwachen

### Im Portal:
1. Gehe zur Function App: **test-function123**

2. Links: **"Monitor"** → **"Logs"**

3. Du siehst alle Ausführungen und Fehler

### Von der Kommandozeile:
```powershell
az functionapp log tail --name test-function123 --resource-group telegram-bot-rg
```

---

## ⏰ Automatische Daily Summary

Der Bot macht täglich um **20:00 UTC** eine Zusammenfassung.

**Um Zeit zu ändern:**

1. Gehe zur Function App
2. Links: **"App Files"** (oder klicke auf **"function_app.py"**)
3. Suche nach: `@app.schedule(schedule="0 20 * * *")`
4. Ändere `20` zu deiner gewünschten Stunde (UTC!)
5. Speichere und der Code wird automatisch deployed

---

## 🐛 Häufige Probleme

### Problem: "No messages found"
**Lösung:** Bot muss admin in der Gruppe sein. Rechte überprüfen.

### Problem: "Webhook errors"
**Lösung:** Webhook URL prüfen - muss öffentlich erreichbar sein
```powershell
curl -X POST https://api.telegram.org/bot<TOKEN>/getWebhookInfo
```

### Problem: "Summary generation timeout"
**Lösung:** Azure **Premium Plan** verwenden (Consumption Plan hat 10 min Timeout für BART)

### Problem: "Storage connection string invalid"
**Lösung:** Nochmals kopieren und in Settings aktualisieren

---

## 📱 Telegram Gruppe finden (Chat ID)

Wenn du nicht weißt, was `TARGET_CHAT_ID` ist:

1. Starte den Bot in der Gruppe
2. Schreibe `/start`
3. Der Bot antwortet - kopiere die ID von der Response

Oder mit diesem Tool:
```python
import telebot

bot = telebot.TeleBot("YOUR_BOT_TOKEN")

@bot.message_handler(commands=['id'])
def send_id(message):
    bot.reply_to(message, f"Chat ID: {message.chat.id}")

bot.infinity_polling()
```

---

## 🎉 Fertig!

Dein Bot läuft jetzt auf Azure und:
- ✅ Loggt automatisch Nachrichten aus der Gruppe
- ✅ Erstellt täglich um 20:00 Uhr eine Zusammenfassung
- ✅ Speichert alles persistent im Blob Storage
- ✅ Gewichtet deine Nachrichten höher

---

## 💡 Nächste Schritte

1. **Monitoring einrichten:**
   - Function App → "Monitor" → "Alerts"
   - Alert für Fehler erstellen

2. **Kosten überwachen:**
   - Portal → "Cost Management"
   - Consumption Plan ist kostenlos bis 1 Mio. Aufrufe/Monat

3. **Logs speichern:**
   - Application Insights aktivieren (empfohlen)
   - Function App → "Settings" → "Monitoring"

---

## 📞 Support

- Azure Docs: https://docs.microsoft.com/azure/azure-functions/
- Telegram Bot API: https://core.telegram.org/bots/api
- Probleme? Check Portal Logs!
