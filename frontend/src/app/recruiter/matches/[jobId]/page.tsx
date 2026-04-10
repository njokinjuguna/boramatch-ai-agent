'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

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

type JobRequirements = {
  required_phrases?: string[];
  preferred_phrases?: string[];
  years_experience?: number | null;
  location?: string | null;
  work_mode?: string | null;
  education_requirements?: string[];
  certification_requirements?: string[];
  language_requirements?: string[];
  responsibility_phrases?: string[];
  communication_requirements?: string[];
  active_dimensions?: string[];
};

type MatchResponse = {
  job_requirements?: JobRequirements;
  matches_found?: number;
  results?: MatchResult[];
  message?: string;
};

function renderList(items?: string[]) {
  if (!items || items.length === 0) return '—';
  return items.join(', ');
}

export default function MatchesPage() {
  const params = useParams();
  const jobId = Array.isArray(params?.jobId) ? params.jobId[0] : params?.jobId;

  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [requirements, setRequirements] = useState<JobRequirements | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const fetchMatches = async () => {
      try {
        setLoading(true);
        setError(null);
        setMessage(null);

        const matchRes = await fetch('/api/match', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ job_id: jobId }),
        });

        const matchData: MatchResponse = await matchRes.json();

        if (!matchRes.ok) {
          throw new Error(matchData?.message || 'Failed to get matches');
        }

        console.log('Match response:', matchData);

        setRequirements(matchData.job_requirements || null);
        setMatches(matchData.results || []);
        setMessage(matchData.message || null);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unexpected error';
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchMatches();
  }, [jobId]);

  return (
    <div className="p-4 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Matches for Job {jobId}</h1>

      {loading && <p>Loading...</p>}
      {error && <p className="text-red-500">❌ {error}</p>}

      {!loading && !error && requirements && (
        <div className="border rounded-lg p-4 mb-6 bg-gray-50">
          <h2 className="text-xl font-semibold mb-3">Detected Job Requirements</h2>

          <div className="space-y-2 text-sm">
            <p><strong>Active Dimensions:</strong> {renderList(requirements.active_dimensions)}</p>
            <p><strong>Required Phrases:</strong> {renderList(requirements.required_phrases)}</p>
            <p><strong>Preferred Phrases:</strong> {renderList(requirements.preferred_phrases)}</p>
            <p><strong>Years of Experience:</strong> {requirements.years_experience ?? '—'}</p>
            <p><strong>Location:</strong> {requirements.location || '—'}</p>
            <p><strong>Work Mode:</strong> {requirements.work_mode || '—'}</p>
            <p><strong>Education Requirements:</strong> {renderList(requirements.education_requirements)}</p>
            <p><strong>Certification Requirements:</strong> {renderList(requirements.certification_requirements)}</p>
            <p><strong>Language Requirements:</strong> {renderList(requirements.language_requirements)}</p>
            <p><strong>Responsibility Phrases:</strong> {renderList(requirements.responsibility_phrases)}</p>
            <p><strong>Communication Requirements:</strong> {renderList(requirements.communication_requirements)}</p>
          </div>
        </div>
      )}

      {!loading && !error && message && (
        <p className="mb-4 text-gray-700">{message}</p>
      )}

      {!loading && !error && matches.length === 0 && (
        <p>No matches found.</p>
      )}

      {!loading && matches.length > 0 && (
        <ul className="space-y-4">
          {matches.map((match, index) => (
            <li key={match.candidate.file_id || index} className="border p-4 rounded-lg shadow">
              <div className="mb-3">
                <h3 className="text-lg font-semibold">
                  {match.candidate.name && match.candidate.name !== 'Not found'
                    ? match.candidate.name
                    : match.candidate.filename}
                </h3>
                <p><strong>Filename:</strong> {match.candidate.filename}</p>
                <p><strong>Email:</strong> {match.candidate.email || '—'}</p>
                <p><strong>Phone:</strong> {match.candidate.phone || '—'}</p>
              </div>

              <div className="mb-3">
                <h4 className="font-semibold">Scores</h4>
                <p><strong>Final Score:</strong> {match.scores.final_score}</p>
                <p><strong>Semantic Score:</strong> {match.scores.semantic_score}</p>
                <p><strong>Required Score:</strong> {match.scores.required_score}</p>
                <p><strong>Preferred Score:</strong> {match.scores.preferred_score}</p>
                <p><strong>Experience Score:</strong> {match.scores.experience_score}</p>
                <p><strong>Location Score:</strong> {match.scores.location_score}</p>
                <p><strong>Work Mode Score:</strong> {match.scores.work_mode_score ?? '—'}</p>
                <p><strong>Education Score:</strong> {match.scores.education_score}</p>
                <p><strong>Certification Score:</strong> {match.scores.certification_score}</p>
                <p><strong>Language Score:</strong> {match.scores.language_score ?? '—'}</p>
                <p><strong>Responsibility Score:</strong> {match.scores.responsibility_score ?? '—'}</p>
                <p><strong>Communication Score:</strong> {match.scores.communication_score ?? '—'}</p>
              </div>

              <div className="mb-3">
                <h4 className="font-semibold">Match Analysis</h4>
                <p><strong>Confidence:</strong> {match.match_analysis.confidence}</p>
                <p><strong>Shortlist Status:</strong> {match.match_analysis.shortlist_status}</p>

                <p><strong>Matched Required:</strong> {renderList(match.match_analysis.matched_required)}</p>
                <p><strong>Missing Required:</strong> {renderList(match.match_analysis.missing_required)}</p>

                <p><strong>Matched Preferred:</strong> {renderList(match.match_analysis.matched_preferred)}</p>
                <p><strong>Missing Preferred:</strong> {renderList(match.match_analysis.missing_preferred)}</p>

                <p><strong>Matched Education:</strong> {renderList(match.match_analysis.matched_education)}</p>
                <p><strong>Missing Education:</strong> {renderList(match.match_analysis.missing_education)}</p>

                <p><strong>Matched Certifications:</strong> {renderList(match.match_analysis.matched_certifications)}</p>
                <p><strong>Missing Certifications:</strong> {renderList(match.match_analysis.missing_certifications)}</p>

                <p><strong>Matched Languages:</strong> {renderList(match.match_analysis.matched_languages)}</p>
                <p><strong>Missing Languages:</strong> {renderList(match.match_analysis.missing_languages)}</p>

                <p><strong>Matched Responsibilities:</strong> {renderList(match.match_analysis.matched_responsibilities)}</p>
                <p><strong>Missing Responsibilities:</strong> {renderList(match.match_analysis.missing_responsibilities)}</p>

                <p><strong>Matched Communication:</strong> {renderList(match.match_analysis.matched_communication)}</p>
                <p><strong>Missing Communication:</strong> {renderList(match.match_analysis.missing_communication)}</p>
              </div>

              <div className="mb-3">
                <h4 className="font-semibold">Candidate Profile</h4>
                <p><strong>Skills:</strong> {renderList(match.profile.skills)}</p>
                <p><strong>Years Experience:</strong> {match.profile.years_experience ?? '—'}</p>
                <p><strong>Location:</strong> {match.profile.location || '—'}</p>
                <p><strong>Work Mode:</strong> {match.profile.work_mode || '—'}</p>
                <p><strong>Education:</strong> {renderList(match.profile.education)}</p>
                <p><strong>Certifications:</strong> {renderList(match.profile.certifications)}</p>
                <p><strong>Languages:</strong> {renderList(match.profile.languages)}</p>
                <p><strong>Job Titles:</strong> {renderList(match.profile.job_titles)}</p>
                <p><strong>Responsibility Evidence:</strong> {renderList(match.profile.responsibility_evidence)}</p>
                <p><strong>Communication Evidence:</strong> {renderList(match.profile.communication_evidence)}</p>
              </div>

              <div className="mb-3">
                <h4 className="font-semibold">Explanation</h4>
                <p>{match.explanation}</p>
              </div>

              <div className="mb-3">
                <h4 className="font-semibold">Snippet</h4>
                <p>{match.snippet}</p>
              </div>

              <a
                href={`/api/resume/view?file_id=${match.candidate.file_id}`}
                target="_blank"
                rel="noreferrer"
                className="text-blue-600 underline"
              >
                View Resume
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}