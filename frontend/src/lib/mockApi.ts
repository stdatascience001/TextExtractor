// Mock API for document extraction

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
  fileType: "pdf" | "image";
  pages: ExtractedPage[];
  fileName: string;
  fileUrl: string; // URL for displaying the document
  extractedText?: string; // Optional full extracted text
  structuredData?: StructuredMedicalData;
  fullText?: string;
}

const API_URL = 'http://localhost:8000';

export const uploadDocument = async (file: File): Promise<ExtractedDocument> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) throw new Error('Upload failed');
  return response.json();
};

