import { Download, ExternalLink, Eye } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "../api/client";


function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}


export default function WorkHistory() {
  const [items, setItems] = useState([]);
  const [view, setView] = useState("sheet");
  const [targetFolder, setTargetFolder] = useState(() => localStorage.getItem("workHistoryTargetFolder") || "");
  const [saving, setSaving] = useState("");
  const [saveMessage, setSaveMessage] = useState("");

  useEffect(() => {
    api.get("/generations/").then((response) => setItems(response.data));
  }, []);

  function updateTargetFolder(value) {
    setTargetFolder(value);
    localStorage.setItem("workHistoryTargetFolder", value);
  }

  async function saveResume(item, type) {
    setSaving(`${item.id}-${type}`);
    setSaveMessage("");
    try {
      const endpoint = type === "docx" ? "save-docx" : "save";
      const response = await api.post(`/generations/${item.id}/${endpoint}/`, {
        target_folder: targetFolder,
      });
      setSaveMessage(`Saved ${type.toUpperCase()} to ${response.data.path || "the requested folder"}`);
    } catch (err) {
      setSaveMessage(err.response?.data?.detail || `Could not save ${type.toUpperCase()}.`);
    } finally {
      setSaving("");
    }
  }

  function renderSaveButtons(item) {
    return (
      <div className="sheet-actions">
        <button
          className="icon-button"
          type="button"
          onClick={() => saveResume(item, "docx")}
          title="Save DOCX to requested folder"
          disabled={saving === `${item.id}-docx`}
        >
          <Download size={16} />
        </button>
        <button
          className="icon-button secondary"
          type="button"
          onClick={() => saveResume(item, "pdf")}
          title="Save PDF to requested folder"
          disabled={saving === `${item.id}-pdf`}
        >
          PDF
        </button>
      </div>
    );
  }

  const groupedByName = items.reduce((groups, item) => {
    const name = item.resume_title || "Untitled Resume";
    if (!groups[name]) groups[name] = [];
    groups[name].push(item);
    return groups;
  }, {});

  return (
    <>
      <header className="page-header"><h1>Work History</h1><p>Generated resume activity by job, company, and position.</p></header>
      <div className="workspace-form compact-form">
        <label>Requested folder path
          <input
            value={targetFolder}
            onChange={(e) => updateTargetFolder(e.target.value)}
            placeholder="E:/Project/Django/Resume Project/resume/selected"
          />
        </label>
      </div>
      {saveMessage && <p className="success">{saveMessage}</p>}
      <div className="tabs">
        <button type="button" className={view === "sheet" ? "active" : ""} onClick={() => setView("sheet")}>Sheet</button>
        <button type="button" className={view === "name" ? "active" : ""} onClick={() => setView("name")}>By Name</button>
      </div>
      {view === "sheet" ? (
        <div className="sheet-wrap">
          <table className="sheet-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Job URL</th>
                <th>Resume Name</th>
                <th>Company</th>
                <th>Position</th>
                <th>Result</th>
                <th>Save</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{formatDate(item.created_at)}</td>
                  <td>
                    {item.job_url ? (
                      <a className="sheet-link" href={item.job_url} target="_blank" rel="noreferrer">
                        Open <ExternalLink size={14} />
                      </a>
                    ) : "Not set"}
                  </td>
                  <td>{item.resume_title}</td>
                  <td>{item.company_name || "Not set"}</td>
                  <td>{item.job_title}</td>
                  <td><Link className="sheet-link" to={`/result/${item.id}`}>View <Eye size={14} /></Link></td>
                  <td>{renderSaveButtons(item)}</td>
                </tr>
              ))}
              {!items.length && (
                <tr>
                  <td colSpan="7">No work history yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="name-groups">
          {Object.entries(groupedByName).map(([name, entries]) => (
            <section key={name} className="name-group">
              <header>
                <h2>{name}</h2>
                <span>{entries.length} {entries.length === 1 ? "entry" : "entries"}</span>
              </header>
              <div className="sheet-wrap">
                <table className="sheet-table compact">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Job URL</th>
                      <th>Company</th>
                      <th>Position</th>
                      <th>Result</th>
                      <th>Save</th>
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((item) => (
                      <tr key={item.id}>
                        <td>{formatDate(item.created_at)}</td>
                        <td>
                          {item.job_url ? (
                            <a className="sheet-link" href={item.job_url} target="_blank" rel="noreferrer">
                              Open <ExternalLink size={14} />
                            </a>
                          ) : "Not set"}
                        </td>
                        <td>{item.company_name || "Not set"}</td>
                        <td>{item.job_title}</td>
                        <td><Link className="sheet-link" to={`/result/${item.id}`}>View <Eye size={14} /></Link></td>
                        <td>{renderSaveButtons(item)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
          {!items.length && <div className="sheet-wrap empty-state">No work history yet.</div>}
        </div>
      )}
    </>
  );
}
