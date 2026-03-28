/**
 * SearchContext — stores search results, loading state, agent steps, and thread info.
 */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
} from "react";

const SearchContext = createContext(null);

// Agent pipeline steps in execution order
const INITIAL_STEPS = [
  {
    key: "supervisor",
    label: "Query Interpreter Agent: understanding your shopping intent...",
    icon: "🔍",
    status: "pending",
  },
  {
    key: "scraper",
    label:
      "Marketplace Collector Agent: fetching products from Daraz + Amazon...",
    icon: "🔍",
    status: "pending",
  },
  {
    key: "filter",
    label: "Quality Gate Agent: removing irrelevant or weak candidates...",
    icon: "📊",
    status: "pending",
  },
  {
    key: "analyzer",
    label: "Value Ranker Agent: scoring and ranking top options...",
    icon: "🏆",
    status: "pending",
  },
  {
    key: "reviewer",
    label: "Review Analyst Agent: summarizing customer feedback...",
    icon: "💬",
    status: "pending",
  },
  {
    key: "explainer",
    label: "Explainability Narrator Agent: writing plain-English reasoning...",
    icon: "💡",
    status: "pending",
  },
];

export function SearchProvider({ children }) {
  const [threadId, setThreadId] = useState(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [steps, setSteps] = useState(INITIAL_STEPS);
  const [rankedProducts, setRankedProducts] = useState([]);
  const [excludedProducts, setExcludedProducts] = useState([]);
  const [fetchExplanation, setFetchExplanation] = useState("");
  const [recommendationExplanations, setRecommendationExplanations] = useState(
    {},
  );
  const [funnelStats, setFunnelStats] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [gateMessage, setGateMessage] = useState(null);

  // Interrupt state for keyword confirmation
  const [interrupt, setInterrupt] = useState(null);

  // Follow-up chat messages
  const [chatMessages, setChatMessages] = useState([]);

  const resetSearch = useCallback(() => {
    setLoading(false);
    setError(null);
    setSteps(INITIAL_STEPS);
    setRankedProducts([]);
    setExcludedProducts([]);
    setFetchExplanation("");
    setRecommendationExplanations({});
    setFunnelStats(null);
    setInterrupt(null);
    setChatMessages([]);
    setSessionId(null);
    setGateMessage(null);
  }, []);

  const startSearch = useCallback(() => {
    setLoading(true);
    setError(null);
    setSteps(INITIAL_STEPS);
    setRankedProducts([]);
    setExcludedProducts([]);
    setFetchExplanation("");
    setRecommendationExplanations({});
    setFunnelStats(null);
    setInterrupt(null);
    setChatMessages([]);
    setSessionId(null);
    setGateMessage(null);
  }, []);

  // Mark a step as done and set the next one to loading
  const completeStep = useCallback((stepKey) => {
    setSteps((prev) => {
      const updated = prev.map((s) => ({ ...s }));
      let foundIdx = -1;
      for (let i = 0; i < updated.length; i++) {
        if (updated[i].key === stepKey) {
          updated[i].status = "done";
          foundIdx = i;
          break;
        }
      }
      // Set the next pending step to loading
      if (
        foundIdx >= 0 &&
        foundIdx + 1 < updated.length &&
        updated[foundIdx + 1].status === "pending"
      ) {
        updated[foundIdx + 1].status = "loading";
      }
      return updated;
    });
  }, []);

  // Set the first step to loading when search starts
  const activateFirstStep = useCallback(() => {
    setSteps((prev) => {
      const updated = prev.map((s) => ({ ...s }));
      if (updated[0]) updated[0].status = "loading";
      return updated;
    });
  }, []);

  // Apply complete event data
  const applyResults = useCallback((data) => {
    setRankedProducts(data.ranked_products || []);
    setExcludedProducts(data.excluded_products || []);
    setFetchExplanation(data.fetch_explanation || "");
    setRecommendationExplanations(data.recommendation_explanations || {});
    setFunnelStats(data.funnel_stats || null);
    if (data.session_id) setSessionId(data.session_id);
    setLoading(false);
    // Mark all steps as done
    setSteps((prev) => prev.map((s) => ({ ...s, status: "done" })));
  }, []);

  // Update products after currency switch
  const updateProducts = useCallback((ranked, excluded) => {
    if (ranked) setRankedProducts(ranked);
    if (excluded) setExcludedProducts(excluded);
  }, []);

  const value = useMemo(
    () => ({
      threadId,
      setThreadId,
      query,
      setQuery,
      loading,
      setLoading,
      error,
      setError,
      steps,
      completeStep,
      activateFirstStep,
      rankedProducts,
      excludedProducts,
      fetchExplanation,
      recommendationExplanations,
      funnelStats,
      sessionId,
      interrupt,
      setInterrupt,
      chatMessages,
      setChatMessages,
      gateMessage,
      setGateMessage,
      resetSearch,
      startSearch,
      applyResults,
      updateProducts,
    }),
    [
      threadId,
      query,
      loading,
      error,
      steps,
      rankedProducts,
      excludedProducts,
      fetchExplanation,
      recommendationExplanations,
      funnelStats,
      sessionId,
      interrupt,
      chatMessages,
      gateMessage,
      completeStep,
      activateFirstStep,
      resetSearch,
      startSearch,
      applyResults,
      updateProducts,
    ],
  );

  return (
    <SearchContext.Provider value={value}>{children}</SearchContext.Provider>
  );
}

export function useSearch() {
  const ctx = useContext(SearchContext);
  if (!ctx) throw new Error("useSearch must be used inside SearchProvider");
  return ctx;
}
