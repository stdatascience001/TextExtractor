import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { AnimationProvider } from "./components/animations/AnimationProvider";

// Unregister any legacy service workers (e.g. from other projects on localhost:5173)
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    for (const registration of registrations) {
      registration.unregister().then(() => {
        // Hard reload the page once a legacy service worker is cleared to clean up state
        window.location.reload();
      });
    }
  });
}

createRoot(document.getElementById("root")!).render(
  <AnimationProvider>
    <App />
  </AnimationProvider>
);
