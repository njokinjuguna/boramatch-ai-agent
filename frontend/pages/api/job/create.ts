// pages/api/job/create.ts
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method Not Allowed" });
  }

  try {
    const { title, description } = req.body;

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/job/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, description }),
    });

    const result = await response.json();
    return res.status(response.status).json(result);
  } catch (err) {
    console.error("Job create error:", err);
    return res.status(500).json({ error: "Internal Server Error" });
  }
}
