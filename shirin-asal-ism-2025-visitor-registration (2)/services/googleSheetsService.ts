
import type { VisitorData } from '../types';
import { storageService } from './storageService';

/**
 * MOCKED Google Sheets Service.
 * In a real-world application, this `appendToSheet` function would make a secure
 * API call to a backend endpoint (e.g., a Google Cloud Function or a Google Apps Script
 * Web App URL). The backend would handle authentication and appending the row to the
 * Google Sheet to avoid exposing credentials on the client-side.
 */

// Simulates a network request to a backend that appends data to Google Sheets.
const appendToSheet = (visitor: VisitorData): Promise<{ success: boolean }> => {
    console.log("MOCK API: Appending to Google Sheet:", visitor);
    return new Promise(resolve => {
        // Simulate network latency between 500ms and 1500ms
        const delay = 500 + Math.random() * 1000;
        setTimeout(() => {
            // Removed the random failure to ensure the mock API always succeeds.
            const success = true;
            if (success) {
                console.log(`MOCK API: Successfully appended ${visitor.firstName} ${visitor.lastName}`);
                resolve({ success: true });
            } else {
                console.error(`MOCK API: Failed to append ${visitor.firstName} ${visitor.lastName}`);
                resolve({ success: false });
            }
        }, delay);
    });
};

const syncQueuedSubmissions = async (): Promise<boolean> => {
    const queuedSubmissions = storageService.getQueuedSubmissions();
    if (queuedSubmissions.length === 0) {
        return true; // Nothing to sync
    }

    // Process one submission at a time
    const submissionToSync = queuedSubmissions[0];
    try {
        const result = await appendToSheet(submissionToSync);
        if (result.success) {
            // If successful, remove it from the queue and move to "submitted"
            storageService.removeSubmissionFromQueue(submissionToSync.id);
            storageService.addVisitorToSubmitted(submissionToSync);
            // Recursively call to process next item in queue
            return syncQueuedSubmissions();
        } else {
            // If it fails, stop processing so we don't get out of order.
            console.log("Sync failed for one record, pausing sync until next interval.");
            return false;
        }
    } catch (error) {
        console.error("Error during sync:", error);
        return false;
    }
};


export const googleSheetsService = {
    syncQueuedSubmissions,
};