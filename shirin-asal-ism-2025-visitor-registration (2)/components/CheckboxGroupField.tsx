
import React from 'react';

interface CheckboxGroupFieldProps {
    legend: string;
    options: string[];
    selectedOptions: string[];
    onChange: (selected: string[]) => void;
}

export const CheckboxGroupField: React.FC<CheckboxGroupFieldProps> = ({ legend, options, selectedOptions, onChange }) => {
    
    const handleChange = (option: string) => {
        const newSelection = selectedOptions.includes(option)
            ? selectedOptions.filter(item => item !== option)
            : [...selectedOptions, option];
        onChange(newSelection);
    };

    return (
        <fieldset>
            <legend className="text-sm font-medium text-gray-900 mb-2">{legend}</legend>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {options.map(option => (
                    <div key={option} className="flex items-center">
                        <input
                            id={option}
                            name={option}
                            type="checkbox"
                            checked={selectedOptions.includes(option)}
                            onChange={() => handleChange(option)}
                            className="h-4 w-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                        />
                        <label htmlFor={option} className="ml-2 block text-sm text-gray-700">
                            {option}
                        </label>
                    </div>
                ))}
            </div>
        </fieldset>
    );
};
