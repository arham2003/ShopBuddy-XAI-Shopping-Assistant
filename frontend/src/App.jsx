import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { CurrencyProvider } from "./contexts/CurrencyContext";
import { SearchProvider } from "./contexts/SearchContext";
import { HistoryProvider } from "./contexts/HistoryContext";
import MainApp from "./pages/MainApp";
import LandingPage from "./pages/LandingPage";
import LegalPage from "./pages/LegalPage";
import { Toaster } from "./components/ui/sonner";

export default function App() {
  return (
    <CurrencyProvider>
      <SearchProvider>
        <HistoryProvider>
          <Router>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/app" element={<MainApp />} />
              <Route path="/legal" element={<LegalPage />} />
            </Routes>
          </Router>
          <Toaster position="top-right" />
        </HistoryProvider>
      </SearchProvider>
    </CurrencyProvider>
  );
}
