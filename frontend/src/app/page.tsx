"use client";

import { useEffect, useRef, useState } from "react";

type Job = {
  title: string;
  description: string;
  job_id: string;
};

type FeedbackState = {
  type: "success" | "error" | "info" | "";
  text: string;
};

type UploadPayload = {
  status?: "success" | "duplicate";
  message?: string;
  candidate_email?: string;
  candidate_id?: string;
  job_id?: string;
  application_id?: string;
};

type UploadApiResponse = {
  status?: string;
  upload?: UploadPayload;
  error?: string;
  detail?: string;
};

const CandidatePage = () => {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [feedback, setFeedback] = useState<FeedbackState>({ type: "", text: "" });
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const fetchJob = async () => {
      try {
        const res = await fetch("/api/job/latest");
        const data = await res.json();
        setJob(data);
      } catch (err) {
        console.error("Failed to load job", err);
        setFeedback({
          type: "error",
          text: "We could not load the current job posting. Please refresh the page and try again.",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchJob();
  }, []);

  const clearFileInput = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback({ type: "", text: "" });
    setUploading(true);

    if (!file || !job?.job_id) {
      setFeedback({
        type: "error",
        text: "Please choose your resume file before submitting.",
      });
      setUploading(false);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("job_id", job.job_id);

    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data: UploadApiResponse = await res.json();

      if (!res.ok) {
        throw new Error(data.error || data.detail || "Upload failed.");
      }

      const uploadResult = data.upload;

      if (!uploadResult) {
        throw new Error("Unexpected server response.");
      }

      if (uploadResult.status === "duplicate") {
        setFeedback({
          type: "info",
          text:
            uploadResult.message ||
            "You already applied for this role.",
        });
        clearFileInput();
        return;
      }

      if (uploadResult.status === "success") {
        setFeedback({
          type: "success",
          text:
            uploadResult.message ||
            "Your resume has been submitted successfully. Thank you for applying — our team will review your profile.",
        });
        clearFileInput();
        return;
      }

      throw new Error("Unknown upload result returned by the server.");
    } catch (err: any) {
      setFeedback({
        type: "error",
        text:
          err.message ||
          "Something went wrong while uploading your resume. Please try again.",
      });
    } finally {
      setUploading(false);
    }
  };

  const feedbackStyles =
    feedback.type === "success"
      ? "border-green-200 bg-green-50 text-green-800"
      : feedback.type === "error"
      ? "border-red-200 bg-red-50 text-red-700"
      : "border-amber-200 bg-amber-50 text-amber-800";

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-center text-gray-800 mb-8">
        📄 BoraMatch – Apply for This Role
      </h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        <section className="border rounded-xl bg-gray-50 p-5 shadow-sm lg:sticky lg:top-6 max-h-[75vh] overflow-y-auto">
          {loading ? (
            <p className="text-center text-gray-600">Loading job description...</p>
          ) : job ? (
            <>
              <h2 className="text-xl font-semibold text-gray-700 mb-3">Job Description</h2>
              <p className="text-gray-800 whitespace-pre-wrap font-semibold">{job.title}</p>
              <p className="mt-3 text-gray-700 whitespace-pre-wrap leading-7">
                {job.description}
              </p>
            </>
          ) : (
            <p className="text-center text-red-500">No job posting available yet.</p>
          )}
        </section>

        <section className="space-y-5">
          <div className="border rounded-xl bg-white p-5 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-700 mb-4">Submit Your Application</h2>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block font-medium mb-2">
                  Upload Your Resume (PDF or DOCX)
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.doc,.docx"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="border rounded px-4 py-2 w-full"
                />
                {file && (
                  <p className="mt-2 text-sm text-gray-600">
                    Selected file: <span className="font-medium">{file.name}</span>
                  </p>
                )}
              </div>

              <button
                type="submit"
                disabled={!file || uploading}
                className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <>
                    <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 00-8 8h4z"
                      />
                    </svg>
                    Uploading...
                  </>
                ) : (
                  "Submit Resume"
                )}
              </button>
            </form>
          </div>

          {uploading && (
            <div className="border border-blue-200 bg-blue-50 text-blue-700 rounded-xl p-4 text-center shadow-sm">
              We are securely uploading your resume. Please wait a moment...
            </div>
          )}

          {feedback.text && !uploading && (
            <div className={`border rounded-xl p-4 text-center shadow-sm ${feedbackStyles}`}>
              <p className="font-semibold">
                {feedback.type === "success"
                  ? "Application received"
                  : feedback.type === "error"
                  ? "Upload unsuccessful"
                  : "Already applied"}
              </p>
              <p className="mt-2">{feedback.text}</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
};

export default CandidatePage;