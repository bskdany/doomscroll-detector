import { useState } from "react"

function IndexPopup() {
  const [status, setStatus] = useState<string | null>(null)

  async function downloadCSV() {
    setStatus("Fetching data…")

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })

    if (!tab?.id || !tab.url?.includes("instagram.com")) {
      setStatus("Navigate to Instagram first, then try again.")
      return
    }

    try {
      const response: { data: { ts: number; state: string }[] } =
        await chrome.tabs.sendMessage(tab.id, { type: "GET_DB_DATA" })

      const rows = response?.data ?? []

      const csv = [
        "timestamp_ms,datetime,state",
        ...rows.map((r) => {
          const dt = new Date(r.ts).toISOString()
          return `${r.ts},${dt},${r.state}`
        })
      ].join("\n")

      const blob = new Blob([csv], { type: "text/csv" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "instagram_state_log.csv"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      setStatus(`Downloaded ${rows.length} row${rows.length !== 1 ? "s" : ""}.`)
    } catch {
      setStatus("Error: reload the Instagram tab and try again.")
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        padding: 16,
        gap: 12,
        minWidth: 240,
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
      }}>
      <h2 style={{ margin: 0, fontSize: 15 }}>Instagram State Detector</h2>
      <button
        onClick={downloadCSV}
        style={{
          padding: "8px 14px",
          background: "#0095f6",
          color: "#fff",
          border: "none",
          borderRadius: 6,
          fontWeight: 600,
          fontSize: 13,
          cursor: "pointer"
        }}>
        Download CSV
      </button>
      {status && (
        <p style={{ margin: 0, fontSize: 12, color: "#555" }}>{status}</p>
      )}
    </div>
  )
}

export default IndexPopup
