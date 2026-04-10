// pages/api/job/by_id.ts
import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { job_id } = req.query;
  if (!job_id) return res.status(400).json({ error: 'Missing job_id' });

  try {
    const response = await fetch(`http://localhost:8000/job/by_id?job_id=${job_id}`);
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error: any) {
    res.status(500).json({ error: 'Unable to connect to backend', details: error.message });
  }
}
