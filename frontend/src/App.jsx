/**
 * App — root component wrapping the app with context providers.
 */
import { CurrencyProvider } from "./contexts/CurrencyContext";
import { SearchProvider } from "./contexts/SearchContext";
import { HistoryProvider } from "./contexts/HistoryContext";
import Navbar from "./components/Navbar";
import HistorySidebar from "./components/HistorySidebar";
import { ScrollProgress } from "./components/ui/scroll-progress";
import { LightRays } from "./components/ui/light-rays";
import Dashboard from "./pages/Dashboard";
import { useCallback, useRef } from "react";

function AppShell() {
  const triggerSearchRef = useRef(null);
  const restoreResultsRef = useRef(null);

  const handleHistoryClick = useCallback((entry) => {
    if (restoreResultsRef.current) restoreResultsRef.current(entry);
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-50">
      <LightRays
        className="fixed inset-0 z-0"
        color="rgba(120, 140, 255, 0.18)"
        blur={42}
        speed={15}
        count={8}
        length="72vh"
      />
      <HistorySidebar onHistoryClick={handleHistoryClick} />
      <Navbar />
      <ScrollProgress className="top-16 z-40" />
      <main className="relative z-10 pt-16">
        <Dashboard
          triggerSearchRef={triggerSearchRef}
          restoreResultsRef={restoreResultsRef}
        />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <CurrencyProvider>
      <SearchProvider>
        <HistoryProvider>
          <AppShell />
        </HistoryProvider>
      </SearchProvider>
    </CurrencyProvider>
  );
}
