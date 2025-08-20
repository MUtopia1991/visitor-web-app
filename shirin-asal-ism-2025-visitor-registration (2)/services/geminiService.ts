
import { GoogleGenAI, Type } from "@google/genai";

const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

const responseSchema = {
    type: Type.OBJECT,
    properties: {
        firstName: { type: Type.STRING },
        lastName: { type: Type.STRING },
        jobTitle: { type: Type.STRING },
        companyName: { type: Type.STRING },
        phone: { type: Type.STRING },
        email: { type: Type.STRING },
        website: { type: Type.STRING },
    },
};

const extractInfoFromImage = async (base64Image: string) => {
    try {
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: {
                parts: [
                    {
                        inlineData: {
                            mimeType: 'image/jpeg',
                            data: base64Image,
                        },
                    },
                    {
                        text: 'Extract the contact information from this business card. Provide only the JSON object.',
                    },
                ],
            },
            config: {
                responseMimeType: 'application/json',
                responseSchema: responseSchema,
            },
        });
        
        const jsonText = response.text.trim();
        return JSON.parse(jsonText);

    } catch (error) {
        console.error("Error extracting info from image:", error);
        throw new Error("Failed to extract information from the business card.");
    }
};

export const geminiService = {
    extractInfoFromImage,
};