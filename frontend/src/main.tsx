import React from "react"
import { createRoot } from "react-dom/client"
import { BrowserRouter } from "react-router-dom"
import App from "./App"
import "./index.css"

/*
  main.tsx is the ONE place React attaches itself to the page.
  Read it top to bottom:
    1. find the <div id="root"> from index.html
    2. wrap the app in BrowserRouter so URLs work
    3. render <App /> into it
  You will basically never edit this file again.
*/
createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
