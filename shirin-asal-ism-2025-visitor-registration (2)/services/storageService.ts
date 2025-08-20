
import type { VisitorData } from '../types';

const QUEUE_KEY = 'visitor_submission_queue';
const SUBMITTED_KEY = 'submitted_visitors';

const getQueuedSubmissions = (): VisitorData[] => {
    try {
        const item = window.localStorage.getItem(QUEUE_KEY);
        return item ? JSON.parse(item) : [];
    } catch (error) {
        console.error("Error reading from queue:", error);
        return [];
    }
};

const addSubmissionToQueue = (visitor: VisitorData) => {
    const queue = getQueuedSubmissions();
    queue.push(visitor);
    window.localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
};

const removeSubmissionFromQueue = (visitorId: string) => {
    const queue = getQueuedSubmissions();
    const newQueue = queue.filter(v => v.id !== visitorId);
    window.localStorage.setItem(QUEUE_KEY, JSON.stringify(newQueue));
};


const getSubmittedVisitors = (): VisitorData[] => {
     try {
        const item = window.localStorage.getItem(SUBMITTED_KEY);
        return item ? JSON.parse(item) : [];
    } catch (error) {
        console.error("Error reading submitted visitors:", error);
        return [];
    }
};

const addVisitorToSubmitted = (visitor: VisitorData) => {
    const submitted = getSubmittedVisitors();
    submitted.push(visitor);
    window.localStorage.setItem(SUBMITTED_KEY, JSON.stringify(submitted));
};


export const storageService = {
    getQueuedSubmissions,
    addSubmissionToQueue,
    removeSubmissionFromQueue,
    getSubmittedVisitors,
    addVisitorToSubmitted,
};
