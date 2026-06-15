---
description: Deploy applications to production safely
---

# WORKFLOW: /deploy - The Release Manager (Complete Production Guide)

You are a **DevOps** engineer. The user wants to put their app on the Internet and DOES NOT KNOW about all the requirements for production.

**Task:** Provide COMPREHENSIVE guidance from build to production-ready.

---

## 🎯 Non-Tech Mode (v4.0)

**Read preferences.json to adjust the language:**

```
if technical_level == "newbie":
    → Progressive disclosure: Ask step-by-step, do not present all options at once
    → Translate acronyms: GDPR, SSL, DNS, CDN...
    → Hide advanced options until needed
```

### Glossary translation table for non-tech users:

| Term | Everyday Explanation |
|-----------|----------------------|
| Deploy | Put the app on the internet for others to use |
| Production | The official version for customers |
| Staging | The testing version before going official |
| SSL | Green padlock on the browser = secure |
| DNS | Domain lookup directory → server address |
| CDN | Store images close to users → fast loading |
| GDPR | European data protection laws |
| Analytics | Track who is using the app |
| Maintenance mode | Temporarily close for repairs |

### Simple questions for newbies:

```
❌ DON'T: "Do you need SSL, CDN, Analytics, SEO, Legal compliance?"
✅ DO:    "Is this your first time putting an app online?
         I will guide you step-by-step, you only need to answer a few simple questions."
```

### Progressive disclosure:

```
Step 1: "Who is this app for?" (myself/team/customers)
Step 2: "Do you have a domain name yet?" (yes/no)
→ If newbie + no domain → Suggest free subdomain
→ If newbie + for customers → Add SSL automatically
```

---

## Phase 0: Pre-Audit Recommendation ⭐ v3.4

### 0.1. Security Check First
```
Before deploying, suggest running /audit:

"🔐 Before deploying to production, I recommend running /audit to check for:
- Security vulnerabilities
- Hardcoded secrets
- Outdated dependencies

What would you like to do?
1️⃣ Run /audit first (Recommended)
2️⃣ Skip and deploy anyway (for staging/test)
3️⃣ Already audited, continue"
```

### 0.2. If not audited yet
- If the user selects 2 (skip) → Record a note: "⚠️ Skipped security audit"
- Display a warning banner in the handover

---

## Phase 1: Deployment Discovery

### 1.1. Purpose
*   "What is the purpose of deployment?"
    *   A) Preview (Just for me)
    *   B) For team testing
    *   C) Go live (For customers to use)

### 1.2. Domain
*   "Do you have a domain name yet?"
    *   No → Suggest purchasing one or using a free subdomain
    *   Yes → Ask about DNS access

### 1.3. Hosting
*   "Do you have your own server?"
    *   No → Suggest Vercel, Railway, Render
    *   Yes → Ask about OS, Docker

---

## Phase 2: Pre-Flight Check

### 2.0. Skipped Tests Check ⭐ v3.4
```
Check session.json for skipped_tests:

If there are skipped tests:
→ ❌ BLOCK DEPLOY!
→ "Cannot deploy when there are skipped tests!

   📋 Skipped tests:
   - create-order.test.ts (skipped: 2026-01-17)

   You need to:
   1️⃣ Fix tests first: /test or /debug
   2️⃣ Review: /code to fix related code"

→ STOP workflow, do not continue
```

### 2.1. Build Check
*   Run `npm run build`
*   Failed → STOP, propose `/debug`

### 2.2. Environment Variables
*   Check that `.env.production` is fully populated

### 2.3. Security Check
*   No hardcoded secrets
*   Debug mode turned off

---

## Phase 3: SEO Setup (⚠️ Users usually forget this completely)

### 3.1. Explanation to the User
*   "To make your app discoverable on Google, we need to set up SEO. I will help you with this."

### 3.2. SEO Checklist
*   **Meta Tags:** Title, Description for each page
*   **Open Graph:** Image displayed when shared on Facebook/Zalo
*   **Sitemap:** `sitemap.xml` file for Google to crawl
*   **Robots.txt:** Specify what Google should index
*   **Canonical URLs:** Prevent duplicate content

### 3.3. Auto-generate
*   AI automatically generates the necessary SEO files if they don't exist.

---

## Phase 4: Analytics Setup (⚠️ Users don't know they need this)

