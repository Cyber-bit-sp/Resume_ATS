import { Download, Eye, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import api from "../api/client";


function safeFileToken(value, fallback) {
  const token = (value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return token || fallback;
}


function defaultDownloadName(item) {
  const date = item?.created_at ? new Date(item.created_at) : new Date();
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  const ss = String(date.getSeconds()).padStart(2, "0");
  const resume = safeFileToken(item?.resume_title, "resume");
  const target = safeFileToken(item?.company_name || item?.job_title, "job");
  return `${y}${m}${d}_${hh}${mm}${ss}_${resume}_${target}.pdf`;
}


function getFilenameFromHeader(contentDisposition) {
  if (!contentDisposition) return "";
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1]);
  const basicMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  return basicMatch?.[1] || "";
}

export default function HistoryPage() {
  const [items, setItems] = useState([]);

  async function load() {
    const response = await api.get("/generations/");
    setItems(response.data);
  }

  useEffect(() => {
    load();
  }, []);

  async function download(item) {
    const response = await api.get(`/generations/${item.id}/download/`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const headerName = getFilenameFromHeader(response.headers?.["content-disposition"]);
    const fileName = headerName || defaultDownloadName(item);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", fileName);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  async function remove(item) {
    await api.delete(`/generations/${item.id}/`);
    setItems((prev) => prev.filter((entry) => entry.id !== item.id));
  }

  return (
    <>
      <header className="page-header"><h1>History</h1><p>Previous generated resumes and downloads.</p></header>
      <div className="list">
        {items.map((item) => (
          <article key={item.id} className="row-card">
            <div>
              <h3>{item.resume_title} → {item.job_title}</h3>
              <p>{item.company_name || "Company not set"} · {item.template_name ? "Source format used" : "Generated format"} · ATS {item.ats_score}</p>
            </div>
            <div className="row-actions">
              <Link className="icon-button" to={`/result/${item.id}`} title="View result"><Eye size={18} /></Link>
              <button className="icon-button" type="button" onClick={() => download(item)} title="Download PDF"><Download size={18} /></button>
              <button className="icon-button" type="button" onClick={() => remove(item)} title="Delete history"><Trash2 size={18} /></button>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
