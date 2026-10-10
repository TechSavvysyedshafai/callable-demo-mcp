import { env } from "cloudflare:workers";
import type { McpServer } from "@modelcontextprotocol/server";
import { z } from "zod";

const KITE_BASE = "https://api.kite.trade";

// Secrets: `wrangler secret put ZERODHA_API_KEY` / `ZERODHA_ACCESS_TOKEN`
// (or put them in .dev.vars for `wrangler dev`). The access token expires daily.
type ZerodhaEnv = { ZERODHA_API_KEY?: string; ZERODHA_ACCESS_TOKEN?: string };

type ToolResult = { content: { type: "text"; text: string }[]; isError?: boolean };

const text = (value: unknown, isError = false): ToolResult => ({
	content: [
		{ type: "text", text: typeof value === "string" ? value : JSON.stringify(value, null, 2) },
	],
	...(isError ? { isError } : {}),
});

async function kite(path: string, params: [string, string][] = []): Promise<ToolResult> {
	const { ZERODHA_API_KEY, ZERODHA_ACCESS_TOKEN } = env as unknown as ZerodhaEnv;
	if (!ZERODHA_API_KEY || !ZERODHA_ACCESS_TOKEN) {
		return text("Missing ZERODHA_API_KEY / ZERODHA_ACCESS_TOKEN secrets.", true);
	}
	const url = new URL(path, KITE_BASE);
	for (const [k, v] of params) url.searchParams.append(k, v);
	const res = await fetch(url, {
		headers: {
			"X-Kite-Version": "3",
			Authorization: `token ${ZERODHA_API_KEY}:${ZERODHA_ACCESS_TOKEN}`,
		},
	});
	const body = (await res.json().catch(() => null)) as {
		status?: string;
		data?: unknown;
		message?: string;
	} | null;
	if (!res.ok || body?.status !== "success") {
		return text(`Kite API error ${res.status}: ${body?.message ?? res.statusText}`, true);
	}
	return text(body.data);
}

const instruments = z
	.array(z.string().regex(/^[A-Z]+:.+$/, "Use EXCHANGE:TRADINGSYMBOL, e.g. NSE:INFY"))
	.min(1)
	.max(500)
	.describe('Instruments as "EXCHANGE:TRADINGSYMBOL", e.g. ["NSE:INFY", "NFO:NIFTY26OCTFUT"]');

export function registerZerodhaTools(server: McpServer) {
	server.registerTool(
		"zerodha_quote",
		{
			description:
				"Full live market quote (LTP, OHLC, volume, OI, circuit limits, 5-level depth). Max 500 instruments.",
			inputSchema: z.object({ instruments }),
		},
		({ instruments }) =>
			kite(
				"/quote",
				instruments.map((i) => ["i", i]),
			),
	);

	server.registerTool(
		"zerodha_ltp",
		{
			description: "Last traded price for up to 1000 instruments.",
			inputSchema: z.object({ instruments }),
		},
		({ instruments }) =>
			kite(
				"/quote/ltp",
				instruments.map((i) => ["i", i]),
			),
	);

	server.registerTool(
		"zerodha_ohlc",
		{
			description: "Live OHLC and last price for up to 1000 instruments.",
			inputSchema: z.object({ instruments }),
		},
		({ instruments }) =>
			kite(
				"/quote/ohlc",
				instruments.map((i) => ["i", i]),
			),
	);

	server.registerTool(
		"zerodha_historical",
		{
			description:
				"Historical OHLCV candles for an instrument token (get tokens from zerodha_instruments). Requires the Kite historical data add-on.",
			inputSchema: z.object({
				instrument_token: z.number().int().positive(),
				interval: z.enum([
					"minute",
					"3minute",
					"5minute",
					"10minute",
					"15minute",
					"30minute",
					"60minute",
					"day",
				]),
				from: z.string().describe("yyyy-mm-dd or yyyy-mm-dd hh:mm:ss (IST)"),
				to: z.string().describe("yyyy-mm-dd or yyyy-mm-dd hh:mm:ss (IST)"),
				oi: z.boolean().optional().describe("Include open interest (derivatives)"),
			}),
		},
		({ instrument_token, interval, from, to, oi }) =>
			kite(`/instruments/historical/${instrument_token}/${interval}`, [
				["from", from],
				["to", to],
				...(oi ? ([["oi", "1"]] as [string, string][]) : []),
			]),
	);

	server.registerTool(
		"zerodha_instruments",
		{
			description:
				"Search the instrument master (tradingsymbol, name, token, lot size, expiry) for an exchange. Returns at most `limit` matches.",
			inputSchema: z.object({
				exchange: z.enum(["NSE", "BSE", "NFO", "BFO", "CDS", "MCX"]),
				query: z
					.string()
					.min(1)
					.describe("Case-insensitive substring of tradingsymbol or name"),
				limit: z.number().int().min(1).max(100).default(20),
			}),
		},
		async ({ exchange, query, limit }) => {
			const { ZERODHA_API_KEY, ZERODHA_ACCESS_TOKEN } = env as unknown as ZerodhaEnv;
			if (!ZERODHA_API_KEY || !ZERODHA_ACCESS_TOKEN) {
				return text("Missing ZERODHA_API_KEY / ZERODHA_ACCESS_TOKEN secrets.", true);
			}
			const res = await fetch(`${KITE_BASE}/instruments/${exchange}`, {
				headers: {
					"X-Kite-Version": "3",
					Authorization: `token ${ZERODHA_API_KEY}:${ZERODHA_ACCESS_TOKEN}`,
				},
			});
			if (!res.ok) return text(`Kite API error ${res.status}: ${res.statusText}`, true);
			// CSV: instrument_token,exchange_token,tradingsymbol,name,last_price,expiry,strike,tick_size,lot_size,instrument_type,segment,exchange
			const [header, ...rows] = (await res.text()).trim().split("\n");
			const cols = header.split(",");
			const q = query.toLowerCase();
			const matches = rows
				.map((r) => r.split(","))
				.filter((f) => `${f[2]} ${f[3]}`.toLowerCase().includes(q))
				.slice(0, limit)
				.map((f) =>
					Object.fromEntries(cols.map((c, i) => [c, f[i]?.replace(/^"|"$/g, "")])),
				);
			return text(matches);
		},
	);

	server.registerTool(
		"zerodha_portfolio",
		{
			description: "Your holdings and current day/net positions.",
			inputSchema: z.object({ kind: z.enum(["holdings", "positions"]) }),
		},
		({ kind }) => kite(kind === "holdings" ? "/portfolio/holdings" : "/portfolio/positions"),
	);
}
