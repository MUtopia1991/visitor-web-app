
export enum LeadRating {
    Hot = 'Hot',
    Warm = 'Warm',
    Cold = 'Cold',
}
  
export enum ContactMethod {
    Email = 'Email',
    Phone = 'Phone',
}

export interface VisitorData {
    id: string;
    timestamp: string;
    firstName: string;
    lastName: string;
    jobTitle: string;
    companyName: string;
    companyWebsite: string;
    country: string;
    businessSector: string;
    email: string;
    phone: string;
    productsOfInterest: string[];
    contactMethod: ContactMethod;
    leadRating: LeadRating;
    notes: string;
    consent: boolean;
    businessCardImage?: string; // base64 string
}
