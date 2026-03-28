/**
 * Dashboard — main page that orchestrates the search flow, SSE streaming, and result display.
 */
import { useState, useCallback, useRef } from "react";
import { useSearch } from "../contexts/SearchContext";
import { useCurrency } from "../contexts/CurrencyContext";
import { searchProducts, resumeSearch, sendFollowUp } from "../services/api";
import HeroSearch from "../components/HeroSearch";
import DemoSessions from "../components/DemoSessions";
import AgentActivityFeed from "../components/AgentActivityFeed";
import TopPicks from "../components/TopPicks";
import ReviewInsights from "../components/ReviewInsights";
import SecondChanceShelf from "../components/SecondChanceShelf";
import FollowUpChat from "../components/FollowUpChat";

export default function Dashboard() {
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
  const abortRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState("gemini-3-flash-preview");

  // Common SSE event handler
  const handleEvent = useCallback(
    (eventType, data) => {
      switch (eventType) {
        case "step_complete":
          completeStep(data.step);
          break;
        case "interrupt":
          setThreadId(data.thread_id);
          setInterrupt(data);
          setLoading(false);
          break;
        case "complete":
          if (data.session_id) setThreadId(data.session_id);
          // Update exchange rate if provided
          if (data.exchange_rate) {
            setExchangeRate((prev) => ({ ...prev, ...data.exchange_rate }));
          }
          applyResults(data);
          break;
        case "error":
          setError(data.error || "An unexpected error occurred");
          setLoading(false);
          break;
        case "blocked":
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
    ],
  );

  const handleError = useCallback(
    (err) => {
      setError(err.message || "Connection error");
      setLoading(false);
    },
    [setError, setLoading],
  );

  // Start a new search
  const handleSearch = useCallback(
    (q, model) => {
      if (abortRef.current) abortRef.current.abort();
      const m = model || selectedModel;
      setSelectedModel(m);
      setQuery(q);
      setGateMessage(null);
      startSearch();
      activateFirstStep();
      abortRef.current = searchProducts(
        q,
        displayCurrency,
        m,
        handleEvent,
        handleError,
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
    ],
  );

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
    setInterrupt(null);
    setLoading(true);
    activateFirstStep();
    // Complete supervisor since we're past it
    completeStep("supervisor");
    abortRef.current = resumeSearch(
      interrupt.thread_id,
      query,
      true,
      displayCurrency,
      selectedModel,
      handleEvent,
      handleError,
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

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-32 space-y-8">
      {/* Hero search — always visible */}
      <HeroSearch
        onSearch={handleSearch}
        onConfirm={handleConfirm}
        onEdit={handleEditKeywords}
        interrupt={interrupt}
      />

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
        />
      )}
    </div>
  );
}
