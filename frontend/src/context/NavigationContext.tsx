import React, { createContext, useContext, useState, useEffect } from 'react';
import { ViewName } from '../types';

interface NavigationContextType {
  currentView: ViewName;
  selectedRecordId: string | null;
  selectedDiscrepancyId: string | null;
  navigate: (
    view: ViewName,
    params?: { recordId?: string; discrepancyId?: string }
  ) => void;
  goBack: () => void;
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined);

export const NavigationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentView, setCurrentView] = useState<ViewName>('dashboard');
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);
  const [selectedDiscrepancyId, setSelectedDiscrepancyId] = useState<string | null>(null);
  const [history, setHistory] = useState<{ view: ViewName; recordId: string | null }[]>([
    { view: 'dashboard', recordId: null },
  ]);

  const navigate = (
    view: ViewName,
    params?: { recordId?: string; discrepancyId?: string }
  ): void => {
    setCurrentView(view);
    if (params?.recordId !== undefined) {
      setSelectedRecordId(params.recordId || null);
    }
    if (params?.discrepancyId !== undefined) {
      setSelectedDiscrepancyId(params.discrepancyId || null);
    }

    setHistory((prev) => [...prev, { view, recordId: params?.recordId || null }]);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const goBack = (): void => {
    if (history.length > 1) {
      const newHistory = [...history];
      newHistory.pop(); // Remove current
      const previous = newHistory[newHistory.length - 1];
      setHistory(newHistory);
      setCurrentView(previous.view);
      setSelectedRecordId(previous.recordId);
    } else {
      setCurrentView('dashboard');
      setSelectedRecordId(null);
    }
  };

  return (
    <NavigationContext.Provider
      value={{
        currentView,
        selectedRecordId,
        selectedDiscrepancyId,
        navigate,
        goBack,
      }}
    >
      {children}
    </NavigationContext.Provider>
  );
};

export const useNavigation = (): NavigationContextType => {
  const context = useContext(NavigationContext);
  if (!context) {
    throw new Error('useNavigation must be used within a NavigationProvider');
  }
  return context;
};
