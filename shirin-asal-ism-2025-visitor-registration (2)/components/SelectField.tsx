
import React from 'react';

interface SelectFieldProps {
    label: string;
    name: string;
    value: string;
    options: string[];
    onChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
    required?: boolean;
}

export const SelectField: React.FC<SelectFieldProps> = ({ label, name, value, options, onChange, required = false }) => {
    return (
        <div>
            <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">
                {label} {required && <span className="text-red-500">*</span>}
            </label>
            <select
                id={name}
                name={name}
                value={value}
                onChange={onChange}
                required={required}
                className="block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-red-500 focus:border-red-500 sm:text-sm"
            >
                <option value="" disabled>{`-- Select ${label} --`}</option>
                {options.map(option => (
                    <option key={option} value={option}>{option}</option>
                ))}
            </select>
        </div>
    );
};
