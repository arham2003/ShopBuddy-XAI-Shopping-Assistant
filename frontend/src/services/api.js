import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// ── Standard REST endpoints ──────────────────────────────

export async function switchCurrency(threadId, displayCurrency) {
  const { data } = await client.post("/api/switch-currency", {
    thread_id: threadId,
    display_currency: displayCurrency,
  });
  return data;
}

export async function getExchangeRate() {
  const { data } = await client.get("/api/exchange-rate");
  return data;
}

export async function getDemoSessions() {
  const { data } = await client.get("/api/demo-sessions");
  return data;
}

export async function cancelQuery(threadId) {
  const { data } = await client.post("/api/query/cancel", {
    thread_id: threadId,
  });
  return data;
}

// ── SSE streaming helper ─────────────────────────────────
// /api/query and /api/followup are POST endpoints that return SSE,
// so we use fetch + ReadableStream instead of EventSource (GET-only).

function parseSSEChunk(text) {
  const events = [];
  const blocks = text.split("\n\n");
  for (const block of blocks) {
    if (!block.trim()) continue;
    let eventType = "message";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        eventType = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        data += line.slice(5).trim();
      }
    }
    if (data) {
      try {
        events.push({ event: eventType, data: JSON.parse(data) });
      } catch {
        events.push({ event: eventType, data });
      }
    }
  }
  return events;
}

/**
 * Stream SSE from a POST endpoint. Calls onEvent(eventType, data) for each SSE event.
 * Returns an abort controller so the caller can cancel the stream.
 */
export function streamSSE(url, body, onEvent, onError) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}${url}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!res.ok) {
        const errText = await res.text();
        onError?.(new Error(`HTTP ${res.status}: ${errText}`));
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        // Normalize \r\n to \n (sse_starlette uses \r\n line endings)
        buffer += decoder
          .decode(value, { stream: true })
          .replace(/\r\n/g, "\n");

        // Split on double-newline boundaries — only process complete blocks
        const parts = buffer.split("\n\n");
        buffer = parts.pop(); // keep incomplete tail in buffer

        for (const part of parts) {
          if (!part.trim()) continue;
          const events = parseSSEChunk(part + "\n\n");
          for (const evt of events) {
            onEvent(evt.event, evt.data);
          }
        }
      }

      // Flush remaining buffer
      if (buffer.trim()) {
        const events = parseSSEChunk(buffer + "\n\n");
        for (const evt of events) {
          onEvent(evt.event, evt.data);
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    }
  })();

  return controller;
}

// ── High-level streaming wrappers ────────────────────────

export function searchProducts(
  query,
  displayCurrency,
  model,
  onEvent,
  onError,
) {
  return streamSSE(
    "/api/query",
    { query, display_currency: displayCurrency, model },
    onEvent,
    onError,
  );
}

export function resumeSearch(
  threadId,
  query,
  approved,
  displayCurrency,
  model,
  onEvent,
  onError,
) {
  return streamSSE(
    "/api/query",
    {
      query,
      thread_id: threadId,
      approved,
      display_currency: displayCurrency,
      model,
    },
    onEvent,
    onError,
  );
}

export function sendFollowUp(
  threadId,
  query,
  displayCurrency,
  model,
  onEvent,
  onError,
) {
  return streamSSE(
    "/api/followup",
    { thread_id: threadId, query, display_currency: displayCurrency, model },
    onEvent,
    onError,
  );
}
