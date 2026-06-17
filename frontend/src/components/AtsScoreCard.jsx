export default function AtsScoreCard({ score }) {
  const value = Number(score || 0);
  return (
    <div className="score-card">
      <div className="score-ring" style={{ "--score": `${value * 3.6}deg` }}>
        <span>{value}</span>
      </div>
      <div>
        <h3>ATS Score</h3>
        <p>Advisory keyword match score based on the saved job description.</p>
      </div>
    </div>
  );
}
