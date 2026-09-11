import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';

/* ─────────────────────────── Types ──────────────────────────────── */

export interface HistoryChatMessage {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  time: string;
}

export type HistoryStatus = 'Completed' | 'Processing' | 'Failed';
export type HistoryModality = 'Optical' | 'SAR' | 'Multispectral' | 'Thermal';

export interface HistoryEntry {
  id: string;
  name: string;               // analysis/display name (can be renamed)
  imageUrl: string;           // base64 or src URL for thumbnail
  fileName: string;           // original file name
  fileSize?: string;
  fileDimensions?: string;
  fileType?: string;
  modality: HistoryModality;
  spectralChannel: string;    // e.g. "True Color (RGB)"
  region: string;             // active region at save time
  status: HistoryStatus;
  confidence: number;         // e.g. 94.2
  dataset?: string;           // optional dataset label
  chatMessages: HistoryChatMessage[];
  createdAt: string;          // ISO date string
  updatedAt: string;
  userEmail: string;          // scoped per user
}

/* ─────────────────────────── Context ────────────────────────────── */

interface HistoryContextType {
  entries: HistoryEntry[];
  isLoading: boolean;
  addEntry: (entry: Omit<HistoryEntry, 'id' | 'createdAt' | 'updatedAt' | 'userEmail'>) => string;
  updateEntry: (id: string, patch: Partial<Omit<HistoryEntry, 'id' | 'userEmail'>>) => void;
  deleteEntry: (id: string) => void;
  renameEntry: (id: string, newName: string) => void;
  getEntry: (id: string) => HistoryEntry | undefined;
  saveWorkspaceSnapshot: (
    id: string,
    patch: Partial<Pick<HistoryEntry, 'chatMessages' | 'spectralChannel' | 'region' | 'modality' | 'status' | 'confidence'>>
  ) => void;
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);

const STORAGE_KEY = 'satquery_analysis_history';

/** Filter out legacy starter/seed records */
function cleanStorageEntries(all: HistoryEntry[]): HistoryEntry[] {
  return all.filter((e) => e && e.id && !e.id.startsWith('sq-seed-'));
}

/* ─────────────────────────── Provider ───────────────────────────── */

export const HistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const userEmail = user?.email || 'guest@satquery.ai';

  const [entries, setEntries] = useState<HistoryEntry[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const all: HistoryEntry[] = cleanStorageEntries(JSON.parse(raw));
      // Save cleaned records back (without dummy seeds)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
      return all.filter((e) => e.userEmail === userEmail);
    } catch {
      return [];
    }
  });

  const [isLoading, setIsLoading] = useState(false);

  /* Persist entries for current user without clobbering other users */
  const persistAll = useCallback(
    (currentUserEntries: HistoryEntry[]) => {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        const all: HistoryEntry[] = raw ? cleanStorageEntries(JSON.parse(raw)) : [];
        const others = all.filter((e) => e.userEmail !== userEmail);
        localStorage.setItem(STORAGE_KEY, JSON.stringify([...others, ...currentUserEntries]));
      } catch {
        // Storage might fail if quote exceeded
      }
    },
    [userEmail]
  );

  /* We manually persist on changes to avoid effect race conditions during auth */

  /* If user changes, re-fetch entries from localStorage */
  useEffect(() => {
    setIsLoading(true);
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        setEntries([]);
      } else {
        const all: HistoryEntry[] = cleanStorageEntries(JSON.parse(raw));
        setEntries(all.filter((e) => e.userEmail === userEmail));
      }
    } catch {
      setEntries([]);
    }
    setIsLoading(false);
  }, [userEmail]);

  const addEntry = useCallback(
    (entry: Omit<HistoryEntry, 'id' | 'createdAt' | 'updatedAt' | 'userEmail'>): string => {
      const id = `sq-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
      const now = new Date().toISOString();
      const newEntry: HistoryEntry = {
        ...entry,
        id,
        userEmail,
        createdAt: now,
        updatedAt: now,
      };
      setEntries((prev) => {
        const next = [newEntry, ...prev];
        persistAll(next);
        return next;
      });
      return id;
    },
    [userEmail, persistAll]
  );

  const updateEntry = useCallback(
    (id: string, patch: Partial<Omit<HistoryEntry, 'id' | 'userEmail'>>) => {
      setEntries((prev) => {
        const next = prev.map((e) =>
          e.id === id ? { ...e, ...patch, updatedAt: new Date().toISOString() } : e
        );
        persistAll(next);
        return next;
      });
    },
    [persistAll]
  );

  const deleteEntry = useCallback((id: string) => {
    setEntries((prev) => {
      const next = prev.filter((e) => e.id !== id);
      persistAll(next);
      return next;
    });
  }, [persistAll]);

  const renameEntry = useCallback((id: string, newName: string) => {
    setEntries((prev) => {
      const next = prev.map((e) =>
        e.id === id ? { ...e, name: newName.trim() || e.name, updatedAt: new Date().toISOString() } : e
      );
      persistAll(next);
      return next;
    });
  }, [persistAll]);

  const getEntry = useCallback(
    (id: string) => entries.find((e) => e.id === id),
    [entries]
  );

  const saveWorkspaceSnapshot = useCallback(
    (
      id: string,
      patch: Partial<Pick<HistoryEntry, 'chatMessages' | 'spectralChannel' | 'region' | 'modality' | 'status' | 'confidence'>>
    ) => {
      setEntries((prev) => {
        const next = prev.map((e) =>
          e.id === id ? { ...e, ...patch, updatedAt: new Date().toISOString() } : e
        );
        persistAll(next);
        return next;
      });
    },
    [persistAll]
  );

  return (
    <HistoryContext.Provider
      value={{
        entries,
        isLoading,
        addEntry,
        updateEntry,
        deleteEntry,
        renameEntry,
        getEntry,
        saveWorkspaceSnapshot,
      }}
    >
      {children}
    </HistoryContext.Provider>
  );
};

export const useHistory = (): HistoryContextType => {
  const ctx = useContext(HistoryContext);
  if (!ctx) throw new Error('useHistory must be used within a HistoryProvider');
  return ctx;
};

export default HistoryContext;
