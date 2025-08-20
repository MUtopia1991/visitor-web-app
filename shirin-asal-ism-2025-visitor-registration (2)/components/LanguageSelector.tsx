
import React from 'react';
import { useLanguage } from '../context/LanguageContext';

export const LanguageSelector: React.FC = () => {
    const { language, setLanguage } = useLanguage();

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        setLanguage(e.target.value);
    };

    return (
        <div className="relative">
            <select
                value={language}
                onChange={handleChange}
                className="appearance-none bg-white border border-gray-300 text-gray-700 py-2 pl-3 pr-8 rounded-md leading-tight focus:outline-none focus:bg-white focus:border-red-500"
            >
                <option value="en">English</option>
                <option value="fa">فارسی (Persian)</option>
                <option value="ar">العربية (Arabic)</option>
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
            </div>
        </div>
    );
};
