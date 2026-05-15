import type { PlasmoCSConfig, PlasmoGetStyle } from "plasmo"
import { useEffect, useRef, useState } from "react"

export const config: PlasmoCSConfig = {
  matches: ["https://www.instagram.com/*"]
}

export const getStyle: PlasmoGetStyle = () => {
  const style = document.createElement("style")
  style.textContent = `
    .box {
      position: fixed;
      top: 16px;
      right: 16px;
      z-index: 2147483647;
      background: #000;
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      padding: 8px 14px;
      border-radius: 6px;
      opacity: 0.92;
      pointer-events: none;
      user-select: none;
      line-height: 1.4;
    }
    .label {
      color: #888;
      font-weight: 400;
      font-size: 10px;
      display: block;
      margin-bottom: 2px;
    }
  `
  return style
}

type InstagramState =
  | "scrolling_reels"
  | "scrolling_home"
  | "stories"
  | "comments"
  | "sending"
  | "unknown"

function hasShareButton(): boolean {
  return Array.from(document.querySelectorAll("span[dir='auto']")).some((el) =>
    ["Send to chat", "Send to group"].includes(el.textContent?.trim() ?? "")
  )
}

function isSendingVisible(): boolean {
  return Array.from(document.querySelectorAll("span[dir='auto']")).some(
    (el) => el.textContent?.trim() === "Share"
  )
}

function isCommentsVisible(): boolean {
  return Array.from(
    document.querySelectorAll(
      "div[role='heading'][aria-level='1'], h1"
    )
  ).some((el) => el.textContent?.trim() === "Comments")
}

function detectState(): InstagramState {
  const path = window.location.pathname

  if (path.startsWith("/stories/")) return "stories"
  if (isCommentsVisible()) return "comments"
  if (isSendingVisible()) return "sending"

  if (path.startsWith("/reels")) return "scrolling_reels"
  if (path.startsWith("/direct/t/") && hasShareButton()) return "scrolling_reels"
  if (path === "/" || path === "/home/") return "scrolling_home"

  return "unknown"
}

const DB_NAME = "ig_state_db"
const STORE_NAME = "state_log"

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME, { keyPath: "ts" })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function logStateChange(state: InstagramState) {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, "readwrite")
  tx.objectStore(STORE_NAME).add({ ts: Date.now(), state })
  db.close()
}

async function getAllRecords(): Promise<{ ts: number; state: InstagramState }[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly")
    const req = tx.objectStore(STORE_NAME).getAll()
    req.onsuccess = () => {
      db.close()
      resolve(req.result)
    }
    req.onerror = () => {
      db.close()
      reject(req.error)
    }
  })
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === "GET_DB_DATA") {
    getAllRecords()
      .then((data) => sendResponse({ data }))
      .catch(() => sendResponse({ data: [] }))
    return true
  }
})

export default function InstagramStateOverlay() {
  const [state, setState] = useState<InstagramState>("unknown")
  const currentState = useRef<InstagramState>("unknown")

  function transition(next: InstagramState) {
    if (next === currentState.current) return
    currentState.current = next
    setState(next)
    logStateChange(next)
  }

  useEffect(() => {
    const handleScroll = () => transition(detectState())

    const handleNav = () => transition(detectState())

    const originalPush = history.pushState.bind(history)
    history.pushState = (...args) => {
      originalPush(...args)
      handleNav()
    }

    const observer = new MutationObserver(() => transition(detectState()))
    observer.observe(document.body, { childList: true, subtree: true })

    window.addEventListener("scroll", handleScroll, { passive: true })
    window.addEventListener("popstate", handleNav)

    return () => {
      observer.disconnect()
      history.pushState = originalPush
      window.removeEventListener("scroll", handleScroll)
      window.removeEventListener("popstate", handleNav)
    }
  }, [])

  return (
    <div className="box">
      <span className="label">instagram state</span>
      {state}
    </div>
  )
}
