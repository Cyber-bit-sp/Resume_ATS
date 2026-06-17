export default function ResumePreview({ text }) {
  return <pre className="resume-preview">{text || "Generated resume preview will appear here."}</pre>;
}
