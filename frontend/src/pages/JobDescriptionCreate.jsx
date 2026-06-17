import { Save, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import api from "../api/client";

const ROLE_HINTS = [
  "engineer",
  "developer",
  "manager",
  "analyst",
  "architect",
  "designer",
  "scientist",
  "specialist",
  "consultant",
  "administrator",
  "lead",
  "principal",
  "intern",
  "director",
  "officer",
  "head",
];

const COMPANY_HINTS = [
  "inc",
  "llc",
  "ltd",
  "corp",
  "company",
  "technologies",
  "solutions",
  "labs",
  "systems",
  "group",
  "studio",
  "partners",
];

function roleScore(value) {
  const text = (value || "").toLowerCase();
  return ROLE_HINTS.reduce((score, hint) => score + (text.includes(hint) ? 1 : 0), 0);
}

function companyScore(value) {
  const text = (value || "").toLowerCase();
  return COMPANY_HINTS.reduce((score, hint) => score + (text.includes(hint) ? 1 : 0), 0);
}

function slugToCompanyName(slug) {
  if (!slug) return "";
  // Remove trailing digits: "UtilityWarehouse1" → "UtilityWarehouse"
  const withoutTrailingDigits = slug.replace(/\d+$/, "");
  // Split CamelCase: "UtilityWarehouse" → "Utility Warehouse"
  const spaced = withoutTrailingDigits.replace(/([a-z])([A-Z])/g, "$1 $2");
  // Normalise hyphens/underscores and capitalise each word
  return spaced
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ")
    .trim();
}

function extractCompanyFromUrl(jobUrl) {
  try {
    const url = new URL(jobUrl);
    const host = url.hostname.toLowerCase();
    const segments = url.pathname.split("/").filter(Boolean);

    // SmartRecruiters: jobs.smartrecruiters.com/{CompanySlug}/...
    if (host.includes("smartrecruiters.com")) return slugToCompanyName(segments[0] || "");
    // Greenhouse:      boards.greenhouse.io/{company}/jobs/...
    if (host.includes("greenhouse.io")) return slugToCompanyName(segments[0] || "");
    // Lever:           jobs.lever.co/{company}/...
    if (host.includes("lever.co")) return slugToCompanyName(segments[0] || "");
    // Ashby:           jobs.ashbyhq.com/{company}/...
    if (host.includes("ashbyhq.com")) return slugToCompanyName(segments[0] || "");
    // Workday:         {company}.wd1.myworkdayjobs.com/...
    if (host.includes("myworkdayjobs.com")) return slugToCompanyName(host.split(".")[0]);
  } catch {
    // invalid URL — ignore
  }
  return "";
}

function extractCapturedDetails(payload) {
  const pageTitle = (payload?.page_title || "").trim();
  const jobUrl = payload?.job_url || "";

  const titleOnly = pageTitle.split("|")[0].trim();

  // 1. Try URL-based company extraction (most reliable for known job boards)
  const urlCompany = extractCompanyFromUrl(jobUrl);
  if (urlCompany) {
    let jobTitle = titleOnly;
    // Strip the company name from the front of the page title if present
    if (titleOnly.toLowerCase().startsWith(urlCompany.toLowerCase())) {
      jobTitle = titleOnly.slice(urlCompany.length).replace(/^[\s\-\u2013\u2014|:,]+/, "").trim();
    }
    return {
      jobTitle: jobTitle || titleOnly || "Captured Job Description",
      companyName: urlCompany,
    };
  }

  // 2. "Job Title at Company Name" pattern
  const atMatch = titleOnly.match(/^(.+?)\s+at\s+(.+)$/i);
  if (atMatch) {
    const left = atMatch[1].trim();
    const right = atMatch[2].trim();
    if (roleScore(left) >= companyScore(left)) {
      return { jobTitle: left, companyName: right };
    }
    return { jobTitle: right, companyName: left };
  }

  // 3. Separator-based split: "Job Title - Company" / "Job Title | Company"
  const parts = titleOnly
    .split(/\s[-\u2013\u2014|]\s/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length >= 2) {
    const first = parts[0];
    const second = parts[1];
    const firstRole = roleScore(first);
    const secondRole = roleScore(second);
    const firstCompany = companyScore(first);
    const secondCompany = companyScore(second);

    if (secondRole > firstRole || firstCompany > secondCompany) {
      return { jobTitle: second, companyName: first };
    }

    if (firstRole > secondRole || secondCompany > firstCompany) {
      return { jobTitle: first, companyName: second };
    }

    return { jobTitle: first, companyName: second };
  }

  return {
    jobTitle: titleOnly || "Captured Job Description",
    companyName: "",
  };
}

export default function JobDescriptionCreate() {
  const lastCaptureRef = useRef("");
  const [items, setItems] = useState([]);
  const [uploadFile, setUploadFile] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    job_title: "",
    company_name: "",
    location: "",
    work_type: "",
    job_url: "",
    description_text: "",
  });

  async function load() {
    const response = await api.get("/jobs/");
    setItems(response.data);
  }

  useEffect(() => { load(); }, []);

  async function saveCapturedJob(payload) {
    const details = extractCapturedDetails(payload);
    const requestBody = new FormData();
    requestBody.append("job_title", details.jobTitle);
    requestBody.append("company_name", details.companyName);
    requestBody.append("location", "");
    requestBody.append("work_type", "");
    requestBody.append("job_url", payload.job_url || "");
    requestBody.append("description_text", payload.description_text || "");

    const response = await api.post("/jobs/", requestBody, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    localStorage.setItem("atsLastCapturedJobId", String(response.data?.id || ""));
    await load();
  }

  useEffect(() => {
    function handleMessage(event) {
      if (event.data?.source !== "ats-resume-extension" || event.data?.type !== "JOB_DESCRIPTION_CAPTURED") return;

      const payload = event.data.payload || {};
      const captureKey = payload.capturedAt || [payload.job_url, payload.description_text].join("|");
      if (captureKey && lastCaptureRef.current === captureKey) {
        return;
      }

      if (!payload.description_text) {
        return;
      }

      const details = extractCapturedDetails(payload);
      setForm((current) => ({
        ...current,
        job_title: current.job_title || details.jobTitle,
        company_name: current.company_name || details.companyName,
        job_url: payload.job_url || current.job_url,
        description_text: payload.description_text || current.description_text,
      }));
      setUploadFile(null);
      lastCaptureRef.current = captureKey;

      saveCapturedJob(payload).catch((err) => {
        setError(err.response?.data?.detail || "Captured job could not be auto-saved.");
      });

      if (window.parent && window.parent !== window) {
        window.parent.postMessage(
          {
            source: "ats-resume-app",
            type: "JOB_DESCRIPTION_CAPTURED_ACK",
            payload: {
              capturedAt: payload.capturedAt || "",
            },
          },
          "*"
        );
      }
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    const payload = new FormData();
    Object.entries(form).forEach(([key, value]) => payload.append(key, value));
    if (uploadFile) payload.append("upload_file", uploadFile);
    try {
      const response = await api.post("/jobs/", payload, { headers: { "Content-Type": "multipart/form-data" } });
      localStorage.setItem("atsLastCapturedJobId", String(response.data?.id || ""));
    } catch (err) {
      setError(err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join(" ") || "Job could not be saved.");
      return;
    }
    setForm({ job_title: "", company_name: "", location: "", work_type: "", job_url: "", description_text: "" });
    setUploadFile(null);
    event.target.reset();
    load();
  }

  async function remove(id) {
    await api.delete(`/jobs/${id}/`);
    load();
  }

  return (
    <>
      <header className="page-header"><h1>Job Description</h1><p>Save target roles for keyword matching and generation.</p></header>
      <form className="workspace-form" onSubmit={submit}>
        <div className="two-col">
          <label>Job title<input value={form.job_title} onChange={(e) => setForm({ ...form, job_title: e.target.value })} required /></label>
          <label>Company<input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} /></label>
          <label>Location<input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} /></label>
          <label>Work type<input value={form.work_type} onChange={(e) => setForm({ ...form, work_type: e.target.value })} /></label>
        </div>
        <label>Job URL<input value={form.job_url} onChange={(e) => setForm({ ...form, job_url: e.target.value })} /></label>
        <label>Upload job file
          <span className="file-input">
            <Upload size={18} />
            <input type="file" accept=".doc,.txt,.pdf" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} />
          </span>
        </label>
        <label>Description<textarea rows="12" value={form.description_text} onChange={(e) => setForm({ ...form, description_text: e.target.value })} required={!uploadFile} /></label>
        {error && <p className="error">{error}</p>}
        <button type="submit"><Save size={18} /> Save Job</button>
      </form>
      <div className="list">
        {items.map((item) => (
          <article key={item.id} className="row-card">
            <div><h3>{item.job_title}</h3><p>{item.company_name || "Company not set"} · {item.location || "Location not set"}</p></div>
            <button className="icon-button" type="button" onClick={() => remove(item.id)} title="Delete job"><Trash2 size={18} /></button>
          </article>
        ))}
      </div>
    </>
  );
}
