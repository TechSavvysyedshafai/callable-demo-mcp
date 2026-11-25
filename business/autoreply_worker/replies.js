// AI Helper Patna auto-replies: decides what to answer a customer, from the approved fact sheet only.
// No AI calls, no costs: keyword rules in English and Hinglish. Anything unclear is handed to Syed.
export const FACTS = {
  intro: 'Namaste! This is the AI Helper Patna assistant replying for Syed.',
  offer: 'We help small Patna businesses use AI on ONE task that wastes time, e.g. a stock sheet, checking supplier bills, customer reminders, or WhatsApp/Instagram posts in Hindi or English. Free for the first 3 businesses: about 2 hours a week for 4 weeks.',
  price: 'The first 3 businesses get it free. After that, approximate prices (Syed confirms): one-time setup Rs 5,000-15,000, monthly support Rs 2,000-5,000.',
  safety: 'We never ask for bank logins, UPI PINs or passwords, and we never promise exact savings; we measure before and after honestly.',
  book: 'To book a free first visit, please reply in one message with: 1) business name and type, 2) area in Patna, 3) the one task that takes most of your time, 4) a good day and time.',
  handoff: 'Thanks! I have passed this to Syed. He will reply within a day. Nothing is booked until he confirms.'
};
const has = (t, words) => words.some(w => t.includes(w));
export function decide(text){
  const t = (text || '').toLowerCase();
  if (!t.trim()) return {reply: null, handoff: false};
  // booking details: several parts in one message (numbers or commas, plus a day/time word)
  const parts = (t.match(/\d\)|\n|,/g) || []).length;
  if (parts >= 3 && has(t, ['am','pm','monday','tuesday','wednesday','thursday','friday','saturday','sunday','kal','aaj','morning','evening','subah','shaam','baje'])) return {reply: FACTS.handoff, handoff: true, lead: true};
  if (has(t, ['price','cost','charge','fee','kitna','kitne','paisa','rate','rupees','rs '])) return {reply: FACTS.price + '\n\n' + FACTS.book, handoff: false};
  if (has(t, ['book','visit','appointment','slot','milna','aaiye','meet','interested','join','start'])) return {reply: FACTS.book, handoff: false};
  if (has(t, ['password','bank','upi','safe','data','privacy','bharosa'])) return {reply: FACTS.safety, handoff: false};
  if (has(t, ['what','kya','kaise','how','service','help','details','info','offer','ai'])) return {reply: FACTS.offer + '\n\n' + FACTS.book, handoff: false};
  if (has(t, ['hi','hello','namaste','hey','salaam','assalam'])) return {reply: FACTS.intro + '\n\n' + FACTS.offer + '\n\n' + FACTS.book, handoff: false};
  return {reply: FACTS.handoff, handoff: true};   // anything else: Syed decides
}
