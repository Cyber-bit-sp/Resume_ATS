import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/client";

export default function GenerateResume() {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const needsResume = !resumes.length;
  const needsJob = !jobs.length;
  const missingSetup = needsResume || needsJob;
  const [form, setForm] = useState({
    resume_id: "",
    job_description_id: "",
    prompt_id: "",
  });

  useEffect(() => {
    async function load() {
      const [resumeResponse, jobResponse, promptResponse] = await Promise.all([
        api.get("/resumes/"),
        api.get("/jobs/"),
        api.get("/prompts/"),
      ]);
      setResumes(resumeResponse.data);
      setJobs(jobResponse.data);
      setPrompts(promptResponse.data);

      const lastCapturedJobId = localStorage.getItem("atsLastCapturedJobId") || "";
      const hasCapturedJob = jobResponse.data.some((item) => String(item.id) === lastCapturedJobId);

      setForm((current) => ({
        ...current,
        job_description_id:
          current.job_description_id
          || (hasCapturedJob ? lastCapturedJobId : ""),
      }));
    }
    load();
  }, []);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = new FormData();
      payload.append("resume_id", String(Number(form.resume_id)));
      payload.append("job_description_id", String(Number(form.job_description_id)));
      if (form.prompt_id) {
        payload.append("prompt_id", String(Number(form.prompt_id)));
      }
      const response = await api.post("/generate-resume/", payload, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      navigate(`/result/${response.data.id}`);
    } catch (err) {
      setError(
        err.response?.data?.detail
          || "Generation failed."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <header className="page-header"><h1>Generate Resume</h1><p>Select the source resume and target job. If no DOCX template exists, a clean default format is generated automatically.</p></header>
      <form className="workspace-form" onSubmit={submit}>
        <div className="two-col">
          <label>Resume<select value={form.resume_id} onChange={(e) => setForm({ ...form, resume_id: e.target.value })} required>
            <option value="">Choose resume</option>
            {resumes.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select></label>
          <label>Job<select value={form.job_description_id} onChange={(e) => setForm({ ...form, job_description_id: e.target.value })} required>
            <option value="">Choose job</option>
            {jobs.map((item) => <option key={item.id} value={item.id}>{item.job_title} {item.company_name ? `· ${item.company_name}` : ""}</option>)}
          </select></label>
        </div>
        <label>Prompt
          <select value={form.prompt_id} onChange={(e) => setForm({ ...form, prompt_id: e.target.value })}>
            <option value="">No saved prompt</option>
            {prompts.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select>
        </label>
        {missingSetup && (
          <p className="error">
            {needsResume && needsJob
              ? "Save an original resume and a job description before generating."
              : needsResume
                ? "Save an original resume before generating."
                : "Save a job description before generating."}
          </p>
        )}
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading || missingSetup}><Sparkles size={18} /> {loading ? "Generating..." : "Generate Resume"}</button>
      </form>
    </>
  );
}
