# AURIX Backend — Fixes & Change Log
> **Author:** Divyansh Gaur  
> **For:** Bhavya Gupta's reference and review  
> **Commit:** `b910597` on branch `Bhavya` of `bhavyagupta-5/Major-Project`  
> **Date:** 2026-09-12

---

## Files Changed

| File | Change |
|---|---|
| `aurix-backend/server.js` | Fixed CORS + fixed webhook log message |
| `aurix-backend/services/scannerService.js` | Fixed progress persistence to Supabase |
| `aurix-backend/routes/scans.js` | Added missing `GET /api/scans` list route |

---

## Fix #1 — CORS Blocks VS Code Extension ✅ DONE

**File:** `aurix-backend/server.js` lines 25-38

**Before:**
```js
const allowedOrigins = [
  process.env.CLIENT_URL || 'http://localhost:5173',
  'https://renthour-ai.vercel.app'  // wrong app!
];
app.use(cors({
  origin: function(origin, callback) {
    if (!origin || allowedOrigins.indexOf(origin) !== -1) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true
}));
```

**After:**
```js
const allowedOrigins = [
  process.env.CLIENT_URL || 'http://localhost:5173',
  process.env.WEB_APP_URL || 'https://aurix-web.vercel.app',
  'http://localhost:3000',
  'http://localhost:5173',
];
app.use(cors({
  origin: function(origin, callback) {
    if (!origin) return callback(null, true);                               // VS Code, Postman, server-to-server
    if (origin.startsWith('vscode-webview://')) return callback(null, true); // VS Code extension webview
    if (allowedOrigins.indexOf(origin) !== -1) return callback(null, true);  // whitelist
    if (process.env.NODE_ENV !== 'production') return callback(null, true);  // dev mode
    callback(new Error('Not allowed by CORS'));
  },
  credentials: true
}));
```

> **Note for Bhavya:** Add `WEB_APP_URL=https://your-actual-vercel-url.vercel.app` to your Render environment variables when Bhumika's web app is deployed.

---

## Fix #2 — Progress % Not Saved to Supabase ✅ DONE

**File:** `aurix-backend/services/scannerService.js` lines 37-46

**Before:**
```js
await supabaseAdmin.from('scans').update({
    status: updatedState.status,
    updated_at: updatedState.updated_at
}).eq('id', scanId);
```

**After:**
```js
await supabaseAdmin.from('scans').update({
    status: updatedState.status,
    progress: updatedState.progress,         // ADDED
    current_step: updatedState.current_step, // ADDED
    updated_at: updatedState.updated_at
}).eq('id', scanId);
```

**Why this matters:** Render's free tier restarts the server every ~15 minutes. The old code only kept progress in a `Map()` in RAM — all progress was lost on restart. Now `progress` and `current_step` survive restarts.

---

## Fix #3 — Missing `GET /api/scans` Route ✅ DONE

**File:** `aurix-backend/routes/scans.js` — added before `POST /github`

```js
router.get('/', requireAuth, async (req, res) => {
    const userId = req.user.id;
    const { data, error } = await supabaseAdmin
        .from('scans')
        .select('id, status, progress, current_step, total_findings, neutralized_count, created_at, updated_at, project_id')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(20);
    if (error) return res.status(500).json({ error: 'Failed to fetch scans' });
    return res.status(200).json(data || []);
});
```

---

## Fix #4 — Webhook Log Shows Wrong Count ✅ DONE

**File:** `aurix-backend/server.js` line 249

**Before:**
```js
log: `[WEBHOOK] AI Worker finalized scan. ${findings ? findings.length : 0} vulnerabilities verified.`
// Always showed ALL findings count (e.g. 309), not the neutralized ones (2)
```

**After:**
```js
log: `[WEBHOOK] AI Worker finalized scan. ${summary?.exploitable_count || 0} exploitable found, ${summary?.neutralized_count || 0} neutralized.`
// Now correctly shows: "6 exploitable found, 2 neutralized"
```

---

## Fix #5 — Hardcoded Fake `project_id` in VS Code Extension ✅ DONE

**File:** `vscode-extension/src/api/ApiConnector.ts` line 22

**Before:**
```ts
form.append('project_id', '123e4567-e89b-12d3-a456-426614174000'); // fake UUID — doesn't exist in Supabase
```

**After:**
```ts
form.append('project_id', '<REAL_UUID_FROM_SUPABASE>'); // real project ID from projects table
```

---

## Webhook Payload Contract (AI Engine → Backend)

This is exactly what the AI engine sends to the backend after each scan:

```json
POST /api/internal/webhook/scan-complete
Headers: { "x-webhook-token": "aurix-dev-token" }

{
  "scan_id": "uuid-string",
  "url": "https://github.com/...",
  "timestamp": "2026-09-12T11:00:47Z",
  "summary": {
    "total_findings": 309,
    "exploitable_count": 6,
    "neutralized_count": 2,
    "elapsed_seconds": 364.5,
    "scan_engine": "Project AURIX LangGraph v3"
  },
  "findings": [
    {
      "id": "uuid",
      "rule_id": "avoid-raw-sql",
      "tool": "opengrep",
      "category": "sast",
      "title": "avoid-raw-sql",
      "description": "Unsanitized user input flows into a raw SQL query",
      "severity": "MEDIUM",
      "cvss": 5.5,
      "file": "introduction/views.py",
      "line": 878,
      "evidence": "cursor.execute(...)",
      "fix": "Use parameterized queries",
      "verified": true,
      "wargame_status": "Neutralized",
      "ai_reasoning": "SQL injection via string concatenation confirmed exploitable",
      "poc_script": "import requests\n...",
      "patch_code": "# Fixed version\n..."
    }
  ]
}
```

```json
POST /api/internal/webhook/scan-progress
Headers: { "x-webhook-token": "aurix-dev-token" }

{
  "scan_id": "uuid-string",
  "status": "SCANNING",
  "progress": 45,
  "current_step": "AI Triage chunk 2/5"
}
```

---

## Status Summary

| # | Fix | Status | Commit |
|---|---|---|---|
| 1 | CORS fix for VS Code extension & web app | Done | `b910597` |
| 2 | Progress % + current_step saved to Supabase DB | Done | `b910597` |
| 3 | `GET /api/scans` list route added | Done | `b910597` |
| 4 | Webhook log shows correct exploitable/neutralized counts | Done | `b910597` |
| 5 | Real `project_id` (`119574a9-...`) in VS Code ApiConnector.ts | Done | `pending` |
