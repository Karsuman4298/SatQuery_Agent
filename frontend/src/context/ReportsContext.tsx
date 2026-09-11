import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import { type HistoryEntry, type HistoryModality, type HistoryChatMessage } from './HistoryContext';

export type ReportStatus = 'Ready' | 'Generating' | 'Failed';
export type ReportType = 'Analysis Report' | 'Exported Report';

export interface ReportEntry {
  id: string;
  title: string;
  analysisId: string;
  analysisName: string;
  imageUrl: string;
  fileName: string;
  fileSize?: string;
  fileDimensions?: string;
  fileType?: string;
  modality: HistoryModality;
  spectralChannel: string;
  region: string;
  confidence: number;
  dataset?: string;
  chatMessages: HistoryChatMessage[];
  detectedRegions?: Array<{ name: string; type: string; score: string }>;
  status: ReportStatus;
  reportType: ReportType;
  isShared: boolean;
  createdAt: string;
  updatedAt: string;
  userEmail: string;
}

interface ReportsContextType {
  reports: ReportEntry[];
  isLoading: boolean;
  generateReportFromAnalysis: (
    analysis: HistoryEntry,
    reportType?: ReportType,
    customDetectedRegions?: Array<{ name: string; type: string; score: string }>
  ) => string;
  deleteReport: (id: string) => void;
  markAsShared: (id: string) => void;
  getReport: (id: string) => ReportEntry | undefined;
}

const ReportsContext = createContext<ReportsContextType | undefined>(undefined);

const STORAGE_KEY = 'satquery_reports_storage';

/** Remove any old dummy/seed records if present */
function cleanReportEntries(all: ReportEntry[]): ReportEntry[] {
  return all.filter((r) => r && r.id && !r.id.startsWith('sq-seed-'));
}

export const ReportsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const userEmail = user?.email || 'guest@satquery.ai';

  const [reports, setReports] = useState<ReportEntry[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const all: ReportEntry[] = cleanReportEntries(JSON.parse(raw));
      localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
      return all.filter((r) => r.userEmail === userEmail);
    } catch {
      return [];
    }
  });

  const [isLoading, setIsLoading] = useState(false);

  /* Persist current user's reports to localStorage without overwriting other users */
  const persistAll = useCallback(
    (currentUserReports: ReportEntry[]) => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const all: ReportEntry[] = raw ? cleanReportEntries(JSON.parse(raw)) : [];
        const others = all.filter((r) => r.userEmail !== userEmail);
        localStorage.setItem(STORAGE_KEY, JSON.stringify([...others, ...currentUserReports]));
      } catch {
        // storage quota safety
      }
    },
    [userEmail]
  );

  /* We manually persist on changes to avoid effect race conditions during auth */

  /* Re-fetch when user changes */
  useEffect(() => {
    setIsLoading(true);
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setReports([]);
      } else {
        const all: ReportEntry[] = cleanReportEntries(JSON.parse(raw));
        setReports(all.filter((r) => r.userEmail === userEmail));
      }
    } catch {
      setReports([]);
    }
    setIsLoading(false);
  }, [userEmail]);

  const generateReportFromAnalysis = useCallback(
    (
      analysis: HistoryEntry,
      reportType: ReportType = 'Analysis Report',
      customDetectedRegions?: Array<{ name: string; type: string; score: string }>
    ): string => {
      const id = `rep-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
      const now = new Date().toISOString();

      const newReport: ReportEntry = {
        id,
        title: `${reportType} — ${analysis.name}`,
        analysisId: analysis.id,
        analysisName: analysis.name,
        imageUrl: analysis.imageUrl,
        fileName: analysis.fileName,
        fileSize: analysis.fileSize,
        fileDimensions: analysis.fileDimensions,
        fileType: analysis.fileType,
        modality: analysis.modality,
        spectralChannel: analysis.spectralChannel,
        region: analysis.region,
        confidence: analysis.confidence || 92.5,
        dataset: analysis.dataset || 'Satellite Imagery',
        chatMessages: analysis.chatMessages || [],
        detectedRegions: customDetectedRegions || [
          { name: analysis.region || 'Region Alpha', type: 'Primary Sector', score: `${analysis.confidence || 92.5}%` },
        ],
        status: 'Ready',
        reportType,
        isShared: false,
        createdAt: now,
        updatedAt: now,
        userEmail,
      };

      setReports((prev) => {
        const next = [newReport, ...prev];
        persistAll(next);
        return next;
      });
      return id;
    },
    [userEmail, persistAll]
  );

  const deleteReport = useCallback((id: string) => {
    setReports((prev) => {
      const next = prev.filter((r) => r.id !== id);
      persistAll(next);
      return next;
    });
  }, [persistAll]);

  const markAsShared = useCallback((id: string) => {
    setReports((prev) => {
      const next = prev.map((r) => (r.id === id ? { ...r, isShared: true, updatedAt: new Date().toISOString() } : r));
      persistAll(next);
      return next;
    });
  }, [persistAll]);

  const getReport = useCallback(
    (id: string) => reports.find((r) => r.id === id),
    [reports]
  );

  return (
    <ReportsContext.Provider
      value={{
        reports,
        isLoading,
        generateReportFromAnalysis,
        deleteReport,
        markAsShared,
        getReport,
      }}
    >
      {children}
    </ReportsContext.Provider>
  );
};

export const useReports = (): ReportsContextType => {
  const ctx = useContext(ReportsContext);
  if (!ctx) throw new Error('useReports must be used within a ReportsProvider');
  return ctx;
};

export default ReportsContext;
