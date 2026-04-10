"use client";

import React, { useEffect, useState } from "react";
import Modal from "@/components/Modal";
import { format } from "date-fns";
import { Users, CheckCircle } from "lucide-react";

type Job = {
  job_id: string;
  title: string;
  description: string;
  created_at: string;
};

type ResumeItem = {
  file_id: string;
  filename: string;
  text_preview?: string;
  candidate_name?: string;
  candidate_email?: string;
  candidate_phone?: string;
  profile?: Record<string, unknown>;
};

type MatchResult = {
  candidate: {
    file_id: string;
    filename: string;
    name: string;
    email: string;
    phone: string;
  };
  profile: {
    skills: string[];
    years_experience: number;
    location: string | null;
    work_mode?: string | null;
    education: string[];
    certifications: string[];
    languages?: string[];
    job_titles?: string[];
    responsibility_evidence?: string[];
    communication_evidence?: string[];
  };
  scores: {
    final_score: number;
    semantic_score: number;
    required_score: number;
    preferred_score: number;
    experience_score: number;
    location_score: number;
    work_mode_score?: number;
    education_score: number;
    certification_score: number;
    language_score?: number;
    responsibility_score?: number;
    communication_score?: number;
  };
  match_analysis: {
    confidence: string;
    shortlist_status: string;
    matched_required: string[];
    missing_required: string[];
    matched_preferred: string[];
    missing_preferred: string[];
    matched_education: string[];
    missing_education: string[];
    matched_certifications: string[];
    missing_certifications: string[];
    matched_languages?: string[];
    missing_languages?: string[];
    matched_responsibilities?: string[];
    missing_responsibilities?: string[];
    matched_communication?: string[];
    missing_communication?: string[];
  };
  explanation: string;
  snippet: string;
};

function renderList(items?: string[]) {
  if (!items || items.length === 0) return "—";
  return items.join(", ");
}