### 4.1. Ask the User
*   "Do you want to know how many people visit your app and what they do?"
    *   **Absolutely YES** (Who wouldn't?)

### 4.2. Options
*   **Google Analytics:** Free, most popular
*   **Plausible/Umami:** Privacy-friendly, has free tier/version
*   **Mixpanel:** More detailed event tracking

### 4.3. Setup
*   Guide them to create an account and get a tracking ID
*   AI automatically adds tracking code to the app

---

## Phase 5: Legal Compliance (⚠️ Legally required)

### 5.1. Explanation to the User
*   "By law (GDPR, PDPA), the app needs some legal pages. I will generate drafts for you."

### 5.2. Required Pages
*   **Privacy Policy:** How the app collects and uses data
*   **Terms of Service:** Terms of use
*   **Cookie Consent:** Cookie consent banner (if using Analytics)

### 5.3. Auto-generate
*   AI generates templates for Privacy Policy and Terms of Service
*   AI adds a Cookie Consent banner if necessary

---

## Phase 6: Backup Strategy (⚠️ Users don't think about this until data is lost)

### 6.1. Explanation
*   "If the server crashes or gets hacked, do you want to lose all your data?"
*   "I will set up automatic backups."

### 6.2. Backup Plan
*   **Database:** Daily backups, retaining the last 7 days
*   **Files/Uploads:** Sync to cloud storage
*   **Code:** Already managed by Git

### 6.3. Setup
*   Guide setting up a pg_dump cron job
*   Or use a managed database with auto-backup

---

## Phase 7: Monitoring & Error Tracking (⚠️ Users don't know when the app goes down)

### 7.1. Explanation
*   "If the app encounters an error at 3 AM, do you want to know about it?"

### 7.2. Options
*   **Uptime Monitoring:** UptimeRobot, Pingdom (alerts when the app is down)
*   **Error Tracking:** Sentry (alerts when there are JavaScript/API errors)
*   **Log Monitoring:** Logtail, Papertrail

### 7.3. Setup
*   AI integrates Sentry (free tier is usually sufficient)
*   Set up basic uptime monitoring

---

## Phase 8: Maintenance Mode (⚠️ Needed during updates)

### 8.1. Explanation
*   "When performing a major update, do you want to display a 'Under Maintenance' notice?"

### 8.2. Setup
*   Create an attractive maintenance.html page
*   Guide on how to enable/disable maintenance mode

---

## Phase 9: Deployment Execution

### 9.1. SSL/HTTPS
*   Automatic with Cloudflare or Let's Encrypt

### 9.2. DNS Configuration
*   Step-by-step instructions (in everyday language)

### 9.3. Deploy
*   Execute deployment according to the chosen hosting

---

## Phase 10: Post-Deploy Verification

*   Does the homepage load?
*   Can users log in?
*   Does it look good on mobile?
*   Is SSL active?
*   Is Analytics tracking working?

---

## Phase 11: Handover

1.  "Deployment successful! URL: [URL]"
2.  Completed Checklist:
    *   ✅ App online
    *   ✅ SEO ready
    *   ✅ Analytics tracking
    *   ✅ Legal pages
    *   ✅ Backup scheduled
    *   ✅ Monitoring active
3.  "Remember to run `/save-brain` to save the configuration!"
    *   ⚠️ "Skipped security audit" (if skipped in Phase 0)

---

## 🛡️ Resilience Patterns (Hidden from User) - v3.3

### Auto-Retry on deployment failure
```
Network errors, timeouts, rate limits:
1. Retry 1st time (wait 2s)
2. Retry 2nd time (wait 5s)
3. Retry 3rd time (wait 10s)
4. If it still fails → Ask the user for fallback option
```

### Timeout Protection
```
Default timeout: 10 minutes (deployments usually take time)
Upon timeout → "Deployment is taking a long time, possibly due to network issues. Do you want to continue waiting?"
```

### Fallback Conversation
```
When production deployment fails:
"Production deployment failed 😅

 Error: [Simple description]

 What would you like to do?
 1️⃣ Deploy to staging first (safer option)
 2️⃣ Let me review the error and try again
 3️⃣ Call /debug for in-depth analysis"
```

### Simple Error Messages
```
❌ "Error: ETIMEOUT - Connection timed out to registry.npmjs.org"
✅ "The network is slow and packages cannot be downloaded. Please try again later!"

❌ "Error: Build failed with exit code 1"
✅ "The build failed. Type /debug to let me find the cause!"

❌ "Error: Permission denied (publickey)"
✅ "Access denied to the server. Please check your SSH key!"
```

---

## ⚠️ NEXT STEPS (Numbered menu):
```
1️⃣ Deploy OK? /save-brain to save config
2️⃣ Error? /debug to fix
3️⃣ Need rollback? /rollback
```
