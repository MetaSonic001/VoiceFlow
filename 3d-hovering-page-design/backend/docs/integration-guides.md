# VoiceFlow Integration Guides

Post-call webhook payload and step-by-step guides for Make (Integromat), Zapier, and n8n.

---

## Webhook Payload Reference

Every enabled webhook receives a signed POST request after each call completes.

### Headers
```
Content-Type: application/json
X-VoiceFlow-Signature: <hmac-sha256-hex>
X-VoiceFlow-Timestamp: <unix-epoch-seconds>
```

### Signature Verification
```python
import hmac, hashlib

def verify(body: bytes, timestamp: str, secret: str, signature: str) -> bool:
    payload = (timestamp + "." + body.decode()).encode()
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Payload Shape
```json
{
  "event": "call.completed",
  "call_id": "...",
  "agent_id": "...",
  "tenant_id": "...",
  "duration": 87,
  "transcript": "...",
  "summary": "Caller asked about pricing...",
  "sentiment_score": 0.82,
  "sentiment_label": "positive",
  "extracted_variables": {
    "patient_name": "John Smith",
    "appointment_date": "2025-06-12"
  },
  "lead_data": {
    "name": "John Smith",
    "intent": "book appointment",
    "intent_level": "hot",
    "call_outcome": "booked"
  },
  "recording_url": "https://...",
  "timestamp": "2025-06-10T14:32:00Z"
}
```

---

## Make (Integromat)

### 1. Create a Webhook Trigger
1. Open Make → **Create a new scenario**
2. Search for **Webhooks** → choose **Custom webhook**
3. Click **Add** → copy the webhook URL Make provides
4. Paste the URL into VoiceFlow → Agent → Integrations → Webhooks → URL field
5. Enter a shared secret in the **HMAC secret** field
6. Click **Save All**

### 2. Parse the payload
- Add a **JSON → Parse JSON** module after the Webhook trigger
- Map `{{1.body}}` as the input JSON string
- You now have access to all fields: `call_id`, `summary`, `extracted_variables.*`, etc.

### 3. Example: Add a row to Google Sheets
1. Add **Google Sheets → Add a Row** module
2. Map columns:
   - Call ID → `{{1.call_id}}`
   - Caller Name → `{{1.lead_data.name}}`
   - Summary → `{{1.summary}}`
   - Sentiment → `{{1.sentiment_label}}`
   - Any extracted variable → `{{1.extracted_variables.patient_name}}`

### 4. Verify the signature (optional but recommended)
- Add a **Tools → Set variable** module before processing
- Set `valid = {{sha256(1.timestamp + "." + 1.rawBody; "your-secret")}}` 
- Add a **Router** that only continues when `valid == X-VoiceFlow-Signature`

---

## Zapier

### 1. Create a Zap with a Webhook trigger
1. New Zap → Trigger: **Webhooks by Zapier** → **Catch Hook**
2. Copy the webhook URL Zapier gives you
3. Paste it into VoiceFlow → Agent → Integrations → Webhooks
4. Click **Test** in VoiceFlow to send a test payload
5. In Zapier, click **Test trigger** — you should see the payload

### 2. Use the data in actions
Zapier will auto-detect all fields from the test:
- `call_id`, `summary`, `sentiment_label`, `duration`
- `lead_data__name`, `lead_data__intent_level`, `lead_data__call_outcome`
- `extracted_variables__patient_name` (nested fields flattened with `__`)

### 3. Example: Create a HubSpot Contact
1. Action: **HubSpot → Create/Update Contact**
2. Map:
   - Phone → `lead_data__phone`
   - First Name → `lead_data__name` (split with formatter)
   - Lead Status → based on `lead_data__intent_level`
   - Note → `summary`

### 4. Example: Send a Slack notification
1. Action: **Slack → Send Channel Message**
2. Message: `New call from {{lead_data__name}} ({{sentiment_label}}) — {{summary}}`

---

## n8n

### 1. Add a Webhook node
1. New workflow → Add node: **Webhook**
2. Authentication: **None** (we validate via HMAC in code) or **Header Auth**
3. Copy the webhook URL shown in n8n
4. Paste into VoiceFlow → Integrations → Webhooks
5. Enable the webhook and click **Save All**

### 2. Parse and verify the signature
Add a **Code** node after the Webhook:
```javascript
const crypto = require('crypto');
const secret = 'your-webhook-secret';
const body = JSON.stringify($input.first().json.body);
const ts = $input.first().headers['x-voiceflow-timestamp'];
const sig = $input.first().headers['x-voiceflow-signature'];
const expected = crypto
  .createHmac('sha256', secret)
  .update(ts + '.' + body)
  .digest('hex');
if (expected !== sig) throw new Error('Invalid signature');
return $input.all();
```

### 3. Access payload fields
After the Code node, all fields are accessible:
- `{{ $json.body.call_id }}`
- `{{ $json.body.summary }}`
- `{{ $json.body.extracted_variables.patient_name }}`
- `{{ $json.body.lead_data.call_outcome }}`

### 4. Example: Insert into Postgres
1. Add **Postgres** node → **Insert**
2. Table: `call_records`
3. Columns: `call_id`, `summary`, `caller_name`, `sentiment`, `duration`
4. Values: map from `$json.body.*`

### 5. Example: Conditional branch
- Add an **IF** node: `lead_data.call_outcome == "interested"`
- True branch → Create CRM record or send a notification
- False branch → Log to a spreadsheet only

---

## Cal.com Mid-Call Booking

The agent can check availability and book appointments **during the voice call**
using the `check_calcom_availability` and `book_calcom_appointment` tools.

### Setup
1. Go to **Agent → Integrations → Cal.com**
2. Enter your Cal.com **API Key** (from `app.cal.com/settings/developer/api-keys`)
3. Enter the **Event Type ID** (visible in the Cal.com event type URL or via `GET /api/v1/event-types`)
4. Click **Save All**

### How it works
- When a caller asks "Can I book an appointment?", the LLM calls `check_calcom_availability`
- The agent reads back available slots to the caller
- When the caller confirms a time, the LLM calls `book_calcom_appointment` with their name, email, and chosen slot
- The booking confirmation is read back to the caller

---

## Google Calendar Mid-Call Booking

Same flow as Cal.com, using a service account.

### Setup
1. Create a Service Account in Google Cloud Console
2. Grant it **Editor** access on your calendar
3. Download the JSON key file
4. Go to **Agent → Integrations → Google Calendar**
5. Paste the entire JSON key file content into **Service Account JSON**
6. Enter the **Calendar ID** (use `primary` or a specific calendar ID)
7. Click **Save All**

---

## GoHighLevel

After each call, VoiceFlow will:
1. Search for the contact by phone number
2. Create or update the contact with extracted data
3. Add a call note with summary + extracted variables
4. Optionally trigger a GHL workflow

### Setup
1. Go to **Settings → Integrations → API Keys** in GHL
2. Copy your API key
3. Go to **Agent → Integrations → GoHighLevel**
4. Paste the API key
5. Optionally enter a **Workflow ID** to auto-trigger a GHL automation
6. Enable and click **Save All**
