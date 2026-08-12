// Mock API for document extraction
import { getAuthHeaders } from "./api";

export interface ExtractedPage {
  pageNumber: number;
  text: string;
  imageUrl?: string; // 🔥 URL for the specific page image
}

export interface PatientInfo {
  name?: string;
  age?: string;
  gender?: string;
  date?: string;
}

export interface MedicalTestResult {
  parameter: string;
  result: string;
  unit: string;
  range: string;
}

export interface Medicine {
  name: string;
  dosage: string;
  frequency: string;
  duration: string;
}

export interface StructuredMedicalData {
  patientInfo: PatientInfo;
  testResults: MedicalTestResult[];
  medicines: Medicine[];
  diagnosis: string;
  advice: string;
  summary: string;
}

export interface ExtractedDocument {
  fileType: "pdf" | "image" | "docx" | "text" | "spreadsheet";
  pages: ExtractedPage[];
  fileName: string;
  fileUrl: string; // URL for displaying the document
  extractedText?: string; // Optional full extracted text
  structuredData?: StructuredMedicalData;
  fullText?: string;
  status?: string;
}

const API_URL = 'http://localhost:8000';

export const uploadDocument = async (file: File): Promise<any> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const activeProjectId = localStorage.getItem("activeProjectId");
  if (activeProjectId) {
    formData.append('project_id', activeProjectId);
  }

  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    headers: {
      ...getAuthHeaders(),
    },
    body: formData,
  });

  if (!response.ok) throw new Error('Upload failed');
  return response.json();
};
