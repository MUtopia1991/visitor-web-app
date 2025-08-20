import React, { useState } from 'react';
import { useLocalization } from '../hooks/useLocalization';

interface LoginScreenProps {
    onLoginSuccess: () => void;
}

// In a real application, this would not be hardcoded.
const CORRECT_PASSWORD = 'ism2025';

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
    const { t } = useLocalization();
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (password === CORRECT_PASSWORD) {
            onLoginSuccess();
        } else {
            setError(t('invalidPassword'));
        }
    };
    
    return (
        <div className="flex items-center justify-center min-h-screen bg-gray-100">
            <div className="w-full max-w-md p-8 space-y-6 bg-white rounded-xl shadow-lg">
                <div className="text-center">
                    {/* Replaced the logo image with text */}
                    <h1 className="text-4xl font-bold text-red-700">Shirin Asal</h1>
                    <h2 className="mt-4 text-2xl font-bold text-gray-900">
                        {t('staffLogin')}
                    </h2>
                     <p className="text-sm text-gray-600">{t('loginPrompt')}</p>
                </div>
                <form className="space-y-6" onSubmit={handleLogin}>
                    <div className="relative">
                         <input
                            id="password"
                            name="password"
                            type="password"
                            autoComplete="current-password"
                            required
                            value={password}
                            onChange={(e) => {
                                setPassword(e.target.value);
                                setError('');
                            }}
                            className="block w-full px-4 py-3 text-gray-900 placeholder-gray-500 border border-gray-300 rounded-md appearance-none focus:outline-none focus:ring-red-500 focus:border-red-500 sm:text-sm"
                            placeholder={t('password')}
                        />
                    </div>
                    {error && <p className="text-sm text-red-600">{error}</p>}
                    <div>
                        <button
                            type="submit"
                            className="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-700 hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                        >
                           {t('login')}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
