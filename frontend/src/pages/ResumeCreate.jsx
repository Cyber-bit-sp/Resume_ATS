import { Save, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";

import api from "../api/client";

export default function ResumeCreate() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ title: "", original_text: "" });
  const [uploadFile, setUploadFile] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    const resumeResponse = await api.get("/resumes/");
    setItems(resumeResponse.data);
  }

  useEffect(() => { load(); }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    const payload = new FormData();
    payload.append("title", form.title);
    payload.append("original_text", form.original_text);
    if (uploadFile) payload.append("upload_file", uploadFile);
    try {
      await api.post("/resumes/", payload, { headers: { "Content-Type": "multipart/form-data" } });
    } catch (err) {
      setError(err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join(" ") || "Resume could not be saved.");
      return;
    }
    setForm({ title: "", original_text: "" });
    setUploadFile(null);
    event.target.reset();
    load();
  }

  async function remove(id) {
    await api.delete(`/resumes/${id}/`);
    load();
  }

  return (
    <>
      <header className="page-header"><h1>Original Resume</h1><p>Paste resume text or upload a resume file. A DOCX template is optional.</p></header>
      <form className="workspace-form" onSubmit={submit}>
        <label>Resume title<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></label>
        <label>Upload resume file
          <span className="file-input">
            <Upload size={18} />
            <input type="file" accept=".doc,.docx,.txt,.pdf" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} />
          </span>
        </label>
        <label>Original resume text<textarea rows="14" value={form.original_text} onChange={(e) => setForm({ ...form, original_text: e.target.value })} required={!uploadFile} /></label>
        {error && <p className="error">{error}</p>}
        <button type="submit"><Save size={18} /> Save Resume</button>
      </form>
      <div className="list">
        {items.map((item) => (
          <article key={item.id} className="row-card">
            <div><h3>{item.title}</h3><p>{item.template_name ? `Template: ${item.template_name}` : "Default generated format"}</p><p>{item.original_text.slice(0, 180)}...</p></div>
            <button className="icon-button" type="button" onClick={() => remove(item.id)} title="Delete resume"><Trash2 size={18} /></button>
          </article>
        ))}
      </div>
    </>
  );
}
