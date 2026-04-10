/**
 * Dashboard — main page that orchestrates the search flow, SSE streaming, and result display.
 */
import { useState, useCallback, useRef, useEffect } from "react";
import { useSearch } from "../contexts/SearchContext";
import { useCurrency } from "../contexts/CurrencyContext";
import { useHistory } from "../contexts/HistoryContext";
import {
  searchProducts,
  resumeSearch,
  sendFollowUp,
  cancelQuery,
} from "../services/api";
import HeroSearch from "../components/HeroSearch";
import DemoSessions from "../components/DemoSessions";
import AgentActivityFeed from "../components/AgentActivityFeed";
import TopPicks from "../components/TopPicks";
import ReviewInsights from "../components/ReviewInsights";
import SecondChanceShelf from "../components/SecondChanceShelf";
import FollowUpChat from "../components/FollowUpChat";

export default function Dashboard({ triggerSearchRef, restoreResultsRef }) {
  const {
    loading,
    error,
    steps,
    interrupt,
    rankedProducts,
    excludedProducts,
    threadId,
    query,
    chatMessages,
    setThreadId,
    setQuery,
    setError,
    setLoading,
    setInterrupt,
    startSearch,
    completeStep,
    activateFirstStep,
    applyResults,
    setChatMessages,
    gateMessage,
    setGateMessage,
  } = useSearch();
  const { displayCurrency, setExchangeRate } = useCurrency();
  const { addToHistory, cacheResults, getCachedResults, deleteEntry } =
    useHistory();
  const abortRef = useRef(null);
  const stopRequestedRef = useRef(false);
  const activeRequestIdRef = useRef(0);
  const queryRef = useRef(""); // stable ref so handleEvent closure always reads latest query
  const [selectedModel, setSelectedModel] = useState("gemini-3-flash-preview");
  const [searchInProgress, setSearchInProgress] = useState(false);

  // Common SSE event handler
  const handleEvent = useCallback(
    (eventType, data, requestId) => {
      if (requestId !== activeRequestIdRef.current) return;

      switch (eventType) {
        case "step_complete":
          completeStep(data.step);
          break;
        case "started":
          setSearchInProgress(true);
          if (data.thread_id) setThreadId(data.thread_id);
          break;
        case "interrupt":
          stopRequestedRef.current = false;
          setThreadId(data.thread_id);
          setInterrupt(data);
          setLoading(false);
          break;
        case "complete":
          stopRequestedRef.current = false;
          setSearchInProgress(false);
          if (data.session_id) setThreadId(data.session_id);
          if (data.exchange_rate) {
            setExchangeRate((prev) => ({ ...prev, ...data.exchange_rate }));
          }
          applyResults(data);
          {
            const entryId = addToHistory({
              query: queryRef.current,
              currency: displayCurrency,
              productCount: (data.ranked_products || []).length,
            });
            cacheResults(entryId, data);
          }
          break;
        case "error":
          stopRequestedRef.current = false;
          setSearchInProgress(false);
          setError(data.error || "An unexpected error occurred");
          setLoading(false);
          break;
        case "blocked":
          if (stopRequestedRef.current) {
            setSearchInProgress(false);
            setGateMessage("Query search cancelled.");
            setError(null);
            setInterrupt(null);
            setLoading(false);
            break;
          }
          setSearchInProgress(false);
          setGateMessage(
            data.message ||
              "I can't help with running commands or installing packages. I can help you find products. Try: 'wireless keyboard under $50'.",
          );
          setError(null);
          setInterrupt(null);
          setLoading(false);
          break;
        default:
          break;
      }
    },
    [
      completeStep,
      setThreadId,
      setInterrupt,
      setLoading,
      setExchangeRate,
      applyResults,
      setError,
      setGateMessage,
      addToHistory,
      cacheResults,
      displayCurrency,
    ],
  );

  const handleError = useCallback(
    (err, requestId) => {
      if (requestId !== activeRequestIdRef.current) return;

      setError(err.message || "Connection error");
      setSearchInProgress(false);
      setLoading(false);
    },
    [setError, setLoading, setSearchInProgress],
  );

  // Start a new search
  const handleSearch = useCallback(
    (q, model) => {
      if (abortRef.current) abortRef.current.abort();
      const requestId = activeRequestIdRef.current + 1;
      activeRequestIdRef.current = requestId;
      stopRequestedRef.current = false;
      const m = model || selectedModel;
      setSelectedModel(m);
      setThreadId(null);
      setQuery(q);
      queryRef.current = q;
      setGateMessage(null);
      setSearchInProgress(true);
      startSearch();
      activateFirstStep();
      abortRef.current = searchProducts(
        q,
        displayCurrency,
        m,
        (eventType, data) => handleEvent(eventType, data, requestId),
        (err) => handleError(err, requestId),
      );
    },
    [
      displayCurrency,
      selectedModel,
      handleEvent,
      handleError,
      startSearch,
      activateFirstStep,
      setQuery,
      setGateMessage,
      setThreadId,
      setSearchInProgress,
    ],
  );

  const handleStopSearch = useCallback(async () => {
    stopRequestedRef.current = true;
    activeRequestIdRef.current += 1;

    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }

    setError(null);
    setInterrupt(null);
    setGateMessage("Query search cancelled.");
    setSearchInProgress(false);
    setLoading(false);

    if (threadId) {
      try {
        await cancelQuery(threadId);
      } catch {
        // The stream is already aborted client-side; backend cancel can fail safely.
      }
    }
  }, [threadId, setLoading, setSearchInProgress]);

  // Expose handleSearch to App via ref so HistorySidebar can re-trigger searches
  useEffect(() => {
    if (triggerSearchRef) triggerSearchRef.current = handleSearch;
  }, [triggerSearchRef, handleSearch]);

  // Restore cached results from a history entry (no backend call)
  const restoreFromCache = useCallback(
    (entry) => {
      activeRequestIdRef.current += 1;
      const cached = getCachedResults(entry.id);
      if (!cached) {
        // Cache miss — remove stale history entry
        deleteEntry(entry.id);
        return;
      }
      // Abort any in-flight search
      if (abortRef.current) abortRef.current.abort();
      // Clear transient UI state
      setError(null);
      setInterrupt(null);
      setGateMessage(null);
      setSearchInProgress(false);
      setChatMessages([]);
      // Set query
      setQuery(entry.query);
      queryRef.current = entry.query;
      // Restore exchange rate if available
      if (cached.data.exchange_rate) {
        setExchangeRate((prev) => ({ ...prev, ...cached.data.exchange_rate }));
      }
      // Apply all result state (sets products, explanations, loading=false, steps=done)
      applyResults(cached.data);
      // Restore threadId so follow-up chat works on cached sessions
      if (cached.data.session_id) setThreadId(cached.data.session_id);
    },
    [
      getCachedResults,
      deleteEntry,
      setError,
      setInterrupt,
      setGateMessage,
      setChatMessages,
      setQuery,
      setExchangeRate,
      applyResults,
      setThreadId,
      setSearchInProgress,
    ],
  );

  useEffect(() => {
    if (restoreResultsRef) restoreResultsRef.current = restoreFromCache;
  }, [restoreResultsRef, restoreFromCache]);

  // Demo click — just runs the query
  const handleDemoClick = useCallback(
    (q) => {
      handleSearch(q);
    },
    [handleSearch],
  );

  // Confirm keywords (resume from interrupt)
  const handleConfirm = useCallback(() => {
    if (!interrupt?.thread_id) return;
    const requestId = activeRequestIdRef.current + 1;
    activeRequestIdRef.current = requestId;
    setInterrupt(null);
    setLoading(true);
    setSearchInProgress(true);
    activateFirstStep();
    // Complete supervisor since we're past it
    completeStep("supervisor");
    abortRef.current = resumeSearch(
      interrupt.thread_id,
      query,
      true,
      displayCurrency,
      selectedModel,
      (eventType, data) => handleEvent(eventType, data, requestId),
      (err) => handleError(err, requestId),
    );
  }, [
    interrupt,
    query,
    displayCurrency,
    selectedModel,
    handleEvent,
    handleError,
    setInterrupt,
    setLoading,
    setSearchInProgress,
    activateFirstStep,
    completeStep,
  ]);

  // Edit keywords — start a fresh search with the edited query
  const handleEditKeywords = useCallback(
    (editedQuery) => {
      setInterrupt(null);
      handleSearch(editedQuery);
    },
    [handleSearch, setInterrupt],
  );

  // Follow-up chat
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const handleFollowUp = useCallback(
    (q) => {
      if (!threadId) return;
      setChatMessages((prev) => [...prev, { role: "user", content: q }]);
      setFollowUpLoading(true);

      sendFollowUp(
        threadId,
        q,
        displayCurrency,
        selectedModel,
        (eventType, data) => {
          if (eventType === "complete") {
            // Extract text response from the follow-up
            const answer =
              data.response ||
              data.fetch_explanation ||
              "Results updated based on your question.";
            setChatMessages((prev) => [
              ...prev,
              { role: "assistant", content: answer },
            ]);
            setFollowUpLoading(false);
          } else if (eventType === "blocked") {
            setChatMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content:
                  data.message ||
                  "I can't help with running commands or installing packages. I can help you find products. Try: 'wireless keyboard under $50'.",
              },
            ]);
            setFollowUpLoading(false);
          } else if (eventType === "error") {
            setChatMessages((prev) => [
              ...prev,
              { role: "assistant", content: `Error: ${data.error}` },
            ]);
            setFollowUpLoading(false);
          }
        },
        () => {
          setChatMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: "Connection error. Please try again.",
            },
          ]);
          setFollowUpLoading(false);
        },
      );
    },
    [threadId, displayCurrency, selectedModel, setChatMessages],
  );

  const hasResults = rankedProducts.length > 0;
  const showActivity = loading && !interrupt;
  const hasActiveQuery = Boolean(query?.trim());

  return (
    <div
      className={`max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 pb-24 sm:pb-32 min-h-screen ${
        hasActiveQuery ? "space-y-4 sm:space-y-6" : "space-y-6 sm:space-y-8"
      }`}
    >
      {/* Hero search — always visible */}
      <div
        className={`[&>div]:transition-all [&>div]:duration-700 [&>div]:ease-out [&>div>h1]:transition-all [&>div>h1]:duration-500 [&>div>h1]:ease-out [&>div>h1]:max-h-24 [&>div>p]:transition-all [&>div>p]:duration-500 [&>div>p]:ease-out [&>div>p]:max-h-20 ${
          hasActiveQuery
            ? "[&>div]:py-2 [&>div]:sm:py-3 [&>div]:space-y-3 [&>div]:sm:space-y-4 [&>div]:-translate-y-6 [&>div]:sm:-translate-y-8 [&>div>h1]:opacity-0 [&>div>h1]:-translate-y-5 [&>div>h1]:max-h-0 [&>div>h1]:overflow-hidden [&>div>h1]:pointer-events-none [&>div>p]:opacity-0 [&>div>p]:-translate-y-5 [&>div>p]:max-h-0 [&>div>p]:overflow-hidden [&>div>p]:pointer-events-none"
            : "[&>div]:translate-y-0"
        }`}
      >
        <HeroSearch
          onSearch={handleSearch}
          onConfirm={handleConfirm}
          onEdit={handleEditKeywords}
          interrupt={interrupt}
          loading={searchInProgress}
          hasActiveQuery={hasActiveQuery}
          onStop={handleStopSearch}
        />
      </div>

      {/* Demo sessions — only before search results */}
      {!hasResults && !loading && !interrupt && (
        <DemoSessions onDemoClick={handleDemoClick} />
      )}

      {/* Agent activity feed */}
      {showActivity && <AgentActivityFeed steps={steps} />}

      {/* Error state */}
      {error && (
        <div className="max-w-lg mx-auto bg-red-50 border border-red-200 rounded-xl p-5 text-center space-y-3">
          <p className="text-red-700 font-medium">Something went wrong</p>
          <p className="text-red-600 text-sm">{error}</p>
          <button
            onClick={() => handleSearch(query)}
            className="px-5 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition-all duration-200"
            aria-label="Retry search"
          >
            Retry Search
          </button>
        </div>
      )}

      {/* Input gate refusal bubble (separate from follow-up chat) */}
      {gateMessage && !loading && (
        <div className="max-w-3xl mx-auto">
          <div className="inline-block max-w-[90%] bg-slate-100 text-slate-800 rounded-2xl px-5 py-3 text-sm leading-relaxed border border-slate-200">
            {gateMessage}
          </div>
        </div>
      )}

      {/* Results */}
      {hasResults && !loading && (
        <>
          <TopPicks products={rankedProducts} />
          <ReviewInsights products={rankedProducts} />
          {excludedProducts.length > 0 && (
            <SecondChanceShelf products={excludedProducts} />
          )}
        </>
      )}

      {/* No results state */}
      {!loading &&
        !error &&
        !hasResults &&
        query &&
        !interrupt &&
        !gateMessage && (
          <div className="text-center py-12">
            <p className="text-slate-500 text-sm">
              No products found. Try a different search term.
            </p>
          </div>
        )}

      {/* Follow-up chat — only when we have results */}
      {hasResults && !loading && (
        <FollowUpChat
          messages={chatMessages}
          onSend={handleFollowUp}
          loading={followUpLoading}
          model={selectedModel}
          onModelChange={setSelectedModel}
        />
      )}
    </div>
  );
}
