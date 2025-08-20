
import React, { useState, useEffect } from 'react';
import { RegistrationForm } from './components/RegistrationForm';
import { Dashboard } from './components/Dashboard';
import { Header } from './components/Header';
import { LanguageProvider } from './context/LanguageContext';
import { storageService } from './services/storageService';
import { googleSheetsService } from './services/googleSheetsService';
import type { VisitorData } from './types';

enum View {
  Form,
  Dashboard
}

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<View>(View.Form);
  const [allVisitors, setAllVisitors] = useState<VisitorData[]>([]);
  const [syncStatus, setSyncStatus] = useState<string>('Idle');
  const [lastSync, setLastSync] = useState<Date | null>(null);

  const refreshData = () => {
    setAllVisitors(storageService.getSubmittedVisitors());
  };

  useEffect(() => {
    // Initial data load
    refreshData();

    // Background sync process
    const syncInterval = setInterval(async () => {
      const queued = storageService.getQueuedSubmissions();
      if (queued.length > 0) {
        setSyncStatus(`Syncing ${queued.length} records...`);
        try {
          const success = await googleSheetsService.syncQueuedSubmissions();
          if (success) {
            setSyncStatus('Sync successful!');
            setLastSync(new Date());
            refreshData(); // Refresh dashboard data after sync
          } else {
            setSyncStatus('Sync failed. Will retry.');
          }
        } catch (error) {
          console.error("Sync error:", error);
          setSyncStatus('Sync error. Check console.');
        }
      } else {
        setSyncStatus('No items to sync.');
      }
    }, 30000); // Try to sync every 30 seconds

    return () => clearInterval(syncInterval);
  }, []);

  const queuedCount = storageService.getQueuedSubmissions().length;

  return (
    <LanguageProvider>
      <div className="min-h-screen bg-gray-50 text-gray-800 font-sans">
        <Header />
        <main className="container mx-auto p-4 md:p-8">
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center">
              <div className="flex space-x-2 border-b sm:border-b-0 sm:border-0 mb-4 sm:mb-0">
                <button
                  onClick={() => setCurrentView(View.Form)}
                  className={`px-4 py-2 rounded-t-lg text-lg font-semibold transition-colors duration-200 ${currentView === View.Form ? 'bg-red-700 text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                >
                  Registration Form
                </button>
                <button
                  onClick={() => {
                    refreshData();
                    setCurrentView(View.Dashboard);
                  }}
                  className={`px-4 py-2 rounded-t-lg text-lg font-semibold transition-colors duration-200 ${currentView === View.Dashboard ? 'bg-red-700 text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                >
                  Dashboard
                </button>
              </div>
              <div className="text-sm text-gray-500 text-right w-full sm:w-auto">
                <p>Sync Status: <span className="font-medium">{syncStatus}</span></p>
                <p>Queued for Sync: <span className={`font-bold ${queuedCount > 0 ? 'text-orange-500' : 'text-green-500'}`}>{queuedCount}</span></p>
                {lastSync && <p>Last Successful Sync: {lastSync.toLocaleTimeString()}</p>}
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-6 md:p-10">
            {currentView === View.Form ? <RegistrationForm onFormSubmit={refreshData} /> : <Dashboard visitors={allVisitors} />}
          </div>
        </main>
      </div>
    </LanguageProvider>
  );
};

export default App;
