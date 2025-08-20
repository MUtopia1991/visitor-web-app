
import React from 'react';
import type { VisitorData } from '../types';
import { LeadRating } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useLocalization } from '../hooks/useLocalization';

interface DashboardProps {
  visitors: VisitorData[];
}

export const Dashboard: React.FC<DashboardProps> = ({ visitors }) => {
  const { t } = useLocalization();

  if (visitors.length === 0) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-gray-700">{t('dashboard')}</h2>
        <p className="mt-4 text-gray-500">{t('noData')}</p>
      </div>
    );
  }

  // Analytics data processing
  const visitorsByDay = visitors.reduce((acc, visitor) => {
    const date = new Date(visitor.timestamp).toLocaleDateString();
    acc[date] = (acc[date] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const chartDataVisitors = Object.keys(visitorsByDay).map(date => ({
    name: date,
    visitors: visitorsByDay[date],
  }));

  const leadRatingData = [
    { name: t('hot'), count: visitors.filter(v => v.leadRating === LeadRating.Hot).length },
    { name: t('warm'), count: visitors.filter(v => v.leadRating === LeadRating.Warm).length },
    { name: t('cold'), count: visitors.filter(v => v.leadRating === LeadRating.Cold).length },
  ];

  const businessSectorData = visitors.reduce((acc, visitor) => {
    const sector = visitor.businessSector || 'Unknown';
    acc[sector] = (acc[sector] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const chartDataSectors = Object.keys(businessSectorData).map(sector => ({
    name: sector,
    count: businessSectorData[sector],
  }));


  const exportToCSV = () => {
    const headers = Object.keys(visitors[0]).join(',');
    const rows = visitors.map(visitor => 
        Object.values(visitor).map(value => 
            `"${Array.isArray(value) ? value.join(';') : String(value).replace(/"/g, '""')}"`
        ).join(',')
    );
    const csvContent = [headers, ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `shirin_asal_ism2025_visitors_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
  };


  return (
    <div className="space-y-12">
        <div className="flex flex-col md:flex-row justify-between items-center">
            <h2 className="text-3xl font-bold text-gray-800 mb-4 md:mb-0">{t('dashboard')}</h2>
            <button 
                onClick={exportToCSV}
                className="bg-blue-600 text-white font-bold py-2 px-6 rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                <span>{t('exportCSV')}</span>
            </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
            <div className="bg-gray-100 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-600">{t('totalVisitors')}</h3>
                <p className="text-4xl font-bold text-red-700">{visitors.length}</p>
            </div>
            <div className="bg-gray-100 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-600">{t('hotLeads')}</h3>
                <p className="text-4xl font-bold text-red-700">{leadRatingData.find(d => d.name === t('hot'))?.count || 0}</p>
            </div>
            <div className="bg-gray-100 p-6 rounded-lg">
                <h3 className="text-lg font-semibold text-gray-600">{t('peakDay')}</h3>
                <p className="text-4xl font-bold text-red-700">{chartDataVisitors.sort((a,b) => b.visitors - a.visitors)[0]?.name || 'N/A'}</p>
            </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            <div className="h-80">
                <h3 className="text-xl font-semibold mb-4 text-center">{t('visitorsByDay')}</h3>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartDataVisitors}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="visitors" fill="#c0392b" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
            <div className="h-80">
                <h3 className="text-xl font-semibold mb-4 text-center">{t('leadQuality')}</h3>
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={leadRatingData}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="name" />
                        <YAxis />
                        <Tooltip />
                        <Legend />
                        <Bar dataKey="count" fill="#2980b9" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
        
        <div className="h-96">
            <h3 className="text-xl font-semibold mb-4 text-center">{t('visitorsBySector')}</h3>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartDataSectors} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis dataKey="name" type="category" width={150} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" fill="#27ae60" />
                </BarChart>
            </ResponsiveContainer>
        </div>
    </div>
  );
};
