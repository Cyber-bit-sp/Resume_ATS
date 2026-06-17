export default function KeywordMatchList({ matched = [], missing = [] }) {
  return (
    <div className="keyword-grid">
      <section>
        <h3>Matched Keywords</h3>
        <div className="chips">
          {matched.length ? matched.map((keyword) => <span key={keyword}>{keyword}</span>) : <em>No matches yet</em>}
        </div>
      </section>
      <section>
        <h3>Missing Keywords</h3>
        <div className="chips muted">
          {missing.length ? missing.map((keyword) => <span key={keyword}>{keyword}</span>) : <em>No missing keywords</em>}
        </div>
      </section>
    </div>
  );
}
