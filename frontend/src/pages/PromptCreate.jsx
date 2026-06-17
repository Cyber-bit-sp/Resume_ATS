import { Save, Trash2, Upload } from "lucide-react";
import { useEffect, useState } from "react";

import api from "../api/client";

export default function PromptCreate() {
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ title: "", prompt_text: "" });
  const [uploadFile, setUploadFile] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    const response = await api.get("/prompts/");
    setItems(response.data);
  }

  useEffect(() => { load(); }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    const payload = new FormData();
    payload.append("title", form.title);
    payload.append("prompt_text", form.prompt_text);
    if (uploadFile) payload.append("upload_file", uploadFile);
    try {
      await api.post("/prompts/", payload, { headers: { "Content-Type": "multipart/form-data" } });
    } catch (err) {
      setError(err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join(" ") || "Prompt could not be saved.");
      return;
    }
    setForm({ title: "", prompt_text: "" });
    setUploadFile(null);
    event.target.reset();
    load();
  }

  async function remove(id) {
    await api.delete(`/prompts/${id}/`);
    load();
  }

  return (
    <>
      <header className="page-header"><h1>Prompt</h1><p>Import or write reusable generation instructions.</p></header>
      <form className="workspace-form" onSubmit={submit}>
        <label>Prompt title<input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required /></label>
        <label>Upload prompt file
          <span className="file-input">
            <Upload size={18} />
            <input type="file" accept=".doc,.docx,.txt,.pdf" onChange={(e) => setUploadFile(e.target.files?.[0] || null)} />
          </span>
        </label>
        <label>Prompt text<textarea rows="10" value={form.prompt_text} onChange={(e) => setForm({ ...form, prompt_text: e.target.value })} required={!uploadFile} /></label>
        {error && <p className="error">{error}</p>}
        <button type="submit"><Save size={18} /> Save Prompt</button>
      </form>
      <div className="list">
        {items.map((item) => (
          <article key={item.id} className="row-card">
            <div><h3>{item.title}</h3><p>{item.prompt_text.slice(0, 180)}...</p></div>
            <button className="icon-button" type="button" onClick={() => remove(item.id)} title="Delete prompt"><Trash2 size={18} /></button>
          </article>
        ))}
      </div>
    </>
  );
}
