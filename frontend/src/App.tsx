import { useState, useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CompareProvider } from "./context/CompareContext";
import SearchPage from "./pages/SearchPage";
import ComparePage from "./pages/ComparePage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onHashChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);
  return hash;
}

export default function App() {
  const route = useHashRoute();

  return (
    <QueryClientProvider client={queryClient}>
      <CompareProvider>
        {route === "#/compare" ? <ComparePage /> : <SearchPage />}
      </CompareProvider>
    </QueryClientProvider>
  );
}
