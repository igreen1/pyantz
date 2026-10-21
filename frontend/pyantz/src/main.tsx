import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import { setUnauthorizedHandler } from "./services/api";
import { store } from "./store/store";
import { applyScheme, preferredScheme } from "./theme";
import { unauthorized } from "./store/slices/authSlice";
import { Provider } from "react-redux";

// set before the first paint, so a dark page does not start out white
applyScheme(preferredScheme());
setUnauthorizedHandler(() => store.dispatch(unauthorized()));

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <App />
    </Provider>
  </StrictMode>,
);
