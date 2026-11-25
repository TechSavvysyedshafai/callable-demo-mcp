// Cloudflare Worker: Telegram "Chat Automation" (Business mode) bot for AI Helper Patna.
// Telegram calls this Worker (webhook) for each message sent to Syed's personal account by NEW / NON-CONTACT chats
// (Syed chooses that scope in Telegram: Settings > Edit > Chat Automation). The bot answers from the fact sheet
// and forwards leads and anything unclear to Syed. Secrets (never in code): BOT_TOKEN, WEBHOOK_SECRET, OWNER_CHAT_ID.
import { decide } from './replies.js';
const api = (env, method, body) => fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/${method}`, {
  method: 'POST', headers: {'content-type': 'application/json'}, body: JSON.stringify(body) });
export default {
  async fetch(req, env){
    if (req.method !== 'POST') return new Response('ok');
    if (req.headers.get('x-telegram-bot-api-secret-token') !== env.WEBHOOK_SECRET) return new Response('forbidden', {status: 403});
    const u = await req.json().catch(() => ({}));
    const m = u.business_message;
    if (!m || !m.text || !m.from || m.from.is_bot) return new Response('ok');
    if (String(m.from.id) === String(env.OWNER_CHAT_ID)) return new Response('ok');   // Syed's own messages: never answer
    const d = decide(m.text);
    if (d.reply) await api(env, 'sendMessage', { business_connection_id: m.business_connection_id, chat_id: m.chat.id, text: d.reply });
    if (d.handoff){
      const who = [m.from.first_name, m.from.last_name].filter(Boolean).join(' ') + (m.from.username ? ' (@' + m.from.username + ')' : '');
      await api(env, 'sendMessage', { chat_id: env.OWNER_CHAT_ID, text: (d.lead ? 'NEW LEAD' : 'Needs your reply') + ' from ' + who + ':\n\n' + m.text.slice(0, 1500) });
    }
    return new Response('ok');
  }
};
