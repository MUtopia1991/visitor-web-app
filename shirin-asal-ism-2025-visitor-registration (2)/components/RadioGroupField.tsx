
import React from 'react';

interface RadioGroupFieldProps {
    legend: string;
    name: string;
    options: string[];
    selectedValue: string;
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const RadioGroupField: React.FC<RadioGroupFieldProps> = ({ legend, name, options, selectedValue, onChange }) => {
    return (
        <fieldset>
            <legend className="text-sm font-medium text-gray-900 mb-2">{legend}</legend>
            <div className="flex items-center space-x-6">
                {options.map(option => (
                    <div key={option} className="flex items-center">
                        <input
                            id={`${name}-${option}`}
                            name={name}
                            type="radio"
                            value={option}
                            checked={selectedValue === option}
                            onChange={onChange}
                            className="h-4 w-4 text-red-600 border-gray-300 focus:ring-red-500"
                        />
                        <label htmlFor={`${name}-${option}`} className="ml-2 block text-sm text-gray-700">
                            {option}
                        </label>
                    </div>
                ))}
            </div>
        </fieldset>
    );
};
