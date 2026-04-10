import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { job_id } = req.query;

  if (!job_id || typeof job_id !== "string") {
    return res.status(400).json({ error: "Missing job_id" });
  }

  try {
    const response = await fetch(`http://localhost:8000/resume/by-job?job_id=${job_id}`);
    const data = await response.json();
    return res.status(response.status).json(data);
  } catch (err) {
    console.error("Failed to fetch resumes:", err);
    res.status(500).json({ error: "Internal Server Error" });
  }
}