export default function RecruiterPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [modalType, setModalType] = useState<"post" | "applicants" | "matches" | null>(null);

  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const res = await fetch("/api/job/list");
        const data = await res.json();
        if (Array.isArray(data.jobs)) {
          setJobs(data.jobs);
        }
      } catch (err) {
        console.error("Failed to load jobs", err);
      }
    };

    fetchJobs();
  }, []);

  const fetchResumes = async (jobId: string) => {
    try {
      const res = await fetch(`/api/resume/by_job?job_id=${jobId}`);
      const data = await res.json();
      setResumes(data.resumes || []);
    } catch (err) {
      console.error("Failed to fetch resumes", err);
    }
  };

  const fetchMatches = async (jobId: string) => {
    try {
      const res = await fetch(`/api/match`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId }),
      });

      const data = await res.json();
      console.log("Recruiter modal match response:", data);
      setMatches(data.results || []);
    } catch (err) {
      console.error("Failed to fetch matches", err);
    }
  };

  const handlePostJob = async () => {
    setLoading(true);
    setMessage("");

    try {
      const res = await fetch("/api/job/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "Job creation failed");

      setMessage("✅ Job posted.");
      setTitle("");
      setDescription("");

      const refreshRes = await fetch("/api/job/list");
      const refreshData = await refreshRes.json();
      if (Array.isArray(refreshData.jobs)) {
        setJobs(refreshData.jobs);
      }

      setModalType(null);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Something went wrong";
      setMessage("❌ " + errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="max-w-5xl mx-auto py-10 px-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-gray-800">📄 Recruiter Dashboard</h1>
        <button
          onClick={() => setModalType("post")}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          ➕ Post Job
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full border">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-2 text-left">Job Title</th>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.job_id} className="border-t">
                <td className="px-4 py-2">{job.title}</td>
                <td className="px-4 py-2">
                  {format(new Date(job.created_at), "yyyy-MM-dd")}
                </td>
                <td className="flex gap-4 items-center px-4 py-2">
                  <button
                    type="button"
                    title="View Applicants"
                    onClick={async () => {
                      setSelectedJob(job);
                      await fetchResumes(job.job_id);
                      setModalType("applicants");
                    }}
                  >
                    <Users className="w-5 h-5 text-blue-600 hover:text-blue-800 cursor-pointer" />
                  </button>

                  <CheckCircle
                    title="View Matches"
                    className="w-5 h-5 text-green-600 hover:text-green-800 cursor-pointer"
                    onClick={async () => {
                      setSelectedJob(job);
                      await fetchMatches(job.job_id);
                      setModalType("matches");
                    }}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        title="Post a New Job"
        isOpen={modalType === "post"}
        onClose={() => setModalType(null)}
      >
        <div className="space-y-4">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Job Title"
            className="w-full border rounded p-2"
          />

          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Job Description"
            rows={7}
            className="w-full border rounded p-2"
          />

          <button
            onClick={handlePostJob}
            disabled={!title || !description || loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? "Posting..." : "Submit Job"}
          </button>

          {message && <p className="text-sm">{message}</p>}
        </div>
      </Modal>

      <Modal
        title={`Applicants for ${selectedJob?.title || ""}`}
        isOpen={modalType === "applicants" && !!selectedJob}
        onClose={() => setModalType(null)}
      >
        {resumes.length === 0 ? (
          <p>No applicants yet.</p>
        ) : (
          <ul className="space-y-4">
            {resumes.map((r, i) => (
              <li key={r.file_id} className="border rounded-lg p-4 bg-gray-50 shadow-sm">
                <div className="mb-2">
                  <p className="font-semibold text-lg">
                    #{i + 1} —{" "}
                    {r.candidate_name && r.candidate_name !== "Not found"
                      ? r.candidate_name
                      : r.filename}
                  </p>
                  <p className="text-sm text-gray-700">
                    {r.candidate_email || "—"} {r.candidate_phone ? `| ${r.candidate_phone}` : ""}
                  </p>
                </div>

                <div className="mb-2 text-sm text-gray-700">
                  <p><strong>Filename:</strong> {r.filename}</p>
                </div>

                <a
                  href={`https://drive.google.com/file/d/${r.file_id}/view`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 underline inline-block"
                >
                  View Resume
                </a>
              </li>
            ))}
          </ul>
        )}
      </Modal>

      <Modal
        title={`Top Ranked Candidates for ${selectedJob?.title || ""}`}
        isOpen={modalType === "matches" && !!selectedJob}
        onClose={() => setModalType(null)}
      >
        {matches.length === 0 ? (
          <p>No strong matches found.</p>
        ) : (
          <ul className="space-y-4">
            {matches.map((m, i) => (
              <li
                key={m.candidate.file_id}
                className="border rounded-lg p-4 bg-gray-50 shadow-sm"
              >
                <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-2">
                  <div>
                    <p className="font-semibold text-lg">
                      #{i + 1} —{" "}
                      {m.candidate.name && m.candidate.name !== "Not found"
                        ? m.candidate.name
                        : m.candidate.filename}
                    </p>
                    <p className="text-sm text-gray-700">
                      {m.candidate.email || "—"} {m.candidate.phone ? `| ${m.candidate.phone}` : ""}
                    </p>
                  </div>

                  <p className="text-sm text-gray-700 mt-1 sm:mt-0">
                    Final Match Score:{" "}
                    <strong>
                      {m.scores?.final_score != null
                        ? `${(m.scores.final_score * 100).toFixed(1)}%`
                        : "—"}
                    </strong>{" "}
                    — Confidence:{" "}
                    <span className="italic">
                      {m.match_analysis?.confidence || "—"}
                    </span>
                  </p>
                </div>

                <div className="mb-2 text-sm text-gray-700">
                  <p>
                    <strong>Shortlist Status:</strong>{" "}
                    {m.match_analysis?.shortlist_status || "—"}
                  </p>
                  <p>
                    <strong>Semantic Score:</strong>{" "}
                    {m.scores?.semantic_score != null ? m.scores.semantic_score : "—"}
                    {" | "}
                    <strong>Core Requirement Score:</strong>{" "}
                    {m.scores?.required_score != null ? m.scores.required_score : "—"}
                    {" | "}
                    <strong>Preferred Score:</strong>{" "}
                    {m.scores?.preferred_score != null ? m.scores.preferred_score : "—"}
                  </p>
                </div>

                <div className="mb-2 text-sm text-gray-700">
                  <p>
                    <strong>Matched Core:</strong>{" "}
                    {renderList(m.match_analysis?.matched_required)}
                  </p>
                  <p>
                    <strong>Missing Core:</strong>{" "}
                    {renderList(m.match_analysis?.missing_required)}
                  </p>
                </div>

                <div className="mb-2 text-sm text-gray-700">
                  <p>
                    <strong>Skills:</strong> {renderList(m.profile?.skills)}
                  </p>
                  <p>
                    <strong>Years Experience:</strong>{" "}
                    {m.profile?.years_experience ?? "—"}
                    {/* {" | "}
                    <strong>Location:</strong> {m.profile?.location || "—"}
                    {" | "}
                    <strong>Work Mode:</strong> {m.profile?.work_mode || "—"} */}
                  </p>
                </div>

                <div className="mb-2 text-sm text-gray-700">
                  <strong>Explanation:</strong>
                  <div className="mt-1 whitespace-normal break-words leading-6">
                    {m.explanation || "—"}
                  </div>
                </div>

                <a
                  href={`https://drive.google.com/file/d/${m.candidate.file_id}/view`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline mt-3 inline-block"
                >
                  View Resume
                </a>
              </li>
            ))}
          </ul>
        )}
      </Modal>
    </main>
  );
}