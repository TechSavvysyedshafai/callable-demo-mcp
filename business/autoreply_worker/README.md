# AI Helper Patna: Telegram Chat Automation bot

Telegram now lets any user connect a bot to their own profile (Settings > Edit > Chat Automation), so the bot
answers people who message you. This Worker is that bot for AI Helper Patna.

What it does
- Answers new / non-contact chats from the approved fact sheet only (`replies.js`): what we do, prices
  (marked approximate), safety, and how to book a free first visit. Works in English and Hinglish keywords.
- When someone sends booking details, it says "Syed will confirm within a day" and forwards the lead to Syed.
- Anything it doesn't understand is forwarded to Syed. It never answers Syed's own messages.
- Costs nothing: no AI calls; Cloudflare Workers free plan.

Set-up (about 15 minutes, done by Syed)
1. Make a SECOND bot in @BotFather (e.g. "AI Helper Patna Desk"). Don't reuse @AIHelperPatna_bot: that one is
   used by the Claude Telegram plugin, and a bot can't be used by both a webhook and the plugin at the same time.
2. In @BotFather: /mybots > the new bot > Bot Settings > Business Mode > Turn on.
3. Deploy the Worker (needs a free Cloudflare account): in this folder run `npx wrangler deploy`, then add secrets:
   `npx wrangler secret put BOT_TOKEN` (the new bot's token), `WEBHOOK_SECRET` (any long random text),
   `OWNER_CHAT_ID` (your Telegram id: 5464458807).
4. Point Telegram at the Worker (replace the parts in <>):
   https://api.telegram.org/bot<TOKEN>/setWebhook?url=<WORKER_URL>&secret_token=<WEBHOOK_SECRET>&allowed_updates=["business_message","business_connection"]
5. In Telegram: Settings > Edit > Chat Automation > choose the new bot > reply to "New chats" and "Non-contacts" only,
   so friends and family never get bot replies.
6. Test from another phone: send "hi", then "kitna lagega", then a booking message.

Tests: `node test/test_replies.mjs`
