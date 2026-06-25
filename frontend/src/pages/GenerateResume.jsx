import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/client";

export default function GenerateResume() {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const needsResume = !resumes.length;
  const needsPrompt = !prompts.length;
  const missingSetup = needsResume || needsPrompt;
  const [form, setForm] = useState({
    resume_id: "",
    prompt_id: "",
  });

  useEffect(() => {
    async function load() {
      const [resumeResponse, promptResponse] = await Promise.all([
        api.get("/resumes/"),
        api.get("/prompts/"),
      ]);
      setResumes(resumeResponse.data);
      setPrompts(promptResponse.data);
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
      <header className="page-header"><h1>Generate Resume</h1><p>Select the source resume and prompt. The job description is generated automatically from your chosen inputs when you click Generate.</p></header>
      <form className="workspace-form" onSubmit={submit}>
        <div className="two-col">
          <label>Resume<select value={form.resume_id} onChange={(e) => setForm({ ...form, resume_id: e.target.value })} required>
            <option value="">Choose resume</option>
            {resumes.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
          </select></label>
          <label>Prompt
            <select value={form.prompt_id} onChange={(e) => setForm({ ...form, prompt_id: e.target.value })}>
              <option value="">No saved prompt</option>
              {prompts.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
            </select>
          </label>
        </div>
        {missingSetup && (
          <p className="error">
            {needsResume && needsPrompt
              ? "Save an original resume and a prompt before generating."
              : needsResume
                ? "Save an original resume before generating."
                : "Save a prompt before generating."}
          </p>
        )}
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={loading || missingSetup}><Sparkles size={18} /> {loading ? "Generating..." : "Generate Resume"}</button>
      </form>
    </>
  );
}
