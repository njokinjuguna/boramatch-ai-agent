import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/job/latest`);

    const data = await response.json();
    console.log("Job fetched:",data)
    res.status(response.status).json(data);
  } catch (err) {
    console.error("Error fetching latest job:", err);
    res.status(500).json({ error: "Internal Server Error" });
  }
}
