
import React, { useState, useRef } from 'react';
import type { VisitorData } from '../types';
import { LeadRating, ContactMethod } from '../types';
import { COUNTRIES, BUSINESS_SECTORS, PRODUCTS_OF_INTEREST } from '../constants';
import { InputField } from './InputField';
import { SelectField } from './SelectField';
import { CheckboxGroupField } from './CheckboxGroupField';
import { RadioGroupField } from './RadioGroupField';
import { TextAreaField } from './TextAreaField';
import { Spinner } from './Spinner';
import { useLocalization } from '../hooks/useLocalization';
import { geminiService } from '../services/geminiService';
import { storageService } from '../services/storageService';

interface RegistrationFormProps {
    onFormSubmit: () => void;
}

const initialFormData: Omit<VisitorData, 'id' | 'timestamp'> = {
    firstName: '',
    lastName: '',
    jobTitle: '',
    companyName: '',
    companyWebsite: 'https://',
    country: 'United Arab Emirates',
    businessSector: '',
    email: '',
    phone: '',
    productsOfInterest: [],
    contactMethod: ContactMethod.Email,
    leadRating: LeadRating.Warm,
    notes: '',
    consent: false,
    businessCardImage: undefined,
};

export const RegistrationForm: React.FC<RegistrationFormProps> = ({ onFormSubmit }) => {
    const { t } = useLocalization();
    const [formData, setFormData] = useState(initialFormData);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [hasNoWebsite, setHasNoWebsite] = useState(false);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };
    
    const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const { name, checked } = e.target;
        setFormData(prev => ({...prev, [name]: checked }));
    };

    const handleProductsChange = (selectedProducts: string[]) => {
        setFormData(prev => ({ ...prev, productsOfInterest: selectedProducts }));
    };

    const handleScanBusinessCard = () => {
        fileInputRef.current?.click();
    };

    const handleNoWebsiteChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const isChecked = e.target.checked;
        setHasNoWebsite(isChecked);
        if (isChecked) {
            setFormData(prev => ({ ...prev, companyWebsite: '' }));
        } else {
            // Restore default when unchecked
            setFormData(prev => ({ ...prev, companyWebsite: 'https://' }));
        }
    };


    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setIsLoading(true);
        setError(null);
        try {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = async () => {
                const base64Image = (reader.result as string).split(',')[1];
                setFormData(prev => ({...prev, businessCardImage: base64Image}));
                const extractedData = await geminiService.extractInfoFromImage(base64Image);
                
                if (extractedData) {
                    if (extractedData.website) {
                        setHasNoWebsite(false); // Uncheck the box if a website is found
                    }
                    setFormData(prev => {
                        const website = extractedData.website;
                        // Ensure URL has a protocol to be valid for the input type="url"
                        const companyWebsite = website
                            ? (/^https?:\/\//i.test(website) ? website : `https://${website}`)
                            : prev.companyWebsite;

                        return {
                            ...prev,
                            firstName: extractedData.firstName || prev.firstName,
                            lastName: extractedData.lastName || prev.lastName,
                            jobTitle: extractedData.jobTitle || prev.jobTitle,
                            companyName: extractedData.companyName || prev.companyName,
                            email: extractedData.email || prev.email,
                            phone: extractedData.phone || prev.phone,
                            companyWebsite: companyWebsite,
                        };
                    });
                }
            };
        } catch (err) {
            setError(t('cardScanError'));
            console.error(err);
        } finally {
            setIsLoading(false);
            if (e.target) {
                e.target.value = '';
            }
        }
    };
    
    const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        if (!formData.consent) {
            setError(t('consentRequiredError'));
            return;
        }
        setError(null);

        const newVisitor: VisitorData = {
            ...formData,
            id: crypto.randomUUID(),
            timestamp: new Date().toISOString(),
        };

        storageService.addSubmissionToQueue(newVisitor);
        setSuccessMessage(t('submissionSuccess'));
        setFormData(initialFormData);
        setHasNoWebsite(false);
        onFormSubmit();

        setTimeout(() => setSuccessMessage(null), 5000);
    };


    return (
        <form onSubmit={handleSubmit} className="space-y-8">
            <div className="flex flex-col md:flex-row gap-4 items-center p-4 bg-gray-100 rounded-lg">
                <button type="button" onClick={handleScanBusinessCard} disabled={isLoading} className="w-full md:w-auto flex-shrink-0 bg-red-700 text-white font-bold py-3 px-6 rounded-lg hover:bg-red-800 transition-colors disabled:bg-gray-400 flex items-center justify-center space-x-2">
                    {isLoading ? <Spinner /> : (
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
                    )}
                    <span>{t('scanCard')}</span>
                </button>
                <p className="text-gray-600 text-sm md:text-base">{t('scanCardPrompt')}</p>
                <input type="file" accept="image/*" capture="environment" ref={fileInputRef} onChange={handleFileChange} className="hidden" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
                <InputField label={t('firstName')} name="firstName" value={formData.firstName} onChange={handleInputChange} required />
                <InputField label={t('lastName')} name="lastName" value={formData.lastName} onChange={handleInputChange} required />
                <InputField label={t('jobTitle')} name="jobTitle" value={formData.jobTitle} onChange={handleInputChange} />
                <InputField label={t('companyName')} name="companyName" value={formData.companyName} onChange={handleInputChange} required/>
                <InputField label={t('email')} name="email" type="email" value={formData.email} onChange={handleInputChange} required />
                <InputField label={t('phone')} name="phone" type="tel" value={formData.phone} onChange={handleInputChange} />
                <div>
                    <InputField 
                        label={t('companyWebsite')} 
                        name="companyWebsite" 
                        type="url" 
                        value={formData.companyWebsite} 
                        onChange={handleInputChange}
                        disabled={hasNoWebsite}
                    />
                    <div className="mt-2">
                        <label className="flex items-center space-x-2 cursor-pointer">
                            <input 
                                type="checkbox" 
                                checked={hasNoWebsite} 
                                onChange={handleNoWebsiteChange}
                                className="h-4 w-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                            />
                            <span className="text-sm text-gray-700">{t('noWebsite')}</span>
                        </label>
                    </div>
                </div>
                <SelectField label={t('country')} name="country" value={formData.country} options={COUNTRIES} onChange={handleInputChange} required />
                <SelectField label={t('businessSector')} name="businessSector" value={formData.businessSector} options={BUSINESS_SECTORS} onChange={handleInputChange} required />
            </div>
            
            <CheckboxGroupField 
                legend={t('productsOfInterest')}
                options={PRODUCTS_OF_INTEREST}
                selectedOptions={formData.productsOfInterest}
                onChange={handleProductsChange}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                 <RadioGroupField
                    legend={t('preferredContactMethod')}
                    name="contactMethod"
                    options={Object.values(ContactMethod)}
                    selectedValue={formData.contactMethod}
                    onChange={handleInputChange}
                />
                <RadioGroupField
                    legend={t('leadRating')}
                    name="leadRating"
                    options={Object.values(LeadRating)}
                    selectedValue={formData.leadRating}
                    onChange={handleInputChange}
                />
            </div>
            
            <TextAreaField label={t('notes')} name="notes" value={formData.notes} onChange={handleInputChange} />

            <div>
                <label className="flex items-start space-x-3">
                    <input type="checkbox" name="consent" checked={formData.consent} onChange={handleCheckboxChange} className="mt-1 h-5 w-5 text-red-600 border-gray-300 rounded focus:ring-red-500" />
                    <span className="text-sm text-gray-700">{t('consentNotice')}</span>
                </label>
            </div>
            
            {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg" role="alert">{error}</div>}
            {successMessage && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg" role="alert">{successMessage}</div>}

            <div className="text-right">
                <button type="submit" disabled={isLoading} className="bg-green-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-green-700 transition-colors disabled:bg-gray-400 text-lg">
                    {t('submit')}
                </button>
            </div>
        </form>
    );
};
