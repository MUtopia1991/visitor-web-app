import React, { createContext, useState, useContext, ReactNode, useEffect } from 'react';

interface LanguageContextType {
    language: string;
    setLanguage: (language: string) => void;
    t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [language, setLanguage] = useState('en');
    const [translations, setTranslations] = useState<Record<string, Record<string, string>>>({});
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchTranslations = async () => {
            try {
                // Fetch translation files relative to the root index.html
                const [en, fa, ar] = await Promise.all([
                    fetch('./locales/en.json').then(res => { if (!res.ok) throw new Error('Failed to fetch en.json'); return res.json(); }),
                    fetch('./locales/fa.json').then(res => { if (!res.ok) throw new Error('Failed to fetch fa.json'); return res.json(); }),
                    fetch('./locales/ar.json').then(res => { if (!res.ok) throw new Error('Failed to fetch ar.json'); return res.json(); })
                ]);
                setTranslations({ en, fa, ar });
            } catch (error) {
                console.error("Failed to load translation files:", error);
                // In case of error, the app will run with keys as text
            } finally {
                setIsLoading(false);
            }
        };

        fetchTranslations();
    }, []);

    const t = (key: string): string => {
        const langDict = translations[language] || translations['en'];
        return langDict?.[key] || key;
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-100">
                <div className="text-center">
                    {/* Replaced logo image with text */}
                    <h1 className="text-4xl font-bold text-red-700 animate-pulse">Shirin Asal</h1>
                    <p className="mt-4 text-lg text-gray-700">Loading Application...</p>
                </div>
            </div>
        );
    }

    return (
        <LanguageContext.Provider value={{ language, setLanguage, t }}>
            {children}
        </LanguageContext.Provider>
    );
};

export const useLanguage = (): LanguageContextType => {
    const context = useContext(LanguageContext);
    if (!context) {
        throw new Error('useLanguage must be used within a LanguageProvider');
    }
    return context;
};
