/**
 * App — root component wrapping the app with context providers.
 */
import { CurrencyProvider } from './contexts/CurrencyContext';
import { SearchProvider } from './contexts/SearchContext';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <CurrencyProvider>
      <SearchProvider>
        <div className="min-h-screen bg-slate-50">
          <Navbar />
          <main>
            <Dashboard />
          </main>
        </div>
      </SearchProvider>
    </CurrencyProvider>
  );
}
