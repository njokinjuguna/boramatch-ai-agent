// pages/api/job/list.ts
import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    const backendRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/job/list`);
    const data = await backendRes.json();
    res.status(200).json(data);
  } catch (error) {
    console.error("Error fetching job list:", error);
    res.status(500).json({ error: "Failed to fetch job list" });
  }
}
