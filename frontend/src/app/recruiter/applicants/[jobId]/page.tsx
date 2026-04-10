'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

export default function ApplicantsPage() {
  const {jobId} = useParams();
  const [applicants, setApplicants] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Basic text extractors from text_preview
  const extractField = (text: string, field: string): string => {
    const match = text.match(new RegExp(`${field}:?\\s*(.*)`, 'i'));
    return match ? match[1].split('\n')[0].trim() : '';
  };

  useEffect(() => {
    const fetchApplicants = async () => {
      try {
        const res = await fetch(`/api/resume/by_job?job_id=${jobId}`);
        const data = await res.json();
        setApplicants(data.resumes || []);
      } catch (error) {
        console.error('Failed to fetch applicants:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchApplicants();
  }, [jobId]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Applicants for Job <code>{jobId}</code></h1>

      {loading ? (
        <p>Loading...</p>
      ) : applicants.length > 0 ? (
        <ul className="space-y-4">
          {applicants.map((applicant, index) => {
            const preview = applicant.text_preview || '';
            const name = extractField(preview, 'Name') || applicant.filename;
            const email = extractField(preview, 'Email');
            const phone = extractField(preview, 'Phone');
            const resumeUrl = `https://drive.google.com/file/d/${applicant.file_id}/view`;

            return (
              <li key={index} className="border p-4 rounded-md shadow-md">
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email || 'Not found'}</p>
                <p><strong>Phone:</strong> {phone || 'Not found'}</p>
                <p><strong>File:</strong> {applicant.filename}</p>
                <a
                  href={resumeUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 underline mt-2 inline-block"
                >
                  View Resume
                </a>
              </li>
            );
          })}
        </ul>
      ) : (
        <p>No applicants found for this job.</p>
      )}
    </div>
  );
}
