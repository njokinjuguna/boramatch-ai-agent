import type { NextApiRequest, NextApiResponse } from "next";
import { IncomingForm, File as FormidableFile } from "formidable";
import fs from "fs";
import FormData from "form-data";
import axios from "axios";

export const config = {
  api: {
    bodyParser: false,
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: `Method ${req.method} Not Allowed` });
  }

  const form = new IncomingForm({ keepExtensions: true });

  form.parse(req, async (err, fields, files) => {
    if (err) {
      return res.status(500).json({ error: "Form parsing failed." });
    }

    const uploadedFiles = files.file;
    const file = Array.isArray(uploadedFiles) ? uploadedFiles[0] : uploadedFiles;
    const job_id = Array.isArray(fields.job_id) ? fields.job_id[0] : fields.job_id;

    if (!file || !job_id) {
      return res.status(400).json({ error: "File and job_id are required." });
    }

    try {
      const formData = new FormData();
      formData.append("file", fs.createReadStream(file.filepath), file.originalFilename);
      formData.append("job_id", job_id);


      const response = await axios.post("http://localhost:8000/upload", formData, {
        headers: formData.getHeaders(),
      });

      res.status(200).json({ status: "success", upload: response.data });
    } catch (error: any) {
      console.error("❌ Upload failed:", error?.response?.data || error.message);
      res.status(500).json({
        error: "Resume upload failed",
        detail: error?.response?.data?.detail || error.message,
      });
    }
  });
}
