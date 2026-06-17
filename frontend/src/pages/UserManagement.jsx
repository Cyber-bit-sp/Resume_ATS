import { useEffect, useState } from "react";
import { RefreshCw, Save, Trash2, Upload } from "lucide-react";

import api from "../api/client";

const emptyForm = {
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  password: "",
  is_staff: false,
  is_active: true,
};

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [resumes, setResumes] = useState([]);
  const [resumeShares, setResumeShares] = useState({});
  const [form, setForm] = useState(emptyForm);
  const [resumeForm, setResumeForm] = useState({ title: "", original_text: "", shared_with: [] });
  const [resumeFile, setResumeFile] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadUsers() {
    setLoading(true);
    try {
      const response = await api.get("/auth/users/");
      setUsers(response.data);
    } catch {
      setError("Could not load users.");
    } finally {
      setLoading(false);
    }
  }

  async function loadResumes() {
    const response = await api.get("/resumes/");
    setResumes(response.data);
    setResumeShares(
      Object.fromEntries(
        response.data.map((resume) => [resume.id, (resume.shared_with || []).map(Number)])
      )
    );
  }

  useEffect(() => {
    loadUsers();
    loadResumes();
  }, []);

  function updateForm(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function editUser(user) {
    setEditingId(user.id);
    setForm({
      username: user.username || "",
      email: user.email || "",
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      password: "",
      is_staff: Boolean(user.is_staff),
      is_active: Boolean(user.is_active),
    });
    setMessage("");
    setError("");
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function submit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    const payload = { ...form };
    if (editingId && !payload.password) {
      delete payload.password;
    }
    try {
      if (editingId) {
        await api.patch(`/auth/users/${editingId}/`, payload);
        setMessage("User updated.");
      } else {
        await api.post("/auth/users/", payload);
        setMessage("User created.");
      }
      resetForm();
      await loadUsers();
    } catch (err) {
      const details = err.response?.data;
      setError(typeof details === "string" ? details : "Could not save user. Check the fields and password strength.");
    }
  }

  async function deleteUser(user) {
    setMessage("");
    setError("");
    try {
      await api.delete(`/auth/users/${user.id}/`);
      setMessage(`${user.username} deleted.`);
      await loadUsers();
    } catch {
      setError("Could not delete this user.");
    }
  }

  function toggleResumeUser(userId) {
    setResumeForm((current) => {
      const exists = current.shared_with.includes(userId);
      return {
        ...current,
        shared_with: exists
          ? current.shared_with.filter((id) => id !== userId)
          : [...current.shared_with, userId],
      };
    });
  }

  async function submitSharedResume(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    const payload = new FormData();
    payload.append("title", resumeForm.title);
    payload.append("original_text", resumeForm.original_text);
    if (resumeFile) {
      payload.append("upload_file", resumeFile);
    }
    resumeForm.shared_with.forEach((userId) => payload.append("shared_with", String(userId)));

    try {
      await api.post("/resumes/", payload, { headers: { "Content-Type": "multipart/form-data" } });
      setMessage("Shared resume uploaded.");
      setResumeForm({ title: "", original_text: "", shared_with: [] });
      setResumeFile(null);
      event.target.reset();
      await loadResumes();
    } catch (err) {
      setError(err.response?.data?.detail || Object.values(err.response?.data || {}).flat().join(" ") || "Could not upload shared resume.");
    }
  }

  function toggleExistingResumeUser(resumeId, userId) {
    setResumeShares((current) => {
      const selected = current[resumeId] || [];
      const exists = selected.includes(userId);
      return {
        ...current,
        [resumeId]: exists ? selected.filter((id) => id !== userId) : [...selected, userId],
      };
    });
  }

  async function saveResumeShares(resume) {
    setMessage("");
    setError("");
    const payload = new FormData();
    payload.append("title", resume.title);
    payload.append("original_text", resume.original_text);
    (resumeShares[resume.id] || []).forEach((userId) => payload.append("shared_with", String(userId)));
    try {
      await api.patch(`/resumes/${resume.id}/`, payload, { headers: { "Content-Type": "multipart/form-data" } });
      setMessage(`Sharing updated for ${resume.title}.`);
      await loadResumes();
    } catch {
      setError("Could not update resume sharing.");
    }
  }

  return (
    <>
      <header className="page-header">
        <h1>User Management</h1>
        <p>Create accounts and control administrator access.</p>
      </header>

      <form className="workspace-form" onSubmit={submit}>
        <div className="two-col">
          <label>Username<input value={form.username} onChange={(e) => updateForm("username", e.target.value)} required /></label>
          <label>Email<input type="email" value={form.email} onChange={(e) => updateForm("email", e.target.value)} /></label>
          <label>First name<input value={form.first_name} onChange={(e) => updateForm("first_name", e.target.value)} /></label>
          <label>Last name<input value={form.last_name} onChange={(e) => updateForm("last_name", e.target.value)} /></label>
        </div>
        <label>{editingId ? "New password (optional)" : "Password"}<input type="password" value={form.password} onChange={(e) => updateForm("password", e.target.value)} required={!editingId} /></label>
        <div className="inline-options">
          <label className="checkbox"><input type="checkbox" checked={form.is_staff} onChange={(e) => updateForm("is_staff", e.target.checked)} /> Administrator</label>
          <label className="checkbox"><input type="checkbox" checked={form.is_active} onChange={(e) => updateForm("is_active", e.target.checked)} /> Active</label>
        </div>
        {error && <p className="error">{error}</p>}
        {message && <p className="success">{message}</p>}
        <div className="row-actions">
          <button type="submit">{editingId ? "Update User" : "Create User"}</button>
          {editingId && <button className="secondary-button" type="button" onClick={resetForm}>Cancel</button>}
          <button className="secondary-button" type="button" onClick={loadUsers}><RefreshCw size={16} />Refresh</button>
        </div>
      </form>

      <form className="workspace-form" onSubmit={submitSharedResume}>
        <header className="form-header">
          <h2>Shared Resume</h2>
          <p>Upload or paste a resume and assign it to individual users.</p>
        </header>
        <label>Resume title<input value={resumeForm.title} onChange={(e) => setResumeForm({ ...resumeForm, title: e.target.value })} required /></label>
        <label>Upload resume file
          <span className="file-input">
            <Upload size={18} />
            <input type="file" accept=".doc,.docx,.txt,.pdf" onChange={(e) => setResumeFile(e.target.files?.[0] || null)} />
          </span>
        </label>
        <label>Resume text<textarea rows="8" value={resumeForm.original_text} onChange={(e) => setResumeForm({ ...resumeForm, original_text: e.target.value })} required={!resumeFile} /></label>
        <fieldset className="choice-panel">
          <legend>Share with users</legend>
          <div className="choice-grid">
            {users.filter((user) => user.is_active).map((user) => (
              <label className="checkbox" key={user.id}>
                <input
                  type="checkbox"
                  checked={resumeForm.shared_with.includes(user.id)}
                  onChange={() => toggleResumeUser(user.id)}
                />
                {user.username}
              </label>
            ))}
          </div>
        </fieldset>
        <button type="submit"><Save size={18} /> Upload Shared Resume</button>
      </form>

      <section className="workspace-form compact-form">
        <header className="form-header">
          <h2>Shared Resume Library</h2>
          <p>Resumes you own and their assigned users.</p>
        </header>
        {resumes.length ? (
          <div className="list">
            {resumes.map((resume) => (
              <article className="row-card" key={resume.id}>
                <div>
                  <h3>{resume.title}</h3>
                  <p>Uploaded by: {resume.uploaded_by || resume.owner_username || "Unknown"}</p>
                  <p>Assigned to: {resume.shared_with_usernames?.length ? resume.shared_with_usernames.join(", ") : "No users assigned"}</p>
                  <div className="choice-grid inline-choice-grid">
                    {users.filter((user) => user.is_active).map((user) => (
                      <label className="checkbox" key={user.id}>
                        <input
                          type="checkbox"
                          checked={(resumeShares[resume.id] || []).includes(user.id)}
                          onChange={() => toggleExistingResumeUser(resume.id, user.id)}
                        />
                        {user.username}
                      </label>
                    ))}
                  </div>
                </div>
                <button type="button" onClick={() => saveResumeShares(resume)}>Save Sharing</button>
              </article>
            ))}
          </div>
        ) : (
          <p className="empty-state">No shared resumes uploaded yet.</p>
        )}
      </section>

      <div className="sheet-wrap">
        <table className="sheet-table compact">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="5">Loading users...</td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan="5">No users yet.</td></tr>
            ) : (
              users.map((user) => (
                <tr key={user.id}>
                  <td>{user.username}</td>
                  <td>{user.email || "-"}</td>
                  <td>{user.is_superuser ? "Super administrator" : user.is_staff ? "Administrator" : "User"}</td>
                  <td>{user.is_active ? "Active" : "Inactive"}</td>
                  <td>
                    <div className="sheet-actions">
                      <button className="icon-button secondary" type="button" onClick={() => editUser(user)}>Edit</button>
                      <button className="icon-button danger" type="button" onClick={() => deleteUser(user)} title={`Delete ${user.username}`}>
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
