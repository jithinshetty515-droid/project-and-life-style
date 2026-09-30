import { useEffect, useState } from "react";
import Dashboard from "./pages/Dashboard";
import WhatIf from "./pages/WhatIf";
import DataControl from "./pages/DataControl";
import Chat from "./pages/chat";
import { api } from "./services/api";

function App() {
  const [page, setPage] = useState("dashboard");
  const [twin, setTwin] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function loadTwin() {
    try {
      const data = await api.getTwin();
      setTwin(data);
    } catch (err) {
      console.log("No twin loaded yet:", err.message);
    }
  }

  async function loadDemo() {
    setBusy(true);
    setError("");

    try {
      await api.loadDemo();
      await loadTwin();
    } catch (err) {
      console.error("Demo load failed:", err);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function askTwin(message) {
    try {
      setBusy(true);
      const result = await api.chat(message);
      return result;
    } catch (err) {
      console.error("Chat failed:", err);
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadTwin();
  }, []);

  return (
    <div>
      <nav className="p-4 border-b border-white/10 flex gap-4">
        <button onClick={() => setPage("dashboard")}>Dashboard</button>
        <button onClick={() => setPage("whatif")}>What If?</button>
        <button onClick={() => setPage("chat")}>AI Chat</button>
        <button onClick={() => setPage("data")}>Data Control</button>
      </nav>

      {error && (
        <div className="m-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300">
          {error}
        </div>
      )}

      {page === "dashboard" && (
        <Dashboard
          twin={twin}
          onLoadDemo={loadDemo}
          onAsk={askTwin}
          busy={busy}
        />
      )}

      {page === "whatif" && <WhatIf twin={twin} />}
      {page === "chat" && <Chat twin={twin} />}
      {page === "data" && <DataControl twin={twin} />}
    </div>
  );
}

export default App;