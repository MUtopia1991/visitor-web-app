import React from 'react';
import { LanguageSelector } from './LanguageSelector';

export const Header: React.FC = () => {
    return (
        <header className="bg-white shadow-md">
            <div className="container mx-auto px-4 py-3 flex justify-between items-center">
                <div className="flex items-center space-x-4">
                    {/* Replaced the logo image with text */}
                    <span className="text-3xl font-bold text-red-700">Shirin Asal</span>
                    <div>
                        <h1 className="text-xl md:text-2xl font-semibold text-gray-700">Visitor Registration</h1>
                        <p className="text-sm text-gray-600">ISM Middle East 2025 | Dubai</p>
                    </div>
                </div>
                <LanguageSelector />
            </div>
        </header>
    );
};
