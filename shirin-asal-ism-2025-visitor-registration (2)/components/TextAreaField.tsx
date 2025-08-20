
import React from 'react';

interface TextAreaFieldProps {
    label: string;
    name: string;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
    rows?: number;
}

export const TextAreaField: React.FC<TextAreaFieldProps> = ({ label, name, value, onChange, rows = 4 }) => {
    return (
        <div>
            <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">
                {label}
            </label>
            <textarea
                id={name}
                name={name}
                value={value}
                onChange={onChange}
                rows={rows}
                className="block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-red-500 focus:border-red-500 sm:text-sm"
            />
        </div>
    );
};
