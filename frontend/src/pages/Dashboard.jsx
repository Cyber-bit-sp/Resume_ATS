import { useEffect, useState } from "react";

import api from "../api/client";

export default function Dashboard() {
  const [stats, setStats] = useState({ resumes: 0, jobs: 0, generations: 0 });

  useEffect(() => {
    async function load() {
      const [resumes, jobs, generations] = await Promise.all([
        api.get("/resumes/"),
        api.get("/jobs/"),
        api.get("/generations/"),
      ]);
      setStats({
        resumes: resumes.data.length,
        jobs: jobs.data.length,
        generations: generations.data.length,
      });
    }
    load();
  }, []);

  return (
    <>
      <header className="page-header"><h1>Dashboard</h1><p>Your resume generation workspace.</p></header>
      <div className="metric-grid">
        <div><strong>{stats.resumes}</strong><span>Resumes</span></div>
        <div><strong>{stats.jobs}</strong><span>Jobs</span></div>
        <div><strong>{stats.generations}</strong><span>Generated</span></div>
      </div>
    </>
  );
}
