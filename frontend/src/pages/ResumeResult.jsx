import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import api from "../api/client";
import AtsScoreCard from "../components/AtsScoreCard";
import KeywordMatchList from "../components/KeywordMatchList";
import ResumePreview from "../components/ResumePreview";


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


export default function ResumeResult() {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [saveMessage, setSaveMessage] = useState("");
  const [savingType, setSavingType] = useState("");
  const [targetFolder, setTargetFolder] = useState(() => localStorage.getItem("resumeResultTargetFolder") || "");

  useEffect(() => {
    api.get(`/generations/${id}/`).then((response) => setItem(response.data));
  }, [id]);

  if (!item) return <div className="center-screen">Loading result...</div>;

  function updateTargetFolder(value) {
    setTargetFolder(value);
    localStorage.setItem("resumeResultTargetFolder", value);
  }

  async function savePdfToRegistry() {
    setSavingType("pdf");
    setSaveMessage("");
    try {
      const response = await api.post(`/generations/${item.id}/save/`, { target_folder: targetFolder });
      setSaveMessage(`Saved PDF to ${response.data.path || "resume folder"}`);
    } catch (err) {
      setSaveMessage(err.response?.data?.detail || "Could not save PDF.");
    } finally {
      setSavingType("");
    }
  }

  async function saveDocxToRegistry() {
    setSavingType("docx");
    setSaveMessage("");
    try {
      const response = await api.post(`/generations/${item.id}/save-docx/`, { target_folder: targetFolder });
      setSaveMessage(`Saved DOCX to ${response.data.path || "resume folder"}`);
    } catch (err) {
      setSaveMessage(err.response?.data?.detail || "Could not save DOCX.");
    } finally {
      setSavingType("");
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>Generated Resume</h1>
        <p>{item.resume_title} for {item.job_title}{item.company_name ? ` at ${item.company_name}` : ""}</p>
      </header>
      <div className="result-actions">
        <AtsScoreCard score={item.ats_score} />
        <button className="download-button" type="button" onClick={saveDocxToRegistry} disabled={savingType === "docx"}>
          <Download size={18} /> {savingType === "docx" ? "Saving DOCX..." : "Save DOCX"}
        </button>
        <button className="download-button secondary" type="button" onClick={savePdfToRegistry} disabled={savingType === "pdf"}>
          <Download size={18} /> {savingType === "pdf" ? "Saving PDF..." : "Save PDF"}
        </button>
      </div>
      <div className="workspace-form compact-form">
        <label>Save folder path
          <input
            value={targetFolder}
            onChange={(event) => updateTargetFolder(event.target.value)}
            placeholder="Leave blank for the project resume folder, or enter E:/Resumes/Target"
          />
        </label>
      </div>
      {saveMessage && <p className="success">{saveMessage}</p>}
      <KeywordMatchList matched={item.matched_keywords} missing={item.missing_keywords} />
      <ResumePreview text={item.generated_resume_text} />
    </>
  );
}
